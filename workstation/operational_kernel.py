"""Deterministic Operational Kernel for executing validated Operational Capabilities.

Executes browser, filesystem, and composite operational primitives without intermediate
LLM calls. Performs variable interpolation, precondition checks, postcondition verification,
and drift quarantine with handoff to reasoning when unexpected variance occurs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import time
from typing import Any, Callable
from uuid import uuid4

from workstation.artifacts import ArtifactStore
from workstation.operational_capabilities import (
    CapabilityDependency,
    CapabilityDriftError,
    CapabilityLifecycle,
    CapabilityNotFoundError,
    CapabilityResolver,
    CapabilityValidationError,
    OperationalCapability,
    OperationalCapabilityRegistry,
)
from workstation.recipes import sanitize, digest
from workstation.control_plane.verification import (
    VerificationContract, VerificationEvidence, VerificationStatus, evaluate_verification,
)
from workstation.execution_policy import EvidenceStrength


def _resolve_path(path: str, base_dir: str | Path | None = None) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p.resolve()
    base = Path(base_dir) if base_dir else Path.cwd()
    return (base / p).resolve()


def interpolate_variables(value: Any, context: dict[str, Any]) -> Any:
    """Recursively replace $inputs.<var>, $deps.<id>.<var>, $prev.<var> in values."""
    if isinstance(value, dict):
        return {k: interpolate_variables(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [interpolate_variables(v, context) for v in value]
    if isinstance(value, str):
        # Exact match single token replacement (preserves types, e.g. int, dict, list)
        token_match = re.fullmatch(r"\$([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*)", value.strip())
        if token_match:
            resolved = _lookup_dotted_path(token_match.group(1), context)
            if resolved is not None:
                return resolved

        # In-string substring template replacement (both $var and ${var})
        def _replace(match: re.Match) -> str:
            var_name = match.group(1) or match.group(2)
            resolved = _lookup_dotted_path(var_name, context)
            return str(resolved) if resolved is not None else match.group(0)

        return re.sub(r"(?:\$\{([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*)\}|\$([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*))", _replace, value)
    return value


def _lookup_dotted_path(path_str: str, context: dict[str, Any]) -> Any:
    parts = path_str.split(".")
    # Map input -> inputs alias
    if parts[0] == "input":
        parts[0] = "inputs"
    current = context
    for part in parts:
        if isinstance(current, dict):
            if part in current:
                current = current[part]
            else:
                return None
        elif isinstance(current, list):
            try:
                idx = int(part)
                current = current[idx]
            except (ValueError, IndexError):
                return None
        elif hasattr(current, part):
            current = getattr(current, part)
        else:
            return None
    return current


class OperationalKernel:
    """Engine for deterministic capability execution and composition."""

    def __init__(
        self,
        registry: OperationalCapabilityRegistry | None = None,
        resolver: CapabilityResolver | None = None,
        artifacts: ArtifactStore | None = None,
        ora_metrics: Any | None = None,
    ):
        self.artifacts = artifacts or ArtifactStore()
        self.registry = registry or OperationalCapabilityRegistry(artifacts=self.artifacts)
        self.resolver = resolver or CapabilityResolver(registry=self.registry)
        self.invocations: list[Any] = []
        if ora_metrics is not None:
            self.ora_metrics = ora_metrics
        else:
            from workstation.control_plane.metrics import ORAMetrics
            self.ora_metrics = ORAMetrics()

    # -------------------------------------------------------------------------
    # Filesystem Primitives
    # -------------------------------------------------------------------------

    def fs_stat(self, path: str, base_dir: str | Path | None = None) -> dict[str, Any]:
        target = _resolve_path(path, base_dir)
        if not target.exists():
            return {"exists": False, "path": str(target)}
        st = target.stat()
        return {
            "exists": True,
            "path": str(target),
            "is_file": target.is_file(),
            "is_dir": target.is_dir(),
            "size": st.st_size,
            "mtime": st.st_mtime,
        }

    def fs_read(self, path: str, offset: int = 0, limit: int | None = None, base_dir: str | Path | None = None) -> str:
        target = _resolve_path(path, base_dir)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {target}")
        content = target.read_text(encoding="utf-8")
        if offset:
            content = content[offset:]
        if limit is not None:
            content = content[:limit]
        return content

    def fs_write(self, path: str, content: str, overwrite: bool = True, base_dir: str | Path | None = None) -> dict[str, Any]:
        target = _resolve_path(path, base_dir)
        if target.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        # Atomic write
        temp_file = target.with_name(f"{target.name}.tmp.{os.getpid()}")
        try:
            temp_file.write_text(content, encoding="utf-8")
            temp_file.replace(target)
        except Exception:
            if temp_file.exists():
                temp_file.unlink(missing_ok=True)
            raise
        return {"success": True, "path": str(target), "size": len(content), "sha256": hashlib.sha256(content.encode()).hexdigest()}

    def fs_patch(self, path: str, target_content: str, replacement_content: str, base_dir: str | Path | None = None) -> dict[str, Any]:
        target = _resolve_path(path, base_dir)
        content = target.read_text(encoding="utf-8")
        if target_content not in content:
            raise ValueError(f"Target content not found in {target}")
        new_content = content.replace(target_content, replacement_content, 1)
        self.fs_write(str(target), new_content, overwrite=True)
        return {"success": True, "path": str(target), "modified": True}

    def fs_copy(self, src: str, dst: str, base_dir: str | Path | None = None) -> dict[str, Any]:
        src_p = _resolve_path(src, base_dir)
        dst_p = _resolve_path(dst, base_dir)
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_p, dst_p)
        return {"success": True, "src": str(src_p), "dst": str(dst_p)}

    def fs_move(self, src: str, dst: str, base_dir: str | Path | None = None) -> dict[str, Any]:
        src_p = _resolve_path(src, base_dir)
        dst_p = _resolve_path(dst, base_dir)
        dst_p.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(src_p, dst_p)
        return {"success": True, "src": str(src_p), "dst": str(dst_p)}

    def fs_hash_file(self, path: str, base_dir: str | Path | None = None) -> str:
        target = _resolve_path(path, base_dir)
        return hashlib.sha256(target.read_bytes()).hexdigest()

    def fs_list_dir(self, path: str, recursive: bool = False, base_dir: str | Path | None = None) -> list[dict[str, Any]]:
        target = _resolve_path(path, base_dir)
        if not target.is_dir():
            raise NotADirectoryError(f"Not a directory: {target}")
        results = []
        pattern = "**/*" if recursive else "*"
        for item in target.glob(pattern):
            results.append({
                "name": item.name,
                "path": str(item),
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else 0,
            })
        return results

    def fs_mkdir(self, path: str, parents: bool = True, base_dir: str | Path | None = None) -> dict[str, Any]:
        target = _resolve_path(path, base_dir)
        target.mkdir(parents=parents, exist_ok=True)
        return {"success": True, "path": str(target)}

    # -------------------------------------------------------------------------
    # Primitive Dispatch
    # -------------------------------------------------------------------------

    def lower_primitive(
        self,
        primitive: str,
        inputs: dict[str, Any],
        route: str = "native_browser",
    ) -> dict[str, Any]:
        """Lower an operational primitive into a concrete executable tool call without dispatching."""
        if primitive in {"browser_type", "type", "fill", "paste_text_semantic", "paste", "plain_text_paste"}:
            ref = inputs.get("ref") or "@e1"
            anchor = inputs.get("anchor") or inputs.get("semantic_anchor")
            default_mode = "plain_text_paste" if primitive in {"paste_text_semantic", "paste", "plain_text_paste"} else "insert_text"
            payload = {
                "ref": ref,
                "text": inputs.get("text", ""),
                "clear": inputs.get("clear", True),
                "mode": inputs.get("mode", default_mode),
            }
            if anchor:
                payload["semantic_anchor"] = anchor
            return {"tool": "browser_type", "args": payload}
        if primitive in {"browser_click", "click"}:
            return {"tool": "browser_click", "args": {"ref": inputs.get("ref", "@e1")}}
        if primitive in {"browser_navigate", "navigate"}:
            return {"tool": "browser_navigate", "args": {"url": inputs.get("url", "")}}
        return {"tool": primitive, "args": inputs}

    def execute_primitive(
        self,
        primitive: str,
        inputs: dict[str, Any],
        *,
        dispatch: Callable | None = None,
        context: dict[str, Any] | None = None,
    ) -> Any:
        ctx = context or {}
        inputs = interpolate_variables(inputs, ctx)

        # 1. Filesystem primitives
        if primitive in {"fs_stat", "stat"}:
            return self.fs_stat(inputs["path"], base_dir=inputs.get("base_dir"))
        if primitive in {"fs_read", "read_file", "read"}:
            return self.fs_read(inputs["path"], offset=inputs.get("offset", 0), limit=inputs.get("limit"), base_dir=inputs.get("base_dir"))
        if primitive in {"fs_write", "write_file", "write"}:
            return self.fs_write(inputs["path"], inputs["content"], overwrite=inputs.get("overwrite", True), base_dir=inputs.get("base_dir"))
        if primitive in {"fs_patch", "patch"}:
            return self.fs_patch(inputs["path"], inputs["target_content"], inputs["replacement_content"], base_dir=inputs.get("base_dir"))
        if primitive in {"fs_copy", "copy"}:
            return self.fs_copy(inputs["src"], inputs["dst"], base_dir=inputs.get("base_dir"))
        if primitive in {"fs_move", "move"}:
            return self.fs_move(inputs["src"], inputs["dst"], base_dir=inputs.get("base_dir"))
        if primitive in {"fs_hash", "hash_file"}:
            return self.fs_hash_file(inputs["path"], base_dir=inputs.get("base_dir"))
        if primitive in {"fs_list_dir", "list_dir"}:
            return self.fs_list_dir(inputs["path"], recursive=inputs.get("recursive", False), base_dir=inputs.get("base_dir"))
        if primitive in {"fs_mkdir", "mkdir"}:
            return self.fs_mkdir(inputs["path"], parents=inputs.get("parents", True), base_dir=inputs.get("base_dir"))

        # 2. Browser primitives (dispatched through agent scoped dispatcher or loopback)
        if primitive in {"browser_navigate", "navigate"}:
            if not dispatch:
                raise RuntimeError("Browser primitive requires dispatch function")
            nav_args = {"url": inputs["url"]}
            if ctx.get("operation_id"):
                nav_args["operation_id"] = ctx["operation_id"]
            return dispatch("browser_navigate", nav_args)
        if primitive in {"browser_snapshot", "snapshot"}:
            if not dispatch:
                raise RuntimeError("Browser primitive requires dispatch function")
            return dispatch("browser_snapshot", {"full": inputs.get("full", False)})
        if primitive in {"browser_click", "click"}:
            if not dispatch:
                raise RuntimeError("Browser primitive requires dispatch function")
            ref = inputs.get("ref")
            if not ref and inputs.get("anchor"):
                snap = dispatch("browser_snapshot", {"full": False})
                elements = snap.get("elements", []) if isinstance(snap, dict) else []
                ref = self._find_ref_by_anchor(elements, inputs["anchor"])
            if not ref:
                raise CapabilityDriftError(f"Target ref could not be resolved for click: {inputs}")
            return dispatch("browser_click", {"ref": ref})
        if primitive in {"browser_type", "type", "fill", "paste_text_semantic", "paste", "plain_text_paste"}:
            if not dispatch:
                raise RuntimeError("Browser primitive requires dispatch function")
            ref = inputs.get("ref")
            anchor = inputs.get("anchor") or inputs.get("semantic_anchor")
            if not ref and anchor:
                snap = dispatch("browser_snapshot", {"full": False})
                elements = snap.get("elements", []) if isinstance(snap, dict) else []
                ref = self._find_ref_by_anchor(elements, anchor)
            if not ref and not anchor:
                raise CapabilityDriftError(f"Target ref could not be resolved for type: {inputs}")
            default_mode = "plain_text_paste" if primitive in {"paste_text_semantic", "paste", "plain_text_paste"} else "insert_text"
            type_payload = {
                "ref": ref or "@e1",
                "text": inputs.get("text", ""),
                "clear": inputs.get("clear", True),
            }
            if "mode" in inputs or primitive in {"paste_text_semantic", "paste", "plain_text_paste"}:
                type_payload["mode"] = inputs.get("mode", default_mode)
            if anchor:
                type_payload["semantic_anchor"] = anchor
            return dispatch("browser_type", type_payload)
        if primitive in {"browser_read_http", "read_http"}:
            if not dispatch:
                raise RuntimeError("Browser primitive requires dispatch function")
            return dispatch("browser_read_http", {
                "url": inputs["url"],
                "method": inputs.get("method", "GET"),
                "headers": inputs.get("headers", {}),
            })
        if primitive in {"browser_press", "press"}:
            if not dispatch:
                raise RuntimeError("Browser primitive requires dispatch function")
            return dispatch("browser_press", {"key": inputs["key"]})
        if primitive in {"browser_scroll", "scroll"}:
            if not dispatch:
                raise RuntimeError("Browser primitive requires dispatch function")
            return dispatch("browser_scroll", {"direction": inputs.get("direction", "down")})
        if primitive in {"browser_extract_items", "extract_items"}:
            if not dispatch:
                raise RuntimeError("Browser primitive requires dispatch function")
            return dispatch("browser_extract_items", inputs)

        # 3. Control primitives
        if primitive == 'process_observe':
            observer = ctx.get('process_observer')
            if not callable(observer):
                raise CapabilityDriftError('owner-controlled process observer required')
            result = observer(inputs)
            from workstation.experience_compiler.state_abstraction import abstract_state
            return abstract_state('host_process', result).semantic_predicates
        if primitive in {"wait", "sleep"}:
            duration = float(inputs.get("duration", inputs.get("seconds", 0.5)))
            time.sleep(min(10.0, max(0.01, duration)))
            return {"waited_seconds": duration}

        # 4. Fallback dispatch
        if dispatch:
            return dispatch(primitive, inputs)
        raise ValueError(f"Unknown primitive: {primitive}")

    def _find_ref_by_anchor(self, elements: list[dict[str, Any]], anchor: dict[str, Any]) -> str | None:
        if anchor.get('type') in {'testid', 'role_name', 'text'}:
            from workstation.memory import ProcedureStep
            return ProcedureStep(action='resolve', fallback_anchors=[anchor]).resolve_anchor(elements, strict=True) if elements else None
        anchor_type = anchor.get("type")
        anchor_val = str(anchor.get("value", "")).lower()
        if anchor_type == "testid":
            for el in elements:
                tid = str(el.get("testid", el.get("attributes", {}).get("data-testid", ""))).lower()
                if tid and tid == anchor_val:
                    return el.get("ref")
        elif anchor_type == "name":
            for el in elements:
                n = str(el.get("name", "")).lower()
                if n and n == anchor_val:
                    return el.get("ref")
        elif anchor_type == "role_name":
            role_req, _, label_req = anchor_val.partition(":")
            for el in elements:
                r = str(el.get("role", "")).lower()
                lbl = str(el.get("label", el.get("name", ""))).lower()
                if role_req in r and label_req in lbl:
                    return el.get("ref")
        return None

    # -------------------------------------------------------------------------
    # Condition Verification (Preconditions / Postconditions)
    # -------------------------------------------------------------------------

    def verify_condition(self, condition: str | dict[str, Any], context: dict[str, Any]) -> bool:
        if isinstance(condition, str):
            try:
                cond_dict = json.loads(condition)
            except (ValueError, TypeError):
                return False
        elif isinstance(condition, dict):
            cond_dict = condition
        else:
            return False

        if not isinstance(cond_dict, dict):
            return False

        cond_dict = interpolate_variables(cond_dict, context)
        c_type = cond_dict.get("type")

        if c_type == 'semantic_predicate':
            if "key" not in cond_dict or "expected" not in cond_dict:
                return False
            state = context.get('semantic_state', {})
            return cond_dict['key'] in state and state[cond_dict['key']] == cond_dict['expected']

        if c_type == "file_exists":
            if "path" not in cond_dict:
                return False
            target = _resolve_path(cond_dict["path"], cond_dict.get("base_dir"))
            return target.exists()
        if c_type == "file_hash":
            if "path" not in cond_dict or "expected" not in cond_dict:
                return False
            target = _resolve_path(cond_dict["path"], cond_dict.get("base_dir"))
            if not target.exists():
                return False
            actual_hash = hashlib.sha256(target.read_bytes()).hexdigest()
            return actual_hash.lower() == str(cond_dict["expected"]).lower()
        if c_type == "file_contains":
            if "path" not in cond_dict or "text" not in cond_dict:
                return False
            target = _resolve_path(cond_dict["path"], cond_dict.get("base_dir"))
            if not target.exists():
                return False
            return str(cond_dict["text"]) in target.read_text(encoding="utf-8")
        if c_type == "field_equals":
            if "field" not in cond_dict or "expected" not in cond_dict:
                return False
            actual = _lookup_dotted_path(cond_dict["field"], context)
            return actual == cond_dict["expected"]
        if c_type == "not_empty":
            if "field" not in cond_dict:
                return False
            actual = _lookup_dotted_path(cond_dict["field"], context)
            return bool(actual)
        return False

    def check_conditions(self, conditions: list[str | dict[str, Any]], context: dict[str, Any], stage: str) -> None:
        for cond in conditions:
            if not self.verify_condition(cond, context):
                raise CapabilityDriftError(f"{stage.capitalize()} condition failed: {cond}")

    # -------------------------------------------------------------------------
    # Execution & Composition
    # -------------------------------------------------------------------------

    def execute_capability(
        self,
        capability_or_id: str | OperationalCapability,
        inputs: dict[str, Any],
        *,
        version: str | None = None,
        dispatch: Callable | None = None,
        context: dict[str, Any] | None = None,
        owner: str | None = None,
    ) -> dict[str, Any]:
        """Execute a capability, resolving its dependencies and running deterministic steps."""
        if isinstance(capability_or_id, str):
            pinned = (context or {}).get('capability_pins', {}).get(capability_or_id)
            cap = self.resolver.resolve(capability_or_id, pinned['version'] if pinned else version or '*')
            if pinned and (cap.semantic_fingerprint != pinned['semantic_fingerprint'] or
                           cap.compatibility_fingerprint != pinned['compatibility_fingerprint']):
                raise CapabilityDriftError('pinned dependency contract changed')
            if pinned and pinned.get('contract_fingerprint'):
                from workstation.experience_compiler.promotion import contract_fingerprint
                if contract_fingerprint(cap) != pinned['contract_fingerprint']:
                    raise CapabilityDriftError('pinned dependency implementation changed')
        else:
            cap = capability_or_id

        if cap.drift_state == "quarantined":
            raise CapabilityDriftError(f"Capability '{cap.id}' is quarantined due to operational drift")

        exec_context: dict[str, Any] = {
            "inputs": dict(inputs),
            "deps": {},
            "steps": {},
            "prev": None,
        }
        if context:
            exec_context.update({k: v for k, v in context.items() if k not in exec_context})

        task_id = str(exec_context.get("task_id") or owner or getattr(self, "task_id", None) or "task_default")
        run_id = str(exec_context.get("run_id") or getattr(self, "run_id", None) or "run_default")
        operation_id = str(
            exec_context.get("operation_id")
            or getattr(self, "operation_id", None)
            or f"op_{cap.id}_{uuid4().hex[:8]}"
        )
        exec_context["task_id"] = task_id
        exec_context["run_id"] = run_id
        exec_context["operation_id"] = operation_id
        from workstation.telemetry import TelemetryEventType, emit_event
        emit_event(TelemetryEventType.CAPABILITY_EXECUTION_STARTED,
                   source_owner="workstation.operational_kernel", task_id=task_id,
                   run_id=run_id, operation_id=operation_id, capability_id=cap.id,
                   capability_version=cap.version, route=cap.route, status="started",
                   dedupe_key=f"capability-start:{operation_id}",
                   payload={"learned": cap.provenance.get('source') == 'experience_compiler',
                            "composite": cap.route == "composite"})

        learned = cap.provenance.get('source') == 'experience_compiler'
        if learned and cap.lifecycle.value != 'promoted' and not exec_context.get('learning_replay'):
            raise CapabilityValidationError('learned candidates require controlled replay before execution')
        if learned:
            from workstation.experience_compiler.generalization import validate_inputs
            validate_inputs(cap.input_schema, cap.learning_metadata.get('relations', []), inputs)
            if cap.lifecycle.value == 'promoted' and not exec_context.get('learning_replay'):
                from workstation.control_plane.validity_envelope import derive_validity_envelope
                if cap.route == 'native_browser' and cap.scope.get('host'):
                    from urllib.parse import urlsplit

                    navigation = next((step for step in cap.implementation.get('steps', [])
                                       if step.get('primitive') == 'browser_navigate'), None)
                    if navigation is not None:
                        bound = interpolate_variables(navigation.get('args', {}), exec_context)
                        bound_url = urlsplit(str(bound.get('url') or ''))
                        bound_host = bound_url.hostname
                        if bound_host != cap.scope['host'] or (
                            cap.scope.get('path_family') and (bound_url.path or '/') != cap.scope['path_family']
                        ):
                            raise CapabilityValidationError('bound navigation escaped learned host scope')
                        exec_context.setdefault('host', bound_host)
                        exec_context.setdefault('path_family', bound_url.path or '/')
                envelope = derive_validity_envelope(cap, current_context=exec_context)
                if not envelope.is_valid(exec_context):
                    return {"success": False, "execution_acknowledged": False,
                            "status": "NEEDS_REASONING", "reason": "validity_envelope_unproven",
                            "validity_envelope": envelope.to_dict()}
        durable_store = exec_context.get('durable_store')
        durable_item_id = exec_context.get('durable_item_id')
        checkpoint_prefix = cap.id + '@' + cap.version

        def observe_semantics(output=None):
            from workstation.experience_compiler.state_abstraction import abstract_state, filesystem_state
            if cap.route == 'native_browser':
                if (learned and output is not None and navigation_target
                        and isinstance(cap.verifier_contract, dict)
                        and cap.verifier_contract.get('observer') == 'workstation.browser_session_state'):
                    from tools.browser_workstation import read_native_browser_session_state

                    readback = read_native_browser_session_state(
                        str(exec_context.get('task_id') or owner or ''),
                        str(exec_context.get('session_id') or ''),
                        str(exec_context.get('run_id') or ''),
                        str(navigation_target),
                    )
                    return abstract_state(cap.route, readback).semantic_predicates
                if not dispatch:
                    raise CapabilityDriftError('semantic browser observation unavailable')
                raw = dispatch('browser_snapshot', {'full': False})
                if isinstance(raw, str):
                    raw = json.loads(raw)
                if output is not None and cap.scope.get('host'):
                    from urllib.parse import urlsplit
                    if urlsplit(raw.get('url', '')).hostname != cap.scope['host']:
                        raise CapabilityDriftError('browser scope drift')
                return abstract_state(cap.route, raw).semantic_predicates
            if cap.route == 'filesystem':
                steps = cap.implementation.get('steps', [])
                step = steps[-1] if output is not None else steps[0]
                args = interpolate_variables(step.get('args', {}), exec_context)
                path = args.get('path') or args.get('src')
                return filesystem_state(path).semantic_predicates if path else {}
            if cap.route == 'host_process':
                observer = exec_context.get('process_observer')
                if not callable(observer):
                    raise CapabilityDriftError('process observation owner unavailable')
                return abstract_state('host_process', observer(inputs)).semantic_predicates
            if cap.route == 'composite':
                state = {}
                for backend in cap.scope.get('backends', {}):
                    if backend == 'filesystem':
                        filesystem_steps = [s for s in cap.implementation.get('steps', [])
                                            if (s.get('primitive') or '').startswith('fs_')]
                        if filesystem_steps:
                            selected = filesystem_steps[-1] if output is not None else filesystem_steps[0]
                            arguments = interpolate_variables(selected.get('args', {}), exec_context)
                            path = arguments.get('path') or arguments.get('src')
                            if path:
                                state.update(filesystem_state(path).semantic_predicates)
                    elif backend == 'host_process':
                        observer = exec_context.get('process_observer')
                        if not callable(observer):
                            raise CapabilityDriftError('composite process owner unavailable')
                        state.update(abstract_state(backend, observer(inputs)).semantic_predicates)
                    elif backend == 'native_browser':
                        if not dispatch:
                            raise CapabilityDriftError('composite browser owner unavailable')
                        raw = dispatch('browser_snapshot', {'full': False})
                        raw = json.loads(raw) if isinstance(raw, str) else raw
                        from urllib.parse import urlsplit
                        host = cap.scope['backends'][backend].get('host')
                        if host and urlsplit(raw.get('url', '')).hostname != host:
                            raise CapabilityDriftError('composite browser scope drift')
                        state.update(abstract_state(backend, raw).semantic_predicates)
                    else:
                        raise CapabilityDriftError('unsupported composite state owner')
                return state
            return abstract_state(cap.route, output or {}).semantic_predicates

        try:
            # 1. Execute dependencies in topological order
            for dep in cap.dependencies:
                dep_cap = self.registry.get(dep.capability_id)
                if not dep_cap or dep_cap.drift_state != "healthy":
                    raise CapabilityDriftError(f"Child capability '{dep.capability_id}' has drifted ({getattr(dep_cap, 'drift_state', 'missing')}); blocking composite execution")
                pins = exec_context.get("capability_pins") or {}
                if dep.capability_id in pins:
                    pin = pins[dep.capability_id]
                    if pin.get("version") and dep_cap.version != pin["version"]:
                        raise CapabilityDriftError(f"Child capability '{dep.capability_id}' pin changed from {pin['version']} to {dep_cap.version}")
                dep_inputs = {}
                for target_field, src_path in dep.input_mappings.items():
                    val = _lookup_dotted_path(src_path, exec_context)
                    if val is not None:
                        dep_inputs[target_field] = val
                    else:
                        dep_inputs[target_field] = interpolate_variables(src_path, exec_context)

                dep_result = self.execute_capability(
                    dep.capability_id,
                    dep_inputs,
                    version=dep.version_constraint,
                    dispatch=dispatch,
                    context=exec_context,
                    owner=owner,
                )
                if dep_result.get('status') == 'NEEDS_REASONING':
                    return dep_result
                dep_key = dep.output_alias or dep.capability_id
                exec_context["deps"][dep_key] = dep_result

            # 2. Verify preconditions
            pre_checkpoint = checkpoint_prefix + '_preconditions'
            pre_verified = durable_store and durable_store.get_item(durable_item_id).checkpoints.get(pre_checkpoint)
            if learned and cap.preconditions and not pre_verified:
                exec_context['semantic_state'] = observe_semantics()
            if not pre_verified:
                self.check_conditions(cap.preconditions, exec_context, stage="precondition")
                if durable_store:
                    durable_store.update_item_checkpoint(durable_item_id, pre_checkpoint)

            # 3. Execute implementation steps
            steps = cap.implementation.get("steps", [])
            output = None
            navigation_target = None
            for idx, step in enumerate(steps):
                step_id = step.get("id", f"step_{idx}")
                primitive = step.get("primitive") or step.get("tool") or step.get("action")
                step_args = step.get("args") or step.get("inputs") or {}
                checkpoint = checkpoint_prefix + '_' + step_id
                if durable_store:
                    cp = durable_store.get_item(durable_item_id).checkpoints
                    if cp.get(checkpoint + '_meta', {}).get('result_ref'):
                        result_ref = cp[checkpoint + '_meta']['result_ref']
                        try:
                            output = self.artifacts.read_json(result_ref)
                        except json.JSONDecodeError:
                            # Primitive results can be either structured JSON or a
                            # raw textual artifact.  A completed checkpoint must be
                            # replayed exactly as persisted, never re-dispatched.
                            output = self.artifacts.read(result_ref)
                        exec_context['steps'][step_id], exec_context['prev'] = output, output
                        continue
                    if cp.get(checkpoint + '_dispatch'):
                        raise CapabilityDriftError('uncertain mutation requires reconciliation; no blind retry')
                if learned and step.get('when'):
                    exec_context['semantic_state'] = observe_semantics(output)
                    if not all(exec_context['semantic_state'].get(k) == v for k, v in step['when'].items()):
                        continue
                from tools.effects import tool_effect, READ_EFFECTS
                owner_reads = {'fs_stat', 'fs_read', 'fs_hash', 'fs_list_dir', 'stat', 'read', 'hash_file', 'list_dir',
                               'process_observe', 'wait', 'sleep'}
                mutating = primitive not in owner_reads and tool_effect(primitive) not in READ_EFFECTS
                route = 'filesystem' if primitive.startswith('fs_') or primitive in {'read_file', 'write_file', 'stat', 'copy', 'move', 'mkdir', 'hash_file'} else 'host_process' if primitive == 'process_observe' else 'native_browser'
                admission = exec_context.get('primitive_admission')
                if admission:
                    admission(route, mutating)
                bound_args = interpolate_variables(step_args, exec_context)
                if learned and cap.route == 'native_browser' and primitive == 'browser_navigate':
                    navigation_target = bound_args.get('url')
                filesystem_scope = cap.scope.get('backends', {}).get('filesystem', cap.scope)
                if learned and route == 'filesystem' and filesystem_scope.get('base_dir'):
                    base = Path(filesystem_scope['base_dir']).resolve()
                    for key in ('path', 'src', 'dst'):
                        if key in bound_args and not _resolve_path(bound_args[key], bound_args.get('base_dir')).is_relative_to(base):
                            raise CapabilityDriftError('filesystem target escaped exact learned scope')
                if durable_store and mutating:
                    durable_store.update_item_checkpoint(durable_item_id, checkpoint + '_dispatch')
                try:
                    step_result = self.execute_primitive(primitive, bound_args, dispatch=dispatch, context=exec_context)
                except Exception as exc:
                    if durable_store or learned:
                        raise CapabilityDriftError(f'primitive failed; reconcile dispatched effects: {type(exc).__name__}') from exc
                    raise
                if durable_store:
                    ref = self.artifacts.store(owner or cap.id, digest({'checkpoint': checkpoint, 'result': sanitize(step_result)}) + '.json', sanitize(step_result))
                    durable_store.update_item_checkpoint(durable_item_id, checkpoint, metadata={'result_ref': ref.ref})
                exec_context["steps"][step_id] = step_result
                exec_context["prev"] = step_result
                output = step_result

            # If implementation declares explicit return mapping or output
            if "output" in cap.implementation:
                output = interpolate_variables(cap.implementation["output"], exec_context)
            elif output is None:
                output = {"success": True, "id": cap.id, "version": cap.version}

            exec_context["output"] = output

            # 4. Verify postconditions
            if learned:
                exec_context['semantic_state'] = observe_semantics(output)
            self.check_conditions(cap.postconditions, exec_context, stage="postcondition")

            formal_verifier = None
            if isinstance(cap.formal_contract, dict):
                formal_verifier = cap.formal_contract.get("verifier")
            elif cap.formal_contract is not None:
                formal_verifier = getattr(cap.formal_contract, "verifier", None)
            verifier_raw = cap.verifier_contract or formal_verifier or {}
            verifier_contract = (
                verifier_raw if isinstance(verifier_raw, VerificationContract)
                else VerificationContract.from_dict(verifier_raw)
            )
            expected_verification_value = exec_context.get(
                "verification_expected",
                verifier_contract.relation_parameters.get("expected", exec_context.get("semantic_state")),
            )
            task_id = exec_context["task_id"]
            run_id = exec_context["run_id"]
            operation_id = exec_context["operation_id"]

            supplied_evidence = exec_context.get("verification_evidence")
            if (supplied_evidence is None and learned and cap.route == 'native_browser'
                    and navigation_target and verifier_contract.observer == 'workstation.browser_session_state'
                    and verifier_contract.source_kind == 'browser_local_persistence'):
                from tools.browser_workstation import read_native_browser_session_state
                from workstation.experience_compiler.state_abstraction import abstract_state

                try:
                    readback = read_native_browser_session_state(
                        task_id, str(exec_context.get('session_id') or ''), run_id, str(navigation_target),
                        expected_operation_id=operation_id,
                        require_owner_receipt=True,
                    )
                    last_receipt = readback.get('last_receipt') or {}
                    proven_op_id = last_receipt.get('operationId')
                    if not proven_op_id or proven_op_id != operation_id:
                        raise ValueError(f"Browser owner receipt operation_id mismatch: expected {operation_id}, got {proven_op_id}")
                    projected = abstract_state('native_browser', readback).semantic_predicates
                    expected_effects = cap.learning_metadata.get('effects') or {}
                    observed_effects = {key: projected[key] for key in expected_effects}
                    from workstation.control_plane.ir import EQ
                    observed_coverage = tuple(EQ(key, value).fingerprint()
                                              for key, value in sorted(observed_effects.items()))
                    if 'verification_expected' not in exec_context:
                        expected_verification_value = expected_effects
                    ref = self.artifacts.store(task_id,
                        'learned_browser_readback_' + digest({'operation_id': operation_id, 'state': readback}) + '.json',
                        {**readback, 'operation_id': operation_id, 'observed_effects': observed_effects},
                        schema='hermes.browser_local_readback.v1')
                    supplied_evidence = [VerificationEvidence(
                        evidence_id='browser_session:' + operation_id,
                        observer='workstation.browser_session_state',
                        source_kind='browser_local_persistence', value=observed_effects,
                        evidence_strength=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
                        trust_class='trusted_runtime', observer_failure_domain='browser_session_persistence',
                        resource_id=f"browser_task:{task_id}:tab:{readback['tab_id']}",
                        resource_version=str(readback.get('revision', readback['saved_at'])),
                        observed_at=readback.get('saved_at') or datetime.now(timezone.utc).isoformat(), read_after_write=True,
                        covered_predicates=observed_coverage,
                        artifact_ref=ref.ref, task_id=task_id, run_id=run_id, operation_id=operation_id,
                    )]
                except (OSError, ValueError, KeyError, TypeError):
                    supplied_evidence = []
            if supplied_evidence is None:
                # Do NOT manufacture evidence from expected values!
                # Only execute real observers if available.
                observed_val = None
                has_real_observation = False
                obs_fn = exec_context.get("observer_fn") or exec_context.get("readback_fn")
                if obs_fn is None and isinstance(exec_context.get("observers"), dict):
                    obs_fn = exec_context["observers"].get(verifier_contract.observer)

                if obs_fn is not None:
                    try:
                        observed_val = obs_fn()
                        has_real_observation = True
                    except Exception:
                        has_real_observation = False
                elif verifier_contract.observer and verifier_contract.observer in {'fs_stat', 'fs_read', 'fs_hash', 'stat', 'read', 'hash_file'}:
                    obs_args = exec_context.get("observer_args", {})
                    try:
                        observed_val = self.execute_primitive(verifier_contract.observer, obs_args, context=exec_context)
                        has_real_observation = True
                    except Exception:
                        has_real_observation = False
                elif learned and exec_context.get('semantic_state') is not None:
                    observed_val = exec_context.get('semantic_state')
                    has_real_observation = True

                if has_real_observation:
                    # An observer may return a fully declared receipt.  Raw
                    # legacy values retain only the runtime surface we know;
                    # contract requirements never fill their provenance.
                    if isinstance(observed_val, VerificationEvidence):
                        supplied_evidence = [observed_val]
                    elif isinstance(observed_val, dict) and {"evidence_id", "observer", "source_kind", "value"} <= set(observed_val):
                        supplied_evidence = [VerificationEvidence.from_dict(observed_val)]
                    else:
                        builtin_fs = verifier_contract.observer in {'fs_stat', 'fs_read', 'fs_hash', 'stat', 'read', 'hash_file'}
                        supplied_evidence = [VerificationEvidence(
                            evidence_id=f"observation:{cap.id}:{cap.version}",
                            observer=verifier_contract.observer if builtin_fs else "legacy_raw_observer",
                            source_kind="filesystem" if builtin_fs else ("browser_dom" if cap.route in {"browser", "native_browser"} else "runtime_state"),
                            value=observed_val,
                            evidence_strength=(EvidenceStrength.SEMANTIC_PERSISTED_READBACK if builtin_fs else EvidenceStrength.SAME_SESSION_SEMANTIC_OBSERVATION),
                            trust_class="trusted_runtime" if builtin_fs else "untrusted",
                            observer_failure_domain="filesystem" if builtin_fs else ("browser_renderer" if cap.route in {"browser", "native_browser"} else "runtime"),
                            resource_id=str(exec_context.get("resource_id", "")),
                            resource_version=str(exec_context.get("resource_version", "")),
                            observed_at=datetime.now(timezone.utc).isoformat(),
                            read_after_write=bool(builtin_fs), operation_id=operation_id,
                            task_id=task_id, run_id=run_id,
                            covered_predicates=tuple(exec_context.get("observed_predicates", ())),
                        )]
                else:
                    supplied_evidence = []
            verification_result = evaluate_verification(
                verifier_contract,
                expected_verification_value,
                supplied_evidence,
                required_predicates=set(verifier_contract.covered_predicates),
                mutation_failure_domains=set(exec_context.get("mutation_failure_domains", ())),
                mutation_observed_at=str(exec_context.get("mutation_observed_at", "")),
                transition_required=verifier_contract.transition_claim,
                expected_operation_id=operation_id,
                expected_run_id=exec_context.get("expected_run_id"),
                expected_task_id=exec_context.get("expected_task_id"),
            )
            try:
                self.ora_metrics.record_verification(verification_result)
            except Exception:
                pass
            emit_event(TelemetryEventType.VERIFICATION_COMPLETED,
                       source_owner="workstation.verification", task_id=task_id,
                       run_id=run_id, operation_id=operation_id, capability_id=cap.id,
                       capability_version=cap.version, route=cap.route,
                       status=verification_result.status.value,
                       reason_code=verification_result.reason,
                       evidence_refs=tuple(verification_result.evidence_refs),
                       dedupe_key=f"verification:{operation_id}:{verification_result.verifier_fingerprint}",
                       payload={"verifier_fingerprint": verification_result.verifier_fingerprint,
                                "predicate_coverage_count": len(verification_result.covered_predicates)})

            # 5. Record validation evidence & savings
            evidence = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "success",
                "inputs_sample": sanitize(inputs),
            }
            if verification_result.verified:
                cap.success_count += 1
            if learned and verification_result.verified:
                cap.savings['deterministic_replays'] = cap.savings.get('deterministic_replays', 0) + 1
                cap.savings['executor_llm_calls'] = 0
            elif not learned and verification_result.verified:
                cap.savings["llm_calls_saved"] = cap.savings.get("llm_calls_saved", 0) + 1
                cap.savings["tokens_saved"] = cap.savings.get("tokens_saved", 0) + 1500
            if not exec_context.get('learning_replay'):
                self.registry.register(cap)

            from workstation.experience_compiler.models import CapabilityInvocation
            auth_scope = exec_context.get("authority_scope") or getattr(self, "authority_scope", None)
            if hasattr(auth_scope, "to_dict"):
                auth_scope = auth_scope.to_dict()

            invocation = CapabilityInvocation(
                invocation_id=f"inv_{uuid4().hex[:16]}",
                capability_id=cap.id,
                capability_version=cap.version,
                run_id=run_id,
                task_id=task_id,
                operation_id=operation_id,
                inputs=sanitize(inputs),
                state_before=exec_context.get("semantic_state_before") or {},
                state_after=exec_context.get("semantic_state") or {},
                delta={},
                status="COMMITTED" if verification_result.verified else "ACKNOWLEDGED",
                verified=verification_result.verified,
                verifier_status=verification_result.status.value,
                verifier_fingerprint=verification_result.verifier_fingerprint,
                verification_evidence_refs=list(verification_result.evidence_refs),
                covered_predicates=list(verification_result.covered_predicates),
                freshness_satisfied=verification_result.freshness_satisfied,
                verification_reason=verification_result.reason,
                authority_scope=auth_scope,
                timestamp=datetime.now(timezone.utc).timestamp(),
            )
            self.invocations.append(invocation)

            # Durable persistence in ArtifactStore
            try:
                self.artifacts.store(task_id, f"invocation_{invocation.invocation_id}.json", invocation.to_dict())
            except Exception:
                pass

            # Durable persistence in ExecutionJournal
            try:
                from workstation.journal import ExecutionJournal
                from workstation.contracts import ExecutionEventKind
                journal = ExecutionJournal(task_id=task_id, session_id=run_id)
                journal.record(
                    ExecutionEventKind.ACTION,
                    f"CapabilityInvocation {invocation.invocation_id} committed",
                    metadata=invocation.to_dict(),
                )
            except Exception:
                pass

            # Record in ORAMetrics
            try:
                is_comp = (
                    cap.route == "composite"
                    or bool(cap.dependencies)
                    or (isinstance(cap.learning_metadata, dict) and bool(cap.learning_metadata.get("composite")))
                )
                self.ora_metrics.record_capability_invocation(is_composite=is_comp)
                self.ora_metrics.record_transition(
                    verified=verification_result.verified,
                    reasoned=bool(exec_context.get("reasoned") or exec_context.get("learning_replay")),
                )
            except Exception:
                pass

            emit_event(TelemetryEventType.CAPABILITY_EXECUTION_FINISHED,
                       source_owner="workstation.operational_kernel", task_id=task_id,
                       run_id=run_id, operation_id=operation_id, capability_id=cap.id,
                       capability_version=cap.version, route=cap.route,
                       status="VERIFIED" if verification_result.verified else "ACKNOWLEDGED",
                       provider_calls=0 if learned else None,
                       dedupe_key=f"capability-finish:{operation_id}")
            return {
                # Compatibility boundary: older kernel callers consume success
                # as a physical execution ACK.  Terminal owners must consume
                # verification_result (TaskCompiler does) and never this flag.
                "success": True,
                "execution_acknowledged": True,
                "capability_id": cap.id,
                "capability_version": cap.version,
                "output": output,
                "savings": cap.savings,
                # Primitive acknowledgement is not terminal evidence. Emit an
                # accepted verifier only after declared readback or learned
                # semantic observation has actually run.
                "verification": {
                    "accepted": verification_result.verified,
                    "source": "semantic_observer" if learned else (
                        "declared_postconditions" if cap.postconditions else "none"
                    ),
                },
                "verification_result": verification_result.to_dict(),
            }

        except CapabilityDriftError as drift_err:
            if not exec_context.get('learning_replay'):
                self.registry.record_drift(cap.id, str(drift_err), quarantine=True, version=cap.version)
            if owner:
                from workstation.reasoning_handoff import needs_reasoning
                handoff = needs_reasoning(
                    self.artifacts,
                    owner,
                    completed_until=exec_context.get("prev"),
                    expected=f"Capability '{cap.id}' postconditions satisfied",
                    observed=str(drift_err),
                    safe_to_resume=False,
                    context={"capability_id": cap.id, "phase": "operational_kernel"},
                )
                return handoff
            raise

    def load_invocations(self, task_id: str):
        """Reload persisted CapabilityInvocations from ArtifactStore."""
        invocations = []
        safe_task = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in task_id)
        task_dir = self.artifacts.root / safe_task
        if task_dir.exists():
            for p in sorted(task_dir.glob("invocation_*.json")):
                if not p.name.endswith(".meta.json"):
                    try:
                        data = json.loads(p.read_text(encoding="utf-8"))
                        from workstation.experience_compiler.models import CapabilityInvocation
                        invocations.append(CapabilityInvocation.from_dict(data))
                    except Exception:
                        pass
        return invocations

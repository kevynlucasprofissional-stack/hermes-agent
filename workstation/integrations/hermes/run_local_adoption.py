"""Hermes binding of run-local adoption: the runtime owner and its safe checkpoint.

``build_run_adoption_owner`` supplies canonical facts and certified dispatch for ONE agent's
TaskRun; ``workstation_run_local_checkpoint`` is called from the pre-reasoning boundary
(``workstation_operational_resolution``), where no tool is in flight and the agent thread
owns the run. It never starts the learning plane, never answers the turn, and when anything
is not provable it simply returns so ordinary reasoning continues.
"""
from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar
import hashlib
import json
import logging
import re
from types import SimpleNamespace
import uuid
from typing import Any

from workstation.artifacts import ArtifactStore
from workstation.durable_tasks import DurableTaskStore, WorkItem
from workstation.integrations.hermes.effect_authority import trusted_effect_authority_from_agent
from workstation.run_adoption import AdoptionReport, DurableRunAdoptionOwner, RunLocalAdopter

logger = logging.getLogger(__name__)

_in_adoption_checkpoint: ContextVar[bool] = ContextVar("workstation_in_adoption_checkpoint", default=False)


# Primitives supported by the owner. Readback admission is narrower: a raw tool
# response is not an independent verifier for browser_snapshot / trello_api_get.
_SUPPORTED = ("write_file", "read_file", "browser_navigate", "browser_snapshot", "trello_api_get", "browser_extract_items")
_READBACK = ("write_file", "browser_navigate", "browser_extract_items")
_GUTTER = re.compile(r"^\s*\d+\|", re.MULTILINE)


def _readback_write_file(dispatch, artifacts: ArtifactStore, task_id: str):
    """Independent read-after-write through the agent's own ``read_file``; exact content match."""
    def readback(primitive: str, bound_args: dict, raw: Any) -> dict | None:
        if primitive != "write_file" or "content" not in bound_args or "path" not in bound_args:
            return None
        try:
            observed = json.loads(dispatch("read_file", {"path": bound_args["path"]}))
            text = _GUTTER.sub("", str(observed.get("content", "")))
        except Exception:
            return {"ok": False, "evidence_ref": None}
        expected = str(bound_args["content"])
        ok = text.rstrip("\n") == expected.rstrip("\n")
        ref = artifacts.store(task_id, f"readback_{uuid.uuid4().hex[:10]}.json", {
            "primitive": primitive, "path": bound_args["path"], "matched": ok,
            "observed_sha": hashlib.sha256(text.encode()).hexdigest(),
            "expected_sha": hashlib.sha256(expected.encode()).hexdigest(),
        }, schema="workstation.run_local_readback.v1").ref
        return {"ok": ok, "evidence_ref": ref}
    return readback


def _readback_browser_navigate(dispatch, artifacts: ArtifactStore, task_id: str):
    """Independent readback for browser_navigate via browser_snapshot URL verification."""
    def readback(primitive: str, bound_args: dict, raw: Any) -> dict | None:
        if primitive != "browser_navigate" or "url" not in bound_args:
            return None
        expected_url = bound_args["url"]
        try:
            observed = json.loads(dispatch("browser_snapshot", {"full": False}))
            # Extract URL from snapshot
            observed_url = ""
            if isinstance(observed, dict):
                for key in ("url", "current_url", "currentUrl", "page_url", "pageUrl"):
                    val = observed.get(key)
                    if isinstance(val, str) and val.startswith("https://"):
                        observed_url = val
                        break
        except Exception:
            return {"ok": False, "evidence_ref": None}
        from workstation.prefabs.engine import same_destination
        ok = same_destination(observed_url, expected_url)
        ref = artifacts.store(task_id, f"readback_{uuid.uuid4().hex[:10]}.json", {
            "primitive": primitive, "expected_url": expected_url, "observed_url": observed_url, "matched": ok,
        }, schema="workstation.run_local_readback.v1").ref
        return {"ok": ok, "evidence_ref": ref}
    return readback


def _readback_browser_snapshot(dispatch, artifacts: ArtifactStore, task_id: str):
    """Independent readback for browser_snapshot - verify URL matches expected."""
    def readback(primitive: str, bound_args: dict, raw: Any) -> dict | None:
        if primitive != "browser_snapshot":
            return None
        # browser_snapshot itself is the verification - check if result has valid URL
        try:
            observed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(observed, dict):
                has_url = any(
                    isinstance(observed.get(key), str) and observed[key].startswith("https://")
                    for key in ("url", "current_url", "currentUrl", "page_url", "pageUrl")
                )
                ok = has_url
            else:
                ok = False
        except Exception:
            ok = False
        ref = artifacts.store(task_id, f"readback_{uuid.uuid4().hex[:10]}.json", {
            "primitive": primitive, "matched": ok,
        }, schema="workstation.run_local_readback.v1").ref
        return {"ok": ok, "evidence_ref": ref}
    return readback


def _readback_trello_api_get(dispatch, artifacts: ArtifactStore, task_id: str):
    """Independent readback for trello_api_get - verify response has expected fields."""
    def readback(primitive: str, bound_args: dict, raw: Any) -> dict | None:
        if primitive != "trello_api_get":
            return None
        # Verify Trello API response has expected structure
        try:
            observed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(observed, dict):
                # Check for Trello card/board fields
                has_id = "id" in observed or (isinstance(observed.get("cards"), list) and len(observed["cards"]) > 0)
                has_name = "name" in observed or (isinstance(observed.get("cards"), list) and "name" in observed["cards"][0])
                ok = has_id and has_name
            else:
                ok = False
        except Exception:
            ok = False
        ref = artifacts.store(task_id, f"readback_{uuid.uuid4().hex[:10]}.json", {
            "primitive": primitive, "matched": ok,
        }, schema="workstation.run_local_readback.v1").ref
        return {"ok": ok, "evidence_ref": ref}
    return readback


def _readback_browser_extract_items(dispatch, artifacts: ArtifactStore, task_id: str):
    """Independent readback for browser_extract_items via browser_snapshot(full=True) DOM verification."""
    def readback(primitive: str, bound_args: dict, raw: Any) -> dict | None:
        if primitive != "browser_extract_items":
            return None
        extracted = None
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, dict):
                extracted = parsed.get("items") or parsed.get("cards") or [parsed]
            elif isinstance(parsed, list):
                extracted = parsed
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return {"ok": False, "evidence_ref": None}

        if not extracted or not isinstance(extracted, list):
            return {"ok": False, "evidence_ref": None}

        try:
            snapshot_raw = dispatch("browser_snapshot", {"full": True})
            snapshot = json.loads(snapshot_raw) if isinstance(snapshot_raw, str) else snapshot_raw
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, OSError):
            return {"ok": False, "evidence_ref": None}

        if not isinstance(snapshot, dict) or snapshot.get("truncated") is True:
            return {"ok": False, "evidence_ref": None}

        dom_text = snapshot.get("dom") or snapshot.get("html") or snapshot.get("body") or snapshot.get("text") or ""
        if isinstance(snapshot.get("elements"), list):
            dom_text += " " + json.dumps(snapshot["elements"])
        if not dom_text and isinstance(snapshot, dict):
            dom_text = json.dumps(snapshot)

        ok = True
        for item in extracted:
            if not isinstance(item, dict):
                ok = False
                break
            title = str(item.get("title", "")).strip()
            lst = str(item.get("list", "")).strip()
            desc = str(item.get("description", "")).strip()
            if not title or not lst or not desc:
                ok = False
                break
            if title not in dom_text or lst not in dom_text or desc not in dom_text:
                ok = False
                break

        ref = artifacts.store(task_id, f"readback_{uuid.uuid4().hex[:10]}.json", {
            "primitive": primitive,
            "matched": ok,
            "items_count": len(extracted),
            "verified_fields": ["title", "list", "description"],
        }, schema="workstation.run_local_readback.v1").ref
        return {"ok": ok, "evidence_ref": ref}
    return readback


def _build_readback_fns(dispatch, artifacts: ArtifactStore, task_id: str) -> dict[str, callable]:
    """Build readback functions for all supported primitives."""
    return {
        "write_file": _readback_write_file(dispatch, artifacts, task_id),
        "browser_navigate": _readback_browser_navigate(dispatch, artifacts, task_id),
        "browser_snapshot": _readback_browser_snapshot(dispatch, artifacts, task_id),
        "trello_api_get": _readback_trello_api_get(dispatch, artifacts, task_id),
        "browser_extract_items": _readback_browser_extract_items(dispatch, artifacts, task_id),
    }


def build_run_adoption_owner(agent: Any, *, system2_counter=None) -> DurableRunAdoptionOwner | None:
    """Owner for this agent's canonical TaskRun, or ``None`` when the agent has no bound run."""
    task_id = getattr(agent, "_canonical_work_task_id", None)
    run_id = getattr(agent, "_canonical_work_run_id", None)
    if not task_id or run_id is None:
        return None
    cached = getattr(agent, "_run_adoption_owner", None)
    bound = (str(task_id), str(run_id))
    if cached is not None and getattr(cached, "_bound_task_run", None) == bound:
        return cached

    from workstation.integrations.hermes.scoped_execution import (
        workstation_durable_dispatch,
        workstation_scoped_execution,
    )

    session_id = str(getattr(agent, "_conversation_root_id", lambda: None)() or getattr(agent, "session_id", "") or "")
    inner = workstation_durable_dispatch(agent)
    artifacts = ArtifactStore()

    def ensure_bound_run() -> None:
        current = (getattr(agent, "_canonical_work_task_id", None),
                   getattr(agent, "_canonical_work_run_id", None))
        if tuple(str(v) for v in current) != bound:
            raise RuntimeError("taskrun_identity_changed")

    def dispatch(tool: str, args: dict) -> Any:
        ensure_bound_run()
        with workstation_scoped_execution(agent, str(task_id), None):
            return inner(tool, args, str(task_id), f"runlocal_{uuid.uuid4().hex[:10]}")

    readback_fns = _build_readback_fns(dispatch, artifacts, str(task_id))

    def verified_readback(primitive: str, args: dict, raw: Any) -> dict | None:
        ensure_bound_run()
        # Do not let merely having an entry in the dispatcher prove independent
        # verification. Only explicitly admitted primitives may use it.
        handler = readback_fns.get(primitive) if primitive in _READBACK else None
        return handler(primitive, args, raw) if handler is not None else None

    owner = DurableRunAdoptionOwner(
        DurableTaskStore, artifacts,
        authority_for_task=lambda task: trusted_effect_authority_from_agent(agent, session_id, task),
        dispatch_fn=dispatch,
        readback_fn=verified_readback,
        readback_primitives=_READBACK, supported_primitives=_SUPPORTED, system2_counter=system2_counter,
    )
    # The dispatcher closure is bound to one canonical task. Never reuse the
    # owner across a later TaskRun on the same agent instance.
    owner._bound_task_run = bound
    from workstation.experience_compiler.lifecycle import (
        get_validation_environment_provider,
        register_validation_environment_provider,
        create_local_canary_validation_provider,
    )
    if get_validation_environment_provider() is None:
        register_validation_environment_provider(create_local_canary_validation_provider(artifacts))
    try:
        agent._run_adoption_owner = owner
    except AttributeError:
        pass
    return owner


def workstation_run_local_checkpoint(context: Any) -> AdoptionReport | None:
    """Adopt the next verified-equivalent pending items of this run, or do nothing."""
    from workstation.experience_compiler.compilability_monitor import DIRECT, peek_compilability_monitor

    agent = getattr(context, "agent", None)
    monitor = peek_compilability_monitor()
    if agent is None or monitor is None or not monitor.enabled or monitor.mode != DIRECT:
        return None
    task_id = getattr(agent, "_canonical_work_task_id", None)
    run_id = getattr(agent, "_canonical_work_run_id", None)
    if not task_id or run_id is None or not monitor.ready_offers(str(task_id), str(run_id)):
        return None
    owner = build_run_adoption_owner(agent)
    if owner is None:
        return None
    owner.bind_system2_counter(lambda: int(getattr(context, "api_call_count", 0) or 0))
    try:
        report = RunLocalAdopter(owner, monitor).run_checkpoint(str(task_id), str(run_id))
    except Exception:
        logger.warning("run-local adoption checkpoint failed closed", exc_info=True)
        return None
    finally:
        owner.bind_system2_counter(None)
    if report.items:
        agent._run_local_adoption_reports = [*getattr(agent, "_run_local_adoption_reports", []), report]
    return report


def create_safe_item_boundary_callback(
    agent: Any, context: Any = None, drain_timeout: float = 0.5
) -> Callable[[WorkItem], None]:
    """Create a non-reentrant safe item boundary callback for the real TaskRun owner."""
    def on_safe_item_boundary(completed_item: WorkItem) -> None:
        if _in_adoption_checkpoint.get():
            return
        token = _in_adoption_checkpoint.set(True)
        try:
            # Drain briefly to allow the async learning worker to finish candidate mining/validation if pending
            from workstation.experience_compiler.compilability_monitor import peek_compilability_monitor
            monitor = peek_compilability_monitor()
            if monitor is not None and getattr(monitor, "enabled", False):
                try:
                    monitor.drain(timeout=drain_timeout)
                except Exception:  # health: allow BLE001 S110 -- bounded drain timeout failure falls through safely
                    pass
            ctx = context or SimpleNamespace(
                agent=agent,
                api_call_count=int(
                    getattr(agent, "_current_turn_api_calls", 0)
                    or getattr(agent, "api_call_count", 0)
                    or 0
                ),
            )
            workstation_run_local_checkpoint(ctx)
        except Exception:
            logger.warning("run-local adoption checkpoint at safe boundary failed closed", exc_info=True)
        finally:
            _in_adoption_checkpoint.reset(token)

    return on_safe_item_boundary


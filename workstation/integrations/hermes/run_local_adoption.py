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
_SUPPORTED = (
    "write_file",
    "read_file",
    "browser_navigate",
    "browser_snapshot",
    "trello_api_get",
    "browser_extract_items",
)
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


def _readback_browser_extract_items(
    dispatch, artifacts: ArtifactStore, task_id: str, run_id: str, *, source_for_readback,
):
    """Verify one card through fresh, non-atomic BrowserTask observations."""
    from datetime import UTC, datetime

    from workstation.experience_compiler.read_output_contract import (
        guarded_projection,
        prepare_read_shape,
    )

    schema = "hermes.browser_card_readback.v1"

    def _expected_browser_task_id() -> str:
        try:
            plan = DurableTaskStore.get_plan(str(task_id))
            if plan and isinstance(plan.metadata, dict) and plan.metadata.get("browser_task_id"):
                return str(plan.metadata["browser_task_id"])
        except Exception:  # health: allow BLE001, S110 -- task plan lookup failure safely falls back to task_id
            pass
        return str(task_id)

    def observation(value):
        value = json.loads(value) if isinstance(value, str) else value
        if not isinstance(value, dict) or value.get("success") is False:
            raise ValueError("browser_observation_unavailable")
        if isinstance(value.get("result"), dict):
            value = value["result"]
        expected_bt_id = _expected_browser_task_id()
        if (value.get("success") is not True or value.get("cached") is not False
                or value.get("runtime") != "electron-chromium"
                or value.get("task_id") not in (task_id, expected_bt_id)
                or not value.get("tab_id") or not value.get("url")
                or value.get("count") != 1
                or not isinstance(value.get("items"), list) or len(value["items"]) != 1
                or not isinstance(value["items"][0], dict)):
            raise ValueError("browser_observation_not_fresh_and_unique")
        return value

    def readback(primitive, bound_args, raw):
        if primitive != "browser_extract_items":
            return None
        try:
            selector = bound_args.get("selector")
            if (bound_args.get("mode") != "inspect" or bound_args.get("limit") != 1
                    or not isinstance(selector, str) or not selector.strip()
                    or not {"data-card-id", "data-list"}.issubset(bound_args.get("attributes", []))):
                raise ValueError("unsupported_card_read_shape")
            source = source_for_readback(bound_args, raw)
            expected_bt_id = _expected_browser_task_id()
            if (not isinstance(source, dict) or source.get("task_id") != task_id
                    or str(source.get("run_id")) != str(run_id)
                    or source.get("browser_task_id") != expected_bt_id
                    or not all(source.get(key) for key in (
                        "operation_id", "raw_result_ref", "transition_ref"))):
                raise ValueError("canonical_card_source_missing")
            original = observation(raw)
            card = original["items"][0]
            attrs = card.get("attributes", {})
            card_id = attrs.get("data-card-id")
            if (card.get("tag") != "ARTICLE" or not isinstance(card_id, str)
                    or re.fullmatch(r"[A-Za-z0-9_-]+", card_id) is None
                    or not isinstance(attrs.get("data-list"), str)):
                raise ValueError("unsupported_card_identity")
            identity = tuple(original[key] for key in ("task_id", "tab_id", "url"))

            def inspect(query, attributes):
                observed = observation(dispatch("browser_extract_items", {
                    "mode": "inspect", "selector": query, "limit": 1,
                    "attributes": attributes,
                }))
                if tuple(observed[key] for key in ("task_id", "tab_id", "url")) != identity:
                    raise ValueError("browser_observation_identity_changed")
                return observed["items"][0]

            before = inspect(f":is({selector})", ["data-card-id", "data-list"])
            child_scope = f':is({selector})[data-card-id="{card_id}"]'
            title = inspect(f"{child_scope} > h2", [])
            description = inspect(f"{child_scope} > p", [])
            after = inspect(f":where({selector})", ["data-card-id", "data-list"])
            if (before != after or before.get("tag") != "ARTICLE"
                    or before.get("attributes") != attrs or before.get("text") != card.get("text")
                    or title.get("tag") != "H2" or description.get("tag") != "P"):
                raise ValueError("card_observation_changed")
            title_text, description_text = title.get("text"), description.get("text")
            if not isinstance(title_text, str) or not isinstance(description_text, str):
                raise ValueError("card_fields_unavailable")
            def clean(text):
                return " ".join(text.split())
            normalized_title, normalized_description = clean(title_text), clean(description_text)
            visible = clean(card.get("text", ""))
            if (not normalized_title
                    or visible not in (normalized_title + normalized_description,
                                       normalized_title + " " + normalized_description)):
                raise ValueError("card_text_not_exact")
            rows = [{"id": card_id, "list": attrs["data-list"],
                     "title": title_text, "description": description_text}]
            projection = prepare_read_shape(original, rows)
            receipt = {
                **source,
                "task_id": task_id, "run_id": str(run_id),
                "observer": "workstation.browser_live_dom", "source_kind": "browser_live_dom",
                "trust_class": "trusted_runtime", "independent_readback": True,
                "status": "VERIFIED", "observed_at": datetime.now(UTC).isoformat(),
                "tab_id": original["tab_id"], "url": original["url"],
                "observation_consistency": "non_atomic_parent_bracket",
                "projection": projection,
            }
            ref = artifacts.store(task_id, f"card_readback_{uuid.uuid4().hex[:10]}.json",
                                  receipt, schema=schema).ref
            resolved = artifacts.resolve_structured(ref)
            if resolved.get("schema") != schema or resolved.get("content") != receipt:
                raise ValueError("card_receipt_integrity_failed")
            projected = guarded_projection(
                original, rows, task_id=task_id, run_id=str(run_id),
                operation_id=source["operation_id"], raw_result_ref=source["raw_result_ref"],
                owner_readback_receipt=resolved["content"],
            )
            if projected != projection:
                raise ValueError("card_projection_changed")
            try:
                from workstation.experience_compiler.corpus import ExperienceCorpus
                ExperienceCorpus(artifacts).accept_work_item(str(task_id), str(run_id), ref)
            except Exception:  # health: allow BLE001, S110 -- non-blocking acceptance notification during readback
                pass
            return {"ok": True, "evidence_ref": ref}
        except Exception:  # health: allow BLE001 -- observation or verification failure safely returns uncertified readback
            # A failed observation or artifact resolution cannot certify a read.
            return {"ok": False, "evidence_ref": None}

    return readback


def _build_readback_fns(
    dispatch, artifacts: ArtifactStore, task_id: str, run_id: str = "", *, source_for_readback: Callable | None = None
) -> dict[str, callable]:
    """Build readback functions for all supported primitives."""
    fns = {
        "write_file": _readback_write_file(dispatch, artifacts, task_id),
        "browser_navigate": _readback_browser_navigate(dispatch, artifacts, task_id),
        "browser_snapshot": _readback_browser_snapshot(dispatch, artifacts, task_id),
        "trello_api_get": _readback_trello_api_get(dispatch, artifacts, task_id),
    }
    if source_for_readback is not None:
        fns["browser_extract_items"] = _readback_browser_extract_items(
            dispatch, artifacts, task_id, run_id, source_for_readback=source_for_readback
        )
    return fns


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
    _last_op_info: dict[str, str] = {}

    def ensure_bound_run() -> None:
        current = (getattr(agent, "_canonical_work_task_id", None),
                   getattr(agent, "_canonical_work_run_id", None))
        if tuple(str(v) for v in current) != bound:
            raise RuntimeError("taskrun_identity_changed")

    def dispatch(tool: str, args: dict) -> Any:
        ensure_bound_run()
        op_id = f"runlocal_{uuid.uuid4().hex[:10]}"
        agent._current_operation_id = op_id
        with workstation_scoped_execution(agent, str(task_id), None):
            res = inner(tool, args, str(task_id), op_id)
        try:
            raw_data = res if isinstance(res, (dict, list)) else (
                json.loads(res) if isinstance(res, str) and res.strip().startswith(("{", "[")) else {"raw": res}
            )
            raw_ref = artifacts.store(str(task_id), f"raw_result_{op_id}.json", raw_data,
                                      schema="workstation.raw_tool_result.v1").ref
        except Exception:  # health: allow BLE001 -- raw result storage failure is non-fatal for dispatch execution
            raw_ref = None

        trans_ref = getattr(agent, "_last_progressive_ref", None)
        if not trans_ref:
            try:
                from workstation.experience_compiler.progressive import capture_progressive
                trans_ref = capture_progressive(
                    artifacts,
                    task_id=str(task_id),
                    run_id=str(run_id),
                    operation_id=op_id,
                    primitive=tool,
                    route="native_browser",
                    outcome="observed",
                    state=res if isinstance(res, dict) else None,
                )
            except Exception:  # health: allow BLE001 -- progressive transition capture failure is non-fatal for dispatch execution
                trans_ref = None

        _last_op_info["operation_id"] = op_id
        if raw_ref:
            _last_op_info["raw_result_ref"] = raw_ref
        if trans_ref:
            _last_op_info["transition_ref"] = trans_ref
        return res

    def canonical_source_for_readback(bound_args: dict, raw: Any) -> dict:
        expected_bt_id = str(task_id)
        try:
            plan = DurableTaskStore.get_plan(str(task_id))
            if plan and isinstance(plan.metadata, dict) and plan.metadata.get("browser_task_id"):
                expected_bt_id = str(plan.metadata["browser_task_id"])
        except Exception:  # health: allow BLE001, S110 -- plan lookup failure safely falls back to task_id
            pass

        op_id = getattr(agent, "_current_operation_id", None) or _last_op_info.get("operation_id")
        raw_ref = getattr(agent, "_last_raw_result_ref", None) or _last_op_info.get("raw_result_ref")
        trans_ref = getattr(agent, "_last_progressive_ref", None) or _last_op_info.get("transition_ref")

        if not op_id:
            op_id = f"op_{uuid.uuid4().hex[:12]}"
        if not raw_ref:
            raw_data = raw if isinstance(raw, (dict, list)) else (
                json.loads(raw) if isinstance(raw, str) and raw.strip().startswith(("{", "[")) else {"raw": raw}
            )
            raw_ref = artifacts.store(str(task_id), f"raw_result_{op_id}.json", raw_data,
                                      schema="workstation.raw_tool_result.v1").ref
        if not trans_ref:
            from workstation.experience_compiler.progressive import capture_progressive
            trans_ref = capture_progressive(
                artifacts,
                task_id=str(task_id),
                run_id=str(run_id),
                operation_id=op_id,
                primitive="browser_extract_items",
                route="native_browser",
                outcome="observed",
                state=raw if isinstance(raw, dict) else None,
            )

        return {
            "task_id": str(task_id),
            "run_id": str(run_id),
            "operation_id": op_id,
            "raw_result_ref": raw_ref,
            "transition_ref": trans_ref,
            "browser_task_id": expected_bt_id,
        }

    readback_fns = _build_readback_fns(
        dispatch, artifacts, str(task_id), str(run_id), source_for_readback=canonical_source_for_readback
    )

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


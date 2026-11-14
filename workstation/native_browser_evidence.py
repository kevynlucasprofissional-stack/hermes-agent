"""Bounded native Chromium operation evidence; not a Kanban completion verifier.

The owner admission is an ACK only. A fresh same-session snapshot is an
observation, not proof of persistence. External verification requires a trusted
read-only callback supplied by application code, never by model arguments.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import re
from pathlib import Path
from typing import Any, Callable, Literal
from uuid import uuid4
from urllib.parse import urlsplit

from workstation.artifacts import ArtifactStore
from workstation.execution_policy import EvidenceStrength


Status = Literal["observed", "verified", "uncertain"]
SUPPORTED_ACTIONS = frozenset({"browser_click", "browser_type"})
MAX_STATE_BYTES = 8_000_000


@dataclass(frozen=True, slots=True)
class NativeBrowserOperationReceipt:
    task_id: str
    session_id: str
    run_id: str
    operation_id: str
    call_id: str
    browser_task_id: str
    tab_id: str
    action: str
    target_ref: str
    predicate: str
    ack: bool
    fresh_observation: bool
    source_kind: str
    evidence_strength: int
    status: Status
    reason: str | None
    observed_at: str
    evidence_ref: str | None = None


def _unpack(raw: Any) -> dict[str, Any]:
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _origin(url: Any) -> tuple[str, str, int | None] | None:
    if not isinstance(url, str):
        return None
    try:
        parsed = urlsplit(url)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            return None
        return parsed.scheme, parsed.hostname.lower(), parsed.port
    except ValueError:
        return None


def _owner_ack(
    state: dict[str, Any], result: dict[str, Any], *,
    task_id: str, session_id: str, run_id: str, operation_id: str,
    action: str,
) -> tuple[bool, str, dict[str, Any]]:
    if (state.get("version") != 1 or
            not isinstance(state.get("operationAdmissions"), dict) or
            not isinstance(state.get("browserTasks"), dict)):
        return False, "owner_state_invalid", {}
    admission = state["operationAdmissions"].get(operation_id)
    receipt = result.get("receipt")
    if not isinstance(admission, dict) or not isinstance(receipt, dict):
        return False, "owner_admission_or_receipt_missing", {}
    if (admission.get("terminal") or admission.get("acknowledged") is not True or
            any(admission.get(key) != value for key, value in (
                ("operationId", operation_id), ("taskId", task_id),
                ("sessionId", session_id), ("runId", run_id),
                ("action", action)))):
        return False, "owner_admission_mismatch_or_unacknowledged", {}
    tab_id = admission.get("tabId")
    if (not isinstance(tab_id, str) or not tab_id or
            any(receipt.get(key) != value for key, value in (
                ("operationId", operation_id), ("taskId", task_id),
                ("runId", run_id), ("browserTaskId", task_id),
                ("tabId", tab_id), ("action", action)))):
        return False, "owner_receipt_identity_mismatch", {}
    tasks = state["browserTasks"].get("tasks")
    tabs = state.get("tabs")
    if not isinstance(tasks, list) or not isinstance(tabs, list):
        return False, "owner_task_or_tab_missing", {}
    owned_tasks = [t for t in tasks if isinstance(t, dict) and t.get("taskId") == task_id]
    owned_tabs = [t for t in tabs if isinstance(t, dict) and t.get("id") == tab_id]
    if len(owned_tasks) != 1 or len(owned_tabs) != 1:
        return False, "owner_task_or_tab_ambiguous", {}
    task, tab = owned_tasks[0], owned_tabs[0]
    if (task.get("sessionHost") != session_id or str(task.get("runId")) != run_id or
            tab.get("browserTaskId") != task_id or
            tab.get("recoveryState") != "live" or
            tab.get("recoveryReason") is not None):
        return False, "owner_session_or_tab_not_live", {}
    if (_origin(receipt.get("safeUrl")) is None or
            _origin(tab.get("safeUrl")) != _origin(receipt.get("safeUrl"))):
        return False, "owner_origin_mismatch", {}
    if (result.get("success") is not True or
            result.get("runtime") != "electron-chromium" or
            result.get("task_id") != task_id or
            result.get("tab_id") != tab_id or
            result.get("operation_id") != operation_id):
        return False, "controller_response_not_authoritative", {}
    rev = receipt.get("revision")
    if not isinstance(rev, int) or isinstance(rev, bool) or rev < 0:
        return False, "owner_revision_invalid", {}
    # A newer operation may have replaced lastReceipt, but the per-operation
    # admission still records this original ACK. Never read another lastReceipt.
    last = task.get("lastReceipt")
    if isinstance(last, dict) and last.get("operationId") == operation_id and last != receipt:
        return False, "owner_receipt_changed", {}
    try:
        executed = datetime.fromisoformat(str(receipt["executedAt"]).replace("Z", "+00:00"))
        saved = datetime.fromisoformat(str(state["savedAt"]).replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if (executed.tzinfo is None or saved.tzinfo is None or
                (saved - executed).total_seconds() < -2 or
                not -5 <= (now - executed).total_seconds() <= 120):
            return False, "owner_receipt_stale", {}
    except (KeyError, ValueError, TypeError):
        return False, "owner_receipt_time_invalid", {}
    return True, "", {"tab_id": tab_id, "origin": _origin(receipt["safeUrl"])}


def capture_native_browser_operation(
    tool_name: str, raw_result: Any, *,
    task_id: str, session_id: str, run_id: str, call_id: str,
    owner_path: Path | None = None,
    snapshot_reader: Callable[[], Any] | None = None,
    predicate: str = "page_readable_after_action",
    expected_value: Any = None,
    authoritative_reader: Callable[[], tuple[str, dict[str, Any]]] | None = None,
    authoritative_field: str | None = None,
    authoritative_resource_id: str | None = None,
    store: ArtifactStore | None = None,
) -> dict[str, Any] | None:
    """Store a minimal receipt. Only trusted injected readers may certify external state.

    No model-facing arguments can supply the verification callback or level.
    The optional authoritative reader must return (source_url, structured_data).
    Exact expected values and raw DOM/response bodies are never persisted.
    """
    if (tool_name not in SUPPORTED_ACTIONS or
            not all(isinstance(x, str) and x for x in
                    (task_id, session_id, run_id, call_id))):
        return None
    result = _unpack(raw_result)
    op_id = result.get("operation_id")
    if not isinstance(op_id, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", op_id) is None:
        # The action may have crossed the effect boundary: do not invent an ID.
        return None
    from tools.browser_workstation import _workstation_home
    path = owner_path or (_workstation_home() / "Runtime" / "browser-session.json")
    owner: dict[str, Any] = {}
    reason = "owner_state_unavailable"
    try:
        if path.stat().st_size > MAX_STATE_BYTES:
            raise ValueError("owner state too large")
        owner = _unpack(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        pass
    ack, reason, binding = _owner_ack(
        owner, result, task_id=task_id, session_id=session_id,
        run_id=str(run_id), operation_id=op_id, action=tool_name,
    )
    fresh = False
    if ack and snapshot_reader is not None:
        try:
            read = _unpack(snapshot_reader())
            fresh = (read.get("success") is True and
                     read.get("runtime") == "electron-chromium" and
                     read.get("task_id") == task_id and
                     read.get("tab_id") == binding["tab_id"] and
                     read.get("cached") is not True and
                     read.get("snapshot_cache") != "hit" and
                     _origin(read.get("url")) == binding["origin"])
            if not fresh:
                reason = "native_snapshot_stale_or_mismatched"
        except Exception:
            reason = "native_snapshot_unavailable"
    elif ack:
        reason = "fresh_snapshot_not_supplied"

    # A read can race a subsequent write. The singular lastReceipt is NOT
    # evidence for this operation, but can fence a read that came too late.
    if fresh:
        try:
            after = _unpack(path.read_text(encoding="utf-8"))
            tasks_after = after["browserTasks"]["tasks"]
            now_owned = [t for t in tasks_after if isinstance(t, dict) and
                         t.get("taskId") == task_id]
            if (len(now_owned) != 1 or
                    (now_owned[0].get("lastReceipt") or {}).get("operationId") != op_id):
                fresh = False
                reason = "native_snapshot_owner_advanced"
        except (OSError, ValueError, KeyError, TypeError):
            fresh = False
            reason = "native_snapshot_owner_unavailable"

    verified = False
    if (fresh and authoritative_reader is not None and
            authoritative_field is not None and authoritative_resource_id is not None):
        try:
            source_url, values = authoritative_reader()
            verified = (isinstance(values, dict) and
                        values.get("id") == authoritative_resource_id and
                        authoritative_field in values and
                        values[authoritative_field] == expected_value and
                        _origin(source_url) == binding["origin"])
            if not verified:
                reason = "authoritative_readback_mismatch"
            else:
                # An independent GET must still belong to the same in-flight
                # owner operation; another save during GET invalidates causality.
                final_state = _unpack(path.read_text(encoding="utf-8"))
                final_tasks = final_state["browserTasks"]["tasks"]
                owned = [t for t in final_tasks if isinstance(t, dict) and
                         t.get("taskId") == task_id]
                if (len(owned) != 1 or
                        (owned[0].get("lastReceipt") or {}).get("operationId") != op_id):
                    verified = False
                    fresh = False
                    reason = "authoritative_owner_advanced"
        except Exception:
            verified = False
            fresh = False
            reason = "authoritative_readback_unavailable"

    status: Status = "verified" if verified else "observed" if fresh else "uncertain"
    if verified:
        strength = EvidenceStrength.INDEPENDENT_PERSISTED_READBACK
        source_kind = "authorized_external_get"
        reason = ""
    elif fresh:
        strength = EvidenceStrength.SAME_SESSION_SEMANTIC_OBSERVATION
        source_kind = "browser_live_dom"
        reason = "external_persistence_not_verified"
    else:
        strength = EvidenceStrength.TOOL_ACK_ONLY
        source_kind = "browser_local_owner"
        reason = reason or "owner_ack_unavailable"

    raw_target = result.get("target")
    ref = raw_target.get("ref") if isinstance(raw_target, dict) else None
    target_ref = ref if isinstance(ref, str) and re.fullmatch(r"@e[0-9]{1,7}", ref) else ""
    if re.fullmatch(r"[A-Za-z0-9_.:-]{1,96}", str(predicate)) is None:
        predicate = "page_readable_after_action"

    evidence = NativeBrowserOperationReceipt(
        task_id=task_id, session_id=session_id, run_id=str(run_id),
        operation_id=op_id, call_id=call_id, browser_task_id=task_id,
        tab_id=binding.get("tab_id", "") if ack else "",
        action=tool_name, target_ref=target_ref, predicate=str(predicate),
        ack=ack, fresh_observation=fresh, source_kind=source_kind,
        evidence_strength=int(strength), status=status, reason=reason,
        observed_at=datetime.now(timezone.utc).isoformat(),
    )
    artifact = (store or ArtifactStore()).store(
        task_id, f"native_browser_operation_{uuid4().hex}.json",
        asdict(evidence), schema="hermes.native_browser_operation.v1",
    )
    return {**asdict(evidence), "evidence_ref": artifact.ref,
            "sha256": artifact.sha256}

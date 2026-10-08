"""Resumable Authority Supersession and TaskRun Continuation.

Replaces the unrecoverable stale_task_run dead end with typed
AUTHORITY_SUPERSEDED semantics while preserving strict write-fencing:

1. Stale runs remain strictly FENCED from future mutations.
2. Completed work and unconfirmed items are checkpointed atomically.
3. Distinguishes legitimate SUPERSEDED (resumable) from explicit
   REVOKED_BY_USER, CANCELLED, and POLICY_REVOKED (non-resumable).
4. Restores continuation in the current canonical run, resuming ONLY
   unconfirmed items without duplicating UNCERTAIN mutations.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from workstation.artifacts import ArtifactStore


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AuthorityTerminationKind(str, Enum):
    """Why a TaskRun lost mutation authority."""

    SUPERSEDED = "SUPERSEDED"
    REVOKED_BY_USER = "REVOKED_BY_USER"
    CANCELLED = "CANCELLED"
    POLICY_REVOKED = "POLICY_REVOKED"


@dataclass
class AuthoritySuperseded:
    """Typed audit record emitted when a run's mutation lease/authority is superseded."""

    task_id: str
    stale_run_id: str
    current_run_id: Optional[str]
    termination_kind: AuthorityTerminationKind = AuthorityTerminationKind.SUPERSEDED
    checkpoint_ref: Optional[str] = None
    pending_items_ref: Optional[str] = None
    uncertain_effects: List[Dict[str, Any]] = field(default_factory=list)
    continuation_allowed: bool = False
    created_at: str = field(default_factory=_utc_now)
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["termination_kind"] = self.termination_kind.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AuthoritySuperseded:
        cdata = dict(data)
        if "termination_kind" in cdata and isinstance(cdata["termination_kind"], str):
            cdata["termination_kind"] = AuthorityTerminationKind(cdata["termination_kind"])
        return cls(**cdata)


def classify_run_authority(
    live_task: Any,
    pinned_run_id: str,
    policy_revocation: bool = False,
    connection=None,
    plan_status=None,
) -> Optional[AuthoritySuperseded]:
    """Examine live Kanban task state vs pinned run ID to determine authority status.

    Returns None if authority is healthy, or an AuthoritySuperseded record if fenced.
    """
    if not live_task:
        return AuthoritySuperseded(
            task_id="",
            stale_run_id=str(pinned_run_id),
            current_run_id=None,
            termination_kind=AuthorityTerminationKind.CANCELLED,
            continuation_allowed=False,
            details={"reason": "task_not_found"},
        )

    task_id = str(getattr(live_task, "id", ""))
    status = str(getattr(live_task, "status", "")).lower()
    current_run = str(getattr(live_task, "current_run_id", "")) if getattr(live_task, "current_run_id", None) is not None else None

    if connection is not None and pinned_run_id is not None:
        from hermes_cli import kanban_db
        run = kanban_db.get_run(connection, int(pinned_run_id))
        if run is None or run.task_id != task_id:
            policy_revocation = True
        else:
            causes = {str(run.outcome or "").upper(), str(run.status or "").upper(),
                      str((run.metadata or {}).get("termination_kind", "")).upper()}
            for cause, mapped in (("POLICY_REVOKED", "policy_revoked"), ("REVOKED_BY_USER", "revoked"),
                                  ("CANCELLED", "cancelled")):
                if cause in causes:
                    status = mapped
                    break

    if plan_status == "cancelled":
        status = "cancelled"

    if policy_revocation or status == "policy_revoked":
        return AuthoritySuperseded(
            task_id=task_id,
            stale_run_id=str(pinned_run_id),
            current_run_id=current_run,
            termination_kind=AuthorityTerminationKind.POLICY_REVOKED,
            continuation_allowed=False,
            details={"reason": "security_policy_revoked"},
        )

    if status == "cancelled":
        return AuthoritySuperseded(
            task_id=task_id,
            stale_run_id=str(pinned_run_id),
            current_run_id=current_run,
            termination_kind=AuthorityTerminationKind.CANCELLED,
            continuation_allowed=False,
            details={"reason": "task_cancelled_by_user"},
        )

    if status in ("revoked", "rejected"):
        return AuthoritySuperseded(
            task_id=task_id,
            stale_run_id=str(pinned_run_id),
            current_run_id=current_run,
            termination_kind=AuthorityTerminationKind.REVOKED_BY_USER,
            continuation_allowed=False,
            details={"reason": "authority_revoked_by_user"},
        )

    if pinned_run_id is not None and current_run != str(pinned_run_id):
        return AuthoritySuperseded(
            task_id=task_id,
            stale_run_id=str(pinned_run_id),
            current_run_id=current_run,
            termination_kind=AuthorityTerminationKind.SUPERSEDED,
            continuation_allowed=bool(current_run),
            details={"reason": "canonical_run_replaced"},
        )

    return None


def checkpoint_superseded_execution(
    task_id: str,
    stale_run_id: str,
    current_run_id: Optional[str],
    completed_results: List[Dict[str, Any]],
    pending_items: List[Dict[str, Any]],
    uncertain_effects: Optional[List[Dict[str, Any]]] = None,
    artifact_store: Optional[ArtifactStore] = None,
    termination_kind: AuthorityTerminationKind = AuthorityTerminationKind.SUPERSEDED,
) -> AuthoritySuperseded:
    """Persist completed checkpoints and uncompleted worklist during supersession."""
    store = artifact_store or ArtifactStore()
    uncertain_list = uncertain_effects or []

    # Checkpoint completed results
    chk_ref = store.store(
        task_id=task_id,
        name=f"checkpoint_superseded_{stale_run_id}.json",
        content={"task_id": task_id, "stale_run_id": stale_run_id, "results": completed_results},
        media_type="application/json",
        schema="workstation.superseded_checkpoint.v1",
    )

    # Store remaining pending work
    pend_ref = store.store(
        task_id=task_id,
        name=f"pending_work_{stale_run_id}_to_{current_run_id or 'none'}.json",
        content={
            "task_id": task_id,
            "stale_run_id": stale_run_id,
            "current_run_id": current_run_id,
            "pending_items": pending_items,
            "uncertain_effects": uncertain_list,
        },
        media_type="application/json",
        schema="workstation.pending_work.v1",
    )

    continuation_ok = termination_kind == AuthorityTerminationKind.SUPERSEDED and bool(current_run_id)

    record = AuthoritySuperseded(
        task_id=task_id,
        stale_run_id=stale_run_id,
        current_run_id=current_run_id,
        termination_kind=termination_kind,
        checkpoint_ref=chk_ref.ref,
        pending_items_ref=pend_ref.ref,
        uncertain_effects=uncertain_list,
        continuation_allowed=continuation_ok,
    )
    if continuation_ok:
        from workstation.telemetry import TelemetryEventType, emit_event
        emit_event(TelemetryEventType.AUTHORITY_SUPERSEDED, source_owner="workstation.taskrun_authority",
            task_id=task_id, run_id=str(stale_run_id), status="SUPERSEDED",
            dedupe_key=f"supersession:{task_id}:{stale_run_id}:{current_run_id}",
            evidence_refs=(chk_ref.ref, pend_ref.ref), payload={"current_run_id": current_run_id,
                "pending_count": len(pending_items), "uncertain_count": len(uncertain_list)})

    # Also persist the AuthoritySuperseded event
    store.store(
        task_id=task_id,
        name=f"authority_superseded_{stale_run_id}.json",
        content=record.to_dict(),
        media_type="application/json",
        schema="workstation.authority_superseded.v1",
    )
    from workstation.experience_compiler.progressive import capture_progressive
    for effect in uncertain_list:
        capture_progressive(store, task_id=task_id, run_id=stale_run_id,
            operation_id=effect.get("operation_id"), primitive=effect.get("tool", ""),
            route=effect.get("route", ""), outcome="authority_superseded")

    return record


def resume_superseded_work(
    superseded_record: AuthoritySuperseded,
    new_run_id: str,
    artifact_store: Optional[ArtifactStore] = None,
) -> Dict[str, Any]:
    """Restore continuation into new_run_id, enforcing readback on uncertain mutations.

    Returns dict with restored unconfirmed items, requiring reconciliation on any
    uncertain mutations before dispatching them.
    """
    if not superseded_record.continuation_allowed:
        raise PermissionError(
            f"Cannot resume task {superseded_record.task_id}: termination kind is "
            f"{superseded_record.termination_kind.value} (continuation not allowed)"
        )
    if superseded_record.termination_kind != AuthorityTerminationKind.SUPERSEDED or new_run_id != superseded_record.current_run_id:
        raise PermissionError("Cannot resume outside the canonical superseding run")

    store = artifact_store or ArtifactStore()
    if not superseded_record.pending_items_ref:
        return {"task_id": superseded_record.task_id, "new_run_id": new_run_id, "items": []}

    pending_data = store.read_json(superseded_record.pending_items_ref) or {}
    pending_items = pending_data.get("pending_items", [])
    uncertain_effects = pending_data.get("uncertain_effects", [])

    # Index uncertain mutations so they are never blindly duplicated
    uncertain_by_op = {u.get("operation_id"): u for u in uncertain_effects if u.get("operation_id")}

    resumed_items = []
    for item in pending_items:
        item_copy = dict(item)
        op_id = item_copy.get("operation_id")
        if op_id and op_id in uncertain_by_op:
            item_copy["requires_reconciliation"] = True
            item_copy["reconciliation_reason"] = "Prior attempt resulted in UNCERTAIN effect; verify state before re-dispatch"
        item_copy["claimed_run_id"] = new_run_id
        resumed_items.append(item_copy)

    return {
        "task_id": superseded_record.task_id,
        "stale_run_id": superseded_record.stale_run_id,
        "new_run_id": new_run_id,
        "checkpoint_ref": superseded_record.checkpoint_ref,
        "resumed_items": resumed_items,
        "uncertain_effects_count": len(uncertain_effects),
    }

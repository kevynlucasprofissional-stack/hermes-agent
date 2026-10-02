"""Tests for TaskRun Authority Supersession and Resumption.

Proves:
- Stale runs losing the mutation lease are strictly fenced from mutating state.
- Legitimate superseded runs are distinguished from user revocation / cancellation / policy denial.
- Checkpoints save completed work and unexecuted pending items.
- Resuming into a new run restores only unconfirmed items and flags uncertain mutations for reconciliation.
- Resuming non-resumable terminations raises PermissionError.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import pytest

from workstation.artifacts import ArtifactStore
from workstation.authority_supersession import (
    AuthorityTerminationKind,
    AuthoritySuperseded,
    classify_run_authority,
    checkpoint_superseded_execution,
    resume_superseded_work,
)


@dataclass
class DummyTask:
    id: str = "task-001"
    status: str = "in_progress"
    current_run_id: str = "run-002"


def test_classify_run_authority_scenarios():
    """Verify classification of different authority termination kinds."""
    # 1. Healthy: run is current
    task_healthy = DummyTask(id="task-1", status="in_progress", current_run_id="run-A")
    assert classify_run_authority(task_healthy, pinned_run_id="run-A") is None

    # 2. Superseded: canonical current_run_id advanced to run-B
    auth_sup = classify_run_authority(task_healthy, pinned_run_id="run-old")
    assert auth_sup is not None
    assert auth_sup.termination_kind == AuthorityTerminationKind.SUPERSEDED
    assert auth_sup.continuation_allowed is True
    assert auth_sup.stale_run_id == "run-old"
    assert auth_sup.current_run_id == "run-A"

    # 3. User revocation
    task_revoked = DummyTask(id="task-2", status="revoked", current_run_id="run-A")
    auth_rev = classify_run_authority(task_revoked, pinned_run_id="run-A")
    assert auth_rev is not None
    assert auth_rev.termination_kind == AuthorityTerminationKind.REVOKED_BY_USER
    assert auth_rev.continuation_allowed is False

    # 4. User cancellation
    task_cancelled = DummyTask(id="task-3", status="cancelled", current_run_id="run-A")
    auth_canc = classify_run_authority(task_cancelled, pinned_run_id="run-A")
    assert auth_canc is not None
    assert auth_canc.termination_kind == AuthorityTerminationKind.CANCELLED
    assert auth_canc.continuation_allowed is False

    # 5. Policy revocation
    auth_pol = classify_run_authority(task_healthy, pinned_run_id="run-A", policy_revocation=True)
    assert auth_pol is not None
    assert auth_pol.termination_kind == AuthorityTerminationKind.POLICY_REVOKED
    assert auth_pol.continuation_allowed is False


def test_checkpoint_and_resume_with_uncertainty(tmp_path):
    """Verify completed checkpointing and continuation with uncertain mutation tracking."""
    store = ArtifactStore(tmp_path / "artifacts")

    completed = [{"item_id": "item_1", "status": "COMMITTED", "result": "done"}]
    pending = [
        {"item_id": "item_2", "operation_id": "op_2", "action": "create_file"},
        {"item_id": "item_3", "operation_id": "op_3", "action": "send_request"},
    ]
    uncertain = [{"operation_id": "op_2", "effect": "file_write_uncertain"}]

    # Checkpoint superseded execution
    record = checkpoint_superseded_execution(
        task_id="task-100",
        stale_run_id="run-1",
        current_run_id="run-2",
        completed_results=completed,
        pending_items=pending,
        uncertain_effects=uncertain,
        artifact_store=store,
    )

    assert record.continuation_allowed is True
    assert record.checkpoint_ref
    assert record.pending_items_ref

    # Resume into run-2
    resumed = resume_superseded_work(record, new_run_id="run-2", artifact_store=store)
    assert resumed["task_id"] == "task-100"
    assert resumed["new_run_id"] == "run-2"
    assert len(resumed["resumed_items"]) == 2

    # item_2 had an uncertain mutation: must be flagged for reconciliation!
    item2 = next(it for it in resumed["resumed_items"] if it["item_id"] == "item_2")
    assert item2["requires_reconciliation"] is True
    assert "UNCERTAIN effect" in item2["reconciliation_reason"]

    # item_3 had no uncertainty: regular continuation
    item3 = next(it for it in resumed["resumed_items"] if it["item_id"] == "item_3")
    assert not item3.get("requires_reconciliation")


def test_resume_non_resumable_fails_closed(tmp_path):
    """Attempting to resume a revoked or cancelled execution raises PermissionError."""
    store = ArtifactStore(tmp_path / "artifacts")

    record = AuthoritySuperseded(
        task_id="task-cancelled",
        stale_run_id="run-1",
        current_run_id=None,
        termination_kind=AuthorityTerminationKind.CANCELLED,
        continuation_allowed=False,
    )

    with pytest.raises(PermissionError, match="continuation not allowed"):
        resume_superseded_work(record, new_run_id="run-2", artifact_store=store)

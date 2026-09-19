"""Behavior tests for CP4 (Certified Dispatch) and CP5 (AwaitCondition & Trigger Plane)."""
from __future__ import annotations

import json
import pytest

from workstation.artifacts import ArtifactStore
from workstation.contracts import AcceptanceContract, utc_now
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.intent import OperationIntent, OperationMode, operation_intent_hash
from workstation.control_plane.ir import CALL, CREATE, EQ, EXISTS, SET, TRUE, Predicate
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.operational_capabilities import (
    CapabilityLifecycle, OperationalCapability, OperationalCapabilityRegistry
)


@pytest.fixture
def clean_artifacts(tmp_path):
    return ArtifactStore(tmp_path / "artifacts")


def test_await_condition_persistence_and_rehydration(clean_artifacts):
    """Prove AwaitCondition survives process restart by persisting/loading from ArtifactStore."""
    from workstation.control_plane.waiting import (
        AwaitCondition, AwaitConditionStore, AwaitKind, TimeoutAction
    )

    store = AwaitConditionStore(clean_artifacts)

    wait_cond = AwaitCondition(
        wait_id="wait-123",
        kind=AwaitKind.WAITING_FOR_EVENT,
        predicate=EQ("build.status", "success"),
        observer_type="ci_webhook",
        correlation_id="corr-999",
        task_id="task-456",
        run_id="run-001",
        operation_id="op-1",
        deadline="2026-09-18T23:59:59Z",
        timeout_action=TimeoutAction.WAKE_LLM,
    )

    store.save(wait_cond)

    # Simulate restart by creating a new store instance with the same underlying storage
    restored_store = AwaitConditionStore(clean_artifacts)
    loaded = restored_store.get("wait-123")

    assert loaded is not None
    assert loaded.wait_id == "wait-123"
    assert loaded.kind == AwaitKind.WAITING_FOR_EVENT
    assert loaded.correlation_id == "corr-999"
    assert loaded.task_id == "task-456"
    assert loaded.run_id == "run-001"
    assert loaded.timeout_action == TimeoutAction.WAKE_LLM
    assert loaded.predicate.evaluate({"build": {"status": "success"}}) is True
    assert loaded.predicate.evaluate({"build": {"status": "failed"}}) is False


def test_trigger_plane_task_run_fencing(clean_artifacts):
    """Event with mismatched run_id or expired fence is rejected and does NOT resume."""
    from workstation.control_plane.waiting import (
        AwaitCondition, AwaitConditionStore, CausalEventEnvelope, TriggerCoordinator
    )

    store = AwaitConditionStore(clean_artifacts)
    wait_cond = AwaitCondition(
        wait_id="wait-fence-1",
        predicate=EQ("download.done", True),
        correlation_id="corr-dl-1",
        task_id="task-1",
        run_id="run-current",
    )
    store.save(wait_cond)

    coordinator = TriggerCoordinator(store)

    # Event with old/stale run_id
    stale_event = CausalEventEnvelope(
        event_id="evt-stale",
        event_type="download_completed",
        correlation_id="corr-dl-1",
        task_id="task-1",
        run_id="run-OLD",
    )

    resumed = coordinator.handle_event(
        stale_event,
        read_authoritative_state=lambda: {"download": {"done": True}},
    )
    assert resumed is False

    # Event with matching run_id
    valid_event = CausalEventEnvelope(
        event_id="evt-valid",
        event_type="download_completed",
        correlation_id="corr-dl-1",
        task_id="task-1",
        run_id="run-current",
    )
    resumed = coordinator.handle_event(
        valid_event,
        read_authoritative_state=lambda: {"download": {"done": True}},
    )
    assert resumed is True


def test_event_wakes_authoritative_state_confirms(clean_artifacts):
    """Rule 21.2: EVENT WAKES. AUTHORITATIVE STATE CONFIRMS.
    If event arrives but authoritative state does not satisfy predicate -> do NOT resume.
    """
    from workstation.control_plane.waiting import (
        AwaitCondition, AwaitConditionStore, CausalEventEnvelope, TriggerCoordinator
    )

    store = AwaitConditionStore(clean_artifacts)
    wait_cond = AwaitCondition(
        wait_id="wait-state-confirms",
        predicate=EQ("job.status", "completed"),
        correlation_id="corr-job-1",
        task_id="task-job",
        run_id="run-job",
    )
    store.save(wait_cond)

    coordinator = TriggerCoordinator(store)

    event = CausalEventEnvelope(
        event_id="evt-job-finished",
        event_type="job_event",
        correlation_id="corr-job-1",
        task_id="task-job",
        run_id="run-job",
    )

    # Authoritative external state says job is still "running" (or was false wake)
    resumed = coordinator.handle_event(
        event,
        read_authoritative_state=lambda: {"job": {"status": "running"}},
    )
    assert resumed is False

    # Authoritative state now confirms "completed"
    resumed = coordinator.handle_event(
        event,
        read_authoritative_state=lambda: {"job": {"status": "completed"}},
    )
    assert resumed is True


def test_duplicate_event_deduplication(clean_artifacts):
    """Duplicate event with same dedupe_key is suppressed and does NOT trigger duplicate resumption."""
    from workstation.control_plane.waiting import (
        AwaitCondition, AwaitConditionStore, CausalEventEnvelope, TriggerCoordinator
    )

    store = AwaitConditionStore(clean_artifacts)
    wait_cond = AwaitCondition(
        wait_id="wait-dedupe",
        predicate=EQ("status", "done"),
        correlation_id="corr-dedupe",
        task_id="task-1",
        run_id="run-1",
    )
    store.save(wait_cond)

    coordinator = TriggerCoordinator(store)

    evt1 = CausalEventEnvelope(
        event_id="evt-1",
        event_type="done_event",
        correlation_id="corr-dedupe",
        dedupe_key="msg-checksum-12345",
        task_id="task-1",
        run_id="run-1",
    )
    evt2 = CausalEventEnvelope(
        event_id="evt-2",
        event_type="done_event",
        correlation_id="corr-dedupe",
        dedupe_key="msg-checksum-12345",
        task_id="task-1",
        run_id="run-1",
    )

    # First event resumes
    assert coordinator.handle_event(evt1, read_authoritative_state=lambda: {"status": "done"}) is True

    # Duplicate event is dropped
    assert coordinator.handle_event(evt2, read_authoritative_state=lambda: {"status": "done"}) is False


def test_trigger_cycle_circuit_breaker(clean_artifacts):
    """Trigger cycle / no-progress circuit breaker detects loop and trips."""
    from workstation.control_plane.waiting import (
        TriggerCircuitBreaker
    )

    breaker = TriggerCircuitBreaker(max_unproductive_cycles=3)

    key = ("trigger_ci", "cap_rebuild", "repo/branch", "state_hash_abc")

    # 3 cycles without progress
    assert breaker.record_reaction(*key, progress_made=False) is True
    assert breaker.record_reaction(*key, progress_made=False) is True
    assert breaker.record_reaction(*key, progress_made=False) is True

    # 4th cycle trips breaker!
    tripped = breaker.record_reaction(*key, progress_made=False)
    assert tripped is False  # Tripped / blocked!
    assert breaker.is_tripped(*key) is True


def test_uncorrelated_system_event_observation_only():
    """Uncorrelated system event remains observation-only and never automatically creates a task."""
    from workstation.events import SystemEvent, SystemEventPipeline, SystemEventSeverity, SystemEventType

    pipeline = SystemEventPipeline()
    evt = pipeline.ingest_event(
        event_type=SystemEventType.DOWNLOAD_COMPLETED,
        severity=SystemEventSeverity.INFO,
        source="browser",
        title="Download Completed",
        message="file downloaded to tmp",
    )

    assert evt.processed is True
    assert evt.target_task_id is None
    assert evt.resulting_task_id is None  # Never automatically creates a task!


def test_certified_dispatcher_enforces_no_certificate_no_dispatch():
    """Dispatcher refuses execution if certificate is missing or invalid."""
    from workstation.control_plane.dispatcher import CertifiedDispatcher, DispatchError
    from workstation.control_plane.router import ExecutableDecision, RoutingCertificate

    dispatcher = CertifiedDispatcher()

    # Case 1: Attempt dispatch without valid certificate
    invalid_cert = RoutingCertificate(
        target_match=True,
        inputs_bound=False,  # Failed obligation!
        preconditions_hold=True,
        goal_coverage=True,
        effect_containment=True,
        invariant_preservation=True,
        authority_satisfied=True,
        policy_satisfied=True,
        approval_satisfied=True,
        verifier_available=True,
        evidence_strength_sufficient=True,
        state_fresh=True,
        capability_healthy=True,
        no_outstanding_uncertainty=True,
        deterministic_closure=True,
    )
    assert invalid_cert.is_valid() is False

    cap = OperationalCapability(id="test_cap", name="Test", version="1.0.0")
    decision = ExecutableDecision(capability=cap, certificate=invalid_cert)

    with pytest.raises(DispatchError, match="NO VALID CERTIFICATE"):
        dispatcher.dispatch(decision, current_state={"k": "v"})


def test_uncertain_dispatch_reconciliation_before_retry():
    """If dispatch ACK is lost, status is UNCERTAIN and cannot blind-retry."""
    from workstation.control_plane.dispatcher import CertifiedDispatcher, DispatchRecord, DispatchStatus

    dispatcher = CertifiedDispatcher()
    record = DispatchRecord(
        operation_id="op-idempotent-777",
        capability_id="cap_remote_api",
        status=DispatchStatus.UNCERTAIN,
        target="api/order/123",
    )

    # Blind retry is blocked when state is uncertain
    can_retry, reason = dispatcher.can_retry_operation(
        record,
        external_reconciled=False,
    )
    assert can_retry is False
    assert "reconcil" in reason.lower()

    # Once external state is reconciled (e.g. order already exists), verify and commit
    can_retry_after, _ = dispatcher.can_retry_operation(
        record,
        external_reconciled=True,
    )
    assert can_retry_after is True


def test_await_continuation_persistence_and_operation_fencing(clean_artifacts):
    """Continuation holds durable subgraph metadata and respects operation fencing."""
    from workstation.control_plane.waiting import (
        AwaitCondition, AwaitConditionStore, AwaitContinuation, CausalEventEnvelope,
        TriggerCoordinator, is_non_resident_wait, AwaitKind,
    )

    store = AwaitConditionStore(clean_artifacts)
    continuation = AwaitContinuation(
        task_id="task-cont-1",
        run_id="run-cont-1",
        operation_id="op-cont-1",
        plan_id="plan-cont-1",
        work_item_id="item-cont-1",
        capability_pins={"cap.a": {"version": "1.0.0"}},
        last_verified_state={"step_1": "completed"},
        remaining_subgraph=[{"step": 2, "capability_id": "cap.b"}],
    )
    cond = AwaitCondition(
        wait_id="wait-cont-99",
        kind=AwaitKind.WAITING_FOR_EVENT,
        predicate=EQ("pipeline.status", "green"),
        correlation_id="corr-pipeline",
        task_id="task-cont-1",
        run_id="run-cont-1",
        operation_id="op-cont-1",
        continuation=continuation,
    )
    assert is_non_resident_wait(cond) is True
    store.save(cond)

    # Rehydrate
    reloaded_store = AwaitConditionStore(clean_artifacts)
    loaded = reloaded_store.get("wait-cont-99")
    assert loaded is not None
    assert isinstance(loaded.continuation, AwaitContinuation)
    assert loaded.continuation.plan_id == "plan-cont-1"
    assert loaded.continuation.remaining_subgraph == [{"step": 2, "capability_id": "cap.b"}]

    coordinator = TriggerCoordinator(reloaded_store)

    # 1. Event with mismatched operation_id fails fence
    bad_op_event = CausalEventEnvelope(
        event_id="evt-bad-op",
        event_type="pipeline_green",
        correlation_id="corr-pipeline",
        task_id="task-cont-1",
        run_id="run-cont-1",
        operation_id="mismatched-op",
    )
    assert coordinator.handle_event(bad_op_event, lambda: {"pipeline": {"status": "green"}}) is False
    assert reloaded_store.get("wait-cont-99") is not None

    # 2. Event with matching operation_id succeeds and condition is deleted
    good_event = CausalEventEnvelope(
        event_id="evt-good-op",
        event_type="pipeline_green",
        correlation_id="corr-pipeline",
        task_id="task-cont-1",
        run_id="run-cont-1",
        operation_id="op-cont-1",
    )
    resumed_conditions = []
    def on_resume(c, s):
        resumed_conditions.append(c)
        return True

    resumed = coordinator.handle_event(good_event, lambda: {"pipeline": {"status": "green"}}, resume_fn=on_resume)
    assert resumed is True
    assert len(resumed_conditions) == 1
    assert reloaded_store.get("wait-cont-99") is None


def test_failed_resume_keeps_condition_persisted_for_subsequent_retry(clean_artifacts):
    """If resumption callback fails/throws, condition remains persisted and is not dropped."""
    from workstation.control_plane.waiting import (
        AwaitCondition, AwaitConditionStore, CausalEventEnvelope, TriggerCoordinator,
    )

    store = AwaitConditionStore(clean_artifacts)
    cond = AwaitCondition(
        wait_id="wait-retry-1",
        predicate=EQ("ready", True),
        correlation_id="corr-retry",
        task_id="task-1",
        run_id="run-1",
    )
    store.save(cond)

    coordinator = TriggerCoordinator(store)
    event = CausalEventEnvelope(
        event_id="evt-retry-1",
        event_type="ready",
        correlation_id="corr-retry",
        task_id="task-1",
        run_id="run-1",
    )

    # First attempt: resume_fn returns False (e.g. database lock or worker busy)
    resumed = coordinator.handle_event(
        event,
        lambda: {"ready": True},
        resume_fn=lambda c, s: False,
    )
    assert resumed is False
    assert store.get("wait-retry-1") is not None

    # Second attempt: resume_fn returns True
    resumed_retry = coordinator.handle_event(
        event,
        lambda: {"ready": True},
        resume_fn=lambda c, s: True,
    )
    assert resumed_retry is True
    assert store.get("wait-retry-1") is None

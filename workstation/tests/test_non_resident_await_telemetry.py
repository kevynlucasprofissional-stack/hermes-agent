"""Tests for Phase P5: Non-Resident Await & Production Telemetry."""
from pathlib import Path
import tempfile
import pytest

from workstation.artifacts import ArtifactStore
from workstation.control_plane.intent import OperationIntent, OperationMode
from workstation.control_plane.ir import EQ, Predicate
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.metrics import ORAMetrics, ORAMetricsCollector, WakeReason
from workstation.control_plane.router import (
    CapabilityRouter,
    ReasoningDecision,
    WaitDecision,
)
from workstation.control_plane.waiting import (
    AwaitCondition,
    AwaitConditionStore,
    AwaitContinuation,
    AwaitKind,
    CausalEventEnvelope,
    TriggerCoordinator,
)
from workstation.durable_tasks import DurableTaskStore
from workstation.experience_compiler.hierarchical import HierarchicalExperienceCompiler
from workstation.operational_capabilities import (
    CapabilityLifecycle,
    OperationalCapability,
    OperationalCapabilityRegistry,
)
from workstation.operational_kernel import OperationalKernel
from workstation.task_compiler import TaskCompiler


import sqlite3

@pytest.fixture
def temp_env():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        artifacts = ArtifactStore(root_dir=p / "artifacts")
        conn = sqlite3.connect(str(p / "tasks.db"), check_same_thread=False)
        store = DurableTaskStore(conn=conn)
        registry = OperationalCapabilityRegistry(artifacts=artifacts, root=p / "capabilities")
        yield {"path": p, "artifacts": artifacts, "store": store, "registry": registry, "db_path": str(p / "tasks.db")}
        conn.close()


def test_wait_persists_releases_executor_and_resumes_after_restart(temp_env):
    artifacts = temp_env["artifacts"]
    store = temp_env["store"]
    registry = temp_env["registry"]

    ora_metrics = ORAMetrics()
    compiler = TaskCompiler(store=store, artifacts=artifacts, ora_metrics=ora_metrics)

    # Construct an AwaitCondition for a build webhook
    wait_cond = AwaitCondition(
        wait_id="wait_ci_001",
        kind=AwaitKind.WAITING_FOR_EVENT,
        predicate=EQ("build.status", "success"),
        correlation_id="corr_ci_123",
        task_id="task_build_01",
        run_id="run_build_01",
    )

    # Mock or provide router returning WaitDecision
    class MockRouterWait:
        def route(self, intent, current_state, authority, *, runtime_state=None):
            return WaitDecision(
                await_condition=wait_cond,
                reason="waiting_for_ci_build",
            )

    request = {
        "action": "route",
        "operation_intent": {
            "id": "op_wait_01",
            "mode": "DISCOVERY",
            "goal": EQ("build.status", "success").to_dict(),
        },
        "task_id": "task_build_01",
        "run_id": "run_build_01",
    }

    # Inject mock router
    compiler.capability_registry = registry
    compiler.router = MockRouterWait()

    res = compiler.execute(
        request,
        task_id="task_build_01",
        session_id="session_build_01",
        dispatch=lambda *a, **kw: {},
    )

    # 1. Assert worker released and condition persisted
    assert res["routing_decision"] == "WAIT"
    assert res["worker_released"] is True
    assert res["wait_id"] == "wait_ci_001"
    assert res["correlation_id"] == "corr_ci_123"

    # Check condition in store with populated continuation
    await_store = AwaitConditionStore(artifacts=artifacts)
    saved_cond = await_store.get("wait_ci_001")
    assert saved_cond is not None
    assert saved_cond.correlation_id == "corr_ci_123"
    assert saved_cond.task_id == "task_build_01"
    assert saved_cond.run_id == "run_build_01"
    assert isinstance(saved_cond.continuation, AwaitContinuation)
    assert saved_cond.continuation.task_id == "task_build_01"
    assert saved_cond.continuation.run_id == "run_build_01"

    # 2. Simulate process restart by instantiating a completely new TaskCompiler
    new_compiler = TaskCompiler(store=store, artifacts=artifacts)

    # 3. Resume upon event + authoritative state confirmation
    event = CausalEventEnvelope(
        event_id="evt_build_done",
        event_type="ci_webhook_event",
        correlation_id="corr_ci_123",
        task_id="task_build_01",
        run_id="run_build_01",
    )

    resumed = new_compiler.handle_event(
        event=event,
        read_authoritative_state=lambda: {"build": {"status": "success"}},
    )
    assert resumed is True

    # Condition must be deleted from store upon confirmed resumption
    assert await_store.get("wait_ci_001") is None


def test_stale_or_duplicate_event_does_not_resume(temp_env):
    artifacts = temp_env["artifacts"]
    store = temp_env["store"]

    compiler = TaskCompiler(store=store, artifacts=artifacts)
    await_store = AwaitConditionStore(artifacts=artifacts)

    wait_cond = AwaitCondition(
        wait_id="wait_stale_test",
        kind=AwaitKind.WAITING_FOR_EVENT,
        predicate=EQ("ready", True),
        correlation_id="corr_stale_123",
        task_id="task_fence_01",
        run_id="run_current_456",
    )
    await_store.save(wait_cond)

    # 1. Event with stale run_id fails fence
    stale_event = CausalEventEnvelope(
        event_id="evt_stale_1",
        event_type="ready_event",
        correlation_id="corr_stale_123",
        task_id="task_fence_01",
        run_id="run_OLD_999",  # Stale!
    )
    resumed = compiler.handle_event(
        event=stale_event,
        read_authoritative_state=lambda: {"ready": True},
    )
    assert resumed is False
    assert await_store.get("wait_stale_test") is not None

    # 2. Event with identical dedupe_key: first resumes, second is dropped
    valid_event_1 = CausalEventEnvelope(
        event_id="evt_valid_1",
        event_type="ready_event",
        correlation_id="corr_stale_123",
        dedupe_key="unique_checksum_999",
        task_id="task_fence_01",
        run_id="run_current_456",
    )
    valid_event_2 = CausalEventEnvelope(
        event_id="evt_valid_2",
        event_type="ready_event",
        correlation_id="corr_stale_123",
        dedupe_key="unique_checksum_999",  # Duplicate!
        task_id="task_fence_01",
        run_id="run_current_456",
    )

    # First event resumes successfully
    resumed_1 = compiler.handle_event(
        event=valid_event_1,
        read_authoritative_state=lambda: {"ready": True},
    )
    assert resumed_1 is True

    # Second event with same dedupe_key is suppressed
    resumed_2 = compiler.handle_event(
        event=valid_event_2,
        read_authoritative_state=lambda: {"ready": True},
    )
    assert resumed_2 is False


def test_event_wakes_but_authoritative_state_false_does_not_resume(temp_env):
    artifacts = temp_env["artifacts"]
    store = temp_env["store"]

    compiler = TaskCompiler(store=store, artifacts=artifacts)
    await_store = AwaitConditionStore(artifacts=artifacts)

    wait_cond = AwaitCondition(
        wait_id="wait_rule_21_2",
        kind=AwaitKind.WAITING_FOR_EVENT,
        predicate=EQ("server.status", "healthy"),
        correlation_id="corr_srv_health",
        task_id="task_srv_01",
        run_id="run_srv_01",
    )
    await_store.save(wait_cond)

    event = CausalEventEnvelope(
        event_id="evt_srv_01",
        event_type="ping_event",
        correlation_id="corr_srv_health",
        task_id="task_srv_01",
        run_id="run_srv_01",
    )

    # Authoritative state reports server is still "initializing"
    resumed = compiler.handle_event(
        event=event,
        read_authoritative_state=lambda: {"server": {"status": "initializing"}},
    )
    assert resumed is False

    # Condition must remain persisted!
    assert await_store.get("wait_rule_21_2") is not None


def test_ora_and_reentry_metrics_are_wired_to_real_execution_events(temp_env):
    artifacts = temp_env["artifacts"]
    store = temp_env["store"]
    registry = temp_env["registry"]
    ora_metrics = ORAMetrics()

    kernel = OperationalKernel(registry=registry, artifacts=artifacts, ora_metrics=ora_metrics)
    compiler = TaskCompiler(store=store, artifacts=artifacts, ora_metrics=ora_metrics)

    # 1. Register an atomic capability and execute it
    cap_atomic = OperationalCapability(
        id="cap_atomic_metric_test",
        name="Atomic Metric Cap",
        version="1.0.0",
        effect="state_mutation",
        route="filesystem",
        scope={"backends": {"filesystem": {}}},
        implementation={"steps": [{"primitive": "fs_write", "args": {"path": str(temp_env["path"] / "metric.txt"), "content": "1"}}]},
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
    )
    registry.register(cap_atomic)

    kernel.execute_capability("cap_atomic_metric_test", inputs={})

    assert ora_metrics.atomic_capability_invocations == 1
    assert ora_metrics.composite_capability_invocations == 0
    assert ora_metrics.total_capability_invocations == 1
    assert ora_metrics.verified_transitions_deterministic == 0
    assert ora_metrics.unverified_transitions == 1

    # 2. Register child B and propose composite
    cap_b = OperationalCapability(
        id="cap_b_metric_test",
        name="Child B Metric Cap",
        version="1.0.0",
        effect="state_mutation",
        route="filesystem",
        scope={"backends": {"filesystem": {}}},
        implementation={"steps": [{"primitive": "fs_write", "args": {"path": str(temp_env["path"] / "metric_b.txt"), "content": "2"}}]},
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
    )
    registry.register(cap_b)

    hier_compiler = HierarchicalExperienceCompiler(registry=registry)
    composite = hier_compiler.propose_composite(["cap_atomic_metric_test", "cap_b_metric_test"])

    # Execute composite via kernel
    kernel.execute_capability(composite.id, inputs={})

    # Composite execution should increment composite invocations (and also executes its 2 child atomic deps)
    assert ora_metrics.composite_capability_invocations == 1
    assert ora_metrics.atomic_capability_invocations == 3  # 1 initial + 2 deps
    assert ora_metrics.composite_reuse_rate == pytest.approx(1 / 4)

    # 3. Trigger a WaitDecision routing event
    wait_cond = AwaitCondition(
        wait_id="wait_metric_test",
        kind=AwaitKind.WAITING_FOR_EVENT,
        predicate=EQ("x", 1),
        correlation_id="corr_m",
    )
    compiler.metrics_collector.on_routing_decision(WaitDecision(await_condition=wait_cond, reason="waiting"))

    assert ora_metrics.non_resident_wait_count == 1
    assert ora_metrics.wait_non_residency_rate == 1.0

    # 4. Trigger a ReasoningDecision (WAKE_LLM) routing event
    compiler.metrics_collector.on_routing_decision(
        ReasoningDecision(open_condition={"field": "missing"}, reason="open_condition_drift_detected")
    )

    assert ora_metrics.llm_wake_count == 1
    assert "SCHEMA_DRIFT" in ora_metrics.wake_reasons or "OPEN_CONDITION" in ora_metrics.wake_reasons
    assert ora_metrics.total_routing_events == 2
    assert ora_metrics.wake_llm_rate == pytest.approx(1 / 2)
    # ORA has no verified-transition denominator until a canonical verifier passes.
    assert ora_metrics.ora_ratio is None

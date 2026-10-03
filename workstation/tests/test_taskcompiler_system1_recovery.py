import sqlite3
import pytest
from agent.system1_decision import register_system1_decision_provider, reset_system1_decision
from workstation.artifacts import ArtifactStore
from workstation.durable_tasks import DurableTaskStore
from workstation.task_compiler import TaskCompiler
from workstation.system1.provider import FakeSystem1DecisionProvider
from workstation.control_plane.intent import OperationIntent
from workstation.control_plane.ir import EQ
from workstation.control_plane.verification import VerificationEvidence
from workstation.execution_policy import EvidenceStrength
from workstation.operational_capabilities import OperationalCapabilityRegistry
from workstation.tests.test_system1_capability_routing import _validated_verifier


@pytest.mark.parametrize("confidence,has_reader,verified", [(0.99, True, True), (.1, True, True), (.99, False, True), (.99, True, False)])
def test_compiler_known_reprobe_without_system2(tmp_path, monkeypatch, confidence, has_reader, verified):
    import agent.runtime_events as runtime_events
    monkeypatch.setattr(runtime_events, "_observers", [])
    provider_calls = []
    runtime_events.register_runtime_event_observer(lambda name, data: provider_calls.append(data) if name == "provider_called" else None)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    compiler = TaskCompiler(DurableTaskStore(conn=sqlite3.connect(tmp_path / "db")), ArtifactStore(tmp_path / "artifacts"))
    compiler.capability_registry = OperationalCapabilityRegistry(artifacts=compiler.artifacts)
    goal = EQ("service.online", True)
    evidence = VerificationEvidence(evidence_id="owner:read", observer="owner.readback", source_kind="source_of_record",
        value={"service": {"online": True}}, trust_class="trusted_owner" if verified else "untrusted",
        evidence_strength=EvidenceStrength.SEMANTIC_PERSISTED_READBACK, covered_predicates=(goal.fingerprint(),), task_id="t")
    calls = []
    if has_reader:
        compiler.authoritative_state_reader = lambda: calls.append("source.readback") or [evidence]
        compiler.authoritative_state_contract = _validated_verifier(goal)
    reset_system1_decision()
    register_system1_decision_provider(FakeSystem1DecisionProvider(preset_answers={"needs_system2": "no", "known_recovery_path": "reprobe_state"},
        preset_confidence={"needs_system2": confidence, "known_recovery_path": confidence}))
    try:
        result = compiler.execute({"action": "route", "operation_intent": OperationIntent(id="i", target="service", goal=goal).to_dict(),
            "semantic_state": {"service": {"online": False}}}, task_id="t", session_id="s",
            dispatch=lambda *a: pytest.fail("reprobe cannot dispatch mutation"))
        if confidence == .99 and has_reader and verified:
            assert result["routing_decision"] == "SATISFIED"
            assert result["resolution"] == "REPROBE" and result["system2_calls"] == 0
            assert result["verification_result"]["status"] == "VERIFIED"
            assert result["semantic_state"]["service"]["online"] is True
            assert calls == ["source.readback"]
            assert provider_calls == []
        else:
            assert result["routing_decision"] == "WAKE_LLM"
    finally:
        reset_system1_decision()

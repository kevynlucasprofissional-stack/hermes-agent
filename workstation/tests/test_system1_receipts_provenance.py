from types import SimpleNamespace
import pytest
from agent.system1_decision import DecisionRequest, register_system1_decision_provider, reset_system1_decision
from workstation.artifacts import ArtifactStore
from workstation.system1.laya_provider import LayaDecisionProvider
from workstation.system1.receipts import DecisionReceipt, load_decision_receipt, link_decision_receipt
from workstation.control_plane.router import CapabilityRouter, ExecutableDecision
from workstation.control_plane.intent import OperationIntent
from workstation.control_plane.ir import EQ, SET
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.operational_capabilities import OperationalCapabilityRegistry
from workstation.tests.test_system1_capability_routing import _build_test_capability


def test_receipt_roundtrip_unknown_checkpoint_and_request_hash(tmp_path):
    store = ArtifactStore(tmp_path)
    provider = LayaDecisionProvider(artifact_store=store)
    provider._router = SimpleNamespace(predict=lambda **k: {"answers": {"q": {"type": "choice", "choice": "B", "answer_confidence": .99, "probabilities": {"B": .99, "A": .01}}}})
    request = DecisionRequest(task_id="t", run_id="r", operation_id="op", schema_id="s", questions={"q": {"type": "choice", "criteria": {"A": "a", "B": "b"}}})
    result = provider(request)
    receipt = load_decision_receipt(result.details["receipt_ref"], store)
    assert DecisionReceipt.from_dict(receipt.to_dict()).to_dict() == receipt.to_dict()
    assert receipt.request_hash == request.request_hash()
    assert receipt.laya_source_sha and receipt.laya_source_path and receipt.laya_version == "0.3.23"
    assert receipt.model_revision is None and receipt.checkpoint_digest is None
    assert receipt.probabilities["q"]["B"] == .99
    assert store.resolve_ref(receipt.state_ref) and store.resolve_ref(receipt.candidate_set_ref)
    assert store.resolve_ref(receipt.result_ref)
    old_hash = request.request_hash()
    request.candidate_sets = {"q": ["A"]}
    assert request.request_hash() != old_hash


def test_actual_router_receipt_certificate_and_verification_lineage(tmp_path):
    store = ArtifactStore(tmp_path)
    provider = LayaDecisionProvider(artifact_store=store)
    provider._router = SimpleNamespace(predict=lambda **k: {"answers": {"preferred_candidate": {"type": "choice", "choice": "cap_beta", "answer_confidence": .99}}})
    registry = OperationalCapabilityRegistry(artifacts=store)
    for c in ("cap_alpha", "cap_beta"):
        registry.register(_build_test_capability(c))
    reset_system1_decision()
    register_system1_decision_provider(provider)
    try:
        decision = CapabilityRouter(registry=registry).route(OperationIntent(id="i", target="filesystem", goal=EQ("file.exists", True),
            effect_budget=[SET("file.exists", True)], metadata={"target_family": "filesystem"}), {"state": {"ready": True}},
            AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"}), runtime_state={"task_id": "t"}, run_id="r", operation_id="op")
        assert isinstance(decision, ExecutableDecision) and decision.capability.id == "cap_beta"
        receipt = load_decision_receipt(decision.system1_receipt_ref, store)
        assert receipt.downstream_certificate_ref
        assert store.read_json(receipt.downstream_certificate_ref)["operation_id"] == "op"
        verification_ref = store.store("t", "verified.json", {"status": "VERIFIED"}).ref
        assert link_decision_receipt(decision.system1_receipt_ref, store, task_id="t", run_id="r", operation_id="op", verification_ref=verification_ref)
        assert load_decision_receipt(decision.system1_receipt_ref, store).downstream_verification_ref == verification_ref
        with pytest.raises(ValueError, match="lineage mismatch"):
            link_decision_receipt(decision.system1_receipt_ref, store, run_id="different", verification_ref=verification_ref)
    finally:
        reset_system1_decision()


def test_error_fallback_has_durable_receipt(tmp_path):
    provider = LayaDecisionProvider(artifact_store=ArtifactStore(tmp_path))
    def fail(**kwargs):
        raise RuntimeError("provider offline")
    provider._router = SimpleNamespace(predict=fail)
    result = provider(DecisionRequest(questions={"q": {"type": "noul"}}))
    receipt = load_decision_receipt(result.details["receipt_ref"], provider.artifact_store)
    assert receipt.fallback_taken and receipt.influence_mode == "fallback"

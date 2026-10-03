"""The actual 0.3.23 typed response, plus opt-in checkpoint inference."""
import os
from types import SimpleNamespace

import pytest

from agent.system1_decision import DecisionRequest, register_system1_decision_provider, reset_system1_decision
from workstation.artifacts import ArtifactStore
from workstation.system1.laya_provider import LayaDecisionProvider
from workstation.system1.receipts import load_decision_receipt


def test_typed_contract_and_calibrated_gate(tmp_path):
    store = ArtifactStore(root_dir=tmp_path)
    provider = LayaDecisionProvider(artifact_store=store)
    payload = {"model": "laya-rl-agent", "answers": {
        "preferred_candidate": {"type": "choice", "choice": "B", "probabilities": {"A": .1, "B": .9}, "confidence": .4, "answer_confidence": .9},
        "urgency": {"type": "score", "score": 2.8, "probabilities": {"0": .01, "1": .02, "2": .13, "3": .84}, "answer_confidence": .84},
        "risk": {"type": "noul", "noul": .02, "answer_confidence": .98},
    }, "routing": {"model": "multilingual"}}
    provider._router = SimpleNamespace(predict=lambda **kwargs: payload)
    request = DecisionRequest(task_id="t", run_id="r", operation_id="op", schema_id="typed-v1", questions={
        "preferred_candidate": {"type": "choice", "criteria": {"A": "A", "B": "B"}},
        "urgency": {"type": "score", "criteria": ["low", "medium", "high", "critical"]},
        "risk": {"type": "noul"},
    })
    result = provider(request)
    assert result.answers == {"preferred_candidate": "B", "urgency": 2.8, "risk": .02}
    assert result.confidence["preferred_candidate"] == .9
    assert result.calibrated_confidences == result.confidence
    assert result.probabilities["preferred_candidate"] == {"A": .1, "B": .9}
    assert not result.abstentions and not result.fallback_recommended
    assert result.request_hash == request.request_hash()
    receipt = load_decision_receipt(result.details["receipt_ref"], store)
    assert receipt.answers == result.answers
    assert receipt.task_id == "t" and receipt.operation_id == "op"


def test_wrong_old_format_and_unbounded_choice_abstain(tmp_path):
    provider = LayaDecisionProvider(artifact_store=ArtifactStore(root_dir=tmp_path))
    request = DecisionRequest(questions={"q": {"type": "choice", "criteria": {"A": "A"}}})
    for payload in ({"q": {"answer": "A", "confidence": .99}}, {"answers": {"q": {"type": "choice", "choice": "outside", "answer_confidence": .99}}}):
        provider._router = SimpleNamespace(predict=lambda **kwargs: payload)
        result = provider(request)
        assert result.fallback_recommended and result.abstentions == ["q"]


@pytest.mark.skipif(os.getenv("HERMES_LAYA_LIVE_TEST") != "1", reason="explicit checkpoint opt-in required")
def test_live_checkpoint_reaches_bounded_router(tmp_path):
    from workstation.tests.test_system1_capability_routing import _build_test_capability
    from workstation.control_plane.router import CapabilityRouter, ExecutableDecision
    from workstation.control_plane.intent import OperationIntent
    from workstation.control_plane.ir import EQ, SET
    from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
    from workstation.operational_capabilities import OperationalCapabilityRegistry
    provider = LayaDecisionProvider(artifact_store=ArtifactStore(root_dir=tmp_path))
    registry = OperationalCapabilityRegistry(artifacts=provider.artifact_store)
    for name in ("send_email", "read_file"):
        registry.register(_build_test_capability(name))
    reset_system1_decision()
    routed_results = []
    def live_provider(request):
        outcome = provider(request)
        routed_results.append(outcome)
        return outcome
    register_system1_decision_provider(live_provider)
    try:
        result = provider(DecisionRequest(questions={"q": {"type": "choice", "instructions": "Choose the matching word: beta", "criteria": {"cap_alpha": "alpha", "cap_beta": "beta"}}}))
        assert result.answers["q"] in ("cap_alpha", "cap_beta")
        assert "error" not in result.details and provider.provenance.source_bytes_verified
        decision = CapabilityRouter(registry=registry).route(
            OperationIntent(id="live", target="filesystem", goal=EQ("file.exists", True), effect_budget=[SET("file.exists", True)], metadata={"target_family": "filesystem", "objective": "Read an existing file from the filesystem."}),
            {"state": {"ready": True}}, AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"}))
        assert isinstance(decision, ExecutableDecision) and decision.certificate.is_valid()
        assert decision.system1_receipt_ref, [(r.answers, r.confidence, r.abstentions, r.details) for r in routed_results]
        receipt = load_decision_receipt(decision.system1_receipt_ref, provider.artifact_store)
        assert not receipt.fallback_taken and not receipt.abstentions
        assert receipt.answers["preferred_candidate"] == decision.capability.id == "read_file"
        assert receipt.downstream_certificate_ref
        assert receipt.model_revision
    finally:
        reset_system1_decision()

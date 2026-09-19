"""Focused RED/GREEN test suite for H-077 Phase P0: Truthful Core Cleanup.

Seams tested:
- P0-A: Routing does not increment verified transitions or capability invocations.
- P0-B: Unknown/unsupported/malformed conditions fail closed.
- P0-C: Verification cannot synthesize terminal evidence from expected value.
- P0-D: Resource binding must be proven; mismatch or missing identity fails closed.
- P0-E: Causal transition claims require expected_operation_id match; presence alone fails.
- P0-F: Legacy boolean verifier cannot commit; fails closed as INCONCLUSIVE.
"""
from datetime import datetime, timezone
from pathlib import Path
import pytest
import tempfile

from workstation.artifacts import ArtifactStore
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.dispatcher import CertifiedDispatcher, DispatchError, DispatchStatus
from workstation.control_plane.intent import OperationIntent, OperationMode
from workstation.control_plane.ir import EQ
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.metrics import ORAMetrics, ORAMetricsCollector
from workstation.control_plane.router import (
    CapabilityRouter,
    ComposedDecision,
    ExecutableDecision,
    RoutingCertificate,
)
from workstation.control_plane.verification import (
    EvidenceStrength,
    VerificationContract,
    VerificationEvidence,
    VerificationLifecycle,
    VerificationRelation,
    VerificationResult,
    VerificationStatus,
    evaluate_verification,
)
from workstation.operational_capabilities import (
    CapabilityLifecycle,
    OperationalCapability,
    OperationalCapabilityRegistry,
)
from workstation.operational_kernel import CapabilityDriftError, OperationalKernel


# ---------------------------------------------------------------------------
# P0-A Tests
# ---------------------------------------------------------------------------

def test_routing_alone_does_not_increment_verified_or_invocations():
    metrics = ORAMetrics()
    collector = ORAMetricsCollector(metrics=metrics)

    cap = OperationalCapability(
        id="cap_test_routing",
        name="Routing Test",
        version="1.0.0",
        effect="state_mutation",
        route="filesystem",
        scope={},
        implementation={"steps": []},
    )
    cert = RoutingCertificate(
        target_match=True,
        deterministic_closure=True,
        capability_id="cap_test_routing",
        capability_version="1.0.0",
    )
    decision = ExecutableDecision(capability=cap, certificate=cert)

    # Route decision
    collector.on_routing_decision(decision)

    assert metrics.total_routing_events == 1
    assert metrics.verified_transitions_deterministic == 0
    assert metrics.verified_transitions_reasoned == 0
    assert metrics.unverified_transitions == 0
    assert metrics.total_capability_invocations == 0
    assert metrics.atomic_capability_invocations == 0
    assert metrics.composite_capability_invocations == 0
    assert metrics.ora_ratio is None


def test_routing_composed_decision_does_not_increment_verified():
    metrics = ORAMetrics()
    collector = ORAMetricsCollector(metrics=metrics)

    cert = RoutingCertificate(
        target_match=True,
        deterministic_closure=True,
        capability_id="composite",
        capability_version="1.0.0",
    )
    composed_decision = ComposedDecision(plan=[], certificate=cert)

    collector.on_routing_decision(composed_decision)

    assert metrics.total_routing_events == 1
    assert metrics.verified_transitions_deterministic == 0
    assert metrics.total_capability_invocations == 0
    assert metrics.composite_capability_invocations == 0
    assert metrics.ora_ratio is None


def test_transition_has_no_optimistic_verified_default():
    metrics = ORAMetrics()
    collector = ORAMetricsCollector(metrics=metrics)

    # Calling on_transition without arguments must NOT mark verified=True
    collector.on_transition()

    assert metrics.verified_transitions_deterministic == 0
    assert metrics.verified_transitions_reasoned == 0
    assert metrics.unverified_transitions == 1


# ---------------------------------------------------------------------------
# P0-B Tests
# ---------------------------------------------------------------------------

def test_unknown_condition_type_fails_closed():
    kernel = OperationalKernel()

    # Unknown type
    unknown_cond = {"type": "unknown_future_condition", "val": 123}
    assert kernel.verify_condition(unknown_cond, {}) is False

    # Malformed string condition
    assert kernel.verify_condition("not valid json", {}) is False

    # Non-dict object
    assert kernel.verify_condition(12345, {}) is False

    # check_conditions raises CapabilityDriftError on unknown condition
    with pytest.raises(CapabilityDriftError):
        kernel.check_conditions([unknown_cond], {}, stage="precondition")


def test_known_condition_types_still_work():
    kernel = OperationalKernel()

    context = {"semantic_state": {"card_status": "done"}, "order": {"id": "123"}}

    # semantic_predicate
    assert kernel.verify_condition({"type": "semantic_predicate", "key": "card_status", "expected": "done"}, context) is True
    assert kernel.verify_condition({"type": "semantic_predicate", "key": "card_status", "expected": "in_progress"}, context) is False

    # field_equals
    assert kernel.verify_condition({"type": "field_equals", "field": "order.id", "expected": "123"}, context) is True
    assert kernel.verify_condition({"type": "field_equals", "field": "order.id", "expected": "999"}, context) is False

    # not_empty
    assert kernel.verify_condition({"type": "not_empty", "field": "order.id"}, context) is True
    assert kernel.verify_condition({"type": "not_empty", "field": "order.missing"}, context) is False


# ---------------------------------------------------------------------------
# P0-C Tests
# ---------------------------------------------------------------------------

def test_no_synthetic_evidence_from_expected_value():
    kernel = OperationalKernel()

    cap = OperationalCapability(
        id="cap_auto_evidence_adversarial",
        name="Auto Evidence Adversarial",
        version="1.0.0",
        effect="state_mutation",
        route="filesystem",
        scope={},
        implementation={"steps": []},
        verifier_contract=VerificationContract(
            observer="read_card_status",
            source_kind="saas_api",
            relation=VerificationRelation.EXACT,
            covered_predicates=("card_status",),
            minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
            lifecycle=VerificationLifecycle.VALIDATED,
            allowed_trust=("trusted_runtime",),
        ),
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
    )
    kernel.registry.register(cap)

    # Execute capability without providing verification_evidence and with no observer available
    res = kernel.execute_capability("cap_auto_evidence_adversarial", inputs={}, context={
        "verification_expected": "done",
    })

    # The expected value "done" must NOT manufacture terminal evidence!
    assert res["verification"]["accepted"] is False
    assert res["verification_result"]["status"] in ("INCONCLUSIVE", "FAILED")
    assert res["verification_result"]["status"] != "VERIFIED"


def test_real_observer_returning_old_value_fails():
    kernel = OperationalKernel()

    cap = OperationalCapability(
        id="cap_real_observer_fail",
        name="Real Observer Fail",
        version="1.0.0",
        effect="state_mutation",
        route="filesystem",
        scope={},
        implementation={"steps": []},
        verifier_contract=VerificationContract(
            observer="real_status_reader",
            source_kind="saas_api",
            relation=VerificationRelation.EXACT,
            covered_predicates=("status",),
            minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
            lifecycle=VerificationLifecycle.VALIDATED,
            allowed_trust=("trusted_runtime",),
        ),
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
    )
    kernel.registry.register(cap)

    # Real observer returns old value "pending" instead of expected "complete"
    res = kernel.execute_capability("cap_real_observer_fail", inputs={}, context={
        "verification_expected": "complete",
        "observer_fn": lambda: "pending",
    })

    assert res["verification"]["accepted"] is False
    assert res["verification_result"]["status"] == "FAILED"


# ---------------------------------------------------------------------------
# P0-D Tests
# ---------------------------------------------------------------------------

def test_resource_binding_enforced():
    contract = VerificationContract(
        observer="card_reader",
        source_kind="saas_api",
        resource_binding={"resource_id": "card_A"},
        relation=VerificationRelation.EXACT,
        covered_predicates=("title",),
        minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        lifecycle=VerificationLifecycle.VALIDATED,
        allowed_trust=("trusted_runtime",),
    )

    now = datetime.now(timezone.utc).isoformat()

    # Case 1: Evidence matches resource_A
    ev_correct = VerificationEvidence(
        evidence_id="ev_1",
        observer="card_reader",
        source_kind="saas_api",
        value="New Card Title",
        resource_id="card_A",
        evidence_strength=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        trust_class="trusted_runtime",
        observed_at=now,
        read_after_write=True,
        covered_predicates=("title",),
    )
    res_ok = evaluate_verification(contract, "New Card Title", [ev_correct])
    assert res_ok.status == VerificationStatus.VERIFIED

    # Case 2: Evidence matches wrong resource_B (same title on different card)
    ev_wrong_resource = VerificationEvidence(
        evidence_id="ev_2",
        observer="card_reader",
        source_kind="saas_api",
        value="New Card Title",
        resource_id="card_B",
        evidence_strength=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        trust_class="trusted_runtime",
        observed_at=now,
        read_after_write=True,
        covered_predicates=("title",),
    )
    res_mismatch = evaluate_verification(contract, "New Card Title", [ev_wrong_resource])
    assert res_mismatch.status == VerificationStatus.INCONCLUSIVE
    assert "resource_binding_mismatch" in res_mismatch.reason

    # Case 3: Evidence lacks resource_id entirely when binding required
    ev_no_resource = VerificationEvidence(
        evidence_id="ev_3",
        observer="card_reader",
        source_kind="saas_api",
        value="New Card Title",
        resource_id="",
        evidence_strength=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        trust_class="trusted_runtime",
        observed_at=now,
        read_after_write=True,
        covered_predicates=("title",),
    )
    res_missing = evaluate_verification(contract, "New Card Title", [ev_no_resource])
    assert res_missing.status == VerificationStatus.INCONCLUSIVE
    assert "resource_binding_missing" in res_missing.reason


# ---------------------------------------------------------------------------
# P0-E Tests
# ---------------------------------------------------------------------------

def test_operation_identity_enforced_for_transition_claim():
    contract = VerificationContract(
        observer="task_reader",
        source_kind="saas_api",
        relation=VerificationRelation.EXACT,
        covered_predicates=("done",),
        minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        lifecycle=VerificationLifecycle.VALIDATED,
        allowed_trust=("trusted_runtime",),
        transition_claim=True,
    )
    now = datetime.now(timezone.utc).isoformat()

    # Case 1: Evidence matches expected_operation_id
    ev_matching = VerificationEvidence(
        evidence_id="ev_op1",
        observer="task_reader",
        source_kind="saas_api",
        value=True,
        operation_id="op_alpha_123",
        evidence_strength=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        trust_class="trusted_runtime",
        observed_at=now,
        read_after_write=True,
        covered_predicates=("done",),
    )
    res_ok = evaluate_verification(contract, True, [ev_matching], expected_operation_id="op_alpha_123")
    assert res_ok.status == VerificationStatus.VERIFIED
    assert res_ok.transition_proven is True

    # Case 2: Evidence has different non-empty operation_id
    res_diff_op = evaluate_verification(contract, True, [ev_matching], expected_operation_id="op_beta_999")
    assert res_diff_op.status == VerificationStatus.INCONCLUSIVE
    assert res_diff_op.transition_proven is False

    # Case 3: expected_operation_id missing for transition_claim=True
    res_missing_expected = evaluate_verification(contract, True, [ev_matching], expected_operation_id=None)
    assert res_missing_expected.status == VerificationStatus.INCONCLUSIVE
    assert res_missing_expected.transition_proven is False

    # Case 4: transition_claim=False does not require operation_id for state satisfaction
    contract_state_only = VerificationContract(
        observer="task_reader",
        source_kind="saas_api",
        relation=VerificationRelation.EXACT,
        covered_predicates=("done",),
        minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        lifecycle=VerificationLifecycle.VALIDATED,
        allowed_trust=("trusted_runtime",),
        transition_claim=False,
    )
    res_state_only = evaluate_verification(contract_state_only, True, [ev_matching], expected_operation_id=None)
    assert res_state_only.status == VerificationStatus.VERIFIED


# ---------------------------------------------------------------------------
# P0-F Tests
# ---------------------------------------------------------------------------

def test_isolated_boolean_true_never_reaches_committed():
    from workstation.control_plane.router import _state_hash
    dispatcher = CertifiedDispatcher()
    cap = OperationalCapability(id="cap_bool", name="Bool Cap", version="1.0.0", effect="state_mutation", route="filesystem", scope={}, implementation={"steps": []})
    cert = RoutingCertificate.create(capability_id="cap_bool", capability_version=cap.version, precondition_state_hash=_state_hash({}))
    decision = ExecutableDecision(capability=cap, certificate=cert)

    # verifier_fn returning raw True boolean must fail closed as INCONCLUSIVE and never reach COMMITTED
    res = dispatcher.dispatch(
        decision,
        current_state={},
        dispatch_fn=lambda: {"ok": True},
        verifier_fn=lambda result: True,
    )
    assert res["success"] is False
    assert res["error"] == "verification_failed"
    assert res["dispatch_record"]["status"] in (DispatchStatus.UNCERTAIN, DispatchStatus.UNCERTAIN.value)
    assert res["verification_result"]["status"] == "INCONCLUSIVE"
    assert "legacy_boolean_verifier_is_not_canonical_evidence" in res["verification_result"]["reason"]


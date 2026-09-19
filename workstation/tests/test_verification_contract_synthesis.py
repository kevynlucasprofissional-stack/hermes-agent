from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.dispatcher import CertifiedDispatcher, DispatchStatus
from workstation.control_plane.router import ExecutableDecision, RoutingCertificate, _state_hash
from workstation.control_plane.verification import (
    VerificationContract, VerificationEvidence, VerificationLifecycle,
    VerificationRelation, VerificationResult, VerificationStatus,
    evaluate_verification, register_owner_canonicalizer, relation_matches,
    validate_verifier_candidate, validate_verifier_sensitivity, verifier_drifted,
)
from workstation.execution_policy import EvidenceStrength
from workstation.operational_capabilities import CapabilityLifecycle, OperationalCapability


def contract(**overrides):
    base = dict(
        covered_predicates=("card.description",),
        effect_classes=("external_mutation",),
        observer="trello.card.read",
        source_kind="authenticated_http",
        minimum_evidence=EvidenceStrength.INDEPENDENT_PERSISTED_READBACK,
        allowed_trust=("trusted_owner",),
        mutation_failure_domains=("trello_web:browser_renderer",),
        allowed_observer_failure_domains=("trello_api",),
        require_distinct_failure_domain=True,
        temporal_basis="version",
        require_read_after_write=True,
        lifecycle=VerificationLifecycle.VALIDATED,
    )
    base.update(overrides)
    return VerificationContract(**base)


def evidence(value="hello", **overrides):
    base = dict(
        evidence_id="ev-1", observer="trello.card.read",
        source_kind="authenticated_http", value=value,
        evidence_strength=EvidenceStrength.INDEPENDENT_PERSISTED_READBACK,
        trust_class="trusted_owner", observer_failure_domain="trello_api",
        resource_version="42", observed_at=datetime.now(timezone.utc).isoformat(),
        read_after_write=True, covered_predicates=("card.description",),
        artifact_ref="artifact://ev-1", operation_id="op-1",
    )
    base.update(overrides)
    return VerificationEvidence(**base)


def test_verification_contract_roundtrip_and_fingerprint():
    original = contract()
    restored = VerificationContract.from_dict(original.to_dict())
    assert restored == original
    assert restored.fingerprint() == original.fingerprint()
    assert replace(original, extractor_path="card.desc").fingerprint() != original.fingerprint()


def test_exact_relation_rejects_changed_punctuation():
    c = contract(relation=VerificationRelation.EXACT)
    assert relation_matches(c, "Title: value", "Title value") is False


def test_owner_canonical_accepts_only_declared_normalizations():
    register_owner_canonicalizer("trello.description", "1", lambda v: str(v).replace("\r\n", "\n"))
    c = contract(relation=VerificationRelation.OWNER_CANONICAL,
                 canonicalizer_id="trello.description", canonicalizer_version="1")
    assert relation_matches(c, "a\r\nb", "a\nb")
    assert not relation_matches(c, "Title: value", "Title value")


def test_owner_canonicalizer_property_roundtrip_and_negative_examples():
    register_owner_canonicalizer("line-endings", "1", lambda v: str(v).replace("\r\n", "\n"))
    c = contract(relation=VerificationRelation.OWNER_CANONICAL,
                 canonicalizer_id="line-endings", canonicalizer_version="1")
    for text in ("", "alpha", "a\nb", "colon: preserved", "punctuation!"):
        assert relation_matches(c, text, text)
    assert not relation_matches(c, "colon: preserved", "colon preserved")


def test_ack_success_never_implies_persisted_effect():
    cap = OperationalCapability("cap", "cap", lifecycle=CapabilityLifecycle.PROMOTED)
    cert = RoutingCertificate.create(capability_id="cap", capability_version=cap.version,
                                     precondition_state_hash=_state_hash({}))
    result = CertifiedDispatcher().dispatch(
        ExecutableDecision(cap, cert), {}, dispatch_fn=lambda: {"success": True},
        verifier_fn=lambda output: output["success"],
    )
    assert not result["success"]
    assert result["dispatch_record"]["status"] == DispatchStatus.UNCERTAIN.value


def test_dispatcher_uses_canonical_verification_result_not_executor_self_report():
    cap = OperationalCapability("cap", "cap", lifecycle=CapabilityLifecycle.PROMOTED)
    cert = RoutingCertificate.create(capability_id="cap", capability_version=cap.version,
                                     precondition_state_hash=_state_hash({}))
    canonical = VerificationResult(VerificationStatus.FAILED, reason="backend unchanged")
    result = CertifiedDispatcher().dispatch(
        ExecutableDecision(cap, cert), {},
        dispatch_fn=lambda: {"success": True, "verification": {"accepted": True}},
        verification_result_fn=lambda _: canonical,
    )
    assert not result["success"]
    assert result["verification_result"]["status"] == "FAILED"


def test_same_surface_browser_observation_cannot_certify_external_commit():
    result = evaluate_verification(
        contract(), "hello",
        [evidence(observer="trello.card.read", source_kind="authenticated_http",
                  observer_failure_domain="trello_web:browser_renderer")],
        mutation_failure_domains={"trello_web:browser_renderer"},
    )
    assert result.status == VerificationStatus.INCONCLUSIVE
    assert result.reason == "correlated_failure_domain"


def test_state_fresh_requires_temporal_or_version_basis_when_required():
    result = evaluate_verification(contract(), "hello", [evidence(resource_version="")])
    assert result.status == VerificationStatus.STALE


def test_verification_result_distinguishes_failed_inconclusive_conflict_and_stale():
    c = contract()
    assert evaluate_verification(c, "expected", [evidence("wrong")]).status == VerificationStatus.FAILED
    assert evaluate_verification(c, "expected", []).status == VerificationStatus.INCONCLUSIVE
    assert evaluate_verification(c, "expected", [evidence("expected"), evidence("other", evidence_id="ev-2")]).status == VerificationStatus.CONFLICT
    assert evaluate_verification(c, "expected", [evidence("expected", resource_version="")]).status == VerificationStatus.STALE


def test_verifier_without_required_predicate_coverage_cannot_commit():
    result = evaluate_verification(contract(), "hello", [evidence(covered_predicates=())],
                                   required_predicates={"card.description"})
    assert result.status == VerificationStatus.INCONCLUSIVE


def test_verifier_disagreement_preserves_conflict():
    result = evaluate_verification(contract(), "hello", [evidence("hello"), evidence("bye", evidence_id="ev-2")])
    assert result.status == VerificationStatus.CONFLICT


def test_mutation_withheld_distinguishes_state_satisfaction_from_causation():
    state_only = evaluate_verification(contract(transition_claim=False), "hello", [evidence(operation_id="")])
    causal = evaluate_verification(contract(transition_claim=True), "hello", [evidence(operation_id="")])
    assert state_only.status == VerificationStatus.VERIFIED
    assert state_only.transition_proven is True
    assert causal.status == VerificationStatus.INCONCLUSIVE


def test_verifier_negative_control_detects_always_pass_oracle():
    valid, reasons = validate_verifier_sensitivity([
        {"kind": "positive_replay", "passed": True, "phase": "validation", "evidence_ref": "positive"}
    ])
    assert not valid
    assert "missing_discriminative_negative_control" in reasons


def test_verifier_promotion_requires_discovery_validation_split():
    receipts = [
        {"kind": "positive_replay", "passed": True, "phase": "discovery", "evidence_ref": "same"},
        {"kind": "negative_control", "passed": True, "phase": "validation", "evidence_ref": "same"},
    ]
    promoted, reasons = validate_verifier_candidate(contract(lifecycle=VerificationLifecycle.CANDIDATE), receipts)
    assert promoted.lifecycle == VerificationLifecycle.QUARANTINED
    assert "discovery_validation_evidence_reused" in reasons


def test_verifier_fingerprint_drift_quarantines_pair():
    original = contract()
    drifted = replace(original, extractor_path="card.description.v2")
    assert verifier_drifted(original.fingerprint(), drifted)
    result = evaluate_verification(drifted, "hello", [evidence(verifier_fingerprint=original.fingerprint())])
    assert result.status == VerificationStatus.STALE


def test_unannotated_read_tool_cannot_become_independent_e3_verifier():
    legacy = VerificationContract.from_dict({"kind": "readback"})
    assert legacy.minimum_evidence == EvidenceStrength.TOOL_ACK_ONLY
    assert legacy.lifecycle == VerificationLifecycle.CANDIDATE
    assert not legacy.is_sufficient_for(mutation=True)[0]


def test_router_verifier_sufficiency_is_proven_not_presence_based():
    present_but_unknown = VerificationContract.from_dict({"kind": "readback"})
    sufficient, reasons = present_but_unknown.is_sufficient_for(
        required_predicates={"card.description"}, mutation=True, temporal_required=True,
    )
    assert not sufficient
    assert {"verifier_not_validated", "source_unknown", "predicate_coverage_insufficient", "temporal_basis_missing"} <= set(reasons)


def test_await_and_mutation_verification_share_predicate_evaluator_semantics():
    from workstation.control_plane.waiting import evaluate_authoritative_observation
    c = contract()
    mutation = evaluate_verification(c, "hello", [evidence("hello")])
    awaited = evaluate_authoritative_observation(c, "hello", [evidence("hello")],
                                                 required_predicates={"card.description"})
    assert awaited.status == mutation.status == VerificationStatus.VERIFIED
    assert awaited.verifier_fingerprint == mutation.verifier_fingerprint


def test_experience_compiler_proposes_verifier_candidate_without_promoting_it():
    legacy_observation = {
        "schema_version": "1.0.0", "observer": "owner.read", "source_kind": "source_of_record",
        "relation": "EXACT", "covered_predicates": ["x"], "minimum_evidence": 2,
    }
    candidate = VerificationContract.from_dict(legacy_observation)
    assert candidate.lifecycle == VerificationLifecycle.CANDIDATE
    assert not candidate.is_sufficient_for(required_predicates={"x"}, mutation=True)[0]


def test_causal_replay_cannot_upgrade_pair_with_inadmissible_verifier():
    from workstation.experience_compiler.causal import _verified
    cap = SimpleNamespace(
        learning_metadata={"effects": {"x": 1}, "verifier_fingerprint": "expected"}
    )
    assert not _verified(cap, {
        "passed": True, "predicates": {"x": 1}, "evidence_strength": 3,
        "evidence_refs": ["artifact://self-report"],
        "verification_result": {"status": "INCONCLUSIVE", "verifier_fingerprint": "expected"},
    })


def test_run_closure_rejects_candidate_or_stale_verifier():
    candidate = replace(contract(), lifecycle=VerificationLifecycle.CANDIDATE)
    assert not candidate.is_sufficient_for(required_predicates={"card.description"}, mutation=True)[0]
    stale = evaluate_verification(contract(), "hello", [evidence(verifier_fingerprint="old")])
    assert stale.status == VerificationStatus.STALE


def test_run_closure_accepts_validated_fresh_covered_verifier():
    result = evaluate_verification(contract(), "hello", [evidence("hello")],
                                   required_predicates={"card.description"})
    assert result.status == VerificationStatus.VERIFIED
    assert result.freshness_satisfied
    assert set(result.covered_predicates) == {"card.description"}

"""H-077.1 RED/GREEN truth-boundary regressions."""
from datetime import datetime, timezone

import pytest

from workstation.control_plane.validity_envelope import derive_validity_envelope
from workstation.control_plane.verification import (
    VerificationContract, VerificationEvidence, VerificationLifecycle,
    VerificationStatus, evaluate_verification,
)
from workstation.evaluation import evaluate_external_validity
from workstation.execution_policy import EvidenceStrength
from workstation.operational_capabilities import CapabilityLifecycle, OperationalCapability
from workstation.operational_kernel import OperationalKernel


def _contract(**changes):
    body = dict(observer="owner.read", source_kind="source_of_record", covered_predicates=("done",),
                minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
                allowed_trust=("trusted_owner",), lifecycle=VerificationLifecycle.VALIDATED)
    body.update(changes)
    return VerificationContract(**body)


def _evidence(**changes):
    body = dict(evidence_id="readback", observer="owner.read", source_kind="source_of_record", value=True,
                evidence_strength=EvidenceStrength.SEMANTIC_PERSISTED_READBACK, trust_class="trusted_owner",
                observed_at=datetime.now(timezone.utc).isoformat(), covered_predicates=("done",),
                task_id="task-a", run_id="run-a", operation_id="op-a")
    body.update(changes)
    return VerificationEvidence(**body)


@pytest.mark.parametrize("status", ["INCONCLUSIVE", "FAILED", "STALE", "CONFLICT"])
def test_non_verified_ack_is_not_terminal_success(status):
    # This is the representation TaskCompiler consumes after a physical ACK.
    result = {"execution_acknowledged": True, "verification_result": {"status": status, "accepted": False}}
    terminal = result["verification_result"]["status"] == "VERIFIED" and result["verification_result"]["accepted"]
    assert terminal is False


def test_task_run_and_operation_lineage_are_all_fenced():
    c = _contract(transition_claim=True)
    assert evaluate_verification(c, True, [_evidence(task_id="other")], expected_task_id="task-a",
                                 expected_run_id="run-a", expected_operation_id="op-a").reason == "task_id_mismatch"
    assert evaluate_verification(c, True, [_evidence(task_id="")], expected_task_id="task-a").reason == "task_id_missing"
    assert evaluate_verification(c, True, [_evidence(run_id="other")], expected_run_id="run-a").reason == "run_id_mismatch"
    assert evaluate_verification(c, True, [_evidence(run_id="")], expected_run_id="run-a").reason == "run_id_missing"
    assert evaluate_verification(c, True, [_evidence()], expected_task_id="task-a", expected_run_id="run-a",
                                 expected_operation_id="op-a").status == VerificationStatus.VERIFIED


def test_validity_envelope_fails_closed_for_required_context():
    cap = OperationalCapability("promoted", "promoted", lifecycle=CapabilityLifecycle.PROMOTED,
                                scope={"tenant_id": "alpha", "target_family": "card"},
                                verifier_contract=_contract(resource_binding={"resource_id": "card-1"}).to_dict())
    missing = derive_validity_envelope(cap, current_context={})
    assert not missing.is_valid_for_reuse
    assert not derive_validity_envelope(cap, current_context={"tenant_id": "alpha", "target_family": "card"}).is_valid_for_reuse
    assert derive_validity_envelope(cap, current_context={"tenant_id": "alpha", "target_family": "card", "resource_id": "card-1"}).is_valid_for_reuse


def test_external_metrics_exclude_unknown_truth_from_external_rates():
    runs = [{"internal_verified": True, "external_success": False}] + [{"internal_verified": True} for _ in range(99)]
    metrics = evaluate_external_validity(runs)
    assert metrics.fcor == 1.0
    assert metrics.external_oracle_coverage == 0.01
    assert metrics.certified_external_oracle_coverage == 0.01
    assert metrics.external_correctness == 0.0


def test_missing_external_truth_never_becomes_recovery_or_reuse_success():
    metrics = evaluate_external_validity([
        {"recovery_attempted": True, "recovery_succeeded": True},
        {"is_reuse": True, "reuse_success": True, "internal_verified": True},
    ])
    assert metrics.recovery_correctness is None
    assert metrics.external_reuse_reliability is None


def test_raw_observer_cannot_inherit_contract_provenance_or_success_counter():
    cap = OperationalCapability("raw-observer", "raw-observer", verifier_contract=_contract().to_dict())
    result = OperationalKernel().execute_capability(
        cap, {}, context={"verification_expected": True, "observer_fn": lambda: True}, owner="task-a",
    )
    assert result["execution_acknowledged"] is True
    assert result["success"] is False
    assert result["verification_result"]["status"] == "INCONCLUSIVE"
    assert cap.success_count == 0


def test_only_verified_result_increments_success_counter():
    cap = OperationalCapability("verified-observer", "verified-observer", verifier_contract=_contract().to_dict())
    result = OperationalKernel().execute_capability(
        cap, {}, context={"verification_expected": True, "verification_evidence": [_evidence()]}, owner="task-a",
    )
    assert result["execution_acknowledged"] is True
    assert result["success"] is True
    assert cap.success_count == 1


@pytest.mark.parametrize("scenario", ["hidden_state_pair", "source_disagreement", "lost_ack_restart",
    "temporal_maintain", "composition_emergence", "semantic_drift", "goal_shift", "dynamic_queue", "post_promotion_holdout"])
def test_afb_rows_are_derived_from_sut_and_independent_oracle(scenario):
    from workstation.tests.afb_harness import run_afb_scenario
    result = run_afb_scenario(scenario,
        lambda: {"verification_result": {"status": "INCONCLUSIVE", "accepted": False}, "mutation_applied": False},
        lambda: (False, {"oracle": scenario, "executed_independently": True}),
    )
    row = result.metric_row()
    assert row["external_success"] is False
    assert row["oracle_evidence"]["executed_independently"] is True

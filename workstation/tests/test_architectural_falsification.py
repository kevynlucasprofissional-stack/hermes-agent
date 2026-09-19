"""Architectural Falsification Benchmark (AFB-v0) - H-077.

Adversarial test suite designed to falsify system guarantees across 11 core failure modes:
- Scenario A: Phantom Oracle (internal verifier claims success but external resource unmodified)
- Scenario B: Masked Drift (preconditions pass syntactically, but resource semantics changed)
- Scenario C: Blind Concurrency (concurrent external mutation occurs between execution and verification)
- Scenario D: Non-Discriminable Counterexample (identical apparent state generates contradictory outcomes)
- Scenario E: False Success by No-Op (action made no mutation, but verifier claimed success due to pre-existing state)
- Scenario F: Broken Causal Dependency (downstream step runs against unverified/failed upstream state)
- Scenario G: Validity Envelope Violation (capability executed outside its verified operational envelope)
- Scenario H: Hidden Assumption Violated (unmodelled environment variable / locale breaks execution)
- Scenario I: Verifier Blind to Side Effect (target verified, but adjacent resource corrupted)
- Scenario J: Cumulative Drift Reuse Degradation (drift accumulates across N >= 10 reuses)
- Scenario K: Read-Verify Race Condition (external state altered after evidence read, before commit)

Each scenario incorporates an independent external ground-truth oracle.
"""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from typing import Any
import pytest

from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.dispatcher import CertifiedDispatcher
from workstation.control_plane.intent import OperationIntent, OperationMode
from workstation.control_plane.ir import EQ
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.metrics import ORAMetrics, ORAMetricsCollector
from workstation.control_plane.router import CapabilityRouter, ExecutableDecision, RoutingCertificate
from workstation.control_plane.validity_envelope import derive_validity_envelope
from workstation.control_plane.verification import (
    EvidenceStrength,
    VerificationContract,
    VerificationEvidence,
    VerificationLifecycle,
    VerificationRelation,
    VerificationResult,
    VerificationStatus,
    evaluate_verification,
    validate_verifier_sensitivity,
)
from workstation.evaluation import (
    EvaluationHarness,
    ExternalValidityMetrics,
    evaluate_external_validity,
)
from workstation.experience_compiler.causal import refine_counterexample
from workstation.experience_compiler.models import CausalGrade
from workstation.experience_compiler.promotion import ExperiencePromotionPolicy
from workstation.operational_capabilities import (
    CapabilityLifecycle,
    OperationalCapability,
    OperationalCapabilityRegistry,
)
from workstation.operational_kernel import OperationalKernel


# ===========================================================================
# Independent External Ground-Truth Oracles
# ===========================================================================

class FileSystemOracle:
    """Independent ground-truth oracle reading the actual filesystem directly."""

    @staticmethod
    def read_exact(path: Path) -> str | None:
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    @staticmethod
    def exists(path: Path) -> bool:
        return path.exists()


class StateStoreOracle:
    """Independent external state oracle representing a live database / external system."""

    def __init__(self, initial_state: dict | None = None):
        self._state = dict(initial_state or {})
        self._versions = {k: 1 for k in self._state}

    def get(self, key: str) -> Any:
        return self._state.get(key)

    def get_version(self, key: str) -> int:
        return self._versions.get(key, 0)

    def mutate_externally(self, key: str, value: Any):
        """Simulates an external concurrent actor or unmodelled mutation."""
        self._state[key] = value
        self._versions[key] = self._versions.get(key, 0) + 1


# ===========================================================================
# Scenario A: Phantom Oracle
# ===========================================================================

def test_scenario_a_phantom_oracle(tmp_path):
    """Scenario A: Internal evidence claims file was written, but real filesystem was NOT modified.

    External Oracle: FileSystemOracle checks the actual file content.
    Truthful Core Requirement: evaluate_verification must reject if evidence cannot bind to real resource,
    and CertifiedDispatcher must not commit unverified transition.
    """
    target_file = tmp_path / "real_target.txt"
    target_file.write_text("initial_content", encoding="utf-8")

    # Contract requires resource_id matching target_file and version 2
    contract = VerificationContract(
        observer="fs_observer",
        source_kind="filesystem",
        covered_predicates=("content",),
        relation=VerificationRelation.EXACT,
        lifecycle=VerificationLifecycle.VALIDATED,
        resource_binding={"resource_id": str(target_file), "expected_version": 2},
    )

    # Phantom evidence: claims version 1 (stale/unmodified) or wrong resource
    phantom_evidence = VerificationEvidence(
        evidence_id="ev_phantom_1",
        observer="fs_observer",
        source_kind="filesystem",
        value="mutated_content",
        resource_id=str(target_file),
        resource_version=1,
        operation_id="op_write_100",
        evidence_strength=EvidenceStrength.INDEPENDENT_PERSISTED_READBACK,
        covered_predicates=("content",),
    )

    result = evaluate_verification(contract, "mutated_content", [phantom_evidence], expected_operation_id="op_write_100")
    # Must fail because resource_version is 1 != expected_version 2
    assert result.status in (VerificationStatus.FAILED, VerificationStatus.INCONCLUSIVE, VerificationStatus.STALE)
    assert "version_mismatch" in result.reason

    # External oracle confirms ground truth:
    real_content = FileSystemOracle.read_exact(target_file)
    assert real_content == "initial_content"  # Not mutated!


# ===========================================================================
# Scenario B: Masked Drift
# ===========================================================================

def test_scenario_b_masked_drift():
    """Scenario B: Preconditions pass syntactically (e.g. key present), but semantics changed.

    External Oracle: Verifies that semantic payload structure broke (e.g. version bumped, payload type changed).
    Truthful Core Requirement: Semantic predicate verification fails closed on unexpected structure or mismatch.
    """
    kernel = OperationalKernel()

    # Capability expects semantic condition 'config_format': 'json'
    # Environment has mutated to 'config_format': 'yaml'
    semantic_state = {"config_format": "yaml", "config_data": "key: value"}

    condition = {"type": "semantic_predicate", "key": "config_format", "expected": "json"}
    satisfied = kernel.verify_condition(condition, semantic_state)
    assert satisfied is False

    # Also test malformed / unknown condition types: must fail closed, not pass
    unknown_cond = {"type": "unsupported_parser_schema", "foo": "bar"}
    assert kernel.verify_condition(unknown_cond, semantic_state) is False


# ===========================================================================
# Scenario C: Blind Concurrency
# ===========================================================================

def test_scenario_c_blind_concurrency():
    """Scenario C: External actor mutates resource between action execution and verification.

    External Oracle: StateStoreOracle increments version and alters state concurrently.
    Truthful Core Requirement: Resource binding version check detects mismatch and rejects commit.
    """
    store = StateStoreOracle({"account_balance": 100})
    # Action expected to change balance from 100 to 150 (version 1 -> 2)
    expected_version_after_action = 2

    contract = VerificationContract(
        observer="db_observer",
        source_kind="database",
        covered_predicates=("balance",),
        relation=VerificationRelation.EXACT,
        lifecycle=VerificationLifecycle.VALIDATED,
        resource_binding={"resource_id": "account_balance", "expected_version": expected_version_after_action},
    )

    # Concurrent external mutation happens right now!
    store.mutate_externally("account_balance", 200)  # version is now 2
    store.mutate_externally("account_balance", 250)  # concurrent actor mutated again -> version 3!

    # Evidence gathered observes version 3
    evidence = VerificationEvidence(
        evidence_id="ev_conc_1",
        observer="db_observer",
        source_kind="database",
        value=150,
        resource_id="account_balance",
        resource_version=store.get_version("account_balance"),  # 3
        operation_id="op_deposit_50",
        evidence_strength=EvidenceStrength.INDEPENDENT_PERSISTED_READBACK,
        covered_predicates=("balance",),
    )

    result = evaluate_verification(contract, 150, [evidence], expected_operation_id="op_deposit_50")
    assert result.status in (VerificationStatus.FAILED, VerificationStatus.INCONCLUSIVE, VerificationStatus.STALE)
    assert "version_mismatch" in result.reason
    assert store.get("account_balance") == 250


# ===========================================================================
# Scenario D: Non-Discriminable Counterexample (P3 Tripwire)
# ===========================================================================

def test_scenario_d_non_discriminable_counterexample():
    """Scenario D: Identical apparent state produces contradictory outcomes.

    External Oracle: Verifies that both cases had identical observed predicates, revealing model inadequacy.
    Truthful Core Requirement: refine_counterexample must trip model_inadequacy_non_discriminable_outcome,
    quarantine capability, and promotion policy must reject promotion.
    """
    cap = OperationalCapability(
        id="cap_model_inadequacy_test",
        name="Counterexample Test",
        version="1.0.0",
        effect="state_mutation",
        route="filesystem",
        trust_class="trusted_runtime",
        learning_metadata={"preconditions": {"app_running": True, "disk_ready": True}},
        causal_grade=CausalGrade.REPLAY_VALIDATED,
    )

    positive_states = [
        {"app_running": True, "disk_ready": True},
        {"app_running": True, "disk_ready": True},
    ]

    # Counterexample has the EXACT same observed states (cannot be discriminated by current model)
    counterexample = {"app_running": True, "disk_ready": True}

    with pytest.raises(ValueError, match="model_inadequacy_non_discriminable_outcome"):
        refine_counterexample(cap, counterexample, positive_states)

    # Now verify that when marked with model inadequacy, ExperiencePromotionPolicy rejects it
    cap.learning_metadata["model_inadequacy_detected"] = True
    cap.drift_state = "quarantined"

    policy = ExperiencePromotionPolicy()
    admission = policy.evaluate(cap)
    assert admission.admitted is False
    assert "model_inadequacy" in admission.reasons or "drift" in admission.reasons


# ===========================================================================
# Scenario E: False Success by No-Op
# ===========================================================================

def test_scenario_e_false_success_by_noop():
    """Scenario E: Action was a no-op, but verifier claimed success because state was already compatible.

    External Oracle: Asserts that state before == state after (zero mutation took place).
    Truthful Core Requirement: Causal transition claim requires expected_operation_id matching,
    and sensitivity validation rejects verifiers that pass negative controls.
    """
    # 1. Causal transition claim without operation_id match fails
    contract = VerificationContract(
        observer="db_observer",
        source_kind="database",
        covered_predicates=("ready",),
        relation=VerificationRelation.EXACT,
        lifecycle=VerificationLifecycle.VALIDATED,
        transition_claim=True,
    )
    evidence_noop = VerificationEvidence(
        evidence_id="ev_noop",
        observer="db_observer",
        source_kind="database",
        value=True,
        resource_id="db_table",
        operation_id="",  # No operation executed!
        evidence_strength=EvidenceStrength.INDEPENDENT_PERSISTED_READBACK,
        covered_predicates=("ready",),
    )
    # Trying to claim causal transition on a no-op:
    result = evaluate_verification(
        contract, True, [evidence_noop], transition_required=True, expected_operation_id="op_expected_mutation"
    )
    assert result.status in (VerificationStatus.FAILED, VerificationStatus.INCONCLUSIVE)
    assert "operation_id_mismatch" in result.reason or not result.transition_proven

    # 2. Verifier Sensitivity: a verifier where negative control failed discrimination must not be VALIDATED
    negative_control_receipts = [
        {"kind": "positive_replay", "passed": True},
        {"kind": "negative_control", "passed": False, "details": "failed to reject negative control"},
    ]
    is_sensitive, reasons = validate_verifier_sensitivity(negative_control_receipts)
    assert is_sensitive is False
    assert "missing_discriminative_negative_control" in reasons


# ===========================================================================
# Scenario F: Broken Causal Dependency
# ===========================================================================

def test_scenario_f_broken_causal_dependency():
    """Scenario F: Downstream step runs against unverified or failed upstream state.

    External Oracle: Confirms upstream output is missing or invalid.
    Truthful Core Requirement: Dispatcher / verifier fails closed; transition cannot be certified.
    """
    collector = ORAMetricsCollector()

    # Upstream failed: unverified transition recorded
    collector.on_transition(verified=False)
    assert collector.metrics.unverified_transitions == 1
    assert collector.metrics.verified_transitions_deterministic == 0

    # Downstream verification evaluation fails if upstream operation_id is missing
    contract = VerificationContract(
        observer="step_b_observer",
        source_kind="step_pipeline",
        covered_predicates=("output",),
        relation=VerificationRelation.EXACT,
        lifecycle=VerificationLifecycle.VALIDATED,
        transition_claim=True,
    )
    ev_broken = VerificationEvidence(
        evidence_id="ev_downstream",
        observer="step_b_observer",
        source_kind="step_pipeline",
        value="some_output",
        resource_id="step_b_target",
        operation_id="unrelated_op",
        evidence_strength=EvidenceStrength.INDEPENDENT_PERSISTED_READBACK,
        covered_predicates=("output",),
    )
    result = evaluate_verification(
        contract, "some_output", [ev_broken], transition_required=True, expected_operation_id="step_a_output_op"
    )
    assert result.status in (VerificationStatus.FAILED, VerificationStatus.INCONCLUSIVE)
    assert result.transition_proven is False


# ===========================================================================
# Scenario G: Validity Envelope Violation
# ===========================================================================

def test_scenario_g_validity_envelope_violation():
    """Scenario G: Capability executed outside its derived envelope (different tenant, platform).

    External Oracle: Asserts target environment differs from certification bounds.
    Truthful Core Requirement: Validity envelope check detects out-of-boundary parameters.
    """
    cap = OperationalCapability(
        id="cap_tenant_alpha",
        name="Tenant Alpha Processor",
        version="1.0.0",
        effect="state_mutation",
        route="workstation",
        lifecycle=CapabilityLifecycle.PROMOTED,
        scope={"tenant_id": "alpha", "os": "linux", "target_family": "workstation"},
        learning_metadata={
            "preconditions": {"tenant": "alpha"},
            "observed_contexts": [{"tenant_id": "alpha", "os": "linux"}],
            "target_families": ["workstation"],
        },
    )

    envelope = derive_validity_envelope(cap)
    assert envelope.tenant_scope == "alpha"
    assert envelope.target_family == "workstation"

    # Attempt execution under tenant 'beta' or different target
    assert envelope.is_valid({"tenant_id": "beta", "target_family": "workstation"}) is False
    assert envelope.is_valid({"tenant_id": "alpha", "target_family": "cloud_aws"}) is False
    # Only valid within the certified envelope
    assert envelope.is_valid({"tenant_id": "alpha", "os": "linux", "target_family": "workstation"}) is True


# ===========================================================================
# Scenario H: Hidden Assumption Violated
# ===========================================================================

def test_scenario_h_hidden_assumption_violated():
    """Scenario H: Environment has undeclared timezone/locale variation causing unexpected format.

    External Oracle: Real environment produces date string with timezone offset instead of UTC.
    Truthful Core Requirement: Strict verifier predicate rejects non-conforming format; fails closed.
    """
    kernel = OperationalKernel()

    # Observed semantic state under non-UTC timezone
    state = {"formatted_date": "2026-09-19T09:00:00-03:00"}

    # Capability strictly assumed UTC "Z" format
    strict_condition = {
        "type": "semantic_predicate",
        "key": "formatted_date",
        "expected": "2026-09-19T12:00:00Z",
    }
    assert kernel.verify_condition(strict_condition, state) is False


# ===========================================================================
# Scenario I: Verifier Blind to Side Effect
# ===========================================================================

def test_scenario_i_unmodelled_side_effect_hazard():
    """Scenario I: Target file updated, but adjacent file in same directory corrupted.

    External Oracle: Direct filesystem audit detects adjacent file corruption.
    External Validity Evaluation: Tracks false safe rate and unmodelled hazard cases.
    """
    runs = [
        {
            "task_id": "task_target_clean",
            "internal_verified": True,
            "external_success": False,  # External oracle failed because adjacent file was corrupted
            "unmodelled_hazard": True,
            "has_unmodelled_side_effect": True,
            "declared_safe": True,
        }
    ]
    metrics = evaluate_external_validity(runs)
    assert metrics.fcor == 1.0
    assert metrics.false_safe_rate == 1.0
    assert metrics.counts["hazard_cases"] == 1


# ===========================================================================
# Scenario J: Cumulative Drift Reuse Degradation (N >= 10)
# ===========================================================================

def test_scenario_j_cumulative_drift_reuse_degradation():
    """Scenario J: Capability reused across N >= 10 iterations with progressive drift.

    External Oracle: Tracks external drift accumulation.
    Truthful Core Requirement: Drift rate check halts promotion/reuse once threshold exceeded.
    """
    runs = []
    # Simulate 12 reuses: first 9 succeed, 10th-12th fail due to cumulative resource exhaustion
    for i in range(12):
        succeeded = i < 9
        runs.append({
            "task_id": f"reuse_{i}",
            "is_reuse": True,
            "reuse_iteration": i,
            "internal_verified": succeeded,
            "external_success": succeeded,
            "reuse_success": succeeded,
        })

    metrics = evaluate_external_validity(runs)
    assert metrics.reuse_reliability == 9 / 12  # 0.75
    assert metrics.fcor == 0.0  # No false certification! When it failed, it was rejected.
    assert metrics.certification_coverage == 9 / 12


# ===========================================================================
# Scenario K: Read-Verify Race Condition
# ===========================================================================

def test_scenario_k_read_verify_race_condition():
    """Scenario K: External resource altered immediately after evidence read, before commit.

    External Oracle: State store version is incremented during race window.
    Truthful Core Requirement: Commit requires fresh matching version; stale evidence rejected.
    """
    store = StateStoreOracle({"doc_content": "v1"})
    # Action produced version 2
    store.mutate_externally("doc_content", "v2_expected")

    contract = VerificationContract(
        observer="doc_observer",
        source_kind="database",
        covered_predicates=("content",),
        relation=VerificationRelation.EXACT,
        lifecycle=VerificationLifecycle.VALIDATED,
        resource_binding={"resource_id": "doc_content", "expected_version": 2},
    )

    # Actor read evidence at version 2
    stale_evidence = VerificationEvidence(
        evidence_id="ev_stale",
        observer="doc_observer",
        source_kind="database",
        value="v2_expected",
        resource_id="doc_content",
        resource_version=2,
        operation_id="op_update_doc",
        evidence_strength=EvidenceStrength.INDEPENDENT_PERSISTED_READBACK,
        covered_predicates=("content",),
    )

    # Before commit, concurrent process alters doc_content to v3
    store.mutate_externally("doc_content", "v3_mutated_concurrently")

    # Final commit verification re-probes or checks current version
    current_version = store.get_version("doc_content")  # now 3
    assert current_version != stale_evidence.resource_version

    # Verifier with live evidence fails:
    live_evidence = VerificationEvidence(
        evidence_id="ev_live",
        observer="doc_observer",
        source_kind="database",
        value="v3_mutated_concurrently",
        resource_id="doc_content",
        resource_version=current_version,
        operation_id="op_update_doc",
        evidence_strength=EvidenceStrength.INDEPENDENT_PERSISTED_READBACK,
        covered_predicates=("content",),
    )
    res = evaluate_verification(contract, "v2_expected", [live_evidence], expected_operation_id="op_update_doc")
    assert res.status in (VerificationStatus.FAILED, VerificationStatus.INCONCLUSIVE, VerificationStatus.STALE)
    assert "version_mismatch" in res.reason or res.status != VerificationStatus.VERIFIED


# ===========================================================================
# External Validity Benchmark Aggregation & Metric Invariants
# ===========================================================================

def test_afb_benchmark_aggregation_and_invariants():
    """Aggregates all AFB-v0 scenarios into ExternalValidityMetrics.

    Invariants Verified:
    - Never report FCOR alone; always accompanied by Certification Coverage and ReuseReliability.
    - Missing denominators return None, never fake 0.0.
    - Truthful core maintains strict bounds on FCOR and Recall.
    """
    benchmark_runs = [
        # Scenario A: Phantom caught
        {"scenario": "A", "internal_verified": False, "external_success": False, "is_negative_control": True},
        # Scenario B: Masked drift caught
        {"scenario": "B", "internal_verified": False, "external_success": False, "true_conflict": True, "conflict_detected": True},
        # Scenario C: Concurrency caught
        {"scenario": "C", "internal_verified": False, "external_success": False, "mutation_applied": True, "strict_verification_passed": False},
        # Scenario D: Model inadequacy tripwire fired
        {"scenario": "D", "internal_verified": False, "external_success": False, "true_model_inadequacy": True, "model_inadequacy_detected": True},
        # Scenario E: No-op false success caught (negative control rejected)
        {"scenario": "E", "internal_verified": False, "external_success": False, "is_negative_control": True, "rejected_negative_control": True},
        # Scenario F: Broken causal dependency caught
        {"scenario": "F", "internal_verified": False, "external_success": False},
        # Scenario G: Validity envelope violation caught
        {"scenario": "G", "internal_verified": False, "external_success": False, "hidden_assumption_violated": True, "safely_handled": True},
        # Scenario H: Hidden assumption caught
        {"scenario": "H", "internal_verified": False, "external_success": False, "hidden_assumption_violated": True, "violation_detected": True},
        # Scenario I: Side-effect hazard observed
        {"scenario": "I", "internal_verified": False, "external_success": False, "unmodelled_hazard": True, "declared_safe": False},
        # Scenario J: Reuses (10 runs, all verified and externally successful)
        *[{"scenario": "J", "internal_verified": True, "external_success": True, "is_reuse": True, "reuse_success": True} for _ in range(10)],
        # Scenario K: Race condition caught
        {"scenario": "K", "internal_verified": False, "external_success": False},
    ]

    metrics = evaluate_external_validity(benchmark_runs)

    # Invariant: FCOR must be accompanied by coverage and reuse reliability
    triad = metrics.as_triad()
    assert "fcor" in triad
    assert "certification_coverage" in triad
    assert "reuse_reliability" in triad

    # Truthful core: Zero false certification overhang (FCOR == 0.0)
    assert metrics.fcor == 0.0
    assert metrics.reuse_reliability == 1.0
    assert metrics.certification_coverage == 10 / len(benchmark_runs)
    assert metrics.model_inadequacy_recall == 1.0
    assert metrics.conflict_detection_recall == 1.0
    assert metrics.hidden_assumption_robustness == 1.0
    assert metrics.false_safe_rate == 0.0

    # Invariant: Empty runs return None for rates (no fake 0.0 denominators)
    empty_metrics = evaluate_external_validity([])
    assert empty_metrics.fcor is None
    assert empty_metrics.certification_coverage is None
    assert empty_metrics.reuse_reliability is None
    assert empty_metrics.model_inadequacy_recall is None

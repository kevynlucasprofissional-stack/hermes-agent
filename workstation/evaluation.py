"""Model-independent runtime evaluation and regression-budget contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
import os
from typing import Any, Callable

from workstation.contracts import ExecutionEventKind
from workstation.journal import ExecutionJournal


@dataclass(slots=True)
class EvaluationCase:
    name: str
    input: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationResult:
    case_name: str
    success: bool
    actions: int
    latency_seconds: float
    tokens: int = 0
    cost_usd: float = 0.0
    safety_ok: bool = True
    model_independent: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RegressionBudget:
    max_action_increase: int = 0
    max_latency_increase: float = 0.0
    max_token_increase: int = 0
    max_cost_increase: float = 0.0


@dataclass(slots=True)
class RegressionComparison:
    accepted: bool
    reasons: list[str] = field(default_factory=list)
    model_independent: bool = True


class EvaluationHarness:
    def __init__(self, journal: ExecutionJournal | None = None) -> None:
        self.journal = journal

    def external_validity_metrics(self, runs: list[dict[str, Any]]) -> ExternalValidityMetrics:
        """Compute external validity metrics against independent ground truth."""
        return evaluate_external_validity(runs)

    def outcome_metrics(self, runs: list[dict[str, Any]]) -> dict[str, Any]:
        """Local AVCR projection. Missing provenance is never production data."""
        eligible = [r for r in runs if r.get("environment") in {"production", "dogfood"}
                    and r.get("eligible_delegated") is True]
        verified = [r for r in eligible if r.get("outcome_status") == "verified_completed"
                    and r.get("acceptance_approved") is True]
        autonomous = [r for r in verified if not r.get("unplanned_human_rescues")]
        count, complete = len(eligible), len(verified)
        ratio = lambda numerator, denominator: numerator / denominator if denominator and numerator is not None else None
        known_sum = lambda key: sum(r[key] for r in eligible) if eligible and all(r.get(key) is not None for r in eligible) else None
        recoveries = [r for r in eligible if r.get("recovery_attempted") is True]
        efficiency = self.efficiency_metrics(eligible)
        return {
            **efficiency,
            "eligible_delegated_tasks": count, "verified_completion": complete,
            "AVCR": ratio(len(autonomous), count),
            "false_completion_rate": ratio(sum(r.get("done") is True and r not in verified for r in eligible), count),
            "zombie_running_rate": ratio(sum(r.get("running") is True and not r.get("live_handles") for r in eligible), count),
            "planned_handoff_rate": ratio(sum(bool(r.get("planned_handoffs")) for r in eligible), count),
            "unplanned_rescue_rate": ratio(sum(bool(r.get("unplanned_human_rescues")) for r in eligible), count),
            "systemic_failure_amplification": sum(r.get("systemic_failure_amplification", 0) for r in eligible),
            "tokens_per_verified_task": ratio(known_sum("tokens"), complete),
            "cost_per_verified_task": ratio(known_sum("cost_usd"), complete),
            "time_per_verified_task": ratio(known_sum("duration_seconds"), complete),
            "tool_calls_per_verified_task": ratio(known_sum("tool_calls"), complete),
            "recovery_success_rate": ratio(sum(r.get("recovery_success") is True for r in recoveries), len(recoveries)),
            "evidence_coverage": ratio(sum(r.get("verified_evidence_count", 0) for r in eligible), sum(r.get("required_evidence_count", 0) for r in eligible)),
            **{key: sum(r.get(key, 0) for r in eligible) for key in (
                "model_interventions", "tool_calls", "no_progress_calls", "duplicate_calls_blocked", "routine_candidate")},
            "routine_reuse": sum(r.get("routine_reuse", 0) for r in eligible),
            "routine_savings": sum(r.get("routine_savings", 0) for r in eligible),
        }

    def efficiency_metrics(self, runs: list[dict[str, Any]]) -> dict[str, Any]:
        """Explicit sampled denominators; absent observations remain unknown.

        Obstruction requires a caller-confirmed safe/authorized eligible path,
        independently of whether the harness allowed that path to run.
        """
        verified = [r for r in runs if r.get('outcome_status') == 'verified_completed' and r.get('acceptance_approved') is True]
        ratio = lambda n, d: n / d if n is not None and d else None
        total = lambda key: sum(r[key] for r in runs) if runs and all(isinstance(r.get(key), (int, float)) for r in runs) else None
        known_rate = lambda key: ratio(sum(bool(r[key]) for r in runs), len(runs)) if runs and all(key in r and r[key] is not None for r in runs) else None
        eligible = [r for r in runs if r.get('safe_authorized_eligible') is True]
        blocked = sum(r['harness_policy_blocked'] is True for r in eligible) if eligible and all(isinstance(r.get('harness_policy_blocked'), bool) for r in eligible) else None
        discovery, replay = total('discovery_cost'), total('replay_cost')
        return {
            'llm_calls_per_verified_outcome': ratio(total('llm_calls'), len(verified)),
            'tokens_per_verified_outcome': ratio(total('tokens'), len(verified)),
            'tool_calls_per_verified_outcome': ratio(total('tool_calls'), len(verified)),
            'context_reconstruction_overhead': total('context_reconstruction_overhead'),
            'deterministic_replay_rate': known_rate('deterministic_replay'),
            'routine_reuse_rate': known_rate('routine_reuse'), 'drift_rate': known_rate('drift'),
            'human_rescue_rate': known_rate('unplanned_human_rescues'),
            'discovery_cost': discovery, 'replay_cost': replay,
            'estimated_savings': discovery - replay if discovery is not None and replay is not None else None,
            'guardrail_obstruction_eligible_tasks': len(eligible),
            'guardrail_obstruction_rate': ratio(blocked, len(eligible)),
        }

    def run(self, case: EvaluationCase, executor: Callable[[Any], dict[str, Any]]) -> EvaluationResult:
        started = time.monotonic()
        try:
            result = executor(case.input)
            elapsed = time.monotonic() - started
            evaluation = EvaluationResult(
                case_name=case.name,
                success=bool(result.get("success", False)),
                actions=max(0, int(result.get("actions", 0))),
                latency_seconds=float(result.get("latency_seconds", elapsed)),
                tokens=max(0, int(result.get("tokens", 0))),
                cost_usd=max(0.0, float(result.get("cost_usd", 0.0))),
                safety_ok=bool(result.get("safety_ok", True)),
                metadata=dict(result.get("metadata", {})),
            )
            evaluation.metadata.update({k: case.metadata[k] for k in (
                "environment", "build_sha", "workstation_version", "test_case_id", "evaluation_run_id",
                "task_id", "session_id") if k in case.metadata})
            evaluation.metadata.setdefault("environment", "test" if os.environ.get("HERMES_TEST_ISOLATION") else "benchmark")
            self._record(evaluation)
            return evaluation
        except Exception as exc:
            evaluation = EvaluationResult(case.name, False, 0, time.monotonic() - started, metadata={"error": str(exc)})
            self._record(evaluation)
            return evaluation

    def _record(self, result: EvaluationResult) -> None:
        if self.journal is not None:
            self.journal.record(
                ExecutionEventKind.ACTION,
                f"evaluation:{result.case_name}",
                metadata={
                    "success": result.success,
                    "actions": result.actions,
                    "latency_seconds": result.latency_seconds,
                    "tokens": result.tokens,
                    "cost_usd": result.cost_usd,
                    "safety_ok": result.safety_ok,
                    **result.metadata,
                },
            )

    def compare(
        self,
        baseline: EvaluationResult,
        candidate: EvaluationResult,
        budget: RegressionBudget,
    ) -> RegressionComparison:
        reasons: list[str] = []
        if not candidate.success:
            reasons.append("candidate failed")
        if not candidate.safety_ok:
            reasons.append("candidate safety guard failed")
        if candidate.actions - baseline.actions > budget.max_action_increase:
            reasons.append("action regression budget exceeded")
        if candidate.latency_seconds - baseline.latency_seconds > budget.max_latency_increase:
            reasons.append("latency regression budget exceeded")
        if candidate.tokens - baseline.tokens > budget.max_token_increase:
            reasons.append("token regression budget exceeded")
        if candidate.cost_usd - baseline.cost_usd > budget.max_cost_increase:
            reasons.append("cost regression budget exceeded")
        return RegressionComparison(not reasons, reasons)


@dataclass(slots=True)
class SoakResult:
    iterations: int
    failures: int
    success_rate: float
    total_actions: int
    total_latency_seconds: float
    errors: list[str] = field(default_factory=list)
    completed_iterations: int = 0
    duration_seconds: float = 0.0
    timed_out: bool = False


class SoakRunner:
    def run(
        self,
        iterations: int,
        executor: Callable[[int], dict[str, Any]],
        *,
        max_duration_seconds: float | None = None,
    ) -> SoakResult:
        if max_duration_seconds is not None and max_duration_seconds < 0:
            raise ValueError("max_duration_seconds must be non-negative")
        started = time.monotonic()
        failures = 0
        actions = 0
        latency = 0.0
        errors: list[str] = []
        completed = 0
        timed_out = False
        for index in range(max(0, iterations)):
            if max_duration_seconds is not None and time.monotonic() - started >= max_duration_seconds:
                timed_out = True
                break
            try:
                result = executor(index)
                if not bool(result.get("success", False)):
                    failures += 1
                actions += max(0, int(result.get("actions", 0)))
                latency += max(0.0, float(result.get("latency_seconds", 0.0)))
            except Exception as exc:
                failures += 1
                errors.append(str(exc))
            completed += 1
        count = max(0, iterations)
        if max_duration_seconds is not None and not timed_out and time.monotonic() - started >= max_duration_seconds:
            timed_out = completed < count
        return SoakResult(
            count,
            failures,
            (completed - failures) / completed if completed else 1.0,
            actions,
            latency,
            errors,
            completed,
            max(0.0, time.monotonic() - started),
            timed_out,
        )

    def run_for_duration(
        self,
        duration_seconds: float,
        executor: Callable[[int], dict[str, Any]],
        *,
        max_iterations: int = 1_000_000,
    ) -> SoakResult:
        """Run a bounded duration soak while retaining a hard iteration cap."""

        if max_iterations < 0:
            raise ValueError("max_iterations must be non-negative")
        return self.run(
            max_iterations,
            executor,
            max_duration_seconds=duration_seconds,
        )


@dataclass(frozen=True)
class ExternalValidityMetrics:
    total_runs: int = 0
    internal_verified_count: int = 0
    external_success_count: int = 0

    # Core Triad (Never report FCOR in isolation)
    fcor: float | None = None
    certification_coverage: float | None = None
    reuse_reliability: float | None = None

    # Concordance & Validity
    external_correctness: float | None = None
    oracle_agreement_rate: float | None = None
    false_abstention_rate: float | None = None

    # Robustness & Model Limits
    hidden_assumption_robustness: float | None = None
    model_inadequacy_recall: float | None = None
    false_safe_rate: float | None = None
    unsafe_mutation_rate: float | None = None
    conflict_detection_recall: float | None = None
    recovery_correctness: float | None = None
    verifier_sensitivity: float | None = None

    # Amortization
    ora_ratio: float | None = None

    # Counts dictionary preserving exact denominator provenance
    counts: dict[str, int] = field(default_factory=dict)

    def as_triad(self) -> dict[str, float | None]:
        """Core triad: FCOR must always be accompanied by coverage and reuse reliability."""
        return {
            "fcor": self.fcor,
            "certification_coverage": self.certification_coverage,
            "reuse_reliability": self.reuse_reliability,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "internal_verified_count": self.internal_verified_count,
            "external_success_count": self.external_success_count,
            "fcor": self.fcor,
            "certification_coverage": self.certification_coverage,
            "reuse_reliability": self.reuse_reliability,
            "external_correctness": self.external_correctness,
            "oracle_agreement_rate": self.oracle_agreement_rate,
            "false_abstention_rate": self.false_abstention_rate,
            "hidden_assumption_robustness": self.hidden_assumption_robustness,
            "model_inadequacy_recall": self.model_inadequacy_recall,
            "false_safe_rate": self.false_safe_rate,
            "unsafe_mutation_rate": self.unsafe_mutation_rate,
            "conflict_detection_recall": self.conflict_detection_recall,
            "recovery_correctness": self.recovery_correctness,
            "verifier_sensitivity": self.verifier_sensitivity,
            "ora_ratio": self.ora_ratio,
            "counts": dict(self.counts),
        }


def evaluate_external_validity(runs: list[dict[str, Any]]) -> ExternalValidityMetrics:
    """Evaluate external validity metrics against independent ground truth.

    Invariants:
    - Never invent denominators: missing observations return None, not 0.0.
    - FCOR is strictly defined as false certifications over total certifications.
    - Must preserve observational provenance counts.
    """
    if not runs:
        return ExternalValidityMetrics()

    def ratio(n: int | float | None, d: int | float | None) -> float | None:
        if d is None or d == 0 or n is None:
            return None
        return n / d

    total_runs = len(runs)

    def is_internally_verified(r: dict[str, Any]) -> bool | None:
        if "internal_verified" in r:
            return bool(r["internal_verified"])
        if "verified" in r:
            return bool(r["verified"])
        if "internal_status" in r:
            return r["internal_status"] in ("VERIFIED", "COMMITTED")
        if "status" in r and r["status"] in ("VERIFIED", "COMMITTED", "FAILED", "INCONCLUSIVE", "CONFLICT"):
            return r["status"] in ("VERIFIED", "COMMITTED")
        return None

    def is_externally_successful(r: dict[str, Any]) -> bool | None:
        if "external_success" in r:
            return bool(r["external_success"])
        if "external_oracle_success" in r:
            return bool(r["external_oracle_success"])
        return None

    int_ver_runs = [r for r in runs if is_internally_verified(r) is True]
    ext_succ_runs = [r for r in runs if is_externally_successful(r) is True]

    # FCOR: False Certification Overhang Rate = (Internal Verified & External Failed) / Internal Verified
    fcor_num = sum(1 for r in int_ver_runs if is_externally_successful(r) is False)
    fcor = ratio(fcor_num, len(int_ver_runs))

    # Certification coverage = Internal Verified / Total Runs
    cert_coverage = ratio(len(int_ver_runs), total_runs)

    # External correctness = External Success / Total Runs
    ext_correctness = ratio(len(ext_succ_runs), total_runs)

    # Oracle agreement rate: where both are observed
    comparable = [r for r in runs if is_internally_verified(r) is not None and is_externally_successful(r) is not None]
    agreed = sum(1 for r in comparable if is_internally_verified(r) == is_externally_successful(r))
    agreement_rate = ratio(agreed, len(comparable))

    # False abstention: External Success is True but Internal Verified is False
    ext_succ_comparable = [r for r in comparable if is_externally_successful(r) is True]
    false_abstentions = sum(1 for r in ext_succ_comparable if is_internally_verified(r) is False)
    false_abstention_rate = ratio(false_abstentions, len(ext_succ_comparable))

    # Hidden assumption robustness
    hidden_viol_runs = [r for r in runs if r.get("hidden_assumption_violated") is True]
    hidden_safe = sum(
        1 for r in hidden_viol_runs
        if r.get("safely_handled") is True
        or r.get("violation_detected") is True
        or (is_internally_verified(r) is False and not r.get("state_corrupted", False))
    )
    hidden_robustness = ratio(hidden_safe, len(hidden_viol_runs))

    # Model inadequacy recall
    true_inadequacy_runs = [r for r in runs if r.get("true_model_inadequacy") is True]
    inadequacy_detected = sum(1 for r in true_inadequacy_runs if r.get("model_inadequacy_detected") is True)
    inadequacy_recall = ratio(inadequacy_detected, len(true_inadequacy_runs))

    # False safe rate
    hazard_runs = [r for r in runs if r.get("unmodelled_hazard") is True or r.get("has_unmodelled_side_effect") is True]
    false_safes = sum(1 for r in hazard_runs if r.get("declared_safe") is True or is_internally_verified(r) is True)
    false_safe_rate = ratio(false_safes, len(hazard_runs))

    # Unsafe mutation rate
    mutation_runs = [r for r in runs if r.get("mutation_applied") is True]
    unsafe_mutations = sum(1 for r in mutation_runs if r.get("strict_verification_passed") is False or r.get("unsafe_mutation") is True)
    unsafe_mutation_rate = ratio(unsafe_mutations, len(mutation_runs))

    # Conflict detection recall
    conflict_runs = [r for r in runs if r.get("true_conflict") is True or r.get("is_conflict") is True]
    conflicts_detected = sum(1 for r in conflict_runs if r.get("conflict_detected") is True or r.get("internal_status") == "CONFLICT")
    conflict_recall = ratio(conflicts_detected, len(conflict_runs))

    # Recovery correctness
    recovery_runs = [r for r in runs if r.get("recovery_attempted") is True]
    recovery_succ = sum(
        1 for r in recovery_runs
        if r.get("recovery_external_success") is True or (is_externally_successful(r) is True and r.get("recovery_succeeded", True))
    )
    recovery_correctness = ratio(recovery_succ, len(recovery_runs))

    # Verifier sensitivity
    neg_control_runs = [r for r in runs if r.get("is_negative_control") is True]
    neg_rejected = sum(1 for r in neg_control_runs if is_internally_verified(r) is False or r.get("rejected_negative_control") is True)
    verifier_sensitivity = ratio(neg_rejected, len(neg_control_runs))

    # Reuse reliability (N)
    reuse_runs = [r for r in runs if r.get("is_reuse") is True or r.get("reuse_iteration", 0) > 0]
    reuse_succ = sum(1 for r in reuse_runs if r.get("reuse_success") is True or (is_externally_successful(r) is True and is_internally_verified(r) is True))
    reuse_reliability = ratio(reuse_succ, len(reuse_runs))

    # ORA ratio
    ora_runs_det = sum(r.get("deterministic_transitions", 0) for r in runs if "deterministic_transitions" in r)
    ora_runs_rsn = sum(r.get("reasoned_transitions", 0) for r in runs if "reasoned_transitions" in r)
    ora_total = ora_runs_det + ora_runs_rsn
    ora_ratio = ratio(ora_runs_det, ora_total) if ora_total > 0 else None

    counts = {
        "total_runs": total_runs,
        "internal_verified": len(int_ver_runs),
        "external_success": len(ext_succ_runs),
        "fcor_numerator": fcor_num,
        "comparable_runs": len(comparable),
        "hidden_assumption_violations": len(hidden_viol_runs),
        "true_model_inadequacy_cases": len(true_inadequacy_runs),
        "hazard_cases": len(hazard_runs),
        "mutations_applied": len(mutation_runs),
        "conflict_cases": len(conflict_runs),
        "recoveries_attempted": len(recovery_runs),
        "negative_controls": len(neg_control_runs),
        "reuse_runs": len(reuse_runs),
    }

    return ExternalValidityMetrics(
        total_runs=total_runs,
        internal_verified_count=len(int_ver_runs),
        external_success_count=len(ext_succ_runs),
        fcor=fcor,
        certification_coverage=cert_coverage,
        reuse_reliability=reuse_reliability,
        external_correctness=ext_correctness,
        oracle_agreement_rate=agreement_rate,
        false_abstention_rate=false_abstention_rate,
        hidden_assumption_robustness=hidden_robustness,
        model_inadequacy_recall=inadequacy_recall,
        false_safe_rate=false_safe_rate,
        unsafe_mutation_rate=unsafe_mutation_rate,
        conflict_detection_recall=conflict_recall,
        recovery_correctness=recovery_correctness,
        verifier_sensitivity=verifier_sensitivity,
        ora_ratio=ora_ratio,
        counts=counts,
    )


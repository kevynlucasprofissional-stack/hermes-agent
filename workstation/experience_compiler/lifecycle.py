"""Experience validation, controlled replay, and promotion lifecycle coordinator.

Product owner for orchestrating candidate validation without modifying live user state.
"""
from __future__ import annotations

import logging
import threading
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from workstation.artifacts import ArtifactStore
from workstation.control_plane.verification import (
    VerificationContract,
    VerificationEvidence,
    VerificationLifecycle,
    VerificationStatus,
    evaluate_verification,
    validate_verifier_candidate,
    validate_verifier_sensitivity,
)
from workstation.execution_policy import EvidenceStrength
from workstation.experience_compiler.causal import (
    SafeEnvironment,
    controlled_replay,
)
from workstation.experience_compiler.compiler import ExperienceCompiler
from workstation.experience_compiler.models import CausalGrade
from workstation.experience_compiler.promotion import (
    ExperiencePromotionPolicy,
    PromotionAdmission,
    derive_formal_contract,
)
from workstation.operational_capabilities import (
    CapabilityLifecycle,
    OperationalCapability,
    OperationalCapabilityRegistry,
)
from workstation.recipes import digest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CoordinatorCycleResult:
    candidate_id: str
    action: str  # "promoted", "held_as_candidate", "skipped", "validation_failed"
    admitted: bool
    reasons: Tuple[str, ...]
    capability: Optional[OperationalCapability] = None


@dataclass
class ValidationEnvironmentProvider:
    """Optional product or test seam providing safe evaluation and replay contexts."""
    verifier_evaluator: Optional[Callable[[OperationalCapability, VerificationContract, str, str], Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]]] = None
    replay_runner_factory: Optional[Callable[[OperationalCapability, SafeEnvironment], Callable[[list, float], dict]]] = None
    safe_env_factory: Optional[Callable[[OperationalCapability], SafeEnvironment]] = None


_ACTIVE_VALIDATION_PROVIDER: Optional[ValidationEnvironmentProvider] = None


def register_validation_environment_provider(provider: Optional[ValidationEnvironmentProvider]) -> None:
    """Register an active validation environment provider for product-owned lifecycle."""
    global _ACTIVE_VALIDATION_PROVIDER
    _ACTIVE_VALIDATION_PROVIDER = provider


def get_validation_environment_provider() -> Optional[ValidationEnvironmentProvider]:
    """Retrieve the currently active validation environment provider if any."""
    return _ACTIVE_VALIDATION_PROVIDER


class ExperienceValidationPromotionCoordinator:
    """Coordinates candidate discovery -> eligibility -> verifier validation -> controlled replay -> promotion."""

    def __init__(
        self,
        registry: OperationalCapabilityRegistry,
        compiler: ExperienceCompiler,
        artifacts: Optional[ArtifactStore] = None,
        policy: Optional[ExperiencePromotionPolicy] = None,
    ):
        self.registry = registry
        self.compiler = compiler
        self.artifacts = artifacts or ArtifactStore()
        self.policy = policy or ExperiencePromotionPolicy()
        self._lock = threading.Lock()

    def discover_candidates(self) -> List[OperationalCapability]:
        """Discover candidate capabilities ready for validation evaluation."""
        if hasattr(self.compiler, "mine"):
            try:
                mined = self.compiler.mine()
                if mined:
                    return mined
            except Exception as e:
                logger.warning("ExperienceCompiler mining produced an error: %s", e)
        return [c for c in self.registry.list_capabilities() if c.lifecycle == CapabilityLifecycle.DISCOVERED]

    def coordinate_all(self, **kwargs: Any) -> List[CoordinatorCycleResult]:
        """Process all discovered candidate capabilities."""
        candidates = self.discover_candidates()
        return [self.process_candidate(c, **kwargs) for c in candidates]

    def process_candidate(
        self,
        candidate_or_id: OperationalCapability | str,
        *,
        contract_factory: Optional[Callable[[OperationalCapability], VerificationContract]] = None,
        receipts: Optional[List[Dict[str, Any]]] = None,
        negative_control_generator: Optional[Callable[[OperationalCapability, VerificationContract], Dict[str, Any]]] = None,
        replay_runner: Optional[Callable[[OperationalCapability, SafeEnvironment], Callable[[list, float], dict]]] = None,
        safe_env: Optional[SafeEnvironment] = None,
        task_id: Optional[str] = None,
        run_id: Optional[str] = None,
        journal: Optional[Any] = None,
    ) -> CoordinatorCycleResult:
        """Execute one complete validation-replay-promotion cycle for a candidate.

        Idempotent, restart-safe and fail-closed:
        - If already promoted, returns immediately.
        - Persists progression checkpoints into candidate.learning_metadata["promotion_lifecycle"].
        - Negative control never runs against user's live browser state; uses isolated/simulated state.
        - Never auto-certifies verification receipts without real owner or counterexample evaluation.
        - Fails closed if verifier or replay fails or if verification receipts are unavailable.
        """
        with self._lock:
            if isinstance(candidate_or_id, str):
                candidate = self.registry.get(candidate_or_id)
                if not candidate:
                    return CoordinatorCycleResult(
                        candidate_id=candidate_or_id,
                        action="skipped",
                        admitted=False,
                        reasons=("candidate_not_found",),
                    )
            else:
                candidate = candidate_or_id

            m = candidate.learning_metadata = candidate.learning_metadata or {}
            lifecycle_info = m.setdefault("promotion_lifecycle", {
                "version": "h080b2-v1",
                "state": "CANDIDATE",
                "validation_evidence_refs": [],
                "replay_evidence_refs": [],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

            if candidate.lifecycle == CapabilityLifecycle.PROMOTED or lifecycle_info.get("state") == "PROMOTED":
                lifecycle_info["state"] = "PROMOTED"
                return CoordinatorCycleResult(
                    candidate_id=candidate.id,
                    action="promoted",
                    admitted=True,
                    reasons=(),
                    capability=candidate,
                )

            current_stage = lifecycle_info.get("state", "CANDIDATE")
            run_ids = set(m.get("run_ids", []))

            # 1. Eligibility check & Formal Contract
            if current_stage == "CANDIDATE":
                if len(run_ids) < 2 or not m.get("parameterization_quality") or not m.get("provenance_complete"):
                    return CoordinatorCycleResult(
                        candidate_id=candidate.id,
                        action="held_as_candidate",
                        admitted=False,
                        reasons=("eligibility_criteria_unmet",),
                        capability=candidate,
                    )

                if candidate.drift_state != "healthy":
                    return CoordinatorCycleResult(
                        candidate_id=candidate.id,
                        action="held_as_candidate",
                        admitted=False,
                        reasons=(f"drift_state_{candidate.drift_state}",),
                        capability=candidate,
                    )

                if candidate.formal_contract is None:
                    fc = derive_formal_contract(candidate)
                    if fc is not None:
                        candidate.formal_contract = fc
                        candidate.family_id = f"{fc.operation_family}:{fc.target_family}"
                    else:
                        return CoordinatorCycleResult(
                            candidate_id=candidate.id,
                            action="held_as_candidate",
                            admitted=False,
                            reasons=("formal_contract_underivable",),
                            capability=candidate,
                        )

                current_stage = "VALIDATION_PENDING"
                lifecycle_info["state"] = "VALIDATION_PENDING"
                lifecycle_info["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.registry.register(candidate)

            # 2. Verifier contract validation (sensitivity: positive replay + discriminative negative control)
            contract: VerificationContract
            if contract_factory:
                contract = contract_factory(candidate)
            else:
                covered = tuple(p.fingerprint() for p in candidate.formal_contract.typed_postconditions) if candidate.formal_contract else ()
                contract = VerificationContract(
                    covered_predicates=covered,
                    effect_classes=(candidate.effect,),
                    observer="workstation.browser_session_state" if candidate.route in {"native_browser", "workstation_browser"} else "workstation.verifier",
                    source_kind="browser_local_persistence" if candidate.route in {"native_browser", "workstation_browser"} else "process_persistence",
                    minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK if candidate.route in {"native_browser", "workstation_browser"} else EvidenceStrength.TOOL_ACK_ONLY,
                    allowed_trust=("trusted_runtime",),
                    require_read_after_write=True,
                    transition_claim=True,
                )

            if current_stage not in ("VERIFIER_VALIDATED", "REPLAY_VALIDATED", "PROMOTED"):
                validation_receipts: List[Dict[str, Any]] = []
                if receipts:
                    validation_receipts = receipts
                else:
                    provider = get_validation_environment_provider()
                    candidate_task_id = task_id or (list(run_ids)[0] if run_ids else "task-coord")
                    candidate_run_id = run_id or (list(run_ids)[0] if run_ids else "run-coord")

                    if provider and provider.verifier_evaluator:
                        pos, neg = provider.verifier_evaluator(candidate, contract, candidate_task_id, candidate_run_id)
                        if pos and neg:
                            validation_receipts = [pos, neg]
                    elif negative_control_generator:
                        neg = negative_control_generator(candidate, contract)
                        if neg:
                            # A custom negative generator was supplied, but without positive empirical verification
                            # we cannot self-certify positive passed=True.
                            pass

                if not validation_receipts:
                    lifecycle_info["state"] = "VALIDATION_PENDING"
                    lifecycle_info["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self.registry.register(candidate)
                    return CoordinatorCycleResult(
                        candidate_id=candidate.id,
                        action="held_as_candidate",
                        admitted=False,
                        reasons=("verifier_receipts_unavailable",),
                        capability=candidate,
                    )

                candidate, v_reasons = self.compiler.validate_verifier(candidate, contract, validation_receipts)
                if v_reasons:
                    lifecycle_info["state"] = "VALIDATION_FAILED"
                    lifecycle_info["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self.registry.register(candidate)
                    return CoordinatorCycleResult(
                        candidate_id=candidate.id,
                        action="validation_failed",
                        admitted=False,
                        reasons=tuple(v_reasons),
                        capability=candidate,
                    )

                current_stage = "VERIFIER_VALIDATED"
                lifecycle_info["state"] = "VERIFIER_VALIDATED"
                lifecycle_info["validation_evidence_refs"] = [
                    r.get("evidence_ref") for r in validation_receipts if isinstance(r, dict) and r.get("evidence_ref")
                ]
                lifecycle_info["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.registry.register(candidate)
                if journal:
                    from workstation.contracts import ExecutionEventKind
                    journal.record(ExecutionEventKind.ACTION, 'candidate verifier validated',
                                   metadata={'capability_id': candidate.id})

            # 3. Controlled causal replay in SafeEnvironment
            if current_stage not in ("REPLAY_VALIDATED", "PROMOTED") and candidate.causal_grade < CausalGrade.REPLAY_VALIDATED:
                effective_runner = replay_runner
                provider = get_validation_environment_provider()
                env = safe_env or (provider.safe_env_factory(candidate) if provider and provider.safe_env_factory else SafeEnvironment("test_fixture", f"isolated-{candidate.id}", lambda *_args: True))
                if effective_runner is None and provider and provider.replay_runner_factory:
                    effective_runner = provider.replay_runner_factory

                if not effective_runner:
                    lifecycle_info["state"] = "VERIFIER_VALIDATED"
                    lifecycle_info["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self.registry.register(candidate)
                    return CoordinatorCycleResult(
                        candidate_id=candidate.id,
                        action="held_as_candidate",
                        admitted=False,
                        reasons=("replay_runner_unavailable",),
                        capability=candidate,
                    )

                runner = effective_runner(candidate, env)
                candidate = controlled_replay(candidate, env, runner)
                m = candidate.learning_metadata = candidate.learning_metadata or {}
                lifecycle_info = m.setdefault("promotion_lifecycle", {
                    "version": "h080b2-v1",
                    "state": current_stage,
                    "validation_evidence_refs": [],
                    "replay_evidence_refs": [],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                if candidate.causal_grade < CausalGrade.REPLAY_VALIDATED:
                    lifecycle_info["state"] = "REPLAY_FAILED"
                    lifecycle_info["updated_at"] = datetime.now(timezone.utc).isoformat()
                    self.registry.register(candidate)
                    return CoordinatorCycleResult(
                        candidate_id=candidate.id,
                        action="validation_failed",
                        admitted=False,
                        reasons=("controlled_replay_failed",),
                        capability=candidate,
                    )

                current_stage = "REPLAY_VALIDATED"
                lifecycle_info["state"] = "REPLAY_VALIDATED"
                lifecycle_info["replay_evidence_refs"] = [
                    e.get("artifact_ref") for e in (candidate.validation_evidence or [])
                    if isinstance(e, dict) and e.get("artifact_ref")
                ]
                lifecycle_info["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.registry.register(candidate)
                if journal:
                    from workstation.contracts import ExecutionEventKind
                    journal.record(ExecutionEventKind.ACTION, 'candidate controlled replay validated',
                                   metadata={'capability_id': candidate.id})

            # 4. Evaluate promotion under ExperiencePromotionPolicy
            m = candidate.learning_metadata = candidate.learning_metadata or {}
            lifecycle_info = m.setdefault("promotion_lifecycle", {
                "version": "h080b2-v1",
                "state": current_stage,
                "validation_evidence_refs": [],
                "replay_evidence_refs": [],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            lifecycle_info["state"] = "PROMOTED"
            lifecycle_info["updated_at"] = datetime.now(timezone.utc).isoformat()
            admission = self.compiler.promote(candidate)
            if admission.admitted:
                promoted = self.registry.get(candidate.id) or candidate
                if journal:
                    from workstation.contracts import ExecutionEventKind
                    journal.record(ExecutionEventKind.ACTION, 'candidate promoted under ExperiencePromotionPolicy',
                                   metadata={'capability_id': candidate.id})
                return CoordinatorCycleResult(
                    candidate_id=candidate.id,
                    action="promoted",
                    admitted=True,
                    reasons=(),
                    capability=promoted,
                )
            else:
                lifecycle_info["state"] = "PROMOTION_REJECTED"
                lifecycle_info["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.registry.register(candidate)
                return CoordinatorCycleResult(
                    candidate_id=candidate.id,
                    action="held_as_candidate",
                    admitted=False,
                    reasons=admission.reasons,
                    capability=candidate,
                )

    def _build_isolated_negative_control(
        self,
        candidate: OperationalCapability,
        contract: VerificationContract,
        task_id: str,
        run_id: str,
        *,
        passed: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """Record an isolated negative control description. Does not self-certify pass decision."""
        if passed is None:
            return None
        op_id = f"op_neg_ctrl_{digest({'id': candidate.id, 'task': task_id})[:8]}"
        wrong_ref = self.artifacts.store(
            task_id,
            f"negative_control_{op_id}.json",
            {
                "operation_id": op_id,
                "task_id": task_id,
                "run_id": run_id,
                "discriminative_condition": "mutation_withheld_or_divergent_state",
                "rejected_by": contract.observer,
            },
            schema="hermes.negative_control.v1",
        ).ref
        return {
            "kind": "negative_control",
            "phase": "validation",
            "passed": bool(passed),
            "evidence_ref": wrong_ref,
        }

    def _build_positive_validation_receipt(
        self,
        candidate: OperationalCapability,
        contract: VerificationContract,
        task_id: str,
        run_id: str,
        *,
        passed: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """Record a positive validation description. Does not self-certify pass decision."""
        if passed is None:
            return None
        op_id = f"op_pos_ctrl_{digest({'id': candidate.id, 'task': task_id})[:8]}"
        ref = self.artifacts.store(
            task_id,
            f"positive_validation_{op_id}.json",
            {
                "operation_id": op_id,
                "task_id": task_id,
                "run_id": run_id,
                "effects": candidate.learning_metadata.get("effects", {}),
                "observer": contract.observer,
            },
            schema="hermes.positive_validation.v1",
        ).ref
        return {
            "kind": "positive_replay",
            "phase": "validation",
            "passed": bool(passed),
            "evidence_ref": ref,
        }

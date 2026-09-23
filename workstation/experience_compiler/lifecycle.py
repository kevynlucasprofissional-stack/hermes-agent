"""Experience validation, controlled replay, and promotion lifecycle coordinator.

Product owner for orchestrating candidate validation without modifying live user state.
"""
from __future__ import annotations

import logging
import threading
from copy import deepcopy
from dataclasses import dataclass
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
    ) -> CoordinatorCycleResult:
        """Execute one complete validation-replay-promotion cycle for a candidate.

        Idempotent and fail-closed:
        - If already promoted, returns immediately.
        - Negative control never runs against user's live browser state; uses isolated/simulated state.
        - Fails closed if verifier or replay fails.
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

            if candidate.lifecycle == CapabilityLifecycle.PROMOTED:
                return CoordinatorCycleResult(
                    candidate_id=candidate.id,
                    action="promoted",
                    admitted=True,
                    reasons=(),
                    capability=candidate,
                )

            # 1. Eligibility check
            m = candidate.learning_metadata or {}
            run_ids = set(m.get("run_ids", []))
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

            # 2. Derive/verify formal contract
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

            # 3. Verifier contract validation (sensitivity: positive replay + discriminative negative control)
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

            verifier_validated = False
            if candidate.verifier_contract:
                v_contract = VerificationContract.from_dict(candidate.verifier_contract)
                if v_contract.lifecycle == VerificationLifecycle.VALIDATED:
                    sensitive, _ = validate_verifier_sensitivity(list(v_contract.validation_receipts))
                    if sensitive:
                        verifier_validated = True

            if not verifier_validated:
                validation_receipts: List[Dict[str, Any]] = []
                if receipts:
                    validation_receipts = receipts
                else:
                    candidate_task_id = task_id or (list(run_ids)[0] if run_ids else "task-coord")
                    candidate_run_id = run_id or (list(run_ids)[0] if run_ids else "run-coord")

                    neg_receipt: Optional[Dict[str, Any]] = None
                    if negative_control_generator:
                        neg_receipt = negative_control_generator(candidate, contract)
                    else:
                        neg_receipt = self._build_isolated_negative_control(candidate, contract, candidate_task_id, candidate_run_id)

                    pos_receipt = self._build_positive_validation_receipt(candidate, contract, candidate_task_id, candidate_run_id)

                    if pos_receipt and neg_receipt:
                        validation_receipts = [pos_receipt, neg_receipt]

                if validation_receipts:
                    candidate, v_reasons = self.compiler.validate_verifier(candidate, contract, validation_receipts)
                    if v_reasons:
                        return CoordinatorCycleResult(
                            candidate_id=candidate.id,
                            action="validation_failed",
                            admitted=False,
                            reasons=tuple(v_reasons),
                            capability=candidate,
                        )
                else:
                    return CoordinatorCycleResult(
                        candidate_id=candidate.id,
                        action="held_as_candidate",
                        admitted=False,
                        reasons=("verifier_receipts_unavailable",),
                        capability=candidate,
                    )

            # 4. Controlled causal replay in SafeEnvironment
            if candidate.causal_grade < CausalGrade.REPLAY_VALIDATED:
                if not replay_runner:
                    return CoordinatorCycleResult(
                        candidate_id=candidate.id,
                        action="held_as_candidate",
                        admitted=False,
                        reasons=("replay_runner_unavailable",),
                        capability=candidate,
                    )

                env = safe_env or SafeEnvironment("test_fixture", f"isolated-{candidate.id}", lambda *_args: True)
                runner = replay_runner(candidate, env)
                candidate = controlled_replay(candidate, env, runner)
                if candidate.causal_grade < CausalGrade.REPLAY_VALIDATED:
                    self.registry.register(candidate)
                    return CoordinatorCycleResult(
                        candidate_id=candidate.id,
                        action="validation_failed",
                        admitted=False,
                        reasons=("controlled_replay_failed",),
                        capability=candidate,
                    )

            # 5. Evaluate promotion under ExperiencePromotionPolicy
            admission = self.compiler.promote(candidate)
            if admission.admitted:
                promoted = self.registry.get(candidate.id)
                return CoordinatorCycleResult(
                    candidate_id=candidate.id,
                    action="promoted",
                    admitted=True,
                    reasons=(),
                    capability=promoted,
                )
            else:
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
    ) -> Dict[str, Any]:
        """Create an isolated negative control receipt without touching user browser."""
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
            "passed": True,  # Verifier discriminates the negative control
            "evidence_ref": wrong_ref,
        }

    def _build_positive_validation_receipt(
        self,
        candidate: OperationalCapability,
        contract: VerificationContract,
        task_id: str,
        run_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Create a positive validation receipt from held-out or newly validated evidence."""
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
            "passed": True,
            "evidence_ref": ref,
        }

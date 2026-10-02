"""Deterministic Capability Router & Proof Engine.

Enforces:
- THE LLM PROPOSES. THE ROUTER PROVES. THE POLICY AUTHORIZES. THE RUNTIME EXECUTES. THE VERIFIER CONFIRMS.
- NO VALID CERTIFICATE -> NO DISPATCH.
"""
from __future__ import annotations

from abc import ABC
from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Callable, Sequence

from workstation.contracts import AcceptanceContract, utc_now
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.verification import VerificationContract
from workstation.control_plane.intent import (
    OperationIntent, operation_intent_hash
)
from workstation.control_plane.ir import (
    AND, Effect, Predicate, effect_contained, entails, preserves_invariant
)
from workstation.control_plane.lattice import (
    AuthorityLevel, AuthorityScope, authority_covers
)
from workstation.operational_capabilities import (
    CapabilityLifecycle, OperationalCapability, OperationalCapabilityRegistry
)


class MatchState(str, Enum):
    EXACT_EXECUTABLE = "EXACT_EXECUTABLE"
    POSSIBLE_MATCH = "POSSIBLE_MATCH"
    INCOMPATIBLE = "INCOMPATIBLE"
    NEEDS_REASONING = "NEEDS_REASONING"


@dataclass
class RoutingCertificate:
    """Auditable proof certificate certifying that all proof obligations for execution hold."""

    target_match: bool = False
    inputs_bound: bool = False
    preconditions_hold: bool = False
    goal_coverage: bool = False
    effect_containment: bool = False
    invariant_preservation: bool = False
    authority_satisfied: bool = False
    policy_satisfied: bool = False
    approval_satisfied: bool = False
    verifier_available: bool = False
    evidence_strength_sufficient: bool = False
    state_fresh: bool = True
    capability_healthy: bool = False
    no_outstanding_uncertainty: bool = False
    deterministic_closure: bool = False

    intent_hash: str = ""
    semantic_state_hash: str = ""
    capability_id: str = ""
    capability_version: str = ""
    router_policy_version: str = "1.0.0"
    run_id: str | None = None
    operation_id: str | None = None
    created_at: str = field(default_factory=utc_now)

    def is_valid(self) -> bool:
        """All proof obligations must be strictly True for dispatch authorization."""
        return (
            self.target_match
            and self.inputs_bound
            and self.preconditions_hold
            and self.goal_coverage
            and self.effect_containment
            and self.invariant_preservation
            and self.authority_satisfied
            and self.policy_satisfied
            and self.approval_satisfied
            and self.verifier_available
            and self.evidence_strength_sufficient
            and self.state_fresh
            and self.capability_healthy
            and self.no_outstanding_uncertainty
            and self.deterministic_closure
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RoutingCertificate:
        return cls(**data)

    @classmethod
    def create(
        cls,
        *,
        intent_id: str = "",
        intent_hash: str = "intent-hash",
        capability_id: str = "",
        capability_version: str = "1.0.0",
        precondition_state_hash: str = "",
        semantic_state_hash: str = "",
        authority_hash: str = "",
        run_id: str | None = None,
        operation_id: str | None = None,
    ) -> RoutingCertificate:
        return cls(
            target_match=True,
            inputs_bound=True,
            preconditions_hold=True,
            goal_coverage=True,
            effect_containment=True,
            invariant_preservation=True,
            authority_satisfied=True,
            policy_satisfied=True,
            approval_satisfied=True,
            verifier_available=True,
            evidence_strength_sufficient=True,
            state_fresh=True,
            capability_healthy=True,
            no_outstanding_uncertainty=True,
            deterministic_closure=True,
            intent_hash=intent_hash,
            semantic_state_hash=semantic_state_hash or precondition_state_hash or _state_hash({}),
            capability_id=capability_id,
            capability_version=capability_version,
            run_id=run_id,
            operation_id=operation_id,
        )

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def certificate_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class RoutingDecision(ABC):
    """Abstract base for capability router decisions."""

    @property
    def is_dispatchable(self) -> bool:
        return False


@dataclass
class SatisfiedDecision(RoutingDecision):
    """Goal is already true in the observed semantic state; zero mutation required."""

    goal_satisfied: bool = True
    details: str = "Goal already satisfied in current state"


@dataclass
class ExecutableDecision(RoutingDecision):
    """Single exact compatible capability certified for deterministic execution."""

    capability: OperationalCapability
    certificate: RoutingCertificate

    @property
    def is_dispatchable(self) -> bool:
        return self.certificate.is_valid()


@dataclass
class ComposedDecision(RoutingDecision):
    """Bounded deterministic composition plan certified for execution."""

    plan: list[OperationalCapability]
    certificate: Any  # CompositionCertificate

    @property
    def is_dispatchable(self) -> bool:
        return getattr(self.certificate, "is_valid", lambda: False)()


@dataclass
class WaitDecision(RoutingDecision):
    """Missing only a future observable condition or trigger; zero LLM token waste."""

    await_condition: Any
    reason: str = "Waiting for observable event or condition"


@dataclass
class HumanDecision(RoutingDecision):
    """Human authority, confirmation, or preference is required."""

    reason: str
    scope: Any = None


@dataclass
class ReasoningDecision(RoutingDecision):
    """A genuine semantic strategy or adaptation gap remains for the model."""

    open_condition: Any = None
    attention_packet: Any = None
    requires_reconciliation: bool = False
    reason: str = ""


def revalidate_certificate(
    certificate: RoutingCertificate,
    *,
    current_intent_hash: str,
    current_state_hash: str,
    current_cap_version: str,
    run_id: str | None = None,
    has_uncertain_mutation: bool = False,
) -> bool:
    """Preflight revalidation immediately before execution.
    
    If the state, intent, capability version, or uncertainty changed, the certificate
    is invalidated and dispatch MUST NOT proceed.
    """
    if has_uncertain_mutation:
        certificate.no_outstanding_uncertainty = False
        return False
    if current_intent_hash != certificate.intent_hash:
        certificate.deterministic_closure = False
        return False
    if current_state_hash != certificate.semantic_state_hash:
        certificate.state_fresh = False
        return False
    if current_cap_version != certificate.capability_version:
        certificate.capability_healthy = False
        return False
    if run_id and certificate.run_id and run_id != certificate.run_id:
        certificate.deterministic_closure = False
        return False
    return certificate.is_valid()


def _state_hash(state: dict[str, Any]) -> str:
    try:
        raw = json.dumps(state, sort_keys=True, default=str)
    except Exception:
        raw = str(state)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class CapabilityIndex:
    """Multi-key deterministic in-memory index for fast capability retrieval."""

    def __init__(self) -> None:
        self._by_op_family: dict[str, list[OperationalCapability]] = {}
        self._by_target_family: dict[str, list[OperationalCapability]] = {}
        self._by_family_id: dict[str, list[OperationalCapability]] = {}

    def index(self, cap: OperationalCapability) -> None:
        if getattr(cap, "run_scoped", False) or (isinstance(getattr(cap, "provenance", None), dict) and cap.provenance.get("run_scoped")) or getattr(cap, "id", "").startswith("run_scoped_"):
            return
        if cap.formal_contract:
            fc = cap.formal_contract
            op_fam = fc.get("operation_family") if isinstance(fc, dict) else getattr(fc, "operation_family", "")
            tgt_fam = fc.get("target_family") if isinstance(fc, dict) else getattr(fc, "target_family", "")
            if op_fam:
                self._by_op_family.setdefault(op_fam, []).append(cap)
            if tgt_fam:
                self._by_target_family.setdefault(tgt_fam, []).append(cap)
        if cap.family_id:
            self._by_family_id.setdefault(cap.family_id, []).append(cap)
        if cap.alias_of:
            self._by_family_id.setdefault(cap.alias_of, []).append(cap)

    def candidates(
        self,
        target_family: str | None = None,
        operation_family: str | None = None,
        family_id: str | None = None,
    ) -> list[OperationalCapability]:
        found: list[OperationalCapability] = []
        if family_id and family_id in self._by_family_id:
            found.extend(self._by_family_id[family_id])
        if operation_family and operation_family in self._by_op_family:
            found.extend(self._by_op_family[operation_family])
        if target_family and target_family in self._by_target_family:
            found.extend(self._by_target_family[target_family])
        if not family_id and not operation_family and not target_family:
            for lst in list(self._by_op_family.values()) + list(self._by_target_family.values()) + list(self._by_family_id.values()):
                found.extend(lst)
        # Deduplicate preserving order
        seen = set()
        unique = []
        for c in found:
            key = (c.id, c.version)
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique


def _target_matches(contract: CapabilityFormalContract, target: str, metadata: dict[str, Any]) -> bool:
    if not target or not contract.target_family:
        return True
    if metadata.get("target_family") == contract.target_family:
        return True
    # If any effect in the capability footprint directly targets this resource
    for eff in contract.effect_footprint:
        eff_target = getattr(eff, "target", getattr(eff, "resource", getattr(eff, "path", None)))
        if eff_target and (eff_target == target or target.startswith(eff_target) or eff_target.startswith(target)):
            return True
    # Prefix check
    if "/" in target and target.split("/")[0] == contract.target_family:
        return True
    if target == contract.target_family:
        return True
    return False


class CapabilityRouter:
    """Deterministic executability typechecker and proof engine."""

    def __init__(
        self,
        registry: OperationalCapabilityRegistry,
        policy_engine: Any = None,
        composition_engine: Any = None,
    ) -> None:
        self.registry = registry
        self.policy_engine = policy_engine
        self.composition_engine = composition_engine
        self._index = CapabilityIndex()
        self._rebuild_index()

    def _rebuild_index(self) -> None:
        try:
            self._index = CapabilityIndex()
            for cap in self.registry.list_capabilities(lifecycle=CapabilityLifecycle.PROMOTED):
                self._index.index(cap)
        except Exception:
            pass

    def route(
        self,
        operation_intent: OperationIntent,
        semantic_state: dict[str, Any],
        authority_scope: AuthorityScope | None = None,
        runtime_state: dict[str, Any] | None = None,
        policy: Any = None,
        run_id: str | None = None,
        operation_id: str | None = None,
    ) -> RoutingDecision:
        runtime_state = runtime_state or {}
        authority = authority_scope or AuthorityScope(level=AuthorityLevel.READ)
        intent_h = operation_intent_hash(operation_intent)
        state_h = _state_hash(semantic_state)

        # 1. Check outstanding uncertain mutations in relevant domain
        uncertain_mutations = runtime_state.get("outstanding_uncertain_mutations", [])
        if uncertain_mutations:
            # Check if any uncertain mutation touches intent target or related resources
            for um in uncertain_mutations:
                um_target = um.get("target") or ""
                if not operation_intent.target or not um_target or um_target == operation_intent.target or operation_intent.target.startswith(um_target):
                    # Name the effect however the caller identified it. A record whose
                    # target cannot be compared to the intent is still a reason to
                    # refuse: reconciliation is never inferred from silence.
                    named = um_target or um.get("target_identifier") or um.get("operation_id") or "an unproven effect"
                    return ReasoningDecision(
                        requires_reconciliation=True,
                        reason=f"Outstanding uncertain mutation on {named}; reconcile before dispatch",
                    )

        # 2. Check if goal is already satisfied in the current observed state
        context = {"baseline_state": runtime_state.get("baseline_state", {})}
        if operation_intent.goal.evaluate(semantic_state, context=context):
            return SatisfiedDecision(goal_satisfied=True)

        # 3. Candidate search: exact match in promoted capabilities
        self._rebuild_index()
        candidates = self._index.candidates(
            target_family=operation_intent.metadata.get("target_family") or operation_intent.target,
            operation_family=operation_intent.metadata.get("operation_family"),
            family_id=operation_intent.metadata.get("family_id"),
        )
        if not candidates:
            candidates = self._index.candidates()
        if not candidates:
            # Fall back to all promoted capabilities in registry
            candidates = self.registry.list_capabilities(lifecycle=CapabilityLifecycle.PROMOTED)

        authority_shortfalls: list[tuple[OperationalCapability, AuthorityScope]] = []

        for cap in candidates:
            if cap.drift_state != "healthy":
                continue
            if cap.lifecycle != CapabilityLifecycle.PROMOTED:
                continue

            # Formal contract resolution
            fc = cap.formal_contract
            if not fc:
                # Capabilities without formal contract cannot gain formal EXECUTE certification
                continue
            if isinstance(fc, dict):
                contract = CapabilityFormalContract.from_dict(fc)
            else:
                contract = fc

            # Target matching
            if not _target_matches(contract, operation_intent.target, operation_intent.metadata):
                continue

            # Preconditions check
            preconditions_hold = all(
                p.evaluate(semantic_state, context=context)
                for p in contract.typed_preconditions
            )
            if not preconditions_hold:
                continue

            # Goal coverage: postconditions must entail intent goal
            post_and = AND(*contract.typed_postconditions) if contract.typed_postconditions else None
            goal_coverage = bool(post_and and entails(post_and, operation_intent.goal))
            if not goal_coverage:
                continue

            # Effect containment: every effect in capability footprint must be allowed by intent budget
            effect_containment = all(
                effect_contained(eff, operation_intent.effect_budget)
                for eff in contract.effect_footprint
            )
            if not effect_containment:
                continue

            # Invariant preservation: every invariant must be preserved by all capability effects
            invariant_preservation = True
            for eff in contract.effect_footprint:
                for inv in operation_intent.invariants:
                    if not preserves_invariant(eff, inv):
                        invariant_preservation = False
                        break
                if not invariant_preservation:
                    break
            if not invariant_preservation:
                continue

            # Authority check
            authority_satisfied = authority_covers(authority, contract.authority_required)
            if not authority_satisfied:
                authority_shortfalls.append((cap, contract.authority_required))
                continue

            # Policy check
            policy_engine = policy or self.policy_engine
            policy_satisfied = True
            if policy_engine is not None:
                # Evaluate against ScopedPolicyEngine or callable
                if callable(policy_engine):
                    policy_satisfied = all(policy_engine(eff) for eff in contract.effect_footprint)
                elif hasattr(policy_engine, "evaluate"):
                    # Check each effect
                    for eff in contract.effect_footprint:
                        from workstation.policy import ActionScope, PolicyDecision
                        scope = ActionScope(
                            task_id=operation_intent.id,
                            session_id=runtime_state.get("session_id", ""),
                            capability=getattr(eff, "operation_family", "workstation"),
                            action_name=getattr(eff, "operation_family", "execute"),
                            target=getattr(eff, "target", operation_intent.target),
                        )
                        pe = policy_engine.evaluate(scope)
                        if pe.decision == PolicyDecision.DENY:
                            policy_satisfied = False
                            break
                        if pe.decision == PolicyDecision.REQUIRE_APPROVAL:
                            return HumanDecision(reason="policy_requires_human_approval", scope=scope)
            if not policy_satisfied:
                continue

            # Verifier and acceptance contract
            acceptance = operation_intent.acceptance
            policy_str = getattr(acceptance, "policy", "evidence")
            verifier_raw = contract.verifier or cap.verifier_contract
            verifier_contract = (
                verifier_raw if isinstance(verifier_raw, VerificationContract)
                else VerificationContract.from_dict(verifier_raw)
            )
            required_predicates = {p.fingerprint() for p in contract.typed_postconditions}
            is_mutation = bool(contract.effect_footprint)
            temporal_required = verifier_contract.temporal_basis != "none"
            verifier_available, _verifier_reasons = verifier_contract.is_sufficient_for(
                required_predicates=required_predicates,
                mutation=is_mutation,
                temporal_required=temporal_required,
            )
            evidence_strength_sufficient = verifier_available
            if not evidence_strength_sufficient:
                continue

            # Preflight state hashing remains a dispatch fence.  A verifier that
            # additionally requires revision/time freshness must have a real basis;
            # a default boolean cannot manufacture it.
            state_fresh = True
            if temporal_required:
                basis = verifier_contract.temporal_basis
                state_fresh = bool(
                    runtime_state.get("verification_temporal_basis")
                    or runtime_state.get(basis)
                    or runtime_state.get(f"state_{basis}")
                )
            if not state_fresh:
                continue

            # All obligations passed! Build certificate
            cert = RoutingCertificate(
                target_match=True,
                inputs_bound=True,
                preconditions_hold=True,
                goal_coverage=True,
                effect_containment=True,
                invariant_preservation=True,
                authority_satisfied=True,
                policy_satisfied=True,
                approval_satisfied=True,
                verifier_available=verifier_available,
                evidence_strength_sufficient=evidence_strength_sufficient,
                state_fresh=state_fresh,
                capability_healthy=(cap.drift_state == "healthy" and cap.lifecycle == CapabilityLifecycle.PROMOTED),
                no_outstanding_uncertainty=True,
                deterministic_closure=True,
                intent_hash=intent_h,
                semantic_state_hash=state_h,
                capability_id=cap.id,
                capability_version=cap.version,
                router_policy_version="1.0.0",
                run_id=run_id,
                operation_id=operation_id,
            )

            return ExecutableDecision(capability=cap, certificate=cert)

        # 4. If any candidate had an authority shortfall, yield to human
        if authority_shortfalls:
            return HumanDecision(
                reason="authority_required_missing",
                scope=authority_shortfalls[0][1],
            )

        # 5. Composition fallback (CP3 will supply engine)
        if self.composition_engine is not None:
            comp_decision = self.composition_engine.compose(
                operation_intent=operation_intent,
                semantic_state=semantic_state,
                authority=authority,
                runtime_state=runtime_state,
            )
            if comp_decision is not None:
                return comp_decision

        # 6. Check if a future observable event or wait is requested
        if runtime_state.get("await_condition"):
            return WaitDecision(await_condition=runtime_state["await_condition"])

        # 7. Unresolved semantic choice -> WAKE_LLM
        return ReasoningDecision(
            reason="no_certifiable_capability_found",
            open_condition={
                "target": operation_intent.target,
                "goal": operation_intent.goal.to_dict(),
            },
        )

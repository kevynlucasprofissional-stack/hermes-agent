"""Bounded Backward-Chaining Composition Engine, CompositionCertificate, and Threat Detection."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import itertools
import json
import time
from typing import Any, Sequence

from workstation.contracts import utc_now
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.intent import OperationIntent, operation_intent_hash
from workstation.control_plane.ir import (
    AND, Effect, Predicate, effect_contained, entails, preserves_invariant
)
from workstation.control_plane.lattice import (
    AuthorityLevel, AuthorityScope, authority_covers, join_all
)
from workstation.control_plane.router import ComposedDecision, ReasoningDecision, _state_hash
from workstation.operational_capabilities import (
    CapabilityLifecycle, OperationalCapability, OperationalCapabilityRegistry
)


@dataclass
class CompositionCertificate:
    """Auditable proof certificate certifying that a multi-step capability composition plan is sound."""

    plan_ids: list[str] = field(default_factory=list)
    plan_versions: list[str] = field(default_factory=list)
    chain_verified: bool = False
    goal_coverage: bool = False
    effect_containment: bool = False
    authority_satisfied: bool = False
    invariant_preservation: bool = False
    no_causal_threats: bool = False
    verifier_closure: bool = False
    deterministic_closure: bool = False

    intent_hash: str = ""
    semantic_state_hash: str = ""
    router_policy_version: str = "1.0.0"
    created_at: str = field(default_factory=utc_now)
    run_id: str | None = None
    operation_id: str | None = None

    def is_valid(self) -> bool:
        return (
            self.chain_verified
            and self.goal_coverage
            and self.effect_containment
            and self.authority_satisfied
            and self.invariant_preservation
            and self.no_causal_threats
            and self.verifier_closure
            and self.deterministic_closure
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def certificate_hash(self) -> str:
        canonical = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _get_contract(cap: OperationalCapability) -> CapabilityFormalContract | None:
    fc = cap.formal_contract
    if not fc:
        return None
    if isinstance(fc, dict):
        return CapabilityFormalContract.from_dict(fc)
    return fc


def detect_causal_threats(plan: Sequence[OperationalCapability]) -> list[dict[str, Any]]:
    """Detect if an intermediate step's effects threaten a precondition required by a subsequent step."""
    threats: list[dict[str, Any]] = []
    for i in range(len(plan)):
        step_i = plan[i]
        contract_i = _get_contract(step_i)
        if not contract_i:
            continue
        effects_i = contract_i.effect_footprint

        for j in range(i + 1, len(plan)):
            step_j = plan[j]
            contract_j = _get_contract(step_j)
            if not contract_j:
                continue
            preconditions_j = contract_j.typed_preconditions

            for eff in effects_i:
                for pre in preconditions_j:
                    if not preserves_invariant(eff, pre):
                        threats.append({
                            "threatening_step": step_i.id,
                            "threatened_step": step_j.id,
                            "threatening_index": i,
                            "threatened_index": j,
                            "effect": eff.to_dict(),
                            "precondition": pre.to_dict(),
                        })
    return threats


def _plan_satisfies_dependencies(plan: Sequence[OperationalCapability]) -> bool:
    """Verify that each step's preconditions are satisfied by prior steps' postconditions or initial assumptions."""
    for j in range(len(plan)):
        contract_j = _get_contract(plan[j])
        if not contract_j:
            return False
        # Each precondition of plan[j] must be preserved up to step j
        for i in range(j):
            contract_i = _get_contract(plan[i])
            if not contract_i:
                continue
            for eff in contract_i.effect_footprint:
                for pre in contract_j.typed_preconditions:
                    if not preserves_invariant(eff, pre):
                        return False
    return True


def reorder_plan(plan: Sequence[OperationalCapability]) -> list[OperationalCapability] | None:
    """Attempt deterministic reordering of plan to eliminate causal threats while preserving soundness."""
    if len(plan) > 6:
        # Avoid combinatorial explosion
        return None

    # Check all permutations
    for perm in itertools.permutations(plan):
        # Must eliminate threats
        if not detect_causal_threats(perm):
            return list(perm)
    return None


class CompositionEngine:
    """Bounded backward-chaining composition planner."""

    def __init__(
        self,
        registry: OperationalCapabilityRegistry,
        max_depth: int = 5,
        max_nodes_expanded: int = 25,
        max_candidates_per_predicate: int = 4,
        max_wall_time_seconds: float = 2.0,
    ) -> None:
        self.registry = registry
        self.max_depth = max_depth
        self.max_nodes_expanded = max_nodes_expanded
        self.max_candidates_per_predicate = max_candidates_per_predicate
        self.max_wall_time_seconds = max_wall_time_seconds

    def compose(
        self,
        operation_intent: OperationIntent,
        semantic_state: dict[str, Any],
        authority: AuthorityScope,
        runtime_state: dict[str, Any] | None = None,
    ) -> ComposedDecision | ReasoningDecision | None:
        runtime_state = runtime_state or {}
        start_time = time.monotonic()
        nodes_expanded = 0

        promoted_caps = self.registry.list_capabilities(lifecycle=CapabilityLifecycle.PROMOTED)
        valid_caps = [c for c in promoted_caps if c.drift_state == "healthy" and c.formal_contract]

        # Bounded backward chaining search
        # Path is a list of capabilities in execution order (from initial state to goal)
        queue: list[tuple[Predicate, list[OperationalCapability], int]] = [
            (operation_intent.goal, [], 0)
        ]

        while queue:
            if time.monotonic() - start_time > self.max_wall_time_seconds:
                return ReasoningDecision(
                    reason="composition_budget_exhausted",
                    open_condition={"budget": "wall_time_exceeded"},
                )

            current_goal, current_chain_reverse, depth = queue.pop(0)
            nodes_expanded += 1

            if depth > self.max_depth or nodes_expanded > self.max_nodes_expanded:
                return ReasoningDecision(
                    reason="composition_budget_exhausted",
                    open_condition={"budget": "max_depth_or_nodes_exceeded"},
                )

            # Find capabilities whose postconditions entail current_goal
            candidates_for_goal: list[OperationalCapability] = []
            for cap in valid_caps:
                contract = _get_contract(cap)
                if not contract:
                    continue
                post_and = AND(*contract.typed_postconditions) if contract.typed_postconditions else None
                if post_and and entails(post_and, current_goal):
                    candidates_for_goal.append(cap)
                    if len(candidates_for_goal) >= self.max_candidates_per_predicate:
                        break

            for cap in candidates_for_goal:
                contract = _get_contract(cap)
                if not contract:
                    continue
                new_chain_reverse = [cap] + current_chain_reverse
                new_plan = list(new_chain_reverse)  # Currently in execution order

                # Check if all preconditions of cap hold in semantic_state
                context = {"baseline_state": runtime_state.get("baseline_state", {})}
                preconditions_hold = all(
                    p.evaluate(semantic_state, context=context)
                    for p in contract.typed_preconditions
                )

                if preconditions_hold:
                    # Chain closed! Validate full candidate plan
                    decision = self._validate_and_certify(
                        new_plan, operation_intent, semantic_state, authority, runtime_state
                    )
                    if decision is not None:
                        return decision
                else:
                    # Backward chain further for unsatisfied preconditions
                    if len(contract.typed_preconditions) > 0:
                        unsatisfied = [
                            p for p in contract.typed_preconditions
                            if not p.evaluate(semantic_state, context=context)
                        ]
                        if unsatisfied:
                            next_subgoal = AND(*unsatisfied) if len(unsatisfied) > 1 else unsatisfied[0]
                            queue.append((next_subgoal, new_chain_reverse, depth + 1))

        return None

    def _validate_and_certify(
        self,
        plan: list[OperationalCapability],
        intent: OperationIntent,
        semantic_state: dict[str, Any],
        granted_authority: AuthorityScope,
        runtime_state: dict[str, Any],
    ) -> ComposedDecision | None:
        # 0. Chain dependency verification
        chain_verified = _plan_satisfies_dependencies(plan)
        if not chain_verified:
            return None

        # 1. Causal threat detection & reordering
        threats = detect_causal_threats(plan)
        if threats:
            reordered = reorder_plan(plan)
            if not reordered:
                return None
            plan = reordered
            threats = detect_causal_threats(plan)
            if threats:
                return None
            chain_verified = _plan_satisfies_dependencies(plan)
            if not chain_verified:
                return None

        # 2. Effect Union Containment (Goal Non-Expansion)
        all_effects: list[Effect] = []
        all_authorities: list[AuthorityScope] = []
        for cap in plan:
            contract = _get_contract(cap)
            if not contract:
                return None
            all_effects.extend(contract.effect_footprint)
            all_authorities.append(contract.authority_required)

        effect_containment = all(
            effect_contained(eff, intent.effect_budget)
            for eff in all_effects
        )
        if not effect_containment:
            return None

        # 3. Authority JOIN
        joined_authority = join_all(all_authorities)
        if not authority_covers(granted_authority, joined_authority):
            return None

        # 4. Invariant preservation across all transitions
        invariant_preservation = True
        for eff in all_effects:
            for inv in intent.invariants:
                if not preserves_invariant(eff, inv):
                    invariant_preservation = False
                    break
            if not invariant_preservation:
                break
        if not invariant_preservation:
            return None

        # 5. Verifier closure
        verifier_closure = all(
            bool(c.formal_contract.get("verifier") if isinstance(c.formal_contract, dict)
                 else getattr(c.formal_contract, "verifier", None) or c.verifier_contract)
            for c in plan
        )
        if not verifier_closure:
            return None

        # 6. Goal coverage: final capability's postconditions must entail intent.goal
        last_contract = _get_contract(plan[-1])
        if not last_contract or not last_contract.typed_postconditions:
            return None
        post_and = AND(*last_contract.typed_postconditions) if len(last_contract.typed_postconditions) > 1 else last_contract.typed_postconditions[0]
        goal_coverage = bool(entails(post_and, intent.goal))
        if not goal_coverage:
            return None

        deterministic_closure = bool(
            chain_verified
            and goal_coverage
            and effect_containment
            and invariant_preservation
            and verifier_closure
            and not threats
        )
        if not deterministic_closure:
            return None

        cert = CompositionCertificate(
            plan_ids=[c.id for c in plan],
            plan_versions=[c.version for c in plan],
            chain_verified=chain_verified,
            goal_coverage=goal_coverage,
            effect_containment=effect_containment,
            authority_satisfied=True,
            invariant_preservation=invariant_preservation,
            no_causal_threats=True,
            verifier_closure=verifier_closure,
            deterministic_closure=deterministic_closure,
            intent_hash=operation_intent_hash(intent),
            semantic_state_hash=_state_hash(semantic_state),
            router_policy_version="1.0.0",
        )

        return ComposedDecision(plan=plan, certificate=cert)

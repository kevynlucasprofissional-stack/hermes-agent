"""Verified Operational Control Plane Metrics, Failure Attribution, and Shadow Routing.

Enforces:
- Real cost vectors over single lossy scalar aggregations.
- Unknown cost metrics remain strictly None / null (no invented denominators or hallucinated free execution).
- Zero mutable dispatch in shadow evaluation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import time
from typing import Any

from workstation.control_plane.intent import OperationIntent
from workstation.control_plane.lattice import AuthorityScope
from workstation.control_plane.router import (
    CapabilityRouter,
    ComposedDecision,
    ExecutableDecision,
    HumanDecision,
    ReasoningDecision,
    RoutingDecision,
    SatisfiedDecision,
    WaitDecision,
)


class ShadowRouter:
    """Evaluates routing decisions speculatively without executing or mutating state."""

    def __init__(self, router: CapabilityRouter) -> None:
        self.router = router

    def evaluate_shadow(
        self,
        intent: OperationIntent,
        semantic_state: dict[str, Any],
        authority_scope: AuthorityScope,
    ) -> dict[str, Any]:
        """Compute what the router WOULD decide; dispatches 0 mutations."""
        start_t = time.perf_counter()
        decision: RoutingDecision = self.router.route(intent, semantic_state, authority_scope)
        duration_ms = (time.perf_counter() - start_t) * 1000.0

        would_decision = "UNKNOWN"
        would_capability_id = None
        certificate_dict = None

        if isinstance(decision, ExecutableDecision):
            would_decision = "EXECUTE"
            would_capability_id = decision.capability.id
            certificate_dict = decision.certificate.to_dict()
        elif isinstance(decision, SatisfiedDecision):
            would_decision = "SATISFIED"
        elif isinstance(decision, ComposedDecision):
            would_decision = "COMPOSE"
            certificate_dict = decision.certificate.to_dict()
        elif isinstance(decision, WaitDecision):
            would_decision = "WAIT"
        elif isinstance(decision, HumanDecision):
            would_decision = "ASK_HUMAN"
        elif isinstance(decision, ReasoningDecision):
            would_decision = "WAKE_LLM"

        return {
            "would_decision": would_decision,
            "would_capability_id": would_capability_id,
            "certificate": certificate_dict,
            "mutations_dispatched": 0,
            "routing_time_ms": duration_ms,
            "decision": decision,
        }


class FailureClass(str, Enum):
    """Rigorous attribution of operational failures to distinct root causes."""

    INTENT_ERROR = "INTENT_ERROR"
    OBSERVATION_ERROR = "OBSERVATION_ERROR"
    ROUTING_ERROR = "ROUTING_ERROR"
    CAPABILITY_DRIFT = "CAPABILITY_DRIFT"
    COMPOSITION_ERROR = "COMPOSITION_ERROR"
    POLICY_ERROR = "POLICY_ERROR"
    RUNTIME_FAILURE = "RUNTIME_FAILURE"


class FailureAttributor:
    """Classifies operational failures to maintain library health and avoid misblaming."""

    def classify(
        self,
        *,
        certificate_valid: bool = True,
        preconditions_held_at_dispatch: bool = True,
        execution_error: Any = None,
        postconditions_verified: bool = True,
        policy_blocked: bool = False,
        composition_failed: bool = False,
        intent_malformed: bool = False,
        observation_stale: bool = False,
    ) -> FailureClass:
        if intent_malformed:
            return FailureClass.INTENT_ERROR
        if policy_blocked:
            return FailureClass.POLICY_ERROR
        if composition_failed:
            return FailureClass.COMPOSITION_ERROR
        if not certificate_valid:
            return FailureClass.ROUTING_ERROR
        if not preconditions_held_at_dispatch:
            if observation_stale:
                return FailureClass.OBSERVATION_ERROR
            return FailureClass.ROUTING_ERROR
        if execution_error is not None:
            return FailureClass.RUNTIME_FAILURE
        if not postconditions_verified:
            return FailureClass.CAPABILITY_DRIFT
        return FailureClass.RUNTIME_FAILURE


@dataclass
class VOLCMetrics:
    """Verified Outcome Lifetime Cost (VOLC) metric vector.
    
    Explicitly tracks cost components across outcomes without prematurely reducing
    heterogeneous units into a single distorted scalar.
    """

    verified_outcomes: int
    llm_calls: int = 0
    tokens: int = 0
    cpu_seconds: float = 0.0
    wall_time_seconds: float = 0.0
    tool_calls: int = 0
    polls: int = 0
    human_interventions: int = 0
    tokens_cost_usd: float | None = None

    @property
    def llm_calls_per_outcome(self) -> float | None:
        return self.llm_calls / self.verified_outcomes if self.verified_outcomes else None

    @property
    def tokens_per_outcome(self) -> float | None:
        return self.tokens / self.verified_outcomes if self.verified_outcomes else None

    @property
    def tool_calls_per_outcome(self) -> float | None:
        return self.tool_calls / self.verified_outcomes if self.verified_outcomes else None

    @property
    def cost_usd_per_outcome(self) -> float | None:
        if self.tokens_cost_usd is None or not self.verified_outcomes:
            return None
        return self.tokens_cost_usd / self.verified_outcomes

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["llm_calls_per_outcome"] = self.llm_calls_per_outcome
        d["tokens_per_outcome"] = self.tokens_per_outcome
        d["tool_calls_per_outcome"] = self.tool_calls_per_outcome
        d["cost_usd_per_outcome"] = self.cost_usd_per_outcome
        return d


def calculate_volc(
    verified_outcomes: int,
    llm_calls: int = 0,
    tokens: int = 0,
    cpu_seconds: float = 0.0,
    wall_time_seconds: float = 0.0,
    tool_calls: int = 0,
    polls: int = 0,
    human_interventions: int = 0,
    tokens_cost_usd: float | None = None,
) -> VOLCMetrics:
    """Construct VOLCMetrics vector, preserving unknown cost metrics as None."""
    return VOLCMetrics(
        verified_outcomes=verified_outcomes,
        llm_calls=llm_calls,
        tokens=tokens,
        cpu_seconds=cpu_seconds,
        wall_time_seconds=wall_time_seconds,
        tool_calls=tool_calls,
        polls=polls,
        human_interventions=human_interventions,
        tokens_cost_usd=tokens_cost_usd,
    )


class WakeReason(str, Enum):
    """Normalized categories for waking the LLM from deterministic execution."""
    TIMEOUT = "TIMEOUT"
    UNCERTAIN_MUTATION = "UNCERTAIN_MUTATION"
    OPEN_CONDITION = "OPEN_CONDITION"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    HUMAN_INTERVENTION = "HUMAN_INTERVENTION"
    UNEXPECTED_FAILURE = "UNEXPECTED_FAILURE"


@dataclass
class ORAMetrics:
    """Operational Reasoning Amortization (ORA) Metrics.

    Tracks how effectively verified operational experience progressively replaces
    LLM re-reasoning with deterministic operational knowledge.

    Invariants:
    - Never invent synthetic counts or tokens; unknown denominators remain strictly None.
    - Zero division safely returns None.
    """
    verified_transitions_deterministic: int = 0
    verified_transitions_reasoned: int = 0
    unverified_transitions: int = 0

    atomic_capability_invocations: int = 0
    composite_capability_invocations: int = 0
    total_capability_invocations: int = 0

    resident_wait_count: int = 0
    non_resident_wait_count: int = 0
    total_wait_duration_seconds: float = 0.0
    non_resident_wait_duration_seconds: float = 0.0

    llm_wake_count: int = 0
    total_routing_events: int = 0
    wake_reasons: dict[str, int] = field(default_factory=dict)

    amortized_tokens_saved: int | None = None
    amortized_cost_usd_saved: float | None = None

    @property
    def ora_ratio(self) -> float | None:
        """Ratio of verified transitions executed deterministically without LLM."""
        total = self.verified_transitions_deterministic + self.verified_transitions_reasoned
        if not total:
            return None
        return self.verified_transitions_deterministic / total

    @property
    def composite_reuse_rate(self) -> float | None:
        """Ratio of composite capability invocations over total capability invocations."""
        total = self.total_capability_invocations or (self.atomic_capability_invocations + self.composite_capability_invocations)
        if not total:
            return None
        return self.composite_capability_invocations / total

    @property
    def wait_non_residency_rate(self) -> float | None:
        """Ratio of non-resident waits (releasing worker) over total waits."""
        total = self.resident_wait_count + self.non_resident_wait_count
        if not total:
            return None
        return self.non_resident_wait_count / total

    @property
    def wake_llm_rate(self) -> float | None:
        """Ratio of events that triggered WAKE_LLM over total routing events."""
        if not self.total_routing_events:
            return None
        return self.llm_wake_count / self.total_routing_events

    def record_wake_reason(self, reason: str | WakeReason) -> None:
        r_str = reason.value if isinstance(reason, WakeReason) else str(reason)
        self.wake_reasons[r_str] = self.wake_reasons.get(r_str, 0) + 1
        self.llm_wake_count += 1

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ora_ratio"] = self.ora_ratio
        d["composite_reuse_rate"] = self.composite_reuse_rate
        d["wait_non_residency_rate"] = self.wait_non_residency_rate
        d["wake_llm_rate"] = self.wake_llm_rate
        return d

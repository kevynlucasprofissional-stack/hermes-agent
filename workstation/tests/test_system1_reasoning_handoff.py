"""Integration tests for System-1 reasoning handoff and ambiguity classification.

Proves:
- System-1 categorizes the nature of reasoning gaps (ambiguity_kind) prior to waking System-2.
- When System-1 identifies a known recovery path (e.g. reprobe_state) without needing System-2,
  Router resolves deterministically with WaitDecision, avoiding unnecessary LLM wake.
- When real novelty exists, ReasoningDecision carries typed ambiguity_kind and needs_system2=True.
"""
from __future__ import annotations

import pytest

from agent.system1_decision import (
    register_system1_decision_provider,
    unregister_system1_decision_provider,
    reset_system1_decision,
)
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.intent import OperationIntent
from workstation.control_plane.ir import EQ, SET, Predicate
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.router import (
    CapabilityRouter,
    ReasoningDecision,
    WaitDecision,
)
from workstation.operational_capabilities import (
    OperationalCapabilityRegistry,
)
from workstation.system1.provider import FakeSystem1DecisionProvider


def test_system1_avoids_llm_wake_on_known_reprobe_recovery():
    """System-1 classifies needs_system2='no' and recovery='reprobe_state' -> WaitDecision (no LLM wake)."""
    reset_system1_decision()

    # Empty registry -> no capability matches
    registry = OperationalCapabilityRegistry()
    router = CapabilityRouter(registry=registry)

    intent = OperationIntent(
        id="intent_unresolved",
        target="network_service",
        goal=EQ("service.online", True),
    )
    state = {"service": {"online": False}}
    authority = AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"})

    # Register Fake System-1 provider indicating recovery is possible without System-2
    provider = FakeSystem1DecisionProvider(
        name="test_system1_reprobe",
        preset_answers={
            "ambiguity_kind": "known_recovery",
            "needs_system2": "no",
            "known_recovery_path": "reprobe_state",
        },
        preset_confidence={
            "ambiguity_kind": 0.95,
            "needs_system2": 0.98,
            "known_recovery_path": 0.92,
        },
    )
    register_system1_decision_provider(provider)

    try:
        decision = router.route(intent, state, authority)
        # Should NOT be ReasoningDecision (WAKE_LLM); should be WaitDecision!
        assert isinstance(decision, WaitDecision)
        assert decision.await_condition.get("type") == "reprobe_state"
        assert "without requiring System-2" in decision.reason
    finally:
        unregister_system1_decision_provider(provider)
        reset_system1_decision()


def test_system1_classifies_novel_strategy_for_reasoning_decision():
    """When genuine novelty exists, ReasoningDecision carries typed ambiguity_kind and needs_system2=True."""
    reset_system1_decision()

    registry = OperationalCapabilityRegistry()
    router = CapabilityRouter(registry=registry)

    intent = OperationIntent(
        id="intent_novel",
        target="quantum_computer",
        goal=EQ("qubits.entangled", True),
    )
    state = {}
    authority = AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"})

    provider = FakeSystem1DecisionProvider(
        name="test_system1_novel",
        preset_answers={
            "ambiguity_kind": "missing_information",
            "needs_system2": "yes",
            "known_recovery_path": "escalate_to_system2",
        },
        preset_confidence={
            "ambiguity_kind": 0.90,
            "needs_system2": 0.99,
            "known_recovery_path": 0.85,
        },
    )
    register_system1_decision_provider(provider)

    try:
        decision = router.route(intent, state, authority)
        assert isinstance(decision, ReasoningDecision)
        assert decision.ambiguity_kind == "missing_information"
        assert decision.needs_system2 is True
    finally:
        unregister_system1_decision_provider(provider)
        reset_system1_decision()

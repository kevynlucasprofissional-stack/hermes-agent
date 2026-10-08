"""Integration tests for System-1 capability routing influence.

Proves:
- When System-1 prefers candidate B over candidate A, candidate B is evaluated and certified first.
- When System-1 prefers an invalid candidate, Router falls back to other valid candidates.
- When System-1 fails or throws, original candidate order is preserved.
- System-1 NEVER bypasses verification, preconditions, or policy checks.
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
from workstation.control_plane.ir import EQ, SET, TRUE, EXISTS, Effect, Predicate
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.router import (
    CapabilityRouter,
    ExecutableDecision,
    ReasoningDecision,
)
from workstation.control_plane.verification import VerificationContract, VerificationLifecycle
from workstation.execution_policy import EvidenceStrength
from workstation.operational_capabilities import (
    CapabilityLifecycle,
    OperationalCapability,
    OperationalCapabilityRegistry,
)
from workstation.system1.provider import FakeSystem1DecisionProvider


def _validated_verifier(*predicates):
    return VerificationContract(
        covered_predicates=tuple(p.fingerprint() for p in predicates),
        observer="owner.readback",
        source_kind="source_of_record",
        minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        allowed_trust=("trusted_owner",),
        lifecycle=VerificationLifecycle.VALIDATED,
        temporal_basis="none",
    )


def _build_test_capability(cap_id: str, family: str = "filesystem", pass_precondition: bool = True) -> OperationalCapability:
    precondition = EQ("state.ready", True) if pass_precondition else EQ("state.unmet", True)
    contract = CapabilityFormalContract(
        target_family=family,
        typed_preconditions=[precondition],
        typed_postconditions=[EQ("file.exists", True)],
        effect_footprint=[SET("file.exists", True)],
        authority_required=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"}),
        verifier=_validated_verifier(EQ("file.exists", True)),
    )
    return OperationalCapability(
        id=cap_id,
        name=f"Capability {cap_id}",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
        route="atomic",
        formal_contract=contract,
    )


def test_system1_candidate_reordering_preferred_candidate():
    """System-1 prefers candidate B; candidate B is certified and returned first."""
    reset_system1_decision()

    registry = OperationalCapabilityRegistry()
    cap_a = _build_test_capability("cap_alpha")
    cap_b = _build_test_capability("cap_beta")
    registry.register(cap_a)
    registry.register(cap_b)

    router = CapabilityRouter(registry=registry)

    intent = OperationIntent(
        id="intent_1",
        target="filesystem",
        goal=EQ("file.exists", True),
        effect_budget=[SET("file.exists", True)],
        metadata={"target_family": "filesystem"},
    )
    state = {"state": {"ready": True}}
    authority = AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"})

    # 1. Without System-1 provider, first registered (cap_alpha) is selected
    dec_default = router.route(intent, state, authority)
    assert isinstance(dec_default, ExecutableDecision)
    assert dec_default.capability.id == "cap_alpha"

    # 2. Register Fake System-1 provider that prefers cap_beta
    provider = FakeSystem1DecisionProvider(
        name="test_system1_beta",
        preset_answers={"preferred_candidate": "cap_beta"},
        preset_confidence={"preferred_candidate": 0.99},
    )
    register_system1_decision_provider(provider)

    try:
        dec_reordered = router.route(intent, state, authority)
        assert isinstance(dec_reordered, ExecutableDecision)
        assert dec_reordered.capability.id == "cap_beta"
        assert dec_reordered.certificate.is_valid()
    finally:
        unregister_system1_decision_provider(provider)
        reset_system1_decision()


def test_system1_invalid_candidate_fallback():
    """System-1 prefers an invalid candidate (precondition fails); Router falls back to valid candidate."""
    reset_system1_decision()

    registry = OperationalCapabilityRegistry()
    cap_a = _build_test_capability("cap_alpha", pass_precondition=True)
    cap_b = _build_test_capability("cap_beta", pass_precondition=False)
    registry.register(cap_a)
    registry.register(cap_b)

    router = CapabilityRouter(registry=registry)

    intent = OperationIntent(
        id="intent_2",
        target="filesystem",
        goal=EQ("file.exists", True),
        effect_budget=[SET("file.exists", True)],
        metadata={"target_family": "filesystem"},
    )
    state = {"state": {"ready": True}}  # satisfies cap_a, but NOT cap_b
    authority = AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"})

    provider = FakeSystem1DecisionProvider(
        name="test_system1_pick_invalid",
        preset_answers={"preferred_candidate": "cap_beta"},
        preset_confidence={"preferred_candidate": 0.99},
    )
    register_system1_decision_provider(provider)

    try:
        dec = router.route(intent, state, authority)
        # Even though System-1 preferred cap_beta, cap_beta fails precondition proof
        # so Router falls back to cap_alpha
        assert isinstance(dec, ExecutableDecision)
        assert dec.capability.id == "cap_alpha"
        assert dec.certificate.is_valid()
    finally:
        unregister_system1_decision_provider(provider)
        reset_system1_decision()


def test_system1_provider_failure_preserves_order():
    """When System-1 provider throws an exception, Router logs and preserves original order."""
    reset_system1_decision()

    registry = OperationalCapabilityRegistry()
    cap_a = _build_test_capability("cap_alpha")
    cap_b = _build_test_capability("cap_beta")
    registry.register(cap_a)
    registry.register(cap_b)

    router = CapabilityRouter(registry=registry)

    intent = OperationIntent(
        id="intent_3",
        target="filesystem",
        goal=EQ("file.exists", True),
        effect_budget=[SET("file.exists", True)],
        metadata={"target_family": "filesystem"},
    )
    state = {"state": {"ready": True}}
    authority = AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"})

    provider = FakeSystem1DecisionProvider(
        name="test_failing_provider",
        should_fail=True,
    )
    register_system1_decision_provider(provider)

    try:
        dec = router.route(intent, state, authority)
        assert isinstance(dec, ExecutableDecision)
        assert dec.capability.id == "cap_alpha"
        assert dec.certificate.is_valid()
    finally:
        unregister_system1_decision_provider(provider)
        reset_system1_decision()

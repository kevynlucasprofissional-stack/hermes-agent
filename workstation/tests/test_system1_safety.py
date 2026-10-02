"""Safety and Authority Invariant tests for System-1 integration.

Enforces:
- System-1 has ZERO authority to mint certificates, grant permissions, or bypass policy.
- A 99.99% confident destructive candidate without required authority produces NO DISPATCH.
- Policy denials and effect containment violations strictly block dispatch regardless of System-1 ranking.
- Self-verification is strictly impossible: Verifier contracts cannot be satisfied by System-1 confidence.
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
from workstation.control_plane.ir import EQ, SET, DELETE, Effect, Predicate
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.router import (
    CapabilityRouter,
    ExecutableDecision,
    HumanDecision,
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


def test_destructive_candidate_without_authority_blocked():
    """A destructive capability ranked 99.99% by System-1 MUST NOT dispatch when authority is missing."""
    reset_system1_decision()

    registry = OperationalCapabilityRegistry()

    # Destructive capability requiring HIGH authority
    destructive_contract = CapabilityFormalContract(
        target_family="database",
        typed_preconditions=[EQ("db.online", True)],
        typed_postconditions=[EQ("table.dropped", True)],
        effect_footprint=[DELETE("db.users_table")],
        authority_required=AuthorityScope(
            level=AuthorityLevel.EXTERNAL_IRREVERSIBLE,
            allowed_actions={"drop_table"},
            allowed_resources={"db.users_table"},
        ),
        verifier=_validated_verifier(EQ("table.dropped", True)),
    )
    destructive_cap = OperationalCapability(
        id="db.drop_users_table",
        name="Drop Users Table",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
        route="atomic",
        formal_contract=destructive_contract,
    )
    registry.register(destructive_cap)

    router = CapabilityRouter(registry=registry)

    intent = OperationIntent(
        id="intent_drop",
        target="database",
        goal=EQ("table.dropped", True),
        effect_budget=[DELETE("db.users_table")],
        metadata={"target_family": "database"},
    )
    state = {"db": {"online": True}}
    # Caller only has low/read-only authority
    low_authority = AuthorityScope(
        level=AuthorityLevel.READ,
        allowed_actions={"read"},
    )

    # System-1 is 99.99% confident that db.drop_users_table should be chosen
    provider = FakeSystem1DecisionProvider(
        name="overconfident_system1",
        preset_answers={"preferred_candidate": "db.drop_users_table"},
        preset_confidence={"preferred_candidate": 0.9999},
    )
    register_system1_decision_provider(provider)

    try:
        decision = router.route(intent, state, low_authority)
        # MUST NOT be executable: no valid certificate can be minted!
        assert not isinstance(decision, ExecutableDecision)
        assert not decision.is_dispatchable
        # Must yield HumanDecision due to authority shortfall
        assert isinstance(decision, HumanDecision)
        assert decision.reason == "authority_required_missing"
    finally:
        unregister_system1_decision_provider(provider)
        reset_system1_decision()


def test_effect_budget_exceeded_blocked():
    """If candidate effects exceed the operation intent effect budget, dispatch is strictly blocked."""
    reset_system1_decision()

    registry = OperationalCapabilityRegistry()

    # Capability produces extra effect not allowed by intent budget
    contract = CapabilityFormalContract(
        target_family="filesystem",
        typed_preconditions=[EQ("file.readable", True)],
        typed_postconditions=[EQ("file.cleaned", True)],
        effect_footprint=[SET("file.cleaned", True), DELETE("file.backup")],
        authority_required=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"}),
        verifier=_validated_verifier(EQ("file.cleaned", True)),
    )
    cap = OperationalCapability(
        id="file.clean_and_delete_backup",
        name="Clean and delete backup",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
        route="atomic",
        formal_contract=contract,
    )
    registry.register(cap)

    router = CapabilityRouter(registry=registry)

    # Intent budget only permits SET("file.cleaned", True); forbids DELETE
    intent = OperationIntent(
        id="intent_budget_limited",
        target="filesystem",
        goal=EQ("file.cleaned", True),
        effect_budget=[SET("file.cleaned", True)],  # DELETE is omitted!
        metadata={"target_family": "filesystem"},
    )
    state = {"file": {"readable": True}}
    authority = AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"})

    provider = FakeSystem1DecisionProvider(
        name="test_budget_exceeded",
        preset_answers={"preferred_candidate": "file.clean_and_delete_backup"},
        preset_confidence={"preferred_candidate": 0.999},
    )
    register_system1_decision_provider(provider)

    try:
        decision = router.route(intent, state, authority)
        assert not isinstance(decision, ExecutableDecision)
        assert not decision.is_dispatchable
    finally:
        unregister_system1_decision_provider(provider)
        reset_system1_decision()

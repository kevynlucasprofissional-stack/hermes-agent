"""Tests for CP0: Predicate/Effect IR, OperationIntent, and Intent vs Authority contracts."""
from __future__ import annotations

import json
import pytest

from workstation.contracts import AcceptanceContract, IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.work_intent import WorkIntent, work_intent


def test_work_intent_backward_compatibility():
    """Prove WorkIntent continues working exactly as before."""
    envelope = MessageEnvelope(
        origin=MessageOrigin.HUMAN,
        intent_authority=IntentAuthority.CREATE_WORK,
        session_id="sess-123",
        content="do some work",
    )
    wi = work_intent(envelope)
    assert isinstance(wi, WorkIntent)
    assert wi.execution_class in {"INTERACTIVE_REASONING", "DETERMINISTIC_SINGLE", "DETERMINISTIC_BATCH", "BROWSER_TRANSACTION", "PROMPT_QUEUE"}
    assert wi.durability in {"turn", "durable"}
    assert wi.acceptance_policy is not None


def test_predicate_ir_deterministic_evaluation():
    from workstation.control_plane.ir import (
        EQ, NEQ, AND, OR, NOT, EXISTS, ABSENT, IN, SUBSET, LT, LTE, GT, GTE,
        UNCHANGED, TRANSITION, TRUE, FALSE
    )

    state = {
        "user": {"name": "Alice", "age": 30, "roles": ["admin", "editor"]},
        "repository": {"default_branch": "main", "status": "clean"},
        "pr": {"state": "open", "reviews": 2},
        "flags": {"feature_x": True},
    }

    assert TRUE().evaluate(state) is True
    assert FALSE().evaluate(state) is False

    assert EQ("user.name", "Alice").evaluate(state) is True
    assert EQ("user.age", 30).evaluate(state) is True
    assert NEQ("user.name", "Bob").evaluate(state) is True
    assert NEQ("user.age", 25).evaluate(state) is True

    assert EXISTS("repository.default_branch").evaluate(state) is True
    assert ABSENT("repository.deleted_field").evaluate(state) is True
    assert ABSENT("missing_key").evaluate(state) is True

    assert IN("admin", "user.roles").evaluate(state) is True
    assert IN("viewer", "user.roles").evaluate(state) is False
    assert SUBSET(["admin"], "user.roles").evaluate(state) is True

    assert LT("user.age", 40).evaluate(state) is True
    assert LTE("user.age", 30).evaluate(state) is True
    assert GT("pr.reviews", 1).evaluate(state) is True
    assert GTE("pr.reviews", 2).evaluate(state) is True

    assert AND(EQ("user.name", "Alice"), GT("user.age", 20)).evaluate(state) is True
    assert OR(EQ("user.name", "Bob"), EQ("user.name", "Alice")).evaluate(state) is True
    assert NOT(EQ("user.name", "Bob")).evaluate(state) is True

    # UNCHANGED compares against a baseline state in context
    context = {"baseline_state": {"repository": {"default_branch": "main"}}}
    assert UNCHANGED("repository.default_branch").evaluate(state, context=context) is True
    context_changed = {"baseline_state": {"repository": {"default_branch": "dev"}}}
    assert UNCHANGED("repository.default_branch").evaluate(state, context=context_changed) is False

    # TRANSITION checks before and after values
    assert TRANSITION("pr.state", "open", "merged").evaluate(
        {"pr": {"state": "merged"}},
        context={"baseline_state": {"pr": {"state": "open"}}}
    ) is True


def test_predicate_ir_canonical_serialization_and_hash():
    from workstation.control_plane.ir import EQ, AND, OR

    # AND operands order should be normalized canonically
    p1 = AND(EQ("b", 2), EQ("a", 1))
    p2 = AND(EQ("a", 1), EQ("b", 2))

    assert p1.to_dict() == p2.to_dict()
    assert p1.fingerprint() == p2.fingerprint()


def test_predicate_entailment():
    from workstation.control_plane.ir import EQ, AND, OR, TRUE, FALSE, entails

    p_a = EQ("pr.state", "merged")
    p_b = EQ("pr.merged_at", "2026-09-18")
    p_and = AND(p_a, p_b)

    assert entails(TRUE(), TRUE()) is True
    assert entails(p_a, p_a) is True
    # AND(A, B) entails A
    assert entails(p_and, p_a) is True
    assert entails(p_and, p_b) is True
    # A does NOT entail AND(A, B)
    assert entails(p_a, p_and) is False
    # A entails OR(A, B)
    assert entails(p_a, OR(p_a, p_b)) is True


def test_effect_ir_containment_and_invariants():
    from workstation.control_plane.ir import (
        SET, CREATE, DELETE, CALL, MOVE,
        UNCHANGED, ABSENT, EXISTS, EQ,
        effect_contained, preserves_invariant
    )

    budget = [
        CALL("github.pull_request.merge", "github.pull_request/123"),
        SET("github.pull_request/123.state", "merged"),
    ]

    allowed_call = CALL("github.pull_request.merge", "github.pull_request/123")
    forbidden_call = CALL("github.pull_request.close", "github.pull_request/123")
    forbidden_delete = DELETE("github.repository/main")

    assert effect_contained(allowed_call, budget) is True
    assert effect_contained(forbidden_call, budget) is False
    assert effect_contained(forbidden_delete, budget) is False

    # Invariant checks
    inv_unchanged = UNCHANGED("repository.default_branch")
    safe_effect = SET("pr.state", "merged")
    unsafe_effect = SET("repository.default_branch", "dev")
    unsafe_delete = DELETE("repository.default_branch")

    assert preserves_invariant(safe_effect, inv_unchanged) is True
    assert preserves_invariant(unsafe_effect, inv_unchanged) is False
    assert preserves_invariant(unsafe_delete, inv_unchanged) is False


def test_operation_intent_immutability_and_hash():
    from workstation.control_plane.intent import (
        OperationIntent, OperationMode, IntentRevision,
        canonical_operation_intent_json, operation_intent_hash
    )
    from workstation.control_plane.ir import EQ, UNCHANGED, CALL

    intent = OperationIntent(
        id="intent-001",
        mode=OperationMode.ACHIEVE,
        target="github.pull_request/123",
        goal=EQ("state", "merged"),
        invariants=[UNCHANGED("repository.default_branch")],
        effect_budget=[CALL("github.pull_request.merge", "github.pull_request/123")],
        authority_ref="envelope-auth-ref-1",
        acceptance=AcceptanceContract(policy="evidence"),
    )

    # Declarative: does not contain physical tools
    serialized = canonical_operation_intent_json(intent)
    assert "browser_click" not in serialized
    assert "work_execute" not in serialized

    h1 = operation_intent_hash(intent)
    h2 = operation_intent_hash(intent)
    assert h1 == h2
    assert len(h1) == 64

    # IntentRevision
    revised_intent = OperationIntent(
        id="intent-001-rev1",
        mode=OperationMode.ACHIEVE,
        target="github.pull_request/123",
        goal=EQ("state", "closed"),
        invariants=[UNCHANGED("repository.default_branch")],
        effect_budget=[CALL("github.pull_request.close", "github.pull_request/123")],
        authority_ref="envelope-auth-ref-2",
        lineage=["intent-001"],
    )
    h_revised = operation_intent_hash(revised_intent)
    assert h1 != h_revised

    revision = IntentRevision.create(
        parent_intent=intent,
        new_intent=revised_intent,
        reason="User requested close instead of merge",
        authority_ref="envelope-auth-ref-2",
    )
    assert revision.parent_intent_id == "intent-001"
    assert revision.old_hash == h1
    assert revision.new_hash == h_revised


def test_intent_is_not_authority():
    """Prove CanExecute(E) = IntentAllows(E) AND AuthorityAllows(E) AND PolicyAllows(E)."""
    from workstation.control_plane.lattice import (
        AuthorityLevel, AuthorityScope, can_execute_effect
    )
    from workstation.control_plane.ir import CALL, DELETE
    from workstation.control_plane.intent import OperationIntent, OperationMode

    call_merge = CALL("github.pull_request.merge", "repo/pr-123")
    delete_repo = DELETE("repo")

    # Intent allows merge only
    intent = OperationIntent(
        id="intent-002",
        mode=OperationMode.ACHIEVE,
        target="repo/pr-123",
        effect_budget=[call_merge],
        authority_ref="trusted-envelope-1",
    )

    # Authority grant allows merge AND delete_repo
    authority = AuthorityScope(
        level=AuthorityLevel.EXTERNAL_IRREVERSIBLE,
        allowed_actions={"github.pull_request.merge", "github.repository.delete"},
        allowed_resources={"repo", "repo/pr-123"},
    )

    # Policy allows both
    policy_allow = lambda effect: True

    # Case 1: Merge is allowed by Intent AND Authority AND Policy -> True
    assert can_execute_effect(call_merge, intent, authority, policy_eval=policy_allow) is True

    # Case 2: Delete repo is allowed by Authority and Policy, but NOT by Intent -> False
    assert can_execute_effect(delete_repo, intent, authority, policy_eval=policy_allow) is False

    # Case 3: Intent allows an action that Authority denies -> False
    restricted_authority = AuthorityScope(
        level=AuthorityLevel.READ,
        allowed_actions={"github.pull_request.read"},
        allowed_resources={"repo/pr-123"},
    )
    assert can_execute_effect(call_merge, intent, restricted_authority, policy_eval=policy_allow) is False

    # Case 4: Policy denies -> False
    policy_deny = lambda effect: False
    assert can_execute_effect(call_merge, intent, authority, policy_eval=policy_deny) is False

"""Behavior tests for CP2: Capability Router, Proof Obligations, RoutingCertificate, and Determinism Gate."""
from __future__ import annotations

import pytest

from workstation.contracts import AcceptanceContract
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.intent import OperationIntent, OperationMode, operation_intent_hash
from workstation.control_plane.ir import (
    AND, CALL, CREATE, DELETE, EQ, EXISTS, NOT, OR, SET, TRUE, UNCHANGED, Effect, Predicate
)
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.operational_capabilities import (
    CapabilityLifecycle, OperationalCapability, OperationalCapabilityRegistry
)


@pytest.fixture
def clean_registry(tmp_path):
    from workstation.artifacts import ArtifactStore
    store = ArtifactStore(tmp_path / "artifacts")
    return OperationalCapabilityRegistry(artifacts=store, root=tmp_path / "capabilities")


def test_router_satisfied_when_goal_already_met(clean_registry):
    """When the goal is already true in current semantic state -> SATISFIED, zero mutation."""
    from workstation.control_plane.router import CapabilityRouter, SatisfiedDecision

    intent = OperationIntent(
        id="intent-1",
        mode=OperationMode.ACHIEVE,
        target="repo/pr-123",
        goal=EQ("pr.state", "merged"),
        effect_budget=[CALL("github.pull_request.merge", "repo/pr-123")],
    )
    semantic_state = {"pr": {"state": "merged"}}
    router = CapabilityRouter(clean_registry)

    decision = router.route(
        operation_intent=intent,
        semantic_state=semantic_state,
        authority_scope=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"}),
    )

    assert isinstance(decision, SatisfiedDecision)
    assert decision.goal_satisfied is True
    assert decision.is_dispatchable is False


def test_router_exact_match_executable_produces_valid_certificate(clean_registry):
    """Exact compatible promoted capability produces ExecutableDecision with valid RoutingCertificate."""
    from workstation.control_plane.router import CapabilityRouter, ExecutableDecision, RoutingCertificate

    # Register promoted capability with formal contract
    cap = OperationalCapability(
        id="github.pr.merge",
        name="Merge GitHub PR",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="scm.pull_request.merge",
            target_family="github.pull_request",
            typed_preconditions=[EQ("pr.state", "open"), EQ("pr.mergeable", True)],
            typed_postconditions=[EQ("pr.state", "merged"), EXISTS("pr.merged_at")],
            effect_footprint=[CALL("github.pull_request.merge", "repo/pr-123"), SET("pr.state", "merged")],
            authority_required=AuthorityScope(
                level=AuthorityLevel.EXTERNAL_REVERSIBLE,
                allowed_actions={"github.pull_request.merge"},
                allowed_resources={"repo/pr-123"},
            ),
            preserves=[UNCHANGED("repo.default_branch")],
            verifier={"kind": "api_check", "evidence_strength": "E2"},
        ),
    )
    clean_registry.register(cap)

    intent = OperationIntent(
        id="intent-merge-1",
        target="repo/pr-123",
        goal=EQ("pr.state", "merged"),
        invariants=[UNCHANGED("repo.default_branch")],
        effect_budget=[
            CALL("github.pull_request.merge", "repo/pr-123"),
            SET("pr.state", "merged"),
        ],
        acceptance=AcceptanceContract(policy="evidence"),
    )

    semantic_state = {
        "pr": {"state": "open", "mergeable": True},
        "repo": {"default_branch": "main"},
    }

    granted_authority = AuthorityScope(
        level=AuthorityLevel.EXTERNAL_REVERSIBLE,
        allowed_actions={"github.pull_request.merge"},
        allowed_resources={"repo/pr-123"},
    )

    router = CapabilityRouter(clean_registry)
    decision = router.route(
        operation_intent=intent,
        semantic_state=semantic_state,
        authority_scope=granted_authority,
    )

    assert isinstance(decision, ExecutableDecision)
    assert decision.is_dispatchable is True
    assert decision.capability.id == "github.pr.merge"
    assert isinstance(decision.certificate, RoutingCertificate)
    assert decision.certificate.is_valid() is True
    assert decision.certificate.goal_coverage is True
    assert decision.certificate.effect_containment is True
    assert decision.certificate.invariant_preservation is True
    assert decision.certificate.authority_satisfied is True
    assert decision.certificate.preconditions_hold is True


def test_router_rejects_on_false_precondition(clean_registry):
    """If capability preconditions are false in current state -> cannot EXECUTE."""
    from workstation.control_plane.router import CapabilityRouter, ExecutableDecision

    cap = OperationalCapability(
        id="github.pr.merge",
        name="Merge GitHub PR",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="scm.pull_request.merge",
            target_family="github.pull_request",
            typed_preconditions=[EQ("pr.state", "open"), EQ("pr.mergeable", True)],
            typed_postconditions=[EQ("pr.state", "merged")],
            effect_footprint=[CALL("github.pull_request.merge", "repo/pr-123")],
            authority_required=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"github.pull_request.merge"}),
        ),
    )
    clean_registry.register(cap)

    intent = OperationIntent(
        id="intent-1",
        target="repo/pr-123",
        goal=EQ("pr.state", "merged"),
        effect_budget=[CALL("github.pull_request.merge", "repo/pr-123")],
    )

    # pr.mergeable is False!
    semantic_state = {"pr": {"state": "open", "mergeable": False}}

    router = CapabilityRouter(clean_registry)
    decision = router.route(
        operation_intent=intent,
        semantic_state=semantic_state,
        authority_scope=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"github.pull_request.merge"}),
    )

    assert not isinstance(decision, ExecutableDecision)


def test_router_rejects_forbidden_extra_effect_goal_non_expansion(clean_registry):
    """Goal non-expansion: capability covering goal but producing extra forbidden effects MUST reject."""
    from workstation.control_plane.router import CapabilityRouter, ExecutableDecision

    # Capability merges PR AND deletes repo!
    cap = OperationalCapability(
        id="rogue.merge",
        name="Merge PR and Delete Repo",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="scm.pull_request.merge",
            target_family="github.pull_request",
            typed_preconditions=[EQ("pr.state", "open")],
            typed_postconditions=[EQ("pr.state", "merged")],
            effect_footprint=[
                CALL("github.pull_request.merge", "repo/pr-123"),
                DELETE("github.repository/full_repo"),
            ],
            authority_required=AuthorityScope(level=AuthorityLevel.EXTERNAL_IRREVERSIBLE, allowed_actions={"*"}),
        ),
    )
    clean_registry.register(cap)

    # Intent only allows merging PR
    intent = OperationIntent(
        id="intent-1",
        target="repo/pr-123",
        goal=EQ("pr.state", "merged"),
        effect_budget=[CALL("github.pull_request.merge", "repo/pr-123")],
    )

    semantic_state = {"pr": {"state": "open"}}
    router = CapabilityRouter(clean_registry)

    decision = router.route(
        operation_intent=intent,
        semantic_state=semantic_state,
        authority_scope=AuthorityScope(level=AuthorityLevel.EXTERNAL_IRREVERSIBLE, allowed_actions={"*"}),
    )

    assert not isinstance(decision, ExecutableDecision)


def test_router_rejects_invariant_violation(clean_registry):
    """Capability that achieves goal but destroys an invariant MUST reject."""
    from workstation.control_plane.router import CapabilityRouter, ExecutableDecision

    cap = OperationalCapability(
        id="git.reset_hard",
        name="Hard reset",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="git.sync",
            target_family="git.repository",
            typed_preconditions=[TRUE()],
            typed_postconditions=[EQ("repo.in_sync", True)],
            effect_footprint=[SET("repo.in_sync", True), DELETE("repo.uncommitted_changes")],
            authority_required=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"*"}),
        ),
    )
    clean_registry.register(cap)

    # Invariant: preserve uncommitted changes!
    intent = OperationIntent(
        id="intent-sync",
        target="repo",
        goal=EQ("repo.in_sync", True),
        invariants=[UNCHANGED("repo.uncommitted_changes")],
        effect_budget=[SET("repo.in_sync", True), DELETE("repo.uncommitted_changes")],
    )

    semantic_state = {"repo": {"in_sync": False, "uncommitted_changes": "stash-1"}}
    router = CapabilityRouter(clean_registry)

    decision = router.route(
        operation_intent=intent,
        semantic_state=semantic_state,
        authority_scope=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"*"}),
    )

    assert not isinstance(decision, ExecutableDecision)


def test_router_rejects_insufficient_authority_asks_human(clean_registry):
    """When capability is otherwise valid but authority is insufficient -> ASK_HUMAN decision."""
    from workstation.control_plane.router import CapabilityRouter, ExecutableDecision, HumanDecision

    cap = OperationalCapability(
        id="github.pr.merge",
        name="Merge GitHub PR",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="scm.pull_request.merge",
            target_family="github.pull_request",
            typed_preconditions=[EQ("pr.state", "open")],
            typed_postconditions=[EQ("pr.state", "merged")],
            effect_footprint=[CALL("github.pull_request.merge", "repo/pr-123")],
            authority_required=AuthorityScope(
                level=AuthorityLevel.EXTERNAL_REVERSIBLE,
                allowed_actions={"github.pull_request.merge"},
            ),
        ),
    )
    clean_registry.register(cap)

    intent = OperationIntent(
        id="intent-1",
        target="repo/pr-123",
        goal=EQ("pr.state", "merged"),
        effect_budget=[CALL("github.pull_request.merge", "repo/pr-123")],
    )

    semantic_state = {"pr": {"state": "open"}}
    # Granted authority is only READ!
    granted_authority = AuthorityScope(level=AuthorityLevel.READ, allowed_actions={"*"})

    router = CapabilityRouter(clean_registry)
    decision = router.route(
        operation_intent=intent,
        semantic_state=semantic_state,
        authority_scope=granted_authority,
    )

    assert isinstance(decision, HumanDecision)
    assert decision.reason == "authority_required_missing"


def test_router_uncertain_mutation_dominates_and_reconciles(clean_registry):
    """Relevant outstanding uncertain mutation blocks new mutable dispatch."""
    from workstation.control_plane.router import CapabilityRouter, ExecutableDecision, ReasoningDecision

    cap = OperationalCapability(
        id="github.pr.merge",
        name="Merge GitHub PR",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="scm.pull_request.merge",
            target_family="github.pull_request",
            typed_preconditions=[EQ("pr.state", "open")],
            typed_postconditions=[EQ("pr.state", "merged")],
            effect_footprint=[CALL("github.pull_request.merge", "repo/pr-123")],
            authority_required=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"}),
        ),
    )
    clean_registry.register(cap)

    intent = OperationIntent(
        id="intent-1",
        target="repo/pr-123",
        goal=EQ("pr.state", "merged"),
        effect_budget=[CALL("github.pull_request.merge", "repo/pr-123")],
    )

    semantic_state = {"pr": {"state": "open"}}

    # Runtime state has uncertain mutation on target
    runtime_state = {
        "outstanding_uncertain_mutations": [
            {"target": "repo/pr-123", "operation_id": "op-999", "status": "uncertain"}
        ]
    }

    router = CapabilityRouter(clean_registry)
    decision = router.route(
        operation_intent=intent,
        semantic_state=semantic_state,
        authority_scope=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"}),
        runtime_state=runtime_state,
    )

    assert not isinstance(decision, ExecutableDecision)
    assert decision.requires_reconciliation is True


def test_preflight_revalidation_detects_stale_world():
    """State change after routing invalidates certificate before mutable dispatch."""
    from workstation.control_plane.router import RoutingCertificate, revalidate_certificate

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
        verifier_available=True,
        evidence_strength_sufficient=True,
        state_fresh=True,
        capability_healthy=True,
        no_outstanding_uncertainty=True,
        deterministic_closure=True,
        intent_hash="hash-1",
        semantic_state_hash="state-hash-v1",
        capability_id="cap-1",
        capability_version="1.0.0",
        router_policy_version="1.0.0",
        run_id="run-1",
        operation_id="op-1",
    )
    assert cert.is_valid() is True

    # Fresh state matches
    assert revalidate_certificate(
        cert,
        current_intent_hash="hash-1",
        current_state_hash="state-hash-v1",
        current_cap_version="1.0.0",
        run_id="run-1",
        has_uncertain_mutation=False,
    ) is True

    # State changed to v2 -> revalidation FAILS and marks certificate invalid
    assert revalidate_certificate(
        cert,
        current_intent_hash="hash-1",
        current_state_hash="state-hash-v2",
        current_cap_version="1.0.0",
        run_id="run-1",
        has_uncertain_mutation=False,
    ) is False
    assert cert.is_valid() is False
    assert cert.state_fresh is False


def test_metamorphic_property_invariants(clean_registry):
    """Property tests: adding irrelevant authority does not change decision; removing required halts execution."""
    from workstation.control_plane.router import CapabilityRouter, ExecutableDecision

    cap = OperationalCapability(
        id="fs.create_file",
        name="Create File",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="fs.create",
            target_family="filesystem.file",
            typed_preconditions=[EXISTS("dir")],
            typed_postconditions=[EXISTS("dir/file.txt")],
            effect_footprint=[CREATE("dir/file.txt")],
            authority_required=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"create"}, allowed_resources={"dir/file.txt"}),
            preserves=[UNCHANGED("dir/other.txt")],
            verifier={"kind": "fs_stat", "evidence_strength": "E2"},
        ),
    )
    clean_registry.register(cap)

    intent = OperationIntent(
        id="intent-fs",
        target="dir/file.txt",
        goal=EXISTS("dir/file.txt"),
        invariants=[UNCHANGED("dir/other.txt")],
        effect_budget=[CREATE("dir/file.txt")],
    )

    state = {"dir": {"exists": True}, "dir/other.txt": "preserved"}
    base_auth = AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"create"}, allowed_resources={"dir/file.txt"})

    router = CapabilityRouter(clean_registry)
    d1 = router.route(intent, state, base_auth)
    assert isinstance(d1, ExecutableDecision)

    # Metamorphic 1: Adding irrelevant authority does NOT change execution
    expanded_auth = AuthorityScope(
        level=AuthorityLevel.EXTERNAL_IRREVERSIBLE,
        allowed_actions={"create", "delete", "format_disk"},
        allowed_resources={"dir/file.txt", "unrelated_res"},
    )
    d2 = router.route(intent, state, expanded_auth)
    assert isinstance(d2, ExecutableDecision)
    assert d2.capability.id == d1.capability.id

    # Metamorphic 2: Removing required action halts execution
    diminished_auth = AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"read_only"}, allowed_resources={"dir/file.txt"})
    d3 = router.route(intent, state, diminished_auth)
    assert not isinstance(d3, ExecutableDecision)

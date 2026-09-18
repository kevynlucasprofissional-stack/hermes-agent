"""Behavior tests for CP6, CP7, CP8 and integration with TaskCompiler/work_execute."""
from __future__ import annotations

import pytest

from workstation.artifacts import ArtifactStore
from workstation.contracts import AcceptanceContract, IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.intent import OperationIntent, OperationMode
from workstation.control_plane.ir import CALL, CREATE, EQ, EXISTS, SET, TRUE, UNCHANGED
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.operational_capabilities import (
    CapabilityLifecycle, OperationalCapability, OperationalCapabilityRegistry
)


@pytest.fixture
def clean_env(tmp_path):
    artifacts = ArtifactStore(tmp_path / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts=artifacts, root=tmp_path / "capabilities")
    return artifacts, registry


def test_attention_packet_and_open_condition(clean_env):
    """Prove reasoning handoff bundles minimal OpenCondition and AttentionPacket."""
    from workstation.reasoning_handoff import (
        AttentionPacket, OpenCondition, create_attention_packet, needs_reasoning
    )

    artifacts, _ = clean_env

    open_cond = OpenCondition(
        condition_type="SEMANTIC_GAP",
        proposition="merge_conflict_resolution_strategy == unknown",
        known_facts={"pr_id": 123, "conflicting_files": ["app.py"]},
        available_authority={"modify_files": True},
        remaining_subgraph=[{"step": "resolve_conflicts"}, {"step": "complete_merge"}],
    )

    packet = AttentionPacket(
        intent_id="intent-conflict-1",
        intent_hash="hash-123",
        expected="Clean branch without merge conflicts",
        observed="Conflict on app.py",
        open_condition=open_cond,
        available_authority={"modify_files": True},
        safe_to_resume=True,
    )

    handoff = needs_reasoning(
        artifacts,
        "owner-task-1",
        completed_until="checkout",
        expected=packet.expected,
        observed=packet.observed,
        safe_to_resume=packet.safe_to_resume,
        context={"attention_packet": packet.to_dict()},
    )

    assert handoff["status"] == "NEEDS_REASONING"
    assert "state_ref" in handoff

    # Read back persisted packet
    stored = artifacts.read_json(handoff["state_ref"])
    stored_packet = stored["context"]["attention_packet"]
    assert stored_packet["intent_id"] == "intent-conflict-1"
    assert stored_packet["open_condition"]["proposition"] == "merge_conflict_resolution_strategy == unknown"


def test_llm_proposal_requires_router_re_admission(clean_env):
    """LLM proposed plan fragment or intent refinement must return to Router; cannot bypass admission."""
    from workstation.control_plane.router import CapabilityRouter, ExecutableDecision

    _, registry = clean_env
    router = CapabilityRouter(registry)

    # Capability registered in library
    cap = OperationalCapability(
        id="resolve.rebase",
        name="Resolve via Rebase",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="git.rebase",
            target_family="git.branch",
            typed_preconditions=[EQ("branch.state", "diverged")],
            typed_postconditions=[EQ("branch.state", "rebased")],
            effect_footprint=[CALL("git.rebase", "feature-branch")],
            authority_required=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"git.rebase"}, allowed_resources={"feature-branch"}),
            verifier={"kind": "v"},
        ),
    )
    registry.register(cap)

    # LLM proposes an updated OperationIntent
    llm_proposed_intent = OperationIntent(
        id="intent-rebase-proposal",
        target="feature-branch",
        goal=EQ("branch.state", "rebased"),
        effect_budget=[CALL("git.rebase", "feature-branch")],
    )

    # Must pass through Router for verification
    state = {"branch": {"state": "diverged"}}
    authority = AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"git.rebase"}, allowed_resources={"feature-branch"})

    decision = router.route(llm_proposed_intent, state, authority)
    assert isinstance(decision, ExecutableDecision)
    assert decision.is_dispatchable is True
    assert decision.capability.id == "resolve.rebase"


def test_skill_capability_family_resolution_without_physical_pins(clean_env):
    """Skills declare semantic family dependencies; Router resolves concrete implementation."""
    from workstation.control_plane.router import CapabilityRouter, ExecutableDecision

    _, registry = clean_env

    # Implementation 1: GitHub implementation
    github_cap = OperationalCapability(
        id="github.pr.merge.v2",
        name="GitHub PR Merge",
        version="2.0.0",
        family_id="scm.pull_request.merge",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="scm.pull_request.merge",
            target_family="github.pull_request",
            typed_preconditions=[EQ("pr.state", "open")],
            typed_postconditions=[EQ("pr.state", "merged")],
            effect_footprint=[CALL("github.pull_request.merge", "gh/pr-1")],
            authority_required=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"}),
            verifier={"kind": "v"},
        ),
    )
    registry.register(github_cap)

    # Implementation 2: GitLab implementation
    gitlab_cap = OperationalCapability(
        id="gitlab.mr.merge.v1",
        name="GitLab MR Merge",
        version="1.0.0",
        family_id="scm.pull_request.merge",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="scm.pull_request.merge",
            target_family="gitlab.merge_request",
            typed_preconditions=[EQ("mr.state", "opened")],
            typed_postconditions=[EQ("mr.state", "merged")],
            effect_footprint=[CALL("gitlab.merge_request.merge", "gl/mr-1")],
            authority_required=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"}),
            verifier={"kind": "v"},
        ),
    )
    registry.register(gitlab_cap)

    router = CapabilityRouter(registry)

    # Intent requests family via target "github.pull_request"
    gh_intent = OperationIntent(
        id="intent-gh",
        target="github.pull_request/pr-1",
        goal=EQ("pr.state", "merged"),
        effect_budget=[CALL("github.pull_request.merge", "gh/pr-1")],
        metadata={"target_family": "github.pull_request"},
    )
    d_gh = router.route(
        gh_intent,
        {"pr": {"state": "open"}},
        AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"*"}),
    )
    assert isinstance(d_gh, ExecutableDecision)
    assert d_gh.capability.id == "github.pr.merge.v2"


def test_shadow_router_mode(clean_env):
    """Shadow Router computes what it WOULD decide without dispatching mutable I/O."""
    from workstation.control_plane.metrics import ShadowRouter
    from workstation.control_plane.router import CapabilityRouter, ExecutableDecision

    _, registry = clean_env
    cap = OperationalCapability(
        id="test_cap",
        name="Test",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            typed_preconditions=[TRUE()],
            typed_postconditions=[EQ("status", "done")],
            effect_footprint=[SET("status", "done")],
            authority_required=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"set"}),
            verifier={"kind": "v"},
        ),
    )
    registry.register(cap)

    router = CapabilityRouter(registry)
    shadow = ShadowRouter(router)

    intent = OperationIntent(
        id="intent-shadow",
        goal=EQ("status", "done"),
        effect_budget=[SET("status", "done")],
    )

    record = shadow.evaluate_shadow(
        intent,
        semantic_state={"status": "pending"},
        authority_scope=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"set"}),
    )

    assert record["would_decision"] == "EXECUTE"
    assert record["would_capability_id"] == "test_cap"
    assert record["mutations_dispatched"] == 0  # Zero mutations dispatched!


def test_failure_attribution():
    """Prove failure attribution classifies INTENT_ERROR vs CAPABILITY_DRIFT vs ROUTING_ERROR."""
    from workstation.control_plane.metrics import FailureAttributor, FailureClass

    attributor = FailureAttributor()

    # Precondition held at routing, but postcondition failed after execution -> CAPABILITY_DRIFT
    c1 = attributor.classify(
        certificate_valid=True,
        preconditions_held_at_dispatch=True,
        execution_error=None,
        postconditions_verified=False,
    )
    assert c1 == FailureClass.CAPABILITY_DRIFT

    # Execution threw a runtime network error -> RUNTIME_FAILURE
    c2 = attributor.classify(
        certificate_valid=True,
        preconditions_held_at_dispatch=True,
        execution_error="ConnectionRefusedError",
        postconditions_verified=False,
    )
    assert c2 == FailureClass.RUNTIME_FAILURE

    # Certificate was invalid from the start -> ROUTING_ERROR
    c3 = attributor.classify(
        certificate_valid=False,
        preconditions_held_at_dispatch=False,
        execution_error=None,
        postconditions_verified=False,
    )
    assert c3 == FailureClass.ROUTING_ERROR


def test_volc_metrics_vector():
    """Verified Outcome Lifetime Cost retains explicit vector and unknown metrics remain None."""
    from workstation.control_plane.metrics import VOLCMetrics, calculate_volc

    metrics = calculate_volc(
        verified_outcomes=5,
        llm_calls=2,
        tokens=1500,
        cpu_seconds=3.2,
        wall_time_seconds=12.5,
        tool_calls=10,
        polls=4,
        human_interventions=0,
        # tokens_cost_usd is UNKNOWN
        tokens_cost_usd=None,
    )

    assert isinstance(metrics, VOLCMetrics)
    assert metrics.llm_calls_per_outcome == 2 / 5
    assert metrics.tokens_per_outcome == 1500 / 5
    assert metrics.tool_calls_per_outcome == 10 / 5
    assert metrics.cost_usd_per_outcome is None  # Unknown remains None/null!


def test_task_compiler_work_execute_route_action(clean_env):
    """work_execute with action='route' integrates with CapabilityRouter and executes certified capability."""
    from workstation.task_compiler import TaskCompiler

    artifacts, registry = clean_env

    # Register capability in registry
    cap = OperationalCapability(
        id="fs.mkdir_task",
        name="Make directory",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="fs.mkdir",
            target_family="filesystem",
            typed_preconditions=[TRUE()],
            typed_postconditions=[EXISTS("new_folder")],
            effect_footprint=[CREATE("new_folder")],
            authority_required=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"create"}),
            verifier={"kind": "fs_stat"},
        ),
        implementation={"steps": [{"primitive": "mkdir", "args": {"path": "new_folder"}}]},
    )
    registry.register(cap)

    compiler = TaskCompiler(artifacts=artifacts)

    intent_dict = {
        "id": "intent-mkdir",
        "target": "filesystem/new_folder",
        "goal": {"type": "EXISTS", "path": "new_folder"},
        "effect_budget": [{"kind": "CREATE", "resource": "new_folder"}],
    }

    result = compiler.execute(
        {
            "action": "route",
            "operation_intent": intent_dict,
            "semantic_state": {"new_folder": {"exists": False}},
            "authority": {"level": 1, "allowed_actions": ["create"], "allowed_resources": ["*"]},
        },
        task_id="task-test-route",
        session_id="sess-route-1",
        dispatch=lambda tool, args, t_id, s_id: {"exists": True},
    )

    assert result["success"] is True
    assert result.get("routing_decision") in {"EXECUTE", "EXECUTABLE"}
    assert result.get("capability_id") == "fs.mkdir_task"
    assert "certificate_hash" in result

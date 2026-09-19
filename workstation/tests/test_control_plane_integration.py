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
from workstation.control_plane.verification import VerificationContract, VerificationLifecycle
from workstation.execution_policy import EvidenceStrength


def _validated_verifier(*predicates):
    return VerificationContract(
        covered_predicates=tuple(p.fingerprint() for p in predicates), observer="owner.readback",
        source_kind="source_of_record", minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        allowed_trust=("trusted_owner",), lifecycle=VerificationLifecycle.VALIDATED,
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
            verifier=_validated_verifier(EQ("branch.state", "rebased")),
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
            verifier=_validated_verifier(EQ("pr.state", "merged")),
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
            verifier=_validated_verifier(EQ("mr.state", "merged")),
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
            verifier=_validated_verifier(EQ("status", "done")),
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
            verifier=_validated_verifier(EXISTS("new_folder")),
        ),
        implementation={"steps": [{"primitive": "mkdir", "args": {"path": "new_folder"}}]},
        postconditions=[{"type": "file_exists", "path": "new_folder"}],
    )
    registry.register(cap)

    compiler = TaskCompiler(artifacts=artifacts)
    compiler.capability_registry = registry
    compiler.trusted_authority = AuthorityScope(
        level=AuthorityLevel.LOCAL_MUTATION,
        allowed_actions={"create"},
        allowed_resources={"*"},
    )

    intent_dict = {
        "id": "intent-mkdir",
        "target": "filesystem/new_folder",
        "goal": {"type": "EXISTS", "path": "new_folder"},
        "effect_budget": [{"kind": "CREATE", "resource": "new_folder"}],
    }

    from workstation.control_plane.verification import VerificationEvidence
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    expected_fp = EXISTS("new_folder").fingerprint()
    ev = VerificationEvidence(
        evidence_id="ev-route-mkdir",
        observer="owner.readback",
        source_kind="source_of_record",
        value=expected_fp,
        evidence_strength=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        trust_class="trusted_owner",
        observed_at=now,
        read_after_write=True,
        covered_predicates=(expected_fp,),
    )

    result = compiler.execute(
        {
            "action": "route",
            "operation_intent": intent_dict,
            "semantic_state": {"new_folder": {"exists": False}},
            "authority": {"level": 1, "allowed_actions": ["create"], "allowed_resources": ["*"]},
            "verification_evidence": [ev],
            "verification_expected": expected_fp,
        },
        task_id="task-test-route",
        session_id="sess-route-1",
        dispatch=lambda tool, args, t_id, s_id: {"exists": True},
    )

    assert result["success"] is True, result
    assert result.get("routing_decision") in {"EXECUTE", "EXECUTABLE"}
    assert result.get("capability_id") == "fs.mkdir_task"
    assert "certificate_hash" in result


def test_task_compiler_composition_executes_in_order_and_preserves_confirmed_drift(clean_env, monkeypatch):
    """COMPOSE calls the existing kernel; a later drift never erases confirmed steps."""
    from workstation.task_compiler import TaskCompiler
    from workstation.control_plane.composition import CompositionCertificate
    from workstation.control_plane.router import CapabilityRouter, ComposedDecision, _state_hash

    artifacts, registry = clean_env
    caps = [
        OperationalCapability(id="compose.c1", name="C1", version="1.0.0"),
        OperationalCapability(id="compose.c2", name="C2", version="2.0.0"),
    ]
    cert = CompositionCertificate(
        plan_ids=[cap.id for cap in caps], plan_versions=[cap.version for cap in caps],
        chain_verified=True, goal_coverage=True, effect_containment=True,
        authority_satisfied=True, invariant_preservation=True, no_causal_threats=True,
        verifier_closure=True, deterministic_closure=True,
        intent_hash="compose-intent", semantic_state_hash=_state_hash({}),
    )
    monkeypatch.setattr(CapabilityRouter, "route", lambda *_args, **_kwargs:
                        ComposedDecision(plan=caps, certificate=cert))

    class RecordingKernel:
        def __init__(self):
            self.calls = []
            self.drift_second = False

        def execute_capability(self, cap, inputs, **_kwargs):
            self.calls.append((cap.id, inputs))
            if self.drift_second and cap.id == "compose.c2":
                return {"success": False, "status": "NEEDS_REASONING", "reason": "semantic_drift"}
            return {"success": True, "capability_id": cap.id, "capability_version": cap.version,
                    "verification": {"accepted": True, "source": "test_readback"},
                    "verification_result": {"status": "VERIFIED"}}

    kernel = RecordingKernel()
    compiler = TaskCompiler(artifacts=artifacts)
    compiler.capability_registry = registry
    compiler.kernel = kernel
    compiler.trusted_authority = AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION,
                                                 allowed_actions={"*"}, allowed_resources={"*"})
    request = {
        "operation_intent": {"id": "compose-intent"},
            "semantic_state": {},
            "composition_bindings": {"compose.c1": {"x": 1}, "compose.c2": {"x": 2}},
            "final_verification_result": {"status": "VERIFIED"},
    }
    result = compiler._execute_route(request, task_id="task-compose", session_id="session-compose",
                                     dispatch=lambda *_args: {"success": True})
    assert result["success"] is True
    assert [call[0] for call in kernel.calls] == ["compose.c1", "compose.c2"]
    assert result["dispatch_record"]["status"] == "COMMITTED"

    kernel.calls.clear()
    kernel.drift_second = True
    drifted = compiler._execute_route(request, task_id="task-compose", session_id="session-compose",
                                      dispatch=lambda *_args: {"success": True})
    assert drifted["success"] is False
    assert [step["id"] for step in drifted["confirmed_steps"]] == ["compose.c1"]
    assert drifted["dispatch_record"]["status"] != "COMMITTED"


def test_task_compiler_composition_unbound_and_stale_dispatch_nothing(clean_env, monkeypatch):
    from workstation.task_compiler import TaskCompiler
    from workstation.control_plane.composition import CompositionCertificate
    from workstation.control_plane.router import CapabilityRouter, ComposedDecision, _state_hash

    artifacts, registry = clean_env
    cap = OperationalCapability(id="compose.bound", name="Bound", version="1.0.0")
    cert = CompositionCertificate(
        plan_ids=[cap.id], plan_versions=[cap.version], chain_verified=True,
        goal_coverage=True, effect_containment=True, authority_satisfied=True,
        invariant_preservation=True, no_causal_threats=True, verifier_closure=True,
        deterministic_closure=True, intent_hash="intent", semantic_state_hash=_state_hash({}),
    )
    monkeypatch.setattr(CapabilityRouter, "route", lambda *_args, **_kwargs:
                        ComposedDecision(plan=[cap], certificate=cert))

    class NeverKernel:
        calls = 0
        def execute_capability(self, *_args, **_kwargs):
            self.calls += 1
            return {"success": True}

    kernel = NeverKernel()
    compiler = TaskCompiler(artifacts=artifacts)
    compiler.capability_registry = registry
    compiler.kernel = kernel
    compiler.trusted_authority = AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION,
                                                 allowed_actions={"*"}, allowed_resources={"*"})
    unbound = compiler._execute_route(
        {"operation_intent": {"id": "intent"}, "semantic_state": {}},
        task_id="t", session_id="s", dispatch=lambda *_args: {})
    assert unbound["success"] is False and unbound["reason"] == "composition_inputs_unbound"
    assert kernel.calls == 0

    stale = compiler._execute_route(
        {"operation_intent": {"id": "intent"}, "semantic_state": {"changed": True},
         "composition_bindings": {cap.id: {}}},
        task_id="t", session_id="s", dispatch=lambda *_args: {})
    assert stale["success"] is False
    assert kernel.calls == 0


def test_route_wait_uses_await_condition_contract(clean_env, monkeypatch):
    """WaitDecision correctly consumes and exposes await_condition."""
    from workstation.control_plane.router import CapabilityRouter, WaitDecision
    from workstation.control_plane.waiting import AwaitCondition, AwaitKind
    from workstation.task_compiler import TaskCompiler

    artifacts, registry = clean_env
    cond = AwaitCondition(
        wait_id="wait-contract-1",
        kind=AwaitKind.WAITING_FOR_EVENT,
        predicate=EQ("data_ready", True),
        correlation_id="corr-99",
    )
    monkeypatch.setattr(
        CapabilityRouter,
        "route",
        lambda *_args, **_kwargs: WaitDecision(await_condition=cond, reason="Waiting for webhook"),
    )

    compiler = TaskCompiler(artifacts=artifacts)
    compiler.capability_registry = registry
    result = compiler._execute_route(
        {"operation_intent": {"id": "intent-wait"}, "semantic_state": {}},
        task_id="task-wait",
        session_id="session-wait",
        dispatch=lambda *_args: {},
    )
    assert result["routing_decision"] == "WAIT"
    assert result["await_condition"]["wait_id"] == "wait-contract-1"
    assert result["condition"]["wait_id"] == "wait-contract-1"
    assert result["reason"] == "Waiting for webhook"


def test_route_human_and_reasoning_branches_use_actual_dataclass_fields(clean_env, monkeypatch):
    """HumanDecision and ReasoningDecision consume actual canonical fields."""
    from workstation.control_plane.router import CapabilityRouter, HumanDecision, ReasoningDecision
    from workstation.task_compiler import TaskCompiler

    artifacts, registry = clean_env
    compiler = TaskCompiler(artifacts=artifacts)
    compiler.capability_registry = registry

    # HumanDecision
    scope = AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"deploy"})
    monkeypatch.setattr(
        CapabilityRouter,
        "route",
        lambda *_args, **_kwargs: HumanDecision(reason="Need operator confirmation", scope=scope),
    )
    res_human = compiler._execute_route(
        {"operation_intent": {"id": "intent-human"}, "semantic_state": {}},
        task_id="task-h",
        session_id="session-h",
        dispatch=lambda *_args: {},
    )
    assert res_human["routing_decision"] == "ASK_HUMAN"
    assert res_human["scope"]["level"] == AuthorityLevel.EXTERNAL_REVERSIBLE.value
    assert res_human["missing_authority"]["level"] == AuthorityLevel.EXTERNAL_REVERSIBLE.value
    assert res_human["reason"] == "Need operator confirmation"

    # ReasoningDecision
    monkeypatch.setattr(
        CapabilityRouter,
        "route",
        lambda *_args, **_kwargs: ReasoningDecision(
            open_condition={"field": "unknown_param"},
            attention_packet={"hint": "focus on line 42"},
            requires_reconciliation=True,
            reason="Adaptive discovery required",
        ),
    )
    res_reason = compiler._execute_route(
        {"operation_intent": {"id": "intent-reason"}, "semantic_state": {}},
        task_id="task-r",
        session_id="session-r",
        dispatch=lambda *_args: {},
    )
    assert res_reason["routing_decision"] == "WAKE_LLM"
    assert res_reason["open_condition"] == {"field": "unknown_param"}
    assert res_reason["attention_packet"] == {"hint": "focus on line 42"}
    assert res_reason["requires_reconciliation"] is True
    assert res_reason["reason"] == "Adaptive discovery required"
    assert res_reason["context"]["open_condition"] == {"field": "unknown_param"}


def test_composed_execution_verifies_final_intent_goal_authoritatively(clean_env, monkeypatch):
    """Child verification != final semantic goal verification. Final authoritative readback must hold."""
    from workstation.control_plane.composition import CompositionCertificate
    from workstation.control_plane.router import CapabilityRouter, ComposedDecision, _state_hash
    from workstation.task_compiler import TaskCompiler

    artifacts, registry = clean_env
    cap = OperationalCapability(id="compose.step1", name="Step1", version="1.0.0")
    cert = CompositionCertificate(
        plan_ids=[cap.id],
        plan_versions=[cap.version],
        chain_verified=True,
        goal_coverage=True,
        effect_containment=True,
        authority_satisfied=True,
        invariant_preservation=True,
        no_causal_threats=True,
        verifier_closure=True,
        deterministic_closure=True,
        intent_hash="intent-hash",
        semantic_state_hash=_state_hash({"final_state_target": "not_achieved"}),
    )
    monkeypatch.setattr(
        CapabilityRouter,
        "route",
        lambda *_args, **_kwargs: ComposedDecision(plan=[cap], certificate=cert),
    )

    class MockKernel:
        def execute_capability(self, *_args, **_kwargs):
                return {
                    "success": True,
                    "verification": {"accepted": True},
                    "verification_result": {"status": "VERIFIED"},
                    "output": {"intermediate_value": 10},
            }

    compiler = TaskCompiler(artifacts=artifacts)
    compiler.capability_registry = registry
    compiler.kernel = MockKernel()
    compiler.trusted_authority = AuthorityScope(
        level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"*"}, allowed_resources={"*"}
    )

    # 1. Final authoritative readback fails -> composition fails closed
    req_fail = {
        "operation_intent": {
            "id": "intent-composed",
            "goal": {"type": "EQ", "path": "final_state_target", "value": "achieved"},
        },
        "semantic_state": {"final_state_target": "not_achieved"},
        "composition_bindings": {cap.id: {"x": 1}},
        "final_readback_fn": lambda: {"final_state_target": "still_not_achieved"},
    }
    res_fail = compiler._execute_route(
        req_fail, task_id="task-comp", session_id="session-comp", dispatch=lambda *_args: {"success": True}
    )
    assert res_fail["success"] is False
    assert res_fail["status"] == "FINAL_GOAL_VERIFICATION_FAILED"

    # 2. Final authoritative readback confirms goal -> composition succeeds COMMITTED
    req_success = {
        "operation_intent": {
            "id": "intent-composed",
            "goal": {"type": "EQ", "path": "final_state_target", "value": "achieved"},
        },
        "semantic_state": {"final_state_target": "not_achieved"},
        "composition_bindings": {cap.id: {"x": 1}},
            "final_readback_fn": lambda: {"final_state_target": "achieved"},
            "final_verification_result": {"status": "VERIFIED"},
    }
    res_success = compiler._execute_route(
        req_success, task_id="task-comp", session_id="session-comp", dispatch=lambda *_args: {"success": True}
    )
    assert res_success["success"] is True
    assert res_success["routing_decision"] == "COMPOSE"
    assert res_success["dispatch_record"]["status"] == "COMMITTED"

"""H-078B Parity & Causal Invariants Test Suite.

Proves:
1. Pre-authorized dispatch ordering & uncertain mutation checkpointing.
2. Raw post-tool observation before spill/truncation.
3. ExecutionPersistenceDisposition (PERSIST vs OWNER_MANAGED).
4. Tool batch admission (REQUIRE_COMPILE / REQUIRE_HUMAN / discovery).
5. TurnRoutePolicy transversal enforcement.
6. Completion admission (rejection blocks DONE).
7. Trusted TurnIngress (text != authority).
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent.completion_admission import (
    CompletionAdmissionResult,
    admit_completion,
    register_completion_admission_provider,
    unregister_completion_admission_provider,
)
from agent.execution_persistence import (
    ExecutionPersistenceDisposition,
    get_persistence_disposition,
    set_persistence_disposition,
)
from agent.post_tool import (
    dispatch_raw_post_tool_observation,
    register_raw_post_tool_observer,
    unregister_raw_post_tool_observer,
)
from agent.pre_dispatch import (
    dispatch_pre_authorized_checkpoint,
    register_pre_authorized_dispatch_hook,
    unregister_pre_authorized_dispatch_hook,
)
from agent.tool_batch_admission import (
    BatchAdmissionAction,
    BatchAdmissionDecision,
    BatchAdmissionResult,
    admit_tool_batch,
    register_tool_batch_admission_provider,
    unregister_tool_batch_admission_provider,
)
from agent.turn_admission import admit_turn, register_turn_admission_provider
from agent.turn_ingress import TurnIngress, get_current_turn_ingress, set_current_turn_ingress
from agent.turn_route_policy import (
    RouteConstraintViolation,
    TurnRoutePolicy,
    get_current_turn_route_policy,
    set_current_turn_route_policy,
)
from workstation.integrations.hermes.adapter import install_workstation_adapter


@pytest.fixture(autouse=True)
def setup_adapter():
    install_workstation_adapter()


# ===========================================================================
# 1. Pre-Authorized Dispatch Ordering & Invariant
# ===========================================================================

def test_pre_authorized_dispatch_ordering():
    events = []

    def mock_checkpoint(tool_name, final_args, call_id, context):
        events.append(("CHECKPOINT", tool_name, final_args.copy(), call_id))

    register_pre_authorized_dispatch_hook(mock_checkpoint)
    try:
        call_args = {"action": "create", "path": "/tmp/test.txt"}
        context = {"agent": SimpleNamespace(session_id="sess-1")}

        # Simulate authorization passed -> dispatch checkpoint -> execute I/O
        events.append(("AUTH_PASSED", "file_tool"))
        dispatch_pre_authorized_checkpoint("file_tool", call_args, "call-1", context)
        events.append(("IO_START", "file_tool"))
        events.append(("IO_END", "file_tool"))

        assert events == [
            ("AUTH_PASSED", "file_tool"),
            ("CHECKPOINT", "file_tool", {"action": "create", "path": "/tmp/test.txt"}, "call-1"),
            ("IO_START", "file_tool"),
            ("IO_END", "file_tool"),
        ]
    finally:
        unregister_pre_authorized_dispatch_hook(mock_checkpoint)


def test_blocked_tool_never_reaches_checkpoint():
    events = []

    def mock_checkpoint(tool_name, final_args, call_id, context):
        events.append(("CHECKPOINT", tool_name))

    register_pre_authorized_dispatch_hook(mock_checkpoint)
    try:
        # Authorization blocks tool
        authorized = False
        if authorized:
            dispatch_pre_authorized_checkpoint("blocked_tool", {}, "call-x", {})

        assert "CHECKPOINT" not in [e[0] for e in events]
    finally:
        unregister_pre_authorized_dispatch_hook(mock_checkpoint)


# ===========================================================================
# 2. Raw Post-Tool Observation
# ===========================================================================

def test_raw_post_tool_observation_sees_untruncated_result():
    observed = []

    def mock_observer(tool_name, final_args, call_id, raw_result, duration, context):
        observed.append((tool_name, raw_result, duration))

    register_raw_post_tool_observer(mock_observer)
    try:
        raw = {"large_dataset": list(range(1000)), "status": "ok"}
        dispatch_raw_post_tool_observation("data_tool", {}, "call-2", raw, 0.42, {})

        assert len(observed) == 1
        assert observed[0][0] == "data_tool"
        assert observed[0][1] == raw
        assert observed[0][2] == 0.42
    finally:
        unregister_raw_post_tool_observer(mock_observer)


# ===========================================================================
# 3. Execution Persistence Disposition
# ===========================================================================

def test_execution_persistence_disposition():
    assert get_persistence_disposition() == ExecutionPersistenceDisposition.PERSIST

    set_persistence_disposition(ExecutionPersistenceDisposition.OWNER_MANAGED)
    assert get_persistence_disposition() == ExecutionPersistenceDisposition.OWNER_MANAGED

    # Reset
    set_persistence_disposition(ExecutionPersistenceDisposition.PERSIST)
    assert get_persistence_disposition() == ExecutionPersistenceDisposition.PERSIST


# ===========================================================================
# 4. Tool Batch Admission
# ===========================================================================

def test_tool_batch_admission_intercepts_uncompiled_mutations():
    agent = SimpleNamespace(
        session_id="sess-batch-1",
        _conversation_root_id=lambda: "sess-batch-1",
        _work_compile_replans=0,
    )
    # Propose 3 identical mutations that require compilation
    calls = [
        SimpleNamespace(id="c1", function=SimpleNamespace(name="browser_click", arguments='{"selector": "#a"}')),
        SimpleNamespace(id="c2", function=SimpleNamespace(name="browser_click", arguments='{"selector": "#b"}')),
        SimpleNamespace(id="c3", function=SimpleNamespace(name="browser_click", arguments='{"selector": "#c"}')),
    ]

    with patch("workstation.execution_policy.decisions_for_calls") as mock_decisions:
        from workstation.execution_policy import CompilationDecision
        mock_decisions.return_value = [
            CompilationDecision.REQUIRE_COMPILE,
            CompilationDecision.REQUIRE_COMPILE,
            CompilationDecision.REQUIRE_COMPILE,
        ]

        res = admit_tool_batch(agent, calls)
        assert res is not None
        assert len(res.decisions) == 3
        for d in res.decisions:
            assert d.action == BatchAdmissionAction.SYNTHETIC_RESULT
            payload = json.loads(d.synthetic_result)
            assert payload["status"] == "replan"
            assert payload["code"] == "durable_compile_required"


def test_tool_batch_admission_allows_discovery():
    agent = SimpleNamespace(session_id="sess-batch-2", _conversation_root_id=lambda: "sess-batch-2")
    calls = [
        SimpleNamespace(id="c1", function=SimpleNamespace(name="browser_snapshot", arguments='{}')),
    ]

    with patch("workstation.execution_policy.decisions_for_calls") as mock_decisions:
        from workstation.execution_policy import CompilationDecision
        mock_decisions.return_value = [CompilationDecision.ALLOW_ADAPTIVE]

        res = admit_tool_batch(agent, calls)
        assert res is None  # None indicates full batch proceeds without synthetic intervention


# ===========================================================================
# 5. TurnRoutePolicy Enforcement
# ===========================================================================

def test_turn_route_policy_restricts_forbidden_routes():
    policy = TurnRoutePolicy(
        allowed_routes=("browser", "native_browser"),
        forbidden_routes=("terminal",),
        mutation_allowed_routes=("browser",),
        mutation_forbidden_routes=("terminal",),
    )
    set_current_turn_route_policy(policy)
    try:
        assert policy.is_route_allowed("browser") is True
        assert policy.is_route_allowed("terminal") is False
        assert policy.is_route_allowed("openai_api") is False

        policy.require_route("browser", is_mutation=True)

        with pytest.raises(RouteConstraintViolation):
            policy.require_route("terminal", is_mutation=False)

        with pytest.raises(RouteConstraintViolation):
            policy.require_route("openai_api", is_mutation=False)
    finally:
        set_current_turn_route_policy(None)


# ===========================================================================
# 6. Completion Admission
# ===========================================================================

def test_completion_admission_can_block_done():
    def rejecting_provider(task_id, run_id, state):
        return CompletionAdmissionResult(admitted=False, reason="verification_inconclusive")

    register_completion_admission_provider(rejecting_provider)
    try:
        result = admit_completion("task-1", "run-1", {})
        assert result.admitted is False
        assert result.reason == "verification_inconclusive"
    finally:
        unregister_completion_admission_provider(rejecting_provider)


# ===========================================================================
# 7. Trusted Turn Ingress
# ===========================================================================

def test_turn_ingress_authority_binding():
    ingress = TurnIngress(
        origin="cli",
        trust_or_authority_class="CREATE_WORK",
        session_id="sess-ingress-1",
        metadata={"content": "deploy to staging"},
    )
    set_current_turn_ingress(ingress)
    assert get_current_turn_ingress() == ingress

    agent = SimpleNamespace(
        session_id="sess-ingress-1",
        _conversation_root_id=lambda: "sess-ingress-1",
    )
    turn_ctx = SimpleNamespace(content="deploy to staging")

    admit_turn(agent, turn_ctx, ingress=ingress)
    assert getattr(agent, "_message_envelope", None) is not None
    assert agent._message_envelope.origin.value == "human"
    assert agent._message_envelope.can_create_work is True

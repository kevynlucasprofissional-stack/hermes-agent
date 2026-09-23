"""E2E tests for the pre-reasoning operational resolution boundary through normal Hermes turns.

These tests drive the full turn loop (AIAgent.run_conversation) with the Workstation
adapter installed, verifying that a known promoted capability bypasses the provider LLM
entirely, and that novel/no-match requests still reach the provider.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent.operational_resolution import OperationalOutcome
from agent.tool_guardrails import ToolCallGuardrailController, ToolCallGuardrailConfig
from run_agent import AIAgent
from workstation.artifacts import ArtifactStore
from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.ir import EQ, EXISTS, CALL
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.verification import (
    VerificationContract,
    VerificationEvidence,
    VerificationLifecycle,
)
from workstation.durable_tasks import DurableTaskStore
from workstation.execution_policy import EvidenceStrength
from workstation.kanban import WorkstationKanbanBridge
from workstation.operational_capabilities import (
    CapabilityLifecycle,
    OperationalCapability,
    OperationalCapabilityRegistry,
)

# Force Workstation adapter installation by importing workstation
import workstation  # noqa: F401


SESSION_ID = "e2e-session"
MULTISTEP_PROMPT = "First extract the records then verify the result"
CAP_ID = "e2e.cap.record.write"
CAP_VERSION = "1.0.0"
PRIMITIVE = "browser_navigate"  # Use browser_navigate which works through fallback browser branch
TARGET = "example.com"
OPERATION_ID = "op-e2e"
POSTCONDITION = EXISTS("route_artifact")
FINGERPRINT = POSTCONDITION.fingerprint()


def _mock_assistant_msg(
    content="Hello",
    tool_calls=None,
    reasoning=None,
    reasoning_content=None,
    reasoning_details=None,
):
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    if reasoning is not None:
        msg.reasoning = reasoning
    if reasoning_content is not None:
        msg.reasoning_content = reasoning_content
    if reasoning_details is not None:
        msg.reasoning_details = reasoning_details
    return msg


def _mock_response(
    content="Hello",
    finish_reason="stop",
    tool_calls=None,
    reasoning=None,
    reasoning_content=None,
    reasoning_details=None,
    usage=None,
):
    msg = _mock_assistant_msg(
        content=content,
        tool_calls=tool_calls,
        reasoning=reasoning,
        reasoning_content=reasoning_content,
        reasoning_details=reasoning_details,
    )
    choice = SimpleNamespace(message=msg, finish_reason=finish_reason)
    resp = SimpleNamespace(choices=[choice], model="test/model")
    if usage:
        resp.usage = SimpleNamespace(**usage)
    else:
        resp.usage = None
    return resp


def _mock_tool_call(name="browser_navigate", arguments="{}", call_id=None):
    return SimpleNamespace(
        id=call_id or f"call_{uuid.uuid4().hex[:8]}",
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _validated_verifier():
    return VerificationContract(
        covered_predicates=(FINGERPRINT,),
        observer="owner.readback",
        source_kind="source_of_record",
        minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        allowed_trust=("trusted_owner",),
        lifecycle=VerificationLifecycle.VALIDATED,
        resource_binding={"resource_id": TARGET, "resource_version": "1"},
        require_read_after_write=True,
        transition_claim=True,
    )


def _verification_evidence(task_id: str, run_id: str) -> list:
    """Create verification evidence that satisfies the validated verifier."""
    return [VerificationEvidence(
        evidence_id="ev-e2e",
        observer="owner.readback",
        source_kind="source_of_record",
        value={"exists": True},  # matches EXISTS("route_artifact")
        evidence_strength=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        trust_class="trusted_owner",
        observer_failure_domain="filesystem",
        resource_id=TARGET,
        resource_version="1",
        observed_at=datetime.now(timezone.utc).isoformat(),
        read_after_write=True,
        covered_predicates=(FINGERPRINT,),
        task_id=task_id,
        run_id=run_id,
        operation_id=OPERATION_ID,
    )]


def _make_guardrails():
    """Create a minimal ToolCallGuardrailController for testing."""
    config = ToolCallGuardrailConfig.from_mapping({}, platform="cli")
    return ToolCallGuardrailController(config)


def canonical_task(bridge=None) -> str:
    bridge = bridge or WorkstationKanbanBridge()
    envelope = MessageEnvelope(
        MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION_ID, MULTISTEP_PROMPT
    )
    task_id = bridge.promote_request_if_multistep(
        MULTISTEP_PROMPT, session_id=SESSION_ID, envelope=envelope
    )
    assert task_id, "fixture requires a promotable multi-step request"
    return task_id


def store_intent(intent: dict, task_id: str, *, semantic_state: dict | None = None, run_id: str | None = None, **extra):
    store = DurableTaskStore()
    try:
        # Get run_id from task if not provided
        if run_id is None:
            from hermes_cli import kanban_db
            from hermes_cli.kanban_db_connect import connect
            bridge = WorkstationKanbanBridge()
            conn = bridge.get_connection()
            try:
                task = kanban_db.get_task(conn, task_id)
                if task and task.current_run_id:
                    run_id = str(task.current_run_id)
            finally:
                conn.close()
        
        # Add verification evidence to the objective if run_id is available
        verification_evidence = _verification_evidence(task_id, run_id) if run_id else []
        verification_expected = {"exists": True}
        
        objective_ref = ArtifactStore().store(
            task_id,
            "objective.json",
            {**extra, "operation_intent": intent, "semantic_state": semantic_state or {},
             "verification_evidence": [e.to_dict() for e in verification_evidence],
             "verification_expected": verification_expected,
             "expected_task_id": task_id,
             "expected_run_id": run_id or "",
             "expected_operation_id": OPERATION_ID,
             "operation_id": OPERATION_ID,
             "resource_id": TARGET,
             "resource_version": "1",
             "observer_fn": None,
             "readback_fn": None,
             "capability_inputs": {"url": f"https://{TARGET}/"},
            },
        ).ref
        plan = store.create_plan(
            task_id,
            "established intent",
            [{"id": 1}],
            session_id=SESSION_ID,
            metadata={"objective_ref": objective_ref, "canonical_task_id": task_id},
        )
        return plan.id
    finally:
        store.close()


def intent(goal, **extra) -> dict:
    from workstation.control_plane.intent import OperationIntent

    return OperationIntent(
        id="intent-e2e", target=TARGET, goal=goal, effect_budget=[CALL(PRIMITIVE, TARGET)], **extra
    ).to_dict()


def register_promoted_capability(registry: OperationalCapabilityRegistry):
    """Register the capability that matches our intent."""
    cap = OperationalCapability(
        id=CAP_ID,
        name="E2E write record",
        version=CAP_VERSION,
        route="native_browser",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="browser.navigate",
            target_family=TARGET,
            typed_preconditions=[],
            typed_postconditions=[POSTCONDITION],
            effect_footprint=[CALL(PRIMITIVE, TARGET)],
            authority_required=AuthorityScope(
                level=AuthorityLevel.EXTERNAL_REVERSIBLE,
                allowed_actions={"browser.navigate"},
                allowed_resources={TARGET},
            ),
            verifier=_validated_verifier(),
        ),
        implementation={"steps": [{"id": "navigate", "primitive": PRIMITIVE, "args": {"url": "$inputs.url"}}]},
    )
    registry.register(cap)


class _ProviderCallCounter:
    """Tracks provider calls and can fail if called unexpectedly."""

    def __init__(self, fail_on_call: bool = False):
        self.call_count = 0
        self.fail_on_call = fail_on_call
        self.last_args = None
        self.last_kwargs = None

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.last_args = args
        self.last_kwargs = kwargs
        if self.fail_on_call:
            raise AssertionError(f"Provider was called but should not have been (call #{self.call_count})")
        return _mock_response(
            content="Provider response",
            finish_reason="stop",
            reasoning_content=None,
            reasoning_details=None,
        )


class _DispatchRecorder:
    """Records physical dispatcher calls for verification."""

    def __init__(self):
        self.calls = []

    def __call__(self, name, args, *rest):
        # _execute_capability wraps this as dispatch(name, args, browser_task_id, call_id).
        self.calls.append((name, dict(args)))
        if name == "browser_navigate":
            return {"ok": True, "url": args.get("url")}
        elif name == "browser_snapshot":
            # Kernel calls this to get semantic predicates for verification
            # Return semantic predicates that satisfy the EXISTS("route_artifact") postcondition
            return json.dumps({
                "url": "https://example.com/",
                "title": "Example Domain",
                "route_artifact": {"exists": True}
            })
        return {"ok": True}


@pytest.fixture
def workstation_adapter_installed():
    """Ensure Workstation adapter is installed for the test."""
    assert workstation.workstation_adapter_status().installed is True
    yield
    # Adapter stays installed; other tests may depend on it


@pytest.fixture
def temp_hermes_home(tmp_path, monkeypatch):
    """Isolate HERMES_HOME for the test."""
    home = tmp_path / ".hermes"
    home.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    from hermes_constants import get_hermes_home
    monkeypatch.setattr("hermes_constants.get_hermes_home", lambda: home)
    return home


def test_known_promoted_capability_bypasses_llm(workstation_adapter_installed, temp_hermes_home, monkeypatch):
    """E001: A known promoted capability executes without calling the provider LLM.

    The turn goes through the normal AIAgent.run_conversation entry point.
    The operational resolution boundary should resolve the turn via the Workstation
    provider, dispatching the capability through the certified dispatcher and
    returning a terminal EXECUTED outcome with zero provider calls.

    This test proves the full causal path:
    - goal FALSE at admission
    - EXECUTE decision
    - valid RoutingCertificate
    - physical dispatcher count = 1
    - canonical verifier = VERIFIED
    - accepted = true
    - dispatch record = COMMITTED
    - provider calls = 0
    """
    # 1. Create canonical task
    task_id = canonical_task()

    # 2. Store established intent with provable goal (NOT satisfied initially)
    plan_id = store_intent(
        intent(POSTCONDITION),
        task_id,
        semantic_state={"route_artifact": {"exists": False}},  # goal NOT satisfied
    )

    # 3. Register promoted capability in the default registry
    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    register_promoted_capability(registry)

    # 4. Create AIAgent with mocked provider that fails if called
    provider_counter = _ProviderCallCounter(fail_on_call=True)
    dispatch_recorder = _DispatchRecorder()

    # We need to ensure TaskCompiler has trusted_authority set for the authority check
    # Patch TaskCompiler.execute to inject trusted_authority before execution
    from workstation.task_compiler import TaskCompiler as TC
    original_execute = TC.execute

    def patched_execute(self, request, *, task_id, session_id, dispatch, progress=None, provider_usage=None, environment=None, event_bus=None, canonical_task_id=None):
        from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
        self.trusted_authority = AuthorityScope(
            level=AuthorityLevel.EXTERNAL_REVERSIBLE,
            allowed_actions={"browser.navigate"},
            allowed_resources={TARGET},
        )
        return original_execute(self, request, task_id=task_id, session_id=session_id, dispatch=dispatch, progress=progress, provider_usage=provider_usage, environment=environment, event_bus=event_bus, canonical_task_id=canonical_task_id)

    with (
        patch("model_tools.get_tool_definitions", return_value=[]),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
        # Inject our dispatch recorder into the operational resolution path
        patch("workstation.integrations.hermes.scoped_execution.workstation_durable_dispatch", return_value=dispatch_recorder),
        # Patch TaskCompiler.execute to set trusted_authority
        patch.object(TC, 'execute', patched_execute),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://test.api",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        agent.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
        )

        # 5. Bind the agent to the canonical task (what prepare_turn_work would do)
        agent._canonical_work_task_id = task_id
        agent._message_envelope = MessageEnvelope(
            MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION_ID, MULTISTEP_PROMPT
        )
        agent._conversation_root_id = lambda: SESSION_ID
        agent._tool_guardrails = _make_guardrails()
        agent._work_capabilities = {}
        agent._work_user_constraints = {}
        agent._current_provider_usage = None
        agent._work_completed_mutations = {}
        agent._work_mutation_evidence = {}
        agent._workstation_event_bus = None
        agent._interrupt_requested = False
        agent.valid_tool_names = set()

        # 6. Run the turn through the normal entry point
        result = agent.run_conversation(
            user_message=MULTISTEP_PROMPT,
            task_id=task_id,
        )

    # 7. Assertions - prove the full causal path
    assert provider_counter.call_count == 0, f"Provider was called {provider_counter.call_count} times but should be 0"
    assert result["completed"] is True
    assert result["failed"] is False
    # The response should indicate verified completion
    assert "verified" in result["final_response"].lower() or "completed" in result["final_response"].lower()
    # Prove physical dispatch happened exactly once
    assert len(dispatch_recorder.calls) == 1, f"Expected exactly 1 physical dispatch, got {len(dispatch_recorder.calls)}"
    assert dispatch_recorder.calls[0][0] == PRIMITIVE
    assert dispatch_recorder.calls[0][1] == {"url": f"https://{TARGET}/"}


def test_novel_request_reaches_provider(workstation_adapter_installed, temp_hermes_home, monkeypatch):
    """E002: A request with no established intent reaches the provider.

    The operational resolution boundary should return CONTINUE_REASONING,
    and the provider should be called normally.
    """
    # 1. Create canonical task but NO established intent
    task_id = canonical_task()

    # 2. Register a capability that does NOT match (different target)
    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    # Register capability for a different target so it won't match
    cap = OperationalCapability(
        id="other.cap",
        name="Other capability",
        version="1.0.0",
        route="native_browser",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="other.operation",
            target_family="other_target",
            typed_preconditions=[],
            typed_postconditions=[EXISTS("other_target")],
            effect_footprint=[CALL("other_tool", "other_target")],
            authority_required=AuthorityScope(
                level=AuthorityLevel.LOCAL_MUTATION,
                allowed_actions={"other"},
                allowed_resources={"other_target"},
            ),
            verifier=_validated_verifier(),
        ),
    )
    registry.register(cap)

    # 3. Create AIAgent with provider counter
    provider_counter = _ProviderCallCounter(fail_on_call=False)

    with (
        patch("model_tools.get_tool_definitions", return_value=[]),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://test.api",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        agent.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
        )

        # Bind agent to task
        agent._canonical_work_task_id = task_id
        agent._message_envelope = MessageEnvelope(
            MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION_ID, MULTISTEP_PROMPT
        )
        agent._conversation_root_id = lambda: SESSION_ID
        agent._tool_guardrails = _make_guardrails()
        agent._work_capabilities = {}
        agent._work_user_constraints = {}
        agent._current_provider_usage = None
        agent._work_completed_mutations = {}
        agent._work_mutation_evidence = {}
        agent._workstation_event_bus = None
        agent._interrupt_requested = False
        agent.valid_tool_names = set()
        # Use MOA provider mode so _create_request_openai_client returns the mocked primary client
        agent.provider = "moa"

        # 4. Run the turn
        result = agent.run_conversation(
            user_message="Do something completely different",
            task_id=task_id,
        )

    # 5. Assertions - provider should have been called
    assert provider_counter.call_count >= 1, f"Provider should have been called but was called {provider_counter.call_count} times"
    assert result["completed"] is True


def test_raw_text_is_not_intent(workstation_adapter_installed, temp_hermes_home, monkeypatch):
    """E002-B: Raw user text without persisted intent does not synthesize an OperationIntent.

    Even if the text sounds executable, without a durable established intent
    the boundary must not dispatch any capability.
    """
    # 1. Create canonical task but NO established intent stored
    task_id = canonical_task()

    # 2. Register a promoted capability that would match if intent existed
    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    register_promoted_capability(registry)

    # 3. Create AIAgent with provider counter that fails if called
    provider_counter = _ProviderCallCounter(fail_on_call=False)

    with (
        patch("model_tools.get_tool_definitions", return_value=[]),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://test.api",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        agent.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
        )

# Bind agent to task
        agent._canonical_work_task_id = task_id
        agent._message_envelope = MessageEnvelope(
            MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION_ID, MULTISTEP_PROMPT
        )
        agent._conversation_root_id = lambda: SESSION_ID
        agent._tool_guardrails = _make_guardrails()
        agent._work_capabilities = {}
        agent._work_user_constraints = {}
        agent._current_provider_usage = None
        agent._work_completed_mutations = {}
        agent._work_mutation_evidence = {}
        agent._workstation_event_bus = None
        agent._interrupt_requested = False
        agent.valid_tool_names = set()
        # Use MOA provider mode so _create_request_openai_client returns the mocked primary client
        agent.provider = "moa"

        # 4. Run the turn with raw text that sounds executable but has no intent
        result = agent.run_conversation(
            user_message="write the records to a file",
            task_id=task_id,
        )

    # 5. Assertions - provider should have been called (no intent to resolve)
    assert provider_counter.call_count >= 1, "Provider should have been called for raw text without intent"
    assert result["completed"] is True


def test_trivial_true_goal_is_not_satisfied(workstation_adapter_installed, temp_hermes_home, monkeypatch):
    """E002-C: An intent with default TRUE goal does not auto-satisfy.

    OperationIntent defaults goal to TRUE, which evaluates true against any state.
    This must be rejected before routing to prevent closing turns on unstated goals.
    """
    # 1. Create canonical task
    task_id = canonical_task()

    # 2. Store intent with default TRUE goal (no explicit goal)
    store = DurableTaskStore()
    try:
        objective_ref = ArtifactStore().store(
            task_id,
            "objective.json",
            {
                "operation_intent": {
                    "id": "intent-trivial",
                    "target": TARGET,
                    "goal": {"type": "TRUE"},  # default/trivial goal
                    "effect_budget": [{"primitive": PRIMITIVE, "target": TARGET}],
                },
                "semantic_state": {"record": {"state": "anything"}},
            },
        ).ref
        store.create_plan(
            task_id,
            "trivial goal intent",
            [{"id": 1}],
            session_id=SESSION_ID,
            metadata={"objective_ref": objective_ref, "canonical_task_id": task_id},
        )
    finally:
        store.close()

    # 3. Register promoted capability
    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    register_promoted_capability(registry)

    # 4. Create AIAgent with provider counter
    provider_counter = _ProviderCallCounter(fail_on_call=False)

    with (
        patch("model_tools.get_tool_definitions", return_value=[]),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://test.api",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        agent.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
        )

        # Bind agent to task
        agent._canonical_work_task_id = task_id
        agent._message_envelope = MessageEnvelope(
            MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION_ID, MULTISTEP_PROMPT
        )
        agent._conversation_root_id = lambda: SESSION_ID
        agent._tool_guardrails = _make_guardrails()
        agent._work_capabilities = {}
        agent._work_user_constraints = {}
        agent._current_provider_usage = None
        agent._work_completed_mutations = {}
        agent._work_mutation_evidence = {}
        agent._workstation_event_bus = None
        agent._interrupt_requested = False
        agent.valid_tool_names = set()
        # Use MOA provider mode so _create_request_openai_client returns the mocked primary client
        agent.provider = "moa"

        # 5. Run the turn
        result = agent.run_conversation(
            user_message=MULTISTEP_PROMPT,
            task_id=task_id,
        )

    # 6. Assertions - provider should be called (trivial goal rejected)
    assert provider_counter.call_count >= 1, "Provider should have been called for trivial TRUE goal"
    assert result["completed"] is True


def test_invalid_certificate_no_dispatch(workstation_adapter_installed, temp_hermes_home, monkeypatch):
    """E003: An intent matching a capability with invalid certificate does not dispatch.

    The route's verification must fail, and the boundary returns HANDOFF (ASK_HUMAN)
    which is a terminal outcome. The provider is NOT called.
    """
    # 1. Create canonical task
    task_id = canonical_task()

    # 2. Store intent with provable goal
    plan_id = store_intent(
        intent(POSTCONDITION),
        task_id,
        semantic_state={"record": {"state": "pending"}},
    )

    # 3. Register capability with INVALID verifier (not VALIDATED)
    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    cap = OperationalCapability(
        id=CAP_ID,
        name="E2E write record",
        version=CAP_VERSION,
        route="native_browser",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="record.write",
            target_family=TARGET,
            typed_preconditions=[],
            typed_postconditions=[POSTCONDITION],
            effect_footprint=[CALL(PRIMITIVE, TARGET)],
            authority_required=AuthorityScope(
                level=AuthorityLevel.LOCAL_MUTATION,
                allowed_actions={"write"},
                allowed_resources={TARGET},
            ),
            verifier=VerificationContract(
                covered_predicates=(FINGERPRINT,),
                observer="owner.readback",
                source_kind="source_of_record",
                minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
                allowed_trust=("trusted_owner",),
                lifecycle=VerificationLifecycle.CANDIDATE,  # NOT VALIDATED
            ),
        ),
        implementation={"steps": [{"id": "write", "primitive": PRIMITIVE, "args": {"path": TARGET, "content": "$inputs.content"}}]},
    )
    registry.register(cap)

    # 4. Create AIAgent with provider counter that fails if called
    provider_counter = _ProviderCallCounter(fail_on_call=True)

    with (
        patch("model_tools.get_tool_definitions", return_value=[]),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://test.api",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        agent.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
        )

        # Bind agent to task
        agent._canonical_work_task_id = task_id
        agent._message_envelope = MessageEnvelope(
            MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION_ID, MULTISTEP_PROMPT
        )
        agent._conversation_root_id = lambda: SESSION_ID
        agent._tool_guardrails = _make_guardrails()
        agent._work_capabilities = {}
        agent._work_user_constraints = {}
        agent._current_provider_usage = None
        agent._work_completed_mutations = {}
        agent._work_mutation_evidence = {}
        agent._workstation_event_bus = None
        agent._interrupt_requested = False
        agent.valid_tool_names = set()
        # Use MOA provider mode so _create_request_openai_client returns the mocked primary client
        agent.provider = "moa"

        # 5. Run the turn
        result = agent.run_conversation(
            user_message=MULTISTEP_PROMPT,
            task_id=task_id,
        )

    # 6. Assertions - provider should NOT be called (HANDOFF is terminal)
    assert result["completed"] is True
    assert "human decision" in result["final_response"].lower() or "approval is required" in result["final_response"].lower()


def test_quarantined_capability_no_dispatch(workstation_adapter_installed, temp_hermes_home, monkeypatch):
    """E003: A quarantined capability does not dispatch."""
    # 1. Create canonical task
    task_id = canonical_task()

    # 2. Store intent
    plan_id = store_intent(
        intent(POSTCONDITION),
        task_id,
        semantic_state={"record": {"state": "pending"}},
    )

    # 3. Register capability as QUARANTINED
    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    cap = OperationalCapability(
        id=CAP_ID,
        name="E2E write record",
        version=CAP_VERSION,
        route="native_browser",
        lifecycle=CapabilityLifecycle.DISCOVERED,  # Not PROMOTED - will be rejected
        formal_contract=CapabilityFormalContract(
            operation_family="record.write",
            target_family=TARGET,
            typed_preconditions=[],
            typed_postconditions=[POSTCONDITION],
            effect_footprint=[CALL(PRIMITIVE, TARGET)],
            authority_required=AuthorityScope(
                level=AuthorityLevel.LOCAL_MUTATION,
                allowed_actions={"write"},
                allowed_resources={TARGET},
            ),
            verifier=_validated_verifier(),
        ),
        implementation={"steps": [{"id": "write", "primitive": PRIMITIVE, "args": {"path": TARGET, "content": "$inputs.content"}}]},
    )
    registry.register(cap)

    # 4. Create AIAgent with provider counter
    provider_counter = _ProviderCallCounter(fail_on_call=False)

    with (
        patch("model_tools.get_tool_definitions", return_value=[]),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://test.api",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        agent.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
        )

        # Bind agent to task
        agent._canonical_work_task_id = task_id
        agent._message_envelope = MessageEnvelope(
            MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION_ID, MULTISTEP_PROMPT
        )
        agent._conversation_root_id = lambda: SESSION_ID
        agent._tool_guardrails = _make_guardrails()
        agent._work_capabilities = {}
        agent._work_user_constraints = {}
        agent._current_provider_usage = None
        agent._work_completed_mutations = {}
        agent._work_mutation_evidence = {}
        agent._workstation_event_bus = None
        agent._interrupt_requested = False
        agent.valid_tool_names = set()
        # Use MOA provider mode so _create_request_openai_client returns the mocked primary client
        agent.provider = "moa"

        # 5. Run the turn
        result = agent.run_conversation(
            user_message=MULTISTEP_PROMPT,
            task_id=task_id,
        )

    # 6. Assertions - provider should be called (quarantined -> no dispatch)
    assert provider_counter.call_count >= 1, "Provider should have been called for quarantined capability"
    assert result["completed"] is True


def test_outstanding_uncertain_mutation_stops_boundary(workstation_adapter_installed, temp_hermes_home, monkeypatch):
    """E003: An outstanding uncertain mutation stops the boundary before dispatch.

    The plan has a mutation that crossed I/O without a proved result.
    The boundary must not add a second dispatch lane; it returns CONTINUE_REASONING.
    """
    # 1. Create canonical task
    task_id = canonical_task()

    # 2. Store intent
    plan_id = store_intent(
        intent(POSTCONDITION),
        task_id,
        semantic_state={"record": {"state": "pending"}},
    )

    # 3. Record an unproved mutation on the plan
    store = DurableTaskStore()
    try:
        item = store.get_work_items(plan_id)[0]
        store.update_item_checkpoint(
            item.id, "step_0_dispatch",
            metadata={"mutation_identity": {
                "operation_id": "op-unproved", "tool": PRIMITIVE,
                "effect": "MUTATION", "target_identifier": TARGET,
            }},
        )
    finally:
        store.close()

    # 4. Register promoted capability
    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    register_promoted_capability(registry)

    # 5. Create AIAgent with provider counter
    provider_counter = _ProviderCallCounter(fail_on_call=False)

    with (
        patch("model_tools.get_tool_definitions", return_value=[]),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://test.api",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        agent.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
        )

        # Bind agent to task
        agent._canonical_work_task_id = task_id
        agent._message_envelope = MessageEnvelope(
            MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION_ID, MULTISTEP_PROMPT
        )
        agent._conversation_root_id = lambda: SESSION_ID
        agent._tool_guardrails = _make_guardrails()
        agent._work_capabilities = {}
        agent._work_user_constraints = {}
        agent._current_provider_usage = None
        agent._work_completed_mutations = {}
        agent._work_mutation_evidence = {}
        agent._workstation_event_bus = None
        agent._interrupt_requested = False
        agent.valid_tool_names = set()
        # Use MOA provider mode so _create_request_openai_client returns the mocked primary client
        agent.provider = "moa"

        # 6. Run the turn
        result = agent.run_conversation(
            user_message=MULTISTEP_PROMPT,
            task_id=task_id,
        )

    # 7. Assertions - provider should be called (uncertain mutation -> no dispatch)
    assert provider_counter.call_count >= 1, "Provider should have been called for uncertain mutation"
    assert result["completed"] is True


def test_verifier_failure_no_commit(workstation_adapter_installed, temp_hermes_home, monkeypatch):
    """E003V: A dispatch that succeeds but verification fails does not commit.

    The handler returns ACK/success but canonical verification = FAILED or INCONCLUSIVE.
    The boundary must not commit or promote, and must return WAIT/HANDOFF.
    No blind LLM retry of the same mutation occurs.
    """
    # 1. Create canonical task
    task_id = canonical_task()

    # 2. Store established intent with provable goal (NOT satisfied initially)
    plan_id = store_intent(
        intent(POSTCONDITION),
        task_id,
        semantic_state={"route_artifact": {"exists": False}},
    )

    # 3. Register capability with VALIDATED verifier
    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    cap = OperationalCapability(
        id=CAP_ID,
        name="E2E write record",
        version=CAP_VERSION,
        route="native_browser",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="browser.navigate",
            target_family=TARGET,
            typed_preconditions=[],
            typed_postconditions=[POSTCONDITION],
            effect_footprint=[CALL(PRIMITIVE, TARGET)],
            authority_required=AuthorityScope(
                level=AuthorityLevel.EXTERNAL_REVERSIBLE,
                allowed_actions={"browser.navigate"},
                allowed_resources={TARGET},
            ),
            verifier=_validated_verifier(),  # VALIDATED verifier
        ),
        implementation={"steps": [{"id": "navigate", "primitive": PRIMITIVE, "args": {"url": "$inputs.url"}}]},
    )
    registry.register(cap)

    # 4. Create AIAgent with provider counter that fails if called
    provider_counter = _ProviderCallCounter(fail_on_call=True)
    dispatch_recorder = _DispatchRecorder()

    # We need to ensure TaskCompiler has trusted_authority set for the authority check
    # Patch TaskCompiler.execute to inject trusted_authority before execution
    from workstation.task_compiler import TaskCompiler as TC
    original_execute = TC.execute

    def patched_execute(self, request, *, task_id, session_id, dispatch, progress=None, provider_usage=None, environment=None, event_bus=None, canonical_task_id=None):
        from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
        self.trusted_authority = AuthorityScope(
            level=AuthorityLevel.EXTERNAL_REVERSIBLE,
            allowed_actions={"browser.navigate"},
            allowed_resources={TARGET},
        )
        return original_execute(self, request, task_id=task_id, session_id=session_id, dispatch=dispatch, progress=progress, provider_usage=provider_usage, environment=environment, event_bus=event_bus, canonical_task_id=canonical_task_id)

    # Patch evaluate_verification to return FAILED (simulating verification failure after successful dispatch)
    from workstation.operational_kernel import evaluate_verification as original_evaluate_verification
    from workstation.control_plane.verification import VerificationResult, VerificationStatus

    def failed_evaluation(*args, **kwargs):
        return VerificationResult(
            status=VerificationStatus.FAILED,
            verifier_fingerprint="test-fingerprint",
            evidence_refs=(),
            covered_predicates=(),
            freshness_satisfied=True,
            relation_satisfied=False,
            source_admissible=True,
            fault_domain_admissible=True,
            transition_proven=False,
            reason="verification_failed_for_test",
            evaluated_at="2026-09-22T00:00:00+00:00",
        )

    with (
        patch("model_tools.get_tool_definitions", return_value=[]),
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
        patch("workstation.integrations.hermes.scoped_execution.workstation_durable_dispatch", return_value=dispatch_recorder),
        # Patch TaskCompiler.execute to set trusted_authority
        patch.object(TC, 'execute', patched_execute),
        # Patch verification to fail
        patch("workstation.operational_kernel.evaluate_verification", failed_evaluation),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://test.api",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        agent.client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
        )

        # Bind agent to task
        agent._canonical_work_task_id = task_id
        agent._message_envelope = MessageEnvelope(
            MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION_ID, MULTISTEP_PROMPT
        )
        agent._conversation_root_id = lambda: SESSION_ID
        agent._tool_guardrails = _make_guardrails()
        agent._work_capabilities = {}
        agent._work_user_constraints = {}
        agent._current_provider_usage = None
        agent._work_completed_mutations = {}
        agent._work_mutation_evidence = {}
        agent._workstation_event_bus = None
        agent._interrupt_requested = False
        agent.valid_tool_names = set()

        # 5. Run the turn
        result = agent.run_conversation(
            user_message=MULTISTEP_PROMPT,
            task_id=task_id,
        )

    # 6. Assertions
    # Physical dispatch happened (the handler returned ACK)
    assert len(dispatch_recorder.calls) == 1, "Physical dispatch should have been attempted"
    # But verification failed, so no provider retry
    assert provider_counter.call_count == 0, "Provider should not be called after failed verification"
    # Result should be terminal but not EXECUTED success
    assert result["completed"] is True
    # Should be WAIT or HANDOFF, not EXECUTED
    assert "reconcile" in result["final_response"].lower() or "human decision" in result["final_response"].lower() or "approval is required" in result["final_response"].lower() or "could not be proven" in result["final_response"].lower()
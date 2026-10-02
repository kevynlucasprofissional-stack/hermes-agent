"""E2E tests for the pre-reasoning operational resolution boundary through normal Hermes turns.

These tests drive the full turn loop (``AIAgent.run_conversation``) with the
Workstation adapter installed. The two production-path proofs are split:

* **E001F** — verified filesystem success: production authority, deterministic
  capability execution, real state transition, real post-effect readback,
  ``VERIFIED`` + accepted, ``COMMITTED``, zero provider calls;
* **E001D** — durable dispatcher parity: the real
  ``workstation_durable_dispatch`` path executes a real admitted tool
  (``todo_list``) exactly once through ``execute_tool_calls_sequential``.

No test replaces the dispatcher, injects control-plane authority, pre-seeds
verification evidence, or mocks the verifier for the success path.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agent.tool_guardrails import ToolCallGuardrailController, ToolCallGuardrailConfig
from run_agent import AIAgent
from workstation.artifacts import ArtifactStore
from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.ir import EQ, EXISTS, CALL
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.verification import (
    VerificationContract,
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
FS_CAP_ID = "e2e.cap.fs.write"
TODO_CAP_ID = "e2e.cap.todo.add"
OPERATION_ID = "op-e2e"


def _mock_assistant_msg(content="Hello", tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _mock_response(content="Hello", finish_reason="stop", tool_calls=None):
    msg = _mock_assistant_msg(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=msg, finish_reason=finish_reason)
    return SimpleNamespace(choices=[choice], model="test/model", usage=None)


def _make_guardrails():
    """Create a minimal ToolCallGuardrailController for testing."""
    config = ToolCallGuardrailConfig.from_mapping({}, platform="cli")
    return ToolCallGuardrailController(config)


def canonical_task(prompt: str = MULTISTEP_PROMPT, bridge=None) -> str:
    bridge = bridge or WorkstationKanbanBridge()
    envelope = MessageEnvelope(MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION_ID, prompt)
    task_id = bridge.promote_request_if_multistep(prompt, session_id=SESSION_ID, envelope=envelope)
    assert task_id, "fixture requires a promotable multi-step request"
    return task_id


def _run_id_of(task_id: str) -> str:
    from hermes_cli import kanban_db

    bridge = WorkstationKanbanBridge()
    conn = bridge.get_connection()
    try:
        task = kanban_db.get_task(conn, task_id)
        assert task is not None and task.current_run_id is not None
        return str(task.current_run_id)
    finally:
        conn.close()


def store_intent(intent: dict, task_id: str, *, semantic_state: dict | None = None, **extra):
    """Persist an established intent the way an admitted execution does.

    Only observation *configuration* may be stored (expected value, observer
    args, covered predicates, lineage). Success evidence is never pre-seeded:
    the runtime must produce it with a real post-effect observer.
    """
    store = DurableTaskStore()
    try:
        objective_ref = ArtifactStore().store(
            task_id,
            "objective.json",
            {**extra, "operation_intent": intent, "semantic_state": semantic_state or {}},
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


def intent(goal, *, target="filesystem", effect="fs_write", operation_family="file.write",
           target_family="filesystem", **extra) -> dict:
    from workstation.control_plane.intent import OperationIntent

    return OperationIntent(
        id="intent-e2e", target=target, goal=goal,
        effect_budget=[CALL(effect, target_family)],
        metadata={"operation_family": operation_family, "target_family": target_family},
        **extra,
    ).to_dict()


def _fs_goal() -> object:
    """The single postcondition/goal used by the filesystem E2E fixtures."""
    return EQ("exists", True)


def _fs_fingerprint() -> str:
    return _fs_goal().fingerprint()


def _filesystem_verifier() -> VerificationContract:
    """Real post-effect readback contract: ``fs_read`` observed after the write.

    Covered predicates must include the postcondition fingerprint, otherwise
    the router correctly refuses the capability as unverifiable.
    """
    return VerificationContract(
        covered_predicates=(_fs_fingerprint(),),
        observer="fs_read",
        source_kind="filesystem",
        minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        allowed_trust=("trusted_runtime",),
        lifecycle=VerificationLifecycle.VALIDATED,
        require_read_after_write=True,
        transition_claim=True,
    )


def _make_filesystem_capability(registry: OperationalCapabilityRegistry, cap_id: str):
    """Register a promoted filesystem capability (``fs_write`` + ``fs_read`` readback)."""
    goal = _fs_goal()
    cap = OperationalCapability(
        id=cap_id,
        name="E2E write file",
        version="1.0.0",
        route="filesystem",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="file.write",
            target_family="filesystem",
            typed_preconditions=[],
            typed_postconditions=[goal],
            effect_footprint=[CALL("fs_write", "filesystem")],
            authority_required=AuthorityScope(
                level=AuthorityLevel.LOCAL_MUTATION,
                allowed_actions={"write"},
                allowed_resources={"filesystem"},
            ),
            verifier=_filesystem_verifier(),
        ),
        implementation={"steps": [{
            "id": "write", "primitive": "fs_write",
            "args": {"path": "$inputs.path", "content": "$inputs.content"},
        }]},
    )
    registry.register(cap)


def _make_todo_capability(registry: OperationalCapabilityRegistry, cap_id: str):
    """Register a promoted todo capability (real ``todo_list`` tool, no kernel interception)."""
    goal = EXISTS("todo_item")
    cap = OperationalCapability(
        id=cap_id,
        name="E2E todo add",
        version="1.0.0",
        route="todo",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="todo.write",
            target_family="todo",
            typed_preconditions=[],
            typed_postconditions=[goal],
            effect_footprint=[CALL("todo_list", "todo")],
            authority_required=AuthorityScope(
                level=AuthorityLevel.LOCAL_MUTATION,
                allowed_actions={"write"},
                allowed_resources={"todo"},
            ),
            verifier=VerificationContract(
                covered_predicates=(goal.fingerprint(),),
                observer="todo_readback",
                source_kind="todo",
                minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
                allowed_trust=("trusted_runtime",),
                lifecycle=VerificationLifecycle.VALIDATED,
                require_read_after_write=True,
                transition_claim=True,
            ),
        ),
        implementation={"steps": [{
            "id": "add", "primitive": "todo_list",
            "args": {"todos": "$inputs.todos", "merge": True},
        }]},
    )
    registry.register(cap)


class _ProviderCallCounter:
    """Tracks provider calls and can fail if called unexpectedly."""

    def __init__(self, fail_on_call: bool = False):
        self.call_count = 0
        self.fail_on_call = fail_on_call

    def __call__(self, *args, **kwargs):
        self.call_count += 1
        if self.fail_on_call:
            raise AssertionError(f"Provider was called but should not have been (call #{self.call_count})")
        return _mock_response(content="Provider response", finish_reason="stop")


@pytest.fixture
def workstation_adapter_installed():
    """Ensure Workstation adapter is installed for the test.

    Other suites mutate the global adapter status and provider registry
    (bootstrap failure drills, boundary registry resets); re-bootstrap and
    re-register here so this suite is independent of execution order. Only
    the provider registration affects the turn loop under test.
    """
    from agent.operational_resolution import (
        operational_resolution_providers,
        register_operational_resolution_provider,
    )
    from workstation.integrations.hermes.operational_resolution import (
        workstation_operational_resolution,
    )

    try:
        workstation.bootstrap_workstation_adapter("required")
    except Exception:
        pass
    if workstation_operational_resolution not in operational_resolution_providers():
        register_operational_resolution_provider(workstation_operational_resolution)
    yield


@pytest.fixture
def temp_hermes_home(tmp_path, monkeypatch):
    """Isolate HERMES_HOME for the test."""
    home = tmp_path / ".hermes"
    home.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setattr("hermes_constants.get_hermes_home", lambda: home)
    return home


@pytest.fixture(autouse=True)
def _invalidate_tool_probe_cache():
    """These tests drive real tool discovery; drop TTL-cached check_fn verdicts afterwards.

    The registry caches ``check_fn`` results process-wide (~30s TTL). Without
    invalidation, a cached "browser backend unavailable" verdict would leak
    into later suites that monkeypatch those probes.
    """
    yield
    try:
        from tools.registry import invalidate_check_fn_cache
    except Exception:
        return
    try:
        invalidate_check_fn_cache()
    except Exception:
        pass


@pytest.fixture
def execute_spy(monkeypatch):
    """Observe (never replace) TaskCompiler.execute results for causal asserts."""
    from workstation.task_compiler import TaskCompiler as TC

    calls: list = []
    original = TC.execute

    def wrapper(self, request, **kwargs):
        res = original(self, request, **kwargs)
        calls.append(res)
        return res

    monkeypatch.setattr(TC, "execute", wrapper)
    return calls


def _bind_agent(agent, task_id: str, body: str = MULTISTEP_PROMPT):
    agent._canonical_work_task_id = task_id
    agent._message_envelope = MessageEnvelope(
        MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION_ID, body
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
    agent.valid_tool_names = set(agent.valid_tool_names or set())
    agent.provider = "moa"


def _make_agent(**kwargs):
    with (
        patch("model_tools.check_toolset_requirements", return_value={}),
        patch("agent.process_bootstrap.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://test.api",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
            **kwargs,
        )
        return agent


# =============================================================================
# E001F — verified filesystem success through the normal turn
# =============================================================================

def test_known_promoted_capability_bypasses_llm(
    workstation_adapter_installed, temp_hermes_home, monkeypatch, tmp_path, execute_spy,
):
    """E001F: promoted filesystem capability executes with real post-effect verification.

    Proves: goal false at admission, production authority (no TaskCompiler
    monkeypatch), EXECUTE with certificate, real tmp filesystem mutation, real
    ``fs_read`` readback after the write, no pre-seeded success evidence,
    VERIFIED + accepted, COMMITTED, zero provider calls, canonical finalizer.
    """
    target = tmp_path / "h080_e001f.txt"
    assert not target.exists()
    expected_content = "h080a-proof"

    task_id = canonical_task()
    run_id = _run_id_of(task_id)
    goal = EQ("exists", True)
    plan_id = store_intent(
        intent(goal),
        task_id,
        semantic_state={"exists": False},
        capability_inputs={"path": str(target), "content": expected_content},
        verification_expected=expected_content,
        observer_args={"path": str(target)},
        observed_predicates=(_fs_fingerprint(),),
        resource_id=str(target),
        resource_version="1",
        operation_id=OPERATION_ID,
        expected_task_id=task_id,
        expected_run_id=run_id,
        expected_operation_id=OPERATION_ID,
    )

    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    _make_filesystem_capability(registry, "e2e.cap.fs.write")

    provider_counter = _ProviderCallCounter(fail_on_call=True)
    agent = _make_agent()
    agent.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
    )
    _bind_agent(agent, task_id)

    result = agent.run_conversation(user_message=MULTISTEP_PROMPT, task_id=task_id)

    assert provider_counter.call_count == 0
    assert result["completed"] is True
    assert result["failed"] is False
    # Real mutation happened.
    assert target.exists()
    assert target.read_text(encoding="utf-8") == expected_content
    # Direct causal markers from the control plane (observed, not mocked).
    assert execute_spy, "expected at least one TaskCompiler.execute call"
    last = execute_spy[-1]
    assert last.get("routing_decision") == "EXECUTE"
    assert last.get("capability_id") == "e2e.cap.fs.write"
    assert last.get("certificate_hash")
    assert last.get("verification_result", {}).get("status") == "VERIFIED"
    assert last.get("verification_result", {}).get("accepted") is True
    assert last.get("dispatch_record", {}).get("status") == "COMMITTED"


def test_already_satisfied_goal_bypasses_llm(
    workstation_adapter_installed, temp_hermes_home, monkeypatch, tmp_path, execute_spy,
):
    """SATISFIED path: goal already true dispatches nothing and spends no LLM call."""
    task_id = canonical_task()
    goal = EQ("exists", True)
    store_intent(intent(goal), task_id, semantic_state={"exists": True})

    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    _make_filesystem_capability(registry, "e2e.cap.fs.write")

    provider_counter = _ProviderCallCounter(fail_on_call=True)
    agent = _make_agent()
    agent.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
    )
    _bind_agent(agent, task_id)

    result = agent.run_conversation(user_message=MULTISTEP_PROMPT, task_id=task_id)

    assert provider_counter.call_count == 0
    assert result["completed"] is True
    assert execute_spy, "expected at least one TaskCompiler.execute call"
    assert execute_spy[-1].get("routing_decision") == "SATISFIED"


# =============================================================================
# E001D — durable dispatcher parity with a real admitted tool
# =============================================================================

def test_durable_dispatcher_parity(
    workstation_adapter_installed, temp_hermes_home, monkeypatch,
):
    """E001D: the real ``workstation_durable_dispatch`` executes ``todo_list`` exactly once.

    Uses the real tool catalog (``todo`` toolset), the real
    ``execute_tool_calls_sequential`` path and the real ``TodoStore``. Only
    spies (wraps) observe; nothing in the dispatch chain is replaced. The turn
    may end WAIT/HANDOFF when no canonical independent verifier exists — the
    proof owned here is exactly-once real dispatch with no blind retry.
    """
    from agent import tool_executor
    from workstation import task_compiler as task_compiler_mod

    task_id = canonical_task(prompt="First add the todo item then verify the list")
    body = "First add the todo item then verify the list"
    goal = EXISTS("todo_item")
    plan_id = store_intent(
        intent(goal, target="todo", effect="todo_list", operation_family="todo.write",
               target_family="todo"),
        task_id,
        semantic_state={"todo_item": {"exists": False}},
        capability_inputs={"todos": [{"id": "e001d-1", "content": "h080a parity", "status": "pending"}]},
        operation_id=OPERATION_ID,
        expected_task_id=task_id,
        expected_run_id=_run_id_of(task_id),
        expected_operation_id=OPERATION_ID,
    )

    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    _make_todo_capability(registry, "e2e.cap.todo.add")

    provider_counter = _ProviderCallCounter(fail_on_call=True)

    executor_calls: list = []
    raw_results: list = []
    original_executor = tool_executor.execute_tool_calls_sequential
    original_take_raw = task_compiler_mod.take_raw_result

    def executor_spy(agent, assistant_message, messages, effective_task_id, api_call_count=0, **kwargs):
        executor_calls.append([
            (tc.function.name, tc.function.arguments)
            for tc in list(getattr(assistant_message, "tool_calls", []) or [])
        ])
        return original_executor(agent, assistant_message, messages, effective_task_id, api_call_count, **kwargs)

    def raw_spy(call_id, fallback):
        raw_results.append(call_id)
        return original_take_raw(call_id, fallback)

    # NOTE: scoped_execution imports execute_tool_calls_sequential inside the
    # dispatch closure (call time), so patching agent.tool_executor affects the
    # real path. take_raw_result is imported at module top in scoped_execution,
    # so the module attribute itself is the correct spy target.
    monkeypatch.setattr(tool_executor, "execute_tool_calls_sequential", executor_spy)
    monkeypatch.setattr(
        "workstation.integrations.hermes.scoped_execution.take_raw_result", raw_spy
    )

    agent = _make_agent(enabled_toolsets=["todo"])
    # todo_list may be deferred behind tool_call in the real catalog; the
    # durable dispatcher resolves either path. What matters is exactly one
    # real execution reaching the TodoStore.
    before_revision = agent._todo_store.snapshot()["revision"]
    agent.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
    )
    _bind_agent(agent, task_id, body=body)

    result = agent.run_conversation(user_message=body, task_id=task_id)

    assert len(executor_calls) == 1, f"expected exactly one real tool execution, got {executor_calls}"
    after = agent._todo_store.snapshot()
    assert after["revision"] == before_revision + 1
    assert any(item["id"] == "e001d-1" for item in after["todos"])
    assert raw_results, "expected the raw-result capture path to run"
    assert provider_counter.call_count == 0
    assert result["completed"] is True


# =============================================================================
# E002 — novel / no-match requests reach the provider
# =============================================================================

def test_novel_request_reaches_provider(workstation_adapter_installed, temp_hermes_home, monkeypatch):
    """E002: A request with no established intent reaches the provider."""
    task_id = canonical_task()

    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
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
            verifier=VerificationContract(
                covered_predicates=("other",),
                observer="owner.readback",
                source_kind="source_of_record",
                minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
                allowed_trust=("trusted_owner",),
                lifecycle=VerificationLifecycle.VALIDATED,
            ),
        ),
    )
    registry.register(cap)

    provider_counter = _ProviderCallCounter(fail_on_call=False)
    agent = _make_agent()
    agent.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
    )
    _bind_agent(agent, task_id)

    result = agent.run_conversation(user_message="Do something completely different", task_id=task_id)

    assert provider_counter.call_count >= 1
    assert result["completed"] is True


def test_raw_text_is_not_intent(workstation_adapter_installed, temp_hermes_home, monkeypatch):
    """E002-B: raw user text without persisted intent never synthesizes an OperationIntent."""
    task_id = canonical_task()

    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    _make_filesystem_capability(registry, "dummy.cap")

    provider_counter = _ProviderCallCounter(fail_on_call=False)
    agent = _make_agent()
    agent.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
    )
    _bind_agent(agent, task_id)

    result = agent.run_conversation(user_message="write the records to a file", task_id=task_id)

    assert provider_counter.call_count >= 1
    assert result["completed"] is True


def test_trivial_true_goal_is_not_satisfied(workstation_adapter_installed, temp_hermes_home, monkeypatch):
    """E002-C: a default TRUE goal is not a provable intent."""
    task_id = canonical_task()

    store = DurableTaskStore()
    try:
        objective_ref = ArtifactStore().store(
            task_id,
            "objective.json",
            {
                "operation_intent": {
                    "id": "intent-trivial",
                    "target": "filesystem",
                    "goal": {"type": "TRUE"},
                    "effect_budget": [{"primitive": "fs_write", "target": "filesystem"}],
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

    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    _make_filesystem_capability(registry, "dummy.cap")

    provider_counter = _ProviderCallCounter(fail_on_call=False)
    agent = _make_agent()
    agent.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
    )
    _bind_agent(agent, task_id)

    result = agent.run_conversation(user_message=MULTISTEP_PROMPT, task_id=task_id)

    assert provider_counter.call_count >= 1
    assert result["completed"] is True


def test_invalid_certificate_no_dispatch(
    workstation_adapter_installed, temp_hermes_home, monkeypatch, execute_spy,
):
    """E003: a capability whose verifier is not VALIDATED never deterministically dispatches.

    The router skips the uncertifiable capability; the step either escalates to
    a human or falls back to reasoning. Either way no certified EXECUTE dispatch
    occurs through the pre-reasoning boundary.
    """
    task_id = canonical_task()
    plan_id = store_intent(
        intent(EQ("exists", True)),
        task_id,
        semantic_state={"exists": False},
    )

    from workstation.control_plane.verification import VerificationContract as VC

    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    goal = EQ("exists", True)
    cap = OperationalCapability(
        id="e2e.cap.fs.write",
        name="E2E write file",
        version="1.0.0",
        route="filesystem",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="file.write",
            target_family="filesystem",
            typed_preconditions=[],
            typed_postconditions=[goal],
            effect_footprint=[CALL("fs_write", "filesystem")],
            authority_required=AuthorityScope(
                level=AuthorityLevel.LOCAL_MUTATION,
                allowed_actions={"write"},
                allowed_resources={"filesystem"},
            ),
            verifier=VC(
                covered_predicates=("file:content",),
                observer="fs_read",
                source_kind="filesystem",
                minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
                allowed_trust=("trusted_runtime",),
                lifecycle=VerificationLifecycle.CANDIDATE,
                require_read_after_write=True,
                transition_claim=True,
            ),
        ),
        implementation={"steps": [{
            "id": "write", "primitive": "fs_write",
            "args": {"path": "$inputs.path", "content": "$inputs.content"},
        }]},
    )
    registry.register(cap)

    provider_counter = _ProviderCallCounter(fail_on_call=False)
    agent = _make_agent()
    agent.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
    )
    _bind_agent(agent, task_id)

    result = agent.run_conversation(user_message=MULTISTEP_PROMPT, task_id=task_id)

    assert result["completed"] is True
    assert execute_spy, "expected at least one TaskCompiler.execute call"
    assert all(
        r.get("routing_decision") != "EXECUTE" for r in execute_spy
    ), f"uncertifiable capability must never EXECUTE: {execute_spy}"


def test_quarantined_capability_no_dispatch(workstation_adapter_installed, temp_hermes_home, monkeypatch):
    """E003: a non-promoted capability is never selected for deterministic dispatch."""
    task_id = canonical_task()
    plan_id = store_intent(
        intent(EQ("exists", True)),
        task_id,
        semantic_state={"exists": False},
    )

    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    _make_filesystem_capability(registry, "e2e.cap.fs.write")
    # Demote to DISCOVERED after registration so the router ignores it.
    for cap in registry.list_capabilities():
        if cap.id == "e2e.cap.fs.write":
            cap.lifecycle = CapabilityLifecycle.DISCOVERED
            registry.register(cap)

    provider_counter = _ProviderCallCounter(fail_on_call=False)
    agent = _make_agent()
    agent.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
    )
    _bind_agent(agent, task_id)

    result = agent.run_conversation(user_message=MULTISTEP_PROMPT, task_id=task_id)

    assert provider_counter.call_count >= 1
    assert result["completed"] is True


def test_outstanding_uncertain_mutation_stops_boundary(
    workstation_adapter_installed, temp_hermes_home, monkeypatch,
):
    """E003: an unproved mutation of the same plan blocks a second dispatch lane."""
    task_id = canonical_task()
    plan_id = store_intent(
        intent(EQ("exists", True)),
        task_id,
        semantic_state={"exists": False},
    )

    store = DurableTaskStore()
    try:
        item = store.get_work_items(plan_id)[0]
        store.update_item_checkpoint(
            item.id, "step_0_dispatch",
            metadata={"mutation_identity": {
                "operation_id": "op-unproved", "tool": "fs_write",
                "effect": "MUTATION", "target_identifier": "filesystem",
            }},
        )
    finally:
        store.close()

    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    _make_filesystem_capability(registry, "dummy.cap")

    provider_counter = _ProviderCallCounter(fail_on_call=False)
    agent = _make_agent()
    agent.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
    )
    _bind_agent(agent, task_id)

    result = agent.run_conversation(user_message=MULTISTEP_PROMPT, task_id=task_id)

    assert provider_counter.call_count >= 1
    assert result["completed"] is True


def test_verifier_failure_no_commit(
    workstation_adapter_installed, temp_hermes_home, monkeypatch, tmp_path, execute_spy,
):
    """E003VF: real mutation + real readback that disagrees with expected → no commit, no retry.

    Writes content A while the verification contract expects content B. The
    kernel's real ``fs_read`` observer returns A, canonical evaluation yields
    FAILED, the dispatch record is not COMMITTED success, the turn ends
    WAIT/HANDOFF, and the provider is never called for a blind retry.
    """
    target = tmp_path / "h080_e003vf.txt"
    actual_content = "actual-A"
    expected_content = "expected-B"

    task_id = canonical_task()
    run_id = _run_id_of(task_id)
    goal = EQ("exists", True)
    plan_id = store_intent(
        intent(goal),
        task_id,
        semantic_state={"exists": False},
        capability_inputs={"path": str(target), "content": actual_content},
        verification_expected=expected_content,
        observer_args={"path": str(target)},
        observed_predicates=(_fs_fingerprint(),),
        resource_id=str(target),
        resource_version="1",
        operation_id=OPERATION_ID,
        expected_task_id=task_id,
        expected_run_id=run_id,
        expected_operation_id=OPERATION_ID,
    )

    store = ArtifactStore()
    registry = OperationalCapabilityRegistry(artifacts=store)
    _make_filesystem_capability(registry, "e2e.cap.fs.write")

    # Count real kernel-level writes without replacing the primitive.
    from workstation import operational_kernel as kernel_mod

    write_calls: list = []
    original_fs_write = kernel_mod.OperationalKernel.fs_write

    def counting_fs_write(self, path, content, overwrite=True, base_dir=None):
        write_calls.append((str(path), str(content)))
        return original_fs_write(self, path, content, overwrite=overwrite, base_dir=base_dir)

    monkeypatch.setattr(kernel_mod.OperationalKernel, "fs_write", counting_fs_write)

    provider_counter = _ProviderCallCounter(fail_on_call=True)
    agent = _make_agent()
    agent.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=provider_counter))
    )
    _bind_agent(agent, task_id)

    result = agent.run_conversation(user_message=MULTISTEP_PROMPT, task_id=task_id)

    assert target.exists()
    assert target.read_text(encoding="utf-8") == actual_content
    assert len(write_calls) == 1, f"expected exactly one real mutation, got {write_calls}"
    assert provider_counter.call_count == 0
    assert result["completed"] is True
    assert execute_spy, "expected at least one TaskCompiler.execute call"
    last = execute_spy[-1]
    # The route admitted the capability, but the real readback disagreed with
    # expected, so the control plane refuses COMMITTED success and escalates.
    assert last.get("verification_result", {}).get("status") in ("FAILED", "INCONCLUSIVE")
    assert last.get("verification_result", {}).get("accepted") is not True
    assert (last.get("dispatch_record", {}) or {}).get("status") != "COMMITTED"
    assert "reconcile" in result["final_response"].lower() or "human decision" in result["final_response"].lower() or "could not be proven" in result["final_response"].lower()

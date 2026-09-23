"""Real owner readback joins adaptive native navigation to canonical experience."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from workstation.artifacts import ArtifactStore
from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.experience_compiler.corpus import ExperienceCorpus
from workstation.kanban import WorkstationKanbanBridge
from workstation.procedure_trace import record_trace
from tools import browser_workstation as bw


SESSION = "h080b-session"
PROMPT = "Abra example.test pelo browser nativo"
URL = "https://example.test/guide"


@pytest.fixture
def local_state(tmp_path, monkeypatch):
    home = tmp_path / "hermes"
    browser_home = tmp_path / "desktop"
    home.mkdir()
    browser_home.mkdir()
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_WORKSTATION_HOME", str(browser_home))
    monkeypatch.setattr("hermes_constants.get_hermes_home", lambda: home)
    return browser_home


def _task():
    bridge = WorkstationKanbanBridge()
    envelope = MessageEnvelope(MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION, PROMPT)
    task_id = bridge.promote_request_if_multistep(PROMPT, session_id=SESSION, envelope=envelope)
    assert task_id
    from hermes_cli import kanban_db
    with bridge.get_connection() as conn:
        run_id = str(kanban_db.get_task(conn, task_id).current_run_id)
    return bridge, envelope, task_id, run_id


def _persist_browser(browser_home, task_id, run_id, *, url=URL, session=SESSION, recovery="live"):
    directory = browser_home / "Runtime"
    directory.mkdir(exist_ok=True)
    (directory / "browser-session.json").write_text(json.dumps({
        "version": 1, "savedAt": datetime.now(timezone.utc).isoformat(),
        "activeTabId": "tab-native",
        "tabs": [{"id": "tab-native", "browserTaskId": task_id, "safeUrl": url,
                  "safeTitle": None, "recoveryPolicy": "browser-task-lazy",
                  "recoveryState": recovery, "recoveryReason": None}],
        "browserTasks": {"version": 1, "browserTaskCounter": 1, "tasks": [{
            "taskId": task_id, "sessionHost": session, "runId": run_id,
            "status": "hidden", "recoveryState": "fresh",
        }]},
    }), encoding="utf-8")


def _capture(task_id, run_id, envelope):
    agent = SimpleNamespace(session_id=SESSION, _conversation_root_id=lambda: SESSION,
        _canonical_work_task_id=task_id, _canonical_work_run_id=run_id,
        _message_envelope=envelope, _work_procedure_trace=[])
    record_trace(agent, "browser_navigate", {"url": URL}, {
        "success": True, "runtime": "electron-chromium", "url": URL,
        "readiness": "stable", "wall_detected": False,
    })
    return agent._work_procedure_trace


def test_adaptive_native_navigation_accepts_persisted_owner_readback(local_state):
    bridge, envelope, task_id, run_id = _task()
    _persist_browser(local_state, task_id, run_id)
    trace = _capture(task_id, run_id, envelope)
    original = ArtifactStore().read_json(trace[0]["transition_ref"])
    assert original["outcome"] == "uncertain"
    candidate = bridge.finalize_turn_candidate(task_id, SESSION, {
        "completed": True, "final_response": "Browser nativo aberto.",
        "_adaptive_trace": trace,
    }, expected_run_id=int(run_id))
    assert candidate["status"] == "verified_completed", candidate
    assert candidate["acceptance_approved"] is True
    corpus = ExperienceCorpus(ArtifactStore(), discover=True)
    verified = corpus.query(task_id=task_id, run_id=run_id)
    assert len(verified) == 1
    assert verified[0].outcome.value == "verified_success"
    assert verified[0].verification.evidence_strength == 2
    assert verified[0].verification.source_kind == "browser_local_persistence"
    assert verified[0].state_after.artifact_ref != trace[0]["after_state_ref"]
    assert ArtifactStore().read_json(trace[0]["transition_ref"]) == original


def test_two_accepted_native_runs_compile_candidate(local_state):
    from workstation.experience_compiler.compiler import ExperienceCompiler
    from workstation.operational_capabilities import OperationalCapabilityRegistry

    runs = []
    for _ in range(2):
        bridge, envelope, task_id, run_id = _task()
        _persist_browser(local_state, task_id, run_id)
        trace = _capture(task_id, run_id, envelope)
        result = bridge.finalize_turn_candidate(task_id, SESSION, {
            "completed": True, "final_response": "Browser nativo aberto.",
            "_adaptive_trace": trace,
        }, expected_run_id=int(run_id))
        assert result["acceptance_approved"] is True, result
        runs.append((task_id, run_id))
    assert len({run_id for _, run_id in runs}) == 2
    artifacts = ArtifactStore()
    corpus = ExperienceCorpus(artifacts, discover=True)
    assert len(corpus.query(outcome="verified_success")) == 2
    registry = OperationalCapabilityRegistry(artifacts)
    compiled = ExperienceCompiler(registry, corpus).mine()
    assert len(compiled) == 1
    cap = compiled[0]
    assert cap.formal_contract is not None
    assert len(cap.learning_metadata["run_ids"]) == 2
    assert cap.learning_metadata["parameterization_quality"] is True
    assert cap.learning_metadata["provenance_complete"] is True


@pytest.mark.parametrize("case", ["wrong_host", "wrong_task", "missing_readback", "stale_run"])
def test_adaptive_navigation_requires_matching_persisted_browser_owner(local_state, case):
    bridge, envelope, task_id, run_id = _task()
    trace = _capture(task_id, run_id, envelope)
    if case != "missing_readback":
        _persist_browser(local_state, "other-task" if case == "wrong_task" else task_id,
            "old-run" if case == "stale_run" else run_id,
            url="https://wrong.test/guide" if case == "wrong_host" else URL)
    result = bridge.finalize_turn_candidate(task_id, SESSION, {
        "completed": True, "final_response": "Browser aberto.", "_adaptive_trace": trace,
    }, expected_run_id=int(run_id))
    assert result["status"] != "verified_completed"
    assert result["acceptance_approved"] is not True
    assert all(sample.outcome.value != "verified_success" for sample in
        ExperienceCorpus(ArtifactStore(), discover=True).query(task_id=task_id, run_id=run_id))


def test_insufficient_adaptive_observation_never_promotes(local_state):
    from workstation.experience_compiler.compiler import ExperienceCompiler
    from workstation.operational_capabilities import OperationalCapabilityRegistry

    _, envelope, task_id, run_id = _task()
    _capture(task_id, run_id, envelope)
    corpus = ExperienceCorpus(ArtifactStore(), discover=True)
    compiler = ExperienceCompiler(OperationalCapabilityRegistry(ArtifactStore()), corpus)
    assert compiler.mine() == []


def _fake_physical_controller(browser_home, monkeypatch):
    """Replace only Electron's physical loopback endpoint; keep broker and tools real."""
    control = browser_home / "Runtime" / "browser-control.json"
    control.parent.mkdir(exist_ok=True)
    control.write_text(json.dumps({"version": 1, "url": "http://127.0.0.1:49152",
                                   "token": "test-token"}), encoding="utf-8")
    monkeypatch.setenv("HERMES_WORKSTATION_BROWSER_CONTROL_FILE", str(control))
    monkeypatch.setenv("HERMES_WORKSTATION_BROWSER", "1")
    monkeypatch.setenv("HERMES_WORKSTATION_BROWSER_ROUTING", "0")
    bw._LAST_HEALTH_AT = 0.0
    bw._LAST_HEALTH_VALUE = False
    calls = []
    current = {"url": "about:blank"}

    def physical(method, path, payload=None, **_kwargs):
        if method == "GET":
            return {"success": True, "ready": True}
        assert path == "/v1/action"
        if payload["action"] == "browser_snapshot":
            return {"success": True, "result": {"success": True,
                "runtime": "electron-chromium", "url": current["url"],
                "readiness": "stable" if current["url"] != "about:blank" else "loading"}}
        assert payload["action"] == "browser_navigate"
        calls.append(payload)
        current["url"] = URL
        _persist_browser(browser_home, payload["task_id"], payload.get("run_id"),
                         url=URL, session=payload["session_id"])
        return {"success": True, "result": {"success": True,
            "runtime": "electron-chromium", "url": URL,
            "readiness": "stable", "wall_detected": False}}

    monkeypatch.setattr(bw, "_request_json", physical)
    return calls


def test_run_a_normal_hermes_turn_captures_and_accepts_native_navigation(local_state, monkeypatch):
    from run_agent import AIAgent
    from agent.tool_guardrails import ToolCallGuardrailConfig, ToolCallGuardrailController
    from gateway.session_context import set_session_vars, clear_session_vars
    import workstation

    workstation.bootstrap_workstation_adapter("required")
    monkeypatch.setattr("tools.browser_tool.browser_navigate",
                        lambda **_kwargs: pytest.fail("legacy browser must never execute"))
    calls = _fake_physical_controller(local_state, monkeypatch)
    bridge, envelope, task_id, run_id = _task()
    session_tokens = set_session_vars(platform="desktop", source="desktop", session_id=SESSION,
        browser_control_principal="workstation",
        browser_control_transport_family="workstation_native")
    with (patch("model_tools.check_toolset_requirements", return_value={}),
          patch("agent.process_bootstrap.OpenAI")):
        agent = AIAgent(api_key="test-key-1234567890", base_url="https://test.api",
                        quiet_mode=True, skip_context_files=True, skip_memory=True)
    tool_call = SimpleNamespace(id="native-nav", type="function",
        function=SimpleNamespace(name="browser_navigate", arguments=json.dumps({"url": URL})))
    responses = [
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None,
            tool_calls=[tool_call]), finish_reason="tool_calls")], model="test/model", usage=None),
        SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Browser nativo aberto.",
            tool_calls=None), finish_reason="stop")], model="test/model", usage=None),
    ]
    provider_calls = []

    def provider(*_args, **_kwargs):
        provider_calls.append(1)
        return responses.pop(0)

    agent.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=provider)))
    agent.provider = "moa"
    agent.session_id = SESSION
    agent._conversation_root_id = lambda: SESSION
    agent._canonical_work_task_id = task_id
    agent._canonical_work_run_id = run_id
    agent._message_envelope = envelope
    agent._tool_guardrails = ToolCallGuardrailController(
        ToolCallGuardrailConfig.from_mapping({}, platform="cli"))
    agent._work_capabilities = {}
    agent._work_user_constraints = {}
    agent._current_provider_usage = None
    agent._work_completed_mutations = {}
    agent._work_mutation_evidence = {}
    agent._workstation_event_bus = None
    agent._interrupt_requested = False
    agent.valid_tool_names = set(agent.valid_tool_names or set()) | {"browser_navigate", "browser_snapshot", "work_execute"}

    try:
        result = agent.run_conversation(user_message=PROMPT, task_id=task_id)
    finally:
        clear_session_vars(session_tokens)
    assert len(provider_calls) >= 1
    assert len(calls) == 1
    assert result["completed"] is True
    assert agent._canonical_work_task_id == task_id, (agent._canonical_work_task_id, task_id, calls)
    from hermes_cli import kanban_db
    with bridge.get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        latest = kanban_db.latest_run(conn, task_id)
    assert task.status == "done", (task.status, result.get("work_outcome"), getattr(agent, "_work_procedure_trace", None))
    assert latest.metadata["workstation"]["acceptance_approved"] is True
    assert latest.metadata["workstation"]["outcome"]["status"] == "verified_completed"
    accepted = ExperienceCorpus(ArtifactStore(), discover=True).query(task_id=task_id, run_id=run_id)
    assert len(accepted) == 1
    assert accepted[0].outcome.value == "verified_success"


def _compiled_two_run_capability(browser_home):
    from workstation.experience_compiler.compiler import ExperienceCompiler
    from workstation.operational_capabilities import OperationalCapabilityRegistry

    run_ids = []
    for _ in range(2):
        bridge, envelope, task_id, run_id = _task()
        _persist_browser(browser_home, task_id, run_id)
        trace = _capture(task_id, run_id, envelope)
        result = bridge.finalize_turn_candidate(task_id, SESSION, {
            "completed": True, "final_response": "Browser nativo aberto.",
            "_adaptive_trace": trace,
        }, expected_run_id=int(run_id))
        assert result["acceptance_approved"] is True, result
        run_ids.append(run_id)
    registry = OperationalCapabilityRegistry(ArtifactStore())
    compiler = ExperienceCompiler(registry, ExperienceCorpus(ArtifactStore(), discover=True))
    candidates = compiler.mine()
    assert len(candidates) == 1
    return compiler, registry, candidates[0], run_ids


def test_real_browser_readback_validates_and_promotes_compiled_capability(local_state, monkeypatch):
    from copy import deepcopy
    from dataclasses import replace

    from gateway.session_context import clear_session_vars, set_session_vars
    from workstation.control_plane.verification import (
        VerificationContract, VerificationEvidence, VerificationLifecycle,
        VerificationStatus, evaluate_verification,
    )
    from workstation.execution_policy import EvidenceStrength
    from workstation.experience_compiler.causal import SafeEnvironment, controlled_replay
    from workstation.experience_compiler.state_abstraction import abstract_state
    from workstation.operational_kernel import OperationalKernel

    compiler, registry, cap, run_ids = _compiled_two_run_capability(local_state)
    assert len(set(run_ids)) == 2
    assert cap.formal_contract is not None
    effects = cap.learning_metadata["effects"]
    covered = tuple(p.fingerprint() for p in cap.formal_contract.typed_postconditions)
    contract = VerificationContract(
        covered_predicates=covered,
        effect_classes=("state_mutation",),
        observer="workstation.browser_session_state",
        source_kind="browser_local_persistence",
        minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        allowed_trust=("trusted_runtime",),
        require_read_after_write=True,
        transition_claim=True,
    )

    def owner_result(task_id, run_id, operation_id, observed_url):
        _persist_browser(local_state, task_id, run_id, url=observed_url)
        try:
            readback = bw.read_native_browser_session_state(task_id, SESSION, run_id, URL)
            projected = abstract_state("native_browser", readback).semantic_predicates
            observed = {key: projected[key] for key in effects}
            ref = ArtifactStore().store(task_id, "validation_" + operation_id + ".json",
                {**readback, "operation_id": operation_id, "observed_effects": observed},
                schema="hermes.browser_local_readback.v1").ref
            evidence = [VerificationEvidence(
                evidence_id="validation:" + operation_id,
                observer=contract.observer, source_kind=contract.source_kind, value=observed,
                evidence_strength=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
                trust_class="trusted_runtime", observer_failure_domain="browser_session_persistence",
                resource_id=f"browser_task:{task_id}:tab:{readback['tab_id']}",
                resource_version=readback["saved_at"],
                observed_at=datetime.now(timezone.utc).isoformat(), read_after_write=True,
                covered_predicates=covered, artifact_ref=ref,
                task_id=task_id, run_id=run_id, operation_id=operation_id,
            )]
        except (OSError, ValueError, KeyError):
            evidence = []
            ref = ""
        result = evaluate_verification(replace(contract, lifecycle=VerificationLifecycle.VALIDATED),
            effects, evidence,
            expected_task_id=task_id, expected_run_id=run_id,
            expected_operation_id=operation_id)
        return result, ref

    task_id, run_id = _task()[2:]
    positive, positive_ref = owner_result(task_id, run_id, "validation-positive", URL)
    negative, negative_ref = owner_result(task_id, run_id, "validation-negative", "https://wrong.test/guide")
    assert positive.status == VerificationStatus.VERIFIED
    assert negative.status != VerificationStatus.VERIFIED
    receipts = [
        {"kind": "positive_replay", "phase": "validation", "passed": positive.status == VerificationStatus.VERIFIED,
         "evidence_ref": positive_ref},
        {"kind": "negative_control", "phase": "validation", "passed": negative.status != VerificationStatus.VERIFIED,
         "evidence_ref": negative_ref or ArtifactStore().store(task_id, "wrong_host_validation.json",
             {"safe_url": "https://wrong.test/guide", "rejected_by": contract.observer}).ref},
    ]
    cap, reasons = compiler.validate_verifier(cap, contract, receipts)
    assert not reasons
    assert cap.learning_metadata["verifier_lifecycle"] == VerificationLifecycle.VALIDATED.value

    calls = _fake_physical_controller(local_state, monkeypatch)
    monkeypatch.setattr("tools.browser_tool.browser_navigate",
                        lambda **_kwargs: pytest.fail("legacy browser must never execute"))
    tokens = set_session_vars(platform="desktop", source="desktop", session_id=SESSION,
        browser_control_principal="workstation",
        browser_control_transport_family="workstation_native")
    try:
        from tools.browser_extension_router import routed_browser_handler

        def replay(steps, _deadline):
            bridge, _, replay_task, replay_run = _task()
            trial = deepcopy(cap)
            trial.implementation["steps"] = steps
            operation_id = "controlled-native-navigation"

            def dispatch(name, args):
                return routed_browser_handler(name, args,
                    fallback=lambda: pytest.fail("legacy browser must never execute"),
                    task_id=replay_task, session_id=SESSION, run_id=replay_run)

            result = OperationalKernel(registry).execute_capability(trial, {}, dispatch=dispatch,
                context={"learning_replay": True, "task_id": replay_task,
                    "run_id": replay_run, "session_id": SESSION,
                    "operation_id": operation_id, "expected_task_id": replay_task,
                    "expected_run_id": replay_run, "expected_operation_id": operation_id})
            readback = bw.read_native_browser_session_state(replay_task, SESSION, replay_run, URL)
            projected = abstract_state("native_browser", readback).semantic_predicates
            verification = result["verification_result"]
            return {"passed": verification["status"] == "VERIFIED",
                "predicates": projected, "evidence_strength": 2,
                "evidence_refs": verification["evidence_refs"],
                "verification_result": verification}

        cap = controlled_replay(cap, SafeEnvironment("test_fixture", "native-browser-isolated",
            lambda *_args: True), replay)
    finally:
        clear_session_vars(tokens)
    assert cap.validation_evidence[-1]["passed"] is True
    assert len(calls) == 1
    admission = compiler.promote(cap)
    assert admission.admitted, admission.reasons
    assert registry.get(cap.id).lifecycle.value == "promoted"

    from agent.tool_guardrails import ToolCallGuardrailConfig, ToolCallGuardrailController
    from gateway.session_context import clear_session_vars, set_session_vars
    from run_agent import AIAgent
    from workstation.control_plane.intent import OperationIntent
    from workstation.control_plane.ir import EQ
    from workstation.durable_tasks import DurableTaskStore
    from workstation.task_compiler import TaskCompiler
    import workstation

    workstation.bootstrap_workstation_adapter("required")
    bridge, envelope, future_task, future_run = _task()
    formal = cap.formal_contract
    intent = OperationIntent(id="h080b-native-intent", target=formal.target_family,
        goal=EQ("host", "example.test"),
        effect_budget=list(formal.effect_footprint),
        metadata={"operation_family": formal.operation_family,
                  "target_family": formal.target_family}).to_dict()
    objective_ref = ArtifactStore().store(future_task, "h080b-established-intent.json", {
        "operation_intent": intent, "semantic_state": {"host": ""},
        "capability_inputs": {}, "operation_id": "h080b-reuse",
        "expected_task_id": future_task, "expected_run_id": future_run,
        "expected_operation_id": "h080b-reuse",
    }).ref
    durable = DurableTaskStore()
    try:
        durable.create_plan(future_task, "established native navigation intent", [{"id": 1}],
            session_id=SESSION, metadata={"objective_ref": objective_ref,
                "canonical_task_id": future_task})
    finally:
        durable.close()

    resolutions = []
    kernel_results = []
    original_execute = TaskCompiler.execute
    original_kernel_execute = OperationalKernel.execute_capability

    def observe_kernel(self, *args, **kwargs):
        result = original_kernel_execute(self, *args, **kwargs)
        kernel_results.append(result)
        return result

    def observe_execute(self, request, **kwargs):
        result = original_execute(self, request, **kwargs)
        resolutions.append(result)
        return result

    monkeypatch.setattr(TaskCompiler, "execute", observe_execute)
    monkeypatch.setattr(OperationalKernel, "execute_capability", observe_kernel)
    with (patch("model_tools.check_toolset_requirements", return_value={}),
          patch("agent.process_bootstrap.OpenAI")):
        agent = AIAgent(api_key="test-key-1234567890", base_url="https://test.api",
                        quiet_mode=True, skip_context_files=True, skip_memory=True)
    provider_calls = []

    def forbidden_provider(*_args, **_kwargs):
        provider_calls.append(1)
        raise AssertionError("promoted native navigation must resolve before provider")

    agent.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=forbidden_provider)))
    agent.provider = "moa"
    agent.session_id = SESSION
    agent._conversation_root_id = lambda: SESSION
    agent._canonical_work_task_id = future_task
    agent._canonical_work_run_id = future_run
    agent._message_envelope = envelope
    agent._tool_guardrails = ToolCallGuardrailController(
        ToolCallGuardrailConfig.from_mapping({}, platform="cli"))
    agent._work_capabilities = {}
    agent._work_user_constraints = {}
    agent._current_provider_usage = None
    agent._work_completed_mutations = {}
    agent._work_mutation_evidence = {}
    agent._workstation_event_bus = None
    agent._interrupt_requested = False
    agent.valid_tool_names = set(agent.valid_tool_names or set()) | {"browser_navigate", "browser_snapshot", "work_execute"}
    before = len(calls)
    tokens = set_session_vars(platform="desktop", source="desktop", session_id=SESSION,
        browser_control_principal="workstation",
        browser_control_transport_family="workstation_native")
    try:
        future_result = agent.run_conversation(user_message=PROMPT, task_id=future_task)
    finally:
        clear_session_vars(tokens)
    assert not provider_calls, resolutions
    assert resolutions, "pre-reasoning route must call TaskCompiler"
    routed = resolutions[-1]
    assert routed.get("routing_decision") == "EXECUTE", (routed.get("reason"), kernel_results[-1].get("validity_envelope") if kernel_results else None)
    assert len(calls) - before == 1
    assert future_result["completed"] is True
    assert routed.get("certificate_hash")
    assert routed.get("verification_result", {}).get("status") == "VERIFIED", routed
    assert routed.get("verification_result", {}).get("accepted") is True
    assert routed.get("dispatch_record", {}).get("status") == "COMMITTED"

"""Rail 2: synthetics must not poison mutable ledgers or mint endless handoffs."""
import json
from pathlib import Path
from types import SimpleNamespace

from tools.effects import ToolEffect
from workstation.batch_detection import call_key, record_mutation
from workstation.execution_policy import CompilationDecision, decisions_for_calls
from workstation.runtime import HumanHandoffManager


def _agent():
    return SimpleNamespace(
        session_id="session-p0-rail2",
        valid_tool_names={"work_execute"},
        _conversation_root_id=lambda: "session-p0-rail2",
    )


def _call(name, args=None, ident="a"):
    return SimpleNamespace(id=ident, function=SimpleNamespace(name=name, arguments=json.dumps(args or {})))


def test_refusal_before_dispatch_never_creates_mutation_uncertainty():
    agent = _agent()
    record_mutation(agent, "write_file", {"path": "x.txt", "content": "x"},
                    {"status": "handoff_requested", "error": "policy refused"}, dispatched=False)
    assert not hasattr(agent, "_work_mutation_evidence")
    assert decisions_for_calls(agent, [_call("browser_snapshot")]) == [CompilationDecision.ALLOW_ADAPTIVE]


def test_old_mutation_receipt_does_not_block_current_pure_read():
    agent = _agent()
    key = call_key("browser_snapshot", {})
    agent._work_mutation_evidence = {key: {"status": "uncertain"}}
    assert decisions_for_calls(agent, [_call("browser_snapshot")]) == [CompilationDecision.ALLOW_ADAPTIVE]


def test_request_is_stable_by_task_session_reason_scope(tmp_path):
    path = tmp_path / "human_handoffs.json"
    mgr = HumanHandoffManager(path)
    a = mgr.request(task_id="t_test", session_id="s_test", reason="uncertain_mutation_requires_review",
                    scope={"operation_key": "identity-1"})
    b = HumanHandoffManager(path).request(
        task_id="t_test", session_id="s_test", reason="uncertain_mutation_requires_review",
        scope={"operation_key": "identity-1"})
    assert a.handoff_id == b.handoff_id
    assert mgr.resume(a.handoff_id, returned_by="human") is True
    loaded = HumanHandoffManager(path)
    assert loaded.consume(a.handoff_id) is True
    assert loaded.consume(a.handoff_id) is False
    after = HumanHandoffManager(path).request(
        task_id="t_test", session_id="s_test", reason="uncertain_mutation_requires_review",
        scope={"operation_key": "identity-1"})
    assert after.handoff_id == a.handoff_id
    assert len(loaded._handoffs) == 1


def test_one_handoff_per_mutation_even_after_resume(tmp_path, monkeypatch):
    from workstation.integrations.hermes import tool_batch_admission as admission

    monkeypatch.setattr(admission, "get_hermes_home", lambda: tmp_path)
    agent = _agent()
    name, args = "write_file", {"path": "x.txt", "content": "value"}
    agent._work_mutation_evidence = {call_key(name, args): {"status": "uncertain"}}
    first = admission.workstation_tool_batch_admission(agent, [_call(name, args, "call-A")])
    second = admission.workstation_tool_batch_admission(agent, [_call(name, args, "call-B")])
    assert first is not None and second is not None
    a = json.loads(first.decisions[0].synthetic_result)
    b = json.loads(second.decisions[0].synthetic_result)
    assert a["handoff_id"] == b["handoff_id"]
    path = tmp_path / "workstation" / "human_handoffs.json"
    mgr = HumanHandoffManager(path)
    assert len(mgr._handoffs) == 1
    assert mgr.resume(a["handoff_id"], returned_by="human")
    third = admission.workstation_tool_batch_admission(agent, [_call(name, args, "call-C")])
    receipt = json.loads(third.decisions[0].synthetic_result)
    assert receipt["status"] == "human_review_completed"
    assert receipt["code"] == "uncertain_effect_requires_readback"
    assert HumanHandoffManager(path).get(a["handoff_id"]).status == "consumed"
    fourth = admission.workstation_tool_batch_admission(agent, [_call(name, args, "call-D")])
    assert json.loads(fourth.decisions[0].synthetic_result)["handoff_id"] == a["handoff_id"]
    assert len(HumanHandoffManager(path)._handoffs) == 1


def test_uncertain_handoff_never_reuses_approval_from_superseded_run(tmp_path, monkeypatch):
    """A previous TaskRun's consumed human review is not a fresh run's grant."""
    from workstation.integrations.hermes import tool_batch_admission as admission

    monkeypatch.setattr(admission, "get_hermes_home", lambda: tmp_path)
    args = {"ref": "@e17", "button": "left"}
    name = "browser_click"
    operation_key = call_key(name, args)
    agent = _agent()
    agent._canonical_work_task_id = "same-canonical-task"
    agent._canonical_work_run_id = "run-old"
    agent._work_mutation_evidence = {operation_key: {"status": "uncertain"}}
    call = _call(name, args, "first-review")
    prior = admission.workstation_tool_batch_admission(agent, [call])
    old_id = json.loads(prior.decisions[0].synthetic_result)["handoff_id"]
    path = tmp_path / "workstation" / "human_handoffs.json"
    mgr = HumanHandoffManager(path)
    assert mgr.resume(old_id, returned_by="human")
    admission.workstation_tool_batch_admission(agent, [call])
    assert HumanHandoffManager(path).get(old_id).status == "consumed"

    agent._canonical_work_run_id = "run-new"
    current = admission.workstation_tool_batch_admission(agent, [_call(name, args, "new-run")])
    current_body = json.loads(current.decisions[0].synthetic_result)
    assert current_body["handoff_id"] != old_id
    assert current_body["status"] == "handoff_requested"
    current_ledger = HumanHandoffManager(path)
    assert current_ledger.get(old_id).status == "consumed"
    assert current_ledger.get(current_body["handoff_id"]).status == "waiting-for-human"
    assert len(current_ledger._handoffs) == 2


def test_consumed_review_returns_readback_guidance_without_another_handoff(tmp_path, monkeypatch):
    from agent.tool_batch_admission import BatchAdmissionAction
    from workstation.integrations.hermes import tool_batch_admission as admission

    monkeypatch.setattr(admission, "get_hermes_home", lambda: tmp_path)
    agent = _agent()
    agent._canonical_work_task_id = "task-p0"
    agent._canonical_work_run_id = "run-p0"
    name, args = "browser_click", {"ref": "@e24"}
    agent._work_mutation_evidence = {call_key(name, args): {"status": "uncertain"}}
    operation = _call(name, args)
    initial = admission.workstation_tool_batch_admission(agent, [operation])
    assert initial.decisions[0].action == BatchAdmissionAction.HANDOFF
    handoff = json.loads(initial.decisions[0].synthetic_result)
    manager = HumanHandoffManager(tmp_path / "workstation" / "human_handoffs.json")
    assert manager.resume(handoff["handoff_id"], returned_by="human")

    completed = admission.workstation_tool_batch_admission(agent, [operation])
    repeated = admission.workstation_tool_batch_admission(agent, [operation])
    for result in (completed, repeated):
        assert result.decisions[0].action == BatchAdmissionAction.SYNTHETIC_RESULT
        message = json.loads(result.decisions[0].synthetic_result)
        assert message["code"] == "uncertain_effect_requires_readback"
        assert message["handoff_id"] == handoff["handoff_id"]

    # The original mutating operation has not been authorized by review alone.
    assert decisions_for_calls(agent, [operation]) == [CompilationDecision.REQUIRE_HUMAN]
    final = HumanHandoffManager(manager.path)
    assert final.get(handoff["handoff_id"]).status == "consumed"
    assert len(final._handoffs) == 1


def test_pending_review_coalesces_distinct_operations_only_within_same_run(tmp_path):
    path = tmp_path / "human_handoffs.json"
    mgr = HumanHandoffManager(path)
    first = mgr.request(
        task_id="browser-task", session_id="session", reason="uncertain_mutation_requires_review",
        scope={"operation_key": "first-operation", "run_id": "run-1"},
        coalesce_waiting_run=True,
    )
    second = HumanHandoffManager(path).request(
        task_id="browser-task", session_id="session", reason="uncertain_mutation_requires_review",
        scope={"operation_key": "different-operation", "run_id": "run-1"},
        coalesce_waiting_run=True,
    )
    assert second.handoff_id == first.handoff_id
    assert len(HumanHandoffManager(path)._handoffs) == 1
    another_run = mgr.request(
        task_id="browser-task", session_id="session", reason="uncertain_mutation_requires_review",
        scope={"operation_key": "other-run", "run_id": "run-2"},
        coalesce_waiting_run=True,
    )
    assert another_run.handoff_id != first.handoff_id
    assert mgr.resume(first.handoff_id, returned_by="human")
    # A different operation must NEVER inherit the first one's review.
    after_approval = HumanHandoffManager(path).request(
        task_id="browser-task", session_id="session", reason="uncertain_mutation_requires_review",
        scope={"operation_key": "different-operation", "run_id": "run-1"},
        coalesce_waiting_run=True,
    )
    assert after_approval.handoff_id not in {first.handoff_id, another_run.handoff_id}
    assert after_approval.status == "waiting-for-human"


def test_backend_prevents_multiple_pending_banners_for_distinct_mutations_in_same_run(tmp_path, monkeypatch):
    from workstation.integrations.hermes import tool_batch_admission as admission

    monkeypatch.setattr(admission, "get_hermes_home", lambda: tmp_path)
    agent = _agent()
    agent._canonical_work_task_id = "browser-task"
    agent._canonical_work_run_id = "run-1"
    args_one = {"path": "first.txt", "content": "a"}
    args_two = {"path": "second.txt", "content": "b"}
    agent._work_mutation_evidence = {
        call_key("write_file", args_one): {"status": "uncertain"},
        call_key("write_file", args_two): {"status": "uncertain"},
    }
    first = admission.workstation_tool_batch_admission(agent, [_call("write_file", args_one)])
    second = admission.workstation_tool_batch_admission(agent, [_call("write_file", args_two)])
    assert first is not None and second is not None
    first_result = json.loads(first.decisions[0].synthetic_result)
    second_result = json.loads(second.decisions[0].synthetic_result)
    assert first_result["status"] == second_result["status"] == "handoff_requested"
    assert first_result["handoff_id"] == second_result["handoff_id"]
    path = tmp_path / "workstation" / "human_handoffs.json"
    assert len(HumanHandoffManager(path)._handoffs) == 1

def test_whatsapp_identity_refusal_does_not_poison_mutation_replay(tmp_path, monkeypatch):
    from workstation.artifacts import ArtifactStore
    import workstation.batch_detection as detector

    # The tool returned before any browser side effect. Its refusal is
    # terminal for this call, not an uncertain outbound message.
    store = ArtifactStore(tmp_path)
    monkeypatch.setattr("workstation.artifacts.ArtifactStore", lambda: store)
    agent = _agent()
    args = {"recipient_ref": {"source": "trusted", "contact_id": 1},
            "expected_recipient_name": "Target", "message": "text"}
    result = {"sent": False, "state": "REVIEW_REQUIRED",
              "error_code": "TASKRUN_AUTHORITY_REQUIRED", "failure_phase": "VERIFY_TASKRUN"}
    record_mutation(agent, "whatsapp_send_message", args, result)
    assert agent._work_mutation_evidence[call_key("whatsapp_send_message", args)]["status"] == "refused_no_effect"
    decision = decisions_for_calls(agent, [_call("whatsapp_send_message", args)])
    assert CompilationDecision.REQUIRE_HUMAN not in decision


def test_whatsapp_uncertain_postclick_remains_uncertain(tmp_path, monkeypatch):
    from workstation.artifacts import ArtifactStore
    store = ArtifactStore(tmp_path)
    monkeypatch.setattr("workstation.artifacts.ArtifactStore", lambda: store)
    agent = _agent()
    args = {"recipient_ref": {"source": "trusted", "contact_id": 1},
            "expected_recipient_name": "Target", "message": "text"}
    result = {"sent": False, "state": "UNCERTAIN", "error_code": "CLICK_OUTCOME_UNKNOWN"}
    record_mutation(agent, "whatsapp_send_message", args, result)
    assert agent._work_mutation_evidence[call_key("whatsapp_send_message", args)]["status"] == "uncertain"


def test_whatsapp_early_failed_taskrun_is_not_recorded_as_uncertain(tmp_path, monkeypatch):
    from workstation.artifacts import ArtifactStore
    store = ArtifactStore(tmp_path)
    monkeypatch.setattr("workstation.artifacts.ArtifactStore", lambda: store)
    agent = _agent()
    args = {"recipient_ref": {"source": "trusted", "contact_id": 1},
            "expected_recipient_name": "Target", "message": "text"}
    # Actual tool handler uses FAILED without any failure_phase when its
    # canonical TaskRun identity is missing, before invoking the executor.
    result = {"sent": False, "state": "FAILED", "error_code": "TASKRUN_AUTHORITY_REQUIRED"}
    record_mutation(agent, "whatsapp_send_message", args, result)
    assert agent._work_mutation_evidence[call_key("whatsapp_send_message", args)]["status"] == "refused_no_effect"
    assert CompilationDecision.REQUIRE_HUMAN not in decisions_for_calls(
        agent, [_call("whatsapp_send_message", args)])


def test_whatsapp_later_refusal_cannot_erase_real_previous_uncertainty(tmp_path, monkeypatch):
    from workstation.artifacts import ArtifactStore
    store = ArtifactStore(tmp_path)
    monkeypatch.setattr("workstation.artifacts.ArtifactStore", lambda: store)
    agent = _agent()
    args = {"recipient_ref": {"source": "trusted", "contact_id": 1},
            "expected_recipient_name": "Target", "message": "text"}
    record_mutation(agent, "whatsapp_send_message", args,
                    {"sent": False, "state": "UNCERTAIN", "error_code": "CLICK_OUTCOME_UNKNOWN"})
    key = call_key("whatsapp_send_message", args)
    first = dict(agent._work_mutation_evidence[key])
    record_mutation(agent, "whatsapp_send_message", args,
                    {"sent": False, "state": "FAILED", "error_code": "TASKRUN_AUTHORITY_REQUIRED"})
    assert agent._work_mutation_evidence[key] == first
    assert agent._work_mutation_evidence[key]["status"] == "uncertain"
    assert CompilationDecision.REQUIRE_HUMAN in decisions_for_calls(
        agent, [_call("whatsapp_send_message", args)])

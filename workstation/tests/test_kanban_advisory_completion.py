"""Regression: advisory read-only work reaches canonical DONE with durable evidence."""
from types import SimpleNamespace

import pytest

from hermes_cli import kanban_db
from workstation.contracts import (
    AcceptanceContract, IntentAuthority, MessageEnvelope, MessageOrigin,
)
from workstation.integrations.hermes.completion_admission import workstation_completion_admission
from workstation.integrations.hermes.tool_observer import (
    workstation_pre_dispatch_hook, workstation_raw_post_tool_observer,
)
from workstation.kanban import WorkstationKanbanBridge
from workstation.work_intent import prepare_turn_work, work_intent


PROMPT = "Primeiro leia o arquivo, depois compare os dados e resuma os achados."


def _agent():
    return SimpleNamespace(
        session_id="advisory-read-session",
        _conversation_root_id=lambda: "advisory-read-session",
        valid_tool_names={"work_execute"},
        _work_tool_observations=[],
        _work_procedure_trace=[],
        _work_procedure_trace_truncated=False,
    )


def _prepare(agent, prompt=PROMPT):
    envelope = MessageEnvelope(
        MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK,
        agent.session_id, prompt, correlation_id="read-turn-1",
    )
    intent = prepare_turn_work(agent, prompt, envelope)
    assert intent.requires_task
    return intent, agent._canonical_work_task_id


def _candidate(agent, task_id, *, completed=True, trace_truncated=False):
    result = {"completed": completed, "failed": False, "interrupted": False,
              "final_response": "Arquivo lido. As duas observacoes foram comparadas."}
    return workstation_completion_admission(
        task_id, str(agent._canonical_work_run_id or ""),
        {"session_id": agent.session_id, "agent": agent, "turn_result": result,
         "_work_procedure_trace": agent._work_procedure_trace,
         "_work_procedure_trace_truncated": trace_truncated},
    )


def _observe_real_read(agent, path):
    args = {"path": str(path)}
    context = {"agent": agent, "dispatched": True}
    workstation_pre_dispatch_hook("read_file", args, "read-call-1", context)
    raw = {"ok": True, "content": path.read_text(encoding="utf-8")}
    workstation_raw_post_tool_observer(
        "read_file", args, "read-call-1", raw, 0.01, context,
    )
    assert agent._work_tool_observations[0]["status"] == "completed"


def test_advisory_read_reaches_done_with_canonical_run_and_persisted_result(tmp_path):
    agent = _agent()
    intent, task_id = _prepare(agent)
    assert intent.acceptance_policy.policy == "advisory"
    bridge = WorkstationKanbanBridge()
    with bridge.get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        assert task.status == "triage" and task.current_run_id is None
    input_file = tmp_path / "source.txt"
    input_file.write_text("a=1, b=2", encoding="utf-8")
    _observe_real_read(agent, input_file)
    admitted = _candidate(agent, task_id)
    assert admitted.admitted is True, admitted.reason
    # Fresh connection: actual canonical transition, not a mocked report.
    with bridge.get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        assert task.status == "done"
        run = kanban_db.latest_run(conn, task_id)
        assert run.outcome == "completed"
        ws = run.metadata["workstation"]
        assert ws["acceptance_approved"] is True
        assert ws["outcome"]["status"] == "verified_completed"
        assert ws["outcome"]["evidence_refs"][0]["kind"] == "advisory_result"


@pytest.mark.parametrize("case", ["no_read", "truncated", "failed_read"])
def test_advisory_cannot_complete_without_trustworthy_read(case, tmp_path):
    agent = _agent()
    _, task_id = _prepare(agent)
    if case != "no_read":
        path = tmp_path / "source.txt"
        path.write_text("real source", encoding="utf-8")
        _observe_real_read(agent, path)
    if case == "failed_read":
        agent._work_tool_observations[0]["status"] = "failed"
    admitted = _candidate(agent, task_id, trace_truncated=case == "truncated")
    assert admitted.admitted is False
    with WorkstationKanbanBridge().get_connection() as conn:
        assert kanban_db.get_task(conn, task_id).status == "triage"


def test_advisory_cannot_certify_unverified_mutation():
    agent = _agent()
    _, task_id = _prepare(agent)
    # An observed write/unknown tool has no independent persisted readback.
    agent._work_tool_observations.append(
        {"call_id": "write", "tool": "write_file", "effect": "MUTATION",
         "status": "completed"},
    )
    assert _candidate(agent, task_id).admitted is False
    with WorkstationKanbanBridge().get_connection() as conn:
        assert kanban_db.get_task(conn, task_id).status == "triage"


def test_missing_evidence_is_capability_block_not_human_input():
    bridge = WorkstationKanbanBridge()
    prompt = "First extract records then verify each result"
    envelope = MessageEnvelope(
        MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, "evidence-session", prompt,
    )
    task_id = bridge.promote_request_if_multistep(
        prompt, session_id="evidence-session", envelope=envelope,
        acceptance_contract=AcceptanceContract(policy="evidence"),
    )
    result = bridge.finalize_turn_candidate(
        task_id, "evidence-session",
        {"completed": True, "final_response": "No independent readback."},
        observed_tools=[],
    )
    assert result["acceptance_approved"] is False
    with bridge.get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        assert task.status == "blocked" and task.block_kind == "capability"


def test_mutation_request_never_receives_advisory_contract():
    envelope = MessageEnvelope(
        MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, "s",
        "Primeiro investigue o sistema, depois corrija o arquivo e teste.",
    )
    assert work_intent(envelope).acceptance_policy.policy == "evidence"


def test_advisory_mutation_is_held_for_reconciliation_not_marked_done():
    agent = _agent()
    _, task_id = _prepare(agent)
    args = {"path": "no-file-will-be-written.txt", "content": "unsafe"}
    # Pre-dispatch creates an uncertainty checkpoint but DOES NOT execute I/O.
    workstation_pre_dispatch_hook(
        "write_file", args, "write-call-1", {"agent": agent, "dispatched": True},
    )
    assert agent._canonical_work_run_id is not None
    admission = _candidate(agent, task_id)
    assert admission.admitted is False
    with WorkstationKanbanBridge().get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        assert task.status == "blocked" and task.block_kind == "needs_input"


def test_previous_blocked_advisory_card_cannot_be_closed_by_new_turn():
    agent = _agent()
    _, task_id = _prepare(agent)
    bridge = WorkstationKanbanBridge()
    run_id = bridge.start_triaged_task(
        task_id, session_id=agent.session_id, objective=PROMPT,
    )
    with bridge.get_connection() as conn:
        assert kanban_db.block_task(
            conn, task_id, kind="capability", reason="readback unavailable",
            expected_run_id=int(run_id),
        )
    result = bridge.finalize_turn_candidate(
        task_id, agent.session_id,
        {"completed": True, "final_response": "Some content"},
        observed_tools=[{"effect": "PURE_READ", "status": "completed"}],
    )
    assert result["status"] == "not_running"
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, task_id).status == "blocked"


def test_advisory_running_task_rejects_wrong_run_identity():
    agent = _agent()
    _, task_id = _prepare(agent)
    bridge = WorkstationKanbanBridge()
    current = int(bridge.start_triaged_task(
        task_id, session_id=agent.session_id, objective=PROMPT,
    ))
    result = bridge.finalize_turn_candidate(
        task_id, agent.session_id,
        {"completed": True, "final_response": "Some content"},
        expected_run_id=current + 1,
        observed_tools=[{"effect": "PURE_READ", "status": "completed"}],
    )
    assert result["status"] == "run_unbound"
    with bridge.get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        assert task.status == "running" and task.current_run_id == current


def test_read_only_classifier_rejects_requested_card_mutation():
    envelope = MessageEnvelope(
        MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, "s",
        "Primeiro analise os dados, depois compare os cartões e marque como concluídos.",
    )
    assert work_intent(envelope).acceptance_policy.policy == "evidence"


@pytest.mark.parametrize("error_type", [TypeError, RuntimeError])
def test_postcommit_telemetry_failure_cannot_hide_canonical_done(monkeypatch, tmp_path, error_type):
    agent = _agent()
    _, task_id = _prepare(agent)
    source = tmp_path / "input.txt"
    source.write_text("only a read", encoding="utf-8")
    _observe_real_read(agent, source)

    def telemetry_crash(*args, **kwargs):
        raise error_type("optional telemetry failed after DONE commit")

    monkeypatch.setattr("workstation.telemetry.emit_event", telemetry_crash)
    admitted = _candidate(agent, task_id)
    # The canonical DONE transaction is already committed when learning fails.
    assert admitted.admitted is True
    with WorkstationKanbanBridge().get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        assert task.status == "done"
        assert kanban_db.latest_run(conn, task_id).outcome == "completed"

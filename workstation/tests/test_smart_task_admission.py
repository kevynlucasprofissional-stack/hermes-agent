"""P0: chat/action/task admission must not mint a TaskRun before execution."""
from types import SimpleNamespace

import pytest

from hermes_cli import kanban_db
from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.kanban import WorkstationKanbanBridge
from workstation.work_intent import prepare_turn_work, work_intent


def agent(session="task-admission"):
    return SimpleNamespace(session_id=session, _conversation_root_id=lambda: session,
                           valid_tool_names={"work_execute"})


def human(session, content, turn="turn-1"):
    return MessageEnvelope(MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK,
                           session, content, correlation_id=turn)


@pytest.mark.parametrize("content", [
    "Como funciona o browser do Hermes?",
    "Pesquise o que é Kanban.",
    "O que é uma pesquisa de mercado?",
    "Abra o Trello.",
    "Abra o Hyperframe.",
    "Me explique este site.",
])
def test_conversation_and_one_shot_actions_never_create_canonical_tasks(content):
    a = agent()
    intent = prepare_turn_work(a, content, human(a.session_id, content))
    assert not intent.requires_task
    assert getattr(a, "_canonical_work_task_id", None) is None
    with WorkstationKanbanBridge().get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0


def test_durable_request_is_triaged_without_run_and_reused_within_turn():
    a = agent()
    content = "Primeiro extraia os dados, depois gere um relatório e verifique os resultados"
    env = human(a.session_id, content)
    intent = prepare_turn_work(a, content, env)
    assert intent.requires_task
    task_id = a._canonical_work_task_id
    assert task_id
    assert a._canonical_work_run_id is None
    with WorkstationKanbanBridge().get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        assert task.status == "triage"
        assert task.current_run_id is None
        assert conn.execute("SELECT COUNT(*) FROM task_runs").fetchone()[0] == 0
    prepare_turn_work(a, content, env)
    assert a._canonical_work_task_id == task_id
    with WorkstationKanbanBridge().get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1


def test_new_conversational_turn_clears_previous_task_and_run_not_chat():
    a = agent()
    text = "First extract reports then verify each result"
    prepare_turn_work(a, text, human(a.session_id, text))
    task_id = a._canonical_work_task_id
    a._canonical_work_run_id = "stale-run"
    new = human(a.session_id, "Como funciona uma TaskRun?", "turn-next")
    assert not prepare_turn_work(a, new.content, new).requires_task
    assert a._canonical_work_task_id is None
    assert a._canonical_work_run_id is None
    with WorkstationKanbanBridge().get_connection() as conn:
        assert kanban_db.get_task(conn, task_id).status == "triage"


def test_blocked_previous_task_does_not_regain_authority_or_duplicate():
    a = agent()
    text = "First extract reports then verify each result"
    envelope = human(a.session_id, text)
    prepare_turn_work(a, text, envelope)
    old = a._canonical_work_task_id
    with WorkstationKanbanBridge().get_connection() as conn:
        # A triage task is not yet executing; flag it blocked explicitly.
        conn.execute("UPDATE tasks SET status = 'blocked' WHERE id = ?", (old,))
        conn.commit()
    prepare_turn_work(a, text, envelope)
    assert a._canonical_work_task_id is None
    assert a._canonical_work_run_id is None
    assert a._work_blocked_task_id == old
    with WorkstationKanbanBridge().get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1


def test_browser_navigation_claims_existing_triaged_task_before_native_owner():
    from workstation.batch_detection import prepare_mutation

    a = agent("qa-browser-navigation-canonical")
    request = "Primeiro abra a pagina QA, depois digite um titulo, salve e confira o resultado"
    prepare_turn_work(a, request, human(a.session_id, request))
    task_id = a._canonical_work_task_id
    assert a._canonical_work_run_id is None
    prepare_mutation(a, "browser_navigate", {"url": "http://127.0.0.1:12345/"})
    with WorkstationKanbanBridge().get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        assert task.status == "running"
        assert str(task.current_run_id) == str(a._canonical_work_run_id)
        assert conn.execute(
            "SELECT COUNT(*) FROM task_runs WHERE task_id=?", (task_id,),
        ).fetchone()[0] == 1


def test_first_real_mutation_claims_triaged_run_only_once():
    from workstation.batch_detection import prepare_mutation
    a = agent()
    text = "First generate a report then verify its contents"
    prepare_turn_work(a, text, human(a.session_id, text))
    task_id = a._canonical_work_task_id
    assert a._canonical_work_run_id is None
    args = {"path": "output.txt", "content": "ok"}
    prepare_mutation(a, "write_file", args)
    with WorkstationKanbanBridge().get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        assert task.status == "running"
        assert task.current_run_id is not None
        assert str(task.current_run_id) == str(a._canonical_work_run_id)
        assert conn.execute("SELECT COUNT(*) FROM task_runs WHERE task_id = ?", (task_id,)).fetchone()[0] == 1


def test_untrusted_ingress_cannot_create_task_from_multistep_prose():
    a = agent()
    text = "First extract reports then verify each result"
    env = MessageEnvelope(MessageOrigin.RUNTIME, IntentAuthority.OBSERVATION_ONLY, a.session_id, text)
    assert not prepare_turn_work(a, text, env).requires_task
    assert getattr(a, "_canonical_work_task_id", None) is None


def test_unstarted_triage_task_never_blocks_or_completes_on_turn_end():
    from workstation.integrations.hermes.completion_admission import workstation_completion_admission
    a = agent()
    content = "First gather three reports then compare and verify them"
    prepare_turn_work(a, content, human(a.session_id, content))
    task_id = a._canonical_work_task_id
    result = WorkstationKanbanBridge().finalize_turn_candidate(
        task_id, a.session_id, {"completed": True, "final_response": "I will analyze the reports"})
    assert result["status"] == "queued_unstarted"
    assert not result["acceptance_approved"]
    admission = workstation_completion_admission(
        task_id, "", {"session_id": a.session_id,
                      "turn_result": {"completed": True, "final_response": "queued"}})
    assert not admission.admitted
    assert admission.reason == "outcome_queued_unstarted"
    with WorkstationKanbanBridge().get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        assert task.status == "triage" and task.current_run_id is None


def test_session_restart_deduplicates_unfinished_work_across_turn_ids():
    text = "First extract invoices then verify and export results"
    first = agent()
    prepare_turn_work(first, text, human(first.session_id, text, "turn-A"))
    task_id = first._canonical_work_task_id
    restarted = agent()
    prepare_turn_work(restarted, text, human(restarted.session_id, text, "turn-B"))
    assert restarted._canonical_work_task_id == task_id
    assert restarted._canonical_work_run_id is None
    with WorkstationKanbanBridge().get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
    with WorkstationKanbanBridge().get_connection() as conn:
        conn.execute("UPDATE tasks SET status='blocked' WHERE id=?", (task_id,))
        conn.commit()
    third = agent()
    prepare_turn_work(third, text, human(third.session_id, text, "turn-C"))
    assert third._canonical_work_task_id is None
    assert third._canonical_work_run_id is None
    assert third._work_blocked_task_id == task_id
    with WorkstationKanbanBridge().get_connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1


def test_active_run_survives_only_same_trusted_turn_and_not_new_correlation():
    from workstation.batch_detection import prepare_mutation
    a = agent()
    content = "First gather reports then verify and save results"
    first = human(a.session_id, content, "turn-original")
    prepare_turn_work(a, content, first)
    task_id = a._canonical_work_task_id
    prepare_mutation(a, "write_file", {"path": "receipt.txt", "content": "value"})
    run_id = a._canonical_work_run_id
    assert run_id is not None
    prepare_turn_work(a, content, first)
    assert str(a._canonical_work_run_id) == str(run_id)
    next_turn = human(a.session_id, content, "turn-next")
    prepare_turn_work(a, content, next_turn)
    assert a._canonical_work_task_id is None
    assert a._canonical_work_run_id is None
    assert a._work_blocked_task_id == task_id


def test_compiler_without_executable_steps_does_not_claim_triage_task():
    from workstation.task_compiler import TaskCompiler
    a = agent()
    content = "First gather reports then verify and save results"
    prepare_turn_work(a, content, human(a.session_id, content))
    task_id = a._canonical_work_task_id
    compiler = TaskCompiler()
    try:
        with pytest.raises((ValueError, KeyError, TypeError)):
            compiler.execute({"operation_key": "invalid-empty"},
                             task_id=task_id, canonical_task_id=task_id,
                             session_id=a.session_id, dispatch=lambda *_: None)
    finally:
        compiler.store.close()
    with WorkstationKanbanBridge().get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        assert task.status == "triage" and task.current_run_id is None

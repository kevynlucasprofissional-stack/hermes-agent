"""Single-message WhatsApp TaskRun admission: real canonical lease, no manual Kanban."""

from types import SimpleNamespace

import pytest

from hermes_cli import kanban_db
from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.kanban import WorkstationKanbanBridge
from workstation.task_compiler import current_work_execution_identity
from workstation.integrations.hermes.whatsapp_point_admission import admitted_whatsapp_point_send


ARGS = {
    "recipient_ref": {"source": "hermes_local", "contact_id": 1},
    "expected_recipient_name": "Self",
    "message": "Only once",
}


def _agent(*, origin=MessageOrigin.HUMAN, authority=IntentAuthority.CREATE_WORK,
           turn="turn-a", session="session-a", prompt="Send this WhatsApp message"):
    agent = SimpleNamespace(
        session_id=session, _conversation_root_id=lambda: session,
        _message_envelope=MessageEnvelope(origin, authority, session, prompt,
                                          correlation_id=turn),
        _canonical_work_task_id=None, _canonical_work_run_id=None,
    )
    return agent


def test_name_only_send_must_match_literal_authenticated_request():
    agent = _agent(prompt="Abre o WhatsApp e manda oi para Kevyn ACIRV")
    args = {"target_name": "Kevyn ACIRV", "message": "oi"}
    with admitted_whatsapp_point_send(agent, args, "named-call"):
        identity = current_work_execution_identity()
        assert identity and identity["run_id"]
    assert current_work_execution_identity() is None


def test_model_cannot_switch_named_target_not_in_original_turn():
    agent = _agent(prompt="Abre o WhatsApp e manda oi para Kevyn ACIRV")
    with pytest.raises(PermissionError, match="WHATSAPP_REQUESTED_TARGET_MISMATCH"):
        with admitted_whatsapp_point_send(
            agent, {"target_name": "Você", "message": "oi"}, "wrong-target-call"
        ):
            pytest.fail("should reject")
    with WorkstationKanbanBridge().get_connection() as db:
        assert db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0


def test_autoclaims_real_run_at_selected_single_send_only():
    agent = _agent()
    assert current_work_execution_identity() is None
    with admitted_whatsapp_point_send(agent, ARGS, "model-call-1"):
        identity = current_work_execution_identity()
        assert identity is not None
        assert identity["session_id"] == agent.session_id
        assert identity["kanban_card_id"] == agent._canonical_work_task_id
        assert identity["run_id"] == agent._canonical_work_run_id
        with WorkstationKanbanBridge().get_connection() as db:
            task = kanban_db.get_task(db, identity["kanban_card_id"])
            assert task.status == "running"
            assert str(task.current_run_id) == identity["run_id"]
            assert task.body == agent._message_envelope.content
            assert db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
    assert current_work_execution_identity() is None
    # A second tool call in the same user turn never claims a second run or sends.
    with pytest.raises(PermissionError, match="WHATSAPP_POINT_ALREADY_DISPATCHED"):
        with admitted_whatsapp_point_send(agent, ARGS, "model-call-2"):
            pytest.fail("duplicate dispatched")
    with WorkstationKanbanBridge().get_connection() as db:
        assert db.execute("SELECT COUNT(*) FROM task_runs").fetchone()[0] == 1


@pytest.mark.parametrize("origin,authority,turn", [
    (MessageOrigin.RUNTIME, IntentAuthority.OBSERVATION_ONLY, "turn-a"),
    (MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, ""),
])
def test_untrusted_or_unidentified_turn_never_creates_task(origin, authority, turn):
    agent = _agent(origin=origin, authority=authority, turn=turn)
    with pytest.raises(PermissionError):
        with admitted_whatsapp_point_send(agent, ARGS, "model-call"):
            pass
    with WorkstationKanbanBridge().get_connection() as db:
        assert db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0


def test_missing_recipient_or_message_never_creates_task():
    agent = _agent()
    with pytest.raises(ValueError):
        with admitted_whatsapp_point_send(agent, {**ARGS, "message": ""}, "model-call"):
            pass
    with WorkstationKanbanBridge().get_connection() as db:
        assert db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0


def test_same_turn_cannot_reopen_blocked_task():
    agent = _agent()
    with admitted_whatsapp_point_send(agent, ARGS, "model-call-1"):
        task_id = agent._canonical_work_task_id
    with WorkstationKanbanBridge().get_connection() as db:
        db.execute("UPDATE tasks SET status='blocked' WHERE id=?", (task_id,))
        db.commit()
    second_agent = _agent()
    with pytest.raises(PermissionError):
        with admitted_whatsapp_point_send(second_agent, ARGS, "model-call-2"):
            pass
    with WorkstationKanbanBridge().get_connection() as db:
        assert db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1


def test_dispatcher_exposes_real_taskrun_to_registered_model_tool(monkeypatch):
    import json
    from unittest.mock import Mock
    import agent.tool_executor as dispatcher
    import agent.terminal_approval_batch as terminal_batch
    import agent.pre_dispatch as hooks
    import tools.browser_tool
    import tools.browser_workstation as wrapper
    from tools.registry import registry

    agent = _agent()
    agent._tool_guardrails = SimpleNamespace(
        before_call=lambda name, args: SimpleNamespace(allows_execution=True))
    monkeypatch.setattr(dispatcher, "_pre_tool_block",
                        lambda agent, ref: (None, ref.args))
    monkeypatch.setattr(dispatcher, "_context_pruned_argument_paths",
                        lambda name, args: [])
    monkeypatch.setattr(dispatcher, "_begin_tool_execution",
                        lambda *args: None)
    monkeypatch.setattr(dispatcher, "_run_with_activity_heartbeat",
                        lambda _agent, _name, execute: execute())
    monkeypatch.setattr(terminal_batch, "prepare_current_terminal", lambda ref: None)
    observed = []
    monkeypatch.setattr(hooks, "dispatch_pre_authorized_checkpoint",
                        lambda *a: observed.append(current_work_execution_identity()))
    sender = Mock(return_value={"sent": False, "state": "OBSERVED"})
    monkeypatch.setattr(wrapper, "whatsapp_send_message", sender)
    ref = dispatcher._ToolCallRef("whatsapp_send_message", dict(ARGS),
                                  "unrelated-route-id", "call-1", [])
    state = dispatcher._ManagedToolResult(None, dict(ARGS), [], False, True)
    result = dispatcher._dispatch_authorized_once(
        agent, state, ref,
        execute=lambda args: registry.dispatch("whatsapp_send_message", args,
                                               session_id=agent.session_id,
                                               tool_call_id="call-1"),
        scope_block=None, display_index=None, begin_execution=None,
        authorization_gate=None,
    )
    assert json.loads(result)["state"] == "OBSERVED"
    assert observed and observed[0]["kanban_card_id"] == agent._canonical_work_task_id
    sender.assert_called_once()
    assert sender.call_args.kwargs["run_id"] == agent._canonical_work_run_id
    assert sender.call_args.kwargs["operation_id"] == "call-1"
    assert current_work_execution_identity() is None
    with WorkstationKanbanBridge().get_connection() as db:
        assert db.execute("SELECT COUNT(*) FROM task_runs").fetchone()[0] == 1


def test_new_user_turn_can_send_again_without_reusing_old_run():
    agent = _agent()
    with admitted_whatsapp_point_send(agent, ARGS, "call-1"):
        previous = current_work_execution_identity()
    # Existing turn admission clears the completed per-turn context.
    agent._message_envelope = MessageEnvelope(
        MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK,
        agent.session_id, "Please send a second WhatsApp message",
        correlation_id="turn-b",
    )
    agent._canonical_work_task_id = None
    agent._canonical_work_run_id = None
    with admitted_whatsapp_point_send(agent, ARGS, "call-2"):
        new = current_work_execution_identity()
        assert new["kanban_card_id"] != previous["kanban_card_id"]
        assert new["run_id"] != previous["run_id"]


def test_real_runtime_turn_id_is_used_when_ingress_has_no_correlation_id():
    agent = _agent(turn="")
    # Hermes builds this server-owned ID after initial turn admission.
    agent._current_turn_id = "runtime-generated-current-turn"
    with admitted_whatsapp_point_send(agent, ARGS, "call-1"):
        identity = current_work_execution_identity()
        assert identity is not None
        assert identity["run_id"] == agent._canonical_work_run_id
    with WorkstationKanbanBridge().get_connection() as db:
        assert db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1


def test_model_schema_explains_automatic_canonical_taskrun():
    import tools.browser_tool
    from tools.registry import registry
    schema = registry.get_schema("whatsapp_send_message")
    description = schema["description"].casefold()
    assert "host automatically claims a canonical taskrun" in description
    assert "no manual kanban card or second approval" in description
    assert "session-only" not in description


def test_compressed_session_uses_live_browser_session_and_root_owned_taskrun():
    agent = _agent(session="child-session")
    agent._conversation_root_id = lambda: "root-session"
    agent._message_envelope = MessageEnvelope(
        MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK,
        "root-session", "Send in compressed conversation", correlation_id="turn-root",
    )
    with admitted_whatsapp_point_send(agent, ARGS, "call-1"):
        identity = current_work_execution_identity()
        assert identity["session_id"] == "child-session"
        with WorkstationKanbanBridge().get_connection() as db:
            task = kanban_db.get_task(db, identity["kanban_card_id"])
            assert task.session_id == "root-session"
            assert str(task.current_run_id) == identity["run_id"]


def test_durable_turn_auto_triaged_before_runtime_turn_id_reuses_own_taskrun():
    from workstation.work_intent import prepare_turn_work
    prompt = "Primeiro localize o contato; depois envie uma mensagem WhatsApp e verifique o recibo."
    agent = _agent(turn="", prompt=prompt)
    initial = prepare_turn_work(agent, prompt, agent._message_envelope)
    assert initial.requires_task
    existing = agent._canonical_work_task_id
    assert existing
    assert agent._canonical_work_run_id is None
    assert not agent._canonical_work_turn_id
    # The live desktop turn identity is established *after* turn admission.
    agent._current_turn_id = "runtime-owned-turn-123"
    with admitted_whatsapp_point_send(agent, ARGS, "tool-call-durable"):
        ident = current_work_execution_identity()
        assert ident["kanban_card_id"] == existing
        assert ident["run_id"]
    with WorkstationKanbanBridge().get_connection() as db:
        assert db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM task_runs").fetchone()[0] == 1


def test_batch_claims_one_canonical_run_for_exact_user_manifest():
    from workstation.integrations.hermes.whatsapp_point_admission import (
        admitted_whatsapp_batch_send,
    )
    message1 = "Batch synthetic message one"
    message2 = "Batch synthetic message two"
    prompt = ("Envie ao Kevyn ACIRV: " + message1
              + ". E no autochat: " + message2)
    agent = _agent(prompt=prompt)
    args = {"items": [
        {"target_name": "Kevyn ACIRV", "message": message1},
        {"recipient_ref": {"source": "hermes_local", "contact_id": 1},
         "expected_recipient_name": "+55 64 9247-0988 (Você)",
         "message": message2},
    ]}
    with admitted_whatsapp_batch_send(agent, args, "batch-call"):
        identity = current_work_execution_identity()
        assert identity is not None and identity["run_id"]
        with WorkstationKanbanBridge().get_connection() as db:
            task = kanban_db.get_task(db, identity["kanban_card_id"])
            assert task.title == "WhatsApp lote"
            assert db.execute("SELECT COUNT(*) FROM task_runs").fetchone()[0] == 1


def test_batch_rejects_unmentioned_recipient_or_message_before_creating_task():
    from workstation.integrations.hermes.whatsapp_point_admission import (
        admitted_whatsapp_batch_send,
    )
    agent = _agent(prompt="Enviar para Kevyn ACIRV: Olá autorizado")
    args = {"items": [
        {"target_name": "Kevyn ACIRV", "message": "Olá autorizado"},
        {"target_name": "Outro Contato", "message": "Texto inventado"},
    ]}
    with pytest.raises(PermissionError):
        with admitted_whatsapp_batch_send(agent, args, "batch-call"):
            pytest.fail("untrusted batch should fail")
    with WorkstationKanbanBridge().get_connection() as db:
        assert db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 0

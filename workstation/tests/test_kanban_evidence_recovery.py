"""Read-only child recovers original external mutation without replay."""
from __future__ import annotations

from types import SimpleNamespace
import json

import pytest
from hermes_cli import kanban_db
from workstation.integrations.hermes.tool_observer import (
    workstation_pre_dispatch_hook, workstation_raw_post_tool_observer,
)
from workstation.tests.test_kanban_direct_file_readback import _bound_run, _admit
from workstation.tests.test_kanban_external_readback import CARD, _trello_fixture


def _queue_recovery(monkeypatch, *, result_override=None, intent_override=None):
    state = _trello_fixture(monkeypatch)
    import workstation.trello_sync_api as api
    if intent_override is not None:
        monkeypatch.setattr(api, "get_intent", lambda *_: dict(intent_override))
    original_remote = api._remote
    state["unavailable"] = True

    def maybe_remote(*a):
        if state["unavailable"]:
            raise RuntimeError("temporary authorized GET unavailable")
        return original_remote(*a)

    monkeypatch.setattr(api, "_remote", maybe_remote)
    bridge, agent, parent_id, original_run = _bound_run()
    args = {"card_id": CARD, "review_run_id": "qa-review-1", "expected_revision": 2}
    ctx = {"agent": agent, "dispatched": True}
    workstation_pre_dispatch_hook("workstation_db_trello_api_push", args, "api-call-1", ctx)
    workstation_raw_post_tool_observer(
        "workstation_db_trello_api_push", args, "api-call-1",
        result_override if result_override is not None
        else {"ok": True, "status": "verified", "intent_id": "intent-1"},
        0.01, ctx,
    )
    assert "external_readback" not in agent._work_tool_observations[0]
    result = _admit(agent, parent_id, original_run)
    assert result.admitted is False
    assert result.receipt["status"] == "recovery_queued", result.receipt
    child_id = result.receipt["recovery_task_id"]
    with bridge.get_connection() as conn:
        parent = kanban_db.get_task(conn, parent_id)
        child = kanban_db.get_task(conn, child_id)
        assert parent.status == "todo" and child.status == "ready"
        assert conn.execute("SELECT 1 FROM task_links WHERE parent_id=? AND child_id=?",
                            (child_id, parent_id)).fetchone()
    return bridge, agent, parent_id, original_run, child_id, state


def _complete_child_by_actual_read(bridge, agent, child_id, tmp_path):
    input_file = tmp_path / "readonly.txt"
    input_file.write_text("legitimate original operation evidence investigation", encoding="utf-8")
    child_agent = SimpleNamespace(
        session_id=agent.session_id,
        _conversation_root_id=lambda: agent.session_id,
        _canonical_work_task_id=child_id,
        _canonical_work_run_id=None,
        _work_tool_observations=[],
        _work_mutation_evidence={}, _work_mutation_shapes={},
        _work_completed_mutations={}, _work_capabilities={},
        valid_tool_names=set(),
    )
    args = {"path": str(input_file)}
    ctx = {"agent": child_agent, "dispatched": True}
    workstation_pre_dispatch_hook("read_file", args, "read-child", ctx)
    workstation_raw_post_tool_observer("read_file", args, "read-child",
                                       {"content": input_file.read_text(encoding="utf-8")},
                                       0.01, ctx)
    return bridge.finalize_turn_candidate(
        child_id, agent.session_id,
        {"completed": True, "failed": False, "interrupted": False,
         "final_response": "Consultei a fonte sem realizar nova mutação."},
        observed_tools=child_agent._work_tool_observations,
    )


def test_recovery_child_finishes_parent_from_fresh_trello_get(monkeypatch, tmp_path):
    bridge, agent, parent_id, previous, child_id, state = _queue_recovery(monkeypatch)
    child_agent = SimpleNamespace(_canonical_work_task_id=child_id,
                                  _work_tool_observations=[],
                                  valid_tool_names=set())
    with pytest.raises(PermissionError, match="read_only"):
        workstation_pre_dispatch_hook(
            "write_file", {"path": str(tmp_path / "forbidden"), "content": "bad"},
            "mutation-denied", {"agent": child_agent, "dispatched": True},
        )
    assert not (tmp_path / "forbidden").exists()
    state["unavailable"] = False
    outcome = _complete_child_by_actual_read(bridge, agent, child_id, tmp_path)
    assert outcome["acceptance_approved"] is True, outcome
    with bridge.get_connection() as conn:
        parent = kanban_db.get_task(conn, parent_id)
        child = kanban_db.get_task(conn, child_id)
        assert child.status == "done" and parent.status == "done"
        run = kanban_db.latest_run(conn, parent_id)
        assert int(run.id) != int(previous)
        ws = run.metadata["workstation"]
        assert ws["acceptance_approved"] is True
        assert ws["outcome"]["verifier_results"][0]["verifier"] == "recovered_workstation_db_trello_api_push"
        status = conn.execute(
            "SELECT status FROM workstation_evidence_recovery WHERE parent_task_id=?",
            (parent_id,),
        ).fetchone()[0]
        assert status == "completed"
    assert state["gets"] >= 1  # Owner GET; never second PUT.


def test_unavailable_source_after_child_proof_fails_closed(monkeypatch, tmp_path):
    bridge, agent, parent_id, previous, child_id, state = _queue_recovery(monkeypatch)
    assert state["unavailable"]
    outcome = _complete_child_by_actual_read(bridge, agent, child_id, tmp_path)
    assert outcome["acceptance_approved"] is True
    with bridge.get_connection() as conn:
        parent = kanban_db.get_task(conn, parent_id)
        assert parent.status != "done"
        row = conn.execute(
            "SELECT status FROM workstation_evidence_recovery WHERE parent_task_id=?",
            (parent_id,),
        ).fetchone()
        assert row and row[0] == "needs_verifier"
    # Nothing can accidentally re-dispatch the original mutation.
    with pytest.raises(PermissionError, match="read_only"):
        workstation_pre_dispatch_hook(
            "workstation_db_trello_api_push",
            {"card_id": CARD, "review_run_id": "qa-review-1", "expected_revision": 2},
            "replay-blocked",
            {"agent": SimpleNamespace(_canonical_work_task_id=parent_id,
                                      _work_tool_observations=[], valid_tool_names=set()),
             "dispatched": True},
        )


def test_resumed_parent_can_reprobe_after_authorized_unblock(monkeypatch, tmp_path):
    bridge, agent, parent_id, original, child_id, state = _queue_recovery(monkeypatch)
    _complete_child_by_actual_read(bridge, agent, child_id, tmp_path)
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, parent_id).status == "blocked"
        # Controlled operator recovery in the isolated test DB; no replay.
        assert kanban_db.unblock_task(conn, parent_id)
        claimed = kanban_db.claim_task(conn, parent_id, claimer="qa-readback-only")
        assert claimed and claimed.current_run_id
        resumed_run = str(claimed.current_run_id)
    state["unavailable"] = False
    from workstation.integrations.hermes.completion_admission import workstation_completion_admission
    receipt = workstation_completion_admission(
        parent_id, resumed_run, {
            "session_id": agent.session_id,
            "turn_result": {"completed": True, "failed": False, "interrupted": False,
                            "final_response": "Reconciliacao da fonte recuperada"},
        },
    )
    assert receipt.admitted is True, receipt.reason
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, parent_id).status == "done"
        assert conn.execute(
            "SELECT status FROM workstation_evidence_recovery WHERE parent_task_id=?",
            (parent_id,),
        ).fetchone()[0] == "completed"


def test_unrelated_failed_read_prevents_auto_recovery_child():
    from workstation.evidence_recovery import schedule_recovery
    bridge, agent, parent_id, run_id = _bound_run()
    observed = [
        {"call_id": "mutation", "tool": "workstation_db_trello_api_push",
         "effect": "MUTATION", "status": "completed",
         "recovery_descriptor": {"tool": "workstation_db_trello_api_push",
                                 "card_id": CARD, "review_run_id": "qa-review-1"}},
        {"call_id": "failed-read", "tool": "read_file",
         "effect": "PURE_READ", "status": "failed"},
    ]
    assert schedule_recovery(
        task_id=parent_id, session_id=agent.session_id, run_id=int(run_id),
        observed_tools=observed, pending=["Source read failed"]) is None
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, parent_id).status == "running"


def test_unknown_interactive_effect_prevents_borrowing_recovery_evidence():
    from workstation.evidence_recovery import schedule_recovery
    bridge, agent, parent_id, run_id = _bound_run()
    observed = [
        {"call_id": "mutation", "tool": "whatsapp_send_message",
         "effect": "MUTATION", "status": "unknown",
         "recovery_descriptor": {"tool": "whatsapp_send_message",
                                 "operation_id": "send-1"}},
        {"call_id": "click", "tool": "browser_click",
         "effect": "INTERACTIVE", "status": "completed"},
    ]
    assert schedule_recovery(
        task_id=parent_id, session_id=agent.session_id, run_id=int(run_id),
        observed_tools=observed, pending=["Unverified browser effect"]) is None


def _uncertain_trello_intent(reason="api_put_result_unknown"):
    return {
        "intent_id": "intent-1", "operation_id": "trello-qa-api-title-1234",
        "state": "uncertain", "target_title": "New title",
        "remote_before": "Old title", "failure_reason": reason,
    }


def test_lost_trello_put_ack_reconciles_by_get_without_reissuing_put(monkeypatch, tmp_path):
    # Owner reported UNCERTAIN after attempting PUT, not a successful tool ACK.
    bridge, agent, parent_id, previous, child_id, state = _queue_recovery(
        monkeypatch, intent_override=_uncertain_trello_intent(),
        result_override={"ok": False, "status": "uncertain", "intent_id": "intent-1",
                         "reason": "api_put_result_unknown"},
    )
    state["unavailable"] = False
    result = _complete_child_by_actual_read(bridge, agent, child_id, tmp_path)
    assert result["acceptance_approved"] is True
    with bridge.get_connection() as conn:
        parent = kanban_db.get_task(conn, parent_id)
        assert parent.status == "done"
        ws = kanban_db.latest_run(conn, parent_id).metadata["workstation"]
        assert ws["acceptance_approved"] is True
        assert ws["outcome"]["verifier_results"][0]["source_kind"] == "authenticated_remote_get"
    assert state["gets"] == 1  # Only GET; original PUT was never redispatched.


def test_trello_predispatch_uncertainty_must_not_promote_to_done(monkeypatch, tmp_path):
    # An intent invalidated before PUT is not evidence that Hermes executed it.
    bridge, agent, parent_id, previous, child_id, state = _queue_recovery(
        monkeypatch, intent_override=_uncertain_trello_intent("local_changed_after_intent"),
        result_override={"ok": False, "status": "uncertain", "intent_id": "intent-1",
                         "reason": "local_changed_after_intent"},
    )
    state["unavailable"] = False
    _complete_child_by_actual_read(bridge, agent, child_id, tmp_path)
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, parent_id).status != "done"
        assert conn.execute(
            "SELECT status FROM workstation_evidence_recovery WHERE parent_task_id=?",
            (parent_id,),
        ).fetchone()[0] == "needs_verifier"

@pytest.mark.parametrize("failure_phase", ["PRE_SEND", "RESOLVE_RECIPIENT"])
def test_whatsapp_pre_send_failure_does_not_open_recovery_child(failure_phase):
    """A definite pre-send rejection has no remote effect to investigate."""
    from workstation.evidence_recovery import schedule_recovery
    bridge, agent, parent_id, run_id = _bound_run()
    agent._work_tool_observations = [{
        "call_id": "qa-p4-no-effect",
        "tool": "whatsapp_send_message",
        "effect": "MUTATION",
        "status": "started",
        "recovery_descriptor": {
            "tool": "whatsapp_send_message",
            "operation_id": "qa-p4-no-effect",
        },
    }]
    workstation_raw_post_tool_observer(
        "whatsapp_send_message",
        {"recipient_ref": {"source": "hermes_local", "contact_id": 1}},
        "qa-p4-no-effect",
        {"sent": False, "state": "FAILED",
         "error_code": "RECIPIENT_NAME_MISMATCH",
         "failure_phase": failure_phase},
        0.01, {"agent": agent, "dispatched": True},
    )
    row = agent._work_tool_observations[0]
    assert row["status"] == "failed"
    assert row.get("no_effect") is True
    assert schedule_recovery(
        task_id=parent_id, session_id=agent.session_id,
        run_id=int(run_id), observed_tools=[row],
        pending=["Pre-send mismatch"],
    ) is None
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, parent_id).status == "running"
        assert conn.execute(
            "SELECT COUNT(*) FROM task_links WHERE parent_id=?", (parent_id,)
        ).fetchone()[0] == 0

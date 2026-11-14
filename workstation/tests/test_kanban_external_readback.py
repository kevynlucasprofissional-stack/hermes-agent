"""Independent Trello/WhatsApp proofs enter the canonical Workstation Kanban gate.

The mock Trello transport is an isolated owner GET fixture, not a production
Trello mutation. WhatsApp uses a real local SQLite causal-receipt record.
"""
import hashlib
import json
import sqlite3
from types import SimpleNamespace

from hermes_cli import kanban_db
from workstation.integrations.hermes.tool_observer import (
    workstation_pre_dispatch_hook, workstation_raw_post_tool_observer,
)
from workstation.tests.test_kanban_direct_file_readback import _bound_run, _admit


CARD = "a" * 24
QA_BOARD = "6aefcc8e38ac0595e0035341"
LINK = "https://trello.com/c/ABCDEFGH/qa"
OP = "trello-qa-api-title-1234"


def _trello_fixture(monkeypatch):
    state = {"remote": "New title", "gets": 0}
    intent = {
        "state": "verified", "intent_id": "intent-1",
        "operation_id": OP, "target_title": "New title",
        "readback_json": json.dumps({
            "id": CARD, "name": "New title", "shortUrl": LINK,
        }),
    }
    import workstation.trello_sync_api as api
    import workstation.prefabs.trello as trello
    monkeypatch.setattr(api, "get_intent", lambda *_: dict(intent))
    def remote(*_):
        state["gets"] += 1
        return {"id": CARD, "name": state["remote"], "idBoard": QA_BOARD,
                "closed": False, "shortUrl": LINK}
    monkeypatch.setattr(api, "_remote", remote)
    monkeypatch.setattr(trello.Credential, "from_secret_scope",
                        lambda: object())
    monkeypatch.setattr(trello, "TrelloClient",
                        lambda **kw: SimpleNamespace())
    return state


def _observe(agent, tool, args, result, *, call_id=None):
    ctx = {"agent": agent, "dispatched": True}
    identity = call_id or args.get("operation_id") or tool + "-call"
    workstation_pre_dispatch_hook(tool, args, identity, ctx)
    workstation_raw_post_tool_observer(
        tool, args, identity, result, 0.01, ctx,
    )
    return agent._work_tool_observations[-1]


def test_trello_verified_qa_push_owner_get_reaches_canonical_done(monkeypatch):
    state = _trello_fixture(monkeypatch)
    bridge, agent, task_id, run_id = _bound_run()
    args = {"card_id": CARD, "review_run_id": "qa-review-1",
            "expected_revision": 2}
    row = _observe(agent, "workstation_db_trello_api_push", args,
                   {"ok": True, "status": "verified", "intent_id": "intent-1"})
    assert row.get("external_readback") and state["gets"] == 1
    receipt = _admit(agent, task_id, run_id)
    assert receipt.admitted is True, receipt.reason
    assert state["gets"] == 2
    with bridge.get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        run = kanban_db.latest_run(conn, task_id)
        assert task.status == "done"
        assert run.metadata["workstation"]["outcome"]["verifier_results"][0]["verifier"] == "external_trello_readback"


def test_trello_remote_drift_does_not_rewrite_and_stays_not_done(monkeypatch):
    state = _trello_fixture(monkeypatch)
    bridge, agent, task_id, run_id = _bound_run()
    args = {"card_id": CARD, "review_run_id": "qa-review-1",
            "expected_revision": 2}
    row = _observe(agent, "workstation_db_trello_api_push", args,
                   {"ok": True, "status": "verified", "intent_id": "intent-1"})
    assert row.get("external_readback")
    state["remote"] = "Somebody else changed title"
    assert _admit(agent, task_id, run_id).admitted is False
    assert state["gets"] == 2
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, task_id).status != "done"


def _whatsapp_db(path, task_id, session, run, operation, message):
    digest = hashlib.sha256(message.encode("utf-8")).hexdigest()
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE whatsapp_send_logs("
                     "task_id TEXT,session_id TEXT,run_id TEXT,operation_id TEXT,"
                     "message_digest TEXT,state TEXT,sent INTEGER,"
                     "message_data_id TEXT,ack_label TEXT,composer_empty_after INTEGER)")
        conn.execute(
            "INSERT INTO whatsapp_send_logs VALUES(?,?,?,?,?,?,?,?,?,?)",
            (task_id, session, run, operation, digest, "CONFIRMED", 1,
             "sha256:" + "c" * 64, "sent", 1),
        )


def test_persisted_causal_whatsapp_receipt_reaches_done_without_resending(tmp_path, monkeypatch):
    bridge, agent, task_id, run_id = _bound_run()
    path = tmp_path / "control.db"
    op = "send-stable-op-1"
    msg = "Confirmacao do evento"
    _whatsapp_db(path, task_id, agent.session_id, run_id, op, msg)
    import workstation.integrations.hermes.whatsapp_browser_executor as wa
    monkeypatch.setattr(wa, "get_default_db_path", lambda: path)
    args = {"task_id": task_id, "kanban_card_id": task_id,
            "session_id": agent.session_id, "run_id": run_id,
            "operation_id": op, "message": msg, "verify_delivery": True}
    output = {"state": "CONFIRMED", "sent": True,
              "message_data_id": "sha256:" + "c" * 64, "ack_label": "sent"}
    row = _observe(agent, "whatsapp_send_message", args, output)
    assert row.get("external_readback")
    assert _admit(agent, task_id, run_id).admitted is True
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, task_id).status == "done"


def test_whatsapp_fake_ack_or_wrong_run_is_not_completion(tmp_path, monkeypatch):
    bridge, agent, task_id, run_id = _bound_run()
    path = tmp_path / "control.db"
    op, msg = "send-op-2", "No resend"
    _whatsapp_db(path, task_id, agent.session_id, run_id, op, msg)
    import workstation.integrations.hermes.whatsapp_browser_executor as wa
    monkeypatch.setattr(wa, "get_default_db_path", lambda: path)
    args = {"task_id": task_id, "kanban_card_id": task_id,
            "session_id": agent.session_id, "run_id": run_id,
            "operation_id": op, "message": msg}
    row = _observe(agent, "whatsapp_send_message", args,
                   {"state": "CONFIRMED", "sent": True,
                    "message_data_id": "sha256:" + "d" * 64, "ack_label": "sent"})
    assert not row.get("external_readback")
    assert _admit(agent, task_id, run_id).admitted is False
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, task_id).status != "done"


def test_unknown_external_tool_not_certified_by_other_receipt(monkeypatch):
    _trello_fixture(monkeypatch)
    _, agent, task_id, run_id = _bound_run()
    args = {"card_id": CARD, "review_run_id": "qa-review-1", "expected_revision": 2}
    _observe(agent, "workstation_db_trello_api_push", args,
             {"ok": True, "status": "verified", "intent_id": "intent-1"})
    _observe(agent, "github_create_issue", {"title": "unknown"}, {"ok": True})
    assert _admit(agent, task_id, run_id).admitted is False


def test_model_facing_whatsapp_schema_uses_host_call_id_for_receipt(tmp_path, monkeypatch):
    bridge, agent, task_id, run_id = _bound_run()
    path = tmp_path / "control.db"
    op = "real-tool-call-id"
    msg = "Somente leitura apos envio autorizado"
    _whatsapp_db(path, task_id, agent.session_id, run_id, op, msg)
    import workstation.integrations.hermes.whatsapp_browser_executor as wa
    monkeypatch.setattr(wa, "get_default_db_path", lambda: path)
    # Exact public model-facing arguments: no task/run/operation IDs.
    args = {"recipient_ref": {"source": "allowlisted", "contact_id": 1},
            "message": msg, "verify_delivery": True}
    result = {"state": "CONFIRMED", "sent": True,
              "message_data_id": "sha256:" + "c" * 64, "ack_label": "sent"}
    row = _observe(agent, "whatsapp_send_message", args, result, call_id=op)
    assert row.get("external_readback") and row["external_readback"]["operation_id"] == op
    assert _admit(agent, task_id, run_id).admitted is True
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, task_id).status == "done"

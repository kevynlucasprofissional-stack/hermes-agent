"""Regression: a model cannot swap recipient on the same WhatsApp TaskRun."""
from pathlib import Path
import sqlite3

from workstation.integrations.hermes.whatsapp_target_binding import (
    TargetBindingError, bind_recipient_for_run,
)


def test_atomic_run_target_never_switches(tmp_path: Path):
    db = tmp_path / "control.sqlite"
    assert bind_recipient_for_run(db_path=db, session_id="session", run_id="120",
                                  phone_digits="5511999990001")
    assert bind_recipient_for_run(db_path=db, session_id="session", run_id="120",
                                  phone_digits="5511999990001")
    assert not bind_recipient_for_run(db_path=db, session_id="session", run_id="120",
                                      phone_digits="5511999990002")
    assert bind_recipient_for_run(db_path=db, session_id="session", run_id="121",
                                  phone_digits="5511999990002")
    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT recipient_digest FROM whatsapp_run_recipient_bindings "
                           "WHERE session_id='session' AND run_id='120'").fetchone()
        assert row and len(row[0]) == 64
        assert "5511999990001" not in row[0]


def test_model_can_change_both_ref_and_name_but_not_run_target(tmp_path, monkeypatch):
    from workstation.integrations.hermes import whatsapp_browser_executor as executor
    from workstation.integrations.hermes import whatsapp_recipient_resolution as resolution
    from tools import browser_workstation
    from workstation.integrations.hermes.whatsapp_recipient_resolution import ResolvedRecipient

    db = tmp_path / "control.sqlite"
    monkeypatch.setattr(executor, "get_default_db_path", lambda: db)
    seen = []
    def fake_executor(**kwargs):
        seen.append(kwargs["phone_digits"])
        return {"state": "FAILED", "sent": False,
                "error_code": "CHAT_IDENTITY_UNVERIFIED"}
    monkeypatch.setattr(executor, "whatsapp_send_message", fake_executor)
    def fake_resolve(ref):
        if ref["source"] == "acirv_contacts":
            return ResolvedRecipient(ref, "5511999990001", "Kevyn Lucas", db)
        return ResolvedRecipient(ref, "5511999990002", "+55 11 99999-0002 (Você)", db)
    monkeypatch.setattr(resolution, "resolve_recipient_reference", fake_resolve)
    common = dict(message="oi", task_id="t_abc", kanban_card_id="t_abc",
                  session_id="s_123", run_id="120")
    first = browser_workstation.whatsapp_send_message(
        recipient_ref={"source": "acirv_contacts", "contact_id": 88},
        expected_recipient_name="Kevyn Lucas", operation_id="op_1", **common)
    assert first["error_code"] == "CHAT_IDENTITY_UNVERIFIED"
    second = browser_workstation.whatsapp_send_message(
        recipient_ref={"source": "hermes_local", "contact_id": 1},
        expected_recipient_name="+55 11 99999-0002 (Você)",
        operation_id="op_2", **common)
    assert second["error_code"] == "TARGET_CHANGED_REAUTH_REQUIRED"
    assert second["failure_phase"] == "PRE_SEND"
    assert seen == ["5511999990001"]

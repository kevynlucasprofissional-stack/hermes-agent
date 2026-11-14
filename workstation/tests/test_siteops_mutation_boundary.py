"""Synthetic Site Ops -> native WhatsApp contract. No network, CDP, or real send."""
import sqlite3
from types import SimpleNamespace

from tools import browser_workstation
from workstation.integrations.hermes import whatsapp_browser_executor as executor
from workstation.integrations.hermes import whatsapp_recipient_resolution as recipient_resolution

PHONE = "5511999990000"
MESSAGE = "Fixture: confirmacao operacional"
SCOPE = {
    "task_id": "task-fixture",
    "session_id": "session-fixture",
    "kanban_card_id": "card-fixture",
    "run_id": "run-fixture",
    "operation_id": "op-fixture-001",
}

RECIPIENT_REF = {"source": "fixture", "contact_id": "contact-synthetic-1"}


def _stub_recipient(monkeypatch, db_path):
    def resolve(ref):
        assert ref == RECIPIENT_REF
        return SimpleNamespace(
            phone_digits=PHONE, display_name="Fixture Person",
            db_path=db_path, public_reference=RECIPIENT_REF,
        )
    monkeypatch.setattr(recipient_resolution, "resolve_recipient_reference", resolve)


def _header(name="Fixture Person", phone=PHONE):
    return {
        "attributes": {
            "data-testid": "conversation-info-header",
            "data-chat-id": f"{phone}@c.us",
        },
        "text": name,
    }


def _bubble(message_id, *, body=MESSAGE, phone=PHONE, ack="sent"):
    return {
        "attributes": {
            "data-testid": "msg-container",
            "data-id": message_id,
            "data-direction": "outbound",
            "data-recipient-id": f"{phone}@c.us",
            "data-ack": ack,
        },
        "text": body,
    }


def _ready(name="Fixture Person", phone=PHONE):
    return {
        "elements": [
            _header(name, phone),
            {"attributes": {"data-testid": "send", "aria-label": "Enviar"}, "ref": "@send"},
            _bubble(f"true_{PHONE}@c.us_OLD", body="Older fixture text"),
        ]
    }


def test_synthetic_native_send_confirms_once_and_replay_has_zero_extra_effects(tmp_path, monkeypatch):
    db_path = tmp_path / "native-fixture.db"
    sqlite3.connect(db_path).close()  # Native executor requires an existing control database.
    monkeypatch.setattr(executor, "get_default_db_path", lambda: db_path)
    _stub_recipient(monkeypatch, db_path)
    nav_calls, click_calls, snap_calls = [], [], []
    after = {
        "elements": [
            _header(),
            {"attributes": {"data-testid": "ptt-in-button"}, "text": ""},
            _bubble(f"true_{PHONE}@c.us_NEW"),
        ]
    }

    def dispatch(action, args, **lineage):
        assert lineage["task_id"] == SCOPE["task_id"]
        assert lineage["session_id"] == SCOPE["session_id"]
        assert lineage["kanban_card_id"] == SCOPE["kanban_card_id"]
        assert lineage["run_id"] == SCOPE["run_id"]
        assert lineage["operation_id"]
        assert lineage["model_facing"] is False
        if action == "browser_navigate":
            nav_calls.append(args)
            assert "text=" in args["url"]
            return {"success": True}
        if action == "browser_snapshot":
            snap_calls.append(1)
            return _ready() if len(snap_calls) == 1 else after
        if action == "browser_click":
            with sqlite3.connect(db_path) as db:
                reservation = db.execute(
                    "SELECT operation_id, state FROM whatsapp_send_logs"
                ).fetchone()
            assert reservation[0] == SCOPE["operation_id"]
            assert reservation[1] in {"PREPARED", "DISPATCHING"}
            click_calls.append(args)
            return {"success": True}
        raise AssertionError(f"Unexpected action: {action}")

    monkeypatch.setattr(browser_workstation, "_dispatch", dispatch)
    args = {**SCOPE, "recipient_ref": RECIPIENT_REF, "message": MESSAGE,
            "delivery_timeout_seconds": 0.05}
    first = browser_workstation.whatsapp_send_message(**args)
    assert first["sent"] is True, first
    assert first["state"] == "CONFIRMED"
    assert first["ack_label"] == "sent"
    assert len(nav_calls) == len(click_calls) == 1
    with sqlite3.connect(db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM whatsapp_send_logs").fetchone()[0] == 1

    repeated = browser_workstation.whatsapp_send_message(**args)
    assert repeated["sent"] is False
    assert repeated["state"] == "UNCERTAIN"
    assert repeated["error_code"] == "OPERATION_ALREADY_RECORDED"
    assert len(nav_calls) == len(click_calls) == 1


def test_synthetic_wrong_recipient_never_dispatches_click(tmp_path, monkeypatch):
    db_path = tmp_path / "wrong.db"
    sqlite3.connect(db_path).close()
    monkeypatch.setattr(executor, "get_default_db_path", lambda: db_path)
    _stub_recipient(monkeypatch, db_path)
    calls = []

    def dispatch(action, args, **lineage):
        calls.append(action)
        if action == "browser_navigate":
            return {"success": True}
        if action == "browser_snapshot":
            return _ready(phone="5511999991111")
        raise AssertionError("Wrong recipient must never click")

    monkeypatch.setattr(browser_workstation, "_dispatch", dispatch)
    result = browser_workstation.whatsapp_send_message(
        **SCOPE, recipient_ref=RECIPIENT_REF, message=MESSAGE,
        delivery_timeout_seconds=0.03,
    )
    assert result["sent"] is False
    assert result["state"] == "REVIEW_REQUIRED"
    assert "browser_click" not in calls


def test_missing_taskrun_identity_is_rejected_before_browser_access(monkeypatch):
    def reject_any_dispatch(*_args, **_kwargs):
        raise AssertionError("No browser call without TaskRun authority")
    monkeypatch.setattr(browser_workstation, "_dispatch", reject_any_dispatch)
    result = browser_workstation.whatsapp_send_message(
        phone_digits=PHONE, message=MESSAGE, task_id="",
        session_id="session-fixture", kanban_card_id="card-fixture",
        run_id="run-fixture", operation_id="op-fixture-002",
    )
    assert result["state"] == "FAILED"
    assert result["error_code"] == "TASKRUN_AUTHORITY_REQUIRED"

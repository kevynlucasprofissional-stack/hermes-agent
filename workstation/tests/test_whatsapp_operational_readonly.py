"""Lean WhatsApp send contract and contact discovery tests."""
import hashlib
import json
import sqlite3
from pathlib import Path


def test_wrapper_scopes_browser_steps_to_session_and_call_id(monkeypatch, tmp_path):
    import tools.browser_workstation as bridge
    import workstation.integrations.hermes.whatsapp_recipient_resolution as resolution
    import workstation.integrations.hermes.whatsapp_browser_executor as executor

    ref = {"source": "synthetic", "contact_id": 7}
    recipient = resolution.ResolvedRecipient(ref, "15555550123", "Synthetic Contact", tmp_path / "readonly.sqlite")
    monkeypatch.setattr(resolution, "resolve_recipient_reference", lambda _: recipient)

    dispatches = []
    def dispatch(action, args, **kwargs):
        dispatches.append((action, kwargs))
        return {
            "success": True, "runtime": "electron-chromium",
            "task_id": "session-A", "tab_id": "tab-A",
            "url": "https://web.whatsapp.com/",
        }
    monkeypatch.setattr(bridge, "_dispatch", dispatch)

    def primitive(**kwargs):
        snapshot = kwargs["browser_snapshot"]()
        assert snapshot["success"] is True
        return {"sent": False, "state": "OBSERVED", "error_code": "DOM_RECEIPT_ONLY"}
    monkeypatch.setattr(executor, "whatsapp_send_message", primitive)

    result = bridge.whatsapp_send_message(
        recipient_ref=ref, expected_recipient_name="Synthetic Contact",
        message="Exact body", task_id=None, kanban_card_id=None,
        session_id="session-A", run_id="call-A", operation_id="call-A",
    )
    assert result["state"] == "OBSERVED"
    assert len(dispatches) == 1
    action, identity = dispatches[0]
    assert action == "browser_snapshot"
    assert identity["task_id"] is None
    assert identity["session_id"] == "session-A"
    assert identity["kanban_card_id"] is None
    assert identity["run_id"] == "call-A"
    assert identity["model_facing"] is False
    assert identity["session_scope_only"] is True


def test_dispatch_allows_explicit_session_scope_without_kanban(monkeypatch):
    import tools.browser_workstation as bridge

    sent = {}
    def request(method, path, payload, **kwargs):
        sent.update(method=method, path=path, payload=payload)
        return {"result": {
            "success": True, "runtime": "electron-chromium",
            "task_id": "session-A", "tab_id": "tab-A",
            "url": "https://web.whatsapp.com/",
        }}
    monkeypatch.setattr(bridge, "_request_json", request)
    result = json.loads(bridge._dispatch(
        "browser_snapshot", {}, task_id=None, session_id="session-A",
        kanban_card_id=None, run_id="call-A", operation_id="step-A",
        model_facing=False, session_scope_only=True,
    ))
    assert result["success"] is True
    assert sent["method"] == "POST"
    assert sent["path"] == "/v1/action"
    assert sent["payload"]["task_id"] == "session-A"
    assert sent["payload"]["session_id"] == "session-A"
    assert sent["payload"]["run_id"] == "call-A"
    assert sent["payload"]["operation_id"] == "step-A"
    assert "kanban_card_id" not in sent["payload"]


def test_native_executor_requires_session_context_before_browser_or_db(tmp_path):
    from unittest.mock import MagicMock
    from workstation.integrations.hermes.whatsapp_browser_executor import whatsapp_send_message

    db_path = tmp_path / "must-not-be-created.sqlite"
    nav, snap, click, inspect, type_text = (MagicMock() for _ in range(5))
    result = whatsapp_send_message(
        browser_navigate=nav, browser_snapshot=snap, browser_click=click,
        browser_inspect=inspect, browser_type=type_text,
        session_context_verified=False,
        phone_digits="15555550123", message="private text",
        operation_id="call-A", db_path=db_path, persist=True,
    )
    assert result["sent"] is False
    assert result["state"] == "FAILED"
    assert result["error_code"] == "SESSION_CONTEXT_REQUIRED"
    assert result["failure_phase"] == "PRE_SEND"
    assert not db_path.exists()
    for mock in (nav, snap, click, inspect, type_text):
        mock.assert_not_called()


def test_pre_send_failures_are_not_recorded_as_uncertain_mutations():
    from workstation.batch_detection import _whatsapp_pre_dispatch_refusal

    pre = {
        "sent": False, "state": "FAILED",
        "error_code": "RECIPIENT_CHAT_MISMATCH", "failure_phase": "VERIFY_CHAT",
    }
    uncertain = {
        "sent": False, "state": "UNCERTAIN",
        "error_code": "DOM_RECEIPT_TIMEOUT", "failure_phase": "POST_SEND",
    }
    assert _whatsapp_pre_dispatch_refusal("whatsapp_send_message", json.dumps(pre)) is True
    assert _whatsapp_pre_dispatch_refusal("whatsapp_send_message", json.dumps(uncertain)) is False


def test_durable_send_intent_redacts_body_and_keeps_digest(tmp_path):
    from workstation.integrations.hermes.whatsapp_browser_executor import _reserve_send_intent

    path = tmp_path / "control.sqlite"
    sqlite3.connect(path).close()
    body = "private WhatsApp text"
    digest = hashlib.sha256(body.encode()).hexdigest()
    assert _reserve_send_intent(
        db_path=path, operation_id="call-A", task_id="session-A",
        session_id="session-A", run_id="call-A", message=body,
        approval_fingerprint=None,
    ) is True
    with sqlite3.connect(path) as db:
        row = db.execute(
            "SELECT message_body, message_digest FROM whatsapp_send_logs WHERE operation_id='call-A'"
        ).fetchone()
    assert row == ("[redacted]", digest)


def test_contact_lookup_registry_is_readonly_desktop():
    import tools.browser_tool
    from tools.effects import ToolEffect
    from tools.registry import registry

    entry = registry.get_entry("whatsapp_find_contacts")
    assert entry is not None
    assert entry.toolset == "desktop_ui"
    assert entry.effect == ToolEffect.PURE_READ
    assert set(entry.schema["parameters"]["properties"]) == {"source", "query"}
    assert entry.schema["parameters"].get("additionalProperties") is False


def test_contact_lookup_returns_only_trusted_refs_and_not_phone(tmp_path, monkeypatch):
    from tools.whatsapp_catalog_adapter import find_contacts_for_model
    import workstation.integrations.hermes.whatsapp_recipient_resolution as resolver

    path = tmp_path / "contacts.sqlite"
    phone = "15555550123"
    with sqlite3.connect(path) as db:
        db.execute(
            "CREATE TABLE contacts (id INTEGER PRIMARY KEY, display_name TEXT, type TEXT, "
            "phone_raw TEXT, phone_number TEXT, phone_source TEXT, whatsapp_id TEXT)"
        )
        db.executemany("INSERT INTO contacts VALUES (?,?,?,?,?,?,?)", [
            (1, "Pessoa Alvo", "contact", phone, None, "jid", phone + "@c.us"),
            (2, "Pessoa Alvo antiga", "contact", phone, None, "outdated", phone + "@c.us"),
            (3, "Pessoa Alvo inválida", "contact", phone, None, "jid", "bad"),
        ])
    monkeypatch.setattr(
        resolver, "_configured_sources",
        lambda: {"trusted": {"db_path": str(path), "allowed_phone_sources": ["jid"]}},
    )
    raw = find_contacts_for_model(
        {"source": "trusted", "query": "Pessoa Alvo"},
        session_id="session-A", tool_call_id="call-A",
    )
    result = json.loads(raw)
    assert result["success"] is True
    assert result["count"] == 1
    assert result["contacts"][0]["recipient_ref"] == {"source": "trusted", "contact_id": 1}
    assert "approval_required" not in result
    assert result["read_only"] is True
    assert phone not in raw
    assert "sqlite" not in raw

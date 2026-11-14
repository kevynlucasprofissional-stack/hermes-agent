"""Acceptance contracts at the MODEL-FACING WhatsApp registry boundary.

Synthetic, no Browser connection, no production database, no real sends.
These are RED until a trusted Desktop catalog adapter is implemented.
"""
import json

import tools.browser_tool  # noqa: F401 -- the runtime registers tools at import
from tools.effects import ToolEffect
from tools.registry import registry


def test_native_capabilities_registered_for_desktop_only():
    for name in ("whatsapp_read_messages", "whatsapp_batch_preview"):
        entry = registry.get_entry(name)
        assert entry is not None, f"{name} has no callable registry handler"
        assert entry.toolset == "desktop_ui"
        assert registry.get_schema(name) is not None


def test_read_contract_cannot_request_browser_mutations_or_database_writes():
    entry = registry.get_entry("whatsapp_read_messages")
    assert entry is not None
    assert entry.effect == ToolEffect.PURE_READ
    params = entry.schema["parameters"]
    properties = params["properties"]
    assert params.get("additionalProperties") is False
    assert "limit" in properties
    assert 1 <= properties["limit"].get("maximum", 0) <= 50
    assert not {"persist", "db_path", "phone_digits", "message", "browser_action"} & set(properties)


def test_preview_contract_uses_authorized_references_not_private_payloads():
    entry = registry.get_entry("whatsapp_batch_preview")
    assert entry is not None
    assert entry.effect == ToolEffect.PURE_READ
    params = entry.schema["parameters"]
    properties = params["properties"]
    assert params.get("additionalProperties") is False
    assert {"source", "campaign_slug", "step_code"} <= set(properties)
    assert not {
        "recipients", "phone_digits", "db_path", "message_template",
        "approved_by", "approval_token", "authorization_override",
    } & set(properties)


def test_untrusted_preview_reference_fails_closed_at_real_dispatch():
    assert registry.get_entry("whatsapp_batch_preview") is not None, "Unknown tool is not a valid deny"
    raw = registry.dispatch(
        "whatsapp_batch_preview",
        {"source": "synthetic-unknown-source", "campaign_slug": "synthetic-only", "step_code": "wa_1"},
        session_id="synthetic-hermes-session",
        tool_call_id="synthetic-tool-call",
    )
    result = json.loads(raw)
    assert result.get("success") is not True
    assert result.get("state") not in ("APPROVED", "CONFIRMED")
    assert "approval_token" not in result
    assert "15555550123" not in raw


def test_human_approval_must_not_be_a_model_invocable_tool():
    assert registry.get_entry("whatsapp_batch_approve") is None


def test_authorized_synthetic_campaign_preview_is_private_and_readonly(tmp_path, monkeypatch):
    import sqlite3
    import workstation.integrations.hermes.whatsapp_recipient_resolution as resolver

    path = tmp_path / "synthetic-whatsapp.sqlite"
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE campaigns (id INTEGER PRIMARY KEY, slug TEXT);
            CREATE TABLE campaign_messages (id INTEGER PRIMARY KEY, campaign_id INTEGER, step_code TEXT);
            CREATE TABLE campaign_sends (campaign_id INTEGER, campaign_message_id INTEGER,
                                         contact_id INTEGER, status TEXT);
            CREATE TABLE campaign_enrollments (id INTEGER PRIMARY KEY, campaign_id INTEGER,
              contact_id INTEGER, status TEXT, authorized_at TEXT, authorized_via TEXT);
            CREATE TABLE contacts (id INTEGER PRIMARY KEY, whatsapp_id TEXT, display_name TEXT,
              type TEXT, phone_raw TEXT, phone_number TEXT, phone_source TEXT);
            INSERT INTO campaigns VALUES (1,'synthetic-campaign');
            INSERT INTO campaign_messages VALUES (2,1,'wa_1');
            INSERT INTO contacts VALUES (7,'15555550123@c.us','Synthetic Test Person','contact',
              '+15555550123',NULL,'synthetic-provenance');
            INSERT INTO campaign_enrollments VALUES (3,1,7,'replied_authorized','2026-01-01','consent-test');
        """)
    monkeypatch.setattr(resolver, "_configured_sources", lambda: {
        "synthetic-source": {"db_path": str(path), "allowed_phone_sources": ["synthetic-provenance"]}
    })
    before = path.read_bytes()
    raw = registry.dispatch(
        "whatsapp_batch_preview",
        {"source": "synthetic-source", "campaign_slug": "synthetic-campaign", "step_code": "wa_1"},
        session_id="synthetic-desktop-session", tool_call_id="synthetic-read-call",
    )
    result = json.loads(raw)
    assert result["success"] is True
    assert result["eligible_count"] == 1
    assert result["approval_status"] == "NOT_APPROVED"
    assert result["can_send"] is False
    assert "15555550123" not in raw
    assert "Synthetic Test Person" not in raw
    assert path.read_bytes() == before


def test_native_read_registry_redacts_private_body_and_never_persists(monkeypatch):
    import tools.browser_workstation as workstation

    calls = []
    def synthetic_native_read(**kwargs):
        calls.append(kwargs)
        return {"success": True, "messages": [
            {"direction": "inbound", "text": "Contact +15555550123 called", "time_label": "08:23"},
        ]}
    monkeypatch.setattr(workstation, "whatsapp_read_messages_current", synthetic_native_read)
    raw = registry.dispatch(
        "whatsapp_read_messages", {"limit": 2},
        session_id="synthetic-desktop-session", tool_call_id="synthetic-native-call",
    )
    result = json.loads(raw)
    assert result["success"] is True
    assert result["count"] == 1
    assert "15555550123" not in raw
    assert calls == [{"limit": 2, "session_id": "synthetic-desktop-session",
                      "operation_id": "synthetic-native-call"}]

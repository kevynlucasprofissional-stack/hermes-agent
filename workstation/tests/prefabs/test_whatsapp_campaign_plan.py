"""A built-in campaign plan is read-only, multi-step and evidence-aware."""
import json
import sqlite3

from workstation.prefabs.whatsapp_campaign import plan_campaign


def _source(tmp_path):
    db = tmp_path / "workstation-campaign.sqlite"
    with sqlite3.connect(db) as conn:
        conn.executescript("""
          CREATE TABLE campaigns (id INTEGER PRIMARY KEY, slug TEXT);
          CREATE TABLE campaign_messages (
            id INTEGER PRIMARY KEY, campaign_id INTEGER, step_code TEXT,
            step_index INTEGER, body_template TEXT, media_paths TEXT
          );
          CREATE TABLE campaign_enrollments (
            id INTEGER PRIMARY KEY, campaign_id INTEGER, contact_id INTEGER,
            status TEXT, authorized_at TEXT, authorized_via TEXT
          );
          CREATE TABLE campaign_sends (
            id INTEGER PRIMARY KEY, campaign_id INTEGER, contact_id INTEGER,
            campaign_message_id INTEGER, step_code TEXT, status TEXT, evidence TEXT
          );
          INSERT INTO campaigns VALUES (1,'fixture-campaign');
          INSERT INTO campaign_messages VALUES
            (11,1,'wa_01',1,'Hello [nome]','[]'),
            (12,1,'wa_02',2,'Caption','["fixture.jpg"]');
          INSERT INTO campaign_enrollments VALUES
            (100,1,10,'replied_authorized','2026-11-11','human'),
            (101,1,11,'pending',NULL,NULL);
          INSERT INTO campaign_sends VALUES
            (200,1,10,11,'wa_01','sent','{"verified":"saw bubble"}');
        """)
    return db


def test_native_plan_flags_legacy_evidence_and_keeps_personal_data_private(tmp_path):
    db = _source(tmp_path)
    result = plan_campaign(db, "fixture-campaign")
    assert result["total_recipients"] == 2
    assert len(result["steps"]) == 2
    assert result["steps"][0]["legacy_unverified"] == 1
    assert result["steps"][1]["media"] is True
    assert result["approval_status"] == "NOT_APPROVED"
    assert result["can_send"] is False
    serialized = json.dumps(result)
    assert "Hello [nome]" not in serialized
    assert "fixture.jpg" not in serialized
    assert "saw bubble" not in serialized


def test_structured_native_receipt_is_counted_only_for_exact_step(tmp_path):
    db = _source(tmp_path)
    receipt = json.dumps({
        "state": "CONFIRMED", "sent": True,
        "message_data_id": "sha256:" + "b" * 64,
        "ack_label": "delivered", "header_verified": "synthetic target",
    })
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE campaign_sends SET evidence=? WHERE id=200", (receipt,))
    summary = plan_campaign(db, "fixture-campaign")
    assert summary["steps"][0]["structured_receipt_shapes"] == 1
    assert summary["steps"][0]["legacy_unverified"] == 0
    assert summary["steps"][1]["structured_receipt_shapes"] == 0
    assert summary["independently_verified"] is False


def test_unknown_campaign_is_not_created(tmp_path):
    db = _source(tmp_path)
    assert plan_campaign(db, "unknown")["error_code"] == "CAMPAIGN_NOT_FOUND"
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 1

def test_desktop_prefab_exposes_bounded_campaign_plan_without_skill(tmp_path, monkeypatch):
    from tools import whatsapp_catalog_adapter, workstation_prefabs
    db = _source(tmp_path)
    monkeypatch.setattr(
        whatsapp_catalog_adapter, "_read_only_source",
        lambda alias: db if alias == "approved-profile-alias" else None,
    )
    result = json.loads(workstation_prefabs._handler(
        {"action": "whatsapp_campaign_plan", "source": "approved-profile-alias",
         "campaign_slug": "fixture-campaign"},
        session_id="desktop-session", tool_call_id="call-1",
    ))
    assert result["ok"] is True
    assert result["data"]["step_count"] == 2
    assert result["data"]["can_send"] is False
    unauthorized = json.loads(workstation_prefabs._handler(
        {"action": "whatsapp_campaign_plan", "source": "forbidden",
         "campaign_slug": "fixture-campaign"},
        session_id="desktop-session", tool_call_id="call-2",
    ))
    assert unauthorized["ok"] is False
    assert "sqlite" not in json.dumps(unauthorized)

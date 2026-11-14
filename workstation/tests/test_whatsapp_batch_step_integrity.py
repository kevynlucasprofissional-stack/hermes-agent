"""Regression: native WhatsApp batch must not manufacture a send confirmation.

Only synthetic databases and fake browser callbacks are used.
"""
import json
import sqlite3

from workstation.integrations.hermes.whatsapp_batch_executor import (
    _record_campaign_send_mirrored,
)


def _db():
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
      CREATE TABLE campaigns (id INTEGER PRIMARY KEY, slug TEXT UNIQUE);
      CREATE TABLE campaign_messages (
        id INTEGER PRIMARY KEY, campaign_id INTEGER, step_code TEXT, step_index INTEGER
      );
      CREATE TABLE campaign_enrollments (
        id INTEGER PRIMARY KEY, campaign_id INTEGER, contact_id INTEGER
      );
      CREATE TABLE campaign_sends (
        id INTEGER PRIMARY KEY, campaign_id INTEGER, enrollment_id INTEGER,
        contact_id INTEGER, campaign_message_id INTEGER, step_code TEXT,
        channel TEXT, status TEXT, transport TEXT, attempted_at TEXT,
        sent_at TEXT, confirmed_at TEXT, evidence TEXT, error_message TEXT,
        updated_at TEXT
      );
      INSERT INTO campaigns VALUES (6,'test-run');
      INSERT INTO campaign_messages VALUES (1,6,'wa_01',1), (2,6,'wa_02',2);
      INSERT INTO campaign_enrollments VALUES (99,6,22);
    """)
    return conn


def test_mirror_only_the_exact_approved_step():
    with _db() as conn:
        _record_campaign_send_mirrored(
            conn, campaign_slug="test-run", contact_id=22,
            step_code="wa_02", status="sent",
            evidence={"state": "CONFIRMED", "sent": True,
                      "message_data_id": "sha256:" + "a"*64,
                      "ack_label": "sent", "header_verified": "recipient"},
        )
        rows = conn.execute("SELECT step_code, campaign_message_id FROM campaign_sends").fetchall()
        assert rows == [("wa_02", 2)]


def test_no_mirror_for_unverified_free_text():
    with _db() as conn:
        _record_campaign_send_mirrored(
            conn, campaign_slug="test-run", contact_id=22,
            step_code="wa_01", status="sent",
            evidence={"verified": "I saw the bubble"},
        )
        assert conn.execute("SELECT COUNT(*) FROM campaign_sends").fetchone()[0] == 0


def test_missing_step_does_not_fall_back_to_first_step():
    with _db() as conn:
        _record_campaign_send_mirrored(
            conn, campaign_slug="test-run", contact_id=22,
            step_code="unknown", status="sent",
            evidence={"state": "CONFIRMED", "sent": True,
                      "message_data_id": "sha256:" + "a"*64,
                      "ack_label": "sent", "header_verified": "recipient"},
        )
        assert conn.execute("SELECT COUNT(*) FROM campaign_sends").fetchone()[0] == 0

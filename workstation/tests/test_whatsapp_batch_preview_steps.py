"""WA-MVP-01: read-only step-scoped preview and resume safety regressions."""

import json
import sqlite3
from contextlib import closing

from workstation.integrations.hermes import whatsapp_batch_executor as batch

CAMPAIGN = "synthetic-step-campaign"
PHONE = "5511999999999"
BODY = "Synthetic body for WA-MVP-01"


def _recipient(status="authorized"):
    return {
        "contact_id": 7,
        "display_name": "Synthetic Recipient",
        "phone_digits": PHONE,
        "message_body": BODY,
        "permission_status": status,
    }


def _db(tmp_path, *, step_column=True):
    path = tmp_path / "preview-steps.sqlite"
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("CREATE TABLE campaigns (id INTEGER PRIMARY KEY, slug TEXT UNIQUE)")
        conn.execute("INSERT INTO campaigns VALUES (1, ?)", (CAMPAIGN,))
        if step_column:
            conn.execute(
                "CREATE TABLE campaign_sends (campaign_id INTEGER, contact_id INTEGER, "
                "step_code TEXT, status TEXT, evidence TEXT)"
            )
        else:
            conn.execute(
                "CREATE TABLE campaign_sends (campaign_id INTEGER, contact_id INTEGER, status TEXT)"
            )
        conn.commit()
    return path


def _send(path, step, status, *, evidence=None):
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(
            "INSERT INTO campaign_sends VALUES (1, 7, ?, ?, ?)",
            (step, status, evidence),
        )
        conn.commit()


def _preview(path, step, recipient=None):
    return batch.whatsapp_batch_preview(
        recipients=[recipient or _recipient()],
        campaign_slug=CAMPAIGN,
        step_code=step,
        db_path=path,
    )


def test_resume_wrapper_forwards_only_supported_parameters(monkeypatch):
    from tools import browser_workstation

    observed = {}

    def fake_resume(*, job_id, browser_navigate, browser_snapshot,
                    browser_click, task_id, session_id, db_path):
        observed.update(job_id=job_id, task_id=task_id,
                        session_id=session_id, db_path=db_path)
        return {"status": "PAUSED", "job_id": job_id}

    monkeypatch.setattr(batch, "whatsapp_batch_resume", fake_resume)
    result = browser_workstation.whatsapp_batch_control(
        job_id="synthetic-job", action="resume",
        task_id="task", session_id="session", db_path="synthetic.sqlite",
    )
    assert result == {"status": "PAUSED", "job_id": "synthetic-job"}
    assert observed == {
        "job_id": "synthetic-job", "task_id": "task",
        "session_id": "session", "db_path": "synthetic.sqlite",
    }


def test_step_scoping_does_not_hide_pending_step_and_blocks_sent_step(tmp_path):
    db = _db(tmp_path)
    _send(db, "wa_01", "sent", evidence='{"verified": true}')
    _send(db, "wa_02", "pending")
    next_step = _preview(db, "wa_02")
    assert next_step["eligible_count"] == 1
    assert next_step["excluded_count"] == 0
    previous_step = _preview(db, "wa_01")
    assert previous_step["eligible_count"] == 0
    assert previous_step["reasons_breakdown"] == {"ALREADY_SENT": 1}
    assert previous_step["legacy_unverified_count"] == 1
    # Public/model-facing result contains no private phone, name or message.
    assert PHONE not in json.dumps(previous_step)
    assert BODY not in json.dumps(next_step)
    assert "Synthetic Recipient" not in json.dumps(next_step)


def test_uncertain_step_blocks_even_when_another_step_was_sent(tmp_path):
    db = _db(tmp_path)
    _send(db, "wa_01", "sent")
    _send(db, "wa_02", "uncertain")
    assert _preview(db, "wa_02")["reasons_breakdown"] == {"ALREADY_UNCERTAIN": 1}
    assert _preview(db, "wa_03")["eligible_count"] == 1


def test_conflicting_status_for_same_step_requires_reconciliation(tmp_path):
    db = _db(tmp_path)
    _send(db, "wa_02", "sent")
    _send(db, "wa_02", "uncertain")
    assert _preview(db, "wa_02")["reasons_breakdown"] == {"ALREADY_UNCERTAIN": 1}


def test_opted_out_is_excluded_from_pending_step(tmp_path):
    db = _db(tmp_path)
    _send(db, "wa_02", "pending")
    result = _preview(db, "wa_02", _recipient("opted_out"))
    assert result["reasons_breakdown"] == {"OPTED_OUT": 1}
    assert result["eligible_count"] == 0
    assert PHONE not in json.dumps(result)


def test_unscoped_legacy_history_never_authorizes_resend_of_unknown_step(tmp_path):
    db = _db(tmp_path, step_column=False)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("INSERT INTO campaign_sends VALUES (1, 7, 'sent')")
        conn.commit()
    result = _preview(db, "wa_02")
    assert result["eligible_count"] == 0
    assert result["reasons_breakdown"] == {"LEGACY_STEP_UNKNOWN": 1}
    assert result["legacy_unverified_count"] == 1
    # Preserve existing no-step legacy behavior, without implying proof.
    original = _preview(db, None)
    assert original["reasons_breakdown"] == {"ALREADY_SENT": 1}


def test_null_step_legacy_record_blocks_unknown_step(tmp_path):
    db = _db(tmp_path)
    _send(db, None, "sent", evidence='{"verified": true}')
    result = _preview(db, "wa_02")
    assert result["reasons_breakdown"] == {"LEGACY_STEP_UNKNOWN": 1}
    assert result["legacy_unverified_count"] == 1


def test_history_read_failure_fails_closed_instead_of_authorizing_send(tmp_path):
    db = _db(tmp_path)
    with closing(sqlite3.connect(db)) as conn:
        conn.execute("DROP TABLE campaign_sends")
        conn.commit()
    result = _preview(db, "wa_01")
    assert result["eligible_count"] == 0
    assert result["reasons_breakdown"] == {"HISTORY_UNAVAILABLE": 1}
    assert PHONE not in json.dumps(result)


def test_empty_step_legacy_record_blocks_unknown_step(tmp_path):
    db = _db(tmp_path)
    _send(db, "", "sent")
    result = _preview(db, "wa_02")
    assert result["eligible_count"] == 0
    assert result["reasons_breakdown"] == {"LEGACY_STEP_UNKNOWN": 1}

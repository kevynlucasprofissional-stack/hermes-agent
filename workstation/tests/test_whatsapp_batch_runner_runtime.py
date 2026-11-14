"""No simulated send is allowed to count as a verified native campaign step."""
import sqlite3

from workstation.integrations.hermes import whatsapp_batch_executor as batch


def _new_job(tmp_path):
    db = tmp_path / "campaign.sqlite"
    job = batch.create_batch_job(
        recipients=[{"contact_id": 7, "display_name": "Synthetic Contact",
                     "phone_digits": "5511999999999", "message_body": "Hello!"}],
        campaign_slug=None, step_code="wa_01", db_path=db,
    )
    return db, job


def _run(db, job):
    def forbidden(**kwargs):
        raise AssertionError("mock browser callbacks must not execute")
    return batch.whatsapp_batch_send(
        job_id=job, browser_navigate=forbidden, browser_snapshot=forbidden,
        browser_click=forbidden, db_path=db, rate_limit_delay_seconds=0,
    )


def test_stale_sending_step_never_becomes_completed(tmp_path):
    db, job = _new_job(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE whatsapp_batch_items SET status='sending' WHERE job_id=?", (job,))
    result = _run(db, job)
    assert result["status"] == "PAUSED"
    assert result["confirmed_items"] == 0


def test_false_confirmed_without_owner_evidence_is_uncertain(tmp_path, monkeypatch):
    db, job = _new_job(tmp_path)

    def fake_send(**kwargs):
        assert kwargs.get("operation_id")
        return {"state": "CONFIRMED", "sent": True}

    monkeypatch.setattr(batch, "whatsapp_send_message", fake_send)
    result = _run(db, job)
    assert result["confirmed_items"] == 0
    assert result["uncertain_items"] == 1


def test_workstation_wrapper_calls_real_batch_signature(monkeypatch):
    from tools import browser_workstation
    observed = {}
    monkeypatch.setattr(
        batch, "whatsapp_batch_send",
        lambda **kwargs: observed.update(kwargs) or {"status": "PAUSED"},
    )
    result = browser_workstation.whatsapp_batch_send(
        job_id="synthetic-job", db_path="synthetic.sqlite",
        task_id="task", session_id="session", rate_limit_delay_seconds=60,
    )
    assert result == {"status": "PAUSED"}
    assert observed["job_id"] == "synthetic-job"
    assert observed["rate_limit_delay_seconds"] == 60
    assert "persist" not in observed

def test_cooldown_is_persisted_before_sleep(tmp_path, monkeypatch):
    from datetime import datetime, UTC
    db, job = _new_job(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("""INSERT INTO whatsapp_batch_items
          (job_id,contact_id,display_name,phone_digits,contact_name_hint,message_body,status)
          VALUES (?,?,?,?,?,?,?)""",
          (job, 8, "Other Synthetic", "5511988888888", "Other Synthetic", "Hello!", "queued"))
        conn.execute("UPDATE whatsapp_batch_jobs SET total_items=2 WHERE job_id=?", (job,))

    def verified(**kwargs):
        return {"sent": True, "state": "CONFIRMED", "message_data_id": "sha256:" + "c"*64,
                "ack_label": "sent", "header_verified": "Synthetic Contact"}

    class StoppedClock(Exception):
        pass

    monkeypatch.setattr(batch, "whatsapp_send_message", verified)
    monkeypatch.setattr(batch.time, "sleep", lambda seconds: (_ for _ in ()).throw(StoppedClock()))
    try:
        batch.whatsapp_batch_send(
            job_id=job, browser_navigate=lambda **kw: None,
            browser_snapshot=lambda **kw: None, browser_click=lambda **kw: None,
            db_path=db, rate_limit_delay_seconds=60,
        )
    except StoppedClock:
        pass
    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT next_allowed_at FROM whatsapp_batch_jobs WHERE job_id=?", (job,)).fetchone()
        assert row and row[0]
        assert datetime.fromisoformat(row[0]) > datetime.now(UTC)


def test_resumed_batch_waits_for_persisted_cooldown_before_dispatch(tmp_path, monkeypatch):
    from datetime import datetime, timedelta, UTC
    db, job = _new_job(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE whatsapp_batch_jobs SET next_allowed_at=? WHERE job_id=?",
                     ((datetime.now(UTC)+timedelta(seconds=50)).isoformat(), job))
    class ClockPaused(Exception):
        pass
    monkeypatch.setattr(batch.time, "sleep",
                        lambda seconds: (_ for _ in ()).throw(ClockPaused()))
    monkeypatch.setattr(batch, "whatsapp_send_message",
                        lambda **kw: (_ for _ in ()).throw(
                            AssertionError("must not dispatch before persisted cooldown")))
    try:
        _run(db, job)
    except ClockPaused:
        pass
    else:
        raise AssertionError("expected deterministic wait from persisted clock")

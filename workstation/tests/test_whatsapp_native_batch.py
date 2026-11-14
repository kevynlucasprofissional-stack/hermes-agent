"""Short native batch: receipts, durable checkpoints, no unsafe retries."""
from __future__ import annotations

import sqlite3
from workstation.integrations.hermes.whatsapp_native_batch import execute_native_batch

ITEMS = [
    {"target_name": "Kevyn ACIRV", "message": "Authorized first synthetic message"},
    {"recipient_ref": {"source": "hermes_local", "contact_id": 1},
     "expected_recipient_name": "+55 64 9247-0988 (Você)",
     "message": "Authorized second synthetic message"},
]
RECEIPT = {"state": "OBSERVED", "ack_label": "sent", "header_verified": True,
           "message_data_id": "sha256:" + "a" * 64,
           "independently_verified": False}


def test_batch_two_distinct_targets_checkpointed_and_no_replay(tmp_path):
    db = tmp_path / "wa.sqlite"
    calls = []
    def send(**kwargs):
        calls.append(kwargs)
        return RECEIPT
    args = dict(items=ITEMS, task_id="task", run_id="run", session_id="session",
                sender=send, db_path=db, interval_seconds=0)
    result = execute_native_batch(**args)
    assert result["state"] == "COMPLETED"
    assert result["observed_count"] == 2
    assert result["confirmed_count"] == 0
    assert result["independently_verified"] is False
    assert len(calls) == 2
    assert calls[0]["target_name"] == "Kevyn ACIRV"
    assert calls[1]["recipient_ref"]["contact_id"] == 1
    assert calls[0]["batch_item_key"] != calls[1]["batch_item_key"]
    assert calls[0]["run_id"] == calls[1]["run_id"] == "run"
    assert calls[0]["operation_id"] != calls[1]["operation_id"]
    repeat = execute_native_batch(**args)
    assert repeat["replayed"] is True
    assert len(calls) == 2
    from workstation.integrations.hermes.whatsapp_native_batch import read_native_batch_status
    public = read_native_batch_status(job_id=result["job_id"], db_path=db)
    assert public["success"] is True
    assert public["observed_count"] == 2
    assert public["state"] == "COMPLETED"
    assert "Kevyn ACIRV" not in str(public)
    assert "Authorized first synthetic message" not in str(public)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM whatsapp_native_batch_jobs").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM whatsapp_native_batch_items WHERE status='OBSERVED'").fetchone()[0] == 2


def test_uncertain_first_item_stops_without_retrying_second(tmp_path):
    calls = []
    def uncertain(**kwargs):
        calls.append(kwargs)
        return {"state": "UNCERTAIN", "error_code": "POST_SEND_UNKNOWN"}
    args = dict(items=ITEMS, task_id="task", run_id="run", session_id="session",
                sender=uncertain, db_path=tmp_path/"uncertain.sqlite",
                interval_seconds=0)
    result = execute_native_batch(**args)
    assert result["state"] == "PAUSED"
    assert [x["state"] for x in result["results"]] == ["UNCERTAIN", "QUEUED"]
    assert len(calls) == 1
    assert execute_native_batch(**args)["replayed"] is True
    assert len(calls) == 1


def test_observed_without_receipt_is_uncertain_and_does_not_advance(tmp_path):
    calls = []
    def not_verified(**kwargs):
        calls.append(kwargs)
        return {"state": "OBSERVED", "ack_label": "sent", "header_verified": True}
    result = execute_native_batch(
        items=ITEMS, task_id="task", run_id="run", session_id="session",
        sender=not_verified, db_path=tmp_path/"receipt.sqlite",
        interval_seconds=0)
    assert result["state"] == "PAUSED"
    assert [r["state"] for r in result["results"]] == ["UNCERTAIN", "QUEUED"]
    assert len(calls) == 1


def test_exception_after_send_attempt_is_uncertain_and_paused(tmp_path):
    called = []
    def explode(**kwargs):
        called.append(kwargs)
        raise RuntimeError("Message may have been sent")
    result = execute_native_batch(
        items=ITEMS, task_id="task", run_id="run", session_id="session",
        sender=explode, db_path=tmp_path/"exception.sqlite",
        interval_seconds=0)
    assert result["results"][0]["error_code"] == "BATCH_DISPATCH_EXCEPTION"
    assert result["state"] == "PAUSED"
    assert len(called) == 1

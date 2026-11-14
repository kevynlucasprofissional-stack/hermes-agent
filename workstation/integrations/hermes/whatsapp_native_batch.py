"""Small authorized native WhatsApp batch on the existing control SQLite.

Separate additive ledger is needed because the legacy batch schema cannot
represent OBSERVED (DOM receipt without independent server ACK). No legacy
tables, contact sources or migrations are modified.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Callable


def execute_native_batch(
    *, items: list[dict[str, Any]], task_id: str, run_id: str,
    session_id: str, sender: Callable[..., dict[str, Any]], db_path: Path,
    interval_seconds: float = 0.5,
) -> dict[str, Any]:
    if (not isinstance(items, list) or not 2 <= len(items) <= 5
            or not all(isinstance(x, dict) for x in items)
            or not task_id or not run_id or not session_id):
        return {"state": "FAILED", "error_code": "BATCH_ARGUMENTS_INVALID"}
    canonical = json.dumps(items, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    fingerprint = hashlib.sha256(
        (session_id + "|" + task_id + "|" + str(run_id) + "|" + canonical).encode()
    ).hexdigest()
    job_id = "wa_hyb_" + fingerprint[:24]
    db_path = Path(db_path)

    with sqlite3.connect(db_path, timeout=5) as db:
        db.execute("PRAGMA busy_timeout=5000")
        db.execute("""CREATE TABLE IF NOT EXISTS whatsapp_native_batch_jobs(
            job_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, run_id TEXT NOT NULL,
            session_id TEXT NOT NULL, manifest_hash TEXT NOT NULL,
            status TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        db.execute("""CREATE TABLE IF NOT EXISTS whatsapp_native_batch_items(
            job_id TEXT NOT NULL, position INTEGER NOT NULL,
            recipient_json TEXT NOT NULL, message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'QUEUED',
            error_code TEXT, message_data_id TEXT, ack_label TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (job_id, position))""")
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute(
            "SELECT status,manifest_hash FROM whatsapp_native_batch_jobs WHERE job_id=?",
            (job_id,),
        ).fetchone()
        if previous is not None:
            if previous[1] != fingerprint:
                db.rollback()
                return {"state": "FAILED", "error_code": "BATCH_MANIFEST_MISMATCH"}
            result_rows = db.execute(
                "SELECT position,status,error_code,ack_label,message_data_id "
                "FROM whatsapp_native_batch_items WHERE job_id=? ORDER BY position",
                (job_id,),
            ).fetchall()
            db.commit()
            return {"state": previous[0], "job_id": job_id, "replayed": True,
                    "results": [_serialize_row(x) for x in result_rows]}
        db.execute(
            "INSERT INTO whatsapp_native_batch_jobs"
            "(job_id,task_id,run_id,session_id,manifest_hash,status) VALUES (?,?,?,?,?,?)",
            (job_id, task_id, str(run_id), session_id, fingerprint, "RUNNING"),
        )
        for n, item in enumerate(items):
            db.execute(
                "INSERT INTO whatsapp_native_batch_items "
                "(job_id,position,recipient_json,message) VALUES (?,?,?,?)",
                (job_id, n, json.dumps({
                    k: v for k, v in item.items() if k != "message"
                }, ensure_ascii=False, sort_keys=True), item["message"]),
            )
        db.commit()

    last_state = "COMPLETED"
    for n, item in enumerate(items):
        with sqlite3.connect(db_path, timeout=5) as db:
            db.execute("BEGIN IMMEDIATE")
            updated = db.execute(
                "UPDATE whatsapp_native_batch_items SET status='SENDING',"
                "updated_at=CURRENT_TIMESTAMP WHERE job_id=? AND position=? "
                "AND status='QUEUED'", (job_id, n),
            )
            if updated.rowcount != 1:
                db.rollback()
                last_state = "PAUSED"
                break
            db.commit()
        try:
            result = sender(
                **item,
                task_id=task_id, kanban_card_id=task_id,
                run_id=run_id, session_id=session_id,
                operation_id=f"op_{fingerprint[:14]}_{n}",
                batch_item_key=f"{job_id}:{n}",
                delivery_timeout_seconds=5.0,
            )
            if not isinstance(result, dict):
                result = {"state": "UNCERTAIN", "error_code": "BATCH_INVALID_SEND_RESULT"}
        except Exception:
            # Exception after dispatch may have caused an external send:
            # never retry this item or advance to the next contact.
            result = {"state": "UNCERTAIN", "error_code": "BATCH_DISPATCH_EXCEPTION"}

        state = result.get("state")
        ack = result.get("ack_label")
        msg = result.get("message_data_id")
        evidence = (ack in {"sent", "delivered", "read"}
                    and isinstance(msg, str) and len(msg) == 71
                    and msg.startswith("sha256:")
                    and result.get("header_verified") is True)
        if state == "OBSERVED" and evidence:
            item_state, item_code = "OBSERVED", "DOM_RECEIPT_ONLY"
        elif (state == "CONFIRMED" and evidence
              and result.get("independently_verified") is True):
            item_state, item_code = "CONFIRMED", None
        elif state in {"FAILED", "REVIEW_REQUIRED"}:
            item_state, item_code = "FAILED", str(result.get("error_code") or state)
        else:
            item_state, item_code = "UNCERTAIN", str(result.get("error_code") or "NO_CAUSAL_RECEIPT")
        with sqlite3.connect(db_path, timeout=5) as db:
            db.execute(
                "UPDATE whatsapp_native_batch_items SET status=?,error_code=?,"
                "message_data_id=?,ack_label=?,updated_at=CURRENT_TIMESTAMP "
                "WHERE job_id=? AND position=? AND status='SENDING'",
                (item_state, item_code, msg if evidence else None,
                 ack if evidence else None, job_id, n),
            )
            db.commit()
        if item_state not in {"OBSERVED", "CONFIRMED"}:
            last_state = "PAUSED"
            break
        if n < len(items) - 1 and interval_seconds > 0:
            time.sleep(min(interval_seconds, 3.0))

    with sqlite3.connect(db_path, timeout=5) as db:
        db.execute("UPDATE whatsapp_native_batch_jobs SET status=? WHERE job_id=?",
                   (last_state, job_id))
        rows = db.execute(
            "SELECT position,status,error_code,ack_label,message_data_id "
            "FROM whatsapp_native_batch_items WHERE job_id=? ORDER BY position",
            (job_id,),
        ).fetchall()
        db.commit()
    return {
        "state": last_state, "job_id": job_id, "replayed": False,
        "observed_count": sum(r[1] == "OBSERVED" for r in rows),
        "confirmed_count": sum(r[1] == "CONFIRMED" for r in rows),
        "independently_verified": all(r[1] == "CONFIRMED" for r in rows),
        "results": [_serialize_row(x) for x in rows],
    }


def _serialize_row(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "position": row[0], "state": row[1], "error_code": row[2],
        "ack_label": row[3], "message_data_id": row[4],
    }


def read_native_batch_status(*, job_id: str, db_path: Path) -> dict[str, Any]:
    """Read checkpoint metadata only; no message text or recipient identifiers."""
    import re
    if not isinstance(job_id, str) or not re.fullmatch(r"wa_hyb_[0-9a-f]{24}", job_id):
        return {"success": False, "error_code": "INVALID_BATCH_ID"}
    try:
        with sqlite3.connect("file:" + Path(db_path).as_posix() + "?mode=ro",
                             uri=True, timeout=3) as db:
            row = db.execute(
                "SELECT status FROM whatsapp_native_batch_jobs WHERE job_id=?",
                (job_id,),
            ).fetchone()
            if not row:
                return {"success": False, "error_code": "BATCH_NOT_FOUND"}
            items = db.execute(
                "SELECT position,status,error_code,ack_label,message_data_id "
                "FROM whatsapp_native_batch_items WHERE job_id=? ORDER BY position",
                (job_id,),
            ).fetchall()
    except (sqlite3.Error, OSError):
        return {"success": False, "error_code": "BATCH_STATUS_UNAVAILABLE"}
    return {
        "success": True, "job_id": job_id, "state": row[0],
        "observed_count": sum(x[1] == "OBSERVED" for x in items),
        "confirmed_count": sum(x[1] == "CONFIRMED" for x in items),
        "results": [_serialize_row(x) for x in items],
    }

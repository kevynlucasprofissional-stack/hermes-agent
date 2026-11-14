"""QA-only Trello title push. One durable intent and one Browser effect attempt."""
from __future__ import annotations
import hashlib
import json
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from workstation.acirv_datasets import get_record
from workstation.dataset_edits import _connect
from workstation.trello_sync_reconcile import verified_browser_card_title

CARD = re.compile(r"^[a-f0-9]{24}$")
RUN = re.compile(r"^[a-zA-Z0-9_.:-]{1,100}$")
TITLE_REF = re.compile(r"^(@e\d+) textarea .*testid=card-back-title-input\s*$", re.M)
QA_BOARD = "Hermes Sync QA"

def shortlink(url: str) -> str:
    if not isinstance(url, str):
        raise ValueError("invalid URL")
    p = urlsplit(url)
    parts = p.path.split("/")
    if (p.scheme != "https" or p.netloc != "trello.com" or p.query or p.fragment
            or len(parts) < 3 or parts[1] != "c"
            or not re.fullmatch(r"[A-Za-z0-9]{8}", parts[2])):
        raise ValueError("invalid Trello card URL")
    return parts[2]

def install(conn: sqlite3.Connection) -> None:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS trello_title_push_intents(
      intent_id TEXT PRIMARY KEY, card_id TEXT NOT NULL,
      review_run_id TEXT NOT NULL, browser_task_id TEXT NOT NULL,
      operation_id TEXT NOT NULL UNIQUE, expected_revision INTEGER NOT NULL,
      remote_before TEXT NOT NULL, target_title TEXT NOT NULL,
      state TEXT NOT NULL, receipts_json TEXT, readback_json TEXT,
      failure_reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
      UNIQUE(card_id, review_run_id))
    """)

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def get_intent(home: Path | None, card_id: str, review_run_id: str) -> dict | None:
    with closing(_connect(home)) as conn:
        install(conn)
        row = conn.execute("SELECT * FROM trello_title_push_intents WHERE card_id=? AND review_run_id=?",
                           (card_id, review_run_id)).fetchone()
        return dict(row) if row else None

def set_state(home: Path | None, intent_id: str, state: str,
              receipts=None, readback=None, reason=None) -> None:
    with closing(_connect(home)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            res = conn.execute(
                "UPDATE trello_title_push_intents SET state=?, receipts_json=?,"
                "readback_json=?, failure_reason=?, updated_at=? WHERE intent_id=?",
                (state, json.dumps(receipts) if receipts is not None else None,
                 json.dumps(readback, ensure_ascii=False) if readback else None,
                 reason, now(), intent_id))
            if res.rowcount != 1:
                raise RuntimeError("intent disappeared")
            conn.commit()
        except Exception:
            conn.rollback()
            raise

def push_reviewed_title(home: Path | None, *, card_id: str, review_run_id: str,
                        expected_revision: int, browser_task_id: str) -> dict:
    """Attempt once. Never redispatch prepared, dispatching, uncertain or verified intents."""
    if (not isinstance(card_id, str) or not CARD.fullmatch(card_id)
            or not isinstance(review_run_id, str) or not RUN.fullmatch(review_run_id)
            or not isinstance(browser_task_id, str)
            or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,120}", browser_task_id)
            or type(expected_revision) is not int or expected_revision < 1):
        raise ValueError("invalid push arguments")
    old = get_intent(home, card_id, review_run_id)
    if old:
        return {"ok": old["state"] == "verified", "status": old["state"],
                "intent_id": old["intent_id"], "redispatched": False}
    detail = get_record(home, "trello", "cards", card_id)
    card = detail["record"]
    if card.get("board_name") != QA_BOARD:
        return {"ok": False, "error": "qa_board_only"}
    if (card.get("status") != "em_aberto" or detail.get("source_conflict_fields")
            or detail.get("local_revision") != expected_revision):
        return {"ok": False, "error": "local_state_changed"}
    with closing(_connect(home)) as conn:
        try:
            row = conn.execute(
                "SELECT plan_json,source_url FROM trello_sync_reviews "
                "WHERE run_id=? AND card_id=?", (review_run_id, card_id)).fetchone()
        except sqlite3.OperationalError:
            row = None
    if row is None:
        return {"ok": False, "error": "review_missing"}
    plan = json.loads(row["plan_json"])
    decision = plan.get("fields", {}).get("name", {})
    if (plan.get("native_observed") is not True
            or plan.get("remote_open_verified") is not True
            or plan.get("browser_task_id") != browser_task_id
            or plan.get("ready_for_external_write") is not False
            or decision.get("action") != "push" or "baseline" not in decision):
        return {"ok": False, "error": "review_not_qualified"}
    target, previous = card.get("name"), decision.get("remote")
    if (not isinstance(target, str) or not target.strip() or len(target) > 500
            or target != decision.get("local") or not isinstance(previous, str)
            or len(previous) > 500 or target == previous):
        return {"ok": False, "error": "title_not_reviewed"}

    from tools.browser_workstation import _dispatch
    try:
        before = verified_browser_card_title(browser_task_id)
        if (not before["open"] or before["name"] != previous
                or before.get("board_name") != QA_BOARD
                or before["list_name"] != plan.get("browser_list_name")
                or shortlink(before["url"]) != shortlink(card["url"])
                or shortlink(row["source_url"]) != shortlink(card["url"])):
            return {"ok": False, "error": "remote_card_changed"}
        snap = json.loads(_dispatch(
            "browser_snapshot", {"full": False, "view": "action_map", "max_chars": 20000},
            task_id=browser_task_id, model_facing=True))
        refs = TITLE_REF.findall(snap.get("snapshot", "")) if snap.get("success") else []
        if len(refs) != 1:
            return {"ok": False, "error": "title_ref_unavailable"}
    except Exception:
        return {"ok": False, "error": "browser_preflight_unavailable"}

    intent_id = hashlib.sha256(f"{card_id}:{review_run_id}".encode()).hexdigest()[:32]
    op_id = "trello-qa-title-" + intent_id
    with closing(_connect(home)) as conn:
        install(conn)
        conn.execute("BEGIN IMMEDIATE")
        try:
            pending = conn.execute(
                "SELECT intent_id,state FROM trello_title_push_intents "
                "WHERE card_id=? AND state IN ('prepared','dispatching','typed','uncertain')",
                (card_id,)).fetchone()
            if pending:
                conn.commit()
                return {"ok": False, "error": "card_has_unresolved_intent",
                        "intent_id": pending["intent_id"]}
            prior = conn.execute(
                "SELECT intent_id,state FROM trello_title_push_intents "
                "WHERE card_id=? AND review_run_id=?", (card_id, review_run_id)).fetchone()
            if prior:
                conn.commit()
                return {"ok": prior["state"] == "verified", "status": prior["state"],
                        "intent_id": prior["intent_id"], "redispatched": False}
            stamp = now()
            conn.execute(
                "INSERT INTO trello_title_push_intents("
                "intent_id,card_id,review_run_id,browser_task_id,operation_id,"
                "expected_revision,remote_before,target_title,state,created_at,updated_at)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (intent_id,card_id,review_run_id,browser_task_id,op_id,
                 expected_revision,previous,target,"prepared",stamp,stamp))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    # Durable PREPARED exists before any side effect. On crash no automatic retries.
    # A local change after review must HOLD before dispatch, never export stale text.
    fresh = get_record(home, "trello", "cards", card_id)
    if (fresh.get("local_revision") != expected_revision
            or fresh["record"].get("name") != target
            or fresh["record"].get("status") != "em_aberto"):
        set_state(home, intent_id, "uncertain", reason="local_changed_after_intent")
        return {"ok": False, "status": "uncertain", "intent_id": intent_id,
                "reason": "local_changed_after_intent", "redispatched": False}
    set_state(home, intent_id, "dispatching")
    receipts, failure = [], None
    try:
        result = json.loads(_dispatch(
            "browser_batch_actions", {"steps": [
                {"kind": "type", "ref": refs[0], "text": target, "clear": True,
                 "anchor": {"type": "testid", "value": "card-back-title-input"}}]},
            task_id=browser_task_id, operation_id=op_id, model_facing=True))
        receipts = result.get("receipts") or []
        if (not result.get("success") or result.get("status") != "verified"
                or result.get("completed_steps") != 1 or result.get("verified_steps") != 1
                or len(receipts) != 1 or not all(
                    isinstance(r, str) and r.startswith(op_id + ":") for r in receipts)):
            failure = "unverified_browser_receipt"
    except Exception:
        failure = "browser_result_unknown"
    if failure is None:
        # Persist typed draft BEFORE a separate save/Enter effect. A crash
        # leaves TYPED on HOLD; no action is automatically retried.
        set_state(home, intent_id, "typed", receipts)
        try:
            commit_id = op_id + "-commit"
            committed = json.loads(_dispatch(
                "browser_press", {"key": "Enter"},
                task_id=browser_task_id, operation_id=commit_id,
                model_facing=True))
            receipt = committed.get("receipt")
            if (not committed.get("success") or not isinstance(receipt, dict)
                    or receipt.get("operationId") != commit_id
                    or receipt.get("browserTaskId") != browser_task_id):
                failure = "commit_receipt_unverified"
            else:
                receipts.append(commit_id + ":" + str(receipt.get("tabId", "")) +
                                ":" + str(receipt.get("revision", "")))
        except Exception:
            failure = "commit_result_unknown"
    if failure is None:
        # A fresh page load proves the title survived Trello's server round-trip.
        try:
            reload = json.loads(_dispatch(
                "browser_navigate", {"url": before["url"]},
                task_id=browser_task_id, operation_id=op_id+"-readback",
                model_facing=True))
            if not reload.get("success"):
                failure = "readback_reload_unverified"
        except Exception:
            failure = "readback_reload_unavailable"
    after = None
    try:
        import time
        for _ in range(3):
            try:
                after = verified_browser_card_title(browser_task_id)
                break
            except ValueError:
                time.sleep(0.6)
        if after is None:
            raise ValueError("readback not ready")
        if (not after["open"] or after["name"] != target
                or after.get("board_name") != QA_BOARD
                or after["list_name"] != before["list_name"]
                or shortlink(after["url"]) != shortlink(before["url"])):
            failure = failure or "readback_mismatch"
    except Exception:
        after = None
        failure = failure or "readback_unavailable"
    state = "verified" if failure is None else "uncertain"
    set_state(home, intent_id, state, receipts, after, failure)
    return {"ok": state == "verified", "status": state, "intent_id": intent_id,
            "owner_receipts_verified": state == "verified", "reason": failure,
            "redispatched": False}

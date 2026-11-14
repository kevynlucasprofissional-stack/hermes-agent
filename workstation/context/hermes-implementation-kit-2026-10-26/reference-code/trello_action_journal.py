"""Reference implementation: durable, append-only Trello action evidence.

Not yet integrated into Hermes Work. Designed to use an existing trusted
SQLite connection, not to create a parallel source of truth for tasks.
No network calls, LLM calls, agent jobs, or outbound effects occur here.

Integration must select the authorized canonical event database connection;
this file deliberately does not guess the project's database path.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

MAX_ACTION_BYTES = 8192
MAX_EVENTS_BATCH = 250


@dataclass(frozen=True)
class AppendOutcome:
    inserted: int
    duplicates: int
    checkpoint: str | None


def install_schema(conn: sqlite3.Connection) -> None:
    """Idempotent. Caller controls migration ownership and database choice."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trello_activity_event (
            board_id TEXT NOT NULL,
            action_id TEXT NOT NULL,
            action_type TEXT NOT NULL,
            event_time TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            captured_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (board_id, action_id)
        );
        CREATE INDEX IF NOT EXISTS ix_trello_activity_time
            ON trello_activity_event(board_id, event_time);
        CREATE TABLE IF NOT EXISTS trello_activity_checkpoint (
            board_id TEXT PRIMARY KEY,
            cursor TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
    """)


def _required(value: Any, label: str, max_chars: int = 256) -> str:
    if not isinstance(value, str) or not value or len(value) > max_chars:
        raise ValueError(f"invalid {label}")
    return value


def normalize_action(action: Mapping[str, Any]) -> tuple[str, str, str, str]:
    """Only retain a bounded allowlist of metadata; never persist raw comments.

    A summary Bot must separately retrieve authorized text when required.
    This minimizes sensitive data and prompt-injection propagation.
    """
    action_id = _required(action.get("id"), "action_id")
    action_type = _required(action.get("type"), "action_type", 128)
    when = _required(action.get("date"), "event_time", 64)
    raw_data = action.get("data")
    data: Mapping[str, Any] = raw_data if isinstance(raw_data, Mapping) else {}
    card = data.get("card") if isinstance(data.get("card"), Mapping) else {}
    before = data.get("listBefore") if isinstance(data.get("listBefore"), Mapping) else {}
    after = data.get("listAfter") if isinstance(data.get("listAfter"), Mapping) else {}
    minimal = {
        "action_id": action_id,
        "action_type": action_type,
        "event_time": when,
        "actor_id": str(action.get("idMemberCreator") or "")[:256],
        "card_id": str(card.get("id") or "")[:256],
        "list_before_id": str(before.get("id") or "")[:256],
        "list_after_id": str(after.get("id") or "")[:256],
    }
    evidence = json.dumps(minimal, ensure_ascii=False, separators=(",", ":"))
    if len(evidence.encode("utf-8")) > MAX_ACTION_BYTES:
        raise ValueError("event evidence too large")
    return action_id, action_type, when, evidence


def append_batch(
    conn: sqlite3.Connection,
    board_id: str,
    actions: Iterable[Mapping[str, Any]],
    *,
    completed_checkpoint: str | None = None,
) -> AppendOutcome:
    """Commit events and a *fully validated* checkpoint in one transaction.

    `completed_checkpoint` is supplied ONLY after the fetching adapter proves
    its pagination window was collected completely. Partial/failed polling
    must not move the checkpoint. Checkpoint format is opaque to this module.
    """
    _required(board_id, "board_id")
    rows = list(actions)
    if len(rows) > MAX_EVENTS_BATCH:
        raise ValueError("batch exceeds limit")
    normalized = [normalize_action(a) for a in rows]  # validate before side effects
    if completed_checkpoint is not None:
        _required(completed_checkpoint, "completed_checkpoint", 512)
    if conn.in_transaction:
        raise RuntimeError("append_batch requires a connection outside a transaction")
    # Explicit BEGIN/commit to keep events + checkpoint atomic.
    inserted = 0
    try:
        conn.execute("BEGIN IMMEDIATE")
        for action_id, kind, when, evidence in normalized:
            result = conn.execute(
                "INSERT OR IGNORE INTO trello_activity_event "
                "(board_id,action_id,action_type,event_time,evidence_json) "
                "VALUES (?,?,?,?,?)",
                (board_id, action_id, kind, when, evidence),
            )
            inserted += result.rowcount
        if completed_checkpoint is not None:
            conn.execute(
                "INSERT INTO trello_activity_checkpoint(board_id,cursor) VALUES (?,?) "
                "ON CONFLICT(board_id) DO UPDATE SET cursor=excluded.cursor, "
                "updated_at=CURRENT_TIMESTAMP",
                (board_id, completed_checkpoint),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return AppendOutcome(inserted, len(normalized) - inserted, completed_checkpoint)


def load_checkpoint(conn: sqlite3.Connection, board_id: str) -> str | None:
    row = conn.execute(
        "SELECT cursor FROM trello_activity_checkpoint WHERE board_id=?",
        (_required(board_id, "board_id"),),
    ).fetchone()
    return row[0] if row else None


def read_events(conn: sqlite3.Connection, board_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
    if not isinstance(limit, int) or not 1 <= limit <= 250:
        raise ValueError("invalid limit")
    rows = conn.execute(
        "SELECT evidence_json FROM trello_activity_event WHERE board_id=? "
        "ORDER BY event_time DESC, action_id DESC LIMIT ?",
        (_required(board_id, "board_id"), limit),
    ).fetchall()
    return [json.loads(row[0]) for row in rows]

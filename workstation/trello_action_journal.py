"""Reference implementation: durable, append-only Trello action evidence.

Not yet integrated into Hermes Work. Designed to use an existing trusted
SQLite connection, not to create a parallel source of truth for tasks.
No network calls, LLM calls, agent jobs, or outbound effects occur here.

Integration must select the authorized canonical event database connection;
this file deliberately does not guess the project's database path.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

MAX_ACTION_BYTES = 8192
MAX_EVENTS_BATCH = 2000


@dataclass(frozen=True)
class AppendOutcome:
    inserted: int
    duplicates: int
    checkpoint: str | None


def install_schema(conn: sqlite3.Connection) -> None:
    """Idempotent. Caller controls migration ownership and database choice."""
    if conn.in_transaction:
        raise RuntimeError("install_schema requires no active transaction")
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


def _safe_object_id(value: Any) -> str:
    """Untrusted nested action fields must never become persisted free text."""
    return value if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{2,64}", value) else ""


def normalize_action(action: Mapping[str, Any]) -> tuple[str, str, str, str]:
    """Only retain a bounded allowlist of metadata; never persist raw comments.

    A summary Bot must separately retrieve authorized text when required.
    This minimizes sensitive data and prompt-injection propagation.
    """
    action_id = _required(action.get("id"), "action_id")
    action_type = _required(action.get("type"), "action_type", 128)
    when_raw = _required(action.get("date"), "event_time", 64)
    try:
        stamp = datetime.fromisoformat(when_raw.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError
        when = stamp.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    except ValueError:
        raise ValueError("invalid event_time") from None
    raw_data = action.get("data")
    data: Mapping[str, Any] = raw_data if isinstance(raw_data, Mapping) else {}
    card = data.get("card") if isinstance(data.get("card"), Mapping) else {}
    before = data.get("listBefore") if isinstance(data.get("listBefore"), Mapping) else {}
    after = data.get("listAfter") if isinstance(data.get("listAfter"), Mapping) else {}
    minimal = {
        "source": "trello_rest_board_actions_v1",
        "action_id": action_id,
        "action_type": action_type,
        "event_time": when,
        "actor_id": _safe_object_id(action.get("idMemberCreator")),
        "card_id": _safe_object_id(card.get("id")),
        "list_before_id": _safe_object_id(before.get("id")),
        "list_after_id": _safe_object_id(after.get("id")),
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
                "updated_at=CURRENT_TIMESTAMP "
                "WHERE excluded.cursor > trello_activity_checkpoint.cursor",
                (board_id, completed_checkpoint),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return AppendOutcome(inserted, len(normalized) - inserted, load_checkpoint(conn, board_id))


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
    return [{"board_id": board_id, **json.loads(row[0])} for row in rows]



def poll_board_actions(
    client: Any,
    conn: sqlite3.Connection,
    board: str,
    *,
    page_size: int = 100,
    max_pages: int = 20,
) -> AppendOutcome:
    """Fetch a full bounded Trello action window, then atomically publish events and cursor.

    Caller owns the existing canonical SQLite connection and schema migration.
    Never dispatch partial pages or advance cursor on network/validation failure.
    """
    from workstation.prefabs.trello import TrelloAccessError, _board_id

    board_id = _board_id(board)
    if type(page_size) is not int or not 1 <= page_size <= 100:
        raise ValueError("invalid page_size (1..100)")
    if type(max_pages) is not int or not 1 <= max_pages <= 20:
        raise ValueError("invalid max_pages (1..20)")
    if conn.in_transaction:
        raise RuntimeError("poll_board_actions requires no active transaction")
    prior = load_checkpoint(conn, board_id)
    since = prior or None
    before = None
    seen_cursors: set[str] = set()
    actions: list[Mapping[str, Any]] = []
    newest_id: str | None = None

    for _ in range(max_pages):
        page = client.board_actions(board_id, before=before, since=since, limit=page_size)
        if not isinstance(page, list):
            raise TrelloAccessError("unexpected action page")
        if len(page) > page_size:
            raise TrelloAccessError("action page exceeds requested bound")
        if not page:
            break
        # Refuse unstable cursor progress instead of silently losing an action.
        current = [normalize_action(row) for row in page]
        ids = [row[0] for row in current]
        if any(ids[i] <= ids[i + 1] for i in range(len(ids) - 1)):
            raise TrelloAccessError("action page order is not newest-first")
        if before is not None and ids[0] >= before:
            raise TrelloAccessError("action cursor did not advance")
        if newest_id is None:
            newest_id = ids[0]
        actions.extend(page)
        next_before = ids[-1]
        if next_before in seen_cursors or next_before == before:
            raise TrelloAccessError("repeated action cursor")
        seen_cursors.add(next_before)
        before = next_before
        if len(page) < page_size:
            break
    else:
        raise TrelloAccessError("action window exceeds bounded pagination limit")

    if not actions:
        return AppendOutcome(0, 0, prior)
    return append_batch(conn, board_id, actions, completed_checkpoint=newest_id)


def poll_board_actions_into_kanban(
    client: Any,
    board: str,
    *,
    kanban_board: str | None = None,
    page_size: int = 100,
    max_pages: int = 20,
) -> AppendOutcome:
    """Opt-in entrypoint using the *existing* Hermes canonical Kanban DB resolver.

    This is not a scheduler and never starts work or performs Trello PUT/POST/DELETE.
    """
    from workstation.kanban import WorkstationKanbanBridge

    conn = WorkstationKanbanBridge(board=kanban_board).get_connection()
    try:
        install_schema(conn)
        return poll_board_actions(client, conn, board, page_size=page_size, max_pages=max_pages)
    finally:
        conn.close()


def read_events_for_day(
    conn: sqlite3.Connection, board_id: str, day: str, *, limit: int = 100,
) -> list[dict[str, Any]]:
    """Metadata-only day query in UTC; no comment bodies, desc or raw actions."""
    from datetime import date as date_type
    try:
        if date_type.fromisoformat(day).isoformat() != day:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("invalid UTC day") from None
    if type(limit) is not int or not 1 <= limit <= 250:
        raise ValueError("invalid limit")
    rows = conn.execute(
        "SELECT evidence_json FROM trello_activity_event "
        "WHERE board_id=? AND event_time>=? AND event_time<? "
        "ORDER BY event_time DESC, action_id DESC LIMIT ?",
        (_required(board_id, "board_id"), day + "T00:00:00.000Z",
         date_type.fromordinal(date_type.fromisoformat(day).toordinal() + 1).isoformat() + "T00:00:00.000Z",
         limit),
    ).fetchall()
    return [{"board_id": board_id, **json.loads(row[0])} for row in rows]

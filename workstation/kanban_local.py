"""Independent, local-first Workstation board. No imports from Hermes Kanban.

Agent execution is deliberately outside this module. A future optional adapter
may link a Workstation card to a Hermes task without sharing its state store.
"""
from __future__ import annotations

import json
import sqlite3
import secrets
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from hermes_constants import get_hermes_home


class BoardError(ValueError):
    pass


class BoardConflict(BoardError):
    pass


def board_path() -> Path:
    return get_hermes_home() / "workstation" / "board.sqlite"


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS boards (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS columns (
  id TEXT PRIMARY KEY, board_id TEXT NOT NULL REFERENCES boards(id),
  name TEXT NOT NULL, position INTEGER NOT NULL,
  UNIQUE(board_id, position)
);
CREATE TABLE IF NOT EXISTS cards (
  id TEXT PRIMARY KEY, board_id TEXT NOT NULL REFERENCES boards(id),
  column_id TEXT NOT NULL REFERENCES columns(id),
  title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
  position INTEGER NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
  UNIQUE(column_id, position)
);
CREATE INDEX IF NOT EXISTS idx_cards_board ON cards(board_id);
CREATE TABLE IF NOT EXISTS card_checklists (
  id TEXT PRIMARY KEY,
  card_id TEXT NOT NULL REFERENCES cards(id),
  title TEXT NOT NULL,
  position INTEGER NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_checklists_card ON card_checklists(card_id, position);
CREATE TABLE IF NOT EXISTS checklist_items (
  id TEXT PRIMARY KEY,
  checklist_id TEXT NOT NULL REFERENCES card_checklists(id),
  body TEXT NOT NULL,
  completed INTEGER NOT NULL DEFAULT 0,
  position INTEGER NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_checklist ON checklist_items(checklist_id, position);
CREATE TABLE IF NOT EXISTS board_activity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  board_id TEXT NOT NULL REFERENCES boards(id),
  card_id TEXT REFERENCES cards(id),
  kind TEXT NOT NULL,
  actor_type TEXT NOT NULL,
  actor_id TEXT,
  session_id TEXT,
  source TEXT,
  payload TEXT,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_board_activity ON board_activity(board_id, id);
CREATE INDEX IF NOT EXISTS idx_card_activity ON board_activity(card_id, id);
CREATE TABLE IF NOT EXISTS card_delegations (
 id TEXT PRIMARY KEY, card_id TEXT NOT NULL REFERENCES cards(id),
 attempt INTEGER NOT NULL, idempotency_key TEXT NOT NULL UNIQUE,
 assignee TEXT, task_id TEXT, state TEXT NOT NULL DEFAULT 'requested',
 task_status TEXT, last_error TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL,
 UNIQUE(card_id,attempt)
);
CREATE INDEX IF NOT EXISTS idx_delegation_card ON card_delegations(card_id,attempt);
"""


def _id(prefix: str) -> str:
    return prefix + "_" + secrets.token_hex(12)


@contextmanager
def database(path: Path | None = None) -> Iterator[sqlite3.Connection]:
    target = path if path is not None else board_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=5, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.executescript(SCHEMA)
        # Additive migration for existing Workstation SQLite files.
        for table, column, definition in (
            ("boards", "archived", "INTEGER NOT NULL DEFAULT 0"),
            ("boards", "revision", "INTEGER NOT NULL DEFAULT 1"),
            ("columns", "archived", "INTEGER NOT NULL DEFAULT 0"),
            ("columns", "revision", "INTEGER NOT NULL DEFAULT 1"),
            ("cards", "archived", "INTEGER NOT NULL DEFAULT 0"),
            ("cards", "metadata_json", "TEXT NOT NULL DEFAULT '{}'"),
        ):
            names = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
            if column not in names:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[None]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()


def _required(value: str, kind: str, max_length: int = 200) -> str:
    value = value.strip()
    if not value or len(value) > max_length:
        raise BoardError(f"{kind} must contain 1-{max_length} characters")
    return value


def _row(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def list_boards(conn: sqlite3.Connection, include_archived: bool = False) -> list[dict]:
    where = "" if include_archived else "WHERE archived=0"
    return [dict(r) for r in conn.execute(f"SELECT * FROM boards {where} ORDER BY created_at, id")]


def create_board(conn: sqlite3.Connection, name: str) -> dict:
    name = _required(name, "Board name")
    board_id = _id("wb")
    with transaction(conn):
        conn.execute("INSERT INTO boards (id,name,created_at) VALUES (?,?,?)", (board_id, name, int(time.time())))
        for position, title in enumerate(("A fazer", "Em andamento", "Concluído")):
            conn.execute(
                "INSERT INTO columns (id,board_id,name,position) VALUES (?,?,?,?)",
                (_id("wc"), board_id, title, position),
            )
    return get_board(conn, board_id)


def get_board(conn: sqlite3.Connection, board_id: str, include_archived: bool = False) -> dict:
    board = _row(conn.execute("SELECT * FROM boards WHERE id=?", (board_id,)).fetchone())
    if board is None or (board["archived"] and not include_archived):
        raise BoardError("Board not found")
    board["columns"] = []
    where = "" if include_archived else "AND archived=0"
    for column in conn.execute(
        f"SELECT * FROM columns WHERE board_id=? {where} ORDER BY position", (board_id,)
    ):
        col = dict(column)
        col["cards"] = [
            dict(card) for card in conn.execute(
                f"SELECT * FROM cards WHERE column_id=? {where} ORDER BY position", (col["id"],)
            )
        ]
        board["columns"].append(col)
    return board


def create_column(conn: sqlite3.Connection, board_id: str, name: str) -> dict:
    name = _required(name, "Column name")
    with transaction(conn):
        if conn.execute("SELECT 1 FROM boards WHERE id=?", (board_id,)).fetchone() is None:
            raise BoardError("Board not found")
        position = conn.execute(
            "SELECT COUNT(*) FROM columns WHERE board_id=?", (board_id,)
        ).fetchone()[0]
        column_id = _id("wc")
        conn.execute("INSERT INTO columns (id,board_id,name,position) VALUES (?,?,?,?)", (column_id, board_id, name, position))
    return _row(conn.execute("SELECT * FROM columns WHERE id=?", (column_id,)).fetchone())


def create_card(conn: sqlite3.Connection, board_id: str, column_id: str, title: str,
                description: str = "") -> dict:
    title = _required(title, "Card title")
    if len(description) > 20000:
        raise BoardError("Description too long")
    with transaction(conn):
        column = conn.execute(
            "SELECT 1 FROM columns WHERE id=? AND board_id=?", (column_id, board_id)
        ).fetchone()
        if column is None:
            raise BoardError("Column not found on this board")
        position = conn.execute(
            "SELECT COUNT(*) FROM cards WHERE column_id=?", (column_id,)
        ).fetchone()[0]
        card_id = _id("wcard")
        now = int(time.time())
        conn.execute(
            "INSERT INTO cards (id,board_id,column_id,title,description,position,created_at,updated_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (card_id, board_id, column_id, title, description, position, now, now),
        )
        _activity(conn, _card_or_error(conn, card_id), "card_created", {"title": title})
    return _row(conn.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone())


def move_card(conn: sqlite3.Connection, card_id: str, column_id: str,
              expected_revision: int) -> dict:
    with transaction(conn):
        card = conn.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
        if card is None:
            raise BoardError("Card not found")
        if card["revision"] != expected_revision:
            raise BoardConflict("Card changed since it was opened")
        target = conn.execute(
            "SELECT 1 FROM columns WHERE id=? AND board_id=?",
            (column_id, card["board_id"]),
        ).fetchone()
        if target is None:
            raise BoardError("Target column not found on this board")
        if card["column_id"] != column_id:
            # Dense ranks avoid UNIQUE conflicts without overwriting another card.
            conn.execute(
                "UPDATE cards SET position=position+1000000 WHERE column_id=?",
                (card["column_id"],),
            )
            for i, row in enumerate(conn.execute(
                "SELECT id FROM cards WHERE column_id=? AND id<>? ORDER BY position, id",
                (card["column_id"], card_id),
            )):
                conn.execute("UPDATE cards SET position=? WHERE id=?", (i, row["id"]))
            position = conn.execute(
                "SELECT COUNT(*) FROM cards WHERE column_id=?", (column_id,)
            ).fetchone()[0]
            conn.execute(
                "UPDATE cards SET column_id=?,position=?,revision=revision+1,updated_at=? WHERE id=?",
                (column_id, position, int(time.time()), card_id),
            )
            _activity(conn, card, "card_moved", {"from": card["column_id"], "to": column_id})
    return _row(conn.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone())


def update_card(conn: sqlite3.Connection, card_id: str, title: str,
                description: str, expected_revision: int) -> dict:
    title = _required(title, "Card title")
    if len(description) > 20000:
        raise BoardError("Description too long")
    with transaction(conn):
        cur = conn.execute(
            "UPDATE cards SET title=?,description=?,revision=revision+1,updated_at=? "
            "WHERE id=? AND revision=?",
            (title, description, int(time.time()), card_id, expected_revision),
        )
        if cur.rowcount != 1:
            if conn.execute("SELECT 1 FROM cards WHERE id=?", (card_id,)).fetchone():
                raise BoardConflict("Card changed since it was opened")
            raise BoardError("Card not found")
        _activity(conn, _card_or_error(conn, card_id), "card_updated")
    return _row(conn.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone())


def _card_or_error(conn: sqlite3.Connection, card_id: str) -> sqlite3.Row:
    card = conn.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone()
    if card is None:
        raise BoardError("Card not found")
    return card


def _activity(conn: sqlite3.Connection, card: sqlite3.Row, kind: str, payload: dict | None = None) -> None:
    # Actor identity is unavailable at this REST boundary; never invent it.
    conn.execute(
        "INSERT INTO board_activity (board_id,card_id,kind,actor_type,payload,created_at) VALUES (?,?,?,?,?,?)",
        (card["board_id"], card["id"], kind, "unknown", json.dumps(payload or {}, ensure_ascii=False), int(time.time())),
    )


def list_checklists(conn: sqlite3.Connection, card_id: str) -> list[dict]:
    _card_or_error(conn, card_id)
    result = [dict(r) for r in conn.execute(
        "SELECT * FROM card_checklists WHERE card_id=? ORDER BY position,id", (card_id,)
    )]
    for checklist in result:
        checklist["items"] = [dict(r) for r in conn.execute(
            "SELECT * FROM checklist_items WHERE checklist_id=? ORDER BY position,id", (checklist["id"],)
        )]
    return result


def get_card_details(conn: sqlite3.Connection, card_id: str) -> dict:
    card = dict(_card_or_error(conn, card_id))
    card["checklists"] = list_checklists(conn, card_id)
    card["metadata"] = json.loads(card["metadata_json"] or "{}")
    card["delegations"] = list_delegations(conn, card_id)
    card["activity"] = []
    for row in conn.execute("SELECT * FROM board_activity WHERE card_id=? ORDER BY id DESC LIMIT 100", (card_id,)):
        event = dict(row)
        event["payload"] = json.loads(event["payload"] or "{}")
        card["activity"].append(event)
    return card


def create_checklist(conn: sqlite3.Connection, card_id: str, title: str) -> dict:
    title = _required(title, "Checklist title")
    with transaction(conn):
        card = _card_or_error(conn, card_id)
        position = conn.execute("SELECT COUNT(*) FROM card_checklists WHERE card_id=?", (card_id,)).fetchone()[0]
        checklist_id, now = _id("wcl"), int(time.time())
        conn.execute("INSERT INTO card_checklists VALUES (?,?,?,?,?,?,?)",
                     (checklist_id, card_id, title, position, 1, now, now))
        _activity(conn, card, "checklist_created", {"checklist_id": checklist_id, "title": title})
    return next(c for c in list_checklists(conn, card_id) if c["id"] == checklist_id)


def create_checklist_item(conn: sqlite3.Connection, checklist_id: str, body: str) -> dict:
    body = _required(body, "Checklist item body", 2000)
    with transaction(conn):
        checklist = conn.execute("SELECT * FROM card_checklists WHERE id=?", (checklist_id,)).fetchone()
        if checklist is None:
            raise BoardError("Checklist not found")
        card = _card_or_error(conn, checklist["card_id"])
        position = conn.execute("SELECT COUNT(*) FROM checklist_items WHERE checklist_id=?", (checklist_id,)).fetchone()[0]
        item_id, now = _id("wci"), int(time.time())
        conn.execute("INSERT INTO checklist_items VALUES (?,?,?,?,?,?,?,?)",
                     (item_id, checklist_id, body, 0, position, 1, now, now))
        _activity(conn, card, "checklist_item_created", {"checklist_id": checklist_id, "item_id": item_id})
    return dict(conn.execute("SELECT * FROM checklist_items WHERE id=?", (item_id,)).fetchone())


def update_checklist_item(conn: sqlite3.Connection, item_id: str, expected_revision: int,
                          body: str | None = None, completed: bool | None = None) -> dict:
    if body is None and completed is None:
        raise BoardError("No changes requested")
    if body is not None:
        body = _required(body, "Checklist item body", 2000)
    with transaction(conn):
        item = conn.execute("SELECT * FROM checklist_items WHERE id=?", (item_id,)).fetchone()
        if item is None:
            raise BoardError("Checklist item not found")
        if item["revision"] != expected_revision:
            raise BoardConflict("Checklist item changed since it was opened")
        checklist = conn.execute("SELECT * FROM card_checklists WHERE id=?", (item["checklist_id"],)).fetchone()
        card = _card_or_error(conn, checklist["card_id"])
        conn.execute(
            "UPDATE checklist_items SET body=?,completed=?,revision=revision+1,updated_at=? WHERE id=?",
            (body if body is not None else item["body"],
             int(completed) if completed is not None else item["completed"], int(time.time()), item_id),
        )
        _activity(conn, card, "checklist_item_updated", {"item_id": item_id, "completed": completed})
    return dict(conn.execute("SELECT * FROM checklist_items WHERE id=?", (item_id,)).fetchone())


def delete_checklist_item(conn: sqlite3.Connection, item_id: str, expected_revision: int) -> bool:
    with transaction(conn):
        item = conn.execute("SELECT * FROM checklist_items WHERE id=?", (item_id,)).fetchone()
        if item is None:
            raise BoardError("Checklist item not found")
        if item["revision"] != expected_revision:
            raise BoardConflict("Checklist item changed since it was opened")
        checklist = conn.execute("SELECT * FROM card_checklists WHERE id=?", (item["checklist_id"],)).fetchone()
        card = _card_or_error(conn, checklist["card_id"])
        conn.execute("DELETE FROM checklist_items WHERE id=?", (item_id,))
        for position, row in enumerate(conn.execute(
                "SELECT id FROM checklist_items WHERE checklist_id=? ORDER BY position,id", (item["checklist_id"],))):
            conn.execute("UPDATE checklist_items SET position=? WHERE id=?", (position, row["id"]))
        _activity(conn, card, "checklist_item_deleted", {"item_id": item_id})
    return True


def delete_checklist(conn: sqlite3.Connection, checklist_id: str, expected_revision: int) -> bool:
    with transaction(conn):
        checklist = conn.execute("SELECT * FROM card_checklists WHERE id=?", (checklist_id,)).fetchone()
        if checklist is None:
            raise BoardError("Checklist not found")
        if checklist["revision"] != expected_revision:
            raise BoardConflict("Checklist changed since it was opened")
        card = _card_or_error(conn, checklist["card_id"])
        conn.execute("DELETE FROM checklist_items WHERE checklist_id=?", (checklist_id,))
        conn.execute("DELETE FROM card_checklists WHERE id=?", (checklist_id,))
        for position, row in enumerate(conn.execute(
                "SELECT id FROM card_checklists WHERE card_id=? ORDER BY position,id", (card["id"],))):
            conn.execute("UPDATE card_checklists SET position=? WHERE id=?", (position, row["id"]))
        _activity(conn, card, "checklist_deleted", {"checklist_id": checklist_id})
    return True


def set_archived(conn: sqlite3.Connection, entity: str, entity_id: str,
                 expected_revision: int, archived: bool) -> dict:
    """Soft archive/restore with CAS. Parent visibility hides descendants, never deletes."""
    tables = {"board": "boards", "column": "columns", "card": "cards"}
    table = tables.get(entity)
    if table is None:
        raise BoardError("Unsupported archive entity")
    with transaction(conn):
        row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (entity_id,)).fetchone()
        if row is None:
            raise BoardError(f"{entity.capitalize()} not found")
        if row["revision"] != expected_revision:
            raise BoardConflict(f"{entity.capitalize()} changed since it was opened")
        if bool(row["archived"]) != archived:
            cur = conn.execute(
                f"UPDATE {table} SET archived=?,revision=revision+1 WHERE id=? AND revision=?",
                (int(archived), entity_id, expected_revision),
            )
            if cur.rowcount != 1:
                raise BoardConflict("Concurrent archive update")
            board_id = row["id"] if entity == "board" else row["board_id"]
            card_id = entity_id if entity == "card" else None
            payload = json.dumps({"entity": entity, "id": entity_id}, ensure_ascii=False)
            conn.execute(
                "INSERT INTO board_activity "
                "(board_id,card_id,kind,actor_type,payload,created_at) VALUES (?,?,?,?,?,?)",
                (board_id, card_id, f"{entity}_{'archived' if archived else 'restored'}",
                 "unknown", payload, int(time.time())),
            )
    return dict(conn.execute(f"SELECT * FROM {table} WHERE id=?", (entity_id,)).fetchone())


def _reindex_positions(conn: sqlite3.Connection, table: str, ids: list[str]) -> None:
    # All negative positions are temporary; permanent positions remain dense and nonnegative.
    for position, item_id in enumerate(ids):
        conn.execute(f"UPDATE {table} SET position=? WHERE id=?", (-position - 1, item_id))
    for position, item_id in enumerate(ids):
        conn.execute(f"UPDATE {table} SET position=? WHERE id=?", (position, item_id))


def reorder_column(conn: sqlite3.Connection, column_id: str,
                   expected_revision: int, before_id: str | None = None) -> dict:
    with transaction(conn):
        column = conn.execute("SELECT * FROM columns WHERE id=?", (column_id,)).fetchone()
        if column is None:
            raise BoardError("Column not found")
        if column["revision"] != expected_revision:
            raise BoardConflict("Column changed since it was opened")
        ids = [r["id"] for r in conn.execute(
            "SELECT id FROM columns WHERE board_id=? ORDER BY position,id", (column["board_id"],)
        ) if r["id"] != column_id]
        if before_id is not None and before_id not in ids:
            raise BoardError("Target column not found in board")
        ids.insert(ids.index(before_id) if before_id else len(ids), column_id)
        _reindex_positions(conn, "columns", ids)
        conn.execute("UPDATE columns SET revision=revision+1 WHERE id=?", (column_id,))
        conn.execute(
            "INSERT INTO board_activity (board_id,kind,actor_type,payload,created_at) VALUES (?,?,?,?,?)",
            (column["board_id"], "column_reordered", "unknown", json.dumps({"column_id": column_id}), int(time.time())),
        )
    return dict(conn.execute("SELECT * FROM columns WHERE id=?", (column_id,)).fetchone())


def reorder_card(conn: sqlite3.Connection, card_id: str, target_column_id: str,
                 expected_revision: int, before_id: str | None = None) -> dict:
    with transaction(conn):
        card = _card_or_error(conn, card_id)
        if card["revision"] != expected_revision:
            raise BoardConflict("Card changed since it was opened")
        target = conn.execute("SELECT * FROM columns WHERE id=?", (target_column_id,)).fetchone()
        if target is None or target["board_id"] != card["board_id"]:
            raise BoardError("Target column not found in board")
        old_column_id = card["column_id"]
        destination = [r["id"] for r in conn.execute(
            "SELECT id FROM cards WHERE column_id=? ORDER BY position,id", (target_column_id,)
        ) if r["id"] != card_id]
        if before_id is not None and before_id not in destination:
            raise BoardError("Anchor card not found in destination column")
        destination.insert(destination.index(before_id) if before_id else len(destination), card_id)
        if old_column_id != target_column_id:
            conn.execute("UPDATE cards SET column_id=?,position=? WHERE id=?",
                         (target_column_id, -1000000000, card_id))
            source = [r["id"] for r in conn.execute(
                "SELECT id FROM cards WHERE column_id=? ORDER BY position,id", (old_column_id,)
            )]
            _reindex_positions(conn, "cards", source)
        _reindex_positions(conn, "cards", destination)
        conn.execute("UPDATE cards SET revision=revision+1,updated_at=? WHERE id=?",
                     (int(time.time()), card_id))
        _activity(conn, card, "card_reordered", {"from": old_column_id, "to": target_column_id, "before": before_id})
    return dict(conn.execute("SELECT * FROM cards WHERE id=?", (card_id,)).fetchone())


def reorder_checklist(conn: sqlite3.Connection, checklist_id: str,
                      expected_revision: int, before_id: str | None = None) -> dict:
    with transaction(conn):
        checklist = conn.execute("SELECT * FROM card_checklists WHERE id=?", (checklist_id,)).fetchone()
        if checklist is None:
            raise BoardError("Checklist not found")
        if checklist["revision"] != expected_revision:
            raise BoardConflict("Checklist changed since it was opened")
        ids = [r["id"] for r in conn.execute(
            "SELECT id FROM card_checklists WHERE card_id=? ORDER BY position,id", (checklist["card_id"],)
        ) if r["id"] != checklist_id]
        if before_id is not None and before_id not in ids:
            raise BoardError("Target checklist not found in card")
        ids.insert(ids.index(before_id) if before_id else len(ids), checklist_id)
        _reindex_positions(conn, "card_checklists", ids)
        conn.execute("UPDATE card_checklists SET revision=revision+1,updated_at=? WHERE id=?",
                     (int(time.time()), checklist_id))
        _activity(conn, _card_or_error(conn, checklist["card_id"]), "checklist_reordered",
                  {"checklist_id": checklist_id, "before": before_id})
    return dict(conn.execute("SELECT * FROM card_checklists WHERE id=?", (checklist_id,)).fetchone())


def reorder_checklist_item(conn: sqlite3.Connection, item_id: str,
                           expected_revision: int, before_id: str | None = None) -> dict:
    with transaction(conn):
        item = conn.execute("SELECT * FROM checklist_items WHERE id=?", (item_id,)).fetchone()
        if item is None:
            raise BoardError("Checklist item not found")
        if item["revision"] != expected_revision:
            raise BoardConflict("Checklist item changed since it was opened")
        ids = [r["id"] for r in conn.execute(
            "SELECT id FROM checklist_items WHERE checklist_id=? ORDER BY position,id", (item["checklist_id"],)
        ) if r["id"] != item_id]
        if before_id is not None and before_id not in ids:
            raise BoardError("Target item not found in checklist")
        ids.insert(ids.index(before_id) if before_id else len(ids), item_id)
        _reindex_positions(conn, "checklist_items", ids)
        conn.execute("UPDATE checklist_items SET revision=revision+1,updated_at=? WHERE id=?",
                     (int(time.time()), item_id))
        checklist = conn.execute("SELECT card_id FROM card_checklists WHERE id=?", (item["checklist_id"],)).fetchone()
        _activity(conn, _card_or_error(conn, checklist["card_id"]), "checklist_item_reordered",
                  {"item_id": item_id, "before": before_id})
    return dict(conn.execute("SELECT * FROM checklist_items WHERE id=?", (item_id,)).fetchone())


def update_card_metadata(conn: sqlite3.Connection, card_id: str,
                         expected_revision: int, metadata: dict) -> dict:
    """Replace card JSON metadata atomically; unknown actors are not impersonated."""
    if not isinstance(metadata, dict) or any(not isinstance(k, str) or not k or len(k) > 128 for k in metadata):
        raise BoardError("Metadata must be an object with non-empty keys up to 128 characters")
    try:
        encoded = json.dumps(metadata, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    except (ValueError, TypeError, OverflowError) as exc:
        raise BoardError("Metadata must contain valid JSON values") from exc
    if len(encoded.encode("utf-8")) > 16_384:
        raise BoardError("Metadata exceeds the 16 KiB limit")
    with transaction(conn):
        card = _card_or_error(conn, card_id)
        if card["revision"] != expected_revision:
            raise BoardConflict("Card changed since it was opened")
        conn.execute("UPDATE cards SET metadata_json=?,revision=revision+1,updated_at=? WHERE id=?",
                     (encoded, int(time.time()), card_id))
        _activity(conn, card, "card_metadata_updated", {"keys": sorted(metadata)})
    return get_card_details(conn, card_id)


def list_delegations(conn: sqlite3.Connection, card_id: str) -> list[dict]:
    return [dict(row) for row in conn.execute(
        "SELECT * FROM card_delegations WHERE card_id=? ORDER BY attempt,id", (card_id,))]


def begin_delegation(conn: sqlite3.Connection, card_id: str,
                     expected_revision: int, assignee: str | None = None,
                     new_attempt: bool = False) -> dict:
    """Durable intent only; never schedules an agent task by itself."""
    if assignee is not None:
        assignee = assignee.strip() or None
        if assignee is not None and len(assignee) > 100:
            raise BoardError("Assignee too long")
    with transaction(conn):
        card = _card_or_error(conn, card_id)
        if card["archived"]:
            raise BoardError("Cannot delegate archived card")
        latest = conn.execute(
            "SELECT * FROM card_delegations WHERE card_id=? ORDER BY attempt DESC LIMIT 1",
            (card_id,)).fetchone()
        if latest and (not new_attempt or latest["state"] not in {"done", "archived", "failed", "cancelled"}):
            if latest["assignee"] != assignee:
                raise BoardConflict("Existing delegation has another assignee")
            return dict(latest)
        if card["revision"] != expected_revision:
            raise BoardConflict("Card changed since it was opened")
        attempt = (latest["attempt"] if latest else 0) + 1
        key = f"workstation-card:{card_id}:attempt:{attempt}"
        delegation_id, now = _id("wdg"), int(time.time())
        conn.execute(
            "INSERT INTO card_delegations (id,card_id,attempt,idempotency_key,assignee,created_at,updated_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (delegation_id, card_id, attempt, key, assignee, now, now))
        _activity(conn, card, "delegation_requested", {"attempt": attempt})
    return dict(conn.execute("SELECT * FROM card_delegations WHERE id=?", (delegation_id,)).fetchone())


def link_delegation(conn: sqlite3.Connection, delegation_id: str, task_id: str) -> dict:
    if not task_id or len(task_id) > 128:
        raise BoardError("Invalid official task ID")
    with transaction(conn):
        row = conn.execute("SELECT * FROM card_delegations WHERE id=?", (delegation_id,)).fetchone()
        if row is None:
            raise BoardError("Delegation not found")
        if row["task_id"] and row["task_id"] != task_id:
            raise BoardConflict("Delegation already linked to another task")
        if not row["task_id"]:
            conn.execute("UPDATE card_delegations SET task_id=?,state='delegated',last_error=NULL,updated_at=? WHERE id=?",
                         (task_id, int(time.time()), delegation_id))
            _activity(conn, _card_or_error(conn, row["card_id"]), "delegation_linked",
                      {"task_id": task_id, "attempt": row["attempt"]})
    return dict(conn.execute("SELECT * FROM card_delegations WHERE id=?", (delegation_id,)).fetchone())


def record_delegation_error(conn: sqlite3.Connection, delegation_id: str, error: str) -> None:
    with transaction(conn):
        row = conn.execute("SELECT id FROM card_delegations WHERE id=?", (delegation_id,)).fetchone()
        if row is not None:
            conn.execute("UPDATE card_delegations SET last_error=?,updated_at=? WHERE id=? AND task_id IS NULL",
                         (error[:200], int(time.time()), delegation_id))


def reconcile_delegation(conn: sqlite3.Connection, delegation_id: str,
                         status: str) -> dict:
    """Read-only upstream task projection, persisted in our own SQLite."""
    if status not in {"triage", "todo", "ready", "running", "blocked", "done", "archived"}:
        raise BoardError("Invalid official task status")
    state = {"done": "done", "archived": "archived", "blocked": "waiting"}.get(status, "delegated")
    with transaction(conn):
        row = conn.execute("SELECT * FROM card_delegations WHERE id=?", (delegation_id,)).fetchone()
        if row is None or not row["task_id"]:
            raise BoardError("Linked delegation not found")
        if row["task_status"] != status:
            conn.execute("UPDATE card_delegations SET task_status=?,state=?,updated_at=? WHERE id=?",
                         (status, state, int(time.time()), delegation_id))
            _activity(conn, _card_or_error(conn, row["card_id"]), "delegation_synced",
                      {"task_id": row["task_id"], "status": status})
    return dict(conn.execute("SELECT * FROM card_delegations WHERE id=?", (delegation_id,)).fetchone())

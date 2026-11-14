"""Versioned local edits over imported read-only snapshots.

Imported ACIRV/Trello files remain immutable. Edits by humans/agents are
persisted in their own SQLite journal and projected onto read views. This is
the local edit queue, NOT permission to send effects to Trello.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workstation import acirv_datasets as sources


def path(home: Path | None = None) -> Path:
    return sources.directory(home) / "local-edits.sqlite"


def _connect(home: Path | None = None) -> sqlite3.Connection:
    target = path(home)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    # Use SQLite rollback journal for new local edit stores. On older bundled SQLite,
    # WAL reset races can corrupt concurrently opened databases; do not force WAL.
    # Existing databases retain their current journal mode (no live conversion).
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS edits(
            dataset TEXT NOT NULL, table_name TEXT NOT NULL, record_id TEXT NOT NULL,
            original_json TEXT NOT NULL, changes_json TEXT NOT NULL,
            revision INTEGER NOT NULL, updated_at TEXT NOT NULL, actor TEXT NOT NULL,
            PRIMARY KEY(dataset, table_name, record_id));
        CREATE TABLE IF NOT EXISTS edit_events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset TEXT NOT NULL, table_name TEXT NOT NULL, record_id TEXT NOT NULL,
            revision INTEGER NOT NULL, change_json TEXT NOT NULL,
            actor TEXT NOT NULL, updated_at TEXT NOT NULL);
    """)
    return conn


def _load(conn: sqlite3.Connection, dataset: str, table: str, record_id: str):
    return conn.execute(
        "SELECT * FROM edits WHERE dataset=? AND table_name=? AND record_id=?",
        (dataset, table, str(record_id)),
    ).fetchone()


def project_record(home: Path | None, dataset: str, table: str,
                   record: dict[str, Any], primary_key: str) -> tuple[dict, int, list[str]]:
    if primary_key not in record:
        return record, 0, []
    db_path = path(home)
    if not db_path.is_file():
        return record, 0, []
    with closing(_connect(home)) as conn:
        edit = _load(conn, dataset, table, str(record[primary_key]))
    if not edit:
        return record, 0, []
    original = json.loads(edit["original_json"])
    changes = json.loads(edit["changes_json"])
    conflicts = [key for key, before in original.items() if record.get(key) != before]
    return {**record, **changes}, edit["revision"], conflicts


def project_page(home: Path | None, dataset: str, table: str,
                 rows: list[dict], primary_key: str) -> list[dict]:
    db_path = path(home)
    if not rows or not db_path.is_file():
        return rows
    with closing(_connect(home)) as conn:
        edits = {e["record_id"]: json.loads(e["changes_json"]) for e in conn.execute(
            "SELECT record_id, changes_json FROM edits WHERE dataset=? AND table_name=?",
            (dataset, table),
        )}
    return [{**r, **{k: v for k, v in edits.get(str(r.get(primary_key)), {}).items() if k in r}}
            for r in rows]


def update_record(home: Path | None, dataset: str, table: str, record_id: str, *,
                  changes: dict[str, Any], expected_revision: int, actor: str) -> dict:
    """Patch an imported row via isolated overlay. CAS revision is mandatory."""
    if type(expected_revision) is not int or expected_revision < 0:
        raise ValueError("expected_revision must be 0 for new edit or latest revision")
    if actor not in {"human", "agent"}:
        raise ValueError("Unknown editor")
    if not isinstance(changes, dict) or not changes:
        raise ValueError("At least one changed field is required")
    if len(json.dumps(changes, ensure_ascii=False, allow_nan=False).encode("utf-8")) > 65536:
        raise ValueError("Changes exceed 64 KiB")
    if any(not isinstance(v, (str, int, float, type(None))) or isinstance(v, bool)
           for v in changes.values()):
        raise ValueError("Only scalar string, numeric or null values can be edited")
    with closing(sources._connection(home, dataset)) as origin_conn:
        quoted_table = sources._table(origin_conn, table)
        cols = sources._columns(origin_conn, table)
        pk = next((c["name"] for c in cols if c["primary_key"]), None)
        if not pk:
            raise ValueError("Cannot edit table without a primary key")
        existing_cols = {c["name"] for c in cols}
        fks = {row["from"] for row in origin_conn.execute(f"PRAGMA foreign_key_list({quoted_table})")}
        if any(k not in existing_cols or k == pk or k in fks for k in changes):
            raise ValueError("Unknown, primary-key or foreign-key field")
        row = origin_conn.execute(
            f'SELECT * FROM {quoted_table} WHERE "{pk}"=?', (record_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Record not found")
        original_row = sources._row(row)
    with closing(_connect(home)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            previous = _load(conn, dataset, table, record_id)
            rev = int(previous["revision"]) if previous else 0
            if rev != expected_revision:
                conn.rollback()
                return {"ok": False, "error": "revision_conflict", "current_revision": rev}
            before = json.loads(previous["original_json"]) if previous else {}
            overlay = json.loads(previous["changes_json"]) if previous else {}
            if any(original_row.get(k) != v for k, v in before.items()):
                conn.rollback()
                return {"ok": False, "error": "source_changed",
                        "fields": [k for k, v in before.items() if original_row.get(k) != v]}
            for field, value in changes.items():
                before.setdefault(field, original_row[field])
                if value == before[field]:
                    overlay.pop(field, None)
                    before.pop(field, None)
                else:
                    overlay[field] = value
            now = datetime.now(timezone.utc).isoformat()
            new_rev = rev + 1
            if previous:
                conn.execute(
                    "UPDATE edits SET original_json=?,changes_json=?,revision=?,updated_at=?,actor=? "
                    "WHERE dataset=? AND table_name=? AND record_id=?",
                    (json.dumps(before, ensure_ascii=False), json.dumps(overlay, ensure_ascii=False),
                     new_rev, now, actor, dataset, table, record_id),
                )
            else:
                conn.execute(
                    "INSERT INTO edits VALUES (?,?,?,?,?,?,?,?)",
                    (dataset, table, record_id, json.dumps(before, ensure_ascii=False),
                     json.dumps(overlay, ensure_ascii=False), new_rev, now, actor),
                )
            conn.execute(
                "INSERT INTO edit_events(dataset,table_name,record_id,revision,change_json,actor,updated_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (dataset, table, record_id, new_rev,
                 json.dumps(changes, ensure_ascii=False), actor, now),
            )
            conn.commit()
            return {"ok": True, "status": "saved", "revision": new_rev,
                    "dataset": dataset, "table": table, "record_id": record_id,
                    "pending_external_sync": True}
        except Exception:
            conn.rollback()
            raise

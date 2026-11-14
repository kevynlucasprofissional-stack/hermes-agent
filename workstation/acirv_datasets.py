"""Read-only relational datasets for the Hermes Workstation Database.

Original ACIRV SQLite files are snapshotted by an explicit import command.
The board/card store remains untouched. Dataset IDs and SQL identifiers are
validated against the local catalog and SQLite schema; no user SQL is accepted.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home


FILENAMES = {"tarefas": "tarefas.sqlite", "whatsapp": "whatsapp.sqlite", "trello": "trello.sqlite"}
DEFAULT_VIEWS = [
    {"id": "tarefas", "label": "Tarefas ACIRV", "dataset": "tarefas", "table": "tasks",
     "fields": ["id", "code", "title", "status", "priority", "owner", "due_at"], "group_by": "status"},
    {"id": "pendencias", "label": "Pendências WhatsApp", "dataset": "whatsapp", "table": "pendencies",
     "fields": ["id", "title", "status", "priority", "due_date"], "group_by": "status"},
    {"id": "contatos", "label": "Contatos WhatsApp", "dataset": "whatsapp", "table": "contacts",
     "fields": ["id", "display_name", "type", "phone_number"], "group_by": "type"},
    {"id": "conversas", "label": "Conversas WhatsApp", "dataset": "whatsapp", "table": "conversations",
     "fields": ["id", "contact_id", "unread_count", "last_message_at"], "group_by": None},
    {"id": "mensagens", "label": "Mensagens WhatsApp", "dataset": "whatsapp", "table": "messages",
     "fields": ["id", "conversation_id", "direction", "content_text", "timestamp"], "group_by": "direction"},
]
REQUIRED = {"tarefas": {"tasks", "task_links", "task_events"}, "whatsapp": {"contacts", "conversations", "messages", "pendencies"}}


def directory(home: Path | None = None) -> Path:
    return (Path(home) if home is not None else get_hermes_home()) / "workstation" / "datasets"


def _dataset_path(home: Path | None, dataset: str) -> Path:
    if dataset not in FILENAMES:
        raise ValueError("Unknown dataset")
    return directory(home) / FILENAMES[dataset]


def _tables(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )}


def _table(conn: sqlite3.Connection, name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", name) or name not in _tables(conn):
        raise ValueError("Unknown table")
    return '"' + name + '"'


def _columns(conn: sqlite3.Connection, table: str) -> list[dict]:
    return [{"name": row[1], "type": row[2], "primary_key": bool(row[5])}
            for row in conn.execute(f"PRAGMA table_info({_table(conn, table)})")]


def _connection(home: Path | None, dataset: str) -> sqlite3.Connection:
    path = _dataset_path(home, dataset)
    if not path.is_file():
        raise ValueError("Dataset not imported")
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    return conn


def _safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return f"[binary: {len(value)} bytes]"
    return value


def _row(row: sqlite3.Row) -> dict:
    return {key: _safe(row[key]) for key in row.keys()}


def _digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _inspect(conn: sqlite3.Connection) -> dict:
    if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
        raise ValueError("SQLite integrity check failed")
    result = {}
    for name in sorted(_tables(conn)):
        result[name] = conn.execute(f"SELECT COUNT(*) FROM {_table(conn, name)}").fetchone()[0]
    return {"rows": result,
            "foreign_key_violations": len(conn.execute("PRAGMA foreign_key_check").fetchall())}


def import_sources(sources: dict[str, Path], home: Path | None = None) -> dict:
    """Consistent SQLite online backups; do not change source DBs or board.sqlite.

    Two snapshots are validated before replacing any destination. Existing
    destination versions are retained on disk as .previous backups on update.
    This operation is deliberately manual, never triggered by a GET endpoint.
    """
    if set(sources) != {"tarefas", "whatsapp"}:
        raise ValueError("Both named sources are required")
    dest_dir = directory(home)
    dest_dir.mkdir(parents=True, exist_ok=True)
    prepared: dict[str, tuple[Path, dict]] = {}
    try:
        for name, raw_path in sources.items():
            path = Path(raw_path)
            if not path.is_file():
                raise ValueError(f"Missing {name} source")
            fd, tmp_name = tempfile.mkstemp(prefix=name + "-", suffix=".sqlite", dir=dest_dir)
            os.close(fd)
            temp = Path(tmp_name)
            prepared[name] = (temp, {})  # Ensure failure cleanup before inspecting any private rows.
            with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=10)) as original:
                with closing(sqlite3.connect(temp)) as copied:
                    original.backup(copied)
            with closing(sqlite3.connect(temp)) as check:
                check.row_factory = sqlite3.Row
                info = _inspect(check)
                if not REQUIRED[name].issubset(_tables(check)):
                    raise ValueError(f"Incompatible {name} database schema")
            prepared[name] = temp, info
        # A manual source refresh must never silently erase a verified Trello recovery.
        task_target = _dataset_path(home, "tarefas")
        if task_target.is_file() and _digest(task_target) != _digest(prepared["tarefas"][0]):
            with closing(sqlite3.connect(task_target.as_uri() + "?mode=ro", uri=True)) as existing:
                if ("trello_recovery_evidence" in _tables(existing)
                        and existing.execute("SELECT COUNT(*) FROM trello_recovery_evidence").fetchone()[0]):
                    raise ValueError("Tasks snapshot contains recovered Trello history; explicit reconciliation required")
        result = {}
        for name, (temp, info) in prepared.items():
            target = _dataset_path(home, name)
            if target.exists() and _digest(target) == _digest(temp):
                info["status"] = "unchanged"
            else:
                if target.exists():
                    previous = target.with_suffix(".previous.sqlite")
                    with closing(sqlite3.connect(target)) as before:
                        with closing(sqlite3.connect(previous)) as backup:
                            before.backup(backup)
                os.replace(temp, target)
                info["status"] = "imported"
            result[name] = info
        views_path = dest_dir / "views.json"
        if not views_path.exists():
            views_path.write_text(json.dumps(DEFAULT_VIEWS, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    finally:
        for temp, _info in prepared.values():
            temp.unlink(missing_ok=True)


def list_datasets(home: Path | None = None) -> dict:
    result = []
    for key in FILENAMES:
        if not _dataset_path(home, key).is_file():
            continue
        with closing(_connection(home, key)) as conn:
            summary = _inspect(conn)
            result.append({"id": key, "writable": True, "write_mode": "local_revisioned_edits", "tables": [
                {"name": table, "count": count} for table, count in summary["rows"].items()],
                "foreign_key_violations": summary["foreign_key_violations"]})
    views_path = directory(home) / "views.json"
    views = json.loads(views_path.read_text(encoding="utf-8")) if views_path.is_file() else DEFAULT_VIEWS
    return {"datasets": result, "views": views}


def list_records(home: Path | None, dataset: str, table: str, *,
                 limit: int = 100, offset: int = 0, columns: list[str] | None = None,
                 status: str | None = None) -> dict:
    if not isinstance(limit, int) or not 1 <= limit <= 500 or not isinstance(offset, int) or offset < 0:
        raise ValueError("Invalid pagination")
    with closing(_connection(home, dataset)) as conn:
        sql_table = _table(conn, table)
        definitions = _columns(conn, table)
        valid = {column["name"] for column in definitions}
        fields = columns if columns is not None else [column["name"] for column in definitions[:8]]
        if not fields or any(field not in valid for field in fields):
            raise ValueError("Unknown column")
        projection = ", ".join('"' + field + '"' for field in fields)
        where = ' WHERE "status"=?' if status is not None else ""
        if status is not None and "status" not in valid:
            raise ValueError("Table has no status column")
        params = [status] if status is not None else []
        total = conn.execute(f"SELECT COUNT(*) FROM {sql_table}{where}", params).fetchone()[0]
        pk = next((col["name"] for col in definitions if col["primary_key"]), definitions[0]["name"])
        records = [_row(row) for row in conn.execute(
            f"SELECT {projection} FROM {sql_table}{where} ORDER BY \"{pk}\" LIMIT ? OFFSET ?",
            [*params, limit, offset],
        )]
        from workstation.dataset_edits import project_page
        records = project_page(home, dataset, table, records, pk)
        return {"dataset": dataset, "table": table, "columns": [d for d in definitions if d["name"] in fields],
                "primary_key": pk, "rows": records, "total": total, "count": len(records),
                "limit": limit, "offset": offset}


def get_record(home: Path | None, dataset: str, table: str, record_id: str) -> dict:
    with closing(_connection(home, dataset)) as conn:
        sql_table = _table(conn, table)
        definition = _columns(conn, table)
        pk = next((c["name"] for c in definition if c["primary_key"]), None)
        if pk is None:
            raise ValueError("Table has no primary key")
        record = conn.execute(
            f'SELECT * FROM {sql_table} WHERE "{pk}"=?', (record_id,)
        ).fetchone()
        if record is None:
            raise ValueError("Record not found")
        data = _row(record)
        from workstation.dataset_edits import project_record
        data, local_revision, source_conflicts = project_record(home, dataset, table, data, pk)
        links: list[dict] = []
        existing = set()
        def add(target_dataset: str, target_table: str, target_id: Any, relation: str):
            if target_id is None:
                return
            key = (target_dataset, target_table, str(target_id))
            if key in existing:
                return
            existing.add(key)
            try:
                with closing(_connection(home, target_dataset)) as target_conn:
                    target_sql = _table(target_conn, target_table)
                    present = target_conn.execute(
                        f'SELECT 1 FROM {target_sql} WHERE id=?', (target_id,)
                    ).fetchone() is not None
            except (ValueError, sqlite3.OperationalError):
                present = False
            links.append({"dataset": target_dataset, "table": target_table, "id": target_id,
                          "relation": relation, "exists": present})
        for fk in conn.execute(f"PRAGMA foreign_key_list({sql_table})"):
            add(dataset, fk["table"], data.get(fk["from"]), fk["from"])
        if dataset == "tarefas" and table == "tasks":
            add("whatsapp", "contacts", data.get("wa_contact_id"), "wa_contact_id")
            add("whatsapp", "conversations", data.get("wa_conversation_id"), "wa_conversation_id")
            ref = data.get("source_ref") or ""
            if isinstance(ref, str) and re.fullmatch(r"wa:pend:\d+", ref):
                add("whatsapp", "pendencies", int(ref.split(":")[-1]), "source_ref")
        if dataset == "whatsapp" and table == "pendencies":
            with closing(_connection(home, "tarefas")) as task_conn:
                for item in task_conn.execute(
                    "SELECT id FROM tasks WHERE source_ref=? LIMIT 100", (f'wa:pend:{record_id}',)
                ):
                    add("tarefas", "tasks", item[0], "source_ref")
        return {"dataset": dataset, "table": table, "primary_key": pk,
                "record": data, "relations": links, "local_revision": local_revision,
                "pending_external_sync": local_revision > 0, "source_conflict_fields": source_conflicts}

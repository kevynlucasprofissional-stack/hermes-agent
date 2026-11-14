"""Profile-scoped writable agent records in the Hermes Workstation dataset directory.

This is NOT a writer for imported ACIRV/Trello snapshots or upstream Kanban.
The caller must supply a stable namespace/key and use optimistic revisions.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import stat
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home

_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,119}$")
_SECRET_FIELD = re.compile(
    r"(^|[_-])(password|passphrase|secret|api_key|private_key|access_token|refresh_token)($|[_-])",
    re.IGNORECASE,
)
_MAX_BYTES = 131072
_SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_records (
    namespace TEXT NOT NULL,
    record_key TEXT NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(namespace, record_key)
);
CREATE INDEX IF NOT EXISTS idx_agent_records_recent
ON agent_records (namespace, updated_at DESC);
"""


def database_path(home: Path | None = None) -> Path:
    root = Path(home) if home is not None else get_hermes_home()
    return root / "workstation" / "datasets" / "agent-generated.sqlite"


def _connect(home: Path | None = None) -> sqlite3.Connection:
    path = database_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=10000")
    # New profiles use the default rollback journal. Never convert an existing
    # WAL database while other sessions may hold open connections.
    conn.executescript(_SCHEMA)
    if os.name != "nt":
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    return conn


def _name(value: str, field: str) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise ValueError(f"{field} requires 1..120 alphanumeric/._:- characters")
    return value


def _validate_payload(data: dict[str, Any]) -> str:
    if not isinstance(data, dict):
        raise ValueError("data must be a JSON object")
    def check(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if not isinstance(key, str):
                    raise ValueError("JSON keys must be strings")
                if _SECRET_FIELD.search(key):
                    raise ValueError("Do not store credentials or secrets in the Database")
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)
    check(data)
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(",", ":"))
    if len(raw.encode("utf-8")) > _MAX_BYTES:
        raise ValueError("record exceeds 128 KiB; store an artifact path/reference instead")
    return raw


def _record(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "namespace": row["namespace"], "key": row["record_key"],
        "kind": row["kind"], "title": row["title"],
        "data": json.loads(row["payload_json"]), "revision": row["revision"],
        "created_at": row["created_at"], "updated_at": row["updated_at"],
    }


def save_record(*, namespace: str, key: str, kind: str, title: str,
                data: dict[str, Any], expected_revision: int | None = None,
                home: Path | None = None) -> dict[str, Any]:
    """Create once; updates require the previously-read revision.

    Identical repeated payloads are idempotent. No silent last-writer-wins.
    """
    namespace, key, kind = _name(namespace, "namespace"), _name(key, "key"), _name(kind, "kind")
    if not isinstance(title, str) or not title.strip() or len(title) > 250:
        raise ValueError("title must have 1..250 characters")
    if expected_revision is not None and (type(expected_revision) is not int or expected_revision < 1):
        raise ValueError("expected_revision must be a positive integer")
    payload = _validate_payload(data)
    now = datetime.now(timezone.utc).isoformat()
    with closing(_connect(home)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            row = conn.execute(
                "SELECT * FROM agent_records WHERE namespace=? AND record_key=?",
                (namespace, key),
            ).fetchone()
            if row is None:
                if expected_revision is not None:
                    conn.rollback()
                    return {"ok": False, "error": "record_missing", "namespace": namespace, "key": key}
                conn.execute(
                    "INSERT INTO agent_records (namespace,record_key,kind,title,payload_json,revision,created_at,updated_at) "
                    "VALUES (?,?,?,?,?,1,?,?)",
                    (namespace, key, kind, title.strip(), payload, now, now),
                )
                status, revision = "created", 1
            else:
                if row["payload_json"] == payload and row["title"] == title.strip() and row["kind"] == kind:
                    conn.commit()
                    return {"ok": True, "status": "unchanged", "namespace": namespace,
                            "key": key, "revision": row["revision"]}
                if expected_revision != row["revision"]:
                    conn.rollback()
                    return {"ok": False, "error": "revision_conflict", "namespace": namespace,
                            "key": key, "current_revision": row["revision"]}
                revision = row["revision"] + 1
                conn.execute(
                    "UPDATE agent_records SET kind=?,title=?,payload_json=?,revision=?,updated_at=? "
                    "WHERE namespace=? AND record_key=?",
                    (kind, title.strip(), payload, revision, now, namespace, key),
                )
                status = "updated"
            conn.commit()
            return {"ok": True, "status": status, "namespace": namespace,
                    "key": key, "revision": revision}
        except Exception:
            conn.rollback()
            raise


def list_records(*, namespace: str | None = None, kind: str | None = None,
                 key: str | None = None, limit: int = 20,
                 home: Path | None = None) -> dict[str, Any]:
    if type(limit) is not int or limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50")
    if namespace is not None: _name(namespace, "namespace")
    if kind is not None: _name(kind, "kind")
    if key is not None:
        if namespace is None:
            raise ValueError("namespace is required when key is supplied")
        _name(key, "key")
    clauses, params = [], []
    for column, value in (("namespace", namespace), ("kind", kind), ("record_key", key)):
        if value is not None:
            clauses.append(f"{column}=?")
            params.append(value)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    with closing(_connect(home)) as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM agent_records{where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM agent_records{where} ORDER BY updated_at DESC, namespace, record_key LIMIT ?",
            (*params, limit),
        ).fetchall()
        return {"ok": True, "dataset": "agent", "total": total,
                "records": [_record(row) for row in rows]}

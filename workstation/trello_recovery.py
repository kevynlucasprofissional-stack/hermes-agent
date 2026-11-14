"""Restore historical Trello tasks missing from the private ACIRV tasks snapshot.

The original source database is never modified. The 119 old task IDs and their
existing events/links are preserved; all recovered cards are completed/history-only.
"""
from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from workstation import acirv_datasets as datasets

EXPECTED_IDS = 119
EXPECTED_LINKS = 123


def recover(snapshot: Path, home: Path | None = None) -> dict:
    data = json.loads(Path(snapshot).read_text(encoding="utf-8-sig"))
    entries = data.get("rows")
    if (data.get("schema_version") != 1
            or data.get("source_board_name") != "Calendário Editorial"
            or not isinstance(entries, list) or len(entries) != EXPECTED_LINKS):
        raise ValueError("Unexpected historical export or record count")

    groups: dict[int, list[dict]] = defaultdict(list)
    for row in entries:
        task_id = row.get("task_id")
        if (type(task_id) is not int or task_id <= 0
                or not isinstance(row.get("ref"), str) or len(row["ref"]) != 8
                or not isinstance(row.get("title"), str) or not row["title"]
                or row.get("due_complete") is not True
                or row.get("closed") is not False
                or not str(row.get("url", "")).startswith("https://trello.com/c/")):
            raise ValueError("Invalid historical Trello record")
        groups[task_id].append(row)
    if len(groups) != EXPECTED_IDS or len({r["ref"] for r in entries}) != EXPECTED_LINKS:
        raise ValueError("Historical Trello source has missing or duplicate references")

    target = datasets.directory(home) / "tarefas.sqlite"
    if not target.is_file():
        raise ValueError("ACIRV tasks snapshot is not imported")
    digest_before = datasets._digest(target)

    fd, temp_name = tempfile.mkstemp(prefix="recovered-tasks-", suffix=".sqlite", dir=target.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        # SQLite online backup keeps the copied snapshot independent of source WAL.
        with closing(sqlite3.connect(target.as_uri() + "?mode=ro", uri=True, timeout=10)) as original:
            with closing(sqlite3.connect(temp)) as copy:
                original.backup(copy)

        with closing(sqlite3.connect(temp)) as conn:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("BEGIN IMMEDIATE")
            try:
                actual_links = conn.execute("""
                    SELECT l.task_id,substr(l.ref,8) FROM task_links l
                    WHERE l.kind='trello_card' AND l.task_id BETWEEN ? AND ?
                    ORDER BY l.task_id,l.id
                """, (min(groups), max(groups))).fetchall()
                expected_links = [(row["task_id"], row["ref"]) for row in entries]
                if sorted(actual_links) != sorted(expected_links):
                    raise ValueError("The task linkage changed; refusing automatic reconstruction")

                existing = {
                    int(r[0]): (r[1], r[2])
                    for r in conn.execute(
                        "SELECT id, source_ref, status FROM tasks WHERE id BETWEEN ? AND ?",
                        (min(groups), max(groups))
                    )
                }
                already = len(existing) == len(groups)
                if already:
                    if any(existing[id] != (f'trello:{rows[0]["ref"]}', "concluida")
                           for id, rows in groups.items()):
                        raise ValueError("Existing task identifiers conflict with recovered records")
                    if conn.execute("PRAGMA foreign_key_check").fetchone() is not None:
                        raise ValueError("Existing restored tasks still have broken foreign keys")
                    conn.rollback()
                    return {"status": "unchanged", "tasks": len(groups), "links": len(entries),
                            "foreign_key_violations": 0}

                if existing:
                    raise ValueError("Partial recovery detected; refusing to overwrite existing tasks")

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS trello_recovery_evidence (
                        task_id INTEGER NOT NULL REFERENCES tasks(id),
                        short_link TEXT NOT NULL,
                        card_id TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        PRIMARY KEY(task_id,short_link)
                    )
                """)
                for task_id, rows in sorted(groups.items()):
                    first = rows[0]
                    code = f"T-{task_id:04d}"
                    if conn.execute("SELECT 1 FROM tasks WHERE code=?", (code,)).fetchone():
                        raise ValueError(f"Human-readable task code collision: {code}")
                    event = conn.execute(
                        "SELECT MIN(occurred_at) FROM task_events WHERE task_id=?", (task_id,)
                    ).fetchone()[0]
                    if not event:
                        raise ValueError(f"No historical task event for {task_id}")
                    source_tags = sorted({
                        str(label.get("name", "")).strip()
                        for item in rows for label in item.get("labels", [])
                        if isinstance(label, dict) and str(label.get("name", "")).strip()
                    })
                    conn.execute("""
                        INSERT INTO tasks (
                            id,code,title,description,status,priority,owner,source,
                            source_ref,source_url,channel,due_at,completed_at,
                            tags,notes,created_at,updated_at
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        task_id, code, first["title"], first.get("description") or None,
                        "concluida", "normal", "não atribuído", "trello",
                        "trello:" + first["ref"], first["url"], "trello",
                        first.get("due"), first.get("date_completed"),
                        ",".join(source_tags) or None,
                        "Restaurada do export Calendário Editorial; concluída no Trello. "
                        "Histórico anterior e cartões adicionais em task_events/task_links/"
                        "trello_recovery_evidence; não reabrir ou sincronizar automaticamente.",
                        event, event
                    ))
                    for row in rows:
                        conn.execute("""
                            INSERT INTO trello_recovery_evidence
                            (task_id,short_link,card_id,payload_json)
                            VALUES (?,?,?,?)
                        """, (task_id, row["ref"], row["card_id"],
                              json.dumps(row, ensure_ascii=False, separators=(",", ":"))))

                remaining = conn.execute("PRAGMA foreign_key_check").fetchall()
                if remaining:
                    raise ValueError(f"Recovery left {len(remaining)} broken foreign keys")
                expected_count = len(groups)
                if conn.execute("SELECT COUNT(*) FROM trello_recovery_evidence").fetchone()[0] != len(entries):
                    raise ValueError("Incomplete recovery evidence")
                conn.commit()
            except BaseException:
                conn.rollback()
                raise

        # A concurrent importer or another agent must not be overwritten.
        if datasets._digest(target) != digest_before:
            raise RuntimeError("Tasks snapshot changed during recovery; no file replaced")
        before = target.with_name("tarefas.before-recovery.sqlite")
        if not before.exists():
            with closing(sqlite3.connect(target.as_uri() + "?mode=ro", uri=True)) as original:
                with closing(sqlite3.connect(before)) as backup:
                    original.backup(backup)
        os.replace(temp, target)
        with closing(sqlite3.connect(target.as_uri() + "?mode=ro", uri=True)) as check:
            total = check.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            fk = len(check.execute("PRAGMA foreign_key_check").fetchall())
        return {"status": "restored", "tasks": expected_count,
                "links": len(entries), "total_tasks": total,
                "foreign_key_violations": fk, "backup": str(before)}
    finally:
        temp.unlink(missing_ok=True)

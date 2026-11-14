"""One-time read-only Trello inventory import into the existing Workstation Database.

This is not a live or bidirectional sync. The connector snapshot is an explicit,
private input. Neither Trello nor original task databases are mutated.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
from collections import defaultdict
from contextlib import closing
from pathlib import Path

from workstation import acirv_datasets as datasets

_CARD_ARI = re.compile(r"^ari:cloud:trello::card/workspace/[^/]+/([0-9a-f]{24})$")
_DONE_LIST = re.compile(r"(?:^|[\s_-])(finalizad[oa]s?|conclu[ií]d[oa]s?|feitos?|done|completed)(?:[\s_-]|$)", re.I)
VIEWS = [
    {"id": "trello_ativos", "label": "Trello · Em aberto", "dataset": "trello", "table": "cards",
     "fields": ["id", "name", "board_name", "list_name", "due", "last_activity_at"], "group_by": "board_name"},
    {"id": "trello_referencias", "label": "Trello · Referências órfãs", "dataset": "trello", "table": "orphan_refs",
     "fields": ["task_id", "ref", "url", "link_count", "event_count", "status"], "group_by": "status"},
]


def import_inventory(snapshot: Path, home: Path | None = None) -> dict:
    """Validate an externally obtained snapshot, then atomically replace only trello.sqlite."""
    payload = json.loads(Path(snapshot).read_text(encoding="utf-8-sig"))
    if payload.get("schema_version") != 1 or not isinstance(payload.get("cards"), list):
        raise ValueError("Invalid Trello inventory format")
    if payload.get("selection") != "!closed && !complete && !dueComplete && !completed_list":
        raise ValueError("Trello inventory selection not verified")
    stats = payload.get("stats")
    if not isinstance(stats, list) or sum(s.get("active", -1) for s in stats) != len(payload["cards"]):
        raise ValueError("Incomplete Trello inventory")

    rows = []
    seen = set()
    for card in payload["cards"]:
        match = _CARD_ARI.fullmatch(str(card.get("id", "")))
        if not match or match[1] in seen:
            raise ValueError("Invalid or duplicate Trello card ID")
        if (card.get("closed") is not False or card.get("complete") is not False
                or card.get("dueComplete") is not False
                or _DONE_LIST.search(str(card.get("list_name", "")))):
            raise ValueError("Completed or archived card in active inventory")
        if not str(card.get("url", "")).startswith("https://trello.com/c/"):
            raise ValueError("Invalid Trello card URL")
        if not isinstance(card.get("name"), str) or not card["name"]:
            raise ValueError("Card without name")
        seen.add(match[1])
        rows.append((
            match[1], card["name"], str(card.get("desc") or ""), card["url"],
            str(card.get("board_name") or ""), str(card.get("board_id") or ""),
            str(card.get("list_name") or ""), str(card.get("list_id") or ""),
            card.get("due"), card.get("lastActivityAt"), "em_aberto",
            json.dumps(card.get("labels", []), ensure_ascii=False),
            json.dumps(card.get("members", []), ensure_ascii=False),
            json.dumps(card.get("checklists", []), ensure_ascii=False),
            json.dumps(card.get("comments", []), ensure_ascii=False),
            int(card.get("checklistsHasMore") is True),
            int(card.get("commentsHasMore") is True),
        ))

    dest_dir = datasets.directory(home)
    dest_dir.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix="trello-", suffix=".sqlite", dir=dest_dir)
    os.close(fd)
    temp = Path(temp_name)
    try:
        with closing(sqlite3.connect(temp)) as conn:
            conn.executescript("""
              CREATE TABLE cards (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT,
                url TEXT NOT NULL, board_name TEXT, board_id TEXT,
                list_name TEXT, list_id TEXT, due TEXT, last_activity_at TEXT,
                status TEXT NOT NULL, labels_json TEXT, members_json TEXT,
                checklists_json TEXT, comments_json TEXT,
                checklists_truncated INTEGER NOT NULL, comments_truncated INTEGER NOT NULL
              );
              CREATE INDEX idx_cards_board ON cards(board_name);
              CREATE TABLE orphan_refs (
                task_id INTEGER PRIMARY KEY, ref TEXT, url TEXT, label TEXT,
                link_count INTEGER NOT NULL, event_count INTEGER NOT NULL,
                status TEXT NOT NULL
              );
            """)
            conn.executemany("INSERT INTO cards VALUES (" + ",".join(["?"] * 17) + ")", rows)
            task_snapshot = dest_dir / "tarefas.sqlite"
            if task_snapshot.is_file():
                with closing(sqlite3.connect(task_snapshot.as_uri() + "?mode=ro", uri=True)) as original:
                    original.execute("PRAGMA query_only=ON")
                    orphan_groups = defaultdict(list)
                    for row in original.execute("""
                        SELECT l.task_id,l.ref,l.url,l.label FROM task_links l
                        LEFT JOIN tasks t ON t.id=l.task_id
                        WHERE t.id IS NULL AND l.kind='trello_card'
                        ORDER BY l.task_id,l.id
                    """):
                        orphan_groups[row[0]].append(row)
                    for task_id, links in orphan_groups.items():
                        event_count = original.execute(
                            "SELECT COUNT(*) FROM task_events WHERE task_id=?", (task_id,)
                        ).fetchone()[0]
                        conn.execute(
                            "INSERT INTO orphan_refs VALUES (?,?,?,?,?,?,?)",
                            (task_id, links[0][1], links[0][2], links[0][3],
                             len(links), event_count, "referencia_nao_verificada"),
                        )
            conn.commit()
            if conn.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Trello snapshot integrity failure")
            counts = {
                "cards": conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0],
                "orphan_refs": conn.execute("SELECT COUNT(*) FROM orphan_refs").fetchone()[0],
            }

        target = datasets.directory(home) / datasets.FILENAMES["trello"]
        if target.exists() and datasets._digest(target) == datasets._digest(temp):
            status = "unchanged"
        else:
            if target.exists():
                # A connector-only refresh must not erase historic recoveries or
                # open cards imported from user-provided board exports.
                with closing(sqlite3.connect(target.as_uri() + "?mode=ro", uri=True)) as current:
                    tables = {row[0] for row in current.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'")}
                    if ("trello_export_evidence" in tables and current.execute(
                            "SELECT COUNT(*) FROM trello_export_evidence").fetchone()[0]):
                        raise ValueError("Trello snapshot has offline exports; explicit reconciliation required")
                    if ("orphan_refs" in tables and current.execute(
                            "SELECT COUNT(*) FROM orphan_refs WHERE status='recuperada'").fetchone()[0]):
                        raise ValueError("Trello snapshot has recovered history; explicit reconciliation required")
                previous = target.with_suffix(".previous.sqlite")
                with closing(sqlite3.connect(target)) as old:
                    with closing(sqlite3.connect(previous)) as backup:
                        old.backup(backup)
            os.replace(temp, target)
            status = "imported"

        # Retain all existing view customizations and append just the two new views.
        views_file = dest_dir / "views.json"
        views = json.loads(views_file.read_text(encoding="utf-8")) if views_file.exists() else datasets.DEFAULT_VIEWS.copy()
        if not isinstance(views, list):
            raise ValueError("Invalid views catalog")
        existing_ids = {v["id"] for v in views}
        if any(v["id"] not in existing_ids for v in VIEWS):
            updated = views + [v for v in VIEWS if v["id"] not in existing_ids]
            pending = views_file.with_suffix(".trello.tmp")
            pending.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(pending, views_file)
        return {**counts, "status": status, "snapshot": str(snapshot)}
    finally:
        temp.unlink(missing_ok=True)

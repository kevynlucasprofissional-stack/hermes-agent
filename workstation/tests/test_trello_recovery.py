"""Regression checks for recovery of missing ACIRV Trello tasks."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from contextlib import closing

import pytest

from workstation import acirv_datasets as datasets
from workstation.trello_recovery import recover


def fixture(tmp_path: Path):
    home = tmp_path / "home"
    directory = datasets.directory(home)
    directory.mkdir(parents=True)
    source = directory / "tarefas.sqlite"
    with closing(sqlite3.connect(source)) as conn:
        conn.executescript("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY, code TEXT UNIQUE, title TEXT, description TEXT,
                status TEXT, priority TEXT, owner TEXT, source TEXT, source_ref TEXT,
                source_url TEXT, channel TEXT, due_at TEXT, completed_at TEXT,
                tags TEXT, notes TEXT, created_at TEXT, updated_at TEXT
            );
            CREATE TABLE task_links (
                id INTEGER PRIMARY KEY, task_id INTEGER REFERENCES tasks(id),
                kind TEXT, ref TEXT, label TEXT, url TEXT
            );
            CREATE TABLE task_events (
                id INTEGER PRIMARY KEY, task_id INTEGER REFERENCES tasks(id),
                occurred_at TEXT, note TEXT
            );
        """)
        rows = []
        for id in range(268, 387):
            for n in range(2 if id in {283, 290, 367, 377} else 1):
                ref = f"{id:06d}{n:02d}"
                conn.execute("INSERT INTO task_links VALUES (?,?,?,?,?,?)",
                             (len(rows) + 1, id, "trello_card", f"trello:{ref}",
                              "Original", f"https://trello.com/c/{ref}"))
                rows.append({
                    "task_id": id, "ref": ref, "title": f"Tarefa {id}",
                    "description": "Histórico original", "due_complete": True,
                    "closed": False, "date_completed": "2026-10-01T10:00:00Z",
                    "due": None, "url": f"https://trello.com/c/{ref}",
                    "card_id": f"{id:024x}", "labels": [], "attachments": []
                })
            conn.execute("INSERT INTO task_events VALUES (?,?,?,?)",
                         (id, id, "2026-10-23 12:00:00", "import"))
        conn.commit()
    proposal = tmp_path / "recovery.json"
    proposal.write_text(json.dumps({
        "schema_version": 1, "source_board_name": "Calendário Editorial", "rows": rows
    }), encoding="utf-8")
    return home, proposal, source


def test_recovery_fixes_all_fks_preserves_events_links_and_backup(tmp_path):
    home, proposal, original = fixture(tmp_path)
    untouched = original.read_bytes()
    result = recover(proposal, home)
    assert result["status"] == "restored"
    assert result["foreign_key_violations"] == 0
    assert result["tasks"] == 119
    with closing(sqlite3.connect(original)) as conn:
        assert conn.execute("select count(*) from tasks").fetchone()[0] == 119
        assert conn.execute("select count(*) from task_links").fetchone()[0] == 123
        assert conn.execute("select count(*) from task_events").fetchone()[0] == 119
        assert conn.execute("select count(*) from trello_recovery_evidence").fetchone()[0] == 123
        assert conn.execute("select count(*) from tasks where status='concluida'").fetchone()[0] == 119
    with closing(sqlite3.connect(original.with_name("tarefas.before-recovery.sqlite"))) as backup:
        assert backup.execute("select count(*) from tasks").fetchone()[0] == 0
        assert backup.execute("select count(*) from task_links").fetchone()[0] == 123
        assert len(backup.execute("pragma foreign_key_check").fetchall()) == 242
    assert recover(proposal, home)["status"] == "unchanged"


def test_recovery_rejects_partial_payload_without_changing_db(tmp_path):
    home, proposal, original = fixture(tmp_path)
    before = original.read_bytes()
    data = json.loads(proposal.read_text(encoding="utf-8"))
    data["rows"].pop()
    proposal.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="record count"):
        recover(proposal, home)
    assert original.read_bytes() == before

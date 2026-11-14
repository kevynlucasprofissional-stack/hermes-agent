"""Local edits must persist without corrupting source snapshots or losing concurrent edits."""
from __future__ import annotations

import sqlite3

from workstation import acirv_datasets as datasets
from workstation import dataset_edits as edits


def _setup(tmp_path):
    directory = datasets.directory(tmp_path)
    directory.mkdir(parents=True, exist_ok=True)
    source = directory / "tarefas.sqlite"
    with sqlite3.connect(source) as conn:
        conn.executescript("""
            CREATE TABLE tasks(id INTEGER PRIMARY KEY, title TEXT NOT NULL,
                               status TEXT, owner TEXT);
            INSERT INTO tasks VALUES(1,'Original','open','Samara');
        """)
    return source


def test_local_edit_persists_projects_and_conflicts(tmp_path):
    origin = _setup(tmp_path)
    created = edits.update_record(tmp_path, "tarefas", "tasks", "1", changes={"title": "Editado"},
                                  expected_revision=0, actor="human")
    assert created["ok"] and created["revision"] == 1
    detail = datasets.get_record(tmp_path, "tarefas", "tasks", "1")
    assert detail["record"]["title"] == "Editado"
    assert detail["local_revision"] == 1 and detail["pending_external_sync"]
    rows = datasets.list_records(tmp_path, "tarefas", "tasks")
    assert rows["rows"][0]["title"] == "Editado"
    assert edits.update_record(tmp_path, "tarefas", "tasks", "1",
                               changes={"title": "Bad"}, expected_revision=0,
                               actor="agent")["error"] == "revision_conflict"
    updated = edits.update_record(tmp_path, "tarefas", "tasks", "1",
                                  changes={"status": "review"}, expected_revision=1, actor="agent")
    assert updated["revision"] == 2
    assert datasets.get_record(tmp_path, "tarefas", "tasks", "1")["record"]["status"] == "review"
    with sqlite3.connect(origin) as conn:
        assert conn.execute("SELECT title, status FROM tasks").fetchone() == ("Original", "open")
    with sqlite3.connect(edits.path(tmp_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM edit_events").fetchone()[0] == 2
        assert conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "delete"


def test_source_drift_is_flagged_and_never_overwritten(tmp_path):
    origin = _setup(tmp_path)
    edits.update_record(tmp_path, "tarefas", "tasks", "1",
                        changes={"title": "Local"}, expected_revision=0, actor="human")
    with sqlite3.connect(origin) as conn:
        conn.execute("UPDATE tasks SET title='Remote' WHERE id=1")
    detail = datasets.get_record(tmp_path, "tarefas", "tasks", "1")
    assert detail["source_conflict_fields"] == ["title"]
    assert edits.update_record(tmp_path, "tarefas", "tasks", "1", changes={"status": "paused"},
                               expected_revision=1, actor="agent")["error"] == "source_changed"


def test_reject_primary_keys_foreign_keys_and_raw_json(tmp_path):
    origin = _setup(tmp_path)
    for changes in ({"id": 99}, {"missing": 42}, {"title": ["bad"]}):
        try:
            edits.update_record(tmp_path, "tarefas", "tasks", "1",
                                changes=changes, expected_revision=0, actor="human")
        except ValueError:
            pass
        else:
            raise AssertionError(f"Accepted unsafe edit: {changes}")
    assert not edits.path(tmp_path).exists()

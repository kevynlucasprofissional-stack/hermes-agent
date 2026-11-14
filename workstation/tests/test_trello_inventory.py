"""Real SQLite checks for the one-time Trello inventory bridge."""
import json
import sqlite3
from pathlib import Path

import pytest

from workstation import acirv_datasets as datasets
from workstation import trello_inventory


def _fixture(tmp_path: Path):
    home = tmp_path / "home"
    d = datasets.directory(home)
    d.mkdir(parents=True)
    with sqlite3.connect(d / "tarefas.sqlite") as c:
        c.executescript("""
            CREATE TABLE tasks(id INTEGER PRIMARY KEY,title TEXT);
            CREATE TABLE task_events(id INTEGER PRIMARY KEY,task_id INTEGER,note TEXT);
            CREATE TABLE task_links(id INTEGER PRIMARY KEY,task_id INTEGER,kind TEXT,ref TEXT,
                                    url TEXT,label TEXT);
            INSERT INTO tasks VALUES (1,'Existing task');
            INSERT INTO task_events VALUES (1,44,'orphan history');
            INSERT INTO task_links VALUES (1,44,'trello_card','trello:abc12345',
                'https://trello.com/c/abc12345','Trello');
        """)
    payload = {
        "schema_version": 1,
        "selection": "!closed && !complete && !dueComplete && !completed_list",
        "stats": [{"board": "Example", "active": 1}],
        "cards": [{
            "id": "ari:cloud:trello::card/workspace/a/6a4259d9dd044ac57fe5af7c",
            "name": "Example open task", "desc": "Keep original", "closed": False,
            "complete": False, "dueComplete": False, "url": "https://trello.com/c/abc12345",
            "board_name": "Example", "list_name": "A fazer", "board_id": "board",
            "list_id": "list", "due": None, "lastActivityAt": None,
            "comments": [], "checklists": [],
        }],
    }
    snapshot = tmp_path / "inventory.json"
    snapshot.write_text(json.dumps(payload), encoding="utf-8")
    return home, snapshot, payload


def test_import_inventory_preserves_original_tasks_and_orphans(tmp_path):
    home, snapshot, _ = _fixture(tmp_path)
    original = (datasets.directory(home) / "tarefas.sqlite").read_bytes()
    result = trello_inventory.import_inventory(snapshot, home)
    assert result["cards"] == 1
    assert result["orphan_refs"] == 1
    assert (datasets.directory(home) / "tarefas.sqlite").read_bytes() == original
    catalog = datasets.list_datasets(home)
    assert [d["id"] for d in catalog["datasets"]] == ["tarefas", "trello"]
    assert {"trello_ativos", "trello_referencias"} <= {v["id"] for v in catalog["views"]}
    page = datasets.list_records(home, "trello", "cards", limit=5)
    assert page["total"] == 1
    assert page["rows"][0]["name"] == "Example open task"
    detail = datasets.get_record(home, "trello", "cards", "6a4259d9dd044ac57fe5af7c")
    assert detail["record"]["description"] == "Keep original"
    assert datasets.list_records(home, "trello", "orphan_refs", limit=10)["rows"][0]["event_count"] == 1
    result2 = trello_inventory.import_inventory(snapshot, home)
    assert result2["status"] == "unchanged"


@pytest.mark.parametrize("field,value", [
    ("complete", True), ("dueComplete", True), ("closed", True),
    ("list_name", "Finalizados"), ("id", "invalid")
])
def test_rejects_completed_archived_or_invalid_cards_without_writes(tmp_path, field, value):
    home, snapshot, payload = _fixture(tmp_path)
    payload["cards"][0][field] = value
    snapshot.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        trello_inventory.import_inventory(snapshot, home)
    assert not (datasets.directory(home) / "trello.sqlite").exists()

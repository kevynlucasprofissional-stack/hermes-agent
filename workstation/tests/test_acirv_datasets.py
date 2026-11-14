"""Real SQLite regression checks for the Workstation relational dataset bridge."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from workstation import acirv_datasets as datasets


def make_sources(tmp_path: Path) -> dict[str, Path]:
    tasks = tmp_path / "tasks-source.sqlite"
    wa = tmp_path / "wa-source.sqlite"
    with sqlite3.connect(tasks) as conn:
        conn.executescript("""
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY, code TEXT, title TEXT, status TEXT,
                priority TEXT, source_ref TEXT, wa_contact_id INTEGER,
                wa_conversation_id INTEGER, description TEXT
            );
            CREATE TABLE task_events (
                id INTEGER PRIMARY KEY, task_id INTEGER REFERENCES tasks(id), note TEXT
            );
            CREATE TABLE task_links (
                id INTEGER PRIMARY KEY, task_id INTEGER REFERENCES tasks(id), ref TEXT
            );
            INSERT INTO tasks VALUES (1, 'T-0001', 'Preparar release',
              'em_andamento', 'alta', 'wa:pend:3', 2, 5, 'Contexto');
            INSERT INTO task_events VALUES (1, 1, 'Criado');
            INSERT INTO task_events VALUES (2, 999, 'Historico orfao');
        """)
    with sqlite3.connect(wa) as conn:
        conn.executescript("""
            CREATE TABLE contacts(id INTEGER PRIMARY KEY, display_name TEXT);
            CREATE TABLE conversations(
              id INTEGER PRIMARY KEY, contact_id INTEGER REFERENCES contacts(id)
            );
            CREATE TABLE pendencies(
              id INTEGER PRIMARY KEY, contact_id INTEGER REFERENCES contacts(id),
              conversation_id INTEGER, title TEXT, status TEXT, priority TEXT
            );
            CREATE TABLE messages(id INTEGER PRIMARY KEY, conversation_id INTEGER, content_text TEXT);
            INSERT INTO contacts VALUES (2, 'Contato Exemplo');
            INSERT INTO conversations VALUES (5, 2);
            INSERT INTO pendencies VALUES (3, 2, 5, 'Responder', 'awaiting_info', 'high');
            INSERT INTO messages VALUES (4, 5, 'Mensagem teste');
        """)
    return {"tarefas": tasks, "whatsapp": wa}


def test_import_preserves_relations_and_orphans_without_modifying_sources(tmp_path):
    sources = make_sources(tmp_path)
    home = tmp_path / "hermes"
    original = {key: path.read_bytes() for key, path in sources.items()}

    result = datasets.import_sources(sources, home)
    assert result["tarefas"]["rows"]["tasks"] == 1
    assert result["tarefas"]["foreign_key_violations"] == 1
    assert result["whatsapp"]["rows"]["contacts"] == 1
    assert all(path.read_bytes() == original[key] for key, path in sources.items())

    record = datasets.get_record(home, "tarefas", "tasks", "1")
    links = {(link["dataset"], link["table"], str(link["id"])) for link in record["relations"]}
    assert ("whatsapp", "contacts", "2") in links
    assert ("whatsapp", "conversations", "5") in links
    assert ("whatsapp", "pendencies", "3") in links
    assert all(link["exists"] for link in record["relations"])

    snapshot = home / "workstation" / "datasets" / "tarefas.sqlite"
    before = snapshot.read_bytes()
    second = datasets.import_sources(sources, home)
    assert second["tarefas"]["status"] == "unchanged"
    assert snapshot.read_bytes() == before


def test_projections_filters_pages_and_invalid_table_rejection(tmp_path):
    home = tmp_path / "hermes"
    datasets.import_sources(make_sources(tmp_path), home)
    result = datasets.list_records(
        home, "tarefas", "tasks", limit=5, columns=["id", "title", "status"],
        status="em_andamento"
    )
    assert result["count"] == 1
    assert result["rows"] == [{"id": 1, "title": "Preparar release", "status": "em_andamento"}]
    assert result["total"] == 1
    assert "description" not in result["rows"][0]
    assert datasets.list_datasets(home)["datasets"][0]["tables"]
    with pytest.raises(ValueError):
        datasets.list_records(home, "tarefas", "tasks; DROP TABLE tasks", limit=10)
    with pytest.raises(ValueError):
        datasets.list_records(home, "tarefas", "tasks", columns=["bad;SELECT"])
    with pytest.raises(ValueError):
        datasets.list_records(home, "inexistente", "tasks")
    with pytest.raises(ValueError):
        datasets.list_records(home, "tarefas", "tasks", limit=10001)

def test_http_dataset_endpoints_return_paginated_relational_records(tmp_path, monkeypatch):
    import importlib.util
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    home = tmp_path / "hermes"
    datasets.import_sources(make_sources(tmp_path), home)
    original_directory = datasets.directory
    monkeypatch.setattr(datasets, "directory", lambda _home=None: original_directory(home))
    plugin_path = Path(__file__).resolve().parents[2] / "plugins" / "workstation-board" / "dashboard" / "plugin_api.py"
    spec = importlib.util.spec_from_file_location("workstation_board_dataset_test", plugin_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = FastAPI()
    app.include_router(module.router, prefix="/api")
    client = TestClient(app)

    catalog = client.get("/api/datasets")
    assert catalog.status_code == 200
    assert {item["id"] for item in catalog.json()["datasets"]} == {"tarefas", "whatsapp"}
    rows = client.get("/api/datasets/tarefas/tables/tasks",
                      params={"columns": "id,title,status", "limit": 10})
    assert rows.status_code == 200
    assert rows.json()["rows"][0]["title"] == "Preparar release"
    detail = client.get("/api/datasets/tarefas/tables/tasks/rows/1")
    assert detail.status_code == 200
    assert len(detail.json()["relations"]) == 3
    assert client.get("/api/datasets/tarefas/tables/unknown").status_code == 400


def test_invalid_source_cleans_private_temporary_snapshot(tmp_path):
    sources = make_sources(tmp_path)
    with sqlite3.connect(sources["tarefas"]) as conn:
        conn.execute("DROP TABLE task_links")
    home = tmp_path / "hermes"
    with pytest.raises(ValueError, match="Incompatible tarefas"):
        datasets.import_sources(sources, home)
    assert not list(datasets.directory(home).glob("*.sqlite"))


def test_import_refuses_silent_loss_of_recovered_trello_tasks(tmp_path):
    from contextlib import closing

    sources = make_sources(tmp_path)
    home = tmp_path / "hermes"
    datasets.import_sources(sources, home)
    task_copy = datasets.directory(home) / "tarefas.sqlite"
    wa_copy = datasets.directory(home) / "whatsapp.sqlite"
    with closing(sqlite3.connect(task_copy)) as conn:
        conn.execute("CREATE TABLE trello_recovery_evidence(task_id INTEGER, short_link TEXT)")
        conn.execute("INSERT INTO trello_recovery_evidence VALUES (1, 'example')")
        conn.commit()
    before = (task_copy.read_bytes(), wa_copy.read_bytes())
    with pytest.raises(ValueError, match="recovered Trello history"):
        datasets.import_sources(sources, home)
    assert (task_copy.read_bytes(), wa_copy.read_bytes()) == before

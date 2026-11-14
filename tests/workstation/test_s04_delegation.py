"""Explicit delegation with mocked official gateway; never dispatches a real agent."""
import importlib.util
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from workstation import kanban_local as board
from workstation import task_adapter


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(board, "get_hermes_home", lambda: tmp_path)
    path = Path(__file__).resolve().parents[2] / "plugins/workstation-board/dashboard/plugin_api.py"
    spec = importlib.util.spec_from_file_location("board_delegation_test_api", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = FastAPI()
    app.include_router(module.router, prefix="/api/plugins/workstation-board")
    return TestClient(app)


def test_explicit_delegation_is_idempotent_and_reconciles(tmp_path, monkeypatch):
    calls = []
    def fake_create(**kwargs):
        calls.append(kwargs)
        return "official-task-id"
    monkeypatch.setattr(task_adapter, "create_official_task", fake_create)
    monkeypatch.setattr(task_adapter, "get_official_task_status", lambda _: "blocked")
    root = "/api/plugins/workstation-board"
    with _client(tmp_path, monkeypatch) as client:
        base = client.post(root + "/boards", json={"name": "Local"}).json()["board"]
        card = client.post(root + f"/boards/{base['id']}/cards", json={
            "title": "Deliver", "column_id": base["columns"][0]["id"]}).json()["card"]
        url = root + f"/cards/{card['id']}/delegate"
        data = {"confirmed": True, "expected_revision": 1, "assignee": "agent-01"}
        assert client.post(url, json={**data, "confirmed": False}).status_code == 400
        assert calls == []
        first = client.post(url, json=data)
        assert first.status_code == 200, first.text
        assert first.json()["delegation"]["task_id"] == "official-task-id"
        second = client.post(url, json=data)
        assert second.status_code == 200
        assert len(calls) == 1
        assert second.json()["delegation"]["id"] == first.json()["delegation"]["id"]
        assert calls[0]["idempotency_key"].startswith("workstation-card:")
        sync = client.post(root + f"/cards/{card['id']}/delegation/sync")
        assert sync.status_code == 200
        assert sync.json()["delegation"]["state"] == "waiting"
        details = client.get(root + f"/cards/{card['id']}").json()["card"]
        assert details["delegations"][0]["task_status"] == "blocked"
        assert details["activity"][0]["actor_type"] == "unknown"


def test_gateway_failure_keeps_retryable_intent(tmp_path, monkeypatch):
    calls = []
    def fake_create(**kwargs):
        calls.append(kwargs["idempotency_key"])
        if len(calls) == 1:
            raise RuntimeError("Temporary upstream failure")
        return "official-after-retry"
    monkeypatch.setattr(task_adapter, "create_official_task", fake_create)
    root = "/api/plugins/workstation-board"
    with _client(tmp_path, monkeypatch) as client:
        base = client.post(root + "/boards", json={"name": "Local"}).json()["board"]
        card = client.post(root + f"/boards/{base['id']}/cards", json={
            "title": "Deliver", "column_id": base["columns"][0]["id"]}).json()["card"]
        url = root + f"/cards/{card['id']}/delegate"
        data = {"confirmed": True, "expected_revision": 1}
        assert client.post(url, json=data).status_code == 503
        detail = client.get(root + f"/cards/{card['id']}").json()["card"]
        assert len(detail["delegations"]) == 1
        assert detail["delegations"][0]["task_id"] is None
        assert client.post(url, json=data).status_code == 200
        assert calls[0] == calls[1]
        assert len(client.get(root + f"/cards/{card['id']}").json()["card"]["delegations"]) == 1


def test_adapter_reuses_official_task_without_duplicate(tmp_path, monkeypatch):
    import sqlite3
    from hermes_cli import kanban_db, kanban_db_connect

    path = tmp_path / "official.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY,idempotency_key TEXT,created_at INTEGER)")
    calls = []
    def connect(board=None):
        assert board is None
        return sqlite3.connect(path)
    def create(conn, **kwargs):
        calls.append(kwargs)
        conn.execute("INSERT INTO tasks VALUES (?,?,1)", ("task-1", kwargs["idempotency_key"]))
        conn.commit()
        return "task-1"
    monkeypatch.setattr(kanban_db, "init_db", lambda: None)
    monkeypatch.setattr(kanban_db_connect, "connect", connect)
    monkeypatch.setattr(kanban_db, "create_task", create)
    params = dict(title="Job", description="Description", card_id="card-1", board_id="board-1",
                  assignee="agent-01", idempotency_key="workstation-card:card-1:attempt:1")
    assert task_adapter.create_official_task(**params) == "task-1"
    assert task_adapter.create_official_task(**params) == "task-1"
    assert len(calls) == 1
    assert calls[0]["workspace_kind"] == "scratch"
    assert calls[0]["created_by"] == "workstation-database"

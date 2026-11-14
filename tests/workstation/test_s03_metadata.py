"""Metadata stays in Workstation SQLite, with CAS and truthful audit actor."""
import importlib.util
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from workstation import kanban_local as db


def test_metadata_roundtrip_and_concurrency(tmp_path):
    path = tmp_path / "db.sqlite"
    with db.database(path) as conn:
        base = db.create_board(conn, "Metadata")
        card = db.create_card(conn, base["id"], base["columns"][0]["id"], "Ticket")
        assert db.get_card_details(conn, card["id"])["metadata"] == {}
        changed = db.update_card_metadata(conn, card["id"], 1, {"labels": ["a"], "priority": 2})
        assert changed["revision"] == 2
        assert changed["metadata"] == {"labels": ["a"], "priority": 2}
        assert changed["activity"][0]["actor_type"] == "unknown"
        with pytest.raises(db.BoardConflict):
            db.update_card_metadata(conn, card["id"], 1, {"wrong": True})
        with pytest.raises(db.BoardError):
            db.update_card_metadata(conn, card["id"], 2, {"huge": "x" * 20_000})
        with pytest.raises(db.BoardError):
            db.update_card_metadata(conn, card["id"], 2, {"nan": float("nan")})
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    with db.database(path) as conn:
        assert db.get_card_details(conn, card["id"])["metadata"]["labels"] == ["a"]


def test_metadata_rest_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "get_hermes_home", lambda: tmp_path)
    path = Path(__file__).resolve().parents[2] / "plugins/workstation-board/dashboard/plugin_api.py"
    spec = importlib.util.spec_from_file_location("workstation_meta_api", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = FastAPI()
    app.include_router(module.router, prefix="/api/plugins/workstation-board")
    root = "/api/plugins/workstation-board"
    with TestClient(app) as client:
        base = client.post(root + "/boards", json={"name": "Database"}).json()["board"]
        card = client.post(root + f"/boards/{base['id']}/cards", json={
            "title": "Card", "column_id": base["columns"][0]["id"]}).json()["card"]
        endpoint = root + f"/cards/{card['id']}/metadata"
        response = client.patch(endpoint, json={"expected_revision": 1, "metadata": {"role": "draft"}})
        assert response.status_code == 200
        assert response.json()["card"]["metadata"] == {"role": "draft"}
        assert client.patch(endpoint, json={"expected_revision": 1, "metadata": {}}).status_code == 409

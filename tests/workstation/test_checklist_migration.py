"""Database checklist and activity migration tests without upstream dependencies."""
from pathlib import Path
import importlib.util
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from workstation import kanban_local as board


def test_storage_and_revisions(tmp_path):
    path = tmp_path / "test.sqlite"
    with board.database(path) as db:
        first = board.create_board(db, "Workstation")
        card = board.create_card(db, first["id"], first["columns"][0]["id"], "Sample")
        checklist = board.create_checklist(db, card["id"], "Check")
        item = board.create_checklist_item(db, checklist["id"], "Verify")
        updated = board.update_checklist_item(db, item["id"], 1, completed=True)
        assert updated["completed"] == 1 and updated["revision"] == 2
        with pytest.raises(board.BoardConflict):
            board.update_checklist_item(db, item["id"], 1, completed=False)
        detail = board.get_card_details(db, card["id"])
        assert detail["checklists"][0]["items"][0]["completed"] == 1
        assert detail["activity"][0]["kind"] == "checklist_item_updated"
        board.delete_checklist_item(db, item["id"], 2)
        with pytest.raises(board.BoardConflict):
            board.delete_checklist(db, checklist["id"], 99)
        board.delete_checklist(db, checklist["id"], 1)
        assert board.get_card_details(db, card["id"])["checklists"] == []
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    with board.database(path) as db:
        assert len(board.get_card_details(db, card["id"])["activity"]) == 6  # includes card_created


def test_rest_contract(tmp_path, monkeypatch):
    monkeypatch.setattr(board, "get_hermes_home", lambda: tmp_path)
    p = Path(__file__).resolve().parents[2] / "plugins" / "workstation-board" / "dashboard" / "plugin_api.py"
    spec = importlib.util.spec_from_file_location("workstation_board_checklist_api", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/workstation-board")
    root = "/api/plugins/workstation-board"
    with TestClient(app) as client:
        base = client.post(root + "/boards", json={"name": "Test"}).json()["board"]
        card = client.post(root + f"/boards/{base['id']}/cards", json={
            "column_id": base["columns"][0]["id"], "title": "Review"}).json()["card"]
        assert client.post(root + "/cards/no/checklists", json={"title": "Invalid"}).status_code == 404
        response = client.post(root + f"/cards/{card['id']}/checklists", json={"title": "Checklist"})
        assert response.status_code == 201
        checklist_id = response.json()["checklist"]["id"]
        item = client.post(root + f"/checklists/{checklist_id}/items", json={"body": "Verify"}).json()["item"]
        patch = root + f"/checklist-items/{item['id']}"
        assert client.patch(patch, json={"expected_revision": 1, "completed": True}).status_code == 200
        assert client.patch(patch, json={"expected_revision": 1, "completed": False}).status_code == 409
        assert client.get(root + f"/cards/{card['id']}").json()["card"]["checklists"][0]["items"][0]["completed"] == 1
        assert client.post(patch + "/delete", json={"expected_revision": 2}).status_code == 200
        assert client.post(root + f"/checklists/{checklist_id}/delete", json={"expected_revision": 1}).status_code == 200

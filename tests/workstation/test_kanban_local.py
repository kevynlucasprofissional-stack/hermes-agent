"""Risk-focused tests for the independent Workstation Kanban MVP."""
import importlib.util
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from workstation import kanban_local as board


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "own" / "board.sqlite"


def test_create_move_edit_persist_independent_of_upstream(db_path):
    with board.database(db_path) as db:
        first = board.create_board(db, "Trabalho")
        columns = first["columns"]
        card = board.create_card(db, first["id"], columns[0]["id"], "Missão")
        assert card["revision"] == 1
        moved = board.move_card(db, card["id"], columns[1]["id"], 1)
        assert moved["revision"] == 2
        assert moved["column_id"] == columns[1]["id"]
        edited = board.update_card(db, card["id"], "Missão A", "Descrição", 2)
        assert edited["revision"] == 3
        with pytest.raises(board.BoardConflict):
            board.move_card(db, card["id"], columns[2]["id"], 1)
        with pytest.raises(board.BoardError):
            board.move_card(db, card["id"], "other-board-column", 3)
    with board.database(db_path) as db:
        snapshot = board.get_board(db, first["id"])
        assert snapshot["columns"][1]["cards"][0]["title"] == "Missão A"
        assert snapshot["columns"][1]["cards"][0]["description"] == "Descrição"
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_moves_reindex_without_unique_conflict(db_path):
    with board.database(db_path) as db:
        root = board.create_board(db, "Reorder")
        source, target = [c["id"] for c in root["columns"][:2]]
        cards = [board.create_card(db, root["id"], source, str(i)) for i in range(3)]
        board.move_card(db, cards[1]["id"], target, 1)
        snapshot = board.get_board(db, root["id"])
        assert [c["title"] for c in snapshot["columns"][0]["cards"]] == ["0", "2"]
        assert [c["position"] for c in snapshot["columns"][0]["cards"]] == [0, 1]


def test_http_contract_and_profile_home(tmp_path, monkeypatch):
    monkeypatch.setattr(board, "get_hermes_home", lambda: tmp_path)
    path = Path(__file__).resolve().parents[2] / "plugins" / "workstation-board" / "dashboard" / "plugin_api.py"
    spec = importlib.util.spec_from_file_location("workstation_board_plugin_api", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = FastAPI()
    app.include_router(module.router, prefix="/api/plugins/workstation-board")
    with TestClient(app) as client:
        base = "/api/plugins/workstation-board"
        created = client.post(base + "/boards", json={"name": "Minha área"})
        assert created.status_code == 201, created.text
        board_id = created.json()["board"]["id"]
        original_column = created.json()["board"]["columns"][0]["id"]
        target_column = created.json()["board"]["columns"][1]["id"]
        posted = client.post(base + f"/boards/{board_id}/cards",
                             json={"column_id": original_column, "title": "Uma tarefa"})
        assert posted.status_code == 201, posted.text
        card = posted.json()["card"]
        moved = client.post(base + f"/cards/{card['id']}/move",
                            json={"column_id": target_column, "expected_revision": 1})
        assert moved.status_code == 200, moved.text
        stale = client.post(base + f"/cards/{card['id']}/move",
                            json={"column_id": original_column, "expected_revision": 1})
        assert stale.status_code == 409
        fetched = client.get(base + f"/boards/{board_id}")
        assert fetched.status_code == 200
        assert fetched.json()["board"]["columns"][1]["cards"][0]["title"] == "Uma tarefa"
        assert (tmp_path / "workstation" / "board.sqlite").exists()

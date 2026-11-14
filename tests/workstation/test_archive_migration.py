"""Soft archive and restoration preserve independent Workstation records."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pathlib import Path
import importlib.util
from workstation import kanban_local as board


def test_archive_restore_and_cas(tmp_path):
    path = tmp_path / "db.sqlite"
    with board.database(path) as conn:
        base = board.create_board(conn, "Base")
        col = base["columns"][0]
        card = board.create_card(conn, base["id"], col["id"], "Keep")
        archived = board.set_archived(conn, "card", card["id"], 1, True)
        assert archived["revision"] == 2
        assert all(not col["cards"] for col in board.get_board(conn, base["id"])["columns"])
        assert board.get_board(conn, base["id"], True)["columns"][0]["cards"][0]["archived"] == 1
        with pytest.raises(board.BoardConflict):
            board.set_archived(conn, "card", card["id"], 1, False)
        board.set_archived(conn, "card", card["id"], 2, False)
        assert board.get_board(conn, base["id"])["columns"][0]["cards"][0]["id"] == card["id"]
        board.set_archived(conn, "column", col["id"], 1, True)
        assert col["id"] not in [x["id"] for x in board.get_board(conn, base["id"])["columns"]]
        board.set_archived(conn, "column", col["id"], 2, False)
        board.set_archived(conn, "board", base["id"], 1, True)
        assert board.list_boards(conn) == []
        assert len(board.list_boards(conn, True)) == 1
        board.set_archived(conn, "board", base["id"], 2, False)
        assert board.get_board(conn, base["id"])["columns"][0]["cards"][0]["title"] == "Keep"
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    with board.database(path) as conn:
        assert len(board.get_board(conn, base["id"])["columns"][0]["cards"]) == 1


def test_rest_archive_endpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(board, "get_hermes_home", lambda: tmp_path)
    p = Path(__file__).resolve().parents[2] / "plugins/workstation-board/dashboard/plugin_api.py"
    spec = importlib.util.spec_from_file_location("board_archive_api", p)
    plugin = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plugin)
    app = FastAPI()
    app.include_router(plugin.router, prefix="/api/plugins/workstation-board")
    root = "/api/plugins/workstation-board"
    with TestClient(app) as client:
        base = client.post(root + "/boards", json={"name": "Test"}).json()["board"]
        target = root + "/archive/board/" + base["id"]
        assert client.patch(target, json={"expected_revision": 1, "archived": True}).status_code == 200
        assert client.get(root + "/boards").json()["boards"] == []
        assert len(client.get(root + "/boards?include_archived=true").json()["boards"]) == 1
        assert client.patch(target, json={"expected_revision": 1, "archived": False}).status_code == 409
        assert client.patch(target, json={"expected_revision": 2, "archived": False}).status_code == 200

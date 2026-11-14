"""Legacy Database migration and reorder safety."""
import sqlite3

import pytest
from workstation import kanban_local as board


def test_existing_sqlite_upgrades_without_losing_cards(tmp_path):
    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript("""
CREATE TABLE boards (id TEXT PRIMARY KEY,name TEXT NOT NULL,created_at INTEGER NOT NULL);
CREATE TABLE columns (id TEXT PRIMARY KEY,board_id TEXT NOT NULL,name TEXT NOT NULL,
  position INTEGER NOT NULL,UNIQUE(board_id,position));
CREATE TABLE cards (id TEXT PRIMARY KEY,board_id TEXT NOT NULL,column_id TEXT NOT NULL,
  title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',position INTEGER NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,
  UNIQUE(column_id,position));
INSERT INTO boards VALUES('b','Original',1);
INSERT INTO columns VALUES('c','b','Lista',0);
INSERT INTO cards VALUES('k','b','c','Preservar','Descricao',0,1,1,1);
""")
    for _ in range(2):
        with board.database(path) as db:
            card = board.get_board(db, "b")["columns"][0]["cards"][0]
            assert (card["id"], card["description"], card["revision"], card["archived"]) == ("k", "Descricao", 1, 0)
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    with board.database(path) as db:
        assert board.create_card(db, "b", "c", "Novo")["position"] == 1


def test_cross_board_reorder_rejects_without_mutation(tmp_path):
    with board.database(tmp_path / "reorder.sqlite") as db:
        b1, b2 = board.create_board(db, "A"), board.create_board(db, "B")
        col1, col2 = b1["columns"][:2]
        cards = [board.create_card(db, b1["id"], col1["id"], str(i)) for i in range(3)]
        with pytest.raises(board.BoardError):
            board.reorder_card(db, cards[0]["id"], b2["columns"][0]["id"], 1)
        with pytest.raises(board.BoardError):
            board.reorder_column(db, col1["id"], 1, b2["columns"][0]["id"])
        moved = board.reorder_card(db, cards[0]["id"], col1["id"], 1)
        assert [c["id"] for c in board.get_board(db, b1["id"])["columns"][0]["cards"]] == [cards[1]["id"], cards[2]["id"], cards[0]["id"]]
        board.reorder_card(db, moved["id"], col2["id"], 2)
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_checklist_item_and_list_reorder_with_revisions(tmp_path):
    with board.database(tmp_path / "checklist.sqlite") as db:
        base = board.create_board(db, "Check")
        card = board.create_card(db, base["id"], base["columns"][0]["id"], "Ticket")
        lists = [board.create_checklist(db, card["id"], str(i)) for i in range(3)]
        moved = board.reorder_checklist(db, lists[2]["id"], 1, lists[0]["id"])
        assert [x["title"] for x in board.list_checklists(db, card["id"])] == ["2", "0", "1"]
        with pytest.raises(board.BoardConflict):
            board.reorder_checklist(db, lists[2]["id"], 1)
        items = [board.create_checklist_item(db, moved["id"], str(i)) for i in range(3)]
        moved_item = board.reorder_checklist_item(db, items[2]["id"], 1, items[0]["id"])
        assert [x["body"] for x in board.list_checklists(db, card["id"])[0]["items"]] == ["2", "0", "1"]
        with pytest.raises(board.BoardConflict):
            board.reorder_checklist_item(db, items[2]["id"], 1)
        foreign = board.create_checklist_item(db, lists[0]["id"], "foreign")
        with pytest.raises(board.BoardError):
            board.reorder_checklist_item(db, moved_item["id"], 2, foreign["id"])
        assert [x["body"] for x in board.list_checklists(db, card["id"])[0]["items"]] == ["2", "0", "1"]
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_checklist_reorder_http_contract(tmp_path, monkeypatch):
    import importlib.util
    from pathlib import Path
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    monkeypatch.setattr(board, "get_hermes_home", lambda: tmp_path)
    path = Path(__file__).resolve().parents[2] / "plugins/workstation-board/dashboard/plugin_api.py"
    spec = importlib.util.spec_from_file_location("board_s02_api", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    app = FastAPI()
    app.include_router(module.router, prefix="/api/plugins/workstation-board")
    root = "/api/plugins/workstation-board"
    with TestClient(app) as client:
        base = client.post(root + "/boards", json={"name": "Test"}).json()["board"]
        card = client.post(root + f"/boards/{base['id']}/cards",
                           json={"column_id": base["columns"][0]["id"], "title": "Review"}).json()["card"]
        one = client.post(root + f"/cards/{card['id']}/checklists",
                          json={"title": "One"}).json()["checklist"]
        two = client.post(root + f"/cards/{card['id']}/checklists",
                          json={"title": "Two"}).json()["checklist"]
        result = client.post(root + f"/checklists/{two['id']}/reorder",
                             json={"expected_revision": 1, "before_id": one["id"]})
        assert result.status_code == 200, result.text
        assert client.post(root + f"/checklists/{two['id']}/reorder",
                           json={"expected_revision": 1}).status_code == 409
        item_a = client.post(root + f"/checklists/{two['id']}/items",
                             json={"body": "A"}).json()["item"]
        item_b = client.post(root + f"/checklists/{two['id']}/items",
                             json={"body": "B"}).json()["item"]
        assert client.post(root + f"/checklist-items/{item_b['id']}/reorder",
                           json={"expected_revision": 1, "before_id": item_a["id"]}).status_code == 200
        details = client.get(root + f"/cards/{card['id']}").json()["card"]
        assert [x["title"] for x in details["checklists"]] == ["Two", "One"]
        assert [x["body"] for x in details["checklists"][0]["items"]] == ["B", "A"]

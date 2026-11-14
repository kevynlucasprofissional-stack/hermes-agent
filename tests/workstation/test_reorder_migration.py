"""Stable reordering without duplicate positions or lost records."""
import pytest
from workstation import kanban_local as db


def test_card_and_column_reordering(tmp_path):
    with db.database(tmp_path / "database.sqlite") as conn:
        board = db.create_board(conn, "Ops")
        a, b, c = board["columns"]
        cards = [db.create_card(conn, board["id"], a["id"], f"Card {n}") for n in range(3)]
        moved = db.reorder_card(conn, cards[2]["id"], a["id"], 1, cards[0]["id"])
        ordered = db.get_board(conn, board["id"])
        assert [x["id"] for x in ordered["columns"][0]["cards"]] == [cards[2]["id"], cards[0]["id"], cards[1]["id"]]
        with pytest.raises(db.BoardConflict):
            db.reorder_card(conn, cards[2]["id"], a["id"], 1)
        with pytest.raises(db.BoardError):
            db.reorder_card(conn, cards[1]["id"], b["id"], 1, "wrong")
        moved_again = db.reorder_card(conn, moved["id"], b["id"], 2)
        assert moved_again["column_id"] == b["id"]
        assert [x["position"] for x in db.get_board(conn, board["id"])["columns"][0]["cards"]] == [0, 1]
        assert [x["position"] for x in db.get_board(conn, board["id"])["columns"][1]["cards"]] == [0]
        db.reorder_column(conn, c["id"], 1, a["id"])
        assert [x["id"] for x in db.get_board(conn, board["id"])["columns"]] == [c["id"], a["id"], b["id"]]
        with pytest.raises(db.BoardConflict):
            db.reorder_column(conn, c["id"], 1)
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_reorder_http_contract(tmp_path, monkeypatch):
    from pathlib import Path
    import importlib.util
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    monkeypatch.setattr(db, "get_hermes_home", lambda: tmp_path)
    path = Path(__file__).resolve().parents[2] / "plugins/workstation-board/dashboard/plugin_api.py"
    spec = importlib.util.spec_from_file_location("reorder_board_api", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/workstation-board")
    root = "/api/plugins/workstation-board"
    with TestClient(app) as c:
        board = c.post(root + "/boards", json={"name": "HTTP"}).json()["board"]
        col = board["columns"][0]
        cards = [c.post(root + f"/boards/{board['id']}/cards",
                        json={"column_id": col["id"], "title": str(n)}).json()["card"] for n in range(2)]
        moved = c.post(root + f"/cards/{cards[1]['id']}/reorder", json={
            "target_column_id": col["id"], "before_id": cards[0]["id"], "expected_revision": 1})
        assert moved.status_code == 200, moved.text
        assert [x["id"] for x in c.get(root + f"/boards/{board['id']}").json()["board"]["columns"][0]["cards"]] == [
            cards[1]["id"], cards[0]["id"]]
        assert c.post(root + f"/cards/{cards[1]['id']}/reorder", json={
            "target_column_id": col["id"], "expected_revision": 1}).status_code == 409

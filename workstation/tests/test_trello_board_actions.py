"""TDD for read-only board actions: cursors, throttling, validation, bounded pages."""
from __future__ import annotations

import sqlite3

import pytest

from workstation.prefabs.trello import Credential, TrelloAccessError, TrelloClient
from workstation.trello_action_journal import (
    install_schema, load_checkpoint, poll_board_actions, read_events,
)

BOARD = "Edq32SNp"
def a(n):
    return {"id": f"{n:024x}", "type": "updateCard", "date": f"2026-10-{n:02}T12:00:00Z",
            "idMemberCreator": "member123", "data": {"card": {"id": "abc123"}}}


def fake_client(transport):
    return TrelloClient(credential=Credential("fake_key", "fake_token"), transport=transport)


def memory():
    conn = sqlite3.connect(":memory:")
    install_schema(conn)
    return conn


def test_board_actions_uses_official_get_and_safe_filtering():
    calls = []
    def transport(method, endpoint, query, form):
        calls.append((method, endpoint, query, form))
        return [a(2), a(1)]
    c = fake_client(transport)
    rows = c.board_actions("editorial", before="0123456789abcdef01234567", limit=2)
    assert [row["id"] for row in rows] == [a(2)["id"], a(1)["id"]]
    assert calls == [("GET", "/1/boards/" + BOARD + "/actions",
                      {"fields": "id,type,date,data,idMemberCreator", "limit": "2",
                       "before": "0123456789abcdef01234567"}, {})]


@pytest.mark.parametrize("arguments", [
    {"board": "../evil"}, {"board": "!"}, {"board": BOARD, "limit": 0},
    {"board": BOARD, "limit": 1001}, {"board": BOARD, "limit": True},
    {"board": BOARD, "before": "x/y"}, {"board": BOARD, "since": "not-a-cursor"}
])
def test_invalid_board_cursor_and_limit(arguments):
    def transport(*args): raise AssertionError("must fail before transport")
    with pytest.raises(ValueError):
        fake_client(transport).board_actions(**arguments)


def test_non_list_or_malformed_api_response_rejected():
    for bad in ({"unexpected": "response"}, ["invalid"], [{"id": "123"}]):
        client = fake_client(lambda *args: bad)
        with pytest.raises(TrelloAccessError):
            client.board_actions(BOARD)


def test_rate_limit_retries_bounded_only_on_429(monkeypatch):
    from workstation.prefabs import trello
    sleeps, calls = [], []
    monkeypatch.setattr(trello.time, "sleep", lambda t: sleeps.append(t))
    def transport(method, endpoint, query, form):
        calls.append(method)
        if len(calls) < 3:
            raise trello.TrelloRateLimitError(retry_after=0.1)
        return [a(1)]
    assert len(fake_client(transport).board_actions(BOARD)) == 1
    assert calls == ["GET"] * 3
    assert sleeps == [0.1, 0.1]
    def always_429(*args): raise trello.TrelloRateLimitError(retry_after=0)
    with pytest.raises(trello.TrelloRateLimitError):
        fake_client(always_429).board_actions(BOARD)


def test_poll_paginates_reverse_chronology_dedupes_and_persists_newest_cursor():
    full = [a(n) for n in range(5, 0, -1)]
    calls = []
    def transport(method, endpoint, query, form):
        assert method == "GET"
        calls.append(dict(query))
        candidates = [r for r in full
                      if not query.get("since") or r["id"] > query["since"]]
        if query.get("before"):
            candidates = [r for r in candidates if r["id"] < query["before"]]
        return candidates[:int(query["limit"])]
    c, conn = fake_client(transport), memory()
    first = poll_board_actions(c, conn, "editorial", page_size=2)
    assert first.inserted == 5
    assert load_checkpoint(conn, BOARD) == a(5)["id"]
    assert len(read_events(conn, BOARD)) == 5
    assert all("before" not in q or q["before"] for q in calls)
    assert calls[1]["before"] == a(4)["id"]
    assert poll_board_actions(c, conn, "editorial", page_size=2).inserted == 0
    full.insert(0, a(6))
    assert poll_board_actions(c, conn, "editorial", page_size=2).inserted == 1
    assert len(read_events(conn, BOARD)) == 6
    assert load_checkpoint(conn, BOARD) == a(6)["id"]


def test_page_2_failure_never_advances_checkpoint_or_partially_inserts():
    conn = memory()
    failures = [False]
    first_page = [a(4), a(3)]
    def transport(method, endpoint, query, form):
        if query.get("before"):
            if not failures[0]:
                failures[0] = True
                raise TrelloAccessError("intermediate fetch failed")
            return [a(2)]
        return first_page
    c = fake_client(transport)
    with pytest.raises(TrelloAccessError):
        poll_board_actions(c, conn, "editorial", page_size=2)
    assert load_checkpoint(conn, BOARD) is None
    assert read_events(conn, BOARD) == []
    assert poll_board_actions(c, conn, "editorial", page_size=2).inserted == 3


def test_bounded_poll_fails_closed_when_truncated_at_max_pages():
    conn = memory()
    full = [a(n) for n in (5, 4, 3, 2, 1)]
    def transport(method, endpoint, query, form):
        rows = [r for r in full if not query.get("before") or r["id"] < query["before"]]
        return rows[:int(query["limit"])]
    with pytest.raises(TrelloAccessError, match="window"):
        poll_board_actions(fake_client(transport), conn, BOARD, page_size=2, max_pages=2)
    assert load_checkpoint(conn, BOARD) is None and read_events(conn, BOARD) == []


def test_poll_uses_only_existing_kanban_bridge_connection(tmp_path, monkeypatch):
    from workstation.kanban import WorkstationKanbanBridge
    from workstation.trello_action_journal import poll_board_actions_into_kanban, load_checkpoint
    filename = tmp_path / 'hermes-canonical-fixture.sqlite'
    opens = []
    def canonical_connection(self):
        opens.append(self.board)
        return sqlite3.connect(filename)
    monkeypatch.setattr(WorkstationKanbanBridge, "get_connection", canonical_connection)
    calls = []
    def transport(method, endpoint, query, form):
        calls.append(method)
        return [a(1)] if len(calls) == 1 else []
    result = poll_board_actions_into_kanban(
        fake_client(transport), "editorial", kanban_board="fixture-board", page_size=2
    )
    assert opens == ["fixture-board"]
    assert calls == ["GET"]
    assert result.inserted == 1
    conn = sqlite3.connect(filename)
    assert load_checkpoint(conn, BOARD) == a(1)["id"]
    assert read_events(conn, BOARD)[0]["board_id"] == BOARD
    conn.close()


def test_unordered_remote_actions_fail_without_checkpoint():
    conn = memory()
    def transport(method, endpoint, query, form):
        return [a(1), a(3), a(2)]
    with pytest.raises(TrelloAccessError, match="order"):
        poll_board_actions(fake_client(transport), conn, BOARD, page_size=3)
    assert read_events(conn, BOARD) == []
    assert load_checkpoint(conn, BOARD) is None


def test_http_429_maps_to_typed_limit_without_exposing_token(monkeypatch):
    import urllib.error
    from workstation.prefabs import trello
    def fail_http(req, timeout):
        raise urllib.error.HTTPError(req.full_url, 429, 'Rate limit',
                                     {'Retry-After': '0.01'}, None)
    monkeypatch.setattr(trello.urllib.request, "urlopen", fail_http)
    waits = []
    monkeypatch.setattr(trello.time, "sleep", lambda n: waits.append(n))
    with pytest.raises(trello.TrelloRateLimitError) as err:
        TrelloClient(credential=Credential("SECRET_KEY", "SECRET_TOKEN")).board_actions(BOARD)
    assert waits == [0.01, 0.01]
    assert 'SECRET' not in str(err.value)

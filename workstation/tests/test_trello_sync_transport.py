"""Trello routing: authenticated admin -> API; normal member -> native Browser."""
import pytest

from workstation.prefabs.trello import TrelloClient, Credential, TrelloAccessError
from workstation.trello_sync_transport import route_for_board

BOARD = "6aefcc8e38ac0595e0035341"
MEMBER = "65e13416055b4548f2dbd077"


def fake(role="admin", *, closed=False, memberships=None, me=None, board=None):
    calls = []
    member_rows = memberships if memberships is not None else [
        {"idMember": MEMBER, "memberType": role, "unconfirmed": False, "deactivated": False}]
    def transport(method, endpoint, query, form):
        calls.append((method, endpoint))
        assert method == "GET" and not form
        if endpoint == "/1/members/me":
            return me if me is not None else {"id": MEMBER}
        if endpoint == f"/1/boards/{BOARD}":
            return board if board is not None else {"id": BOARD, "name": "Untrusted name",
                                                        "closed": closed}
        if endpoint == f"/1/boards/{BOARD}/memberships":
            return member_rows
        raise AssertionError("unexpected API endpoint")
    return TrelloClient(credential=Credential("fake", "fake"), transport=transport), calls


@pytest.mark.parametrize(("role","route"), [("admin","api"),("normal","browser"),("observer","hold")])
def test_role_selects_transport_without_any_api_writes(role, route):
    client, calls = fake(role)
    result = route_for_board(client, BOARD)
    assert result["transport"] == route
    assert len(calls) == 3
    assert all(method == "GET" for method, _ in calls)


def test_wrong_account_cannot_infer_permission_from_workspace_or_board_title():
    client, _ = fake(memberships=[{"idMember": "a"*24, "memberType": "admin"}])
    result = route_for_board(client, BOARD)
    assert result["transport"] == "hold"
    assert result["reason"] == "membership_unverified"


@pytest.mark.parametrize("memberships", [
    [], [{"idMember": MEMBER, "memberType": "admin", "deactivated": True}],
    [{"idMember": MEMBER, "memberType": "admin", "unconfirmed": True}],
    [{"idMember": MEMBER, "memberType": "admin"}]*2,
])
def test_missing_inactive_or_ambiguous_account_holds(memberships):
    client,_=fake(memberships=memberships)
    assert route_for_board(client,BOARD)["transport"]=="hold"


def test_closed_or_mismatched_board_fails_before_mutation():
    client,_=fake(closed=True)
    with pytest.raises(TrelloAccessError):
        route_for_board(client,BOARD)
    client,_=fake(board={"id":"f"*24,"name":"Untrusted name","closed":False})
    with pytest.raises(TrelloAccessError):
        route_for_board(client,BOARD)


def test_missing_or_malformed_identity_never_yields_role():
    client,_=fake(me={"id":"other"})
    with pytest.raises(ValueError):
        route_for_board(client,BOARD)
    client,_=fake(me={})
    with pytest.raises(TrelloAccessError):
        route_for_board(client,BOARD)


@pytest.mark.parametrize("board_id", ["../admin","abcd","",None,"a"*25])
def test_invalid_board_id_is_rejected_without_any_call(board_id):
    client,calls=fake()
    with pytest.raises(ValueError):
        route_for_board(client,board_id)
    assert calls==[]


def test_agent_route_holds_without_profile_credentials(monkeypatch):
    from workstation.prefabs.trello import Credential, TrelloAccessError
    from plugins.workstation_database_agent import _handle
    def missing():
        raise TrelloAccessError("test: no active profile")
    monkeypatch.setattr(Credential, "from_secret_scope", missing)
    import json
    out=json.loads(_handle("workstation_db_trello_route",
                          {"board_id":"6aefcc8e38ac0595e0035341"}))
    assert out["ok"] is False
    assert out["transport"]=="hold"
    assert out["reason"]=="trello_profile_credentials_unavailable"
    assert "token" not in str(out).lower()


def test_agent_route_binds_to_profile_authenticated_account(monkeypatch):
    import json
    from workstation.prefabs import trello
    from plugins.workstation_database_agent import _handle
    monkeypatch.setattr(trello.Credential,"from_secret_scope",
                        lambda: trello.Credential("dummy","dummy"))
    transport_calls=[]
    def fake(self,method,path,query=None,form=None):
        transport_calls.append((method,path))
        if path == "/1/members/me":
            return {"id":"65e13416055b4548f2dbd077"}
        if path.endswith("/memberships"):
            return [{"idMember":"65e13416055b4548f2dbd077","memberType":"normal"}]
        return {"id":"6aefcc8e38ac0595e0035341","closed":False}
    monkeypatch.setattr(trello.TrelloClient,"_request",fake)
    out=json.loads(_handle("workstation_db_trello_route",
                          {"board_id":"6aefcc8e38ac0595e0035341"}))
    assert out["ok"] and out["transport"]=="browser" and out["role"]=="normal"
    assert [x[0] for x in transport_calls]==["GET","GET","GET"]

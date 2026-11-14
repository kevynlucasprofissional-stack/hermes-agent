"""Select Trello transport from authenticated account membership, never board name.

API is allowed for board admins; ordinary members must use the native
agent-owned Hermes Browser. Missing, inconsistent or stale role evidence HOLDS.
No mutation is performed here.
"""
from __future__ import annotations

import re
from typing import Any
from workstation.prefabs.trello import TrelloClient, TrelloAccessError

_ID = re.compile(r"^[0-9a-fA-F]{24}$")


def _id(value: str, label: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"invalid {label}")
    return value


def route_for_board(client: TrelloClient, board_id: str) -> dict[str, Any]:
    """Read account, board, and membership using the same authenticated API client.

    This is a permissions routing decision, not proof of a successful operation.
    Never use workspace membership or a mutable display name as authorization.
    """
    board_id = _id(board_id, "board_id")
    me = client._request("GET", "/1/members/me", {"fields": "id"})
    board = client._request(
        "GET", f"/1/boards/{board_id}",
        {"fields": "id,name,closed,idMemberCreator"}
    )
    memberships = client._request(
        "GET", f"/1/boards/{board_id}/memberships",
        {"filter": "all"},
    )
    if not isinstance(me, dict) or not isinstance(me.get("id"), str):
        raise TrelloAccessError("authenticated Trello identity unavailable")
    user_id = _id(me["id"], "member_id")
    if (not isinstance(board, dict) or board.get("id") != board_id
            or board.get("closed") is not False
            or not isinstance(memberships, list)):
        raise TrelloAccessError("Trello board authority unavailable")
    own = [m for m in memberships if isinstance(m, dict)
           and m.get("idMember") == user_id]
    if len(own) != 1 or own[0].get("deactivated") is True or own[0].get("unconfirmed") is True:
        return {"transport": "hold", "reason": "membership_unverified", "board_id": board_id}
    role = own[0].get("memberType")
    if role == "admin":
        return {"transport": "api", "role": "admin",
                "board_id": board_id, "member_id": user_id}
    if role == "normal":
        return {"transport": "browser", "role": "normal",
                "board_id": board_id, "member_id": user_id}
    return {"transport": "hold", "reason": "membership_role_unknown", "board_id": board_id}

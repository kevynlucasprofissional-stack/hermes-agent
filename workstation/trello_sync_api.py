"""QA-only Trello REST title synchronization through existing scoped client and journal."""
from __future__ import annotations

import hashlib
import json
import re
from contextlib import closing
from pathlib import Path
from typing import Any

from workstation.acirv_datasets import get_record
from workstation.dataset_edits import _connect
from workstation.prefabs.trello import TrelloAccessError, TrelloClient
from workstation.trello_sync_push import get_intent, install, now, set_state, shortlink
from workstation.trello_sync_reconcile import compare_card, read_reviews, save_review
from workstation.trello_sync_transport import route_for_board

QA_BOARD_ID = "6aefcc8e38ac0595e0035341"
QA_BOARD_NAME = "Hermes Sync QA"
CARD_ID = re.compile(r"^[a-f0-9]{24}$")
RUN_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,100}$")


def _local(home: Path | None, card_id: str, expected_revision: int | None = None) -> dict:
    if not isinstance(card_id, str) or not CARD_ID.fullmatch(card_id):
        raise ValueError("invalid card_id")
    detail = get_record(home, "trello", "cards", card_id)
    card = detail["record"]
    board_id = str(card.get("board_id") or "").split("/")[-1]
    if board_id != QA_BOARD_ID or card.get("board_name") != QA_BOARD_NAME:
        raise ValueError("qa_board_only")
    if (card.get("status") != "em_aberto" or detail.get("source_conflict_fields")
            or expected_revision is not None
            and detail.get("local_revision") != expected_revision):
        raise ValueError("local_state_changed")
    return detail


def _remote(client: TrelloClient, card_id: str) -> dict:
    result = client._request(
        "GET", f"/1/cards/{card_id}", {"fields": "id,name,idBoard,closed,shortUrl"})
    if (not isinstance(result, dict) or result.get("id") != card_id
            or result.get("idBoard") != QA_BOARD_ID
            or result.get("closed") is not False
            or not isinstance(result.get("name"), str)
            or not isinstance(result.get("shortUrl"), str)):
        raise TrelloAccessError("QA card identity or status unverified")
    return result


def _admin(client: TrelloClient) -> str:
    route = route_for_board(client, QA_BOARD_ID)
    if route["transport"] != "api" or route.get("role") != "admin":
        raise TrelloAccessError("Trello admin board authorization unavailable")
    return route["member_id"]


def plan_api_title(
    home: Path | None, client: TrelloClient, *, card_id: str, run_id: str
) -> dict[str, Any]:
    """Only GETs remote state; record immutable local observation, no external effects."""
    if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
        raise ValueError("invalid run_id")
    card = _local(home, card_id)["record"]
    member_id = _admin(client)
    remote = _remote(client, card_id)
    if shortlink(remote["shortUrl"]) != shortlink(card["url"]):
        raise TrelloAccessError("remote card shortlink mismatch")
    baseline: dict[str, str] = {}
    for record in read_reviews(home, card_id):
        plan = record["plan"]
        if (plan.get("api_observed") and plan.get("api_board_id") == QA_BOARD_ID
                and plan.get("api_member_id") == member_id
                and plan.get("remote_open_verified")):
            for field, diff in plan.get("fields", {}).items():
                if diff.get("action") == "equal" and "value" in diff:
                    baseline.setdefault(field, diff["value"])
    plan = compare_card(
        local=card, remote={"name": remote["name"]},
        baseline=baseline or None, observed_fields=["name"],
        remote_open_verified=True)
    plan.update({"api_observed": True, "api_board_id": QA_BOARD_ID,
                 "api_member_id": member_id, "transport": "api"})
    review = save_review(home, run_id=run_id, card_id=card_id,
                         source_url=card["url"], plan=plan)
    return {"ok": review["ok"], "review": review, "plan": plan,
            "external_trello_writes": 0}


def push_api_title(
    home: Path | None, client: TrelloClient, *, card_id: str,
    review_run_id: str, expected_revision: int,
) -> dict[str, Any]:
    """Single PUT max, durable intent before PUT, no retry after ambiguous result."""
    if (not isinstance(review_run_id, str) or not RUN_ID.fullmatch(review_run_id)
            or type(expected_revision) is not int or expected_revision < 1):
        raise ValueError("invalid API push arguments")
    if not isinstance(card_id, str) or not CARD_ID.fullmatch(card_id):
        raise ValueError("invalid card_id")
    old = get_intent(home, card_id, review_run_id)
    if old:
        return {"ok": old["state"] == "verified", "status": old["state"],
                "intent_id": old["intent_id"], "redispatched": False}
    detail = _local(home, card_id, expected_revision)
    local = detail["record"]
    with closing(_connect(home)) as conn:
        try:
            row = conn.execute(
                "SELECT plan_json,source_url FROM trello_sync_reviews "
                "WHERE card_id=? AND run_id=?", (card_id, review_run_id)).fetchone()
        except Exception as exc:
            if "no such table" in str(exc):
                row = None
            else:
                raise
    if row is None:
        return {"ok": False, "error": "review_missing"}
    plan = json.loads(row["plan_json"])
    diff = plan.get("fields", {}).get("name", {})
    if (plan.get("api_observed") is not True
            or plan.get("api_board_id") != QA_BOARD_ID
            or plan.get("remote_open_verified") is not True
            or plan.get("ready_for_external_write") is not False
            or diff.get("action") != "push"
            or "baseline" not in diff):
        return {"ok": False, "error": "review_not_qualified"}
    target, old_name = local.get("name"), diff.get("remote")
    if (not isinstance(target, str) or not target.strip() or len(target) > 500
            or not isinstance(old_name, str) or not old_name.strip()
            or len(old_name) > 500 or old_name == target or diff.get("local") != target):
        return {"ok": False, "error": "local_title_not_reviewed"}
    member_id = _admin(client)
    if member_id != plan.get("api_member_id"):
        return {"ok": False, "error": "api_account_changed"}
    before = _remote(client, card_id)
    if (before["name"] != old_name
            or shortlink(before["shortUrl"]) != shortlink(local["url"])
            or shortlink(row["source_url"]) != shortlink(local["url"])):
        return {"ok": False, "error": "remote_title_changed"}

    intent = hashlib.sha256((card_id + ":" + review_run_id).encode()).hexdigest()[:32]
    operation_id = "trello-qa-api-title-" + intent
    with closing(_connect(home)) as conn:
        install(conn)
        conn.execute("BEGIN IMMEDIATE")
        try:
            pending = conn.execute(
                "SELECT intent_id FROM trello_title_push_intents "
                "WHERE card_id=? AND state IN ('prepared','dispatching','typed','uncertain')",
                (card_id,)).fetchone()
            if pending:
                conn.commit()
                return {"ok": False, "error": "card_has_unresolved_intent",
                        "intent_id": pending["intent_id"]}
            existing = conn.execute(
                "SELECT intent_id,state FROM trello_title_push_intents "
                "WHERE card_id=? AND review_run_id=?", (card_id, review_run_id)).fetchone()
            if existing:
                conn.commit()
                return {"ok": existing["state"] == "verified",
                        "status": existing["state"], "intent_id": existing["intent_id"],
                        "redispatched": False}
            stamp = now()
            conn.execute(
                "INSERT INTO trello_title_push_intents("
                "intent_id,card_id,review_run_id,browser_task_id,operation_id,"
                "expected_revision,remote_before,target_title,state,created_at,updated_at)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (intent, card_id, review_run_id, "api", operation_id,
                 expected_revision, old_name, target, "prepared", stamp, stamp))
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # PREPARED is durable, including if the process dies before dispatch.
    current = get_record(home, "trello", "cards", card_id)
    if (current.get("local_revision") != expected_revision
            or current["record"].get("name") != target
            or current["record"].get("status") != "em_aberto"):
        set_state(home, intent, "uncertain", reason="local_changed_after_intent")
        return {"ok": False, "status": "uncertain", "intent_id": intent,
                "reason": "local_changed_after_intent", "redispatched": False}
    set_state(home, intent, "dispatching")
    failure = None
    receipt = None
    try:
        response = client._request(
            "PUT", f"/1/cards/{card_id}", form={"name": target})
        if not isinstance(response, dict) or response.get("id") != card_id or response.get("name") != target:
            failure = "api_response_unverified"
        else:
            receipt = {"operation_id": operation_id, "card_id": card_id,
                       "accepted_title": target}
    except Exception:
        failure = "api_put_result_unknown"

    try:
        after = _remote(client, card_id)
        if (after.get("name") != target or after.get("idBoard") != QA_BOARD_ID
                or shortlink(after["shortUrl"]) != shortlink(before["shortUrl"])):
            failure = failure or "api_readback_mismatch"
    except Exception:
        after = None
        failure = failure or "api_readback_unavailable"
    state = "verified" if failure is None else "uncertain"
    set_state(home, intent, state, [receipt] if receipt else [],
              after, failure)
    return {"ok": state == "verified", "status": state,
            "intent_id": intent, "reason": failure, "redispatched": False}

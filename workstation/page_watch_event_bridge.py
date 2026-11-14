"""P06 page_changed -> P04 authority seam. Deliberately closed until P04 owner qualifies source.

DO NOT impersonate a Trello action or call enqueue() directly: P04's route
contract currently authorizes only source='trello'. This module is a check,
not a delivery mechanism, while P02/P04 and the Browser gate are HOLD.
"""
from __future__ import annotations

import re
from typing import Any

_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_SHA = re.compile(r"^[a-f0-9]{64}$")


def check_page_event_candidate(event: dict[str, Any], route_id: str) -> dict[str, str]:
    """Validate the minimum metadata envelope with no page content or selectors."""
    if not isinstance(event, dict) or not _ID.fullmatch(route_id):
        raise ValueError("invalid_page_watch_route")
    required = {
        "source", "type", "event_id", "watch_id", "session_id", "tab_id",
        "origin", "route_id", "fingerprint", "observed_at", "previous", "current",
    }
    if set(event) != required or event.get("source") != "page_watch" or event.get("type") != "page_changed":
        raise ValueError("invalid_page_watch_event")
    if event.get("route_id") != route_id:
        raise PermissionError("page_watch_route_mismatch")
    for field in ("event_id", "fingerprint"):
        if not isinstance(event[field], str) or not _SHA.fullmatch(event[field]):
            raise ValueError("invalid_page_watch_fingerprint")
    for field in ("watch_id", "session_id", "tab_id"):
        if not isinstance(event[field], str) or not _ID.fullmatch(event[field]):
            raise ValueError("invalid_page_watch_id")
    for field in ("previous", "current"):
        if type(event[field]) is not int or not 0 <= event[field] <= 1000:
            raise ValueError("invalid_page_watch_count")
    from urllib.parse import urlsplit
    origin = event["origin"]
    if not isinstance(origin, str) or len(origin) > 250:
        raise ValueError("invalid_page_watch_origin")
    parsed = urlsplit(origin)
    if parsed.scheme not in ("https", "http") or not parsed.netloc or parsed.username or parsed.password or (
            parsed.path or parsed.query or parsed.fragment):
        raise ValueError("invalid_page_watch_origin")
    from datetime import datetime
    try:
        observed = datetime.fromisoformat(event["observed_at"].replace("Z", "+00:00"))
        if observed.tzinfo is None:
            raise ValueError("timezone required")
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("invalid_page_watch_time") from exc
    return {
        "source": "page_watch",
        "event_id": event["event_id"],
        "event_type": "page_changed",
        "object_id": event["watch_id"],
        "observed_at": event["observed_at"],
        "route_id": route_id,
        "fingerprint": event["fingerprint"],
    }


def page_watch_outbox_gate(event: dict[str, Any], route_id: str) -> dict[str, str]:
    """P04 is Trello-only; no outbox write or Cron call is authorized at P06."""
    candidate = check_page_event_candidate(event, route_id)
    return {
        "state": "HOLD",
        "reason": "P04_PAGE_WATCH_SOURCE_NOT_QUALIFIED",
        "source": candidate["source"],
        "event_id": candidate["event_id"],
        "route_id": candidate["route_id"],
    }


def accept_authorized_page_watch(
    conn, profile_home, *, watch_id: str, event_id: str, route_id: str,
    dispatch: bool = False, get_job=None, execute=None,
) -> dict[str,str]:
    """Explicit trusted config route, canonical occurrence and existing P04 outbox.

    No default enabled route. Deliver via the existing local Cron only when
    an operator approved the route in profile config; uncertain results NEVER retry.
    """
    from pathlib import Path
    from workstation.business_event_dispatch import (
        load_authorized_routes, enqueue_page_watch_occurrence, dispatch_pending,
    )
    routes = load_authorized_routes(Path(profile_home))
    authorized = routes.get(route_id)
    if authorized is None or authorized.source != "page_watch":
        return {"state":"HOLD","reason":"PAGE_WATCH_ROUTE_NOT_AUTHORIZED"}
    inserted = enqueue_page_watch_occurrence(conn,watch_id,event_id,authorized)
    if not inserted:
        return {"state":"DUPLICATE_IGNORED","event_id":event_id}
    if not dispatch:
        return {"state":"PENDING","event_id":event_id}
    return dispatch_pending(conn,routes={route_id:authorized},
                            get_job=get_job,execute=execute) or {"state":"PENDING","event_id":event_id}


def main() -> int:
    """One-shot authorized bridge. No listener, timer, or automatic retry."""
    import argparse
    import json
    import sys
    from workstation.business_event_dispatch import with_kanban_connection
    parser=argparse.ArgumentParser()
    parser.add_argument("--profile-home",required=True)
    parser.add_argument("--watch-id",required=True)
    parser.add_argument("--event-id",required=True)
    parser.add_argument("--route-id",required=True)
    args=parser.parse_args()
    try:
        output=with_kanban_connection(lambda conn: accept_authorized_page_watch(
            conn,args.profile_home,watch_id=args.watch_id,event_id=args.event_id,
            route_id=args.route_id,dispatch=True,
        ))
        print(json.dumps(output,ensure_ascii=False))
        return 0 if output.get("state") in ("PENDING","UNCERTAIN","FAILED_SAFE","DUPLICATE_IGNORED") else 2
    except Exception as exc:
        # No secrets or page contents.
        print(json.dumps({"state":"HOLD","reason":type(exc).__name__}),file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

"""Pure fail-closed verifier for one previously authorized WhatsApp self-chat canary.

Consumes observations from the *native task-owned isolated DOM inspector*.
Never sends a message, examines private WhatsApp stores, or grants send authority.
"""

from __future__ import annotations

import re
from typing import Any


VALID_ACKS = frozenset({"sent", "delivered", "read"})
ID_PATTERN = re.compile(r"[0-9A-Fa-f]{22,64}\Z")


def assess_causal_dom_receipt(
    *,
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    marker: str,
    expected_author: str,
    self_chat_verified: bool,
    click_once_confirmed: bool,
) -> dict[str, Any]:
    """Attest a *new* message/status observed in the DOM, not server receipt.

    The caller must independently validate task/tab/origin, self-chat UI identity,
    no in-flight concurrent sender, baseline completeness, and the single click.
    """
    def hold(reason: str) -> dict[str, Any]:
        return {"status": "HOLD", "reason": reason,
                "can_send": False, "independently_verified": False}

    if not self_chat_verified:
        return hold("SELF_CHAT_IDENTITY_UNVERIFIED")
    if not click_once_confirmed:
        return hold("DISPATCH_UNVERIFIED")
    if (not isinstance(marker, str) or len(marker) < 16
            or not isinstance(expected_author, str) or not expected_author.strip()):
        return hold("MARKER_OR_AUTHOR_REQUIRED")

    if not isinstance(before, list) or not isinstance(after, list):
        return hold("INSPECTION_INVALID")

    def validate(rows: list[dict[str, Any]]) -> bool:
        ids: set[str] = set()
        if len(rows) >= 64:
            return False
        for row in rows:
            if not isinstance(row, dict):
                return False
            mid = row.get("id")
            if not isinstance(mid, str) or not ID_PATTERN.fullmatch(mid) or mid in ids:
                return False
            ids.add(mid)
            if not isinstance(row.get("body", ""), str):
                return False
        return True

    if not before or not after or not validate(before) or not validate(after):
        return hold("INSPECTION_INCOMPLETE_OR_AMBIGUOUS")
    if any(marker in row["body"] for row in before):
        return hold("MARKER_ALREADY_PRESENT")
    old_ids = {row["id"] for row in before}
    matches = [row for row in after if marker in row["body"]]
    if len(matches) != 1:
        return hold("NEW_MESSAGE_NOT_UNIQUE")
    row = matches[0]
    if row["id"] in old_ids:
        return hold("MESSAGE_ID_NOT_NEW")
    if str(row.get("author", "")).strip().casefold() != expected_author.strip().casefold():
        return hold("OUTBOUND_AUTHOR_UNVERIFIED")
    ack = row.get("ack")
    if ack not in VALID_ACKS:
        return hold("CAUSAL_ACK_MISSING")

    return {
        "status": "CAUSAL_DOM_RECEIPT_OBSERVED",
        "reason": "DOM_STATUS_NOT_INDEPENDENT_SERVER_ACK",
        "ack": ack,
        "new_matching_messages": 1,
        "can_send": False,
        "independently_verified": False,
    }

"""Read-only, task-owned diagnostic for WhatsApp DOM evidence availability.

Never certifies a send. Never navigates, opens a chat, writes data or returns PII.
The native isolated-world inspector is the only permitted transport.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable
from urllib.parse import urlsplit

_INSPECT_LIMIT = 64
_ATTRIBUTES = [
    "data-testid", "data-chat-id", "data-id", "data-recipient-id",
    "data-direction", "data-ack", "aria-label",
]
_SELECTOR = (
    '[data-testid="conversation-info-header"], [data-chat-id], '
    '[data-testid="msg-container"], [data-id^="true_"], '
    '[data-id]:has([data-testid="msg-container"]), '
    '[data-id] [data-testid="msg-meta"] [aria-label], '
    '[data-testid*="contact-info-subtitle"], '
    '[data-testid="conversation-compose-box-input"]'
)
_STATUS_PARENT_SELECTOR = (
    '[data-id]:has([data-testid="msg-container"])'
    ':has([data-testid="msg-meta"] [aria-label])'
)


def _hold(reason: str, **counts: int) -> dict[str, Any]:
    return {
        "status": "HOLD", "reason": reason,
        "can_send": False, "independently_verified": False, **counts,
    }


def assess_historical_author_direction(
    *,
    own_chat_authors: list[str],
    status_chat_authors: list[str],
    no_status_chat_authors: list[str],
) -> dict[str, Any]:
    """Compare historical text-message authors, never infer a new send receipt.

    Input labels originate from scoped, owner-attested native DOM inspections.
    All names stay in memory. The return value contains counts and status only.
    """
    def hold(reason: str) -> dict[str, Any]:
        return _hold(reason)

    if not own_chat_authors:
        return hold("SELF_AUTHOR_UNVERIFIED")
    if (len(own_chat_authors) < 2 or len(status_chat_authors) < 2
            or len(no_status_chat_authors) < 2):
        return hold("HISTORICAL_SAMPLE_INSUFFICIENT")

    def parse(labels: list[str]) -> set[str] | None:
        parsed: set[str] = set()
        for label in labels:
            if not isinstance(label, str):
                return None
            match = re.fullmatch(r"\[[^\]]{3,120}\]\s+(.+):\s*", label)
            if not match:
                return None
            name = " ".join(match.group(1).split()).casefold()
            if not name:
                return None
            parsed.add(name)
        return parsed

    own = parse(own_chat_authors)
    with_status = parse(status_chat_authors)
    without_status = parse(no_status_chat_authors)
    if own is None or with_status is None or without_status is None:
        return hold("HISTORICAL_AUTHOR_FORMAT_UNVERIFIED")
    if len(own) != 1:
        return hold("SELF_AUTHOR_UNVERIFIED")
    if (len(with_status) != 1 or len(without_status) != 1
            or own != with_status or own == without_status):
        return hold("HISTORICAL_AUTHOR_AMBIGUOUS")

    return {
        "status": "HISTORICAL_AUTHOR_MATCH",
        "reason": "HISTORICAL_TEXT_ONLY_NOT_A_SEND_RECEIPT",
        "self_author_samples": len(own_chat_authors),
        "outbound_author_samples": len(status_chat_authors),
        "other_author_samples": len(no_status_chat_authors),
        "can_send": False,
        "independently_verified": False,
    }


def _ui_recipient_phone_consistent(items: list[Any]) -> bool:
    """Compare two UI surfaces only; neither proves send authorization.

    Contact details must be open. Never return, hash, or persist phone values.
    A missing or ambiguous candidate fails closed.
    """
    pattern = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
    panel: list[set[str]] = []
    composer: list[set[str]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        attrs = item.get("attributes") or {}
        if not isinstance(attrs, dict):
            continue
        testid = str(attrs.get("data-testid") or "")
        if not (testid.startswith("contact-info-subtitle")
                or testid == "conversation-compose-box-input"):
            continue
        source = " ".join(str(value or "") for value in (
            item.get("text"), attrs.get("aria-label"), attrs.get("title")))
        numbers = {
            re.sub(r"\D", "", found.group())
            for found in pattern.finditer(source)
            if 10 <= len(re.sub(r"\D", "", found.group())) <= 15
        }
        if testid.startswith("contact-info-subtitle"):
            panel.append(numbers)
        else:
            composer.append(numbers)
    return (len(panel) == 1 and len(composer) == 1
            and len(panel[0]) == len(composer[0]) == 1
            and panel[0] == composer[0])


def _probe_real_dom(
    rows: list[dict[str, Any]],
    initial: dict[str, Any],
    dispatcher: Callable[..., Any],
    task_id: str,
    session_id: str,
    ui_recipient_phone_consistent: bool = False,
) -> dict[str, Any]:
    """Observe *structure* and status labels; never infer direction/destination."""
    message_ids: list[str] = []
    status_counts: dict[str, int] = {}
    for attrs in rows:
        msg_id = attrs.get("data-id")
        testid = attrs.get("data-testid")
        if (isinstance(msg_id, str) and isinstance(testid, str)
                and re.fullmatch(r"[0-9A-Fa-f]{16,128}", msg_id)
                and testid == "conv-msg-" + msg_id):
            message_ids.append(msg_id)

        # The native selector scopes these descendants to data-id ancestors.
        # Never return raw labels; an unrecognized label is NOT a send ACK.
        if not msg_id and not testid:
            label = str(attrs.get("aria-label") or "").strip().casefold()
            category = {
                "lida": "read", "lido": "read", "read": "read",
                "entregue": "delivered", "delivered": "delivered",
                "enviada": "sent", "enviado": "sent", "sent": "sent",
            }.get(label)
            if category:
                status_counts[category] = status_counts.get(category, 0) + 1

    base = {"matching_outbound_shapes": 0, "message_nodes_with_ids": len(message_ids),
            "message_nodes_with_status": 0, "status_label_counts": status_counts,
            "ui_recipient_phone_consistent": ui_recipient_phone_consistent}
    if len(message_ids) != len(set(message_ids)):
        return _hold("INSPECTION_AMBIGUOUS", **base)
    if not message_ids or not status_counts:
        return _hold("OUTBOUND_SCHEMA_INCOMPLETE", **base)

    # CSS :has proves each returned message ancestor owns a status descendant.
    # One deterministic extra native inspection; no per-message LLM loops.
    try:
        raw = dispatcher(
            action="browser_extract_items",
            args={"mode": "inspect", "selector": _STATUS_PARENT_SELECTOR,
                  "limit": _INSPECT_LIMIT, "attributes": ["data-id", "data-testid"]},
            task_id=task_id, session_id=session_id, model_facing=False,
        )
        observed = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return _hold("NATIVE_INSPECT_UNAVAILABLE", **base)
    if not isinstance(observed, dict):
        return _hold("INSPECTION_INCOMPLETE", **base)
    if (observed.get("runtime") != "electron-chromium"
            or observed.get("task_id") != task_id
            or observed.get("url") != initial.get("url")
            or not initial.get("tab_id")
            or observed.get("tab_id") != initial.get("tab_id")):
        return _hold("NATIVE_OWNER_ORIGIN_UNVERIFIED", **base)
    items = observed.get("items")
    count = observed.get("count")
    if (observed.get("success") is not True
            or observed.get("schema_valid") is not True
            or not isinstance(items, list) or not isinstance(count, int)
            or count != len(items) or count >= _INSPECT_LIMIT):
        return _hold("INSPECTION_INCOMPLETE", **base)
    associated: list[str] = []
    for item in items:
        attrs = item.get("attributes") if isinstance(item, dict) else None
        if not isinstance(attrs, dict):
            return _hold("INSPECTION_INCOMPLETE", **base)
        msg_id = attrs.get("data-id")
        if not isinstance(msg_id, str) or attrs.get("data-testid") != "conv-msg-" + msg_id:
            return _hold("INSPECTION_INCOMPLETE", **base)
        associated.append(msg_id)
    if len(associated) != len(set(associated)) or not set(associated).issubset(set(message_ids)):
        return _hold("INSPECTION_AMBIGUOUS", **base)
    base["message_nodes_with_status"] = len(associated)
    if not associated:
        return _hold("OUTBOUND_SCHEMA_INCOMPLETE", **base)

    # Neither self-chat/read labels nor arbitrary DOM IDs prove a new outbound
    # bubble, target chat or a receipt tied to an operation. Always HOLD.
    return _hold("RECIPIENT_DIRECTION_UNVERIFIED", **base)


def probe_native_schema(
    *, task_id: str, session_id: str,
    dispatcher: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Inspect the *already open* page; a canary must be selected separately.

    Even a matching historical outbound bubble is not an independent receipt
    for a new send. The caller never receives text, numbers or raw message IDs.
    """
    if not all(isinstance(v, str) and v.strip() for v in (task_id, session_id)):
        return _hold("TASK_IDENTITY_REQUIRED")

    if dispatcher is None:
        from tools.browser_workstation import _dispatch
        dispatcher = _dispatch

    try:
        response = dispatcher(
            action="browser_extract_items",
            args={"mode": "inspect", "selector": _SELECTOR,
                  "limit": _INSPECT_LIMIT, "attributes": _ATTRIBUTES},
            task_id=task_id, session_id=session_id, model_facing=False,
        )
        data = json.loads(response) if isinstance(response, str) else response
    except Exception:
        return _hold("NATIVE_INSPECT_UNAVAILABLE")

    if not isinstance(data, dict):
        return _hold("INSPECTION_INCOMPLETE")
    try:
        url = urlsplit(data.get("url") or "")
    except (TypeError, ValueError):
        return _hold("NATIVE_OWNER_ORIGIN_UNVERIFIED")
    if (data.get("runtime") != "electron-chromium"
            or data.get("task_id") != task_id
            or url.scheme != "https" or url.hostname != "web.whatsapp.com"):
        return _hold("NATIVE_OWNER_ORIGIN_UNVERIFIED")

    items = data.get("items")
    count = data.get("count")
    if (data.get("success") is not True
            or data.get("schema_valid") is not True
            or not isinstance(items, list)
            or not isinstance(count, int) or count >= _INSPECT_LIMIT
            or count != len(items)
            or len(items) >= _INSPECT_LIMIT):
        return _hold("INSPECTION_INCOMPLETE")

    rows = [item.get("attributes") or {} for item in items
            if isinstance(item, dict) and isinstance(item.get("attributes"), dict)]
    headers = [a for a in rows if a.get("data-testid") == "conversation-info-header"]
    if not headers:
        return _hold("CANARY_CHAT_NOT_SELECTED", matching_outbound_shapes=0)
    if len(headers) != 1:
        return _hold("INSPECTION_AMBIGUOUS", matching_outbound_shapes=0)
    if not isinstance(headers[0].get("data-chat-id"), str):
        return _probe_real_dom(
            rows, data, dispatcher, task_id, session_id,
            ui_recipient_phone_consistent=_ui_recipient_phone_consistent(items),
        )
    chat_id = headers[0]["data-chat-id"]
    if not chat_id:
        return _hold("OUTBOUND_SCHEMA_INCOMPLETE", matching_outbound_shapes=0)

    matching = sum(
        a.get("data-testid") == "msg-container"
        and isinstance(a.get("data-id"), str)
        and a["data-id"].startswith(f"true_{chat_id}_")
        and a.get("data-recipient-id") == chat_id
        and a.get("data-direction") == "outbound"
        and a.get("data-ack") in {"sent", "delivered", "read"}
        for a in rows
    )
    if not matching:
        return _hold("OUTBOUND_SCHEMA_INCOMPLETE", matching_outbound_shapes=0)

    return {
        "status": "SCHEMA_OBSERVED", "reason": "CANARY_RECEIPT_NOT_ATTESTED",
        "matching_outbound_shapes": matching,
        "can_send": False, "independently_verified": False,
    }

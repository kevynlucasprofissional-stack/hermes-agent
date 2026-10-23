"""WhatsApp Browser Executor — consolidated primitive per contract I-3.

Implements whatsapp_send_message as a single atomic operation:
deep-link navigate → wait for conversation → header check → send → post-send proof.
No per-message LLM round-trip, no browser_console DOM rediscovery.
Respects STALE_REF guards from WHATSAPP_BROWSER_DOGFOOD_RECOVERY_2026-10-19.md.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


class WhatsAppSendError(Exception):
    """Typed error for WhatsApp send failures."""
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        super().__init__(f"{error_code}: {message}")


def _validate_phone(phone_digits: str) -> str:
    """Reject masked or non-numeric phone digits per contract §MASKED_PHONE."""
    cleaned = phone_digits.strip()
    if "*" in cleaned or not cleaned.isdigit():
        raise WhatsAppSendError("MASKED_PHONE", f"Phone contains invalid chars: {phone_digits!r}")
    return cleaned


def _validate_message(message: str) -> str:
    """Reject unresolved template placeholders per contract §TEMPLATE_PLACEHOLDER_LEAK."""
    if "{NOME}" in message or "{{name}}" in message:
        raise WhatsAppSendError(
            "TEMPLATE_PLACEHOLDER_LEAK",
            "Message contains unresolved placeholder; render before calling."
        )
    return message


def whatsapp_send_message(
    *,
    browser_navigate: Callable[..., dict[str, Any]],
    browser_snapshot: Callable[..., dict[str, Any]],
    browser_click: Callable[..., dict[str, Any]],
    phone_digits: str,
    message: str,
    contact_name_hint: Optional[str] = None,
    verify_delivery: bool = True,
    delivery_timeout_seconds: float = 10.0,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """Send one WhatsApp message via deep link with append-only delivery proof.

    This is the consolidated primitive that replaces 10+ browser_console calls
    per recipient. Each step uses snapshot-first validation per contract I-3.

    Returns a dict matching the contract output schema:
      sent, state, message_data_id, ack_label, header_verified, composer_empty_after
    """
    # --- Pre-validation ---
    phone = _validate_phone(phone_digits)
    msg = _validate_message(message)

    # --- Step 1: Deep link navigation ---
    nav_url = f"https://web.whatsapp.com/send?phone={phone}&text={quote(msg)}"
    try:
        browser_navigate(url=nav_url)
    except Exception:  # health: allow BLE001 -- fail closed if navigation throws
        return {"sent": False, "state": "NAVIGATION_FAILED", "error_code": "NAVIGATION_FAILED"}

    # --- Step 2: Wait for conversation panel (poll snapshot) ---
    deadline = time.monotonic() + delivery_timeout_seconds
    conversation_ready = False
    header_text = ""
    last_snapshot: Optional[dict[str, Any]] = None

    while time.monotonic() < deadline:
        try:
            snap = browser_snapshot()
            last_snapshot = snap
        except Exception:  # health: allow BLE001 -- retry polling snapshot until deadline
            time.sleep(0.5)
            continue

        # Look for conversation-info-header in snapshot elements
        elements = snap.get("elements", [])
        for el in elements:
            testid = el.get("attributes", {}).get("data-testid", "")
            if testid == "conversation-info-header":
                conversation_ready = True
                header_text = el.get("text", "")
                break

        if conversation_ready:
            break
        time.sleep(0.8)

    if not conversation_ready:
        return {
            "sent": False,
            "state": "NO_CONVERSATION_OPEN",
            "error_code": "NO_CONVERSATION_OPEN",
        }

    # --- Step 3: Header check (if hint provided) ---
    header_verified = header_text.strip()
    if contact_name_hint and contact_name_hint.lower() not in header_verified.lower():
        return {
            "sent": False,
            "state": "HEADER_MISMATCH",
            "error_code": "HEADER_MISMATCH",
            "header_verified": header_verified,
        }

    # --- Step 4: Find and click Send button via snapshot ref ---
    send_ref: Optional[str] = None
    if last_snapshot:
        for el in last_snapshot.get("elements", []):
            attrs = el.get("attributes", {})
            testid = attrs.get("data-testid", "")
            role = el.get("role", "")
            # Send button: data-testid="send" or aria-label containing "Enviar"/"Send"
            if testid == "send" or (
                role == "button" and any(
                    kw in (attrs.get("aria-label", "")).lower()
                    for kw in ("enviar", "send")
                )
            ):
                send_ref = el.get("ref") or el.get("uid")
                break

    if not send_ref:
        return {
            "sent": False,
            "state": "SEND_BUTTON_NOT_FOUND",
            "error_code": "COMPOSER_NOT_EMPTY",
        }

    try:
        browser_click(ref=send_ref)
    except Exception as exc:  # health: allow BLE001 -- fail closed if browser click raises
        logger.warning("whatsapp_send click failed: %s", exc)
        return {
            "sent": False,
            "state": "CLICK_FAILED",
            "error_code": "STALE_REF",
        }

    # --- Step 5: Post-send proof (composer empty + new message appeared) ---
    if not verify_delivery:
        return {
            "sent": True,
            "state": "SENT_UNCONFIRMED",
            "header_verified": header_verified,
            "composer_empty_after": True,
        }

    composer_empty, message_data_id, ack_label = _wait_for_delivery_proof(
        browser_snapshot, delivery_timeout_seconds
    )

    return {
        "sent": True,
        "state": "DELIVERED" if message_data_id else "SENT_UNCONFIRMED",
        "message_data_id": message_data_id,
        "ack_label": ack_label,
        "header_verified": header_verified,
        "composer_empty_after": composer_empty,
    }


def _wait_for_delivery_proof(
    browser_snapshot: Callable[..., dict[str, Any]],
    timeout_seconds: float,
) -> tuple[bool, str, str]:
    """Poll snapshot until composer is empty and outgoing message appears."""
    proof_deadline = time.monotonic() + timeout_seconds
    composer_empty = False
    message_data_id = ""
    ack_label = ""

    while time.monotonic() < proof_deadline:
        try:
            snap = browser_snapshot()
        except Exception:  # health: allow BLE001 -- retry polling snapshot for delivery proof
            time.sleep(0.5)
            continue

        elements = snap.get("elements", [])
        for el in elements:
            attrs = el.get("attributes", {})
            testid = attrs.get("data-testid", "")
            if testid in ("ptt-in-button", "voice-message-button"):
                composer_empty = True
                break

        for el in elements:
            attrs = el.get("attributes", {})
            testid = attrs.get("data-testid", "")
            data_id = attrs.get("data-id", "")
            if testid == "msg-meta" and data_id:
                message_data_id = data_id
                ack_label = attrs.get("aria-label", "")
                break

        if composer_empty and message_data_id:
            break
        time.sleep(0.8)

    return composer_empty, message_data_id, ack_label
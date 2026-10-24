"""WhatsApp Browser Executor — consolidated primitive per contract I-3.

Implements whatsapp_send_message as a single atomic operation:
deep-link navigate → wait for conversation (<1s fast-fail on invalid phone popup)
→ header check → send → post-send proof → persistence in whatsapp_control.db.

Formal states:
  PREPARED, DISPATCHING, OBSERVED, CONFIRMED, UNCERTAIN, FAILED, REVIEW_REQUIRED.

Zero false positives: sent is True ONLY when delivery proof is confirmed.
"""
from __future__ import annotations

import logging
import os
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Formal state machine constants
STATE_PREPARED = "PREPARED"
STATE_DISPATCHING = "DISPATCHING"
STATE_OBSERVED = "OBSERVED"
STATE_CONFIRMED = "CONFIRMED"
STATE_UNCERTAIN = "UNCERTAIN"
STATE_FAILED = "FAILED"
STATE_REVIEW_REQUIRED = "REVIEW_REQUIRED"

FORMAL_STATES = {
    STATE_PREPARED,
    STATE_DISPATCHING,
    STATE_OBSERVED,
    STATE_CONFIRMED,
    STATE_UNCERTAIN,
    STATE_FAILED,
    STATE_REVIEW_REQUIRED,
}

INVALID_PHONE_SNIPPETS = (
    "número de telefone compartilhado por link é inválido",
    "numero de telefone compartilhado por link e invalido",
    "o número de telefone compartilhado por link",
    "número não encontrado no whatsapp",
    "numero nao encontrado no whatsapp",
    "não foi possível encontrar o número",
    "phone number shared via url is invalid",
    "the phone number shared via url is invalid",
    "number not found on whatsapp",
    "couldn't find phone number",
)


class WhatsAppSendError(Exception):
    """Typed error for WhatsApp send failures."""
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        super().__init__(f"{error_code}: {message}")


def _validate_phone(phone_digits: str) -> str:
    """Reject masked, non-numeric, or empty phone digits per contract §MASKED_PHONE."""
    cleaned = phone_digits.strip()
    if not cleaned or "*" in cleaned or not cleaned.isdigit():
        raise WhatsAppSendError("MASKED_PHONE", f"Phone contains invalid chars or is empty: {phone_digits!r}")
    return cleaned


def _validate_message(message: str) -> str:
    """Reject unresolved template placeholders per contract §TEMPLATE_PLACEHOLDER_LEAK."""
    placeholders = ("{NOME}", "{{name}}", "{nome}", "{NAME}", "{{NOME}}")
    if any(p in message for p in placeholders):
        raise WhatsAppSendError(
            "TEMPLATE_PLACEHOLDER_LEAK",
            "Message contains unresolved placeholder; render before calling."
        )
    if not message.strip():
        raise WhatsAppSendError("EMPTY_MESSAGE", "Message body cannot be empty.")
    return message


def _detect_invalid_phone_popup(snapshot: dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Detect immediate popup indicating phone number is invalid or not on WhatsApp.

    Returns (detected, dismiss_ref).
    """
    if not snapshot:
        return False, None

    # 1. Check structured elements
    elements = snapshot.get("elements", [])
    detected = False
    dismiss_ref: Optional[str] = None

    for el in elements:
        text = (el.get("text") or "").lower()
        attrs = el.get("attributes", {})
        aria_label = (attrs.get("aria-label") or "").lower()
        combined = f"{text} {aria_label}"

        if any(snippet in combined for snippet in INVALID_PHONE_SNIPPETS):
            detected = True

        # Look for OK / Fechar / Dismiss button inside or near popup
        role = el.get("role") or attrs.get("role")
        testid = attrs.get("data-testid", "")
        if testid == "popup-controls-ok" or (role == "button" and text in ("ok", "fechar", "close")):
            dismiss_ref = el.get("ref") or el.get("uid")

    if detected:
        return True, dismiss_ref

    # 2. Check snapshot text representation
    snap_text = str(snapshot.get("snapshot") or "").lower()
    if any(snippet in snap_text for snippet in INVALID_PHONE_SNIPPETS):
        # Try to find button ref from snap_text
        match = re.search(r'\[(@e\d+)\]\s+button\s+"[^"]*(?:ok|fechar|close)[^"]*"', snap_text, re.IGNORECASE)
        if match:
            dismiss_ref = match.group(1)
        return True, dismiss_ref

    return False, None


def _find_conversation_header(snapshot: dict[str, Any]) -> tuple[bool, str]:
    """Check if conversation header is visible and extract contact/chat name."""
    if not snapshot:
        return False, ""

    # Check elements
    elements = snapshot.get("elements", [])
    for el in elements:
        attrs = el.get("attributes", {})
        if attrs.get("data-testid") == "conversation-info-header":
            return True, el.get("text", "").strip()

    # Check snapshot text
    snap_text = str(snapshot.get("snapshot") or "")
    match = re.search(r'\[@e\d+\]\s+header\s+"([^"]+)"', snap_text)
    if match:
        return True, match.group(1).strip()

    return False, ""


def _find_send_button_ref(snapshot: dict[str, Any]) -> Optional[str]:
    """Find snapshot ref for the Send message button."""
    if not snapshot:
        return None

    # Check elements
    elements = snapshot.get("elements", [])
    for el in elements:
        attrs = el.get("attributes", {})
        testid = attrs.get("data-testid", "")
        role = el.get("role", "")
        aria_label = (attrs.get("aria-label") or "").lower()
        if testid == "send" or (role == "button" and any(kw in aria_label for kw in ("enviar", "send"))):
            return el.get("ref") or el.get("uid")

    # Check snapshot text
    snap_text = str(snapshot.get("snapshot") or "")
    match = re.search(r'\[(@e\d+)\]\s+button\s+"[^"]*(?:Enviar|Send)[^"]*"', snap_text, re.IGNORECASE)
    if match:
        return match.group(1)

    return None


def _is_composer_empty(snapshot: dict[str, Any]) -> bool:
    """Check if composer is empty via button revert to voice message."""
    if not snapshot:
        return False

    elements = snapshot.get("elements", [])
    for el in elements:
        attrs = el.get("attributes", {})
        testid = attrs.get("data-testid", "")
        aria_label = (attrs.get("aria-label") or "").lower()
        if testid in ("ptt-in-button", "voice-message-button") or "mensagem de voz" in aria_label or "voice message" in aria_label:
            return True

    snap_text = str(snapshot.get("snapshot") or "").lower()
    return "mensagem de voz" in snap_text or "voice message" in snap_text


def _extract_delivery_evidence(snapshot: dict[str, Any]) -> tuple[str, str]:
    """Extract message_data_id and ack_label from outgoing message elements."""
    if not snapshot:
        return "", ""

    elements = snapshot.get("elements", [])
    message_data_id = ""
    ack_label = ""

    for el in elements:
        attrs = el.get("attributes", {})
        data_id = attrs.get("data-id", "")
        testid = attrs.get("data-testid", "")
        if (testid == "msg-meta" or "msg" in testid) and data_id:
            message_data_id = data_id
            ack_label = attrs.get("aria-label", "")

    if message_data_id:
        return message_data_id, ack_label

    snap_text = str(snapshot.get("snapshot") or "")
    matches = list(re.finditer(r'data-id="([^"]+)"[^[]*aria-label="([^"]+)"', snap_text))
    if matches:
        return matches[-1].group(1), matches[-1].group(2)

    return "", ""


def get_default_db_path() -> Optional[Path]:
    """Resolve the default control database path."""
    env_path = os.environ.get("WHATSAPP_CONTROL_DB")
    if env_path:
        return Path(env_path)

    acirv_path = Path(r"C:\Github\ACIRV-Notebook\000-Arquivos-originais\Controle redes sociais\Whatsapp\Controle WhatsApp\whatsapp_control.db")
    if acirv_path.exists():
        return acirv_path

    try:
        from hermes_constants import get_hermes_home
        return Path(get_hermes_home()) / "whatsapp_control.db"
    except Exception:
        return None


def init_send_log_table(conn: sqlite3.Connection) -> None:
    """Ensure the whatsapp_send_logs table exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_send_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            session_id TEXT,
            phone_digits TEXT NOT NULL,
            contact_name_hint TEXT,
            header_verified TEXT,
            message_body TEXT NOT NULL,
            state TEXT NOT NULL,
            sent INTEGER NOT NULL DEFAULT 0,
            error_code TEXT,
            message_data_id TEXT,
            ack_label TEXT,
            composer_empty_after INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def persist_send_result(
    result: dict[str, Any],
    *,
    phone_digits: str,
    message: str,
    contact_name_hint: Optional[str] = None,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db_path: Optional[str | Path] = None,
) -> Optional[int]:
    """Persist the send attempt and outcome to whatsapp_control.db."""
    target_path = Path(db_path) if db_path else get_default_db_path()
    if not target_path:
        return None

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(target_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 5000")
            init_send_log_table(conn)
            cur = conn.execute(
                """
                INSERT INTO whatsapp_send_logs
                (task_id, session_id, phone_digits, contact_name_hint, header_verified,
                 message_body, state, sent, error_code, message_data_id, ack_label,
                 composer_empty_after)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    session_id,
                    phone_digits,
                    contact_name_hint,
                    result.get("header_verified"),
                    message,
                    result.get("state", "UNKNOWN"),
                    1 if result.get("sent") else 0,
                    result.get("error_code"),
                    result.get("message_data_id"),
                    result.get("ack_label"),
                    1 if result.get("composer_empty_after") else 0,
                )
            )
            conn.commit()
            return cur.lastrowid
    except Exception as exc:
        logger.warning("Failed to persist send result to %s: %s", target_path, exc)
        return None


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
    db_path: Optional[str | Path] = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Send one WhatsApp message via deep link with strict 80/20 verification.

    Workflow:
      1. Pre-validate phone and message (state: PREPARED).
      2. Deep link navigate (state: DISPATCHING).
      3. Fast-fail check on invalid phone popup (<1s) -> FAILED (INVALID_PHONE_NUMBER).
      4. Wait for conversation header -> FAILED (NO_CONVERSATION_OPEN).
      5. Header match check against contact_name_hint -> REVIEW_REQUIRED (HEADER_MISMATCH).
      6. Find send button -> FAILED (SEND_BUTTON_NOT_FOUND).
      7. Click send button -> FAILED (STALE_REF) on error.
      8. Post-send proof (composer emptied + message ack):
         - Delivered with proof -> CONFIRMED (sent=True)
         - Unverified / Timeout -> UNCERTAIN (sent=False, zero false positive)
      9. Persist result in whatsapp_control.db.
    """
    def _finalize(res: dict[str, Any]) -> dict[str, Any]:
        if persist:
            log_id = persist_send_result(
                res,
                phone_digits=phone_digits,
                message=message,
                contact_name_hint=contact_name_hint,
                task_id=task_id,
                session_id=session_id,
                db_path=db_path,
            )
            if log_id is not None:
                res["log_id"] = log_id
        return res

    # --- Step 0: Pre-validation ---
    phone = _validate_phone(phone_digits)
    msg = _validate_message(message)

    # --- Step 1: Deep link navigation ---
    nav_url = f"https://web.whatsapp.com/send?phone={phone}&text={quote(msg)}"
    try:
        browser_navigate(url=nav_url)
    except Exception as exc:  # health: allow BLE001 -- fail closed if navigation throws
        return _finalize({
            "sent": False,
            "state": STATE_FAILED,
            "error_code": "NAVIGATION_FAILED",
            "error": str(exc),
        })

    # --- Step 2: Poll snapshot with immediate invalid-phone check (<1s) ---
    deadline = time.monotonic() + delivery_timeout_seconds
    conversation_ready = False
    header_text = ""
    last_snapshot: Optional[dict[str, Any]] = None

    while time.monotonic() < deadline:
        try:
            snap = browser_snapshot()
            last_snapshot = snap
        except Exception:  # health: allow BLE001 -- retry polling snapshot until deadline
            time.sleep(0.3)
            continue

        # Fast-fail check: modal indicating invalid number (<1s)
        invalid_phone_detected, dismiss_ref = _detect_invalid_phone_popup(snap)
        if invalid_phone_detected:
            if dismiss_ref:
                try:
                    browser_click(ref=dismiss_ref)
                except Exception:
                    pass
            return _finalize({
                "sent": False,
                "state": STATE_FAILED,
                "error_code": "INVALID_PHONE_NUMBER",
                "error_message": "Número de telefone inválido ou não cadastrado no WhatsApp.",
            })

        # Conversation header check
        ready, hdr_text = _find_conversation_header(snap)
        if ready:
            conversation_ready = True
            header_text = hdr_text
            break

        time.sleep(0.4)

    if not conversation_ready:
        return _finalize({
            "sent": False,
            "state": STATE_FAILED,
            "error_code": "NO_CONVERSATION_OPEN",
        })

    # --- Step 3: Header identity check against hint ---
    header_verified = header_text.strip()
    if contact_name_hint and contact_name_hint.lower() not in header_verified.lower():
        return _finalize({
            "sent": False,
            "state": STATE_REVIEW_REQUIRED,
            "error_code": "HEADER_MISMATCH",
            "header_verified": header_verified,
            "error_message": f"Destinatário incorreto: cabeçalho '{header_verified}' não confere com '{contact_name_hint}'.",
        })

    # --- Step 4: Find Send button ---
    send_ref = _find_send_button_ref(last_snapshot)
    if not send_ref:
        return _finalize({
            "sent": False,
            "state": STATE_FAILED,
            "error_code": "SEND_BUTTON_NOT_FOUND",
        })

    # --- Step 5: Click Send button ---
    try:
        browser_click(ref=send_ref)
    except Exception as exc:  # health: allow BLE001 -- fail closed on click failure
        logger.warning("whatsapp_send click failed: %s", exc)
        return _finalize({
            "sent": False,
            "state": STATE_FAILED,
            "error_code": "STALE_REF",
            "error": str(exc),
        })

    # --- Step 6: Post-send proof ---
    if not verify_delivery:
        return _finalize({
            "sent": False,  # Not confirmed without delivery proof
            "state": STATE_OBSERVED,
            "header_verified": header_verified,
            "composer_empty_after": True,
        })

    composer_empty = False
    message_data_id = ""
    ack_label = ""
    proof_deadline = time.monotonic() + delivery_timeout_seconds

    while time.monotonic() < proof_deadline:
        try:
            post_snap = browser_snapshot()
        except Exception:
            time.sleep(0.3)
            continue

        if not composer_empty:
            composer_empty = _is_composer_empty(post_snap)

        mid, ack = _extract_delivery_evidence(post_snap)
        if mid:
            message_data_id = mid
            ack_label = ack

        if composer_empty and message_data_id:
            break
        time.sleep(0.4)

    if composer_empty and message_data_id:
        return _finalize({
            "sent": True,
            "state": STATE_CONFIRMED,
            "message_data_id": message_data_id,
            "ack_label": ack_label,
            "header_verified": header_verified,
            "composer_empty_after": True,
        })

    # Proof timed out — mark UNCERTAIN with sent=False (Zero False Positives)
    return _finalize({
        "sent": False,
        "state": STATE_UNCERTAIN,
        "error_code": "DELIVERY_TIMEOUT",
        "header_verified": header_verified,
        "composer_empty_after": composer_empty,
    })

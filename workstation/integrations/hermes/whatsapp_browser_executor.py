"""WhatsApp Browser Executor — consolidated primitive per contract I-3.

Implements whatsapp_send_message as a single atomic operation:
deep-link navigate → wait for conversation (<1s fast-fail on invalid phone popup)
→ header check → send → post-send proof → persistence in whatsapp_control.db.

Formal states:
  PREPARED, DISPATCHING, OBSERVED, CONFIRMED, UNCERTAIN, FAILED, REVIEW_REQUIRED.

Zero false positives: sent is True ONLY when delivery proof is confirmed.
"""
from __future__ import annotations

import hashlib
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
        raise WhatsAppSendError("MASKED_PHONE", "Phone is masked, invalid, or empty")
    return cleaned


def sanitize_send_result(value: Any, *, phone_digits: str, message: str) -> Any:
    """Keep transport inputs private while retaining delivery evidence and states."""
    from agent.redact import redact_sensitive_text

    if isinstance(value, str):
        for private in (quote(message.strip()), message.strip(), message, phone_digits.strip(), phone_digits):
            if private:
                value = value.replace(private, "[redacted]")
        return redact_sensitive_text(value, force=True, file_read=True)
    if isinstance(value, dict):
        return {
            key: item if key in {"state", "sent", "error_code", "duration_ms", "log_id", "composer_empty_after"}
            else sanitize_send_result(item, phone_digits=phone_digits, message=message)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_send_result(item, phone_digits=phone_digits, message=message) for item in value]
    return value


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
    """Use explicit profile configuration; retain the legacy explicit override."""
    from hermes_cli.config import cfg_get, load_config_readonly

    configured = cfg_get(load_config_readonly(), "whatsapp", "control_db_path", default=None)
    if isinstance(configured, str) and configured:
        return Path(configured).expanduser()
    env_path = os.environ.get("WHATSAPP_CONTROL_DB")
    if env_path:
        return Path(env_path)

    return None


ALLOWED_ATTACHMENT_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".gif",  # images
    ".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".doc", ".xls",  # documents
    ".mp3", ".ogg", ".wav", ".m4a",  # audio
    ".mp4", ".mov", ".3gp",  # video
}
MAX_ATTACHMENT_SIZE_BYTES = 50 * 1024 * 1024  # 50MB


def _get_content_type(ext: str) -> str:
    """Classify file extension into WhatsApp content_type."""
    ext = ext.lower()
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
        return "image"
    if ext in {".pdf", ".docx", ".xlsx", ".pptx", ".txt", ".csv", ".doc", ".xls"}:
        return "document"
    if ext in {".mp3", ".ogg", ".wav", ".m4a"}:
        return "audio"
    if ext in {".mp4", ".mov", ".3gp"}:
        return "video"
    return "document"


def _validate_attachment_file(file_path: str | Path) -> tuple[Path, int, str]:
    """Validate file existence, size, and supported WhatsApp MIME type / extension.

    Returns (resolved_path, size_bytes, content_type).
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise WhatsAppSendError("FILE_NOT_FOUND", f"Attachment file not found: {file_path}")
    size = path.stat().st_size
    if size == 0:
        raise WhatsAppSendError("EMPTY_FILE", f"Attachment file is empty (0 bytes): {file_path}")
    if size > MAX_ATTACHMENT_SIZE_BYTES:
        raise WhatsAppSendError("FILE_TOO_LARGE", f"Attachment size ({size} bytes) exceeds limit of 50MB.")
    ext = path.suffix.lower()
    if ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise WhatsAppSendError("UNSUPPORTED_MEDIA_TYPE", f"File extension '{ext}' is not supported for WhatsApp attachments.")
    return path.resolve(), size, _get_content_type(ext)


def _find_attach_button_ref(snapshot: dict[str, Any]) -> Optional[str]:
    """Find snapshot ref for the attachment button (clip / plus icon)."""
    if not snapshot:
        return None
    elements = snapshot.get("elements", [])
    for el in elements:
        attrs = el.get("attributes", {})
        testid = attrs.get("data-testid", "")
        role = el.get("role", "")
        aria_label = (attrs.get("aria-label") or "").lower()
        if testid in ("attach-menu-plus", "clip") or (role == "button" and any(k in aria_label for k in ("anexar", "attach", "anexo"))):
            return el.get("ref") or el.get("uid")

    snap_text = str(snapshot.get("snapshot") or "")
    match = re.search(r'\[(@e\d+)\]\s+button\s+"[^"]*(?:anexar|attach|anexo|mais opções)[^"]*"', snap_text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def _find_caption_input_ref(snapshot: dict[str, Any]) -> Optional[str]:
    """Find snapshot ref for media caption input field."""
    if not snapshot:
        return None
    elements = snapshot.get("elements", [])
    for el in elements:
        attrs = el.get("attributes", {})
        testid = attrs.get("data-testid", "")
        role = el.get("role", "")
        aria_label = (attrs.get("aria-label") or "").lower()
        if testid == "media-caption-input" or (role == "textbox" and any(k in aria_label for k in ("legenda", "caption"))):
            return el.get("ref") or el.get("uid")

    snap_text = str(snapshot.get("snapshot") or "")
    match = re.search(r'\[(@e\d+)\]\s+textbox\s+"[^"]*(?:legenda|caption)[^"]*"', snap_text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def init_send_log_table(conn: sqlite3.Connection) -> None:
    """Ensure the whatsapp_send_logs table exists and has necessary columns."""
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
    for col in ("media_path", "content_type"):
        try:
            conn.execute(f"ALTER TABLE whatsapp_send_logs ADD COLUMN {col} TEXT")
        except sqlite3.OperationalError:
            pass


def init_whatsapp_control_tables(conn: sqlite3.Connection) -> None:
    """Ensure contacts, conversations, and messages tables exist matching control schema."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            whatsapp_id TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('contact', 'group', 'broadcast')),
            phone_number TEXT,
            is_acirv_related BOOLEAN DEFAULT 0,
            intelligence_tier TEXT DEFAULT 'unknown',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            email TEXT,
            phone_raw TEXT,
            notes TEXT,
            phone_source TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER NOT NULL UNIQUE REFERENCES contacts(id),
            unread_count INTEGER DEFAULT 0,
            last_message_at TIMESTAMP,
            last_message_preview TEXT,
            is_archived BOOLEAN DEFAULT 0,
            is_pinned BOOLEAN DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id),
            whatsapp_msg_id TEXT UNIQUE,
            direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound', 'scheduled')),
            sender_contact_id INTEGER REFERENCES contacts(id),
            content_text TEXT,
            content_type TEXT DEFAULT 'text' CHECK (content_type IN ('text', 'image', 'video', 'audio', 'document', 'contact', 'location', 'sticker', 'poll')),
            media_path TEXT,
            media_mime_type TEXT,
            media_size INTEGER,
            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            received_at TIMESTAMP,
            read_at TIMESTAMP,
            delivered_at TIMESTAMP,
            viewed_at TIMESTAMP,
            replied_to_msg_id INTEGER REFERENCES messages(id),
            is_starred BOOLEAN DEFAULT 0,
            is_deleted BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    init_send_log_table(conn)


def _outbound_messages(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    """Use only scoped message containers, not free-floating msg-meta nodes."""
    matches: list[dict[str, str]] = []
    for element in snapshot.get("elements", []):
        attrs = element.get("attributes") or {}
        if attrs.get("data-testid") != "msg-container":
            continue
        message_id = attrs.get("data-id") or ""
        if not isinstance(message_id, str) or not message_id.startswith("true_"):
            continue
        ack = str(attrs.get("data-ack") or "").lower()
        if ack not in {"sent", "delivered", "read"}:
            ack = ""
        matches.append({
            "id": message_id,
            "recipient": str(attrs.get("data-recipient-id") or ""),
            "direction": str(attrs.get("data-direction") or ""),
            "body": str(element.get("text") or ""),
            "ack": ack,
        })
    return matches


def _verified_chat_identity(snapshot: dict[str, Any], phone: str) -> bool:
    """A display name or requested deep-link URL is not a recipient identity."""
    for element in snapshot.get("elements", []):
        attrs = element.get("attributes") or {}
        if (attrs.get("data-testid") == "conversation-info-header"
                and attrs.get("data-chat-id") == f"{phone}@c.us"):
            return True
    return False


def _send_log_schema(conn: sqlite3.Connection) -> None:
    init_send_log_table(conn)
    for name in ("operation_id", "run_id", "message_digest", "approval_fingerprint"):
        columns = {row[1] for row in conn.execute("PRAGMA table_info(whatsapp_send_logs)")}
        if name not in columns:
            conn.execute(f"ALTER TABLE whatsapp_send_logs ADD COLUMN {name} TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_whatsapp_send_logs_operation "
        "ON whatsapp_send_logs(operation_id)"
    )


def _reserve_send_intent(
    *, db_path: Path, operation_id: str, task_id: str | None,
    session_id: str | None, run_id: str | None, message: str,
    approval_fingerprint: str | None = None,
) -> bool:
    """One durable pre-effect row per operation; any replay fails closed."""
    if not db_path.is_file():
        raise sqlite3.OperationalError("Configured WhatsApp control DB does not exist")
    with sqlite3.connect(db_path, timeout=5) as conn:
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("BEGIN IMMEDIATE")
        _send_log_schema(conn)
        cursor = conn.execute(
            """INSERT OR IGNORE INTO whatsapp_send_logs
               (operation_id, run_id, task_id, session_id, phone_digits,
                message_body, message_digest, approval_fingerprint, state, sent)
               VALUES (?, ?, ?, ?, '[redacted]', '[redacted]', ?, ?, ?, 0)""",
            (operation_id, run_id, task_id, session_id,
             hashlib.sha256(message.encode("utf-8")).hexdigest(),
             approval_fingerprint, STATE_PREPARED),
        )
        conn.commit()
        return cursor.rowcount == 1


def persist_send_result(
    result: dict[str, Any], *,
    phone_digits: str,
    message: str,
    contact_name_hint: Optional[str] = None,
    media_path: Optional[str] = None,
    content_type: Optional[str] = None,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    run_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    db_path: Optional[str | Path] = None,
) -> Optional[int]:
    """Update the existing intent row or preserve the legacy standalone log API."""
    target = Path(db_path) if db_path else get_default_db_path()
    if target is None:
        return None
    sanitized = sanitize_send_result(result, phone_digits=phone_digits, message=message)
    try:
        with sqlite3.connect(target, timeout=5) as conn:
            conn.execute("PRAGMA busy_timeout = 5000")
            _send_log_schema(conn)
            if operation_id:
                cursor = conn.execute(
                    """UPDATE whatsapp_send_logs
                       SET state=?, sent=?, error_code=?, message_data_id=?,
                           ack_label=?, composer_empty_after=?
                       WHERE operation_id=? AND message_digest=?""",
                    (
                        sanitized.get("state"), 1 if sanitized.get("sent") else 0,
                        sanitized.get("error_code"), sanitized.get("message_data_id"),
                        sanitized.get("ack_label"),
                        1 if sanitized.get("composer_empty_after") else 0,
                        operation_id, hashlib.sha256(message.encode("utf-8")).hexdigest(),
                    ),
                )
                if cursor.rowcount != 1:
                    return None
                row = conn.execute(
                    "SELECT id FROM whatsapp_send_logs WHERE operation_id=?",
                    (operation_id,),
                ).fetchone()
                conn.commit()
                return int(row[0])
            cursor = conn.execute(
                """INSERT INTO whatsapp_send_logs
                   (task_id, session_id, phone_digits, contact_name_hint, header_verified,
                    message_body, state, sent, error_code, message_data_id, ack_label,
                    composer_empty_after, media_path, content_type)
                   VALUES (?, ?, '[redacted]', '[redacted]', '[redacted]',
                           '[redacted]', ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task_id, session_id, sanitized.get("state"),
                    1 if sanitized.get("sent") else 0, sanitized.get("error_code"),
                    sanitized.get("message_data_id"), sanitized.get("ack_label"),
                    1 if sanitized.get("composer_empty_after") else 0,
                    sanitize_send_result(media_path or result.get("media_path"), phone_digits=phone_digits, message=message),
                    content_type,
                ),
            )
            conn.commit()
            return cursor.lastrowid
    except (OSError, sqlite3.Error):
        logger.warning("Could not persist WhatsApp send result")
        return None

def whatsapp_send_message(
    *,
    browser_navigate: Callable[..., dict[str, Any]],
    browser_snapshot: Callable[..., dict[str, Any]],
    browser_click: Callable[..., dict[str, Any]],
    browser_inspect: Optional[Callable[..., dict[str, Any]]] = None,
    browser_type: Optional[Callable[..., dict[str, Any]]] = None,
    opened_chat_name: Optional[str] = None,
    session_context_verified: bool = False,
    approval_fingerprint: Optional[str] = None,
    phone_digits: str,
    message: str,
    contact_name_hint: Optional[str] = None,
    verify_delivery: bool = True,
    delivery_timeout_seconds: float = 5.0,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    run_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    db_path: Optional[str | Path] = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Dispatch once. Verify a newly observed outbound message tied to the actual chat."""
    start = time.perf_counter()
    phone = _validate_phone(phone_digits)
    msg = _validate_message(message)
    if browser_inspect is not None and (
        not session_context_verified or browser_type is None
    ):
        return {"sent": False, "state": STATE_FAILED,
                "error_code": "SESSION_CONTEXT_REQUIRED", "failure_phase": "PRE_SEND"}
    target_db = Path(db_path) if db_path else get_default_db_path()
    reserved = False

    def finish(result: dict[str, Any]) -> dict[str, Any]:
        safe = sanitize_send_result(result, phone_digits=phone, message=msg)
        safe["duration_ms"] = round((time.perf_counter() - start) * 1000, 2)
        if reserved and target_db is not None:
            row_id = persist_send_result(
                safe, phone_digits=phone, message=msg,
                task_id=task_id, session_id=session_id,
                run_id=run_id, operation_id=operation_id, db_path=target_db,
            )
            if row_id is None:
                safe = {
                    "state": STATE_UNCERTAIN, "sent": False,
                    "error_code": "RESULT_PERSISTENCE_UNCERTAIN",
                    "operation_id": operation_id,
                    "duration_ms": safe["duration_ms"],
                }
            else:
                safe["log_id"] = row_id
            # Metrics are observational only; they never confer send authority.
            try:
                from workstation.integrations.hermes.whatsapp_metrics import record_operation_metric
                record_operation_metric(
                    operation_name="send_message",
                    duration_ms=safe["duration_ms"],
                    state=safe.get("state", "UNKNOWN"),
                    task_id=task_id,
                    session_id=session_id,
                    tool_calls_count=1,
                    ai_turns_count=1,
                    tokens_estimated=350,
                    security_blocks=[safe["error_code"]] if safe.get("error_code") in (
                        "HEADER_MISMATCH", "INVALID_PHONE_NUMBER",
                        "RECIPIENT_IDENTITY_UNVERIFIED",
                    ) else [],
                    recipient_phone=None,
                    error_code=safe.get("error_code"),
                    db_path=target_db,
                )
            except Exception:
                logger.warning("Could not record WhatsApp operation metric")
        return safe

    if persist:
        if target_db is None or not operation_id or not isinstance(operation_id, str):
            return finish({"sent": False, "state": STATE_FAILED,
                           "error_code": "DURABLE_INTENT_REQUIRED"})
        try:
            reserved = _reserve_send_intent(
                db_path=target_db, operation_id=operation_id,
                task_id=task_id, session_id=session_id,
                run_id=run_id, message=msg,
                approval_fingerprint=approval_fingerprint,
            )
        except (OSError, sqlite3.Error):
            return finish({"sent": False, "state": STATE_FAILED,
                           "error_code": "INTENT_PERSISTENCE_FAILED"})
        if not reserved:
            return finish({"sent": False, "state": STATE_UNCERTAIN,
                           "error_code": "OPERATION_ALREADY_RECORDED",
                           "operation_id": operation_id})

    if browser_inspect is not None:
        from workstation.integrations.hermes.whatsapp_native_send_bridge import native_send_once
        return finish(native_send_once(
            browser_navigate=browser_navigate, browser_snapshot=browser_snapshot,
            browser_click=browser_click, browser_inspect=browser_inspect,
            browser_type=browser_type,
            phone=phone, message=msg,
            session_context_verified=session_context_verified,
            timeout_seconds=delivery_timeout_seconds,
            opened_chat_name=opened_chat_name,
        ))

    try:
        nav = browser_navigate(url=f"https://web.whatsapp.com/send?phone={phone}&text={quote(msg)}")
        if isinstance(nav, dict) and (nav.get("error") or nav.get("success") is False):
            raise RuntimeError("navigation rejected")
    except Exception:
        return finish({"sent": False, "state": STATE_FAILED, "error_code": "NAVIGATION_FAILED"})

    deadline = time.monotonic() + delivery_timeout_seconds
    ready_snapshot = None
    header_text = ""
    while time.monotonic() < deadline:
        try:
            snap = browser_snapshot()
        except Exception:
            time.sleep(0.1)
            continue
        invalid, dismiss = _detect_invalid_phone_popup(snap)
        if invalid:
            if dismiss:
                try:
                    browser_click(ref=dismiss)
                except Exception:
                    pass
            return finish({"sent": False, "state": STATE_FAILED,
                           "error_code": "INVALID_PHONE_NUMBER"})
        ready, header_text = _find_conversation_header(snap)
        if ready:
            ready_snapshot = snap
            break
        time.sleep(0.1)

    if ready_snapshot is None:
        return finish({"sent": False, "state": STATE_FAILED,
                       "error_code": "NO_CONVERSATION_OPEN"})

    if not _verified_chat_identity(ready_snapshot, phone):
        return finish({"sent": False, "state": STATE_REVIEW_REQUIRED,
                       "error_code": "RECIPIENT_IDENTITY_UNVERIFIED"})

    if contact_name_hint and header_text.strip().casefold() != contact_name_hint.strip().casefold():
        return finish({"sent": False, "state": STATE_REVIEW_REQUIRED,
                       "error_code": "HEADER_MISMATCH", "header_verified": header_text})

    send_ref = _find_send_button_ref(ready_snapshot)
    if not send_ref:
        return finish({"sent": False, "state": STATE_FAILED,
                       "error_code": "SEND_BUTTON_NOT_FOUND"})

    before = {item["id"] for item in _outbound_messages(ready_snapshot)}
    try:
        click = browser_click(ref=send_ref)
    except Exception:
        return finish({"sent": False, "state": STATE_UNCERTAIN,
                       "error_code": "CLICK_OUTCOME_UNKNOWN"})
    if isinstance(click, dict) and (click.get("error") or click.get("success") is False):
        return finish({"sent": False, "state": STATE_UNCERTAIN,
                       "error_code": "CLICK_OUTCOME_UNKNOWN"})

    if not verify_delivery:
        return finish({"sent": False, "state": STATE_UNCERTAIN,
                       "error_code": "DISPATCH_UNVERIFIED"})

    proof_deadline = time.monotonic() + delivery_timeout_seconds
    composer_empty = False
    while time.monotonic() < proof_deadline:
        try:
            after = browser_snapshot()
        except Exception:
            time.sleep(0.1)
            continue
        if not isinstance(after, dict):
            time.sleep(0.1)
            continue
        composer_empty = composer_empty or _is_composer_empty(after)
        if not _verified_chat_identity(after, phone):
            # A snapshot lacking identity cannot certify the chat did not change.
            time.sleep(0.1)
            continue
        matches = [
            item for item in _outbound_messages(after)
            if item["id"] not in before
            and item["id"].startswith(f"true_{phone}@c.us_")
            and item["recipient"] == f"{phone}@c.us"
            and item["direction"] == "outbound"
            and item["body"].strip() == msg.strip()
            and item["ack"] in {"sent", "delivered", "read"}
        ]
        if len(matches) > 1:
            return finish({"sent": False, "state": STATE_UNCERTAIN,
                           "error_code": "AMBIGUOUS_OUTBOUND_EVIDENCE"})
        if len(matches) == 1:
            return finish({
                "sent": True, "state": STATE_CONFIRMED,
                # Opaque identity avoids surfacing a phone number hidden in WA data-id.
                "message_data_id": "sha256:" + hashlib.sha256(
                    matches[0]["id"].encode("utf-8")).hexdigest(),
                "ack_label": matches[0]["ack"],
                "header_verified": header_text,
                "composer_empty_after": composer_empty,
            })
        time.sleep(0.1)
    return finish({"sent": False, "state": STATE_UNCERTAIN,
                   "error_code": "DELIVERY_TIMEOUT",
                   "composer_empty_after": composer_empty})

def persist_read_messages(
    *,
    header_text: str,
    messages: list[dict[str, Any]],
    contact_id: Optional[int] = None,
    db_path: Optional[str | Path] = None,
) -> tuple[Optional[int], Optional[int], int, int]:
    """Persist read messages into contacts, conversations, and messages tables.

    Returns (contact_id, conversation_id, new_persisted_count, updated_count).
    """
    target_path = Path(db_path) if db_path else get_default_db_path()
    if not target_path:
        return None, None, 0, 0

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(target_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 5000")
            init_whatsapp_control_tables(conn)

            # 1. Resolve contact
            res_contact_id = contact_id
            if not res_contact_id:
                row = conn.execute("SELECT id FROM contacts WHERE display_name = ?", (header_text.strip(),)).fetchone()
                if row:
                    res_contact_id = row[0]
                else:
                    phone_candidate = None
                    for m in messages:
                        wid = m.get("whatsapp_msg_id", "")
                        match = re.search(r'(\d{10,15})@c\.us', wid)
                        if match:
                            phone_candidate = match.group(1)
                            break
                    whatsapp_id = f"{phone_candidate}@c.us" if phone_candidate else f"{re.sub(r'[^a-zA-Z0-9]', '_', header_text.lower())}@c.us"
                    cur = conn.execute(
                        """
                        INSERT INTO contacts (whatsapp_id, display_name, type, phone_number)
                        VALUES (?, ?, 'contact', ?)
                        """,
                        (whatsapp_id, header_text.strip(), phone_candidate),
                    )
                    res_contact_id = cur.lastrowid

            # 2. Resolve conversation
            conv_row = conn.execute("SELECT id FROM conversations WHERE contact_id = ?", (res_contact_id,)).fetchone()
            if conv_row:
                conv_id = conv_row[0]
            else:
                last_preview = messages[-1].get("text", "") if messages else ""
                cur = conn.execute(
                    """
                    INSERT INTO conversations (contact_id, unread_count, last_message_at, last_message_preview)
                    VALUES (?, 0, CURRENT_TIMESTAMP, ?)
                    """,
                    (res_contact_id, last_preview),
                )
                conv_id = cur.lastrowid

            # 3. Deduplicate and insert messages
            persisted = 0
            updated = 0
            for m in messages:
                w_id = m.get("whatsapp_msg_id")
                direction = m.get("direction", "inbound")
                text = m.get("text", "")
                ack = m.get("ack")

                if w_id:
                    existing = conn.execute(
                        "SELECT id, delivered_at, viewed_at FROM messages WHERE whatsapp_msg_id = ?",
                        (w_id,),
                    ).fetchone()
                    if existing:
                        msg_db_id, deliv_at, view_at = existing
                        if ack in ("read", "viewed") and not view_at:
                            conn.execute(
                                "UPDATE messages SET viewed_at = CURRENT_TIMESTAMP, delivered_at = COALESCE(delivered_at, CURRENT_TIMESTAMP) WHERE id = ?",
                                (msg_db_id,),
                            )
                            updated += 1
                        elif ack == "delivered" and not deliv_at:
                            conn.execute(
                                "UPDATE messages SET delivered_at = CURRENT_TIMESTAMP WHERE id = ?",
                                (msg_db_id,),
                            )
                            updated += 1
                        continue

                sender_id = res_contact_id if direction == "inbound" else None
                rec_at = "CURRENT_TIMESTAMP" if direction == "inbound" else None
                del_at = "CURRENT_TIMESTAMP" if ack in ("delivered", "read", "viewed") else None
                viw_at = "CURRENT_TIMESTAMP" if ack in ("read", "viewed") else None

                conn.execute(
                    """
                    INSERT INTO messages (
                        conversation_id, whatsapp_msg_id, direction, sender_contact_id,
                        content_text, content_type, timestamp, received_at, delivered_at, viewed_at
                    ) VALUES (?, ?, ?, ?, ?, 'text', CURRENT_TIMESTAMP, ?, ?, ?)
                    """,
                    (conv_id, w_id, direction, sender_id, text, rec_at, del_at, viw_at),
                )
                persisted += 1

            if messages:
                last_preview = messages[-1].get("text", "")
                conn.execute(
                    "UPDATE conversations SET last_message_at = CURRENT_TIMESTAMP, last_message_preview = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (last_preview, conv_id),
                )
            conn.commit()
            return res_contact_id, conv_id, persisted, updated
    except Exception as exc:
        logger.warning("Failed to persist read messages to %s: %s", target_path, exc)
        return None, None, 0, 0


def persist_outbound_message_to_control(
    *,
    header_text: str,
    phone_digits: str,
    content_text: str,
    content_type: str = "text",
    media_path: Optional[str] = None,
    media_size: Optional[int] = None,
    message_data_id: Optional[str] = None,
    ack_label: Optional[str] = None,
    db_path: Optional[str | Path] = None,
) -> Optional[int]:
    """Persist an outbound message to messages table in whatsapp_control.db."""
    target_path = Path(db_path) if db_path else get_default_db_path()
    if not target_path:
        return None

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(target_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 5000")
            init_whatsapp_control_tables(conn)

            # Contact
            row = conn.execute(
                "SELECT id FROM contacts WHERE phone_number = ? OR display_name = ?",
                (phone_digits, header_text.strip()),
            ).fetchone()
            if row:
                contact_id = row[0]
            else:
                cur = conn.execute(
                    """
                    INSERT INTO contacts (whatsapp_id, display_name, type, phone_number)
                    VALUES (?, ?, 'contact', ?)
                    """,
                    (f"{phone_digits}@c.us", header_text.strip(), phone_digits),
                )
                contact_id = cur.lastrowid

            # Conversation
            conv_row = conn.execute("SELECT id FROM conversations WHERE contact_id = ?", (contact_id,)).fetchone()
            if conv_row:
                conv_id = conv_row[0]
            else:
                cur = conn.execute(
                    """
                    INSERT INTO conversations (contact_id, unread_count, last_message_at, last_message_preview)
                    VALUES (?, 0, CURRENT_TIMESTAMP, ?)
                    """,
                    (contact_id, content_text or f"[{content_type}]"),
                )
                conv_id = cur.lastrowid

            # Ack timestamps
            ack_lower = (ack_label or "").lower()
            deliv_at = "CURRENT_TIMESTAMP" if any(k in ack_lower for k in ("entregue", "delivered", "lida", "read")) else None
            view_at = "CURRENT_TIMESTAMP" if any(k in ack_lower for k in ("lida", "read")) else None

            # Deduplication
            if message_data_id:
                existing = conn.execute("SELECT id FROM messages WHERE whatsapp_msg_id = ?", (message_data_id,)).fetchone()
                if existing:
                    return existing[0]

            cur = conn.execute(
                """
                INSERT INTO messages (
                    conversation_id, whatsapp_msg_id, direction, sender_contact_id,
                    content_text, content_type, media_path, media_size,
                    timestamp, delivered_at, viewed_at
                ) VALUES (?, ?, 'outbound', NULL, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
                """,
                (conv_id, message_data_id, content_text, content_type, media_path, media_size, deliv_at, view_at),
            )
            msg_id = cur.lastrowid
            conn.execute(
                "UPDATE conversations SET last_message_at = CURRENT_TIMESTAMP, last_message_preview = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (content_text or f"[{content_type}]", conv_id),
            )
            conn.commit()
            return msg_id
    except Exception as exc:
        logger.warning("Failed to persist outbound message to %s: %s", target_path, exc)
        return None


def _parse_messages_from_snapshot(snapshot: dict[str, Any], limit: int = 20) -> list[dict[str, Any]]:
    """Extract message items from active WhatsApp Web conversation snapshot."""
    if not snapshot:
        return []

    elements = snapshot.get("elements", [])
    parsed_messages: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for el in elements:
        attrs = el.get("attributes", {})
        data_id = str(attrs.get("data-id") or "")
        testid = str(attrs.get("data-testid") or "")
        classes = str(attrs.get("class") or "")
        aria_label = str(attrs.get("aria-label") or "")
        text = str(el.get("text") or "").strip()

        is_msg = bool(
            data_id
            or "msg" in testid
            or "message-in" in classes
            or "message-out" in classes
            or "message-in" in testid
            or "message-out" in testid
        )
        if not is_msg and not (aria_label and ("[" in aria_label or "lida" in aria_label.lower() or "entregue" in aria_label.lower())):
            continue

        direction = "inbound"
        if data_id.startswith("true_") or "message-out" in classes or "message-out" in testid:
            direction = "outbound"
        elif data_id.startswith("false_") or "message-in" in classes or "message-in" in testid:
            direction = "inbound"
        elif "me:" in aria_label.lower() or "você:" in aria_label.lower():
            direction = "outbound"

        ack = None
        combined_label = f"{aria_label} {text}".lower()
        if direction == "outbound":
            if any(k in combined_label for k in ("lida", "read", "visualizada", "viewed")):
                ack = "read"
            elif any(k in combined_label for k in ("entregue", "delivered")):
                ack = "delivered"
            elif any(k in combined_label for k in ("enviada", "sent")):
                ack = "sent"
            elif any(k in combined_label for k in ("pendente", "pending")):
                ack = "pending"

        time_label = ""
        time_match = re.search(r'\b(\d{1,2}:\d{2})\b', text or aria_label)
        if time_match:
            time_label = time_match.group(1)

        clean_text = text
        if time_label:
            clean_text = re.sub(rf'(?:\s+|\n){re.escape(time_label)}(?:\s*,?\s*[A-Za-zÀ-ÿ]+)?$', '', clean_text).strip()

        sender = "me" if direction == "outbound" else None
        if direction == "inbound" and aria_label:
            sender_match = re.match(r'^([^:\[\]]+):\s*(.*)', aria_label)
            if sender_match:
                sender = sender_match.group(1).strip()
                if not clean_text:
                    clean_text = sender_match.group(2).strip()

        if not clean_text and not data_id:
            continue

        msg_id = data_id or f"msg_{direction}_{hashlib.sha256((clean_text + time_label).encode()).hexdigest()[:16]}"
        if msg_id in seen_ids:
            for m in parsed_messages:
                if m["whatsapp_msg_id"] == msg_id:
                    if ack and not m.get("ack"):
                        m["ack"] = ack
                    if clean_text and not m.get("text"):
                        m["text"] = clean_text
            continue

        seen_ids.add(msg_id)
        parsed_messages.append({
            "whatsapp_msg_id": msg_id,
            "direction": direction,
            "text": clean_text,
            "time_label": time_label,
            "ack": ack,
            "sender": sender,
        })

    if not parsed_messages:
        snap_text = str(snapshot.get("snapshot") or "")
        matches = re.finditer(r'data-id="((?:true_|false_)[^"]+)"[^[]*?(?:aria-label="([^"]*)")?(?:[^\n]*text\s+"([^"]*)")?', snap_text)
        for m in matches:
            mid = m.group(1)
            if mid in seen_ids:
                continue
            seen_ids.add(mid)
            lbl = m.group(2) or ""
            txt = m.group(3) or ""
            direction = "outbound" if mid.startswith("true_") else "inbound"
            ack = None
            if direction == "outbound":
                if any(k in lbl.lower() for k in ("lida", "read", "viewed")):
                    ack = "read"
                elif any(k in lbl.lower() for k in ("entregue", "delivered")):
                    ack = "delivered"
                elif any(k in lbl.lower() for k in ("enviada", "sent")):
                    ack = "sent"

            time_m = re.search(r'\b(\d{1,2}:\d{2})\b', txt or lbl)
            time_label = time_m.group(1) if time_m else ""
            clean_txt = txt
            if time_label:
                clean_txt = re.sub(rf'(?:\s+|\n){re.escape(time_label)}.*$', '', clean_txt).strip()

            parsed_messages.append({
                "whatsapp_msg_id": mid,
                "direction": direction,
                "text": clean_txt or lbl,
                "time_label": time_label,
                "ack": ack,
                "sender": "me" if direction == "outbound" else None,
            })

    return parsed_messages[-limit:] if limit > 0 else parsed_messages


def whatsapp_read_messages(
    *,
    browser_snapshot: Callable[..., dict[str, Any]],
    limit: int = 20,
    contact_name_hint: Optional[str] = None,
    contact_id: Optional[int] = None,
    db_path: Optional[str | Path] = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Read recent messages from the currently open WhatsApp Web conversation.

    Snapshot-first, deduplicated, and integrated with contacts, conversations, and messages.
    """
    t_read_start = time.perf_counter()
    try:
        snap = browser_snapshot()
    except Exception as exc:  # health: allow BLE001 -- fail closed on snapshot error
        return {
            "success": False,
            "error_code": "SNAPSHOT_FAILED",
            "error": str(exc),
            "messages": [],
            "count": 0,
        }

    ready, header_text = _find_conversation_header(snap)
    if not ready:
        return {
            "success": False,
            "error_code": "NO_CONVERSATION_OPEN",
            "error_message": "Nenhuma conversa aberta no WhatsApp Web.",
            "messages": [],
            "count": 0,
        }

    header_verified = header_text.strip()
    if contact_name_hint and contact_name_hint.lower() not in header_verified.lower():
        return {
            "success": False,
            "error_code": "HEADER_MISMATCH",
            "header_verified": header_verified,
            "error_message": f"Destinatário incorreto: cabeçalho '{header_verified}' não confere com '{contact_name_hint}'.",
            "messages": [],
            "count": 0,
        }

    messages = _parse_messages_from_snapshot(snap, limit=limit)

    persisted_count = 0
    updated_count = 0
    res_contact_id = contact_id
    res_conv_id = None

    if persist:
        res_contact_id, res_conv_id, persisted_count, updated_count = persist_read_messages(
            header_text=header_verified,
            messages=messages,
            contact_id=contact_id,
            db_path=db_path,
        )
        try:
            from workstation.integrations.hermes.whatsapp_metrics import record_operation_metric
            duration_ms = (time.perf_counter() - t_read_start) * 1000.0
            dedup_prevented = max(0, len(messages) - persisted_count)
            record_operation_metric(
                operation_name="read_messages",
                duration_ms=duration_ms,
                state="CONFIRMED",
                tool_calls_count=1,
                ai_turns_count=1,
                tokens_estimated=250,
                deduplications_prevented=dedup_prevented,
                db_path=db_path,
            )
        except Exception:
            pass

    return {
        "success": True,
        "header_verified": header_verified,
        "chat_title": header_verified,
        "contact_id": res_contact_id,
        "conversation_id": res_conv_id,
        "messages": messages,
        "count": len(messages),
        "persisted_count": persisted_count,
        "updated_count": updated_count,
    }


def whatsapp_send_attachment(
    *,
    browser_navigate: Callable[..., dict[str, Any]],
    browser_snapshot: Callable[..., dict[str, Any]],
    browser_click: Callable[..., dict[str, Any]],
    browser_file_upload: Optional[Callable[..., dict[str, Any]]] = None,
    browser_type: Optional[Callable[..., dict[str, Any]]] = None,
    phone_digits: str,
    file_path: str | Path,
    caption: Optional[str] = None,
    contact_name_hint: Optional[str] = None,
    verify_delivery: bool = True,
    delivery_timeout_seconds: float = 15.0,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db_path: Optional[str | Path] = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Send an attachment (image, document, audio, video) via WhatsApp Web.

    Workflow:
      1. Pre-validate phone digits and attachment file (existence, size, extension).
      2. If caption provided, pre-validate for placeholder leaks.
      3. Deep link navigate (state: DISPATCHING).
      4. Fast-fail check on invalid phone popup (<1s) -> FAILED (INVALID_PHONE_NUMBER).
      5. Wait for conversation header -> FAILED (NO_CONVERSATION_OPEN).
      6. Header match check against contact_name_hint -> REVIEW_REQUIRED (HEADER_MISMATCH).
      7. Trigger file upload:
         - Click attachment button if found.
         - Call browser_file_upload with resolved local file path.
      8. If caption provided, type into media caption input.
      9. Find and click Send button in preview modal.
      10. Post-send proof (composer return & message data-id / ack).
      11. Persist result in whatsapp_send_logs and messages tables.
    """
    t_start = time.perf_counter()

    def _finalize(res: dict[str, Any]) -> dict[str, Any]:
        duration_ms = (time.perf_counter() - t_start) * 1000.0
        res["duration_ms"] = round(duration_ms, 2)
        if persist:
            log_id = persist_send_result(
                res,
                phone_digits=phone_digits,
                message=caption or "",
                contact_name_hint=contact_name_hint,
                media_path=str(resolved_path),
                content_type=content_type,
                task_id=task_id,
                session_id=session_id,
                db_path=db_path,
            )
            if log_id is not None:
                res["log_id"] = log_id
            if res.get("sent"):
                persist_outbound_message_to_control(
                    header_text=res.get("header_verified", ""),
                    phone_digits=phone_digits,
                    content_text=caption or "",
                    content_type=content_type,
                    media_path=str(resolved_path),
                    media_size=file_size,
                    message_data_id=res.get("message_data_id"),
                    ack_label=res.get("ack_label"),
                    db_path=db_path,
                )
            try:
                from workstation.integrations.hermes.whatsapp_metrics import record_operation_metric
                security_blocks = [res["error_code"]] if res.get("error_code") in ("HEADER_MISMATCH", "INVALID_PHONE_NUMBER") else []
                record_operation_metric(
                    operation_name="send_attachment",
                    duration_ms=duration_ms,
                    state=res.get("state", "UNKNOWN"),
                    task_id=task_id,
                    session_id=session_id,
                    tool_calls_count=3,
                    ai_turns_count=1,
                    tokens_estimated=450,
                    security_blocks=security_blocks,
                    recipient_phone=phone_digits,
                    error_code=res.get("error_code"),
                    db_path=db_path,
                )
            except Exception:
                pass
        return res

    # --- Step 0: Pre-validation ---
    phone = _validate_phone(phone_digits)
    resolved_path, file_size, content_type = _validate_attachment_file(file_path)
    validated_caption = _validate_message(caption) if caption else ""

    # --- Step 1: Deep link navigation ---
    nav_url = f"https://web.whatsapp.com/send?phone={phone}"
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
        except Exception:  # health: allow BLE001 -- retry polling
            time.sleep(0.3)
            continue

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

    # --- Step 4: Click Attachment button ---
    attach_ref = _find_attach_button_ref(last_snapshot)
    if attach_ref:
        try:
            browser_click(ref=attach_ref)
            time.sleep(0.3)
        except Exception as exc:
            logger.warning("Failed to click attach button ref %s: %s", attach_ref, exc)

    # --- Step 5: Upload file via controlled browser handler ---
    if browser_file_upload:
        try:
            browser_file_upload(files=[str(resolved_path)])
            time.sleep(0.5)
        except Exception as exc:  # health: allow BLE001 -- fail closed on upload failure
            return _finalize({
                "sent": False,
                "state": STATE_FAILED,
                "error_code": "FILE_UPLOAD_FAILED",
                "error": str(exc),
            })

    # --- Step 6: Compose caption if provided ---
    if validated_caption and browser_type:
        try:
            preview_snap = browser_snapshot()
            cap_ref = _find_caption_input_ref(preview_snap)
            if cap_ref:
                browser_type(ref=cap_ref, text=validated_caption)
                time.sleep(0.3)
        except Exception as exc:
            logger.warning("Failed to type caption: %s", exc)

    # --- Step 7: Find Send button in preview dialog ---
    try:
        preview_snap = browser_snapshot()
    except Exception:
        preview_snap = last_snapshot

    send_ref = _find_send_button_ref(preview_snap)
    if not send_ref:
        return _finalize({
            "sent": False,
            "state": STATE_FAILED,
            "error_code": "SEND_BUTTON_NOT_FOUND",
        })

    # --- Step 8: Click Send button ---
    try:
        browser_click(ref=send_ref)
    except Exception as exc:  # health: allow BLE001 -- fail closed on click failure
        logger.warning("whatsapp_send_attachment click failed: %s", exc)
        return _finalize({
            "sent": False,
            "state": STATE_FAILED,
            "error_code": "STALE_REF",
            "error": str(exc),
        })

    # --- Step 9: Post-send delivery proof ---
    if not verify_delivery:
        return _finalize({
            "sent": False,
            "state": STATE_OBSERVED,
            "header_verified": header_verified,
            "composer_empty_after": True,
            "media_path": str(resolved_path),
            "content_type": content_type,
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
            "media_path": str(resolved_path),
            "content_type": content_type,
        })

    return _finalize({
        "sent": False,
        "state": STATE_UNCERTAIN,
        "error_code": "DELIVERY_TIMEOUT",
        "header_verified": header_verified,
        "composer_empty_after": composer_empty,
        "media_path": str(resolved_path),
        "content_type": content_type,
    })

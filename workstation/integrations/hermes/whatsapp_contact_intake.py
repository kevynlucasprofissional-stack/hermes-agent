"""Register an explicitly requested unsaved recipient in the existing WhatsApp contact table.

Intake is NOT WhatsApp identity verification, contact consent, or send approval.
The native sender must validate the full phone in the contact-info panel and
obtain the independently authenticated once-only host grant before dispatch.
"""
from __future__ import annotations

from contextlib import closing
import re
import sqlite3
from typing import Any
from urllib.parse import urlsplit, parse_qs


LOCAL_ALIAS = "hermes_local"
PENDING_SOURCE = "user_requested_unverified"
VERIFIED_SOURCE = "whatsapp_native_verified"


class ContactIntakeError(Exception):
    """Public-safe error (never includes the requested phone)."""


def _normalize_international_phone(value: str) -> str:
    """Accept E.164-style phone or a phone-only WhatsApp deep link.

    Never consume a deeplink message parameter as authorization.
    Unprefixed national numbers are ambiguous and explicitly rejected.
    """
    if not isinstance(value, str) or not 8 <= len(value.strip()) <= 200:
        raise ContactIntakeError("INVALID_INTERNATIONAL_PHONE")
    text = value.strip()
    from_url = False
    if text.startswith("https://"):
        url = urlsplit(text)
        if url.username or url.password or url.fragment:
            raise ContactIntakeError("INVALID_CONTACT_DEEPLINK")
        if url.netloc == "wa.me" and url.path.count("/") == 1 and not url.query:
            text = url.path.lstrip("/")
        elif url.netloc in {"web.whatsapp.com", "api.whatsapp.com"} and url.path == "/send":
            query = parse_qs(url.query, keep_blank_values=True)
            if set(query) != {"phone"} or len(query["phone"]) != 1:
                raise ContactIntakeError("INVALID_CONTACT_DEEPLINK")
            text = query["phone"][0]
        else:
            raise ContactIntakeError("INVALID_CONTACT_DEEPLINK")
        from_url = True

    if not re.fullmatch(r"\+?[0-9][0-9 ()-]*", text, flags=re.ASCII):
        raise ContactIntakeError("INVALID_INTERNATIONAL_PHONE")
    digits = re.sub(r"[^0-9]", "", text)
    # Plain digit input must contain a recognizable country prefix; Brazil 55
    # is the present operator's target. Other countries require explicit '+'.
    if not (10 <= len(digits) <= 15 and digits[0] != "0"
            and (from_url or text.startswith("+") or digits.startswith("55"))
            and not (text.startswith("+") and not re.match(r"^\+[1-9]", text))):
        raise ContactIntakeError("INTERNATIONAL_COUNTRY_CODE_REQUIRED")
    return digits


def register_requested_contact(
    *, phone: str, display_name: str = "Contato solicitado",
) -> dict[str, Any]:
    """Stage a pending contact, deduplicated by phone, in the existing control DB.

    Browser verification and human once approval remain separate mandatory gates.
    Expose to the model only via a TaskRun-bound MUTATION.
    """
    digits = _normalize_international_phone(phone)
    if (not isinstance(display_name, str) or not display_name.strip()
            or len(display_name.strip()) > 100
            or any(ord(c) < 32 or ord(c) == 127 for c in display_name)):
        raise ContactIntakeError("INVALID_CONTACT_LABEL")
    label = " ".join(display_name.split())
    from workstation.integrations.hermes.whatsapp_browser_executor import (
        get_default_db_path, init_whatsapp_control_tables,
    )

    path = get_default_db_path()
    if path is None or not path.is_file():
        raise ContactIntakeError("WHATSAPP_CONTROL_DB_UNAVAILABLE")
    try:
        with closing(sqlite3.connect(path, timeout=5)) as conn:
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("BEGIN IMMEDIATE")
            # Reuse the pre-existing WhatsApp contacts schema, not a parallel store.
            init_whatsapp_control_tables(conn)
            rows = conn.execute(
                """SELECT id, display_name, phone_source, whatsapp_id FROM contacts
                   WHERE phone_number=? OR phone_raw=? OR whatsapp_id IN (?, ?)""",
                (digits, "+" + digits, "pending:" + digits, digits + "@c.us"),
            ).fetchall()
            if len(rows) > 1:
                raise ContactIntakeError("AMBIGUOUS_LOCAL_CONTACT")
            if rows:
                contact_id, stored_label, source, identity = rows[0]
                if source not in {PENDING_SOURCE, VERIFIED_SOURCE}:
                    raise ContactIntakeError("CONTACT_PROVENANCE_CONFLICT")
                if stored_label.casefold() != label.casefold():
                    raise ContactIntakeError("CONTACT_LABEL_CONFLICT")
                if identity not in {"pending:" + digits, digits + "@c.us"}:
                    raise ContactIntakeError("CONTACT_IDENTITY_CONFLICT")
                ref_id = int(contact_id)
                verification = "NATIVE_VERIFIED" if source == VERIFIED_SOURCE else "PENDING_NATIVE_VERIFICATION"
            else:
                inserted = conn.execute(
                    """INSERT INTO contacts
                       (whatsapp_id, display_name, type, phone_number, phone_raw,
                        phone_source, is_acirv_related, intelligence_tier)
                       VALUES (?, ?, 'contact', ?, ?, ?, 0, 'unknown')""",
                    ("pending:" + digits, label, digits, "+" + digits, PENDING_SOURCE),
                )
                ref_id = int(inserted.lastrowid)
                verification = "PENDING_NATIVE_VERIFICATION"
            conn.commit()
    except ContactIntakeError:
        raise
    except (OSError, sqlite3.Error):
        raise ContactIntakeError("CONTACT_INTAKE_UNAVAILABLE") from None

    return {
        "recipient_ref": {"source": LOCAL_ALIAS, "contact_id": ref_id},
        "verification_state": verification,
        "send_authorized": False,
    }


def promote_verified_contact(
    ref: dict[str, Any], *, phone_digits: str, receipt_state: str,
) -> bool:
    """Only a causal OBSERVED native panel/receipt may promote staged provenance."""
    if receipt_state != "OBSERVED" or not isinstance(ref, dict) or ref.get("source") != LOCAL_ALIAS:
        return False
    contact_id = ref.get("contact_id")
    if type(contact_id) is not int or contact_id <= 0:
        return False
    from workstation.integrations.hermes.whatsapp_browser_executor import get_default_db_path
    path = get_default_db_path()
    if path is None or not path.is_file():
        return False
    if not isinstance(phone_digits, str) or not re.fullmatch(r"[1-9][0-9]{9,14}", phone_digits):
        return False
    try:
        with closing(sqlite3.connect(path, timeout=5)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            changed = conn.execute(
                """UPDATE contacts SET phone_source=?, whatsapp_id=?,
                   updated_at=CURRENT_TIMESTAMP
                   WHERE id=? AND phone_number=? AND phone_raw=?
                   AND phone_source=? AND whatsapp_id=?""",
                (VERIFIED_SOURCE, phone_digits + "@c.us", contact_id,
                 phone_digits, "+" + phone_digits, PENDING_SOURCE,
                 "pending:" + phone_digits),
            )
            if changed.rowcount != 1:
                row = conn.execute(
                    """SELECT phone_source, whatsapp_id FROM contacts
                       WHERE id=? AND phone_number=?""", (contact_id, phone_digits),
                ).fetchone()
                conn.rollback()
                return bool(row and row == (VERIFIED_SOURCE, phone_digits + "@c.us"))
            conn.commit()
            return True
    except (OSError, sqlite3.Error):
        return False

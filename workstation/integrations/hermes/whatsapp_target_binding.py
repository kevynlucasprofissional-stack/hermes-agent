"""Atomic recipient binding for a model-initiated WhatsApp TaskRun.

The LLM may adjust its arguments after a failure, but may not silently
redirect an existing canonical run to a different phone number.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3


class TargetBindingError(Exception):
    pass


def bind_recipient_for_run(*, db_path: Path, session_id: str, run_id: str,
                           phone_digits: str) -> bool:
    """Return False only if this same run was already bound to another phone.

    BEGIN IMMEDIATE serializes concurrent claims. SQL keeps only a digest.
    No independent DB, no approval state and no duplicate task machinery.
    """
    if (not isinstance(session_id, str) or not session_id
            or not isinstance(run_id, str) or not run_id
            or not isinstance(phone_digits, str) or not phone_digits.isascii()
            or not phone_digits.isdecimal() or not 10 <= len(phone_digits) <= 15):
        raise TargetBindingError("INVALID_TARGET_BINDING")
    digest = hashlib.sha256(phone_digits.encode("ascii")).hexdigest()
    try:
        with sqlite3.connect(db_path, timeout=5) as conn:
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("""CREATE TABLE IF NOT EXISTS whatsapp_run_recipient_bindings (
                session_id TEXT NOT NULL,
                run_id TEXT NOT NULL,
                recipient_digest TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (session_id, run_id)
            )""")
            row = conn.execute(
                "SELECT recipient_digest FROM whatsapp_run_recipient_bindings "
                "WHERE session_id=? AND run_id=?", (session_id, run_id),
            ).fetchone()
            if row is not None:
                conn.commit()
                return row[0] == digest
            conn.execute(
                "INSERT INTO whatsapp_run_recipient_bindings "
                "(session_id, run_id, recipient_digest) VALUES (?, ?, ?)",
                (session_id, run_id, digest),
            )
            conn.commit()
            return True
    except (OSError, sqlite3.Error) as exc:
        raise TargetBindingError("TARGET_BINDING_UNAVAILABLE") from exc

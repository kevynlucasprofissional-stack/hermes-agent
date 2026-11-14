"""Safe, read-only, model-facing WhatsApp Workstation catalog adapters.

All runtime secrets, recipient identity, and database paths stay in trusted code.
These adapters NEVER mint approvals or touch the WhatsApp send path.
"""
from __future__ import annotations

from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
from typing import Any


_SAFE_REF = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}$")


def _deny(error_code: str) -> str:
    return json.dumps({"success": False, "error_code": error_code, "state": "DENIED"})


def _read_only_source(alias: str) -> Path | None:
    from workstation.integrations.hermes.whatsapp_recipient_resolution import _configured_sources

    if not isinstance(alias, str) or not _SAFE_REF.fullmatch(alias):
        return None
    source = _configured_sources().get(alias)
    if not isinstance(source, dict):
        return None
    provenance = source.get("allowed_phone_sources")
    path_str = source.get("db_path")
    if (not isinstance(provenance, list) or not provenance
            or not all(isinstance(s, str) and s.strip() for s in provenance)
            or not isinstance(path_str, str) or not path_str):
        return None
    path = Path(path_str).expanduser()
    if not path.is_absolute() or not path.is_file():
        return None
    return path


def read_messages_for_model(args: dict[str, Any], *, session_id: str | None,
                            tool_call_id: str | None) -> str:
    """Return a bounded observation from the active *native* Browser conversation."""
    if not session_id or not tool_call_id or set(args) - {"limit", "target_name"}:
        return _deny("SESSION_CONTEXT_REQUIRED")
    limit = args.get("limit", 20)
    if type(limit) is not int or not 1 <= limit <= 50:
        return _deny("INVALID_READ_LIMIT")
    from tools.browser_workstation import whatsapp_read_messages_current, whatsapp_read_messages_named

    # Name-directed reads resolve in WhatsApp itself; no CRM required.
    target_name = args.get("target_name")
    if target_name is not None:
        if not isinstance(target_name, str) or not 3 <= len(target_name.strip()) <= 100:
            return _deny("INVALID_TARGET_NAME")
        result = whatsapp_read_messages_named(
            target_name=target_name.strip(), limit=limit,
            session_id=session_id, operation_id=tool_call_id,
        )
    else:
        result = whatsapp_read_messages_current(
            limit=limit, session_id=session_id, operation_id=tool_call_id,
        )
    if not isinstance(result, dict) or not result.get("success"):
        code = result.get("error_code") if isinstance(result, dict) else None
        return _deny(code if isinstance(code, str) and re.fullmatch(r"[A-Z_]{3,64}", code)
                     else "NATIVE_READ_UNAVAILABLE")
    from agent.redact import redact_sensitive_text

    public_messages = []
    for item in result.get("messages", [])[-limit:]:
        if not isinstance(item, dict):
            continue
        direction = item.get("direction")
        if direction not in {"inbound", "outbound", "unknown"}:
            continue
        raw = item.get("text")
        clean = redact_sensitive_text(raw[:500], force=True) if isinstance(raw, str) else ""
        public_messages.append({
            "direction": direction,
            "text_preview": clean[:240],
            "time_label": item.get("time_label") if isinstance(item.get("time_label"), str)
            and re.fullmatch(r"\d{1,2}:\d{2}", item["time_label"]) else "",
        })
    return json.dumps({
        "success": True, "mode": "native_read_only", "count": len(public_messages),
        "messages": public_messages, "persisted": False,
    }, ensure_ascii=False)


def preview_campaign_for_model(args: dict[str, Any], *, session_id: str | None,
                               tool_call_id: str | None) -> str:
    """Read campaign eligibility without returning private contacts or issuing approval.

    Only the configured profile source is accepted. The database is always opened
    with mode=ro and no schema/table migrations, even against production sources.
    """
    if not session_id or not tool_call_id or set(args) - {
        "source", "campaign_slug", "step_code",
    }:
        return _deny("SESSION_CONTEXT_REQUIRED")
    source = args.get("source")
    campaign = args.get("campaign_slug")
    step = args.get("step_code")
    if not isinstance(campaign, str) or not _SAFE_REF.fullmatch(campaign):
        return _deny("INVALID_CAMPAIGN_REFERENCE")
    if not isinstance(step, str) or not _SAFE_REF.fullmatch(step):
        return _deny("INVALID_STEP_REFERENCE")
    path = _read_only_source(source)
    if path is None:
        return _deny("UNAUTHORIZED_RECIPIENT_SOURCE")

    from workstation.integrations.hermes.whatsapp_recipient_resolution import (
        RecipientResolutionError, resolve_recipient_reference,
    )

    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT id FROM campaigns WHERE slug = ?", (campaign,)).fetchone()
            if row is None:
                return _deny("CAMPAIGN_NOT_FOUND")
            campaign_id = int(row["id"])
            step_row = db.execute(
                "SELECT id FROM campaign_messages WHERE campaign_id = ? AND step_code = ?",
                (campaign_id, step),
            ).fetchone()
            if step_row is None:
                return _deny("STEP_NOT_FOUND")
            message_id = int(step_row["id"])
            # A hard cap prevents unexpectedly huge model actions or DB walks.
            members = db.execute(
                "SELECT id, contact_id, status, authorized_at, authorized_via "
                "FROM campaign_enrollments WHERE campaign_id = ? ORDER BY id LIMIT 501",
                (campaign_id,),
            ).fetchall()
            if len(members) > 500:
                return _deny("PREVIEW_LIMIT_EXCEEDED")
            historic = {
                int(r["contact_id"]): str(r["status"])
                for r in db.execute(
                    "SELECT contact_id, status FROM campaign_sends "
                    "WHERE campaign_id = ? AND campaign_message_id = ?",
                    (campaign_id, message_id),
                )
            }
            counts: dict[str, int] = {}
            eligible = 0
            for row in members:
                state = str(row["status"] or "")
                prior = historic.get(int(row["contact_id"]))
                if prior in {"sent", "delivered", "read", "confirmed"}:
                    reason = "ALREADY_SENT"
                elif prior in {"uncertain", "sending", "dispatching"}:
                    reason = "RECONCILIATION_REQUIRED"
                elif state != "replied_authorized" or not (row["authorized_at"] and row["authorized_via"]):
                    reason = "NO_EXPLICIT_CONSENT"
                else:
                    try:
                        resolve_recipient_reference(
                            {"source": source, "campaign_id": campaign_id, "enrollment_id": int(row["id"])}
                        )
                    except RecipientResolutionError:
                        reason = "RECIPIENT_UNAVAILABLE"
                    else:
                        eligible += 1
                        continue
                counts[reason] = counts.get(reason, 0) + 1
    except (sqlite3.Error, OSError, ValueError, TypeError):
        return _deny("CAMPAIGN_PREVIEW_UNAVAILABLE")

    return json.dumps({
        "success": True, "mode": "dry_run_read_only", "source": source,
        "campaign_slug": campaign, "step_code": step,
        "total_contacts": len(members), "eligible_count": eligible,
        "excluded_count": len(members) - eligible,
        "reasons_breakdown": counts,
        "sample_messages": [], "approval_status": "NOT_APPROVED",
        "can_send": False,
    }, ensure_ascii=False)


def find_contacts_for_model(args: dict[str, Any], *, session_id: str | None,
                            tool_call_id: str | None) -> str:
    """Read-only, bounded recipient-reference discovery for desktop sessions.

    Returns never include raw phone, JID, source DB path or send authority.
    """
    if not session_id or not tool_call_id or not isinstance(args, dict) or set(args) != {"source", "query"}:
        return _deny("SESSION_CONTEXT_REQUIRED")
    alias, query = args.get("source"), args.get("query")
    if (not isinstance(alias, str) or not _SAFE_REF.fullmatch(alias)
            or not isinstance(query, str) or not 3 <= len(query.strip()) <= 64
            or any(ord(ch) < 32 for ch in query) or query.strip().isdigit()):
        return _deny("INVALID_CONTACT_QUERY")
    path = _read_only_source(alias)
    if path is None:
        return _deny("UNAUTHORIZED_RECIPIENT_SOURCE")
    from workstation.integrations.hermes.whatsapp_recipient_resolution import (
        RecipientResolutionError, resolve_recipient_reference,
    )
    from agent.redact import redact_sensitive_text

    escaped = (query.strip().replace("\\", "\\\\")
               .replace("%", "\\%").replace("_", "\\_"))
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            rows = conn.execute(
                "SELECT id, display_name FROM contacts "
                "WHERE type='contact' AND display_name LIKE ? ESCAPE '\\' "
                "ORDER BY lower(display_name), id LIMIT 21",
                ("%" + escaped + "%",),
            ).fetchall()
    except sqlite3.Error:
        return _deny("RECIPIENT_SOURCE_UNAVAILABLE")
    matches = []
    for contact_id, label in rows:
        try:
            recipient = resolve_recipient_reference({"source": alias, "contact_id": int(contact_id)})
        except (RecipientResolutionError, ValueError, TypeError):
            continue
        matches.append({
            "recipient_ref": recipient.public_reference,
            "display_name": redact_sensitive_text(str(label or "")[:100], force=True)[:100],
        })
        if len(matches) > 5:
            break
    if len(matches) > 5 or len(rows) >= 21:
        return json.dumps({"success": False, "error_code": "CONTACT_RESULTS_AMBIGUOUS",
                           "count_lower_bound": len(matches)})
    return json.dumps({"success": True, "count": len(matches), "contacts": matches,
                       "read_only": True}, ensure_ascii=False)

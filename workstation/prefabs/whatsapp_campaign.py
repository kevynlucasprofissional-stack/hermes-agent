"""Provider-free WhatsApp campaign structure and legacy evidence audit.

The caller must resolve the DB path from a trusted profile source alias. This
module reads only; it never issues batch approvals, sends or certifies delivery.
"""

from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from workstation.integrations.hermes.whatsapp_batch_executor import (
    _has_verified_send_evidence,
)

_SAFE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}$")
_SENT = {"sent", "delivered", "read", "confirmed"}
_UNCERTAIN = {"uncertain", "dispatching", "sending", "attempted"}


def _bad(code: str) -> dict:
    return {"status": "HOLD", "can_send": False, "error_code": code}


def plan_campaign(db_path: str | Path, campaign_slug: str) -> dict:
    """Inspect all campaign steps with bounded, PII-free output.

    Receipt-shaped JSON is *not* independent verification of an external send.
    Historical free-text evidence is conservatively classified as unverified.
    """
    if not isinstance(campaign_slug, str) or not _SAFE_NAME.fullmatch(campaign_slug):
        return _bad("INVALID_CAMPAIGN_REFERENCE")
    path = Path(db_path)
    if not path.is_absolute() or not path.is_file():
        return _bad("AUTHORIZED_SOURCE_UNAVAILABLE")

    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            campaign = conn.execute(
                "SELECT id FROM campaigns WHERE slug=?", (campaign_slug,)
            ).fetchone()
            if campaign is None:
                return _bad("CAMPAIGN_NOT_FOUND")
            campaign_id = int(campaign["id"])
            steps = conn.execute(
                "SELECT id, step_code, step_index, body_template, media_paths "
                "FROM campaign_messages WHERE campaign_id=? ORDER BY step_index, id LIMIT 33",
                (campaign_id,),
            ).fetchall()
            recipients = conn.execute(
                "SELECT contact_id, status, authorized_at, authorized_via "
                "FROM campaign_enrollments WHERE campaign_id=? ORDER BY id LIMIT 501",
                (campaign_id,),
            ).fetchall()
            if not steps or len(steps) > 32 or len(recipients) > 500:
                return _bad("CAMPAIGN_SIZE_UNSUPPORTED")
            codes = [row["step_code"] for row in steps]
            if len(set(codes)) != len(codes) or any(
                not isinstance(code, str) or not _SAFE_NAME.fullmatch(code)
                for code in codes
            ):
                return _bad("CAMPAIGN_STEP_CONFLICT")
            sends = conn.execute(
                "SELECT contact_id, campaign_message_id, status, evidence "
                "FROM campaign_sends WHERE campaign_id=? LIMIT 16001",
                (campaign_id,),
            ).fetchall()
            if len(sends) > 16000:
                return _bad("CAMPAIGN_SEND_LIMIT_EXCEEDED")
    except (OSError, sqlite3.Error, ValueError, TypeError):
        return _bad("CAMPAIGN_SCHEMA_UNAVAILABLE")

    authorized = sum(
        row["status"] == "replied_authorized" and bool(row["authorized_at"])
        and bool(row["authorized_via"]) for row in recipients
    )
    counters = {}
    repeated = 0
    for entry in sends:
        key = (entry["contact_id"], entry["campaign_message_id"])
        if key in counters:
            repeated += 1
        counters.setdefault(key, []).append(entry)
    out_steps = []
    fingerprint_parts = []
    for step in steps:
        sid = int(step["id"])
        body = str(step["body_template"] or "")
        if not body.strip():
            return _bad("CAMPAIGN_TEMPLATE_INVALID")
        try:
            media = json.loads(step["media_paths"] or "[]")
            if not isinstance(media, list) or any(not isinstance(v, str) for v in media):
                return _bad("CAMPAIGN_MEDIA_MANIFEST_INVALID")
        except (ValueError, TypeError):
            return _bad("CAMPAIGN_MEDIA_MANIFEST_INVALID")
        stats = dict(structured_receipt_shapes=0, legacy_unverified=0,
                     uncertain=0, failed=0, unattempted=0)
        for person in recipients:
            records = counters.get((person["contact_id"], sid), [])
            if not records:
                stats["unattempted"] += 1
                continue
            for send in records:
                status = str(send["status"] or "")
                if status in _SENT:
                    try:
                        proof = json.loads(send["evidence"] or "{}")
                    except (TypeError, ValueError):
                        proof = {}
                    if _has_verified_send_evidence(proof):
                        stats["structured_receipt_shapes"] += 1
                    else:
                        stats["legacy_unverified"] += 1
                elif status in _UNCERTAIN:
                    stats["uncertain"] += 1
                else:
                    stats["failed"] += 1
        fingerprint_parts.append((step["step_code"], hashlib.sha256(body.encode()).hexdigest(),
                                  hashlib.sha256(json.dumps(media, ensure_ascii=False).encode()).hexdigest()))
        out_steps.append({"step_code": step["step_code"], "media": bool(media), **stats})
    fingerprint = hashlib.sha256(json.dumps(
        {"campaign": campaign_slug, "steps": fingerprint_parts,
         "enrollments": len(recipients), "record_count": len(sends)},
        sort_keys=True, ensure_ascii=False,
    ).encode("utf-8")).hexdigest()
    return {
        "status": "READ_ONLY_PLAN", "campaign_slug": campaign_slug,
        "total_recipients": len(recipients), "consented_recipients": authorized,
        "consent_review_required": len(recipients) - authorized,
        "step_count": len(out_steps), "steps": out_steps,
        "duplicate_history_rows": repeated, "manifest_digest": "sha256:" + fingerprint,
        "approval_status": "NOT_APPROVED", "can_send": False,
        "independently_verified": False,
    }

"""WhatsApp Batch Executor — persistent execution queue per contract P2/P3 80/20.

Orchestrates batch message delivery via WhatsApp Web:
- Reuses the consolidated atomic executor `whatsapp_send_message` from P1.
- Guarantees persistent checkpoints in `whatsapp_control.db`.
- Enforces strict safety & approval gates:
    * Pre-flight dry-run inspection (`whatsapp_batch_preview`).
    * Deterministic approval tokens bound to content + recipient manifest hash.
    * Blocks dispatch if unapproved or if batch was altered after approval.
    * Processes one recipient and one step at a time.
    * Skips masked phones, contacts without permission, and ambiguous identities.
    * NEVER automatically repeats UNCERTAIN operations without operator review.
    * Isolated failures on one contact do not halt the batch.
    * Supports progress inspection, pause, resume, and cancellation.
    * Auto-pauses on excessive consecutive failures to prevent runaway errors.
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional

from workstation.integrations.hermes.whatsapp_browser_executor import (
    STATE_CONFIRMED,
    STATE_FAILED,
    STATE_OBSERVED,
    STATE_REVIEW_REQUIRED,
    STATE_UNCERTAIN,
    WhatsAppSendError,
    _validate_message,
    _validate_phone,
    get_default_db_path,
    whatsapp_send_message,
)

logger = logging.getLogger(__name__)

# Batch Job Statuses
JOB_STATUS_PENDING = "PENDING"
JOB_STATUS_RUNNING = "RUNNING"
JOB_STATUS_PAUSED = "PAUSED"
JOB_STATUS_COMPLETED = "COMPLETED"
JOB_STATUS_CANCELLED = "CANCELLED"
JOB_STATUS_FAILED = "FAILED"

# Stop Request Codes
STOP_NONE = 0
STOP_PAUSE = 1
STOP_CANCEL = 2

# Item Statuses
ITEM_STATUS_QUEUED = "queued"
ITEM_STATUS_SENDING = "sending"
ITEM_STATUS_CONFIRMED = "confirmed"
ITEM_STATUS_UNCERTAIN = "uncertain"
ITEM_STATUS_FAILED = "failed"
ITEM_STATUS_SKIPPED = "skipped"

AUTHORIZED_STATES = ("authorized", "replied_authorized", "invite_sent", "confirmed", "attended", "completed")
OUT_OF_FLOW_STATES = ("opted_out", "skipped")


def _has_verified_send_evidence(proof: Any) -> bool:
    """Only owner-derived recipient-bound outbound ACKs can confirm a send."""
    if not isinstance(proof, dict):
        return False
    identifier = proof.get("message_data_id")
    return bool(
        proof.get("state") == STATE_CONFIRMED
        and proof.get("sent") is True
        and isinstance(identifier, str)
        and len(identifier) == 71
        and identifier.startswith("sha256:")
        and all(ch in "0123456789abcdef" for ch in identifier[7:])
        and proof.get("ack_label") in {"sent", "delivered", "read"}
        and isinstance(proof.get("header_verified"), str)
        and proof["header_verified"].strip()
    )


def now_iso() -> str:
    """Current UTC ISO timestamp."""
    return datetime.now(UTC).isoformat()


def init_batch_tables(conn: sqlite3.Connection) -> None:
    """Initialize batch execution and authorization tables if they do not exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_batch_jobs (
            job_id TEXT PRIMARY KEY,
            campaign_slug TEXT,
            step_code TEXT,
            status TEXT NOT NULL CHECK(status IN ('PENDING', 'RUNNING', 'PAUSED', 'COMPLETED', 'CANCELLED', 'FAILED')),
            total_items INTEGER DEFAULT 0,
            processed_items INTEGER DEFAULT 0,
            confirmed_items INTEGER DEFAULT 0,
            uncertain_items INTEGER DEFAULT 0,
            failed_items INTEGER DEFAULT 0,
            skipped_items INTEGER DEFAULT 0,
            current_contact_id INTEGER,
            next_allowed_at TEXT,
            stop_requested INTEGER DEFAULT 0,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_batch_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL REFERENCES whatsapp_batch_jobs(job_id) ON DELETE CASCADE,
            contact_id INTEGER,
            display_name TEXT,
            phone_digits TEXT,
            contact_name_hint TEXT,
            message_body TEXT NOT NULL,
            permission_status TEXT,
            status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued', 'sending', 'confirmed', 'uncertain', 'failed', 'skipped')),
            error_code TEXT,
            error_message TEXT,
            message_data_id TEXT,
            ack_label TEXT,
            attempted_at TEXT,
            completed_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS whatsapp_batch_authorizations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            approval_token TEXT UNIQUE NOT NULL,
            manifest_hash TEXT NOT NULL,
            campaign_slug TEXT,
            step_code TEXT,
            total_eligible INTEGER NOT NULL,
            approved_by TEXT NOT NULL DEFAULT 'operator',
            approved_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'consumed', 'revoked'))
        )
    """)
    # In-place SQLite upgrade; preserve jobs created by older Hermes versions.
    columns = {row[1] for row in conn.execute("PRAGMA table_info(whatsapp_batch_jobs)")}
    if "next_allowed_at" not in columns:
        conn.execute("ALTER TABLE whatsapp_batch_jobs ADD COLUMN next_allowed_at TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_batch_items_job ON whatsapp_batch_items(job_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_batch_jobs_status ON whatsapp_batch_jobs(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_batch_auth_token ON whatsapp_batch_authorizations(approval_token)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_batch_auth_hash ON whatsapp_batch_authorizations(manifest_hash)")


def _validate_recipient_preflight(
    item: dict[str, Any],
    require_authorization: bool = False,
) -> Optional[dict[str, str]]:
    """Check recipient eligibility before touching browser.

    Returns None if valid, or a dict with error_code and error_message if skipped.
    """
    phone = item.get("phone_digits") or item.get("target") or item.get("phone_number") or ""
    try:
        _validate_phone(phone)
    except WhatsAppSendError as exc:
        return {"error_code": exc.error_code, "error_message": f"Telefone inválido ou mascarado: {phone!r}"}

    msg = item.get("message_body") or item.get("body") or item.get("message") or ""
    try:
        _validate_message(msg)
    except WhatsAppSendError as exc:
        return {"error_code": exc.error_code, "error_message": f"Template inválido: {exc!s}"}

    display_name = (item.get("display_name") or item.get("name") or "").strip()
    # Ambiguous identity guards
    if not display_name or display_name.lower() in ("desconhecido", "unknown", "contato", "[nome]"):
        return {"error_code": "AMBIGUOUS_IDENTITY", "error_message": f"Identidade do contato ambígua ou vazia: {display_name!r}"}

    # Permission check if provided
    permission_status = item.get("permission_status") or item.get("enrollment_status")
    if permission_status in OUT_OF_FLOW_STATES:
        return {"error_code": "OPTED_OUT", "error_message": f"Contato optou por sair do fluxo ({permission_status})."}

    if require_authorization and permission_status not in AUTHORIZED_STATES:
        return {"error_code": "NO_AUTHORIZATION", "error_message": f"Contato sem autorização prévia ({permission_status})."}

    return None


def compute_batch_manifest_hash(
    recipients: list[dict[str, Any]],
    campaign_slug: Optional[str] = None,
    step_code: Optional[str] = None,
    message_template: Optional[str] = None,
) -> str:
    """Compute deterministic SHA256 manifest hash of eligible batch content."""
    items_to_hash = []
    for r in sorted(recipients, key=lambda x: (str(x.get("contact_id") or ""), str(x.get("phone_digits") or x.get("target") or ""))):
        items_to_hash.append({
            "contact_id": r.get("contact_id"),
            "display_name": (r.get("display_name") or r.get("name") or "").strip(),
            "phone_digits": (r.get("phone_digits") or r.get("target") or r.get("phone_number") or "").strip(),
            "message_body": (r.get("message_body") or r.get("body") or r.get("message") or "").strip(),
        })

    payload = {
        "campaign_slug": campaign_slug or "",
        "step_code": step_code or "",
        "message_template": message_template or "",
        "items": items_to_hash,
    }
    canonical_json = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def whatsapp_batch_preview(
    *,
    recipients: list[dict[str, Any]],
    campaign_slug: Optional[str] = None,
    step_code: Optional[str] = None,
    message_template: Optional[str] = None,
    require_authorization: bool = False,
    sample_size: int = 3,
    db_path: Optional[str | Path] = None,
    trusted_execution: bool = False,
) -> dict[str, Any]:
    """Dry-run pre-flight inspection for a batch of WhatsApp messages.

    Zero browser calls. Validates every recipient, computes eligible vs excluded,
    identifies reasons, generates sample rendered texts, and returns the
    manifest_hash required for approval.
    """
    target_path = Path(db_path) if db_path else get_default_db_path()

    already_sent_contacts = set()
    uncertain_contacts = set()
    legacy_unknown_contacts = set()
    legacy_unverified_contacts = set()
    history_lookup_failed = False

    # Read historical effects only for this campaign AND requested step.
    # A legacy row without a step cannot be safely attributed to one step.
    if target_path and target_path.exists() and campaign_slug:
        try:
            with sqlite3.connect(target_path) as conn:
                conn.row_factory = sqlite3.Row
                camp_row = conn.execute(
                    "SELECT id FROM campaigns WHERE slug = ?", (campaign_slug,)
                ).fetchone()
                if camp_row:
                    columns = {
                        row[1] for row in conn.execute("PRAGMA table_info(campaign_sends)")
                    }
                    has_step = "step_code" in columns
                    has_evidence = "evidence" in columns
                    fields = "contact_id, status"
                    if has_step:
                        fields += ", step_code"
                    if has_evidence:
                        fields += ", evidence"
                    query = f"SELECT {fields} FROM campaign_sends WHERE campaign_id = ?"
                    params: tuple[Any, ...] = (camp_row[0],)
                    if step_code and has_step:
                        # Unknown legacy steps must remain on HOLD for this contact.
                        query += " AND (step_code = ? OR step_code IS NULL OR step_code = '')"
                        params += (step_code,)

                    for row in conn.execute(query, params):
                        status = row["status"]
                        if status not in ("sent", "delivered", "read", "confirmed",
                                          "uncertain", "sending"):
                            continue
                        contact_id = row["contact_id"]
                        if step_code and (not has_step or not row["step_code"]):
                            legacy_unknown_contacts.add(contact_id)
                        elif status in ("uncertain", "sending"):
                            uncertain_contacts.add(contact_id)
                        else:
                            already_sent_contacts.add(contact_id)

                        # Historical free-text "verified" is NOT a causal receipt.
                        if status in ("sent", "delivered", "read", "confirmed"):
                            raw = row["evidence"] if has_evidence else None
                            try:
                                proof = json.loads(raw) if isinstance(raw, str) else None
                            except (TypeError, ValueError):
                                proof = None
                            if not _has_verified_send_evidence(proof):
                                legacy_unverified_contacts.add(contact_id)
        except sqlite3.Error as exc:
            # A failed history lookup must not silently authorize a resend.
            logger.warning("WhatsApp batch preview history unavailable: %s", type(exc).__name__)
            history_lookup_failed = True

    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    reasons_breakdown: dict[str, int] = {}

    for r in recipients:
        contact_id = r.get("contact_id")

        # Fail closed on unresolved/unknown history; uncertainty wins over "sent".
        if history_lookup_failed:
            reason = "HISTORY_UNAVAILABLE"
            msg = "Histórico da campanha indisponível; verificar antes de enviar."
        elif contact_id is not None and contact_id in legacy_unknown_contacts:
            reason = "LEGACY_STEP_UNKNOWN"
            msg = "Envio histórico sem etapa identificável; requer conciliação."
        elif contact_id is not None and contact_id in uncertain_contacts:
            reason = "ALREADY_UNCERTAIN"
            msg = "Operação anterior em estado incerto; requer conciliação antes de reenviar."
        elif contact_id is not None and contact_id in already_sent_contacts:
            reason = "ALREADY_SENT"
            msg = "Etapa registrada como enviada; prova histórica pode não ser independente."
        else:
            reason = None

        if reason:
            excluded.append({**r, "reason": reason, "error_message": msg})
            reasons_breakdown[reason] = reasons_breakdown.get(reason, 0) + 1
            continue

        err = _validate_recipient_preflight(r, require_authorization=require_authorization)
        if err:
            reason = err["error_code"]
            msg = err["error_message"]
            excluded.append({**r, "reason": reason, "error_message": msg})
            reasons_breakdown[reason] = reasons_breakdown.get(reason, 0) + 1
        else:
            eligible.append(r)

    legacy_unverified_count = len({
        item.get("contact_id") for item in recipients
        if item.get("contact_id") in legacy_unverified_contacts
    })

    manifest_hash = compute_batch_manifest_hash(
        recipients=eligible,
        campaign_slug=campaign_slug,
        step_code=step_code,
        message_template=message_template,
    )

    sample_messages = []
    for it in eligible[:sample_size]:
        sample_messages.append({
            "contact_id": it.get("contact_id"),
            "display_name": it.get("display_name") or it.get("name"),
            "phone_digits": it.get("phone_digits") or it.get("target"),
            "rendered_message": it.get("message_body") or it.get("body") or it.get("message"),
        })

    # Private execution retains contact data; the public/default contract NEVER
    # serializes phone digits, message bodies, contact names or arbitrary errors.
    # Only the batch executor may request the private in-process representation.
    if trusted_execution:
        return {
            "mode": "dry_run_preview",
            "campaign_slug": campaign_slug,
            "step_code": step_code,
            "total_contacts": len(recipients),
            "eligible_count": len(eligible),
            "excluded_count": len(excluded),
            "reasons_breakdown": reasons_breakdown,
            "legacy_unverified_count": legacy_unverified_count,
            "manifest_hash": manifest_hash,
            "sample_messages": sample_messages,
            "eligible_recipients": eligible,
            "excluded_recipients": excluded,
        }
    return {
        "mode": "dry_run_preview",
        "campaign_slug": campaign_slug,
        "step_code": step_code,
        "total_contacts": len(recipients),
        "eligible_count": len(eligible),
        "excluded_count": len(excluded),
        "reasons_breakdown": reasons_breakdown,
        "legacy_unverified_count": legacy_unverified_count,
        "manifest_hash": manifest_hash,
        "sample_messages": [{"contact_id": i.get("contact_id"),
                             "rendered_message": "[redacted]"}
                            for i in sample_messages],
        "eligible_recipients": [{"contact_id": i.get("contact_id")} for i in eligible],
        "excluded_recipients": [{"contact_id": i.get("contact_id"),
                                 "reason": i.get("reason")} for i in excluded],
    }


def whatsapp_batch_approve(
    *,
    manifest_hash: str,
    campaign_slug: Optional[str] = None,
    step_code: Optional[str] = None,
    total_eligible: int = 0,
    approved_by: str = "operator",
    db_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Fail closed until a trusted human-attested approval issuer is integrated.

    Free-form approved_by is an attribution label, NEVER proof of human approval.
    Do not manufacture a token or create a database from this legacy helper.
    """
    return {
        "status": "DENIED",
        "error_code": "HUMAN_APPROVAL_ATTESTATION_REQUIRED",
        "approval_required": True,
    }


def verify_batch_approval(
    *,
    approval_token: str,
    manifest_hash: str,
    db_path: Optional[str | Path] = None,
) -> tuple[bool, Optional[str]]:
    """Verify approval token validity and exact match with manifest hash."""
    target_path = Path(db_path) if db_path else get_default_db_path()
    if not target_path or not target_path.exists():
        return False, "Banco de dados não encontrado."

    with sqlite3.connect(target_path) as conn:
        conn.row_factory = sqlite3.Row
        init_batch_tables(conn)
        row = conn.execute(
            "SELECT * FROM whatsapp_batch_authorizations WHERE approval_token = ?", (approval_token,)
        ).fetchone()

        if not row:
            return False, "Token de aprovação não encontrado."

        if row["status"] != "active":
            return False, f"Token de aprovação inativo ({row['status']})."

        if row["manifest_hash"] != manifest_hash:
            return False, "Manifest hash divergente: os destinatários ou o conteúdo foram alterados após a aprovação."

    return True, None


def create_batch_job(
    *,
    recipients: list[dict[str, Any]],
    campaign_slug: Optional[str] = None,
    step_code: Optional[str] = None,
    job_id: Optional[str] = None,
    db_path: Optional[str | Path] = None,
) -> str:
    """Create a new batch job with its queued items in SQLite."""
    target_path = Path(db_path) if db_path else get_default_db_path()
    if not target_path:
        raise RuntimeError("No database path configured for WhatsApp batch execution.")

    target_path.parent.mkdir(parents=True, exist_ok=True)
    assigned_job_id = job_id or f"batch_{uuid.uuid4().hex[:12]}"

    with sqlite3.connect(target_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        init_batch_tables(conn)

        conn.execute(
            """
            INSERT INTO whatsapp_batch_jobs
            (job_id, campaign_slug, step_code, status, total_items, stop_requested)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (assigned_job_id, campaign_slug, step_code, JOB_STATUS_PENDING, len(recipients)),
        )

        for r in recipients:
            contact_id = r.get("contact_id")
            display_name = r.get("display_name") or r.get("name") or ""
            phone_digits = r.get("phone_digits") or r.get("target") or r.get("phone_number") or ""
            contact_name_hint = r.get("contact_name_hint") or display_name
            message_body = r.get("message_body") or r.get("body") or r.get("message") or ""
            perm_status = r.get("permission_status") or r.get("enrollment_status") or (r.get("status") if r.get("status") != ITEM_STATUS_QUEUED else None)

            conn.execute(
                """
                INSERT INTO whatsapp_batch_items
                (job_id, contact_id, display_name, phone_digits, contact_name_hint, message_body, permission_status, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (assigned_job_id, contact_id, display_name, phone_digits, contact_name_hint, message_body, perm_status, ITEM_STATUS_QUEUED),
            )
        conn.commit()

    return assigned_job_id


def whatsapp_batch_status(
    job_id: str,
    *,
    db_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Inspect progress, counters, and status of a batch job."""
    target_path = Path(db_path) if db_path else get_default_db_path()
    if not target_path or not target_path.exists():
        return {"error": "Database not found", "job_id": job_id}

    with sqlite3.connect(target_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        job = conn.execute("SELECT * FROM whatsapp_batch_jobs WHERE job_id = ?", (job_id,)).fetchone()
        if not job:
            return {"error": "Job not found", "job_id": job_id}

        items = conn.execute(
            "SELECT * FROM whatsapp_batch_items WHERE job_id = ? ORDER BY id", (job_id,)
        ).fetchall()

        return {
            "job_id": job["job_id"],
            "campaign_slug": job["campaign_slug"],
            "step_code": job["step_code"],
            "status": job["status"],
            "total_items": job["total_items"],
            "processed_items": job["processed_items"],
            "confirmed_items": job["confirmed_items"],
            "uncertain_items": job["uncertain_items"],
            "failed_items": job["failed_items"],
            "skipped_items": job["skipped_items"],
            "current_contact_id": job["current_contact_id"],
            "stop_requested": job["stop_requested"],
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
            "items": [dict(it) for it in items],
        }


def whatsapp_batch_pause(
    job_id: str,
    *,
    db_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Request a batch job to pause execution after the current in-flight item completes."""
    target_path = Path(db_path) if db_path else get_default_db_path()
    if not target_path or not target_path.exists():
        return {"error": "Database not found", "job_id": job_id}

    with sqlite3.connect(target_path) as conn:
        cur = conn.execute(
            "UPDATE whatsapp_batch_jobs SET stop_requested = ? WHERE job_id = ?",
            (STOP_PAUSE, job_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return {"error": "Job not found", "job_id": job_id}

    return {"job_id": job_id, "action": "pause_requested", "status": "PAUSE_REQUESTED"}


def whatsapp_batch_cancel(
    job_id: str,
    *,
    db_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Cancel a batch job."""
    target_path = Path(db_path) if db_path else get_default_db_path()
    if not target_path or not target_path.exists():
        return {"error": "Database not found", "job_id": job_id}

    with sqlite3.connect(target_path) as conn:
        cur = conn.execute(
            "UPDATE whatsapp_batch_jobs SET stop_requested = ?, status = ? WHERE job_id = ?",
            (STOP_CANCEL, JOB_STATUS_CANCELLED, job_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            return {"error": "Job not found", "job_id": job_id}

    return {"job_id": job_id, "action": "cancelled", "status": JOB_STATUS_CANCELLED}


def whatsapp_batch_send(
    *,
    browser_navigate: Callable[..., dict[str, Any]],
    browser_snapshot: Callable[..., dict[str, Any]],
    browser_click: Callable[..., dict[str, Any]],
    recipients: Optional[list[dict[str, Any]]] = None,
    job_id: Optional[str] = None,
    campaign_slug: Optional[str] = None,
    step_code: Optional[str] = None,
    require_authorization: bool = False,
    approval_token: Optional[str] = None,
    approval_threshold: int = 1,
    require_approval: Optional[bool] = None,
    rate_limit_delay_seconds: float = 3.0,
    max_messages: Optional[int] = None,
    max_consecutive_failures: int = 3,
    delivery_timeout_seconds: float = 10.0,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Execute or resume a batch send run with strict persistent checkpointing & approval gates."""
    batch_t0 = time.perf_counter()
    target_path = Path(db_path) if db_path else get_default_db_path()
    if not target_path:
        raise RuntimeError("No database path configured for WhatsApp batch execution.")

    # 1. Approval Gate Evaluation (for new batches)
    if not job_id:
        if not recipients:
            return {"error": "No recipients or job_id provided.", "processed": 0}

        # Run pre-flight preview to evaluate eligible items
        preview = whatsapp_batch_preview(
            recipients=recipients,
            campaign_slug=campaign_slug,
            step_code=step_code,
            require_authorization=require_authorization,
            db_path=target_path,
            trusted_execution=True,
        )

        should_require_approval = (
            require_approval if require_approval is not None
            else (preview["eligible_count"] > approval_threshold)
        )

        if should_require_approval:
            if not approval_token:
                return {
                    "status": "APPROVAL_REQUIRED",
                    "approval_required": True,
                    "manifest_hash": preview["manifest_hash"],
                    "eligible_count": preview["eligible_count"],
                    "preview": {
                        "mode": preview["mode"],
                        "total_contacts": preview["total_contacts"],
                        "eligible_count": preview["eligible_count"],
                        "excluded_count": preview["excluded_count"],
                        "reasons_breakdown": preview["reasons_breakdown"],
                        "sample_messages": [
                            {"contact_id": item.get("contact_id"), "rendered_message": "[redacted]"}
                            for item in preview["sample_messages"]
                        ],
                    },
                    "error_code": "APPROVAL_REQUIRED",
                    "error_message": f"Operação com {preview['eligible_count']} destinatários elegíveis requer aprovação explícita. Utilize o manifest_hash '{preview['manifest_hash']}' para aprovar.",
                }

            is_valid, err_msg = verify_batch_approval(
                approval_token=approval_token,
                manifest_hash=preview["manifest_hash"],
                db_path=target_path,
            )
            if not is_valid:
                return {
                    "status": "APPROVAL_INVALID",
                    "approval_required": True,
                    "manifest_hash": preview["manifest_hash"],
                    "error_code": "APPROVAL_INVALID",
                    "error_message": f"Aprovação rejeitada: {err_msg}",
                }

        # Create job with all recipients
        active_job_id = create_batch_job(
            recipients=recipients,
            campaign_slug=campaign_slug,
            step_code=step_code,
            db_path=target_path,
        )
    else:
        active_job_id = job_id
        # Resuming an existing job
        with sqlite3.connect(target_path) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            init_batch_tables(conn)
            job = conn.execute("SELECT status FROM whatsapp_batch_jobs WHERE job_id = ?", (active_job_id,)).fetchone()
            if not job:
                return {"error": f"Job {active_job_id} not found", "job_id": active_job_id}
            if job[0] in (JOB_STATUS_COMPLETED, JOB_STATUS_CANCELLED):
                status_dict = whatsapp_batch_status(active_job_id, db_path=target_path)
                status_dict["warning"] = f"Job {active_job_id} is already {job[0]}"
                return status_dict
            # An interrupted or uncertain external mutation must be reconciled by
            # the canonical owner before *any* queued recipient can advance.
            unresolved = conn.execute(
                "SELECT COUNT(*) FROM whatsapp_batch_items "
                "WHERE job_id = ? AND status IN (?, ?)",
                (active_job_id, ITEM_STATUS_SENDING, ITEM_STATUS_UNCERTAIN),
            ).fetchone()[0]
            if unresolved:
                conn.execute(
                    "UPDATE whatsapp_batch_jobs SET status=?, error_message=? WHERE job_id=?",
                    (JOB_STATUS_PAUSED, "RECONCILIATION_REQUIRED", active_job_id),
                )
                conn.commit()
                status_dict = whatsapp_batch_status(active_job_id, db_path=target_path)
                status_dict["error_code"] = "RECONCILIATION_REQUIRED"
                return status_dict
            conn.execute(
                "UPDATE whatsapp_batch_jobs SET status = ?, stop_requested = 0 WHERE job_id = ?",
                (JOB_STATUS_RUNNING, active_job_id),
            )
            conn.commit()

    # Set status to RUNNING
    with sqlite3.connect(target_path) as conn:
        conn.execute(
            "UPDATE whatsapp_batch_jobs SET status = ? WHERE job_id = ?",
            (JOB_STATUS_RUNNING, active_job_id),
        )
        conn.commit()

    consecutive_failures = 0
    messages_dispatched = 0

    # Main execution loop
    while True:
        # Check stop requests before grabbing next item
        with sqlite3.connect(target_path) as conn:
            conn.row_factory = sqlite3.Row
            job_row = conn.execute(
                "SELECT stop_requested FROM whatsapp_batch_jobs WHERE job_id = ?", (active_job_id,)
            ).fetchone()
            stop_code = job_row["stop_requested"] if job_row else STOP_NONE

        if stop_code == STOP_PAUSE:
            with sqlite3.connect(target_path) as conn:
                conn.execute("UPDATE whatsapp_batch_jobs SET status = ? WHERE job_id = ?", (JOB_STATUS_PAUSED, active_job_id))
                conn.commit()
            logger.info("Batch %s paused per request.", active_job_id)
            break
        elif stop_code == STOP_CANCEL:
            with sqlite3.connect(target_path) as conn:
                conn.execute("UPDATE whatsapp_batch_jobs SET status = ? WHERE job_id = ?", (JOB_STATUS_CANCELLED, active_job_id))
                conn.commit()
            logger.info("Batch %s cancelled per request.", active_job_id)
            break

        # Check operational message limit
        if max_messages is not None and messages_dispatched >= max_messages:
            logger.info("Batch %s reached max_messages limit (%d). Pausing.", active_job_id, max_messages)
            with sqlite3.connect(target_path) as conn:
                conn.execute("UPDATE whatsapp_batch_jobs SET status = ? WHERE job_id = ?", (JOB_STATUS_PAUSED, active_job_id))
                conn.commit()
            break

        # Check excessive consecutive failures
        if consecutive_failures >= max_consecutive_failures:
            error_msg = f"Auto-paused: {consecutive_failures} consecutive failures encountered."
            logger.error("Batch %s: %s", active_job_id, error_msg)
            with sqlite3.connect(target_path) as conn:
                conn.execute(
                    "UPDATE whatsapp_batch_jobs SET status = ?, error_message = ? WHERE job_id = ?",
                    (JOB_STATUS_PAUSED, error_msg, active_job_id),
                )
                conn.commit()
            break

        # Fetch next queued item deterministically
        with sqlite3.connect(target_path) as conn:
            conn.row_factory = sqlite3.Row
            item_row = conn.execute(
                "SELECT * FROM whatsapp_batch_items WHERE job_id = ? AND status = ? ORDER BY id ASC LIMIT 1",
                (active_job_id, ITEM_STATUS_QUEUED),
            ).fetchone()

        if not item_row:
            # An interrupted send is not a completed job, even when queue is empty.
            with sqlite3.connect(target_path) as conn:
                pending_review = conn.execute(
                    "SELECT COUNT(*) FROM whatsapp_batch_items WHERE job_id=? AND status IN (?, ?)",
                    (active_job_id, ITEM_STATUS_SENDING, ITEM_STATUS_UNCERTAIN),
                ).fetchone()[0]
                conn.execute("UPDATE whatsapp_batch_jobs SET status=? WHERE job_id=?",
                             (JOB_STATUS_PAUSED if pending_review else JOB_STATUS_COMPLETED, active_job_id))
                conn.commit()
            break

        # The cooldown is persisted BEFORE sleeping so a gateway restart
        # cannot silently shorten the interval between recipients.
        with sqlite3.connect(target_path) as conn:
            due_row = conn.execute(
                "SELECT next_allowed_at FROM whatsapp_batch_jobs WHERE job_id=?",
                (active_job_id,),
            ).fetchone()
        if due_row and due_row[0]:
            try:
                wait = (datetime.fromisoformat(due_row[0]) - datetime.now(UTC)).total_seconds()
            except ValueError:
                # An invalid persisted clock cannot authorize an early send.
                with sqlite3.connect(target_path) as conn:
                    conn.execute("UPDATE whatsapp_batch_jobs SET status=?, error_message=? WHERE job_id=?",
                                 (JOB_STATUS_PAUSED, "INVALID_PERSISTED_COOLDOWN", active_job_id))
                    conn.commit()
                break
            if wait > 0:
                time.sleep(min(wait, 1.0))
                continue

        item_id = item_row["id"]
        item_dict = dict(item_row)

        # Preflight validation (masked phone, template leaks, ambiguous identity, permissions)
        preflight_error = _validate_recipient_preflight(item_dict, require_authorization=require_authorization)
        if preflight_error:
            with sqlite3.connect(target_path) as conn:
                conn.execute(
                    """
                    UPDATE whatsapp_batch_items
                    SET status = ?, error_code = ?, error_message = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (ITEM_STATUS_SKIPPED, preflight_error["error_code"], preflight_error["error_message"], now_iso(), item_id),
                )
                conn.execute(
                    """
                    UPDATE whatsapp_batch_jobs
                    SET processed_items = processed_items + 1, skipped_items = skipped_items + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                    """,
                    (active_job_id,),
                )
                conn.commit()
            continue

        # Checkpoint: Mark sending
        with sqlite3.connect(target_path) as conn:
            conn.execute(
                """
                UPDATE whatsapp_batch_items
                SET status = ?, attempted_at = ?
                WHERE id = ?
                """,
                (ITEM_STATUS_SENDING, now_iso(), item_id),
            )
            conn.execute(
                """
                UPDATE whatsapp_batch_jobs
                SET current_contact_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
                """,
                (item_dict.get("contact_id"), active_job_id),
            )
            conn.commit()

        # Step: Dispatch single send via P1 consolidated executor
        try:
            send_res = whatsapp_send_message(
                browser_navigate=browser_navigate,
                browser_snapshot=browser_snapshot,
                browser_click=browser_click,
                phone_digits=item_dict["phone_digits"],
                message=item_dict["message_body"],
                contact_name_hint=item_dict.get("contact_name_hint"),
                verify_delivery=True,
                delivery_timeout_seconds=delivery_timeout_seconds,
                task_id=task_id,
                session_id=session_id,
                operation_id="wa_batch_" + hashlib.sha256(
                    f"{active_job_id}:{item_id}".encode("utf-8")
                ).hexdigest()[:24],
                db_path=target_path,
                persist=True,
            )
        except Exception as exc:
            send_res = {
                "sent": False,
                "state": STATE_FAILED,
                "error_code": "DISPATCH_EXCEPTION",
                "error_message": str(exc),
            }

        if send_res.get("state") == STATE_CONFIRMED and not _has_verified_send_evidence(send_res):
            send_res = {"sent": False, "state": STATE_UNCERTAIN,
                        "error_code": "UNVERIFIED_SEND_RECEIPT"}
        res_state = send_res.get("state")
        ts = now_iso()

        # Update checkpoint based on exact outcome
        with sqlite3.connect(target_path) as conn:
            if res_state == STATE_CONFIRMED:
                consecutive_failures = 0
                messages_dispatched += 1
                conn.execute(
                    """
                    UPDATE whatsapp_batch_items
                    SET status = ?, message_data_id = ?, ack_label = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (ITEM_STATUS_CONFIRMED, send_res.get("message_data_id"), send_res.get("ack_label"), ts, item_id),
                )
                conn.execute(
                    """
                    UPDATE whatsapp_batch_jobs
                    SET processed_items = processed_items + 1, confirmed_items = confirmed_items + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                    """,
                    (active_job_id,),
                )

                if campaign_slug and item_dict.get("contact_id"):
                    _record_campaign_send_mirrored(
                        conn,
                        campaign_slug=campaign_slug,
                        contact_id=item_dict["contact_id"],
                        step_code=step_code,
                        status="sent",
                        evidence=send_res,
                    )

            elif res_state == STATE_UNCERTAIN:
                consecutive_failures += 1
                messages_dispatched += 1
                conn.execute(
                    """
                    UPDATE whatsapp_batch_items
                    SET status = ?, error_code = ?, error_message = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (ITEM_STATUS_UNCERTAIN, send_res.get("error_code", "DELIVERY_TIMEOUT"), "Operação incerta: evidência de entrega não observada no tempo limite.", ts, item_id),
                )
                conn.execute(
                    """
                    UPDATE whatsapp_batch_jobs
                    SET processed_items = processed_items + 1, uncertain_items = uncertain_items + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                    """,
                    (active_job_id,),
                )
                if campaign_slug and item_dict.get("contact_id"):
                    _record_campaign_send_mirrored(
                        conn,
                        campaign_slug=campaign_slug,
                        contact_id=item_dict["contact_id"],
                        step_code=step_code,
                        status="uncertain",
                        evidence=send_res,
                    )

            else:
                consecutive_failures += 1
                err_code = send_res.get("error_code") or res_state
                err_msg = send_res.get("error_message") or send_res.get("error") or "Falha no envio."
                conn.execute(
                    """
                    UPDATE whatsapp_batch_items
                    SET status = ?, error_code = ?, error_message = ?, completed_at = ?
                    WHERE id = ?
                    """,
                    (ITEM_STATUS_FAILED, err_code, err_msg, ts, item_id),
                )
                conn.execute(
                    """
                    UPDATE whatsapp_batch_jobs
                    SET processed_items = processed_items + 1, failed_items = failed_items + 1, updated_at = CURRENT_TIMESTAMP
                    WHERE job_id = ?
                    """,
                    (active_job_id,),
                )
                if campaign_slug and item_dict.get("contact_id"):
                    _record_campaign_send_mirrored(
                        conn,
                        campaign_slug=campaign_slug,
                        contact_id=item_dict["contact_id"],
                        step_code=step_code,
                        status="failed",
                        error_message=err_msg,
                    )

            if res_state == STATE_UNCERTAIN:
                conn.execute("UPDATE whatsapp_batch_jobs SET status=? WHERE job_id=?",
                             (JOB_STATUS_PAUSED, active_job_id))
            elif rate_limit_delay_seconds > 0:
                conn.execute(
                    "UPDATE whatsapp_batch_jobs SET next_allowed_at=? WHERE job_id=?",
                    ((datetime.now(UTC) + timedelta(seconds=rate_limit_delay_seconds)).isoformat(), active_job_id),
                )
            conn.commit()

        # Never advance the contact queue after an unverified external effect.
        if res_state == STATE_UNCERTAIN:
            break

    status_summary = whatsapp_batch_status(active_job_id, db_path=target_path)
    try:
        from workstation.integrations.hermes.whatsapp_metrics import record_operation_metric
        batch_duration_ms = (time.perf_counter() - batch_t0) * 1000.0
        final_job_status = status_summary.get("status", "UNKNOWN")
        state_repr = "CONFIRMED" if final_job_status == JOB_STATUS_COMPLETED else "UNCERTAIN"
        record_operation_metric(
            operation_name="batch_send",
            duration_ms=batch_duration_ms,
            state=state_repr,
            campaign_id=campaign_slug,
            job_id=active_job_id,
            task_id=task_id,
            session_id=session_id,
            tool_calls_count=max(1, status_summary.get("processed_items", 1)),
            ai_turns_count=1,
            tokens_estimated=max(350, status_summary.get("processed_items", 1) * 350),
            deduplications_prevented=status_summary.get("skipped_items", 0),
            db_path=target_path,
        )
    except Exception:
        pass
    return status_summary


def whatsapp_batch_resume(
    job_id: str,
    *,
    browser_navigate: Callable[..., dict[str, Any]],
    browser_snapshot: Callable[..., dict[str, Any]],
    browser_click: Callable[..., dict[str, Any]],
    rate_limit_delay_seconds: float = 3.0,
    max_messages: Optional[int] = None,
    delivery_timeout_seconds: float = 10.0,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Resume a paused or interrupted batch job from its persistent checkpoint."""
    return whatsapp_batch_send(
        browser_navigate=browser_navigate,
        browser_snapshot=browser_snapshot,
        browser_click=browser_click,
        job_id=job_id,
        rate_limit_delay_seconds=rate_limit_delay_seconds,
        max_messages=max_messages,
        delivery_timeout_seconds=delivery_timeout_seconds,
        task_id=task_id,
        session_id=session_id,
        db_path=db_path,
    )


def _record_campaign_send_mirrored(
    conn: sqlite3.Connection,
    *,
    campaign_slug: str,
    contact_id: int,
    step_code: Optional[str],
    status: str,
    evidence: Optional[dict[str, Any]] = None,
    error_message: Optional[str] = None,
) -> None:
    """Mirror only the exact campaign step with controller-derived evidence.

    This projection must never turn an arbitrary LLM summary into `sent`.
    """
    if not step_code:
        return
    if status == "sent" and not _has_verified_send_evidence(evidence):
        return
    try:
        camp_row = conn.execute(
            "SELECT id FROM campaigns WHERE slug = ?", (campaign_slug,)
        ).fetchone()
        if not camp_row:
            return
        campaign_id = camp_row[0]

        enr_row = conn.execute(
            "SELECT id FROM campaign_enrollments WHERE campaign_id = ? AND contact_id = ?",
            (campaign_id, contact_id),
        ).fetchone()
        if not enr_row:
            return
        enrollment_id = enr_row[0]

        msg_row = conn.execute(
            "SELECT id, step_code FROM campaign_messages WHERE campaign_id = ? AND step_code = ?",
            (campaign_id, step_code),
        ).fetchone()
        if not msg_row:
            return
        message_id, step_code = msg_row[0], msg_row[1]

        ts = now_iso()
        existing = conn.execute(
            "SELECT id, status FROM campaign_sends WHERE campaign_id = ? AND contact_id = ? AND campaign_message_id = ?",
            (campaign_id, contact_id, message_id),
        ).fetchone()

        evidence_json = json.dumps(evidence, ensure_ascii=False) if evidence else None

        if existing:
            if existing[1] in ("sent", "delivered", "read") and status != "sent":
                return
            conn.execute(
                """
                UPDATE campaign_sends
                SET status = ?, transport = 'whatsapp_web', attempted_at = ?,
                    sent_at = ?, confirmed_at = ?, evidence = ?, error_message = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    status,
                    ts,
                    ts if status == "sent" else None,
                    ts if status == "sent" else None,
                    evidence_json,
                    error_message,
                    ts,
                    existing[0],
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO campaign_sends
                (campaign_id, enrollment_id, contact_id, campaign_message_id, step_code,
                 channel, status, transport, attempted_at, sent_at, confirmed_at, evidence, error_message)
                VALUES (?, ?, ?, ?, ?, 'whatsapp', ?, 'whatsapp_web', ?, ?, ?, ?, ?)
                """,
                (
                    campaign_id,
                    enrollment_id,
                    contact_id,
                    message_id,
                    step_code,
                    status,
                    ts,
                    ts if status == "sent" else None,
                    ts if status == "sent" else None,
                    evidence_json,
                    error_message,
                ),
            )
    except Exception as exc:
        logger.debug("Mirroring to campaign_sends failed: %s", exc)

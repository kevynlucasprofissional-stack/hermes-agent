"""Private recipient lookup; a resolved identity never authorizes a send."""

from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
import re
import sqlite3
from typing import Any, Mapping


class RecipientResolutionError(Exception):
    """A public-safe failure without source paths or recipient data."""

    def __init__(self, error_code: str) -> None:
        self.error_code = error_code
        super().__init__(error_code)


@dataclass(frozen=True)
class ResolvedRecipient:
    public_reference: dict[str, Any]
    phone_digits: str = field(repr=False)
    display_name: str = field(repr=False)
    db_path: Path = field(repr=False)


def _configured_sources() -> Mapping[str, Any]:
    from hermes_cli.config import cfg_get, load_config_readonly

    sources = cfg_get(load_config_readonly(), "whatsapp", "sources", default={})
    configured = dict(sources) if isinstance(sources, dict) else {}
    # The existing WhatsApp control DB is also a trusted local contact directory.
    # Intake marks new entries unverified; this alias grants identity lookup only.
    from workstation.integrations.hermes.whatsapp_browser_executor import get_default_db_path
    from workstation.integrations.hermes.whatsapp_contact_intake import (
        LOCAL_ALIAS, PENDING_SOURCE, VERIFIED_SOURCE,
    )
    path = get_default_db_path()
    if LOCAL_ALIAS not in configured and path is not None and path.is_file():
        configured[LOCAL_ALIAS] = {
            "db_path": str(path.resolve()),
            "allowed_phone_sources": [PENDING_SOURCE, VERIFIED_SOURCE],
        }
    return configured


def _positive_id(value: Any) -> int:
    if type(value) is not int or value <= 0:
        raise RecipientResolutionError("INVALID_RECIPIENT_REFERENCE")
    return value


def resolve_recipient_reference(
    reference: Mapping[str, Any], *, sources: Mapping[str, Any] | None = None,
) -> ResolvedRecipient:
    """Read a contact from a configured source, without changing its database.

    Source aliases and their accepted provenance come from trusted profile config.
    Campaign scope is optional; it narrows identity and observes recorded denials.
    The caller must still perform its normal human and Browser admission checks.
    """
    if not isinstance(reference, dict) or set(reference) - {
        "source", "contact_id", "campaign_id", "enrollment_id",
    }:
        raise RecipientResolutionError("INVALID_RECIPIENT_REFERENCE")
    alias = reference.get("source")
    configured = _configured_sources() if sources is None else sources
    source = configured.get(alias) if isinstance(alias, str) else None
    if not isinstance(source, dict):
        raise RecipientResolutionError("UNAUTHORIZED_RECIPIENT_SOURCE")
    allowed = source.get("allowed_phone_sources")
    if not isinstance(allowed, list) or not allowed or any(not isinstance(item, str) or not item for item in allowed):
        raise RecipientResolutionError("UNAUTHORIZED_RECIPIENT_SOURCE")
    path_value = source.get("db_path")
    if not isinstance(path_value, str) or not path_value:
        raise RecipientResolutionError("RECIPIENT_SOURCE_UNAVAILABLE")
    path = Path(path_value).expanduser()
    if not path.is_absolute() or not path.is_file():
        raise RecipientResolutionError("RECIPIENT_SOURCE_UNAVAILABLE")
    contact_id = _positive_id(reference["contact_id"]) if "contact_id" in reference else None
    scoped = "campaign_id" in reference or "enrollment_id" in reference
    if scoped:
        campaign_id = _positive_id(reference.get("campaign_id"))
        enrollment_id = _positive_id(reference.get("enrollment_id"))
    elif contact_id is None:
        raise RecipientResolutionError("INVALID_RECIPIENT_REFERENCE")
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as conn:
            conn.row_factory = sqlite3.Row
            if scoped:
                row = conn.execute(
                    "SELECT c.id, c.whatsapp_id, c.display_name, c.type, c.phone_raw, "
                    "c.phone_number, c.phone_source, e.status, e.authorized_at, e.authorized_via "
                    "FROM campaign_enrollments e JOIN contacts c ON c.id = e.contact_id "
                    "WHERE e.id = ? AND e.campaign_id = ?",
                    (enrollment_id, campaign_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT id, whatsapp_id, display_name, type, phone_raw, phone_number, phone_source "
                    "FROM contacts WHERE id = ?", (contact_id,),
                ).fetchone()
    except sqlite3.Error:
        raise RecipientResolutionError("RECIPIENT_SOURCE_UNAVAILABLE") from None
    if row is None or (contact_id is not None and row["id"] != contact_id):
        raise RecipientResolutionError("RECIPIENT_IDENTITY_MISMATCH")
    if scoped and (row["status"] in {"opted_out", "replied_declined", "skipped", "failed"} or (
        row["status"] == "replied_authorized" and not (row["authorized_at"] and row["authorized_via"])
    )):
        raise RecipientResolutionError("RECIPIENT_PERMISSION_DENIED")
    if row["type"] != "contact" or row["phone_source"] not in allowed:
        raise RecipientResolutionError("UNAUTHORIZED_RECIPIENT_SOURCE")
    original = row["phone_raw"] if row["phone_raw"] else row["phone_number"]
    if not isinstance(original, str) or not re.fullmatch(r"\+?[1-9][0-9]{7,14}", original.strip()):
        raise RecipientResolutionError("MASKED_PHONE")
    phone = original.strip().removeprefix("+")
    if alias == "hermes_local":
        # The intake writes both columns. Any one-sided edit/drift blocks send.
        if (row["phone_raw"] != "+" + phone
                or row["phone_number"] != phone):
            raise RecipientResolutionError("RECIPIENT_IDENTITY_MISMATCH")
    identity = str(row["whatsapp_id"])
    # Locally requested unsaved numbers have provisional identities until the
    # native WhatsApp contact-info panel and a causal receipt verify them.
    if alias == "hermes_local" and row["phone_source"] == "user_requested_unverified":
        valid_identity = identity == "pending:" + phone
    elif alias == "hermes_local" and row["phone_source"] == "whatsapp_native_verified":
        valid_identity = identity == phone + "@c.us"
    else:
        valid_identity = identity in {phone, f"{phone}@c.us", f"{phone}@s.whatsapp.net"}
    if not valid_identity:
        raise RecipientResolutionError("RECIPIENT_IDENTITY_MISMATCH")
    public_reference = {"source": alias, "contact_id": row["id"]}
    if scoped:
        public_reference.update(campaign_id=campaign_id, enrollment_id=enrollment_id)
    return ResolvedRecipient(public_reference, phone, row["display_name"], path)

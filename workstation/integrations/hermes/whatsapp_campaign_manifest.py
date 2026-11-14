"""Strict, reusable WhatsApp campaign manifest from local Alvos.json/Mensagem.txt.

No send, UI, or database effects. Never infer messages, phones, or media.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any


class CampaignManifestError(ValueError):
    pass


@dataclass(frozen=True)
class CampaignStep:
    code: str
    kind: str  # text | image
    body: str
    media_path: str | None
    media_sha256: str | None


@dataclass(frozen=True)
class CampaignContact:
    name: str
    phone: str
    opted_out: bool
    steps: tuple[CampaignStep, ...]


@dataclass(frozen=True)
class CampaignManifest:
    source_dir: str
    digest: str
    contacts: tuple[CampaignContact, ...]
    skipped: int
    warnings: tuple[str, ...]


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(262144), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_campaign(source_dir: str | Path) -> CampaignManifest:
    root = Path(source_dir).resolve(strict=True)
    if not root.is_dir() or len(str(root)) > 512:
        raise CampaignManifestError("CAMPAIGN_DIRECTORY_INVALID")
    contacts_file = root / "Alvos.json"
    message_file = root / "Mensagem.txt"
    if not contacts_file.is_file() or not message_file.is_file():
        raise CampaignManifestError("CAMPAIGN_FILES_MISSING")
    if contacts_file.stat().st_size > 1048576 or message_file.stat().st_size > 65536:
        raise CampaignManifestError("CAMPAIGN_FILES_TOO_LARGE")
    try:
        data = json.loads(contacts_file.read_text(encoding="utf-8-sig"))
        messages = message_file.read_text(encoding="utf-8-sig")
    except (UnicodeError, ValueError) as exc:
        raise CampaignManifestError("CAMPAIGN_SOURCE_INVALID") from exc
    people = data.get("presencas", data.get("contatos")) if isinstance(data, dict) else None
    if not isinstance(people, list) or not 1 <= len(people) <= 200:
        raise CampaignManifestError("CAMPAIGN_CONTACTS_INVALID")

    section_re = re.compile(r"(?m)^\[Mensagem\s+(\d{2})\]\s*$")
    positions = list(section_re.finditer(messages))
    if not positions or len(positions) > 15:
        raise CampaignManifestError("CAMPAIGN_MESSAGE_SECTIONS_INVALID")
    if len({m.group(1) for m in positions}) != len(positions):
        raise CampaignManifestError("CAMPAIGN_DUPLICATE_STEP")
    templates: list[tuple[str, str, str, str | None, str | None]] = []
    attachments: list[Path] = []
    for n, m in enumerate(positions):
        chunk = messages[m.end():positions[n + 1].start() if n + 1 < len(positions) else len(messages)].strip()
        kind = "text"
        media_path = None
        media_digest = None
        match = re.match(r'^\[Anexar foto\s+"([^"\r\n]+)"\]\s*', chunk)
        if match:
            kind = "image"
            candidate = Path(match.group(1))
            if not candidate.is_absolute() or not candidate.is_file():
                raise CampaignManifestError("CAMPAIGN_ATTACHMENT_MISSING")
            if candidate.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                raise CampaignManifestError("CAMPAIGN_ATTACHMENT_TYPE_INVALID")
            if candidate.stat().st_size == 0 or candidate.stat().st_size > 20_000_000:
                raise CampaignManifestError("CAMPAIGN_ATTACHMENT_SIZE_INVALID")
            candidate = candidate.resolve(strict=True)
            media_path, media_digest = str(candidate), _sha256(candidate)
            attachments.append(candidate)
            chunk = chunk[match.end():].strip()
        if not chunk or re.search(r"\[(?!Nome\])[^\]]+\]", chunk):
            raise CampaignManifestError("CAMPAIGN_UNRESOLVED_PLACEHOLDER")
        templates.append((m.group(1), kind, chunk, media_path, media_digest))
    warnings: list[str] = []
    sequence = [int(code) for code, *_ in templates]
    missing = sorted(set(range(min(sequence), max(sequence) + 1)) - set(sequence))
    if missing:
        warnings.append("MISSING_MESSAGE_NUMBERS:" + ",".join(str(x).zfill(2) for x in missing))
    raw_phones: set[str] = set()
    contacts: list[CampaignContact] = []
    skipped = 0
    for item in people:
        if not isinstance(item, dict):
            raise CampaignManifestError("CAMPAIGN_CONTACT_INVALID")
        full = str(item.get("nome") or item.get("name") or "").strip()
        phone = re.sub(r"\D", "", str(item.get("telefone") or item.get("phone") or ""))
        if not full or not re.fullmatch(r"[1-9]\d{10,14}", phone):
            raise CampaignManifestError("CAMPAIGN_CONTACT_IDENTITY_INVALID")
        if phone in raw_phones:
            raise CampaignManifestError("CAMPAIGN_DUPLICATE_RECIPIENT")
        raw_phones.add(phone)
        opted_out = (item.get("opt_out") is True or item.get("do_not_contact") is True
                     or str(item.get("status") or "").lower() in {
                         "opted_out", "unsubscribed", "do_not_contact", "sair"})
        first = full.split()[0].lower().capitalize()
        rendered = tuple(CampaignStep(
            code=code, kind=kind, body=body.replace("[Nome]", first),
            media_path=media, media_sha256=media_sha
        ) for code, kind, body, media, media_sha in templates)
        contacts.append(CampaignContact(full, phone, opted_out, rendered))
        skipped += int(opted_out)
    digest = hashlib.sha256(
        json.dumps({
            "contacts": [{
                "phone": p.phone, "name": p.name, "opt_out": p.opted_out,
                "steps": [{
                    "code": s.code, "body": s.body, "media_sha256": s.media_sha256,
                    "kind": s.kind,
                } for s in p.steps],
            } for p in contacts],
        }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf8")
    ).hexdigest()
    return CampaignManifest(str(root), digest, tuple(contacts), skipped, tuple(warnings))

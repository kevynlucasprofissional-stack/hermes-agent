from __future__ import annotations

import hashlib
from typing import Any
from urllib.parse import urlsplit

MAX_STRING_LENGTH = 512
MAX_EVIDENCE_REFS = 32
MAX_PAYLOAD_BYTES = 8 * 1024
_BLOCKED_PARTS = (
    "prompt", "response", "message", "dom", "page_text", "html", "form_value",
    "clipboard", "password", "secret", "authorization", "cookie", "api_key",
    "token", "email_body", "file_content",
)


def _safe_key(key: object) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return not any(part in normalized for part in _BLOCKED_PARTS)


def sanitize_url(value: str) -> dict[str, str | None]:
    parsed = urlsplit(value)
    host = (parsed.hostname or "").lower()
    return {
        "host_hash": hashlib.sha256(host.encode()).hexdigest()[:16] if host else None,
        "page_family": (parsed.path or "/")[:MAX_STRING_LENGTH],
    }


def sanitize_payload(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            if not _safe_key(key):
                continue
            key_text = str(key)[:MAX_STRING_LENGTH]
            if key_text.lower().endswith("url") and isinstance(child, str):
                result[key_text] = sanitize_url(child)
            else:
                result[key_text] = sanitize_payload(child)
        return result
    if isinstance(value, (list, tuple)):
        return [sanitize_payload(item) for item in value[:32]]
    if isinstance(value, str):
        return value[:MAX_STRING_LENGTH]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(type(value).__name__)[:MAX_STRING_LENGTH]

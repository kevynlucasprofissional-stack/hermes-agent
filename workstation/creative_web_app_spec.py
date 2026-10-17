"""CW-047 pure helpers: creative web app names and trusted local addresses.

This module is intentionally NOT wired to the Hermes runtime yet.
A managed process + authority owner must authenticate and confirm the instance
before these helpers may be used to navigate the native Browser.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit


@dataclass(frozen=True)
class CreativeWebApp:
    key: str
    label: str
    source_repository: str


APPS = {
    "photocraft": CreativeWebApp(
        "photocraft", "PhotoCraft", "https://github.com/storytold/photocraft"
    ),
    "effectcraft": CreativeWebApp(
        "effectcraft", "EffectCraft", "https://github.com/storytold/effectcraft"
    ),
    "filmcraft": CreativeWebApp(
        "filmcraft", "FilmCraft", "https://github.com/storytold/filmcraft"
    ),
}

_OPEN = re.compile(
    r"^(?:por favor )?(?:abre|abra|abrir|open) (?:o |a )?"
    r"(photo ?craft|effect ?craft|film ?craft)(?: por favor)?$"
)


def recognize_open_creative_app(message: str) -> CreativeWebApp | None:
    """Exact, human-utterance syntax only. Not an authorization decision."""
    if not isinstance(message, str) or len(message) > 120 or "\n" in message:
        return None
    normalized = unicodedata.normalize("NFKD", message.casefold())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    normalized = " ".join(normalized.strip().rstrip(".!?").split())
    matched = _OPEN.fullmatch(normalized)
    if matched is None:
        return None
    name = matched.group(1).replace(" ", "")
    return APPS.get(name)


def prebuilt_site_root(value: str | Path) -> Path:
    """Resolve an explicitly configured prebuilt web DIST; never install/build."""
    if not value or not str(value).strip():
        raise ValueError("missing_prebuilt_web_dist")
    root = Path(value).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError("web_dist_not_directory")
    index = root / "index.html"
    if not index.is_file() or not index.resolve().is_relative_to(root):
        raise ValueError("web_dist_index_missing_or_outside_root")
    return root


def managed_loopback_url(port: int, path: str = "/") -> str:
    """Construct a URL, never consume an arbitrary host provided by an agent."""
    if isinstance(port, bool) or not isinstance(port, int) or not 1024 <= port <= 65535:
        raise ValueError("invalid_managed_port")
    if path not in {"/", "/index.html"}:
        raise ValueError("invalid_managed_path")
    return f"http://127.0.0.1:{port}{path}"


def matches_managed_loopback_url(observed: str, port: int) -> bool:
    """Readback comparator. Readback MUST be controller-owned, not page text."""
    try:
        parsed = urlsplit(observed)
        return (
            parsed.scheme == "http"
            and parsed.hostname == "127.0.0.1"
            and parsed.port == port
            and parsed.username is None
            and parsed.password is None
            and parsed.path in {"/", "/index.html"}
            and not parsed.query
            and not parsed.fragment
        )
    except (TypeError, ValueError):
        return False

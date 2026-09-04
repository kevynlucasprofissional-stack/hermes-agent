from __future__ import annotations

import time
import urllib.request
from dataclasses import asdict, dataclass, field
from typing import Any
import re

from workstation.routing import BrowserBackend, BrowserRoutingContext


@dataclass(frozen=True, slots=True)
class LightpandaConfig:
    enabled: bool = False
    endpoint: str = "http://127.0.0.1:9222"
    timeout_seconds: float = 15.0
    user_agent: str = "Hermes-Lightpanda/2.0 (Headless; Stateless)"


@dataclass(slots=True)
class LightpandaResult:
    url: str
    status_code: int
    title: str
    text: str
    elements: list[dict[str, Any]] = field(default_factory=list)
    execution_time_ms: float = 0.0
    success: bool = True
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LightpandaAdapter:
    """V2 ultra-lightweight headless browser adapter for stateless, read-only web tasks.

    Enforces strict fail-closed boundary: bound or authenticated tasks are NEVER
    serviced by Lightpanda. Only unbound, public read-only tasks qualify.
    """

    def __init__(self, config: LightpandaConfig | None = None) -> None:
        self.config = config or LightpandaConfig()

    def can_handle(self, ctx: BrowserRoutingContext) -> bool:
        """Verify strict non-negotiable fail-closed invariants."""
        if not self.config.enabled:
            return False
        if ctx.bound_to_internal:
            return False
        if ctx.requires_auth:
            return False
        if ctx.requires_visible_state:
            return False
        return bool(ctx.public_read_only and ctx.headless_ok)

    def execute_read(self, url: str, selector: str | None = None) -> LightpandaResult:
        """Execute a stateless read-only extraction."""
        start = time.perf_counter()
        normalized_url = url.strip()
        if not normalized_url.startswith(("http://", "https://")):
            normalized_url = "https://" + normalized_url

        try:
            req = urllib.request.Request(
                normalized_url,
                headers={
                    "User-Agent": self.config.user_agent,
                    "Accept-Encoding": "gzip, deflate",
                },
            )
            with urllib.request.urlopen(req, timeout=self.config.timeout_seconds) as resp:
                final_url = resp.geturl().lower()
                # H-105 Red Team guard: abort and fail-closed if redirected to auth gate
                auth_signatures = [
                    "/login", "/signin", "/auth", "/session/new", "/sso",
                    "accounts.google.com", "login.microsoftonline.com", "auth0.com"
                ]
                if any(sig in final_url for sig in auth_signatures):
                    raise PermissionError(f"AuthRedirectEncountered: target redirected to '{resp.geturl()}', failing closed to internal browser")

                status_code = resp.getcode()
                charset = (resp.headers.get_content_charset() if hasattr(resp.headers, "get_content_charset") else None) or "utf-8"
                html_bytes = resp.read()

                # Transparent decompression (H-105)
                content_encoding = resp.headers.get("Content-Encoding", "").lower()
                if "gzip" in content_encoding:
                    import gzip
                    html_bytes = gzip.decompress(html_bytes)
                elif "deflate" in content_encoding:
                    import zlib
                    try:
                        html_bytes = zlib.decompress(html_bytes)
                    except zlib.error:
                        html_bytes = zlib.decompress(html_bytes, -zlib.MAX_WBITS)

                html_text = html_bytes.decode(charset, errors="replace")

            # Extract title
            title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
            title = title_match.group(1).strip() if title_match else ""

            # Extract clean readable text (strip scripts, styles, html tags)
            clean_html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_text, flags=re.DOTALL | re.IGNORECASE)
            text_chunks = re.findall(r">([^<]+)<", clean_html)
            text = " ".join(t.strip() for t in text_chunks if t.strip())

            # Extract key link elements
            elements: list[dict[str, Any]] = []
            link_matches = re.findall(r'<a[^>]+href=["\'](.*?)["\'][^>]*>(.*?)</a>', clean_html, re.IGNORECASE | re.DOTALL)
            for href, anchor_text in link_matches[:50]:
                cleaned_anchor = re.sub(r"<[^>]+>", "", anchor_text).strip()
                if cleaned_anchor:
                    elements.append({"tag": "a", "href": href, "text": cleaned_anchor})

            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return LightpandaResult(
                url=normalized_url,
                status_code=status_code,
                title=title,
                text=text[:5000],
                elements=elements,
                execution_time_ms=round(elapsed_ms, 2),
                success=True,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return LightpandaResult(
                url=normalized_url,
                status_code=500,
                title="",
                text="",
                execution_time_ms=round(elapsed_ms, 2),
                success=False,
                error=str(exc),
            )

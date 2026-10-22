"""Unified aggregator for native browser optimization metrics.

Collects per-session statistics for Viewport Filter savings and PageFingerprint
Cache hits, then projects an estimated token saving report.  All data stays
in-memory; no PII (URLs, DOM content, form values) is ever stored.

Gated by ``HERMES_BROWSER_TELEMETRY_UNIFIED=1`` (default OFF).  Every public
function is fail-open: exceptions are caught and logged at debug level so the
aggregator never blocks or crashes the browser pipeline.
"""
from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)

_CHARS_PER_TOKEN = 4  # rough average for English / code payloads


def _enabled() -> bool:
    return os.environ.get("HERMES_BROWSER_TELEMETRY_UNIFIED", "0") == "1"


class _SessionBucket:
    """Thread-safe accumulator for one session_id."""

    __slots__ = (
        "cache_hits",
        "extractions_total",
        "lock",
        "original_chars",
        "projected_chars",
        "semantic_preserved",
        "session_id",
        "start_ts",
        "total_offscreen",
        "total_snapshots",
        "viewport_enabled",
    )

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.start_ts = time.monotonic()
        self.lock = threading.Lock()
        self.total_snapshots = 0
        self.cache_hits = 0
        self.viewport_enabled = False
        self.total_offscreen = 0
        self.semantic_preserved = 0
        self.original_chars = 0
        self.projected_chars = 0
        self.extractions_total = 0

    def record_snapshot(
        self,
        *,
        chars: int,
        cached: bool,
        offscreen_count: int = 0,
        semantic_count: int = 0,
        viewport_filter_enabled: bool = False,
        original_chars: int = 0,
    ) -> None:
        with self.lock:
            self.total_snapshots += 1
            if cached:
                self.cache_hits += 1
            if viewport_filter_enabled:
                self.viewport_enabled = True
            self.total_offscreen += offscreen_count
            self.semantic_preserved += semantic_count
            if original_chars > 0:
                self.original_chars += original_chars
                self.projected_chars += chars

    def record_extraction(self, items_count: int) -> None:
        with self.lock:
            self.extractions_total += 1

    def get_report(self) -> dict[str, Any]:
        with self.lock:
            elapsed = time.monotonic() - self.start_ts
            duration_min = round(elapsed / 60, 1)
            hit_rate = (
                f"{self.cache_hits / self.total_snapshots * 100:.1f}%"
                if self.total_snapshots
                else "0.0%"
            )
            savings_chars = max(0, self.original_chars - self.projected_chars)
            savings_pct = (
                f"{savings_chars / self.original_chars * 100:.1f}%"
                if self.original_chars
                else "0.0%"
            )
            tokens_saved = max(0, round(savings_chars / _CHARS_PER_TOKEN))
            note_parts: list[str] = []
            if self.cache_hits > self.total_snapshots * 0.5 and self.total_snapshots > 10:
                note_parts.append("cache hit rate alto indica página estável")
            if self.total_offscreen > 0:
                note_parts.append(f"{self.total_offscreen} elementos offscreen marcados")
            if not note_parts:
                note_parts.append("sem observações especiais")
            return {
                "session_id": self.session_id,
                "duration_minutes": duration_min,
                "total_snapshots": self.total_snapshots,
                "cache_hits": self.cache_hits,
                "cache_hit_rate": hit_rate,
                "viewport_filter_enabled": self.viewport_enabled,
                "total_offscreen_elements": self.total_offscreen,
                "semantic_preserved": self.semantic_preserved,
                "viewport_savings_chars": savings_chars,
                "viewport_savings_percent": savings_pct,
                "total_tokens_saved_estimate": tokens_saved,
                "extractions_total": self.extractions_total,
                "note": "; ".join(note_parts) + ".",
            }

    def reset(self) -> None:
        with self.lock:
            self.__init__(self.session_id)  # type: ignore[misc]


_store: dict[str, _SessionBucket] = {}
_store_lock = threading.Lock()


def _get_bucket(session_id: str) -> _SessionBucket:
    with _store_lock:
        bucket = _store.get(session_id)
        if bucket is None:
            bucket = _SessionBucket(session_id)
            _store[session_id] = bucket
        return bucket


def record_browser_observation(
    session_id: str | None,
    *,
    action: str,
    chars: int = 0,
    cached: bool = False,
    offscreen_count: int = 0,
    semantic_count: int = 0,
    viewport_filter_enabled: bool = False,
    original_chars: int = 0,
    items_count: int = 0,
) -> None:
    """Best-effort recorder; never raises into the caller path."""
    if not _enabled() or not session_id:
        return
    try:
        bucket = _get_bucket(session_id)
        if action == "browser_snapshot":
            bucket.record_snapshot(
                chars=chars,
                cached=cached,
                offscreen_count=offscreen_count,
                semantic_count=semantic_count,
                viewport_filter_enabled=viewport_filter_enabled,
                original_chars=original_chars,
            )
        elif action == "browser_extract_items" and items_count:
            bucket.record_extraction(items_count)
    except Exception as exc:
        logger.debug("Telemetry aggregator note: %s", exc)


def generate_optimization_report(session_id: str) -> dict[str, Any]:
    """Return consolidated metrics for *session_id* (empty dict if unknown/disabled)."""
    if not _enabled() or not session_id:
        return {}
    try:
        bucket = _get_bucket(session_id)
        return bucket.get_report()
    except Exception as exc:
        logger.debug("Telemetry report note: %s", exc)
        return {}


def reset_session_metrics(session_id: str) -> None:
    """Clear accumulated counters for *session_id*."""
    if not _enabled() or not session_id:
        return
    try:
        bucket = _get_bucket(session_id)
        bucket.reset()
    except Exception as exc:
        logger.debug("Telemetry reset note: %s", exc)
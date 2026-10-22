"""Unified telemetry aggregator: correctness, privacy and fail-open guarantees.

These tests validate the BrowserOptimizationMetrics module (Fase 3 / Telemetria
Unificada) without touching the live browser pipeline. The aggregator is
in-memory per session_id and gated by HERMES_BROWSER_TELEMETRY_UNIFIED=1.
"""
from __future__ import annotations

import os
import time

import pytest

from workstation.telemetry import browser_optimization_metrics as bom


@pytest.fixture(autouse=True)
def _enable_flag(monkeypatch):
    """Ensure the aggregator is active for every test in this module."""
    monkeypatch.setenv("HERMES_BROWSER_TELEMETRY_UNIFIED", "1")
    # Reset global store between tests to avoid cross-contamination.
    with bom._store_lock:
        bom._store.clear()
    yield
    with bom._store_lock:
        bom._store.clear()


def test_record_snapshot_miss_and_hit_accumulate_correctly():
    sid = "sess-miss-hit"
    bom.record_browser_observation(
        sid, action="browser_snapshot", chars=1000, cached=False, original_chars=2000,
    )
    bom.record_browser_observation(
        sid, action="browser_snapshot", chars=1000, cached=True, original_chars=2000,
    )
    report = bom.generate_optimization_report(sid)
    assert report["total_snapshots"] == 2
    assert report["cache_hits"] == 1
    assert report["cache_hit_rate"] == "50.0%"
    # savings = sum(original) - sum(projected) = 4000 - 2000 = 2000
    assert report["viewport_savings_chars"] == 2000
    assert report["total_tokens_saved_estimate"] == 500  # 2000 / 4


def test_viewport_filter_fields_aggregate_per_session():
    sid = "sess-viewport"
    bom.record_browser_observation(
        sid,
        action="browser_snapshot",
        chars=800,
        cached=False,
        offscreen_count=12,
        semantic_count=3,
        viewport_filter_enabled=True,
        original_chars=1200,
    )
    bom.record_browser_observation(
        sid,
        action="browser_snapshot",
        chars=900,
        cached=False,
        offscreen_count=8,
        semantic_count=2,
        viewport_filter_enabled=True,
        original_chars=1100,
    )
    report = bom.generate_optimization_report(sid)
    assert report["viewport_filter_enabled"] is True
    assert report["total_offscreen_elements"] == 20
    assert report["semantic_preserved"] == 5
    assert report["viewport_savings_chars"] == 600  # (1200+1100) - (800+900)


def test_extraction_counter_increments_only_for_extract_action():
    sid = "sess-extract"
    bom.record_browser_observation(sid, action="browser_snapshot", chars=500)
    bom.record_browser_observation(
        sid, action="browser_extract_items", items_count=15,
    )
    bom.record_browser_observation(
        sid, action="browser_extract_items", items_count=7,
    )
    report = bom.generate_optimization_report(sid)
    assert report["extractions_total"] == 2
    assert report["total_snapshots"] == 1


def test_reset_clears_session_counters():
    sid = "sess-reset"
    bom.record_browser_observation(sid, action="browser_snapshot", chars=100, cached=True)
    bom.reset_session_metrics(sid)
    report = bom.generate_optimization_report(sid)
    assert report["total_snapshots"] == 0
    assert report["cache_hits"] == 0
    assert report["cache_hit_rate"] == "0.0%"


def test_disabled_flag_returns_empty_report_and_skips_recording(monkeypatch):
    monkeypatch.setenv("HERMES_BROWSER_TELEMETRY_UNIFIED", "0")
    sid = "sess-disabled"
    bom.record_browser_observation(sid, action="browser_snapshot", chars=999)
    assert bom.generate_optimization_report(sid) == {}


def test_no_pii_in_report_output():
    """Report must never contain URLs, DOM content, form values or secrets."""
    sid = "sess-privacy"
    bom.record_browser_observation(
        sid,
        action="browser_snapshot",
        chars=1000,
        original_chars=2000,
        offscreen_count=5,
        semantic_count=1,
        viewport_filter_enabled=True,
    )
    report = bom.generate_optimization_report(sid)
    serialized = str(report)
    # "token" appears in the legitimate field name "total_tokens_saved_estimate";
    # PII check targets actual secret patterns, not metric labels.
    forbidden = ["https://", "http://", "<div", "password", "secret", "api_key"]
    for pattern in forbidden:
        assert pattern not in serialized, f"PII leak detected: {pattern!r} in report"


def test_unknown_session_returns_zeroed_report():
    """On-demand bucket creation means unknown sessions get a zeroed report, not {}."""
    report = bom.generate_optimization_report("never-recorded")
    assert report["total_snapshots"] == 0
    assert report["cache_hits"] == 0
    assert report["cache_hit_rate"] == "0.0%"
    assert report["viewport_savings_chars"] == 0
    assert report["total_tokens_saved_estimate"] == 0


def test_note_reflects_high_cache_hit_rate():
    sid = "sess-note-cache"
    for _ in range(20):
        bom.record_browser_observation(sid, action="browser_snapshot", chars=100, cached=True)
    report = bom.generate_optimization_report(sid)
    assert "cache hit rate alto" in report["note"]


def test_concurrent_records_do_not_corrupt_counters():
    """Thread-safety smoke test: concurrent writes must not lose updates."""
    import threading

    sid = "sess-concurrent"
    errors: list[Exception] = []

    def writer(n: int):
        try:
            for _ in range(n):
                bom.record_browser_observation(
                    sid,
                    action="browser_snapshot",
                    chars=10,
                    cached=False,
                    original_chars=20,
                )
        except Exception as exc:  # pragma: no cover - defensive
            errors.append(exc)

    threads = [threading.Thread(target=writer, args=(50,)) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    report = bom.generate_optimization_report(sid)
    assert report["total_snapshots"] == 200
    # savings = sum(original) - sum(projected) = 200*20 - 200*10 = 2000
    assert report["viewport_savings_chars"] == 2000
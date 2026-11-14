"""Validate an isolated Electron BrowserTask snapshot with the real Hermes selector.

Input is JSON emitted by the native E2E runner; no browser actions are issued.
"""
from __future__ import annotations

import json
import statistics
import sys
import time

from workstation.system1.browser_read_fastpath import find_visible_control


def main() -> None:
    data = json.load(sys.stdin)
    before, after = data["snapshots"]
    samples = []
    for _ in range(9):
        started = time.perf_counter()
        result = find_visible_control(before, ("button", "Relatórios"), lambda: after)
        samples.append((time.perf_counter() - started) * 1000)
        if (result.status, result.ref, result.reason) != ("verified", "@e1", "exact_match"):
            raise AssertionError(f"Native BrowserTask selector did not verify target: {result}; elements={before.get('elements')!r}; readiness={before.get('readiness')!r}; url={before.get('url')!r}")
    browser_ms = sorted(data["snapshot_durations_ms"])
    selector_ms = sorted(samples)
    print(json.dumps({
        "verified": True,
        "native_browser_task": bool(data.get("native")),
        "no_user_focus": not bool(data.get("renderer_has_focus")),
        "native_tasks": data.get("browser_task_count"),
        "target_ref": result.ref,
        "browser_snapshot_n": len(browser_ms),
        "browser_snapshot_p50_ms": round(statistics.median(browser_ms), 3),
        "browser_snapshot_p95_ms": round(browser_ms[-1], 3),
        "selector_p50_ms": round(statistics.median(selector_ms), 3),
        "selector_p95_ms": round(selector_ms[-1], 3),
        "system2_calls": "not_measured",
        "laya_checkpoint_inference": "not_measured",
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()

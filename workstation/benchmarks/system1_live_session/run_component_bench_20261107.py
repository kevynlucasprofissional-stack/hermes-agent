"""Component-level live-input bench for the System 1 browser read fast path.

Inputs are REAL native snapshots captured from this desktop session's BrowserTask
(live_snapshots_20261107.json). The bench exercises workstation.system1.
browser_read_fastpath.find_visible_control with the real LayaDecisionProvider
loaded from the isolated PM environment.

It is NOT an end-to-end human-origin homologation run: the fast path entry point
(maybe_resolve_browser_find) is gated by HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED
and executes only inside an agent turn. This script never touches that gate, never
dispatches a browser operation and never clicks anything.

Run:
    <isolated-pm-python> workstation/benchmarks/system1_live_session/run_component_bench_20261107.py
"""
from __future__ import annotations

import json
import os
import platform
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

FIXTURE = Path(__file__).with_name("live_snapshots_20261107.json")


def main() -> int:
    from workstation.system1.browser_read_fastpath import find_visible_control
    from workstation.system1.laya_provider import LayaDecisionProvider

    provider = LayaDecisionProvider()
    try:
        provider._ensure_router()
        provider_state = "loaded"
    except Exception as exc:  # pragma: no cover - availability probe
        provider_state = f"unavailable: {type(exc).__name__}: {exc}"

    calls: list[dict] = []

    def counting_decide(request):
        started = time.perf_counter()
        result = provider.decide(request)
        calls.append(
            {
                "ms": round((time.perf_counter() - started) * 1000, 2),
                "provider": getattr(result, "provider", None),
                "answers": dict(getattr(result, "answers", {}) or {}),
                "confidence": dict(getattr(result, "confidence", {}) or {}),
                "abstentions": list(getattr(result, "abstentions", []) or []),
                "fallback_recommended": getattr(result, "fallback_recommended", None),
            }
        )
        return result

    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    results: dict[str, list[dict]] = {}
    # Pass 1 includes cold model load; pass 2 measures warm decision latency.
    for pass_no in (1, 2):
        for name, scenario in fixture["scenarios"].items():
            calls.clear()
            readbacks = {"count": 0}

            def readback(before=scenario["before"], after=scenario["after"]):
                readbacks["count"] += 1
                return after

            started = time.perf_counter()
            receipt = find_visible_control(
                dict(scenario["before"]),
                tuple(scenario["intent"]),
                readback,
                decide=counting_decide,
            )
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            results.setdefault(name, []).append({
                "pass": pass_no,
                "url": scenario["url"],
                "intent": scenario["intent"],
                "status": receipt.status,
                "ref": receipt.ref,
                "reason": receipt.reason,
                "provider": receipt.provider,
                "total_ms": elapsed,
                "readback_calls": readbacks["count"],
                "system1_calls": len(calls),
                "system1_call_ms": [c["ms"] for c in calls],
                "system1_detail": calls[:3],
                "navigate_operation_id": scenario["navigate_receipt"]["operationId"],
                "navigate_revision": scenario["navigate_receipt"]["revision"],
            })

    report = {
        "schema": "hermes.system1.live_session.component_bench.v1",
        "kind": "component-level (NOT an end-to-end human-origin turn)",
        "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "platform": platform.platform(),
        "fastpath_env": os.environ.get("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED"),
        "provider": provider_state,
        "laya_version": getattr(provider.provenance, "laya_version", None),
        "laya_source_sha": getattr(provider.provenance, "laya_source_sha", None),
        "model": getattr(provider.provenance, "model", None),
        "device": getattr(provider.provenance, "device", None),
        "calibration_id": getattr(provider.provenance, "calibration_id", None),
        "results": results,
    }
    out = Path(__file__).with_name("component_bench_20261107.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

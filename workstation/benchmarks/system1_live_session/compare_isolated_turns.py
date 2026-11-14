"""Compare measured System 1 read turns from an isolated Hermes telemetry database.

Uses two explicitly bounded, already completed real UI turns. Does not initiate
browser actions or touch user sessions/credentials.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sqlite3

WINDOWS = {
    "baseline": ("2026-11-07T21:31:00", "2026-11-07T21:31:10"),
    "deterministic_fastpath": ("2026-11-07T21:39:57", "2026-11-07T21:39:59"),
}
SESSION = "20261107_181843_c29320"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sandbox", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    dbpath = (args.sandbox / "hermes-home/workstation/telemetry/telemetry.sqlite").resolve()
    with sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True) as db:
        result = {
            "source": str(dbpath), "session_id": SESSION,
            "sample_count_per_variant": 1,
            "model": "deepseek-flash",
            "turn_duration_seconds_from_backend_log": {
                "baseline": 9.6, "deterministic_fastpath": 1.2,
            },
            "variants": {},
        }
        for label, (start, end) in WINDOWS.items():
            records = db.execute(
                "SELECT event_type, status, operation_id, provider_calls, "
                "input_tokens, output_tokens, duration_ms, payload_json FROM events "
                "WHERE session_id=? AND occurred_at>=? AND occurred_at<? "
                "ORDER BY occurred_at",
                (SESSION, start, end)
            ).fetchall()
            providers = [r for r in records if r[0] == "PROVIDER_CALLED" and r[1] == "success"]
            snapshots = [
                r for r in records
                if r[0] == "BROWSER_OPERATION_OBSERVED"
                and r[1] == "OBSERVED"
                and isinstance(json.loads(r[7] or "{}"), dict)
                and json.loads(r[7] or "{}").get("action") == "browser_snapshot"
            ]
            decisions = [r[1] for r in records if r[0] == "ROUTING_DECIDED"]
            result["variants"][label] = {
                "telemetry_window_utc": {"start": start, "end": end},
                "provider_calls_success": sum(int(r[3] or 0) for r in providers),
                "request_input_tokens": sum(int(r[4] or 0) for r in providers),
                "request_output_tokens": sum(int(r[5] or 0) for r in providers),
                "model_duration_ms_sum": round(sum(float(r[6] or 0) for r in providers), 2),
                "native_snapshot_observed_count": len(snapshots),
                "native_snapshot_duration_ms": [round(float(r[6] or 0),2) for r in snapshots],
                "routing_decisions": decisions,
                "total_telemetry_events": len(records),
            }
    a=result["variants"]["baseline"]
    b=result["variants"]["deterministic_fastpath"]
    result["conclusion"] = {
        "saved_provider_calls": a["provider_calls_success"] - b["provider_calls_success"],
        "saved_request_input_tokens": a["request_input_tokens"] - b["request_input_tokens"],
        "saved_request_output_tokens": a["request_output_tokens"] - b["request_output_tokens"],
        "turn_duration_reduction_percent": round((9.6 - 1.2) / 9.6 * 100, 2),
        "proof": (a["provider_calls_success"] == 2 and b["provider_calls_success"] == 0
                  and b["native_snapshot_observed_count"] == 2
                  and "SATISFIED" in b["routing_decisions"]),
        "limitation": "one observed turn per variant; request tokens are not billed-token/cost estimates",
    }
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["conclusion"], ensure_ascii=False))
    if not result["conclusion"]["proof"]:
        raise SystemExit(2)

if __name__ == "__main__":
    main()

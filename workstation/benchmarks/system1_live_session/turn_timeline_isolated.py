"""Read-only event timeline for one session in a dedicated Hermes sandbox."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sqlite3

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sandbox", type=Path)
    ap.add_argument("session")
    ap.add_argument("--limit", type=int, default=36)
    args = ap.parse_args()
    path = (args.sandbox / "hermes-home/workstation/telemetry/telemetry.sqlite").resolve()
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    cols = [
        "event_type", "occurred_at", "status", "reason_code", "operation_id",
        "provider_calls", "input_tokens", "output_tokens", "duration_ms",
        "source_owner", "payload_json",
    ]
    sql = f"SELECT {', '.join(cols)} FROM events WHERE session_id=? ORDER BY rowid DESC LIMIT ?"
    events = [dict(zip(cols, row)) for row in db.execute(sql, (args.session, args.limit))]
    for row in reversed(events):
        raw = row.pop("payload_json", None)
        try:
            payload = json.loads(raw) if raw else {}
        except ValueError:
            payload = {}
        row["payload_keys"] = list(payload) if isinstance(payload, dict) else []
        if isinstance(payload, dict):
            row["routing_decision"] = payload.get("route") or payload.get("decision")
            row["browser_result_kind"] = payload.get("result_kind")
        print(json.dumps(row, ensure_ascii=False))
    db.close()

if __name__ == "__main__":
    main()

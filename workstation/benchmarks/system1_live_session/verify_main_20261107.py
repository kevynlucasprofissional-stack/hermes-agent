"""Read-only production telemetry verification for a single authorized System 1 turn."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta, timezone
import json
import os
import sqlite3

SESSION = "20261107_220115_133cc6"
START = "2026-11-08T01:01:37"
END = "2026-11-08T01:01:41"
database = (Path(os.environ["LOCALAPPDATA"]) / "hermes" / "workstation" / "telemetry" / "telemetry.sqlite").resolve()
conn = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=2)
cols = ["event_type", "occurred_at", "status", "operation_id", "provider_calls",
        "input_tokens", "output_tokens", "duration_ms", "payload_json", "route", "source_owner"]
query = f"SELECT {', '.join(cols)} FROM events WHERE session_id=? AND occurred_at>=? AND occurred_at<? ORDER BY occurred_at"
records = [dict(zip(cols, r)) for r in conn.execute(query, (SESSION, START, END)).fetchall()]
conn.close()
events = []
for r in records:
    payload = json.loads(r.pop("payload_json") or "{}")
    if not isinstance(payload, dict):
        payload = {}
    r["action"] = payload.get("action")
    r["provider"] = payload.get("provider")
    events.append(r)

observed = [x for x in events if x["event_type"] == "BROWSER_OPERATION_OBSERVED"
            and x["status"] == "OBSERVED"]
snapshots = [x for x in observed if x["action"] == "browser_snapshot"]
mutations = [x for x in events if x["event_type"] == "BROWSER_OPERATION_OBSERVED"
             and x["action"] not in (None, "browser_snapshot")]
calls = [x for x in events if x["event_type"] == "PROVIDER_CALLED"]
decisions = [x for x in events if x["event_type"] == "ROUTING_DECIDED"]
print(json.dumps({"session": SESSION, "window_utc": [START, END], "telemetry_db": str(database),
                  "events": events,
                  "summary": {"observed_snapshots": len(snapshots), "browser_mutations": len(mutations),
                              "provider_calls": len(calls), "routing_decisions": [x["status"] for x in decisions],
                              "snapshot_ms": [x["duration_ms"] for x in snapshots],
                              "pass": len(snapshots) == 2 and len(mutations) == 0
                                      and len(calls) == 0 and any(x["status"]=="SATISFIED" for x in decisions)}},
                 ensure_ascii=False, indent=2))
if not (len(snapshots) == 2 and len(mutations) == 0 and len(calls) == 0 and
        any(x["status"] == "SATISFIED" for x in decisions)):
    raise SystemExit(2)

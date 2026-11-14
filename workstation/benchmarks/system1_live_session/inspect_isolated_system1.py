"""Read-only status and token evidence for the separate System 1 Desktop instance."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sqlite3

def connect(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{db.resolve().as_uri()}?mode=ro", uri=True, timeout=2.0)

def rows(db: sqlite3.Connection, table: str, limit=3):
    cols = [row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()]
    return cols, [dict(zip(cols, row)) for row in db.execute(
        f"SELECT * FROM {table} ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("sandbox", type=Path)
    args = p.parse_args()
    home = args.sandbox / "hermes-home"
    for name, dbfile in [
        ("kanban", home / "kanban.db"),
        ("telemetry", home / "workstation" / "telemetry" / "telemetry.sqlite"),
    ]:
        if not dbfile.is_file():
            print(json.dumps({"database":name,"missing":True}))
            continue
        db = connect(dbfile)
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        print(json.dumps({"database":name,"tables":tables}))
        for t in tables:
            if t not in ("tasks", "task_runs", "events", "telemetry_events", "work_items"):
                continue
            cols, samples = rows(db,t)
            # Drop payloads and text blobs, preserving task/run identity and numeric metrics.
            keep = {c for c in cols if c in (
                "id", "task_id","run_id","session_id","status","state","current_run_id",
                "event_type","type","kind","timestamp","created_at","updated_at",
                "started_at","ended_at","provider_calls","input_tokens",
                "output_tokens","duration_ms","name","outcome"
            )}
            sanitized = [{k: v for k,v in s.items() if k in keep} for s in samples]
            print(json.dumps({"table":t,"columns":cols,"recent":sanitized},default=str))
        db.close()

if __name__ == "__main__":
    main()

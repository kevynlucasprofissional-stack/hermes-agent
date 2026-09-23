from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from hermes_constants import get_hermes_home

from .models import TelemetryEventV1
from .privacy import MAX_EVIDENCE_REFS, MAX_PAYLOAD_BYTES, sanitize_payload

DEFAULT_MAX_EVENTS = 250_000


class SQLiteTelemetrySink:
    def __init__(self, path: Path | str | None = None, *, max_events: int = DEFAULT_MAX_EVENTS,
                 prune_batch: int = 1_000):
        self.path = Path(path) if path else get_hermes_home() / "workstation" / "telemetry" / "telemetry.sqlite"
        self.max_events = max(1, int(max_events))
        self.prune_batch = max(1, int(prune_batch))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=0.25)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=250")
        return conn

    def _initialize(self) -> None:
        columns = """
            event_id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL,
            event_type TEXT NOT NULL, occurred_at TEXT NOT NULL, recorded_at TEXT NOT NULL,
            session_id TEXT, task_id TEXT, run_id TEXT, turn_id TEXT, operation_id TEXT,
            capability_id TEXT, capability_version TEXT, route TEXT, phase TEXT, status TEXT,
            reason_code TEXT, duration_ms REAL, provider_calls INTEGER, input_tokens INTEGER,
            output_tokens INTEGER, tool_calls INTEGER, source_owner TEXT NOT NULL, build_sha TEXT,
            workstation_version TEXT, environment TEXT, dedupe_key TEXT,
            evidence_refs_json TEXT NOT NULL, payload_json TEXT NOT NULL
        """
        with self._connect() as conn:
            conn.execute(f"CREATE TABLE IF NOT EXISTS events ({columns})")
            for column in ("occurred_at", "event_type", "task_id", "run_id", "operation_id", "capability_id"):
                conn.execute(f"CREATE INDEX IF NOT EXISTS idx_events_{column} ON events({column})")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_events_dedupe_key ON events(dedupe_key) WHERE dedupe_key IS NOT NULL")

    def emit(self, event: TelemetryEventV1) -> None:
        if len(event.evidence_refs) > MAX_EVIDENCE_REFS:
            raise ValueError("telemetry evidence_refs exceeds 32")
        payload_json = json.dumps(sanitize_payload(event.payload), sort_keys=True, separators=(",", ":"))
        if len(payload_json.encode("utf-8")) > MAX_PAYLOAD_BYTES:
            raise ValueError("telemetry payload exceeds 8 KiB")
        evidence_json = json.dumps(list(event.evidence_refs), separators=(",", ":"))
        data = event.to_dict()
        data["event_type"] = event.event_type.value
        data["evidence_refs_json"] = evidence_json
        data["payload_json"] = payload_json
        names = (
            "event_id", "schema_version", "event_type", "occurred_at", "recorded_at",
            "session_id", "task_id", "run_id", "turn_id", "operation_id", "capability_id",
            "capability_version", "route", "phase", "status", "reason_code", "duration_ms",
            "provider_calls", "input_tokens", "output_tokens", "tool_calls", "source_owner",
            "build_sha", "workstation_version", "environment", "dedupe_key",
            "evidence_refs_json", "payload_json",
        )
        values = tuple(data.get(name) for name in names)
        with self._connect() as conn:
            conn.execute(
                f"INSERT OR IGNORE INTO events ({','.join(names)}) VALUES ({','.join('?' for _ in names)})",
                values,
            )
            count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            if count > self.max_events:
                delete_count = max(self.prune_batch, count - self.max_events)
                conn.execute(
                    "DELETE FROM events WHERE event_id IN (SELECT event_id FROM events ORDER BY occurred_at, recorded_at, rowid LIMIT ?)",
                    (delete_count,),
                )


class TelemetryQuery:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def events(self, *, start: str | None = None, end: str | None = None,
               event_type: str | None = None, task_id: str | None = None,
               run_id: str | None = None, operation_id: str | None = None,
               capability_id: str | None = None) -> list[TelemetryEventV1]:
        clauses: list[str] = []
        values: list[str] = []
        dimensions = {"event_type": event_type, "task_id": task_id, "run_id": run_id,
                      "operation_id": operation_id, "capability_id": capability_id}
        for name, value in dimensions.items():
            if value is not None:
                clauses.append(f"{name}=?")
                values.append(value)
        if start is not None:
            clauses.append("occurred_at>=?")
            values.append(start)
        if end is not None:
            clauses.append("occurred_at<=?")
            values.append(end)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with sqlite3.connect(self.path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"SELECT * FROM events{where} ORDER BY occurred_at, recorded_at, rowid", values).fetchall()
        result = []
        for row in rows:
            data = dict(row)
            data["evidence_refs"] = json.loads(data.pop("evidence_refs_json"))
            data["payload"] = json.loads(data.pop("payload_json"))
            result.append(TelemetryEventV1.from_dict(data))
        return result

    def reconstruct_run(self, task_id: str, run_id: str) -> list[TelemetryEventV1]:
        return self.events(task_id=task_id, run_id=run_id)

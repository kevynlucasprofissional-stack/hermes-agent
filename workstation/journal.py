from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

from hermes_constants import get_hermes_home
from workstation.contracts import EvidenceRef, ExecutionEvent, ExecutionEventKind, RiskLevel, utc_now


def get_journal_dir() -> Path:
    """Resolve the directory for durable workstation execution journals."""
    d = get_hermes_home() / "workstation" / "journals"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_journal_path(task_id: str) -> Path:
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in task_id)
    return get_journal_dir() / f"{safe_name}.jsonl"


class ExecutionJournal:
    """Durable append-only execution and evidence journal for Workstation tasks."""

    def __init__(self, task_id: str, session_id: str, *, file_path: Path | None = None) -> None:
        self.task_id = task_id
        self.session_id = session_id
        self.file_path = file_path or get_journal_path(task_id)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: ExecutionEvent) -> None:
        line = json.dumps(event.to_dict(), ensure_ascii=False) + "\n"
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(line)

    def record(
        self,
        kind: ExecutionEventKind,
        message: str,
        *,
        url: str | None = None,
        risk: RiskLevel = RiskLevel.LOW,
        evidence: list[EvidenceRef] | None = None,
        metadata: dict[str, Any] | None = None,
        browser_tab_id: str | None = None,
    ) -> ExecutionEvent:
        event = ExecutionEvent(
            kind=kind,
            task_id=self.task_id,
            session_id=self.session_id,
            message=message,
            url=url,
            risk=risk,
            evidence=evidence or [],
            metadata=metadata or {},
            browser_tab_id=browser_tab_id,
        )
        self.append(event)
        return event

    def read_events(self) -> list[ExecutionEvent]:
        if not self.file_path.exists():
            return []
        events: list[ExecutionEvent] = []
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    ev_refs = [
                        EvidenceRef(**ref) if isinstance(ref, dict) else ref
                        for ref in data.get("evidence", [])
                    ]
                    event = ExecutionEvent(
                        kind=ExecutionEventKind(data["kind"]),
                        task_id=data["task_id"],
                        session_id=data["session_id"],
                        message=data["message"],
                        timestamp=data.get("timestamp", utc_now()),
                        event_id=data.get("event_id", ""),
                        browser_tab_id=data.get("browser_tab_id"),
                        url=data.get("url"),
                        risk=RiskLevel(data.get("risk", "low")),
                        evidence=ev_refs,
                        metadata=data.get("metadata", {}),
                    )
                    events.append(event)
                except Exception:
                    continue
        return events

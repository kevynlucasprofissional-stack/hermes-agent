from __future__ import annotations

import logging
from typing import Any, Iterable, Optional
import sqlite3

from hermes_cli import kanban_db
from workstation.config import load_workstation_config
from workstation.contracts import BrowserTaskReport, DiscoveredTask, ExecutionEventKind, RiskLevel
from workstation.journal import ExecutionJournal

_log = logging.getLogger(__name__)


def is_multistep_request(prompt: str) -> bool:
    """Classify if a user request is a multistep/asynchronous workflow."""
    keywords = [
        "workflow",
        "multistep",
        "step by step",
        "first",
        "then",
        "finally",
        "automate",
        "extract and",
        "sign in and",
        "fill out",
        "download and",
        "search and",
        "pipeline",
        "batch",
        "follow-up",
        "scrape and",
    ]
    lower = prompt.lower()
    return any(kw in lower for kw in keywords) or ("\n" in prompt.strip() and len(prompt.strip()) > 30)


class WorkstationKanbanBridge:
    """Bridge between Workstation tasks and the canonical Kanban SQLite database."""

    def __init__(self, *, board: Optional[str] = None) -> None:
        self.board = board

    def get_connection(self) -> sqlite3.Connection:
        return kanban_db.connect(board=self.board)

    def promote_request_if_multistep(
        self,
        prompt: str,
        *,
        session_id: str,
        title: Optional[str] = None,
        force: bool = False,
    ) -> Optional[str]:
        """Automatically create a parent Kanban task for a multistep request."""
        cfg = load_workstation_config()
        should_create = force or (
            cfg.raw.get("tasks", {}).get("create_kanban_for_multistep", True)
            and is_multistep_request(prompt)
        )
        if not should_create:
            return None

        clean_title = (title or prompt.strip().split("\n")[0])[:80]
        with self.get_connection() as conn:
            task_id = kanban_db.create_task(
                conn,
                title=clean_title,
                body=prompt,
                created_by="workstation",
                session_id=session_id,
                board=self.board,
                initial_status="running",
            )

        # Start journal for this task
        journal = ExecutionJournal(task_id, session_id)
        journal.record(
            ExecutionEventKind.TASK_CREATED,
            f"Workstation task promoted into Kanban: {clean_title}",
            metadata={"source": "automatic_multistep_promotion", "prompt": prompt},
        )
        return task_id

    def record_discovered_followup(
        self,
        parent_task_id: str,
        followup: DiscoveredTask,
    ) -> str:
        """Record a discovered child task into Kanban with parent dependency."""
        followup.validate()

        with self.get_connection() as conn:
            child_task_id = kanban_db.create_task(
                conn,
                title=followup.title,
                body=f"Reason: {followup.reason}\nDiscovered by: {followup.discovered_by}",
                created_by=followup.discovered_by,
                parents=[parent_task_id],
                session_id=followup.origin_session_id,
                board=self.board,
            )
            if followup.required_for_parent:
                try:
                    kanban_db.block_task(
                        conn,
                        parent_task_id,
                        reason=f"Blocked by required follow-up child task {child_task_id}: {followup.title}",
                        kind="needs_input",
                    )
                except Exception as e:
                    _log.warning("Could not transition parent task %s to blocked: %s", parent_task_id, e)

        # Update followup instance with assigned task_id
        followup.task_id = child_task_id

        # Record into journal
        journal = ExecutionJournal(parent_task_id, followup.origin_session_id)
        journal.record(
            ExecutionEventKind.FOLLOWUP_CREATED,
            f"Discovered child task {child_task_id}: {followup.title}",
            evidence=followup.evidence,
            metadata={
                "child_task_id": child_task_id,
                "reason": followup.reason,
                "discovered_by": followup.discovered_by,
                "required_for_parent": followup.required_for_parent,
            },
        )
        return child_task_id

    def complete_task_with_report(
        self,
        task_id: str,
        report: BrowserTaskReport,
    ) -> bool:
        """Complete Kanban task with structured Workstation report metadata."""
        metadata = report.to_kanban_metadata()
        with self.get_connection() as conn:
            success = kanban_db.complete_task(
                conn,
                task_id=task_id,
                result=report.result,
                summary=report.objective,
                metadata=metadata,
            )

        journal = ExecutionJournal(task_id, report.session_id)
        journal.record(
            ExecutionEventKind.TASK_COMPLETED,
            f"Workstation task completed: {report.result}",
            evidence=report.evidence,
            metadata={"completed": report.completed, "sites": report.sites},
        )
        return success

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import shutil
from typing import Any, Callable, Optional

from workstation.contracts import ExecutionEventKind, RiskLevel
from workstation.journal import ExecutionJournal

_log = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkerStatus(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass(slots=True)
class WorkerHarnessInfo:
    worker_id: str
    name: str
    harness_type: str  # "cli" | "sdk" | "mcp" | "subagent"
    executable: str
    capabilities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    status: WorkerStatus = WorkerStatus.AVAILABLE

    def is_installed(self) -> bool:
        if not self.executable:
            return True
        return shutil.which(self.executable) is not None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["installed"] = self.is_installed()
        return data


@dataclass(slots=True)
class DelegatedTaskHandoff:
    handoff_id: str
    worker_id: str
    parent_task_id: str
    session_id: str
    subtask_prompt: str
    created_at: str = field(default_factory=_utc_now)
    completed_at: str | None = None
    result: str | None = None
    success: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkerRegistry:
    """Registry and orchestrator for specialized worker agents (Codex, Claude Code, Antigravity, OpenCode).

    Retains canonical Hermes task/session/card lineage while delegating bounded subtasks.
    """

    def __init__(self) -> None:
        self._workers: dict[str, WorkerHarnessInfo] = {}
        self._handoffs: dict[str, DelegatedTaskHandoff] = {}
        self._register_default_known_workers()

    def _register_default_known_workers(self) -> None:
        defaults = [
            WorkerHarnessInfo(
                worker_id="antigravity",
                name="Antigravity Coding Assistant",
                harness_type="subagent",
                executable="agy",
                capabilities=["code_editing", "codebase_research", "terminal_execution", "tdd"],
            ),
            WorkerHarnessInfo(
                worker_id="claude-code",
                name="Claude Code CLI",
                harness_type="cli",
                executable="claude",
                capabilities=["code_editing", "terminal_execution", "large_refactoring"],
            ),
            WorkerHarnessInfo(
                worker_id="codex",
                name="OpenAI Codex Harness",
                harness_type="cli",
                executable="codex",
                capabilities=["code_generation", "unit_test_authoring"],
            ),
            WorkerHarnessInfo(
                worker_id="opencode",
                name="OpenCode Worker",
                harness_type="cli",
                executable="opencode",
                capabilities=["code_editing", "git_operations"],
            ),
            WorkerHarnessInfo(
                worker_id="k-tools-neo",
                name="K-Tools-Neo Host Automation",
                harness_type="cli",
                executable="ktools",
                capabilities=["windows_automation", "clipboard", "system_diagnostics"],
            ),
        ]
        for w in defaults:
            self.register_worker(w)

    def register_worker(self, worker: WorkerHarnessInfo) -> None:
        self._workers[worker.worker_id] = worker

    def get_worker(self, worker_id: str) -> WorkerHarnessInfo | None:
        return self._workers.get(worker_id)

    def list_workers(self, capability_filter: str | None = None) -> list[WorkerHarnessInfo]:
        workers = list(self._workers.values())
        if capability_filter:
            return [w for w in workers if capability_filter in w.capabilities]
        return workers

    def delegate_subtask(
        self,
        worker_id: str,
        parent_task_id: str,
        session_id: str,
        prompt: str,
        *,
        executor_fn: Optional[Callable[[str], str]] = None,
        journal: Optional[ExecutionJournal] = None,
    ) -> DelegatedTaskHandoff:
        """Delegate a bounded subtask to a worker agent while preserving canonical lineage."""
        worker = self.get_worker(worker_id)
        if not worker:
            raise ValueError(f"Worker '{worker_id}' not found in registry")

        from uuid import uuid4
        handoff_id = f"handoff-{uuid4().hex[:8]}"

        handoff = DelegatedTaskHandoff(
            handoff_id=handoff_id,
            worker_id=worker_id,
            parent_task_id=parent_task_id,
            session_id=session_id,
            subtask_prompt=prompt,
        )
        self._handoffs[handoff_id] = handoff

        # Record in canonical ExecutionJournal
        if journal:
            journal.record(
                kind=ExecutionEventKind.TASK_STARTED,
                message=f"Delegated subtask to worker '{worker.name}' ({worker_id})",
                metadata={
                    "worker_id": worker_id,
                    "handoff_id": handoff_id,
                    "prompt": prompt[:200],
                },
            )

        if executor_fn:
            try:
                res = executor_fn(prompt)
                handoff.result = res
                handoff.success = True
                handoff.completed_at = _utc_now()
                if journal:
                    journal.record(
                        kind=ExecutionEventKind.ACTION,
                        message=f"Worker '{worker_id}' completed delegated subtask",
                        metadata={"handoff_id": handoff_id, "result_preview": str(res)[:200]},
                    )
            except Exception as exc:
                handoff.success = False
                handoff.result = str(exc)
                handoff.completed_at = _utc_now()
                if journal:
                    journal.record(
                        kind=ExecutionEventKind.ERROR,
                        message=f"Worker '{worker_id}' failed: {exc}",
                        metadata={"handoff_id": handoff_id},
                    )

        return handoff

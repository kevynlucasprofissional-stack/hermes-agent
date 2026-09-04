from __future__ import annotations

import pytest

from workstation.contracts import ExecutionEventKind
from workstation.journal import ExecutionJournal
from workstation.workers import (
    DelegatedTaskHandoff,
    WorkerHarnessInfo,
    WorkerRegistry,
    WorkerStatus,
)


def test_worker_registry_defaults():
    registry = WorkerRegistry()
    workers = registry.list_workers()
    assert len(workers) >= 5

    worker_ids = {w.worker_id for w in workers}
    assert "antigravity" in worker_ids
    assert "claude-code" in worker_ids
    assert "codex" in worker_ids
    assert "opencode" in worker_ids
    assert "k-tools-neo" in worker_ids


def test_worker_registry_filtering():
    registry = WorkerRegistry()
    code_editing_workers = registry.list_workers(capability_filter="code_editing")
    assert len(code_editing_workers) >= 3

    agy = registry.get_worker("antigravity")
    assert agy is not None
    assert agy.name == "Antigravity Coding Assistant"
    assert "tdd" in agy.capabilities
    assert agy.to_dict()["worker_id"] == "antigravity"


def test_delegate_subtask_successful(tmp_path):
    journal_path = tmp_path / "journal.jsonl"
    journal = ExecutionJournal("task-parent-123", "session-dogfood-456", file_path=journal_path)
    registry = WorkerRegistry()

    def mock_executor(prompt: str) -> str:
        return f"Processed: {prompt.upper()}"

    handoff = registry.delegate_subtask(
        worker_id="antigravity",
        parent_task_id="task-parent-123",
        session_id="session-dogfood-456",
        prompt="run unit test suite",
        executor_fn=mock_executor,
        journal=journal,
    )

    assert handoff.success is True
    assert handoff.result == "Processed: RUN UNIT TEST SUITE"
    assert handoff.parent_task_id == "task-parent-123"
    assert handoff.session_id == "session-dogfood-456"
    assert handoff.completed_at is not None

    events = journal.read_events()
    assert len(events) == 2
    assert events[0].kind == ExecutionEventKind.TASK_STARTED
    assert events[1].kind == ExecutionEventKind.ACTION
    assert "antigravity" in events[0].message


def test_delegate_subtask_failure(tmp_path):
    journal_path = tmp_path / "journal.jsonl"
    journal = ExecutionJournal("task-parent-999", "session-err-001", file_path=journal_path)
    registry = WorkerRegistry()

    def failing_executor(prompt: str) -> str:
        raise RuntimeError("CLI failed to execute")

    handoff = registry.delegate_subtask(
        worker_id="claude-code",
        parent_task_id="task-parent-999",
        session_id="session-err-001",
        prompt="refactor large file",
        executor_fn=failing_executor,
        journal=journal,
    )

    assert handoff.success is False
    assert "CLI failed to execute" in (handoff.result or "")
    assert handoff.completed_at is not None

    events = journal.read_events()
    assert len(events) == 2
    assert events[1].kind == ExecutionEventKind.ERROR
    assert "failed" in events[1].message


def test_delegate_subtask_unknown_worker():
    registry = WorkerRegistry()
    with pytest.raises(ValueError, match="not found in registry"):
        registry.delegate_subtask(
            worker_id="nonexistent-worker",
            parent_task_id="task-1",
            session_id="sess-1",
            prompt="do something",
        )

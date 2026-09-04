from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


from datetime import datetime, timezone, timedelta


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _lease_expiry(seconds: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


class ScheduledTaskState(str, Enum):
    QUEUED = "queued"
    ACTIVE = "active"
    WAITING_FOR_HUMAN = "waiting_for_human"
    PARKED = "parked"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class ScheduledTask:
    task_id: str
    session_id: str
    priority: int = 10
    state: ScheduledTaskState = ScheduledTaskState.QUEUED
    created_at: str = field(default_factory=_utc_now)
    started_at: str | None = None
    completed_at: str | None = None
    lease_owner: str | None = None
    lease_expires_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data


class MultiTaskScheduler:
    """V1.1 multi-task scheduling and queue ownership engine.

    Guarantees the core Workstation invariant: at most one task can be ACTIVE
    (bound to the live native host) at any given moment. Sibling tasks are queued,
    parked, or waiting for human input in order of priority and arrival.
    Includes heartbeat and lease expiration guards against orphan task deadlocks.
    """

    def __init__(self, lease_timeout_seconds: float = 120.0) -> None:
        self._tasks: dict[str, ScheduledTask] = {}
        self.lease_timeout_seconds = lease_timeout_seconds

    def enqueue(
        self,
        task_id: str,
        session_id: str,
        priority: int = 10,
        metadata: dict[str, Any] | None = None,
    ) -> ScheduledTask:
        """Add a task to the queue."""
        if task_id in self._tasks:
            return self._tasks[task_id]

        task = ScheduledTask(
            task_id=task_id,
            session_id=session_id,
            priority=priority,
            state=ScheduledTaskState.QUEUED,
            metadata=metadata or {},
        )
        self._tasks[task_id] = task

        # Auto-dispatch if no task is currently active
        if self.active_task() is None:
            self.dispatch_next()

        return task

    def active_task(self) -> ScheduledTask | None:
        """Return the currently ACTIVE task, if any."""
        for task in self._tasks.values():
            if task.state == ScheduledTaskState.ACTIVE:
                return task
        return None

    def dispatch_next(self) -> ScheduledTask | None:
        """Activate the highest-priority queued task if host is free."""
        if self.active_task() is not None:
            return None

        queued_tasks = [
            t for t in self._tasks.values()
            if t.state == ScheduledTaskState.QUEUED
        ]
        if not queued_tasks:
            return None

        # Sort by priority DESC, then created_at ASC (FIFO)
        queued_tasks.sort(key=lambda t: (-t.priority, t.created_at))
        next_task = queued_tasks[0]
        next_task.state = ScheduledTaskState.ACTIVE
        next_task.started_at = _utc_now()
        next_task.lease_owner = f"worker-{next_task.task_id}"
        next_task.lease_expires_at = _lease_expiry(self.lease_timeout_seconds)
        return next_task

    def heartbeat(self, task_id: str) -> bool:
        """Renew the active task's lease duration."""
        task = self._tasks.get(task_id)
        if not task or task.state != ScheduledTaskState.ACTIVE:
            return False
        task.lease_expires_at = _lease_expiry(self.lease_timeout_seconds)
        return True

    def reap_expired_leases(self, now_iso: str | None = None) -> list[ScheduledTask]:
        """Detect tasks whose leases expired and park them, advancing the queue."""
        reaped: list[ScheduledTask] = []
        current_time = now_iso or _utc_now()

        active = self.active_task()
        if active and active.lease_expires_at and active.lease_expires_at < current_time:
            self.park_task(active.task_id, reason="lease_timeout_expired")
            reaped.append(active)

        return reaped

    def park_task(self, task_id: str, reason: str = "") -> ScheduledTask | None:
        """Park an active or queued task and dispatch the next candidate."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        was_active = (task.state == ScheduledTaskState.ACTIVE)
        task.state = ScheduledTaskState.PARKED
        task.lease_owner = None
        task.lease_expires_at = None
        if reason:
            task.metadata["park_reason"] = reason

        if was_active:
            self.dispatch_next()
        return task

    def resume_task(self, task_id: str) -> ScheduledTask | None:
        """Resume a parked task back to QUEUED (or ACTIVE if host is free)."""
        task = self._tasks.get(task_id)
        if not task or task.state not in {ScheduledTaskState.PARKED, ScheduledTaskState.WAITING_FOR_HUMAN}:
            return None

        task.state = ScheduledTaskState.QUEUED
        if self.active_task() is None:
            self.dispatch_next()
        return task

    def request_human_intervention(self, task_id: str, prompt: str = "") -> ScheduledTask | None:
        """Mark task as waiting for human, yielding active host."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        was_active = (task.state == ScheduledTaskState.ACTIVE)
        task.state = ScheduledTaskState.WAITING_FOR_HUMAN
        if prompt:
            task.metadata["human_prompt"] = prompt

        if was_active:
            self.dispatch_next()
        return task

    def complete_task(self, task_id: str, success: bool = True) -> ScheduledTask | None:
        """Complete task and dispatch next in queue."""
        task = self._tasks.get(task_id)
        if not task:
            return None

        was_active = (task.state == ScheduledTaskState.ACTIVE)
        task.state = ScheduledTaskState.COMPLETED if success else ScheduledTaskState.FAILED
        task.completed_at = _utc_now()
        task.lease_owner = None

        if was_active:
            self.dispatch_next()
        return task

    def get_task(self, task_id: str) -> ScheduledTask | None:
        return self._tasks.get(task_id)

    def list_tasks(self, state: ScheduledTaskState | None = None) -> list[ScheduledTask]:
        if state is None:
            return list(self._tasks.values())
        return [t for t in self._tasks.values() if t.state == state]

from workstation.scheduler import MultiTaskScheduler, ScheduledTaskState


def test_single_active_task_invariant():
    sched = MultiTaskScheduler()

    # Enqueue task A -> becomes active
    task_a = sched.enqueue("task-a", session_id="s1", priority=10)
    assert task_a.state == ScheduledTaskState.ACTIVE
    assert sched.active_task() == task_a

    # Enqueue task B -> remains queued (single active host invariant!)
    task_b = sched.enqueue("task-b", session_id="s1", priority=20)
    assert task_b.state == ScheduledTaskState.QUEUED
    assert sched.active_task() == task_a

    # Park task A -> task B is automatically dispatched
    sched.park_task("task-a", reason="background work")
    assert task_a.state == ScheduledTaskState.PARKED
    assert task_b.state == ScheduledTaskState.ACTIVE
    assert sched.active_task() == task_b


def test_priority_and_fifo_dispatch():
    sched = MultiTaskScheduler()

    # Block active host with task 1
    t1 = sched.enqueue("t1", "s1")
    assert t1.state == ScheduledTaskState.ACTIVE

    # Enqueue low priority then high priority
    t_low = sched.enqueue("t_low", "s1", priority=5)
    t_high = sched.enqueue("t_high", "s1", priority=50)

    # Complete t1 -> t_high should be dispatched next
    sched.complete_task("t1", success=True)
    assert t_high.state == ScheduledTaskState.ACTIVE
    assert t_low.state == ScheduledTaskState.QUEUED

    # Complete t_high -> t_low dispatched next
    sched.complete_task("t_high", success=True)
    assert t_low.state == ScheduledTaskState.ACTIVE


def test_human_intervention_yields_host():
    sched = MultiTaskScheduler()
    t1 = sched.enqueue("t1", "s1")
    t2 = sched.enqueue("t2", "s1")

    sched.request_human_intervention("t1", prompt="Solve captcha")
    assert t1.state == ScheduledTaskState.WAITING_FOR_HUMAN
    assert t2.state == ScheduledTaskState.ACTIVE

    # Resume t1 -> joins queue
    sched.resume_task("t1")
    assert t1.state == ScheduledTaskState.QUEUED


def test_scheduler_reaps_expired_lease_and_advances_queue():
    # H-106 Red Team verification: orphan active task timeout deadlock prevention
    sched = MultiTaskScheduler(lease_timeout_seconds=60.0)

    # Task A is active, Task B is waiting in queue
    t_a = sched.enqueue("task-orphan-a", "s1")
    t_b = sched.enqueue("task-waiting-b", "s1")

    assert t_a.state == ScheduledTaskState.ACTIVE
    assert t_b.state == ScheduledTaskState.QUEUED

    # Simulate future timestamp 10 minutes later (lease expired)
    future_time = "2099-01-01T00:00:00+00:00"
    reaped = sched.reap_expired_leases(now_iso=future_time)

    assert len(reaped) == 1
    assert reaped[0].task_id == "task-orphan-a"
    assert t_a.state == ScheduledTaskState.PARKED
    assert t_a.metadata.get("park_reason") == "lease_timeout_expired"

    # Host invariant preserved: next task was automatically unblocked and activated!
    assert t_b.state == ScheduledTaskState.ACTIVE
    assert sched.active_task() == t_b


def test_scheduler_heartbeat_extends_lease():
    sched = MultiTaskScheduler(lease_timeout_seconds=30.0)
    t = sched.enqueue("task-alive", "s1")
    initial_expiry = t.lease_expires_at

    import time
    time.sleep(0.01)
    renewed = sched.heartbeat("task-alive")
    assert renewed is True
    assert t.lease_expires_at is not None
    assert t.lease_expires_at >= (initial_expiry or "")


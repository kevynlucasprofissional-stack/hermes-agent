"""Observational run lineage, published only after the owner commits its claim."""
from agent.runtime_events import notify_runtime_event


def notify_claimed_run(conn, task_id, run_id):
    previous = conn.execute(
        "SELECT id, outcome FROM task_runs WHERE task_id=? AND id<? ORDER BY id DESC LIMIT 1",
        (task_id, run_id),
    ).fetchone()
    if previous is None or previous["outcome"] != "reclaimed":
        return
    notify_runtime_event("task_run_superseded", {
        "task_id": task_id, "stale_run_id": str(previous["id"]), "run_id": str(run_id),
        "termination_kind": "SUPERSEDED",
    })

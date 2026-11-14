"""Optional official Hermes task gateway. Never stores Workstation cards upstream.

Only explicit delegation endpoint invokes create_official_task.
"""
from __future__ import annotations

from contextlib import closing


def create_official_task(*, title: str, description: str, card_id: str,
                         board_id: str, assignee: str | None, idempotency_key: str) -> str:
    from hermes_cli import kanban_db, kanban_db_connect

    kanban_db.init_db()
    with closing(kanban_db_connect.connect(board=None)) as conn:
        # Check even archived tasks: a retry after an interrupted link must not spawn a duplicate.
        previous = conn.execute(
            "SELECT id FROM tasks WHERE idempotency_key=? ORDER BY created_at DESC LIMIT 1",
            (idempotency_key,)).fetchone()
        if previous:
            return str(previous[0])
        body = (description + "\n\n" +
                f"Workstation card: {card_id}\nWorkstation board: {board_id}").strip()
        return kanban_db.create_task(
            conn, title=title, body=body, assignee=assignee,
            created_by="workstation-database", idempotency_key=idempotency_key,
            workspace_kind="scratch", board=None, initial_status="running")


def get_official_task_status(task_id: str) -> str | None:
    from hermes_cli import kanban_db, kanban_db_connect

    with closing(kanban_db_connect.connect(board=None)) as conn:
        task = kanban_db.get_task(conn, task_id)
        return task.status if task else None

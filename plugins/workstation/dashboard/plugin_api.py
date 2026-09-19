from __future__ import annotations

import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/resources")
async def get_workstation_resources():
    """Project the Electron Workstation resources for Dashboard clients."""
    from workstation.client import get_workstation_resources as read_resources
    return await asyncio.to_thread(read_resources)


@router.get("/events")
async def get_workstation_events(task_id: Optional[str] = None, limit: int = 200):
    """Project bounded canonical Workstation journal events for clients."""
    from workstation.client import get_workstation_events as read_events
    return await asyncio.to_thread(read_events, task_id=task_id, limit=limit)


@router.get("/tasks/{task_id}/cockpit")
async def get_workstation_task_cockpit(task_id: str, request: Request, board: Optional[str] = None):
    def read():
        from hermes_cli import kanban_db
        from workstation.cockpit import task_cockpit
        conn = kanban_db.connect(board=board)
        try:
            return task_cockpit(conn, task_id)
        finally:
            conn.close()
    try:
        return await asyncio.to_thread(read)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

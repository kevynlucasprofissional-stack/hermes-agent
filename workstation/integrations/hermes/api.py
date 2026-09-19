from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workstation", tags=["workstation"])


@router.get("/resources")
async def get_workstation_resources():
    try:
        from workstation.client import get_workstation_resources as read_resources
        return read_resources()
    except Exception as exc:
        logger.error("Failed to read workstation resources: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/events")
async def get_workstation_events(task_id: Optional[str] = None, limit: int = 200):
    try:
        from workstation.client import get_workstation_events as read_events
        return read_events(task_id=task_id, limit=limit)
    except Exception as exc:
        logger.error("Failed to read workstation events: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/tasks/{task_id}/cockpit")
async def get_workstation_task_cockpit(task_id: str, request: Request, board: Optional[str] = None):
    try:
        from workstation.cockpit import task_cockpit
        return task_cockpit(task_id, board=board)
    except Exception as exc:
        logger.error("Failed to read workstation task cockpit for %s: %s", task_id, exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def mount_workstation_api(app) -> None:
    """Mount the Workstation API router onto the FastAPI web server."""
    app.include_router(router)
    # Also mount under plugins namespace for upstream plugin API standard
    plugins_router = APIRouter(prefix="/api/plugins/workstation", tags=["workstation"])
    plugins_router.include_router(router, prefix="")
    app.include_router(plugins_router)

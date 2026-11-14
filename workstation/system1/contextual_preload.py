"""Conditionally preload the resident Laya model after real native Browser activity."""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)
_ACTIVITY = frozenset({"browser_navigate", "browser_tab_activate", "browser_show", "browser_create"})


def maybe_preload_after_browser_tool(tool: str, result: Any, *, dispatched: bool) -> str:
    """Never create a browser operation or allocate model memory on an unverified event."""
    if not dispatched or tool not in _ACTIVITY:
        return "not_applicable"
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except ValueError:
            return "unconfirmed"
    if (not isinstance(result, dict) or result.get("success") is not True
            or result.get("runtime") != "electron-chromium"
            or not isinstance(result.get("task_id"), str) or not result["task_id"]):
        return "unconfirmed"
    from agent.system1_decision import system1_decision_providers
    from workstation.system1.laya_provider import LayaDecisionProvider
    import psutil

    providers = [p for p in system1_decision_providers() if isinstance(p, LayaDecisionProvider)]
    if not providers:
        return "unavailable"
    available = int(psutil.virtual_memory().available)
    status = providers[0].schedule_preload(available)
    if status in {"scheduled", "deferred_memory"}:
        logger.info("Laya browser contextual preload: %s (available_gib=%.2f)", status,
                    available / 1024 ** 3)
    return status

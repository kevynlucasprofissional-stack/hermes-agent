from __future__ import annotations

import logging
from typing import Any
from workstation.batch_detection import prepare_mutation, record_mutation
from workstation.task_compiler import capture_raw_result

logger = logging.getLogger(__name__)


def workstation_pre_dispatch_hook(
    tool_name: str,
    final_args: dict[str, Any],
    call_id: str,
    context: dict[str, Any],
) -> None:
    """Invoked at the authorized pre-effect boundary before real external I/O."""
    agent = context.get("agent")
    if agent is None:
        return
    try:
        prepare_mutation(agent, tool_name, final_args)
    except Exception as exc:
        logger.warning("Workstation prepare_mutation hook failed: %s", exc)
        raise


def workstation_raw_post_tool_observer(
    tool_name: str,
    final_args: dict[str, Any],
    call_id: str,
    raw_result: Any,
    duration: float,
    context: dict[str, Any],
) -> None:
    """Invoked immediately after tool handler returns, before any output truncation or spill."""
    agent = context.get("agent")
    if agent is not None:
        dispatched = context.get("dispatched", True)
        duration_ms = duration * 1000 if duration is not None else None
        try:
            record_mutation(
                agent,
                tool_name,
                final_args,
                raw_result,
                dispatched=dispatched,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            logger.warning("Workstation record_mutation observer failed: %s", exc)

    try:
        capture_raw_result(call_id, raw_result)
    except Exception as exc:
        logger.warning("Workstation capture_raw_result observer failed: %s", exc)

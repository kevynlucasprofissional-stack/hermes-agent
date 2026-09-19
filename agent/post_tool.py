from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# RawPostToolObserver signature: (tool_name, final_args, call_id, raw_result, duration, context) -> None
RawPostToolObserver = Callable[[str, dict[str, Any], str, Any, float, dict[str, Any]], None]
_raw_post_tool_observers: list[RawPostToolObserver] = []


def register_raw_post_tool_observer(observer: RawPostToolObserver) -> None:
    if observer not in _raw_post_tool_observers:
        _raw_post_tool_observers.append(observer)


def unregister_raw_post_tool_observer(observer: RawPostToolObserver) -> None:
    if observer in _raw_post_tool_observers:
        _raw_post_tool_observers.remove(observer)


def dispatch_raw_post_tool_observation(
    tool_name: str,
    final_args: dict[str, Any],
    call_id: str,
    raw_result: Any,
    duration: float,
    context: dict[str, Any],
) -> None:
    """Invoked immediately after tool handler returns, before any output truncation or spill.
    
    Guarantees that supervisory observers see the true, uncompressed, unredacted result.
    """
    for observer in list(_raw_post_tool_observers):
        try:
            observer(tool_name, final_args, call_id, raw_result, duration, context)
        except Exception as exc:
            logger.warning("Raw post-tool observer %r failed: %s", observer, exc)

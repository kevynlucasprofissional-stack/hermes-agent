from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# PreDispatchHook signature: (tool_name, final_args, call_id, context) -> None
# MUST be called after final args are settled, after authorization and guardrails pass,
# and immediately before real handler I/O execution.
PreDispatchHook = Callable[[str, dict[str, Any], str, dict[str, Any]], None]
_pre_dispatch_hooks: list[PreDispatchHook] = []


def register_pre_authorized_dispatch_hook(hook: PreDispatchHook) -> None:
    if hook not in _pre_dispatch_hooks:
        _pre_dispatch_hooks.append(hook)


def unregister_pre_authorized_dispatch_hook(hook: PreDispatchHook) -> None:
    if hook in _pre_dispatch_hooks:
        _pre_dispatch_hooks.remove(hook)


def dispatch_pre_authorized_checkpoint(
    tool_name: str,
    final_args: dict[str, Any],
    call_id: str,
    context: dict[str, Any],
) -> None:
    """Invoked at the authorized pre-effect boundary before real external I/O.
    
    Guarantees:
    - Never runs if the call was blocked by authorization or guardrails.
    - Sees the FINAL, possibly rewritten arguments.
    - Runs BEFORE any physical socket, process, or external system call.
    """
    for hook in list(_pre_dispatch_hooks):
        try:
            hook(tool_name, final_args, call_id, context)
        except Exception as exc:
            logger.warning("Pre-dispatch checkpoint hook %r failed: %s", hook, exc)
            raise

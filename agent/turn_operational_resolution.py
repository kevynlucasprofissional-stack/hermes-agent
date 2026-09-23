"""Turn-loop phase: consult operational resolution before the provider call.

Sits between the pre-API pressure gate and ``announce_api_call`` — after trusted
ingress, turn admission and route policy have established session/task/turn
identity and authority, and at the narrowest point whose purpose is to ask the
model for another round of reasoning.

A terminal resolution closes the turn through the same path a text response
takes: the reply is appended to the live transcript, flushed to SessionDB while
``finalize_turn`` still owns the retry, and the loop breaks so post-loop
finalization, trajectory and completion admission all still run. Nothing here
builds a turn result dict by hand — the canonical finalizer stays the only
producer.

Nothing here imports ``agent.conversation_loop`` at module level (cycle).
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Dict, Optional

from agent.message_metadata import append_message
from agent.operational_resolution import (
    OperationalResolutionContext,
    operational_resolution_providers,
    resolve_operational_step,
)

logger = logging.getLogger("agent.conversation_loop")


@dataclass
class OperationalResolutionVerdict:
    """``action`` is ``fallthrough`` (call the model) or ``break`` (turn is over)."""

    action: str
    final_response: Any
    _turn_exit_reason: Any
    api_call_count: Any


def resolve_operational_step_phase(
    agent: Any, *, messages: Any, conversation_history: Any, user_message: Any,
    effective_task_id: Any, turn_id: Any, api_call_count: Any, final_response: Any,
    _turn_exit_reason: Any,
) -> OperationalResolutionVerdict:
    """Ask registered operational providers whether this step still needs reasoning.

    The returned ``final_response`` is the provider's user-facing close-out text,
    which the caller renders exactly as it renders ordinary assistant text.
    """
    if not operational_resolution_providers():
        return OperationalResolutionVerdict(
            "fallthrough", final_response, _turn_exit_reason, api_call_count
        )

    session_id = ""
    try:
        session_id = str(getattr(agent, "_conversation_root_id", lambda: None)() or "")
    except Exception:
        session_id = ""
    session_id = session_id or str(getattr(agent, "session_id", None) or "")

    resolution = resolve_operational_step(
        OperationalResolutionContext(
            agent=agent,
            session_id=session_id,
            task_id=str(effective_task_id or ""),
            turn_id=str(turn_id or ""),
            user_message=user_message,
            messages=messages,
            api_call_count=int(api_call_count or 0),
            iteration=int(api_call_count or 0),
        )
    )
    if not resolution.is_terminal:
        return OperationalResolutionVerdict(
            "fallthrough", final_response, _turn_exit_reason, api_call_count
        )

    append_message(messages, {"role": "assistant", "content": resolution.final_response})
    # Make the answer durable before leaving the loop; failure must not abort the
    # turn, ``finalize_turn`` retries (same contract as a text response).
    try:
        agent._flush_messages_to_session_db(messages, conversation_history)
    except Exception:
        logger.warning(
            "operational resolution flush failed (session=%s) — reply is not yet durable; "
            "relying on finalize_turn retry",
            getattr(agent, "session_id", None) or "none",
            exc_info=True,
        )

    # No provider request was issued for this iteration, so it is refunded exactly
    # as ``run_preflight_gate`` refunds the iteration it ends without calling out.
    # ``finalize_turn`` derives ``completed`` from this count; leaving it charged
    # would report a resolved turn as iteration-limited.
    _refunded = max(int(api_call_count or 0) - 1, 0)
    agent._api_call_count = _refunded

    exit_reason = f"operational_resolution({resolution.outcome.value})"
    return OperationalResolutionVerdict(
        "break", resolution.final_response, exit_reason, _refunded
    )

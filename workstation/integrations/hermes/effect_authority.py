"""Derive trusted effect authority from canonical ingress and session context.

This module is the single source of truth for converting trusted ingress metadata
and canonical task/session identity into a control-plane ``AuthorityScope``.

It owns no policy of its own — it only translates established trust roots into
the bounded capability lattice. The result is a ceiling; request/intent may
narrow it, never expand it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope


@dataclass(frozen=True)
class TrustedAuthorityContext:
    """Inputs that the bridge considers trustworthy."""

    envelope: Optional[MessageEnvelope]
    canonical_task: Optional[Any]  # Task from kanban_db
    session_id: str


def trusted_effect_authority(ctx: TrustedAuthorityContext) -> AuthorityScope:
    """Derive the maximum trusted effect authority for a turn.

    The returned scope is a *ceiling* — the control plane and the intent's
    declared effect budget may narrow it further, but nothing in this flow
    may widen it.

    Resolution order (highest trust first):
    1. Explicit trusted envelope with CREATE_WORK/DELEGATE_WORK + matching
       canonical task/session → LOCAL_MUTATION ceiling.
    2. Authenticated human envelope with CREATE_WORK + canonical task
       (session-bound, no work delegation) → LOCAL_MUTATION ceiling.
    3. Observation-only / UPDATE_WORK / untrusted origin → READ.
    4. Missing envelope or session mismatch → READ.

    External reversible/irreversible are never implicitly granted. They
    require an explicit grant from a trusted owner (approval, connector
    policy, or delegated scope) which is outside this bridge's scope.
    """
    envelope = ctx.envelope
    task = ctx.canonical_task
    session_id = ctx.session_id

    # No envelope or session mismatch → no trust
    if envelope is None or str(getattr(envelope, "session_id", "")) != str(session_id):
        return AuthorityScope(level=AuthorityLevel.READ)

    # Origin must be trusted (human or system acting on human's behalf)
    if envelope.origin not in {MessageOrigin.HUMAN, MessageOrigin.SYSTEM_EVENT}:
        return AuthorityScope(level=AuthorityLevel.READ)

    # Intent authority must allow work creation or delegation
    if envelope.intent_authority not in {
        IntentAuthority.CREATE_WORK,
        IntentAuthority.DELEGATE_WORK,
    }:
        return AuthorityScope(level=AuthorityLevel.READ)

    # Must have a canonical task bound to this session
    if task is None or str(getattr(task, "session_id", "")) != str(session_id):
        return AuthorityScope(level=AuthorityLevel.READ)

    # Task must be active (not done/cancelled)
    task_status = str(getattr(task, "status", "")).lower()
    if task_status in {"done", "cancelled"}:
        return AuthorityScope(level=AuthorityLevel.READ)

    # Task body must match envelope content (binding verification)
    if getattr(task, "body", None) != envelope.content:
        return AuthorityScope(level=AuthorityLevel.READ)

    # All trust conditions met → LOCAL_MUTATION ceiling
    # This allows local filesystem/browser mutations but NOT external
    # reversible/irreversible effects which require explicit grants.
    return AuthorityScope(
        level=AuthorityLevel.LOCAL_MUTATION,
        allowed_actions={"*"},
        allowed_resources={"*"},
    )


def trusted_effect_authority_from_agent(
    agent: Any,
    session_id: str,
    canonical_task: Optional[Any] = None,
) -> AuthorityScope:
    """Convenience wrapper extracting trust context from an AIAgent.

    The agent is expected to carry:
    - ``_message_envelope`` (set by prepare_turn_work)
    - ``_canonical_work_task_id`` (set by prepare_turn_work)
    - ``session_id`` / ``_conversation_root_id``
    """
    envelope = getattr(agent, "_message_envelope", None)
    if canonical_task is None:
        task_id = str(getattr(agent, "_canonical_work_task_id", "") or "")
        if task_id:
            try:
                from hermes_cli import kanban_db
                from workstation.kanban import WorkstationKanbanBridge
                bridge = WorkstationKanbanBridge()
                conn = bridge.get_connection()
                try:
                    canonical_task = kanban_db.get_task(conn, task_id)
                finally:
                    conn.close()
            except Exception:
                canonical_task = None

    return trusted_effect_authority(TrustedAuthorityContext(
        envelope=envelope,
        canonical_task=canonical_task,
        session_id=session_id,
    ))
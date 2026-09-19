from __future__ import annotations

from typing import Any, Optional
from agent.turn_ingress import TurnIngress, TurnOrigin, TurnTrustClass
from agent.turn_route_policy import TurnRoutePolicy, set_current_turn_route_policy
from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.work_intent import prepare_turn_work


def workstation_turn_admission(
    agent: Any,
    turn_context: Any,
    ingress: Optional[Any] = None,
) -> None:
    """Translate generic turn ingress into canonical Workstation WorkIntent & task binding."""
    root = getattr(agent, "_conversation_root_id", lambda: None)()
    session_id = str(root or getattr(agent, "session_id", None) or "")

    user_content = ""
    if hasattr(turn_context, "content"):
        user_content = turn_context.content or ""
    elif isinstance(turn_context, str):
        user_content = turn_context
    elif isinstance(turn_context, dict):
        user_content = turn_context.get("content", "")

    envelope: Optional[MessageEnvelope] = None

    if isinstance(ingress, MessageEnvelope):
        envelope = ingress
    elif isinstance(ingress, TurnIngress):
        origin_map = {
            TurnOrigin.HUMAN: MessageOrigin.HUMAN,
            TurnOrigin.AGENT: MessageOrigin.AGENT,
            TurnOrigin.WORKER: MessageOrigin.WORKER,
            TurnOrigin.SYSTEM_EVENT: MessageOrigin.SYSTEM_EVENT,
            TurnOrigin.CONNECTOR: MessageOrigin.CONNECTOR,
            "human": MessageOrigin.HUMAN,
            "cli": MessageOrigin.HUMAN,
            "desktop": MessageOrigin.HUMAN,
            "gateway": MessageOrigin.HUMAN,
            "agent": MessageOrigin.AGENT,
            "worker": MessageOrigin.WORKER,
            "system_event": MessageOrigin.SYSTEM_EVENT,
            "connector": MessageOrigin.CONNECTOR,
        }
        origin = origin_map.get(ingress.origin, MessageOrigin.RUNTIME)

        authority_map = {
            TurnTrustClass.AUTHENTICATED_USER: IntentAuthority.CREATE_WORK,
            TurnTrustClass.DELEGATED_AGENT: IntentAuthority.DELEGATE_WORK,
            TurnTrustClass.CONNECTOR_WRITE: IntentAuthority.UPDATE_WORK,
            TurnTrustClass.MUTATION_ALLOWED: IntentAuthority.CREATE_WORK,
            TurnTrustClass.OBSERVATION_ONLY: IntentAuthority.OBSERVATION_ONLY,
            TurnTrustClass.UNTRUSTED: IntentAuthority.OBSERVATION_ONLY,
            "AUTHENTICATED_USER": IntentAuthority.CREATE_WORK,
            "CREATE_WORK": IntentAuthority.CREATE_WORK,
            "MUTATION_ALLOWED": IntentAuthority.CREATE_WORK,
            "DELEGATED_AGENT": IntentAuthority.DELEGATE_WORK,
            "DELEGATE_WORK": IntentAuthority.DELEGATE_WORK,
            "CONNECTOR_WRITE": IntentAuthority.UPDATE_WORK,
            "UPDATE_WORK": IntentAuthority.UPDATE_WORK,
            "OBSERVATION_ONLY": IntentAuthority.OBSERVATION_ONLY,
            "UNTRUSTED": IntentAuthority.OBSERVATION_ONLY,
        }
        authority = authority_map.get(
            ingress.trust_or_authority_class,
            IntentAuthority.OBSERVATION_ONLY,
        )

        content = user_content or str(ingress.metadata.get("content", "") if ingress.metadata else "")
        envelope = MessageEnvelope(
            origin=origin,
            intent_authority=authority,
            session_id=session_id,
            content=content,
            correlation_id=ingress.correlation_id,
        )
    else:
        existing = getattr(agent, "_message_envelope", None)
        if isinstance(existing, MessageEnvelope) and existing.session_id == session_id:
            envelope = existing
        else:
            envelope = MessageEnvelope(
                origin=MessageOrigin.RUNTIME,
                intent_authority=IntentAuthority.OBSERVATION_ONLY,
                session_id=session_id,
                content=user_content,
            )

    agent._work_compile_replans = 0
    agent._work_completed_mutations = {}
    agent._work_mutation_evidence = {}
    agent._work_mutation_shapes = {}
    agent._work_compilation_candidates = {}
    agent._work_procedure_trace = []
    agent._work_procedure_trace_truncated = False

    intent = prepare_turn_work(agent, envelope.content, envelope=envelope)

    if intent and intent.constraints:
        policy = TurnRoutePolicy(
            allowed_routes=tuple(intent.constraints.get("allowed_routes", ())),
            forbidden_routes=tuple(intent.constraints.get("forbidden_routes", ())),
            mutation_allowed_routes=tuple(intent.constraints.get("mutation_allowed_routes", ())),
            mutation_forbidden_routes=tuple(intent.constraints.get("mutation_forbidden_routes", ())),
        )
        set_current_turn_route_policy(policy)

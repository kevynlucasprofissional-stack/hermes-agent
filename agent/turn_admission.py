from __future__ import annotations

import logging
from typing import Any, Callable, Optional
from agent.turn_ingress import TurnIngress

logger = logging.getLogger(__name__)

# TurnAdmissionProvider signature: (agent, turn_context, ingress) -> None
TurnAdmissionProvider = Callable[[Any, Any, Optional[TurnIngress]], None]
_turn_admission_providers: list[TurnAdmissionProvider] = []


def register_turn_admission_provider(provider: TurnAdmissionProvider) -> None:
    if provider not in _turn_admission_providers:
        _turn_admission_providers.append(provider)


def unregister_turn_admission_provider(provider: TurnAdmissionProvider) -> None:
    if provider in _turn_admission_providers:
        _turn_admission_providers.remove(provider)


def admit_turn(agent: Any, turn_context: Any, ingress: Optional[TurnIngress] = None) -> None:
    """Execute turn admission providers before LLM calls or tool actions.
    
    Ensures that canonical session/task/run identity and authority are bound
    before compaction, auxiliary calls, or mutation dispatch.
    """
    for provider in list(_turn_admission_providers):
        try:
            provider(agent, turn_context, ingress)
        except Exception as exc:
            logger.warning("Turn admission provider %r failed: %s", provider, exc)
            raise

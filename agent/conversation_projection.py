from __future__ import annotations

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Provider signature: (agent, api_messages, messages) -> list[dict[str, Any]]
ConversationProjectionProvider = Callable[[Any, list[dict[str, Any]], Optional[list]], list[dict[str, Any]]]
_projection_providers: list[ConversationProjectionProvider] = []


def register_conversation_projection_provider(provider: ConversationProjectionProvider) -> None:
    if provider not in _projection_providers:
        _projection_providers.append(provider)


def unregister_conversation_projection_provider(provider: ConversationProjectionProvider) -> None:
    if provider in _projection_providers:
        _projection_providers.remove(provider)


def project_messages_for_provider(
    agent: Any,
    api_messages: list[dict[str, Any]],
    messages: Optional[list] = None,
) -> list[dict[str, Any]]:
    """Project messages for the provider boundary without mutating the canonical transcript."""
    current = api_messages
    for provider in _projection_providers:
        try:
            current = provider(agent, current, messages)
        except Exception as exc:
            logger.warning("Conversation projection provider %r failed: %s", provider, exc)
    return current

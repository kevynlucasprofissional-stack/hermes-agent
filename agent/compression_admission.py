from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

CompressionBypassProvider = Callable[[Any, list], bool]
_compression_bypass_providers: list[CompressionBypassProvider] = []


def register_compression_bypass_provider(provider: CompressionBypassProvider) -> None:
    if provider not in _compression_bypass_providers:
        _compression_bypass_providers.append(provider)


def unregister_compression_bypass_provider(provider: CompressionBypassProvider) -> None:
    if provider in _compression_bypass_providers:
        _compression_bypass_providers.remove(provider)


def should_bypass_compression(agent: Any, messages: list) -> bool:
    """Consult registered compression bypass providers (e.g. durable continuation compaction)."""
    for provider in _compression_bypass_providers:
        try:
            if provider(agent, messages):
                return True
        except Exception as exc:
            logger.warning("Compression bypass provider %r failed: %s", provider, exc)
    return False

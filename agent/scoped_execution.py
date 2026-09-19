from __future__ import annotations

from contextlib import contextmanager
import logging
from typing import Any, Callable, ContextManager, Optional

logger = logging.getLogger(__name__)

ScopedExecutionProvider = Callable[[Any, str, Optional[list]], ContextManager[None]]
_scoped_execution_providers: list[ScopedExecutionProvider] = []


def register_scoped_execution_provider(provider: ScopedExecutionProvider) -> None:
    if provider not in _scoped_execution_providers:
        _scoped_execution_providers.append(provider)


def unregister_scoped_execution_provider(provider: ScopedExecutionProvider) -> None:
    if provider in _scoped_execution_providers:
        _scoped_execution_providers.remove(provider)


@contextmanager
def scoped_execution(
    agent: Any,
    effective_task_id: str,
    messages: Optional[list] = None,
):
    """Scoped execution context manager.
    
    Provides a generic lifecycle boundary for deterministic dispatchers,
    operational references, and execution contexts.
    """
    if not _scoped_execution_providers:
        yield
        return

    # Use the first registered provider (or chain if necessary)
    provider = _scoped_execution_providers[0]
    with provider(agent, effective_task_id, messages):
        yield

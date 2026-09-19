from __future__ import annotations

from enum import Enum
from contextvars import ContextVar


class ExecutionPersistenceDisposition(str, Enum):
    """Controls how tool and turn results are persisted in conversation history.
    
    PERSIST: Normal conversational turn persistence to SessionDB / transcript.
    DEFER: Intermediate steps buffered or deferred; flushed at outer batch boundary.
    OWNER_MANAGED: The execution runner (e.g. DurableBatchRunner / TaskCompiler) owns
                   state persistence and checkpoints; normal turn logging suppresses
                   accidental intermediate SessionDB writes to prevent replay pollution.
    """
    PERSIST = "PERSIST"
    DEFER = "DEFER"
    OWNER_MANAGED = "OWNER_MANAGED"


from typing import Callable, Optional

_persistence_disposition: ContextVar[ExecutionPersistenceDisposition] = ContextVar(
    "persistence_disposition",
    default=ExecutionPersistenceDisposition.PERSIST,
)

_disposition_providers: list[Callable[[], Optional[ExecutionPersistenceDisposition]]] = []


def register_persistence_disposition_provider(
    provider: Callable[[], Optional[ExecutionPersistenceDisposition]]
) -> None:
    if provider not in _disposition_providers:
        _disposition_providers.append(provider)


def get_persistence_disposition() -> ExecutionPersistenceDisposition:
    for provider in reversed(_disposition_providers):
        try:
            disp = provider()
            if disp is not None:
                return disp
        except Exception:
            pass
    return _persistence_disposition.get()


def set_persistence_disposition(disposition: ExecutionPersistenceDisposition):
    return _persistence_disposition.set(disposition)


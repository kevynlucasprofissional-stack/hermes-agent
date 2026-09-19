from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from contextvars import ContextVar


from enum import Enum


class TurnOrigin(str, Enum):
    HUMAN = "human"
    AGENT = "agent"
    WORKER = "worker"
    SYSTEM_EVENT = "system_event"
    CONNECTOR = "connector"
    RUNTIME = "runtime"


class TurnTrustClass(str, Enum):
    AUTHENTICATED_USER = "authenticated_user"
    DELEGATED_AGENT = "delegated_agent"
    CONNECTOR_WRITE = "connector_write"
    MUTATION_ALLOWED = "mutation_allowed"
    OBSERVATION_ONLY = "observation_only"
    UNTRUSTED = "untrusted"


@dataclass
class TurnIngress:
    """Trusted ingress metadata identifying origin and authority of a conversational turn.
    
    Rule: USER TEXT != AUTHORITY. Authority must be provided by a trusted ingress layer.
    """
    origin: TurnOrigin | str
    trust_or_authority_class: TurnTrustClass | str = TurnTrustClass.AUTHENTICATED_USER
    session_id: str = ""
    correlation_id: Optional[str] = None
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    trust_class: Optional[TurnTrustClass | str] = None

    def __post_init__(self) -> None:
        if self.trust_class is not None:
            self.trust_or_authority_class = self.trust_class
        if not self.content and "content" in self.metadata:
            self.content = str(self.metadata["content"])
        elif self.content and "content" not in self.metadata:
            self.metadata["content"] = self.content


_current_turn_ingress: ContextVar[Optional[TurnIngress]] = ContextVar("current_turn_ingress", default=None)


def get_current_turn_ingress() -> Optional[TurnIngress]:
    return _current_turn_ingress.get()


def set_current_turn_ingress(ingress: Optional[TurnIngress]):
    return _current_turn_ingress.set(ingress)

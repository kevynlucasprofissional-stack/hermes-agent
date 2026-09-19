from __future__ import annotations

from typing import Any, Optional
from workstation.continuation import project_for_provider


class WorkstationLLMRequestMiddleware:
    """LLM request middleware that projects wire context without mutating persisted transcript.
    
    Injects authenticated durable handoffs and filters covered work_execute calls on the wire
    while strictly preserving prompt-cache stability and byte-level persisted history.
    """
    def __init__(self, agent: Any = None):
        self.agent = agent

    def __call__(
        self,
        messages: list[dict[str, Any]],
        context: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        agent = (context or {}).get("agent") or self.agent
        if agent is None:
            return messages
        return project_for_provider(agent, messages)

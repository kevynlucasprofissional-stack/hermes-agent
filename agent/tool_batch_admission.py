from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class BatchAdmissionAction(str, Enum):
    EXECUTE = "EXECUTE"
    FILTER = "FILTER"
    REWRITE = "REWRITE"
    SYNTHETIC_RESULT = "SYNTHETIC_RESULT"
    DEFER = "DEFER"
    HANDOFF = "HANDOFF"


@dataclass
class BatchAdmissionDecision:
    call_id: str
    action: BatchAdmissionAction
    synthetic_result: Optional[str] = None
    rewritten_call: Optional[Any] = None
    reason: Optional[str] = None


@dataclass
class BatchAdmissionResult:
    decisions: list[BatchAdmissionDecision]


# Signature: (agent, tool_calls, execution_context) -> Optional[BatchAdmissionResult]
ToolBatchAdmissionProvider = Callable[[Any, list[Any], Optional[dict[str, Any]]], Optional[BatchAdmissionResult]]
_batch_admission_providers: list[ToolBatchAdmissionProvider] = []


def register_tool_batch_admission_provider(provider: ToolBatchAdmissionProvider) -> None:
    if provider not in _batch_admission_providers:
        _batch_admission_providers.append(provider)


def unregister_tool_batch_admission_provider(provider: ToolBatchAdmissionProvider) -> None:
    if provider in _batch_admission_providers:
        _batch_admission_providers.remove(provider)


def admit_tool_batch(
    agent: Any,
    tool_calls: list[Any],
    execution_context: Optional[dict[str, Any]] = None,
) -> Optional[BatchAdmissionResult]:
    """Inspect full assistant tool batch before dispatch.
    
    Allows supervisor/adapter to inspect all calls together, filter uncompiled loops,
    rewrite commands, or return synthetic results for human review or compilation.
    """
    for provider in list(_batch_admission_providers):
        try:
            res = provider(agent, tool_calls, execution_context)
            if res is not None:
                return res
        except Exception as exc:
            logger.warning("Tool batch admission provider %r failed: %s", provider, exc)
            raise
    return None

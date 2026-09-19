from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class CompletionAdmissionResult:
    admitted: bool
    reason: Optional[str] = None
    receipt: Optional[dict[str, Any]] = None


# CompletionAdmissionProvider signature: (task_id, run_id, state) -> CompletionAdmissionResult
CompletionAdmissionProvider = Callable[[str, str, dict[str, Any]], CompletionAdmissionResult]
_completion_admission_providers: list[CompletionAdmissionProvider] = []


def register_completion_admission_provider(provider: CompletionAdmissionProvider) -> None:
    if provider not in _completion_admission_providers:
        _completion_admission_providers.append(provider)


def unregister_completion_admission_provider(provider: CompletionAdmissionProvider) -> None:
    if provider in _completion_admission_providers:
        _completion_admission_providers.remove(provider)


def admit_completion(task_id: str, run_id: str, state: dict[str, Any]) -> CompletionAdmissionResult:
    """Evaluate completion candidate through registered admission providers.
    
    If any provider rejects the candidate, terminal completion (DONE) MUST NOT occur.
    """
    for provider in list(_completion_admission_providers):
        try:
            result = provider(task_id, run_id, state)
            if not result.admitted:
                return result
        except Exception as exc:
            logger.warning("Completion admission provider %r failed: %s", provider, exc)
            return CompletionAdmissionResult(admitted=False, reason=f"provider_error: {exc}")
    return CompletionAdmissionResult(admitted=True)

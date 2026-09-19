from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Signature: (conn, task_id, ws_data, owned, hybrid_owned) -> bool
TaskCompletionAdmissionProvider = Callable[[Any, str, Any, Any, bool], bool]
_task_completion_admission_providers: list[TaskCompletionAdmissionProvider] = []


def register_task_completion_admission_provider(provider: TaskCompletionAdmissionProvider) -> None:
    if provider not in _task_completion_admission_providers:
        _task_completion_admission_providers.append(provider)


def unregister_task_completion_admission_provider(provider: TaskCompletionAdmissionProvider) -> None:
    if provider in _task_completion_admission_providers:
        _task_completion_admission_providers.remove(provider)


def admit_task_completion(
    conn: Any,
    task_id: str,
    ws_data: Any,
    owned: Any,
    hybrid_owned: bool,
) -> bool:
    """Validate task completion against registered admission providers inside complete_task."""
    for provider in list(_task_completion_admission_providers):
        try:
            if not provider(conn, task_id, ws_data, owned, hybrid_owned):
                return False
        except Exception as exc:
            logger.warning("Task completion admission provider %r failed: %s", provider, exc)
            return False
    return True

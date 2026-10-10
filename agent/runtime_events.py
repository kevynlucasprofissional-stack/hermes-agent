"""Content-free runtime event observers for optional product integrations."""
from __future__ import annotations

import logging
import json
from typing import Any, Callable

logger = logging.getLogger(__name__)
_observers: list[Callable[[str, dict[str, Any]], None]] = []


def serialized_size(value: Any) -> int | None:
    """Application UTF-8 size only; never retain content or claim wire bytes."""
    try:
        if hasattr(value, "model_dump"):
            value = value.model_dump()
        text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
        return len(text.encode("utf-8"))
    except Exception:
        return None


def register_runtime_event_observer(observer: Callable[[str, dict[str, Any]], None]) -> None:
    if observer not in _observers:
        _observers.append(observer)


def notify_runtime_event(event_name: str, structural_metadata: dict[str, Any]) -> None:
    for observer in tuple(_observers):
        try:
            observer(event_name, dict(structural_metadata))
        except Exception:
            logger.debug("runtime event observer failed", exc_info=True)

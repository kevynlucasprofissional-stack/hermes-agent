from __future__ import annotations

import logging
from typing import Protocol

from .models import TelemetryEventV1

logger = logging.getLogger(__name__)


class TelemetrySink(Protocol):
    def emit(self, event: TelemetryEventV1) -> None: ...


class NullTelemetrySink:
    def emit(self, event: TelemetryEventV1) -> None:
        return None


def safe_emit(sink: TelemetrySink, event: TelemetryEventV1) -> None:
    try:
        sink.emit(event)
    except Exception as exc:
        try:
            logger.warning("Workstation telemetry emission failed: %.200s", exc)
        except Exception:
            pass

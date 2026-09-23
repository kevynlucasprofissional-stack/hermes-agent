from __future__ import annotations

import logging

from workstation.config import load_workstation_config
from workstation.telemetry import NullTelemetrySink, set_telemetry_sink
from workstation.telemetry.sqlite_sink import SQLiteTelemetrySink

logger = logging.getLogger(__name__)


def install_workstation_telemetry():
    try:
        config = load_workstation_config()
        sink = (SQLiteTelemetrySink(max_events=config.telemetry_max_events)
                if config.telemetry_enabled else NullTelemetrySink())
    except Exception as exc:
        logger.warning("Workstation telemetry unavailable; product remains active: %.200s", exc)
        sink = NullTelemetrySink()
    set_telemetry_sink(sink)
    from agent.runtime_events import register_runtime_event_observer
    register_runtime_event_observer(_observe_runtime_event)
    return sink


def _observe_runtime_event(event_name: str, metadata: dict) -> None:
    if event_name != "provider_called":
        return
    from workstation.telemetry import TelemetryEventType, emit_event
    api_request_id = metadata.get("api_request_id")
    emit_event(TelemetryEventType.PROVIDER_CALLED, source_owner="hermes.provider",
               session_id=metadata.get("session_id"), task_id=metadata.get("task_id"),
               turn_id=metadata.get("turn_id"), duration_ms=metadata.get("duration_ms"),
               provider_calls=1, input_tokens=metadata.get("input_tokens"),
               output_tokens=metadata.get("output_tokens"), status=metadata.get("status"),
               dedupe_key=f"provider:{api_request_id}" if api_request_id else None,
               payload={"api_request_id": api_request_id, "provider": metadata.get("provider"),
                        "model": metadata.get("model"), "purpose": metadata.get("purpose"),
                        "auxiliary": metadata.get("auxiliary", False)})

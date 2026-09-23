from __future__ import annotations

from workstation.control_plane.metrics import ORAMetrics, calculate_volc

from .models import TelemetryEventType, TelemetryEventV1


def project_ora_volc(events: list[TelemetryEventV1]):
    verified_operations: set[str] = set()
    deterministic: set[str] = set()
    reasoned: set[str] = set()
    unverified = 0
    provider_calls = 0
    input_tokens = 0
    output_tokens = 0
    tool_calls = 0
    for event in events:
        if event.event_type == TelemetryEventType.PROVIDER_CALLED:
            provider_calls += event.provider_calls if event.provider_calls is not None else 1
            input_tokens += event.input_tokens or 0
            output_tokens += event.output_tokens or 0
        if event.tool_calls is not None:
            tool_calls += event.tool_calls
        if event.event_type == TelemetryEventType.VERIFICATION_COMPLETED:
            if event.status == "VERIFIED":
                key = event.operation_id or event.event_id
                verified_operations.add(key)
                if event.route in {"deterministic", "execute", "native_browser", "composite"}:
                    deterministic.add(key)
                else:
                    reasoned.add(key)
            else:
                unverified += 1
    ora = ORAMetrics(verified_transitions_deterministic=len(deterministic),
                     verified_transitions_reasoned=len(reasoned),
                     unverified_transitions=unverified)
    volc = calculate_volc(len(verified_operations), llm_calls=provider_calls,
                          tokens=input_tokens + output_tokens, tool_calls=tool_calls)
    return ora, volc

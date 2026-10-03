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
    system1 = {"calls": 0, "successful": 0, "abstained": 0, "fallback": 0, "error": 0}
    superseded = wakes = 0
    tokens_known = True
    cost_known = True
    cost = 0.0
    seen = set()
    for event in events:
        if event.dedupe_key and event.dedupe_key in seen:
            continue
        if event.dedupe_key:
            seen.add(event.dedupe_key)
        if event.event_type == TelemetryEventType.SYSTEM1_COMPLETED:
            system1["calls"] += 1
            for key in ("successful", "abstained", "fallback", "error"):
                system1[key] += event.payload.get(key) is True
        if event.event_type == TelemetryEventType.AUTHORITY_SUPERSEDED:
            superseded += 1
        if event.event_type == TelemetryEventType.LLM_WOKEN:
            wakes += 1
        if event.event_type == TelemetryEventType.PROVIDER_CALLED:
            provider_calls += event.provider_calls if event.provider_calls is not None else 1
            input_tokens += event.input_tokens or 0
            output_tokens += event.output_tokens or 0
            tokens_known = tokens_known and event.input_tokens is not None and event.output_tokens is not None
            cost_known = cost_known and event.cost_usd is not None
            cost += event.cost_usd or 0.0
        if event.tool_calls is not None:
            tool_calls += event.tool_calls
        if event.event_type == TelemetryEventType.VERIFICATION_COMPLETED:
            if event.status == "VERIFIED":
                key = (event.task_id, event.run_id, event.operation_id or event.event_id)
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
    ora.system1_calls = system1["calls"]
    ora.system1_successful_decisions = system1["successful"]
    ora.system1_abstentions = system1["abstained"]
    ora.system1_fallbacks = system1["fallback"]
    ora.system1_errors = system1["error"]
    ora.system2_wake_count = ora.llm_wake_count = wakes
    ora.authority_superseded_count = superseded
    ora.tokens_consumed = input_tokens + output_tokens if tokens_known else None
    ora.total_cost_usd = cost if cost_known and provider_calls else None
    volc = calculate_volc(len(verified_operations), llm_calls=provider_calls,
                          tokens=input_tokens + output_tokens if tokens_known else None, tool_calls=tool_calls,
                          tokens_cost_usd=cost if cost_known and provider_calls else None)
    return ora, volc

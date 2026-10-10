from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from workstation.telemetry import (
    NullTelemetrySink,
    TelemetryEventType,
    TelemetryEventV1,
    emit_event,
    set_telemetry_sink,
)
from workstation.telemetry.privacy import sanitize_payload, sanitize_url
from workstation.telemetry.projectors import project_ora_volc
from workstation.telemetry.sqlite_sink import SQLiteTelemetrySink, TelemetryQuery


def _event(kind=TelemetryEventType.TURN_STARTED, **overrides):
    now = datetime.now(timezone.utc).isoformat()
    values = {"event_type": kind, "occurred_at": now, "recorded_at": now,
              "source_owner": "workstation.test", "task_id": "task-1", "run_id": "run-1"}
    values.update(overrides)
    return TelemetryEventV1(**values)


def test_event_roundtrip_unique_ids_and_unknowns_remain_none():
    first = _event()
    second = _event()
    restored = TelemetryEventV1.from_dict(first.to_dict())
    assert first.event_id != second.event_id
    assert restored == first
    assert restored.provider_calls is None


def test_actual_cost_survives_sqlite_reopen(tmp_path):
    path = tmp_path / "cost.sqlite"
    SQLiteTelemetrySink(path).emit(_event(
        TelemetryEventType.PROVIDER_CALLED, cost_usd=0.002,
        payload={"cost_source": "test-explicit-tariff"}))
    restored = TelemetryQuery(path).events()[0]
    assert restored.cost_usd == 0.002
    assert restored.payload["cost_source"] == "test-explicit-tariff"


def test_repeated_delivery_never_double_charges_a_provider_call():
    call = _event(TelemetryEventType.PROVIDER_CALLED, provider_calls=1,
                  input_tokens=10, output_tokens=2, cost_usd=0.002)
    verified = _event(TelemetryEventType.VERIFICATION_COMPLETED,
                      operation_id="operation", status="VERIFIED")
    ora, volc = project_ora_volc([call, call, verified])
    assert volc.llm_calls == 1
    assert ora.total_cost_usd == 0.002


def test_economics_joins_actual_usage_and_preserves_unknowns_across_runs(tmp_path):
    from workstation.integrations.hermes.telemetry import _observe_runtime_event
    from workstation.telemetry.projectors import project_operation_economics

    sink = SQLiteTelemetrySink(tmp_path / "economics.sqlite")
    set_telemetry_sink(sink)
    try:
        metadata = {"session_id": "s", "api_request_id": "call", "input_tokens": 10,
                    "output_tokens": 2, "cache_read_tokens": 8, "cache_write_tokens": 0,
                    "cost_usd": .002, "cost_source": "controlled-test-tariff"}
        _observe_runtime_event("provider_called", metadata)
        _observe_runtime_event("provider_called", metadata)
        _observe_runtime_event("provider_usage_recorded", metadata)
    finally:
        set_telemetry_sink(None)
    events = TelemetryQuery(sink.path).events()
    events += [_event(TelemetryEventType.VERIFICATION_COMPLETED, operation_id="op", status="VERIFIED"),
               _event(TelemetryEventType.MUTATION_DISPATCHED, operation_id="op", run_id="other")]
    result = project_operation_economics(events)
    assert result["provider_calls"] == 1
    assert result["input_tokens"] == 10 and result["cache_read_tokens"] == 8
    assert result["cost_per_verified_outcome_usd"] == .002
    assert result["cost_sources"] == ["controlled-test-tariff"]
    assert result["uncertain_effects"] == 1
    events.append(_event(TelemetryEventType.PROVIDER_CALLED, call_id="unknown"))
    unknown = project_operation_economics(events)
    assert unknown["cost_usd"] is None and unknown["input_tokens"] is None


def test_tool_telemetry_cannot_prevent_bookkeeping_or_retain_browser_text(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from workstation.integrations.hermes import tool_observer
    from workstation.telemetry.projectors import project_operation_economics
    import workstation.task_compiler

    monkeypatch.setattr(workstation.task_compiler, "durable_execution_active", lambda: False)
    captured = []
    monkeypatch.setattr(tool_observer, "record_mutation", lambda *a, **kw: captured.append("mutation"))
    monkeypatch.setattr(tool_observer, "capture_raw_result", lambda *a: captured.append("raw"))
    path = tmp_path / "tools.sqlite"
    set_telemetry_sink(SQLiteTelemetrySink(path))
    agent = SimpleNamespace(session_id="s", _canonical_work_task_id="t", _canonical_work_run_id="r")
    try:
        for call_id in ("a", "a", "b"):
            tool_observer.workstation_raw_post_tool_observer("browser_console",
                {"code": "PRIVATE_BROWSER_TEXT"}, call_id, "PRIVATE_DOM_TEXT", .01, {"agent": agent})
        # Malformed telemetry inputs must still reach both canonical bookkeeping owners.
        tool_observer.workstation_raw_post_tool_observer("browser_console",
            {"number": float("nan")}, "bad", "result", .01, {"agent": agent})
    finally:
        set_telemetry_sink(None)
    assert captured == ["mutation", "raw"] * 4
    result = project_operation_economics(TelemetryQuery(path).events())
    assert result["console_calls"] == 2 and result["repeated_browser_queries"] == 1
    raw = b"".join(p.read_bytes() for p in path.parent.glob("tools.sqlite*"))
    assert b"PRIVATE_BROWSER_TEXT" not in raw and b"PRIVATE_DOM_TEXT" not in raw


def test_sqlite_durability_dedupe_queries_order_and_retention(tmp_path):
    path = tmp_path / "telemetry.sqlite"
    sink = SQLiteTelemetrySink(path, max_events=3, prune_batch=1)
    start = datetime.now(timezone.utc)
    for index in range(4):
        sink.emit(_event(
            TelemetryEventType.VERIFICATION_COMPLETED,
            occurred_at=(start + timedelta(seconds=index)).isoformat(),
            operation_id=f"op-{index}", capability_id="cap-1",
            dedupe_key="same" if index == 1 else f"event-{index}",
        ))
    sink.emit(_event(dedupe_key="same"))
    reopened = TelemetryQuery(path)
    events = reopened.events(task_id="task-1", run_id="run-1")
    assert len(events) == 3
    assert [event.occurred_at for event in events] == sorted(event.occurred_at for event in events)
    assert len(reopened.events(operation_id="op-3")) == 1
    assert len(reopened.events(capability_id="cap-1")) == 3


def test_bounds_privacy_and_raw_sqlite_canary(tmp_path):
    path = tmp_path / "telemetry.sqlite"
    sink = SQLiteTelemetrySink(path)
    event = _event(payload={
        "prompt": "PROMPT_SECRET_123",
        "response_text": "RESPONSE_SECRET_234",
        "cookie": "COOKIE_SECRET_456",
        "target_url": "https://user:pass@example.test/path?token=URL_SECRET_789#fragment",
        "route": "native_browser",
    })
    sink.emit(event)
    raw = b"".join(candidate.read_bytes() for candidate in path.parent.glob("telemetry.sqlite*"))
    for canary in (b"PROMPT_SECRET_123", b"RESPONSE_SECRET_234", b"COOKIE_SECRET_456", b"URL_SECRET_789", b"user:pass"):
        assert canary not in raw
    assert sanitize_url("https://user:pass@example.test/path?q=secret#x")["page_family"] == "/path"
    assert sanitize_payload({"authorization": "secret", "ok": "value"}) == {"ok": "value"}
    with pytest.raises(ValueError, match="8 KiB"):
        sink.emit(_event(payload={f"field_{i}": "x" * 512 for i in range(32)}))
    with pytest.raises(ValueError, match="evidence_refs"):
        sink.emit(_event(evidence_refs=tuple(str(i) for i in range(33))))


def test_disabled_and_exploding_sink_are_product_fail_open():
    class ExplodingTelemetrySink:
        def emit(self, event):
            raise RuntimeError("store unavailable")

    def product_path():
        emit_event(TelemetryEventType.ROUTING_DECIDED, source_owner="workstation.test",
                   route="execute", payload={"decision": "EXECUTE"})
        return {"route": "execute", "certificate": "same", "effects": 1,
                "verification": "VERIFIED", "accepted": True}

    set_telemetry_sink(NullTelemetrySink())
    baseline = product_path()
    set_telemetry_sink(ExplodingTelemetrySink())
    assert product_path() == baseline
    set_telemetry_sink(None)


def test_h080b_funnel_reconstruction_and_metric_projection(tmp_path):
    path = tmp_path / "telemetry.sqlite"
    sink = SQLiteTelemetrySink(path)
    set_telemetry_sink(sink)
    sequence = [
        TelemetryEventType.EXPERIENCE_ACCEPTED,
        TelemetryEventType.CAPABILITY_CANDIDATE_CREATED,
        TelemetryEventType.VERIFIER_VALIDATION_COMPLETED,
        TelemetryEventType.CONTROLLED_REPLAY_COMPLETED,
        TelemetryEventType.CAPABILITY_PROMOTED,
        TelemetryEventType.ROUTING_DECIDED,
        TelemetryEventType.CAPABILITY_EXECUTION_STARTED,
        TelemetryEventType.MUTATION_DISPATCHED,
        TelemetryEventType.MUTATION_ACKNOWLEDGED,
        TelemetryEventType.VERIFICATION_COMPLETED,
        TelemetryEventType.CAPABILITY_EXECUTION_FINISHED,
        TelemetryEventType.OUTCOME_ACCEPTED,
    ]
    for kind in sequence:
        emit_event(kind, source_owner="workstation.test", task_id="task-h080b", run_id="run-c",
                   operation_id="op-c", capability_id="cap-native", capability_version="1.0.0",
                   route="deterministic", status="VERIFIED" if kind == TelemetryEventType.VERIFICATION_COMPLETED else "success",
                   provider_calls=0 if kind == TelemetryEventType.OUTCOME_ACCEPTED else None)
    events = TelemetryQuery(path).reconstruct_run("task-h080b", "run-c")
    assert [event.event_type for event in events] == sequence
    assert sum(event.provider_calls or 0 for event in events) == 0
    ora, volc = project_ora_volc(events)
    assert ora.ora_ratio == 1.0
    assert volc.verified_outcomes == 1
    assert volc.llm_calls == 0
    set_telemetry_sink(None)

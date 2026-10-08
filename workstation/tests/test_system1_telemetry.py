from types import SimpleNamespace
from agent.runtime_events import register_runtime_event_observer, notify_runtime_event
from agent.system1_decision import DecisionRequest
from workstation.artifacts import ArtifactStore
from workstation.system1.laya_provider import LayaDecisionProvider
from workstation.integrations.hermes.telemetry import _observe_runtime_event
from workstation.telemetry import set_telemetry_sink, NullTelemetrySink
from workstation.telemetry.sqlite_sink import SQLiteTelemetrySink, TelemetryQuery
from workstation.telemetry.projectors import project_ora_volc
from workstation.reasoning_handoff import needs_reasoning
from workstation.tests.test_taskcompiler_supersession_e2e import runtime, test_compiler_supersession_resume_uncertain_without_duplicate as _run_supersession


def test_actual_provider_supersession_handoff_and_unknown_economics(runtime, tmp_path):
    path = tmp_path / "telemetry.sqlite"
    set_telemetry_sink(SQLiteTelemetrySink(path))
    register_runtime_event_observer(_observe_runtime_event)
    compiler = runtime[0]
    provider = LayaDecisionProvider(artifact_store=compiler.artifacts)
    payloads = iter([
        {"answers": {"q": {"type": "choice", "choice": "A", "answer_confidence": .99}}},
        {"answers": {"q": {"type": "choice", "choice": "ABSTAIN", "answer_confidence": .99}}},
    ])
    provider._router = SimpleNamespace(predict=lambda **kw: next(payloads))
    try:
        for _ in range(3):  # third call errors; all calls are observed
            provider(DecisionRequest(task_id="t", run_id="r", operation_id="op", questions={"q": {"type": "choice", "criteria": {"A": "a", "ABSTAIN": "neutral"}}}))
        _run_supersession(runtime)
        needs_reasoning(compiler.artifacts, "t", completed_until=None, expected="contract", observed="gap", safe_to_resume=False,
            context={"run_id": "r", "operation_id": "op"})
        notify_runtime_event("provider_called", {"task_id": "t", "api_request_id": "unknown-usage", "status": "success"})
        events = TelemetryQuery(path).events()
        ora, volc = project_ora_volc(events)
        assert ora.system1_calls == 3
        assert ora.system1_successful_decisions == 1
        assert ora.system1_abstentions == 1
        assert ora.system1_fallbacks == 2 and ora.system1_errors == 1
        assert ora.authority_superseded_count == 1
        assert ora.system2_wake_count >= 1
        assert volc.tokens_per_verified_outcome is None and volc.cost_per_verified_outcome is None
        serialized = path.read_bytes()
        assert b'"questions"' not in serialized and b'"answers"' not in serialized
    finally:
        set_telemetry_sink(NullTelemetrySink())


def test_canonical_taskrun_claim_emits_supersession_after_commit(tmp_path):
    from hermes_cli import kanban_db, kanban_db_connect
    path = tmp_path / "owner-telemetry.sqlite"
    set_telemetry_sink(SQLiteTelemetrySink(path))
    register_runtime_event_observer(_observe_runtime_event)
    conn = kanban_db_connect.connect(tmp_path / "kanban.db")
    try:
        task = kanban_db.create_task(conn, title="owner lifecycle", session_id="s")
        conn.execute("UPDATE tasks SET status='ready' WHERE id=?", (task,))
        conn.commit()
        run_a = kanban_db.claim_task(conn, task, claimer="worker-a")
        assert run_a.current_run_id
        assert kanban_db.reclaim_task(conn, task)
        run_b = kanban_db.claim_task(conn, task, claimer="worker-b")
        assert run_b.current_run_id != run_a.current_run_id
        events = TelemetryQuery(path).events()
        assert project_ora_volc(events)[0].authority_superseded_count == 1
        owner_event = next(e for e in events if e.source_owner == "hermes.kanban_taskrun")
        assert owner_event.run_id == str(run_a.current_run_id)
        assert owner_event.payload["current_run_id"] == str(run_b.current_run_id)
    finally:
        conn.close()
        set_telemetry_sink(NullTelemetrySink())

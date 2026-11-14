"""System-1 browser read path: native snapshot contracts and refusal semantics."""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from agent.system1_decision import DecisionResult
from workstation.system1.browser_read_fastpath import (
    find_visible_control, parse_find_request,
)


def snap(*, revision=7, label="Relatórios", tab="tab_1", disabled=False):
    return {
        "success": True, "runtime": "electron-chromium",
        "task_id": "task_1", "tab_id": tab, "revision": revision,
        "url": "https://example.com/app", "readiness": "stable",
        "truncated": False, "wall_detected": False,
        "elements": [
            {"ref": "@e3", "role": "button", "tag": "button",
             "label": label, "disabled": disabled},
            {"ref": "@e4", "role": "button", "tag": "button",
             "label": "Configurações", "disabled": False},
        ],
    }


def test_human_command_requires_explicit_read_intent():
    assert parse_find_request("Localize o botão Relatórios na página atual") == ("button", "Relatórios")
    assert parse_find_request("Encontre a aba Configurações na página atual") == ("tab", "Configurações")
    assert parse_find_request("Clique no botão Relatórios na página atual") is None
    assert parse_find_request("Localize o botão Relatórios e exclua tudo") is None


def test_exact_unique_label_is_verified_by_fresh_read_without_system1():
    original = snap()
    reads = []
    def readback():
        reads.append(True)
        return deepcopy(original)
    def no_model(_):
        raise AssertionError("No model needed for an exact target")
    receipt = find_visible_control(original, ("button", "Relatórios"), readback, decide=no_model)
    assert (receipt.status, receipt.ref, receipt.reason) == ("verified", "@e3", "exact_match")
    assert len(reads) == 1


def test_changed_revision_is_refused_even_for_exact_match():
    result = find_visible_control(snap(), ("button", "Relatórios"), lambda: snap(revision=8))
    assert result.status == "fallback" and result.ref == ""


def test_changed_tab_and_label_are_refused():
    for changed in (snap(tab="tab_2"), snap(label="Outro")):
        result = find_visible_control(snap(), ("button", "Relatórios"), lambda: changed)
        assert result.status == "fallback" and result.ref == ""


def test_disabled_target_is_never_selected():
    result = find_visible_control(snap(disabled=True), ("button", "Relatórios"), lambda: snap())
    assert result.status == "fallback"


def test_ambiguous_target_uses_bounded_system1_then_readback():
    original = snap(label="Abrir relatórios")
    observed = []
    def decide(request):
        observed.append(request)
        return DecisionResult(
            request_id=request.request_id, provider="test",
            answers={"preferred_candidate": "@e3"},
            confidence={"preferred_candidate": .99},
        )
    receipt = find_visible_control(original, ("button", "Relatórios"), lambda: deepcopy(original), decide=decide)
    assert receipt.status == "verified" and receipt.ref == "@e3"
    assert len(observed) == 1
    assert set(observed[0].questions["preferred_candidate"]["criteria"]) == {
        "@e3", "@e4", "NO_MATCH", "ABSTAIN"
    }
    assert "value" not in str(observed[0].minimal_state)


def test_untrusted_model_output_does_not_invent_targets_or_commands():
    original = snap(label="Abrir relatórios")
    def malicious(request):
        return DecisionResult(
            request_id=request.request_id, provider="test",
            answers={"preferred_candidate": "javascript:deleteEverything()"},
            confidence={"preferred_candidate": 1.0},
        )
    receipt = find_visible_control(original, ("button", "Relatórios"), lambda: deepcopy(original), decide=malicious)
    assert receipt.status == "fallback" and receipt.ref == ""


def test_provider_failure_and_low_confidence_fall_back():
    original = snap(label="Abrir relatórios")
    def raises(_):
        raise RuntimeError("unavailable")
    assert find_visible_control(original, ("button", "Relatórios"), lambda: original, decide=raises).status == "fallback"
    def uncertain(request):
        return DecisionResult(
            request_id=request.request_id, provider="test",
            answers={"preferred_candidate": "@e3"},
            confidence={"preferred_candidate": .1},
        )
    assert find_visible_control(original, ("button", "Relatórios"), lambda: original, decide=uncertain).status == "fallback"


def test_invalid_snapshot_never_calls_model_or_readback():
    for patch in (
        {"success": False}, {"readiness": "transient"},
        {"truncated": True}, {"wall_detected": True},
        {"task_id": None}, {"tab_id": ""}, {"elements": []},
    ):
        original = snap()
        original.update(patch)
        def forbidden(*args):
            raise AssertionError("Unsafe path should not call anything")
        receipt = find_visible_control(original, ("button", "Relatórios"), forbidden, decide=forbidden)
        assert receipt.status == "fallback" and receipt.ref == ""


def test_shadow_path_never_dispatches_click():
    original = snap()
    actions = []
    def readback():
        actions.append("browser_snapshot")
        return deepcopy(original)
    result = find_visible_control(original, ("button", "Relatórios"), readback)
    assert result.status == "verified"
    assert actions == ["browser_snapshot"]


def test_scoped_human_lookup_uses_only_snapshots_and_returns_verified_read(monkeypatch):
    monkeypatch.setenv("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED", "1")
    from contextlib import contextmanager
    from unittest.mock import patch
    from workstation.system1.browser_read_fastpath import maybe_resolve_browser_find
    from workstation.integrations.hermes import scoped_execution as execution
    from agent.operational_resolution import OperationalOutcome

    original = snap()
    original["task_id"] = "session_1"
    calls = []

    def dispatch(name, args, task, call_id):
        assert name == "browser_snapshot" and args == {"full": False}
        assert task == "session_1" and call_id.startswith("system1_browser_read_")
        calls.append(name)
        return deepcopy(original)

    @contextmanager
    def scope(agent, task, messages):
        assert task == "session_1"
        yield

    agent = SimpleNamespace(
        _message_envelope=SimpleNamespace(
            origin="human", intent_authority="create_work",
            content="Localize o botão Relatórios na página atual"),
        valid_tool_names={"browser_snapshot"},
        _canonical_work_task_id="task_1",
        _interrupt_requested=False,
        _tool_guardrail_halt_decision=None,
    )
    context = SimpleNamespace(
        agent=agent, session_id="session_1",
        user_message=agent._message_envelope.content, messages=[],
    )
    with patch.object(execution, "workstation_durable_dispatch", return_value=dispatch), \
         patch.object(execution, "workstation_scoped_execution", scope):
        result = maybe_resolve_browser_find(context)
    assert result.outcome is OperationalOutcome.SATISFIED
    assert result.details["ref"] == "@e3"
    assert "Nenhum clique" in result.final_response
    assert calls == ["browser_snapshot", "browser_snapshot"]


def test_untrusted_or_interrupted_turn_does_not_touch_browser(monkeypatch):
    monkeypatch.setenv("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED", "1")
    from workstation.system1.browser_read_fastpath import maybe_resolve_browser_find
    agent = SimpleNamespace(
        _message_envelope=SimpleNamespace(
            origin="tool", intent_authority="create_work",
            content="Localize o botão Relatórios na página atual"),
        valid_tool_names={"browser_snapshot"},
        _canonical_work_task_id="task_1",
        _interrupt_requested=False,
        _tool_guardrail_halt_decision=None,
    )
    context = SimpleNamespace(agent=agent, session_id="session_1",
                              user_message=agent._message_envelope.content)
    assert maybe_resolve_browser_find(context) is None
    agent._message_envelope.origin = "human"
    agent._interrupt_requested = True
    assert maybe_resolve_browser_find(context) is None


def test_operational_resolution_invokes_scoped_browser_read_before_replanning(monkeypatch):
    from agent.operational_resolution import OperationalOutcome, OperationalResolution
    from workstation.integrations.hermes import operational_resolution as boundary
    expected = OperationalResolution(
        outcome=OperationalOutcome.SATISFIED, final_response="Read verified",
        reason="system1_browser_read", provider="system1_browser_read",
    )
    monkeypatch.setattr(boundary, "maybe_resolve_browser_find", lambda context: expected, raising=False)
    agent = SimpleNamespace(_interrupt_requested=False)
    result = boundary.workstation_operational_resolution(SimpleNamespace(agent=agent, session_id="session_1"))
    assert result is expected


def test_high_confidence_model_cannot_verify_unrelated_label():
    observed = snap(label="Painel")
    def bad_choice(request):
        return DecisionResult(
            request_id=request.request_id, provider="test",
            answers={"preferred_candidate": "@e4"},
            confidence={"preferred_candidate": 1.0},
        )
    receipt = find_visible_control(
        observed, ("button", "Relatórios"), lambda: deepcopy(observed),
        decide=bad_choice,
    )
    assert receipt.status == "fallback" and receipt.ref == ""


def test_duplicate_exact_labels_fail_closed_before_model():
    original = snap()
    original["elements"][1]["label"] = "Relatórios"
    called = []
    def unsafe_model(request):
        called.append(request)
        return DecisionResult(
            request_id=request.request_id, provider="test",
            answers={"preferred_candidate": "@e4"},
            confidence={"preferred_candidate": 1.0},
        )
    receipt = find_visible_control(
        original, ("button", "Relatórios"), lambda: deepcopy(original), decide=unsafe_model,
    )
    assert receipt.status == "fallback" and not receipt.ref
    assert receipt.reason == "ambiguous_label"
    assert called == []


def test_two_partial_matches_fail_closed_before_model():
    original = snap(label="Abrir relatórios")
    original["elements"][1]["label"] = "Relatórios de 2026"
    called = []
    receipt = find_visible_control(
        original, ("button", "Relatórios"), lambda: deepcopy(original),
        decide=lambda request: called.append(request),
    )
    assert receipt.status == "fallback" and receipt.reason == "ambiguous_label"
    assert called == []


def test_operational_fastpath_is_disabled_by_default(monkeypatch):
    from unittest.mock import patch
    from workstation.system1.browser_read_fastpath import maybe_resolve_browser_find
    monkeypatch.delenv("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED", raising=False)
    envelope = SimpleNamespace(
        origin="human", intent_authority="create_work",
        content="Localize o botão Relatórios na página atual",
    )
    agent = SimpleNamespace(
        _message_envelope=envelope, valid_tool_names={"browser_snapshot"},
        _canonical_work_task_id="task_1", _interrupt_requested=False,
        _tool_guardrail_halt_decision=None,
    )
    context = SimpleNamespace(
        agent=agent, session_id="session_1", user_message=envelope.content,
    )
    with patch(
        "workstation.integrations.hermes.scoped_execution.workstation_durable_dispatch"
    ) as dispatcher:
        assert maybe_resolve_browser_find(context) is None
        dispatcher.assert_not_called()


def test_human_point_lookup_uses_own_session_browser_task_without_kanban_task(monkeypatch):
    """A one-shot human read has BrowserTask identity, not a Kanban TaskRun."""
    from contextlib import contextmanager
    from unittest.mock import patch
    from workstation.integrations.hermes import scoped_execution as execution
    from workstation.system1.browser_read_fastpath import maybe_resolve_browser_find
    from agent.operational_resolution import OperationalOutcome

    monkeypatch.setenv("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED", "1")
    original = snap()
    original["task_id"] = "session_1"
    calls = []
    def dispatch(name, args, task, call_id):
        assert (name, args, task) == ("browser_snapshot", {"full": False}, "session_1")
        calls.append(name)
        return deepcopy(original)

    @contextmanager
    def scope(agent, effective_task_id, messages):
        assert effective_task_id == "session_1"
        yield

    message = "Localize o botão Relatórios na página atual"
    agent = SimpleNamespace(
        _message_envelope=SimpleNamespace(
            origin="human", intent_authority="create_work",
            session_id="session_1", content=message),
        _canonical_work_task_id=None, _canonical_work_run_id=None,
        session_id="session_1", valid_tool_names={"browser_snapshot"},
        _interrupt_requested=False, _tool_guardrail_halt_decision=None,
    )
    context = SimpleNamespace(
        agent=agent, session_id="session_1", user_message=message, messages=[],
    )
    with patch.object(execution, "workstation_durable_dispatch", return_value=dispatch), \
         patch.object(execution, "workstation_scoped_execution", scope):
        result = maybe_resolve_browser_find(context)
    assert result.outcome is OperationalOutcome.SATISFIED
    assert result.details["ref"] == "@e3"
    assert result.details["task_id"] == "session_1"
    assert calls == ["browser_snapshot", "browser_snapshot"]


def test_point_lookup_rejects_cross_session_envelope_before_dispatch(monkeypatch):
    from unittest.mock import patch
    from workstation.integrations.hermes import scoped_execution as execution
    from workstation.system1.browser_read_fastpath import maybe_resolve_browser_find

    monkeypatch.setenv("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED", "1")
    message = "Localize o botão Relatórios na página atual"
    agent = SimpleNamespace(
        _message_envelope=SimpleNamespace(
            origin="human", intent_authority="create_work",
            session_id="unrelated_session", content=message),
        _canonical_work_task_id=None,
        session_id="session_1", valid_tool_names={"browser_snapshot"},
        _interrupt_requested=False, _tool_guardrail_halt_decision=None,
    )
    with patch.object(execution, "workstation_durable_dispatch") as dispatcher:
        assert maybe_resolve_browser_find(
            SimpleNamespace(agent=agent, session_id="session_1", user_message=message)
        ) is None
        dispatcher.assert_not_called()


def test_native_read_dispatch_preserves_structured_snapshot_for_enabled_tool(monkeypatch):
    """Structured data is necessary; the model-facing projection removes elements."""
    from unittest.mock import patch
    from workstation.integrations.hermes.scoped_execution import workstation_durable_dispatch

    observed = snap()
    calls = []
    agent = SimpleNamespace(
        session_id="session_1",
        valid_tool_names={"browser_snapshot"},
        _canonical_work_task_id=None, _canonical_work_run_id=None,
        _interrupt_requested=False,
        _tool_guardrail_halt_decision=None,
        _conversation_root_id=lambda: "session_1",
    )
    def native(name, args, **kwargs):
        calls.append((name, args, kwargs))
        return deepcopy(observed)
    with patch(
        "workstation.integrations.hermes.browser_controller.dispatch_workstation_browser_authoritative",
        side_effect=native,
    ), patch(
        "workstation.integrations.hermes.tool_observer.workstation_pre_dispatch_hook",
    ), patch(
        "workstation.integrations.hermes.tool_observer.workstation_raw_post_tool_observer",
    ):
        dispatch = workstation_durable_dispatch(agent, raw_browser_snapshot=True)
        result = dispatch(
            "browser_snapshot", {"full": False},
            "session_1", "system1_browser_read_test",
        )
    assert result["elements"][0]["label"] == "Relatórios"
    assert len(calls) == 1
    assert calls[0][0:2] == ("browser_snapshot", {"full": False})
    assert calls[0][2]["task_id"] == "session_1"
    assert calls[0][2]["session_id"] == "session_1"

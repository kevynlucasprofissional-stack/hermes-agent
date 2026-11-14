"""System 1 can propose, but only an exact QA-local human intent can execute."""
from contextlib import nullcontext
from types import SimpleNamespace

from agent.system1_decision import DecisionResult
from agent.operational_resolution import OperationalOutcome
from workstation.system1.browser_interaction_fastpath import (
    InteractionIntent, InteractionProposal, parse_interaction, propose_interaction,
    maybe_execute_qa_interaction,
)


def _snapshot(url="http://127.0.0.1:18792/interaction", revision=1, text="QA-NAME-EMPTY"):
    return {
        "success": True, "runtime": "electron-chromium", "url": url,
        "task_id": "qa-session", "tab_id": "qa-tab", "revision": revision,
        "readiness": "stable", "truncated": False, "wall_detected": False,
        "text": text,
        "elements": [
            {"ref": "@e1", "label": "Nome", "role": "textbox", "tag": "input", "disabled": False},
            {"ref": "@e2", "label": "Abrir Relatorios", "role": "button", "tag": "button", "disabled": False},
        ],
    }


def _decide(expected_op, expected_ref, *, confidence=.95):
    def choose(request):
        assert request.minimal_state["target"]
        assert "TesteQA" not in str(request.minimal_state)
        assert set(request.questions) == {"operation", "preferred_candidate"}
        return DecisionResult(
            request_id=request.request_id, provider="laya",
            answers={"operation": expected_op, "preferred_candidate": expected_ref},
            confidence={"operation": confidence, "preferred_candidate": confidence},
        )
    return choose


def test_parse_only_explicit_single_step():
    assert parse_interaction('Clique no botão "Relatorios" na página atual').operation == "click"
    got = parse_interaction('Preencha o campo "Nome" com "TesteQA" na página atual')
    assert got == InteractionIntent("type", "Nome", "TesteQA")
    for phrase in ("Envie o formulário", "Clique em tudo", "Preencha o campo Nome",
                   "Clique no botão Salvar na página seguinte"):
        assert parse_interaction(phrase) is None


def test_click_and_fill_bounded_multi_question_laya_proposals():
    before = _snapshot()
    result = propose_interaction(before, InteractionIntent("click", "Relatorios"),
                                 lambda: before, decide=_decide("click", "@e2"))
    assert (result.status, result.operation, result.ref, result.provider) == (
        "verified", "click", "@e2", "laya",
    )
    filled = propose_interaction(before, InteractionIntent("type", "Nome", "TesteQA"),
                                 lambda: before, decide=_decide("type", "@e1"))
    assert filled.status == "verified" and filled.ref == "@e1"


def test_model_mismatch_and_low_confidence_fail_closed():
    snap = _snapshot()
    wrong = propose_interaction(snap, InteractionIntent("click", "Relatorios"),
                                lambda: snap, decide=_decide("type", "@e2"))
    assert wrong.status == "fallback" and wrong.reason == "wrong_operation"
    low = propose_interaction(snap, InteractionIntent("type", "Nome", "TesteQA"),
                              lambda: snap, decide=_decide("type", "@e1", confidence=.5))
    assert low.status == "fallback"


def test_stale_target_rejected_before_any_mutation():
    snap = _snapshot()
    stale = _snapshot(revision=2)
    result = propose_interaction(snap, InteractionIntent("click", "Relatorios"),
                                 lambda: stale, decide=_decide("click", "@e2"))
    assert result.status == "fallback" and result.reason == "stale_target"


def test_duplicated_target_never_reaches_model():
    snap = _snapshot()
    snap["elements"].append({"ref": "@e3", "label": "Abrir Relatorios",
                             "role": "button", "tag": "button", "disabled": False})
    def reject(_):
        raise AssertionError("model should not be consulted")
    result = propose_interaction(snap, InteractionIntent("click", "Relatorios"),
                                 lambda: snap, decide=reject)
    assert result.reason == "ambiguous_target"


def _ctx(message):
    envelope = SimpleNamespace(origin="human", intent_authority="create_work",
                               session_id="qa-session", content=message)
    agent = SimpleNamespace(
        session_id="qa-session", _message_envelope=envelope,
        _interrupt_requested=False, _conversation_root_id=lambda: "qa-session",
        valid_tool_names={"browser_snapshot"},
    )
    return SimpleNamespace(agent=agent, session_id="qa-session", turn_id="turn-01",
                           user_message=message, messages=[])


def _dispatch_factory(before, after, output):
    effects = []
    reads = []
    def durable(_agent, *, raw_browser_snapshot=False):
        assert raw_browser_snapshot
        def dispatch(name, args, task, call_id):
            assert task == "qa-session"
            if name == "browser_snapshot":
                reads.append(name)
                return before if len(reads) <= 2 else after
            effects.append((name, args, call_id))
            return output
        return dispatch
    return durable, effects, reads


def test_other_site_can_never_dispatch(monkeypatch):
    monkeypatch.setenv("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED", "1")
    from workstation.integrations.hermes import scoped_execution
    before = _snapshot(url="https://example.org/")
    durable, effects, reads = _dispatch_factory(before, before, {"success": True})
    monkeypatch.setattr(scoped_execution, "workstation_durable_dispatch", durable)
    monkeypatch.setattr(scoped_execution, "workstation_scoped_execution", lambda *_args: nullcontext())
    assert maybe_execute_qa_interaction(_ctx('Clique no botão "Relatorios" na página atual')) is None
    assert effects == [] and len(reads) == 1


def test_one_native_click_verified_and_never_repeated(monkeypatch):
    monkeypatch.setenv("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED", "1")
    from workstation.integrations.hermes import scoped_execution
    import workstation.system1.browser_interaction_fastpath as module

    before = _snapshot()
    after = _snapshot(revision=2, text="QA-REPORTS-CLICKED-ONCE")
    durable, effects, reads = _dispatch_factory(before, after, {"success": True})
    monkeypatch.setattr(scoped_execution, "workstation_durable_dispatch", durable)
    monkeypatch.setattr(scoped_execution, "workstation_scoped_execution", lambda *_args: nullcontext())
    monkeypatch.setattr(module, "propose_interaction", lambda _before, _intent, read: (
        read(), InteractionProposal("verified", "click", "@e2", "laya", "system1_proposal",
                                    "artifact://receipt"))[1])
    resolution = maybe_execute_qa_interaction(_ctx('Clique no botão "Relatorios" na página atual'))
    assert resolution.outcome is OperationalOutcome.EXECUTED
    assert len(effects) == 1 and effects[0][0] == "browser_click"
    assert len(reads) == 3


def test_unverified_effect_must_handoff_without_retry(monkeypatch):
    monkeypatch.setenv("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED", "1")
    from workstation.integrations.hermes import scoped_execution
    import workstation.system1.browser_interaction_fastpath as module
    before = _snapshot()
    durable, effects, reads = _dispatch_factory(before, before, {"success": True})
    monkeypatch.setattr(scoped_execution, "workstation_durable_dispatch", durable)
    monkeypatch.setattr(scoped_execution, "workstation_scoped_execution", lambda *_args: nullcontext())
    monkeypatch.setattr(module, "propose_interaction", lambda _before, _intent, read: (
        read(), InteractionProposal("verified", "type", "@e1", "laya", "system1_proposal"))[1])
    resolution = maybe_execute_qa_interaction(_ctx('Preencha o campo "Nome" com "TesteQA" na página atual'))
    assert resolution.outcome is OperationalOutcome.HANDOFF
    assert len(effects) == 1 and effects[0][1]["text"] == "TesteQA"
    assert len(reads) == 3


def test_one_native_type_verified(monkeypatch):
    monkeypatch.setenv("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED", "1")
    from workstation.integrations.hermes import scoped_execution
    import workstation.system1.browser_interaction_fastpath as module
    before = _snapshot()
    after = _snapshot(revision=2, text="QA-NAME-ENTERED:TesteQA")
    durable, effects, reads = _dispatch_factory(before, after, {"success": True})
    monkeypatch.setattr(scoped_execution, "workstation_durable_dispatch", durable)
    monkeypatch.setattr(scoped_execution, "workstation_scoped_execution", lambda *_args: nullcontext())
    monkeypatch.setattr(module, "propose_interaction", lambda _before, _intent, read: (
        read(), InteractionProposal("verified", "type", "@e1", "laya", "system1_proposal"))[1])
    resolution = maybe_execute_qa_interaction(_ctx('Preencha o campo "Nome" com "TesteQA" na página atual'))
    assert resolution.outcome is OperationalOutcome.EXECUTED
    assert len(effects) == 1 and effects[0][0:2] == (
        "browser_type", {"ref": "@e1", "text": "TesteQA"},
    )
    assert len(reads) == 3


def test_ambiguous_proposal_never_falls_through_to_system2(monkeypatch):
    monkeypatch.setenv("HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED", "1")
    from workstation.integrations.hermes import scoped_execution
    import workstation.system1.browser_interaction_fastpath as module
    before = _snapshot()
    durable, effects, reads = _dispatch_factory(before, before, {"success": True})
    monkeypatch.setattr(scoped_execution, "workstation_durable_dispatch", durable)
    monkeypatch.setattr(scoped_execution, "workstation_scoped_execution", lambda *_args: nullcontext())
    monkeypatch.setattr(module, "propose_interaction", lambda *_args: InteractionProposal(
        "fallback", reason="ambiguous_target"))
    resolution = maybe_execute_qa_interaction(_ctx('Clique no botão "Relatorios" na página atual'))
    assert resolution.outcome is OperationalOutcome.HANDOFF
    assert resolution.reason == "qa_proposal_rejected"
    assert effects == [] and len(reads) == 1

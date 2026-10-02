"""Behaviour of the pre-reasoning operational resolution boundary.

The boundary exists so an operational runtime can answer a turn without spending a
reasoning round on the provider. These tests pin the contract the harness owes the
loop: an unanswered step reasons, an answered step closes the turn through the
ordinary text-response path, and a defective provider degrades to reasoning rather
than breaking the turn or half-acting.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from agent.operational_resolution import (
    OperationalOutcome,
    OperationalResolution,
    OperationalResolutionContext,
    operational_resolution_metrics,
    operational_resolution_providers,
    register_operational_resolution_provider,
    reset_operational_resolution,
    resolve_operational_step,
)
from agent.turn_operational_resolution import resolve_operational_step_phase


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_operational_resolution()
    yield
    reset_operational_resolution()


class _FakeAgent:
    """Minimal turn host: the boundary reads identity and flushes the reply."""

    def __init__(self, session_id: str = "session-1"):
        self.session_id = session_id
        self.quiet_mode = True
        self.flushes = []
        self._api_call_count = 1

    def _conversation_root_id(self):
        return self.session_id

    def _flush_messages_to_session_db(self, messages, conversation_history):
        self.flushes.append(list(messages))


def _phase(agent, **overrides):
    kwargs = {
        "messages": [{"role": "user", "content": "archive the invoice"}],
        "conversation_history": [],
        "user_message": "archive the invoice",
        "effective_task_id": "task-9",
        "turn_id": "turn-3",
        "api_call_count": 1,
        "final_response": None,
        "_turn_exit_reason": None,
    }
    kwargs.update(overrides)
    return resolve_operational_step_phase(agent, **kwargs)


def _resolving(outcome, *, text="Work is already done.", reason="test", provider=None):
    def _provider(context):
        return OperationalResolution(
            outcome=outcome, final_response=text, reason=reason, provider=provider or ""
        )

    _provider.__name__ = "resolving_provider"
    return _provider


def test_an_unanswered_step_still_reasons():
    """No provider registered is not a resolution — the loop must call the model."""
    agent = _FakeAgent()
    verdict = _phase(agent)

    assert verdict.action == "fallthrough"
    assert verdict.final_response is None
    assert verdict.api_call_count == 1
    assert agent.flushes == []


def test_a_terminal_resolution_closes_the_turn_without_reasoning():
    """The reply is appended and flushed; the loop breaks and never calls out."""
    register_operational_resolution_provider(
        _resolving(OperationalOutcome.EXECUTED, text="Invoice archived and verified.")
    )
    agent = _FakeAgent()
    messages = [{"role": "user", "content": "archive the invoice"}]

    verdict = _phase(agent, messages=messages)

    assert verdict.action == "break"
    assert verdict.final_response == "Invoice archived and verified."
    assert (messages[-1]["role"], messages[-1]["content"]) == (
        "assistant", "Invoice archived and verified."
    )
    assert agent.flushes and agent.flushes[0][-1]["content"] == "Invoice archived and verified."
    assert verdict._turn_exit_reason == "operational_resolution(EXECUTED)"


def test_the_iteration_is_refunded_because_no_request_was_issued():
    """``completed`` is derived from the call count, so a resolved step must not be charged."""
    register_operational_resolution_provider(_resolving(OperationalOutcome.SATISFIED))
    agent = _FakeAgent()

    verdict = _phase(agent, api_call_count=4)

    assert verdict.api_call_count == 3
    assert agent._api_call_count == 3


def test_a_flush_failure_does_not_abort_the_turn():
    """Durability is finalized later; a flush error must not lose the reply."""
    register_operational_resolution_provider(_resolving(OperationalOutcome.WAIT))

    class _FlakyAgent(_FakeAgent):
        def _flush_messages_to_session_db(self, messages, conversation_history):
            raise RuntimeError("session db unavailable")

    messages = [{"role": "user", "content": "archive the invoice"}]
    verdict = _phase(_FlakyAgent(), messages=messages)

    assert verdict.action == "break"
    assert messages[-1]["content"] == "Work is already done."


@pytest.mark.parametrize(
    "outcome",
    [OperationalOutcome.SATISFIED, OperationalOutcome.EXECUTED, OperationalOutcome.WAIT, OperationalOutcome.HANDOFF],
)
def test_every_terminal_outcome_ends_the_step(outcome):
    register_operational_resolution_provider(_resolving(outcome))
    assert _phase(_FakeAgent()).action == "break"


def test_continue_reasoning_is_not_a_resolution():
    register_operational_resolution_provider(
        _resolving(OperationalOutcome.CONTINUE_REASONING, text="should be ignored")
    )
    verdict = _phase(_FakeAgent())

    assert verdict.action == "fallthrough"
    assert operational_resolution_metrics()["misses"] == 1


def test_a_raising_provider_degrades_to_reasoning():
    """An optimizer defect costs a reasoning round; it must not break the turn."""
    def _broken(context):
        raise RuntimeError("provider bug")

    register_operational_resolution_provider(_broken)
    verdict = _phase(_FakeAgent())

    assert verdict.action == "fallthrough"
    assert operational_resolution_metrics()["errors"] == 1


def test_a_terminal_outcome_without_reply_text_degrades_to_reasoning():
    """Ending a turn on an empty reply is worse than reasoning."""
    register_operational_resolution_provider(
        _resolving(OperationalOutcome.SATISFIED, text="")
    )
    verdict = _phase(_FakeAgent())

    assert verdict.action == "fallthrough"
    assert operational_resolution_metrics()["errors"] == 1


def test_a_wrong_return_type_degrades_to_reasoning():
    register_operational_resolution_provider(lambda context: "EXECUTED")
    verdict = _phase(_FakeAgent())

    assert verdict.action == "fallthrough"
    assert operational_resolution_metrics()["errors"] == 1


def test_an_undecided_provider_does_not_block_a_deciding_one():
    """Providers are consulted in order until one answers terminally."""
    register_operational_resolution_provider(lambda context: None)
    register_operational_resolution_provider(_resolving(OperationalOutcome.HANDOFF, text="Approve this."))

    verdict = _phase(_FakeAgent())

    assert verdict.action == "break"
    assert verdict.final_response == "Approve this."


def test_the_first_terminal_provider_wins():
    register_operational_resolution_provider(_resolving(OperationalOutcome.WAIT, text="first"))
    register_operational_resolution_provider(_resolving(OperationalOutcome.EXECUTED, text="second"))

    verdict = _phase(_FakeAgent())

    assert verdict.final_response == "first"


def test_an_unregistered_provider_stops_being_consulted():
    from agent.operational_resolution import unregister_operational_resolution_provider

    provider = _resolving(OperationalOutcome.EXECUTED)
    register_operational_resolution_provider(provider)
    unregister_operational_resolution_provider(provider)

    assert operational_resolution_providers() == ()
    assert _phase(_FakeAgent()).action == "fallthrough"


def test_the_provider_sees_the_turn_identity_it_must_bind_to():
    """A provider cannot resolve safely without session/task/turn identity."""
    seen = {}

    def _provider(context):
        seen["session"] = context.session_id
        seen["task"] = context.task_id
        seen["turn"] = context.turn_id
        seen["api_call_count"] = context.api_call_count
        return None

    register_operational_resolution_provider(_provider)
    _phase(_FakeAgent(session_id="root-7"), effective_task_id="task-9", turn_id="turn-3", api_call_count=2)

    assert seen == {"session": "root-7", "task": "task-9", "turn": "turn-3", "api_call_count": 2}


def test_consulting_the_boundary_is_observable():
    """Misses and hits are counted, so coverage is measurable rather than assumed."""
    register_operational_resolution_provider(lambda context: None)
    resolve_operational_step(
        OperationalResolutionContext(
            agent=SimpleNamespace(), session_id="s", task_id="t", turn_id="u",
            user_message="m", messages=[], api_call_count=0, iteration=0,
        )
    )

    metrics = operational_resolution_metrics()
    assert metrics["steps"] == 1
    assert metrics["misses"] == 1
    assert metrics["hits"] == 0

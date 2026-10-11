"""Fresh commands reach the existing router without a historical objective."""
from types import SimpleNamespace

from agent.operational_resolution import OperationalOutcome, OperationalResolutionContext
from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.ir import EQ, SET
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.durable_tasks import DurableTaskStore
from workstation.integrations.hermes.operational_resolution import workstation_operational_resolution
from workstation.operational_capabilities import (
    CapabilityLifecycle, OperationalCapability, OperationalCapabilityRegistry,
)
from workstation.work_intent import prepare_turn_work


def admit(text, authority=IntentAuthority.CREATE_WORK):
    agent = SimpleNamespace(session_id="fresh-command", _conversation_root_id=lambda: "fresh-command",
        _interrupt_requested=False, _tool_guardrails=None, _work_capabilities={},
        _work_user_constraints={}, _current_provider_usage=None, _work_completed_mutations={},
        _work_mutation_evidence={}, _workstation_event_bus=None, valid_tool_names=set())
    envelope = MessageEnvelope(MessageOrigin.HUMAN, authority, agent.session_id, text)
    return agent, prepare_turn_work(agent, text, envelope)


def consult(agent):
    return workstation_operational_resolution(OperationalResolutionContext(
        agent=agent, session_id=agent.session_id,
        task_id=str(getattr(agent, "_canonical_work_task_id", "") or ""), turn_id="fresh-turn",
        user_message=agent._message_envelope.content, messages=[], api_call_count=0, iteration=0))


def test_fresh_trello_command_reaches_authority_router_without_prior_objective():
    agent, work = admit("Abre o Trello.")
    assert work.requires_task and work.requires_browser
    assert agent._canonical_work_task_id
    store = DurableTaskStore()
    try:
        assert store.get_connection().execute("SELECT COUNT(*) FROM work_plans").fetchone()[0] == 0
    finally:
        store.close()
    # A real registered candidate requires authority human ingress cannot grant.
    # The existing router must refuse it; recognition must never elevate permission.
    OperationalCapabilityRegistry().register(OperationalCapability(
        id="test.open_trello", name="open Trello", version="1",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="browser.open_site", target_family="native_browser",
            typed_postconditions=[EQ("url", "https://trello.com/")],
            effect_footprint=[SET("url", "https://trello.com/")],
            authority_required=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE,
                allowed_actions={"navigate"}, allowed_resources={"native_browser"}),
            verifier={"kind": "value", "evidence_strength": "E2"})))
    resolution = consult(agent)
    assert resolution is not None and resolution.outcome is OperationalOutcome.HANDOFF
    assert resolution.reason == "ASK_HUMAN"


def test_ambiguous_observed_uninstalled_and_cancelled_commands_do_not_dispatch():
    for text in ("Abre o Trello ou o Hyperframe.", "Não abre o Trello.",
                 "Como abre o Trello?", "Abre o Trello e apaga tudo."):
        agent, work = admit(text)
        assert not work.requires_task
        assert consult(agent) is None
    observed, work = admit("Abre o Trello.", IntentAuthority.OBSERVATION_ONLY)
    assert not work.requires_task and consult(observed) is None
    fresh, work = admit("Abre o Trello.")
    assert work.requires_task
    assert consult(fresh) is None, "missing installed capability falls back to reasoning"
    fresh._interrupt_requested = True
    assert consult(fresh) is None

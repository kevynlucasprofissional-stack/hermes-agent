"""The Workstation answer to the pre-reasoning operational resolution boundary.

``workstation.integrations.hermes.operational_resolution`` is the only thing that
decides whether a Hermes turn can be answered from the durable operational plane
instead of spending a reasoning round on the provider. Every test here drives it
through its real entry point with real durable state — no faked router, no faked
certificate, no patched decision — because the property under test is precisely
that the answer comes from the existing control plane and from nothing else.

What is pinned:

* the boundary binds to the canonical task the *turn* belongs to, re-verifying the
  same conditions turn admission used, and is inert when any of them moved;
* an intent is only honoured when it carries a provable goal, so an unstated
  ``TRUE`` goal can never close a turn;
* an unresolved effect of the same plan stops the boundary before dispatch, so it
  cannot become a second, silent retry lane;
* a route verdict is mapped without being upgraded: only a canonically
  ``VERIFIED`` result is a terminal ``EXECUTED``, and authority the task does not
  hold is a human decision rather than a fall-through.
"""

from __future__ import annotations

import json

import pytest
from types import SimpleNamespace

from agent.operational_resolution import OperationalOutcome, OperationalResolutionContext
from workstation.artifacts import ArtifactStore
from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.durable_tasks import DurableTaskStore
from workstation.integrations.hermes.operational_resolution import (
    workstation_operational_resolution,
)
from workstation.kanban import WorkstationKanbanBridge

SESSION = "session-resolution"

# A request the workstation promotes into canonical work: work_intent must see it
# as multi-step, and the envelope must carry CREATE_WORK authority for the same
# session and the same text, exactly as trusted ingress would.
MULTISTEP_PROMPT = "First extract the records then verify the result"


def canonical_task(bridge=None) -> str:
    """Create the canonical kanban task a turn would be admitted against."""
    bridge = bridge or WorkstationKanbanBridge()
    envelope = MessageEnvelope(
        MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, SESSION, MULTISTEP_PROMPT
    )
    task_id = bridge.promote_request_if_multistep(
        MULTISTEP_PROMPT, session_id=SESSION, envelope=envelope
    )
    assert task_id, "fixture requires a promotable multi-step request"
    return task_id


def bound_agent(task_id: str, *, body: str = MULTISTEP_PROMPT, session_id: str = SESSION):
    """The minimum a turn must leave on the agent for the boundary to bind.

    ``prepare_turn_work`` sets exactly these two attributes; every other attribute
    here is what scoped execution reads when the boundary dispatches.
    """
    return SimpleNamespace(
        session_id=session_id,
        _conversation_root_id=lambda: session_id,
        _canonical_work_task_id=task_id,
        _message_envelope=MessageEnvelope(
            MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, session_id, body
        ),
        _tool_guardrails=None,
        _work_capabilities={},
        _work_user_constraints={},
        _current_provider_usage=None,
        _work_completed_mutations={},
        _work_mutation_evidence={},
        _workstation_event_bus=None,
        _interrupt_requested=False,
        valid_tool_names=set(),
    )


def consult(agent, session_id: str = SESSION):
    """Ask the boundary, as the turn loop does once per iteration."""
    return workstation_operational_resolution(
        OperationalResolutionContext(
            agent=agent,
            session_id=session_id,
            task_id=str(getattr(agent, "_canonical_work_task_id", "") or ""),
            turn_id="turn-1",
            user_message="",
            messages=[],
            api_call_count=0,
            iteration=0,
        )
    )


def store_intent(intent: dict, task_id: str, *, semantic_state: dict | None = None, **extra):
    """Persist an established intent the way an admitted execution does.

    A prior execution writes one work plan whose ``objective_ref`` points at the
    sanitized request; this reproduces that record from the durable layer only.
    """
    store = DurableTaskStore()
    try:
        objective_ref = ArtifactStore().store(
            task_id,
            "objective.json",
            {**extra, "operation_intent": intent, "semantic_state": semantic_state or {}},
        ).ref
        plan = store.create_plan(
            task_id,
            "established intent",
            [{"id": 1}],
            session_id=SESSION,
            metadata={"objective_ref": objective_ref, "canonical_task_id": task_id},
        )
        return plan.id
    finally:
        store.close()


def eq(path: str, value):
    from workstation.control_plane.ir import EQ

    return EQ(path, value)


def exists(path: str):
    from workstation.control_plane.ir import EXISTS

    return EXISTS(path)


def created(path: str):
    from workstation.control_plane.ir import CREATE

    return CREATE(path)


def written(path: str, value) -> dict:
    from workstation.control_plane.ir import SET

    return SET(path, value)


def intent(goal, **extra) -> dict:
    """The persisted form of an intent, produced by the intent's own serializer."""
    from workstation.control_plane.intent import OperationIntent

    return OperationIntent(id="intent-resolution", target="record", goal=goal, **extra).to_dict()


def test_a_turn_with_no_canonical_task_reasons():
    """Without a bound task there is no identity to resolve against — reason."""
    agent = SimpleNamespace(session_id=SESSION, _conversation_root_id=lambda: SESSION)
    assert consult(agent) is None


def test_a_turn_bound_to_a_finished_task_is_not_acted_on():
    """A task that reached a terminal state between turns is not resumed."""
    task_id = canonical_task()
    store = DurableTaskStore()
    try:
        conn = store.get_connection()
        conn.execute("UPDATE tasks SET status='done' WHERE id=?", (task_id,))
        conn.commit()
    finally:
        store.close()
    store_intent(intent(eq("record.state", "ready")), task_id)

    assert consult(bound_agent(task_id)) is None


def test_a_task_rebound_to_a_different_request_is_not_acted_on():
    """The binding is to this turn's text; a superseded request must not resolve."""
    task_id = canonical_task()
    store_intent(intent(eq("record.state", "ready")), task_id)

    stale = bound_agent(task_id, body="A different request entirely")
    assert consult(stale) is None


def test_a_turn_from_another_session_is_not_acted_on():
    task_id = canonical_task()
    store_intent(intent(eq("record.state", "ready")), task_id)

    agent = bound_agent(task_id, session_id="other-session")
    assert consult(agent, session_id="other-session") is None


def test_a_turn_with_no_established_intent_reasons():
    """Nothing was ever executed here, so there is nothing to resolve."""
    task_id = canonical_task()
    assert consult(bound_agent(task_id)) is None


def test_an_intent_with_an_unstated_goal_is_not_an_intent():
    """``goal`` defaults to TRUE, which holds against the empty pre-reasoning state.

    Honouring it would close the turn on a goal nobody ever stated, so a goal that
    can be proven by saying nothing is refused before it is routed.
    """
    task_id = canonical_task()
    store_intent(
        {"id": "intent-phantom", "target": "record", "goal": {"type": "TRUE"}},
        task_id,
        semantic_state={"record": {"state": "ready"}},
    )

    assert consult(bound_agent(task_id)) is None


def test_an_already_satisfied_goal_resolves_without_reasoning():
    """A goal the recorded state already entails needs no dispatch and no model.

    This is also the guard against re-gating the boundary on
    ``durable_execution_active()``: that flag means "a compiled batch is running
    now" and is false on every pre-reasoning step by construction, so requiring it
    would silently make this module dead code. Nothing here is inside a batch.
    """
    task_id = canonical_task()
    store_intent(
        intent(eq("record.state", "ready")),
        task_id,
        semantic_state={"record": {"state": "ready"}},
    )

    resolution = consult(bound_agent(task_id))

    assert resolution is not None
    assert resolution.outcome is OperationalOutcome.SATISFIED
    assert resolution.reason == "SATISFIED"
    # Still a real answer: the turn loop refuses a terminal outcome with no text.
    assert "already satisfied" in resolution.final_response


def test_an_intent_with_no_certifiable_capability_reasons():
    """No promoted capability covers the goal, so the model must still be asked.

    Nothing may be dispatched on the way to that answer: an unmatched intent is a
    reasoning gap, not an execution opportunity.
    """
    task_id = canonical_task()
    plan_id = store_intent(
        intent(exists("record"), effect_budget=[created("record")]),
        task_id,
        semantic_state={"record": {"exists": False}},
    )
    before = _plan_ids()

    resolution = consult(bound_agent(task_id))

    assert resolution is None
    assert _plan_ids() == before, "an unresolved intent must not create an execution plan"
    assert DurableTaskStore().get_plan(plan_id) is not None


def test_authority_the_task_does_not_hold_goes_to_a_human():
    """A matching capability the task lacks authority for is a human decision.

    The route refuses to certify it; the boundary must report that refusal as a
    handoff rather than degrade it into another reasoning round that could try the
    same mutation again.
    """
    from workstation.control_plane.contract import CapabilityFormalContract
    from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
    from workstation.operational_capabilities import (
        CapabilityLifecycle,
        OperationalCapability,
        OperationalCapabilityRegistry,
    )

    task_id = canonical_task()
    registry = OperationalCapabilityRegistry()
    registry.register(OperationalCapability(
        id="cap.config.create", name="create config", version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="config.create", target_family="record",
            typed_postconditions=[exists("record")],
            effect_footprint=[created("record")],
            authority_required=AuthorityScope(
                level=AuthorityLevel.LOCAL_MUTATION,
                allowed_actions={"create"}, allowed_resources={"record"},
            ),
            verifier={"kind": "exists", "evidence_strength": "E2"},
        ),
    ))
    store_intent(
        intent(exists("record"), effect_budget=[created("record")]),
        task_id,
        semantic_state={"record": {"exists": False}},
    )
    before = _plan_ids()

    resolution = consult(bound_agent(task_id))

    assert resolution is not None
    assert resolution.outcome is OperationalOutcome.HANDOFF
    assert resolution.reason == "ASK_HUMAN"
    assert "human decision" in resolution.final_response
    assert _plan_ids() == before, "a refused route must not dispatch"


def test_an_effect_that_crossed_io_unproved_stops_the_boundary_before_dispatch():
    """The boundary never adds a second dispatch lane over an unresolved effect.

    The plan's own record says a mutation was dispatched and nothing proved what
    happened. Reconciling that is reasoning and human work, so the step must
    return to reasoning — and it must not route, let alone dispatch.
    """
    from workstation.control_plane.contract import CapabilityFormalContract
    from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
    from workstation.operational_capabilities import (
        CapabilityLifecycle,
        OperationalCapability,
        OperationalCapabilityRegistry,
    )

    task_id = canonical_task()
    registry = OperationalCapabilityRegistry()
    registry.register(OperationalCapability(
        id="cap.record.write", name="write record", version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="record.write", target_family="record",
            typed_postconditions=[eq("record.state", "written")],
            effect_footprint=[written("record.state", "written")],
            authority_required=AuthorityScope(
                level=AuthorityLevel.LOCAL_MUTATION,
                allowed_actions={"write"}, allowed_resources={"record"},
            ),
            verifier={"kind": "value", "evidence_strength": "E2"},
        ),
    ))
    plan_id = store_intent(
        intent(
            eq("record.state", "written"),
            effect_budget=[written("record.state", "written")],
        ),
        task_id,
        semantic_state={"record": {"state": "pending"}},
    )
    _dispatch_then_lose_the_result(plan_id)
    before = _plan_ids()

    resolution = consult(bound_agent(task_id))

    assert resolution is None
    assert _plan_ids() == before, "an unproved effect must not be dispatched again"


def _dispatch_then_lose_the_result(plan_id: str) -> None:
    """Record a mutation that crossed I/O whose result was never proved.

    Written through the durable store's own checkpoint API, which is the only
    thing that creates this state in production.
    """
    store = DurableTaskStore()
    try:
        item = store.get_work_items(plan_id)[0]
        store.update_item_checkpoint(
            item.id, "step_0_dispatch",
            metadata={"mutation_identity": {
                "operation_id": "op-unproved", "tool": "write_file",
                "effect": "MUTATION", "target_identifier": "record.json",
            }},
        )
    finally:
        store.close()


def _plan_ids() -> set:
    """Every work plan the canonical DB currently holds."""
    store = DurableTaskStore()
    try:
        conn = store.get_connection()
        return {row[0] for row in conn.execute("SELECT id FROM work_plans")}
    finally:
        store.close()

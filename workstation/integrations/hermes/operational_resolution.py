"""Answer a turn from the durable operational plane before a reasoning round is spent.

The upstream harness asks, once per loop iteration and before the provider call,
whether the turn is already advanced far enough that another reasoning round
would only rediscover what the operational plane knows
(``agent.operational_resolution``). This module is the Hermes Work answer.

It owns no decision of its own. Everything it does is read from, and dispatched
through, the control plane that already exists:

* the **intent** is not invented here — it is read from the objective a previous,
  admitted execution persisted in the existing ``DurableTaskStore`` /
  ``ArtifactStore`` pair (``plan.metadata['objective_ref']``), which is the same
  record ``TaskCompiler.resume`` replays;
* the **route** is ``CapabilityRouter``'s, reached through
  ``TaskCompiler._execute_route`` — certificate, authority narrowing, effect
  budget, uncertain-mutation guard and canonical verification all unchanged;
* the **execution** goes through ``workstation_durable_dispatch``, so it runs the
  real primitives through the agent's own tool executor under the agent's own
  guardrails, approval and route constraints;
* the **wait/handoff** outcomes are the ones the route itself produced
  (``AwaitCondition``, ``HumanDecision``).

What this module decides is only *whether there is enough trusted material to
ask*, and *which operational outcome the control plane's answer corresponds to*.
When there is not — no canonical task, no established intent, an intent with no
provable goal, or a route that yielded ``WAKE_LLM`` — it answers
``CONTINUE_REASONING``, which is the harness default and costs one reasoning
round rather than risking an unfounded action.

Two properties are load-bearing and are covered by tests in
``workstation/tests/test_operational_resolution_provider.py``:

* a terminal outcome is returned only with proof — ``VERIFIED`` plus
  ``accepted`` from the canonical verification, never from an acknowledgement;
* once a dispatch has been attempted, its failure is terminal (``WAIT`` or
  ``HANDOFF``), never a fall-through, so a reasoning round cannot dispatch the
  same mutation a second time.

A third property is the reason this module reads the durable ledger before it
routes: while the plan that owns the intent still has a mutation that crossed
I/O without a proved result, the boundary does not dispatch at all. It answers
``CONTINUE_REASONING``, because reconciling an unresolved effect is reasoning
and human work, and it must never become a second, silent retry lane.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from agent.operational_resolution import OperationalOutcome, OperationalResolution
from workstation.integrations.hermes.effect_authority import trusted_effect_authority_from_agent

logger = logging.getLogger(__name__)

# How many durable plans of one canonical task are inspected while looking for an
# already-established intent. Bounded so a long-lived task cannot turn the
# pre-reasoning path into an unbounded history read.
PLAN_SCAN_LIMIT = 20

# Route verdicts that dispatched (or composed) an effect under a valid certificate.
_EFFECT_DECISIONS = {"EXECUTE", "COMPOSE"}

# Composition that returned without crossing I/O: its inputs were never bound.
_UNBOUND_COMPOSITION = "composition_inputs_unbound"


def _canonical_task(agent: Any, session_id: str):
    """The trusted kanban task this turn belongs to, or ``None`` if not bindable.

    Re-verifies the conditions ``prepare_turn_work`` used when it accepted the
    task, so a task that was superseded, finished or re-bound to a different
    request between turns cannot be acted on.

    Deliberately not gated on ``durable_execution_active()``: that flag means "a
    compiled batch is running right now", and this boundary runs precisely when
    nothing is executing. Requiring it here would make the boundary dead code.
    """
    from hermes_cli import kanban_db
    from workstation.kanban import WorkstationKanbanBridge

    task_id = str(getattr(agent, "_canonical_work_task_id", None) or "")
    envelope = getattr(agent, "_message_envelope", None)
    if not task_id or envelope is None:
        return None

    bridge = WorkstationKanbanBridge()
    conn = bridge.get_connection()
    try:
        task = kanban_db.get_task(conn, task_id)
    finally:
        conn.close()
    if task is None or str(task.session_id) != str(session_id):
        return None
    if str(task.status) in {"done", "cancelled"}:
        return None
    if task.body != envelope.content:
        return None
    return task


def _provable_goal(intent_dict: Any) -> bool:
    """Whether an intent carries a goal that can actually be proven.

    ``OperationIntent`` defaults ``goal`` to ``TRUE``, which evaluates true
    against any state — including the empty state a pre-reasoning step has. An
    intent like that would route straight to ``SatisfiedDecision`` and close the
    turn on a goal nobody ever stated, so it is not treated as an intent.
    """
    if not isinstance(intent_dict, dict):
        return False
    goal = intent_dict.get("goal")
    if not isinstance(goal, dict):
        return False
    return str(goal.get("type", "")).strip().upper() not in {"", "TRUE"}


def _established_intent(store: Any, artifacts: Any, task: Any):
    """Find the most recent durable objective carrying an already-established intent.

    Returns ``(plan_row, objective)`` or ``(None, None)``. The scan is bounded by
    ``PLAN_SCAN_LIMIT`` so the number of plans read stays constant however long a
    task has lived.
    """
    # The store owns this connection (it may even be an externally supplied one);
    # reading through it must not close it, or the caller cannot read again.
    conn = store.get_connection()
    rows = [dict(row) for row in conn.execute(
        "SELECT * FROM work_plans ORDER BY created_at DESC LIMIT ?", (PLAN_SCAN_LIMIT,)
    )]
    for row in rows:
        try:
            metadata = json.loads(row.get("metadata") or "{}")
        except (TypeError, ValueError):
            continue
        if not isinstance(metadata, dict):
            continue
        if row.get("task_id") != task.id and metadata.get("canonical_task_id") != task.id:
            continue
        objective_ref = metadata.get("objective_ref")
        if not objective_ref:
            continue
        try:
            objective = artifacts.read_json(objective_ref)
        except Exception:
            logger.debug("operational resolution: unreadable objective %s", objective_ref, exc_info=True)
            continue
        if not isinstance(objective, dict) or not _provable_goal(objective.get("operation_intent")):
            continue
        return row, objective
    return None, None


def _verified(result: Any) -> bool:
    """Canonical verification only: an acknowledgement is not a verification."""
    if not isinstance(result, dict):
        return False
    verification = result.get("verification_result")
    if not isinstance(verification, dict):
        return False
    return (str(verification.get("status", "")).strip().upper() == "VERIFIED"
            and verification.get("accepted") is True)


def _text_for(outcome: OperationalOutcome, result: dict) -> str:
    """Compose the user-facing close-out. Names the capability and its durable result."""
    capability_id = str(result.get("capability_id") or "")
    if not capability_id:
        plan = result.get("plan")
        capability_id = " + ".join(str(c) for c in plan) if isinstance(plan, list) and plan else "capability"
    plan_id = str(result.get("plan_id") or "")
    results_ref = str(result.get("results_ref") or "")
    if outcome is OperationalOutcome.SATISFIED:
        return "That goal is already satisfied by the recorded verified state; no further action was taken."
    if outcome is OperationalOutcome.EXECUTED:
        lines = [f"Completed and independently verified via '{capability_id}'."]
        if plan_id:
            lines.append(f"Durable plan: {plan_id}.")
        if results_ref:
            lines.append(f"Verified result: {results_ref}.")
        return " ".join(lines)
    if outcome is OperationalOutcome.HANDOFF:
        # Say only what is known: the route refused to continue and a human owns the
        # next step. Whether an effect crossed I/O is recorded in the dispatch record
        # and the durable journal, not claimed here.
        reason = str(result.get("reason") or "human approval is required")
        return f"This step needs a human decision: {reason}."
    reason = str(result.get("reason") or "the effect could not be proven")
    return (
        f"Work was dispatched but not canonically verified ({reason}); the durable journal owns "
        "this step and it will not be retried blindly. Reconcile before continuing."
    )


def _outcome_for(result: Any):
    """Map a route verdict to an operational outcome. ``None`` means keep reasoning.

    The verdicts are the ones ``TaskCompiler._execute_route`` returns; the mapping
    adds no outcome of its own and never upgrades an unproved dispatch.
    """
    if not isinstance(result, dict):
        return None, None
    decision = str(result.get("routing_decision") or "")
    if decision == "SATISFIED":
        return OperationalOutcome.SATISFIED, _text_for(OperationalOutcome.SATISFIED, result)
    if decision in _EFFECT_DECISIONS:
        if result.get("success") is True and _verified(result):
            return OperationalOutcome.EXECUTED, _text_for(OperationalOutcome.EXECUTED, result)
        if str(result.get("reason") or "") == _UNBOUND_COMPOSITION:
            # The composition returned before its first step: nothing crossed I/O,
            # and binding the inputs is reasoning work, not a wait.
            return None, None
        return OperationalOutcome.WAIT, _text_for(OperationalOutcome.WAIT, result)
    if decision == "WAIT":
        condition = result.get("await_condition") or result.get("condition") or {}
        reason = result.get("reason") or "an awaited condition has not been met"
        detail = ""
        if isinstance(condition, dict) and condition.get("description"):
            detail = f" Waiting on: {condition['description']}."
        return OperationalOutcome.WAIT, f"Nothing to do yet — {reason}.{detail}"
    if decision == "ASK_HUMAN":
        # The route's own escalation: missing authority, a certified dispatch it
        # refused (including an uncertain mutation), or a verification it could not
        # accept. All three are human decisions, none of them is a retry.
        return OperationalOutcome.HANDOFF, _text_for(OperationalOutcome.HANDOFF, result)
    return None, None


def _dispatch_intent(agent: Any, context: Any, task: Any, objective: dict, runtime_state: dict):
    """Route and dispatch an already-established intent through the existing control plane."""
    from workstation.integrations.hermes.scoped_execution import (
        workstation_durable_dispatch,
        workstation_scoped_execution,
    )
    from workstation.task_compiler import TaskCompiler

    compiler = TaskCompiler(store=None, artifacts=None)
    try:
        # The current run, so lineage and the stale-run guard both refer to the
        # run this turn actually belongs to.
        compiler.canonical_run_id = (
            str(task.current_run_id) if task.current_run_id is not None else None
        )
        # Derive trusted effect authority from canonical ingress/session
        compiler.trusted_authority = trusted_effect_authority_from_agent(
            agent, str(context.session_id), task
        )
        dispatch = workstation_durable_dispatch(agent)
        with workstation_scoped_execution(agent, task.id, context.messages):
            return compiler.execute(
                {**objective, "runtime_state": runtime_state},
                task_id=task.id,
                session_id=str(context.session_id),
                dispatch=dispatch,
                canonical_task_id=task.id,
            )
    finally:
        compiler.store.close()


def workstation_operational_resolution(context: Any) -> Optional[OperationalResolution]:
    """Resolve one pre-reasoning step from durable Hermes Work state, or defer to reasoning.

    Reading failures defer to reasoning: nothing was dispatched, so a reasoning
    round is strictly safer. Failures after a dispatch was attempted never fall
    through — they resolve the step as ``WAIT``/``HANDOFF`` so the same mutation
    cannot be dispatched twice.
    """
    from workstation.artifacts import ArtifactStore
    from workstation.durable_tasks import DurableTaskStore

    agent = getattr(context, "agent", None)
    if agent is None:
        return None

    try:
        task = _canonical_task(agent, str(getattr(context, "session_id", "") or ""))
        if task is None:
            return None
        store = DurableTaskStore()
        try:
            plan_row, objective = _established_intent(store, ArtifactStore(), task)
            outstanding = store.outstanding_uncertain_mutations(plan_row["id"]) if plan_row else []
        finally:
            store.close()
        if plan_row is None:
            return None
    except Exception:
        logger.debug("operational resolution: no trustworthy intent to read", exc_info=True)
        return None

    # An effect of this plan crossed I/O and nothing proved what happened. The
    # record is handed to the route, which owns reconciliation gating and refuses
    # to dispatch on it; the boundary never adds a second, silent dispatch lane on
    # top of an unresolved one.
    runtime_state = {
        "outstanding_uncertain_mutations": [
            {
                "operation_id": record.get("operation_id"),
                "tool": record.get("tool"),
                "scope": record.get("scope"),
                "target_identifier": record.get("target_identifier"),
                "item_id": record.get("item_id"),
                "step": record.get("step"),
                "status": "uncertain",
            }
            for record in outstanding
        ]
    }

    try:
        result = _dispatch_intent(agent, context, task, objective, runtime_state)
    except InterruptedError:
        # The operator stopped the session; the ordinary interrupt path owns this
        # turn, and a terminal resolution here would race it.
        return None
    except Exception as exc:
        logger.warning(
            "Operational resolution dispatch failed (task=%s, plan=%s): %s",
            task.id, plan_row.get("id"), exc, exc_info=True,
        )
        return OperationalResolution(
            outcome=OperationalOutcome.WAIT,
            final_response=(
                "Dispatched work could not be completed or verified "
                f"({type(exc).__name__}); the durable journal owns this step and it will not be "
                "retried blindly. Reconcile before continuing."
            ),
            reason=f"dispatch_failed:{type(exc).__name__}",
            details={"task_id": task.id, "plan_id": plan_row.get("id")},
        )

    outcome, text = _outcome_for(result)
    if outcome is None:
        return None
    return OperationalResolution(
        outcome=outcome,
        final_response=text,
        reason=str((result or {}).get("routing_decision") or ""),
        details={
            "task_id": task.id,
            "plan_id": (result or {}).get("plan_id") or plan_row.get("id"),
            "routing_decision": (result or {}).get("routing_decision"),
            "capability_id": (result or {}).get("capability_id"),
            "certificate_hash": (result or {}).get("certificate_hash"),
            "verification_status": (result or {}).get("verification_result", {}).get("status"),
            "verification_accepted": (result or {}).get("verification_result", {}).get("accepted"),
            "dispatch_status": (result or {}).get("dispatch_record", {}).get("status"),
            "results_ref": (result or {}).get("results_ref"),
        },
    )

from __future__ import annotations

import json
from typing import Any, Optional
from agent.tool_batch_admission import (
    BatchAdmissionAction,
    BatchAdmissionDecision,
    BatchAdmissionResult,
)
from hermes_constants import get_hermes_home
from workstation.batch_detection import mutation_summary
from workstation.execution_policy import CompilationDecision, decisions_for_calls
from workstation.runtime import HumanHandoffManager
from workstation.task_compiler import discovery_guidance


def workstation_tool_batch_admission(
    agent: Any,
    tool_calls: list[Any],
    execution_context: Optional[dict[str, Any]] = None,
) -> Optional[BatchAdmissionResult]:
    """Inspect full assistant tool-call batch through Workstation execution policy."""
    if not tool_calls:
        return None

    import workstation.execution_policy as ep

    decisions = ep.decisions_for_calls(agent, tool_calls)
    has_intervention = any(
        d in {ep.CompilationDecision.REQUIRE_COMPILE, ep.CompilationDecision.REQUIRE_HUMAN}
        for d in decisions
    )
    if not has_intervention:
        return None

    agent._work_compile_replans = getattr(agent, "_work_compile_replans", 0) + 1

    root_id = getattr(agent, "_conversation_root_id", lambda: None)()
    session_id = root_id or getattr(agent, "session_id", "")
    task_id = getattr(agent, "_canonical_work_task_id", None) or session_id

    batch_decisions: list[BatchAdmissionDecision] = []

    for call, decision in zip(tool_calls, decisions):
        call_id = getattr(call, "id", "")
        fn_name = getattr(getattr(call, "function", None), "name", "")
        fn_args_raw = getattr(getattr(call, "function", None), "arguments", "{}")
        try:
            fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else (fn_args_raw or {})
        except Exception:
            fn_args = {}

        if decision == CompilationDecision.REQUIRE_HUMAN:
            handoff_mgr = HumanHandoffManager(
                get_hermes_home() / "workstation" / "human_handoffs.json"
            )
            from workstation.batch_detection import call_key
            # A human review belongs to a specific canonical TaskRun, not
            # merely to a chat/task and a repeatable tool argument shape.
            # A newer run must never inherit the old run's consumed approval.
            scope = {"operation_key": call_key(fn_name, fn_args)}
            run_id = getattr(agent, "_canonical_work_run_id", None)
            if run_id is not None:
                scope["run_id"] = str(run_id)
            handoff = handoff_mgr.request(
                task_id=task_id,
                session_id=session_id,
                reason="uncertain_mutation_requires_review",
                scope=scope,
                coalesce_waiting_run=True,
            )
            if handoff.status == "ready":
                handoff_mgr.consume(handoff.handoff_id)
            reviewed = handoff.status == "consumed"
            synthetic = json.dumps({
                "status": "human_review_completed" if reviewed else "handoff_requested",
                "handoff_id": handoff.handoff_id,
                "reason": ("Independent readback is required; human review alone cannot authorize replay of an uncertain external mutation"
                           if reviewed else "Human confirmation required before destructive mutation"),
                "tool": fn_name,
                "code": "uncertain_effect_requires_readback" if reviewed else "uncertain_mutation_requires_review",
            })
            batch_decisions.append(
                BatchAdmissionDecision(
                    call_id=call_id,
                    # A consumed review does not request another human popup.
                    # It is readback guidance, never permission to replay a write.
                    action=(BatchAdmissionAction.SYNTHETIC_RESULT if reviewed
                            else BatchAdmissionAction.HANDOFF),
                    synthetic_result=synthetic,
                    reason="readback_required" if reviewed else "require_human",
                )
            )
        elif decision == ep.CompilationDecision.REQUIRE_COMPILE:
            try:
                summary = mutation_summary(agent)
            except Exception:
                summary = {}
            try:
                guidance = discovery_guidance(agent)
            except Exception:
                guidance = {}
            synthetic = json.dumps({
                "status": "replan",
                "code": "durable_compile_required",
                "summary": "Repetitive work requires work_execute. Compile remaining items and verified steps once; these calls did not execute.",
                **guidance,
                **summary,
                "blocked_action": fn_name,
                "reason": "Use structured read/discovery tools to prepare the plan; arbitrary execution cannot assert read-only authority.",
            })
            batch_decisions.append(
                BatchAdmissionDecision(
                    call_id=call_id,
                    action=BatchAdmissionAction.SYNTHETIC_RESULT,
                    synthetic_result=synthetic,
                    reason="require_compile",
                )
            )
        else:
            batch_decisions.append(
                BatchAdmissionDecision(
                    call_id=call_id,
                    action=BatchAdmissionAction.EXECUTE,
                )
            )

    return BatchAdmissionResult(decisions=batch_decisions)

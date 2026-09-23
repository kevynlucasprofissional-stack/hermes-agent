from __future__ import annotations

import logging
from typing import Any
from agent.completion_admission import CompletionAdmissionResult
from workstation.kanban import WorkstationKanbanBridge
from workstation.procedure_trace import candidate_steps, trace_compatibility

logger = logging.getLogger(__name__)


def workstation_completion_admission(
    task_id: str,
    run_id: str,
    state: dict[str, Any],
) -> CompletionAdmissionResult:
    """Evaluate whether task completion can be admitted as canonical DONE."""
    session_id = state.get("session_id", "")
    turn_result = state.get("turn_result") or state

    try:
        bridge = WorkstationKanbanBridge()
        conn = bridge.get_connection()
        try:
            from hermes_cli import kanban_db
            task = kanban_db.get_task(conn, task_id)
            if task is None:
                # Not a kanban task or not found; admit completion
                return CompletionAdmissionResult(admitted=True)
            if session_id and task.session_id != session_id:
                return CompletionAdmissionResult(admitted=False, reason="session_id_mismatch")
        finally:
            conn.close()

        trace = state.get("_work_procedure_trace", [])
        truncated = state.get("_work_procedure_trace_truncated", False)
        repeatability = state.get("_work_repeatability_hint", False)

        if isinstance(turn_result, dict):
            turn_result["_adaptive_trace"] = [] if truncated else list(trace)
            turn_result["_adaptive_procedure_steps"] = [] if truncated else candidate_steps(trace)
            turn_result["_adaptive_repeatability_hint"] = repeatability
            turn_result["_adaptive_procedure_compatibility"] = trace_compatibility(trace)

        try:
            candidate = bridge.finalize_turn_candidate(
                task_id=task_id,
                session_id=session_id,
                turn_result=turn_result,
                expected_run_id=int(run_id) if run_id and str(run_id).isdigit() else None,
            )
        finally:
            if isinstance(turn_result, dict):
                for key in (
                    "_adaptive_trace",
                    "_adaptive_procedure_steps",
                    "_adaptive_repeatability_hint",
                    "_adaptive_procedure_compatibility",
                ):
                    turn_result.pop(key, None)

        if isinstance(candidate, dict):
            if candidate.get("status") == "verified_completed" or candidate.get("acceptance_approved") is True:
                return CompletionAdmissionResult(admitted=True, receipt=candidate)
            if candidate.get("status") in {"uncertain", "blocked", "failed"}:
                return CompletionAdmissionResult(
                    admitted=False,
                    reason=f"outcome_{candidate.get('status')}",
                    receipt=candidate,
                )
            return CompletionAdmissionResult(admitted=True, receipt=candidate)

        if hasattr(candidate, "verified"):
            if candidate.verified:
                return CompletionAdmissionResult(
                    admitted=True,
                    receipt={"status": "verified_completed", "run_id": str(candidate.run_id)},
                )
            reasons = candidate.pending_items or [f"outcome_{candidate.outcome_status}"]
            return CompletionAdmissionResult(
                admitted=False,
                reason="; ".join(str(r) for r in reasons),
                receipt={"pending": candidate.pending_items, "status": str(candidate.outcome_status)},
            )
    except Exception as exc:
        logger.warning("Workstation completion admission check failed: %s", exc)
        return CompletionAdmissionResult(
            admitted=False,
            reason=f"evaluation_error: {exc}",
            receipt={"task_id": task_id, "status": "uncertain", "acceptance_approved": False},
        )

    return CompletionAdmissionResult(admitted=True)

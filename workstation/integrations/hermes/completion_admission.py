from __future__ import annotations

import logging
from typing import Any
from agent.completion_admission import CompletionAdmissionResult
from workstation.kanban import WorkstationKanbanBridge
from workstation.procedure_trace import candidate_steps, trace_compatibility

logger = logging.getLogger(__name__)


def _committed_completion_receipt(task_id: str, run_id: str, session_id: str) -> dict | None:
    """Read back a genuine canonical DONE if optional post-commit work crashed.

    Never infer acceptance from a task status alone: check run, provenance,
    stored acceptance metadata and the canonical completed event.
    """
    if not session_id:
        return None
    from hermes_cli import kanban_db
    conn = WorkstationKanbanBridge().get_connection()
    try:
        task = kanban_db.get_task(conn, task_id)
        run = kanban_db.latest_run(conn, task_id)
        if (task is None or task.status != "done" or task.session_id != session_id
                or run is None or run.status != "done" or run.outcome != "completed"):
            return None
        metadata = run.metadata if isinstance(run.metadata, dict) else {}
        ws = metadata.get("workstation") or {}
        outcome = ws.get("outcome") or {}
        identity = str(run.id)
        if (ws.get("acceptance_approved") is not True
                or ws.get("session_id") != session_id
                or str(ws.get("run_id")) != identity
                or outcome.get("status") != "verified_completed"
                or outcome.get("task_id") != task_id
                or outcome.get("session_id") != session_id
                or str(outcome.get("run_id")) != identity
                or (run_id and str(run_id) != identity)):
            return None
        event = conn.execute(
            "SELECT 1 FROM task_events WHERE task_id=? AND run_id=? "
            "AND kind='completed' LIMIT 1", (task_id, run.id),
        ).fetchone()
        if event is None:
            return None
        return {"task_id": task_id, "run_id": identity,
                "status": "verified_completed", "acceptance_approved": True,
                "receipt_source": "canonical_committed_readback"}
    finally:
        conn.close()


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

        # A resumed parent may already have an authenticated, child-verified
        # source readback. Reconcile it BEFORE any attempt to rerun the effect.
        # This uses the original operation identity, not a synthetic tool ACK.
        if run_id and str(run_id).isdigit() and session_id:
            try:
                from workstation.evidence_recovery import try_recover_running_parent
                recovered = try_recover_running_parent(
                    task_id=task_id, session_id=session_id, run_id=int(run_id),
                    board=bridge.board,
                )
                if recovered is not None:
                    return CompletionAdmissionResult(admitted=True, receipt=recovered)
            except Exception:
                logger.warning("Read-only parent recovery unavailable", exc_info=True)

        trace = state.get("_work_procedure_trace", [])
        truncated = state.get("_work_procedure_trace_truncated", False)
        repeatability = state.get("_work_repeatability_hint", False)
        agent = state.get("agent")
        # Use the actual current-turn observer, not model-generated turn text.
        observed_tools = (getattr(agent, "_work_tool_observations", None) if agent is not None
                          else state.get("_work_tool_observations"))

        if isinstance(turn_result, dict):
            turn_result["_adaptive_trace"] = [] if truncated else list(trace)
            turn_result["_adaptive_procedure_steps"] = [] if truncated else candidate_steps(trace)
            turn_result["_adaptive_repeatability_hint"] = repeatability
            turn_result["_adaptive_procedure_compatibility"] = trace_compatibility(trace)

        native_contract = (getattr(agent, "_work_browser_readback_contract", None)
                           if agent is not None else None)
        if native_contract is None and agent is not None:
            from workstation.browser_operation_readback import bind_trusted_browser_expectation
            native_contract = bind_trusted_browser_expectation(
                getattr(agent, "_work_browser_readback_expectation", None),
                observed_tools, task_id=task_id, session_id=session_id,
                run_id=str(run_id or ""),
            )
        try:
            candidate = bridge.finalize_turn_candidate(
                task_id=task_id,
                session_id=session_id,
                turn_result=turn_result,
                expected_run_id=int(run_id) if run_id and str(run_id).isdigit() else None,
                observed_tools=observed_tools,
                trace_truncated=bool(truncated),
                native_browser_contract=native_contract,
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
            # A receipt is not completion proof unless its task, optional run
            # identity, verified status and explicit acceptance all agree.
            valid_identity = candidate.get("task_id") == task_id and (
                candidate.get("run_id") is None or str(candidate["run_id"]) == str(run_id)
            )
            if (
                valid_identity
                and candidate.get("status") == "verified_completed"
                and candidate.get("acceptance_approved") is True
            ):
                return CompletionAdmissionResult(admitted=True, receipt=candidate)
            return CompletionAdmissionResult(
                admitted=False,
                reason=f"outcome_{candidate.get('status') or 'unverified'}",
                receipt=candidate,
            )

        if hasattr(candidate, "verified"):
            # Legacy result objects are accepted only with matching run and
            # a positively verified outcome; no truthy flag may borrow a run.
            verified = (
                candidate.verified is True
                and str(getattr(candidate, "run_id", "")) == str(run_id)
                and getattr(candidate, "task_id", task_id) == task_id
            )
            if verified:
                return CompletionAdmissionResult(
                    admitted=True,
                    receipt={"status": "verified_completed", "run_id": str(candidate.run_id)},
                )
            reasons = getattr(candidate, "pending_items", None) or ["unverified_or_mismatched_run"]
            return CompletionAdmissionResult(
                admitted=False,
                reason="; ".join(str(r) for r in reasons),
                receipt={"pending": getattr(candidate, "pending_items", []), "status": str(getattr(candidate, "outcome_status", "unverified"))},
            )

        return CompletionAdmissionResult(
            admitted=False,
            reason="unrecognized_completion_receipt",
            receipt={"task_id": task_id, "status": "uncertain", "acceptance_approved": False},
        )
    except Exception as exc:
        logger.warning("Workstation completion admission check failed: %s", exc, exc_info=True)
        # The canonical transaction can have committed before an optional
        # experience/telemetry projection raised. Never report a false failure
        # or retry its effects: accept only a fresh, identity-bound DB readback.
        try:
            receipt = _committed_completion_receipt(
                task_id, str(run_id or ""), str(state.get("session_id") or ""),
            )
            if receipt is not None:
                return CompletionAdmissionResult(admitted=True, receipt=receipt)
        except Exception:
            logger.warning("Canonical post-commit reconciliation failed", exc_info=True)
        return CompletionAdmissionResult(
            admitted=False,
            reason=f"evaluation_error: {exc}",
            receipt={"task_id": task_id, "status": "uncertain", "acceptance_approved": False},
        )

    return CompletionAdmissionResult(admitted=False, reason="completion_unverified")

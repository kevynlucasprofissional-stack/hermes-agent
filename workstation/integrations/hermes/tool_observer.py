from __future__ import annotations

import logging
import hashlib
from typing import Any
from workstation.batch_detection import prepare_mutation, record_mutation
from workstation.task_compiler import capture_raw_result

logger = logging.getLogger(__name__)


def workstation_pre_dispatch_hook(
    tool_name: str,
    final_args: dict[str, Any],
    call_id: str,
    context: dict[str, Any],
) -> None:
    """Invoked at the authorized pre-effect boundary before real external I/O."""
    agent = context.get("agent")
    if agent is None:
        return
    try:
        prepare_mutation(agent, tool_name, final_args)
    except Exception as exc:
        logger.warning("Workstation prepare_mutation hook failed: %s", exc)
        raise


def workstation_raw_post_tool_observer(
    tool_name: str,
    final_args: dict[str, Any],
    call_id: str,
    raw_result: Any,
    duration: float,
    context: dict[str, Any],
) -> None:
    """Invoked immediately after tool handler returns, before any output truncation or spill."""
    agent = context.get("agent")
    if agent is not None:
        dispatched = context.get("dispatched", True)
        duration_ms = duration * 1000 if duration is not None else None
        from workstation.task_compiler import durable_execution_active
        if dispatched and durable_execution_active():
            from workstation.experience_compiler.progressive import capture_progressive
            from workstation.artifacts import ArtifactStore
            from tools.effects import tool_effect, READ_EFFECTS
            from workstation.routing import canonical_route_for_tool
            from agent.tool_guardrails import classify_tool_failure
            import json
            text = raw_result if isinstance(raw_result, str) else json.dumps(raw_result)
            failed = classify_tool_failure(tool_name, text)[0]
            t_id = getattr(agent, "_canonical_work_task_id", None)
            r_id = getattr(agent, "_canonical_work_run_id", None)
            op_id = getattr(agent, "_current_operation_id", None) or call_id
            c_route = canonical_route_for_tool(tool_name)
            outcome = "failed" if failed else "observed" if tool_effect(tool_name) in READ_EFFECTS else "uncertain"
            ref = capture_progressive(ArtifactStore(), task_id=t_id,
                run_id=r_id,
                operation_id=op_id,
                primitive=tool_name, route=c_route,
                outcome=outcome)
            if ref:
                try:
                    from workstation.experience_compiler.compilability_monitor import notify_online_compilability
                    from workstation.integrations.hermes.run_local_adoption import build_run_adoption_owner
                    notify_online_compilability(
                        ref=ref,
                        task_id=t_id,
                        run_id=r_id,
                        operation_id=op_id,
                        primitive=tool_name,
                        route=c_route,
                        outcome=outcome,
                        event_kind="tool_finished",
                        agent=agent,
                        owner=build_run_adoption_owner(agent),
                    )
                except Exception as mon_exc:
                    logger.debug("notify_online_compilability skipped: %s", mon_exc)
        try:
            record_mutation(
                agent,
                tool_name,
                final_args,
                raw_result,
                dispatched=dispatched,
                duration_ms=duration_ms,
            )
        except Exception as exc:
            logger.warning("Workstation record_mutation observer failed: %s", exc)

    try:
        capture_raw_result(call_id, raw_result)
    except Exception as exc:
        logger.warning("Workstation capture_raw_result observer failed: %s", exc)

    try:
        from workstation.telemetry import TelemetryEventType, emit_event
        from workstation.recipes import sanitize, canonical_bytes
        from workstation.routing import canonical_route_for_tool
        from agent.runtime_events import serialized_size

        dispatched = context.get("dispatched", True)
        emit_event(TelemetryEventType.TOOL_COMPLETED, source_owner="workstation.tool_observer",
            session_id=getattr(agent, "session_id", None),
            task_id=getattr(agent, "_canonical_work_task_id", None),
            run_id=getattr(agent, "_canonical_work_run_id", None), call_id=call_id,
            operation_id=getattr(agent, "_current_operation_id", None) or call_id,
            route=canonical_route_for_tool(tool_name), tool_calls=1 if dispatched else 0,
            status="observed" if dispatched else "denied", duration_ms=duration * 1000 if duration is not None else None,
            request_bytes=serialized_size(final_args), result_bytes=serialized_size(raw_result),
            dedupe_key=f"tool:{getattr(agent, 'session_id', None)}:{call_id}" if call_id else None,
            payload={"tool_name": tool_name,
                     "read_fingerprint": hashlib.sha256(canonical_bytes(sanitize(final_args))).hexdigest()
                     if tool_name in {"browser_snapshot", "browser_extract_items", "browser_console"} else None})
    except Exception:
        logger.debug("Tool telemetry unavailable", exc_info=True)

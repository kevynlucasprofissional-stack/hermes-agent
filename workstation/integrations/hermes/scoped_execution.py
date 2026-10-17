from __future__ import annotations

from contextlib import contextmanager
import json
from types import SimpleNamespace
from typing import Any, Optional

from workstation.task_compiler import (
    capture_raw_result,
    execution_context,
    operational_references,
    take_raw_result,
)


def workstation_durable_dispatch(agent: Any):
    """Build the deterministic durable dispatcher bound to one agent's session scope.

    This is the only way an operational capability may reach a real primitive:
    it runs the primitive through the agent's own tool executor, so approval,
    guardrails, interruption, route policy and raw-result capture all behave
    exactly as they do for a model-issued call. Callers that need to execute
    outside a model turn (the turn-boundary operational resolver) enter
    :func:`workstation_scoped_execution` around the call so the execution
    context — constraints, references, mutation evidence — is established too.
    """
    def _durable_dispatch(name: str, args: dict, task_id: str, call_id: str):
        if getattr(agent, "_interrupt_requested", False) or getattr(agent, "_tool_guardrail_halt_decision", None):
            raise InterruptedError("Durable work interrupted")
        if name not in getattr(agent, "valid_tool_names", set()):
            from tools.browser_workstation import _WORKSTATION_SCHEMA_TOOLS
            if name in _WORKSTATION_SCHEMA_TOOLS:
                import time
                from workstation.integrations.hermes.browser_controller import (
                    dispatch_workstation_browser_authoritative,
                )
                from workstation.integrations.hermes.tool_observer import (
                    workstation_pre_dispatch_hook,
                    workstation_raw_post_tool_observer,
                )
                session_id = str(
                    getattr(agent, "_conversation_root_id", lambda: None)()
                    or getattr(agent, "session_id", "")
                    or ""
                )
                run_id = getattr(agent, "_canonical_work_run_id", None)
                ctx = {"agent": agent, "dispatched": True}
                workstation_pre_dispatch_hook(name, args, call_id, ctx)
                start_t = time.monotonic()
                try:
                    res = dispatch_workstation_browser_authoritative(
                        name,
                        args,
                        task_id=task_id,
                        session_id=session_id,
                        run_id=str(run_id) if run_id is not None else None,
                        operation_id=call_id,
                    )
                finally:
                    duration = time.monotonic() - start_t
                workstation_raw_post_tool_observer(name, args, call_id, res, duration, ctx)
                capture_raw_result(call_id, res)
                return take_raw_result(call_id, res)

            from tools.tool_search import scoped_deferrable_names
            from model_tools import get_tool_definitions
            scoped = scoped_deferrable_names(
                get_tool_definitions(
                    enabled_toolsets=getattr(agent, "enabled_toolsets", None),
                    disabled_toolsets=getattr(agent, "disabled_toolsets", None),
                    quiet_mode=True,
                    skip_tool_search_assembly=True,
                )
            )
            if "tool_call" not in getattr(agent, "valid_tool_names", set()) or name not in scoped:
                raise ValueError(f"Tool outside session scope: {name}")
            args = {"name": name, "arguments": args}
            name = "tool_call"

        call = SimpleNamespace(
            id=call_id,
            type="function",
            function=SimpleNamespace(name=name, arguments=json.dumps(args)),
        )
        item_messages = []
        from agent.tool_executor import execute_tool_calls_sequential
        execute_tool_calls_sequential(
            agent,
            SimpleNamespace(tool_calls=[call]),
            item_messages,
            task_id,
            finalize=False,
        )
        results = [m for m in item_messages if m.get("role") == "tool"]
        if not results:
            raise RuntimeError("Scoped dispatcher produced no tool result")
        return take_raw_result(call_id, results[-1]["content"])

    return _durable_dispatch


@contextmanager
def workstation_scoped_execution(
    agent: Any,
    effective_task_id: str,
    messages: Optional[list] = None,
):
    """Workstation scoped execution manager.

    Binds deterministic durable dispatch, operational references, and execution context.
    On exit, attaches operational references to the last tool message.
    """
    _durable_dispatch = workstation_durable_dispatch(agent)

    root_id = getattr(agent, "_conversation_root_id", lambda: None)()
    session_id = root_id or getattr(agent, "session_id", "") or ""
    tool_guardrails = getattr(agent, "_tool_guardrails", None)
    mark_progress = tool_guardrails.mark_verified_progress if tool_guardrails else None

    boundary_callback = None
    if agent is not None:
        try:
            from workstation.integrations.hermes.run_local_adoption import (
                create_safe_item_boundary_callback,
            )
            boundary_callback = create_safe_item_boundary_callback(agent)
        except Exception:
            import logging
            logging.getLogger(__name__).debug("Failed to create safe item boundary callback", exc_info=True)

    work_capabilities = getattr(agent, "_work_capabilities", {})
    work_context = execution_context(
        _durable_dispatch,
        session_id,
        mark_progress,
        getattr(agent, "_work_user_constraints", {}),
        getattr(agent, "_current_provider_usage", None),
        getattr(agent, "_work_completed_mutations", {}),
        event_bus=getattr(agent, "_workstation_event_bus", None),
        canonical_task_id=getattr(agent, "_canonical_work_task_id", None),
        mutation_evidence=getattr(agent, "_work_mutation_evidence", {}),
        capabilities=work_capabilities,
        canonical_run_id=getattr(agent, "_canonical_work_run_id", None),
        safe_item_boundary=boundary_callback,
    )


    with work_context:
        try:
            yield
        finally:
            refs = operational_references()
            if refs and messages:
                for msg in reversed(messages):
                    if msg.get("role") == "tool":
                        msg["_hermes_operational_refs"] = refs
                        break

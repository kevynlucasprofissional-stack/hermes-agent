from __future__ import annotations

from contextlib import contextmanager
import json
from types import SimpleNamespace
from typing import Any, Optional

from workstation.task_compiler import (
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

from __future__ import annotations

import logging
from typing import Any, Optional

from agent.completion_admission import register_completion_admission_provider
from agent.operational_resolution import register_operational_resolution_provider
from agent.post_tool import register_raw_post_tool_observer
from agent.pre_dispatch import register_pre_authorized_dispatch_hook
from agent.tool_batch_admission import register_tool_batch_admission_provider
from agent.turn_admission import register_turn_admission_provider
from agent.scoped_execution import register_scoped_execution_provider
from agent.compression_admission import register_compression_bypass_provider
from agent.conversation_projection import register_conversation_projection_provider
from workstation.continuation import durable_compaction, project_for_provider
from workstation.integrations.hermes.browser_controller import (
    ensure_workstation_browser_controller,
    register_workstation_browser_capabilities,
)
from workstation.integrations.hermes.completion_admission import (
    workstation_completion_admission,
)
from workstation.integrations.hermes.operational_resolution import (
    workstation_operational_resolution,
)
from workstation.integrations.hermes.scoped_execution import (
    workstation_scoped_execution,
)
from workstation.integrations.hermes.tool_batch_admission import (
    workstation_tool_batch_admission,
)
from workstation.integrations.hermes.tool_observer import (
    workstation_pre_dispatch_hook,
    workstation_raw_post_tool_observer,
)
from workstation.integrations.hermes.turn_admission import workstation_turn_admission

from agent.task_completion_admission import (
    register_task_completion_admission_provider,
)
from workstation.integrations.hermes.task_completion_admission import (
    workstation_task_completion_admission,
)

logger = logging.getLogger(__name__)

_installed = False


def install_workstation_adapter(agent: Optional[Any] = None) -> None:
    """Install the Hermes First-Party Workstation Adapter into generic lifecycle contracts.
    
    Wires:
    1. Turn admission (canonical task/run/authority binding)
    2. Tool batch admission (Progressive Compilation / human handoff)
    3. Scoped execution (durable dispatch & execution context)
    4. Pre-authorized dispatch checkpoint (uncertain-before-I/O journal recording)
    5. Raw post-tool observation (recording mutations, results, procedure traces, learning)
    6. Completion admission (validating verification contracts before DONE)
    7. Browser capability registration
    8. Compression bypass (durable continuation compaction)
    9. Conversation wire projection (project_for_provider)
    10. Task completion admission (kanban completion verification)
    11. Operational resolution (answer a pre-reasoning step from durable work)
    """
    global _installed
    if _installed:
        return

    try:
        register_turn_admission_provider(workstation_turn_admission)
        register_tool_batch_admission_provider(workstation_tool_batch_admission)
        register_scoped_execution_provider(workstation_scoped_execution)
        register_pre_authorized_dispatch_hook(workstation_pre_dispatch_hook)
        register_raw_post_tool_observer(workstation_raw_post_tool_observer)
        register_completion_admission_provider(workstation_completion_admission)
        register_workstation_browser_capabilities()
        from tools.browser_extension_router import register_browser_controller_provider
        from tools.browser_workstation import workstation_schema_tools_for_current_session
        from tools.registry import register_schema_availability_provider
        register_browser_controller_provider(ensure_workstation_browser_controller)
        register_schema_availability_provider(workstation_schema_tools_for_current_session)
        register_compression_bypass_provider(durable_compaction)
        register_conversation_projection_provider(project_for_provider)
        register_task_completion_admission_provider(workstation_task_completion_admission)
        register_operational_resolution_provider(workstation_operational_resolution)

        from agent.execution_persistence import (
            ExecutionPersistenceDisposition,
            register_persistence_disposition_provider,
        )
        from workstation.task_compiler import durable_execution_active

        def _workstation_persistence_disposition():
            if durable_execution_active():
                return ExecutionPersistenceDisposition.OWNER_MANAGED
            return None

        register_persistence_disposition_provider(_workstation_persistence_disposition)

        from tools.file_tools import (
            register_uri_scheme_read_handler,
            register_file_read_projection,
        )

        def _artifact_read_handler(path: str, max_content_bytes: int = 100000, **kw):
            import json
            from workstation.artifacts import ArtifactStore
            return json.dumps(
                ArtifactStore().resolve_structured(path, max_content_bytes=max_content_bytes),
                ensure_ascii=False,
            )

        def _workstation_file_read_projection(task_id: str, resolved_str: str, offset: int, limit: int, result_dict: dict):
            import json
            from workstation.reference_plane import ReadCache
            from workstation.artifacts import ArtifactStore
            projection = ReadCache(ArtifactStore(), task_id).project(
                {"path": resolved_str, "offset": offset, "limit": limit}, result_dict
            )
            if projection.get("cache_hit"):
                return json.dumps(projection, ensure_ascii=False)
            return None

        register_uri_scheme_read_handler("artifact", _artifact_read_handler)
        register_file_read_projection(_workstation_file_read_projection)

        from tools.tool_search import register_tool_search_projection

        def _workstation_tool_search_projection(name: str, fn: dict, args: dict):
            from gateway.session_context import get_session_env
            if get_session_env("HERMES_SESSION_SOURCE", "") == "desktop":
                from workstation.reference_plane import schema_projection
                from workstation.artifacts import ArtifactStore
                from tools.registry import registry
                from hermes_constants import hermes_home_key
                session = get_session_env("HERMES_SESSION_ID", "")
                if session:
                    import hashlib
                    scope = hashlib.sha256(session.encode()).hexdigest()
                    projection = schema_projection(
                        ArtifactStore(),
                        f"schemas_{scope}",
                        fn,
                        f"{hermes_home_key()}:{registry._generation}",
                        full=args.get("full") is True,
                    )
                    if projection.get("cache_hit") and not args.get("full"):
                        import json
                        return json.dumps(projection, ensure_ascii=False)
            return None

        register_tool_search_projection(_workstation_tool_search_projection)

        from tools.close_preview_tool import register_preview_action_guard

        def _workstation_preview_guard(task_id: str, action: str):
            try:
                from workstation.browser_session import BrowserControlLeaseManager
                BrowserControlLeaseManager.get_instance().assert_action_allowed(task_id, action)
            except Exception as exc:
                if exc.__class__.__name__ == "HumanTakeoverActiveError":
                    return str(exc)
            return None

        register_preview_action_guard(_workstation_preview_guard)

        _installed = True
        logger.info("Hermes First-Party Workstation Adapter installed successfully.")
    except Exception as exc:
        logger.error("Failed to install Hermes First-Party Workstation Adapter: %s", exc)
        raise

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Optional
from pathlib import Path

from gateway.browser_control_broker import (
    BROWSER_CONTROL_CAPABILITIES,
    BrowserControlBroker,
    ControllerScope,
    get_registered_browser_control_capabilities,
    register_browser_control_capability,
)
from tools.browser_workstation import (
    call_workstation_browser,
    workstation_browser_enabled,
    workstation_controller_available,
    workstation_route_is_bound,
    workstation_routing_enabled,
)
from tools.browser_tool import _process_extracted_items_durably
from workstation.runtime import EvidenceStateStore, RuntimeEventBus, RuntimeEvent, ExecutionStatus

logger = logging.getLogger(__name__)

WORKSTATION_BROWSER_CAPABILITIES = (
    "browser_console",
    "browser_extract_items",
    "browser_get_images",
    "browser_vision",
    "browser_read_http",
    "browser_extension_load",
    "browser_extension_verify",
    "browser_extension_remove",
    "browser_extension_open_options",
)


def dispatch_workstation_browser_authoritative(
    action: str, args: Dict[str, Any], *, task_id: Optional[str] = None,
    session_id: Optional[str] = None, run_id: Optional[str] = None,
) -> Any:
    """Preserve Workstation route policy and human fencing behind the broker."""
    from workstation.task_compiler import active_constraints, durable_execution_active
    from workstation.routing import require_allowed_route
    constraints = active_constraints()
    if durable_execution_active() or constraints:
        require_allowed_route("native_browser", constraints)
    if task_id:
        from workstation.browser_session import BrowserControlLeaseManager
        BrowserControlLeaseManager.get_instance().assert_action_allowed(
            task_id, action, fence_token=args.get("fence_token"),
        )
    return call_workstation_browser(
        action, args, task_id=task_id, session_id=session_id, run_id=run_id,
    )


def register_workstation_browser_capabilities() -> None:
    """Register Workstation-specific browser capabilities with the generic broker registry."""
    for cap in WORKSTATION_BROWSER_CAPABILITIES:
        register_browser_control_capability(cap)


class WorkstationBrowserController:
    """Bridges the Workstation native Chromium/Electron browser into BrowserControlBroker.
    
    Preserves Workstation ownership:
    - Persistent WebContentsView
    - BrowserTask lifecycle and state persistence
    - Human takeover / release control
    - Background execution
    - Stale run fencing
    """
    def __init__(self, broker: Optional[BrowserControlBroker] = None):
        self.broker = broker
        self.scope: Optional[ControllerScope] = None
        # Initialize EvidenceStateStore and RuntimeEventBus for browser lifecycle events
        self._evidence_store = EvidenceStateStore(Path("workstation_browser_evidence.json"))
        self._event_bus = RuntimeEventBus()
        register_workstation_browser_capabilities()

    def _get_session_id(self) -> str:
        """Get the session ID from the controller scope or return a default."""
        if self.scope and self.scope.session_id:
            return self.scope.session_id
        # Fallback to a default session ID for browser controller operations
        return "browser-controller-session"

    def attach_to_broker(
        self,
        broker: BrowserControlBroker,
        *,
        principal_id: str = "workstation",
        profile_id: str = "default",
        session_id: str = "workstation_native",
        controller_id: str = "workstation_electron",
    ) -> ControllerScope:
        self.broker = broker
        all_caps = frozenset(
            BROWSER_CONTROL_CAPABILITIES
            | get_registered_browser_control_capabilities()
            | {"browser_select", "browser_wait"}
        )
        scope = ControllerScope(
            principal_id=principal_id,
            profile_id=profile_id,
            session_id=session_id,
            transport_family="workstation_native",
            controller_id=controller_id,
            browser_profile_id="workstation",
            capabilities=all_caps,
        )
        self.scope = scope
        broker.attach(scope, self._handle_command, owner=self)
        return scope

    def _handle_command(self, frame: dict) -> None:
        if not self.broker:
            return
        params = frame.get("params", frame)
        cmd_id = params.get("command_id", "")
        action = params.get("action", "")
        args = params.get("arguments", {})
        task_id = params.get("task_id")
        session_id = params.get("session_id")
        run_id = params.get("run_id")

        try:
            raw_result = dispatch_workstation_browser_authoritative(
                action,
                args,
                task_id=task_id,
                session_id=session_id,
                run_id=run_id,
            )

            # Process the result based on action type for Workstation-specific domain logic
            processed_result = self._process_browser_action_result(action, raw_result, args, {
                "task_id": task_id,
                "session_id": session_id,
                "run_id": run_id
            })

            try:
                res_obj = json.loads(processed_result) if isinstance(processed_result, str) else processed_result
            except Exception:
                res_obj = processed_result
            self.broker.complete(cmd_id, scope=self.scope, ok=True, result=res_obj)
        except Exception as exc:
            self.broker.complete(cmd_id, scope=self.scope, ok=False, result={"error": str(exc)})

    def create(self, task_id: str) -> Dict[str, Any]:
        """Create a new BrowserTask with one task-owned live page at most."""
        from tools.browser_workstation import workstation_routed_browser_handler
        result = workstation_routed_browser_handler(
            "browser_create",
            {"task_id": task_id},
            fallback=lambda: {"error": "workstation controller unavailable"},
            task_id=task_id,
        )

        # Parse the result
        parsed_result = json.loads(result) if isinstance(result, str) else result

        # Publish browser created event
        from workstation.runtime import RuntimeEvent
        self._event_bus.publish(RuntimeEvent(
            type="browser.created",
            task_id=task_id,
            session_id=self._get_session_id(),
            payload=parsed_result
        ))

        # Update evidence state store - create initial state
        from workstation.runtime import EvidenceState
        state = EvidenceState(task_id=task_id, session_id=self._get_session_id())
        state.add_evidence("browser_controller", "created", ttl_seconds=3600)
        self._evidence_store.upsert(state)

        return parsed_result

    def show(self, task_id: str, host: str, bounds: Dict[str, Any]) -> Dict[str, Any]:
        """Expose the task's existing page and park a previously visible BrowserTask when necessary."""
        from tools.browser_workstation import workstation_routed_browser_handler
        result = workstation_routed_browser_handler(
            "browser_show",
            {"task_id": task_id, "host": host, "bounds": bounds},
            fallback=lambda: {"error": "workstation controller unavailable"},
            task_id=task_id,
        )

        # Parse the result
        parsed_result = json.loads(result) if isinstance(result, str) else result

        # Publish browser shown event
        from workstation.runtime import RuntimeEvent
        self._event_bus.publish(RuntimeEvent(
            type="browser.shown",
            task_id=task_id,
            session_id=self._get_session_id(),
            payload={
                "host": host,
                "bounds": bounds,
                "result": parsed_result
            }
        ))

        # Update evidence state store
        from workstation.runtime import EvidenceState
        state = self._evidence_store.get(task_id)
        if state is None:
            state = EvidenceState(task_id=task_id, session_id=self._get_session_id())
        state.add_evidence("browser_controller", "shown", ttl_seconds=3600)
        state.add_evidence("browser_controller", "host", host, ttl_seconds=3600)
        state.add_evidence("browser_controller", "bounds", bounds, ttl_seconds=3600)
        self._evidence_store.upsert(state)

        return parsed_result

    def hide(self, task_id: str) -> Dict[str, Any]:
        """Remove the page from the visible host but keep page/task alive."""
        from tools.browser_workstation import workstation_routed_browser_handler
        result = workstation_routed_browser_handler(
            "browser_hide",
            {"task_id": task_id},
            fallback=lambda: {"error": "workstation controller unavailable"},
            task_id=task_id,
        )

        # Parse the result
        parsed_result = json.loads(result) if isinstance(result, str) else result

        # Publish browser hidden event
        from workstation.runtime import RuntimeEvent
        self._event_bus.publish(RuntimeEvent(
            type="browser.hidden",
            task_id=task_id,
            session_id=self._get_session_id(),
            payload=parsed_result
        ))

        # Update evidence state store
        from workstation.runtime import EvidenceState
        state = self._evidence_store.get(task_id)
        if state is None:
            state = EvidenceState(task_id=task_id, session_id=self._get_session_id())
        state.add_evidence("browser_controller", "hidden", ttl_seconds=3600)
        self._evidence_store.upsert(state)

        return parsed_result

    def park(self, task_id: str) -> Dict[str, Any]:
        """Keep the page alive in the background parking strategy and keep page/task state."""
        from tools.browser_workstation import workstation_routed_browser_handler
        result = workstation_routed_browser_handler(
            "browser_park",
            {"task_id": task_id},
            fallback=lambda: {"error": "workstation controller unavailable"},
            task_id=task_id,
        )

        # Parse the result
        parsed_result = json.loads(result) if isinstance(result, str) else result

        # Publish browser parked event
        from workstation.runtime import RuntimeEvent
        self._event_bus.publish(RuntimeEvent(
            type="browser.parked",
            task_id=task_id,
            session_id=self._get_session_id(),
            payload=parsed_result
        ))

        # Update evidence state store
        from workstation.runtime import EvidenceState
        state = self._evidence_store.get(task_id)
        if state is None:
            state = EvidenceState(task_id=task_id, session_id=self._get_session_id())
        state.add_evidence("browser_controller", "parked", ttl_seconds=3600)
        self._evidence_store.upsert(state)

        return parsed_result

    def destroy(self, task_id: str) -> Dict[str, Any]:
        """Explicit terminal operation: close/remove the owned live page and remove BrowserTask metadata."""
        from tools.browser_workstation import workstation_routed_browser_handler
        result = workstation_routed_browser_handler(
            "browser_destroy",
            {"task_id": task_id},
            fallback=lambda: {"error": "workstation controller unavailable"},
            task_id=task_id,
        )

        # Parse the result
        parsed_result = json.loads(result) if isinstance(result, str) else result

        # Publish browser destroyed event
        from workstation.runtime import RuntimeEvent
        self._event_bus.publish(RuntimeEvent(
            type="browser.destroyed",
            task_id=task_id,
            session_id=self._get_session_id(),
            payload=parsed_result
        ))

        # Update evidence state store
        from workstation.runtime import EvidenceState
        state = self._evidence_store.get(task_id)
        if state is None:
            state = EvidenceState(task_id=task_id, session_id=self._get_session_id())
        state.add_evidence("browser_controller", "destroyed", ttl_seconds=3600)
        # Mark as terminated
        state.status = ExecutionStatus.TERMINATED
        self._evidence_store.upsert(state)

        return parsed_result

    def _process_browser_action_result(self, action: str, raw_result: Any, args: dict, kw: dict) -> str:
        """Process browser action results with Workstation-specific domain logic.

        This moves Workstation-specific seam processing from the generic browser tool
        to the WorkstationBrowserController to close seams like SEAM-BROWSER-DOMAIN.
        """
        if action == "browser_extract_items":
            return _process_extracted_items_durably(raw_result, args, kw)
        # For other actions, return the raw result unchanged
        if isinstance(raw_result, str):
            return raw_result
        return json.dumps(raw_result, ensure_ascii=False)


_CONTROLLERS: Dict[tuple[str, str, str], WorkstationBrowserController] = {}


def ensure_workstation_browser_controller(
    *, action: str, session_id: Optional[str] = None, task_id: Optional[str] = None,
    principal_id: Optional[str] = None, transport_family: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Optional[Dict[str, str]]:
    """Attach the native Workstation controller for one server-owned session lane.

    An unbound task may retain the configured legacy fallback. Once a BrowserTask
    is bound—or fallback is disabled—the broker lane is installed even when the
    loopback runtime is currently offline, so controller loss fails closed.
    """
    if not workstation_browser_enabled() or not session_id:
        return None
    try:
        from gateway.session_context import get_session_env
        surface = str(get_session_env("HERMES_SESSION_SOURCE", "") or
                      get_session_env("HERMES_SESSION_PLATFORM", "")).lower()
    except Exception:
        surface = ""
    if surface != "desktop" and transport_family != "workstation_native":
        return None

    available = workstation_controller_available(force=workstation_route_is_bound(task_id, session_id))
    if not available and workstation_routing_enabled() and not workstation_route_is_bound(task_id, session_id):
        return None

    principal = principal_id or "workstation"
    transport = transport_family or "workstation_native"
    key = (principal, session_id, transport)
    controller = _CONTROLLERS.get(key)
    from gateway.browser_control_broker import get_browser_control_broker
    broker = get_browser_control_broker()
    if controller is None or controller.broker is not broker:
        controller = WorkstationBrowserController(broker)
        controller.attach_to_broker(
            broker, principal_id=principal, session_id=session_id,
            controller_id=f"workstation_electron:{session_id}",
        )
        if controller.scope is not None and controller.scope.transport_family != transport:
            broker.detach(controller.scope, owner=controller, notify_controller=False)
            controller.scope = ControllerScope(
                **{**controller.scope.__dict__, "transport_family": transport}
            )
            broker.attach(controller.scope, controller._handle_command, owner=controller)
        _CONTROLLERS[key] = controller
    return {
        "session_id": session_id, "task_id": task_id or "",
        "principal_id": principal, "transport_family": transport,
        "run_id": run_id or "",
    }

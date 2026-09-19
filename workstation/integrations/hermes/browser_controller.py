from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Optional

from gateway.browser_control_broker import (
    BrowserControlBroker,
    ControllerScope,
    register_browser_control_capability,
)
from tools.browser_workstation import (
    call_workstation_browser,
    workstation_browser_enabled,
    workstation_controller_available,
)

logger = logging.getLogger(__name__)

WORKSTATION_BROWSER_CAPABILITIES = (
    "browser_console",
    "browser_extract_items",
    "browser_get_images",
    "browser_vision",
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
        register_workstation_browser_capabilities()

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
        all_caps = frozenset([
            "browser_navigate",
            "browser_click",
            "browser_type",
            "browser_snapshot",
            "browser_screenshot",
            "browser_scroll",
            "browser_select",
            "browser_wait",
            *WORKSTATION_BROWSER_CAPABILITIES,
        ])
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
        cmd_id = frame.get("command_id", "")
        action = frame.get("action", "")
        args = frame.get("args", {})
        task_id = frame.get("task_id")
        session_id = frame.get("session_id")
        run_id = frame.get("run_id")

        try:
            raw_result = call_workstation_browser(
                action,
                args,
                task_id=task_id,
                session_id=session_id,
                run_id=run_id,
            )
            try:
                res_obj = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
            except Exception:
                res_obj = raw_result
            self.broker.complete(cmd_id, ok=True, result=res_obj)
        except Exception as exc:
            self.broker.complete(cmd_id, ok=False, result={"error": str(exc)})

"""Focus-independent native BrowserTask file selection for Desktop sessions.

Electron enforces explicit per-task upload grants, origin, realpath and file size.
This surface never falls back to the system clipboard or an external browser.
"""

from __future__ import annotations

import json
from typing import Any

from tools.effects import ToolEffect
from tools.registry import registry


def _native_upload(**kwargs: Any) -> str:
    from tools.browser_workstation import (
        WorkstationBrowserUnavailable, workstation_routed_browser_handler,
    )

    def no_external_browser() -> None:
        raise WorkstationBrowserUnavailable(
            "Native Workstation Browser required for file upload; no fallback."
        )

    return workstation_routed_browser_handler(
        fallback=no_external_browser, **kwargs,
    )


def handle_browser_file_upload(args: dict[str, Any], **kw: Any) -> str:
    from tools.browser_workstation import workstation_desktop_session

    if not workstation_desktop_session() or not kw.get("session_id"):
        return json.dumps({"success": False, "error_code": "DESKTOP_SESSION_REQUIRED"})

    if not isinstance(args, dict) or set(args) - {"files", "selector"}:
        return json.dumps({"success": False, "error_code": "INVALID_ARGUMENT"})

    files = args.get("files")
    selector = args.get("selector", 'input[type="file"]')
    if (not isinstance(files, list) or not 1 <= len(files) <= 10
            or any(not isinstance(f, str) or not f.strip() for f in files)
            or not isinstance(selector, str) or not 1 <= len(selector) <= 512):
        return json.dumps({"success": False, "error_code": "INVALID_ARGUMENT"})

    return _native_upload(
        action="browser_file_upload",
        args={"files": files, "selector": selector},
        task_id=kw.get("task_id"),
        session_id=kw["session_id"],
        run_id=kw.get("run_id"),
        operation_id=kw.get("tool_call_id"),
    )


def _check() -> bool:
    from tools.browser_workstation import workstation_browser_enabled

    return workstation_browser_enabled()


registry.register(
    name="browser_file_upload",
    toolset="desktop_ui",
    schema={
        "name": "browser_file_upload",
        "description": (
            "Select local files in the current task-owned native Electron Browser "
            "without Windows keyboard focus, clipboard, file picker, or foreground window. "
            "Requires a live Desktop session, BrowserTask authority, and an operator-configured "
            "task/session/run-scoped upload_grant authorizing the file directory and page origin. "
            "Selecting is NOT sending: inspect the preview, send separately, and verify the result. "
            "On uncertain or reconciliation_required result, stop and reconcile; never blindly retry."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1, "maxItems": 10,
                    "description": "Absolute local file paths inside the pre-authorized upload roots.",
                },
                "selector": {
                    "type": "string",
                    "description": (
                        "CSS selector matching exactly one HTML file input in the current "
                        "main frame; default: input[type=file]. For pages with multiple "
                        "inputs, inspect DOM and supply a specific selector."
                    ),
                },
            },
            "required": ["files"],
            "additionalProperties": False,
        },
    },
    handler=handle_browser_file_upload,
    check_fn=_check,
    effect=ToolEffect.MUTATION,
)

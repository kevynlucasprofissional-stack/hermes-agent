"""Open the internal React Creative Workstation through the existing Desktop GUI event bridge.

The GUI gateway scopes this event to the window owning the active turn.
No BrowserTask, TaskRun, external URL or loopback studio is created.
"""
from tools import desktop_ui
from tools.effects import ToolEffect
from tools.registry import registry


def open_creative_workstation() -> str:
    """Request to show/focus the internal Creative Workstation app."""
    return desktop_ui.emit_or_error(
        "creative.open",
        {},
        "Failed to open the Creative Workstation: ",
        "The Creative Workstation is only available in the Hermes desktop app.",
        {"success": True, "status": "requested", "app": "creative-workstation"},
    )


registry.register(
    name="open_creative_workstation",
    toolset="desktop_ui",
    schema={
        "name": "open_creative_workstation",
        "description": (
            "Open or focus the internal React Creative Workstation inside the Hermes "
            "Desktop Workstation Hub. Use directly for requests like "
            "'Abra o Creative Workstation', 'open the Creative editor', or "
            "'show the creative workspace'. No file search, URL navigation, "
            "HyperFrames, browser_creative_studio_open, or BrowserTask is required. "
            "A successful result acknowledges the UI request, not a completed edit."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    handler=lambda args, **_kw: open_creative_workstation(),
    effect=ToolEffect.INTERACTIVE,
    emoji="🎨",
)

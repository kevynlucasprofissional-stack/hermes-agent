"""Close the Hermes desktop GUI's preview pane, or one tab (``preview.close``).
Registration lives in `desktop_preview`. The renderer drops the matching tab — or
the whole pane when no url is given — only for the window that asked."""

from tools import desktop_ui
from tools.registry import tool_error
from tools.open_preview_tool import _normalize_target

_PREVIEW_ACTION_GUARDS: list = []


def register_preview_action_guard(guard) -> None:
    if guard not in _PREVIEW_ACTION_GUARDS:
        _PREVIEW_ACTION_GUARDS.append(guard)


def close_preview_tool(url: str = "", task_id: str = "") -> str:
    """Ask the desktop GUI to close the preview pane, or the tab for ``url``."""
    target = _normalize_target(url or "")
    if task_id:
        for guard in _PREVIEW_ACTION_GUARDS:
            blocked = guard(task_id, "close_preview")
            if blocked is not None:
                return tool_error(blocked)
    return desktop_ui.emit_or_error(
        "preview.close", {"url": target}, "Failed to close the preview pane: ",
        "The preview pane is only available in the Hermes desktop app.", {"success": True, "url": target},
    )

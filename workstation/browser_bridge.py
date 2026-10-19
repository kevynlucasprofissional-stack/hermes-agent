"""Browser to Workspace / Artifact Store structured bridge.

Extracts DOM structures, JavaScript variables (e.g. window.__sc, search results),
and page captures directly into the filesystem or ArtifactStore without passing
through base64, chat context, or simulated browser downloads.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Callable, Optional

from workstation.artifacts import ArtifactRef, ArtifactStore

logger = logging.getLogger(__name__)


class BridgeSecurityError(PermissionError):
    """Raised when an extraction attempts to write outside permitted directories."""


def _validate_safe_destination(dest_path: Path, allowed_roots: Optional[list[Path]] = None) -> Path:
    """Validate that dest_path resolves inside one of the allowed roots.

    Uses ``Path.is_relative_to`` (Python 3.9+) instead of textual prefix matching
    to prevent sibling-directory escapes such as ``/workspace-ok2`` passing a check
    against ``/workspace-ok``. The resolved path is returned so callers can write
    to the validated location rather than re-resolving from an untrusted input.
    """
    resolved = dest_path.resolve()
    if allowed_roots:
        roots = [Path(root).resolve() for root in allowed_roots]
        if not any(resolved == root or resolved.is_relative_to(root) for root in roots):
            raise BridgeSecurityError(
                f"Destination {resolved} is outside allowed workspaces: {[str(r) for r in roots]}"
            )
    return resolved


def browser_save_json(
    evaluate_fn: Callable[[str], Any],
    expression: str,
    destination_path: str | Path,
    *,
    allowed_roots: Optional[list[Path]] = None,
) -> dict[str, Any]:
    """Evaluate JS expression and save the resulting JSON directly to destination_path."""
    wrap_script = f"""
    (() => {{
        try {{
            const res = ({expression});
            return JSON.stringify({{ success: true, data: res }});
        }} catch (err) {{
            return JSON.stringify({{ success: false, error: String(err) }});
        }}
    }})()
    """
    raw = evaluate_fn(wrap_script)
    parsed: dict[str, Any] = {}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception as exc:
            parsed = {"success": False, "error": f"Failed decoding evaluation result: {exc}"}
    elif isinstance(raw, dict):
        parsed = raw
    else:
        parsed = {"success": True, "data": raw}

    if not parsed.get("success", True) or "error" in parsed:
        error_msg = parsed.get("error", "Evaluation returned error")
        raise RuntimeError(f"Browser evaluation failed: {error_msg}")

    data = parsed.get("data")
    # Use the validated/resolved path for writing to prevent TOCTOU issues
    # where the original destination_path could differ from what was checked.
    dest = _validate_safe_destination(Path(destination_path), allowed_roots)
    dest.parent.mkdir(parents=True, exist_ok=True)

    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    dest.write_bytes(json_bytes)

    return {
        "success": True,
        "destination": str(dest),
        "size_bytes": len(json_bytes),
    }


def browser_capture_to_artifact(
    evaluate_fn: Callable[[str], Any],
    expression: str,
    task_id: str,
    artifact_name: str,
    *,
    artifact_store: Optional[ArtifactStore] = None,
    schema: Optional[str] = None,
) -> ArtifactRef:
    """Evaluate JS in page and persist result directly into ArtifactStore."""
    store = artifact_store or ArtifactStore()
    wrap_script = f"""
    (() => {{
        try {{
            const val = ({expression});
            return JSON.stringify(val);
        }} catch (err) {{
            return JSON.stringify({{ error: String(err) }});
        }}
    }})()
    """
    raw = evaluate_fn(wrap_script)
    parsed: Any
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
    else:
        parsed = raw

    return store.store(
        task_id=task_id,
        name=artifact_name,
        content=parsed,
        schema=schema,
    )

"""B0.1 — Path containment tests for browser_bridge._validate_safe_destination.

RED/GREEN suite covering:
- Valid destination inside an allowed root.
- Sibling directory with a matching prefix (e.g. workspace-ok2 vs workspace-ok).
- Symlink that resolves outside the allowed root.
- Non-existent destination whose parent is inside an allowed root.
- Existing file destination inside an allowed root.
- No allowed_roots supplied (validation skipped, path still resolved).
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from workstation.browser_bridge import BridgeSecurityError, _validate_safe_destination


@pytest.fixture()
def workspace_root(tmp_path: Path) -> Path:
    """Create a temporary allowed workspace root."""
    root = tmp_path / "workspace-ok"
    root.mkdir()
    return root


def test_valid_destination_inside_root(workspace_root: Path) -> None:
    dest = workspace_root / "subdir" / "output.json"
    result = _validate_safe_destination(dest, allowed_roots=[workspace_root])
    assert result == dest.resolve()
    assert result.is_relative_to(workspace_root.resolve())


def test_sibling_prefix_directory_rejected(workspace_root: Path) -> None:
    """A sibling directory whose name starts with the root name must be rejected.

    This is the exact regression that motivated switching from textual
    ``startswith`` to ``Path.is_relative_to``.
    """
    sibling = workspace_root.parent / "workspace-ok2"
    sibling.mkdir(exist_ok=True)
    escape_dest = sibling / "stolen.json"

    with pytest.raises(BridgeSecurityError, match="outside allowed workspaces"):
        _validate_safe_destination(escape_dest, allowed_roots=[workspace_root])


def test_symlink_resolving_outside_root_rejected(workspace_root: Path, tmp_path: Path) -> None:
    """Symlinks that resolve outside the allowed root must be rejected."""
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    real_target = outside_dir / "secret.json"
    real_target.write_text("{}")

    link_path = workspace_root / "innocent-link.json"
    try:
        link_path.symlink_to(real_target)
    except OSError as exc:
        pytest.skip(f"symlinks not supported on this platform: {exc}")

    with pytest.raises(BridgeSecurityError, match="outside allowed workspaces"):
        _validate_safe_destination(link_path, allowed_roots=[workspace_root])


def test_nonexistent_destination_with_valid_parent_accepted(workspace_root: Path) -> None:
    """A non-existent file whose parent resolves inside the root is accepted.

    The caller is responsible for creating parent directories after validation.
    """
    dest = workspace_root / "new-dir" / "future.json"
    assert not dest.exists()

    result = _validate_safe_destination(dest, allowed_roots=[workspace_root])
    assert result == dest.resolve()


def test_existing_file_inside_root_accepted(workspace_root: Path) -> None:
    existing = workspace_root / "already-here.json"
    existing.write_text('{"ok": true}')

    result = _validate_safe_destination(existing, allowed_roots=[workspace_root])
    assert result == existing.resolve()


def test_no_allowed_roots_returns_resolved_path(tmp_path: Path) -> None:
    """When no roots are configured the function still resolves the path."""
    dest = tmp_path / "anywhere" / "file.json"
    result = _validate_safe_destination(dest, allowed_roots=None)
    assert result == dest.resolve()


def test_empty_allowed_roots_list_accepts_any_path(tmp_path: Path) -> None:
    """An empty list behaves like no restriction (no roots to check against)."""
    dest = tmp_path / "free.json"
    result = _validate_safe_destination(dest, allowed_roots=[])
    assert result == dest.resolve()


def test_destination_equal_to_root_accepted(workspace_root: Path) -> None:
    """The root itself is a valid destination (edge case for is_relative_to)."""
    result = _validate_safe_destination(workspace_root, allowed_roots=[workspace_root])
    assert result == workspace_root.resolve()
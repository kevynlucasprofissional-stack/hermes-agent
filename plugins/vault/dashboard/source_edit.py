from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from workstation.vault import VaultManager


class VaultEditConflict(Exception):
    """The note changed after it was opened in the editor."""


def read_note_source(manager: VaultManager, note: dict[str, Any]) -> dict[str, Any]:
    """Return exact UTF-8 Markdown source, including original line endings."""
    with manager._lock:
        path = manager._safe_indexed_path(note["path"])
        raw = path.read_bytes()
        return {**note, "content": raw.decode("utf-8"), "revision": hashlib.sha256(raw).hexdigest()}


def update_note_source(
    manager: VaultManager, rel_path: str, content: str, expected_revision: str
) -> dict[str, Any]:
    """Replace existing Markdown only if its on-disk revision is unchanged."""
    if not isinstance(expected_revision, str) or len(expected_revision) != 64:
        raise ValueError("A valid revision is required to update a note")
    if not isinstance(content, str):
        raise ValueError("Markdown content must be text")
    parts = manager._relative_parts(rel_path, field_name="note path")
    if not parts[-1].lower().endswith(".md"):
        raise ValueError("Only Markdown notes may be edited")

    with manager._lock:
        title = manager.index.path_to_title.get("/".join(parts))
        indexed = manager.index.notes.get(title) if title else None
        if not indexed or indexed.rel_path != "/".join(parts):
            raise ValueError("Note not found or filename is ambiguous in the Vault index")
        path = manager._safe_indexed_path(indexed.path)
        if path != manager._assert_contained(manager.vault_dir.joinpath(*parts), must_exist=True):
            raise ValueError("Note path changed while editing")
        current = path.read_bytes()
        if hashlib.sha256(current).hexdigest() != expected_revision:
            raise VaultEditConflict("Note changed on disk; reload before saving")
        # Titles remain globally unique in the current index; refuse a collision.
        from workstation.vault import canonicalize_title, parse_frontmatter_and_content

        frontmatter, _ = parse_frontmatter_and_content(content)
        new_title = frontmatter.get("title") or canonicalize_title(path.name)
        if not isinstance(new_title, str) or not new_title.strip():
            raise ValueError("Invalid note title in frontmatter")
        occupant = manager.index.notes.get(new_title)
        if occupant is not None and occupant.rel_path != "/".join(parts):
            raise ValueError("Another Markdown file already uses this title")
        manager._atomic_write(path, content)
        manager._scan_locked()
        refreshed = manager.get_note("/".join(parts))
        if refreshed is None or refreshed["rel_path"] != "/".join(parts):
            raise ValueError("Updated note could not be resolved in Vault index")
        return read_note_source(manager, refreshed)

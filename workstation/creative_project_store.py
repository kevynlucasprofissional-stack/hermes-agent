"""Portable Creative source revisions, independent of execution authority/state."""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from hermes_constants import get_hermes_home


@dataclass(frozen=True)
class CreativeProjectRevision:
    project_id: str
    revision_id: str
    manifest_path: Path
    source_path: Path
    source_sha256: str
    parent_revision: str | None
    operation_id: str


def _identifier(value: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[a-f0-9]{32}", value) is None:
        raise ValueError("Invalid Creative project/revision identifier")
    return value


def _root() -> Path:
    home = Path(get_hermes_home()).resolve()
    root = home / "workstation" / "creative" / "projects"
    if not root.resolve().is_relative_to(home):
        raise ValueError("Creative projects escape the active profile")
    return root


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False,
                       separators=(",", ":")) + "\n").encode("utf-8")


def _source_bytes(source: dict) -> bytes:
    if not isinstance(source, dict):
        raise ValueError("Creative source must be an object")
    data = _json_bytes(source)
    if len(data) > 262_144:
        raise ValueError("Creative source exceeds size budget")
    return data


def load_creative_revision(project_id: str, revision_id: str) -> CreativeProjectRevision:
    """Read only within the current profile; refuse edited or redirected revisions."""
    root = _root()
    directory = root / _identifier(project_id) / "revisions" / _identifier(revision_id)
    if directory.resolve() != directory or not directory.is_dir():
        raise ValueError("Creative revision is missing or redirected")
    manifest_path, source_path = directory / "manifest.json", directory / "source.creative.json"
    for path in (manifest_path, source_path):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 262_144:
            raise ValueError("Creative revision file is missing, redirected or oversized")
    manifest = json.loads(manifest_path.read_bytes())
    expected = {"schema_version", "project_id", "revision_id", "parent_revision", "engine", "source", "operation_id"}
    if (not isinstance(manifest, dict) or set(manifest) != expected
            or type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1
            or manifest["project_id"] != project_id or manifest["revision_id"] != revision_id
            or manifest["engine"] != "electron-svg"):
        raise ValueError("Invalid Creative manifest")
    parent = manifest["parent_revision"]
    operation_id = _identifier(manifest["operation_id"])
    if parent is not None:
        _identifier(parent)
    source = manifest["source"]
    if (not isinstance(source, dict) or set(source) != {"path", "sha256"}
            or source["path"] != "source.creative.json"):
        raise ValueError("Invalid Creative source reference")
    data = source_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if source["sha256"] != digest:
        raise ValueError("Creative source was changed outside its recorded revision")
    if not isinstance(json.loads(data), dict):
        raise ValueError("Invalid Creative source")
    return CreativeProjectRevision(project_id, revision_id, manifest_path, source_path, digest, parent, operation_id)


def save_creative_revision(source: dict, *, project_id: str | None = None,
                           parent_revision: str | None = None,
                           operation_id: str | None = None) -> CreativeProjectRevision:
    """Append immutable files; never overwrite a human-edited source or a head pointer.

    Callers must perform canonical TaskRun admission before invoking this file store.
    This function supplies persistence, never approval or execution certification.
    """
    data = _source_bytes(source)
    operation_id = _identifier(operation_id) if operation_id is not None else uuid.uuid4().hex
    if (project_id is None) != (parent_revision is None):
        raise ValueError("Existing projects require an explicit parent revision")
    if project_id is not None:
        load_creative_revision(project_id, parent_revision)
    else:
        project_id = uuid.uuid4().hex
    revision_id = uuid.uuid4().hex
    root = _root()
    directory = root / project_id / "revisions" / revision_id
    if directory.parent.resolve() != directory.parent:
        raise ValueError("Creative project directory was redirected")
    directory.parent.mkdir(parents=True, exist_ok=True)
    if directory.parent.resolve() != directory.parent:
        raise ValueError("Creative project directory was redirected")
    directory.mkdir()
    digest = hashlib.sha256(data).hexdigest()
    manifest = {"schema_version": 1, "project_id": project_id, "revision_id": revision_id,
                "operation_id": operation_id,
                "parent_revision": parent_revision, "engine": "electron-svg",
                "source": {"path": "source.creative.json", "sha256": digest}}
    with (directory / "source.creative.json").open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    # Manifest is the commit marker: incomplete source-only revisions cannot reopen.
    with (directory / "manifest.json").open("xb") as stream:
        stream.write(_json_bytes(manifest))
        stream.flush()
        os.fsync(stream.fileno())
    return load_creative_revision(project_id, revision_id)

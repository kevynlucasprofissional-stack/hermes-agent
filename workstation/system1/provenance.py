"""Provenance diagnosis and verification for Laya System-1 runtime."""

from __future__ import annotations

import json
import hashlib
from importlib import metadata
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SUBTREE_DIR = REPO_ROOT / "workstation" / "third_party" / "laya"
LOCK_PATH = REPO_ROOT / "workstation" / "components.lock.json"


def _read_locked_laya_metadata() -> Dict[str, Any]:
    """Read locked metadata for Laya from components.lock.json."""
    if not LOCK_PATH.is_file():
        return {}
    try:
        data = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        return data.get("components", {}).get("laya", {})
    except Exception:
        return {}


from dataclasses import asdict, dataclass


@dataclass
class LayaProvenance:
    """Provenance metadata for the active Laya runtime."""
    provider: str
    source_path: str
    laya_version: str
    laya_source_sha: str
    lock_sha: str
    is_vendored: bool
    locked_version: str = "0.3.23"
    locked_role: str = "system1-runtime-upstream"
    expected_subtree_dir: str = ""
    model: str = "multilingual"
    checkpoint_revision: Optional[str] = None
    checkpoint_digest: Optional[str] = None
    device: str = "cpu"
    calibration_id: str = "laya-v1-20261002"
    question_schema_version: str = "1.0.0"
    source_bytes_verified: bool = False

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_laya_provenance(
    model: str = "multilingual",
    checkpoint_revision: Optional[str] = None,
    checkpoint_digest: Optional[str] = None,
    calibration_id: str = "laya-v1-20261002",
    question_schema_version: str = "1.0.0",
    device: Optional[str] = None,
) -> LayaProvenance:
    """Collect full runtime provenance for the active Laya installation.

    Proves which source, commit, version, checkpoint and calibration are active.
    """
    import laya

    source_path = Path(laya.__file__).resolve()
    laya_version = getattr(laya, "__version__", "")

    lock_meta = _read_locked_laya_metadata()
    locked_sha = lock_meta.get("ref", "4aa6761be8173de4ce6d92c31b3e40b6eaf59a7c")
    locked_version = lock_meta.get("version", "0.3.23")
    locked_role = lock_meta.get("role", "system1-runtime-upstream")

    # Check whether the import resolves inside the approved vendored subtree
    try:
        is_vendored = source_path.is_relative_to(EXPECTED_SUBTREE_DIR.resolve())
    except AttributeError:
        # Python < 3.9 compatibility fallback
        is_vendored = str(source_path).startswith(str(EXPECTED_SUBTREE_DIR.resolve()))

    manifest = json.loads(Path(__file__).with_name("laya_source_manifest.json").read_text())
    package_root = source_path.parent.parent
    def matches(root: Path) -> bool:
        return all(
            (root / name).is_file()
            and hashlib.sha256((root / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() == digest
            for name, digest in manifest["files"].items()
        )
    # Non-editable uv path sources install a wheel into site-packages. Require
    # local-install provenance AND byte identity, never a matching version alone.
    if not is_vendored:
        try:
            from urllib.parse import urlparse, unquote
            from urllib.request import url2pathname
            direct = json.loads(metadata.distribution("laya").read_text("direct_url.json") or "{}")
            url = urlparse(direct.get("url", ""))
            is_vendored = url.scheme == "file" and Path(url2pathname(unquote(url.path))).resolve() == EXPECTED_SUBTREE_DIR.resolve()
        except (metadata.PackageNotFoundError, ValueError, TypeError):
            is_vendored = False
    verified = matches(EXPECTED_SUBTREE_DIR) and matches(package_root) and manifest["revision"] == locked_sha

    return LayaProvenance(
        provider="laya",
        source_path=str(source_path),
        laya_version=laya_version,
        laya_source_sha=manifest["revision"] if verified else "",
        lock_sha=locked_sha,
        locked_version=locked_version,
        locked_role=locked_role,
        is_vendored=is_vendored,
        expected_subtree_dir=str(EXPECTED_SUBTREE_DIR.resolve()),
        model=model,
        checkpoint_revision=checkpoint_revision,
        checkpoint_digest=checkpoint_digest,
        device=device or "cpu",
        calibration_id=calibration_id,
        question_schema_version=question_schema_version,
        source_bytes_verified=verified,
    )


def verify_laya_provenance(strict: bool = True) -> bool:
    """Verify that Laya resolves to the vendored subtree and matches lock metadata.

    Raises RuntimeError if strict=True and Laya does not resolve from the vendored path.
    """
    provenance = get_laya_provenance()
    if not provenance.is_vendored:
        msg = (
            f"Laya provenance violation: import resolved from {provenance.source_path}, "
            f"expected vendored subtree at {provenance.expected_subtree_dir}. "
            "Hermes Work refuses non-vendored or unapproved global Laya installs."
        )
        if strict:
            raise RuntimeError(msg)
        return False

    if provenance.locked_version and provenance.laya_version != provenance.locked_version:
        msg = f"Version mismatch: Laya version {provenance.laya_version} does not match locked {provenance.locked_version}"
        if strict:
            raise RuntimeError(msg)
        return False

    if not provenance.source_bytes_verified:
        if strict:
            raise RuntimeError("Laya provenance violation: imported/source bytes differ from approved revision")
        return False

    return True

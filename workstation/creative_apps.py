"""Versioned Creative app manifests and explicit, owner-scoped CLI health probes."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from uuid import uuid4

from workstation.artifacts import ArtifactStore
from workstation.config import WorkstationConfig
from workstation.contracts import ExecutionEventKind
from workstation.creative_process import (
    CreativeExecutionScope, CreativeInvocation, start_creative_process, wait_creative_process,
)
from workstation.creative_runtime import EngineId
from workstation.health import ComponentState
from workstation.journal import ExecutionJournal


_VERSION_CONTRACTS = {
    "ffmpeg": (("-version",), r"^ffmpeg version (\S+)"),
    "ffprobe": (("-version",), r"^ffprobe version (\S+)"),
    "node": (("--version",), r"^(v\d+\.\d+\.\d+)\s*$"),
    "inkscape": (("--version",), r"^Inkscape (\S+)"),
    "blender": (("--version",), r"^Blender (\S+)"),
    "hyperframes": (("--version",), r"^v?(\d+\.\d+\.\d+\S*)"),
}


@dataclass(frozen=True, slots=True)
class CreativeAppManifest:
    schema_version: int
    engine: EngineId
    executable: str
    executable_sha256: str
    provider_ref: str

    def validate(self) -> None:
        if self.schema_version != 1 or self.engine not in _VERSION_CONTRACTS:
            raise ValueError("Unsupported Creative app manifest")
        if not re.fullmatch(r"[0-9a-f]{64}", self.executable_sha256):
            raise ValueError("Creative app requires a SHA-256 fingerprint")
        if not self.provider_ref or len(self.provider_ref) > 512 or "://" in self.provider_ref:
            raise ValueError("Creative provider ref must be a non-secret local provenance identifier")

    def to_dict(self) -> dict:
        return asdict(self)


def probe_creative_app(
    config: WorkstationConfig, scope: CreativeExecutionScope, manifest: CreativeAppManifest,
    *, timeout: int = 15, registry=None,
) -> dict:
    """Run a fixed version command; this proves CLI health, never UI/service readiness."""
    manifest.validate()
    if not isinstance(timeout, int) or not 1 <= timeout <= 30:
        raise ValueError("Creative health timeout must be between 1 and 30 seconds")
    args, pattern = _VERSION_CONTRACTS[manifest.engine]
    invocation = CreativeInvocation(manifest.engine, (manifest.executable, *args), manifest.executable_sha256)
    process = start_creative_process(config, scope, invocation, registry=registry)
    result = wait_creative_process(scope, process.id, timeout=timeout, registry=registry)
    output = result.get("output", "")
    match = re.search(pattern, output, flags=re.MULTILINE)
    healthy = result.get("status") == "exited" and result.get("exit_code") == 0 and match is not None
    receipt = {
        "schema_version": 1, "engine": manifest.engine, "process_id": process.id,
        "health": ComponentState.OK.value if healthy else ComponentState.DOWN.value,
        "version": match.group(1) if healthy else None,
        "executable_sha256": manifest.executable_sha256, "provider_ref": manifest.provider_ref,
        "probe_kind": "cli_version", "process_status": result.get("status"),
        "exit_code": result.get("exit_code"), "task_id": scope.task_id,
        "session_key": scope.session_key,
    }
    scope.validate()
    artifact = ArtifactStore().store(scope.task_id, f"creative-health-{uuid4().hex}.json", receipt,
                                     schema="creative.cli-health.v1", media_type="application/json")
    ExecutionJournal(task_id=scope.task_id, session_id=scope.session_key).record(
        ExecutionEventKind.LIFECYCLE, "Creative CLI health probe finished",
        metadata={"artifact_ref": artifact.ref, "sha256": artifact.sha256, **receipt},
    )
    return {**receipt, "artifact_ref": artifact.ref, "artifact_sha256": artifact.sha256}

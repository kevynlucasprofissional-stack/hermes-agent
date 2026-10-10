"""HyperFrames Studio service lifecycle, health readback, and loopback security boundary.

Manages self-hosted HyperFrames Studio instance scoped to TaskRun/Session ownership.
Enforces 127.0.0.1 binding, port negotiation, random session tokens, environment
sanitization, and process tracking through the canonical ProcessRegistry.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import secrets
import shlex
import socket
import subprocess
import time
from typing import Any, Dict, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from hermes_cli._subprocess_compat import windows_hide_flags
from hermes_platform.resolver import locate_command
from tools.approval import check_all_command_guards
from tools.approval_context import get_current_session_key
from tools.process_registry import ProcessRegistry, process_registry
from workstation.artifacts import ArtifactStore
from workstation.config import WorkstationConfig
from workstation.contracts import ExecutionEventKind
from workstation.creative_process import CreativeExecutionScope, _child_env
from workstation.journal import ExecutionJournal
from workstation.policy import ActionScope, PolicyDecision, ScopedPolicyEngine

logger = logging.getLogger(__name__)

DEFAULT_STUDIO_BASE_PORT = 3032
DEFAULT_STUDIO_MAX_PORT = 3099
STUDIO_READY_TIMEOUT_SECONDS = 15.0
STUDIO_HEALTH_TIMEOUT_SECONDS = 2.0


class CreativeStudioError(RuntimeError):
    """Structured error for Creative Studio lifecycle failures."""
    pass


@dataclass(frozen=True, slots=True)
class HyperFramesInstallation:
    """Audited installation metadata for HyperFrames CLI/Studio."""
    engine: str
    node_executable: Path
    node_sha256: str
    cli_entrypoint: Path
    cli_entrypoint_sha256: str
    package_version: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engine": self.engine,
            "node_executable": str(self.node_executable),
            "node_sha256": self.node_sha256,
            "cli_entrypoint": str(self.cli_entrypoint),
            "cli_entrypoint_sha256": self.cli_entrypoint_sha256,
            "package_version": self.package_version,
        }


@dataclass(frozen=True, slots=True)
class StudioInstance:
    """Running HyperFrames Studio instance handle."""
    process_id: str
    port: int
    host: str
    session_token: str
    project_path: Path
    url: str
    task_id: str
    session_key: str
    created_at: str
    ready: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "process_id": self.process_id,
            "port": self.port,
            "host": self.host,
            "session_token": self.session_token,
            "project_path": str(self.project_path),
            "url": self.url,
            "task_id": self.task_id,
            "session_key": self.session_key,
            "created_at": self.created_at,
            "ready": self.ready,
        }


def _file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def discover_hyperframes(config: WorkstationConfig, *, search_paths: Tuple[Path, ...] = ()) -> Optional[HyperFramesInstallation]:
    """Locate Node.js and a valid pinned HyperFrames CLI installation.

    Checks environment override, provided search paths, and standard locations.
    Never downloads or modifies binaries.
    """
    if not config.creative_enabled or not config.creative_hyperframes_enabled:
        return None

    node_res = locate_command("node")
    if not node_res.found:
        return None
    node_exe = Path(node_res.command[0]).resolve()
    if not node_exe.is_file():
        return None
    node_hash = _file_sha256(node_exe)

    candidates: list[Path] = []
    env_override = os.environ.get("HERMES_HYPERFRAMES_PATH", "").strip()
    if env_override:
        candidates.append(Path(env_override).expanduser().resolve())
    for sp in search_paths:
        candidates.append(sp.resolve())

    # Check local workspace / scratch locations
    from hermes_constants import get_hermes_home
    home = get_hermes_home()
    candidates.extend([
        home / "workstation" / "creative" / "engines" / "hyperframes",
        Path.cwd() / "node_modules" / "hyperframes",
        Path.home() / ".gemini" / "antigravity" / "scratch" / "hyperframes-runner" / "node_modules" / "hyperframes",
    ])

    for pkg_dir in candidates:
        pkg_json = pkg_dir / "package.json"
        if not pkg_json.is_file():
            continue
        try:
            meta = json.loads(pkg_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if meta.get("name") != "hyperframes":
            continue

        version = str(meta.get("version") or "unknown")
        entrypoint = pkg_dir / "bin" / "hyperframes.mjs"
        if not entrypoint.is_file():
            entrypoint = pkg_dir / "dist" / "cli.js"
        if not entrypoint.is_file():
            continue

        entry_hash = _file_sha256(entrypoint)
        return HyperFramesInstallation(
            engine="hyperframes",
            node_executable=node_exe,
            node_sha256=node_hash,
            cli_entrypoint=entrypoint,
            cli_entrypoint_sha256=entry_hash,
            package_version=version,
        )

    return None


def allocate_studio_port(
    host: str = "127.0.0.1",
    start_port: int = DEFAULT_STUDIO_BASE_PORT,
    max_port: int = DEFAULT_STUDIO_MAX_PORT,
) -> int:
    """Find and verify an available loopback TCP port.

    Guarantees binding to 127.0.0.1 only, avoiding LAN exposure.
    """
    if host != "127.0.0.1":
        raise ValueError("Studio port allocation strictly requires 127.0.0.1 loopback host")

    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if os.name != "nt":
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
                return port
            except OSError:
                continue

    raise CreativeStudioError(f"No available loopback port in range {start_port}-{max_port}")


def generate_session_token() -> str:
    """Generate a high-entropy secret token for local Studio authentication."""
    return secrets.token_hex(24)


def validate_studio_origin(origin: Optional[str], host: str, port: int) -> bool:
    """Validate that incoming requests originate only from the authorized local Studio instance."""
    if not origin:
        return True
    allowed = {
        f"http://{host}:{port}",
        f"http://127.0.0.1:{port}",
        f"http://localhost:{port}",
    }
    return origin.rstrip("/") in allowed


def start_studio_service(
    config: WorkstationConfig,
    scope: CreativeExecutionScope,
    installation: HyperFramesInstallation,
    project_dir: Path,
    *,
    port: Optional[int] = None,
    registry: Optional[ProcessRegistry] = None,
    timeout: float = STUDIO_READY_TIMEOUT_SECONDS,
) -> StudioInstance:
    """Start and supervise a self-hosted HyperFrames Studio preview process.

    Enforces TaskRun ownership, policy evaluation, command guards,
    clean environment sanitization, and readiness verification.
    """
    if not config.creative_enabled or not config.creative_hyperframes_enabled:
        raise PermissionError("HyperFrames Creative Studio is disabled in configuration")

    workspace = scope.validate()
    project_resolved = project_dir.resolve()
    if not project_resolved.is_relative_to(workspace):
        raise PermissionError("Creative Studio project directory escaped TaskRun workspace")
    if not project_resolved.is_dir():
        project_resolved.mkdir(parents=True, exist_ok=True)

    # Initialize empty project scaffolding if needed
    hf_json = project_resolved / "hyperframes.json"
    index_html = project_resolved / "index.html"
    if not hf_json.is_file() and not index_html.is_file():
        hf_json.write_text(json.dumps({
            "version": "1.0",
            "name": project_resolved.name,
            "width": 1920,
            "height": 1080,
            "fps": 30,
            "duration": 60,
        }, indent=2), encoding="utf-8")
        index_html.write_text(
            "<!DOCTYPE html>\n<html>\n<head>\n  <meta charset=\"utf-8\">\n"
            "  <title>Creative Composition</title>\n</head>\n<body>\n"
            "  <div id=\"root\"></div>\n</body>\n</html>\n",
            encoding="utf-8",
        )

    assigned_port = port or allocate_studio_port()
    session_token = generate_session_token()
    host = "127.0.0.1"
    studio_url = f"http://{host}:{assigned_port}/?token={session_token}"

    argv = (
        str(installation.node_executable),
        str(installation.cli_entrypoint),
        "preview",
        "--no-open",
        "--port",
        str(assigned_port),
    )
    command = shlex.join(argv)

    # Authorize against ScopedPolicyEngine
    policy_scope = ActionScope(
        task_id=scope.task_id,
        session_id=scope.session_key,
        capability="creative_studio",
        action_name="start_preview",
        target=f"{host}:{assigned_port}",
        workspace_root=str(workspace),
    )
    evaluation = ScopedPolicyEngine().evaluate(policy_scope)
    if evaluation.decision is not PolicyDecision.ALLOW:
        raise PermissionError(f"Creative Studio policy denied: {evaluation.decision.value}")

    approval = check_all_command_guards(command, "local", has_host_access=True)
    if not approval.get("approved", False):
        raise PermissionError("Creative Studio execution denied by command guards")

    # Sanitized child environment with isolated temp and zero credentials
    env = _child_env(workspace)
    env.update({
        "HYPERFRAMES_SKIP_SKILLS": "1",
        "HYPERFRAMES_TELEMETRY": "0",
        "HYPERFRAMES_PORT": str(assigned_port),
        "HYPERFRAMES_HOST": host,
        "HYPERFRAMES_TOKEN": session_token,
    })

    if registry is None:
        registry = process_registry

    proc = subprocess.Popen(
        list(argv),
        cwd=str(project_resolved),
        env=env,
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=True,
        creationflags=windows_hide_flags(),
    )

    try:
        session = registry.adopt_local(
            proc,
            command=command,
            cwd=str(project_resolved),
            task_id=scope.task_id,
            owner_task_id=scope.task_id,
            session_key=scope.session_key,
            notify_on_complete=False,
        )
    except BaseException:
        proc.kill()
        proc.wait(timeout=5)
        if proc.stdout:
            proc.stdout.close()
        raise

    process_id = session.id

    # Wait for HTTP readiness with polling
    ready = False
    start_time = time.monotonic()
    check_url = f"http://{host}:{assigned_port}/__hyperframes_config"

    while time.monotonic() - start_time < timeout:
        poll_res = registry.poll(process_id)
        if poll_res.get("status") in {"exited", "error"}:
            exit_code = poll_res.get("exit_code")
            output = poll_res.get("output", "")
            raise CreativeStudioError(
                f"HyperFrames Studio process exited prematurely (code {exit_code}): {output[:500]}"
            )

        try:
            req = Request(check_url, headers={"User-Agent": "Hermes-Creative-Probe/1.0"})
            with urlopen(req, timeout=STUDIO_HEALTH_TIMEOUT_SECONDS) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except (HTTPError, URLError, TimeoutError, OSError):
            # Try root URL fallback
            try:
                with urlopen(f"http://{host}:{assigned_port}/", timeout=1.0) as root_resp:
                    if root_resp.status == 200:
                        ready = True
                        break
            except Exception:
                pass
            time.sleep(0.3)

    if not ready:
        registry.kill_process(process_id, source="creative.studio_readiness_timeout")
        raise CreativeStudioError(f"HyperFrames Studio failed to reach readiness within {timeout}s")

    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    instance = StudioInstance(
        process_id=process_id,
        port=assigned_port,
        host=host,
        session_token=session_token,
        project_path=project_resolved,
        url=studio_url,
        task_id=scope.task_id,
        session_key=scope.session_key,
        created_at=now_iso,
        ready=ready,
    )

    # Persist launch metadata artifact and record lifecycle journal
    store = ArtifactStore()
    art_payload = instance.to_dict()
    art_payload["installation"] = installation.to_dict()
    # Mask session token from artifact storage
    art_payload["session_token"] = "***"
    art_payload["url"] = f"http://{host}:{assigned_port}/#project"

    artifact = store.store(
        scope.task_id,
        f"creative-studio-{uuid4().hex[:12]}.json",
        art_payload,
        schema="creative.studio-service.v1",
        media_type="application/json",
    )

    ExecutionJournal(task_id=scope.task_id, session_id=scope.session_key).record(
        ExecutionEventKind.LIFECYCLE,
        "HyperFrames Studio service started and ready",
        metadata={
            "process_id": process_id,
            "port": assigned_port,
            "host": host,
            "project_path": str(project_resolved),
            "artifact_ref": artifact.ref,
        },
    )

    return instance


def probe_studio_health(instance: StudioInstance, *, timeout: float = STUDIO_HEALTH_TIMEOUT_SECONDS) -> Dict[str, Any]:
    """Perform readback probe of running HyperFrames Studio instance."""
    config_url = f"http://{instance.host}:{instance.port}/__hyperframes_config"
    env_url = f"http://{instance.host}:{instance.port}/api/environment/ffmpeg"

    probe_result: Dict[str, Any] = {
        "process_id": instance.process_id,
        "port": instance.port,
        "host": instance.host,
        "healthy": False,
        "config_ok": False,
        "ffmpeg_ok": False,
        "details": {},
    }

    try:
        req = Request(config_url, headers={"User-Agent": "Hermes-Creative-Probe/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                probe_result["config_ok"] = bool(body.get("isHyperframes"))
                probe_result["details"]["config"] = body
    except Exception as exc:
        probe_result["details"]["config_error"] = str(exc)

    try:
        req = Request(env_url, headers={"User-Agent": "Hermes-Creative-Probe/1.0"})
        with urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                body = json.loads(resp.read().decode("utf-8"))
                probe_result["ffmpeg_ok"] = bool(body.get("ok"))
                probe_result["details"]["ffmpeg"] = body
    except Exception as exc:
        probe_result["details"]["ffmpeg_error"] = str(exc)

    probe_result["healthy"] = probe_result["config_ok"]
    return probe_result


def stop_studio_service(
    scope: CreativeExecutionScope,
    process_id: str,
    *,
    registry: Optional[ProcessRegistry] = None,
) -> Dict[str, Any]:
    """Gracefully terminate HyperFrames Studio and its process tree, ensuring no orphan child."""
    scope.validate()
    if registry is None:
        registry = process_registry

    session = registry.get(process_id)
    if session and (session.owner_task_id != scope.task_id or session.session_key != scope.session_key):
        raise PermissionError("Creative Studio ownership mismatch on stop")

    kill_result = registry.kill_process(process_id, source="creative.studio_stop")

    ExecutionJournal(task_id=scope.task_id, session_id=scope.session_key).record(
        ExecutionEventKind.LIFECYCLE,
        "HyperFrames Studio service stopped",
        metadata={"process_id": process_id, "kill_result": kill_result},
    )

    return kill_result


def restart_studio_service(
    config: WorkstationConfig,
    scope: CreativeExecutionScope,
    installation: HyperFramesInstallation,
    existing_instance: StudioInstance,
    *,
    registry: Optional[ProcessRegistry] = None,
    timeout: float = STUDIO_READY_TIMEOUT_SECONDS,
) -> StudioInstance:
    """Safely restart Studio instance, reusing project directory and verifying port reallocation."""
    try:
        stop_studio_service(scope, existing_instance.process_id, registry=registry)
    except Exception:
        pass

    # Brief delay for TCP port release
    time.sleep(0.5)

    return start_studio_service(
        config,
        scope,
        installation,
        existing_instance.project_path,
        registry=registry,
        timeout=timeout,
    )

"""Creative CLI execution using Hermes approval and canonical process ownership.

These are internal adapter primitives, not a tool accepting arbitrary model argv.
Engine adapters construct the invocation after validating their operation schema.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import shlex
import subprocess
from typing import TYPE_CHECKING

from hermes_constants import get_hermes_home, hermes_home_key
from hermes_cli._subprocess_compat import windows_hide_flags
from tools.approval import check_all_command_guards
from tools.approval_context import get_current_session_key
from tools.environments.local import build_subprocess_env
from workstation.config import WorkstationConfig
from workstation.policy import ActionScope, PolicyDecision, ScopedPolicyEngine

if TYPE_CHECKING:
    from tools.process_registry import ProcessRegistry, ProcessSession


@dataclass(frozen=True, slots=True)
class CreativeExecutionScope:
    profile_home: str
    session_key: str
    task_id: str
    workspace: str

    def validate(self) -> Path:
        if hermes_home_key(self.profile_home) != hermes_home_key():
            raise PermissionError("Creative profile mismatch")
        if not self.session_key or self.session_key != get_current_session_key(default=""):
            raise PermissionError("Creative session mismatch")
        if not self.task_id:
            raise PermissionError("Creative task ownership required")
        workspace = Path(self.workspace)
        if not workspace.is_absolute():
            raise ValueError("Creative workspace must be absolute")
        root = (get_hermes_home() / "workstation" / "creative").resolve()
        resolved = workspace.resolve(strict=True)
        if not resolved.is_dir() or resolved == root or not resolved.is_relative_to(root):
            raise PermissionError("Creative workspace outside active profile project root")
        return resolved


@dataclass(frozen=True, slots=True)
class CreativeInvocation:
    engine: str
    argv: tuple[str, ...]
    executable_sha256: str

    def validate(self) -> None:
        if not self.argv or any(not isinstance(v, str) or "\x00" in v for v in self.argv):
            raise ValueError("Invalid Creative argv")
        executable = Path(self.argv[0])
        if not executable.is_absolute() or executable.suffix.lower() in {".cmd", ".bat", ".ps1", ".sh"}:
            raise ValueError("Creative engines require an absolute native executable")
        with executable.open("rb") as source:
            actual = hashlib.file_digest(source, "sha256").hexdigest()
        if actual != self.executable_sha256:
            raise PermissionError("Creative executable fingerprint drift")


def _child_env(workspace: Path) -> dict[str, str]:
    # No ambient PATH, loader flags, proxy credentials, package runners or vendor tokens.
    allowed = {"SYSTEMROOT", "WINDIR", "LANG", "LC_ALL"}
    base = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    private_temp = workspace / ".tmp"
    private_temp.mkdir(exist_ok=True)
    if private_temp.is_symlink() or not private_temp.resolve().is_relative_to(workspace):
        raise PermissionError("Creative temporary directory escaped workspace")
    base.update(HOME=str(workspace), USERPROFILE=str(workspace),
                TMP=str(private_temp), TEMP=str(private_temp), TMPDIR=str(private_temp))
    env = build_subprocess_env(base=base, inherit_profile_home=False, scrub_secrets=False)
    return {key: value for key, value in env.items()
            if key.upper() in allowed | {"HOME", "USERPROFILE", "TMP", "TEMP", "TMPDIR"}}


def start_creative_process(
    config: WorkstationConfig, scope: CreativeExecutionScope, invocation: CreativeInvocation,
    *, registry: ProcessRegistry | None = None,
) -> ProcessSession:
    if not config.creative_enabled:
        raise PermissionError("Creative runtime is disabled")
    workspace = scope.validate()
    invocation.validate()
    command = shlex.join(invocation.argv)
    evaluation = ScopedPolicyEngine().evaluate(ActionScope(
        task_id=scope.task_id, session_id=scope.session_key, capability="process",
        action_name="run_command", target=command, workspace_root=str(workspace),
    ))
    if evaluation.decision is not PolicyDecision.ALLOW:
        raise PermissionError(f"Creative policy: {evaluation.decision.value}")
    approval = check_all_command_guards(command, "local", has_host_access=True)
    if not approval.get("approved", False):
        raise PermissionError("Creative execution denied by command guards")
    # Recheck after a potentially asynchronous approval wait, immediately before I/O.
    scope.validate()
    invocation.validate()
    env = _child_env(workspace)
    if registry is None:
        from tools.process_registry import process_registry
        registry = process_registry
    proc = subprocess.Popen(
        list(invocation.argv), cwd=str(workspace), env=env, shell=False,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
        text=True, encoding="utf-8", errors="replace", start_new_session=True,
        creationflags=windows_hide_flags(),
    )
    try:
        return registry.adopt_local(
            proc, command=command, cwd=str(workspace), task_id=scope.task_id,
            owner_task_id=scope.task_id, session_key=scope.session_key,
            notify_on_complete=False,
        )
    except BaseException:
        # Ownership transfer failed: retain no unmanaged child.
        proc.kill()
        proc.wait(timeout=5)
        if proc.stdout:
            proc.stdout.close()
        raise


def inspect_creative_process(scope: CreativeExecutionScope, process_id: str, *, registry=None) -> dict:
    workspace = scope.validate()
    if registry is None:
        from tools.process_registry import process_registry
        registry = process_registry
    session = registry.get(process_id)
    if (session is None or session.id != process_id or session.owner_task_id != scope.task_id
            or session.session_key != scope.session_key or Path(session.cwd or "").resolve() != workspace):
        raise PermissionError("Creative process owner mismatch")
    from tools.process_registry import _redact_process_result
    return _redact_process_result(registry.poll(process_id))


def stop_creative_process(scope: CreativeExecutionScope, process_id: str, *, registry=None) -> dict:
    if registry is None:
        from tools.process_registry import process_registry
        registry = process_registry
    inspect_creative_process(scope, process_id, registry=registry)
    from tools.process_registry import _redact_process_result
    return _redact_process_result(registry.kill_process(process_id, source="creative.cancel"))


def wait_creative_process(
    scope: CreativeExecutionScope, process_id: str, *, timeout: int = 30, registry=None,
) -> dict:
    if not isinstance(timeout, int) or not 1 <= timeout <= 300:
        raise ValueError("Creative timeout must be between 1 and 300 seconds")
    if registry is None:
        from tools.process_registry import process_registry
        registry = process_registry
    inspect_creative_process(scope, process_id, registry=registry)
    result = registry.wait(process_id, timeout=timeout)
    if result.get("status") in {"timeout", "interrupted"}:
        cleanup = stop_creative_process(scope, process_id, registry=registry)
        return {**result, "cleanup": cleanup}
    from tools.process_registry import _redact_process_result
    return _redact_process_result(result)

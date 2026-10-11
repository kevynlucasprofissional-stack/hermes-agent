from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

import pytest

from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from tools.approval_context import reset_current_session_key, set_current_session_key
from tools.process_registry import ProcessRegistry
from workstation.config import WorkstationConfig
from workstation.creative_process import (
    CreativeExecutionScope, CreativeInvocation, inspect_creative_process,
    start_creative_process, stop_creative_process, wait_creative_process,
)


def _invocation(code):
    binary = Path(sys.executable).resolve()
    return CreativeInvocation("test-helper", (str(binary), "-u", "-c", code),
                              hashlib.sha256(binary.read_bytes()).hexdigest())


def test_process_real_environment_owner_and_cancellation(tmp_path, monkeypatch):
    home = tmp_path / "profile-a"
    workspace = home / "workstation" / "creative" / "project"
    workspace.mkdir(parents=True)
    home_token = set_hermes_home_override(home)
    session_token = set_current_session_key("session-a")
    registry = ProcessRegistry()
    scope = CreativeExecutionScope(str(home), "session-a", "task-a", str(workspace))
    config = WorkstationConfig({"creative": {"enabled": True}})
    monkeypatch.setenv("CREATIVE_SECRET_CANARY", "must-not-leak")
    monkeypatch.setenv("NODE_OPTIONS", "must-not-be-inherited")
    try:
        child = start_creative_process(config, scope, _invocation(
            "import json,os; print(json.dumps(dict(os.environ)))"), registry=registry)
        result = wait_creative_process(scope, child.id, timeout=10, registry=registry)
        assert result["status"] == "exited" and result["exit_code"] == 0
        environment = json.loads(result["output"].strip())
        assert "CREATIVE_SECRET_CANARY" not in environment and "NODE_OPTIONS" not in environment
        assert environment["HOME"] == str(workspace.resolve())
        assert child.owner_task_id == "task-a" and child.session_key == "session-a"
        with pytest.raises(PermissionError):
            inspect_creative_process(replace(scope, task_id="task-b"), child.id, registry=registry)
        token_b = set_hermes_home_override(tmp_path / "profile-b")
        try:
            with pytest.raises(PermissionError):
                inspect_creative_process(scope, child.id, registry=registry)
        finally:
            reset_hermes_home_override(token_b)
        assert inspect_creative_process(scope, child.id, registry=registry)["status"] == "exited"
        sleeper = start_creative_process(config, scope, _invocation(
            "import time; time.sleep(60)"), registry=registry)
        registry._write_checkpoint()
        recovered = ProcessRegistry()
        assert recovered.recover_from_checkpoint() == 1
        assert inspect_creative_process(scope, sleeper.id, registry=recovered)["detached"] is True
        cancelled = stop_creative_process(scope, sleeper.id, registry=recovered)
        assert cancelled.get("status") != "error"
        assert sleeper.process.poll() is not None
        assert inspect_creative_process(scope, sleeper.id, registry=registry)["status"] == "exited"
    finally:
        registry.kill_all()
        reset_current_session_key(session_token)
        reset_hermes_home_override(home_token)


def test_refusals_are_atomic_and_timeout_reaps_child(tmp_path, monkeypatch):
    home = tmp_path / "profile"
    workspace = home / "workstation" / "creative" / "project"
    workspace.mkdir(parents=True)
    ht = set_hermes_home_override(home)
    st = set_current_session_key("session")
    registry = ProcessRegistry()
    scope = CreativeExecutionScope(str(home), "session", "task", str(workspace))
    enabled = WorkstationConfig({"creative": {"enabled": True}})
    invocation = _invocation("import time; time.sleep(60)")
    try:
        for config, candidate_scope, command in (
            (WorkstationConfig({}), scope, invocation),
            (enabled, replace(scope, session_key="other"), invocation),
            (enabled, replace(scope, workspace=str(tmp_path)), invocation),
            (enabled, scope, replace(invocation, executable_sha256="0" * 64)),
        ):
            with pytest.raises(PermissionError):
                start_creative_process(config, candidate_scope, command, registry=registry)
        with monkeypatch.context() as guard:
            guard.setattr("workstation.creative_process.check_all_command_guards",
                          lambda *args, **kwargs: {"approved": False})
            with pytest.raises(PermissionError):
                start_creative_process(enabled, scope, invocation, registry=registry)
        assert not registry._running
        assert not (workspace / ".tmp").exists()
        child = start_creative_process(enabled, scope, invocation, registry=registry)
        result = wait_creative_process(scope, child.id, timeout=1, registry=registry)
        assert result["status"] == "timeout" and result["cleanup"].get("status") != "error"
        assert child.process.poll() is not None
        assert workspace.is_dir()
    finally:
        registry.kill_all()
        reset_current_session_key(st)
        reset_hermes_home_override(ht)

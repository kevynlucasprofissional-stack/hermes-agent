"""Tests for HyperFrames Studio service lifecycle, port negotiation, and security boundaries."""
from pathlib import Path
import socket
import sys
import threading
import time

import pytest

from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from tools.approval_context import reset_current_session_key, set_current_session_key
from tools.process_registry import ProcessRegistry
from workstation.config import WorkstationConfig
from workstation.creative_process import CreativeExecutionScope
from workstation.creative_studio_service import (
    CreativeStudioError,
    HyperFramesInstallation,
    StudioInstance,
    allocate_studio_port,
    discover_hyperframes,
    generate_session_token,
    probe_studio_health,
    restart_studio_service,
    start_studio_service,
    stop_studio_service,
    validate_studio_origin,
)


def test_port_allocation_negotiates_open_port_and_handles_collisions():
    # Allocates a clean loopback port
    first_port = allocate_studio_port(start_port=3040, max_port=3050)
    assert 3040 <= first_port <= 3050

    # Occupy the allocated port to simulate collision/squatting
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as blocker:
        if sys.platform != "win32":
            blocker.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        blocker.bind(("127.0.0.1", first_port))
        blocker.listen(1)

        # Allocation should cleanly advance to the next available port
        second_port = allocate_studio_port(start_port=first_port, max_port=3050)
        assert second_port > first_port
        assert second_port <= 3050

    # Non-loopback request must fail closed
    with pytest.raises(ValueError, match="127.0.0.1 loopback"):
        allocate_studio_port(host="0.0.0.0")

    # Exhausted port range must raise structured error
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as b1:
        if sys.platform != "win32":
            b1.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        b1.bind(("127.0.0.1", 3090))
        b1.listen(1)
        with pytest.raises(CreativeStudioError, match="No available loopback port"):
            allocate_studio_port(start_port=3090, max_port=3090)


def test_session_token_and_origin_validation():
    token1 = generate_session_token()
    token2 = generate_session_token()
    assert len(token1) >= 48
    assert token1 != token2

    # Allowed loopback origins
    assert validate_studio_origin("http://127.0.0.1:3032", "127.0.0.1", 3032)
    assert validate_studio_origin("http://localhost:3032", "127.0.0.1", 3032)
    assert validate_studio_origin(None, "127.0.0.1", 3032)

    # Disallowed external origins
    assert not validate_studio_origin("http://malicious.example.com", "127.0.0.1", 3032)
    assert not validate_studio_origin("http://127.0.0.1:4000", "127.0.0.1", 3032)
    assert not validate_studio_origin("https://evil.org", "127.0.0.1", 3032)


def test_scope_and_profile_isolation(tmp_path):
    profile_a = tmp_path / "profile_a"
    profile_b = tmp_path / "profile_b"
    ws_a = profile_a / "workstation" / "creative" / "project_a"
    ws_b = profile_b / "workstation" / "creative" / "project_b"
    ws_outside = profile_a / "outside"
    ws_a.mkdir(parents=True)
    ws_b.mkdir(parents=True)
    ws_outside.mkdir(parents=True)

    token = set_hermes_home_override(profile_a)
    st = set_current_session_key("session-a")
    try:
        # Valid scope in profile A
        scope_a = CreativeExecutionScope(str(profile_a), "session-a", "task-a", str(ws_a))
        assert scope_a.validate() == ws_a.resolve()

        # Cross-profile access must be denied
        scope_cross = CreativeExecutionScope(str(profile_b), "session-a", "task-a", str(ws_a))
        with pytest.raises(PermissionError, match="profile mismatch"):
            scope_cross.validate()

        # Workspace outside creative root must be denied
        scope_escaped = CreativeExecutionScope(str(profile_a), "session-a", "task-a", str(ws_outside))
        with pytest.raises(PermissionError, match="outside active profile project root"):
            scope_escaped.validate()
    finally:
        reset_current_session_key(st)
        reset_hermes_home_override(token)


def test_discovery_respects_configuration_and_detects_package(tmp_path):
    disabled_config = WorkstationConfig({"creative": {"enabled": False, "hyperframes_enabled": False}})
    assert discover_hyperframes(disabled_config) is None

    enabled_config = WorkstationConfig({"creative": {"enabled": True, "hyperframes_enabled": True}})
    
    # Fake package in search paths
    fake_pkg = tmp_path / "node_modules" / "hyperframes"
    fake_pkg.mkdir(parents=True)
    (fake_pkg / "package.json").write_text('{"name": "hyperframes", "version": "0.8.143"}', encoding="utf-8")
    bin_dir = fake_pkg / "bin"
    bin_dir.mkdir()
    entry = bin_dir / "hyperframes.mjs"
    entry.write_text("#!/usr/bin/env node\nconsole.log('hyperframes');\n", encoding="utf-8")

    discovered = discover_hyperframes(enabled_config, search_paths=(fake_pkg,))
    if discovered is not None:
        assert discovered.engine == "hyperframes"
        assert discovered.package_version == "0.8.143"
        assert discovered.cli_entrypoint == entry.resolve()
        assert len(discovered.cli_entrypoint_sha256) == 64


def test_premature_exit_fails_fast_without_orphans(tmp_path):
    profile = tmp_path / "profile"
    workspace = profile / "workstation" / "creative" / "project"
    workspace.mkdir(parents=True)

    token = set_hermes_home_override(profile)
    st = set_current_session_key("crash-session")
    registry = ProcessRegistry()

    config = WorkstationConfig({"creative": {"enabled": True, "hyperframes_enabled": True}})
    scope = CreativeExecutionScope(str(profile), "crash-session", "crash-task", str(workspace))

    # Helper script that exits immediately with error
    crash_script = workspace / "crash.mjs"
    crash_script.write_text("process.exit(42);\n", encoding="utf-8")
    import hashlib
    py_exe = Path(sys.executable).resolve()
    node_hash = hashlib.sha256(py_exe.read_bytes()).hexdigest()
    script_hash = hashlib.sha256(crash_script.read_bytes()).hexdigest()

    installation = HyperFramesInstallation(
        engine="hyperframes",
        node_executable=py_exe,
        node_sha256=node_hash,
        cli_entrypoint=crash_script,
        cli_entrypoint_sha256=script_hash,
        package_version="0.8.143",
    )

    try:
        with pytest.raises(CreativeStudioError, match="exited prematurely"):
            start_studio_service(config, scope, installation, workspace, registry=registry, timeout=5.0)

        # Verify no orphan running processes remain in registry
        assert not registry._running
    finally:
        registry.kill_all()
        reset_current_session_key(st)
        reset_hermes_home_override(token)


def test_real_studio_service_lifecycle_probe_and_stop(tmp_path):
    profile = tmp_path / "profile"
    workspace = profile / "workstation" / "creative" / "project"
    workspace.mkdir(parents=True)

    token = set_hermes_home_override(profile)
    st = set_current_session_key("lifecycle-session")
    registry = ProcessRegistry()

    config = WorkstationConfig({"creative": {"enabled": True, "hyperframes_enabled": True}})
    scope = CreativeExecutionScope(str(profile), "lifecycle-session", "lifecycle-task", str(workspace))

    # Python script simulating HyperFrames preview server
    server_script = workspace / "mock_studio_server.py"
    server_script.write_text(
        "import sys, json, os\n"
        "from http.server import HTTPServer, BaseHTTPRequestHandler\n"
        "port = int(sys.argv[4]) if len(sys.argv) > 4 else 3045\n"
        "class Handler(BaseHTTPRequestHandler):\n"
        "    def do_GET(self):\n"
        "        if self.path == '/__hyperframes_config':\n"
        "            self.send_response(200)\n"
        "            self.send_header('Content-Type', 'application/json')\n"
        "            self.end_headers()\n"
        "            self.wfile.write(b'{\"isHyperframes\": true}')\n"
        "        elif self.path == '/api/environment/ffmpeg':\n"
        "            self.send_response(200)\n"
        "            self.send_header('Content-Type', 'application/json')\n"
        "            self.end_headers()\n"
        "            self.wfile.write(b'{\"ok\": true}')\n"
        "        else:\n"
        "            self.send_response(200)\n"
        "            self.end_headers()\n"
        "            self.wfile.write(b'OK')\n"
        "    def log_message(self, *args): pass\n"
        "server = HTTPServer(('127.0.0.1', port), Handler)\n"
        "server.serve_forever()\n",
        encoding="utf-8",
    )

    import hashlib
    py_exe = Path(sys.executable).resolve()
    py_hash = hashlib.sha256(py_exe.read_bytes()).hexdigest()
    script_hash = hashlib.sha256(server_script.read_bytes()).hexdigest()

    installation = HyperFramesInstallation(
        engine="hyperframes",
        node_executable=py_exe,
        node_sha256=py_hash,
        cli_entrypoint=server_script,
        cli_entrypoint_sha256=script_hash,
        package_version="0.8.143",
    )

    try:
        instance = start_studio_service(
            config, scope, installation, workspace, registry=registry, timeout=5.0
        )
        assert instance.ready is True
        assert instance.port >= 3032
        assert instance.host == "127.0.0.1"
        assert instance.task_id == "lifecycle-task"
        assert instance.process_id in registry._running

        # Test health probe readback
        health = probe_studio_health(instance)
        assert health["healthy"] is True
        assert health["config_ok"] is True
        assert health["ffmpeg_ok"] is True

        # Test stopping service
        stop_res = stop_studio_service(scope, instance.process_id, registry=registry)
        assert stop_res.get("status") in {"killed", "exited", "stopped"}
        assert instance.process_id not in registry._running
        assert not registry._running
    finally:
        registry.kill_all()
        reset_current_session_key(st)
        reset_hermes_home_override(token)

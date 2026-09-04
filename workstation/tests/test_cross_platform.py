from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest

from workstation.cross_platform import (
    AgenticBenchmarkRegistry,
    CrossPlatformHostManager,
    HostPlatformKind,
    detect_host_platform,
)
from workstation.host import LinuxHostCapabilityProvider, WindowsHostCapabilityProvider
from workstation.omarchy import OmarchyAdapter, OmarchyHostProfile


def test_detect_host_platform():
    kind = detect_host_platform()
    assert kind in (HostPlatformKind.WINDOWS, HostPlatformKind.LINUX, HostPlatformKind.DARWIN)


def test_agentic_benchmark_registry_defaults():
    registry = AgenticBenchmarkRegistry()
    benchmarks = registry.list_benchmarks()
    assert len(benchmarks) >= 8

    ids = {b.harness_id for b in benchmarks}
    assert "omarchy" in ids
    assert "upstream-hermes" in ids
    assert "openhands" in ids
    assert "opencode" in ids
    assert "claude-code" in ids
    assert "codex" in ids
    assert "antigravity" in ids
    assert "browseros" in ids

    # Validate 4 architectural criteria answers
    for b in benchmarks:
        assert isinstance(b.hermes_has_problem, bool)
        assert b.expressible_in_hermes is True
        assert b.upstream_delta_safe is True
        assert len(b.problem_solved) > 10


def test_cross_platform_host_manager_windows():
    manager = CrossPlatformHostManager(platform_kind=HostPlatformKind.WINDOWS)
    provider = manager.get_capability_provider()
    assert isinstance(provider, WindowsHostCapabilityProvider)
    summary = manager.get_host_summary()
    assert summary["platform"] == "windows"
    assert "filesystem" in summary["supported_capabilities"]


def test_cross_platform_host_manager_linux():
    manager = CrossPlatformHostManager(platform_kind=HostPlatformKind.LINUX)
    provider = manager.get_capability_provider()
    assert isinstance(provider, LinuxHostCapabilityProvider)


def test_omarchy_adapter_detection_mocked(monkeypatch):
    monkeypatch.setenv("OMARCHY_HOST", "1")
    monkeypatch.setenv("OMARCHY_VERSION", "2.0-custom")

    adapter = OmarchyAdapter()
    profile = adapter.detect()
    assert profile.is_omarchy is True
    assert profile.version == "2.0-custom"


def test_omarchy_adapter_launch_agent_mocked():
    adapter = OmarchyAdapter()
    with patch("shutil.which", return_value="/usr/bin/agy"), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="Code fixed", stderr="")
        res = adapter.launch_agent("agy", "fix bug")
        assert res["success"] is True
        assert res["stdout"] == "Code fixed"

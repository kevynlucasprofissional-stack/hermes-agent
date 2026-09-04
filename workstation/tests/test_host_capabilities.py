from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch
import pytest

from workstation.host import (
    HostCapabilityResult,
    HostCapabilityType,
    KToolsNeoCapabilityAdapter,
    LinuxHostCapabilityProvider,
    WindowsHostCapabilityProvider,
    get_host_capability_provider,
)


def test_host_capability_types():
    assert HostCapabilityType.CLIPBOARD == "clipboard"
    assert HostCapabilityType.FILESYSTEM == "filesystem"
    assert HostCapabilityType.PROCESS == "process"
    assert HostCapabilityType.GIT == "git"
    assert HostCapabilityType.NOTIFICATION == "notification"
    assert HostCapabilityType.DIAGNOSTICS == "diagnostics"


def test_windows_provider_diagnostics():
    provider = WindowsHostCapabilityProvider()
    res = provider.get_diagnostics()
    assert res.success is True
    assert res.capability == HostCapabilityType.DIAGNOSTICS
    assert "os" in res.output
    assert "cpu_count" in res.output
    assert "disk" in res.output


def test_windows_provider_inspect_workspace(tmp_path):
    provider = WindowsHostCapabilityProvider()
    test_file = tmp_path / "hello.txt"
    test_file.write_text("world", encoding="utf-8")
    sub_dir = tmp_path / "subdir"
    sub_dir.mkdir()

    res = provider.inspect_workspace(str(tmp_path))
    assert res.success is True
    assert res.metadata["total_count"] == 2
    names = {entry["name"] for entry in res.output["entries"]}
    assert "hello.txt" in names
    assert "subdir" in names


def test_windows_provider_inspect_nonexistent_workspace():
    provider = WindowsHostCapabilityProvider()
    res = provider.inspect_workspace("C:\\invalid\\nonexistent\\path\\xyz123")
    assert res.success is False
    assert "does not exist" in res.error


def test_windows_provider_clipboard_mocked():
    provider = WindowsHostCapabilityProvider()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="mocked clipboard content", stderr="")
        res = provider.read_clipboard()
        assert res.success is True
        assert res.output == "mocked clipboard content"


def test_linux_provider_mocked():
    provider = LinuxHostCapabilityProvider()
    with patch("shutil.which", return_value="/usr/bin/wl-paste"), patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="linux clipboard", stderr="")
        res = provider.read_clipboard()
        assert res.success is True
        assert res.output == "linux clipboard"


def test_ktools_neo_adapter_fallback():
    mock_fallback = MagicMock()
    mock_fallback.read_clipboard.return_value = HostCapabilityResult(
        success=True,
        capability=HostCapabilityType.CLIPBOARD,
        action="read_clipboard",
        output="fallback content",
    )
    mock_fallback.get_diagnostics.return_value = HostCapabilityResult(
        success=True,
        capability=HostCapabilityType.DIAGNOSTICS,
        action="get_diagnostics",
        output={"os": "Windows"},
    )
    adapter = KToolsNeoCapabilityAdapter(fallback_provider=mock_fallback)
    assert adapter.is_available() is False

    res = adapter.read_clipboard()
    assert res.output == "fallback content"

    diag = adapter.get_diagnostics()
    assert diag.output["ktools_installed"] is False


def test_get_host_capability_provider_factory():
    provider_win = get_host_capability_provider("windows")
    assert isinstance(provider_win, WindowsHostCapabilityProvider)

    provider_ktools = get_host_capability_provider("ktools")
    assert isinstance(provider_ktools, KToolsNeoCapabilityAdapter)

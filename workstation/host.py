from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
import logging
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any, Optional

_log = logging.getLogger(__name__)


class HostCapabilityType(str, Enum):
    FILESYSTEM = "filesystem"
    PROCESS = "process"
    CLIPBOARD = "clipboard"
    GIT = "git"
    NOTIFICATION = "notification"
    DIAGNOSTICS = "diagnostics"


@dataclass(slots=True)
class HostCapabilityResult:
    success: bool
    capability: HostCapabilityType
    action: str
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["capability"] = self.capability.value
        return data


class HostCapabilityProvider(ABC):
    """Abstract contract for safe host-capability operations outside the browser."""

    @abstractmethod
    def get_supported_capabilities(self) -> list[HostCapabilityType]:
        pass

    @abstractmethod
    def read_clipboard(self) -> HostCapabilityResult:
        pass

    @abstractmethod
    def write_clipboard(self, text: str) -> HostCapabilityResult:
        pass

    @abstractmethod
    def get_diagnostics(self) -> HostCapabilityResult:
        pass

    @abstractmethod
    def send_notification(self, title: str, message: str) -> HostCapabilityResult:
        pass

    @abstractmethod
    def run_command(
        self,
        command: list[str],
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> HostCapabilityResult:
        pass

    @abstractmethod
    def inspect_workspace(self, workspace_path: str) -> HostCapabilityResult:
        pass

    @abstractmethod
    def git_status(self, repo_path: str) -> HostCapabilityResult:
        pass


class WindowsHostCapabilityProvider(HostCapabilityProvider):
    """Windows-native host capability implementation."""

    def get_supported_capabilities(self) -> list[HostCapabilityType]:
        return list(HostCapabilityType)

    def read_clipboard(self) -> HostCapabilityResult:
        # Try pyperclip if installed
        try:
            import pyperclip  # type: ignore

            text = pyperclip.paste()
            return HostCapabilityResult(
                success=True,
                capability=HostCapabilityType.CLIPBOARD,
                action="read_clipboard",
                output=text,
            )
        except Exception:
            pass

        # Fallback to PowerShell Get-Clipboard
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            text = res.stdout.strip()
            return HostCapabilityResult(
                success=True,
                capability=HostCapabilityType.CLIPBOARD,
                action="read_clipboard",
                output=text,
            )
        except Exception as exc:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.CLIPBOARD,
                action="read_clipboard",
                error=str(exc),
            )

    def write_clipboard(self, text: str) -> HostCapabilityResult:
        try:
            import pyperclip  # type: ignore

            pyperclip.copy(text)
            return HostCapabilityResult(
                success=True,
                capability=HostCapabilityType.CLIPBOARD,
                action="write_clipboard",
                output=True,
            )
        except Exception:
            pass

        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $input"],
                input=text,
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            return HostCapabilityResult(
                success=res.returncode == 0,
                capability=HostCapabilityType.CLIPBOARD,
                action="write_clipboard",
                output=res.returncode == 0,
                error=res.stderr.strip() if res.returncode != 0 else None,
            )
        except Exception as exc:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.CLIPBOARD,
                action="write_clipboard",
                error=str(exc),
            )

    def get_diagnostics(self) -> HostCapabilityResult:
        try:
            total, used, free = shutil.disk_usage(os.getcwd())
            diag = {
                "os": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "python_version": sys.version.split()[0],
                "cpu_count": os.cpu_count() or 1,
                "disk": {
                    "total_gb": round(total / (1024**3), 2),
                    "used_gb": round(used / (1024**3), 2),
                    "free_gb": round(free / (1024**3), 2),
                },
            }
            return HostCapabilityResult(
                success=True,
                capability=HostCapabilityType.DIAGNOSTICS,
                action="get_diagnostics",
                output=diag,
            )
        except Exception as exc:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.DIAGNOSTICS,
                action="get_diagnostics",
                error=str(exc),
            )

    def send_notification(self, title: str, message: str) -> HostCapabilityResult:
        # Inspectable and deterministic desktop notification attempt
        try:
            ps_script = f"""
            [reflection.assembly]::loadwithpartialname('System.Windows.Forms') | Out-Null
            $notify = new-object system.windows.forms.notifyicon
            $notify.icon = [system.drawing.systemicons]::information
            $notify.balloontiptitle = '{title}'
            $notify.balloontiptext = '{message}'
            $notify.visible = $true
            $notify.showballoontip(3000)
            """
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            return HostCapabilityResult(
                success=True,
                capability=HostCapabilityType.NOTIFICATION,
                action="send_notification",
                output=True,
                metadata={"title": title, "message": message},
            )
        except Exception as exc:
            _log.warning(f"Failed to send notification: {exc}")
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.NOTIFICATION,
                action="send_notification",
                error=str(exc),
            )

    def run_command(
        self,
        command: list[str],
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> HostCapabilityResult:
        try:
            res = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return HostCapabilityResult(
                success=res.returncode == 0,
                capability=HostCapabilityType.PROCESS,
                action="run_command",
                output={
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "exit_code": res.returncode,
                },
                metadata={"command": command, "cwd": cwd},
            )
        except subprocess.TimeoutExpired as exc:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.PROCESS,
                action="run_command",
                error=f"Command timed out after {timeout}s",
                metadata={"command": command},
            )
        except Exception as exc:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.PROCESS,
                action="run_command",
                error=str(exc),
                metadata={"command": command},
            )

    def inspect_workspace(self, workspace_path: str) -> HostCapabilityResult:
        p = Path(workspace_path)
        if not p.exists() or not p.is_dir():
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.FILESYSTEM,
                action="inspect_workspace",
                error=f"Workspace path does not exist or is not a directory: {workspace_path}",
            )

        try:
            entries = []
            for item in p.iterdir():
                entries.append(
                    {
                        "name": item.name,
                        "is_dir": item.is_dir(),
                        "size_bytes": item.stat().st_size if item.is_file() else None,
                    }
                )
            return HostCapabilityResult(
                success=True,
                capability=HostCapabilityType.FILESYSTEM,
                action="inspect_workspace",
                output={"path": str(p), "entries": entries[:200]},
                metadata={"total_count": len(entries)},
            )
        except Exception as exc:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.FILESYSTEM,
                action="inspect_workspace",
                error=str(exc),
            )

    def git_status(self, repo_path: str) -> HostCapabilityResult:
        return self.run_command(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            timeout=10.0,
        )


class LinuxHostCapabilityProvider(HostCapabilityProvider):
    """Linux/Omarchy reference host capability implementation."""

    def get_supported_capabilities(self) -> list[HostCapabilityType]:
        return list(HostCapabilityType)

    def read_clipboard(self) -> HostCapabilityResult:
        tool = shutil.which("wl-paste") or shutil.which("xclip")
        if not tool:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.CLIPBOARD,
                action="read_clipboard",
                error="No clipboard utility (wl-paste or xclip) found on Linux host",
            )
        cmd = [tool] if "wl-paste" in tool else [tool, "-selection", "clipboard", "-o"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
            return HostCapabilityResult(
                success=res.returncode == 0,
                capability=HostCapabilityType.CLIPBOARD,
                action="read_clipboard",
                output=res.stdout.strip(),
            )
        except Exception as exc:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.CLIPBOARD,
                action="read_clipboard",
                error=str(exc),
            )

    def write_clipboard(self, text: str) -> HostCapabilityResult:
        tool = shutil.which("wl-copy") or shutil.which("xclip")
        if not tool:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.CLIPBOARD,
                action="write_clipboard",
                error="No clipboard utility (wl-copy or xclip) found on Linux host",
            )
        cmd = [tool] if "wl-copy" in tool else [tool, "-selection", "clipboard"]
        try:
            res = subprocess.run(cmd, input=text, capture_output=True, text=True, timeout=5.0)
            return HostCapabilityResult(
                success=res.returncode == 0,
                capability=HostCapabilityType.CLIPBOARD,
                action="write_clipboard",
                output=res.returncode == 0,
            )
        except Exception as exc:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.CLIPBOARD,
                action="write_clipboard",
                error=str(exc),
            )

    def get_diagnostics(self) -> HostCapabilityResult:
        try:
            total, used, free = shutil.disk_usage(os.getcwd())
            diag = {
                "os": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "python_version": sys.version.split()[0],
                "cpu_count": os.cpu_count() or 1,
                "disk": {
                    "total_gb": round(total / (1024**3), 2),
                    "used_gb": round(used / (1024**3), 2),
                    "free_gb": round(free / (1024**3), 2),
                },
            }
            return HostCapabilityResult(
                success=True,
                capability=HostCapabilityType.DIAGNOSTICS,
                action="get_diagnostics",
                output=diag,
            )
        except Exception as exc:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.DIAGNOSTICS,
                action="get_diagnostics",
                error=str(exc),
            )

    def send_notification(self, title: str, message: str) -> HostCapabilityResult:
        notify_send = shutil.which("notify-send")
        if not notify_send:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.NOTIFICATION,
                action="send_notification",
                error="notify-send binary not found",
            )
        try:
            res = subprocess.run([notify_send, title, message], capture_output=True, text=True, timeout=5.0)
            return HostCapabilityResult(
                success=res.returncode == 0,
                capability=HostCapabilityType.NOTIFICATION,
                action="send_notification",
                output=res.returncode == 0,
            )
        except Exception as exc:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.NOTIFICATION,
                action="send_notification",
                error=str(exc),
            )

    def run_command(
        self,
        command: list[str],
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> HostCapabilityResult:
        try:
            res = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return HostCapabilityResult(
                success=res.returncode == 0,
                capability=HostCapabilityType.PROCESS,
                action="run_command",
                output={
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                    "exit_code": res.returncode,
                },
                metadata={"command": command, "cwd": cwd},
            )
        except Exception as exc:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.PROCESS,
                action="run_command",
                error=str(exc),
            )

    def inspect_workspace(self, workspace_path: str) -> HostCapabilityResult:
        p = Path(workspace_path)
        if not p.exists() or not p.is_dir():
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.FILESYSTEM,
                action="inspect_workspace",
                error=f"Directory does not exist: {workspace_path}",
            )
        try:
            entries = [{"name": item.name, "is_dir": item.is_dir()} for item in p.iterdir()]
            return HostCapabilityResult(
                success=True,
                capability=HostCapabilityType.FILESYSTEM,
                action="inspect_workspace",
                output={"path": str(p), "entries": entries[:200]},
            )
        except Exception as exc:
            return HostCapabilityResult(
                success=False,
                capability=HostCapabilityType.FILESYSTEM,
                action="inspect_workspace",
                error=str(exc),
            )

    def git_status(self, repo_path: str) -> HostCapabilityResult:
        return self.run_command(["git", "status", "--porcelain"], cwd=repo_path, timeout=10.0)


class KToolsNeoCapabilityAdapter(HostCapabilityProvider):
    """Adapter for K-Tools-Neo capability provider.

    Adapts candidate external Windows/host automation tool without becoming a hard
    dependency or a second control plane. Delegates to fallback native provider if ktools
    is not installed.
    """

    def __init__(self, fallback_provider: Optional[HostCapabilityProvider] = None) -> None:
        self.fallback = fallback_provider or (
            WindowsHostCapabilityProvider() if sys.platform == "win32" else LinuxHostCapabilityProvider()
        )
        self.ktools_executable = shutil.which("ktools")

    def is_available(self) -> bool:
        return self.ktools_executable is not None

    def get_supported_capabilities(self) -> list[HostCapabilityType]:
        return self.fallback.get_supported_capabilities()

    def read_clipboard(self) -> HostCapabilityResult:
        if self.is_available():
            try:
                res = subprocess.run(["ktools", "clipboard", "get"], capture_output=True, text=True, timeout=5.0)
                if res.returncode == 0:
                    return HostCapabilityResult(
                        success=True,
                        capability=HostCapabilityType.CLIPBOARD,
                        action="ktools_read_clipboard",
                        output=res.stdout.strip(),
                        metadata={"provider": "k-tools-neo"},
                    )
            except Exception as exc:
                _log.debug(f"ktools clipboard failed, falling back: {exc}")
        return self.fallback.read_clipboard()

    def write_clipboard(self, text: str) -> HostCapabilityResult:
        if self.is_available():
            try:
                res = subprocess.run(["ktools", "clipboard", "set", text], capture_output=True, text=True, timeout=5.0)
                if res.returncode == 0:
                    return HostCapabilityResult(
                        success=True,
                        capability=HostCapabilityType.CLIPBOARD,
                        action="ktools_write_clipboard",
                        output=True,
                        metadata={"provider": "k-tools-neo"},
                    )
            except Exception as exc:
                _log.debug(f"ktools clipboard set failed, falling back: {exc}")
        return self.fallback.write_clipboard(text)

    def get_diagnostics(self) -> HostCapabilityResult:
        res = self.fallback.get_diagnostics()
        if res.success and isinstance(res.output, dict):
            res.output["ktools_installed"] = self.is_available()
        return res

    def send_notification(self, title: str, message: str) -> HostCapabilityResult:
        return self.fallback.send_notification(title, message)

    def run_command(
        self,
        command: list[str],
        cwd: str | None = None,
        timeout: float = 30.0,
    ) -> HostCapabilityResult:
        return self.fallback.run_command(command, cwd=cwd, timeout=timeout)

    def inspect_workspace(self, workspace_path: str) -> HostCapabilityResult:
        return self.fallback.inspect_workspace(workspace_path)

    def git_status(self, repo_path: str) -> HostCapabilityResult:
        return self.fallback.git_status(repo_path)


def get_host_capability_provider(provider_type: str = "auto") -> HostCapabilityProvider:
    """Factory to retrieve the appropriate host capability provider."""
    if provider_type == "ktools":
        return KToolsNeoCapabilityAdapter()
    if provider_type == "windows" or (provider_type == "auto" and sys.platform == "win32"):
        return WindowsHostCapabilityProvider()
    return LinuxHostCapabilityProvider()

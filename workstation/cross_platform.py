from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import logging
import platform
import sys
from typing import Any, Dict, List, Optional

from workstation.host import (
    HostCapabilityProvider,
    HostCapabilityType,
    LinuxHostCapabilityProvider,
    WindowsHostCapabilityProvider,
    get_host_capability_provider,
)
from workstation.omarchy import OmarchyAdapter

_log = logging.getLogger(__name__)


class HostPlatformKind(str, Enum):
    WINDOWS = "windows"
    LINUX = "linux"
    DARWIN = "darwin"
    UNKNOWN = "unknown"


def detect_host_platform() -> HostPlatformKind:
    sys_plat = sys.platform.lower()
    if sys_plat.startswith("win"):
        return HostPlatformKind.WINDOWS
    if sys_plat.startswith("linux"):
        return HostPlatformKind.LINUX
    if sys_plat.startswith("darwin"):
        return HostPlatformKind.DARWIN
    return HostPlatformKind.UNKNOWN


@dataclass(slots=True)
class BenchmarkEntry:
    harness_id: str
    name: str
    problem_solved: str
    hermes_has_problem: bool
    expressible_in_hermes: bool
    upstream_delta_safe: bool
    notes: str


class AgenticBenchmarkRegistry:
    """Maintains architectural reference tracking against external agentic desktop/workstation environments.

    Tracks Omarchy, Hermes upstream, OpenHands, OpenCode, Claude Code, Codex, Antigravity, and BrowserOS.
    """

    def __init__(self) -> None:
        self._entries: dict[str, BenchmarkEntry] = {}
        self._load_default_benchmarks()

    def _load_default_benchmarks(self) -> None:
        defaults = [
            BenchmarkEntry(
                harness_id="omarchy",
                name="Omarchy Linux OS",
                problem_solved="System-level coding agent default and unified CLI launcher on Linux",
                hermes_has_problem=True,
                expressible_in_hermes=True,
                upstream_delta_safe=True,
                notes="Integrated via OmarchyAdapter without distro-specific file hacking",
            ),
            BenchmarkEntry(
                harness_id="upstream-hermes",
                name="Hermes Upstream",
                problem_solved="Narrow-waist agent loop, multi-platform gateway, skills and prompt caching",
                hermes_has_problem=False,
                expressible_in_hermes=True,
                upstream_delta_safe=True,
                notes="Authoritative base; Workstation preserves canonical prompt caching and invariants",
            ),
            BenchmarkEntry(
                harness_id="openhands",
                name="OpenHands",
                problem_solved="Containerized sandbox environment for arbitrary coding agents",
                hermes_has_problem=True,
                expressible_in_hermes=True,
                upstream_delta_safe=True,
                notes="Adapted via ScopedPolicyEngine and terminal environments",
            ),
            BenchmarkEntry(
                harness_id="opencode",
                name="OpenCode",
                problem_solved="Terminal-native code generation and git workflow execution",
                hermes_has_problem=True,
                expressible_in_hermes=True,
                upstream_delta_safe=True,
                notes="Registered as worker in WorkerRegistry",
            ),
            BenchmarkEntry(
                harness_id="claude-code",
                name="Claude Code",
                problem_solved="High-iteration CLI terminal refactoring agent",
                hermes_has_problem=True,
                expressible_in_hermes=True,
                upstream_delta_safe=True,
                notes="Delegated bounded subtasks via WorkerRegistry without replacing Hermes conductor",
            ),
            BenchmarkEntry(
                harness_id="codex",
                name="Codex CLI",
                problem_solved="Deterministic code generation harness",
                hermes_has_problem=True,
                expressible_in_hermes=True,
                upstream_delta_safe=True,
                notes="Delegated bounded subtasks via WorkerRegistry",
            ),
            BenchmarkEntry(
                harness_id="antigravity",
                name="Google Antigravity Agent",
                problem_solved="Pair-programming agent with subagents, TDD discipline, and artifacts",
                hermes_has_problem=True,
                expressible_in_hermes=True,
                upstream_delta_safe=True,
                notes="Full subagent/worker integration with execution journal evidence",
            ),
            BenchmarkEntry(
                harness_id="browseros",
                name="BrowserOS / BrowserClaw",
                problem_solved="Agent-dedicated persistent browser with live user profiles and accounts",
                hermes_has_problem=True,
                expressible_in_hermes=True,
                upstream_delta_safe=True,
                notes="Hermes Workstation Chromium internal runtime matches persistent profile model",
            ),
        ]
        for b in defaults:
            self._entries[b.harness_id] = b

    def list_benchmarks(self) -> list[BenchmarkEntry]:
        return list(self._entries.values())

    def get_benchmark(self, harness_id: str) -> Optional[BenchmarkEntry]:
        return self._entries.get(harness_id)

    def to_matrix(self) -> list[dict[str, Any]]:
        return [asdict(e) for e in self._entries.values()]


class CrossPlatformHostManager:
    """Coordinates host capability providers and reference adapters across Windows and Linux."""

    def __init__(self, platform_kind: Optional[HostPlatformKind] = None) -> None:
        self.platform_kind = platform_kind or detect_host_platform()
        self.omarchy = OmarchyAdapter()
        self.benchmark_registry = AgenticBenchmarkRegistry()

    def get_capability_provider(self) -> HostCapabilityProvider:
        if self.platform_kind == HostPlatformKind.WINDOWS:
            return WindowsHostCapabilityProvider()
        return LinuxHostCapabilityProvider()

    def is_omarchy(self) -> bool:
        return self.omarchy.detect().is_omarchy

    def get_host_summary(self) -> dict[str, Any]:
        provider = self.get_capability_provider()
        diag = provider.get_diagnostics()
        return {
            "platform": self.platform_kind.value,
            "is_omarchy": self.is_omarchy(),
            "diagnostics": diag.output if diag.success else None,
            "supported_capabilities": [c.value for c in provider.get_supported_capabilities()],
        }

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import logging
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Optional

from workstation.events import SystemEvent, SystemEventPipeline

_log = logging.getLogger(__name__)


@dataclass(slots=True)
class OmarchyHostProfile:
    """Omarchy Linux reference host integration contract.

    Treats Omarchy as an architectural benchmark and Linux integration target,
    normalizing launcher, system skills, and host events without distro-specific file hacking.
    """

    is_omarchy: bool = False
    version: Optional[str] = None
    default_coding_agent: Optional[str] = None
    available_skills: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class OmarchyAdapter:
    """Adapter for the Omarchy Linux reference environment."""

    def __init__(self, event_pipeline: Optional[SystemEventPipeline] = None) -> None:
        self.event_pipeline = event_pipeline
        self._profile: Optional[OmarchyHostProfile] = None

    def detect(self) -> OmarchyHostProfile:
        """Detect if running under Omarchy or a compatible Linux desktop."""
        if self._profile is not None:
            return self._profile

        is_omarchy = False
        version = None
        default_agent = None

        if os.getenv("OMARCHY_HOST") == "1":
            is_omarchy = True
            version = os.getenv("OMARCHY_VERSION", "1.0-dev")

        release_file = Path("/etc/omarchy-release")
        if release_file.exists():
            is_omarchy = True
            try:
                version = release_file.read_text(encoding="utf-8").strip()
            except Exception:
                version = "unknown"

        # Default coding agent probe
        for cand in ("agy", "claude", "codex", "opencode", "hermes"):
            if shutil.which(cand):
                default_agent = cand
                break

        # Discover system skills
        skills = []
        skills_dir = Path("/usr/share/omarchy/skills")
        if skills_dir.exists() and skills_dir.is_dir():
            for p in skills_dir.glob("*.md"):
                skills.append(p.stem)

        self._profile = OmarchyHostProfile(
            is_omarchy=is_omarchy,
            version=version,
            default_coding_agent=default_agent,
            available_skills=skills,
        )
        return self._profile

    def launch_agent(
        self,
        agent_binary: str,
        prompt: str,
        *,
        timeout: float = 60.0,
    ) -> dict[str, Any]:
        """Normalized launcher over heterogeneous agent CLIs on Linux."""
        exe = shutil.which(agent_binary)
        if not exe:
            return {
                "success": False,
                "error": f"Agent executable '{agent_binary}' not found on host",
            }

        try:
            res = subprocess.run(
                [exe, prompt],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": res.returncode == 0,
                "stdout": res.stdout,
                "stderr": res.stderr,
                "exit_code": res.returncode,
            }
        except Exception as exc:
            return {
                "success": False,
                "error": str(exc),
            }

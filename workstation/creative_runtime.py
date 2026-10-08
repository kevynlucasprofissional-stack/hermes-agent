"""Passive Creative engine discovery, projected through existing runtime capabilities.

Presence never implies health, license clearance, or execution authority. This module
does not install, launch, import vendor packages, or maintain process state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from hermes_platform.resolver import LookupContext, locate_command
from workstation.config import WorkstationConfig


EngineId = Literal["ffmpeg", "ffprobe", "node", "inkscape", "blender"]
ENGINE_COMMANDS: tuple[EngineId, ...] = ("ffmpeg", "ffprobe", "node", "inkscape", "blender")


@dataclass(frozen=True, slots=True)
class CreativeEngineObservation:
    engine: EngineId
    status: Literal["disabled", "present", "missing"]
    executable: str | None = None
    source: str = "none"
    version: None = None
    health: Literal["not_checked"] = "not_checked"

    def to_dict(self) -> dict:
        return asdict(self)


def inspect_creative_engines(
    config: WorkstationConfig, *, context: LookupContext | None = None
) -> tuple[CreativeEngineObservation, ...]:
    """Resolve local executables only when explicitly enabled by the caller's config.

    Version and service health require a separately admitted diagnostic operation;
    finding a binary on PATH must not run code merely to display availability.
    """
    if not config.creative_enabled:
        return tuple(CreativeEngineObservation(engine, "disabled") for engine in ENGINE_COMMANDS)
    observations = []
    for engine in ENGINE_COMMANDS:
        resolution = locate_command(engine, context)
        observations.append(CreativeEngineObservation(
            engine=engine,
            status="present" if resolution.found else "missing",
            executable=resolution.command[0] if resolution.found else None,
            source=resolution.source,
        ))
    return tuple(observations)

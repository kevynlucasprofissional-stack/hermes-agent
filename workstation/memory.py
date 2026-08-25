from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProceduralMemoryResult(str, Enum):
    FOUND = "found"
    MISS = "miss"
    BROKEN = "broken"


@dataclass(slots=True)
class WebProcedure:
    name: str
    site: str
    intent: str
    side_effect: str
    version: int = 1


class ProceduralMemory:
    """V2 boundary inspired by browser-memory: discover -> run -> explore -> learn."""

    def discover(self, site: str, goal: str) -> list[WebProcedure]:
        return []

    def record_success(self, site: str, goal: str, journal_id: str) -> None:
        return None

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class PerceptionView:
    snapshot_id: str
    view: str
    payload: dict[str, Any]
    estimated_tokens: int
    truncated: bool = False


class PerceptionEngine:
    """V2 boundary for compact, provenance-aware browser perception."""

    def summarize(self, raw_capture: dict[str, Any], token_budget: int) -> PerceptionView:
        raise NotImplementedError

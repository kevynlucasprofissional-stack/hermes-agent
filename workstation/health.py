from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum


class ComponentState(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class WorkstationHealth:
    hermes_gateway: ComponentState = ComponentState.UNKNOWN
    desktop: ComponentState = ComponentState.UNKNOWN
    browser_runtime: ComponentState = ComponentState.UNKNOWN
    browser_controller: ComponentState = ComponentState.UNKNOWN
    kanban: ComponentState = ComponentState.UNKNOWN
    dashboard_lan: ComponentState = ComponentState.UNKNOWN

    def to_dict(self) -> dict[str, str]:
        return {key: value.value for key, value in asdict(self).items()}

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PATH = Path(__file__).with_name("workstation.yaml")


@dataclass(frozen=True, slots=True)
class WorkstationConfig:
    raw: dict[str, Any]

    @property
    def enabled(self) -> bool:
        return bool(self.raw.get("workstation", {}).get("enabled", True))

    @property
    def browser_routing_enabled(self) -> bool:
        return bool(self.raw.get("browser", {}).get("routing", {}).get("enabled", True))

    @property
    def lan_enabled(self) -> bool:
        return bool(self.raw.get("lan", {}).get("enabled", False))

    @property
    def lan_requires_auth(self) -> bool:
        return bool(self.raw.get("lan", {}).get("require_auth", True))


def load_workstation_config(path: Path | str = DEFAULT_PATH) -> WorkstationConfig:
    target = Path(path)
    data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError("workstation.yaml must contain a mapping")
    cfg = WorkstationConfig(data)
    if cfg.lan_enabled and not cfg.lan_requires_auth:
        raise ValueError("Hermes Workstation refuses LAN mode without authentication")
    return cfg

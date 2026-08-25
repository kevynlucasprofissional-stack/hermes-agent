from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class BrowserRuntimeKind(str, Enum):
    ELECTRON_CHROMIUM = "electron-chromium"
    LIGHTPANDA = "lightpanda"
    AGENT_BROWSER = "agent-browser"
    BROWSER_EXEC = "browser-exec"


@dataclass(frozen=True, slots=True)
class BrowserRuntimeCapabilities:
    persistent_profile: bool
    visible: bool
    background: bool
    cdp: bool
    screenshots: bool
    task_binding: bool


class BrowserRuntime(ABC):
    """Cross-runtime contract. Electron implementation lives in apps/desktop."""

    kind: BrowserRuntimeKind

    @abstractmethod
    def capabilities(self) -> BrowserRuntimeCapabilities: ...

    @abstractmethod
    def health(self) -> dict: ...

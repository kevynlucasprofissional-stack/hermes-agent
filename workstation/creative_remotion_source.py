"""Typed invitation source for the first external Remotion adapter."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from pathlib import Path
import re


def remotion_native_files() -> dict[str, bytes]:
    root = Path(__file__).parent / "creative_templates" / "remotion"
    return {name: (root / name).read_bytes() for name in ("Invitation.tsx", "index.tsx", "package.json")}


@dataclass(frozen=True)
class RemotionInvitation:
    title: str
    subtitle: str
    footer: str
    background: str = "#14263d"
    foreground: str = "#ffffff"
    accent: str = "#f6c85f"
    width: int = 360
    height: int = 640
    fps: int = 30
    duration_seconds: int = 8
    logo_radius: float = 62

    def validate(self) -> None:
        for text in (self.title, self.subtitle, self.footer):
            if (not isinstance(text, str) or not text.strip() or len(text) > 160
                    or any(ord(character) < 32 for character in text)):
                raise ValueError("Invalid Remotion invitation text")
        for color in (self.background, self.foreground, self.accent):
            if not isinstance(color, str) or re.fullmatch(r"#[0-9a-fA-F]{6}", color) is None:
                raise ValueError("Remotion invitation colors must be hex RGB")
        if (type(self.width) is not int or type(self.height) is not int
                or not 32 <= self.width <= 4096 or not 32 <= self.height <= 4096
                or self.width % 2 or self.height % 2 or self.width * self.height > 8_000_000):
            raise ValueError("Remotion invitation dimensions exceed budget")
        if (type(self.fps) is not int or self.fps not in {15, 24, 25, 30, 60}
                or type(self.duration_seconds) is not int or not 1 <= self.duration_seconds <= 30
                or self.fps * self.duration_seconds > 1800):
            raise ValueError("Remotion invitation timeline exceeds budget")
        if (type(self.logo_radius) not in {float, int} or not math.isfinite(self.logo_radius)
                or not 1 <= self.logo_radius <= min(self.width, self.height) / 3):
            raise ValueError("Remotion invitation logo radius exceeds canvas")

    def to_source(self) -> dict:
        self.validate()
        return {"schema_version": 1, "template": "invitation-v1", "props": asdict(self)}

    @classmethod
    def from_source(cls, source: dict) -> RemotionInvitation:
        if (not isinstance(source, dict) or set(source) != {"schema_version", "template", "props"}
                or type(source["schema_version"]) is not int or source["schema_version"] != 1
                or source["template"] != "invitation-v1" or not isinstance(source["props"], dict)):
            raise ValueError("Invalid Remotion invitation source")
        try:
            result = cls(**source["props"])
        except TypeError as error:
            raise ValueError("Unknown or missing Remotion invitation property") from error
        result.validate()
        return result

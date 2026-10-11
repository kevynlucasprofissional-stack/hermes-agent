"""Freeform scene capability adapters for SVG, Canvas 2D, Three.js, and AV media (CWN-05)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from html import escape
import math
from pathlib import Path
import re
from typing import Any

from workstation.creative_document import (
    Asset,
    Clip,
    Composition,
    CreativeDocument,
    Keyframe,
    Layer,
)
from workstation.creative_time import (
    CanonicalTime,
    MediaTimeMap,
    RationalFps,
)


class SecuritySandboxError(ValueError):
    """Raised when an asset path escapes the workspace or contains malicious scripts."""
    pass


_FORBIDDEN_SVG_TAGS = re.compile(r"<\s*(script|iframe|object|embed|applet)", re.IGNORECASE)
_FORBIDDEN_EVENT_ATTRS = re.compile(r"\s+on[a-z]+\s*=", re.IGNORECASE)
_FORBIDDEN_SCHEMES = re.compile(r"(javascript:|data:\s*text/html)", re.IGNORECASE)


def sanitize_svg_text(text: str) -> str:
    """Sanitize text injected into SVG DOM, removing dangerous tags and scripts."""
    clean = _FORBIDDEN_SVG_TAGS.sub("", text)
    clean = _FORBIDDEN_EVENT_ATTRS.sub(" data-blocked-on=", clean)
    clean = _FORBIDDEN_SCHEMES.sub("blocked:", clean)
    return clean


def _interpolate_keyframes(keyframes: list[Keyframe], prop_path: str, t: CanonicalTime, default_val: Any) -> Any:
    kfs = [k for k in keyframes if k.property_path == prop_path]
    if not kfs:
        return default_val
    kfs.sort(key=lambda k: k.time)
    if t <= kfs[0].time:
        return kfs[0].value
    if t >= kfs[-1].time:
        return kfs[-1].value

    # Find bounding keyframes
    for i in range(len(kfs) - 1):
        k1, k2 = kfs[i], kfs[i + 1]
        if k1.time <= t <= k2.time:
            # Linear interpolation for numeric values
            if isinstance(k1.value, (int, float)) and isinstance(k2.value, (int, float)):
                t_span = float((k2.time - k1.time).to_seconds())
                if t_span <= 0:
                    return k1.value
                progress = float((t - k1.time).to_seconds()) / t_span
                return k1.value + (k2.value - k1.value) * progress
            return k1.value
    return default_val


@dataclass
class RenderContext:
    workspace_root: Path | None = None
    fps: RationalFps = field(default_factory=lambda: RationalFps(30, 1))
    random_seed: int = 42


class SceneAdapter(ABC):
    """Base interface for all rendering and scene capability adapters."""

    @abstractmethod
    def render_at(self, t: CanonicalTime, frame_idx: int, ctx: RenderContext) -> dict[str, Any]:
        """Deterministically evaluate node state at time t and discrete frame_idx."""
        pass


class SvgVectorAdapter(SceneAdapter):
    def __init__(self, layer: Layer):
        self.layer = layer

    def render_at(self, t: CanonicalTime, frame_idx: int, ctx: RenderContext) -> dict[str, Any]:
        opacity = _interpolate_keyframes(self.layer.keyframes, "transform.opacity", t, self.layer.transform.get("opacity", 1.0))
        x = _interpolate_keyframes(self.layer.keyframes, "transform.x", t, self.layer.transform.get("x", 0.0))
        y = _interpolate_keyframes(self.layer.keyframes, "transform.y", t, self.layer.transform.get("y", 0.0))

        raw_text = str(self.layer.declared_parameters.get("text", self.layer.name))
        safe_text = sanitize_svg_text(raw_text)
        color = str(self.layer.declared_parameters.get("color", "#ffffff"))
        font_size = self.layer.declared_parameters.get("font_size", 32)

        markup = (
            f'<text x="{x}" y="{y}" fill="{color}" font-size="{font_size}" '
            f'opacity="{opacity}">{escape(safe_text)}</text>'
        )

        return {
            "layer_id": self.layer.layer_id,
            "kind": "vector_svg",
            "transform": {"x": x, "y": y, "opacity": opacity},
            "parameters": dict(self.layer.declared_parameters),
            "rendered_markup": markup,
        }


class CanvasEffectAdapter(SceneAdapter):
    def __init__(self, layer: Layer):
        self.layer = layer

    def render_at(self, t: CanonicalTime, frame_idx: int, ctx: RenderContext) -> dict[str, Any]:
        params = dict(self.layer.declared_parameters)
        # Deterministic seed calculation prevents wall-clock drift
        seed = (ctx.random_seed + frame_idx) % 2147483647
        return {
            "layer_id": self.layer.layer_id,
            "kind": "html_canvas",
            "is_opaque": self.layer.is_opaque(),
            "opaque_code": self.layer.opaque_code,
            "parameters": params,
            "deterministic_seed": seed,
            "transform": dict(self.layer.transform),
        }


class ThreeJsSceneAdapter(SceneAdapter):
    def __init__(self, layer: Layer, asset: Asset | None = None):
        self.layer = layer
        self.asset = asset

    def render_at(self, t: CanonicalTime, frame_idx: int, ctx: RenderContext) -> dict[str, Any]:
        params = dict(self.layer.declared_parameters)
        rot_speed = float(params.get("rotation_speed", 1.0))
        angle_rad = (float(t.to_seconds()) * rot_speed) % (2 * math.pi)

        return {
            "layer_id": self.layer.layer_id,
            "kind": "three_js_scene",
            "asset_id": self.asset.asset_id if self.asset else None,
            "asset_path": self.asset.path if self.asset else None,
            "camera_position": list(params.get("camera_position", [0, 0, 5])),
            "fov": params.get("fov", 60),
            "rotation_y_radians": round(angle_rad, 4),
            "transform": dict(self.layer.transform),
        }


class AudioVisualMediaAdapter(SceneAdapter):
    def __init__(self, clip: Clip, asset: Asset | None = None):
        self.clip = clip
        self.asset = asset
        self.time_map = MediaTimeMap(clip.timeline_range, clip.source_in, clip.speed)

    def render_at(self, t: CanonicalTime, frame_idx: int, ctx: RenderContext) -> dict[str, Any]:
        source_time = self.time_map.timeline_to_source(t)
        return {
            "clip_id": self.clip.clip_id,
            "asset_id": self.clip.asset_id,
            "asset_path": self.asset.path if self.asset else "",
            "source_time_seconds": float(source_time.to_seconds()),
            "source_frame": source_time.to_frame(ctx.fps),
            "speed": self.clip.speed,
        }


@dataclass
class CompositeFrameState:
    time: CanonicalTime
    frame_index: int
    layer_nodes: dict[str, dict[str, Any]]
    clip_nodes: dict[str, dict[str, Any]]

    def get_layer_node(self, layer_id: str) -> dict[str, Any]:
        return self.layer_nodes[layer_id]

    def get_clip_node(self, clip_id: str) -> dict[str, Any]:
        return self.clip_nodes[clip_id]


class CompositeScene:
    """Manages multi-engine scene evaluation for a composition at arbitrary frames."""

    def __init__(
        self,
        composition: Composition,
        adapters: list[tuple[str, str, SceneAdapter]],  # (node_type, id, adapter)
        ctx: RenderContext,
    ):
        self.composition = composition
        self.adapters = adapters
        self.ctx = ctx

    @classmethod
    def from_composition(
        cls,
        comp: Composition,
        assets: dict[str, Asset],
        workspace_root: str | None = None,
    ) -> CompositeScene:
        root_path = Path(workspace_root).resolve() if workspace_root else None

        # Verify asset path security fences
        for a_id, asset in assets.items():
            if ".." in asset.path or asset.path.startswith("/") or (len(asset.path) > 1 and asset.path[1] == ":"):
                if root_path:
                    try:
                        resolved = (root_path / asset.path).resolve()
                        if not resolved.is_relative_to(root_path):
                            raise SecuritySandboxError(f"Path traversal detected in asset {a_id}: {asset.path}")
                    except (ValueError, RuntimeError) as e:
                        raise SecuritySandboxError(f"Path traversal detected: {e}") from e
                else:
                    raise SecuritySandboxError(f"Path traversal detected in asset {a_id}: {asset.path}")

        ctx = RenderContext(workspace_root=root_path, fps=comp.fps)
        adapters: list[tuple[str, str, SceneAdapter]] = []

        # Layer adapters
        for layer in comp.layers:
            if layer.kind == "vector_svg":
                adapters.append(("layer", layer.layer_id, SvgVectorAdapter(layer)))
            elif layer.kind == "html_canvas":
                adapters.append(("layer", layer.layer_id, CanvasEffectAdapter(layer)))
            elif layer.kind == "three_js_scene":
                asset_id = layer.declared_parameters.get("asset_id")
                asset = assets.get(asset_id) if asset_id else None
                adapters.append(("layer", layer.layer_id, ThreeJsSceneAdapter(layer, asset)))

        # Clip adapters
        for track in comp.tracks:
            for clip in track.clips:
                asset = assets.get(clip.asset_id)
                adapters.append(("clip", clip.clip_id, AudioVisualMediaAdapter(clip, asset)))

        return cls(comp, adapters, ctx)

    def seek(self, t: CanonicalTime) -> CompositeFrameState:
        """Deterministically evaluate all layers and active clips at time t."""
        frame_idx = t.to_frame(self.ctx.fps)
        layer_nodes: dict[str, dict[str, Any]] = {}
        clip_nodes: dict[str, dict[str, Any]] = {}

        for kind, node_id, adapter in self.adapters:
            if kind == "layer":
                layer_nodes[node_id] = adapter.render_at(t, frame_idx, self.ctx)
            elif kind == "clip":
                # Only evaluate clip if time t falls inside its half-open timeline range
                av_adapter: AudioVisualMediaAdapter = adapter  # type: ignore
                if av_adapter.clip.timeline_range.contains(t):
                    clip_nodes[node_id] = av_adapter.render_at(t, frame_idx, self.ctx)

        return CompositeFrameState(
            time=t,
            frame_index=frame_idx,
            layer_nodes=layer_nodes,
            clip_nodes=clip_nodes,
        )

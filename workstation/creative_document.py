"""Engine-neutral Creative Document specification and serialization (CWN-01)."""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import re
from typing import Any
import uuid

from workstation.creative_time import CanonicalTime, RationalFps, TimeRange


class CreativeDocumentError(ValueError):
    """Raised when creative document validation, migration, or schema checks fail."""
    pass


_ID_REGEX = re.compile(r"^[a-f0-9]{32}$")
CURRENT_SCHEMA_VERSION = 1


def _validate_id(identifier: str, field_name: str = "identifier") -> str:
    if not isinstance(identifier, str) or not _ID_REGEX.match(identifier):
        raise CreativeDocumentError(f"Invalid {field_name}: must be a 32-character hexadecimal string, got '{identifier}'")
    return identifier


@dataclass
class Keyframe:
    keyframe_id: str
    property_path: str
    time: CanonicalTime
    value: Any
    easing: str = "linear"

    def __post_init__(self):
        _validate_id(self.keyframe_id, "keyframe_id")


@dataclass
class Layer:
    layer_id: str
    name: str
    kind: str  # "vector_svg", "html_canvas", "three_js_scene", "text", "shape", "nle_clip"
    declared_parameters: dict[str, Any] = field(default_factory=dict)
    opaque_code: str | None = None
    transform: dict[str, Any] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "opacity": 1.0})
    keyframes: list[Keyframe] = field(default_factory=list)

    def __post_init__(self):
        _validate_id(self.layer_id, "layer_id")

    def is_opaque(self) -> bool:
        return bool(self.opaque_code and self.opaque_code.strip())


@dataclass
class Clip:
    clip_id: str
    track_id: str
    asset_id: str
    name: str
    timeline_range: TimeRange
    source_in: CanonicalTime
    speed: float = 1.0
    reverse: bool = False
    freeze: bool = False
    linked_clip_ids: list[str] = field(default_factory=list)
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        _validate_id(self.clip_id, "clip_id")
        _validate_id(self.track_id, "track_id")
        _validate_id(self.asset_id, "asset_id")


@dataclass
class Track:
    track_id: str
    name: str
    kind: str  # "video", "audio", "graphic", "subtitle"
    z_index: int = 0
    locked: bool = False
    muted: bool = False
    solo: bool = False
    clips: list[Clip] = field(default_factory=list)

    def __post_init__(self):
        _validate_id(self.track_id, "track_id")


@dataclass
class Asset:
    asset_id: str
    name: str
    kind: str  # "video", "audio", "image", "vector", "3d_model", "font"
    path: str
    sha256: str
    duration: CanonicalTime | None = None
    width: int | None = None
    height: int | None = None
    sample_rate: int | None = None
    channels: int | None = None

    def __post_init__(self):
        _validate_id(self.asset_id, "asset_id")
        if not self.sha256 or len(self.sha256) != 64:
            raise CreativeDocumentError(f"Asset {self.asset_id} must have a valid 64-char SHA-256 digest")


@dataclass
class Marker:
    marker_id: str
    name: str
    time: CanonicalTime
    color: str = "#ffff00"
    comment: str = ""

    def __post_init__(self):
        _validate_id(self.marker_id, "marker_id")


@dataclass
class Composition:
    composition_id: str
    name: str
    width: int
    height: int
    fps: RationalFps
    duration: CanonicalTime
    sample_rate: int = 48000
    background_color: str = "#000000"
    tracks: list[Track] = field(default_factory=list)
    layers: list[Layer] = field(default_factory=list)
    markers: list[Marker] = field(default_factory=list)

    def __post_init__(self):
        _validate_id(self.composition_id, "composition_id")
        if self.width <= 0 or self.height <= 0:
            raise CreativeDocumentError("Composition dimensions must be strictly positive")


@dataclass
class CreativeDocument:
    project_id: str
    name: str
    schema_version: int = CURRENT_SCHEMA_VERSION
    compositions: list[Composition] = field(default_factory=list)
    assets: dict[str, Asset] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        _validate_id(self.project_id, "project_id")


def create_empty_project(
    name: str = "Untitled Project",
    width: int = 1920,
    height: int = 1080,
    fps: RationalFps = RationalFps(30, 1),
    duration_seconds: float = 60.0,
) -> CreativeDocument:
    """Create a minimal well-formed CreativeDocument."""
    project_id = uuid.uuid4().hex
    comp_id = uuid.uuid4().hex
    comp = Composition(
        composition_id=comp_id,
        name="Main Composition",
        width=width,
        height=height,
        fps=fps,
        duration=CanonicalTime.from_seconds(duration_seconds),
    )
    return CreativeDocument(
        project_id=project_id,
        name=name,
        schema_version=CURRENT_SCHEMA_VERSION,
        compositions=[comp],
        assets={},
    )


def document_to_dict(doc: CreativeDocument) -> dict[str, Any]:
    """Serialize CreativeDocument to a pure JSON-serializable dictionary."""
    return {
        "schema_version": doc.schema_version,
        "project_id": doc.project_id,
        "name": doc.name,
        "metadata": doc.metadata,
        "assets": {
            a_id: {
                "asset_id": asset.asset_id,
                "name": asset.name,
                "kind": asset.kind,
                "path": asset.path,
                "sha256": asset.sha256,
                "duration": str(asset.duration.to_seconds()) if asset.duration else None,
                "width": asset.width,
                "height": asset.height,
                "sample_rate": asset.sample_rate,
                "channels": asset.channels,
            }
            for a_id, asset in doc.assets.items()
        },
        "compositions": [
            {
                "composition_id": comp.composition_id,
                "name": comp.name,
                "width": comp.width,
                "height": comp.height,
                "fps": {"num": comp.fps.numerator, "den": comp.fps.denominator},
                "duration": str(comp.duration.to_seconds()),
                "sample_rate": comp.sample_rate,
                "background_color": comp.background_color,
                "tracks": [
                    {
                        "track_id": trk.track_id,
                        "name": trk.name,
                        "kind": trk.kind,
                        "z_index": trk.z_index,
                        "locked": trk.locked,
                        "muted": trk.muted,
                        "solo": trk.solo,
                        "clips": [
                            {
                                "clip_id": clip.clip_id,
                                "track_id": clip.track_id,
                                "asset_id": clip.asset_id,
                                "name": clip.name,
                                "timeline_range": {
                                    "start": str(clip.timeline_range.start.to_seconds()),
                                    "end": str(clip.timeline_range.end.to_seconds()),
                                },
                                "source_in": str(clip.source_in.to_seconds()),
                                "speed": clip.speed,
                                "reverse": clip.reverse,
                                "freeze": clip.freeze,
                                "linked_clip_ids": clip.linked_clip_ids,
                                "properties": clip.properties,
                            }
                            for clip in trk.clips
                        ],
                    }
                    for trk in comp.tracks
                ],
                "layers": [
                    {
                        "layer_id": layer.layer_id,
                        "name": layer.name,
                        "kind": layer.kind,
                        "declared_parameters": layer.declared_parameters,
                        "opaque_code": layer.opaque_code,
                        "transform": layer.transform,
                        "keyframes": [
                            {
                                "keyframe_id": kf.keyframe_id,
                                "property_path": kf.property_path,
                                "time": str(kf.time.to_seconds()),
                                "value": kf.value,
                                "easing": kf.easing,
                            }
                            for kf in layer.keyframes
                        ],
                    }
                    for layer in comp.layers
                ],
                "markers": [
                    {
                        "marker_id": m.marker_id,
                        "name": m.name,
                        "time": str(m.time.to_seconds()),
                        "color": m.color,
                        "comment": m.comment,
                    }
                    for m in comp.markers
                ],
            }
            for comp in doc.compositions
        ],
    }


def load_document_from_dict(data: dict[str, Any]) -> CreativeDocument:
    """Deserialize and validate CreativeDocument dictionary."""
    if not isinstance(data, dict):
        raise CreativeDocumentError("Document root must be a dictionary")

    version = data.get("schema_version")
    if not isinstance(version, int):
        raise CreativeDocumentError("Missing or invalid schema_version")
    if version > CURRENT_SCHEMA_VERSION:
        raise CreativeDocumentError(f"Unsupported schema_version: {version}")

    project_id = _validate_id(data.get("project_id", ""), "project_id")
    name = str(data.get("name", "Untitled Project"))
    metadata = dict(data.get("metadata", {}))

    # Assets
    assets_raw = data.get("assets", {})
    if not isinstance(assets_raw, dict):
        raise CreativeDocumentError("Assets field must be a dictionary")

    assets: dict[str, Asset] = {}
    for a_id, a_data in assets_raw.items():
        if not isinstance(a_data, dict):
            raise CreativeDocumentError(f"Asset {a_id} must be an object")
        if "inline_data" in a_data or "base64" in a_data:
            raise CreativeDocumentError(f"Inline binary blobs forbidden in asset {a_id}")
        asset_id = _validate_id(a_data.get("asset_id", a_id), "asset_id")
        dur_str = a_data.get("duration")
        assets[asset_id] = Asset(
            asset_id=asset_id,
            name=str(a_data.get("name", "")),
            kind=str(a_data.get("kind", "video")),
            path=str(a_data.get("path", "")),
            sha256=str(a_data.get("sha256", "")),
            duration=CanonicalTime.from_seconds(Fraction(dur_str)) if dur_str else None,
            width=a_data.get("width"),
            height=a_data.get("height"),
            sample_rate=a_data.get("sample_rate"),
            channels=a_data.get("channels"),
        )

    # Compositions
    comps_raw = data.get("compositions", [])
    if not isinstance(comps_raw, list):
        raise CreativeDocumentError("Compositions field must be a list")

    compositions: list[Composition] = []
    for c_data in comps_raw:
        if not isinstance(c_data, dict):
            raise CreativeDocumentError("Composition entry must be an object")
        comp_id = _validate_id(c_data.get("composition_id", ""), "composition_id")
        fps_info = c_data.get("fps", {"num": 30, "den": 1})
        fps = RationalFps(fps_info["num"], fps_info["den"])
        dur_str = c_data.get("duration", "60")
        duration = CanonicalTime.from_seconds(Fraction(dur_str))

        # Tracks & Clips
        tracks: list[Track] = []
        for t_data in c_data.get("tracks", []):
            track_id = _validate_id(t_data.get("track_id", ""), "track_id")
            clips: list[Clip] = []
            for cl_data in t_data.get("clips", []):
                clip_id = _validate_id(cl_data.get("clip_id", ""), "clip_id")
                tr_data = cl_data.get("timeline_range", {})
                t_range = TimeRange(
                    CanonicalTime.from_seconds(Fraction(tr_data["start"])),
                    CanonicalTime.from_seconds(Fraction(tr_data["end"])),
                )
                source_in = CanonicalTime.from_seconds(Fraction(cl_data.get("source_in", "0")))
                clips.append(
                    Clip(
                        clip_id=clip_id,
                        track_id=track_id,
                        asset_id=_validate_id(cl_data.get("asset_id", ""), "asset_id"),
                        name=str(cl_data.get("name", "")),
                        timeline_range=t_range,
                        source_in=source_in,
                        speed=float(cl_data.get("speed", 1.0)),
                        reverse=bool(cl_data.get("reverse", False)),
                        freeze=bool(cl_data.get("freeze", False)),
                        linked_clip_ids=list(cl_data.get("linked_clip_ids", [])),
                        properties=dict(cl_data.get("properties", {})),
                    )
                )
            tracks.append(
                Track(
                    track_id=track_id,
                    name=str(t_data.get("name", "")),
                    kind=str(t_data.get("kind", "video")),
                    z_index=int(t_data.get("z_index", 0)),
                    locked=bool(t_data.get("locked", False)),
                    muted=bool(t_data.get("muted", False)),
                    solo=bool(t_data.get("solo", False)),
                    clips=clips,
                )
            )

        # Layers & Keyframes
        layers: list[Layer] = []
        for l_data in c_data.get("layers", []):
            layer_id = _validate_id(l_data.get("layer_id", ""), "layer_id")
            keyframes: list[Keyframe] = []
            for kf_data in l_data.get("keyframes", []):
                kf_id = _validate_id(kf_data.get("keyframe_id", ""), "keyframe_id")
                keyframes.append(
                    Keyframe(
                        keyframe_id=kf_id,
                        property_path=str(kf_data.get("property_path", "")),
                        time=CanonicalTime.from_seconds(Fraction(kf_data.get("time", "0"))),
                        value=kf_data.get("value"),
                        easing=str(kf_data.get("easing", "linear")),
                    )
                )
            layers.append(
                Layer(
                    layer_id=layer_id,
                    name=str(l_data.get("name", "")),
                    kind=str(l_data.get("kind", "vector_svg")),
                    declared_parameters=dict(l_data.get("declared_parameters", {})),
                    opaque_code=l_data.get("opaque_code"),
                    transform=dict(l_data.get("transform", {"x": 0.0, "y": 0.0, "opacity": 1.0})),
                    keyframes=keyframes,
                )
            )

        # Markers
        markers: list[Marker] = []
        for m_data in c_data.get("markers", []):
            m_id = _validate_id(m_data.get("marker_id", ""), "marker_id")
            markers.append(
                Marker(
                    marker_id=m_id,
                    name=str(m_data.get("name", "")),
                    time=CanonicalTime.from_seconds(Fraction(m_data.get("time", "0"))),
                    color=str(m_data.get("color", "#ffff00")),
                    comment=str(m_data.get("comment", "")),
                )
            )

        compositions.append(
            Composition(
                composition_id=comp_id,
                name=str(c_data.get("name", "Composition")),
                width=int(c_data.get("width", 1920)),
                height=int(c_data.get("height", 1080)),
                fps=fps,
                duration=duration,
                sample_rate=int(c_data.get("sample_rate", 48000)),
                background_color=str(c_data.get("background_color", "#000000")),
                tracks=tracks,
                layers=layers,
                markers=markers,
            )
        )

    return CreativeDocument(
        project_id=project_id,
        name=name,
        schema_version=version,
        compositions=compositions,
        assets=assets,
        metadata=metadata,
    )

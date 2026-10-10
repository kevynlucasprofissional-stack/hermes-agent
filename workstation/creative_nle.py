"""Non-linear video editing (NLE), multi-track timeline, transitions, audio, and SVG design depth.

Provides track and clip management (video, audio, text, vector), trimming with ripple,
splitting, reordering, volume controls, waveform peaks, transitions, and SVG sanitization
embedded directly within native HyperFrames compositions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
import json
import logging
import math
from pathlib import Path
import re
from typing import Any, Dict, List, Literal, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)

TrackType = Literal["video", "audio", "text", "vector"]
TransitionType = Literal["fade", "crossfade", "wipe", "slide", "none"]

_ALLOWED_SVG_TAGS = {
    "svg", "g", "path", "rect", "circle", "ellipse", "line",
    "polyline", "polygon", "text", "tspan", "defs", "use", "lineargradient",
    "radialgradient", "stop", "mask", "clippath", "filter", "fegaussianblur",
}

_FORBIDDEN_SVG_ATTR_PATTERNS = [re.compile(r"^on[a-z]+", re.IGNORECASE)]
_FORBIDDEN_SVG_URL_SCHEMES = [
    re.compile(r"^\s*javascript:", re.IGNORECASE),
    re.compile(r"^\s*data:\s*text/html", re.IGNORECASE),
]


@dataclass
class Clip:
    """Individual media, text, or vector clip on a timeline track."""
    clip_id: str
    track_id: str
    start_time: float
    end_time: float
    source_path: Optional[str] = None
    in_point: float = 0.0
    out_point: float = 0.0
    volume: float = 1.0
    muted: bool = False
    text_content: Optional[str] = None
    typography: Optional[Dict[str, Any]] = None
    vector_svg: Optional[str] = None
    transform: Optional[Dict[str, Any]] = None
    transition_in: Optional[Dict[str, Any]] = None
    transition_out: Optional[Dict[str, Any]] = None
    keyframes: Optional[List[Dict[str, Any]]] = None

    @property
    def duration(self) -> float:
        return max(0.0, self.end_time - self.start_time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "track_id": self.track_id,
            "start_time": round(self.start_time, 3),
            "end_time": round(self.end_time, 3),
            "duration": round(self.duration, 3),
            "source_path": self.source_path,
            "in_point": round(self.in_point, 3),
            "out_point": round(self.out_point, 3),
            "volume": round(self.volume, 2),
            "muted": self.muted,
            "text_content": self.text_content,
            "typography": self.typography,
            "vector_svg": self.vector_svg,
            "transform": self.transform,
            "transition_in": self.transition_in,
            "transition_out": self.transition_out,
            "keyframes": self.keyframes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Clip:
        return cls(
            clip_id=str(data["clip_id"]),
            track_id=str(data.get("track_id", "")),
            start_time=float(data.get("start_time", 0.0)),
            end_time=float(data.get("end_time", 0.0)),
            source_path=data.get("source_path"),
            in_point=float(data.get("in_point", 0.0)),
            out_point=float(data.get("out_point", 0.0)),
            volume=float(data.get("volume", 1.0)),
            muted=bool(data.get("muted", False)),
            text_content=data.get("text_content"),
            typography=data.get("typography"),
            vector_svg=data.get("vector_svg"),
            transform=data.get("transform"),
            transition_in=data.get("transition_in"),
            transition_out=data.get("transition_out"),
            keyframes=data.get("keyframes"),
        )


@dataclass
class Track:
    """Timeline track grouping clips of a specific type (video, audio, text, vector)."""
    track_id: str
    track_type: TrackType
    name: str
    muted: bool = False
    locked: bool = False
    clips: List[Clip] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "track_type": self.track_type,
            "name": self.name,
            "muted": self.muted,
            "locked": self.locked,
            "clips": [clip.to_dict() for clip in self.clips],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Track:
        clips = [Clip.from_dict(c) for c in data.get("clips", [])]
        return cls(
            track_id=str(data["track_id"]),
            track_type=data.get("track_type", "video"),
            name=str(data.get("name", "")),
            muted=bool(data.get("muted", False)),
            locked=bool(data.get("locked", False)),
            clips=clips,
        )


@dataclass
class Timeline:
    """Multi-track NLE timeline data model."""
    duration: float = 10.0
    fps: int = 30
    width: int = 1920
    height: int = 1080
    tracks: List[Track] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "duration": round(self.duration, 3),
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "tracks": [t.to_dict() for t in self.tracks],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Timeline:
        tracks = [Track.from_dict(t) for t in data.get("tracks", [])]
        return cls(
            duration=float(data.get("duration", 10.0)),
            fps=int(data.get("fps", 30)),
            width=int(data.get("width", 1920)),
            height=int(data.get("height", 1080)),
            tracks=tracks,
        )


# SVG Sanitizer
class _SVGSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output: List[str] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        clean_tag = tag.lower().strip()
        if clean_tag not in _ALLOWED_SVG_TAGS:
            raise ValueError(f"Dangerous or unsupported SVG tag: <{clean_tag}>")

        clean_attrs = []
        for k, v in attrs:
            attr_name = k.lower().strip()
            for pattern in _FORBIDDEN_SVG_ATTR_PATTERNS:
                if pattern.match(attr_name):
                    raise ValueError(f"Executable attribute '{attr_name}' is forbidden in SVG")
            val_str = str(v or "")
            for scheme in _FORBIDDEN_SVG_URL_SCHEMES:
                if scheme.match(val_str):
                    raise ValueError(f"Disallowed URL scheme in SVG attribute '{attr_name}'")
            if (attr_name in {"href", "xlink:href"} and "://" in val_str):
                raise ValueError(f"External reference URL in SVG attribute '{attr_name}' is forbidden")
            clean_attrs.append(f'{attr_name}="{val_str}"')

        attr_str = (" " + " ".join(clean_attrs)) if clean_attrs else ""
        self.output.append(f"<{clean_tag}{attr_str}>")

    def handle_endtag(self, tag: str):
        clean_tag = tag.lower().strip()
        if clean_tag in _ALLOWED_SVG_TAGS:
            self.output.append(f"</{clean_tag}>")

    def handle_data(self, data: str):
        self.output.append(data)


def sanitize_svg_markup(svg_content: str) -> str:
    """Validate and sanitize SVG markup against script injection and external URLs."""
    if not svg_content or not svg_content.strip():
        raise ValueError("SVG markup cannot be empty")
    sanitizer = _SVGSanitizer()
    sanitizer.feed(svg_content)
    clean_svg = "".join(sanitizer.output)
    if not clean_svg.strip().startswith("<svg"):
        raise ValueError("SVG markup must begin with <svg> root element")
    return clean_svg


def sanitize_typography(params: Dict[str, Any]) -> Dict[str, Any]:
    """Validate typography properties, enforcing safe values."""
    sanitized: Dict[str, Any] = {}
    if "font_size" in params:
        fs = str(params["font_size"]).strip()
        if not re.fullmatch(r"^\d+(\.\d+)?(px|rem|em|%)?$", fs):
            raise ValueError(f"Invalid font_size value: '{fs}'")
        sanitized["font_size"] = fs

    if "font_family" in params:
        ff = str(params["font_family"]).strip()
        if re.search(r"[;\{\}\<\>]", ff) or "javascript:" in ff.lower():
            raise ValueError(f"Invalid font_family value: '{ff}'")
        sanitized["font_family"] = ff

    if "font_weight" in params:
        fw = str(params["font_weight"]).strip().lower()
        if fw not in {"normal", "bold", "bolder", "lighter", "100", "200", "300", "400", "500", "600", "700", "800", "900"}:
            raise ValueError(f"Invalid font_weight: '{fw}'")
        sanitized["font_weight"] = fw

    if "color" in params:
        c = str(params["color"]).strip()
        if not re.fullmatch(r"^(#[0-9a-fA-F]{3,8}|rgba?\([0-9,\.\s%]+\)|[a-zA-Z]+)$", c):
            raise ValueError(f"Invalid color value: '{c}'")
        sanitized["color"] = c

    if "text_align" in params:
        ta = str(params["text_align"]).strip().lower()
        if ta not in {"left", "center", "right", "justify"}:
            raise ValueError(f"Invalid text_align: '{ta}'")
        sanitized["text_align"] = ta

    if "letter_spacing" in params:
        ls = str(params["letter_spacing"]).strip()
        if not re.fullmatch(r"^-?\d+(\.\d+)?(px|rem|em)?$", ls):
            raise ValueError(f"Invalid letter_spacing: '{ls}'")
        sanitized["letter_spacing"] = ls

    return sanitized


# Timeline Operations
def add_nle_track(
    timeline: Timeline,
    track_id: str,
    track_type: TrackType,
    name: str,
) -> Track:
    """Add a new track to the timeline."""
    if any(t.track_id == track_id for t in timeline.tracks):
        raise ValueError(f"Track with ID '{track_id}' already exists")
    if track_type not in {"video", "audio", "text", "vector"}:
        raise ValueError(f"Invalid track type: '{track_type}'")

    track = Track(track_id=track_id, track_type=track_type, name=name)
    timeline.tracks.append(track)
    return track


def get_track(timeline: Timeline, track_id: str) -> Optional[Track]:
    for t in timeline.tracks:
        if t.track_id == track_id:
            return t
    return None


def find_clip(timeline: Timeline, clip_id: str) -> Tuple[Optional[Track], Optional[Clip]]:
    for track in timeline.tracks:
        for clip in track.clips:
            if clip.clip_id == clip_id:
                return track, clip
    return None, None


def add_nle_clip(timeline: Timeline, track_id: str, clip: Clip) -> Clip:
    """Add a clip to a specified track."""
    track = get_track(timeline, track_id)
    if track is None:
        raise ValueError(f"Track '{track_id}' not found in timeline")

    if clip.start_time < 0:
        raise ValueError("Clip start_time must be non-negative")
    if clip.end_time <= clip.start_time:
        raise ValueError("Clip end_time must be strictly greater than start_time")

    if any(c.clip_id == clip.clip_id for c in track.clips):
        raise ValueError(f"Clip '{clip.clip_id}' already exists on track '{track_id}'")

    clip.track_id = track_id
    track.clips.append(clip)
    # Keep track clips sorted by start_time
    track.clips.sort(key=lambda c: c.start_time)

    # Update timeline total duration if clip extends past current duration
    if clip.end_time > timeline.duration:
        timeline.duration = clip.end_time

    return clip


def trim_nle_clip(
    timeline: Timeline,
    clip_id: str,
    new_start_time: float,
    new_end_time: float,
    ripple: bool = False,
) -> Clip:
    """Trim a clip's boundaries, optionally rippling following clips."""
    track, clip = find_clip(timeline, clip_id)
    if track is None or clip is None:
        raise ValueError(f"Clip '{clip_id}' not found")

    if new_start_time < 0:
        raise ValueError("Trimmed start_time must be >= 0")
    if new_end_time <= new_start_time:
        raise ValueError("Trimmed end_time must be strictly greater than start_time")

    old_end = clip.end_time
    delta = new_end_time - old_end

    clip.start_time = new_start_time
    clip.end_time = new_end_time

    if ripple and delta != 0:
        # Shift all subsequent clips on the same track
        for subsequent in track.clips:
            if subsequent.clip_id != clip.clip_id and subsequent.start_time >= old_end - 0.001:
                subsequent.start_time = max(0.0, subsequent.start_time + delta)
                subsequent.end_time = max(subsequent.start_time + 0.001, subsequent.end_time + delta)

    track.clips.sort(key=lambda c: c.start_time)
    _recalc_timeline_duration(timeline)
    return clip


def split_nle_clip(timeline: Timeline, clip_id: str, split_time: float) -> Tuple[Clip, Clip]:
    """Split an existing clip into two distinct clips at split_time."""
    track, clip = find_clip(timeline, clip_id)
    if track is None or clip is None:
        raise ValueError(f"Clip '{clip_id}' not found")

    if not (clip.start_time < split_time < clip.end_time):
        raise ValueError(
            f"Split time {split_time} must be strictly between clip start ({clip.start_time}) and end ({clip.end_time})"
        )

    split_offset = split_time - clip.start_time
    old_end = clip.end_time
    old_out = clip.out_point

    # Clip A (left)
    clip.end_time = split_time
    clip.out_point = clip.in_point + split_offset

    # Clip B (right)
    b_id = f"{clip.clip_id}_b_{uuid4().hex[:4]}"
    clip_b = Clip(
        clip_id=b_id,
        track_id=clip.track_id,
        start_time=split_time,
        end_time=old_end,
        source_path=clip.source_path,
        in_point=clip.in_point + split_offset,
        out_point=old_out,
        volume=clip.volume,
        muted=clip.muted,
        text_content=clip.text_content,
        typography=clip.typography.copy() if clip.typography else None,
        vector_svg=clip.vector_svg,
        transform=clip.transform.copy() if clip.transform else None,
        transition_in=None,
        transition_out=clip.transition_out,
        keyframes=clip.keyframes.copy() if clip.keyframes else None,
    )
    clip.transition_out = None

    track.clips.append(clip_b)
    track.clips.sort(key=lambda c: c.start_time)
    return clip, clip_b


def delete_nle_clip(timeline: Timeline, clip_id: str, ripple: bool = False) -> bool:
    """Delete a clip, optionally performing ripple delete to pull subsequent clips backward."""
    track, clip = find_clip(timeline, clip_id)
    if track is None or clip is None:
        raise ValueError(f"Clip '{clip_id}' not found")

    clip_duration = clip.duration
    old_end = clip.end_time

    track.clips.remove(clip)

    if ripple and clip_duration > 0:
        for subsequent in track.clips:
            if subsequent.start_time >= old_end - 0.001:
                subsequent.start_time = max(0.0, subsequent.start_time - clip_duration)
                subsequent.end_time = max(subsequent.start_time + 0.001, subsequent.end_time - clip_duration)

    track.clips.sort(key=lambda c: c.start_time)
    _recalc_timeline_duration(timeline)
    return True


def reorder_nle_clips(timeline: Timeline, track_id: str, clip_ids: List[str]) -> List[Clip]:
    """Reorder and pack clips sequentially on a track according to clip_ids order."""
    track = get_track(timeline, track_id)
    if track is None:
        raise ValueError(f"Track '{track_id}' not found")

    existing_ids = {c.clip_id for c in track.clips}
    if set(clip_ids) != existing_ids:
        raise ValueError("Reorder clip_ids list must contain exactly all existing clips for the track")

    clip_map = {c.clip_id: c for c in track.clips}
    reordered: List[Clip] = []
    current_time = 0.0

    for cid in clip_ids:
        c = clip_map[cid]
        dur = c.duration
        c.start_time = current_time
        c.end_time = current_time + dur
        current_time += dur
        reordered.append(c)

    track.clips = reordered
    _recalc_timeline_duration(timeline)
    return reordered


def add_nle_transition(
    timeline: Timeline,
    clip_a_id: str,
    clip_b_id: str,
    transition_type: TransitionType,
    duration: float = 0.5,
) -> Tuple[Clip, Clip]:
    """Configure a transition between two clips."""
    _, clip_a = find_clip(timeline, clip_a_id)
    _, clip_b = find_clip(timeline, clip_b_id)
    if clip_a is None or clip_b is None:
        raise ValueError(f"Both clips '{clip_a_id}' and '{clip_b_id}' must exist")

    if duration <= 0 or duration > min(clip_a.duration, clip_b.duration):
        raise ValueError(f"Transition duration ({duration}s) exceeds available clip lengths")

    if transition_type not in {"fade", "crossfade", "wipe", "slide", "none"}:
        raise ValueError(f"Unsupported transition type: '{transition_type}'")

    clip_a.transition_out = {"type": transition_type, "duration": round(duration, 3)}
    clip_b.transition_in = {"type": transition_type, "duration": round(duration, 3)}
    return clip_a, clip_b


def set_clip_audio(
    timeline: Timeline,
    clip_id: str,
    volume: float,
    muted: bool = False,
) -> Clip:
    """Set volume and mute state on an audio or video clip."""
    _, clip = find_clip(timeline, clip_id)
    if clip is None:
        raise ValueError(f"Clip '{clip_id}' not found")

    clip.volume = max(0.0, min(2.0, float(volume)))
    clip.muted = bool(muted)
    return clip


def generate_waveform_peaks(data: bytes, num_samples: int = 100) -> List[float]:
    """Generate normalized (0.0 to 1.0) audio peak waveform data for timeline visual feedback."""
    if not data or num_samples <= 0:
        return [0.0] * max(1, num_samples)

    # Process bytes into 8-bit or 16-bit PCM amplitude peaks
    chunk_size = max(1, len(data) // num_samples)
    peaks: List[float] = []

    for i in range(num_samples):
        start = i * chunk_size
        end = min(len(data), start + chunk_size)
        if start >= len(data):
            peaks.append(0.0)
            continue
        chunk = data[start:end]
        if not chunk:
            peaks.append(0.0)
            continue
        # Compute normalized deviation from center (128 for unsigned 8-bit)
        max_val = max(abs(b - 128) for b in chunk)
        norm_peak = min(1.0, max_val / 128.0)
        peaks.append(round(norm_peak, 3))

    return peaks


def _recalc_timeline_duration(timeline: Timeline) -> None:
    max_end = 0.0
    for t in timeline.tracks:
        for c in t.clips:
            if c.end_time > max_end:
                max_end = c.end_time
    if max_end > 0:
        timeline.duration = max(timeline.duration, round(max_end, 3))

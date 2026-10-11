"""Bounded Three.js and 3D scene composition support for HyperFrames compositions.

Provides glTF 2.0 (GLB) binary parsing, security validation, resource budgets,
scene configuration metadata, and optional Blender specialist inspection.
Three.js is hosted inside HyperFrames compositions rather than as a separate editor.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import shutil
import struct
from typing import Any, Dict, List, Optional, Tuple

from workstation.config import WorkstationConfig

logger = logging.getLogger(__name__)

# Constants and limits
GLB_MAGIC = 0x46546C67          # b"glTF"
GLB_JSON_CHUNK_TYPE = 0x4E4F534A  # b"JSON"
GLB_BIN_CHUNK_TYPE = 0x004E4942   # b"BIN\0"

MAX_GLB_BYTE_SIZE = 16 * 1024 * 1024  # 16MB budget
MAX_NODES = 1000
MAX_MESHES = 500
MAX_MATERIALS = 500
MAX_ANIMATIONS = 50
MAX_ACCESSORS = 1000
MAX_BUFFER_VIEWS = 1000

# Prohibited URI patterns in GLB internal references
_DISALLOWED_URI_SCHEMES = re.compile(r"^(https?|ftp|file|javascript|vbscript|data):", re.IGNORECASE)


@dataclass(frozen=True)
class GLBAssetMetadata:
    """Metadata and inspection receipt for a validated glTF 2.0 GLB binary asset."""
    name: str
    byte_size: int
    sha256: str
    version: int
    generator: Optional[str]
    node_count: int
    mesh_count: int
    material_count: int
    animation_count: int
    animation_names: List[str]
    buffer_byte_length: int
    has_binary_chunk: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThreeJsSceneConfig:
    """Configuration for a Three.js 3D viewport embedded in a HyperFrames composition."""
    canvas_id: str
    width: int = 1280
    height: int = 720
    background_color: str = "#0f172a"
    camera_fov: float = 60.0
    camera_near: float = 0.1
    camera_far: float = 1000.0
    camera_position: Tuple[float, float, float] = (0.0, 1.5, 3.0)
    camera_target: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    ambient_light_color: str = "#ffffff"
    ambient_light_intensity: float = 0.7
    directional_light_color: str = "#ffffff"
    directional_light_intensity: float = 1.0
    directional_light_position: Tuple[float, float, float] = (5.0, 10.0, 7.5)
    model_asset: Optional[str] = None
    active_animation: Optional[str] = None
    model_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    model_rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    model_scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    enable_shadows: bool = True
    enable_orbit_controls: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canvas_id": self.canvas_id,
            "width": self.width,
            "height": self.height,
            "background_color": self.background_color,
            "camera": {
                "fov": self.camera_fov,
                "near": self.camera_near,
                "far": self.camera_far,
                "position": list(self.camera_position),
                "target": list(self.camera_target),
            },
            "lights": {
                "ambient": {
                    "color": self.ambient_light_color,
                    "intensity": self.ambient_light_intensity,
                },
                "directional": {
                    "color": self.directional_light_color,
                    "intensity": self.directional_light_intensity,
                    "position": list(self.directional_light_position),
                },
            },
            "model_asset": self.model_asset,
            "active_animation": self.active_animation,
            "transform": {
                "position": list(self.model_position),
                "rotation": list(self.model_rotation),
                "scale": list(self.model_scale),
            },
            "enable_shadows": self.enable_shadows,
            "enable_orbit_controls": self.enable_orbit_controls,
        }


def validate_glb_uri(uri: str, field_name: str) -> None:
    """Validate internal glTF URI references to prevent path traversal and network exfiltration."""
    stripped = uri.strip()
    if _DISALLOWED_URI_SCHEMES.match(stripped):
        raise ValueError(f"External or disallowed URI scheme in GLB {field_name}: '{uri}'")

    if stripped.startswith("/") or stripped.startswith("\\") or (len(stripped) > 1 and stripped[1] == ":"):
        raise ValueError(f"Absolute path in GLB {field_name} is forbidden: '{uri}'")

    # Path traversal check
    norm_parts = Path(stripped).parts
    if ".." in norm_parts:
        raise ValueError(f"Path traversal in GLB {field_name} is forbidden: '{uri}'")


def inspect_glb_bytes(data: bytes, asset_name: str = "asset.glb") -> GLBAssetMetadata:
    """Parse, inspect, and enforce strict security boundaries on GLB binary data."""
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("GLB data must be bytes or bytearray")

    byte_size = len(data)
    if byte_size > MAX_GLB_BYTE_SIZE:
        raise ValueError(f"GLB asset size ({byte_size} bytes) exceeds maximum budget of {MAX_GLB_BYTE_SIZE} bytes (16MB)")

    if byte_size < 20:
        raise ValueError(f"GLB asset is truncated: only {byte_size} bytes (minimum header is 20 bytes)")

    # 1. Header (12 bytes)
    magic, version, declared_length = struct.unpack("<III", data[:12])
    if magic != GLB_MAGIC:
        raise ValueError(f"Invalid GLB magic header: {hex(magic)} (expected {hex(GLB_MAGIC)})")

    if version != 2:
        raise ValueError(f"Unsupported glTF version: {version}. Only glTF 2.0 is supported")

    if declared_length != byte_size:
        raise ValueError(f"GLB file length mismatch: header declares {declared_length} bytes, actual is {byte_size} bytes")

    # 2. Chunk 0: JSON chunk
    json_chunk_length, json_chunk_type = struct.unpack("<II", data[12:20])
    if json_chunk_type != GLB_JSON_CHUNK_TYPE:
        raise ValueError(f"First GLB chunk must be JSON chunk (0x4E4F534A), got {hex(json_chunk_type)}")

    json_start = 20
    json_end = json_start + json_chunk_length
    if json_end > byte_size:
        raise ValueError("GLB JSON chunk extends beyond file length")

    json_raw = data[json_start:json_end]
    try:
        json_str = json_raw.decode("utf-8").rstrip("\x20")
        scene_json = json.loads(json_str)
    except Exception as exc:
        raise ValueError(f"Corrupt or malformed JSON chunk in GLB: {exc}") from exc

    if not isinstance(scene_json, dict):
        raise ValueError("GLB JSON chunk root must be an object")

    # 3. Chunk 1: Optional BIN chunk
    has_bin = False
    bin_length = 0
    if json_end < byte_size:
        if json_end + 8 > byte_size:
            raise ValueError("Truncated secondary GLB chunk header")
        bin_chunk_len, bin_chunk_type = struct.unpack("<II", data[json_end:json_end + 8])
        if bin_chunk_type != GLB_BIN_CHUNK_TYPE:
            raise ValueError(f"Secondary GLB chunk must be BIN chunk (0x004E4942), got {hex(bin_chunk_type)}")
        has_bin = True
        bin_length = bin_chunk_len
        if json_end + 8 + bin_chunk_len > byte_size:
            raise ValueError("GLB BIN chunk extends beyond file length")

    # 4. Security & Resource Budget Validation
    nodes = scene_json.get("nodes", [])
    if len(nodes) > MAX_NODES:
        raise ValueError(f"GLB node count ({len(nodes)}) exceeds limit of {MAX_NODES}")

    meshes = scene_json.get("meshes", [])
    if len(meshes) > MAX_MESHES:
        raise ValueError(f"GLB mesh count ({len(meshes)}) exceeds limit of {MAX_MESHES}")

    materials = scene_json.get("materials", [])
    if len(materials) > MAX_MATERIALS:
        raise ValueError(f"GLB material count ({len(materials)}) exceeds limit of {MAX_MATERIALS}")

    animations = scene_json.get("animations", [])
    if len(animations) > MAX_ANIMATIONS:
        raise ValueError(f"GLB animation count ({len(animations)}) exceeds limit of {MAX_ANIMATIONS}")

    accessors = scene_json.get("accessors", [])
    if len(accessors) > MAX_ACCESSORS:
        raise ValueError(f"GLB accessor count ({len(accessors)}) exceeds limit of {MAX_ACCESSORS}")

    buffer_views = scene_json.get("bufferViews", [])
    if len(buffer_views) > MAX_BUFFER_VIEWS:
        raise ValueError(f"GLB bufferView count ({len(buffer_views)}) exceeds limit of {MAX_BUFFER_VIEWS}")

    # Inspect buffers and images for external URIs / path traversal
    for idx, buf in enumerate(scene_json.get("buffers", [])):
        if isinstance(buf, dict) and "uri" in buf:
            validate_glb_uri(buf["uri"], f"buffer[{idx}].uri")

    for idx, img in enumerate(scene_json.get("images", [])):
        if isinstance(img, dict) and "uri" in img:
            validate_glb_uri(img["uri"], f"image[{idx}].uri")

    animation_names = [
        str(a.get("name", f"anim_{i}"))
        for i, a in enumerate(animations)
        if isinstance(a, dict)
    ]

    generator = None
    asset_dict = scene_json.get("asset", {})
    if isinstance(asset_dict, dict):
        generator = asset_dict.get("generator")

    sha256 = hashlib.sha256(data).hexdigest()

    return GLBAssetMetadata(
        name=asset_name,
        byte_size=byte_size,
        sha256=sha256,
        version=version,
        generator=generator,
        node_count=len(nodes),
        mesh_count=len(meshes),
        material_count=len(materials),
        animation_count=len(animations),
        animation_names=animation_names,
        buffer_byte_length=bin_length,
        has_binary_chunk=has_bin,
    )


def create_minimal_valid_glb(
    name: str = "Scene",
    animation_name: Optional[str] = None,
) -> bytes:
    """Generate a standard-compliant, minimal valid glTF 2.0 GLB binary for testing or default scenes."""
    # 3 vertices (triangle), each 3 float32 coordinates (36 bytes total)
    vertex_data = struct.pack(
        "<9f",
        0.0, 0.0, 0.0,
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
    )

    bin_len = len(vertex_data)
    # Pad BIN chunk to 4-byte alignment with nulls
    bin_pad = (4 - (bin_len % 4)) % 4
    padded_bin = vertex_data + (b"\x00" * bin_pad)

    scene_json: Dict[str, Any] = {
        "asset": {
            "version": "2.0",
            "generator": "Hermes Creative Three.js 2026-10-09",
        },
        "scene": 0,
        "scenes": [
            {"name": name, "nodes": [0]},
        ],
        "nodes": [
            {
                "name": f"{name}_Root",
                "mesh": 0,
                "translation": [0.0, 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0, 1.0],
                "scale": [1.0, 1.0, 1.0],
            },
        ],
        "meshes": [
            {
                "name": f"{name}_Mesh",
                "primitives": [
                    {
                        "attributes": {"POSITION": 0},
                        "material": 0,
                    },
                ],
            },
        ],
        "materials": [
            {
                "name": f"{name}_Material",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [0.2, 0.6, 1.0, 1.0],
                    "metallicFactor": 0.1,
                    "roughnessFactor": 0.5,
                },
            },
        ],
        "accessors": [
            {
                "bufferView": 0,
                "byteOffset": 0,
                "componentType": 5126,  # FLOAT
                "count": 3,
                "type": "VEC3",
                "max": [1.0, 1.0, 0.0],
                "min": [0.0, 0.0, 0.0],
            },
        ],
        "bufferViews": [
            {
                "buffer": 0,
                "byteOffset": 0,
                "byteLength": bin_len,
                "target": 34962,  # ARRAY_BUFFER
            },
        ],
        "buffers": [
            {
                "byteLength": bin_len,
            },
        ],
    }

    if animation_name:
        scene_json["animations"] = [
            {
                "name": animation_name,
                "channels": [],
                "samplers": [],
            },
        ]

    json_bytes = json.dumps(scene_json, separators=(",", ":")).encode("utf-8")
    # Pad JSON chunk to 4-byte alignment with spaces (0x20)
    json_pad = (4 - (len(json_bytes) % 4)) % 4
    padded_json = json_bytes + (b"\x20" * json_pad)

    total_len = 12 + 8 + len(padded_json) + 8 + len(padded_bin)

    header = struct.pack("<III", GLB_MAGIC, 2, total_len)
    chunk0_header = struct.pack("<II", len(padded_json), GLB_JSON_CHUNK_TYPE)
    chunk1_header = struct.pack("<II", len(padded_bin), GLB_BIN_CHUNK_TYPE)

    return header + chunk0_header + padded_json + chunk1_header + padded_bin


def generate_threejs_canvas_dom(config: ThreeJsSceneConfig) -> Any:
    """Generate a DOMElement representation of the Three.js viewport canvas."""
    from workstation.creative_operations import DOMElement

    attrs: Dict[str, str] = {
        "id": config.canvas_id,
        "data-hf-id": config.canvas_id,
        "data-hf-3d": "true",
        "width": str(config.width),
        "height": str(config.height),
        "style": (
            f"width: 100%; height: 100%; display: block; "
            f"background-color: {config.background_color};"
        ),
    }
    if config.model_asset:
        attrs["data-hf-model"] = config.model_asset
    if config.active_animation:
        attrs["data-hf-anim"] = config.active_animation

    return DOMElement(
        tag="canvas",
        attrs=attrs,
    )


def inspect_blender_specialist(config: WorkstationConfig) -> Dict[str, Any]:
    """Inspect optional Blender specialist executable without blocking the primary Three.js runtime.

    Blender is an optional offline specialist tool for 3D conversions/rendering;
    its presence or absence does not prevent Three.js composition playback or export.
    """
    blender_path = shutil.which("blender")
    # Also check typical Windows paths if not in PATH
    if not blender_path and os.name == "nt":
        candidates = [
            Path(r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"),
            Path(r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe"),
            Path(r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe"),
            Path(r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe"),
        ]
        for c in candidates:
            if c.is_file():
                blender_path = str(c)
                break

    if not blender_path:
        return {
            "available": False,
            "version": None,
            "executable_path": None,
            "capabilities": [],
            "role": "optional_specialist",
        }

    # Attempt light version probe
    version = None
    try:
        import subprocess
        proc = subprocess.run([blender_path, "--version"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            match = re.search(r"^Blender (\S+)", proc.stdout, re.MULTILINE)
            if match:
                version = match.group(1)
    except Exception as exc:
        logger.debug("Failed probing Blender version: %s", exc)

    return {
        "available": True,
        "version": version or "unknown",
        "executable_path": blender_path,
        "capabilities": ["gltf_export", "fbx_conversion", "cycles_render", "eevee_render"],
        "role": "optional_specialist",
    }

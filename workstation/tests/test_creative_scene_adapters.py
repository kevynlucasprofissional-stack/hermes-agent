"""Tests for CWN-05 Freeform scene capability adapters (SVG, Canvas, Three.js, AV)."""
from fractions import Fraction
import pytest

from workstation.creative_document import (
    Asset,
    Clip,
    Composition,
    CreativeDocument,
    Keyframe,
    Layer,
    Track,
    create_empty_project,
    document_to_dict,
    load_document_from_dict,
)
from workstation.creative_time import CanonicalTime, RationalFps, TimeRange
from workstation.creative_scene_adapters import (
    CompositeScene,
    SvgVectorAdapter,
    CanvasEffectAdapter,
    ThreeJsSceneAdapter,
    AudioVisualMediaAdapter,
    RenderContext,
    SecuritySandboxError,
)


def _build_mixed_project() -> CreativeDocument:
    doc = create_empty_project(name="Mixed Multi-Engine Project", width=1920, height=1080, fps=RationalFps(30, 1))
    comp = doc.compositions[0]

    # 1. Video asset & clip
    video_asset = Asset(
        asset_id="1" * 32,
        name="bg_video.mp4",
        kind="video",
        path="assets/bg_video.mp4",
        sha256="a" * 64,
        duration=CanonicalTime.from_seconds(30),
    )
    doc.assets[video_asset.asset_id] = video_asset
    v_track = Track(track_id="2" * 32, name="Video", kind="video")
    v_clip = Clip(
        clip_id="3" * 32,
        track_id=v_track.track_id,
        asset_id=video_asset.asset_id,
        name="Background Video",
        timeline_range=TimeRange(CanonicalTime.from_seconds(0), CanonicalTime.from_seconds(20)),
        source_in=CanonicalTime.from_seconds(5),
    )
    v_track.clips.append(v_clip)
    comp.tracks.append(v_track)

    # 2. Editable SVG Title Layer with Keyframes
    svg_layer = Layer(
        layer_id="4" * 32,
        name="SVG Title",
        kind="vector_svg",
        declared_parameters={"text": "Hermes Creative", "color": "#00ffcc", "font_size": 48},
        transform={"x": 960, "y": 200, "opacity": 1.0},
    )
    svg_layer.keyframes.append(
        Keyframe(
            keyframe_id="5" * 32,
            property_path="transform.opacity",
            time=CanonicalTime.from_seconds(0),
            value=0.0,
        )
    )
    svg_layer.keyframes.append(
        Keyframe(
            keyframe_id="6" * 32,
            property_path="transform.opacity",
            time=CanonicalTime.from_seconds(1),
            value=1.0,
        )
    )
    comp.layers.append(svg_layer)

    # 3. Canvas 2D Procedural Effect (Opaque with exposed parameters)
    canvas_layer = Layer(
        layer_id="7" * 32,
        name="Noise Gradient Shader",
        kind="html_canvas",
        declared_parameters={"intensity": 0.8, "frequency": 2.5},
        opaque_code="function render(ctx, t, p) { ctx.fillStyle = 'rgba(255,0,0,' + p.intensity + ')'; ctx.fillRect(0,0,1920,1080); }",
        transform={"x": 0, "y": 0, "opacity": 0.5},
    )
    comp.layers.append(canvas_layer)

    # 4. Three.js 3D Object Layer
    three_asset = Asset(
        asset_id="8" * 32,
        name="logo_3d.glb",
        kind="3d_model",
        path="assets/logo_3d.glb",
        sha256="b" * 64,
    )
    doc.assets[three_asset.asset_id] = three_asset
    three_layer = Layer(
        layer_id="9" * 32,
        name="3D Logo Viewport",
        kind="three_js_scene",
        declared_parameters={
            "asset_id": three_asset.asset_id,
            "fov": 60,
            "rotation_speed": 1.0,
            "camera_position": [0, 0, 5],
        },
        transform={"x": 960, "y": 540, "opacity": 1.0},
    )
    comp.layers.append(three_layer)

    return doc


def test_mixed_project_creation_and_deterministic_seek():
    """DoD: same project has editable SVG title + Canvas effect + Three.js object + video/audio, with arbitrary frame seek."""
    doc = _build_mixed_project()
    comp = doc.compositions[0]
    scene = CompositeScene.from_composition(comp, doc.assets)

    # Deterministic frame seek: seeking out of order must yield identical outputs!
    t1 = CanonicalTime.from_seconds(1.0)
    t2 = CanonicalTime.from_seconds(5.0)

    # Seek t1 first
    state_t1_first = scene.seek(t1)
    # Seek t2
    state_t2 = scene.seek(t2)
    # Seek t1 again
    state_t1_second = scene.seek(t1)

    assert state_t1_first == state_t1_second
    assert state_t1_first != state_t2

    # Check SVG animated opacity at t=1.0 is 1.0 (keyframe 2)
    svg_node = state_t1_first.get_layer_node("4" * 32)
    assert svg_node["transform"]["opacity"] == 1.0

    # Check AV mapping: at t=5.0s, source offset is 5s + 5s = 10s
    av_node = state_t2.get_clip_node("3" * 32)
    assert av_node["source_time_seconds"] == 10.0


def test_parameter_only_modification_preserves_opaque_code():
    """DoD: parameter-only modification updates output without corrupting opaque code."""
    doc = _build_mixed_project()
    comp = doc.compositions[0]
    canvas_layer = next(l for l in comp.layers if l.kind == "html_canvas")
    orig_code = canvas_layer.opaque_code

    # Modify only declared parameter
    canvas_layer.declared_parameters["intensity"] = 0.2
    scene = CompositeScene.from_composition(comp, doc.assets)
    state = scene.seek(CanonicalTime.from_seconds(2.0))

    canvas_node = state.get_layer_node(canvas_layer.layer_id)
    assert canvas_node["parameters"]["intensity"] == 0.2
    assert canvas_layer.opaque_code == orig_code


def test_security_sandbox_rejects_unsafe_code_and_path_traversal():
    """DoD: zero cross-profile leakage, safe sandbox defense."""
    doc = _build_mixed_project()
    comp = doc.compositions[0]

    # Injecting forbidden script tag in SVG
    svg_layer = next(l for l in comp.layers if l.kind == "vector_svg")
    svg_layer.declared_parameters["text"] = "<script>alert('xss')</script>"

    scene = CompositeScene.from_composition(comp, doc.assets)
    state = scene.seek(CanonicalTime.from_seconds(0.0))
    svg_out = state.get_layer_node(svg_layer.layer_id)
    # Malicious script tag must be sanitized / escaped
    assert "<script>" not in svg_out["rendered_markup"]

    # Reject asset path escaping workspace
    malicious_asset = Asset(
        asset_id="f" * 32,
        name="escape.mp4",
        kind="video",
        path="../../etc/passwd",
        sha256="0" * 64,
    )
    doc.assets[malicious_asset.asset_id] = malicious_asset
    bad_clip = Clip(
        clip_id="e" * 32,
        track_id=comp.tracks[0].track_id,
        asset_id=malicious_asset.asset_id,
        name="Escape Clip",
        timeline_range=TimeRange(CanonicalTime.from_seconds(0), CanonicalTime.from_seconds(5)),
        source_in=CanonicalTime.from_seconds(0),
    )
    comp.tracks[0].clips.append(bad_clip)

    with pytest.raises(SecuritySandboxError, match="Path traversal detected"):
        CompositeScene.from_composition(comp, doc.assets, workspace_root="C:/safe/workspace")

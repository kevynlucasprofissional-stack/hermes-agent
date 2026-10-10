"""Unit and integration tests for P5 3D/Three.js composition and GLB asset handling."""
from __future__ import annotations

import base64
import json
from pathlib import Path
import struct
import pytest

from gateway.session_context import scoped_current_session_id
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from tools.approval_context import reset_current_session_key, set_current_session_key
from workstation.config import WorkstationConfig
from workstation.creative_3d import (
    GLBAssetMetadata,
    MAX_ANIMATIONS,
    MAX_GLB_BYTE_SIZE,
    MAX_MATERIALS,
    MAX_MESHES,
    MAX_NODES,
    ThreeJsSceneConfig,
    create_minimal_valid_glb,
    generate_threejs_canvas_dom,
    inspect_blender_specialist,
    inspect_glb_bytes,
)
from workstation.creative_operations import (
    CreativeOperation,
    apply_creative_operation,
    find_element_by_id,
    inspect_project,
    parse_html_tree,
)
from workstation.creative_project_runtime import CreativeRunContext
from workstation.creative_project_store import (
    CreativeConflictError,
    load_creative_revision,
    save_creative_revision,
)
from workstation.tests.test_creative_project_runtime import _task


@pytest.fixture
def op_context(tmp_path: Path, monkeypatch):
    home = tmp_path / "profile"
    monkeypatch.setenv("HERMES_KANBAN_DB", str(home / "kanban.db"))
    ht = set_hermes_home_override(home)
    st = set_current_session_key("approval-key")
    try:
        with scoped_current_session_id("durable-session"):
            context = _task(home)
            config = WorkstationConfig({"creative": {"enabled": True, "hyperframes_enabled": True}})
            yield config, context, home
    finally:
        reset_current_session_key(st)
        reset_hermes_home_override(ht)


@pytest.fixture
def sample_hyperframes_project(op_context):
    config, context, home = op_context
    project_id = "test-3d-project-01"
    initial_html = (
        "<!DOCTYPE html><html><head><title>3D Test</title></head>"
        "<body><div id=\"root\" data-hf-id=\"hf-root\"><h1>3D Title</h1></div></body></html>"
    )
    initial_meta = {
        "title": "3D HyperFrames Composition",
        "fps": 30,
        "duration": 5.0,
    }
    rev = save_creative_revision(
        initial_meta,
        engine="hyperframes",
        native_files={
            "index.html": initial_html.encode("utf-8"),
            "hyperframes.json": json.dumps(initial_meta).encode("utf-8"),
        },
    )
    return rev


def test_minimal_glb_generation_and_inspection():
    """Verify standard-compliant minimal GLB binary is correctly generated and parsed."""
    glb_data = create_minimal_valid_glb(name="HeroRobot", animation_name="Walk")
    assert isinstance(glb_data, bytes)
    assert len(glb_data) > 0

    meta = inspect_glb_bytes(glb_data, asset_name="robot.glb")
    assert meta.name == "robot.glb"
    assert meta.version == 2
    assert meta.node_count == 1
    assert meta.mesh_count == 1
    assert meta.material_count == 1
    assert meta.animation_count == 1
    assert meta.animation_names == ["Walk"]
    assert meta.has_binary_chunk is True
    assert meta.buffer_byte_length == 36
    assert len(meta.sha256) == 64
    assert meta.generator == "Hermes Creative Three.js 2026-10-09"


def test_glb_size_budget_enforcement():
    """Verify oversized GLB (> 16MB) is rejected immediately."""
    fake_header = struct.pack("<III", 0x46546C67, 2, MAX_GLB_BYTE_SIZE + 10)
    fake_data = fake_header + b"\x00" * (MAX_GLB_BYTE_SIZE + 1)
    with pytest.raises(ValueError, match="exceeds maximum budget"):
        inspect_glb_bytes(fake_data)


def test_glb_header_validation():
    """Verify bad magic, invalid version, and length mismatch are rejected."""
    valid_glb = create_minimal_valid_glb()

    # Bad magic
    bad_magic = b"ABCD" + valid_glb[4:]
    with pytest.raises(ValueError, match="Invalid GLB magic"):
        inspect_glb_bytes(bad_magic)

    # Bad version
    bad_version = valid_glb[:4] + struct.pack("<I", 1) + valid_glb[8:]
    with pytest.raises(ValueError, match="Unsupported glTF version"):
        inspect_glb_bytes(bad_version)

    # Declared length mismatch
    bad_length = valid_glb[:8] + struct.pack("<I", len(valid_glb) + 50) + valid_glb[12:]
    with pytest.raises(ValueError, match="length mismatch"):
        inspect_glb_bytes(bad_length)

    # Truncated
    with pytest.raises(ValueError, match="truncated"):
        inspect_glb_bytes(b"glTF")


def test_glb_security_uri_sanitization():
    """Verify external URLs, path traversal, and dangerous schemes are rejected in GLB references."""
    def build_custom_glb(buffers=None, images=None):
        scene = {
            "asset": {"version": "2.0"},
            "buffers": buffers or [],
            "images": images or [],
        }
        json_b = json.dumps(scene).encode("utf-8")
        pad = (4 - (len(json_b) % 4)) % 4
        padded_json = json_b + (b"\x20" * pad)
        total_len = 12 + 8 + len(padded_json)
        header = struct.pack("<III", 0x46546C67, 2, total_len)
        chunk0 = struct.pack("<II", len(padded_json), 0x4E4F534A)
        return header + chunk0 + padded_json

    # External URL in buffer
    with pytest.raises(ValueError, match="External or disallowed URI scheme"):
        inspect_glb_bytes(build_custom_glb(buffers=[{"uri": "https://malicious.org/payload.bin"}]))

    # Dangerous scheme
    with pytest.raises(ValueError, match="External or disallowed URI scheme"):
        inspect_glb_bytes(build_custom_glb(images=[{"uri": "data:text/html;base64,PHNjcmlwdD4="}]))

    # Path traversal in image
    with pytest.raises(ValueError, match="Path traversal in GLB"):
        inspect_glb_bytes(build_custom_glb(images=[{"uri": "../../../etc/passwd"}]))

    # Absolute path
    with pytest.raises(ValueError, match="Absolute path in GLB"):
        inspect_glb_bytes(build_custom_glb(buffers=[{"uri": "/usr/bin/secret.bin"}]))


def test_glb_resource_budgets():
    """Verify geometry limits (nodes, meshes, materials, animations) prevent resource exhaustion."""
    def build_budget_exceeded_glb(key: str, count: int):
        scene = {
            "asset": {"version": "2.0"},
            key: [{"id": i} for i in range(count)],
        }
        json_b = json.dumps(scene).encode("utf-8")
        pad = (4 - (len(json_b) % 4)) % 4
        padded_json = json_b + (b"\x20" * pad)
        total_len = 12 + 8 + len(padded_json)
        header = struct.pack("<III", 0x46546C67, 2, total_len)
        chunk0 = struct.pack("<II", len(padded_json), 0x4E4F534A)
        return header + chunk0 + padded_json

    # Too many nodes
    with pytest.raises(ValueError, match="node count .* exceeds limit"):
        inspect_glb_bytes(build_budget_exceeded_glb("nodes", MAX_NODES + 1))

    # Too many meshes
    with pytest.raises(ValueError, match="mesh count .* exceeds limit"):
        inspect_glb_bytes(build_budget_exceeded_glb("meshes", MAX_MESHES + 1))

    # Too many materials
    with pytest.raises(ValueError, match="material count .* exceeds limit"):
        inspect_glb_bytes(build_budget_exceeded_glb("materials", MAX_MATERIALS + 1))

    # Too many animations
    with pytest.raises(ValueError, match="animation count .* exceeds limit"):
        inspect_glb_bytes(build_budget_exceeded_glb("animations", MAX_ANIMATIONS + 1))


def test_threejs_scene_config_and_canvas_dom():
    """Verify ThreeJsSceneConfig serialization and DOM generation."""
    config = ThreeJsSceneConfig(
        canvas_id="hf-canvas-3d",
        width=1920,
        height=1080,
        background_color="#1e293b",
        model_asset="assets/robot.glb",
        active_animation="Idle",
    )
    dom = generate_threejs_canvas_dom(config)
    assert dom.tag == "canvas"
    assert dom.attrs["id"] == "hf-canvas-3d"
    assert dom.attrs["data-hf-3d"] == "true"
    assert dom.attrs["data-hf-model"] == "assets/robot.glb"
    assert dom.attrs["data-hf-anim"] == "Idle"
    assert dom.attrs["width"] == "1920"
    assert dom.attrs["height"] == "1080"
    assert "background-color: #1e293b" in dom.attrs["style"]

    cfg_dict = config.to_dict()
    assert cfg_dict["canvas_id"] == "hf-canvas-3d"
    assert cfg_dict["camera"]["fov"] == 60.0
    assert cfg_dict["lights"]["ambient"]["intensity"] == 0.7


def test_blender_specialist_inspection(op_context):
    """Verify Blender specialist discovery executes cleanly without throwing or blocking."""
    config, context, home = op_context
    info = inspect_blender_specialist(config)
    assert isinstance(info, dict)
    assert "available" in info
    assert "capabilities" in info
    assert info["role"] == "optional_specialist"
    if info["available"]:
        assert info["executable_path"] is not None
        assert "gltf_export" in info["capabilities"]


def test_add_3d_canvas_operation(op_context, sample_hyperframes_project):
    """Verify agent can add a 3D Three.js canvas to an existing HyperFrames composition."""
    config, context, home = op_context
    op = CreativeOperation(
        kind="add_3d_canvas",
        project_id=sample_hyperframes_project.project_id,
        parent_revision_id=sample_hyperframes_project.revision_id,
        params={
            "canvas_id": "hf-3d-viewport",
            "parent_id": "hf-root",
            "width": 1280,
            "height": 720,
            "background_color": "#020617",
        },
    )

    new_rev, details = apply_creative_operation(config, context, op)
    assert new_rev.parent_revision == sample_hyperframes_project.revision_id
    assert details["added_canvas_id"] == "hf-3d-viewport"

    # Verify HTML was updated
    html_text = (new_rev.manifest_path.parent / "index.html").read_text(encoding="utf-8")
    assert 'data-hf-3d="true"' in html_text
    assert 'id="hf-3d-viewport"' in html_text

    # Verify hyperframes.json records 3D scene
    meta_json = json.loads((new_rev.manifest_path.parent / "hyperframes.json").read_text(encoding="utf-8"))
    assert "scenes_3d" in meta_json
    assert "hf-3d-viewport" in meta_json["scenes_3d"]
    assert meta_json["scenes_3d"]["hf-3d-viewport"]["background_color"] == "#020617"


def test_import_3d_asset_and_bind_to_canvas(op_context, sample_hyperframes_project):
    """Verify GLB binary asset import, validation, storage under assets/, and canvas binding."""
    config, context, home = op_context

    # 1. First add a 3D canvas
    add_canvas_op = CreativeOperation(
        kind="add_3d_canvas",
        project_id=sample_hyperframes_project.project_id,
        parent_revision_id=sample_hyperframes_project.revision_id,
        params={"canvas_id": "main-3d-canvas"},
    )
    rev_canvas, _ = apply_creative_operation(config, context, add_canvas_op)

    # 2. Import a valid GLB asset and bind to the canvas
    glb_bytes = create_minimal_valid_glb(name="Character", animation_name="Run")
    import_op = CreativeOperation(
        kind="import_3d_asset",
        project_id=rev_canvas.project_id,
        parent_revision_id=rev_canvas.revision_id,
        params={
            "asset_name": "character.glb",
            "data_bytes": glb_bytes,
            "canvas_id": "main-3d-canvas",
        },
    )
    rev_imported, details = apply_creative_operation(config, context, import_op)
    assert details["imported_asset"] == "assets/character.glb"
    assert details["bound_to_canvas"] == "main-3d-canvas"
    assert details["metadata"]["animation_names"] == ["Run"]

    # Verify file saved on disk under assets/character.glb
    saved_asset_path = rev_imported.manifest_path.parent / "assets" / "character.glb"
    assert saved_asset_path.is_file()
    assert saved_asset_path.read_bytes() == glb_bytes

    # Verify canvas DOM element updated with data-hf-model
    html_text = (rev_imported.manifest_path.parent / "index.html").read_text(encoding="utf-8")
    assert 'data-hf-model="assets/character.glb"' in html_text

    # 3. Update 3D transform and active animation
    update_op = CreativeOperation(
        kind="update_3d_transform",
        project_id=rev_imported.project_id,
        parent_revision_id=rev_imported.revision_id,
        params={
            "canvas_id": "main-3d-canvas",
            "position": [0.0, 1.0, -2.0],
            "rotation": [0.0, 1.57, 0.0],
            "scale": [2.0, 2.0, 2.0],
            "active_animation": "Run",
        },
    )
    rev_transformed, transform_details = apply_creative_operation(config, context, update_op)
    assert transform_details["updated_canvas_id"] == "main-3d-canvas"
    assert transform_details["active_animation"] == "Run"
    assert transform_details["transform"]["position"] == [0.0, 1.0, -2.0]

    # Verify canvas attribute data-hf-anim updated
    updated_html = (rev_transformed.manifest_path.parent / "index.html").read_text(encoding="utf-8")
    assert 'data-hf-anim="Run"' in updated_html

    # Verify persistent roundtrip across new revision
    reloaded = load_creative_revision(rev_transformed.project_id, rev_transformed.revision_id)
    assert (reloaded.manifest_path.parent / "assets" / "character.glb").is_file()


def test_import_3d_asset_base64_and_etag_conflict(op_context, sample_hyperframes_project):
    """Verify base64 import payload decoding and 409 conflict detection on stale ETag."""
    config, context, home = op_context
    glb_bytes = create_minimal_valid_glb(name="Prop")
    b64_payload = base64.b64encode(glb_bytes).decode("ascii")

    # Valid base64 import
    op = CreativeOperation(
        kind="import_3d_asset",
        project_id=sample_hyperframes_project.project_id,
        parent_revision_id=sample_hyperframes_project.revision_id,
        params={
            "asset_name": "prop.glb",
            "data_base64": b64_payload,
        },
        if_match=sample_hyperframes_project.etag,
    )
    rev_ok, _ = apply_creative_operation(config, context, op)
    assert (rev_ok.manifest_path.parent / "assets" / "prop.glb").is_file()

    # Stale ETag must raise CreativeConflictError
    stale_op = CreativeOperation(
        kind="import_3d_asset",
        project_id=sample_hyperframes_project.project_id,
        parent_revision_id=sample_hyperframes_project.revision_id,
        params={
            "asset_name": "prop2.glb",
            "data_base64": b64_payload,
        },
        if_match="stale-invalid-etag",
    )
    with pytest.raises(CreativeConflictError, match="409 Conflict"):
        apply_creative_operation(config, context, stale_op)

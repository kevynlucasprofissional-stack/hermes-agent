"""Tests for CWN-01 Creative Document schema, stable IDs, roundtripping, and validation."""
import json
import pytest

from workstation.creative_document import (
    CreativeDocument,
    Composition,
    Track,
    Clip,
    Layer,
    Asset,
    Keyframe,
    CreativeDocumentError,
    create_empty_project,
    load_document_from_dict,
    document_to_dict,
)
from workstation.creative_time import CanonicalTime, RationalFps, TimeRange


def test_create_and_serialize_document():
    doc = create_empty_project(name="Test Short Film", width=1920, height=1080, fps=RationalFps(30000, 1001))
    assert doc.schema_version == 1
    assert len(doc.project_id) == 32
    assert len(doc.compositions) == 1

    comp = doc.compositions[0]
    assert comp.width == 1920
    assert comp.height == 1080
    assert comp.fps == RationalFps(30000, 1001)

    # Add asset
    asset = Asset(
        asset_id="a" * 32,
        name="interview_a_roll.mp4",
        kind="video",
        path="media/interview_a_roll.mp4",
        sha256="e" * 64,
        duration=CanonicalTime.from_seconds(60),
        width=1920,
        height=1080,
    )
    doc.assets[asset.asset_id] = asset

    # Add track and clip
    v_track = Track(track_id="b" * 32, name="Video 1", kind="video", z_index=0)
    clip = Clip(
        clip_id="c" * 32,
        track_id=v_track.track_id,
        asset_id=asset.asset_id,
        name="Interview Clip 1",
        timeline_range=TimeRange(CanonicalTime.from_seconds(0), CanonicalTime.from_seconds(10)),
        source_in=CanonicalTime.from_seconds(5),
        speed=1.0,
    )
    v_track.clips.append(clip)
    comp.tracks.append(v_track)

    # Add vector layer with keyframes
    layer = Layer(
        layer_id="d" * 32,
        name="Lower Third Title",
        kind="vector_svg",
        declared_parameters={"text": "Jane Doe", "color": "#ffffff"},
        transform={"x": 100, "y": 800, "opacity": 1.0},
    )
    kf1 = Keyframe(
        keyframe_id="e" * 32,
        property_path="transform.opacity",
        time=CanonicalTime.from_seconds(0),
        value=0.0,
        easing="linear",
    )
    kf2 = Keyframe(
        keyframe_id="f" * 32,
        property_path="transform.opacity",
        time=CanonicalTime.from_seconds(1),
        value=1.0,
        easing="ease_out",
    )
    layer.keyframes.extend([kf1, kf2])
    comp.layers.append(layer)

    # Serialize to dictionary
    data = document_to_dict(doc)
    assert data["schema_version"] == 1
    assert data["project_id"] == doc.project_id
    assert len(data["compositions"]) == 1

    # Roundtrip back
    reloaded = load_document_from_dict(data)
    assert reloaded.project_id == doc.project_id
    assert len(reloaded.compositions) == 1
    r_comp = reloaded.compositions[0]
    assert r_comp.fps == RationalFps(30000, 1001)
    assert len(r_comp.tracks) == 1
    assert r_comp.tracks[0].clips[0].name == "Interview Clip 1"
    assert r_comp.tracks[0].clips[0].timeline_range.duration.to_seconds() == 10
    assert len(r_comp.layers) == 1
    assert len(r_comp.layers[0].keyframes) == 2
    assert r_comp.layers[0].keyframes[1].easing == "ease_out"


def test_document_validation_rejects_malformed_data():
    # Missing schema_version
    with pytest.raises(CreativeDocumentError, match="Missing or invalid schema_version"):
        load_document_from_dict({"project_id": "a" * 32})

    # Future incompatible schema version
    with pytest.raises(CreativeDocumentError, match="Unsupported schema_version: 99"):
        load_document_from_dict({"schema_version": 99, "project_id": "a" * 32})

    # Invalid ID
    with pytest.raises(CreativeDocumentError, match="Invalid project_id"):
        load_document_from_dict({"schema_version": 1, "project_id": "bad-id"})

    # Reject inline binary blob
    doc_with_blob = {
        "schema_version": 1,
        "project_id": "a" * 32,
        "name": "Project with binary",
        "compositions": [],
        "assets": {
            "a" * 32: {
                "asset_id": "a" * 32,
                "name": "raw.bin",
                "kind": "video",
                "inline_data": "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8=",
            }
        },
    }
    with pytest.raises(CreativeDocumentError, match="Inline binary blobs forbidden"):
        load_document_from_dict(doc_with_blob)


def test_document_preserves_opaque_procedural_layer():
    doc = create_empty_project(name="Procedural Scene")
    layer = Layer(
        layer_id="b" * 32,
        name="Shader Background",
        kind="html_canvas",
        opaque_code="const gl = canvas.getContext('webgl'); // shader code",
        declared_parameters={"speed": 1.5, "palette": "cyberpunk"},
    )
    doc.compositions[0].layers.append(layer)

    serialized = document_to_dict(doc)
    reloaded = load_document_from_dict(serialized)
    r_layer = reloaded.compositions[0].layers[0]
    assert r_layer.is_opaque() is True
    assert r_layer.opaque_code == layer.opaque_code
    assert r_layer.declared_parameters["palette"] == "cyberpunk"


def test_document_persistence_and_conflict_handling(tmp_path):
    from hermes_constants import reset_hermes_home_override, set_hermes_home_override
    from workstation.creative_project_store import (
        CreativeConflictError,
        save_creative_document,
        load_creative_document,
    )

    token = set_hermes_home_override(tmp_path / "user_profile")
    try:
        doc = create_empty_project(name="Document Persistence Test")
        rev1 = save_creative_document(doc)
        assert rev1.engine == "creative-document"
        assert rev1.project_id == doc.project_id
        assert rev1.parent_revision is None

        # Reopen from store
        reloaded = load_creative_document(rev1.project_id, rev1.revision_id)
        assert reloaded.name == "Document Persistence Test"
        assert reloaded.project_id == doc.project_id
        assert len(reloaded.compositions) == 1

        # Second revision
        reloaded.name = "Updated Project Name"
        rev2 = save_creative_document(reloaded, parent_revision=rev1.revision_id, if_match=rev1.etag)
        assert rev2.parent_revision == rev1.revision_id

        # Concurrent edit attempt with stale ETag raises CreativeConflictError (409)
        with pytest.raises(CreativeConflictError, match="409 Conflict"):
            save_creative_document(reloaded, parent_revision=rev2.revision_id, if_match=rev1.etag)
    finally:
        reset_hermes_home_override(token)

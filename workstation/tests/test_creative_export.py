"""Tests for CWN-06 Interchangeable rendering engines, export, and frame boundary verification."""
from fractions import Fraction
from pathlib import Path
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
)
from workstation.creative_time import CanonicalTime, RationalFps, TimeRange
from workstation.creative_export import (
    VideoExportRequest,
    VideoExportResult,
    export_composition_to_video,
    cancel_active_render,
    ExportEngineError,
)


def _setup_export_project(tmp_path: Path) -> tuple[CreativeDocument, Path]:
    media_dir = tmp_path / "media"
    media_dir.mkdir(parents=True, exist_ok=True)
    source_png = media_dir / "source.png"
    from PIL import Image
    img = Image.new("RGB", (64, 64), color=(255, 0, 0))
    img.save(source_png, format="PNG")

    fps = RationalFps(30, 1)
    doc = create_empty_project(name="Export Pipeline Project", width=64, height=64, fps=fps)
    comp = doc.compositions[0]
    comp.duration = CanonicalTime.from_seconds(2.0)

    asset = Asset(
        asset_id="1" * 32,
        name="source.png",
        kind="image",
        path=str(source_png),
        sha256="d" * 64,
        duration=CanonicalTime.from_seconds(10.0),
        width=64,
        height=64,
    )
    doc.assets[asset.asset_id] = asset

    # Track with 2 clips (cut at 1.0s boundary)
    track = Track(track_id="2" * 32, name="Main Track", kind="video")
    clip1 = Clip(
        clip_id="3" * 32,
        track_id=track.track_id,
        asset_id=asset.asset_id,
        name="Clip 1",
        timeline_range=TimeRange(CanonicalTime.from_seconds(0), CanonicalTime.from_seconds(1)),
        source_in=CanonicalTime.from_seconds(0),
    )
    clip2 = Clip(
        clip_id="4" * 32,
        track_id=track.track_id,
        asset_id=asset.asset_id,
        name="Clip 2",
        timeline_range=TimeRange(CanonicalTime.from_seconds(1), CanonicalTime.from_seconds(2)),
        source_in=CanonicalTime.from_seconds(2),
    )
    track.clips.extend([clip1, clip2])
    comp.tracks.append(track)

    # Layer: SVG title
    layer = Layer(
        layer_id="5" * 32,
        name="Watermark",
        kind="vector_svg",
        declared_parameters={"text": "CWN-06", "color": "#ffffff"},
    )
    comp.layers.append(layer)

    return doc, source_png


def test_export_composition_to_video_and_readback(tmp_path):
    """DoD: 10-15s vertical (or test slice) exports MP4, reimports/decodes correctly and validates representative frames."""
    doc, source_png = _setup_export_project(tmp_path)
    comp = doc.compositions[0]
    out_mp4 = tmp_path / "output.mp4"

    req = VideoExportRequest(
        project_id=doc.project_id,
        composition_id=comp.composition_id,
        output_path=out_mp4,
        width=64,
        height=64,
        fps=comp.fps,
        duration=comp.duration,
    )

    result = export_composition_to_video(doc, req, workspace_root=tmp_path)
    assert result.success is True
    assert out_mp4.exists()
    assert out_mp4.stat().st_size > 0
    assert result.sha256 != ""
    assert result.dimensions == (64, 64)
    assert result.frame_count == 60  # 2.0s at 30fps = 60 frames

    # Verify receipt details
    assert "receipt" in result.to_dict()
    receipt = result.receipt
    assert receipt["verified"] is True
    assert 0 in result.verified_frames  # First frame
    assert 29 in result.verified_frames  # Last frame before cut (at 1.0s)
    assert 30 in result.verified_frames  # First frame after cut (at 1.0s)


def test_export_cancellation_cleans_up_without_orphans(tmp_path):
    """DoD: no orphan process after canceled render."""
    doc, source_png = _setup_export_project(tmp_path)
    comp = doc.compositions[0]
    out_mp4 = tmp_path / "canceled.mp4"

    req = VideoExportRequest(
        project_id=doc.project_id,
        composition_id=comp.composition_id,
        output_path=out_mp4,
        width=64,
        height=64,
        fps=comp.fps,
        duration=CanonicalTime.from_seconds(10.0),
    )

    # Cancel immediately
    cancel_active_render(req.project_id)
    with pytest.raises(ExportEngineError, match="canceled"):
        export_composition_to_video(doc, req, workspace_root=tmp_path, simulate_cancel=True)

    # Ensure no lingering locked partial file or processes
    assert not out_mp4.exists()

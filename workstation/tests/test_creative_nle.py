"""Unit and integration tests for P4 NLE, multi-track timeline, audio, transitions, and SVG design depth."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from gateway.session_context import scoped_current_session_id
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from tools.approval_context import reset_current_session_key, set_current_session_key
from workstation.config import WorkstationConfig
from workstation.creative_nle import (
    Clip,
    Timeline,
    Track,
    add_nle_clip,
    add_nle_track,
    add_nle_transition,
    delete_nle_clip,
    generate_waveform_peaks,
    get_track,
    reorder_nle_clips,
    sanitize_svg_markup,
    sanitize_typography,
    set_clip_audio,
    split_nle_clip,
    trim_nle_clip,
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
def sample_nle_project(op_context):
    config, context, home = op_context
    initial_html = (
        "<!DOCTYPE html><html><head><title>NLE Test</title></head>"
        "<body><div id=\"root\" data-hf-id=\"hf-root\"><h1>Timeline Composition</h1></div></body></html>"
    )
    initial_meta = {
        "title": "NLE Timeline Composition",
        "fps": 30,
        "duration": 10.0,
        "width": 1920,
        "height": 1080,
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


# 1. Timeline Data Model & Serialization Tests
def test_timeline_track_clip_serialization():
    timeline = Timeline(duration=15.0, fps=30, width=1920, height=1080)
    add_nle_track(timeline, "v1", "video", "Main Video")
    add_nle_track(timeline, "a1", "audio", "Music Track")

    clip_v1 = Clip(clip_id="c1", track_id="v1", start_time=0.0, end_time=5.0, source_path="assets/intro.mp4")
    clip_a1 = Clip(clip_id="c2", track_id="a1", start_time=0.0, end_time=15.0, source_path="assets/bgm.mp3", volume=0.8)

    add_nle_clip(timeline, "v1", clip_v1)
    add_nle_clip(timeline, "a1", clip_a1)

    data = timeline.to_dict()
    assert data["duration"] == 15.0
    assert len(data["tracks"]) == 2
    assert len(data["tracks"][0]["clips"]) == 1
    assert data["tracks"][1]["clips"][0]["volume"] == 0.8

    reloaded = Timeline.from_dict(data)
    assert reloaded.duration == 15.0
    assert len(reloaded.tracks) == 2
    assert reloaded.tracks[0].clips[0].clip_id == "c1"


# 2. Trim and Ripple Trim Tests
def test_clip_trim_standard_and_ripple():
    timeline = Timeline(duration=20.0)
    add_nle_track(timeline, "v1", "video", "Track 1")

    # Three sequential clips
    c1 = Clip(clip_id="c1", track_id="v1", start_time=0.0, end_time=4.0)
    c2 = Clip(clip_id="c2", track_id="v1", start_time=4.0, end_time=8.0)
    c3 = Clip(clip_id="c3", track_id="v1", start_time=8.0, end_time=12.0)

    add_nle_clip(timeline, "v1", c1)
    add_nle_clip(timeline, "v1", c2)
    add_nle_clip(timeline, "v1", c3)

    # 1. Non-ripple trim on c1: lengthen c1 from 4.0 to 6.0
    trim_nle_clip(timeline, "c1", 0.0, 6.0, ripple=False)
    assert c1.end_time == 6.0
    # c2 and c3 unchanged without ripple
    assert c2.start_time == 4.0
    assert c3.start_time == 8.0

    # 2. Ripple trim on c2: shrink c2 from (4.0 - 8.0) to (4.0 - 6.0) -> delta = -2.0
    trim_nle_clip(timeline, "c2", 4.0, 6.0, ripple=True)
    assert c2.end_time == 6.0
    # c3 must have shifted earlier by 2.0 seconds: from 8.0 to 6.0!
    assert c3.start_time == 6.0
    assert c3.end_time == 10.0


def test_trim_negative_cases():
    timeline = Timeline(duration=10.0)
    add_nle_track(timeline, "v1", "video", "Track 1")
    c1 = Clip(clip_id="c1", track_id="v1", start_time=0.0, end_time=5.0)
    add_nle_clip(timeline, "v1", c1)

    with pytest.raises(ValueError, match="must be >= 0"):
        trim_nle_clip(timeline, "c1", -1.0, 4.0)

    with pytest.raises(ValueError, match="strictly greater than start_time"):
        trim_nle_clip(timeline, "c1", 4.0, 4.0)


# 3. Clip Split Tests
def test_clip_split():
    timeline = Timeline(duration=10.0)
    add_nle_track(timeline, "v1", "video", "Track 1")
    c = Clip(clip_id="c1", track_id="v1", start_time=0.0, end_time=10.0, in_point=5.0, out_point=15.0)
    add_nle_clip(timeline, "v1", c)

    clip_a, clip_b = split_nle_clip(timeline, "c1", split_time=4.0)
    assert clip_a.clip_id == "c1"
    assert clip_a.start_time == 0.0
    assert clip_a.end_time == 4.0
    assert clip_a.in_point == 5.0
    assert clip_a.out_point == 9.0  # 5.0 + 4.0

    assert clip_b.start_time == 4.0
    assert clip_b.end_time == 10.0
    assert clip_b.in_point == 9.0
    assert clip_b.out_point == 15.0

    track = get_track(timeline, "v1")
    assert len(track.clips) == 2


def test_split_negative_cases():
    timeline = Timeline(duration=10.0)
    add_nle_track(timeline, "v1", "video", "Track 1")
    c = Clip(clip_id="c1", track_id="v1", start_time=2.0, end_time=8.0)
    add_nle_clip(timeline, "v1", c)

    with pytest.raises(ValueError, match="strictly between"):
        split_nle_clip(timeline, "c1", split_time=1.0)

    with pytest.raises(ValueError, match="strictly between"):
        split_nle_clip(timeline, "c1", split_time=8.0)


# 4. Clip Deletion and Ripple Delete
def test_clip_delete_and_ripple():
    timeline = Timeline(duration=15.0)
    add_nle_track(timeline, "v1", "video", "Track 1")
    c1 = Clip(clip_id="c1", track_id="v1", start_time=0.0, end_time=3.0)
    c2 = Clip(clip_id="c2", track_id="v1", start_time=3.0, end_time=7.0)  # duration = 4.0
    c3 = Clip(clip_id="c3", track_id="v1", start_time=7.0, end_time=10.0)

    add_nle_clip(timeline, "v1", c1)
    add_nle_clip(timeline, "v1", c2)
    add_nle_clip(timeline, "v1", c3)

    # Ripple delete c2 (4.0s duration)
    delete_nle_clip(timeline, "c2", ripple=True)
    track = get_track(timeline, "v1")
    assert len(track.clips) == 2
    assert track.clips[0].clip_id == "c1"
    assert track.clips[1].clip_id == "c3"
    # c3 was at 7.0-10.0, shifts back by 4.0s to 3.0-6.0
    assert track.clips[1].start_time == 3.0
    assert track.clips[1].end_time == 6.0


# 5. Clip Reordering
def test_clip_reordering():
    timeline = Timeline(duration=10.0)
    add_nle_track(timeline, "v1", "video", "Track 1")
    c1 = Clip(clip_id="c1", track_id="v1", start_time=0.0, end_time=2.0)
    c2 = Clip(clip_id="c2", track_id="v1", start_time=2.0, end_time=5.0)
    c3 = Clip(clip_id="c3", track_id="v1", start_time=5.0, end_time=9.0)

    add_nle_clip(timeline, "v1", c1)
    add_nle_clip(timeline, "v1", c2)
    add_nle_clip(timeline, "v1", c3)

    # Reorder to c3, c1, c2
    reordered = reorder_nle_clips(timeline, "v1", ["c3", "c1", "c2"])
    assert [c.clip_id for c in reordered] == ["c3", "c1", "c2"]

    # c3 (4s dur): 0.0 - 4.0
    assert reordered[0].start_time == 0.0
    assert reordered[0].end_time == 4.0
    # c1 (2s dur): 4.0 - 6.0
    assert reordered[1].start_time == 4.0
    assert reordered[1].end_time == 6.0
    # c2 (3s dur): 6.0 - 9.0
    assert reordered[2].start_time == 6.0
    assert reordered[2].end_time == 9.0


# 6. Transitions & Audio Volume & Waveforms
def test_transitions_and_audio():
    timeline = Timeline(duration=10.0)
    add_nle_track(timeline, "v1", "video", "Video")
    c1 = Clip(clip_id="c1", track_id="v1", start_time=0.0, end_time=4.0)
    c2 = Clip(clip_id="c2", track_id="v1", start_time=4.0, end_time=8.0)
    add_nle_clip(timeline, "v1", c1)
    add_nle_clip(timeline, "v1", c2)

    add_nle_transition(timeline, "c1", "c2", "crossfade", duration=0.8)
    assert c1.transition_out == {"type": "crossfade", "duration": 0.8}
    assert c2.transition_in == {"type": "crossfade", "duration": 0.8}

    # Audio setting
    set_clip_audio(timeline, "c1", volume=1.5, muted=True)
    assert c1.volume == 1.5
    assert c1.muted is True

    # Waveform generation
    peaks = generate_waveform_peaks(b"\x80\xFF\x80\x00\x80\xFF", num_samples=3)
    assert len(peaks) == 3
    assert all(0.0 <= p <= 1.0 for p in peaks)


# 7. Typography & SVG Vector Sanitization
def test_typography_and_svg_sanitization():
    # Valid typography
    clean_typo = sanitize_typography({
        "font_size": "24px",
        "font_family": "Helvetica, Arial",
        "font_weight": "bold",
        "color": "#38bdf8",
        "text_align": "center",
    })
    assert clean_typo["font_size"] == "24px"
    assert clean_typo["color"] == "#38bdf8"

    with pytest.raises(ValueError, match="Invalid font_size"):
        sanitize_typography({"font_size": "24px; color: red"})

    # Valid SVG
    valid_svg = (
        '<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">'
        '<circle cx="50" cy="50" r="40" fill="#f43f5e" />'
        '<rect x="10" y="10" width="80" height="20" fill="#fbbf24" />'
        '</svg>'
    )
    sanitized = sanitize_svg_markup(valid_svg)
    assert "<svg" in sanitized
    assert "<circle" in sanitized

    # Script tag injection in SVG
    with pytest.raises(ValueError, match="Dangerous or unsupported SVG tag"):
        sanitize_svg_markup('<svg><script>alert(1)</script></svg>')

    # Executable event handler in SVG
    with pytest.raises(ValueError, match="Executable attribute"):
        sanitize_svg_markup('<svg><rect onload="alert(1)" /></svg>')

    # Remote external reference
    with pytest.raises(ValueError, match="External reference URL"):
        sanitize_svg_markup('<svg><use href="http://malicious.org/icon.svg" /></svg>')


# 8. End-to-End Multi-Track Composition Agent Operations
def test_e2e_multitrack_composition_workflow(op_context, sample_nle_project):
    """Verify end-to-end multi-track composition with video, audio, text, and SVG vector graphics."""
    config, context, home = op_context
    project_id = sample_nle_project.project_id
    rev_id = sample_nle_project.revision_id

    # 1. Add tracks: video, audio, text, vector
    op_track_v = CreativeOperation(
        kind="add_nle_track",
        project_id=project_id,
        parent_revision_id=rev_id,
        params={"track_id": "track_v1", "track_type": "video", "name": "Background Video"},
    )
    rev_1, _ = apply_creative_operation(config, context, op_track_v)

    op_track_a = CreativeOperation(
        kind="add_nle_track",
        project_id=project_id,
        parent_revision_id=rev_1.revision_id,
        params={"track_id": "track_a1", "track_type": "audio", "name": "Score Audio"},
    )
    rev_2, _ = apply_creative_operation(config, context, op_track_a)

    op_track_t = CreativeOperation(
        kind="add_nle_track",
        project_id=project_id,
        parent_revision_id=rev_2.revision_id,
        params={"track_id": "track_t1", "track_type": "text", "name": "Titles"},
    )
    rev_3, _ = apply_creative_operation(config, context, op_track_t)

    op_track_svg = CreativeOperation(
        kind="add_nle_track",
        project_id=project_id,
        parent_revision_id=rev_3.revision_id,
        params={"track_id": "track_s1", "track_type": "vector", "name": "Graphics"},
    )
    rev_4, _ = apply_creative_operation(config, context, op_track_svg)

    # 2. Add video clip, audio clip, animated text clip, and SVG vector badge
    op_clip_v = CreativeOperation(
        kind="add_nle_clip",
        project_id=project_id,
        parent_revision_id=rev_4.revision_id,
        params={
            "track_id": "track_v1",
            "clip_id": "clip_main_video",
            "start_time": 0.0,
            "end_time": 8.0,
            "source_path": "assets/scenery.mp4",
        },
    )
    rev_5, _ = apply_creative_operation(config, context, op_clip_v)

    op_clip_a = CreativeOperation(
        kind="add_nle_clip",
        project_id=project_id,
        parent_revision_id=rev_5.revision_id,
        params={
            "track_id": "track_a1",
            "clip_id": "clip_soundtrack",
            "start_time": 0.0,
            "end_time": 8.0,
            "source_path": "assets/music.mp3",
            "volume": 0.75,
        },
    )
    rev_6, _ = apply_creative_operation(config, context, op_clip_a)

    op_clip_t = CreativeOperation(
        kind="add_nle_clip",
        project_id=project_id,
        parent_revision_id=rev_6.revision_id,
        params={
            "track_id": "track_t1",
            "clip_id": "clip_title_card",
            "start_time": 1.0,
            "end_time": 5.0,
            "text_content": "Hermes Creative Workstation",
            "typography": {
                "font_size": "32px",
                "font_family": "Inter, sans-serif",
                "font_weight": "bold",
                "color": "#f8fafc",
                "text_align": "center",
            },
        },
    )
    rev_7, _ = apply_creative_operation(config, context, op_clip_t)

    op_clip_svg = CreativeOperation(
        kind="add_nle_clip",
        project_id=project_id,
        parent_revision_id=rev_7.revision_id,
        params={
            "track_id": "track_s1",
            "clip_id": "clip_vector_logo",
            "start_time": 0.0,
            "end_time": 6.0,
            "vector_svg": '<svg viewBox="0 0 100 100"><polygon points="50,5 90,90 10,90" fill="#38bdf8"/></svg>',
        },
    )
    rev_8, details_svg = apply_creative_operation(config, context, op_clip_svg)
    assert details_svg["added_clip"]["clip_id"] == "clip_vector_logo"

    # 3. Trim video clip with ripple and verify duration
    op_trim = CreativeOperation(
        kind="trim_nle_clip",
        project_id=project_id,
        parent_revision_id=rev_8.revision_id,
        params={
            "clip_id": "clip_main_video",
            "start_time": 0.0,
            "end_time": 10.0,
            "ripple": True,
        },
    )
    rev_9, trim_details = apply_creative_operation(config, context, op_trim)
    assert trim_details["trimmed_clip"]["end_time"] == 10.0

    # 4. Split video clip at 5.0s
    op_split = CreativeOperation(
        kind="split_nle_clip",
        project_id=project_id,
        parent_revision_id=rev_9.revision_id,
        params={
            "clip_id": "clip_main_video",
            "split_time": 5.0,
        },
    )
    rev_10, split_details = apply_creative_operation(config, context, op_split)
    assert split_details["clip_a"]["end_time"] == 5.0
    assert split_details["clip_b"]["start_time"] == 5.0

    # 5. Add crossfade transition between the two split video clips
    clip_b_id = split_details["clip_b"]["clip_id"]
    op_trans = CreativeOperation(
        kind="add_nle_transition",
        project_id=project_id,
        parent_revision_id=rev_10.revision_id,
        params={
            "clip_a_id": "clip_main_video",
            "clip_b_id": clip_b_id,
            "transition_type": "crossfade",
            "duration": 0.5,
        },
    )
    rev_11, _ = apply_creative_operation(config, context, op_trans)

    # 6. Read back and verify index.html and hyperframes.json
    html_text = (rev_11.manifest_path.parent / "index.html").read_text(encoding="utf-8")
    meta_json = json.loads((rev_11.manifest_path.parent / "hyperframes.json").read_text(encoding="utf-8"))

    # HTML contains all clip DOM representations
    assert 'data-hf-clip="clip_main_video"' in html_text
    assert 'data-hf-clip="clip_title_card"' in html_text
    assert 'Hermes Creative Workstation' in html_text
    assert 'polygon' in html_text
    assert 'data-volume="0.75"' in html_text

    # JSON metadata contains complete timeline structure
    assert "timeline" in meta_json
    timeline_meta = meta_json["timeline"]
    assert len(timeline_meta["tracks"]) == 4

    # 7. ETag conflict verification (stale parent revision)
    stale_op = CreativeOperation(
        kind="trim_nle_clip",
        project_id=project_id,
        parent_revision_id=rev_1.revision_id,  # Stale revision
        params={"clip_id": "clip_main_video", "start_time": 0.0, "end_time": 4.0},
        if_match="stale_etag_value",
    )
    with pytest.raises(CreativeConflictError, match="409 Conflict"):
        apply_creative_operation(config, context, stale_op)

    # 8. Reload revision from store
    reloaded = load_creative_revision(project_id, rev_11.revision_id)
    assert reloaded.revision_id == rev_11.revision_id

"""Tests for CWN-03 NLE cutting primitives with linked A/V, track locks, and ripple."""
from fractions import Fraction
import pytest

from workstation.creative_document import (
    Asset,
    Clip,
    Composition,
    CreativeDocument,
    Track,
    create_empty_project,
    document_to_dict,
)
from workstation.creative_time import CanonicalTime, RationalFps, TimeRange
from workstation.creative_commands import Actor, CreativeCommand, execute_command
from workstation.creative_transactions import CreativeHistory, CreativeTransaction
from workstation.creative_timeline import (
    split_clip_op,
    trim_clip_op,
    ripple_delete_op,
    slip_clip_op,
    slide_clip_op,
    roll_clip_op,
    set_clip_speed_op,
)


def _setup_nle_project():
    """Helper creating a 2-track project (Video track V1, Audio track A1) with linked clips."""
    fps = RationalFps(30000, 1001)
    doc = create_empty_project(name="NLE Timeline Project", fps=fps)
    comp = doc.compositions[0]

    asset = Asset(
        asset_id="a" * 32,
        name="interview.mp4",
        kind="video",
        path="media/interview.mp4",
        sha256="1" * 64,
        duration=CanonicalTime.from_seconds(60),
    )
    doc.assets[asset.asset_id] = asset

    # V1 track
    v_track = Track(track_id="1" * 32, name="V1", kind="video", z_index=0)
    # A1 track
    a_track = Track(track_id="2" * 32, name="A1", kind="audio", z_index=1)

    # 10s clip on timeline [0, 10), source [5, 15)
    v_clip = Clip(
        clip_id="c" * 32,
        track_id=v_track.track_id,
        asset_id=asset.asset_id,
        name="Interview Video",
        timeline_range=TimeRange(CanonicalTime.from_seconds(0), CanonicalTime.from_seconds(10)),
        source_in=CanonicalTime.from_seconds(5),
        speed=1.0,
        linked_clip_ids=["d" * 32],
    )
    a_clip = Clip(
        clip_id="d" * 32,
        track_id=a_track.track_id,
        asset_id=asset.asset_id,
        name="Interview Audio",
        timeline_range=TimeRange(CanonicalTime.from_seconds(0), CanonicalTime.from_seconds(10)),
        source_in=CanonicalTime.from_seconds(5),
        speed=1.0,
        linked_clip_ids=["c" * 32],
    )

    v_track.clips.append(v_clip)
    a_track.clips.append(a_clip)
    comp.tracks.extend([v_track, a_track])
    return doc, comp, v_clip, a_clip


def test_clip_split_with_linked_audio():
    doc, comp, v_clip, a_clip = _setup_nle_project()
    actor = Actor(actor_id="editor_1", actor_type="hermes_agent")

    # Split at t = 4.0s
    cmd = CreativeCommand(
        command_id="clip.split",
        params={
            "composition_id": comp.composition_id,
            "clip_id": v_clip.clip_id,
            "split_time": "4",
        },
        actor=actor,
        idempotency_key="split_1",
    )
    res = execute_command(doc, cmd)
    assert res.success is True

    # V1 and A1 should now both have 2 clips!
    v_track = comp.tracks[0]
    a_track = comp.tracks[1]
    assert len(v_track.clips) == 2
    assert len(a_track.clips) == 2

    v_left, v_right = v_track.clips[0], v_track.clips[1]
    assert v_left.timeline_range.start.to_seconds() == 0
    assert v_left.timeline_range.end.to_seconds() == 4
    assert v_left.source_in.to_seconds() == 5

    assert v_right.timeline_range.start.to_seconds() == 4
    assert v_right.timeline_range.end.to_seconds() == 10
    # source_in of right clip should be 5 + 4 = 9s!
    assert v_right.source_in.to_seconds() == 9

    # Audio clip symmetrically split!
    a_left, a_right = a_track.clips[0], a_track.clips[1]
    assert a_left.timeline_range.end.to_seconds() == 4
    assert a_right.source_in.to_seconds() == 9
    assert a_left.linked_clip_ids == [v_left.clip_id]
    assert a_right.linked_clip_ids == [v_right.clip_id]


def test_clip_split_at_2x_speed():
    doc, comp, v_clip, a_clip = _setup_nle_project()
    v_clip.speed = 2.0
    a_clip.speed = 2.0

    actor = Actor(actor_id="editor_1", actor_type="hermes_agent")
    # Split at t = 2s on timeline. At 2x speed, 2s on timeline advances source by 4s!
    cmd = CreativeCommand(
        command_id="clip.split",
        params={
            "composition_id": comp.composition_id,
            "clip_id": v_clip.clip_id,
            "split_time": "2",
        },
        actor=actor,
        idempotency_key="split_2x",
    )
    res = execute_command(doc, cmd)
    assert res.success is True

    v_track = comp.tracks[0]
    v_left, v_right = v_track.clips[0], v_track.clips[1]
    assert v_left.source_in.to_seconds() == 5
    # 5 + 2s * 2.0 = 9s!
    assert v_right.source_in.to_seconds() == 9


def test_clip_trim_and_ripple_respects_locked_tracks():
    doc, comp, v_clip, a_clip = _setup_nle_project()
    # Add second clip to V1: [10, 20)
    v2_clip = Clip(
        clip_id="e" * 32,
        track_id=comp.tracks[0].track_id,
        asset_id=v_clip.asset_id,
        name="V1 Clip 2",
        timeline_range=TimeRange(CanonicalTime.from_seconds(10), CanonicalTime.from_seconds(20)),
        source_in=CanonicalTime.from_seconds(20),
    )
    comp.tracks[0].clips.append(v2_clip)

    # Add a clip on a LOCKED music track M1: [0, 25)
    m_track = Track(track_id="3" * 32, name="Music", kind="audio", z_index=2, locked=True)
    m_clip = Clip(
        clip_id="f" * 32,
        track_id=m_track.track_id,
        asset_id=v_clip.asset_id,
        name="Background Music",
        timeline_range=TimeRange(CanonicalTime.from_seconds(0), CanonicalTime.from_seconds(25)),
        source_in=CanonicalTime.from_seconds(0),
    )
    m_track.clips.append(m_clip)
    comp.tracks.append(m_track)

    actor = Actor(actor_id="editor_1", actor_type="hermes_agent")
    # Ripple trim v_clip end from 10 to 6 (duration shortened by 4s)
    cmd = CreativeCommand(
        command_id="clip.trim",
        params={
            "composition_id": comp.composition_id,
            "clip_id": v_clip.clip_id,
            "new_end": "6",
            "ripple": True,
        },
        actor=actor,
        idempotency_key="trim_ripple_1",
    )
    res = execute_command(doc, cmd)
    assert res.success is True

    # v_clip end is now 6
    assert v_clip.timeline_range.end.to_seconds() == 6
    # v2_clip rippled from 10 to 6 (shifted earlier by 4s)
    assert v2_clip.timeline_range.start.to_seconds() == 6
    assert v2_clip.timeline_range.end.to_seconds() == 16

    # Locked track M1 must NOT shift at all!
    assert m_clip.timeline_range.start.to_seconds() == 0
    assert m_clip.timeline_range.end.to_seconds() == 25


def test_clip_ripple_delete_removes_clip_and_shifts_following():
    doc, comp, v_clip, a_clip = _setup_nle_project()
    # Add following clips at [10, 15)
    v2_clip = Clip(
        clip_id="e" * 32,
        track_id=comp.tracks[0].track_id,
        asset_id=v_clip.asset_id,
        name="V1 Clip 2",
        timeline_range=TimeRange(CanonicalTime.from_seconds(10), CanonicalTime.from_seconds(15)),
        source_in=CanonicalTime.from_seconds(20),
    )
    comp.tracks[0].clips.append(v2_clip)

    actor = Actor(actor_id="editor_1", actor_type="hermes_agent")
    cmd = CreativeCommand(
        command_id="clip.rippleDelete",
        params={
            "composition_id": comp.composition_id,
            "clip_id": v_clip.clip_id,
        },
        actor=actor,
        idempotency_key="rd_1",
    )
    res = execute_command(doc, cmd)
    assert res.success is True

    # v_clip and its linked a_clip deleted
    assert len(comp.tracks[0].clips) == 1
    assert comp.tracks[0].clips[0].clip_id == v2_clip.clip_id
    # v2_clip shifted from 10 down to 0 (by deleted duration 10s)!
    assert comp.tracks[0].clips[0].timeline_range.start.to_seconds() == 0
    assert comp.tracks[0].clips[0].timeline_range.end.to_seconds() == 5


def test_clip_slip_and_slide():
    doc, comp, v_clip, a_clip = _setup_nle_project()
    actor = Actor(actor_id="editor_1", actor_type="hermes_agent")

    # Slip: shifts source_in by +2s without changing timeline placement
    cmd_slip = CreativeCommand(
        command_id="clip.slip",
        params={"composition_id": comp.composition_id, "clip_id": v_clip.clip_id, "delta_seconds": "2"},
        actor=actor,
        idempotency_key="slip_1",
    )
    res = execute_command(doc, cmd_slip)
    assert res.success is True
    assert v_clip.timeline_range.start.to_seconds() == 0
    assert v_clip.timeline_range.end.to_seconds() == 10
    assert v_clip.source_in.to_seconds() == 7  # 5 + 2 = 7

    # Slide: shifts timeline position by +3s without changing source_in
    cmd_slide = CreativeCommand(
        command_id="clip.slide",
        params={"composition_id": comp.composition_id, "clip_id": v_clip.clip_id, "delta_seconds": "3"},
        actor=actor,
        idempotency_key="slide_1",
    )
    res = execute_command(doc, cmd_slide)
    assert res.success is True
    assert v_clip.timeline_range.start.to_seconds() == 3
    assert v_clip.timeline_range.end.to_seconds() == 13
    assert v_clip.source_in.to_seconds() == 7


def test_clip_roll_between_adjacent_clips():
    doc, comp, v_clip, a_clip = _setup_nle_project()
    # Add adjacent clip v2 at [10, 18) with source_in 0
    v2_clip = Clip(
        clip_id="e" * 32,
        track_id=comp.tracks[0].track_id,
        asset_id=v_clip.asset_id,
        name="V1 Clip 2",
        timeline_range=TimeRange(CanonicalTime.from_seconds(10), CanonicalTime.from_seconds(18)),
        source_in=CanonicalTime.from_seconds(0),
    )
    comp.tracks[0].clips.append(v2_clip)

    actor = Actor(actor_id="editor_1", actor_type="hermes_agent")
    # Roll cut from 10 to 12 (+2s): v1 extends to 12, v2 starts at 12 with source_in shifted by 2s!
    cmd_roll = CreativeCommand(
        command_id="clip.roll",
        params={
            "composition_id": comp.composition_id,
            "left_clip_id": v_clip.clip_id,
            "right_clip_id": v2_clip.clip_id,
            "new_split_time": "12",
        },
        actor=actor,
        idempotency_key="roll_1",
    )
    res = execute_command(doc, cmd_roll)
    assert res.success is True
    assert v_clip.timeline_range.end.to_seconds() == 12
    assert v2_clip.timeline_range.start.to_seconds() == 12
    assert v2_clip.source_in.to_seconds() == 2
    # Total combined timeline duration is still 18s!
    assert v2_clip.timeline_range.end.to_seconds() == 18


def test_timeline_undo_recovers_exact_state():
    doc, comp, v_clip, a_clip = _setup_nle_project()
    initial_dict = document_to_dict(doc)
    history = CreativeHistory()
    actor = Actor(actor_id="editor_1", actor_type="hermes_agent")

    # Split clip
    tx = CreativeTransaction(commands=[
        CreativeCommand(
            command_id="clip.split",
            params={"composition_id": comp.composition_id, "clip_id": v_clip.clip_id, "split_time": "5"},
            actor=actor,
            idempotency_key="tx_split",
        )
    ])
    history.commit(doc, tx)
    assert len(doc.compositions[0].tracks[0].clips) == 2

    # Undo recovers exact initial document!
    history.undo(doc)
    assert document_to_dict(doc) == initial_dict

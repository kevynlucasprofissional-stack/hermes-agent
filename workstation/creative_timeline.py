"""NLE cutting primitives, linked A/V, track locks, and ripple logic (CWN-03)."""
from __future__ import annotations

from fractions import Fraction
from typing import Any
import uuid

from workstation.creative_document import (
    Clip,
    Composition,
    CreativeDocument,
    Track,
)
from workstation.creative_time import (
    CanonicalTime,
    MediaTimeMap,
    RationalFps,
    TimeRange,
)


class TimelineOperationError(ValueError):
    """Raised when an NLE cutting operation fails validation or constraints."""
    pass


def _find_clip_and_track(doc: CreativeDocument, comp_id: str, clip_id: str) -> tuple[Composition, Track, Clip, int]:
    for c in doc.compositions:
        if c.composition_id == comp_id:
            for t in c.tracks:
                for idx, cl in enumerate(t.clips):
                    if cl.clip_id == clip_id:
                        return c, t, cl, idx
    raise TimelineOperationError(f"Clip {clip_id} not found in composition {comp_id}")


def split_clip_op(
    doc: CreativeDocument,
    composition_id: str,
    clip_id: str,
    split_time: CanonicalTime,
) -> tuple[Clip, Clip, list[tuple[Clip, Clip]]]:
    """Split a clip (and its linked companion clips) at split_time into left and right clips."""
    comp, track, clip, idx = _find_clip_and_track(doc, composition_id, clip_id)
    if track.locked:
        raise TimelineOperationError(f"Cannot split clip {clip_id}: track {track.track_id} is locked")

    if not (clip.timeline_range.start < split_time < clip.timeline_range.end):
        raise TimelineOperationError(
            f"Split time {split_time} must be strictly inside clip timeline range {clip.timeline_range.start}..{clip.timeline_range.end}"
        )

    t_map = MediaTimeMap(clip.timeline_range, clip.source_in, clip.speed)
    split_source = t_map.timeline_to_source(split_time)

    # Left clip retains original clip_id
    left_range = TimeRange(clip.timeline_range.start, split_time)
    right_range = TimeRange(split_time, clip.timeline_range.end)
    right_clip_id = uuid.uuid4().hex

    right_clip = Clip(
        clip_id=right_clip_id,
        track_id=track.track_id,
        asset_id=clip.asset_id,
        name=f"{clip.name} (Part 2)",
        timeline_range=right_range,
        source_in=split_source,
        speed=clip.speed,
        reverse=clip.reverse,
        freeze=clip.freeze,
        properties=dict(clip.properties),
    )
    clip.timeline_range = left_range

    # Insert right clip immediately after left clip
    track.clips.insert(idx + 1, right_clip)

    # Symmetrically split linked clips (e.g. companion audio tracks)
    linked_splits: list[tuple[Clip, Clip]] = []
    old_linked_ids = list(clip.linked_clip_ids)
    new_left_links: list[str] = []
    new_right_links: list[str] = []

    for l_id in old_linked_ids:
        try:
            _, l_track, l_clip, l_idx = _find_clip_and_track(doc, composition_id, l_id)
            if l_track.locked:
                continue
            if l_clip.timeline_range.start < split_time < l_clip.timeline_range.end:
                l_map = MediaTimeMap(l_clip.timeline_range, l_clip.source_in, l_clip.speed)
                l_split_source = l_map.timeline_to_source(split_time)
                l_right_id = uuid.uuid4().hex

                l_right_clip = Clip(
                    clip_id=l_right_id,
                    track_id=l_track.track_id,
                    asset_id=l_clip.asset_id,
                    name=f"{l_clip.name} (Part 2)",
                    timeline_range=TimeRange(split_time, l_clip.timeline_range.end),
                    source_in=l_split_source,
                    speed=l_clip.speed,
                    reverse=l_clip.reverse,
                    freeze=l_clip.freeze,
                    properties=dict(l_clip.properties),
                )
                l_clip.timeline_range = TimeRange(l_clip.timeline_range.start, split_time)
                l_track.clips.insert(l_idx + 1, l_right_clip)

                l_clip.linked_clip_ids = [clip.clip_id]
                l_right_clip.linked_clip_ids = [right_clip.clip_id]

                new_left_links.append(l_clip.clip_id)
                new_right_links.append(l_right_clip.clip_id)
                linked_splits.append((l_clip, l_right_clip))
        except TimelineOperationError:
            pass

    clip.linked_clip_ids = new_left_links
    right_clip.linked_clip_ids = new_right_links
    return clip, right_clip, linked_splits


def trim_clip_op(
    doc: CreativeDocument,
    composition_id: str,
    clip_id: str,
    new_start: CanonicalTime | None = None,
    new_end: CanonicalTime | None = None,
    ripple: bool = False,
) -> None:
    """Trim a clip's head or tail, optionally rippling subsequent clips on unlocked tracks."""
    comp, track, clip, _ = _find_clip_and_track(doc, composition_id, clip_id)
    if track.locked:
        raise TimelineOperationError(f"Cannot trim clip {clip_id}: track {track.track_id} is locked")

    old_start = clip.timeline_range.start
    old_end = clip.timeline_range.end
    old_duration = clip.timeline_range.duration

    target_start = new_start if new_start is not None else old_start
    target_end = new_end if new_end is not None else old_end

    new_range = TimeRange(target_start, target_end)
    new_duration = new_range.duration

    # Adjust source_in if head was trimmed
    if target_start != old_start:
        delta_start = target_start - old_start if target_start > old_start else -(old_start - target_start)
        speed_frac = Fraction(clip.speed).limit_denominator(1_000_000)
        source_delta = delta_start.fraction * speed_frac
        clip.source_in = CanonicalTime(clip.source_in.fraction + source_delta)

    clip.timeline_range = new_range

    # Adjust linked clips
    for l_id in clip.linked_clip_ids:
        try:
            _, l_trk, l_cl, _ = _find_clip_and_track(doc, composition_id, l_id)
            if not l_trk.locked:
                l_cl.timeline_range = new_range
                if target_start != old_start:
                    l_cl.source_in = clip.source_in
        except TimelineOperationError:
            pass

    # Ripple subsequent clips if requested
    if ripple:
        delta_secs = new_duration.fraction - old_duration.fraction
        # Shift following clips on all unlocked tracks
        for trk in comp.tracks:
            if trk.locked:
                continue
            for cl in trk.clips:
                if cl.clip_id == clip.clip_id or cl.clip_id in clip.linked_clip_ids:
                    continue
                if cl.timeline_range.start >= old_end:
                    sh_start = CanonicalTime(cl.timeline_range.start.fraction + delta_secs)
                    sh_end = CanonicalTime(cl.timeline_range.end.fraction + delta_secs)
                    cl.timeline_range = TimeRange(sh_start, sh_end)


def ripple_delete_op(
    doc: CreativeDocument,
    composition_id: str,
    clip_id: str,
) -> None:
    """Delete a clip and linked clips, rippling subsequent clips earlier to close the gap."""
    comp, track, clip, idx = _find_clip_and_track(doc, composition_id, clip_id)
    if track.locked:
        raise TimelineOperationError(f"Cannot delete clip {clip_id}: track {track.track_id} is locked")

    deleted_duration = clip.timeline_range.duration
    old_end = clip.timeline_range.end

    track.clips.pop(idx)

    # Delete linked companion clips
    for l_id in clip.linked_clip_ids:
        try:
            _, l_trk, _, l_idx = _find_clip_and_track(doc, composition_id, l_id)
            if not l_trk.locked:
                l_trk.clips.pop(l_idx)
        except TimelineOperationError:
            pass

    # Ripple shift earlier by deleted_duration for clips starting at or after old_end on unlocked tracks
    delta_secs = -deleted_duration.fraction
    for trk in comp.tracks:
        if trk.locked:
            continue
        for cl in trk.clips:
            if cl.timeline_range.start >= old_end:
                sh_start = CanonicalTime(cl.timeline_range.start.fraction + delta_secs)
                sh_end = CanonicalTime(cl.timeline_range.end.fraction + delta_secs)
                cl.timeline_range = TimeRange(sh_start, sh_end)


def slip_clip_op(
    doc: CreativeDocument,
    composition_id: str,
    clip_id: str,
    delta_seconds: CanonicalTime,
) -> None:
    """Slip changes the clip's source in-point without moving its timeline placement."""
    comp, track, clip, _ = _find_clip_and_track(doc, composition_id, clip_id)
    if track.locked:
        raise TimelineOperationError(f"Cannot slip clip {clip_id}: track {track.track_id} is locked")

    new_source_in = clip.source_in + delta_seconds
    clip.source_in = new_source_in

    for l_id in clip.linked_clip_ids:
        try:
            _, l_trk, l_cl, _ = _find_clip_and_track(doc, composition_id, l_id)
            if not l_trk.locked:
                l_cl.source_in = new_source_in
        except TimelineOperationError:
            pass


def slide_clip_op(
    doc: CreativeDocument,
    composition_id: str,
    clip_id: str,
    delta_seconds: CanonicalTime,
) -> None:
    """Slide moves the clip along the timeline without changing its source in-point."""
    comp, track, clip, _ = _find_clip_and_track(doc, composition_id, clip_id)
    if track.locked:
        raise TimelineOperationError(f"Cannot slide clip {clip_id}: track {track.track_id} is locked")

    new_start = clip.timeline_range.start + delta_seconds
    new_end = clip.timeline_range.end + delta_seconds
    clip.timeline_range = TimeRange(new_start, new_end)

    for l_id in clip.linked_clip_ids:
        try:
            _, l_trk, l_cl, _ = _find_clip_and_track(doc, composition_id, l_id)
            if not l_trk.locked:
                l_cl.timeline_range = TimeRange(new_start, new_end)
        except TimelineOperationError:
            pass


def roll_clip_op(
    doc: CreativeDocument,
    composition_id: str,
    left_clip_id: str,
    right_clip_id: str,
    new_split_time: CanonicalTime,
) -> None:
    """Roll adjusts the edit point between two adjacent clips, maintaining overall duration."""
    comp, l_trk, l_clip, _ = _find_clip_and_track(doc, composition_id, left_clip_id)
    _, r_trk, r_clip, _ = _find_clip_and_track(doc, composition_id, right_clip_id)

    if l_trk.locked or r_trk.locked:
        raise TimelineOperationError("Cannot roll cut: one or both tracks are locked")

    old_cut = l_clip.timeline_range.end
    if old_cut != r_clip.timeline_range.start:
        raise TimelineOperationError("Roll requires adjacent clips touching at the same edit boundary")

    if not (l_clip.timeline_range.start < new_split_time < r_clip.timeline_range.end):
        raise TimelineOperationError(f"New edit point {new_split_time} must remain between {l_clip.timeline_range.start} and {r_clip.timeline_range.end}")

    # Shift on cut
    delta = new_split_time.fraction - old_cut.fraction

    l_clip.timeline_range = TimeRange(l_clip.timeline_range.start, new_split_time)

    speed_r_frac = Fraction(r_clip.speed).limit_denominator(1_000_000)
    new_r_source_in = CanonicalTime(r_clip.source_in.fraction + delta * speed_r_frac)
    r_clip.source_in = new_r_source_in
    r_clip.timeline_range = TimeRange(new_split_time, r_clip.timeline_range.end)


def set_clip_speed_op(
    doc: CreativeDocument,
    composition_id: str,
    clip_id: str,
    speed: float,
    keep_duration: bool = False,
) -> None:
    """Set clip speed factor (e.g. 2.0x, 0.5x, -1.0x reverse)."""
    comp, track, clip, _ = _find_clip_and_track(doc, composition_id, clip_id)
    if track.locked:
        raise TimelineOperationError(f"Cannot set speed: track {track.track_id} is locked")

    if speed == 0.0:
        clip.freeze = True
        return

    old_speed = clip.speed
    clip.speed = speed
    if speed < 0:
        clip.reverse = True

    if not keep_duration:
        # Scale timeline duration inversely with speed
        scale = abs(old_speed / speed)
        orig_dur = clip.timeline_range.duration.fraction
        new_dur_frac = orig_dur * Fraction(scale).limit_denominator(1_000_000)
        new_end = CanonicalTime(clip.timeline_range.start.fraction + new_dur_frac)
        clip.timeline_range = TimeRange(clip.timeline_range.start, new_end)

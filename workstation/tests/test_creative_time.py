"""Tests for CWN-01 canonical rational time and source-to-timeline mapping."""
from fractions import Fraction
import pytest

from workstation.creative_time import (
    CanonicalTime,
    RationalFps,
    TimeRange,
    MediaTimeMap,
    TimecodeFormat,
    format_timecode,
    parse_timecode,
)


def test_rational_fps_standards():
    fps_24 = RationalFps(24, 1)
    assert fps_24.as_fraction() == Fraction(24, 1)
    assert float(fps_24) == 24.0

    fps_ntsc = RationalFps(30000, 1001)
    assert fps_ntsc.numerator == 30000
    assert fps_ntsc.denominator == 1001
    assert abs(float(fps_ntsc) - 29.97002997) < 1e-6
    assert fps_ntsc.is_drop_frame_eligible() is True

    fps_60 = RationalFps(60, 1)
    assert float(fps_60) == 60.0

    fps_5994 = RationalFps(60000, 1001)
    assert abs(float(fps_5994) - 59.94005994) < 1e-6

    # Rejection of invalid rates
    with pytest.raises(ValueError, match="Numerator and denominator must be positive"):
        RationalFps(0, 1)
    with pytest.raises(ValueError, match="Numerator and denominator must be positive"):
        RationalFps(30, -1)


def test_canonical_time_ticks_and_conversions():
    # Canonical time base: 120,000 ticks/sec (common multiple of 24, 25, 30, 48, 50, 60, 1000)
    t0 = CanonicalTime.from_seconds(0.5)
    assert t0.to_seconds() == Fraction(1, 2)
    assert float(t0.to_seconds()) == 0.5

    t1 = CanonicalTime.from_frames(30, RationalFps(30, 1))
    assert t1.to_seconds() == Fraction(1, 1)

    # Frame rounding and boundaries: 0.5s at 29.97fps is frame 14 (14.985 frames; frame 15 starts at 0.5005s)
    fps_ntsc = RationalFps(30000, 1001)
    assert t0.to_frame(fps_ntsc) == 14
    t_f15 = CanonicalTime.from_frames(15, fps_ntsc)
    assert t_f15.to_frame(fps_ntsc) == 15


def test_canonical_time_arithmetic_and_validation():
    t1 = CanonicalTime.from_seconds(1)
    t2 = CanonicalTime.from_seconds(2)
    assert (t1 + t2).to_seconds() == Fraction(3, 1)
    assert (t2 - t1).to_seconds() == Fraction(1, 1)

    with pytest.raises(ValueError, match="Negative time not allowed"):
        _ = t1 - t2

    with pytest.raises(ValueError, match="Invalid non-finite time"):
        CanonicalTime.from_seconds(float("nan"))
    with pytest.raises(ValueError, match="Invalid non-finite time"):
        CanonicalTime.from_seconds(float("inf"))


def test_time_range_half_open_interval():
    r = TimeRange(CanonicalTime.from_seconds(1), CanonicalTime.from_seconds(4))
    assert r.duration.to_seconds() == Fraction(3, 1)
    assert r.contains(CanonicalTime.from_seconds(1)) is True
    assert r.contains(CanonicalTime.from_seconds(3.99)) is True
    assert r.contains(CanonicalTime.from_seconds(4)) is False  # Half-open [start, end)

    # Overlaps
    r2 = TimeRange(CanonicalTime.from_seconds(3), CanonicalTime.from_seconds(5))
    assert r.overlaps(r2) is True

    r3 = TimeRange(CanonicalTime.from_seconds(4), CanonicalTime.from_seconds(6))
    assert r.overlaps(r3) is False  # Touching at boundary does not overlap

    # Rejection of zero or negative duration
    with pytest.raises(ValueError, match="Duration must be strictly positive"):
        TimeRange(CanonicalTime.from_seconds(3), CanonicalTime.from_seconds(3))
    with pytest.raises(ValueError, match="Duration must be strictly positive"):
        TimeRange(CanonicalTime.from_seconds(3), CanonicalTime.from_seconds(2))


def test_smpte_timecode_drop_frame_and_non_drop():
    fps_ntsc = RationalFps(30000, 1001)

    # Non-drop frame at 30fps
    fps_30 = RationalFps(30, 1)
    tc_ndf = format_timecode(CanonicalTime.from_seconds(65.5), fps_30, drop_frame=False)
    assert tc_ndf == "00:01:05:15"
    parsed = parse_timecode(tc_ndf, fps_30)
    assert parsed.to_seconds() == Fraction(131, 2)

    # Drop frame at 29.97fps: uses ';' as separator
    tc_df = format_timecode(CanonicalTime.from_seconds(60.0), fps_ntsc, drop_frame=True)
    assert ";" in tc_df
    # In SMPTE drop-frame, frame numbers 0 and 1 are dropped at the start of every minute except minutes 0, 10, 20...
    parsed_df = parse_timecode(tc_df, fps_ntsc)
    assert abs(float(parsed_df.to_seconds()) - 60.0) < 0.05


def test_source_to_timeline_mapping_normal_speed():
    # 5-second clip placed at timeline 10s to 15s, mapping to source 2s to 7s
    t_map = MediaTimeMap(
        timeline_range=TimeRange(CanonicalTime.from_seconds(10), CanonicalTime.from_seconds(15)),
        source_in=CanonicalTime.from_seconds(2),
        speed=1.0,
    )
    assert t_map.timeline_to_source(CanonicalTime.from_seconds(10)).to_seconds() == Fraction(2, 1)
    assert t_map.timeline_to_source(CanonicalTime.from_seconds(12.5)).to_seconds() == Fraction(9, 2)
    assert t_map.timeline_to_source(CanonicalTime.from_seconds(14.99)).to_seconds() == Fraction(699, 100)

    # Outside range returns ValueError
    with pytest.raises(ValueError, match="Timeline time outside range"):
        t_map.timeline_to_source(CanonicalTime.from_seconds(9.99))


def test_source_to_timeline_mapping_2x_speed():
    # 2 seconds on timeline at 2x speed consumes 4 seconds of source media!
    t_map = MediaTimeMap(
        timeline_range=TimeRange(CanonicalTime.from_seconds(0), CanonicalTime.from_seconds(2)),
        source_in=CanonicalTime.from_seconds(10),
        speed=2.0,
    )
    # At t=0s -> source=10s
    assert t_map.timeline_to_source(CanonicalTime.from_seconds(0)).to_seconds() == Fraction(10, 1)
    # At t=1s -> source=12s
    assert t_map.timeline_to_source(CanonicalTime.from_seconds(1)).to_seconds() == Fraction(12, 1)
    # At t=2s (boundary) -> source=14s
    assert t_map.source_out.to_seconds() == Fraction(14, 1)


def test_source_to_timeline_mapping_reverse():
    # Reverse playback: timeline 0 to 3s, source spans from 5s down to 2s
    t_map = MediaTimeMap(
        timeline_range=TimeRange(CanonicalTime.from_seconds(0), CanonicalTime.from_seconds(3)),
        source_in=CanonicalTime.from_seconds(5),
        speed=-1.0,
    )
    # At t=0s -> source=5s
    assert t_map.timeline_to_source(CanonicalTime.from_seconds(0)).to_seconds() == Fraction(5, 1)
    # At t=1s -> source=4s
    assert t_map.timeline_to_source(CanonicalTime.from_seconds(1)).to_seconds() == Fraction(4, 1)
    # At t=3s -> source=2s
    assert t_map.source_out.to_seconds() == Fraction(2, 1)


def test_source_to_timeline_mapping_freeze_frame():
    # Freeze frame: speed=0, holds frame at source_in=5.0s for 4s of timeline
    t_map = MediaTimeMap(
        timeline_range=TimeRange(CanonicalTime.from_seconds(10), CanonicalTime.from_seconds(14)),
        source_in=CanonicalTime.from_seconds(5),
        speed=0.0,
    )
    assert t_map.timeline_to_source(CanonicalTime.from_seconds(10)).to_seconds() == Fraction(5, 1)
    assert t_map.timeline_to_source(CanonicalTime.from_seconds(12)).to_seconds() == Fraction(5, 1)
    assert t_map.timeline_to_source(CanonicalTime.from_seconds(13.99)).to_seconds() == Fraction(5, 1)

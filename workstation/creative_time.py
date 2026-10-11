"""Canonical rational time, frame conversions, and source-to-timeline mapping (CWN-01)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import math
import re


class TimecodeFormat(str, Enum):
    DROP_FRAME = "drop_frame"
    NON_DROP_FRAME = "non_drop_frame"


@dataclass(frozen=True)
class RationalFps:
    numerator: int
    denominator: int = 1

    def __post_init__(self):
        if not isinstance(self.numerator, int) or not isinstance(self.denominator, int):
            raise TypeError("Fps numerator and denominator must be integers")
        if self.numerator <= 0 or self.denominator <= 0:
            raise ValueError("Numerator and denominator must be positive")

    def as_fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    def __float__(self) -> float:
        return float(self.as_fraction())

    def is_drop_frame_eligible(self) -> bool:
        """Drop-frame timecode applies primarily to NTSC 29.97 and 59.94 fps."""
        frac = self.as_fraction()
        return frac in {Fraction(30000, 1001), Fraction(60000, 1001)}


@dataclass(frozen=True)
class CanonicalTime:
    """Exact rational time in seconds, preventing floating-point drift across cuts."""
    fraction: Fraction

    def __post_init__(self):
        if not isinstance(self.fraction, Fraction):
            object.__setattr__(self, "fraction", Fraction(self.fraction))
        if self.fraction < 0:
            raise ValueError("Negative time not allowed in canonical editing space")

    @classmethod
    def zero(cls) -> CanonicalTime:
        return cls(Fraction(0, 1))

    @classmethod
    def from_seconds(cls, seconds: float | int | Fraction | str) -> CanonicalTime:
        if isinstance(seconds, float):
            if math.isnan(seconds) or math.isinf(seconds):
                raise ValueError("Invalid non-finite time")
            # Convert float to exact rational
            return cls(Fraction(seconds).limit_denominator(1_000_000))
        return cls(Fraction(seconds))

    @classmethod
    def from_frames(cls, frame_index: int, fps: RationalFps) -> CanonicalTime:
        if frame_index < 0:
            raise ValueError("Frame index cannot be negative")
        return cls(Fraction(frame_index) / fps.as_fraction())

    def to_seconds(self) -> Fraction:
        return self.fraction

    def to_frame(self, fps: RationalFps) -> int:
        """Calculate the discrete integer frame index for half-open interval [frame, frame+1)."""
        exact_frame = self.fraction * fps.as_fraction()
        return int(math.floor(float(exact_frame) + 1e-9))

    def __add__(self, other: CanonicalTime) -> CanonicalTime:
        return CanonicalTime(self.fraction + other.fraction)

    def __sub__(self, other: CanonicalTime) -> CanonicalTime:
        diff = self.fraction - other.fraction
        if diff < 0:
            raise ValueError("Negative time not allowed")
        return CanonicalTime(diff)

    def __lt__(self, other: CanonicalTime) -> bool:
        return self.fraction < other.fraction

    def __le__(self, other: CanonicalTime) -> bool:
        return self.fraction <= other.fraction

    def __gt__(self, other: CanonicalTime) -> bool:
        return self.fraction > other.fraction

    def __ge__(self, other: CanonicalTime) -> bool:
        return self.fraction >= other.fraction

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CanonicalTime):
            return False
        return self.fraction == other.fraction

    def __repr__(self) -> str:
        return f"CanonicalTime({self.fraction}s)"


@dataclass(frozen=True)
class TimeRange:
    """Half-open interval [start, end) representing a continuous time segment."""
    start: CanonicalTime
    end: CanonicalTime

    def __post_init__(self):
        if self.end <= self.start:
            raise ValueError("Duration must be strictly positive (end > start)")

    @property
    def duration(self) -> CanonicalTime:
        return self.end - self.start

    def contains(self, t: CanonicalTime) -> bool:
        return self.start <= t < self.end

    def overlaps(self, other: TimeRange) -> bool:
        return self.start < other.end and other.start < self.end


def format_timecode(time: CanonicalTime, fps: RationalFps, drop_frame: bool = False) -> str:
    """Format SMPTE timecode (HH:MM:SS:FF or HH:MM:SS;FF for drop-frame)."""
    fps_frac = fps.as_fraction()
    if drop_frame and fps.is_drop_frame_eligible():
        # SMPTE drop-frame algorithm for 29.97 fps (30000/1001)
        # Drop 2 frames per minute except every 10th minute
        total_seconds = float(time.to_seconds())
        # Nominal frame count
        nominal_fps = round(float(fps))
        frame_number = time.to_frame(fps)
        drop_frames = 2 if nominal_fps == 30 else 4
        frames_per_10min = round(nominal_fps * 60 * 10 * 1000 / 1001)
        frames_per_min = round(nominal_fps * 60 * 1000 / 1001) - drop_frames

        d = frame_number // frames_per_10min
        m = frame_number % frames_per_10min
        if m > drop_frames:
            frame_number += drop_frames * 9 * d + drop_frames * ((m - drop_frames) // frames_per_min)
        else:
            frame_number += drop_frames * 9 * d

        ff = frame_number % nominal_fps
        ss = (frame_number // nominal_fps) % 60
        mm = ((frame_number // nominal_fps) // 60) % 60
        hh = ((frame_number // nominal_fps) // 3600)
        return f"{hh:02d}:{mm:02d}:{ss:02d};{ff:02d}"
    else:
        # Non-drop frame
        nominal_fps = round(float(fps))
        frame_idx = time.to_frame(fps)
        ff = frame_idx % nominal_fps
        total_secs = frame_idx // nominal_fps
        ss = total_secs % 60
        mm = (total_secs // 60) % 60
        hh = total_secs // 3600
        return f"{hh:02d}:{mm:02d}:{ss:02d}:{ff:02d}"


def parse_timecode(tc: str, fps: RationalFps) -> CanonicalTime:
    """Parse SMPTE timecode string back into CanonicalTime."""
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})([:;])(\d{2})", tc)
    if not match:
        raise ValueError(f"Invalid timecode format: {tc}")
    hh, mm, ss, sep, ff = match.groups()
    hours, minutes, seconds, frames = int(hh), int(mm), int(ss), int(ff)
    nominal_fps = round(float(fps))

    if sep == ";":
        # Drop-frame calculation
        drop_frames = 2 if nominal_fps == 30 else 4
        total_minutes = hours * 60 + minutes
        frame_number = ((hours * 3600 + minutes * 60 + seconds) * nominal_fps + frames)
        frame_number -= drop_frames * (total_minutes - total_minutes // 10)
        return CanonicalTime.from_frames(frame_number, fps)
    else:
        total_frames = (hours * 3600 + minutes * 60 + seconds) * nominal_fps + frames
        return CanonicalTime.from_frames(total_frames, fps)


@dataclass(frozen=True)
class MediaTimeMap:
    """Bi-directional mapping between timeline position and source media position."""
    timeline_range: TimeRange
    source_in: CanonicalTime
    speed: float = 1.0

    @property
    def source_duration(self) -> CanonicalTime:
        if self.speed == 0.0:
            return CanonicalTime.zero()
        raw_sec = abs(float(self.timeline_range.duration.to_seconds())) * abs(self.speed)
        return CanonicalTime.from_seconds(raw_sec)

    @property
    def source_out(self) -> CanonicalTime:
        if self.speed == 0.0:
            return self.source_in
        if self.speed < 0:
            # Reverse playback: source moves backwards from source_in
            diff_frac = self.timeline_range.duration.fraction * Fraction(abs(self.speed)).limit_denominator(1_000_000)
            return CanonicalTime(self.source_in.fraction - diff_frac)
        else:
            diff_frac = self.timeline_range.duration.fraction * Fraction(self.speed).limit_denominator(1_000_000)
            return CanonicalTime(self.source_in.fraction + diff_frac)

    def timeline_to_source(self, t: CanonicalTime) -> CanonicalTime:
        """Map a timeline time t in [start, end) to source time."""
        if not (self.timeline_range.start <= t <= self.timeline_range.end):
            raise ValueError(f"Timeline time outside range: {t}")
        offset = t - self.timeline_range.start
        if self.speed == 0.0:
            return self.source_in
        speed_frac = Fraction(self.speed).limit_denominator(1_000_000)
        if self.speed < 0:
            delta = offset.fraction * abs(speed_frac)
            return CanonicalTime(self.source_in.fraction - delta)
        else:
            delta = offset.fraction * speed_frac
            return CanonicalTime(self.source_in.fraction + delta)

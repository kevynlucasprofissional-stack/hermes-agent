"""Independent ffprobe and decoded-frame contracts; never execution certification."""
from __future__ import annotations

from fractions import Fraction
import hashlib
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def inspect_video_probe(probe: dict, *, width: int, height: int, fps: int,
                        frames: int, size_bytes: int) -> dict:
    streams = probe.get("streams")
    container = probe.get("format")
    if not isinstance(streams, list) or len(streams) != 1 or not isinstance(container, dict):
        raise ValueError("Creative video requires exactly one video stream")
    stream = streams[0]
    if (stream.get("codec_type") != "video" or stream.get("codec_name") != "h264"
            or stream.get("pix_fmt") != "yuv420p" or stream.get("width") != width
            or stream.get("height") != height or "mp4" not in container.get("format_name", "").split(",")):
        raise ValueError("Creative video codec/container/dimensions mismatch")
    try:
        duration = Fraction(container["duration"])
        stream_duration = Fraction(stream["duration"])
        actual_fps = Fraction(stream["avg_frame_rate"])
        nominal_fps = Fraction(stream["r_frame_rate"])
        decoded_frames = int(stream["nb_read_frames"])
        declared_frames = int(stream["nb_frames"])
        actual_size = int(container["size"])
    except (ValueError, TypeError, KeyError, ZeroDivisionError) as error:
        raise ValueError("Creative video probe is incomplete or non-finite") from error
    expected_duration = Fraction(frames, fps)
    if (actual_fps != fps or nominal_fps != fps or decoded_frames != frames or declared_frames != frames
            or actual_size != size_bytes or size_bytes <= 0
            or abs(duration - expected_duration) > Fraction(1, fps)
            or abs(stream_duration - expected_duration) > Fraction(1, fps)):
        raise ValueError("Creative video duration/rate/frame-count/size mismatch")
    return {"codec": "h264", "pixel_format": "yuv420p", "container": "mp4",
            "width": width, "height": height, "fps": fps, "decoded_frames": decoded_frames,
            "duration_seconds": float(duration), "size_bytes": size_bytes,
            "probe_kind": "ffprobe-count-frames"}


def inspect_video_preview(source: Path, preview: Path) -> dict:
    """Compare a frame decoded from MP4 to its immutable still-image input."""
    with Image.open(source) as expected, Image.open(preview) as actual:
        expected.load()
        actual.load()
        if actual.format != "PNG" or actual.size != expected.size:
            raise ValueError("Creative decoded preview format/dimensions mismatch")
        difference = ImageChops.difference(expected.convert("RGB"), actual.convert("RGB"))
        mean_error = sum(ImageStat.Stat(difference).mean) / 3
        if mean_error > 6:
            raise ValueError("Creative decoded video frame differs from source")
    return {"decoder": "Pillow", "mean_absolute_rgb_error": mean_error,
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "preview_sha256": hashlib.sha256(preview.read_bytes()).hexdigest()}

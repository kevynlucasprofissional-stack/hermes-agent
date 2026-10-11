from copy import deepcopy

import pytest
from PIL import Image

from workstation.creative_video_metadata import inspect_video_preview, inspect_video_probe


def test_probe_requires_decoded_frames_and_consistent_container_timing():
    probe = {"streams": [{"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p",
        "width": 360, "height": 640, "avg_frame_rate": "30/1", "r_frame_rate": "30/1",
        "duration": "8.0", "nb_read_frames": "240", "nb_frames": "240"}],
        "format": {"format_name": "mov,mp4", "duration": "8.0", "size": "1024"}}
    kwargs = dict(width=360, height=640, fps=30, frames=240, size_bytes=1024)
    assert inspect_video_probe(probe, **kwargs)["decoded_frames"] == 240
    for section, key, value in (("streams", "nb_read_frames", "239"), ("streams", "duration", "7"),
                                ("format", "size", "1025"), ("streams", "avg_frame_rate", "0/0")):
        changed = deepcopy(probe)
        target = changed[section][0] if section == "streams" else changed[section]
        target[key] = value
        with pytest.raises(ValueError):
            inspect_video_probe(changed, **kwargs)


def test_decoded_preview_must_resemble_immutable_input(tmp_path):
    source, preview = tmp_path / "source.png", tmp_path / "preview.png"
    Image.new("RGB", (32, 32), (20, 38, 61)).save(source)
    Image.new("RGB", (32, 32), (21, 39, 62)).save(preview)
    assert inspect_video_preview(source, preview)["mean_absolute_rgb_error"] == 1
    Image.new("RGB", (32, 32), "yellow").save(preview)
    with pytest.raises(ValueError, match="differs"):
        inspect_video_preview(source, preview)

"""Decode native Creative fixture outputs independently of Electron's renderer."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from PIL import Image
from workstation.creative_media import inspect_creative_png


def verify(root: Path) -> dict:
    receipt = json.loads((root / "native-receipt.json").read_text(encoding="utf-8"))
    first = receipt["first"]
    assert receipt["runtime"] == "electron-chromium"
    assert first["receipt"]["browserTaskId"] == first["task_id"]
    assert first["receipt"]["operationId"] == first["operation_id"]
    assert first["receipt"]["runId"] == "cw03a-native-run"
    source = (root / "invitation.creative.json").read_bytes()
    assert hashlib.sha256(source).hexdigest() == first["source_sha256"]
    assert hashlib.sha256((root / "invitation.svg").read_bytes()).hexdigest() == first["svg_sha256"]
    initial = inspect_creative_png(root / "invitation.png", width=360, height=640, sha256=first["sha256"])
    variant = inspect_creative_png(root / "invitation-variant.png", width=360, height=640,
                                   sha256=receipt["variant_sha256"])
    assert receipt["reopen_sha256"] == first["sha256"] != receipt["variant_sha256"]
    assert receipt["foreground_preserved"] is True
    assert set(receipt["negative_controls"]) == {"malformed-shape", "stale-source", "wrong-session", "stale-run", "human-control"}
    with Image.open(root / "invitation.png") as image:
        pixels = image.convert("RGB")
        assert pixels.getpixel((0, 0)) == (20, 38, 61), "background not rendered"
        assert pixels.getpixel((180, 130)) == (246, 200, 95), "circle not rendered"
        assert pixels.getpixel((40, 260)) == (35, 67, 102), "panel not rendered"
        assert len(pixels.getcolors(maxcolors=360 * 640) or []) > 10, "text/antialiasing absent"
    return {"schema_version": 1, "initial": initial, "variant": variant,
            "source_hash_match": True, "svg_hash_match": True, "pixel_controls": "pass",
            "scope": "native fixture media readback; not baseline/capability certification"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence_directory", type=Path)
    args = parser.parse_args()
    result = verify(args.evidence_directory)
    (args.evidence_directory / "independent-readback.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))

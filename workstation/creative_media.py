"""Independent media readback facts; these never certify an execution or capability."""
from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image


def inspect_creative_png(
    path: Path | str, *, width: int, height: int, sha256: str,
) -> dict:
    if (type(width) is not int or type(height) is not int or not 1 <= width <= 4096
            or not 1 <= height <= 4096 or width * height > 8_388_608):
        raise ValueError("Invalid expected PNG dimensions")
    target = Path(path)
    if target.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("Creative PNG exceeds size budget")
    with target.open("rb") as stream:
        actual_sha = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual_sha != sha256:
        raise ValueError("Creative PNG hash mismatch")
    with Image.open(target) as image:
        if image.format != "PNG" or image.size != (width, height) or getattr(image, "n_frames", 1) != 1:
            raise ValueError("Creative PNG format/dimensions mismatch")
        image.verify()
    with Image.open(target) as image:
        image.load()
        return {"media_type": "image/png", "width": width, "height": height,
                "sha256": actual_sha, "size_bytes": target.stat().st_size,
                "decoder": "Pillow", "decoded": True}

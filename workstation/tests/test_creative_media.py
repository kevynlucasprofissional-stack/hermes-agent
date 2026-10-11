import hashlib

from PIL import Image
import pytest

from workstation.creative_media import inspect_creative_png


def test_png_readback_decodes_bytes_and_rejects_dimension_or_hash_mismatch(tmp_path):
    target = tmp_path / "frame.png"
    Image.new("RGB", (32, 64), "red").save(target)
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    result = inspect_creative_png(target, width=32, height=64, sha256=digest)
    assert result["decoded"] is True and result["width"] == 32
    assert "VERIFIED" not in result.values()
    with pytest.raises(ValueError):
        inspect_creative_png(target, width=64, height=32, sha256=digest)
    with pytest.raises(ValueError):
        inspect_creative_png(target, width=32, height=64, sha256="0" * 64)


def test_successful_file_write_or_matching_hash_is_not_png_proof(tmp_path):
    target = tmp_path / "frame.png"
    target.write_bytes(b"not a PNG even though it exists")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    with pytest.raises(OSError):
        inspect_creative_png(target, width=32, height=64, sha256=digest)
    Image.new("RGB", (32, 64), "blue").save(target)
    target.write_bytes(target.read_bytes()[:40])
    truncated = hashlib.sha256(target.read_bytes()).hexdigest()
    with pytest.raises((OSError, SyntaxError)):
        inspect_creative_png(target, width=32, height=64, sha256=truncated)

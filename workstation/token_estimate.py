"""Provider-neutral token estimation for browser tool traffic.

Port of ``browseros-mcp/src/token_estimate.rs`` (BrowserOS Neo) to Python.
Version 1 counts UTF-8 text with a bytes-per-token heuristic and images with
bounded 32×32 patches. Protocol envelopes, metadata and opaque binary data are
deliberately excluded.

Usage::

    from workstation.token_estimate import (
        estimate_text_tokens,
        estimate_tool_input_tokens,
        estimate_tool_output_tokens,
        estimate_json_output_tokens,
        estimate_image_tokens_from_dimensions,
        slice_text_by_estimated_tokens,
        TOKEN_ESTIMATOR_VERSION,
    )
"""

from __future__ import annotations

import base64
import binascii
import json
import math
import struct
from typing import Any, Dict, Iterable, List, Optional, Union

# ---------------------------------------------------------------------------
# Constants (kept in sync with token_estimate.rs v1)
# ---------------------------------------------------------------------------

APPROX_CHARS_PER_TOKEN: int = 3
IMAGE_PATCH_EDGE_PX: int = 32
MAX_IMAGE_PATCHES: int = 1536
TOKEN_ESTIMATOR_VERSION: int = 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def estimate_text_tokens(text: str) -> int:
    """Estimate tokens for UTF-8 text using ceil(bytes / 3)."""
    if not text:
        return 0
    return math.ceil(len(text.encode("utf-8")) / APPROX_CHARS_PER_TOKEN)


def estimate_tool_input_tokens(tool_name: str, arguments: Any) -> int:
    """Estimate input tokens: tool name + compact JSON arguments."""
    name_tokens = _bounded_tokens(estimate_text_tokens(tool_name))
    try:
        compact = json.dumps(arguments, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError):
        compact = ""
    arg_tokens = _bounded_tokens(estimate_text_tokens(compact))
    return name_tokens + arg_tokens


def estimate_tool_output_tokens(content: list[dict[str, Any]]) -> int:
    """Estimate output tokens from a list of content blocks.

    Each block should be a dict with at least ``{"type": "text", "text": "..."}``
    or ``{"type": "image", "data": "<base64>", "mime_type": "image/png"}``.
    Unknown types contribute zero.
    """
    return _saturating_sum(_estimate_content_block_tokens(b) for b in content)


def estimate_json_output_tokens(value: Any) -> int:
    """Estimate tokens for a JSON-serializable result value."""
    try:
        compact = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError):
        return 0
    return _bounded_tokens(estimate_text_tokens(compact))


def estimate_image_tokens_from_dimensions(width_px: int, height_px: int) -> int:
    """Estimate image tokens from pixel dimensions using bounded patch model."""
    if width_px <= 0 or height_px <= 0:
        return 0
    w_patches = math.ceil(width_px / IMAGE_PATCH_EDGE_PX)
    h_patches = math.ceil(height_px / IMAGE_PATCH_EDGE_PX)
    patches = min(w_patches * h_patches, MAX_IMAGE_PATCHES)
    return _bounded_tokens(patches)


def slice_text_by_estimated_tokens(text: str, max_tokens: int) -> str:
    """Return the longest prefix of *text* that fits within *max_tokens*.

    Mirrors the Rust implementation's approach: compute the byte budget
    directly (``max_tokens * APPROX_CHARS_PER_TOKEN``) then floor to a valid
    UTF-8 character boundary. This avoids a binary search that could stall on
    multi-byte characters (Rust issue #2707).
    """
    if max_tokens <= 0:
        return ""
    if estimate_text_tokens(text) <= max_tokens:
        return text
    max_bytes = min(max_tokens * APPROX_CHARS_PER_TOKEN, len(text.encode("utf-8")))
    encoded = text.encode("utf-8")[:max_bytes]
    # Decode with error handling to land on a valid char boundary
    return encoded.decode("utf-8", errors="ignore")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _bounded_tokens(tokens: int) -> int:
    """Clamp to i64 range (mirrors Rust bounded_tokens)."""
    if tokens < 0:
        return 0
    # Python ints are arbitrary precision; cap at a sane ceiling
    return min(tokens, 2**63 - 1)


def _saturating_sum(values: Iterable[int]) -> int:
    cap = 2**63 - 1
    total = 0
    for v in values:
        total += v
        if total >= cap:
            return cap
    return total


def _estimate_content_block_tokens(block: dict[str, Any]) -> int:
    btype = block.get("type", "")
    if btype == "text":
        text = block.get("text", "")
        return _bounded_tokens(estimate_text_tokens(str(text)))
    if btype == "image":
        data = block.get("data", "")
        return _estimate_image_tokens_b64(str(data))
    if btype == "resource":
        resource = block.get("resource", {})
        if isinstance(resource, dict) and "text" in resource:
            return _bounded_tokens(estimate_text_tokens(str(resource["text"])))
        return 0
    # audio, resource_link, unknown → 0
    return 0


def _estimate_image_tokens_b64(encoded: str) -> int:
    """Decode base64 image, extract dimensions from PNG/JPEG/GIF/BMP header."""
    if not encoded:
        return 0
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return 0
    dims = _extract_image_dimensions(raw)
    if dims is None:
        return 0
    return estimate_image_tokens_from_dimensions(dims[0], dims[1])


def _extract_image_dimensions(data: bytes) -> Optional[tuple]:
    """Extract (width, height) from common image format headers."""
    if len(data) < 24:
        return None
    # PNG: 8-byte signature + IHDR chunk
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w = struct.unpack(">I", data[16:20])[0]
        h = struct.unpack(">I", data[20:24])[0]
        return (w, h)
    # JPEG: FF D8 FF
    if data[:3] == b"\xff\xd8\xff":
        return _jpeg_dimensions(data)
    # GIF: GIF87a or GIF89a
    if data[:6] in (b"GIF87a", b"GIF89a"):
        w = struct.unpack("<H", data[6:8])[0]
        h = struct.unpack("<H", data[8:10])[0]
        return (w, h)
    # BMP: BM + header
    if data[:2] == b"BM" and len(data) >= 26:
        w = struct.unpack("<I", data[18:22])[0]
        h = abs(struct.unpack("<i", data[22:26])[0])
        return (w, h)
    return None


def _jpeg_dimensions(data: bytes) -> Optional[tuple]:
    """Parse JPEG SOF marker for dimensions."""
    i = 2
    length = len(data)
    while i < length - 8:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        # SOF markers: C0-C3, C5-C7, C9-CB, CD-CF
        if marker in (0xC0, 0xC1, 0xC2, 0xC3,
                       0xC5, 0xC6, 0xC7,
                       0xC9, 0xCA, 0xCB,
                       0xCD, 0xCE, 0xCF):
            if i + 9 > length:
                return None
            h = struct.unpack(">H", data[i + 5:i + 7])[0]
            w = struct.unpack(">H", data[i + 7:i + 9])[0]
            return (w, h)
        # Skip non-SOF segments
        if i + 3 >= length:
            return None
        seg_len = struct.unpack(">H", data[i + 2:i + 4])[0]
        i += 2 + seg_len
    return None


# ---------------------------------------------------------------------------
# Self-test (run with: python -m workstation.token_estimate)
# ---------------------------------------------------------------------------

def _self_test() -> None:
    """Run tests mirroring the Rust test suite."""
    failures = []

    def check(name: str, actual: Any, expected: Any) -> None:
        if actual != expected:
            failures.append(f"FAIL {name}: got {actual}, expected {expected}")

    # text_uses_utf8_bytes_rounded_up
    check("empty_text", estimate_text_tokens(""), 0)
    check("abc", estimate_text_tokens("abc"), 1)
    check("abcd", estimate_text_tokens("abcd"), 2)
    check("éé", estimate_text_tokens("éé"), 2)  # 4 bytes / 3 = ceil(1.33) = 2

    # tool_input_counts_name_and_compact_arguments
    args = {"b": [1, True], "a": "é"}
    compact = '{"a":"é","b":[1,true]}'
    expected = estimate_text_tokens("browser") + estimate_text_tokens(compact)
    check("tool_input", estimate_tool_input_tokens("browser", args), expected)

    # output_sums_text_blocks
    content = [
        {"type": "text", "text": "abc"},
        {"type": "text", "text": "abcdef"},
    ]
    check("output_sum", estimate_tool_output_tokens(content),
          estimate_text_tokens("abc") + estimate_text_tokens("abcdef"))

    # image_patch_count_is_capped
    check("patch_cap", estimate_image_tokens_from_dimensions(2048, 2048), 1536)

    # standard_screenshot
    check("screenshot", estimate_image_tokens_from_dimensions(1920, 1080), 1536)

    # small image
    check("small_image", estimate_image_tokens_from_dimensions(33, 65), 6)

    # zero dimensions
    check("zero_dims", estimate_image_tokens_from_dimensions(0, 0), 0)

    # slicing tests
    check("slice_zero", slice_text_by_estimated_tokens("abc", 0), "")
    check("slice_within", slice_text_by_estimated_tokens("hello", 100), "hello")
    check("slice_ascii", slice_text_by_estimated_tokens("abcdefghij", 2), "abcdef")

    # multibyte slicing
    cjk = "汉" * 5001
    sliced = slice_text_by_estimated_tokens(cjk, 5000)
    check("slice_cjk_len", len(sliced), 5000)
    check("slice_cjk_tokens", estimate_text_tokens(sliced), 5000)

    # two-byte char slicing
    accented = "é" * 3001
    sliced_acc = slice_text_by_estimated_tokens(accented, 2000)
    check("slice_accented_max", estimate_text_tokens(sliced_acc) <= 2000, True)

    # json_output
    check("json_string", estimate_json_output_tokens("abcdef"),
          estimate_text_tokens('"abcdef"'))
    check("json_null", estimate_json_output_tokens(None),
          estimate_text_tokens("null"))

    # saturating sum
    check("saturate", _saturating_sum([2**63 - 1, 1]), 2**63 - 1)

    if failures:
        for f in failures:
            print(f)
        raise SystemExit(1)
    else:
        print(f"All {17} tests passed. TOKEN_ESTIMATOR_VERSION={TOKEN_ESTIMATOR_VERSION}")


if __name__ == "__main__":
    _self_test()
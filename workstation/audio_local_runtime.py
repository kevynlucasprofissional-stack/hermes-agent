"""P05 bounded, local-only adapter over the existing Hermes transcribe_audio tool.

No new STT provider, model download, LLM invocation or network fallbacks. The
caller must supply an already-cached, complete faster-whisper snapshot.
"""
from __future__ import annotations

import hashlib
import os
import wave
from pathlib import Path
from typing import Any, Callable

MAX_AUDIO_BYTES = 25 * 1024 * 1024
_CACHE_FILES = ("model.bin", "config.json", "tokenizer.json")


def _model_snapshot(candidate: Path) -> Path:
    path = Path(candidate)
    if path.is_symlink() or not path.is_dir():
        raise ValueError("model_not_cached")
    resolved = path.resolve(strict=True)
    if not all((resolved / part).is_file() and (resolved / part).stat().st_size > 0
               for part in _CACHE_FILES):
        raise ValueError("model_not_cached")
    return resolved


def resolve_cached_whisper_model(hub_dir: Path, preset: str = "base") -> Path:
    """Resolve an installed Systran faster-whisper model without contacting HF Hub."""
    if preset not in {"tiny", "base", "small"}:
        raise ValueError("unsupported local model preset")
    cache = Path(hub_dir) / ("models--Systran--faster-whisper-" + preset) / "snapshots"
    if not cache.is_dir():
        raise ValueError("model_not_cached")
    for candidate in sorted(cache.iterdir(), key=lambda x: x.name):
        try:
            return _model_snapshot(candidate)
        except (ValueError, OSError):
            continue
    raise ValueError("model_not_cached")


def _valid_input(source: Path, max_bytes: int) -> tuple[Path, str, float]:
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_AUDIO_BYTES:
        raise ValueError("invalid_audio_limit")
    if source.is_symlink():
        raise ValueError("audio_symlink_denied")
    if source.exists() and not source.is_file():
        raise ValueError("invalid_audio")
    if not source.is_file():
        raise ValueError("audio_not_found")
    if source.suffix.lower() != ".wav":
        raise ValueError("invalid_audio_extension")
    size = source.stat().st_size
    if size > max_bytes:
        raise ValueError("audio_too_large")
    if size < 44:
        raise ValueError("invalid_audio")
    try:
        with wave.open(str(source), "rb") as reader:
            if reader.getnchannels() != 1 or reader.getsampwidth() != 2:
                raise ValueError("invalid_audio")
            if not 8000 <= reader.getframerate() <= 48000:
                raise ValueError("invalid_audio")
            duration = reader.getnframes() / reader.getframerate()
            if duration <= 0 or duration > 300:
                raise ValueError("invalid_audio")
    except (wave.Error, EOFError, OSError) as exc:
        raise ValueError("invalid_audio") from exc
    return source.resolve(strict=True), hashlib.sha256(source.read_bytes()).hexdigest(), duration


def transcribe_cached_local(
    input_path: Path, *, model_snapshot: Path,
    config: dict[str, Any] | None = None, max_bytes: int = MAX_AUDIO_BYTES,
    transcriber: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Path -> existing Hermes transcribe_audio -> factual text/hint/provenance.

    Reject cloud, command, disabled, oversized, non-PCM, missing-model inputs
    before the tool is invoked; may only use locally cached snapshot files.
    This adapter does NOT infer acoustic language from transcript or call LLM.
    """
    if config is None:
        from tools.transcription_tools import _load_stt_config
        config = _load_stt_config()
    if not isinstance(config, dict):
        raise PermissionError("local STT config required")
    if config.get("enabled") is False or config.get("provider", "local") != "local":
        raise PermissionError("local-only STT provider required")
    if config.get("pre_transcription") or config.get("hooks"):
        raise PermissionError("local-only transcription hooks not permitted")
    path, content_hash, duration = _valid_input(Path(input_path), max_bytes)
    model_path = _model_snapshot(Path(model_snapshot))
    if transcriber is None:
        # Never let caller-supplied config opt an actually remote Hermes profile
        # into STT. The real transcribe_audio resolves the active profile again.
        from tools.transcription_tools import _load_stt_config, _get_provider
        active = _load_stt_config()
        if (not isinstance(active, dict) or active.get("enabled") is False
                or _get_provider(active) != "local"
                or active.get("pre_transcription") or active.get("hooks")):
            raise PermissionError("active profile is not local-only STT")
        # Report language from the effective profile, not a caller-supplied hint.
        config = active
        import importlib.util
        if importlib.util.find_spec("faster_whisper") is None:
            raise RuntimeError("local_asr_dependency_missing")
        from tools.transcription_tools import transcribe_audio
        transcriber = transcribe_audio
    result = transcriber(str(path), model=str(model_path),
                         source="workstation_audio_qualification")
    if not isinstance(result, dict) or result.get("success") is not True or result.get("provider") != "local":
        raise RuntimeError("local_asr_failed")
    transcript = result.get("transcript")
    if not isinstance(transcript, str) or not transcript.strip():
        raise RuntimeError("local_asr_failed_empty")
    hint = config.get("language") or (config.get("local") or {}).get("language")
    language = hint if hint in ("pt", "pt-BR", "pt_BR") else None
    if language in ("pt", "pt_BR"):
        language = "pt-BR"
    return {
        "text": transcript.strip(),
        "language": language,
        "provenance": {
            "provider": "local",
            "engine": "faster-whisper",
            "model_source": "cached_snapshot",
            "model_preset": "cached",
            "language_basis": "configured_hint" if language else "not_provided",
            "input_sha256": content_hash,
            "duration_seconds": round(duration, 3),
            "network_calls": "not_permitted",
            "llm_calls": 0,
        },
    }

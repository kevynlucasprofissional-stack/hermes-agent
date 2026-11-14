"""P05 RED tests: hard local-only admission before delegating to existing STT tool."""
import os
from pathlib import Path
import wave
import pytest

from workstation.audio_local_runtime import resolve_cached_whisper_model, transcribe_cached_local


def model_dir(tmp_path):
    folder=tmp_path/"models"/"snapshot"
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("model.bin","config.json","tokenizer.json"):
        (folder/name).write_bytes(b"fake-test-asset")
    return folder


def wav_file(tmp_path, seconds=0.5):
    file=tmp_path/"fixture.wav"
    with wave.open(str(file),"wb") as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
        w.writeframes(b"\x00\x00"*int(16000*seconds))
    return file


def test_missing_audio_blocks_backend(tmp_path):
    calls=[]
    with pytest.raises(ValueError, match="not_found"):
        transcribe_cached_local(tmp_path/"missing.wav",model_snapshot=model_dir(tmp_path),
                                config={"enabled":True,"provider":"local"},transcriber=lambda *a,**kw:calls.append(a))
    assert not calls


def test_giant_file_is_rejected_before_model_load(tmp_path):
    file=tmp_path/"oversized.wav"
    with file.open("wb") as handle:
        handle.truncate(30*1024*1024)
    with pytest.raises(ValueError,match="too_large"):
        transcribe_cached_local(file,model_snapshot=model_dir(tmp_path),max_bytes=1024,
                                config={"enabled":True,"provider":"local"},transcriber=lambda *args:None)


def test_invalid_wave_or_unsupported_extension_rejected(tmp_path):
    file=tmp_path/"broken.wav"
    file.write_bytes(b"not a WAV")
    with pytest.raises(ValueError,match="invalid_audio"):
        transcribe_cached_local(file,model_snapshot=model_dir(tmp_path),
                                config={"enabled":True,"provider":"local"},transcriber=lambda *a,**kw:None)
    with pytest.raises(ValueError,match="invalid_audio"):
        transcribe_cached_local(tmp_path,model_snapshot=model_dir(tmp_path),
                                config={"enabled":True,"provider":"local"},transcriber=lambda *a,**kw:None)


def test_disabled_and_cloud_providers_never_dispatch(tmp_path):
    calls=[]
    for cfg in ({"enabled":False,"provider":"local"},{"enabled":True,"provider":"openai"},
                {"enabled":True,"provider":"local_command"}):
        with pytest.raises(PermissionError,match="local"):
            transcribe_cached_local(wav_file(tmp_path),model_snapshot=model_dir(tmp_path),config=cfg,
                                    transcriber=lambda *a,**kw:calls.append(a))
    assert calls==[]


def test_uncached_model_does_not_download(tmp_path):
    calls=[]
    with pytest.raises(ValueError,match="model_not_cached"):
        transcribe_cached_local(wav_file(tmp_path),model_snapshot=tmp_path/"missing-snapshot",
                                config={"enabled":True,"provider":"local"},
                                transcriber=lambda *a,**kw:calls.append(a))
    assert not calls


def test_local_pt_br_provider_returns_explicit_provenance_without_llm(tmp_path):
    file=wav_file(tmp_path)
    model=model_dir(tmp_path)
    calls=[]
    def existing_transcribe(path, model, source):
        calls.append((path,model,source))
        return {"success":True,"transcript":"Bom dia. Este é um teste.", "provider":"local"}
    result=transcribe_cached_local(file,model_snapshot=model,
                                  config={"enabled":True,"provider":"local","language":"pt-BR"},
                                  transcriber=existing_transcribe)
    assert result["text"]=="Bom dia. Este é um teste."
    assert result["language"]=="pt-BR"
    assert result["provenance"]["provider"]=="local"
    assert result["provenance"]["language_basis"]=="configured_hint"
    assert result["provenance"]["model_source"]=="cached_snapshot"
    assert len(result["provenance"]["input_sha256"])==64
    assert calls==[(str(file.resolve()),str(model.resolve()),"workstation_audio_qualification")]


def test_no_transcription_claimed_for_provider_failure(tmp_path):
    with pytest.raises(RuntimeError,match="local_asr_failed"):
        transcribe_cached_local(wav_file(tmp_path),model_snapshot=model_dir(tmp_path),
                                config={"enabled":True,"provider":"local"},
                                transcriber=lambda *a,**kw:{"success":False,"error":"decoder failed"})


def test_language_hint_does_not_pretend_model_detected_language(tmp_path):
    result=transcribe_cached_local(wav_file(tmp_path),model_snapshot=model_dir(tmp_path),
              config={"enabled":True,"provider":"local"},
              transcriber=lambda *a,**kw:{"success":True,"transcript":"olá","provider":"local"})
    assert result["language"] is None
    assert result["provenance"]["language_basis"]=="not_provided"


def test_cache_resolution_never_downloads(tmp_path):
    hub=tmp_path/"hub"
    cache=hub/"models--Systran--faster-whisper-base"/"snapshots"/"abc123"
    cache.mkdir(parents=True)
    for name in ("model.bin","config.json","tokenizer.json"):
        (cache/name).write_bytes(b"x")
    assert resolve_cached_whisper_model(hub,"base")==cache.resolve()
    with pytest.raises(ValueError,match="model_not_cached"):
        resolve_cached_whisper_model(hub,"small")


def test_symlink_input_rejected(tmp_path):
    x=wav_file(tmp_path)
    link=tmp_path/"link.wav"
    try:link.symlink_to(x)
    except OSError:pytest.skip("requires Windows symlink privilege")
    with pytest.raises(ValueError,match="symlink"):
        transcribe_cached_local(link,model_snapshot=model_dir(tmp_path),
                                config={"enabled":True,"provider":"local"},transcriber=lambda *a,**kw:None)


def test_missing_whisper_dependency_fails_before_backend(monkeypatch,tmp_path):
    import importlib.util
    import tools.transcription_tools as stt
    monkeypatch.setattr(stt,"_load_stt_config",lambda:{"enabled":True,"provider":"local"})
    monkeypatch.setattr(stt,"_get_provider",lambda _:"local")
    original = importlib.util.find_spec
    monkeypatch.setattr(importlib.util,"find_spec",
                        lambda name: None if name == "faster_whisper" else original(name))
    with pytest.raises(RuntimeError,match="dependency_missing"):
        transcribe_cached_local(wav_file(tmp_path),model_snapshot=model_dir(tmp_path),
                                config={"enabled":True,"provider":"local"},transcriber=None)


def test_cloud_provider_result_cannot_impersonate_local_transcription(tmp_path):
    with pytest.raises(RuntimeError,match="local_asr_failed"):
        transcribe_cached_local(wav_file(tmp_path),model_snapshot=model_dir(tmp_path),
                                config={"enabled":True,"provider":"local"},
                                transcriber=lambda *a,**kw:{
                                    "success":True,"transcript":"unsafe","provider":"openai"})


def test_real_cron_model_precedence_job_then_cron_then_agent(monkeypatch,tmp_path):
    import cron.scheduler as scheduler
    home = tmp_path / "cron_profile"
    home.mkdir()
    config = home / "config.yaml"
    monkeypatch.setattr(scheduler,"_get_hermes_home",lambda:home)
    monkeypatch.setattr(scheduler,"cron_env_setting",lambda _: "")
    config.write_text(
       "model:\n  default: agent-model\ncron:\n  model: cron-model\n  model_provider: scoped-provider\n",
       encoding="utf-8",
    )
    pinned = scheduler._load_cron_job_config(
        {"id":"p05p","name":"p05 pinned","model":"job-model","provider":"job-provider"},
        "p05p","p05 pinned")
    assert pinned.model == "job-model"
    assert pinned.cron_default_provider == "scoped-provider"
    inherited = scheduler._load_cron_job_config(
        {"id":"p05c","name":"p05 inherited"},"p05c","p05 inherited")
    assert inherited.model == "cron-model"
    assert inherited.cron_default_provider == "scoped-provider"
    config.write_text("model:\n  default: agent-model\ncron:\n  model_provider: scoped-provider\n",encoding="utf-8")
    agent_fallback=scheduler._load_cron_job_config(
        {"id":"p05a","name":"p05 fallback"},"p05a","p05 fallback")
    assert agent_fallback.model == "agent-model"
    assert agent_fallback.cron_default_provider == "scoped-provider"


def test_active_profile_cannot_be_overridden_to_cloud_by_caller_config(tmp_path,monkeypatch):
    import tools.transcription_tools as stt
    monkeypatch.setattr(stt,"_load_stt_config",lambda:{"enabled":True,"provider":"openai"})
    monkeypatch.setattr(stt,"_get_provider",lambda _: "openai")
    with pytest.raises(PermissionError, match="active profile"):
        transcribe_cached_local(
            wav_file(tmp_path), model_snapshot=model_dir(tmp_path),
            config={"enabled":True,"provider":"local"},
        )

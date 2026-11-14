"""P05 native offline smoke: isolated Hermes profile, real SAPI pt-BR WAV + Whisper base.

Execute with the existing Hermes 3.11 venv; no pytest, no downloads, no
external TTS and no persisted voice recordings. Prints metrics only.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path


def run() -> int:
    project = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project))
    import importlib.util
    # Native lab loads the standalone adapter file without bootstrapping the
    # unrelated mandatory Workstation supervisor in this incomplete venv.
    module_path = project / 'workstation' / 'audio_local_runtime.py'
    spec = importlib.util.spec_from_file_location('p05_native_audio_adapter', module_path)
    assert spec and spec.loader
    native_audio = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(native_audio)
    resolve_cached_whisper_model = native_audio.resolve_cached_whisper_model
    cache = Path.home() / ".cache" / "huggingface" / "hub"
    model = resolve_cached_whisper_model(cache, "base")
    if platform.system() != "Windows":
        raise RuntimeError("native SAPI fixture requires Windows")
    ps_script = project / "workstation" / "tests" / "fixtures" / "sapi_ptbr_fixture.ps1"
    import psutil
    process = psutil.Process()
    stats: dict[str, object] = {
        "python": sys.version.split()[0],
        "architecture": platform.machine(),
        "provider_stt": "faster-whisper",
        "provider_tts": "Hermes command provider / Microsoft SAPI pt-BR",
        "audio_text_fixture_only": True,
        "model": "cached Systran/faster-whisper-base",
        "compute_device": "cpu",
        "compute_type": "int8",
        "llm_calls": 0,
        "network_allowed": False,
    }

    with tempfile.TemporaryDirectory(prefix="hermes-p05-offline-") as temporary:
        root = Path(temporary)
        home = root / "hermes-profile"
        home.mkdir()
        # Existing TTS command provider runs a literal, reviewed local PS script.
        static_ps = str(ps_script).replace("\\", "/")
        home.joinpath("config.yaml").write_text(
            "stt:\n  enabled: true\n  provider: local\n  language: pt-BR\n"
            "  local:\n    device: cpu\n    compute_type: int8\n    model: base\n"
            "tts:\n  provider: sapi-p05-local\n  providers:\n"
            "    sapi-p05-local:\n      type: command\n      format: wav\n"
            "      voice_compatible: false\n"
            f"      command: 'powershell.exe -NoProfile -NonInteractive -File \"{static_ps}\" -OutputPath {{output_path}} -TextFile {{input_path}}'\n",
            encoding="utf-8",
        )
        os.environ["HERMES_HOME"] = str(home)
        # Import ONLY after scoping the throwaway config.
        import importlib.metadata
        stats["faster_whisper_version"] = importlib.metadata.version("faster-whisper")
        stats["ctranslate2_version"] = importlib.metadata.version("ctranslate2")
        from tools.tts_tool import text_to_speech_tool
        transcribe_cached_local = native_audio.transcribe_cached_local

        phrase = "Bom dia, este é um teste de voz em português brasileiro."
        wav = root / "sapi-ptbr.wav"
        original_connect = socket.socket.connect
        original_create = socket.create_connection
        outbound_attempts: list[str] = []

        def no_connect(*args, **kwargs):
            outbound_attempts.append("blocked")
            raise RuntimeError("P05_NO_OUTBOUND_NETWORK")

        socket.socket.connect = no_connect
        socket.create_connection = no_connect
        try:
            start = time.perf_counter()
            reply = json.loads(text_to_speech_tool(phrase, output_path=str(wav)))
            stats["tts_seconds"] = round(time.perf_counter()-start,3)
            if reply.get("success") is not True:
                raise RuntimeError("TTS_NOT_QUALIFIED: "+str(reply.get("error", "unknown"))[:300])
            output = Path(reply["file_path"])
            if output != wav or not output.is_file() or output.stat().st_size < 1000:
                raise RuntimeError("TTS_WRONG_FILE_OR_EMPTY")
            with wave.open(str(wav),"rb") as reader:
                stats["wav_duration_seconds"] = round(reader.getnframes()/reader.getframerate(),3)
                stats["wav_hz"] = reader.getframerate()
                stats["wav_channels"] = reader.getnchannels()
                stats["wav_bits"] = reader.getsampwidth()*8
            probe = subprocess.run(
                ["ffprobe","-v","error","-show_entries","format=duration,format_name:"
                 "stream=codec_name,sample_rate,channels","-of","json",str(wav)],
                capture_output=True,text=True,timeout=10,check=True,
            )
            data=json.loads(probe.stdout)
            stats["ffprobe_format"] = data.get("format",{}).get("format_name")
            stats["ffprobe_codec"] = (data.get("streams") or [{}])[0].get("codec_name")
            start=time.perf_counter()
            result = transcribe_cached_local(
                wav,model_snapshot=model,
                config={"enabled":True,"provider":"local","language":"pt-BR"},
            )
            stats["asr_seconds"] = round(time.perf_counter()-start,3)
            stats["transcribed_text"] = result["text"]
            stats["language"] = result["language"]
            stats["language_basis"] = result["provenance"]["language_basis"]
            stats["file_sha256"] = result["provenance"]["input_sha256"]
            stats["rss_parent_megabytes"] = round(process.memory_info().rss/(1024**2),1)
            import unicodedata, re
            def tokens(text: str) -> list[str]:
                clean = unicodedata.normalize("NFKD",text.lower())
                clean = "".join(c for c in clean if not unicodedata.combining(c))
                return re.findall(r"[a-z]+",clean)
            a,b = tokens(phrase),tokens(result["text"])
            # Levenshtein WER; a single clip is only a smoke signal.
            dp=list(range(len(b)+1))
            for i,item in enumerate(a,1):
                nxt=[i]+[0]*len(b)
                for j,word in enumerate(b,1):
                    nxt[j]=min(nxt[j-1]+1,dp[j]+1,dp[j-1]+(item!=word))
                dp=nxt
            stats["word_error_rate"] = round(dp[-1]/len(a),3)
            stats["outbound_attempts"] = len(outbound_attempts)
            if outbound_attempts:
                raise RuntimeError("Unexpected outbound network attempt (blocked)")
            if not result["text"].strip():
                raise RuntimeError("ASR_EMPTY")
            print("P05_NATIVE_OFFLINE_PASS "+json.dumps(stats,ensure_ascii=False,sort_keys=True))
        finally:
            socket.socket.connect = original_connect
            socket.create_connection = original_create
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run())
    except Exception as exc:
        print("P05_NATIVE_OFFLINE_FAIL "+type(exc).__name__+" "+str(exc)[:350],file=sys.stderr)
        raise SystemExit(1)

"""Fixed media-engine probes and commands using the canonical process owner."""
from __future__ import annotations

from dataclasses import dataclass
import re
import time

from hermes_constants import reset_hermes_home_override, set_hermes_home_override

from workstation.config import WorkstationConfig
from workstation.creative_apps import CreativeAppManifest
from workstation.creative_process import (
    CreativeExecutionScope, CreativeInvocation, start_creative_process,
)
from workstation.creative_project_runtime import CreativeRunContext


@dataclass(frozen=True)
class CreativeVideoEngines:
    ffmpeg: CreativeAppManifest
    ffprobe: CreativeAppManifest

    def validate(self) -> None:
        for engine, manifest in (("ffmpeg", self.ffmpeg), ("ffprobe", self.ffprobe)):
            manifest.validate()
            if manifest.engine != engine:
                raise ValueError("Creative video engine identity mismatch")

    @classmethod
    def from_config(cls, config: WorkstationConfig) -> CreativeVideoEngines:
        engines = config.raw.get("creative", {}).get("engines", {})
        try:
            result = cls(CreativeAppManifest(**engines["ffmpeg"]), CreativeAppManifest(**engines["ffprobe"]))
        except (KeyError, TypeError) as error:
            raise ValueError("Creative video requires explicit pinned engine manifests") from error
        result.validate()
        return result


def run_media_command(config: WorkstationConfig, context: CreativeRunContext,
                      manifest: CreativeAppManifest, arguments: tuple[str, ...], *,
                      timeout: int = 30, registry=None) -> dict:
    """Internal adapter primitive; model/CLI inputs never supply these arguments."""
    manifest.validate()
    if manifest.engine not in {"ffmpeg", "ffprobe"}:
        raise ValueError("Not a Creative media engine")
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise ValueError("Creative media timeout exceeds budget")
    workspace = context.validate(config)
    scope = CreativeExecutionScope(context.profile_home, context.session_key, context.task_id, str(workspace))
    if registry is None:
        from tools.process_registry import process_registry
        registry = process_registry
    child = start_creative_process(config, scope, CreativeInvocation(
        manifest.engine, (manifest.executable, *arguments), manifest.executable_sha256), registry=registry)
    deadline = time.monotonic() + timeout
    try:
        while True:
            context.validate(config)
            result = registry.wait(child.id, timeout=1)
            if result.get("status") != "timeout":
                break
            if time.monotonic() >= deadline:
                raise TimeoutError("Creative media engine exceeded duration budget")
        context.validate(config)
    except BaseException:
        # Cleanup stays with the original process/profile owner even if the
        # caller's active profile changed while waiting. No new process is started.
        token = set_hermes_home_override(context.profile_home)
        try:
            registry.kill_process(child.id, source="creative.video.authority_lost")
        finally:
            reset_hermes_home_override(token)
        raise
    if result.get("status") != "exited" or result.get("exit_code") != 0:
        if result.get("status") == "interrupted":
            registry.kill_process(child.id, source="creative.video.interrupted")
        raise RuntimeError("Creative media engine did not exit successfully")
    log = registry.read_log(child.id, offset=0, limit=4096)
    if log.get("total_lines", 0) > 4096 or len(log.get("output", "")) > 200_000:
        raise ValueError("Creative media engine output exceeds inspection budget")
    return {"process_id": child.id, "exit_code": 0, "output": log.get("output", ""),
            "engine": manifest.engine, "executable_sha256": manifest.executable_sha256}


def inspect_video_engines(config: WorkstationConfig, context: CreativeRunContext,
                          engines: CreativeVideoEngines, *, registry=None) -> dict:
    engines.validate()
    facts = {}
    for manifest in (engines.ffmpeg, engines.ffprobe):
        result = run_media_command(config, context, manifest, ("-version",), timeout=15, registry=registry)
        version = re.search(rf"^{manifest.engine} version (\S+)", result["output"], flags=re.MULTILINE)
        if version is None:
            raise ValueError("Creative media executable failed its version contract")
        facts[manifest.engine] = {"version": version.group(1), "executable_sha256": manifest.executable_sha256,
                                  "provider_ref": manifest.provider_ref, "process_id": result["process_id"],
                                  "version_output": result["output"]}
    configuration = facts["ffmpeg"]["version_output"]
    if "--enable-nonfree" in configuration or "--enable-libx264" not in configuration:
        raise ValueError("Creative H.264 adapter requires an audited non-nonfree libx264 build")
    license_result = run_media_command(config, context, engines.ffmpeg, ("-L",), timeout=15, registry=registry)
    license_text = license_result["output"]
    if "GNU General Public License" not in license_text or "version 3" not in license_text:
        raise ValueError("Selected FFmpeg build does not match the audited GPLv3 contract")
    return {"engines": facts, "ffmpeg_license": "GPL-3.0-or-later", "license_output": license_text,
            "license_process_id": license_result["process_id"],
            "distribution_scope": "externally installed executable; not bundled or redistributed"}

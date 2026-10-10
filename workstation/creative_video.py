"""Bounded still-PNG to H.264/MP4 adapter; existing TaskRun/process/artifact owners."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from uuid import uuid4

from workstation.artifacts import ArtifactStore
from workstation.config import WorkstationConfig
from workstation.contracts import ExecutionEventKind
from workstation.creative_media import inspect_creative_png
from workstation.creative_project_runtime import CreativeEffectUncertain, CreativeRunContext
from workstation.creative_project_store import load_creative_revision
from workstation.creative_video_metadata import inspect_video_preview, inspect_video_probe
from workstation.creative_video_process import CreativeVideoEngines, inspect_video_engines, run_media_command
from workstation.journal import ExecutionJournal
from workstation.policy import ActionScope, PolicyDecision, ScopedPolicyEngine


@dataclass(frozen=True)
class CreativeStillVideoRequest:
    project_id: str
    revision_id: str
    source_png: str
    source_sha256: str
    width: int
    height: int
    duration_seconds: int = 8
    fps: int = 30

    def validate(self, workspace: Path) -> Path:
        if (type(self.duration_seconds) is not int or not 1 <= self.duration_seconds <= 30
                or type(self.fps) is not int or self.fps not in {15, 24, 25, 30, 60}
                or self.duration_seconds * self.fps > 1800):
            raise ValueError("Creative video duration/rate exceeds budget")
        if (type(self.width) is not int or type(self.height) is not int
                or self.width % 2 or self.height % 2):
            raise ValueError("Creative H.264 dimensions must be even integers")
        source = Path(self.source_png)
        if not source.is_absolute() or source.is_symlink() or not source.resolve(strict=True).is_relative_to(workspace):
            raise PermissionError("Creative video input is outside TaskRun workspace")
        inspect_creative_png(source, width=self.width, height=self.height, sha256=self.source_sha256)
        return source.resolve(strict=True)


def encode_still_video(config: WorkstationConfig, context: CreativeRunContext,
                       request: CreativeStillVideoRequest, engines: CreativeVideoEngines, *, registry=None) -> dict:
    workspace = context.validate(config)
    source = request.validate(workspace)
    revision = load_creative_revision(request.project_id, request.revision_id)
    project = revision.manifest_path.parent.parent.parent
    if not project.is_relative_to(workspace):
        raise PermissionError("Creative video project is outside TaskRun workspace")
    operation_id = uuid4().hex
    destination = project / "renders" / operation_id
    policy = ScopedPolicyEngine().evaluate(ActionScope(
        task_id=context.task_id, session_id=context.session_id, capability="filesystem", action_name="write",
        target=str(destination), workspace_root=str(workspace),
    ))
    if policy.decision is not PolicyDecision.ALLOW:
        raise PermissionError("Creative video output denied by filesystem policy")
    engines.validate()
    build = inspect_video_engines(config, context, engines, registry=registry)
    context.validate(config)
    source_data = source.read_bytes()
    if hashlib.sha256(source_data).hexdigest() != request.source_sha256:
        raise ValueError("Creative video source changed before snapshot")
    journal = ExecutionJournal(task_id=context.task_id, session_id=context.session_id)
    journal.record(ExecutionEventKind.ACTION, "Creative video encode prepared", metadata={
        "operation_id": operation_id, "run_id": context.run_id, "project_id": request.project_id,
        "revision_id": request.revision_id, "source_sha256": request.source_sha256,
    })
    if destination.resolve().parent != (project / "renders") or (project / "renders").is_symlink():
        raise PermissionError("Creative video render directory was redirected")
    source_snapshot = destination / "input.png"
    output, preview = destination / "video.mp4", destination / "preview.png"
    frames = request.duration_seconds * request.fps
    try:
        destination.mkdir(parents=True, exist_ok=False)
        with source_snapshot.open("xb") as stream:
            stream.write(source_data)
        encoded = run_media_command(config, context, engines.ffmpeg, (
            "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-max_alloc", "67108864",
            "-protocol_whitelist", "file,pipe", "-threads", "2", "-f", "image2", "-pattern_type", "none",
            "-loop", "1", "-framerate", str(request.fps), "-i", str(source_snapshot),
            "-map", "0:v:0", "-an", "-sn", "-dn", "-c:v", "libx264", "-threads", "2",
            "-filter_threads", "1", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-frames:v", str(frames), "-r", str(request.fps), "-movflags", "+faststart",
            "-fs", "67108864", "-f", "mp4", str(output)), timeout=120, registry=registry)
        if not output.is_file() or output.is_symlink() or not 1 <= output.stat().st_size <= 67_108_864:
            raise ValueError("Creative video output is missing or oversized")
        probe_result = run_media_command(config, context, engines.ffprobe, (
            "-v", "error", "-protocol_whitelist", "file,pipe", "-f", "mov", "-count_frames",
            "-show_entries", "stream=codec_name,codec_type,width,height,pix_fmt,r_frame_rate,avg_frame_rate,duration,nb_frames,nb_read_frames:format=format_name,duration,size",
            "-of", "json", str(output)), timeout=30, registry=registry)
        probe = json.loads(probe_result["output"])
        facts = inspect_video_probe(probe, width=request.width, height=request.height, fps=request.fps,
                                    frames=frames, size_bytes=output.stat().st_size)
        decoded = run_media_command(config, context, engines.ffmpeg, (
            "-hide_banner", "-loglevel", "error", "-nostdin", "-n", "-max_alloc", "67108864",
            "-protocol_whitelist", "file,pipe", "-threads", "2", "-f", "mov", "-i", str(output),
            "-map", "0:v:0", "-frames:v", "1", "-threads", "1", "-f", "image2", "-update", "1",
            str(preview)), timeout=30, registry=registry)
        if preview.stat().st_size > 33_554_432:
            raise ValueError("Creative video preview exceeds size budget")
        visual = inspect_video_preview(source_snapshot, preview)
        load_creative_revision(request.project_id, request.revision_id)
        context.validate(config)
        store = ArtifactStore()
        video_bytes = output.read_bytes()
        video_ref = store.store(context.task_id, f"creative-video-{operation_id}.mp4", video_bytes, media_type="video/mp4")
        preview_ref = store.store(context.task_id, f"creative-video-preview-{operation_id}.png",
                                  preview.read_bytes(), media_type="image/png")
        receipt = {"schema_version": 1, "operation_id": operation_id, "task_id": context.task_id,
                   "run_id": context.run_id, "session_id": context.session_id, "project_id": request.project_id,
                   "revision_id": request.revision_id, "project_source_sha256": revision.source_sha256,
                   "source_png_sha256": request.source_sha256, "video": facts, "decoded_preview": visual,
                   "video_artifact": video_ref.to_dict(), "preview_artifact": preview_ref.to_dict(),
                   "build": build, "process_ids": [encoded["process_id"], probe_result["process_id"], decoded["process_id"]]}
        receipt_ref = store.store(context.task_id, f"creative-video-receipt-{operation_id}.json", receipt,
                                  schema="creative.video.v1", media_type="application/json")
        context.validate(config)
        journal.record(ExecutionEventKind.DELIVERABLE, "Creative MP4 and decoded preview persisted", metadata={
            "operation_id": operation_id, "run_id": context.run_id, "receipt_ref": receipt_ref.ref,
            "receipt_sha256": receipt_ref.sha256, "project_id": request.project_id,
            "revision_id": request.revision_id, "video_sha256": video_ref.sha256,
        })
        return {**receipt, "receipt_artifact": receipt_ref.to_dict()}
    except Exception as error:
        raise CreativeEffectUncertain(operation_id) from error

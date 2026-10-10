"""HyperFrames seekable motion video render adapter with independent ffprobe/artifact verification."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
from pathlib import Path
import shlex
import subprocess
from uuid import uuid4

from hermes_cli._subprocess_compat import windows_hide_flags
from tools.approval import check_all_command_guards
from tools.process_registry import ProcessRegistry, process_registry
from workstation.artifacts import ArtifactStore
from workstation.config import WorkstationConfig
from workstation.contracts import ExecutionEventKind
from workstation.creative_process import _child_env
from workstation.creative_project_runtime import CreativeEffectUncertain, CreativeRunContext
from workstation.creative_project_store import load_creative_revision
from workstation.creative_studio_service import HyperFramesInstallation
from workstation.creative_video_metadata import inspect_video_probe
from workstation.creative_video_process import CreativeVideoEngines, inspect_video_engines, run_media_command
from workstation.journal import ExecutionJournal
from workstation.policy import ActionScope, PolicyDecision, ScopedPolicyEngine

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class HyperFramesRenderRequest:
    project_id: str
    revision_id: str
    output_filename: str = "motion.mp4"
    expected_width: int = 1920
    expected_height: int = 1080
    expected_fps: int = 30
    timeout_seconds: int = 180


def render_hyperframes_video(
    config: WorkstationConfig,
    context: CreativeRunContext,
    installation: HyperFramesInstallation,
    request: HyperFramesRenderRequest,
    engines: CreativeVideoEngines,
    *,
    registry: ProcessRegistry | None = None,
) -> dict:
    """Render a seekable motion MP4 from a HyperFrames project revision.

    Supervised by canonical TaskRun ownership, ProcessRegistry, ArtifactStore,
    and independently verified using ffprobe and decoded preview extraction.
    """
    workspace = context.validate(config)
    revision = load_creative_revision(request.project_id, request.revision_id)
    if revision.engine != "hyperframes":
        raise ValueError(f"HyperFrames render requires engine='hyperframes', got '{revision.engine}'")

    project_dir = revision.manifest_path.parent
    if not project_dir.is_relative_to(workspace):
        raise PermissionError("Creative project directory is outside TaskRun workspace")

    engines.validate()
    build = inspect_video_engines(config, context, engines, registry=registry)
    context.validate(config)

    operation_id = uuid4().hex
    destination_dir = project_dir.parent.parent / "renders" / operation_id
    policy = ScopedPolicyEngine().evaluate(ActionScope(
        task_id=context.task_id,
        session_id=context.session_id,
        capability="filesystem",
        action_name="write",
        target=str(destination_dir),
        workspace_root=str(workspace),
    ))
    if policy.decision is not PolicyDecision.ALLOW:
        raise PermissionError("Creative render output denied by filesystem policy")

    output_path = destination_dir / request.output_filename
    preview_path = destination_dir / "preview.png"

    journal = ExecutionJournal(task_id=context.task_id, session_id=context.session_id)
    journal.record(
        ExecutionEventKind.ACTION,
        "HyperFrames motion render prepared",
        metadata={
            "operation_id": operation_id,
            "run_id": context.run_id,
            "project_id": request.project_id,
            "revision_id": request.revision_id,
        },
    )

    try:
        destination_dir.mkdir(parents=True, exist_ok=True)
        argv = (
            str(installation.node_executable),
            str(installation.cli_entrypoint),
            "render",
            "-o",
            str(output_path),
        )
        command = shlex.join(argv)
        approval = check_all_command_guards(command, "local", has_host_access=True)
        if not approval.get("approved", False):
            raise PermissionError("HyperFrames render execution denied by command guards")

        env = _child_env(workspace)
        env.update({
            "HYPERFRAMES_SKIP_SKILLS": "1",
            "HYPERFRAMES_TELEMETRY": "0",
        })

        if registry is None:
            registry = process_registry

        proc = subprocess.Popen(
            list(argv),
            cwd=str(project_dir),
            env=env,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            start_new_session=True,
            creationflags=windows_hide_flags(),
        )

        session = registry.adopt_local(
            proc,
            command=command,
            cwd=str(project_dir),
            task_id=context.task_id,
            owner_task_id=context.task_id,
            session_key=context.session_key,
            notify_on_complete=False,
        )

        wait_res = registry.wait(session.id, timeout=request.timeout_seconds)
        if wait_res.get("status") in {"timeout", "interrupted"}:
            registry.kill_process(session.id, source="creative.render_timeout")
            raise CreativeStudioError(f"HyperFrames render timed out after {request.timeout_seconds}s")
        if wait_res.get("exit_code") != 0:
            raise CreativeStudioError(
                f"HyperFrames render failed with code {wait_res.get('exit_code')}: {wait_res.get('output', '')[:500]}"
            )

        if not output_path.is_file() or output_path.stat().st_size < 100:
            raise ValueError("HyperFrames render output file is missing or empty")

        # Independent ffprobe verification
        probe_result = run_media_command(
            config,
            context,
            engines.ffprobe,
            (
                "-v", "error",
                "-protocol_whitelist", "file,pipe",
                "-f", "mov",
                "-count_frames",
                "-show_entries",
                "stream=codec_name,codec_type,width,height,pix_fmt,r_frame_rate,avg_frame_rate,duration,nb_frames,nb_read_frames:format=format_name,duration,size",
                "-of", "json",
                str(output_path),
            ),
            timeout=30,
            registry=registry,
        )
        probe = json.loads(probe_result["output"])

        # Read stream facts
        video_stream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None)
        if not video_stream:
            raise ValueError("Rendered output contains no video stream")

        width = int(video_stream.get("width") or 0)
        height = int(video_stream.get("height") or 0)
        frames = int(video_stream.get("nb_read_frames") or video_stream.get("nb_frames") or 0)

        facts = inspect_video_probe(
            probe,
            width=width,
            height=height,
            fps=request.expected_fps,
            frames=frames,
            size_bytes=output_path.stat().st_size,
        )

        # Extract decoded preview snapshot frame
        run_media_command(
            config,
            context,
            engines.ffmpeg,
            (
                "-hide_banner", "-loglevel", "error", "-nostdin", "-n",
                "-protocol_whitelist", "file,pipe", "-threads", "2",
                "-f", "mov", "-i", str(output_path),
                "-map", "0:v:0", "-frames:v", "1", "-threads", "1",
                "-f", "image2", "-update", "1",
                str(preview_path),
            ),
            timeout=30,
            registry=registry,
        )

        # Persist deliverables to ArtifactStore
        store = ArtifactStore()
        video_bytes = output_path.read_bytes()
        preview_bytes = preview_path.read_bytes() if preview_path.is_file() else b""

        video_ref = store.store(
            context.task_id,
            f"creative-hyperframes-{operation_id}.mp4",
            video_bytes,
            media_type="video/mp4",
        )
        preview_ref = store.store(
            context.task_id,
            f"creative-hyperframes-preview-{operation_id}.png",
            preview_bytes,
            media_type="image/png",
        )

        receipt = {
            "schema_version": 1,
            "operation_id": operation_id,
            "task_id": context.task_id,
            "run_id": context.run_id,
            "session_id": context.session_id,
            "project_id": request.project_id,
            "revision_id": request.revision_id,
            "engine": "hyperframes",
            "video": facts,
            "video_artifact": video_ref.to_dict(),
            "preview_artifact": preview_ref.to_dict(),
            "build": build,
            "process_id": session.id,
        }

        receipt_ref = store.store(
            context.task_id,
            f"creative-hyperframes-receipt-{operation_id}.json",
            receipt,
            schema="creative.hyperframes-video.v1",
            media_type="application/json",
        )

        journal.record(
            ExecutionEventKind.DELIVERABLE,
            "HyperFrames motion video rendered and persisted",
            metadata={
                "operation_id": operation_id,
                "run_id": context.run_id,
                "project_id": request.project_id,
                "revision_id": request.revision_id,
                "receipt_ref": receipt_ref.ref,
                "video_sha256": video_ref.sha256,
            },
        )

        return {**receipt, "receipt_artifact": receipt_ref.to_dict()}
    except Exception as error:
        raise CreativeEffectUncertain(operation_id) from error

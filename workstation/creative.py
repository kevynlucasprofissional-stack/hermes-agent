"""Opt-in Creative CLI; inherits session/profile identity from Hermes, never mints it."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from gateway.session_context import get_session_env
from hermes_constants import get_hermes_home
from hermes_cli.config import load_config_readonly
from tools.approval_context import get_current_session_key
from tools.browser_workstation import WorkstationBrowserError
from workstation.config import WorkstationConfig
from workstation.creative_project_runtime import CreativeEffectUncertain, CreativeRunContext, save_project_for_run
from workstation.creative_project_store import load_creative_revision
from workstation.creative_render import render_project_for_run
from workstation.creative_video import CreativeStillVideoRequest, encode_still_video
from workstation.creative_video_process import CreativeVideoEngines


def _execute(args, config, context, workspace):
    def save():
        source_path = args.source.resolve(strict=True)
        if (not source_path.is_file() or not source_path.is_relative_to(workspace)
                or source_path.stat().st_size > 262_144):
            raise PermissionError("Creative input source is outside workspace or oversized")
        return save_project_for_run(config, context, json.loads(source_path.read_bytes()),
                                    project_id=args.project_id, parent_revision=args.parent_revision, engine=args.engine)

    def inspect():
        revision = load_creative_revision(args.project_id, args.revision_id)
        if not revision.source_path.is_relative_to(workspace):
            raise PermissionError("Creative project is outside TaskRun workspace")
        return {"project_id": revision.project_id, "revision_id": revision.revision_id,
                "engine": revision.engine,
                "source_sha256": revision.source_sha256, "parent_revision": revision.parent_revision,
                "source": json.loads(revision.source_path.read_bytes())}

    handlers = {
        "save": save, "inspect": inspect,
        "render": lambda: render_project_for_run(config, context, project_id=args.project_id,
            revision_id=args.revision_id, browser_task_id=args.browser_task_id),
        "video": lambda: encode_still_video(config, context, CreativeStillVideoRequest(
            args.project_id, args.revision_id, str(args.source_png), args.source_sha256,
            args.width, args.height, args.duration_seconds, args.fps), CreativeVideoEngines.from_config(config)),
    }
    return handlers[args.command]()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes Creative projects (explicit opt-in required)")
    parser.add_argument("--task-id", required=True, help="Existing canonical Kanban task")
    parser.add_argument("--run-id", required=True, type=int, help="Existing live TaskRun")
    commands = parser.add_subparsers(dest="command", required=True)
    save = commands.add_parser("save", help="Append an editable source revision")
    save.add_argument("--source", required=True, type=Path)
    save.add_argument("--project-id")
    save.add_argument("--parent-revision")
    save.add_argument("--engine", choices=("electron-svg", "remotion"), default="electron-svg")
    inspect = commands.add_parser("inspect", help="Read a recorded project revision")
    render = commands.add_parser("render", help="Render through an already-owned native BrowserTask")
    video = commands.add_parser("video", help="Encode an owned PNG using explicitly pinned media engines")
    for command in (inspect, render, video):
        command.add_argument("--project-id", required=True)
        command.add_argument("--revision-id", required=True)
    render.add_argument("--browser-task-id", required=True)
    video.add_argument("--source-png", required=True, type=Path)
    video.add_argument("--source-sha256", required=True)
    video.add_argument("--width", required=True, type=int)
    video.add_argument("--height", required=True, type=int)
    video.add_argument("--duration-seconds", default=8, type=int)
    video.add_argument("--fps", default=30, type=int)
    args = parser.parse_args(argv)
    config = WorkstationConfig(load_config_readonly())
    context = CreativeRunContext(str(get_hermes_home()), get_current_session_key(default=""),
                                 get_session_env("HERMES_SESSION_ID", ""), args.task_id, args.run_id)
    try:
        workspace = context.validate(config)
        result = _execute(args, config, context, workspace)
    except (OSError, ValueError, PermissionError, RuntimeError) as error:
        # Do not print external engine/controller text or credentials to the terminal.
        failure = {"success": False, "error_type": type(error).__name__,
                   "retryable": False, "instruction": "Inspect the owner journal before retrying"}
        if isinstance(error, WorkstationBrowserError):
            failure.update(error_code=error.error_code, state_changed=error.state_changed)
        if isinstance(error, CreativeEffectUncertain):
            failure.update(error_code="EFFECT_UNCERTAIN", state_changed=True, operation_id=error.operation_id)
        print(json.dumps(failure), file=sys.stderr)
        return 1
    print(json.dumps({"success": True, "result": result}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

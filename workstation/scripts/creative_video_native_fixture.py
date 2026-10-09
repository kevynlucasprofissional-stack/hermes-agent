"""Exercise installed media binaries against an ephemeral canonical TaskRun."""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import yaml

from gateway.session_context import scoped_current_session_id
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from hermes_cli import kanban_db
from hermes_cli.kanban_db_connect import connect_closing
from tools.approval_context import reset_current_session_key, set_current_session_key
from workstation.config import WorkstationConfig
from workstation.creative_apps import CreativeAppManifest
from workstation.creative_project_runtime import CreativeRunContext, save_project_for_run
from workstation.creative import main as creative_main
from workstation.creative_video_process import CreativeVideoEngines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--ffprobe", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    engines = CreativeVideoEngines(*(CreativeAppManifest(
        1, name, str(path.resolve(strict=True)), hashlib.sha256(path.read_bytes()).hexdigest(),
        "installed:ffmpeg-full:8.1.1:gyan") for name, path in (("ffmpeg", args.ffmpeg), ("ffprobe", args.ffprobe))))
    config = WorkstationConfig({"creative": {"enabled": True}})
    with tempfile.TemporaryDirectory(prefix="hermes-creative-video-") as temporary:
        home = Path(temporary) / "profile"
        workspace = home / "workstation" / "creative" / "projects"
        workspace.mkdir(parents=True)
        (home / "config.yaml").write_text(yaml.safe_dump({"creative": {"enabled": True,
            "engines": {"ffmpeg": engines.ffmpeg.to_dict(), "ffprobe": engines.ffprobe.to_dict()}}}), encoding="utf-8")
        previous = os.environ.get("HERMES_KANBAN_DB")
        os.environ["HERMES_KANBAN_DB"] = str(home / "kanban.db")
        home_token = set_hermes_home_override(home)
        session_token = set_current_session_key("creative-video-fixture-key")
        try:
            with scoped_current_session_id("creative-video-fixture-session"):
                with connect_closing() as connection:
                    task_id = kanban_db.create_task(connection, title="Creative native video fixture",
                        session_id="creative-video-fixture-session", workspace_kind="dir", workspace_path=str(workspace))
                    task = kanban_db.claim_task(connection, task_id, ttl_seconds=300)
                if task is None:
                    raise RuntimeError("Cannot claim fixture TaskRun")
                context = CreativeRunContext(str(home), "creative-video-fixture-key",
                    "creative-video-fixture-session", task_id, task.current_run_id)
                source = workspace / "input.png"
                shutil.copyfile(args.input, source)
                revision = save_project_for_run(config, context, {"kind": "still-image", "asset": "input.png"})
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    exit_code = creative_main(["--task-id", task_id, "--run-id", str(task.current_run_id),
                        "video", "--project-id", revision["project_id"], "--revision-id", revision["revision_id"],
                        "--source-png", str(source), "--source-sha256", hashlib.sha256(source.read_bytes()).hexdigest(),
                        "--width", "360", "--height", "640"])
                if exit_code != 0:
                    raise RuntimeError("Creative video CLI fixture failed")
                receipt = json.loads(stdout.getvalue())["result"]
                renders = workspace / revision["project_id"] / "renders" / receipt["operation_id"]
                args.output.mkdir(parents=True, exist_ok=False)
                for name in ("video.mp4", "preview.png"):
                    shutil.copyfile(renders / name, args.output / name)
                (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
                print(json.dumps({"output": str(args.output.resolve()), "video": receipt["video"]}))
        finally:
            reset_current_session_key(session_token)
            reset_hermes_home_override(home_token)
            if previous is None:
                os.environ.pop("HERMES_KANBAN_DB", None)
            else:
                os.environ["HERMES_KANBAN_DB"] = previous


if __name__ == "__main__":
    main()

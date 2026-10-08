"""Prepare an ephemeral canonical TaskRun for the real Electron/CLI integration test."""
from __future__ import annotations

import json
import os
from pathlib import Path

from hermes_constants import get_hermes_home
from hermes_cli import kanban_db
from hermes_cli.kanban_db_connect import connect_closing


def main() -> None:
    isolation = Path(os.environ["HERMES_TEST_ISOLATION"]).resolve(strict=True)
    home = get_hermes_home().resolve()
    if home == isolation or not home.is_relative_to(isolation):
        raise ValueError("Native fixture must use an isolated child profile")
    workspace = home / "workstation" / "creative" / "projects"
    workspace.mkdir(parents=True)
    (home / "config.yaml").write_text("creative:\n  enabled: true\n", encoding="utf-8")
    source = workspace / "invitation-input.json"
    source.write_text(json.dumps({
        "schemaVersion": 1, "width": 360, "height": 640, "background": "#14263d",
        "elements": [
            {"kind": "circle", "x": 180, "y": 130, "radius": 62, "fill": "#f6c85f"},
            {"kind": "text", "x": 180, "y": 300, "size": 30, "fill": "#ffffff",
             "anchor": "middle", "text": "HERMES PROJECT"},
        ],
    }), encoding="utf-8")
    with connect_closing() as connection:
        task_id = kanban_db.create_task(connection, title="Native Creative fixture",
                                       session_id="creative-project-session", workspace_kind="dir",
                                       workspace_path=str(workspace))
        task = kanban_db.claim_task(connection, task_id, ttl_seconds=300)
    if task is None:
        raise RuntimeError("Native fixture could not claim canonical TaskRun")
    print(json.dumps({"task_id": task_id, "run_id": task.current_run_id, "source": str(source)}))


if __name__ == "__main__":
    main()

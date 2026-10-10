"""Adapter contracts using a simulated owner; these do not qualify native rendering."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

from PIL import Image
import pytest

from gateway.session_context import scoped_current_session_id
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from hermes_cli import kanban_db
from hermes_cli.kanban_db_connect import connect_closing
from tools.approval_context import reset_current_session_key, set_current_session_key
from workstation.config import WorkstationConfig
from workstation.creative_project_runtime import CreativeEffectUncertain, CreativeRunContext, save_project_for_run
from workstation.creative_render import render_project_for_run
from workstation.journal import ExecutionJournal


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    home = tmp_path / "profile"
    native = tmp_path / "native"
    workspace = home / "workstation" / "creative" / "projects"
    workspace.mkdir(parents=True)
    native.mkdir()
    monkeypatch.setenv("HERMES_KANBAN_DB", str(home / "kanban.db"))
    monkeypatch.setenv("HERMES_WORKSTATION_HOME", str(native))
    projection = native / "Runtime" / "browser-session.json"
    projection.parent.mkdir()
    token = set_hermes_home_override(home)
    key_token = set_current_session_key("approval-key")
    try:
        with scoped_current_session_id("durable-session"):
            with connect_closing() as connection:
                task_id = kanban_db.create_task(connection, title="render contract", session_id="durable-session",
                                               workspace_kind="dir", workspace_path=str(workspace))
                task = kanban_db.claim_task(connection, task_id, ttl_seconds=300)
            context = CreativeRunContext(str(home), "approval-key", "durable-session", task_id, task.current_run_id)
            config = WorkstationConfig({"creative": {"enabled": True}})
            revision = save_project_for_run(config, context, {"width": 32, "height": 64})
            yield home, native, projection, context, config, revision
    finally:
        reset_current_session_key(key_token)
        reset_hermes_home_override(token)


def test_adapter_real_http_receipt_file_decode_artifact_and_distinct_identities(prepared, monkeypatch):
    home, native, projection, context, config, revision = prepared
    capture = native / "Browser" / "Screenshots" / "fixture.png"
    capture.parent.mkdir(parents=True)
    Image.new("RGB", (32, 64), "blue").save(capture)
    digest = hashlib.sha256(capture.read_bytes()).hexdigest()
    calls = []
    tamper = [False]

    class Owner(BaseHTTPRequestHandler):
        def do_POST(self):
            assert self.headers["Authorization"] == "Bearer fixture-only-token"
            payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append(payload)
            receipt = {"operationId": payload["operation_id"], "taskId": "native-browser",
                       "browserTaskId": "native-browser", "runId": str(context.run_id), "tabId": "native-tab",
                       "revision": len(calls), "action": "browser_creative_render"}
            task = {"taskId": "native-browser", "sessionHost": context.session_id,
                    "runId": str(context.run_id), "kanbanCardId": context.task_id,
                    "revision": len(calls), "lastReceipt": receipt, "status": "parked"}
            state = {"version": 1, "browserTasks": {"version": 1, "tasks": [task]},
                     "tabs": [{"browserTaskId": "native-browser", "id": "native-tab", "recoveryState": "live"}]}
            projection.write_text(json.dumps(state), encoding="utf-8")
            svg = "<svg/>"
            result = {"success": True, "runtime": "electron-chromium", "receipt": receipt, "tab_id": "native-tab",
                      "source_sha256": payload["arguments"]["source_sha256"], "screenshot_path": str(capture),
                      "sha256": digest, "svg_source": svg, "svg_sha256": hashlib.sha256(svg.encode()).hexdigest()}
            if tamper[0]:
                task["lastReceipt"] = {**receipt, "operationId": "other-operation"}
                projection.write_text(json.dumps(state), encoding="utf-8")
            data = json.dumps({"success": True, "result": result}).encode()
            self.send_response(200)
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Owner)
    control = native / "control.json"
    control.write_text(json.dumps({"version": 1, "url": f"http://127.0.0.1:{server.server_port}",
                                  "token": "fixture-only-token"}), encoding="utf-8")
    monkeypatch.setenv("HERMES_WORKSTATION_BROWSER_CONTROL_FILE", str(control))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        result = render_project_for_run(config, context, project_id=revision["project_id"],
                                        revision_id=revision["revision_id"], browser_task_id="native-browser")
        assert result["media_readback"]["decoded"] is True
        assert result["png_artifact"]["sha256"] == digest
        assert calls[0]["task_id"] == "native-browser" and calls[0]["kanban_card_id"] == context.task_id
        assert "operation_id" not in calls[0]["arguments"]
        artifacts = set((home / "workstation" / "artifacts" / context.task_id).iterdir())
        tamper[0] = True
        with pytest.raises(CreativeEffectUncertain):
            render_project_for_run(config, context, project_id=revision["project_id"],
                                   revision_id=revision["revision_id"], browser_task_id="native-browser")
        assert len(calls) == 2  # no automatic retry after a mismatching owner receipt
        assert set((home / "workstation" / "artifacts" / context.task_id).iterdir()) == artifacts
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_post_dispatch_authority_loss_is_uncertain_and_never_publishes(prepared, monkeypatch):
    home, native, projection, context, config, revision = prepared
    calls = []

    def terminate(*args, **kwargs):
        calls.append(True)
        with connect_closing() as connection:
            connection.execute("UPDATE tasks SET status='cancelled' WHERE id=?", (context.task_id,))
            connection.commit()
        return {}

    monkeypatch.setattr("workstation.creative_render.dispatch_workstation_browser_authoritative", terminate)
    artifacts = set((home / "workstation" / "artifacts" / context.task_id).iterdir())
    with pytest.raises(CreativeEffectUncertain) as failure:
        render_project_for_run(config, context, project_id=revision["project_id"],
                               revision_id=revision["revision_id"], browser_task_id="native-browser")
    assert len(calls) == 1 and failure.value.operation_id
    assert set((home / "workstation" / "artifacts" / context.task_id).iterdir()) == artifacts
    events = ExecutionJournal(task_id=context.task_id, session_id=context.session_id).read_events()
    assert events[-1].metadata["operation_id"] == failure.value.operation_id
    with pytest.raises(PermissionError):
        render_project_for_run(config, context, project_id=revision["project_id"],
                               revision_id=revision["revision_id"], browser_task_id="native-browser")
    assert len(calls) == 1

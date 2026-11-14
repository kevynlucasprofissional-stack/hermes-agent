"""P2 canonical admission integration with real fixture HTTP/SQLite and fake Browser ACK.

These unit/integration tests are NOT native Chromium E2E. The live check
is run separately through the authenticated Electron owner.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sqlite3
import threading
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from hermes_cli import kanban_db
from workstation.artifacts import ArtifactStore
from workstation.browser_operation_readback import (
    BrowserReadbackContract, verify_native_browser_receipts,
)
from workstation.native_browser_evidence import capture_native_browser_operation
from workstation.tests.fixtures.browser_kanban_qa_fixture import make_server
from workstation.tests.test_kanban_direct_file_readback import _admit, _bound_run


@pytest.fixture
def env(tmp_path, monkeypatch):
    home = tmp_path / "home"
    browser = tmp_path / "desktop"
    home.mkdir()
    (browser / "Runtime").mkdir(parents=True)
    db_path = tmp_path / "kanban-isolated.db"
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.setenv("HERMES_KANBAN_DB", str(db_path))
    monkeypatch.setenv("HERMES_WORKSTATION_HOME", str(browser))
    server = make_server(tmp_path / "fixture.sqlite")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/"
    try:
        bridge, agent, task_id, run_id = _bound_run()
        assert db_path.exists()
        yield {
            "url": url, "bridge": bridge, "agent": agent,
            "task": task_id, "run": run_id, "browser": browser,
            "fixture_db": tmp_path / "fixture.sqlite",
            "kanban_db": db_path,
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def _setup_owner(env):
    now = datetime.now(timezone.utc).isoformat()
    return {
        "version": 1, "savedAt": now,
        "tabs": [{"id": "tab-qa-p2", "browserTaskId": env["task"],
                  "safeUrl": env["url"], "recoveryState": "live",
                  "recoveryReason": None}],
        "browserTasks": {"version": 1, "tasks": [{
            "taskId": env["task"], "sessionHost": env["agent"].session_id,
            "runId": env["run"], "lastReceipt": None,
        }]},
        "operationAdmissions": {},
    }


def _observe(env, state, *, action, call_id, operation_id):
    now = datetime.now(timezone.utc).isoformat()
    receipt = {
        "operationId": operation_id, "taskId": env["task"],
        "runId": env["run"], "browserTaskId": env["task"],
        "tabId": "tab-qa-p2", "action": action, "revision": 2,
        "safeUrl": env["url"], "executedAt": now,
    }
    state["savedAt"] = now
    state["browserTasks"]["tasks"][0]["lastReceipt"] = receipt
    state["operationAdmissions"][operation_id] = {
        "operationId": operation_id, "taskId": env["task"],
        "sessionId": env["agent"].session_id, "runId": env["run"],
        "tabId": "tab-qa-p2", "action": action,
        "argumentsDigest": "a" * 64, "acknowledged": True,
    }
    path = env["browser"] / "Runtime" / "browser-session.json"
    path.write_text(json.dumps(state), encoding="utf-8")
    raw = {"success": True, "runtime": "electron-chromium",
           "task_id": env["task"], "tab_id": "tab-qa-p2",
           "operation_id": operation_id, "receipt": receipt}
    proof = capture_native_browser_operation(
        action, raw, task_id=env["task"],
        session_id=env["agent"].session_id, run_id=env["run"],
        call_id=call_id, owner_path=path,
        snapshot_reader=lambda: {"success": True, "runtime": "electron-chromium",
                                 "task_id": env["task"], "tab_id": "tab-qa-p2",
                                 "url": env["url"], "cached": False})
    assert proof and proof["status"] == "observed", proof
    row = {"call_id": call_id, "tool": action, "effect": "INTERACTIVE",
           "status": "completed", "native_browser_evidence": proof}
    env["agent"]._work_tool_observations.append(row)
    return row


def _submit_real_fixture(env, *, value="QA P2 persistido", revision=0):
    with urlopen(env["url"], timeout=3) as response:
        page = response.read().decode()
    operation = re.search(
        r'name="operation_id" type="hidden" value="([a-f0-9]{32})"', page)
    assert operation
    data = urlencode({
        "title": value, "expected_revision": str(revision),
        "operation_id": operation[1],
    }).encode()
    return urlopen(Request(env["url"] + "save", data=data, method="POST"), timeout=3)


def _getter(env):
    def read(path):
        assert path == "/api/item"
        with urlopen(env["url"] + "api/item", timeout=3) as response:
            body = json.load(response)
        return {
            "status": 200, "ok": True, "content_type": "application/json",
            "url": env["url"] + "api/item", "json": body,
        }
    return read


def _prepare(env, *, commit=True):
    state = _setup_owner(env)
    _observe(env, state, action="browser_type", call_id="call-type",
             operation_id="op_p2_type")
    if commit:
        _observe(env, state, action="browser_click", call_id="call-click",
                 operation_id="op_p2_click")
    env["agent"]._work_browser_readback_contract = BrowserReadbackContract(
        commit_call_id="call-click", input_call_ids=("call-type",),
        read_path="/api/item", resource_id="qa-1",
        expected_fields=(("title", "QA P2 persistido"), ("revision", 1)),
        revision_before=0, revision_after=1,
    )
    return state


def test_real_fixture_persisted_get_enters_canonical_done(env, monkeypatch):
    """Actual HTTP POST+GET and Kanban SQLite, synthetic Browser owner receipt."""
    _prepare(env)
    with _submit_real_fixture(env) as response:
        assert response.status == 200
    monkeypatch.setattr("tools.browser_workstation.call_workstation_browser",
                        lambda action, args, **kw: _getter(env)(args["url"]))
    admitted = _admit(env["agent"], env["task"], env["run"])
    assert admitted.admitted is True, admitted.reason
    with sqlite3.connect(env["fixture_db"]) as source:
        assert source.execute("SELECT title,revision FROM qa_item WHERE id=1").fetchone() == (
            "QA P2 persistido", 1)
    with sqlite3.connect(env["kanban_db"]) as fresh:
        fresh.row_factory = sqlite3.Row
        task = kanban_db.get_task(fresh, env["task"])
        run = kanban_db.latest_run(fresh, env["task"])
        assert task.status == "done" and run.status == "done"
        outcome = run.metadata["workstation"]["outcome"]
        assert outcome["status"] == "verified_completed"
        assert outcome["verifier_results"][0]["verifier"] == "native_browser_external_readback"
        assert outcome["evidence_refs"] and outcome["operation_id"] == "op_p2_click"


@pytest.mark.parametrize("issue", [
    "missing_contract", "no_commit", "extra_click", "missing_type_proof",
    "wrong_task", "wrong_run", "wrong_tab", "wrong_op", "bad_status",
    "wrong_revision", "wrong_title", "wrong_resource", "wrong_origin",
    "stale_snapshot", "trace_truncated", "unknown_effect", "out_of_order",
    "read_labeled_click", "uncovered_batch", "wrong_http_path", "read_unavailable",
    "ui_only", "read_http_500",
])
def test_browser_finalizer_rejects_incomplete_or_forged_effect(env, monkeypatch, issue):
    _prepare(env)
    contract = env["agent"]._work_browser_readback_contract
    observations = env["agent"]._work_tool_observations
    read = _getter(env)
    if issue != "ui_only":
        with _submit_real_fixture(env):
            pass
    if issue == "missing_contract":
        env["agent"]._work_browser_readback_contract = None
    elif issue == "no_commit":
        observations.pop()
    elif issue == "extra_click":
        observations.append({"tool": "browser_click", "call_id": "another-click",
                             "effect": "INTERACTIVE", "status": "completed"})
    elif issue == "missing_type_proof":
        observations[0].pop("native_browser_evidence")
    elif issue == "wrong_task":
        observations[1]["native_browser_evidence"]["task_id"] = "other"
    elif issue == "wrong_run":
        observations[1]["native_browser_evidence"]["run_id"] = "other"
    elif issue == "wrong_tab":
        observations[1]["native_browser_evidence"]["tab_id"] = "other"
    elif issue == "wrong_op":
        observations[1]["native_browser_evidence"]["operation_id"] = "other"
    elif issue == "bad_status":
        observations[1]["status"] = "failed"
    elif issue == "wrong_revision":
        read = lambda path: {**_getter(env)(path), "json": {"id": "qa-1",
                     "title": "QA P2 persistido", "revision": 0}}
    elif issue == "wrong_title":
        read = lambda path: {**_getter(env)(path), "json": {"id": "qa-1",
                     "title": "drift", "revision": 1}}
    elif issue == "wrong_resource":
        read = lambda path: {**_getter(env)(path), "json": {"id": "qa-2",
                     "title": "QA P2 persistido", "revision": 1}}
    elif issue == "wrong_origin":
        read = lambda path: {**_getter(env)(path), "url": "https://other.example/api/item"}
    elif issue == "stale_snapshot":
        observations[1]["native_browser_evidence"]["status"] = "uncertain"
    elif issue == "unknown_effect":
        observations.append({"tool": "write_file", "call_id": "external-write",
                             "effect": "MUTATION", "status": "completed"})
    elif issue == "out_of_order":
        observations.reverse()
    elif issue == "read_labeled_click":
        observations.append({"tool": "browser_click", "call_id": "forged-read",
                             "effect": "PURE_READ", "status": "completed"})
    elif issue == "uncovered_batch":
        observations.append({"tool": "browser_batch_actions", "call_id": "batch",
                             "effect": "INTERACTIVE", "status": "completed"})
    elif issue == "wrong_http_path":
        read = lambda path: {**_getter(env)(path), "url": env["url"] + "another"}
    elif issue == "read_unavailable":
        def read(path):
            raise ConnectionError("QA read unavailable")
    elif issue == "read_http_500":
        read = lambda path: {**_getter(env)(path), "status": 500, "ok": False}
    monkeypatch.setattr("tools.browser_workstation.call_workstation_browser",
                        lambda action, args, **kw: read(args["url"]))
    if issue == "trace_truncated":
        result = verify_native_browser_receipts(
            observations, task_id=env["task"], session_id=env["agent"].session_id,
            run_id=env["run"], trace_truncated=True, contract=contract, read_http=read)
        assert result[2] and not result[0]
        return
    admission = _admit(env["agent"], env["task"], env["run"])
    assert admission.admitted is False, issue
    with sqlite3.connect(env["kanban_db"]) as fresh:
        fresh.row_factory = sqlite3.Row
        assert kanban_db.get_task(fresh, env["task"]).status != "done"


def test_conflict_409_does_not_verify_or_resend(env, monkeypatch):
    _prepare(env)
    with _submit_real_fixture(env, value="Another writer"):
        pass
    with pytest.raises(HTTPError) as error:
        with _submit_real_fixture(env, value="QA P2 persistido", revision=0):
            pass
    assert error.value.code == 409
    monkeypatch.setattr("tools.browser_workstation.call_workstation_browser",
                        lambda action, args, **kw: _getter(env)(args["url"]))
    assert _admit(env["agent"], env["task"], env["run"]).admitted is False
    with sqlite3.connect(env["fixture_db"]) as source:
        assert source.execute("SELECT COUNT(*) FROM qa_applied_operations").fetchone()[0] == 1

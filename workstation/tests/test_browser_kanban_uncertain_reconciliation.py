"""HTTP303 lost ACK: real localhost POST and fresh GET, no second mutation.

Owner admission and observer rows in this isolated contract test are fixtures;
the separate native runner exercises real Chromium for the normal path.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytest

from hermes_cli import kanban_db
from workstation.browser_operation_readback import BrowserReadbackContract
from workstation.tests.test_browser_kanban_canonical_readback import env, _setup_owner, _observe, _admit

CLICK_OPERATION = "op_browser_click_missing_ack"
CLICK_CALL = "call-click-lost"
TITLE = "QA P3 recovered"


def _scenario(env, *, wrong_remote=False, wrong_run=False, wrong_tab=False,
              wrong_revision=False, missing_pending=False, bad_status=False):
    state = _setup_owner(env)
    _observe(env, state, action="browser_type",
             call_id="call-type", operation_id="op_p3_type")

    pending = {
        "operationId": CLICK_OPERATION, "taskId": env["task"],
        "sessionId": env["agent"].session_id,
        "runId": "9999" if wrong_run else env["run"],
        "tabId": "alien-tab" if wrong_tab else "tab-qa-p2",
        "action": "browser_click",
        "argumentsDigest": "a" * 64,
    }
    if not missing_pending:
        state["operationAdmissions"][CLICK_OPERATION] = pending
    (env["browser"] / "Runtime" / "browser-session.json").write_text(
        json.dumps(state), encoding="utf-8")

    page = urlopen(env["url"], timeout=3).read().decode("utf-8")
    submitted_id = re.search(
        r'name="operation_id" type="hidden" value="([a-f0-9]{32})"', page,
    ).group(1)
    data = urlencode({
        "title": TITLE, "expected_revision": "0",
        "operation_id": submitted_id,
    }).encode()
    with urlopen(Request(env["url"] + "save", data=data, method="POST"),
                 timeout=3) as response:
        assert response.status == 200  # urllib follows the HTTP303 after POST

    env["agent"]._work_tool_observations.append({
        "call_id": CLICK_CALL,
        "tool": "browser_click", "effect": "INTERACTIVE",
        "status": "completed" if bad_status else "failed",
        "browser_uncertain_error": "browser_input_delivery_unverified",
    })
    env["agent"]._work_browser_readback_contract = BrowserReadbackContract(
        commit_call_id=CLICK_CALL, input_call_ids=("call-type",),
        read_path="/api/item/operation", resource_id="qa-1",
        expected_fields=(("title", TITLE), ("revision", 1)),
        revision_before=0,
        revision_after=2 if wrong_revision else 1,
        uncertain_operation_id=CLICK_OPERATION,
        remote_operation_id=("f" * 32 if wrong_remote else submitted_id),
    )
    def read_http(path):
        with urlopen(env["url"] + path.lstrip("/"), timeout=3) as response:
            return {
                "status": response.status, "ok": True,
                "content_type": response.headers.get("Content-Type"),
                "url": response.url, "json": json.load(response),
            }
    return read_http


@pytest.mark.parametrize("fault", [
    None, "wrong_remote", "wrong_run", "wrong_tab", "wrong_revision",
    "missing_pending", "bad_status",
])
def test_lost_ack_reconciles_only_original_owned_persisted_effect(env, monkeypatch, fault):
    args = {fault: True} if fault else {}
    read_http = _scenario(env, **args)
    monkeypatch.setattr(
        "tools.browser_workstation.call_workstation_browser",
        lambda action, arguments, **kw: read_http(arguments["url"]),
    )
    result = _admit(env["agent"], env["task"], env["run"])
    expected = fault is None
    assert result.admitted is expected, (fault, result.reason)
    with sqlite3.connect(env["fixture_db"]) as db:
        assert db.execute("SELECT COUNT(*) FROM qa_applied_operations").fetchone()[0] == 1
        assert db.execute("SELECT revision FROM qa_item WHERE id=1").fetchone()[0] == 1
    with sqlite3.connect(env["kanban_db"]) as db:
        db.row_factory = sqlite3.Row
        task = kanban_db.get_task(db, env["task"])
        assert (task.status == "done") is expected
        if expected:
            latest = kanban_db.latest_run(db, env["task"])
            outcome = latest.metadata["workstation"]["outcome"]
            verifier = outcome["verifier_results"][0]
            assert verifier["verifier"] == "native_browser_external_readback"
            assert verifier["source_kind"] == "browser_authenticated_same_origin_get"
            assert verifier["owner_ack"] is False
            assert outcome["operation_id"] == CLICK_OPERATION
    # No browser_click or POST replay: the original pending admission
    # is not converted into a fabricated ACK by the Python verifier.
    state = json.loads((Path(env["browser"]) / "Runtime" / "browser-session.json").read_text())
    pending = state.get("operationAdmissions", {}).get(CLICK_OPERATION)
    if pending:
        assert pending.get("acknowledged") is not True

def test_observer_marks_only_the_exact_native_lost_ack_code(monkeypatch):
    from types import SimpleNamespace
    from workstation.integrations.hermes import tool_observer
    monkeypatch.setattr(tool_observer, "capture_raw_result", lambda *args: None)
    agent = SimpleNamespace(
        _work_tool_observations=[{"call_id": "lost", "tool": "browser_click",
                                  "effect": "INTERACTIVE", "status": "started"}],
        valid_tool_names=set(),
        _canonical_work_task_id=None, _canonical_work_run_id=None,
        session_id="qa", _conversation_root_id=lambda: "qa",
    )
    tool_observer.workstation_raw_post_tool_observer(
        "browser_click", {"ref": "save"}, "lost",
        {"success": False, "error_code": "CAPABILITY_MISSING",
         "message": "browser_input_delivery_unverified"},
        0.01, {"agent": agent, "dispatched": True},
    )
    row = agent._work_tool_observations[0]
    assert row["status"] == "failed"
    assert row["browser_uncertain_error"] == "browser_input_delivery_unverified"

@pytest.mark.parametrize("message,recognized", [
    ("Error executing browser_click: browser_input_delivery_unverified", True),
    ("Error executing tool 'browser_click': browser_input_delivery_unverified", True),
    ("Error executing browser_navigate: browser_input_delivery_unverified", False),
    ("Error executing browser_click: other_failure", False),
])
def test_actual_executor_error_text_preserves_lost_ack_for_recovery(
    monkeypatch, message, recognized,
):
    from types import SimpleNamespace
    from workstation.integrations.hermes import tool_observer

    monkeypatch.setattr(tool_observer, "capture_raw_result", lambda *args: None)
    agent = SimpleNamespace(
        _work_tool_observations=[{"call_id": "original-click", "tool": "browser_click",
                                  "effect": "INTERACTIVE", "status": "started"}],
        valid_tool_names=set(), _canonical_work_task_id=None,
        _canonical_work_run_id=None, session_id="qa",
        _conversation_root_id=lambda: "qa",
    )
    # model_tools.handle_function_call turns a raised WorkstationBrowserError
    # into {"error": "Error executing browser_click: ..."}.
    tool_observer.workstation_raw_post_tool_observer(
        "browser_click", {"ref": "save"}, "original-click",
        {"error": message}, 0.01, {"agent": agent, "dispatched": True},
    )
    row = agent._work_tool_observations[0]
    assert row["status"] == "failed"
    assert (row.get("browser_uncertain_error") == "browser_input_delivery_unverified") is recognized


@pytest.mark.parametrize("fault", [None, "wrong_remote", "wrong_revision"])
def test_original_failed_click_303_reconciles_through_actual_observer_format(
    env, monkeypatch, fault,
):
    """One real fixture POST/303; inject lost result only, never dispatch another click."""
    from workstation.browser_operation_readback import TrustedBrowserReadbackExpectation
    from workstation.integrations.hermes.tool_observer import workstation_raw_post_tool_observer
    from workstation.integrations.hermes import tool_observer

    read = _scenario(env, **({fault: True} if fault else {}))
    agent = env["agent"]
    old = agent._work_browser_readback_contract
    agent._work_browser_readback_contract = None
    agent._work_browser_readback_expectation = TrustedBrowserReadbackExpectation(
        task_id=env["task"], session_id=agent.session_id, run_id=env["run"],
        expected_origin=env["url"].rstrip("/"), read_path=old.read_path,
        resource_id=old.resource_id, expected_fields=old.expected_fields,
        revision_before=0, revision_after=old.revision_after,
        remote_operation_id=old.remote_operation_id,
    )
    click_row = agent._work_tool_observations[-1]
    click_row["status"] = "started"
    click_row.pop("browser_uncertain_error", None)
    monkeypatch.setattr(tool_observer, "capture_raw_result", lambda *a: None)
    workstation_raw_post_tool_observer(
        "browser_click", {"ref": "save"}, CLICK_CALL,
        {"error": "Error executing browser_click: browser_input_delivery_unverified"},
        0.01, {"agent": agent, "dispatched": True},
    )
    assert click_row["browser_uncertain_error"] == "browser_input_delivery_unverified"
    reads = []
    def read_only(action, arguments, **kwargs):
        assert action == "browser_read_http", "no second browser_click or other mutation"
        reads.append(action)
        return read(arguments["url"])
    monkeypatch.setattr("tools.browser_workstation.call_workstation_browser", read_only)

    admission = _admit(agent, env["task"], env["run"])
    assert admission.admitted is (fault is None), (fault, admission.reason)
    assert len(reads) <= 1
    with sqlite3.connect(env["fixture_db"]) as db:
        assert db.execute("SELECT revision FROM qa_item WHERE id=1").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM qa_applied_operations").fetchone()[0] == 1
    with sqlite3.connect(env["kanban_db"]) as db:
        db.row_factory = sqlite3.Row
        assert (kanban_db.get_task(db, env["task"]).status == "done") is (fault is None)
        if fault is None:
            run = kanban_db.latest_run(db, env["task"])
            outcome = run.metadata["workstation"]["outcome"]
            assert run.status == "done"
            assert outcome["operation_id"] == CLICK_OPERATION
            assert outcome["verifier_results"][0]["owner_ack"] is False
            assert outcome["evidence_refs"]
        else:
            assert "uncertain" in admission.reason
    owner = json.loads((env["browser"] / "Runtime" / "browser-session.json").read_text())
    assert owner["operationAdmissions"][CLICK_OPERATION].get("acknowledged") is not True


def test_host_expectation_binds_unique_original_pending_click_without_ack(env, monkeypatch):
    from workstation.browser_operation_readback import TrustedBrowserReadbackExpectation
    read_http = _scenario(env)
    old = env["agent"]._work_browser_readback_contract
    env["agent"]._work_browser_readback_contract = None
    env["agent"]._work_browser_readback_expectation = TrustedBrowserReadbackExpectation(
        task_id=env["task"], session_id=env["agent"].session_id,
        run_id=env["run"], expected_origin=env["url"].rstrip("/"),
        read_path=old.read_path, resource_id=old.resource_id,
        expected_fields=old.expected_fields, revision_before=0,
        revision_after=1, remote_operation_id=old.remote_operation_id,
    )
    monkeypatch.setattr(
        "tools.browser_workstation.call_workstation_browser",
        lambda action, arguments, **kw: read_http(arguments["url"]),
    )
    result = _admit(env["agent"], env["task"], env["run"])
    assert result.admitted, result.reason
    with sqlite3.connect(env["fixture_db"]) as con:
        assert con.execute("SELECT COUNT(*) FROM qa_applied_operations").fetchone()[0] == 1

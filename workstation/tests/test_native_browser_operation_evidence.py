"""P1 operation evidence: ownership, observation, source proof and adversarial cases.

Tests use actual persisted JSON structures but do NOT claim a Chromium E2E.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import re

import pytest

from workstation.artifacts import ArtifactStore
from workstation.native_browser_evidence import capture_native_browser_operation
from workstation.tests.fixtures.browser_kanban_qa_fixture import make_server


URL = "https://example.test/qa?private_token=never_store"
TASK = "t-evidence"
SESSION = "s-evidence"
RUN = "9"
OP = "op_click_abcd1234"
CALL = "call-test-1"
TAB = "tab-evidence"
ACTION = "browser_click"


@pytest.fixture
def proof_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    store = ArtifactStore(root_dir=tmp_path / "artifacts")
    path = tmp_path / "browser-session.json"
    now = datetime.now(timezone.utc).isoformat()
    receipt = {
        "operationId": OP, "taskId": TASK, "runId": RUN,
        "browserTaskId": TASK, "tabId": TAB, "revision": 3,
        "action": ACTION, "safeUrl": URL, "executedAt": now,
    }
    state = {
        "version": 1, "savedAt": now,
        "browserTasks": {"version": 1, "tasks": [{
            "taskId": TASK, "sessionHost": SESSION, "runId": RUN,
            "revision": 3, "lastReceipt": receipt,
        }]},
        "tabs": [{"id": TAB, "browserTaskId": TASK, "safeUrl": URL,
                  "recoveryState": "live", "recoveryReason": None}],
        "operationAdmissions": {OP: {
            "operationId": OP, "taskId": TASK, "sessionId": SESSION,
            "runId": RUN, "tabId": TAB, "action": ACTION,
            "argumentsDigest": "a" * 64, "acknowledged": True,
        }},
    }
    result = {
        "success": True, "runtime": "electron-chromium",
        "task_id": TASK, "tab_id": TAB, "operation_id": OP,
        "receipt": receipt, "snapshot": "PRIVATE_CANARY_NOT_PERSIST",
    }
    snapshot = {"success": True, "runtime": "electron-chromium",
                "task_id": TASK, "tab_id": TAB, "url": URL,
                "snapshot": "PRIVATE_CANARY_NOT_PERSIST"}
    def capture(*, tool_name=ACTION, **kwargs):
        path.write_text(json.dumps(state), encoding="utf-8")
        return capture_native_browser_operation(
            tool_name, result, task_id=TASK, session_id=SESSION,
            run_id=RUN, call_id=CALL, owner_path=path,
            snapshot_reader=lambda: snapshot, store=store, **kwargs,
        )
    return SimpleNamespace(state=state, result=result, snapshot=snapshot,
                           capture=capture, store=store, path=path)


def test_browser_type_and_click_share_the_owner_contract(proof_env):
    proof_env.result["receipt"]["action"] = "browser_type"
    proof_env.state["operationAdmissions"][OP]["action"] = "browser_type"
    proof = proof_env.capture(tool_name="browser_type")
    assert proof["status"] == "observed"
    assert proof["action"] == "browser_type"
    assert proof["ack"] is True


def test_real_owner_ack_and_new_native_snapshot_are_observed_not_verified(proof_env):
    proof = proof_env.capture()
    assert proof["ack"] and proof["fresh_observation"]
    assert proof["status"] == "observed"
    assert proof["evidence_strength"] == 1
    assert proof["reason"] == "external_persistence_not_verified"
    stored = proof_env.store.read_json(proof["evidence_ref"])
    assert stored["operation_id"] == OP and stored["call_id"] == CALL
    assert "PRIVATE_CANARY_NOT_PERSIST" not in json.dumps(stored)
    assert "private_token" not in json.dumps(stored)
    assert "example.test" not in json.dumps(stored)
    assert stored["status"] != "verified"


@pytest.mark.parametrize("mismatch", [
    "run", "tab", "operation", "admission_missing", "receipt_missing",
    "ack_false", "wrong_action", "another_task", "other_session",
    "owner_not_chromium", "timestamp_stale", "tab_not_live",
    "owner_revision", "receipt_changed", "response_failed",
])
def test_forged_or_stale_owner_identity_is_never_verified(proof_env, mismatch):
    s, r = proof_env.state, proof_env.result
    if mismatch == "run":
        s["operationAdmissions"][OP]["runId"] = "other-run"
    elif mismatch == "tab":
        r["receipt"]["tabId"] = "other-tab"
    elif mismatch == "operation":
        r["operation_id"] = "other-op"
    elif mismatch == "admission_missing":
        s["operationAdmissions"].clear()
    elif mismatch == "receipt_missing":
        r.pop("receipt")
    elif mismatch == "ack_false":
        s["operationAdmissions"][OP]["acknowledged"] = False
    elif mismatch == "wrong_action":
        s["operationAdmissions"][OP]["action"] = "browser_type"
    elif mismatch == "another_task":
        s["operationAdmissions"][OP]["taskId"] = "other-task"
    elif mismatch == "other_session":
        s["browserTasks"]["tasks"][0]["sessionHost"] = "other-session"
    elif mismatch == "owner_not_chromium":
        r["runtime"] = "legacy"
    elif mismatch == "timestamp_stale":
        r["receipt"]["executedAt"] = (
            datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    elif mismatch == "tab_not_live":
        s["tabs"][0]["recoveryState"] = "parked"
    elif mismatch == "owner_revision":
        r["receipt"]["revision"] = -1
    elif mismatch == "receipt_changed":
        s["browserTasks"]["tasks"][0]["lastReceipt"] = dict(r["receipt"], revision=999)
    elif mismatch == "response_failed":
        r["success"] = False
    proof = proof_env.capture()
    assert proof is not None
    assert proof["ack"] is False, mismatch
    assert proof["status"] == "uncertain"
    assert proof["evidence_strength"] == 0


@pytest.mark.parametrize("change", ["cached", "tab", "runtime", "origin", "failed"])
def test_fake_snapshot_rejected_even_with_valid_owner_ack(proof_env, change):
    s = proof_env.snapshot
    if change == "cached":
        s["snapshot_cache"] = "hit"
    elif change == "tab":
        s["tab_id"] = "other-tab"
    elif change == "runtime":
        s["runtime"] = "playwright"
    elif change == "origin":
        s["url"] = "https://other.example/qa"
    elif change == "failed":
        s["success"] = False
    proof = proof_env.capture()
    assert proof["ack"] is True
    assert proof["fresh_observation"] is False
    assert proof["status"] == "uncertain"


def test_browser_owner_without_new_read_or_read_failure_not_verified(proof_env):
    state = proof_env.state
    proof_env.path.write_text(json.dumps(state), encoding="utf-8")
    kw = dict(task_id=TASK, session_id=SESSION, run_id=RUN, call_id=CALL,
              owner_path=proof_env.path, store=proof_env.store)
    no_read = capture_native_browser_operation(ACTION, proof_env.result, **kw)
    assert no_read["status"] == "uncertain"
    failed = capture_native_browser_operation(
        ACTION, proof_env.result, snapshot_reader=lambda: (_ for _ in ()).throw(TimeoutError()),
        **kw)
    assert failed["status"] == "uncertain"
    assert failed["reason"] == "native_snapshot_unavailable"


def test_non_native_or_missing_operation_does_not_fake_receipt(proof_env):
    assert capture_native_browser_operation(
        "write_file", proof_env.result, task_id=TASK, session_id=SESSION,
        run_id=RUN, call_id=CALL, store=proof_env.store) is None
    proof_env.result.pop("operation_id")
    assert proof_env.capture() is None


def test_authoritative_callback_must_match_field_and_origin(proof_env):
    args = dict(predicate="qa_item.title", authoritative_field="title",
                authoritative_resource_id="qa-1", expected_value="Updated")
    ui_only = proof_env.capture(**args)
    assert ui_only["status"] == "observed"
    mismatch = proof_env.capture(
        **args, authoritative_reader=lambda: (URL, {"id": "qa-1", "title": "Other"}))
    assert mismatch["status"] == "observed"
    other_origin = proof_env.capture(
        **args, authoritative_reader=lambda: ("https://other.example", {"id": "qa-1", "title": "Updated"}))
    assert other_origin["status"] == "observed"
    exact = proof_env.capture(
        **args, authoritative_reader=lambda: (URL, {"id": "qa-1", "title": "Updated"}))
    assert exact["status"] == "verified"
    assert exact["evidence_strength"] == 3
    stored = proof_env.store.read_json(exact["evidence_ref"])
    assert "Updated" not in json.dumps(stored)


def test_actual_loopback_http_independent_get_can_certify_fixture_only(proof_env, tmp_path):
    """Real HTTP GET + SQLite; Chromium mutation still NOT exercised here."""
    server = make_server(tmp_path / "independent.sqlite")
    import threading
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        page_url = f"http://127.0.0.1:{server.server_port}/"
        proof_env.result["receipt"]["safeUrl"] = page_url
        proof_env.state["tabs"][0]["safeUrl"] = page_url
        proof_env.snapshot["url"] = page_url
        with urlopen(page_url, timeout=3) as response:
            html = response.read().decode("utf-8")
        match = re.search(r'name="operation_id" type="hidden" value="([a-f0-9]{32})"', html)
        assert match
        post = urlencode({"title": "Atualizado por HTTP QA", "expected_revision": "0",
                          "operation_id": match[1]}).encode()
        with urlopen(Request(page_url + "save", data=post, method="POST"), timeout=3):
            pass
        def external_read():
            with urlopen(page_url + "api/item", timeout=3) as response:
                return page_url + "api/item", json.load(response)
        _, data = external_read()
        assert data == {"id": "qa-1", "title": "Atualizado por HTTP QA", "revision": 1}
        proof = proof_env.capture(
            predicate="qa_item.title", authoritative_field="title",
            expected_value="Atualizado por HTTP QA", authoritative_resource_id="qa-1",
            authoritative_reader=external_read)
        assert proof["status"] == "verified"
        assert proof["evidence_strength"] == 3
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)



def test_post_tool_observer_attaches_bound_observation_without_approval(
    proof_env, tmp_path, monkeypatch,
):
    """Exercise the real observer hook with a bounded owner fixture.

    This is not a Chromium E2E; no real page is clicked.
    """
    import workstation.integrations.hermes.tool_observer as observer
    import tools.browser_workstation as bw

    home = tmp_path / "desktop"
    (home / "Runtime").mkdir(parents=True)
    (home / "Runtime" / "browser-session.json").write_text(
        json.dumps(proof_env.state), encoding="utf-8")
    monkeypatch.setattr(bw, "_workstation_home", lambda: home)
    calls = []
    def read_snapshot(action, args, **kwargs):
        calls.append((action, kwargs))
        return json.dumps(proof_env.snapshot)
    monkeypatch.setattr(bw, "call_workstation_browser", read_snapshot)
    monkeypatch.setattr(observer, "record_mutation", lambda *a, **kw: None)
    monkeypatch.setattr(observer, "capture_raw_result", lambda *a, **kw: None)
    monkeypatch.setattr("workstation.task_compiler.durable_execution_active",
                        lambda: False)

    agent = SimpleNamespace(
        session_id=SESSION, _conversation_root_id=lambda: SESSION,
        _canonical_work_task_id=TASK, _canonical_work_run_id=RUN,
        _work_tool_observations=[{
            "call_id": CALL, "tool": ACTION,
            "effect": "INTERACTIVE", "status": "started",
        }],
        _work_capabilities={},
    )
    observer.workstation_raw_post_tool_observer(
        ACTION, {"ref": "@e1"}, CALL, json.dumps(proof_env.result),
        0.01, {"agent": agent, "dispatched": True},
    )
    row = agent._work_tool_observations[0]
    assert row["status"] == "completed"
    assert row["native_browser_evidence"]["status"] == "observed"
    assert row["native_browser_evidence"]["evidence_strength"] == 1
    assert "external_readback" not in row
    assert len(calls) == 1 and calls[0][0] == "browser_snapshot"
    assert calls[0][1]["run_id"] == RUN and calls[0][1]["session_id"] == SESSION


def test_read_after_later_mutation_is_uncertain(proof_env):
    """Another operation can race the snapshot; don't borrow its UI."""
    from workstation.native_browser_evidence import capture_native_browser_operation
    def later():
        proof_env.state["browserTasks"]["tasks"][0]["lastReceipt"] = {
            "operationId": "op_other", "taskId": TASK,
        }
        proof_env.path.write_text(json.dumps(proof_env.state), encoding="utf-8")
        return proof_env.snapshot
    proof_env.path.write_text(json.dumps(proof_env.state), encoding="utf-8")
    result = capture_native_browser_operation(
        ACTION, proof_env.result, task_id=TASK,
        session_id=SESSION, run_id=RUN, call_id=CALL,
        owner_path=proof_env.path, store=proof_env.store,
        snapshot_reader=later,
    )
    assert result["ack"] is True and result["fresh_observation"] is False
    assert result["status"] == "uncertain"
    assert result["reason"] == "native_snapshot_owner_advanced"


def test_receipts_are_immutable_and_targets_are_redacted(proof_env):
    proof_env.result["target"] = {"ref": "@e17", "name": "PRIVATE_FORM_CONTENT"}
    first = proof_env.capture()
    proof_env.snapshot["snapshot_cache"] = "hit"
    second = proof_env.capture()
    assert first["evidence_ref"] != second["evidence_ref"]
    assert proof_env.store.read_json(first["evidence_ref"])["status"] == "observed"
    assert proof_env.store.read_json(second["evidence_ref"])["status"] == "uncertain"
    stored = proof_env.store.read_json(first["evidence_ref"])
    assert stored["target_ref"] == "@e17"
    assert "PRIVATE_FORM_CONTENT" not in json.dumps(stored)



def test_observed_browser_receipt_cannot_complete_canonical_kanban(proof_env, tmp_path, monkeypatch):
    """Even a valid native ACK + live DOM must not count as external persistence."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes_kanban"))
    from hermes_cli import kanban_db
    from workstation.tests.test_kanban_direct_file_readback import _bound_run, _admit

    bridge, agent, task_id, run_id = _bound_run()
    proof = proof_env.capture()
    assert proof["status"] == "observed" and proof["evidence_strength"] == 1
    agent._work_tool_observations.append({
        "call_id": CALL, "tool": "browser_click", "effect": "INTERACTIVE",
        "status": "completed", "native_browser_evidence": proof,
    })
    outcome = _admit(agent, task_id, run_id)
    assert outcome.admitted is False
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, task_id).status != "done"



def test_authoritative_get_racing_another_operation_cannot_verify(proof_env):
    def racing_get():
        proof_env.state["browserTasks"]["tasks"][0]["lastReceipt"] = {
            "operationId": "op_later", "taskId": TASK,
        }
        proof_env.path.write_text(json.dumps(proof_env.state), encoding="utf-8")
        return URL, {"id": "qa-1", "title": "Updated"}
    proof = proof_env.capture(
        predicate="qa_item.title", authoritative_field="title",
        expected_value="Updated", authoritative_resource_id="qa-1",
        authoritative_reader=racing_get)
    assert proof["status"] == "uncertain"
    assert proof["reason"] == "authoritative_owner_advanced"



def test_matching_value_from_wrong_external_resource_is_not_verification(proof_env):
    base = dict(predicate="qa_item.title", authoritative_field="title",
                expected_value="Updated", authoritative_resource_id="qa-1")
    wrong = proof_env.capture(
        **base, authoritative_reader=lambda: (URL, {"id": "qa-2", "title": "Updated"}))
    assert wrong["status"] == "observed"
    assert wrong["evidence_strength"] == 1
    missing_resource = proof_env.capture(
        predicate="qa_item.title", authoritative_field="title",
        expected_value="Updated",
        authoritative_reader=lambda: (URL, {"id": "qa-1", "title": "Updated"}))
    assert missing_resource["status"] == "observed"

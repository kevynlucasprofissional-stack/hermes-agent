"""Trusted host expectation -> native browser ledger -> canonical acceptance.

QA fixture commits via real HTTP/SQLite. Owner receipts are synthetic here;
the distinct native Chromium qualification stays in the P2 runner.
"""
from __future__ import annotations

import sqlite3

from hermes_cli import kanban_db
from workstation.browser_operation_readback import TrustedBrowserReadbackExpectation
from workstation.tests.test_browser_kanban_canonical_readback import (
    _admit, _getter, _prepare, _submit_real_fixture, env,
)


def _host_bind(data, *, origin=None):
    agent = data["agent"]
    agent._work_browser_readback_contract = None
    agent._work_browser_readback_expectation = TrustedBrowserReadbackExpectation(
        task_id=data["task"], session_id=agent.session_id, run_id=data["run"],
        expected_origin=origin if origin is not None else data["url"].rstrip("/"),
        read_path="/api/item", resource_id="qa-1",
        expected_fields=(("title", "QA P2 persistido"), ("revision", 1)),
        revision_before=0, revision_after=1,
    )


def _navigation(data, *, after=False):
    row = {"call_id": "qa-nav", "tool": "browser_navigate",
           "effect": "INTERACTIVE", "status": "completed"}
    if after:
        data["agent"]._work_tool_observations.insert(2, row)
    else:
        data["agent"]._work_tool_observations.insert(0, row)


def _no_done(data):
    with sqlite3.connect(data["kanban_db"]) as db:
        db.row_factory = sqlite3.Row
        assert kanban_db.get_task(db, data["task"]).status != "done"


def test_host_expectation_and_pre_navigation_enter_canonical_done(env, monkeypatch):
    _prepare(env)
    _host_bind(env)
    _navigation(env)
    with _submit_real_fixture(env):
        pass
    monkeypatch.setattr("tools.browser_workstation.call_workstation_browser",
                        lambda action, args, **kw: _getter(env)(args["url"]))
    result = _admit(env["agent"], env["task"], env["run"])
    assert result.admitted is True, result.reason
    with sqlite3.connect(env["kanban_db"]) as db:
        db.row_factory = sqlite3.Row
        assert kanban_db.get_task(db, env["task"]).status == "done"
        stored = kanban_db.latest_run(db, env["task"])
        assert stored.metadata["workstation"]["outcome"]["verifier_results"][0][
            "verifier"] == "native_browser_external_readback"


def test_model_cannot_appoint_trusted_expectation_with_plain_dict(env, monkeypatch):
    _prepare(env)
    _host_bind(env)
    env["agent"]._work_browser_readback_expectation = vars_like = {
        "task_id": env["task"], "read_path": "/api/item",
        "expected_fields": {"title": "QA P2 persistido", "revision": 1},
    }
    assert vars_like["read_path"] == "/api/item"
    with _submit_real_fixture(env):
        pass
    monkeypatch.setattr("tools.browser_workstation.call_workstation_browser",
                        lambda action, args, **kw: _getter(env)(args["url"]))
    assert _admit(env["agent"], env["task"], env["run"]).admitted is False
    _no_done(env)


def test_wrong_host_origin_rejected(env, monkeypatch):
    _prepare(env)
    _host_bind(env, origin="https://other.example")
    _navigation(env)
    with _submit_real_fixture(env):
        pass
    monkeypatch.setattr("tools.browser_workstation.call_workstation_browser",
                        lambda action, args, **kw: _getter(env)(args["url"]))
    assert _admit(env["agent"], env["task"], env["run"]).admitted is False
    _no_done(env)


def test_navigation_after_typing_does_not_count_as_save_proof(env, monkeypatch):
    _prepare(env)
    _host_bind(env)
    _navigation(env, after=True)
    with _submit_real_fixture(env):
        pass
    monkeypatch.setattr("tools.browser_workstation.call_workstation_browser",
                        lambda action, args, **kw: _getter(env)(args["url"]))
    assert _admit(env["agent"], env["task"], env["run"]).admitted is False
    _no_done(env)


def test_extra_click_does_not_become_canonical_done(env, monkeypatch):
    _prepare(env)
    _host_bind(env)
    _navigation(env)
    env["agent"]._work_tool_observations.append({
        "call_id": "extra-click", "tool": "browser_click",
        "effect": "INTERACTIVE", "status": "completed"})
    with _submit_real_fixture(env):
        pass
    monkeypatch.setattr("tools.browser_workstation.call_workstation_browser",
                        lambda action, args, **kw: _getter(env)(args["url"]))
    assert _admit(env["agent"], env["task"], env["run"]).admitted is False
    _no_done(env)

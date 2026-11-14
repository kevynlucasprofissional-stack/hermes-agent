"""Isolated, behavior-oriented tests for agent-facing Workstation Database capability."""
from __future__ import annotations

import json
import sqlite3

import pytest

from plugins.workstation_database_agent import _handle, register
from plugins.workstation_database_agent import store


def test_save_query_idempotency_and_optimistic_update(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "get_hermes_home", lambda: tmp_path)
    args = {"namespace": "acirv", "key": "daily-2026-11-07", "kind": "report",
            "title": "Daily summary", "data": {"done": 3, "artifact_path": "F:/reports/a.md"}}
    first = json.loads(_handle("workstation_db_save", args))
    assert first["status"] == "created" and first["revision"] == 1
    assert json.loads(_handle("workstation_db_save", args))["status"] == "unchanged"
    path = store.database_path()
    assert path.exists() and path.parent.name == "datasets"
    queried = json.loads(_handle("workstation_db_query", {"dataset": "agent", "namespace": "acirv",
                                                          "key": "daily-2026-11-07"}))
    assert queried["records"][0]["data"]["done"] == 3
    conflict = json.loads(_handle("workstation_db_save", {**args, "data": {"done": 4}}))
    assert conflict["error"] == "revision_conflict" and conflict["current_revision"] == 1
    updated = json.loads(_handle("workstation_db_save",
                                 {**args, "data": {"done": 4}, "expected_revision": 1}))
    assert updated["status"] == "updated" and updated["revision"] == 2
    stale = json.loads(_handle("workstation_db_save",
                               {**args, "data": {"done": 5}, "expected_revision": 1}))
    assert stale["error"] == "revision_conflict"
    assert store.list_records(namespace="acirv", home=tmp_path)["records"][0]["data"]["done"] == 4
    with sqlite3.connect(path) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_separate_profiles_and_no_secrets_or_binary(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    store.save_record(namespace="project", key="work", kind="checkpoint", title="A", data={"n": 1}, home=a)
    assert store.list_records(home=a)["total"] == 1
    assert store.list_records(home=b)["total"] == 0
    for invalid in ({"password": "secret"}, {"nested": [{"access_token": "x"}]},
                    {"binary": "x" * 140000}):
        with pytest.raises(ValueError):
            store.save_record(namespace="project", key="bad", kind="checkpoint",
                              title="Blocked", data=invalid, home=a)
    assert store.list_records(home=a)["total"] == 1


def test_tool_contract_and_imported_sources_read_only(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "get_hermes_home", lambda: tmp_path)
    import workstation.acirv_datasets as datasets
    monkeypatch.setattr(datasets, "get_hermes_home", lambda: tmp_path)
    class Context:
        tools = {}
        def register_tool(self, **kw):
            self.tools[kw["name"]] = kw
    ctx = Context()
    register(ctx)
    assert set(ctx.tools) == {"workstation_db_catalog", "workstation_db_query", "workstation_db_save", "workstation_db_update", "workstation_db_trello_plan", "workstation_db_trello_pull", "workstation_db_trello_push", "workstation_db_trello_route", "workstation_db_trello_api_plan", "workstation_db_trello_api_push"}
    assert all(info["toolset"] == "file" for info in ctx.tools.values())
    catalog = json.loads(ctx.tools["workstation_db_catalog"]["handler"]({}))
    assert catalog["ok"] and catalog["writable"]["dataset"] == "agent"
    assert catalog["imported_writable_local"] == []
    result = json.loads(ctx.tools["workstation_db_query"]["handler"]({"dataset": "tarefas", "table": "tasks"}))
    assert result["ok"] is False
    # The imported dataset directory is not a fallback writer for agent records.
    assert not (datasets.directory(tmp_path) / "tarefas.sqlite").exists()
    assert not (datasets.directory(tmp_path) / "whatsapp.sqlite").exists()
    invalid = json.loads(ctx.tools["workstation_db_save"]["handler"]({
        "namespace": "acirv", "key": "x", "kind": "control",
        "title": "Credentials", "data": {"api_key": "foo"}}))
    assert invalid["ok"] is False


def _trello_case(tmp_path, monkeypatch):
    import sqlite3
    from workstation import acirv_datasets as datasets
    from workstation import trello_sync_reconcile as sync

    monkeypatch.setattr(datasets, "get_hermes_home", lambda: tmp_path)
    folder = datasets.directory(tmp_path)
    folder.mkdir(parents=True, exist_ok=True)
    card_id = "6aeb662086d13678d3a28f64"
    url = "https://trello.com/c/gZy747hA/944"
    with sqlite3.connect(folder / "trello.sqlite") as conn:
        conn.execute("CREATE TABLE cards(id TEXT PRIMARY KEY,name TEXT,description TEXT,status TEXT,url TEXT)")
        conn.execute("INSERT INTO cards VALUES(?,?,?,?,?)", (card_id, "Hermes Work", "", "em_aberto", url))
    remote = {"url": url, "name": "Hermes Work", "open": True, "list_name": "Quarta"}
    def verified(task):
        if task != "native-test":
            raise ValueError("unknown BrowserTask")
        return {**remote, "browser_task_id": task}
    monkeypatch.setattr(sync, "verified_browser_card_title", verified)
    args = {"card_id": card_id, "source_url": url, "browser_task_id": "native-test"}
    return folder, remote, args


def test_native_trello_plan_is_idempotent_and_untrusted_remote_ignored(tmp_path, monkeypatch):
    from workstation.trello_sync_reconcile import read_reviews
    folder, remote, args = _trello_case(tmp_path, monkeypatch)
    req = {**args, "run_id": "native-baseline", "remote": {"name": "INJECTED"},
           "remote_open_verified": False}
    first = json.loads(_handle("workstation_db_trello_plan", req))
    assert first["ok"] and first["review"]["status"] == "recorded"
    assert first["plan"]["native_observed"] is True
    assert first["plan"]["browser_task_id"] == "native-test"
    assert first["plan"]["fields"]["name"]["action"] == "equal"
    assert first["plan"]["fields"]["name"]["value"] == "Hermes Work"
    assert json.loads(_handle("workstation_db_trello_plan", req))["review"]["status"] == "unchanged"

    remote["name"] = "Renomeado no Trello"
    conflict = json.loads(_handle("workstation_db_trello_plan", req))
    assert not conflict["ok"] and conflict["review"]["error"] == "same_run_changed"
    assert conflict["plan"]["pull"] == ["name"]
    next_run = json.loads(_handle("workstation_db_trello_plan", {**args, "run_id": "native-next"}))
    assert next_run["ok"] and next_run["plan"]["pull"] == ["name"]
    assert len(read_reviews(tmp_path, args["card_id"])) == 2

    wrong = json.loads(_handle("workstation_db_trello_plan", {**args, "run_id": "wrong",
        "source_url": "https://trello.com/c/badid123/944"}))
    assert not wrong["ok"]
    wrong_task = json.loads(_handle("workstation_db_trello_plan", {**args, "run_id": "wrong-task",
        "browser_task_id": "other-task"}))
    assert not wrong_task["ok"]
    remote["url"] = "https://trello.com/c/Yzzzzzzz/999"
    wrong_tab = json.loads(_handle("workstation_db_trello_plan", {**args, "run_id": "wrong-tab"}))
    assert wrong_tab["error"] == "native Browser is showing a different Trello card"
    with sqlite3.connect(folder / "trello.sqlite") as conn:
        assert conn.execute("SELECT name FROM cards").fetchone()[0] == "Hermes Work"


def test_verified_pull_rechecks_browser_and_only_writes_local_overlay(tmp_path, monkeypatch):
    import sqlite3
    from workstation import acirv_datasets as datasets
    folder, remote, args = _trello_case(tmp_path, monkeypatch)
    def plan(run):
        return json.loads(_handle("workstation_db_trello_plan", {**args, "run_id": run}))
    def pull(run, revision=0):
        return json.loads(_handle("workstation_db_trello_pull", {
            "card_id": args["card_id"], "run_id": run, "expected_revision": revision}))
    assert plan("base")["plan"]["fields"]["name"]["action"] == "equal"
    remote["name"] = "Nome atualizado no site"
    assert plan("change")["plan"]["pull"] == ["name"]
    assert pull("missing")["error"] == "review_missing"
    assert pull("change", 5)["error"] == "revision_conflict"

    remote["name"] = "Outra mudan?a inesperada"
    assert pull("change")["error"] == "remote_field_changed"
    remote["name"] = "Nome atualizado no site"
    remote["open"] = False
    assert pull("change")["error"] == "remote_card_changed"
    remote["open"] = True
    remote["list_name"] = "Finalizados"
    assert pull("change")["error"] == "remote_card_changed"
    remote["list_name"] = "Quarta"

    saved = pull("change")
    assert saved["ok"] and saved["revision"] == 1
    assert saved["external_trello_writes"] == 0
    assert pull("change")["status"] == "no_changes"
    detail = datasets.get_record(tmp_path, "trello", "cards", args["card_id"])
    assert detail["record"]["name"] == "Nome atualizado no site"
    assert detail["local_revision"] == 1
    with sqlite3.connect(folder / "trello.sqlite") as conn:
        assert conn.execute("SELECT name FROM cards").fetchone()[0] == "Hermes Work"
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    remote["open"] = False
    deferred = plan("closed")
    assert deferred["plan"]["remote_open_verified"] is False
    assert pull("closed", 1)["error"] == "review_not_qualified"

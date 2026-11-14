"""One-shot title push must persist intent before browser effects and never replay."""
import json
import sqlite3

from workstation import acirv_datasets as ds
from workstation import dataset_edits
from workstation import trello_sync_push as push
from workstation.trello_sync_reconcile import compare_card, save_review

CARD = "ab" * 12
URL = "https://trello.com/c/QaBc1234/23"


def setup(tmp_path, monkeypatch, board="Hermes Sync QA"):
    monkeypatch.setattr(ds, "get_hermes_home", lambda: tmp_path)
    folder = ds.directory(tmp_path)
    folder.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(folder / "trello.sqlite") as conn:
        conn.execute("CREATE TABLE cards(id TEXT PRIMARY KEY,name TEXT,status TEXT,url TEXT,board_name TEXT)")
        conn.execute("INSERT INTO cards VALUES(?,?,?,?,?)", (CARD, "Original", "em_aberto", URL, board))
    modified = dataset_edits.update_record(
        tmp_path, "trello", "cards", CARD,
        changes={"name": "Updated from Hermes"}, expected_revision=0, actor="human")
    assert modified["revision"] == 1
    plan = compare_card(local={"name": "Updated from Hermes"}, remote={"name": "Original"},
                        baseline={"name": "Original"}, observed_fields=["name"],
                        remote_open_verified=True)
    assert plan["push"] == ["name"]
    plan.update({"native_observed": True, "browser_task_id": "qa-task", "browser_list_name": "To Do"})
    save_review(tmp_path, run_id="qa-run", card_id=CARD, source_url=URL, plan=plan)
    remote = {"url": URL, "name": "Original", "list_name": "To Do", "open": True,
              "board_name": board}
    monkeypatch.setattr(push, "verified_browser_card_title", lambda task: {**remote, "browser_task_id": task})
    return remote, folder


def test_success_has_intent_before_browser_and_receipt_plus_readback(tmp_path, monkeypatch):
    remote, folder = setup(tmp_path, monkeypatch)
    from tools import browser_workstation as browser
    calls = []
    def dispatch(action, args, **kwargs):
        calls.append(action)
        if action == "browser_snapshot":
            return json.dumps({"success": True, "snapshot": '@e9 textarea "Original" testid=card-back-title-input'})
        if action == "browser_navigate":
            assert args["url"] == URL
            return json.dumps({"success": True})
        if action == "browser_press":
            with sqlite3.connect(dataset_edits.path(tmp_path)) as c:
                assert c.execute("SELECT state FROM trello_title_push_intents").fetchone()[0] == "typed"
            return json.dumps({"success": True, "receipt": {
                "operationId": kwargs["operation_id"],
                "browserTaskId": "qa-task", "tabId": "qa-tab", "revision": 3}})
        assert action == "browser_batch_actions"
        with sqlite3.connect(dataset_edits.path(tmp_path)) as c:
            row = c.execute("SELECT state,target_title,operation_id FROM trello_title_push_intents").fetchone()
            assert row[0] == "dispatching" and row[1] == "Updated from Hermes"
            op = row[2]
        assert args["steps"] == [
            {"kind": "type", "ref": "@e9", "text": "Updated from Hermes", "clear": True,
             "anchor": {"type": "testid", "value": "card-back-title-input"}},
        ]
        assert kwargs["operation_id"] == op
        remote["name"] = row[1]
        return json.dumps({"success": True, "status": "verified", "completed_steps": 1,
                           "verified_steps": 1, "receipts": [op + ":0:a"]})
    monkeypatch.setattr(browser, "_dispatch", dispatch)
    args = {"card_id": CARD, "review_run_id": "qa-run", "expected_revision": 1,
            "browser_task_id": "qa-task"}
    result = push.push_reviewed_title(tmp_path, **args)
    assert result["status"] == "verified" and result["ok"]
    assert calls == ["browser_snapshot", "browser_batch_actions", "browser_press", "browser_navigate"]
    assert push.push_reviewed_title(tmp_path, **args)["status"] == "verified"
    assert calls == ["browser_snapshot", "browser_batch_actions", "browser_press", "browser_navigate"]
    saved = push.get_intent(tmp_path, CARD, "qa-run")
    assert saved["state"] == "verified"
    assert json.loads(saved["readback_json"])["name"] == remote["name"]
    assert len(json.loads(saved["receipts_json"])) == 2
    with sqlite3.connect(folder / "trello.sqlite") as conn:
        assert conn.execute("SELECT name FROM cards").fetchone()[0] == "Original"
    assert ds.get_record(tmp_path, "trello", "cards", CARD)["record"]["name"] == remote["name"]


def test_unknown_effect_never_retries_even_if_readback_has_target(tmp_path, monkeypatch):
    remote, _ = setup(tmp_path, monkeypatch)
    from tools import browser_workstation as browser
    calls = []
    def dispatch(action, args, **kwargs):
        calls.append(action)
        if action == "browser_snapshot":
            return json.dumps({"success": True, "snapshot": '@e9 textarea "Original" testid=card-back-title-input'})
        remote["name"] = "Updated from Hermes"
        raise RuntimeError("lost native receipt after effect")
    monkeypatch.setattr(browser, "_dispatch", dispatch)
    kwargs = {"card_id": CARD, "review_run_id": "qa-run", "expected_revision": 1,
              "browser_task_id": "qa-task"}
    assert push.push_reviewed_title(tmp_path, **kwargs)["status"] == "uncertain"
    assert push.get_intent(tmp_path, CARD, "qa-run")["failure_reason"] == "browser_result_unknown"
    assert push.push_reviewed_title(tmp_path, **kwargs)["status"] == "uncertain"
    assert calls == ["browser_snapshot", "browser_batch_actions"]


def test_refuses_production_board_and_stale_revision_without_browser(tmp_path, monkeypatch):
    remote, _ = setup(tmp_path, monkeypatch, board="ACIRV + VCOM: SCRUM")
    kwargs = {"card_id": CARD, "review_run_id": "qa-run", "expected_revision": 1,
              "browser_task_id": "qa-task"}
    assert push.push_reviewed_title(tmp_path, **kwargs)["error"] == "qa_board_only"
    with sqlite3.connect(ds.directory(tmp_path) / "trello.sqlite") as conn:
        conn.execute("UPDATE cards SET board_name='Hermes Sync QA'")
    assert push.push_reviewed_title(tmp_path, **{**kwargs, "expected_revision": 2})["error"] == "local_state_changed"
    remote["name"] = "Stale"
    assert push.push_reviewed_title(tmp_path, **kwargs)["error"] == "remote_card_changed"
    assert push.get_intent(tmp_path, CARD, "qa-run") is None


def test_unverified_receipts_hold_even_when_browser_shows_target(tmp_path, monkeypatch):
    remote, _ = setup(tmp_path, monkeypatch)
    from tools import browser_workstation as browser
    calls = []
    def dispatch(action, args, **kwargs):
        calls.append(action)
        if action == "browser_snapshot":
            return json.dumps({"success": True, "snapshot":
                '@e9 textarea "Original" testid=card-back-title-input'})
        remote["name"] = "Updated from Hermes"
        return json.dumps({"success": True, "status": "uncertain",
                           "completed_steps": 2, "verified_steps": 1,
                           "receipts": [kwargs["operation_id"] + ":0:a", None]})
    monkeypatch.setattr(browser, "_dispatch", dispatch)
    args = {"card_id": CARD, "review_run_id": "qa-run", "expected_revision": 1,
            "browser_task_id": "qa-task"}
    out = push.push_reviewed_title(tmp_path, **args)
    assert out["status"] == "uncertain"
    assert push.get_intent(tmp_path, CARD, "qa-run")["failure_reason"] == "unverified_browser_receipt"
    assert push.push_reviewed_title(tmp_path, **args)["status"] == "uncertain"
    assert calls == ["browser_snapshot", "browser_batch_actions"]


def test_forged_local_qa_label_cannot_send_to_remote_production_board(tmp_path, monkeypatch):
    remote, _ = setup(tmp_path, monkeypatch)
    remote["board_name"] = "ACIRV + VCOM: SCRUM"
    args = {"card_id": CARD, "review_run_id": "qa-run", "expected_revision": 1,
            "browser_task_id": "qa-task"}
    assert push.push_reviewed_title(tmp_path, **args)["error"] == "remote_card_changed"
    assert push.get_intent(tmp_path, CARD, "qa-run") is None

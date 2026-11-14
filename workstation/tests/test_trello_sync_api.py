"""Official Trello API QA sync: fresh permissions, durable intent and no replay."""
import json
import sqlite3
import pytest

from workstation import acirv_datasets as datasets
from workstation import dataset_edits
from workstation import trello_sync_api as api
from workstation.prefabs.trello import TrelloClient, Credential, TrelloAccessError

BOARD = api.QA_BOARD_ID
CARD = "ab" * 12
USER = "65e13416055b4548f2dbd077"
URL = "https://trello.com/c/QaBc1234/qa-test"


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(datasets, "get_hermes_home", lambda: tmp_path)
    folder = datasets.directory(tmp_path)
    folder.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(folder / "trello.sqlite") as conn:
        conn.execute(
            "CREATE TABLE cards(id TEXT PRIMARY KEY,name TEXT,status TEXT,url TEXT,"
            "board_id TEXT,board_name TEXT)")
        conn.execute(
            "INSERT INTO cards VALUES(?,?,?,?,?,?)",
            (CARD, "Initial title", "em_aberto", URL,
             "ari:cloud:trello::board/workspace/65e13ef2b939389fa44f3cf0/" + BOARD,
             "Hermes Sync QA"))
    remote = {"id": CARD, "idBoard": BOARD, "name": "Initial title",
              "closed": False, "shortUrl": "https://trello.com/c/QaBc1234"}
    ledger = []
    role = {"memberType": "admin"}

    def transport(method, path, query, form):
        ledger.append((method, path))
        if path == "/1/members/me":
            assert method == "GET"
            return {"id": USER}
        if path == f"/1/boards/{BOARD}":
            assert method == "GET"
            return {"id": BOARD, "name": "Hermes Sync QA", "closed": False}
        if path == f"/1/boards/{BOARD}/memberships":
            assert method == "GET"
            return [{"idMember": USER, "memberType": role["memberType"]}]
        if path == f"/1/cards/{CARD}" and method == "GET":
            return dict(remote)
        if path == f"/1/cards/{CARD}" and method == "PUT":
            assert form == {"name": "Updated via Trello API"}
            with sqlite3.connect(dataset_edits.path(tmp_path)) as conn:
                row = conn.execute(
                    "SELECT state,target_title,browser_task_id FROM trello_title_push_intents"
                ).fetchone()
                assert row == ("dispatching", form["name"], "api")
            remote["name"] = form["name"]
            return dict(remote)
        raise AssertionError("unexpected method or URL")
    client = TrelloClient(credential=Credential("testing-key", "testing-token"),
                          transport=transport)
    return client, remote, ledger, role, folder


def prepare(tmp_path, client):
    before = api.plan_api_title(tmp_path, client, card_id=CARD, run_id="qa-api-before")
    assert before["ok"] and before["plan"]["fields"]["name"]["action"] == "equal"
    edited = dataset_edits.update_record(
        tmp_path, "trello", "cards", CARD,
        changes={"name": "Updated via Trello API"}, expected_revision=0, actor="human")
    assert edited["revision"] == 1
    plan = api.plan_api_title(tmp_path, client, card_id=CARD, run_id="qa-api-push")
    assert plan["ok"] and plan["plan"]["push"] == ["name"]
    assert plan["external_trello_writes"] == 0
    return {"card_id": CARD, "review_run_id": "qa-api-push", "expected_revision": 1}


def test_api_title_push_happy_path_preserves_import_and_never_replays(tmp_path, monkeypatch):
    client, remote, ledger, role, folder = setup(tmp_path, monkeypatch)
    args = prepare(tmp_path, client)
    result = api.push_api_title(tmp_path, client, **args)
    assert result["ok"] and result["status"] == "verified"
    assert remote["name"] == "Updated via Trello API"
    assert sum(method == "PUT" for method, _ in ledger) == 1
    old_count = len(ledger)
    repeat = api.push_api_title(tmp_path, client, **args)
    assert repeat["ok"] and repeat["status"] == "verified"
    assert repeat["redispatched"] is False
    assert len(ledger) == old_count
    with sqlite3.connect(dataset_edits.path(tmp_path)) as conn:
        state, raw_receipts = conn.execute(
            "SELECT state,receipts_json FROM trello_title_push_intents").fetchone()
        assert state == "verified"
        assert json.loads(raw_receipts)[0]["accepted_title"] == remote["name"]
    with sqlite3.connect(folder / "trello.sqlite") as conn:
        assert conn.execute("SELECT name FROM cards").fetchone()[0] == "Initial title"
    assert datasets.get_record(tmp_path, "trello", "cards", CARD)["record"]["name"] == remote["name"]


def test_api_ambiguous_put_never_retries_even_when_remote_changed(tmp_path, monkeypatch):
    client, remote, ledger, role, _ = setup(tmp_path, monkeypatch)
    args = prepare(tmp_path, client)
    original = client._transport

    def lost_reply(method, path, query, form):
        if method == "PUT":
            ledger.append((method, path))
            remote["name"] = form["name"]
            raise TrelloAccessError("network lost after effect")
        return original(method, path, query, form)

    client._transport = lost_reply
    out = api.push_api_title(tmp_path, client, **args)
    assert out["status"] == "uncertain" and not out["ok"]
    assert out["reason"] == "api_put_result_unknown"
    put_count = sum(method == "PUT" for method, _ in ledger)
    assert put_count == 1
    assert api.push_api_title(tmp_path, client, **args)["status"] == "uncertain"
    assert sum(method == "PUT" for method, _ in ledger) == put_count


def test_admin_membership_must_be_revalidated_before_put(tmp_path, monkeypatch):
    client, remote, ledger, role, _ = setup(tmp_path, monkeypatch)
    args = prepare(tmp_path, client)
    role["memberType"] = "normal"
    with pytest.raises(TrelloAccessError):
        api.push_api_title(tmp_path, client, **args)
    assert not any(method == "PUT" for method, _ in ledger)
    assert api.get_intent(tmp_path, CARD, "qa-api-push") is None


def test_remote_title_drift_blocks_without_intent(tmp_path, monkeypatch):
    client, remote, ledger, role, _ = setup(tmp_path, monkeypatch)
    args = prepare(tmp_path, client)
    remote["name"] = "Changed by someone else"
    assert api.push_api_title(tmp_path, client, **args)["error"] == "remote_title_changed"
    assert not any(method == "PUT" for method, _ in ledger)


def test_revision_conflict_and_wrong_remote_board_fail_closed(tmp_path, monkeypatch):
    client, remote, ledger, role, _ = setup(tmp_path, monkeypatch)
    args = prepare(tmp_path, client)
    with pytest.raises(ValueError):
        api.push_api_title(tmp_path, client, **{**args, "expected_revision": 8})
    remote["idBoard"] = "f" * 24
    with pytest.raises(TrelloAccessError):
        api.push_api_title(tmp_path, client, **args)
    assert not any(method == "PUT" for method, _ in ledger)


def test_api_member_only_cannot_even_plan_write(tmp_path, monkeypatch):
    client, remote, ledger, role, _ = setup(tmp_path, monkeypatch)
    role["memberType"] = "normal"
    with pytest.raises(TrelloAccessError):
        api.plan_api_title(tmp_path, client, card_id=CARD, run_id="no-plan")
    assert not any(method == "PUT" for method, _ in ledger)


def test_api_tools_fail_closed_without_profile_secrets(monkeypatch):
    import json
    from workstation.prefabs.trello import Credential, TrelloAccessError
    from plugins.workstation_database_agent import _handle

    def missing():
        raise TrelloAccessError("do not leak credentials")
    monkeypatch.setattr(Credential, "from_secret_scope", missing)
    plan=json.loads(_handle("workstation_db_trello_api_plan",
        {"card_id":"ab"*12,"run_id":"qa-no-secret"}))
    push=json.loads(_handle("workstation_db_trello_api_push",
        {"card_id":"ab"*12,"review_run_id":"qa-no-secret","expected_revision":1}))
    for result in (plan,push):
        assert result == {"ok": False, "transport": "hold",
                          "reason": "trello_api_credentials_or_permission_unavailable"}
        assert "do not leak" not in str(result)


def test_agent_dispatch_api_plan_and_push_with_scoped_fake_transport(tmp_path,monkeypatch):
    import json
    from workstation import acirv_datasets as datasets
    from workstation import dataset_edits
    from workstation.tests.test_trello_sync_api import setup, CARD
    from workstation.prefabs import trello
    from agent.secret_scope import set_secret_scope, reset_secret_scope
    from plugins.workstation_database_agent import register

    client, remote, ledger, role, folder=setup(tmp_path,monkeypatch)
    # No real network: every call uses the fake transport of the test client.
    monkeypatch.setattr(trello.TrelloClient,"_request",
        lambda self,method,path,query=None,form=None:
          client._transport(method,path,query or {},form or {}))
    token=set_secret_scope({"TRELLO_API_KEY":"fakekey","TRELLO_TOKEN":"faketoken"},
                           profile_home=str(tmp_path))
    try:
        class Context:
            def __init__(self):
                self.tools={}
            def register_tool(self, **kw):
                self.tools[kw["name"]]=kw
        ctx=Context()
        register(ctx)
        assert "workstation_db_trello_api_plan" in ctx.tools
        def invoke(name,args):
            return json.loads(ctx.tools[name]["handler"](args))
        before=invoke("workstation_db_trello_api_plan",{
            "card_id":CARD,"run_id":"scoped-api-baseline"})
        assert "ok" in before, before
        assert before["ok"] and before["plan"]["fields"]["name"]["action"]=="equal"
        local=dataset_edits.update_record(tmp_path,"trello","cards",CARD,
            changes={"name":"Updated via Trello API"},expected_revision=0,actor="human")
        assert local["revision"]==1
        review=invoke("workstation_db_trello_api_plan",{
            "card_id":CARD,"run_id":"scoped-api-push"})
        assert review["ok"] and review["plan"]["push"]==["name"]
        args={"card_id":CARD,"review_run_id":"scoped-api-push","expected_revision":1}
        sent=invoke("workstation_db_trello_api_push",args)
        assert sent["ok"] and sent["status"]=="verified"
        assert invoke("workstation_db_trello_api_push",args)["redispatched"] is False
        assert sum(method=="PUT" for method,_ in ledger)==1
        assert remote["name"]=="Updated via Trello API"
    finally:
        reset_secret_scope(token)


def test_api_put_success_but_readback_unavailable_is_uncertain_without_retry(tmp_path,monkeypatch):
    client, remote, ledger, role, folder=setup(tmp_path,monkeypatch)
    args=prepare(tmp_path,client)
    original=client._transport
    state={"wrote":False}
    def flaky(method,path,query,form):
        if method=="PUT":
            state["wrote"]=True
            return original(method,path,query,form)
        if state["wrote"] and method=="GET" and path==f"/1/cards/{CARD}":
            raise TrelloAccessError("GET unavailable after PUT")
        return original(method,path,query,form)
    client._transport=flaky
    result=api.push_api_title(tmp_path,client,**args)
    assert result["status"]=="uncertain" and result["reason"]=="api_readback_unavailable"
    assert sum(method=="PUT" for method,_ in ledger)==1
    assert api.push_api_title(tmp_path,client,**args)["redispatched"] is False
    assert sum(method=="PUT" for method,_ in ledger)==1


def test_api_three_way_conflict_preserves_local_and_remote(tmp_path,monkeypatch):
    client,remote,ledger,role,folder=setup(tmp_path,monkeypatch)
    baseline=api.plan_api_title(tmp_path,client,card_id=CARD,run_id="qa-common")
    assert baseline["plan"]["fields"]["name"]["action"]=="equal"
    edit=dataset_edits.update_record(tmp_path,"trello","cards",CARD,
        changes={"name":"Updated via Trello API"},expected_revision=0,actor="human")
    assert edit["revision"]==1
    remote["name"]="Different human edit"
    plan=api.plan_api_title(tmp_path,client,card_id=CARD,run_id="qa-both-changed")
    assert plan["plan"]["conflicts"]==["name"] and not plan["plan"]["push"]
    result=api.push_api_title(tmp_path,client,card_id=CARD,
        review_run_id="qa-both-changed",expected_revision=1)
    assert result["error"]=="review_not_qualified"
    assert not any(method=="PUT" for method,_ in ledger)


def test_api_qa_board_identity_not_just_display_name(tmp_path,monkeypatch):
    client,remote,ledger,role,folder=setup(tmp_path,monkeypatch)
    with sqlite3.connect(folder/"trello.sqlite") as conn:
        conn.execute("UPDATE cards SET board_id=? WHERE id=?",
                     ("ari:cloud:trello::board/workspace/abc/"+"f"*24,CARD))
    with pytest.raises(ValueError,match="qa_board_only"):
        api.plan_api_title(tmp_path,client,card_id=CARD,run_id="wrong-board")
    assert ledger==[]

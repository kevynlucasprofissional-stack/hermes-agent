import sqlite3
import pytest

from workstation.business_event_outbox import install_outbox_schema, read_delivery
from workstation.business_event_dispatch import (
    AuthorizedBusinessRoute, dispatch_pending, enqueue_page_watch_occurrence
)

ORIGIN="http://127.0.0.1:8123"
EID="a"*64

def route(origin=ORIGIN):
    return AuthorizedBusinessRoute(
      route_id="fixture-local",source="page_watch",board_id="page_watch",
      event_types=frozenset({"page_changed"}),job_id="local-fixture-job",
      delivery="local",origin=origin)

def conn():
    connection=sqlite3.connect(":memory:")
    install_outbox_schema(connection)
    connection.execute("""CREATE TABLE page_watch_occurrence (
      watch_id TEXT, event_id TEXT,origin TEXT,route_id TEXT,
      previous INTEGER,current INTEGER,state TEXT,created_at TEXT)""")
    connection.execute(
      "INSERT INTO page_watch_occurrence VALUES (?,?,?,?,?,?,?,?)",
      ("watch-fixture",EID,ORIGIN,"fixture-local",1,2,"PENDING","2026-10-28 14:00:00")
    )
    connection.commit()
    return connection

def test_rejects_arbitrary_or_missing_origin():
    with pytest.raises(PermissionError):
        route("https://web.whatsapp.com")
    with pytest.raises(PermissionError):
        AuthorizedBusinessRoute("fixture-local","page_watch","page_watch",
          frozenset({"page_changed"}),"local-fixture-job")

def test_authorized_local_page_event_enters_p04_once_and_dispatches_uncertain():
    db=conn()
    assert enqueue_page_watch_occurrence(db,"watch-fixture",EID,route())
    assert not enqueue_page_watch_occurrence(db,"watch-fixture",EID,route())
    calls=[]
    def executor(job_id, prompt):
        calls.append((job_id,prompt))
        return {"claimed":True,"success":True}
    output=dispatch_pending(
      db,routes={"fixture-local":route()},
      get_job=lambda _id:{"id":"local-fixture-job","enabled":True,"deliver":"local"},
      execute=executor,
    )
    assert output["state"]=="UNCERTAIN"
    assert len(calls)==1
    assert "page_watch" in calls[0][1]
    assert "Trello" not in calls[0][1]
    assert dispatch_pending(db,routes={"fixture-local":route()},
      get_job=lambda _id:{"id":"local-fixture-job","enabled":True,"deliver":"local"},
      execute=executor) is None
    assert len(calls)==1
    assert read_delivery(db,"page_watch",EID,"fixture-local")["state"]=="UNCERTAIN"

def test_paused_job_prevents_execution():
    db=conn()
    assert enqueue_page_watch_occurrence(db,"watch-fixture",EID,route())
    outputs=[]
    result=dispatch_pending(
      db,routes={"fixture-local":route()},
      get_job=lambda _id:{"id":"local-fixture-job","enabled":False,"deliver":"local"},
      execute=lambda *_:outputs.append(1)
    )
    assert result["state"]=="FAILED_SAFE"
    assert outputs==[]

@pytest.mark.parametrize("corrupt",[
 ("origin","http://127.0.0.1:9000"),
 ("route_id","unknown"),
 ("state","UNCERTAIN"),
])
def test_source_authority_mismatch_never_enqueues(corrupt):
    db=conn()
    db.execute(f"UPDATE page_watch_occurrence SET {corrupt[0]}=?",(corrupt[1],))
    db.commit()
    with pytest.raises(PermissionError):
        enqueue_page_watch_occurrence(db,"watch-fixture",EID,route())
    assert db.execute("SELECT COUNT(*) FROM business_event_outbox").fetchone()[0]==0

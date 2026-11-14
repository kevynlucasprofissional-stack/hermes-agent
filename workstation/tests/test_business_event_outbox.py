"""P04 additional outbox regression, durable restart and route configuration."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import pytest

from workstation.business_event_outbox import (
    BusinessEventEnvelope, ClaimedEvent, claim_next, enqueue, expire_claims,
    install_outbox_schema, read_delivery, read_decisions, settle,
)
from workstation.business_event_dispatch import load_authorized_routes, with_kanban_connection


def envelope(event_id="B100:event01"):
    return BusinessEventEnvelope(
        source="trello",event_id=event_id,event_type="updateCard",
        object_id="card101",observed_at="2026-10-26T17:00:00Z",
        payload_ref="trello_activity_event:"+event_id,
    )


def new_db():
    conn=sqlite3.connect(":memory:")
    install_outbox_schema(conn)
    return conn


def test_reference_duplicate_exact_key_only():
    conn=new_db()
    assert enqueue(conn,envelope(),route_id="daily",job_id="j1")
    assert not enqueue(conn,envelope(),route_id="daily",job_id="j1")
    assert enqueue(conn,envelope(),route_id="other",job_id="j1")
    assert conn.execute("SELECT count(*) FROM business_event_outbox").fetchone()[0]==2


def test_reference_claim_no_reclaim_and_token_fence():
    conn=new_db()
    enqueue(conn,envelope(),route_id="daily",job_id="j1")
    item=claim_next(conn)
    assert item is not None and item.claim_token
    assert claim_next(conn) is None
    assert not settle(conn, ClaimedEvent(item.source,item.event_id,item.route_id,item.payload_ref,"wrong"),state="FAILED_SAFE")
    assert settle(conn,item,state="UNCERTAIN")
    assert not settle(conn,item,state="FAILED_SAFE")
    assert claim_next(conn) is None


def test_restart_keeps_pending_and_unknown_and_no_duplicate(tmp_path):
    db_path=tmp_path/"authorized-canonical.sqlite"
    with sqlite3.connect(db_path) as conn:
        install_outbox_schema(conn)
        enqueue(conn,envelope("B100:e1"),route_id="daily",job_id="j1")
        enqueue(conn,envelope("B100:e2"),route_id="daily",job_id="j1")
        first=claim_next(conn)
        assert first.event_id=="B100:e1"
        assert settle(conn,first,state="UNCERTAIN")
    with sqlite3.connect(db_path) as conn:
        install_outbox_schema(conn)
        assert not enqueue(conn,envelope("B100:e1"),route_id="daily",job_id="j1")
        second=claim_next(conn)
        assert second.event_id=="B100:e2"
        assert claim_next(conn) is None
        assert read_delivery(conn,"trello","B100:e1","daily")["attempt_count"]==1


def test_install_keeps_foreign_tasks_table_and_migration_idempotent():
    conn=sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE tasks(id TEXT PRIMARY KEY, title TEXT)")
    conn.execute("INSERT INTO tasks VALUES ('x','preserved')")
    conn.commit()
    install_outbox_schema(conn)
    install_outbox_schema(conn)
    assert conn.execute("SELECT title FROM tasks").fetchone()[0]=="preserved"
    assert conn.execute("SELECT count(*) FROM business_event_decision").fetchone()[0]==0


def test_operator_only_config_loader_and_duplicate_route_refused(tmp_path):
    home=tmp_path/"bot_profile"
    home.mkdir()
    assert load_authorized_routes(home)=={}
    yaml_text="""business_events:
  routes:
    - id: daily
      source: trello
      board_id: B100
      event_types: [updateCard]
      job_id: job-existing
      delivery: local
      enabled: true
    - id: inactive
      source: trello
      board_id: B100
      event_types: [commentCard]
      job_id: job-existing
      enabled: false
"""
    (home/"config.yaml").write_text(yaml_text,encoding="utf-8")
    routes=load_authorized_routes(home)
    assert list(routes)==["daily"] and routes["daily"].job_id=="job-existing"
    (home/"config.yaml").write_text(yaml_text.replace("id: inactive","id: daily").replace("enabled: false","enabled: true"),encoding="utf-8")
    with pytest.raises(ValueError,match="duplicate"):
        load_authorized_routes(home)


def test_external_destination_in_route_is_forbidden(tmp_path):
    home=tmp_path/"hermes"
    home.mkdir()
    (home/"config.yaml").write_text(
        "business_events:\n  routes:\n    - id: alert\n      source: trello\n"
        "      board_id: B100\n      event_types: [updateCard]\n"
        "      job_id: j\n      delivery: whatsapp\n      enabled: true\n",
        encoding="utf-8",
    )
    with pytest.raises(PermissionError):
        load_authorized_routes(home)


def test_canonical_connection_is_used_without_new_db(monkeypatch,tmp_path):
    from workstation.kanban import WorkstationKanbanBridge
    path=tmp_path/"chosen-canonical.sqlite"
    observed=[]
    def chosen(self):
        observed.append(self.board)
        return sqlite3.connect(path)
    monkeypatch.setattr(WorkstationKanbanBridge,"get_connection",chosen)
    def act(conn):
        enqueue(conn,envelope(),route_id="daily",job_id="j1")
        return read_delivery(conn,"trello","B100:event01","daily")["state"]
    assert with_kanban_connection(act,kanban_board="selected-board")=="PENDING"
    assert observed==["selected-board"]
    with sqlite3.connect(path) as conn:
        assert read_delivery(conn,"trello","B100:event01","daily")["state"]=="PENDING"


def test_decision_audit_contains_no_trello_raw_text():
    conn=new_db()
    enqueue(conn,envelope(),route_id="daily",job_id="j1")
    item=claim_next(conn)
    settle(conn,item,state="UNCERTAIN")
    decisions=read_decisions(conn,source="trello",event_id="B100:event01")
    assert [v["decision"] for v in decisions]==["ENQUEUED","CLAIM_ACQUIRED","SETTLED_UNCERTAIN"]
    assert "desc" not in json.dumps(decisions)


def test_no_random_business_id_allows_source_stable_identity():
    with pytest.raises(ValueError):
        BusinessEventEnvelope(source="trello",event_id="",event_type="updateCard",
                              object_id="card101",observed_at="2026-10-26T17:00:00Z",
                              payload_ref="trello_activity_event:B100:one")


def test_uncertain_requires_independent_receipt_before_reconciliation():
    from workstation.business_event_outbox import reconcile_uncertain
    conn=new_db()
    enqueue(conn,envelope(),route_id="daily",job_id="j1")
    item=claim_next(conn)
    assert settle(conn,item,state="UNCERTAIN")
    with pytest.raises(ValueError,match="independent"):
        reconcile_uncertain(conn,source="trello",event_id="B100:event01",
                            route_id="daily",state="DELIVERED",
                            evidence_ref="",independent_verifier=None)
    with pytest.raises(ValueError,match="rejected"):
        reconcile_uncertain(conn,source="trello",event_id="B100:event01",
                            route_id="daily",state="DELIVERED",
                            evidence_ref="receipt:123",independent_verifier=lambda *args: False)
    calls=[]
    def independent(row,state,receipt):
        calls.append((row["event_id"],state,receipt))
        return row["event_id"] == "B100:event01" and receipt == "receipt:123"
    assert reconcile_uncertain(conn,source="trello",event_id="B100:event01",
                                route_id="daily",state="DELIVERED",
                                evidence_ref="receipt:123",independent_verifier=independent)
    assert calls == [("B100:event01","DELIVERED","receipt:123")]
    assert claim_next(conn) is None
    assert read_delivery(conn,"trello","B100:event01","daily")["state"]=="DELIVERED"
    assert not reconcile_uncertain(conn,source="trello",event_id="B100:event01",
                                   route_id="daily",state="DELIVERED",
                                   evidence_ref="receipt:123",independent_verifier=independent)


def test_stale_claim_migration_not_auto_retry_and_explicit_no_effect_proof():
    from workstation.business_event_outbox import reconcile_uncertain
    conn=new_db()
    enqueue(conn,envelope(),route_id="daily",job_id="j1")
    when=datetime(2026,10,26,tzinfo=timezone.utc)
    item=claim_next(conn,now=when,lease_seconds=1)
    assert expire_claims(conn,now=when.replace(minute=1))==1
    assert claim_next(conn) is None
    assert reconcile_uncertain(conn,source="trello",event_id="B100:event01",
                               route_id="daily",state="FAILED_SAFE",
                               evidence_ref="audit:no_effect",
                               independent_verifier=lambda row,state,ref: True)
    assert read_delivery(conn,"trello","B100:event01","daily")["state"]=="FAILED_SAFE"
    assert read_delivery(conn,"trello","B100:event01","daily")["attempt_count"]==1

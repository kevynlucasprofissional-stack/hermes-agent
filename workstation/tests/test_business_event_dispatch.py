"""P04: RED/GREEN tests for durable authorized outbox and conservative Cron effects."""
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from workstation.business_event_outbox import (
    BusinessEventEnvelope, install_outbox_schema, enqueue, claim_next,
    settle, expire_claims, read_delivery, read_decisions, ClaimedEvent,
)
from workstation.business_event_dispatch import (
    AuthorizedBusinessRoute, enqueue_trello_journal_action, dispatch_pending,
    dispatch_authorized_event,
)
from workstation.trello_action_journal import install_schema as install_trello_schema, append_batch


def fixture_conn():
    conn = sqlite3.connect(":memory:")
    install_trello_schema(conn)
    install_outbox_schema(conn)
    return conn


def action(n="a1", kind="updateCard", board="B123"):
    return {"id": n, "type": kind, "date": "2026-10-26T13:14:00Z",
            "idMemberCreator": "actor22",
            "data": {"card": {"id": "card22", "name": "CONFIDENTIAL_TITLE"},
                     "text": "SECRET_COMMENT"}}


def route(job="job-123", board="B123"):
    return AuthorizedBusinessRoute(
        route_id="trello-daily", source="trello", board_id=board,
        event_types=frozenset(("updateCard",)), job_id=job, delivery="local",
    )


def example_envelope():
    return BusinessEventEnvelope(
        source="trello", event_id="B123:a1", event_type="updateCard",
        object_id="card22", observed_at="2026-10-26T13:14:00.000Z",
        payload_ref="trello_activity_event:B123:a1",
    )


def trusted_job(ident="job-123"):
    return {"id": ident, "name": "[bot:trello-relator] Trello", "enabled": True,
            "deliver": "local", "no_agent": False}


def test_duplicate_envelope_and_route_only_once():
    conn = fixture_conn()
    assert enqueue(conn, example_envelope(), route_id="trello-daily", job_id="job-123")
    assert not enqueue(conn, example_envelope(), route_id="trello-daily", job_id="job-123")
    assert len(read_decisions(conn, source="trello", event_id="B123:a1")) >= 1
    assert read_delivery(conn, "trello", "B123:a1", "trello-daily")["state"] == "PENDING"


def test_conflicting_duplicate_payload_is_rejected():
    conn = fixture_conn()
    enqueue(conn, example_envelope(), route_id="trello-daily", job_id="job-123")
    with pytest.raises(ValueError, match="conflict"):
        enqueue(conn, replace(example_envelope(), payload_ref="trello_activity_event:B123:different"),
                route_id="trello-daily", job_id="job-123")
    with pytest.raises(ValueError, match="conflict"):
        enqueue(conn, example_envelope(), route_id="trello-daily", job_id="other-job")


def test_two_workers_share_one_claim_and_no_double_dispatch(tmp_path):
    filename = tmp_path / "canonical-test.sqlite"
    with sqlite3.connect(filename) as init:
        install_outbox_schema(init)
        enqueue(init, example_envelope(), route_id="trello-daily", job_id="job-123")
    def worker(_):
        with sqlite3.connect(filename, timeout=5) as conn:
            return claim_next(conn, route_id="trello-daily")
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(worker, range(2)))
    assert sum(claim is not None for claim in claims) == 1
    with sqlite3.connect(filename) as conn:
        delivery = read_delivery(conn, "trello", "B123:a1", "trello-daily")
        assert delivery["state"] == "CLAIMED" and delivery["attempt_count"] == 1


def test_crash_after_claim_becomes_uncertain_and_is_never_requeued():
    conn = fixture_conn()
    enqueue(conn, example_envelope(), route_id="trello-daily", job_id="job-123")
    now = datetime(2026, 10, 27, tzinfo=timezone.utc)
    claim = claim_next(conn, route_id="trello-daily", now=now, lease_seconds=30)
    assert claim is not None
    assert expire_claims(conn, now=now + timedelta(seconds=31)) == 1
    assert read_delivery(conn, "trello", "B123:a1", "trello-daily")["state"] == "UNCERTAIN"
    assert claim_next(conn, route_id="trello-daily", now=now + timedelta(hours=1)) is None
    with pytest.raises(ValueError, match="independent"):
        settle(conn, claim, state="DELIVERED", evidence_ref="fake")
    assert not settle(conn, claim, state="FAILED_SAFE")


def test_source_not_authorized_never_enqueue_or_dispatch():
    conn = fixture_conn()
    append_batch(conn, "B123", [action("a1")])
    with pytest.raises(PermissionError):
        enqueue_trello_journal_action(conn, "B123", "a1", replace(route(), source="fake"))
    assert conn.execute("SELECT COUNT(*) FROM business_event_outbox").fetchone()[0] == 0


def test_wrong_board_action_type_and_missing_journal_never_enqueue():
    conn = fixture_conn()
    append_batch(conn, "B123", [action("a1"), action("a2", kind="commentCard")])
    for board, id_ in (("WRONG", "a1"), ("B123", "a2"), ("B123", "missing")):
        with pytest.raises((PermissionError, LookupError)):
            enqueue_trello_journal_action(conn, board, id_, route())
    assert conn.execute("SELECT COUNT(*) FROM business_event_outbox").fetchone()[0] == 0


def test_trello_to_journal_to_dispatch_fake_cron_single_invocation():
    conn = fixture_conn()
    append_batch(conn, "B123", [action("a1")])
    assert enqueue_trello_journal_action(conn, "B123", "a1", route())
    assert not enqueue_trello_journal_action(conn, "B123", "a1", route())
    invoked = []
    def fake_execute(job_id, extra_prompt):
        invoked.append((job_id, extra_prompt))
        return {"claimed": True, "success": True}
    first = dispatch_pending(conn, routes={"trello-daily": route()},
                             get_job=trusted_job, execute=fake_execute)
    assert first["state"] == "UNCERTAIN", first
    assert len(invoked) == 1 and invoked[0][0] == "job-123"
    assert "[B123:a1]" in invoked[0][1]
    assert "SECRET" not in invoked[0][1]
    assert "CONFIDENTIAL" not in invoked[0][1]
    assert dispatch_pending(conn, routes={"trello-daily": route()},
                            get_job=trusted_job, execute=fake_execute) is None
    assert len(invoked) == 1


def test_missing_job_preflight_is_failed_safe_without_invoking_cron():
    conn = fixture_conn()
    append_batch(conn, "B123", [action("a1")])
    enqueue_trello_journal_action(conn, "B123", "a1", route())
    invoked = []
    result = dispatch_pending(conn, routes={"trello-daily": route()},
                              get_job=lambda _: None,
                              execute=lambda *args: invoked.append(args))
    assert result["state"] == "FAILED_SAFE"
    assert invoked == []
    assert dispatch_pending(conn, routes={"trello-daily": route()},
                            get_job=lambda _: None, execute=lambda *args: invoked.append(args)) is None


def test_paused_or_external_delivery_job_does_not_fire():
    for job in (dict(trusted_job(), enabled=False), dict(trusted_job(), deliver="whatsapp")):
        conn = fixture_conn()
        enqueue(conn, example_envelope(), route_id="trello-daily", job_id="job-123")
        calls = []
        result = dispatch_pending(conn, routes={"trello-daily": route()},
                                  get_job=lambda _: job,
                                  execute=lambda *args: calls.append(args))
        assert result["state"] == "FAILED_SAFE" and not calls


def test_exception_after_cron_invocation_is_uncertain_never_retry():
    conn = fixture_conn()
    enqueue(conn, example_envelope(), route_id="trello-daily", job_id="job-123")
    called = []
    def maybe_effect(*args):
        called.append(1)
        raise RuntimeError("network transport unknown")
    result = dispatch_pending(conn, routes={"trello-daily": route()},
                              get_job=trusted_job, execute=maybe_effect)
    assert result["state"] == "UNCERTAIN"
    assert dispatch_pending(conn, routes={"trello-daily": route()},
                            get_job=trusted_job, execute=maybe_effect) is None
    assert len(called) == 1


def test_no_route_approval_is_failed_safe_not_dispatched():
    conn = fixture_conn()
    enqueue(conn, example_envelope(), route_id="trello-daily", job_id="job-123")
    calls = []
    result = dispatch_pending(conn, routes={}, get_job=trusted_job,
                              execute=lambda *args: calls.append(args))
    assert result is None and calls == []
    assert read_delivery(conn, "trello", "B123:a1", "trello-daily")["state"] == "PENDING"


def test_settle_requires_claim_token_and_independent_delivery_evidence():
    conn = fixture_conn()
    enqueue(conn, example_envelope(), route_id="trello-daily", job_id="job-123")
    claim = claim_next(conn, route_id="trello-daily")
    forged = replace(claim, claim_token="wrong")
    assert not settle(conn, forged, state="FAILED_SAFE")
    with pytest.raises(ValueError, match="independent"):
        settle(conn, claim, state="DELIVERED")
    assert settle(conn, claim, state="UNCERTAIN")
    assert not settle(conn, claim, state="FAILED_SAFE")


def test_legacy_reference_schema_migrates_additively_without_touching_tasks():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO tasks VALUES ('keep')")
    conn.commit()
    # Reference P04 schema has fewer columns than complete implementation.
    conn.executescript("""CREATE TABLE business_event_outbox (
       source TEXT NOT NULL, event_id TEXT NOT NULL, route_id TEXT NOT NULL,
       payload_ref TEXT NOT NULL,
       state TEXT NOT NULL, claim_token TEXT, attempt_count INTEGER NOT NULL DEFAULT 0,
       created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
       updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
       PRIMARY KEY(source,event_id,route_id));""")
    install_outbox_schema(conn)
    install_outbox_schema(conn)
    assert conn.execute("SELECT id FROM tasks").fetchone()[0] == "keep"
    assert "event_type" in {row[1] for row in conn.execute("PRAGMA table_info(business_event_outbox)")}
    assert enqueue(conn, example_envelope(), route_id="trello-daily", job_id="job-123")


def test_rollback_on_sql_failure_does_not_leave_fake_decision():
    conn = fixture_conn()
    conn.executescript("""CREATE TRIGGER reject_outbox BEFORE INSERT ON business_event_outbox
      BEGIN SELECT RAISE(ABORT,'denied'); END;""")
    with pytest.raises(sqlite3.DatabaseError):
        enqueue(conn, example_envelope(), route_id="trello-daily", job_id="job-123")
    assert conn.execute("SELECT COUNT(*) FROM business_event_decision").fetchone()[0] == 0


def test_two_concurrent_dispatchers_run_one_fake_cron_call(tmp_path):
    filename=tmp_path/"canonical-concurrent.sqlite"
    with sqlite3.connect(filename) as conn:
        install_trello_schema(conn)
        install_outbox_schema(conn)
        append_batch(conn,"B123",[action("a1")])
        enqueue_trello_journal_action(conn,"B123","a1",route())
    fired=[]
    lock=threading.Lock()
    def fake_execute(job_id,prompt):
        with lock:
            fired.append(job_id)
        return {"claimed":True,"success":True}
    def worker(_):
        with sqlite3.connect(filename,timeout=5) as conn:
            return dispatch_pending(conn,routes={"trello-daily":route()},
                                    get_job=trusted_job,execute=fake_execute)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(worker,(0,1)))
    assert len(fired)==1
    assert sum(result is not None for result in outcomes)==1
    with sqlite3.connect(filename) as conn:
        row=read_delivery(conn,"trello","B123:a1","trello-daily")
        assert row["state"]=="UNCERTAIN" and row["attempt_count"]==1


def test_existing_hermes_cron_registry_is_used_without_scheduling_or_delivery(tmp_path):
    from cron import jobs
    conn=fixture_conn()
    append_batch(conn,"B123",[action("a1")])
    home=tmp_path/"isolated-bot"
    home.mkdir()
    with jobs.use_cron_store(home):
        cron_job=jobs.create_job(
            prompt="TEST_ONLY",name="[bot:test] Fixture",
            schedule="every 1h",deliver="local",model="fixture-model",
        )
        approved=route(job=cron_job["id"])
        assert enqueue_trello_journal_action(conn,"B123","a1",approved)
        fired=[]
        outcome=dispatch_pending(
            conn,routes={approved.route_id:approved},
            execute=lambda id,prompt: (fired.append(id) or {"claimed":True,"success":True}),
        )
        assert outcome["state"]=="UNCERTAIN"
        assert fired==[cron_job["id"]]
        assert jobs.get_job(cron_job["id"])["deliver"]=="local"
        assert jobs.get_job(cron_job["id"])["enabled"] is True
        assert jobs.get_job(cron_job["id"])["last_run_at"] is None


def test_dispatcher_never_claims_foreign_route_and_empty_permissions_do_nothing():
    conn=fixture_conn()
    append_batch(conn,"B123",[action("a1")])
    original=example_envelope()
    enqueue(conn,original,route_id="foreign-route",job_id="foreign-job")
    assert dispatch_pending(conn,routes={},get_job=trusted_job,execute=lambda *args: (_ for _ in ()).throw(AssertionError)) is None
    assert read_delivery(conn,"trello","B123:a1","foreign-route")["state"]=="PENDING"
    assert enqueue_trello_journal_action(conn,"B123","a1",route())
    calls=[]
    result=dispatch_pending(conn,routes={"trello-daily":route()},get_job=trusted_job,
                            execute=lambda *args: (calls.append(args) or {"claimed":True,"success":True}))
    assert result["state"]=="UNCERTAIN" and len(calls)==1
    assert read_delivery(conn,"trello","B123:a1","foreign-route")["state"]=="PENDING"


def test_lease_reconciliation_scoped_to_authorized_route_only():
    conn=fixture_conn()
    enqueue(conn,example_envelope(),route_id="foreign-route",job_id="foreign-job")
    old=datetime(2026,10,26,tzinfo=timezone.utc)
    foreign=claim_next(conn,route_id="foreign-route",now=old,lease_seconds=1)
    assert foreign is not None
    append_batch(conn,"B123",[action("a1")])
    enqueue_trello_journal_action(conn,"B123","a1",route())
    result=dispatch_pending(conn,routes={"trello-daily":route()},
                            get_job=trusted_job,
                            execute=lambda *args: {"claimed":True,"success":True})
    assert result["state"]=="UNCERTAIN"
    assert read_delivery(conn,"trello","B123:a1","foreign-route")["state"]=="CLAIMED"
    assert expire_claims(conn,now=old+timedelta(seconds=2),route_id="foreign-route")==1
    assert read_delivery(conn,"trello","B123:a1","foreign-route")["state"]=="UNCERTAIN"

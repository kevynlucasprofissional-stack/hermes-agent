"""P06-R offline reference proofs. Never opens Hermes production SQLite."""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import sqlite3
from pathlib import Path

import pytest

SPEC=importlib.util.spec_from_file_location("p06r_sequence_ledger",Path(__file__).with_name("sequence_ledger.py"))
assert SPEC is not None and SPEC.loader is not None
import sys
module=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=module
SPEC.loader.exec_module(module)


def conn(path=":memory:"):
    connection=sqlite3.connect(path,timeout=5)
    module.migrate(connection)
    return connection


def take(connection,activation="activation1",key="domrevision1",previous=1,current=2):
    return module.reserve(connection,watch_id="watch1",activation_key=activation,
                          observation_key=key,route_id="route1",
                          previous=previous,current=current)


def test_replay_one_event_stable():
    with conn() as db:
        a=take(db)
        b=take(db)
        assert a==b
        assert a.sequence==1 and len(a.event_id)==64
        assert len(module.pending(db,"watch1"))==1


def test_independent_equal_transition_after_restart_has_different_id(tmp_path):
    path=tmp_path/"canonical-test.sqlite"
    with conn(path) as db:
        first=take(db)
    with conn(path) as db:
        second=take(db,activation="activation2")
        assert first.event_id!=second.event_id
        assert [first.sequence,second.sequence]==[1,2]
        assert len(module.pending(db,"watch1"))==2


def test_distinct_observation_with_same_transition_in_one_activation():
    with conn() as db:
        first=take(db,key="revision1")
        second=take(db,key="revision2")
        assert first.event_id!=second.event_id


def test_two_workers_same_observation_only_one_record(tmp_path):
    path=tmp_path/"canonical.sqlite"
    with conn(path):pass
    def worker(_):
        db=sqlite3.connect(path,timeout=5)
        try: return take(db)
        finally: db.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a,b=pool.map(worker,range(2))
    assert a==b
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM p06_watch_occurrence").fetchone()[0]==1


def test_two_workers_separate_occurrences_not_suppressed(tmp_path):
    path=tmp_path/"canonical.sqlite"
    with conn(path):pass
    def worker(n):
        db=sqlite3.connect(path,timeout=5)
        try:return take(db,activation=f"activation{n}")
        finally:db.close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        a,b=pool.map(worker,(1,2))
    assert a.sequence!=b.sequence
    assert a.event_id!=b.event_id


def test_crash_after_commit_before_publish_keeps_pending(tmp_path):
    path=tmp_path/"canonical.sqlite"
    db=conn(path)
    old=take(db)
    db.close() # Simulate process death between acceptance and publish
    with conn(path) as reopened:
        assert module.pending(reopened,"watch1")[0]==old
        assert take(reopened)==old
        with pytest.raises(PermissionError):
            module.ack_outbox(reopened,old.event_id,independent_receipt=False)
        assert module.ack_outbox(reopened,old.event_id,independent_receipt=True)
        assert module.pending(reopened,"watch1")==[]
        assert not module.ack_outbox(reopened,old.event_id,independent_receipt=True)


def test_conflicting_replay_denied_and_does_not_consume_seq():
    with conn() as db:
        first=take(db)
        with pytest.raises(ValueError,match="conflicting"):
            take(db,current=3)
        second=take(db,key="revision2")
        assert second.sequence==first.sequence+1


def test_bad_event_identity_and_noop_rejected():
    with conn() as db:
        with pytest.raises(ValueError):
            take(db,activation="../secret")
        with pytest.raises(ValueError):
            take(db,previous=2,current=2)


def test_schema_additive_and_tasks_preserved(tmp_path):
    path=tmp_path/"canonical.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY)")
        db.execute("INSERT INTO tasks VALUES ('keep')")
        db.commit()
    with conn(path) as db:
        module.migrate(db)
        assert db.execute("SELECT id FROM tasks").fetchone()[0]=="keep"
        assert take(db).state=="PENDING"

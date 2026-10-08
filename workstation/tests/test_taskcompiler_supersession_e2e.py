"""Real compiler/SQLite continuation, including uncertain-effect readback."""
from collections import Counter

import pytest

from hermes_cli import kanban_db, kanban_db_connect
from tools.registry import registry
from tools.effects import ToolEffect
from workstation.artifacts import ArtifactStore
from workstation.durable_tasks import DurableTaskStore
from workstation.task_compiler import TaskCompiler


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setattr(registry, "_tools", dict(registry._tools))
    for name, effect in (("test_write", ToolEffect.MUTATION), ("test_readback", ToolEffect.PURE_READ)):
        registry.register(name, "test", {"name": name}, lambda **kw: {}, effect=effect)
    conn = kanban_db_connect.connect(tmp_path / "kanban.db")
    task = kanban_db.create_task(conn, title="continuation", session_id="session")
    claimed = kanban_db.claim_task(conn, task, claimer="worker-a")
    assert claimed.current_run_id == 1
    compiler = TaskCompiler(DurableTaskStore(conn=conn), ArtifactStore(tmp_path / "artifacts"))
    compiler.canonical_run_id = "1"
    request = {"operation_key": "resume", "items": [{"id": n} for n in range(3)], "steps": [
        {"id": "write", "tool": "test_write", "args": {"id": "$item.id"}, "expect": {"ok": True}},
        {"id": "readback", "tool": "test_readback", "verifies": ["write"], "args": {"id": "$item.id"}, "expect": {"id": "$item.id"}},
    ]}
    return compiler, conn, task, request


def supersede(conn, task):
    assert kanban_db.reclaim_task(conn, task)
    claimed = kanban_db.claim_task(conn, task, claimer="worker-b")
    assert claimed.current_run_id == 2


def test_compiler_supersession_resume_uncertain_without_duplicate(runtime):
    compiler, conn, task, request = runtime
    writes, reads = Counter(), Counter()
    def dispatch(name, args, *_):
        item = args["id"]
        if name == "test_readback":
            reads[item] += 1
            return {"id": item}
        writes[item] += 1
        if item == 1:
            supersede(conn, task)
            raise OSError("ack lost after effect")
        return {"ok": True}
    first = compiler.execute(request, task_id=task, canonical_task_id=task, session_id="session", dispatch=dispatch)
    assert writes == {0: 1, 1: 1}
    plan = compiler.store.get_plan(first["plan_id"])
    assert compiler.store.outstanding_uncertain_mutations(plan.id)
    stale = compiler.resume(plan.id, session_id="session", dispatch=dispatch)
    assert stale["status"] == "AUTHORITY_SUPERSEDED" and writes == {0: 1, 1: 1}
    compiler.canonical_run_id = "2"
    resumed = compiler.resume(plan.id, session_id="session", dispatch=dispatch)
    assert resumed["completed"] == 3, [(i.input_payload, i.status.value, i.validation_result) for i in compiler.store.get_work_items(plan.id)]
    assert writes == {0: 1, 1: 1, 2: 1}
    assert reads[1] >= 1
    items = compiler.store.get_work_items(plan.id)
    assert items[0].run_id == "1"  # confirmed lineage is preserved
    assert all(i.run_id == "2" for i in items[1:])
    assert items[1].checkpoints["step_0_meta"]["reconciled"]
    checkpoint = compiler.store.get_plan(plan.id).metadata["supersession"]
    assert compiler.artifacts.read_json(checkpoint["checkpoint_ref"])["results"]
    assert checkpoint["uncertain_effects"]
    compiler.canonical_run_id = "1"
    assert compiler.resume(plan.id, session_id="session", dispatch=lambda *a: pytest.fail("stale invocation"))["status"] == "AUTHORITY_SUPERSEDED"


def test_uncertain_readback_failure_never_redispatches(runtime):
    compiler, conn, task, request = runtime
    def lose_ack(name, args, *_):
        if name == "test_write":
            supersede(conn, task)
            raise OSError("unknown effect")
        return {"id": args["id"]}
    first = compiler.execute(request, task_id=task, session_id="session", dispatch=lose_ack)
    compiler.canonical_run_id = "2"
    reads = []
    def read_only(name, args, *_):
        assert name == "test_readback"
        reads.append(args)
        return {"id": "unconfirmed"}
    result = compiler.resume(first["plan_id"], session_id="session", dispatch=read_only)
    assert reads and result["completed"] == 0
    assert compiler.store.outstanding_uncertain_mutations(first["plan_id"])


def test_adoption_does_not_lend_authority_to_running_old_worker(runtime):
    compiler, conn, task, request = runtime
    writes = []
    def dispatch(name, args, *_):
        if name == "test_readback":
            return {"id": args["id"]}
        writes.append(args["id"])
        if args["id"] == 0:
            supersede(conn, task)
            conn.execute("UPDATE work_plans SET run_id='2'")
            conn.commit()
        return {"ok": True}
    result = compiler.execute(request, task_id=task, session_id="session", dispatch=dispatch)
    assert writes == [0]
    assert result["completed"] == 1


@pytest.mark.parametrize("status", ["cancelled", "revoked", "policy_revoked"])
def test_compiler_nonresumable_termination(runtime, status):
    compiler, conn, task, request = runtime
    def interrupt(name, args, *_):
        if name == "test_write":
            supersede(conn, task)
        return {"ok": True, "id": args["id"]}
    first = compiler.execute(request, task_id=task, session_id="session", dispatch=interrupt)
    # Status classification uses the canonical owner; no synthetic authority is granted.
    conn.execute("UPDATE tasks SET status=? WHERE id=?", (status, task))
    conn.commit()
    compiler.canonical_run_id = "2"
    result = compiler.resume(first["plan_id"], session_id="session", dispatch=lambda *a: pytest.fail("must not dispatch"))
    assert not result["dispatched"]
    assert not result["authority_superseded"]["continuation_allowed"]


@pytest.mark.parametrize("cause", ["CANCELLED", "REVOKED_BY_USER", "POLICY_REVOKED"])
def test_old_run_termination_survives_new_canonical_claim(runtime, cause):
    compiler, conn, task, request = runtime
    def dispatch(name, args, *_):
        if name == "test_write":
            supersede(conn, task)
            raise OSError("uncertain old run")
        return {"id": args["id"]}
    first = compiler.execute(request, task_id=task, session_id="session", dispatch=dispatch)
    conn.execute("UPDATE task_runs SET outcome=? WHERE id=1", (cause,))
    conn.commit()
    assert kanban_db.get_task(conn, task).status == "running"
    compiler.canonical_run_id = "2"
    result = compiler.resume(first["plan_id"], session_id="session", dispatch=lambda *a: pytest.fail("terminated work dispatched"))
    assert result["status"] == cause and not result["dispatched"]
    assert not result["authority_superseded"]["continuation_allowed"]
    assert compiler.store.get_plan(first["plan_id"]).run_id == "1"


def test_cancelled_durable_plan_cannot_be_adopted(runtime):
    compiler, conn, task, request = runtime
    def dispatch(name, args, *_):
        if name == "test_write":
            supersede(conn, task)
            raise OSError("uncertain effect")
        return {"id": args["id"]}
    first = compiler.execute(request, task_id=task, session_id="session", dispatch=dispatch)
    compiler.store.update_plan_state(first["plan_id"], "cancelled")
    compiler.canonical_run_id = "2"
    result = compiler.resume(first["plan_id"], session_id="session", dispatch=lambda *a: pytest.fail("cancelled plan dispatched"))
    assert result["status"] == "CANCELLED" and not result["dispatched"]
    assert compiler.store.get_plan(first["plan_id"]).status == "cancelled"
    with pytest.raises(PermissionError, match="cancelled_plan_not_resumable"):
        compiler.store.adopt_superseded_plan(first["plan_id"], canonical_task_id=task, new_run_id="2", checkpoint={})

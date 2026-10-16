"""OL-MVP: safe batch boundary allows an authorized in-flight adopter to finish next items.

This is a STORE RECONCILIATION unit test, not proof of browser readback or DIRECT admission.
"""
from __future__ import annotations

from uuid import uuid4

from hermes_cli.kanban_db_boards import create_board

from workstation.artifacts import ArtifactStore
from workstation.batch_runner import DurableBatchRunner
from workstation.durable_tasks import DurableTaskStore, WorkItemStatus


def _runner(tmp_path):
    board = "ol_mvp_" + uuid4().hex[:12]
    create_board(board)
    store = DurableTaskStore(board=board)
    artifacts = ArtifactStore(root_dir=tmp_path / "artifacts")
    runner = DurableBatchRunner(
        "ol_mvp_task_" + uuid4().hex[:12],
        task_store=store,
        artifact_store=artifacts,
        max_retries=0,
        backoff_seconds=0,
    )
    return runner, store, artifacts


def test_safe_boundary_refreshes_work_item_state_after_external_completion(tmp_path):
    runner, store, artifacts = _runner(tmp_path)
    dispatched = []
    boundaries = []

    def worker(payload, _item):
        dispatched.append(payload["item_id"])
        return {"item_id": payload["item_id"]}

    def boundary(completed_item):
        boundaries.append(completed_item.input_payload["item_id"])
        if completed_item.input_payload["item_id"] != 1:
            return
        plan = store.get_plan(runner.task_id)
        item2 = store.get_work_items(plan.id)[1]
        assert item2.status == WorkItemStatus.PENDING
        # Simulate a SEPARATELY VERIFIED adopter completing the next item.
        # This test proves only that the runner must not execute the stale item twice.
        store.update_item_checkpoint(item2.id, "navigate", "ok")
        store.update_item_checkpoint(item2.id, "ready", "ok")
        output = {"item_id": 2}
        raw = artifacts.store(task_id=runner.task_id, name="adopter_raw_2.json",
                              content=output, schema="raw_batch_capture",
                              summary={"output_type": "dict"})
        store.mark_item_captured(item2.id, raw.ref)
        normalized = artifacts.store(task_id=runner.task_id, name="adopter_norm_2.json",
                                     content=output, schema="normalized_batch_output")
        store.mark_item_persisted(item2.id, normalized.ref)
        store.record_evidence(item2.id, normalized.ref)
        store.mark_item_validated(item2.id, {"valid": True, "suspect": False})
        store.complete_item(item2.id)

    summary = runner.execute_batch(
        "three items",
        [{"item_id": 1}, {"item_id": 2}, {"item_id": 3}],
        worker_fn=worker,
        on_safe_item_boundary=boundary,
    )
    assert dispatched == [1, 3], "item 2 was already completed via another authorized path"
    assert boundaries == [1, 3]
    assert summary.total_items == 3
    assert summary.success_count == 3
    assert all(i.status == WorkItemStatus.COMPLETED
               for i in store.get_work_items(summary.plan_id))


def test_learning_callback_failure_never_blocks_primary_task(tmp_path, caplog):
    runner, _, _ = _runner(tmp_path)
    dispatched = []

    def worker(payload, _item):
        dispatched.append(payload["item_id"])
        return {"item_id": payload["item_id"]}

    def broken_callback(_item):
        raise RuntimeError("learning worker unavailable")

    summary = runner.execute_batch(
        "three items",
        [{"item_id": 1}, {"item_id": 2}, {"item_id": 3}],
        worker_fn=worker,
        on_safe_item_boundary=broken_callback,
    )
    assert dispatched == [1, 2, 3]
    assert summary.success_count == 3
    assert "Optional run-local learning checkpoint failed" in caplog.text


def test_default_batch_behavior_is_unchanged(tmp_path):
    runner, _, _ = _runner(tmp_path)
    dispatched = []
    summary = runner.execute_batch(
        "two items",
        [{"item_id": 1}, {"item_id": 2}],
        worker_fn=lambda payload, _item: dispatched.append(payload["item_id"]) or payload,
    )
    assert dispatched == [1, 2]
    assert summary.success_count == 2

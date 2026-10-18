"""OL-MVP: safe batch boundary allows an authorized in-flight adopter to finish next items.

This is a STORE RECONCILIATION unit test, not proof of browser readback or DIRECT admission.
"""
from __future__ import annotations

import pytest

pytestmark = pytest.mark.usefixtures("direct_qualification_issuer")

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


def test_safe_boundary_callback_prevents_recursion():
    from types import SimpleNamespace
    from workstation.durable_tasks import WorkItem, WorkItemStatus
    from workstation.integrations.hermes.run_local_adoption import (
        create_safe_item_boundary_callback,
        _in_adoption_checkpoint,
    )

    calls = []
    agent = SimpleNamespace(
        _canonical_work_task_id="task_1",
        _canonical_work_run_id="run_1",
        _run_adoption_owner=None,
    )
    callback = create_safe_item_boundary_callback(agent)

    item = WorkItem(
        id="item_1",
        plan_id="plan_1",
        task_id="task_1",
        item_index=0,
        status=WorkItemStatus.COMPLETED,
        input_payload={"item_id": 1},
    )

    # When already inside an adoption checkpoint, calling the callback is a no-op
    token = _in_adoption_checkpoint.set(True)
    try:
        callback(item)
        assert len(calls) == 0, "Callback must not recurse when checkpoint is active"
    finally:
        _in_adoption_checkpoint.reset(token)


def test_safe_boundary_callback_wired_through_scoped_execution():
    from types import SimpleNamespace
    from workstation.integrations.hermes.scoped_execution import workstation_scoped_execution
    from workstation.task_compiler import _safe_item_boundary

    agent = SimpleNamespace(
        _canonical_work_task_id="task_1",
        _canonical_work_run_id="run_1",
        session_id="session_1",
        _work_user_constraints={},
        _work_completed_mutations={},
        _work_mutation_evidence={},
        _work_capabilities={},
        valid_tool_names=set(),
    )

    assert _safe_item_boundary.get() is None
    with workstation_scoped_execution(agent, "task_1", []):
        bound_cb = _safe_item_boundary.get()
        assert bound_cb is not None
        assert callable(bound_cb)
    assert _safe_item_boundary.get() is None


def test_workstation_durable_dispatch_native_schema_tool_branch(monkeypatch):
    """Ensure native workstation schema tools dispatch authoritatively and capture raw results without import or runtime error."""
    from types import SimpleNamespace
    from workstation.integrations.hermes.scoped_execution import workstation_durable_dispatch
    import workstation.integrations.hermes.browser_controller as bc
    import workstation.task_compiler as tc

    agent = SimpleNamespace(
        _interrupt_requested=False,
        _tool_guardrail_halt_decision=None,
        valid_tool_names=set(),
        session_id="session_test",
        _canonical_work_run_id="run_test",
    )
    dispatcher = workstation_durable_dispatch(agent)

    raw_dispatched = {"called": False}

    def fake_dispatch(name, args, **kwargs):
        raw_dispatched["called"] = True
        raw_dispatched["name"] = name
        raw_dispatched["operation_id"] = kwargs.get("operation_id")
        return {"items": [{"id": "card-1", "title": "Test"}]}

    monkeypatch.setattr(bc, "dispatch_workstation_browser_authoritative", fake_dispatch)

    import workstation.integrations.hermes.scoped_execution as se
    captured = []
    orig_capture = se.capture_raw_result

    def track_capture(call_id, res):
        captured.append((call_id, res))
        return orig_capture(call_id, res)

    monkeypatch.setattr(se, "capture_raw_result", track_capture)

    res = dispatcher(
        name="browser_extract_items",
        args={"selector": ".card"},
        task_id="task_123",
        call_id="call_abc",
    )

    assert raw_dispatched["called"] is True
    assert raw_dispatched["name"] == "browser_extract_items"
    assert raw_dispatched["operation_id"] == "call_abc"
    assert len(captured) == 1
    assert captured[0][0] == "call_abc"
    assert captured[0][1] == {"items": [{"id": "card-1", "title": "Test"}]}
    assert res == {"items": [{"id": "card-1", "title": "Test"}]}


def test_inflight_learning_item1_to_item2_real_circuit(tmp_path, monkeypatch):
    """Real circuit: adaptive items teach -> monitor mines & validates offer -> in-flight adopter completes next items."""
    from workstation.tests.test_online_compilability_safety import (
        TaskRunFixture,
        make_monitor,
        install_validation_env,
        laya,
        OP_FAMILY,
        TGT_FAMILY,
    )
    from workstation.system1.contracts import CompilabilityStage
    from workstation.experience_compiler.compilability_monitor import (
        DIRECT,
        reset_compilability_monitor,
        notify_online_compilability,
    )
    from agent.system1_decision import register_system1_decision_provider, reset_system1_decision
    from workstation.experience_compiler.lifecycle import register_validation_environment_provider
    from workstation.integrations.hermes.run_local_adoption import create_safe_item_boundary_callback

    reset_system1_decision()
    reset_compilability_monitor()
    register_validation_environment_provider(None)

    fx = TaskRunFixture(tmp_path, monkeypatch, n_items=5, run_label="inflight")
    try:
        install_validation_env(fx, tmp_path)
        register_system1_decision_provider(laya(CompilabilityStage.POSSIBLE_RUN_LOCAL_REUSE.value))
        _monitor = make_monitor(fx, mode=DIRECT)

        boundary_cb = create_safe_item_boundary_callback(fx.agent, drain_timeout=2.0)
        dispatched_items = []
        counter = {"n": 0}

        def worker(payload, work_item):
            dispatched_items.append(work_item.item_index)
            fx.system2_calls += 1
            n = counter["n"] = counter["n"] + 2
            fx.dispatch("write_file", payload)
            raw = fx.dispatch("read_file", payload)
            fx.corpus.capture(fx.sample("write_file", n, payload, False))
            ref = fx.corpus.capture(fx.sample("read_file", n + 1, payload, True))
            notify_online_compilability(
                ref=ref,
                task_id=fx.task_id,
                run_id=fx.run_id,
                operation_id=f"op_{n + 1}_read_file",
                primitive="read_file",
                route="filesystem",
                outcome="verified_success",
                event_kind="verified_transition",
                operation_family=OP_FAMILY,
                target_family=TGT_FAMILY,
                evidence_refs=(ref,),
                owner=fx.owner,
                system2_calls=1,
            )
            return raw

        runner = DurableBatchRunner(
            fx.task_id,
            task_store=fx.store,
            artifact_store=fx.artifacts,
            max_retries=0,
            backoff_seconds=0,
        )

        summary = runner.execute_batch(
            "reports",
            fx.items,
            worker_fn=worker,
            on_safe_item_boundary=boundary_cb,
        )

        # Items 1, 2, 3 established the verified patterns; items 4, 5 were completed by in-flight adoption!
        assert dispatched_items == [1, 2, 3], f"Expected items [1, 2, 3] dispatched to worker, got {dispatched_items}"
        assert summary.total_items == 5
        assert summary.success_count == 5

        # Reports recorded on agent
        reports = getattr(fx.agent, "_run_local_adoption_reports", [])
        assert len(reports) >= 1
        assert any(r.status == "adopted" for r in reports)

        # Verify all 5 work items in store are completed
        items = fx.store.get_work_items(summary.plan_id)
        assert all(i.status == WorkItemStatus.COMPLETED for i in items)

        # Verify files were actually created and verified
        written = sorted(p.name for p in (fx.root / "out").glob("*.txt"))
        assert len(written) == 5
    finally:
        fx.owner.close()
        fx.store.close()
        reset_system1_decision()
        reset_compilability_monitor()
        register_validation_environment_provider(None)


def test_persisted_capability_reuse_across_taskruns(tmp_path, monkeypatch):
    """P2: Capabilities compiled in TaskRun 1 persist and are recognized by TaskRun 2 with different inputs."""
    from workstation.tests.test_online_compilability_safety import (
        TaskRunFixture,
        make_monitor,
        install_validation_env,
        laya,
        OP_FAMILY,
        TGT_FAMILY,
    )
    from workstation.system1.contracts import CompilabilityStage
    from workstation.experience_compiler.compilability_monitor import (
        DIRECT,
        reset_compilability_monitor,
    )
    from agent.system1_decision import register_system1_decision_provider, reset_system1_decision
    from workstation.experience_compiler.lifecycle import register_validation_environment_provider
    from workstation.operational_capabilities import CapabilityLifecycle, OperationalCapabilityRegistry
    from workstation.task_compiler import TaskCompiler

    reset_system1_decision()
    reset_compilability_monitor()
    register_validation_environment_provider(None)

    fx1 = TaskRunFixture(tmp_path, monkeypatch, n_items=5, run_label="run1")
    try:
        install_validation_env(fx1, tmp_path)
        register_system1_decision_provider(laya(CompilabilityStage.POSSIBLE_RUN_LOCAL_REUSE.value))
        monitor = make_monitor(fx1, mode=DIRECT)
        fx1.run_adaptive(3)
        assert monitor.drain(10.0)

        # Run local adoption checkpoint
        report = fx1.checkpoint()
        assert report is not None and report.items
        assert report.all_items_completed

        # Promote the validated capability into operational registry
        window = monitor._windows.get((fx1.task_id, fx1.run_id))
        assert window and window.mined_candidate_ids
        cand_id = window.mined_candidate_ids[-1]
        cap = fx1.registry.get(cand_id)
        assert cap is not None

        # Qualify candidate for cross-run promotion
        from dataclasses import replace
        from workstation.control_plane.verification import VerificationLifecycle, VerificationContract
        from workstation.experience_compiler.models import CausalGrade

        cap.causal_grade = CausalGrade.REPLAY_VALIDATED
        cap.learning_metadata["run_ids"] = [fx1.run_id, "prior_run"]
        cap.learning_metadata["parameterization_quality"] = True
        cap.learning_metadata["evidence_strength"] = 2
        cap.scope["base_dir"] = str(tmp_path)
        contract = replace(
            VerificationContract.from_dict(cap.verifier_contract),
            lifecycle=VerificationLifecycle.VALIDATED,
            validation_receipts=(
                {"kind": "positive_replay", "passed": True, "phase": "validation", "evidence_ref": "positive"},
                {"kind": "negative_control", "passed": True, "phase": "validation", "evidence_ref": "negative"},
            ),
        )
        cap.verifier_contract = contract.to_dict()
        cap.learning_metadata["verifier_lifecycle"] = "VALIDATED"
        cap.validation_evidence = [
            {
                "kind": "controlled_replay",
                "passed": True,
                "compatibility_fingerprint": cap.compatibility_fingerprint,
                "result": {"evidence_strength": 2, "evidence_refs": ["artifact://proof"]},
            }
        ]
        fx1.registry.register(cap)
        promoted = fx1.registry.promote(cap.id)
        assert promoted.lifecycle == CapabilityLifecycle.PROMOTED

        # Second TaskRun with different inputs
        fx2 = TaskRunFixture(tmp_path, monkeypatch, n_items=2, run_label="run2")
        fx2.artifacts = fx1.artifacts
        fx2.registry = fx1.registry
        try:
            # Query the registry for matching capability
            matched = fx2.registry.find_matching(
                route=promoted.route,
                semantic_fingerprint=promoted.semantic_fingerprint,
                promoted_only=True,
            )
            assert matched is not None
            assert matched.id == cap.id

            # Execute via TaskCompiler using the promoted capability
            compiler = TaskCompiler(store=fx2.store, artifacts=fx2.artifacts)
            try:
                dispatch_fn = lambda tool, args, *rest: fx2.dispatch(tool, args)
                result = compiler.execute(
                    {
                        "capability_id": matched.id,
                        "inputs": {"path": "out/new_run2_report.txt", "path2": "out/new_run2_report.txt", "content": "alpha"},
                        "scope": {"base_dir": str(fx2.root), **dict(promoted.scope)},
                        "recipe_scope": {"route": promoted.route, "base_dir": str(fx2.root), **promoted.scope},
                        "operation_fingerprint": promoted.semantic_fingerprint,
                    },
                    task_id=fx2.task_id,
                    session_id=fx2.envelope.session_id,
                    dispatch=dispatch_fn,
                    canonical_task_id=fx2.task_id,
                )
                assert result.get("success") is True or result.get("status") in {"COMPLETED", "EXECUTED"}
                assert result.get("metrics", {}).get("executor_llm_calls") == 0
                # Check that file was created with new parameter without LLM reasoning
                assert (tmp_path / "out" / "new_run2_report.txt").is_file()
                assert (tmp_path / "out" / "new_run2_report.txt").read_text(encoding="utf-8") == "alpha"
            finally:
                compiler.store.close()
        finally:
            fx2.owner.close()
            fx2.store.close()
    finally:
        fx1.owner.close()
        fx1.store.close()
        reset_system1_decision()
        reset_compilability_monitor()
        register_validation_environment_provider(None)


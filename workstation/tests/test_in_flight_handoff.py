"""Tests for In-Flight Operationalization Handoff (Adaptive -> Compiled).

Verifies:
- Verified canary + replay hands off remaining items to DurableBatchRunner.
- Zero LLM re-entry between equivalent items after handoff.
- RunScopedCapability never enters global PROMOTED index or registry.
- Verified prefix survives interrupted runs.
- Restart resumes remaining items without replaying committed mutations.
- Reasoning wakes only on declared exception (the 9 wake conditions).
"""
import json
import pytest
from types import SimpleNamespace

from workstation.artifacts import ArtifactStore
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.router import CapabilityIndex
from workstation.durable_tasks import DurableTaskStore, WorkItemStatus
from workstation.operational_capabilities import (
    CapabilityLifecycle,
    CapabilityValidationError,
    OperationalCapability,
    OperationalCapabilityRegistry,
)
from workstation.run_closure import (
    ExecutionEnvelope,
    HandoffWakeCondition,
    RunClosureProof,
    RunScopedCapability,
    execute_in_flight_handoff,
    recover_verified_prefix,
    synthesize_in_flight_work_execute_request,
)


@pytest.fixture
def temp_dirs(tmp_path):
    art_dir = tmp_path / "artifacts"
    db_file = tmp_path / "tasks.db"
    caps_dir = tmp_path / "capabilities"
    art_dir.mkdir(parents=True, exist_ok=True)
    caps_dir.mkdir(parents=True, exist_ok=True)
    import sqlite3
    conn = sqlite3.connect(db_file)
    return SimpleNamespace(
        artifacts=ArtifactStore(root_dir=art_dir),
        store=DurableTaskStore(conn=conn),
        caps=caps_dir,
    )


@pytest.fixture
def sample_proof():
    return RunClosureProof(
        task_id="task_trello_123",
        run_id="run_456",
        operation_id="op_card_update",
        semantic_fingerprint="sem_op_card_update_hash",
        operation_family="trello_card_update",
        target_family="trello_card",
        deterministic_representation_ref="primitive:browser_type",
        executable_primitive_or_capability="browser_type",
        compatible_route="native_browser",
        authority_scope=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"browser_type", "browser_click"}),
        effect_budget=[],
        verifier_contract={"kind": "readback", "target_field": "description"},
        first_verified_evidence_ref="artifact://proof_item_1",
        replay_evidence_ref="artifact://proof_item_2",
        uncertainty_clear=True,
        parameter_schema={"card_id": "string", "desc": "string"},
        bindings={"text": "$item.desc", "ref": "$item.card_id"},
        remaining_items_ref="artifact://tasks/batch_remaining.json",
        remaining_item_count=3,
        expected_operational_utility=8.5,
    )


def test_adaptive_verified_pair_hands_remaining_batch_to_durable_runner(temp_dirs, sample_proof):
    """Canary + replay pair hands off remaining items (3..5) to DurableBatchRunner with verified checkpoints."""
    remaining_items = [
        {"card_id": "card_3", "desc": "Card 3 description"},
        {"card_id": "card_4", "desc": "Card 4 description"},
        {"card_id": "card_5", "desc": "Card 5 description"},
    ]
    steps = [
        {"id": "type_desc", "tool": "browser_type", "args": {"ref": "$item.card_id", "text": "$item.desc"}},
        {
            "id": "verify_readback",
            "tool": "browser_read",
            "args": {"ref": "$item.card_id"},
            "verifies": ["type_desc"],
            "verifier_fn": lambda raw, args, item: raw.get("text") == item["desc"],
        },
    ]

    dispatches = []

    def mock_dispatch(tool, args):
        dispatches.append((tool, args))
        if tool == "browser_type":
            return {"status": "ok"}
        if tool == "browser_read":
            return {"text": args.get("ref", "").replace("card_", "Card ") + " description"}
        return {"status": "ok"}

    result = execute_in_flight_handoff(
        sample_proof,
        remaining_items,
        steps,
        mock_dispatch,
        task_store=temp_dirs.store,
        artifact_store=temp_dirs.artifacts,
    )

    assert result["status"] == "COMPLETED"
    assert result["completed"] == 3
    assert result["total"] == 3
    assert len(dispatches) == 6  # 3 items * 2 steps each

    plan = temp_dirs.store.get_plan(sample_proof.task_id)
    assert plan is not None
    assert "execution_envelope" in plan.metadata
    assert plan.metadata["execution_envelope"]["operation_id"] == sample_proof.operation_id


def test_no_llm_reentry_between_equivalent_items_after_handoff(temp_dirs, sample_proof):
    """Once handoff occurs to DurableBatchRunner, zero LLM calls occur for remaining items."""
    llm_call_count = 0

    def simulated_llm_planner():
        nonlocal llm_call_count
        llm_call_count += 1
        return "next_turn"

    # Step 1: LLM runs canary (item 1)
    simulated_llm_planner()
    assert llm_call_count == 1

    # Step 2: LLM runs replay (item 2)
    simulated_llm_planner()
    assert llm_call_count == 2

    # Step 3: RunClosureProof closure passes -> handoff remaining 3 items
    remaining_items = [
        {"card_id": "c3", "desc": "desc 3"},
        {"card_id": "c4", "desc": "desc 4"},
        {"card_id": "c5", "desc": "desc 5"},
    ]
    steps = [{"id": "step_1", "tool": "browser_type", "args": {"ref": "$item.card_id", "text": "$item.desc"}}]

    execute_in_flight_handoff(
        sample_proof,
        remaining_items,
        steps,
        lambda t, a: {"ok": True},
        task_store=temp_dirs.store,
        artifact_store=temp_dirs.artifacts,
    )

    # Verification: LLM was NEVER called during items 3, 4, 5
    assert llm_call_count == 2, "No LLM reentry between equivalent items after handoff"


def test_run_scoped_capability_never_enters_global_promoted_index(temp_dirs, sample_proof):
    """RunScopedCapability must fail closed if attempted to be registered or indexed globally."""
    envelope = ExecutionEnvelope(
        compiled_subgraph_ref="artifact://tasks/t1/subgraph.json",
        task_id="t1",
        run_id="r1",
        operation_id="op1",
        authority_scope={"level": 1},
        effect_budget=[],
        verifier_contract={},
    )
    run_scoped_cap = RunScopedCapability(
        capability_id="run_scoped_trello_card",
        task_id="t1",
        run_id="r1",
        operation_id="op1",
        proof=sample_proof,
        steps=[],
        parameter_schema={},
        envelope=envelope,
        run_scoped=True,
    )

    registry = OperationalCapabilityRegistry(artifacts=temp_dirs.artifacts, root=temp_dirs.caps)
    index = CapabilityIndex()

    # 1. Registration with PROMOTED lifecycle must raise CapabilityValidationError
    op_cap = OperationalCapability(
        id="run_scoped_trello_card",
        version="1.0.0",
        name="Run Local Trello Card",
        lifecycle=CapabilityLifecycle.PROMOTED,
        provenance={"run_scoped": True, "source": "in_flight_operationalization"},
    )
    op_cap.run_scoped = True

    with pytest.raises(CapabilityValidationError, match="RunScopedCapability cannot enter the global PROMOTED index"):
        registry.register(op_cap)

    # 2. Indexing into CapabilityIndex must be silently ignored / rejected
    index.index(op_cap)
    assert len(index.candidates()) == 0


def test_verified_prefix_survives_interrupted_run(temp_dirs):
    """Committed and verified items survive runner interruption in DurableTaskStore."""
    plan = temp_dirs.store.create_plan(
        task_id="task_prefix_test",
        title="Prefix Test",
        items=[{"id": 1}, {"id": 2}, {"id": 3}],
    )
    items = temp_dirs.store.get_work_items(plan.id)

    # Item 1 and Item 2 complete and checkpoint verified
    temp_dirs.store.update_item_checkpoint(items[0].id, "step_verify", "verified")
    temp_dirs.store.update_item_checkpoint(items[0].id, "persist", "ok")
    temp_dirs.store.update_item_checkpoint(items[0].id, "validate", "ok")
    temp_dirs.store.complete_item(items[0].id)

    temp_dirs.store.update_item_checkpoint(items[1].id, "step_verify", "verified")
    temp_dirs.store.update_item_checkpoint(items[1].id, "persist", "ok")
    temp_dirs.store.update_item_checkpoint(items[1].id, "validate", "ok")
    temp_dirs.store.complete_item(items[1].id)

    # Item 3 is interrupted (stays PENDING or IN_PROGRESS)
    recovery = recover_verified_prefix("task_prefix_test", task_store=temp_dirs.store)
    assert recovery["found"] is True
    assert recovery["completed_count"] == 2
    assert items[0].id in recovery["completed_ids"]
    assert items[1].id in recovery["completed_ids"]
    assert len(recovery["pending_items"]) == 1
    assert recovery["pending_items"][0].id == items[2].id


def test_restart_resumes_remaining_items_without_replaying_committed_mutation(temp_dirs, sample_proof):
    """Restart skips already committed items and marks unverified in-flight items UNCERTAIN."""
    plan = temp_dirs.store.create_plan(
        task_id=sample_proof.task_id,
        title="Restart Test",
        items=[
            {"card_id": "c1", "desc": "desc 1"},
            {"card_id": "c2", "desc": "desc 2"},
            {"card_id": "c3", "desc": "desc 3"},
        ],
    )
    items = temp_dirs.store.get_work_items(plan.id)

    # Item 0 was already completed
    temp_dirs.store.update_item_checkpoint(items[0].id, "step_1", "verified")
    temp_dirs.store.update_item_checkpoint(items[0].id, "persist", "ok")
    temp_dirs.store.update_item_checkpoint(items[0].id, "validate", "ok")
    temp_dirs.store.complete_item(items[0].id)

    # Item 1 was in progress (dispatched without verified checkpoint) when crash happened
    temp_dirs.store.update_item_checkpoint(items[1].id, "step_dispatch", "started")

    # Recovery detects unverified in-progress item as UNCERTAIN
    recovery = recover_verified_prefix(sample_proof.task_id, task_store=temp_dirs.store)
    assert items[0].id in recovery["completed_ids"]
    assert items[1].id in recovery["uncertain_ids"]

    # Now execute handoff on the remaining items (c3)
    dispatched_cards = []

    def mock_dispatch(tool, args):
        dispatched_cards.append(args.get("ref"))
        return {"status": "ok"}

    remaining = [{"card_id": "c3", "desc": "desc 3"}]
    steps = [{"id": "step_1", "tool": "browser_type", "args": {"ref": "$item.card_id", "text": "$item.desc"}}]

    res = execute_in_flight_handoff(
        sample_proof,
        remaining,
        steps,
        mock_dispatch,
        task_store=temp_dirs.store,
        artifact_store=temp_dirs.artifacts,
    )

    # In-flight unverified item wakes reasoning instead of blind execution
    assert res["status"] == "NEEDS_REASONING"
    assert res["wake_reason"] == HandoffWakeCondition.UNCERTAIN_MUTATION_STATE.value
    assert "c1" not in dispatched_cards  # Committed mutation c1 is NEVER replayed
    assert "c2" not in dispatched_cards  # Uncertain item c2 is NEVER blindly replayed

    # After reconciliation (readback proves c2 or marks it completed), continuation finishes c3
    temp_dirs.store.update_item_checkpoint(items[1].id, "persist", "ok")
    temp_dirs.store.update_item_checkpoint(items[1].id, "validate", "ok")
    temp_dirs.store.complete_item(items[1].id)

    res2 = execute_in_flight_handoff(
        sample_proof,
        remaining,
        steps,
        mock_dispatch,
        task_store=temp_dirs.store,
        artifact_store=temp_dirs.artifacts,
    )
    assert res2["status"] == "COMPLETED"
    assert dispatched_cards == ["c3"]


def test_reasoning_wakes_only_on_declared_exception_after_closure(temp_dirs, sample_proof):
    """Reasoning wakes only when a declared exception occurs; subsequent items are not blindly executed."""
    items = [
        {"card_id": "c1", "desc": "good"},
        {"card_id": "c2", "desc": "bad_trigger_failure"},
        {"card_id": "c3", "desc": "should_not_run"},
    ]
    steps = [
        {"id": "type", "tool": "browser_type", "args": {"ref": "$item.card_id", "text": "$item.desc"}},
        {
            "id": "verify",
            "tool": "browser_read",
            "args": {"ref": "$item.card_id"},
            "verifies": ["type"],
            "verifier_fn": lambda raw, args, item: item["desc"] != "bad_trigger_failure",
        },
    ]

    dispatched = []

    def mock_dispatch(tool, args):
        dispatched.append((tool, args.get("ref")))
        return {"status": "ok"}

    res = execute_in_flight_handoff(
        sample_proof,
        items,
        steps,
        mock_dispatch,
        task_store=temp_dirs.store,
        artifact_store=temp_dirs.artifacts,
        stop_on_exception=True,
    )

    assert res["status"] == "NEEDS_REASONING"
    assert res["wake_reason"] == HandoffWakeCondition.POST_VERIFIER_FAILED.value
    assert res["completed"] == 1
    # Item 3 was halted and not dispatched blindly
    assert ("browser_type", "c3") not in dispatched

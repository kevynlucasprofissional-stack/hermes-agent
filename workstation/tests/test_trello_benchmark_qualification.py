"""Phase P6: 12-Item Trello-Shaped Benchmark & Qualification Suite.

Proves:
1. Canary on item 1 + verified replay on item 2.
2. In-flight closure proof emitted and accepted with positive operational utility.
3. Handoff of remaining 10 items to DurableBatchRunner with atomic checkpoints.
4. Deliberate anomaly on item 7 triggers compact reasoning wake; once reconciled, resumes
   without replaying already committed items (items 1-6).
5. Large payload (>50KB) on item 5 handled via ArtifactStore (text_ref) without polluting LLM context.
6. Authoritative final readback confirms all 12 items persisted with correct state.
"""
from pathlib import Path
import sqlite3
import tempfile
from typing import Any
import pytest

from workstation.artifacts import ArtifactStore
from workstation.control_plane.ir import CREATE, EQ, Effect
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.router import RoutingCertificate
from workstation.durable_tasks import DurableTaskStore, WorkItemStatus
from workstation.reasoning_handoff import AttentionPacket, OpenCondition, needs_reasoning
from workstation.run_closure import (
    HandoffWakeCondition,
    RunClosureProof,
    evaluate_run_local_closure,
    execute_in_flight_handoff,
    recover_verified_prefix,
)
from tools.browser_workstation import resolve_browser_type_text


class MockTrelloEnvironment:
    """Realistic simulation of Trello-like board with ProseMirror editor and explicit save."""

    def __init__(self, artifacts: ArtifactStore, task_id: str, run_id: str) -> None:
        self.artifacts = artifacts
        self.task_id = task_id
        self.run_id = run_id
        self.backend_cards: dict[str, dict[str, Any]] = {}
        self.current_editor_text: str = ""
        self.current_due_date: str = ""
        self.current_title: str = ""
        self.anomaly_active: bool = True  # Item 7 anomaly trigger
        self.item_7_reconciled: bool = False
        self.mutation_counts: dict[str, int] = {}

    def dispatch(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        if tool == "browser_type":
            selector = args.get("selector", "")
            # Resolve text_ref / artifact_ref if present
            resolve_browser_type_text(args, task_id=self.task_id, session_id=self.run_id, artifact_store=self.artifacts)
            text = args.get("text", "")

            if selector == "#card-title":
                self.current_title = text
            elif selector == "#prosemirror-editor":
                # Simulated ProseMirror editor: preserves formatting & paragraphs
                self.current_editor_text = text
            elif selector == "#due-date-picker":
                self.current_due_date = text
            return {"ok": True, "typed": True, "selector": selector, "length": len(text)}

        elif tool == "browser_click":
            selector = args.get("selector", "")
            if selector == "#due-date-open":
                return {"ok": True, "picker_opened": True}

            if selector == "#save-button":
                item_idx = args.get("item_index", 0)
                card_id = f"card_item_{item_idx}"

                # Deliberate anomaly on item 7: transient save button lock
                if item_idx == 7 and self.anomaly_active and not self.item_7_reconciled:
                    return {
                        "ok": False,
                        "error": "save_button_disabled: transient editor synchronization conflict",
                        "code": "unexpected_state",
                    }

                # Explicit Save commits to backend storage
                self.mutation_counts[card_id] = self.mutation_counts.get(card_id, 0) + 1
                self.backend_cards[card_id] = {
                    "card_id": card_id,
                    "title": self.current_title,
                    "description": self.current_editor_text,
                    "due_date": self.current_due_date,
                    "persisted": True,
                }
                return {
                    "ok": True,
                    "persisted": True,
                    "card_id": card_id,
                    "version": self.mutation_counts[card_id],
                }

            if selector == "#reconcile-sync":
                self.item_7_reconciled = True
                return {"ok": True, "reconciled": True}

            return {"ok": True, "clicked": selector}

        elif tool == "browser_readback":
            card_id = args.get("card_id")
            card = self.backend_cards.get(card_id)
            if card:
                return {"ok": True, "persisted": True, "card": card}
            return {"ok": False, "persisted": False, "card": None}

        raise ValueError(f"Unknown mock browser tool: {tool}")


@pytest.fixture
def trello_fixture():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        artifacts = ArtifactStore(root_dir=root / "artifacts")
        db_conn = sqlite3.connect(str(root / "tasks.db"), check_same_thread=False)
        task_store = DurableTaskStore(conn=db_conn)
        task_id = "task_trello_bench_001"
        run_id = "run_trello_bench_001"
        env = MockTrelloEnvironment(artifacts, task_id, run_id)
        yield {
            "root": root,
            "artifacts": artifacts,
            "db_conn": db_conn,
            "task_store": task_store,
            "task_id": task_id,
            "run_id": run_id,
            "env": env,
        }
        try:
            task_store.close()
        except Exception:
            pass
        try:
            db_conn.close()
        except Exception:
            pass


def test_trello_shaped_12_item_fixture_closes_after_canary_and_finishes(trello_fixture):
    """End-to-end benchmark qualification proving in-flight operationalization on 12 Trello items."""
    artifacts = trello_fixture["artifacts"]
    task_store = trello_fixture["task_store"]
    task_id = trello_fixture["task_id"]
    run_id = trello_fixture["run_id"]
    env = trello_fixture["env"]

    # ---------------------------------------------------------------------
    # 1. Dataset of 12 items
    # ---------------------------------------------------------------------
    # Generate a large payload (>50KB) stored in ArtifactStore for item 5
    large_content = ("# Technical Specification for Workstation Card\n" + ("Paragraph with prose mirror details.\n" * 1500))
    assert len(large_content.encode("utf-8")) > 50000  # > 50KB!

    large_artifact = artifacts.store(
        task_id,
        "large_payload_item_5.txt",
        large_content,
        media_type="text/plain",
    )

    items = []
    for i in range(1, 13):
        item = {
            "item_index": i,
            "card_id": f"card_item_{i}",
            "title": f"Trello Task {i}",
            "due_date": f"2026-10-{i:02d}",
        }
        if i == 5:
            item["text_ref"] = large_artifact.ref
            item["description"] = None  # Replaced by text_ref
        else:
            item["description"] = f"Standard description for card {i}"
        items.append(item)

    # ---------------------------------------------------------------------
    # 2. Adaptive Phase: Canary (Item 1) + Replay (Item 2)
    # ---------------------------------------------------------------------
    def execute_adaptive_item(item_payload: dict[str, Any]) -> dict[str, Any]:
        idx = item_payload["item_index"]
        # 1. Type title
        env.dispatch("browser_type", {"selector": "#card-title", "text": item_payload["title"]})
        # 2. Type editor description (using text_ref or direct text)
        if item_payload.get("text_ref"):
            env.dispatch("browser_type", {"selector": "#prosemirror-editor", "text_ref": item_payload["text_ref"]})
        else:
            env.dispatch("browser_type", {"selector": "#prosemirror-editor", "text": item_payload["description"]})
        # 3. Set due date
        env.dispatch("browser_type", {"selector": "#due-date-picker", "text": item_payload["due_date"]})
        # 4. Save
        save_res = env.dispatch("browser_click", {"selector": "#save-button", "item_index": idx})
        assert save_res["ok"] is True
        # 5. Readback
        read_res = env.dispatch("browser_readback", {"card_id": f"card_item_{idx}"})
        assert read_res["persisted"] is True
        return {"card_id": f"card_item_{idx}", "readback": read_res}

    canary_res = execute_adaptive_item(items[0])
    replay_res = execute_adaptive_item(items[1])

    first_ref = artifacts.store(task_id, "canary_evidence.json", canary_res).ref
    replay_ref = artifacts.store(task_id, "replay_evidence.json", replay_res).ref

    # Store remaining items (items 3 to 12)
    remaining_items = items[2:]
    assert len(remaining_items) == 10
    rem_ref = artifacts.store(task_id, "remaining_items.json", remaining_items).ref

    from types import SimpleNamespace
    mock_agent = SimpleNamespace(
        has_uncertain_mutation=False,
        operational_closure_for_call=lambda name, args: {
            "deterministic_representation": True,
            "executable_primitive": True,
            "compatible_route": True,
            "authority_policy_compatible": True,
            "verifier_readback": True,
            "certified_dispatch": True,
            "uncertainty_clear": True,
            "route": "native_browser",
        },
    )

    admitted, proof, reasons = evaluate_run_local_closure(
        mock_agent,
        name="native_browser.card_pipeline",
        args={"selector": "#card-title", "text": "title"},
        route="native_browser",
        semantic_family="trello_card_creation",
        semantic_fingerprint="trello_card_sem_fp_v1",
        contract={"effect": "state_mutation", "target_family": "trello_board"},
        task_id=task_id,
        run_id=run_id,
        operation_id="op_create_trello_card",
        first_verified_ref=first_ref,
        replay_verified_ref=replay_ref,
        verifier_contract={"readback": "browser_readback", "check": "persisted"},
        remaining_items_ref=rem_ref,
        remaining_item_count=len(remaining_items),
        requested_authority=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"browser_click", "browser_type"}),
        authorized_authority=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"browser_click", "browser_type"}),
        effect_budget=[CREATE("backend_cards")],
        requested_effects=[CREATE("backend_cards")],
        parameter_schema={"properties": {"title": {"type": "string"}, "due_date": {"type": "string"}}},
        bindings={"$item.title": "title", "$item.due_date": "due_date"},
        deterministic_ref="subgraph://trello_card_subgraph",
        executable_primitive_or_capability="native_browser.card_pipeline",
        source_trace_refs=["trace_canary_01", "trace_replay_02"],
    )
    assert admitted is True, f"Closure rejected: {reasons}"
    assert proof is not None
    assert proof.expected_operational_utility > 0.0

    # ---------------------------------------------------------------------
    # 4. Handoff to DurableBatchRunner (Items 3 to 12)
    # ---------------------------------------------------------------------
    steps = [
        {
            "id": "type_title",
            "tool": "browser_type",
            "args": {"selector": "#card-title", "text": "$item.title"},
        },
        {
            "id": "type_description",
            "tool": "browser_type",
            "args": {
                "selector": "#prosemirror-editor",
                "text": "$item.description",
                "text_ref": "$item.text_ref",
            },
        },
        {
            "id": "type_due_date",
            "tool": "browser_type",
            "args": {"selector": "#due-date-picker", "text": "$item.due_date"},
        },
        {
            "id": "click_save",
            "tool": "browser_click",
            "args": {"selector": "#save-button", "item_index": "$item.item_index"},
            "verifier_fn": lambda res, args, item: res.get("ok") is True and res.get("persisted") is True,
            "readback": True,
        },
        {
            "id": "verify_readback",
            "tool": "browser_readback",
            "args": {"card_id": "$item.card_id"},
            "verifier_fn": lambda res, args, item: res.get("ok") is True and res.get("persisted") is True,
            "readback": True,
        },
    ]

    def runner_dispatch(tool: str, args: dict[str, Any]) -> dict[str, Any]:
        cleaned_args = dict(args)
        if "text_ref" in cleaned_args and (not cleaned_args["text_ref"] or str(cleaned_args["text_ref"]).startswith("$item.")):
            del cleaned_args["text_ref"]
        if "text" in cleaned_args and (cleaned_args["text"] is None or str(cleaned_args["text"]).startswith("$item.")):
            del cleaned_args["text"]
        return env.dispatch(tool, cleaned_args)

    # First run: Items 3 to 6 will succeed; Item 7 will encounter deliberate anomaly
    handoff_result = execute_in_flight_handoff(
        proof,
        remaining_items,
        steps,
        dispatch=runner_dispatch,
        task_store=task_store,
        artifact_store=artifacts,
        stop_on_exception=True,
    )

    # ---------------------------------------------------------------------
    # 5. Deliberate Anomaly Handling & Reasoning Wake
    # ---------------------------------------------------------------------
    assert handoff_result["status"] == "NEEDS_REASONING"
    assert handoff_result["safe_to_resume"] is True

    # Items 3, 4, 5, 6 are completed (4 items from the remaining batch + 2 from adaptive = 6 cards)
    assert len(env.backend_cards) == 6
    assert "card_item_3" in env.backend_cards
    assert "card_item_4" in env.backend_cards
    assert "card_item_5" in env.backend_cards
    assert "card_item_6" in env.backend_cards
    assert "card_item_7" not in env.backend_cards

    # Prove Item 5 resolved the >50KB large text_ref cleanly
    item_5_card = env.backend_cards["card_item_5"]
    assert len(item_5_card["description"].encode("utf-8")) > 50000
    assert item_5_card["description"] == large_content

    # Item 7 was halted. Verify recovery prefix:
    prefix_recovery = recover_verified_prefix(task_id, task_store=task_store)
    assert prefix_recovery["found"] is True
    assert prefix_recovery["completed_count"] == 4  # items 3, 4, 5, 6 in this runner plan

    # Construct compact reasoning handoff packet
    attention = AttentionPacket(
        intent_id="save_card_7",
        completed_until="card_item_6",
        expected="save_button enabled and clickable",
        observed="save_button_disabled",
        open_condition=OpenCondition(
            condition_type="state_lock",
            proposition="Item 7 encountered transient editor sync lock",
            known_facts={"focus_target": "#save-button", "failing_step": "click_save"},
        ),
        safe_to_resume=True,
    )
    handoff_packet = needs_reasoning(
        artifacts,
        owner=task_id,
        completed_until="card_item_6",
        expected="save_button enabled and clickable",
        observed="save_button_disabled",
        safe_to_resume=True,
        context={"attention": attention.to_dict(), "item_index": 7},
    )
    assert handoff_packet["status"] == "NEEDS_REASONING"

    # ---------------------------------------------------------------------
    # 6. Reconcile & Resume Without Replaying Committed Items
    # ---------------------------------------------------------------------
    # Reasoning executes reconciliation: clicks `#reconcile-sync`
    env.dispatch("browser_click", {"selector": "#reconcile-sync"})
    assert env.item_7_reconciled is True

    # Pending items: items 7 to 12
    pending_work_items = prefix_recovery["pending_items"]
    pending_items_payload = [p.input_payload for p in pending_work_items]
    assert len(pending_items_payload) == 6  # items 7, 8, 9, 10, 11, 12

    import dataclasses
    resume_proof = dataclasses.replace(
        proof,
        task_id=f"{task_id}_resume",
        operation_id="op_create_trello_card_resumed",
        remaining_item_count=len(pending_items_payload),
        expected_operational_utility=250.0,
    )

    resumed_handoff = execute_in_flight_handoff(
        resume_proof,
        pending_items_payload,
        steps,
        dispatch=runner_dispatch,
        task_store=task_store,
        artifact_store=artifacts,
        stop_on_exception=True,
    )
    assert resumed_handoff["status"] == "COMPLETED"

    # ---------------------------------------------------------------------
    # 7. Authoritative Final Readback: All 12 Items Persisted Exactly Once
    # ---------------------------------------------------------------------
    assert len(env.backend_cards) == 12

    for i in range(1, 13):
        card_id = f"card_item_{i}"
        assert card_id in env.backend_cards
        card = env.backend_cards[card_id]
        assert card["title"] == f"Trello Task {i}"
        assert card["due_date"] == f"2026-10-{i:02d}"
        assert card["persisted"] is True
        # Each card mutation occurred exactly once (no duplicate replays of committed items)
        assert env.mutation_counts[card_id] == 1

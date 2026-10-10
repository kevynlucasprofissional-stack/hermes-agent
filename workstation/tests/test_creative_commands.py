"""Tests for CWN-02 Unified Command Bus, transactions, idempotency, and undo/redo."""
from fractions import Fraction
import pytest

from workstation.creative_document import (
    CreativeDocument,
    create_empty_project,
    document_to_dict,
)
from workstation.creative_time import CanonicalTime, RationalFps, TimeRange
from workstation.creative_commands import (
    Actor,
    CreativeCommand,
    execute_command,
    CommandRegistry,
)
from workstation.creative_transactions import (
    CreativeTransaction,
    CreativeHistory,
    TransactionConflictError,
    TransactionExecutionError,
)


def test_mouse_and_agent_equivalent_serialized_mutation():
    """DoD: mouse and agent executing equivalent command produce identical serialized document."""
    doc_mouse = create_empty_project(name="Project Mouse")
    doc_agent = create_empty_project(name="Project Mouse")
    # Align project and comp IDs for exact comparison
    doc_agent.project_id = doc_mouse.project_id
    doc_agent.compositions[0].composition_id = doc_mouse.compositions[0].composition_id

    human_actor = Actor(actor_id="user_1", actor_type="human_mouse")
    agent_actor = Actor(actor_id="hermes_agent_1", actor_type="hermes_agent")

    # Command: track.add
    cmd_track_mouse = CreativeCommand(
        command_id="track.add",
        params={"composition_id": doc_mouse.compositions[0].composition_id, "track_id": "1" * 32, "name": "V1", "kind": "video"},
        actor=human_actor,
        idempotency_key="idemp_1",
    )
    cmd_track_agent = CreativeCommand(
        command_id="track.add",
        params={"composition_id": doc_agent.compositions[0].composition_id, "track_id": "1" * 32, "name": "V1", "kind": "video"},
        actor=agent_actor,
        idempotency_key="idemp_1",
    )

    execute_command(doc_mouse, cmd_track_mouse)
    execute_command(doc_agent, cmd_track_agent)

    # Command: layer.create
    cmd_layer_mouse = CreativeCommand(
        command_id="layer.create",
        params={
            "composition_id": doc_mouse.compositions[0].composition_id,
            "layer_id": "2" * 32,
            "name": "Title",
            "kind": "vector_svg",
            "declared_parameters": {"color": "#ff0000"},
        },
        actor=human_actor,
        idempotency_key="idemp_2",
    )
    cmd_layer_agent = CreativeCommand(
        command_id="layer.create",
        params={
            "composition_id": doc_agent.compositions[0].composition_id,
            "layer_id": "2" * 32,
            "name": "Title",
            "kind": "vector_svg",
            "declared_parameters": {"color": "#ff0000"},
        },
        actor=agent_actor,
        idempotency_key="idemp_2",
    )

    execute_command(doc_mouse, cmd_layer_mouse)
    execute_command(doc_agent, cmd_layer_agent)

    dict_mouse = document_to_dict(doc_mouse)
    dict_agent = document_to_dict(doc_agent)
    assert dict_mouse == dict_agent


def test_compound_transaction_fault_at_step_3_leaves_exact_old_state():
    """DoD: compound 4-step command fault at step 3 leaves exact old state."""
    doc = create_empty_project(name="Batch Project")
    initial_dict = document_to_dict(doc)

    actor = Actor(actor_id="hermes_1", actor_type="hermes_agent")
    comp_id = doc.compositions[0].composition_id

    # Step 1: add track
    c1 = CreativeCommand(
        command_id="track.add",
        params={"composition_id": comp_id, "track_id": "1" * 32, "name": "V1", "kind": "video"},
        actor=actor,
        idempotency_key="k1",
    )
    # Step 2: add layer
    c2 = CreativeCommand(
        command_id="layer.create",
        params={"composition_id": comp_id, "layer_id": "2" * 32, "name": "Layer1", "kind": "text"},
        actor=actor,
        idempotency_key="k2",
    )
    # Step 3: FAULTY command (invalid track_id or illegal param)
    c3 = CreativeCommand(
        command_id="clip.add",
        params={"composition_id": comp_id, "track_id": "non_existent_track", "clip_id": "3" * 32, "asset_id": "4" * 32},
        actor=actor,
        idempotency_key="k3",
    )
    # Step 4: another layer
    c4 = CreativeCommand(
        command_id="layer.create",
        params={"composition_id": comp_id, "layer_id": "5" * 32, "name": "Layer2", "kind": "text"},
        actor=actor,
        idempotency_key="k4",
    )

    tx = CreativeTransaction(commands=[c1, c2, c3, c4])

    with pytest.raises(TransactionExecutionError):
        tx.apply(doc)

    # Document must be completely unchanged
    after_fault_dict = document_to_dict(doc)
    assert after_fault_dict == initial_dict
    assert len(doc.compositions[0].tracks) == 0
    assert len(doc.compositions[0].layers) == 0


def test_undo_redo_recovers_byte_equivalent_document():
    """DoD: undo/redo recovers byte-equivalent document."""
    doc = create_empty_project(name="History Project")
    initial_dict = document_to_dict(doc)
    history = CreativeHistory()
    actor = Actor(actor_id="user_1", actor_type="human_mouse")
    comp_id = doc.compositions[0].composition_id

    # Transaction 1: Add a track
    tx1 = CreativeTransaction(commands=[
        CreativeCommand(
            command_id="track.add",
            params={"composition_id": comp_id, "track_id": "1" * 32, "name": "V1", "kind": "video"},
            actor=actor,
            idempotency_key="t1",
        )
    ])
    history.commit(doc, tx1)
    state_after_tx1 = document_to_dict(doc)
    assert len(doc.compositions[0].tracks) == 1

    # Transaction 2: Add a layer
    tx2 = CreativeTransaction(commands=[
        CreativeCommand(
            command_id="layer.create",
            params={"composition_id": comp_id, "layer_id": "2" * 32, "name": "Title", "kind": "text"},
            actor=actor,
            idempotency_key="t2",
        )
    ])
    history.commit(doc, tx2)
    state_after_tx2 = document_to_dict(doc)
    assert len(doc.compositions[0].layers) == 1

    # Undo tx2
    assert history.can_undo() is True
    history.undo(doc)
    assert document_to_dict(doc) == state_after_tx1

    # Undo tx1
    history.undo(doc)
    assert document_to_dict(doc) == initial_dict

    # Redo tx1
    assert history.can_redo() is True
    history.redo(doc)
    assert document_to_dict(doc) == state_after_tx1

    # Redo tx2
    history.redo(doc)
    assert document_to_dict(doc) == state_after_tx2


def test_revision_mismatch_and_idempotency():
    """DoD: revision mismatch rejects; canceled/restarted command cannot silently double-apply."""
    doc = create_empty_project(name="Concurrency Project")
    history = CreativeHistory()
    actor = Actor(actor_id="hermes_1", actor_type="hermes_agent")
    comp_id = doc.compositions[0].composition_id

    cmd = CreativeCommand(
        command_id="track.add",
        params={"composition_id": comp_id, "track_id": "1" * 32, "name": "V1", "kind": "video"},
        actor=actor,
        idempotency_key="repeat_key_1",
    )
    tx = CreativeTransaction(commands=[cmd], expected_revision=0)

    # First apply succeeds
    history.commit(doc, tx)
    assert len(doc.compositions[0].tracks) == 1
    assert history.current_revision == 1

    # Applying same transaction again with stale expected_revision=0 fails with conflict
    tx_stale = CreativeTransaction(commands=[cmd], expected_revision=0)
    with pytest.raises(TransactionConflictError, match="Revision mismatch"):
        history.commit(doc, tx_stale)

    # Re-executing transaction with already-seen idempotency key at current revision does not double-apply
    tx_replay = CreativeTransaction(commands=[cmd], expected_revision=1)
    history.commit(doc, tx_replay)
    # Track must not be duplicated!
    assert len(doc.compositions[0].tracks) == 1

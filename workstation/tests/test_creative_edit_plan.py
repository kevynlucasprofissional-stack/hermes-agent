"""Tests for CWN-04 Semantic Edit Plan and reversible preview."""
from fractions import Fraction
import pytest

from workstation.creative_document import (
    Asset,
    Clip,
    Composition,
    CreativeDocument,
    Track,
    create_empty_project,
    document_to_dict,
)
from workstation.creative_time import CanonicalTime, RationalFps, TimeRange
from workstation.creative_commands import Actor, CreativeCommand
from workstation.creative_transactions import CreativeHistory
from workstation.creative_edit_plan import (
    EditPlanState,
    PlanConflictError,
    SemanticEditPlan,
    SemanticEditPlanManager,
)


def _setup_test_project():
    fps = RationalFps(30, 1)
    doc = create_empty_project(name="AI Edit Plan Project", fps=fps)
    comp = doc.compositions[0]
    asset = Asset(
        asset_id="a" * 32,
        name="interview.mp4",
        kind="video",
        path="media/interview.mp4",
        sha256="1" * 64,
        duration=CanonicalTime.from_seconds(60),
    )
    doc.assets[asset.asset_id] = asset

    v_track = Track(track_id="1" * 32, name="V1", kind="video", z_index=0)
    clip = Clip(
        clip_id="c" * 32,
        track_id=v_track.track_id,
        asset_id=asset.asset_id,
        name="Interview A",
        timeline_range=TimeRange(CanonicalTime.from_seconds(0), CanonicalTime.from_seconds(20)),
        source_in=CanonicalTime.from_seconds(0),
    )
    v_track.clips.append(clip)
    comp.tracks.append(v_track)
    return doc, comp, clip


def test_proposal_preview_does_not_modify_user_document():
    """DoD: proposal preview does not modify user document."""
    doc, comp, clip = _setup_test_project()
    initial_dict = document_to_dict(doc)

    manager = SemanticEditPlanManager()
    agent_actor = Actor(actor_id="hermes_agent", actor_type="hermes_agent")

    # Hermes proposes removing silence by splitting and trimming clip
    c1 = CreativeCommand(
        command_id="clip.split",
        params={"composition_id": comp.composition_id, "clip_id": clip.clip_id, "split_time": "5"},
        actor=agent_actor,
        idempotency_key="plan_split_1",
    )
    c2 = CreativeCommand(
        command_id="layer.create",
        params={"composition_id": comp.composition_id, "layer_id": "2" * 32, "name": "AI Subtitle", "kind": "text"},
        actor=agent_actor,
        idempotency_key="plan_layer_1",
    )

    plan = manager.propose_plan(
        doc=doc,
        base_revision_id="rev_0",
        intent="Remove pause and add subtitle",
        commands=[c1, c2],
        provenance={"task_id": "task_1", "model": "hermes-v3"},
    )
    assert plan.state == EditPlanState.PROPOSED

    # Generate preview
    preview_doc = manager.preview_plan(plan, doc)
    assert plan.state == EditPlanState.PREVIEWED
    assert preview_doc is not doc  # Copy-on-write clone!

    # Preview document has mutations
    assert len(preview_doc.compositions[0].tracks[0].clips) == 2
    assert len(preview_doc.compositions[0].layers) == 1

    # User document remains completely untouched!
    assert document_to_dict(doc) == initial_dict
    assert len(doc.compositions[0].tracks[0].clips) == 1
    assert len(doc.compositions[0].layers) == 0


def test_selective_acceptance_transitions_to_partial():
    """DoD: accept subset and rerender; partial never claims DONE/APPLIED."""
    doc, comp, clip = _setup_test_project()
    manager = SemanticEditPlanManager()
    history = CreativeHistory()
    agent_actor = Actor(actor_id="hermes_agent", actor_type="hermes_agent")

    c1 = CreativeCommand(
        command_id="clip.split",
        params={"composition_id": comp.composition_id, "clip_id": clip.clip_id, "split_time": "5"},
        actor=agent_actor,
        idempotency_key="cmd_1",
    )
    c2 = CreativeCommand(
        command_id="layer.create",
        params={"composition_id": comp.composition_id, "layer_id": "2" * 32, "name": "AI Subtitle", "kind": "text"},
        actor=agent_actor,
        idempotency_key="cmd_2",
    )

    plan = manager.propose_plan(
        doc=doc,
        base_revision_id="rev_0",
        intent="Split clip and add subtitle",
        commands=[c1, c2],
        provenance={"task_id": "task_1"},
    )
    manager.preview_plan(plan, doc)

    # User accepts ONLY command index 0 (the split), rejecting subtitle (index 1)
    manager.apply_plan(plan, doc, history, selected_command_indices=[0])

    assert plan.state == EditPlanState.PARTIAL  # Must be PARTIAL, not APPLIED!
    assert len(doc.compositions[0].tracks[0].clips) == 2
    assert len(doc.compositions[0].layers) == 0  # Subtitle was omitted!


def test_conflict_after_manual_edit_denied():
    """DoD: conflict after manual edit denied or resolved explicitly; never overwrite."""
    doc, comp, clip = _setup_test_project()
    manager = SemanticEditPlanManager()
    history = CreativeHistory()
    agent_actor = Actor(actor_id="hermes_agent", actor_type="hermes_agent")
    human_actor = Actor(actor_id="user_1", actor_type="human_mouse")

    # Plan proposed at base revision 0
    c1 = CreativeCommand(
        command_id="clip.split",
        params={"composition_id": comp.composition_id, "clip_id": clip.clip_id, "split_time": "5"},
        actor=agent_actor,
        idempotency_key="cmd_1",
    )
    plan = manager.propose_plan(
        doc=doc,
        base_revision_id="rev_0",
        intent="Split clip",
        commands=[c1],
        provenance={"task_id": "task_1"},
    )

    # Human makes a manual edit in the meantime (bumps revision from 0 to 1)
    human_cmd = CreativeCommand(
        command_id="track.add",
        params={"composition_id": comp.composition_id, "track_id": "3" * 32, "name": "B-Roll", "kind": "video"},
        actor=human_actor,
        idempotency_key="human_add_track",
    )
    from workstation.creative_transactions import CreativeTransaction
    history.commit(doc, CreativeTransaction(commands=[human_cmd]))
    assert history.current_revision == 1

    # Attempting to apply plan built against stale revision 0 must raise PlanConflictError!
    with pytest.raises(PlanConflictError, match="Document was modified after plan creation"):
        manager.apply_plan(plan, doc, history)

    # Live human edit is completely preserved!
    assert len(doc.compositions[0].tracks) == 2
    assert doc.compositions[0].tracks[1].name == "B-Roll"


def test_missing_external_artifact_blocks_plan():
    """DoD: missing external artifact is not classified as applied."""
    doc, comp, clip = _setup_test_project()
    manager = SemanticEditPlanManager()
    agent_actor = Actor(actor_id="hermes_agent", actor_type="hermes_agent")

    # Command referencing non-existent external asset file
    c_import = CreativeCommand(
        command_id="asset.import",
        params={
            "asset_id": "9" * 32,
            "name": "generated_music.wav",
            "path": "non_existent_path/generated_music.wav",
            "sha256": "0" * 64,
        },
        actor=agent_actor,
        idempotency_key="import_missing",
    )

    plan = manager.propose_plan(
        doc=doc,
        base_revision_id="rev_0",
        intent="Import AI generated music",
        commands=[c_import],
        provenance={"task_id": "task_1"},
        required_external_paths=["non_existent_path/generated_music.wav"],
    )

    is_valid = manager.validate_plan(plan, doc)
    assert is_valid is False
    assert plan.state == EditPlanState.BLOCKED
    assert any("Missing required external file" in d for d in plan.diagnostics)

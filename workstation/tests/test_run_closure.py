"""Tests for Phase P1: RunClosureProof and evaluate_run_local_closure."""
import pytest
from types import SimpleNamespace

from workstation.control_plane.ir import EQ, SET
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.run_closure import (
    RunClosureProof,
    compute_expected_operational_utility,
    evaluate_run_local_closure,
)


@pytest.fixture
def mock_agent_closure():
    return SimpleNamespace(
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


def test_run_local_closure_requires_verified_replay_and_verifier(mock_agent_closure):
    """Closure handoff strictly fails closed without verified execution, replay, and verifier."""
    base_kwargs = {
        "name": "browser_type",
        "args": {"ref": "@e1", "text": "hello"},
        "route": "native_browser",
        "semantic_family": "trello:card_desc",
        "semantic_fingerprint": "sem_op_123",
        "contract": {"effect": "state_mutation", "target_family": "trello_card"},
        "task_id": "task-test",
        "run_id": "run-test",
        "remaining_items_ref": "artifact://tasks/batch_dataset.json",
        "remaining_item_count": 10,
        "parameter_schema": {"text": "string"},
        "requested_authority": AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"browser_type"}),
        "authorized_authority": AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"browser_type"}),
    }

    # 1. Missing first verified execution evidence
    ok, proof, reasons = evaluate_run_local_closure(
        mock_agent_closure,
        first_verified_ref=None,
        replay_verified_ref="artifact://proof_replay",
        verifier_contract={"kind": "readback"},
        **base_kwargs,
    )
    assert ok is False
    assert "missing_first_verified_evidence" in reasons
    assert proof is None

    # 2. Missing compatible replay/canary for mutation
    ok, proof, reasons = evaluate_run_local_closure(
        mock_agent_closure,
        first_verified_ref="artifact://proof_1",
        replay_verified_ref=None,
        verifier_contract={"kind": "readback"},
        **base_kwargs,
    )
    assert ok is False
    assert "missing_compatible_verified_replay" in reasons
    assert proof is None

    # 3. Missing verifier contract
    ok, proof, reasons = evaluate_run_local_closure(
        mock_agent_closure,
        first_verified_ref="artifact://proof_1",
        replay_verified_ref="artifact://proof_replay",
        verifier_contract={},
        **base_kwargs,
    )
    assert ok is False
    assert "insufficient_verifier_contract" in reasons
    assert proof is None

    # 4. Missing remaining items ref
    ok, proof, reasons = evaluate_run_local_closure(
        mock_agent_closure,
        first_verified_ref="artifact://proof_1",
        replay_verified_ref="artifact://proof_replay",
        verifier_contract={"kind": "readback"},
        **{**base_kwargs, "remaining_items_ref": None},
    )
    assert ok is False
    assert "missing_remaining_items_ref" in reasons
    assert proof is None

    # 5. Full valid closure proof
    ok, proof, reasons = evaluate_run_local_closure(
        mock_agent_closure,
        first_verified_ref="artifact://proof_1",
        replay_verified_ref="artifact://proof_replay",
        verifier_contract={"kind": "readback"},
        **base_kwargs,
    )
    assert ok is True
    assert not reasons
    assert isinstance(proof, RunClosureProof)
    assert proof.semantic_fingerprint == "sem_op_123"
    assert proof.remaining_item_count == 10
    assert proof.expected_operational_utility > 0.0


def test_run_local_closure_cannot_expand_authority_or_effect_budget(mock_agent_closure):
    """Run-local closure cannot widen granted authority or exceed intent effect budget."""
    base_kwargs = {
        "name": "browser_type",
        "args": {"ref": "@e1", "text": "hello"},
        "route": "native_browser",
        "semantic_family": "trello:card_desc",
        "semantic_fingerprint": "sem_op_123",
        "contract": {"effect": "state_mutation", "target_family": "trello_card"},
        "first_verified_ref": "artifact://proof_1",
        "replay_verified_ref": "artifact://proof_replay",
        "verifier_contract": {"kind": "readback"},
        "remaining_items_ref": "artifact://tasks/batch.json",
        "remaining_item_count": 5,
        "parameter_schema": {"text": "string"},
    }

    # Authority expansion attempt
    ok, proof, reasons = evaluate_run_local_closure(
        mock_agent_closure,
        requested_authority=AuthorityScope(level=AuthorityLevel.EXTERNAL_REVERSIBLE, allowed_actions={"all"}),
        authorized_authority=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"read"}),
        **base_kwargs,
    )
    assert ok is False
    assert "authority_expansion_forbidden" in reasons
    assert proof is None

    # Effect budget expansion attempt
    ok, proof, reasons = evaluate_run_local_closure(
        mock_agent_closure,
        requested_authority=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"browser_type"}),
        authorized_authority=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"browser_type"}),
        requested_effects=[SET("card.description", "new"), SET("card.external_webhook", "call")],
        effect_budget=[SET("card.description", "new")],
        **base_kwargs,
    )
    assert ok is False
    assert "effect_budget_expansion_forbidden" in reasons
    assert proof is None

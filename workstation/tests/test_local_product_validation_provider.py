import os
import shutil
import tempfile
from pathlib import Path
import pytest

from workstation.artifacts import ArtifactStore
from workstation.control_plane.verification import (
    VerificationContract,
    VerificationStatus,
    VerificationLifecycle,
)
from workstation.execution_policy import EvidenceStrength
from workstation.experience_compiler.causal import controlled_replay
from workstation.experience_compiler.lifecycle import (
    get_validation_environment_provider,
    register_validation_environment_provider,
    create_local_canary_validation_provider,
)
from workstation.experience_compiler.models import CausalGrade
from workstation.operational_capabilities import OperationalCapability


@pytest.fixture(autouse=True)
def clean_validation_provider():
    old = get_validation_environment_provider()
    register_validation_environment_provider(None)
    yield
    register_validation_environment_provider(old)


def make_file_candidate(task_id: str = "task-local-1", run_id: str = "run-1"):
    return OperationalCapability(
        id="cap_write_local_01",
        name="write_report_file_locally",
        version="v1",
        route="local_tool",
        effect="state_mutation",
        input_schema={"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}},
        implementation={
            "steps": [
                {
                    "id": "step_write",
                    "primitive": "write_file",
                    "args": {"path": "$inputs.path", "content": "$inputs.content"},
                }
            ]
        },
        source_trace_refs=[],
        verifier_contract={
            "covered_predicates": ["exists"],
            "effect_classes": ["state_mutation"],
            "observer": "workstation.verifier",
            "source_kind": "filesystem",
            "minimum_evidence": EvidenceStrength.SEMANTIC_PERSISTED_READBACK.value,
            "allowed_trust": ["trusted_runtime"],
            "require_read_after_write": True,
            "transition_claim": True,
        },
        learning_metadata={
            "run_ids": [run_id],
            "task_id": task_id,
            "bindings": [{"path": "out/sample.txt", "content": "CANARY_TEST_CONTENT"}],
            "verifier_fingerprint": "expected_verifier_fp_12345",
            "effects": {"exists": True},
            "provenance_complete": True,
            "parameterization_quality": True,
        },
        provenance={"origins": [{"task_id": task_id, "run_id": run_id}]},
    )


def test_local_product_validation_provider_isolated_positive_probe_and_negative_control(tmp_path):
    artifacts = ArtifactStore(tmp_path / "artifacts")
    sandbox_base = tmp_path / "sandbox_base"
    provider = create_local_canary_validation_provider(artifacts=artifacts, sandbox_base=sandbox_base)

    cand = make_file_candidate()
    contract = VerificationContract.from_dict(cand.verifier_contract)
    pos, neg = provider.verifier_evaluator(cand, contract, "task-local-1", "run-1")

    assert pos is not None and neg is not None
    assert pos["kind"] == "positive_replay"
    assert pos["passed"] is True
    assert pos["evidence_ref"].startswith("artifact://tasks/task-local-1/")
    assert pos["verification_result"]["status"] == VerificationStatus.VERIFIED.value

    assert neg["kind"] == "negative_control"
    assert neg["passed"] is True
    assert neg["evidence_ref"].startswith("artifact://tasks/task-local-1/")

    # Assert live filesystem outside sandbox was not touched
    assert not (tmp_path / "out" / "sample.txt").exists()


def test_local_product_validation_provider_controlled_replay(tmp_path):
    artifacts = ArtifactStore(tmp_path / "artifacts")
    sandbox_base = tmp_path / "sandbox_base"
    provider = create_local_canary_validation_provider(artifacts=artifacts, sandbox_base=sandbox_base)

    cand = make_file_candidate()
    env = provider.safe_env_factory(cand)
    runner = provider.replay_runner_factory(cand, env)

    replayed = controlled_replay(cand, env, runner)
    assert replayed.causal_grade == CausalGrade.REPLAY_VALIDATED
    evidence = [e for e in replayed.validation_evidence if e.get("kind") == "controlled_replay"]
    assert len(evidence) == 1
    assert evidence[0]["passed"] is True
    assert len(evidence[0]["result"]["evidence_refs"]) >= 1
    ref = evidence[0]["result"]["evidence_refs"][0]
    assert ref.startswith("artifact://tasks/task-local-1/")


def test_local_product_validation_provider_fails_closed_on_path_traversal(tmp_path):
    artifacts = ArtifactStore(tmp_path / "artifacts")
    sandbox_base = tmp_path / "sandbox_base"
    provider = create_local_canary_validation_provider(artifacts=artifacts, sandbox_base=sandbox_base)

    cand = make_file_candidate()
    # Malicious or buggy traversal attempt
    cand.learning_metadata["bindings"] = [{"path": "../../outside.txt", "content": "ESCAPE"}]

    env = provider.safe_env_factory(cand)
    runner = provider.replay_runner_factory(cand, env)

    replayed = controlled_replay(cand, env, runner)
    # Must fail closed: replay fails
    assert replayed.causal_grade < CausalGrade.REPLAY_VALIDATED
    evidence = [e for e in replayed.validation_evidence if e.get("kind") == "controlled_replay"]
    assert len(evidence) == 1
    assert evidence[0]["passed"] is False


def test_local_product_validation_provider_rejects_unsupported_primitive(tmp_path):
    artifacts = ArtifactStore(tmp_path / "artifacts")
    sandbox_base = tmp_path / "sandbox_base"
    provider = create_local_canary_validation_provider(artifacts=artifacts, sandbox_base=sandbox_base)

    cand = make_file_candidate()
    cand.implementation["steps"][0]["primitive"] = "unsupported_dangerous_primitive"

    contract = VerificationContract.from_dict(cand.verifier_contract)
    pos, neg = provider.verifier_evaluator(cand, contract, "task-local-1", "run-1")
    assert pos is None and neg is None

"""Tests for Phase P4: Durable CapabilityInvocation & Causal Composite Promotion."""
import pytest
from pathlib import Path
import tempfile
import uuid

from workstation.artifacts import ArtifactStore
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.experience_compiler.hierarchical import HierarchicalExperienceCompiler
from workstation.experience_compiler.models import CapabilityInvocation, CausalGrade
from workstation.operational_capabilities import (
    CapabilityDependency,
    CapabilityDriftError,
    CapabilityLifecycle,
    CapabilityValidationError,
    OperationalCapability,
    OperationalCapabilityRegistry,
)
from workstation.operational_kernel import OperationalKernel


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


def test_capability_invocation_is_durable_with_real_run_operation_authority_lineage(temp_dir):
    artifacts = ArtifactStore(root_dir=temp_dir / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts=artifacts, root=temp_dir / "capabilities")
    kernel = OperationalKernel(registry=registry, artifacts=artifacts)

    # Register a base operational capability
    cap = OperationalCapability(
        id="cap_write_lineage",
        name="Write Lineage Cap",
        version="1.0.0",
        effect="state_mutation",
        route="filesystem",
        scope={"backends": {"filesystem": {}}},
        implementation={
            "steps": [
                {
                    "id": "write_1",
                    "primitive": "fs_write",
                    "args": {"path": str(temp_dir / "lineage.txt"), "content": "Lineage verified"},
                }
            ]
        },
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
    )
    registry.register(cap)

    auth_scope = {
        "level": "local_mutation",
        "allowed_actions": ["write"],
        "allowed_resources": ["filesystem"],
    }
    task_id = "task_lineage_001"
    run_id = "run_lineage_001"
    operation_id = "op_lineage_001"

    exec_context = {
        "task_id": task_id,
        "run_id": run_id,
        "operation_id": operation_id,
        "authority_scope": auth_scope,
        "semantic_state_before": {"file_exists": False},
        "semantic_state": {"file_exists": True},
    }

    result = kernel.execute_capability(
        "cap_write_lineage",
        inputs={},
        context=exec_context,
    )
    assert result["success"] is True

    # Check that in-memory invocations captured the execution
    assert len(kernel.invocations) == 1
    inv = kernel.invocations[0]
    assert inv.task_id == task_id
    assert inv.run_id == run_id
    assert inv.operation_id == operation_id
    assert inv.status == "ACKNOWLEDGED"
    assert inv.verified is False
    assert inv.verifier_status == "INCONCLUSIVE"
    assert inv.authority_scope["level"] == "local_mutation"

    # Simulate restart by creating a new kernel instance with the same artifact store
    new_kernel = OperationalKernel(registry=registry, artifacts=artifacts)
    assert len(new_kernel.invocations) == 0

    # Reload invocations from ArtifactStore
    reloaded_invocations = new_kernel.load_invocations(task_id)
    assert len(reloaded_invocations) == 1
    reloaded = reloaded_invocations[0]

    assert reloaded.task_id == task_id
    assert reloaded.run_id == run_id
    assert reloaded.operation_id == operation_id
    assert reloaded.status == "ACKNOWLEDGED"
    assert reloaded.verified is False
    assert reloaded.verifier_status == "INCONCLUSIVE"
    assert reloaded.authority_scope["level"] == "local_mutation"
    assert reloaded.state_after.get("file_exists") is True


def test_recurrence_only_proposes_composite_candidate_not_promoted(temp_dir):
    artifacts = ArtifactStore(root_dir=temp_dir / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts=artifacts, root=temp_dir / "capabilities")
    compiler = HierarchicalExperienceCompiler(registry=registry)

    # Register two child capabilities with PROMOTED lifecycle
    cap_a = OperationalCapability(
        id="cap_child_a",
        name="Child A",
        version="1.0.0",
        effect="read_only",
        route="filesystem",
        scope={"backends": {"filesystem": {}}},
        implementation={"steps": [{"primitive": "fs_read", "args": {"path": "dummy_a"}}]},
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
    )
    cap_b = OperationalCapability(
        id="cap_child_b",
        name="Child B",
        version="1.0.0",
        effect="read_only",
        route="filesystem",
        scope={"backends": {"filesystem": {}}},
        implementation={"steps": [{"primitive": "fs_read", "args": {"path": "dummy_b"}}]},
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
    )
    registry.register(cap_a)
    registry.register(cap_b)

    # Propose composite
    composite = compiler.propose_composite(["cap_child_a", "cap_child_b"])

    # Must be DISCOVERED, NEVER directly PROMOTED
    assert composite.lifecycle == CapabilityLifecycle.DISCOVERED
    assert composite.dependencies[0].capability_id == "cap_child_a"
    assert composite.dependencies[1].capability_id == "cap_child_b"

    # Verify registered in registry as DISCOVERED
    fetched = registry.get(composite.id)
    assert fetched is not None
    assert fetched.lifecycle == CapabilityLifecycle.DISCOVERED

    # Promoted-only search in registry must NOT return it
    promoted_list = registry.list_capabilities(lifecycle=CapabilityLifecycle.PROMOTED)
    assert composite.id not in [c.id for c in promoted_list]


def test_composite_promotion_requires_causal_replay_policy(temp_dir):
    artifacts = ArtifactStore(root_dir=temp_dir / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts=artifacts, root=temp_dir / "capabilities")
    compiler = HierarchicalExperienceCompiler(registry=registry)

    cap_a = OperationalCapability(
        id="cap_sub_1",
        name="Sub 1",
        version="1.0.0",
        effect="read_only",
        route="filesystem",
        implementation={"steps": [{"primitive": "fs_read", "args": {"path": "dummy"}}]},
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
    )
    cap_b = OperationalCapability(
        id="cap_sub_2",
        name="Sub 2",
        version="1.0.0",
        effect="read_only",
        route="filesystem",
        implementation={"steps": [{"primitive": "fs_read", "args": {"path": "dummy"}}]},
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
    )
    registry.register(cap_a)
    registry.register(cap_b)

    composite = compiler.propose_composite(["cap_sub_1", "cap_sub_2"])

    # 1. Attempt promotion without causal replay evidence -> MUST FAIL
    with pytest.raises(CapabilityValidationError) as excinfo:
        compiler.promote_composite(composite)
    assert "composite promotion denied" in str(excinfo.value)

    # 2. Provide required causal replay and admission metadata
    composite.postconditions = [{"key": "read_completed", "expected": True}]
    composite.semantic_fingerprint = "sem_fp_test_123"
    composite.compatibility_fingerprint = "compat_fp_test_123"
    composite.causal_grade = CausalGrade.REPLAY_VALIDATED
    composite.trust_class = "trusted_runtime"
    composite.taint = []
    composite.drift_state = "healthy"
    composite.learning_metadata.update({
        "semantic_closure": True,
        "parameterization_quality": True,
        "evidence_strength": 2,
        "provenance_complete": True,
        "authority_origins": ["user", "system"],
        "run_ids": ["run_1", "run_2"],
        "drift_rate": 0.0,
        "unresolved_counterexamples": 0,
        "utility": 100,
        "risk": "ordinary",
        "blast_radius": 0,
        "requires_approval": False,
    })
    composite.validation_evidence = [
        {
            "kind": "controlled_replay",
            "passed": True,
            "compatibility_fingerprint": "compat_fp_test_123",
            "result": {
                "evidence_refs": ["ref_replay_01"],
                "evidence_strength": 2,
            },
        }
    ]
    from workstation.control_plane.verification import VerificationContract, VerificationLifecycle
    from workstation.execution_policy import EvidenceStrength
    composite.verifier_contract = VerificationContract(
        covered_predicates=("read_completed",), observer="fixture.readback",
        source_kind="test_fixture", minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        allowed_trust=("trusted_runtime",), lifecycle=VerificationLifecycle.VALIDATED,
        validation_receipts=(
            {"kind": "positive_replay", "passed": True, "phase": "validation", "evidence_ref": "positive"},
            {"kind": "negative_control", "passed": True, "phase": "validation", "evidence_ref": "negative"},
        ),
    ).to_dict()

    promoted = compiler.promote_composite(composite)
    assert promoted.lifecycle == CapabilityLifecycle.PROMOTED
    fetched = registry.get(composite.id)
    assert fetched.lifecycle == CapabilityLifecycle.PROMOTED


def test_child_drift_or_pin_change_blocks_composite_execution(temp_dir):
    artifacts = ArtifactStore(root_dir=temp_dir / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts=artifacts, root=temp_dir / "capabilities")
    compiler = HierarchicalExperienceCompiler(registry=registry)
    kernel = OperationalKernel(registry=registry, artifacts=artifacts)

    file_a = temp_dir / "drift_a.txt"
    file_b = temp_dir / "drift_b.txt"

    cap_a = OperationalCapability(
        id="cap_drift_child_a",
        name="Drift Child A",
        version="1.0.0",
        effect="state_mutation",
        route="filesystem",
        scope={"backends": {"filesystem": {}}},
        implementation={"steps": [{"primitive": "fs_write", "args": {"path": str(file_a), "content": "hello a"}}]},
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
    )
    cap_b = OperationalCapability(
        id="cap_drift_child_b",
        name="Drift Child B",
        version="1.0.0",
        effect="state_mutation",
        route="filesystem",
        scope={"backends": {"filesystem": {}}},
        implementation={"steps": [{"primitive": "fs_write", "args": {"path": str(file_b), "content": "hello b"}}]},
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
    )
    registry.register(cap_a)
    registry.register(cap_b)

    composite = compiler.propose_composite(["cap_drift_child_a", "cap_drift_child_b"])

    # 1. Successful execution when both children are healthy
    result = kernel.execute_capability(composite.id, inputs={})
    assert result["success"] is True
    assert file_a.exists() and file_b.exists()

    # 2. Child drift blocks composite execution
    cap_a.drift_state = "quarantined"
    registry.register(cap_a)

    with pytest.raises(CapabilityDriftError) as excinfo:
        kernel.execute_capability(composite.id, inputs={})
    assert "quarantined" in str(excinfo.value)

    # Restore child_a to healthy
    cap_a.drift_state = "healthy"
    registry.register(cap_a)

    # 3. Pin change blocks composite execution
    # Pin child_a to version 0.9.0 while registry has 1.0.0
    context_with_stale_pin = {
        "capability_pins": {
            "cap_drift_child_a": {"version": "0.9.0"}
        }
    }
    with pytest.raises(CapabilityDriftError) as excinfo:
        kernel.execute_capability(composite.id, inputs={}, context=context_with_stale_pin)
    assert "pin changed from 0.9.0 to 1.0.0" in str(excinfo.value)

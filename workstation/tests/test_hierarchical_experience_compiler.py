"""Tests for Phase P3: Hierarchical Operational Learning & Composite OperationalCapability."""
import pytest

from workstation.artifacts import ArtifactStore
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.ir import EQ, SET
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.experience_compiler.hierarchical import HierarchicalExperienceCompiler
from workstation.experience_compiler.models import CapabilityInvocation
from workstation.operational_capabilities import (
    CapabilityDriftError,
    CapabilityLifecycle,
    OperationalCapability,
    OperationalCapabilityRegistry,
)
from workstation.operational_kernel import OperationalKernel


@pytest.fixture
def clean_registry(tmp_path):
    artifacts = ArtifactStore(tmp_path / "artifacts")
    return OperationalCapabilityRegistry(artifacts)


def test_capability_invocation_is_persisted_only_after_verified_execution(clean_registry):
    """OperationalKernel captures CapabilityInvocation upon verified execution."""
    kernel = OperationalKernel(registry=clean_registry)
    cap = OperationalCapability(
        id="cap.test.primitive",
        name="Test primitive",
        route="host_process",
        effect="read_only",
        lifecycle=CapabilityLifecycle.PROMOTED,
        implementation={"output": {"msg": "done"}},
    )
    clean_registry.register(cap)

    # Successful execution captures invocation
    result = kernel.execute_capability(cap.id, {"x": 1})
    assert result["success"] is True
    assert len(kernel.invocations) == 1
    inv = kernel.invocations[0]
    assert inv.capability_id == cap.id
    assert inv.status == "ACKNOWLEDGED"
    assert inv.verified is False
    assert inv.verifier_status == "INCONCLUSIVE"
    assert inv.inputs == {"x": 1}

    # Failed execution does not record a committed successful invocation
    failing_cap = OperationalCapability(
        id="cap.failing",
        name="Failing primitive",
        route="host_process",
        preconditions=[{"type": "field_equals", "field": "inputs.must_be_true", "expected": True}],
        implementation={"output": {"msg": "done"}},
    )
    clean_registry.register(failing_cap)

    initial_count = len(kernel.invocations)
    with pytest.raises(CapabilityDriftError):
        kernel.execute_capability(failing_cap.id, {"must_be_true": False})
    assert len(kernel.invocations) == initial_count


def test_repeated_capability_sequence_proposes_composite(clean_registry):
    """HierarchicalExperienceCompiler mines recurring sequences and proposes composite without flattening."""
    cap_a = OperationalCapability(
        id="cap.checkout_repo",
        name="Checkout repo",
        route="host_process",
        effect="state_mutation",
        lifecycle=CapabilityLifecycle.PROMOTED,
        family_id="vcs:checkout",
        formal_contract=CapabilityFormalContract(
            operation_family="vcs",
            target_family="checkout",
            typed_postconditions=[EQ("repo.checked_out", True)],
            effect_footprint=[SET("repo.checked_out", True)],
            authority_required=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"vcs"}),
        ),
        implementation={"output": {"repo_path": "/tmp/repo"}},
    )
    cap_b = OperationalCapability(
        id="cap.run_tests",
        name="Run tests",
        route="host_process",
        effect="read_only",
        lifecycle=CapabilityLifecycle.PROMOTED,
        family_id="ci:test",
        formal_contract=CapabilityFormalContract(
            operation_family="ci",
            target_family="test",
            typed_postconditions=[EQ("tests.passed", True)],
            effect_footprint=[],
            authority_required=AuthorityScope(level=AuthorityLevel.READ, allowed_actions={"test"}),
        ),
        implementation={"output": {"tests_passed": True}},
    )
    clean_registry.register(cap_a)
    clean_registry.register(cap_b)

    invocations = [
        # Run 1: A -> B
        CapabilityInvocation(invocation_id="inv1", capability_id=cap_a.id, run_id="run-1", verified=True, status="COMMITTED"),
        CapabilityInvocation(invocation_id="inv2", capability_id=cap_b.id, run_id="run-1", verified=True, status="COMMITTED"),
        # Run 2: A -> B
        CapabilityInvocation(invocation_id="inv3", capability_id=cap_a.id, run_id="run-2", verified=True, status="COMMITTED"),
        CapabilityInvocation(invocation_id="inv4", capability_id=cap_b.id, run_id="run-2", verified=True, status="COMMITTED"),
    ]

    compiler = HierarchicalExperienceCompiler(clean_registry)
    sequences = compiler.mine_sequences(invocations, min_support=2)
    assert [cap_a.id, cap_b.id] in sequences

    composite = compiler.propose_composite([cap_a.id, cap_b.id])
    assert composite.route == "composite"
    assert len(composite.dependencies) == 2
    assert composite.dependencies[0].capability_id == cap_a.id
    assert composite.dependencies[1].capability_id == cap_b.id
    assert composite.family_id == "vcs:checkout->ci:test"
    assert composite.formal_contract is not None
    assert composite.formal_contract.authority_required.level == AuthorityLevel.LOCAL_MUTATION
    assert composite.learning_metadata["composite"] is True


def test_promoted_composite_preserves_child_dependencies_and_executes(clean_registry):
    """Composite execution sequentially resolves and invokes child dependencies."""
    kernel = OperationalKernel(registry=clean_registry)
    cap_step1 = OperationalCapability(
        id="cap.step1",
        name="Step 1",
        route="host_process",
        lifecycle=CapabilityLifecycle.PROMOTED,
        implementation={"output": {"val": 42}},
    )
    cap_step2 = OperationalCapability(
        id="cap.step2",
        name="Step 2",
        route="host_process",
        lifecycle=CapabilityLifecycle.PROMOTED,
        implementation={"output": {"success": True, "result": "computed"}},
    )
    clean_registry.register(cap_step1)
    clean_registry.register(cap_step2)

    compiler = HierarchicalExperienceCompiler(clean_registry)
    composite = compiler.propose_composite([cap_step1.id, cap_step2.id])
    clean_registry.register(composite)

    res = kernel.execute_capability(composite.id, {})
    assert res["success"] is True
    assert "step_0" in res["output"]["deps"]
    assert res["output"]["deps"]["step_0"]["output"]["val"] == 42
    assert res["output"]["deps"]["step_1"]["output"]["result"] == "computed"


def test_child_drift_or_quarantine_blocks_composite_execution(clean_registry):
    """If any child dependency drifts or is quarantined, composite execution fails closed."""
    kernel = OperationalKernel(registry=clean_registry)
    cap_a = OperationalCapability(
        id="cap.healthy_a",
        name="Healthy A",
        route="host_process",
        lifecycle=CapabilityLifecycle.PROMOTED,
        implementation={"output": {"ok": True}},
    )
    cap_b = OperationalCapability(
        id="cap.drifted_b",
        name="Drifted B",
        route="host_process",
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
        implementation={"output": {"ok": True}},
    )
    clean_registry.register(cap_a)
    clean_registry.register(cap_b)

    compiler = HierarchicalExperienceCompiler(clean_registry)
    composite = compiler.propose_composite([cap_a.id, cap_b.id])
    clean_registry.register(composite)

    # Now simulate operational drift / quarantine on child B
    clean_registry.record_drift(cap_b.id, "regression detected in downstream API", quarantine=True)

    with pytest.raises(CapabilityDriftError, match="quarantined"):
        kernel.execute_capability(composite.id, {})

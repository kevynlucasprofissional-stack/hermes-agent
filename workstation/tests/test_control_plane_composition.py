"""Behavior tests for CP3: Bounded Backward-Chaining Composition, CompositionCertificate, and Threat Detection."""
from __future__ import annotations

import pytest

from workstation.contracts import AcceptanceContract
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.intent import OperationIntent, OperationMode
from workstation.control_plane.ir import (
    AND, CALL, CREATE, DELETE, EQ, EXISTS, NOT, OR, SET, TRUE, UNCHANGED, ABSENT, Effect, Predicate
)
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.operational_capabilities import (
    CapabilityLifecycle, OperationalCapability, OperationalCapabilityRegistry
)
from workstation.control_plane.verification import VerificationContract, VerificationLifecycle
from workstation.execution_policy import EvidenceStrength


def _validated_verifier(*predicates):
    return VerificationContract(
        covered_predicates=tuple(p.fingerprint() for p in predicates), observer="owner.readback",
        source_kind="source_of_record", minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        allowed_trust=("trusted_owner",), lifecycle=VerificationLifecycle.VALIDATED,
    )


@pytest.fixture
def clean_registry(tmp_path):
    from workstation.artifacts import ArtifactStore
    store = ArtifactStore(tmp_path / "artifacts")
    return OperationalCapabilityRegistry(artifacts=store, root=tmp_path / "capabilities")


def test_composition_backward_chaining_success(clean_registry):
    """Prove backward chaining C1 -> C2 achieves Goal and produces CompositionCertificate."""
    from workstation.control_plane.composition import CompositionEngine
    from workstation.control_plane.router import CapabilityRouter, ComposedDecision

    # C1: git.fetch: requires True, produces remote_refs_fetched=True
    c1 = OperationalCapability(
        id="git.fetch",
        name="Git Fetch",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="git.fetch",
            target_family="git.repository",
            typed_preconditions=[TRUE()],
            typed_postconditions=[EQ("git.remote_refs_fetched", True)],
            effect_footprint=[CALL("git.fetch", "repo")],
            authority_required=AuthorityScope(level=AuthorityLevel.READ, allowed_actions={"git.fetch"}, allowed_resources={"repo"}),
            verifier=_validated_verifier(EQ("git.remote_refs_fetched", True)),
        ),
    )
    clean_registry.register(c1)

    # C2: git.fast_forward: requires remote_refs_fetched=True, produces local_synced=True
    c2 = OperationalCapability(
        id="git.fast_forward",
        name="Git Fast Forward",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            operation_family="git.fast_forward",
            target_family="git.repository",
            typed_preconditions=[EQ("git.remote_refs_fetched", True)],
            typed_postconditions=[EQ("git.local_synced", True)],
            effect_footprint=[CALL("git.fast_forward", "repo"), SET("git.local_synced", True)],
            authority_required=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"git.fast_forward", "set"}, allowed_resources={"repo"}),
            verifier=_validated_verifier(EQ("git.local_synced", True)),
        ),
    )
    clean_registry.register(c2)

    intent = OperationIntent(
        id="intent-sync",
        target="repo",
        goal=EQ("git.local_synced", True),
        effect_budget=[
            CALL("git.fetch", "repo"),
            CALL("git.fast_forward", "repo"),
            SET("git.local_synced", True),
        ],
    )

    state = {"git": {"remote_refs_fetched": False, "local_synced": False}}
    granted_authority = AuthorityScope(
        level=AuthorityLevel.LOCAL_MUTATION,
        allowed_actions={"git.fetch", "git.fast_forward", "set"},
        allowed_resources={"repo"},
    )

    engine = CompositionEngine(clean_registry)
    router = CapabilityRouter(clean_registry, composition_engine=engine)
    decision = router.route(intent, state, granted_authority)

    assert isinstance(decision, ComposedDecision)
    assert decision.is_dispatchable is True
    assert [c.id for c in decision.plan] == ["git.fetch", "git.fast_forward"]
    cert = decision.certificate
    assert cert.is_valid() is True
    assert cert.goal_coverage is True
    assert cert.effect_containment is True
    assert cert.authority_satisfied is True


def test_composition_effect_union_exceeds_budget_rejected(clean_registry):
    """If the union of child effects exceeds intent budget -> reject composition."""
    from workstation.control_plane.composition import CompositionEngine
    from workstation.control_plane.router import CapabilityRouter, ComposedDecision

    c1 = OperationalCapability(
        id="step1",
        name="Step 1",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            typed_preconditions=[TRUE()],
            typed_postconditions=[EQ("p1", True)],
            # Produces an extra effect not in Intent budget!
            effect_footprint=[SET("p1", True), DELETE("extra_resource")],
            authority_required=AuthorityScope(level=AuthorityLevel.EXTERNAL_IRREVERSIBLE, allowed_actions={"*"}),
            verifier={"kind": "v"},
        ),
    )
    clean_registry.register(c1)

    c2 = OperationalCapability(
        id="step2",
        name="Step 2",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            typed_preconditions=[EQ("p1", True)],
            typed_postconditions=[EQ("goal_state", True)],
            effect_footprint=[SET("goal_state", True)],
            authority_required=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"*"}),
            verifier={"kind": "v"},
        ),
    )
    clean_registry.register(c2)

    intent = OperationIntent(
        id="intent-no-delete",
        goal=EQ("goal_state", True),
        # Notice: DELETE("extra_resource") is NOT in budget!
        effect_budget=[SET("p1", True), SET("goal_state", True)],
    )

    engine = CompositionEngine(clean_registry)
    router = CapabilityRouter(clean_registry, composition_engine=engine)
    decision = router.route(intent, {"p1": False, "goal_state": False}, AuthorityScope(level=AuthorityLevel.EXTERNAL_IRREVERSIBLE, allowed_actions={"*"}))

    assert not isinstance(decision, ComposedDecision)


def test_composition_child_mutation_not_hidden_by_read_parent(clean_registry):
    """Authority of composition is JOIN of all children; child mutation requires write authority."""
    from workstation.control_plane.composition import CompositionEngine
    from workstation.control_plane.router import CapabilityRouter, ComposedDecision, HumanDecision

    c1 = OperationalCapability(
        id="step1_read",
        name="Read Step",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            typed_preconditions=[TRUE()],
            typed_postconditions=[EQ("read_done", True)],
            effect_footprint=[],
            authority_required=AuthorityScope(level=AuthorityLevel.READ),
            verifier={"kind": "v"},
        ),
    )
    clean_registry.register(c1)

    c2 = OperationalCapability(
        id="step2_write",
        name="Write Step",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            typed_preconditions=[EQ("read_done", True)],
            typed_postconditions=[EQ("goal_written", True)],
            effect_footprint=[SET("goal_written", True)],
            authority_required=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"set"}, allowed_resources={"goal_written"}),
            verifier={"kind": "v"},
        ),
    )
    clean_registry.register(c2)

    intent = OperationIntent(
        id="intent-join-auth",
        goal=EQ("goal_written", True),
        effect_budget=[SET("goal_written", True)],
    )

    # Granted authority is only READ!
    granted_auth = AuthorityScope(level=AuthorityLevel.READ, allowed_actions={"*"})

    engine = CompositionEngine(clean_registry)
    router = CapabilityRouter(clean_registry, composition_engine=engine)
    decision = router.route(intent, {"read_done": False, "goal_written": False}, granted_auth)

    # Must NOT compose and dispatch with insufficient authority
    assert not isinstance(decision, ComposedDecision)


def test_composition_threat_detection_and_reordering(clean_registry):
    """Intermediate effect threatening future precondition is detected and reordered if safe."""
    from workstation.control_plane.composition import CompositionEngine, detect_causal_threats, reorder_plan
    from workstation.control_plane.contract import CapabilityFormalContract

    # C_create: creates file A
    c_create = OperationalCapability(
        id="c_create",
        name="Create A",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            typed_preconditions=[TRUE()],
            typed_postconditions=[EXISTS("file_A")],
            effect_footprint=[CREATE("file_A")],
            verifier={"kind": "v"},
        ),
    )
    # C_clean: deletes temp directory (which contains file A)
    c_clean = OperationalCapability(
        id="c_clean",
        name="Clean Temp",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            typed_preconditions=[TRUE()],
            typed_postconditions=[ABSENT("temp_dir")],
            effect_footprint=[DELETE("file_A"), DELETE("temp_dir")],
            verifier={"kind": "v"},
        ),
    )
    # C_read: reads file A (requires file A to exist)
    c_read = OperationalCapability(
        id="c_read",
        name="Read A",
        version="1.0.0",
        lifecycle=CapabilityLifecycle.PROMOTED,
        formal_contract=CapabilityFormalContract(
            typed_preconditions=[EXISTS("file_A")],
            typed_postconditions=[EQ("read_done", True)],
            effect_footprint=[],
            verifier={"kind": "v"},
        ),
    )

    # Candidate plan: c_create -> c_clean -> c_read
    # c_clean destroys file_A before c_read can read it!
    plan_with_threat = [c_create, c_clean, c_read]
    threats = detect_causal_threats(plan_with_threat)
    assert len(threats) > 0
    assert threats[0]["threatening_step"] == "c_clean"
    assert threats[0]["threatened_step"] == "c_read"

    # Reordering: c_create -> c_read -> c_clean is safe!
    safe_plan = reorder_plan(plan_with_threat)
    assert safe_plan is not None
    assert [c.id for c in safe_plan] == ["c_create", "c_read", "c_clean"]
    assert len(detect_causal_threats(safe_plan)) == 0


def test_composition_budget_exhaustion_wakes_llm(clean_registry):
    """When backward chaining exceeds max_depth -> falls back to WAKE_LLM."""
    from workstation.control_plane.composition import CompositionEngine
    from workstation.control_plane.router import CapabilityRouter, ReasoningDecision

    # Chain of 10 capabilities: step_0 -> step_1 -> ... -> step_9
    for i in range(10):
        c = OperationalCapability(
            id=f"chain_step_{i}",
            name=f"Chain Step {i}",
            version="1.0.0",
            lifecycle=CapabilityLifecycle.PROMOTED,
            formal_contract=CapabilityFormalContract(
                typed_preconditions=[EQ(f"p_{i}", True)] if i > 0 else [TRUE()],
                typed_postconditions=[EQ(f"p_{i+1}", True)],
                effect_footprint=[SET(f"p_{i+1}", True)],
                verifier={"kind": "v"},
            ),
        )
        clean_registry.register(c)

    intent = OperationIntent(
        id="intent-deep",
        goal=EQ("p_10", True),
        effect_budget=[SET(f"p_{i}", True) for i in range(11)],
    )

    # Set engine max_depth = 3 (less than 10)
    engine = CompositionEngine(clean_registry, max_depth=3)
    router = CapabilityRouter(clean_registry, composition_engine=engine)
    decision = router.route(intent, {"p_0": True}, AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={"*"}))

    assert isinstance(decision, ReasoningDecision)
    assert decision.reason in {"composition_budget_exhausted", "no_certifiable_capability_found"}

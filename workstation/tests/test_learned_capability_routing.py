"""Tests for Phase P1: Experience Compiler <-> Capability Router Bridge."""
import json
import pytest

from workstation.artifacts import ArtifactStore
from workstation.control_plane.contract import CapabilityFormalContract
from workstation.control_plane.intent import OperationIntent
from workstation.control_plane.ir import EQ, SET, AND
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.router import CapabilityRouter, ExecutableDecision
from workstation.experience_compiler.compiler import ExperienceCompiler
from workstation.experience_compiler.models import (
    AuthorityOrigin,
    EvidenceStrength,
    Operation,
    Provenance,
    SemanticState,
    StateDelta,
    TransitionOutcome,
    TransitionSample,
    Verification,
)
from workstation.experience_compiler.promotion import (
    ExperiencePromotionPolicy,
    derive_formal_contract,
)
from workstation.operational_capabilities import (
    CapabilityLifecycle,
    OperationalCapability,
    OperationalCapabilityRegistry,
)


def _sample(primitive, run="r1", before=None, after=None, parameters=None, effect="read_only", verified=True, authority_origin=AuthorityOrigin.USER, authority_scope=None):
    a = SemanticState(semantic_predicates=before or {})
    b = SemanticState(semantic_predicates=after or {})
    return TransitionSample(
        state_before=a,
        state_after=b,
        delta=StateDelta.between(a, b),
        operation=Operation(
            primitive=primitive,
            canonical_route="native_browser",
            target_family="github_pr",
            operation_family="merge_pr",
            parameters=parameters or {},
            effect_class=effect,
            scope={"host": "github.com"},
        ),
        verification=Verification(
            EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
            "owner_readback",
            b.semantic_predicates if verified else {},
            ["artifact://proof"],
        ),
        outcome=TransitionOutcome.VERIFIED_SUCCESS if verified else TransitionOutcome.FAILED,
        provenance=Provenance(
            task_id="task-1",
            run_id=run,
            operation_id=primitive,
            runtime="electron-chromium",
            source="fixture",
            authority_origin=authority_origin,
            trust_class="trusted_runtime",
            authority_ref="auth://ref-1" if authority_scope else None,
            authority_scope=authority_scope,
        ),
    )


def test_provenance_authority_fields_roundtrip():
    """Provenance persists authority_ref and authority_scope without leaking handles."""
    scope = {"level": 2, "allowed_actions": ["merge_pr"], "allowed_resources": ["github_pr"]}
    p = Provenance(
        task_id="task-1",
        run_id="run-1",
        operation_id="op-1",
        runtime="electron-chromium",
        authority_origin=AuthorityOrigin.USER,
        trust_class="trusted_runtime",
        authority_ref="artifact://auth/grant-1",
        authority_scope=scope,
    )
    d = p.__dict__
    assert d["authority_ref"] == "artifact://auth/grant-1"
    assert d["authority_scope"] == scope

    sample = TransitionSample(provenance=p)
    serialized = sample.to_dict()
    assert serialized["provenance"]["authority_ref"] == "artifact://auth/grant-1"
    assert serialized["provenance"]["authority_scope"]["level"] == 2

    restored = TransitionSample.from_dict(serialized)
    assert restored.provenance.authority_ref == "artifact://auth/grant-1"
    assert restored.provenance.authority_scope["level"] == 2


def test_derive_formal_contract_refuses_unproven_authority():
    """Derivation fails closed (returns None) if mutation authority origin is unproven or untrusted."""
    cap = OperationalCapability(
        id="cap.untrusted",
        name="Untrusted mutation",
        effect="state_mutation",
        route="native_browser",
        scope={"host": "github.com"},
        learning_metadata={
            "effects": {"pr_merged": True},
            "preconditions": {"pr_open": True},
            "authority_origins": ["environment"],  # untrusted origin!
            "operation_families": ["merge_pr"],
            "target_families": ["github_pr"],
            "evidence_strength": 2,
        },
    )
    contract = derive_formal_contract(cap)
    assert contract is None


def test_derive_formal_contract_derives_contract_and_family_id():
    """Derivation produces valid CapabilityFormalContract with typed predicates and correct family_id."""
    cap = OperationalCapability(
        id="cap.trusted",
        name="Trusted merge",
        effect="state_mutation",
        route="native_browser",
        scope={"host": "github.com"},
        provenance={
            "source": "experience_compiler",
            "origins": [{
                "authority_scope": {
                    "level": 1,
                    "allowed_actions": ["merge_pr", "native_browser"],
                    "allowed_resources": ["github_pr"],
                }
            }],
        },
        learning_metadata={
            "effects": {"pr_merged": True},
            "preconditions": {"pr_open": True},
            "authority_origins": ["user"],
            "operation_families": ["merge_pr"],
            "target_families": ["github_pr"],
            "evidence_strength": 2,
        },
    )
    contract = derive_formal_contract(cap)
    assert contract is not None
    assert contract.operation_family == "merge_pr"
    assert contract.target_family == "github_pr"
    assert len(contract.typed_preconditions) == 1
    assert contract.typed_preconditions[0].to_dict() == {"type": "EQ", "path": "pr_open", "value": True}
    assert len(contract.typed_postconditions) == 1
    assert contract.typed_postconditions[0].to_dict() == {"type": "EQ", "path": "pr_merged", "value": True}
    assert len(contract.effect_footprint) == 1
    assert contract.effect_footprint[0].to_dict() == {"kind": "SET", "path": "pr_merged", "value": True}
    assert contract.authority_required.level == AuthorityLevel.LOCAL_MUTATION


def test_learned_contract_fails_on_multiple_operation_families():
    """Incompatible operation families block formal contract derivation fail-closed."""
    cap = OperationalCapability(
        id="cap.ambiguous_op",
        name="Ambiguous Op",
        effect="state_mutation",
        learning_metadata={
            "effects": {"done": True},
            "operation_families": ["op_a", "op_b"],
            "target_families": ["tgt_a"],
            "authority_origins": ["user"],
            "explicit_authority_scope": {"level": 1, "allowed_actions": ["*"], "allowed_resources": ["*"]},
        },
    )
    assert derive_formal_contract(cap) is None


def test_learned_contract_fails_on_multiple_target_families():
    """Incompatible target families block formal contract derivation fail-closed."""
    cap = OperationalCapability(
        id="cap.ambiguous_tgt",
        name="Ambiguous Target",
        effect="state_mutation",
        learning_metadata={
            "effects": {"done": True},
            "operation_families": ["op_a"],
            "target_families": ["tgt_a", "tgt_b"],
            "authority_origins": ["user"],
            "explicit_authority_scope": {"level": 1, "allowed_actions": ["*"], "allowed_resources": ["*"]},
        },
    )
    assert derive_formal_contract(cap) is None


def test_learned_contract_fails_on_mutation_without_explicit_authority_scope():
    """Learned mutation without trusted explicit authority scope never becomes generically routable."""
    cap = OperationalCapability(
        id="cap.no_auth_scope",
        name="No Auth Scope Mutation",
        effect="state_mutation",
        learning_metadata={
            "effects": {"done": True},
            "operation_families": ["op_a"],
            "target_families": ["tgt_a"],
            "authority_origins": ["user"],  # origin string alone cannot fabricate authority
        },
    )
    assert derive_formal_contract(cap) is None


def test_learned_capability_routes_via_operation_intent_without_llm(tmp_path):
    """A promoted capability derived from experience is routed by OperationIntent without LLM."""
    artifacts = ArtifactStore(tmp_path / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts)

    auth_scope = {"level": 1, "allowed_actions": ["merge_pr", "native_browser"], "allowed_resources": ["github_pr"]}

    # 1. Compile traces across 2 runs with verified successes
    traces = [
        [
            _sample("browser_navigate", run="r1", before={"pr_open": True}, after={"pr_open": True}),
            _sample(
                "browser_click",
                run="r1",
                before={"pr_open": True},
                after={"pr_open": False, "pr_merged": True},
                parameters={"semantic_anchor": {"type": "testid", "value": "merge-btn"}},
                effect="state_mutation",
                authority_scope=auth_scope,
            ),
        ],
        [
            _sample("browser_navigate", run="r2", before={"pr_open": True}, after={"pr_open": True}),
            _sample(
                "browser_click",
                run="r2",
                before={"pr_open": True},
                after={"pr_open": False, "pr_merged": True},
                parameters={"semantic_anchor": {"type": "testid", "value": "merge-btn"}},
                effect="state_mutation",
                authority_scope=auth_scope,
            ),
        ],
    ]

    compiler = ExperienceCompiler(registry)
    cap = compiler.compile(traces)
    assert cap is not None
    assert cap.formal_contract is not None
    assert cap.family_id == "merge_pr:github_pr"

    # 2. Promote capability with controlled replay validation
    from workstation.experience_compiler.models import CausalGrade
    cap.causal_grade = CausalGrade.REPLAY_VALIDATED
    cap.validation_evidence = [{
        'kind': 'controlled_replay',
        'passed': True,
        'compatibility_fingerprint': cap.compatibility_fingerprint,
        'result': {'evidence_refs': ['artifact://proof'], 'evidence_strength': 2},
    }]
    admission = compiler.promote(cap)
    assert admission.admitted is True
    assert cap.lifecycle == CapabilityLifecycle.PROMOTED

    # 3. Route through CapabilityRouter with OperationIntent
    router = CapabilityRouter(registry)
    intent = OperationIntent(
        id="intent-merge",
        target="github_pr",
        goal=EQ("pr_merged", True),
        effect_budget=[SET("pr_merged", True), SET("pr_open", False)],
        metadata={"target_family": "github_pr", "operation_family": "merge_pr"},
    )
    current_state = {"pr_open": True, "pr_merged": False}
    authority = AuthorityScope(
        level=AuthorityLevel.LOCAL_MUTATION,
        allowed_actions={"merge_pr", "native_browser"},
        allowed_resources={"github_pr"},
    )

    decision = router.route(intent, current_state, authority_scope=authority)

    # 4. Verify pure deterministic route without LLM
    assert isinstance(decision, ExecutableDecision)
    assert decision.capability.id == cap.id
    assert decision.certificate.is_valid() is True
    assert decision.certificate.capability_id == cap.id
    assert decision.certificate.target_match is True
    assert decision.certificate.goal_coverage is True

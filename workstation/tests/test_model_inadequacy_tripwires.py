"""Test suite for H-077 Priority 3: Model-Inadequacy Tripwires.

Validates:
- Tripwire model_inadequacy_non_discriminable_outcome fires when hypotheses cannot be discriminated.
- Generalization is suspended upon non-discriminable counterexample.
- Capability is quarantined upon model inadequacy detection.
- ExperiencePromotionPolicy strictly blocks automatic promotion of inadequate capabilities.
- ORAMetrics records model inadequacy events and reasons without synthetic denominators.
- ValidityEnvelope diagnostic projection marks model_inadequacy_suspected=True and is_valid_for_reuse=False.
"""
from copy import deepcopy
import pytest

from workstation.control_plane.metrics import ORAMetrics, ORAMetricsCollector
from workstation.control_plane.validity_envelope import derive_validity_envelope
from workstation.experience_compiler.causal import refine_counterexample
from workstation.experience_compiler.models import CausalGrade
from workstation.experience_compiler.promotion import ExperiencePromotionPolicy
from workstation.operational_capabilities import CapabilityLifecycle, OperationalCapability


def test_non_discriminable_counterexample_raises_tripwire_and_quarantines():
    """Non-discriminable counterexample raises model_inadequacy_non_discriminable_outcome."""
    cap = OperationalCapability(
        id="cap_tripwire_test",
        name="Tripwire Test Capability",
        version="1.0.0",
        effect="state_mutation",
        route="workstation",
        trust_class="trusted_runtime",
        lifecycle=CapabilityLifecycle.PROMOTED,
        drift_state="healthy",
        learning_metadata={
            "preconditions": {"service_up": True, "auth_valid": True},
        },
        causal_grade=CausalGrade.REPLAY_VALIDATED,
    )

    positive_states = [
        {"service_up": True, "auth_valid": True},
        {"service_up": True, "auth_valid": True},
    ]

    # Counterexample has the exact same observed state as positive runs
    counterexample = {"service_up": True, "auth_valid": True}

    with pytest.raises(ValueError) as exc_info:
        refine_counterexample(cap, counterexample, positive_states)

    err_msg = str(exc_info.value)
    assert "model_inadequacy_non_discriminable_outcome" in err_msg
    assert "adaptive reasoning required" in err_msg


def test_promotion_policy_blocks_model_inadequacy():
    """ExperiencePromotionPolicy rejects capability with model_inadequacy_detected."""
    cap = OperationalCapability(
        id="cap_promo_inadequacy",
        name="Promotion Inadequacy Block",
        version="1.0.0",
        effect="state_mutation",
        route="workstation",
        trust_class="trusted_runtime",
        lifecycle=CapabilityLifecycle.DISCOVERED,
        drift_state="healthy",
        learning_metadata={
            "semantic_closure": True,
            "parameterization_quality": True,
            "evidence_strength": 2,
            "provenance_complete": True,
            "authority_origins": ["user"],
            "run_ids": ["run1", "run2"],
            "drift_rate": 0.05,
            "unresolved_counterexamples": 0,
            "utility": 1,
            "risk": "ordinary",
            "blast_radius": 1,
            # Flag model inadequacy:
            "model_inadequacy_detected": True,
            "model_inadequacy_reason": "model_inadequacy_non_discriminable_outcome",
        },
        causal_grade=CausalGrade.REPLAY_VALIDATED,
        semantic_fingerprint="sem_fp",
        compatibility_fingerprint="compat_fp",
        postconditions=[{"type": "predicate", "key": "status", "expected": "ok"}],
    )

    policy = ExperiencePromotionPolicy()
    admission = policy.evaluate(cap)
    assert admission.admitted is False
    assert "model_inadequacy" in admission.reasons


def test_ora_metrics_records_model_inadequacy():
    """ORAMetrics and ORAMetricsCollector record model inadequacy events without inventing denominators."""
    metrics = ORAMetrics()
    collector = ORAMetricsCollector(metrics=metrics)

    assert metrics.model_inadequacy_events == 0
    assert metrics.model_inadequacy_reasons == {}

    collector.on_model_inadequacy("model_inadequacy_non_discriminable_outcome")
    collector.on_model_inadequacy("model_inadequacy_non_discriminable_outcome")
    collector.on_model_inadequacy("model_inadequacy_unmodelled_side_effect")

    assert metrics.model_inadequacy_events == 3
    assert metrics.model_inadequacy_reasons["model_inadequacy_non_discriminable_outcome"] == 2
    assert metrics.model_inadequacy_reasons["model_inadequacy_unmodelled_side_effect"] == 1

    # Invariant: unknown denominators remain None
    assert metrics.ora_ratio is None
    assert metrics.amortized_tokens_saved is None


def test_validity_envelope_projects_model_inadequacy():
    """Validity envelope projects model_inadequacy_suspected=True and invalidates reuse."""
    cap = OperationalCapability(
        id="cap_env_inadequacy",
        name="Envelope Inadequacy Test",
        version="1.0.0",
        effect="state_mutation",
        route="workstation",
        lifecycle=CapabilityLifecycle.PROMOTED,
        learning_metadata={
            "model_inadequacy_detected": True,
            "unresolved_counterexamples": 1,
        },
        drift_state="quarantined",
    )

    envelope = derive_validity_envelope(cap)
    assert envelope.model_inadequacy_suspected is True
    assert envelope.counterexample_count == 1
    assert envelope.is_valid_for_reuse is False
    assert "model_inadequacy_suspected" in envelope.invalidation_reasons
    assert "capability_quarantined" in envelope.invalidation_reasons
    assert envelope.is_valid() is False

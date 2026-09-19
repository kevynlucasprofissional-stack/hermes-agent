"""Tests for Phase P4: Operational Reasoning Amortization (ORA) Metrics."""
import json
import pytest

from workstation.control_plane.metrics import ORAMetrics, WakeReason


def test_ora_metrics_preserve_unknown_denominators_as_null():
    """Unknown denominators or unmeasured metrics must remain strictly None / null."""
    metrics = ORAMetrics()

    assert metrics.ora_ratio is None
    assert metrics.composite_reuse_rate is None
    assert metrics.wait_non_residency_rate is None
    assert metrics.wake_llm_rate is None
    assert metrics.amortized_tokens_saved is None
    assert metrics.amortized_cost_usd_saved is None

    # Serialized JSON must contain null, never fabricated zeros or numbers
    d = metrics.to_dict()
    assert d["ora_ratio"] is None
    assert d["composite_reuse_rate"] is None
    assert d["wait_non_residency_rate"] is None
    assert d["wake_llm_rate"] is None
    assert d["amortized_tokens_saved"] is None

    serialized = json.dumps(d)
    parsed = json.loads(serialized)
    assert parsed["ora_ratio"] is None
    assert parsed["amortized_tokens_saved"] is None


def test_ora_metrics_ratio_calculation():
    """Calculates exact ratios when events and invocations are supplied."""
    metrics = ORAMetrics(
        verified_transitions_deterministic=80,
        verified_transitions_reasoned=20,
        unverified_transitions=5,
        atomic_capability_invocations=5,
        composite_capability_invocations=15,
        total_capability_invocations=20,
        resident_wait_count=1,
        non_resident_wait_count=9,
        total_routing_events=100,
    )

    # 80 / (80 + 20) = 0.8
    assert metrics.ora_ratio == pytest.approx(0.8)

    # 15 / 20 = 0.75
    assert metrics.composite_reuse_rate == pytest.approx(0.75)

    # 9 / (1 + 9) = 0.9
    assert metrics.wait_non_residency_rate == pytest.approx(0.9)


def test_wake_reason_breakdown_and_rate():
    """Records wake reasons faithfully and computes wake rate over total routing events."""
    metrics = ORAMetrics(total_routing_events=50)

    metrics.record_wake_reason(WakeReason.UNCERTAIN_MUTATION)
    metrics.record_wake_reason(WakeReason.UNCERTAIN_MUTATION)
    metrics.record_wake_reason(WakeReason.OPEN_CONDITION)
    metrics.record_wake_reason(WakeReason.TIMEOUT)
    metrics.record_wake_reason(WakeReason.SCHEMA_DRIFT)

    assert metrics.llm_wake_count == 5
    assert metrics.wake_reasons["UNCERTAIN_MUTATION"] == 2
    assert metrics.wake_reasons["OPEN_CONDITION"] == 1
    assert metrics.wake_reasons["TIMEOUT"] == 1
    assert metrics.wake_reasons["SCHEMA_DRIFT"] == 1

    # 5 / 50 = 0.1
    assert metrics.wake_llm_rate == pytest.approx(0.1)

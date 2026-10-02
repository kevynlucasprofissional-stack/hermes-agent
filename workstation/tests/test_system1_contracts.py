"""Unit tests for System-1 Decision Contracts and Receipts.

Proves:
- DecisionRequest, DecisionResult, and DecisionReceipt schemas and hashing.
- NeutralChoice and ambiguity contracts.
- Core generic seam provider registration, execution, and unregistration.
- Receipt persistence and retrieval roundtripping.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from agent.system1_decision import (
    DecisionRequest,
    DecisionResult,
    decide_system1,
    register_system1_decision_provider,
    unregister_system1_decision_provider,
    reset_system1_decision,
    system1_decision_metrics,
)
from workstation.system1.contracts import (
    NeutralChoice,
    AmbiguityKind,
    ProgressClass,
    compute_state_hash,
)
from workstation.system1.receipts import (
    DecisionReceipt,
    persist_decision_receipt,
    load_decision_receipt,
)
from workstation.system1.provider import FakeSystem1DecisionProvider


def test_decision_contracts_and_hashing():
    """Verify hashing and structure of requests and results."""
    req = DecisionRequest(
        domain="control_plane.router",
        schema_id="candidate_ranking",
        questions={"preferred_candidate": {"type": "choice", "criteria": {"c1": "c1", "c2": "c2"}}},
        state={"objective": "read test file", "target": "filesystem"},
        context={"run_id": "run-001", "operation_id": "op-001"},
    )
    req_hash = req.request_hash()
    assert isinstance(req_hash, str)
    assert len(req_hash) == 64

    res = DecisionResult(
        provider="fake",
        schema_id="candidate_ranking",
        decisions={"preferred_candidate": "c1"},
        confidences={"preferred_candidate": 0.95},
        calibrated_confidences={"preferred_candidate": 0.90},
        request_hash=req_hash,
    )
    assert res.decisions["preferred_candidate"] == "c1"
    assert res.confidences["preferred_candidate"] == 0.95
    assert res.receipt_hash()


def test_decision_receipt_persistence():
    """Verify storing and loading DecisionReceipts."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage_dir = Path(tmp_dir)
        receipt = DecisionReceipt(
            receipt_id="rec-12345",
            domain="control_plane.router",
            schema_id="candidate_ranking",
            task_id="task-001",
            run_id="run-001",
            operation_id="op-001",
            state_digest="digest-abc",
            request_hash="req-hash-1",
            provider="fake",
            model="multilingual",
            laya_version="0.3.23",
            laya_source_sha="sha123",
            decisions={"preferred_candidate": "file_read"},
            confidences={"preferred_candidate": 0.98},
            calibrated_confidences={"preferred_candidate": 0.92},
            latency_ms=12.5,
        )

        p = persist_decision_receipt(receipt, storage_dir)
        assert p.is_file()

        loaded = load_decision_receipt(p)
        assert loaded.receipt_id == "rec-12345"
        assert loaded.decisions["preferred_candidate"] == "file_read"
        assert loaded.confidences["preferred_candidate"] == 0.98
        assert loaded.provider == "fake"
        assert loaded.receipt_hash() == receipt.receipt_hash()


def test_core_generic_seam_lifecycle():
    """Verify registering, invoking, and unregistering a provider on the generic core seam."""
    reset_system1_decision()

    # With no provider registered, fallback returns neutral choices
    req = DecisionRequest(
        domain="control_plane.router",
        schema_id="candidate_ranking",
        questions={"preferred_candidate": {"type": "choice", "criteria": {"c1": "c1", "c2": "c2"}}},
        state={"objective": "read test file"},
    )
    fallback_res = decide_system1(req)
    assert fallback_res.provider == "deterministic_fallback"
    assert fallback_res.decisions["preferred_candidate"] == NeutralChoice.ABSTAIN.value

    # Register fake provider
    provider = FakeSystem1DecisionProvider(
        name="test_fake",
        preset_decisions={"preferred_candidate": "c2"},
        preset_confidences={"preferred_candidate": 0.99},
    )
    register_system1_decision_provider(provider)

    active_res = decide_system1(req)
    assert active_res.provider == "test_fake"
    assert active_res.decisions["preferred_candidate"] == "c2"
    assert active_res.confidences["preferred_candidate"] == 0.99

    metrics = system1_decision_metrics()
    assert metrics["invocations"] >= 2
    assert metrics["fallbacks"] >= 1

    # Unregister provider
    unregister_system1_decision_provider(provider)
    unregistered_res = decide_system1(req)
    assert unregistered_res.provider == "deterministic_fallback"

    reset_system1_decision()

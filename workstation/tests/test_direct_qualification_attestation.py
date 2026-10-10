"""Tests for DF-008 / DF3: Verifiable DIRECT Qualification Attestation.

Validates that:
1. Arbitrary non-empty strings (e.g. "receipt-1") no longer enable DIRECT mode.
2. Only cryptographically/structurally bound attestations (workstation.direct_qualification.v1)
   with intact signature, valid timestamps, and active status are accepted.
3. Revoked or expired attestations fail closed to SHADOW mode with specific reasons.
4. Tampered signatures fail closed with signature mismatch.
"""
from __future__ import annotations

import hashlib
import json
import time
import pytest

pytestmark = pytest.mark.usefixtures("direct_qualification_issuer")

from workstation.artifacts import ArtifactStore
from workstation.experience_compiler.compilability_monitor import (
    DIRECT,
    SHADOW,
    OnlineCompilabilityMonitor,
    resolve_policy,
    create_direct_qualification_attestation,
    verify_qualification_attestation,
)


def test_arbitrary_string_is_rejected_as_direct_qualification():
    """DF-008: Arbitrary non-empty string cannot enable DIRECT mode."""
    policy = resolve_policy(DIRECT, qualification_ref="receipt-1")
    assert policy.mode == SHADOW
    assert policy.downgrade_reason == "invalid_qualification_attestation"

    policy_arbitrary = resolve_policy(DIRECT, qualification_ref="some_random_token")
    assert policy_arbitrary.mode == SHADOW
    assert policy_arbitrary.downgrade_reason == "invalid_qualification_attestation"


def test_missing_qualification_ref_downgrades():
    """Empty or missing qualification ref fails closed."""
    policy = resolve_policy(DIRECT, qualification_ref="")
    assert policy.mode == SHADOW
    assert policy.downgrade_reason == "direct_requires_qualification_ref"


def test_valid_structured_attestation_enables_direct_mode():
    """Valid signed attestation successfully enables DIRECT mode."""
    attestation = create_direct_qualification_attestation(
        code_version="v0.9.1",
        provider="laya",
        model="laya-v1",
        operation_family="file_edit",
        effect_class="state_mutation",
    )
    policy = resolve_policy(DIRECT, qualification_ref=attestation)
    assert policy.mode == DIRECT
    assert policy.downgrade_reason == ""


def test_revoked_attestation_fails_closed():
    """Revoked attestation forces SHADOW mode."""
    attestation = create_direct_qualification_attestation(
        code_version="v0.9.1",
        provider="laya",
        revoked=True,
        revocation_reason="security_advisory_20261009",
    )
    policy = resolve_policy(DIRECT, qualification_ref=attestation)
    assert policy.mode == SHADOW
    assert policy.downgrade_reason == "qualification_revoked"


def test_expired_attestation_fails_closed():
    """Expired attestation forces SHADOW mode."""
    attestation = create_direct_qualification_attestation(
        code_version="v0.9.1",
        provider="laya",
        expires_at=time.time() - 100.0,  # Expired in past
    )
    policy = resolve_policy(DIRECT, qualification_ref=attestation)
    assert policy.mode == SHADOW
    assert policy.downgrade_reason == "qualification_expired"


def test_tampered_signature_fails_closed():
    """Attestation with altered payload/signature mismatch forces SHADOW mode."""
    attestation = create_direct_qualification_attestation(
        code_version="v0.9.1",
        provider="laya",
    )
    # Tamper with code_version without updating signature
    tampered = dict(attestation)
    tampered["code_version"] = "v0.9.2-unauthorized"

    policy = resolve_policy(DIRECT, qualification_ref=tampered)
    assert policy.mode == SHADOW
    assert policy.downgrade_reason == "qualification_signature_mismatch"


def test_self_signed_attestation_cannot_enable_direct(tmp_path, monkeypatch):
    """An attacker who controls a payload cannot issue their own DIRECT permission."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes-home"))
    now = time.time()
    forged = {
        "attestation_id": "attacker-issued",
        "schema": "workstation.direct_qualification.v1",
        "code_version": "attacker-code",
        "provider": "laya",
        "model": "laya-v1",
        "model_revision": "attacker-model-revision",
        "operation_family": "file_edit",
        "effect_class": "state_mutation",
        "verifier_contract": {"name": "attacker-verifier"},
        "safe_env": "production",
        "exact_tests": ["attacker-claimed-test"],
        "issued_at": now,
        "expires_at": now + 3600,
        "revoked": False,
        "revocation_reason": "",
    }
    canonical = json.dumps(forged, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    forged["signature"] = hashlib.sha256(canonical.encode()).hexdigest()[:32]

    policy = resolve_policy(DIRECT, qualification_ref=forged)

    assert policy.mode == SHADOW


def test_rehashed_attestation_cannot_expand_qualified_scope(tmp_path, monkeypatch):
    """A holder cannot turn a revoked read-only qualification into mutating DIRECT."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes-home"))
    attestation = create_direct_qualification_attestation(
        code_version="reviewed-code",
        model_revision="reviewed-model",
        operation_family="read_status",
        effect_class="read_only",
        revoked=True,
        revocation_reason="qualification_withdrawn",
    )
    forged = {
        **attestation,
        "code_version": "attacker-code",
        "model_revision": "attacker-model",
        "operation_family": "file_edit",
        "effect_class": "state_mutation",
        "revoked": False,
        "revocation_reason": "",
    }
    canonical = json.dumps(
        {key: value for key, value in forged.items() if key != "signature"},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    forged["signature"] = hashlib.sha256(canonical.encode()).hexdigest()[:32]

    policy = resolve_policy(DIRECT, qualification_ref=forged)

    assert policy.mode == SHADOW


def test_resolvable_artifact_ref_attestation(tmp_path):
    """Attestation stored in ArtifactStore and referenced via artifact:// resolves and qualifies."""
    artifacts = ArtifactStore(root_dir=tmp_path / "artifacts")
    attestation = create_direct_qualification_attestation(
        code_version="v0.9.1",
        provider="laya",
        operation_family="batch_cards",
    )
    ref = artifacts.store(
        "task_admin",
        "laya_direct_attestation.json",
        attestation,
        schema="workstation.direct_qualification.v1",
    )

    policy = resolve_policy(DIRECT, qualification_ref=ref.ref, artifacts=artifacts)
    assert policy.mode == DIRECT
    assert policy.downgrade_reason == ""

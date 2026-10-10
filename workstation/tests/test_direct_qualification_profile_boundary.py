"""Real config + scoped .env trust path, never production credentials."""
import base64
from contextlib import contextmanager
import json
import time
from types import SimpleNamespace

import pytest
import yaml

from agent.secret_scope import (
    build_profile_secret_scope, reset_multiplex_context, reset_secret_scope,
    set_multiplex_context, set_secret_scope,
)
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from workstation.experience_compiler.compilability_monitor import (
    DIRECT, SHADOW, OnlineCompilabilityMonitor, TaskRunObservationWindow,
    create_direct_qualification_attestation, resolve_policy,
)

CLAIMS = dict(code_version="a" * 40, provider="laya", model="laya-v1",
              model_revision="b" * 40, operation_family="write_report",
              effect_class="state_mutation", verifier_contract={"observer": "independent-reader"},
              safe_env="isolated_sandbox")


def provision(home, key):
    home.mkdir()
    trust = dict(issuer="qualification-operator", key_id="key-1",
                 secret_ref="WORKSTATION_DIRECT_QUALIFICATION_KEY", bindings=[CLAIMS],
                 revoked_attestation_ids=[])
    config = {"workstation": {"online_compilability": {"qualification_trust": trust}}}
    (home / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    (home / ".env").write_text(
        "WORKSTATION_DIRECT_QUALIFICATION_KEY=" + base64.b64encode(key).decode() + "\n",
        encoding="utf-8")
    return config


@contextmanager
def profile(home):
    home_token = set_hermes_home_override(home)
    secret_token = set_secret_scope(build_profile_secret_scope(home), profile_home=home)
    multiplex_token = set_multiplex_context(True)
    try:
        yield
    finally:
        reset_multiplex_context(multiplex_token)
        reset_secret_scope(secret_token)
        reset_hermes_home_override(home_token)


def test_real_profile_trust_isolated_a_b_a_and_all_claims_authenticated(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    provision(a, b"A" * 32)
    provision(b, b"B" * 32)
    with profile(a):
        att = create_direct_qualification_attestation(**CLAIMS, exact_tests=("controlled-replay",))
        assert resolve_policy(DIRECT, att).mode == DIRECT
        for field in (*CLAIMS, "issuer", "key_id", "issued_at", "expires_at", "revoked", "exact_tests"):
            forged = {**att, field: "attacker-replaced-claim"}
            assert resolve_policy(DIRECT, forged).mode == SHADOW, field
        # Even a real issuer's signature cannot introduce an unconfigured binding.
        wrong_code = create_direct_qualification_attestation(
            **{**CLAIMS, "code_version": "c" * 40}, exact_tests=("controlled-replay",))
        assert resolve_policy(DIRECT, wrong_code).downgrade_reason == "qualification_binding_mismatch"
    with profile(b):
        assert resolve_policy(DIRECT, att).mode == SHADOW
    with profile(a):
        assert resolve_policy(DIRECT, att).mode == DIRECT


def test_live_revocation_expiry_scope_and_missing_trust_fail_closed(tmp_path):
    home = tmp_path / "operator"
    config = provision(home, b"A" * 32)
    with profile(home):
        att = create_direct_qualification_attestation(**CLAIMS, exact_tests=("controlled-replay",))
        monitor = OnlineCompilabilityMonitor(mode=DIRECT, direct_qualification_ref=att)
        window = TaskRunObservationWindow("task", "run")
        proof = SimpleNamespace(effect_budget=[{"kind": "CREATE"}], verifier_contract=CLAIMS["verifier_contract"])
        offer = SimpleNamespace(status="ready", operation_family="write_report", proof=proof)
        window.offers["candidate"] = offer
        monitor._windows[("task", "run")] = window
        assert monitor.ready_offers("task", "run") == [offer]
        offer.operation_family = "other-family"
        assert monitor.ready_offers("task", "run") == []
        offer.operation_family = "write_report"
        trust = config["workstation"]["online_compilability"]["qualification_trust"]
        trust["revoked_attestation_ids"] = [att["attestation_id"]]
        (home / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
        assert monitor.ready_offers("task", "run") == []
        assert monitor.mode == SHADOW and monitor.mode_downgrade_reason == "qualification_revoked"
        trust["revoked_attestation_ids"] = []
        (home / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
        for validity in ({"issued_at": time.time() + 60}, {"expires_at": time.time() - 1},
                         {"expires_at": time.time() + 86401}):
            invalid = create_direct_qualification_attestation(**CLAIMS, exact_tests=("controlled-replay",), **validity)
            assert resolve_policy(DIRECT, json.dumps(invalid)).mode == SHADOW
        (home / "config.yaml").write_text("{}", encoding="utf-8")
        assert resolve_policy(DIRECT, att).downgrade_reason == "qualification_trust_missing"
        with pytest.raises(ValueError, match="qualification_trust_missing"):
            create_direct_qualification_attestation(**CLAIMS)

"""Derived Validity Envelope Projection (H-077 P4).

Pure diagnostic projection over existing operational owners:
- OperationIntent
- CapabilityFormalContract
- VerificationContract
- Execution Context & Evidence History

Enforces:
- No new source of truth or parallel registry (D-025).
- Fail closed when information required for a claim is absent.
- Detect when current operational context leaves the validated envelope.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any

from workstation.control_plane.intent import OperationIntent
from workstation.control_plane.verification import VerificationContract, VerificationLifecycle
from workstation.operational_capabilities import CapabilityLifecycle, OperationalCapability


@dataclass(frozen=True)
class ValidityEnvelope:
    """Immutable envelope defining the validated operational boundaries of a capability."""

    capability_id: str
    capability_version: str
    intent_id: str = ""
    goal_predicates: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    authority_scope: dict[str, Any] = field(default_factory=dict)
    resource_binding: dict[str, Any] = field(default_factory=dict)
    temporal_basis: str = "none"
    max_age_seconds: float | None = None
    required_trust: tuple[str, ...] = ()
    mutation_failure_domains: tuple[str, ...] = ()
    allowed_observer_failure_domains: tuple[str, ...] = ()
    context_fingerprint: str = ""
    observed_preconditions: tuple[str, ...] = ()
    counterexample_count: int = 0
    model_inadequacy_suspected: bool = False
    is_valid_for_reuse: bool = True
    invalidation_reasons: tuple[str, ...] = ()

    @property
    def tenant_scope(self) -> str | None:
        return self.authority_scope.get("tenant_id") or self.authority_scope.get("tenant")

    @property
    def target_family(self) -> str | None:
        return self.authority_scope.get("target_family") or self.authority_scope.get("target")

    def is_valid(self, context: dict[str, Any] | None = None) -> bool:
        if not self.is_valid_for_reuse:
            return False
        if context:
            for k, v in self.authority_scope.items():
                if k in context and str(context[k]) != str(v):
                    return False
            if self.resource_binding:
                expected_res = self.resource_binding.get("resource_id") or self.resource_binding.get("id")
                current_res = context.get("resource_id") or context.get("target_resource")
                if expected_res and current_res and str(expected_res) != str(current_res):
                    return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def derive_validity_envelope(
    capability: OperationalCapability | dict[str, Any],
    intent: OperationIntent | None = None,
    current_context: dict[str, Any] | None = None,
) -> ValidityEnvelope:
    """Pure diagnostic derivation of the validity envelope from existing canonical owners."""
    ctx = current_context or {}
    cap = capability if isinstance(capability, OperationalCapability) else OperationalCapability.from_dict(capability)

    reasons: list[str] = []

    # 1. VerificationContract projection
    verifier_raw = cap.verifier_contract or getattr(cap.formal_contract, "verifier", None) or {}
    vc = verifier_raw if isinstance(verifier_raw, VerificationContract) else VerificationContract.from_dict(verifier_raw)

    # 2. Extract Intent bounds
    intent_id = ""
    goal_preds: list[str] = []
    invariants: list[str] = []
    if intent is not None:
        intent_id = intent.id
        if hasattr(intent.goal, "fingerprint"):
            goal_preds.append(intent.goal.fingerprint())
        elif isinstance(intent.goal, dict):
            goal_preds.append(json.dumps(intent.goal, sort_keys=True))
        for inv in getattr(intent, "invariants", ()):
            invariants.append(inv.fingerprint() if hasattr(inv, "fingerprint") else str(inv))

    # 3. Learning metadata & counterexamples
    meta = cap.learning_metadata if isinstance(cap.learning_metadata, dict) else {}
    unresolved_ce = int(meta.get("unresolved_counterexamples", 0))
    model_inadequacy = bool(meta.get("model_inadequacy_detected", False))

    if model_inadequacy:
        reasons.append("model_inadequacy_suspected")
    if unresolved_ce > 0:
        reasons.append("unresolved_counterexamples_present")
    if cap.drift_state == "quarantined":
        reasons.append("capability_quarantined")

    # 4. Scope & Resource binding enforcement
    if cap.scope:
        for scope_k, scope_v in cap.scope.items():
            if scope_k in ctx and str(ctx[scope_k]) != str(scope_v):
                reasons.append(f"context_{scope_k}_mismatch")

    binding = dict(vc.resource_binding) if vc.resource_binding else {}
    if binding:
        expected_res = binding.get("resource_id") or binding.get("id") or binding.get("path")
        current_res = ctx.get("resource_id") or ctx.get("target_resource")
        if expected_res and current_res and str(expected_res) != str(current_res):
            reasons.append("context_resource_binding_mismatch")

    # 5. Preconditions
    preconds = tuple(
        p.get("key", str(p)) if isinstance(p, dict) else str(p)
        for p in cap.preconditions
    )

    # Context fingerprint
    ctx_fp_payload = {
        "capability_id": cap.id,
        "version": cap.version,
        "preconditions": preconds,
        "resource_binding": binding,
    }
    raw_fp = json.dumps(ctx_fp_payload, sort_keys=True, separators=(",", ":"))
    ctx_fp = hashlib.sha256(raw_fp.encode("utf-8")).hexdigest()

    is_valid = (len(reasons) == 0) and (cap.lifecycle == CapabilityLifecycle.PROMOTED)

    return ValidityEnvelope(
        capability_id=cap.id,
        capability_version=cap.version,
        intent_id=intent_id,
        goal_predicates=tuple(goal_preds),
        invariants=tuple(invariants),
        authority_scope=cap.scope,
        resource_binding=binding,
        temporal_basis=vc.temporal_basis,
        max_age_seconds=vc.max_age_seconds,
        required_trust=vc.allowed_trust,
        mutation_failure_domains=vc.mutation_failure_domains,
        allowed_observer_failure_domains=vc.allowed_observer_failure_domains,
        context_fingerprint=ctx_fp,
        observed_preconditions=preconds,
        counterexample_count=unresolved_ce,
        model_inadequacy_suspected=model_inadequacy,
        is_valid_for_reuse=is_valid,
        invalidation_reasons=tuple(reasons),
    )

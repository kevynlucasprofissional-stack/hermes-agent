"""Certified Dispatcher, Preflight Revalidation, and Effectively-Once Execution.

Enforces:
- NO VALID CERTIFICATE -> NO DISPATCH.
- PREPARED -> DISPATCHED -> ACKNOWLEDGED -> VERIFIED -> COMMITTED.
- Never blind retry on uncertain mutations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
from typing import Any, Callable

from workstation.contracts import utc_now
from workstation.control_plane.router import (
    ComposedDecision, ExecutableDecision, RoutingCertificate, _state_hash, revalidate_certificate
)
from workstation.control_plane.verification import VerificationResult, VerificationStatus


class DispatchStatus(str, Enum):
    PREPARED = "PREPARED"
    DISPATCHED = "DISPATCHED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    VERIFIED = "VERIFIED"
    COMMITTED = "COMMITTED"
    UNCERTAIN = "UNCERTAIN"


class DispatchError(Exception):
    """Raised when dispatch authorization fails or is attempted without a valid certificate."""
    pass


@dataclass
class DispatchRecord:
    """Durable record of an operation dispatch for idempotency and effectively-once reconciliation."""

    operation_id: str
    capability_id: str
    status: DispatchStatus = DispatchStatus.PREPARED
    target: str = ""
    dispatched_at: str = field(default_factory=utc_now)
    acknowledged_at: str | None = None
    verified_at: str | None = None
    idempotency_key: str = ""
    authority_scope: dict[str, Any] = field(default_factory=dict)
    verifier_status: str = "not_verified"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CertifiedDispatcher:
    """Dispatches execution only under verified certificates with preflight freshness guarantees."""

    def __init__(self, kernel: Any = None) -> None:
        self.kernel = kernel
        self._records: dict[str, DispatchRecord] = {}

    def dispatch(
        self,
        decision: ExecutableDecision | ComposedDecision,
        current_state: dict[str, Any],
        dispatch_fn: Callable[..., Any] | None = None,
        run_id: str | None = None,
        has_uncertain_mutation: bool = False,
        authority_scope: Any = None,
        verifier_fn: Callable[[Any], bool] | None = None,
        verification_result_fn: Callable[[Any], VerificationResult | dict[str, Any]] | None = None,
        ack_is_terminal_evidence: bool = False,
    ) -> dict[str, Any]:
        """Dispatch certified decision with strict preflight revalidation."""
        cert = getattr(decision, "certificate", None)
        if cert is None or not cert.is_valid():
            raise DispatchError("NO VALID CERTIFICATE -> NO DISPATCH")

        # Preflight revalidation
        current_state_h = _state_hash(current_state)
        current_capability = getattr(decision, "capability", None)
        if isinstance(decision, ComposedDecision):
            current_versions = [cap.version for cap in decision.plan]
            is_fresh = (
                not has_uncertain_mutation
                and current_state_h == cert.semantic_state_hash
                and current_versions == cert.plan_versions
                and (not run_id or not cert.run_id or run_id == cert.run_id)
                and cert.is_valid()
            )
        else:
            cap_v = current_capability.version if current_capability else getattr(cert, "capability_version", "")
            is_fresh = revalidate_certificate(
                cert,
                current_intent_hash=cert.intent_hash,
                current_state_hash=current_state_h,
                current_cap_version=cap_v,
                run_id=run_id,
                has_uncertain_mutation=has_uncertain_mutation,
            )
        if not is_fresh:
            raise DispatchError("Preflight revalidation failed: state or context drifted; certificate invalidated")

        # Prepare dispatch record in PREPARED state
        op_id = cert.operation_id or f"op-{cert.certificate_hash()[:16]}"
        auth_dict = authority_scope.to_dict() if hasattr(authority_scope, "to_dict") else (authority_scope if isinstance(authority_scope, dict) else {})
        record = DispatchRecord(
            operation_id=op_id,
            capability_id=getattr(decision, "capability", None).id if hasattr(decision, "capability") else "composite",
            status=DispatchStatus.PREPARED,
            idempotency_key=op_id,
            authority_scope=auth_dict,
        )
        self._records[op_id] = record

        # Transition to DISPATCHED before executing
        record.status = DispatchStatus.DISPATCHED
        record.dispatched_at = utc_now()
        from workstation.telemetry import TelemetryEventType, emit_event
        emit_event(TelemetryEventType.MUTATION_DISPATCHED,
                   source_owner="workstation.certified_dispatcher",
                   run_id=run_id, operation_id=op_id, capability_id=record.capability_id,
                   status=record.status.value, dedupe_key=f"dispatch:{op_id}")

        # Execute using kernel or dispatch function
        try:
            if dispatch_fn:
                result = dispatch_fn()
            elif self.kernel:
                cap = getattr(decision, "capability", None)
                result = self.kernel.execute_capability(cap) if cap else {"success": True}
            else:
                result = {"success": True, "operation_id": op_id}

            record.status = DispatchStatus.ACKNOWLEDGED
            record.acknowledged_at = utc_now()
            emit_event(TelemetryEventType.MUTATION_ACKNOWLEDGED,
                       source_owner="workstation.certified_dispatcher",
                       run_id=run_id, operation_id=op_id, capability_id=record.capability_id,
                       status=record.status.value, dedupe_key=f"ack:{op_id}")

            # Verification phase: cannot advance to COMMITTED without verification
            verification_result: VerificationResult | None = None
            if verification_result_fn is not None:
                try:
                    candidate = verification_result_fn(result)
                    verification_result = candidate if isinstance(candidate, VerificationResult) else VerificationResult.from_dict(candidate)
                except Exception:
                    verification_result = VerificationResult(VerificationStatus.INCONCLUSIVE, reason="verification_callback_error")
            elif verifier_fn is not None:
                # Compatibility callbacks may still run, but a boolean cannot be
                # terminal truth.  Callers must migrate to canonical results.
                try:
                    candidate = verifier_fn(result)
                    if isinstance(candidate, VerificationResult):
                        verification_result = candidate
                    elif isinstance(candidate, dict) and "status" in candidate:
                        verification_result = VerificationResult.from_dict(candidate)
                    else:
                        verification_result = VerificationResult(
                            VerificationStatus.INCONCLUSIVE,
                            reason="legacy_boolean_verifier_is_not_canonical_evidence",
                        )
                except Exception:
                    verification_result = VerificationResult(VerificationStatus.INCONCLUSIVE, reason="legacy_verifier_error")
            elif ack_is_terminal_evidence:
                # This exception is deliberately opt-in at a trusted contract
                # boundary. A successful-looking tool payload is only an ACK.
                verified = not (
                    isinstance(result, dict)
                    and (result.get("success") is False or result.get("ok") is False or result.get("error"))
                )
                verification_result = VerificationResult(
                    VerificationStatus.VERIFIED if verified else VerificationStatus.FAILED,
                    reason="trusted_owner_ack_terminal_contract",
                )

            if verification_result_fn is None and verifier_fn is None and not ack_is_terminal_evidence:
                record.verifier_status = "needs_verification"
                return {
                    "success": False,
                    "result": result,
                    "dispatch_record": record.to_dict(),
                    "error": "needs_verification",
                }

            if verification_result is None or not verification_result.verified:
                record.status = DispatchStatus.UNCERTAIN
                record.verifier_status = (
                    verification_result.status.value.lower() if verification_result else "inconclusive"
                )
                return {
                    "success": False,
                    "result": result,
                    "dispatch_record": record.to_dict(),
                    "verification_result": verification_result.to_dict() if verification_result else None,
                    "error": "verification_failed",
                }

            record.status = DispatchStatus.VERIFIED
            record.verified_at = utc_now()
            record.verifier_status = "verified"

            record.status = DispatchStatus.COMMITTED
            emit_event(TelemetryEventType.VERIFICATION_COMPLETED,
                       source_owner="workstation.verification", run_id=run_id,
                       operation_id=op_id, capability_id=record.capability_id,
                       status=verification_result.status.value,
                       reason_code=verification_result.reason,
                       evidence_refs=tuple(verification_result.evidence_refs),
                       dedupe_key=f"verification:{op_id}:{verification_result.verifier_fingerprint}")
            return {"success": True, "result": result, "verification_result": verification_result.to_dict(), "dispatch_record": record.to_dict()}
        except Exception as exc:
            record.status = DispatchStatus.UNCERTAIN
            record.verifier_status = "failed"
            raise DispatchError(f"Execution failed; status marked UNCERTAIN: {exc}") from exc

    def can_retry_operation(
        self,
        record: DispatchRecord,
        external_reconciled: bool = False,
    ) -> tuple[bool, str]:
        """Check if an operation can be safely retried under effectively-once semantics."""
        if record.status == DispatchStatus.UNCERTAIN:
            if not external_reconciled:
                return False, "Uncertain mutation requires authoritative external reconciliation before retry"
            return True, "Reconciliation completed; retry safe under same operation contract"
        if record.status == DispatchStatus.COMMITTED:
            return False, "Operation already committed"
        return True, "Safe to dispatch"

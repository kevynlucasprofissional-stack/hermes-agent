"""Progressive artifact capture; observation never implies promotion."""
import logging

from workstation.execution_policy import EvidenceStrength

from .models import TransitionSample, TransitionOutcome, Operation, Provenance, Verification, StateDelta
from .corpus import ExperienceCorpus
from .state_abstraction import abstract_state

logger = logging.getLogger(__name__)


def capture_progressive(artifacts, *, task_id, run_id, operation_id, primitive, route, outcome,  # health: allow CC -- multi-schema verification and transition projection pipeline
                        state=None, evidence_refs=(), verification=None,
                        operation_family="", target_family="", effect_class="unknown", scope=None,
                        state_before=None, state_before_ref=None, raw_result_ref=None):
    if not task_id or not run_id or not operation_id:
        return None
    verified_post_resources = set()
    verified_card_projection = None
    if outcome == TransitionOutcome.VERIFIED_SUCCESS.value:
        # An observation with a caller-supplied "VERIFIED" flag is not enough.
        # Only a persisted, operation-bound owner readback may enter the corpus
        # as VERIFIED_SUCCESS. Later promotion remains independently gated.
        if (verification is None
                or verification.status != "VERIFIED"
                or verification.trust_class != "trusted_runtime"
                or verification.evidence_strength < EvidenceStrength.SEMANTIC_PERSISTED_READBACK
                or not verification.observer
                or not verification.verifier_fingerprint
                or not verification.evidence_refs):
            return None
        for ref in verification.evidence_refs:
            if not isinstance(ref, str) or not ref.startswith("artifact://tasks/"):
                return None
            try:
                evidence = artifacts.resolve_structured(ref)
            except (OSError, ValueError, KeyError):
                return None
            body = evidence.get("content")
            if (not isinstance(body, dict)
                    or body.get("task_id") != task_id
                    or str(body.get("run_id")) != str(run_id)
                    or body.get("operation_id") != operation_id):
                return None
            schema = evidence.get("schema")
            if schema == "workstation.run_local_readback.v1":  # health: allow HX011 -- dispatch across discrete readback artifact schemas
                if body.get("matched") is not True:
                    return None
            elif schema == "hermes.browser_local_readback.v1":
                if body.get("read_after_write") is not True or body.get("recovery_state") != "live":
                    return None
            elif schema == "hermes.browser_card_readback.v1":
                if (body.get("status") != "VERIFIED"
                        or body.get("independent_readback") is not True
                        or body.get("trust_class") != "trusted_runtime"
                        or not isinstance(body.get("projection"), dict)):
                    return None
                verified_card_projection = body["projection"]
            elif schema == "hermes.canonical_verification.v1":
                result = body.get("result") or {}
                if (result.get("status") != "VERIFIED"
                        or result.get("accepted") is not True
                        or not result.get("evidence_refs")):
                    return None
                # The canonical verifier receipt must link to independently
                # persisted evidence, not just self-assert a terminal status.
                for proof_ref in result["evidence_refs"]:
                    if not isinstance(proof_ref, str):
                        return None
                    if not proof_ref.startswith(f"artifact://tasks/{task_id}/"):
                        return None
                    try:
                        underlying = artifacts.resolve_structured(proof_ref)
                    except (OSError, ValueError, KeyError):
                        return None
                    payload = underlying.get("content")
                    if underlying.get("content_omitted") or not underlying.get("schema"):
                        return None
                    if isinstance(payload, dict):
                        if (payload.get("task_id", task_id) != task_id
                                or str(payload.get("run_id", run_id)) != str(run_id)
                                or payload.get("operation_id", operation_id) != operation_id):
                            return None
                        if (underlying.get("schema") == "workstation.run_local_readback.v1"
                                and payload.get("matched") is not True):
                            return None
                        if underlying.get("schema") == "workstation.operational_filesystem_readback.v1":
                            if (payload.get("read_after_write") is not True
                                    or payload.get("observer") not in {"fs_hash", "hash_file", "fs_stat", "stat"}
                                    or not payload.get("resource")
                                    or "value" not in payload):
                                return None
                            verified_post_resources.add(str(payload["resource"]))
            else:
                return None
    # Families and effect class come from the runtime-owned capability contract.
    # Never infer replay arguments from raw tool output or free-form observations.
    before = None
    if outcome == TransitionOutcome.VERIFIED_SUCCESS.value and state_before_ref is not None:
        # A caller-provided pre-state, even from the runtime's execution context,
        # is not independent evidence that those predicates existed before I/O.
        # Only a separately persisted owner read-before-write record qualifies.
        if not isinstance(state_before, dict) or not isinstance(state_before_ref, str):
            return None
        try:
            pre_proof = artifacts.resolve_structured(state_before_ref)
        except (OSError, ValueError, KeyError):
            return None
        pre = pre_proof.get("content")
        if (pre_proof.get("schema") != "workstation.operational_prestate_readback.v1"
                or not isinstance(pre, dict)
                or pre.get("task_id") != task_id
                or str(pre.get("run_id")) != str(run_id)
                or pre.get("operation_id") != operation_id
                or pre.get("observer") != "workstation.operational_prestate"
                or pre.get("read_before_write") is not True
                or not isinstance(pre.get("state"), dict)):
            return None
        before = abstract_state(route, pre["state"], state_before_ref)
        if verified_post_resources and str(pre.get("resource") or "") not in verified_post_resources:
            return None
        if before.semantic_predicates != abstract_state(route, state_before).semantic_predicates:
            return None
    after = abstract_state(route, state or verified_card_projection or {})
    # Unknown or unproven pre-state must never generate inferred causal effects.
    delta = StateDelta.between(before, after) if before is not None else StateDelta()
    sample = TransitionSample(operation=Operation(
            primitive=primitive, canonical_route=route,
            operation_family=str(operation_family or ""), target_family=str(target_family or ""),
            effect_class=str(effect_class or "unknown"), scope=scope if isinstance(scope, dict) else {},
        ),
        state_before=before if before is not None else abstract_state(route, {}),
        state_after=after, delta=delta,
        outcome=TransitionOutcome(outcome), provenance=Provenance(task_id=task_id, run_id=str(run_id),
            operation_id=operation_id, runtime=route, source="progressive_owner", trust_class="trusted_runtime"),
        verification=verification or Verification(evidence_refs=list(evidence_refs)),
        raw_result_ref=raw_result_ref)
    try:
        return ExperienceCorpus(artifacts).capture(sample)
    except (OSError, ValueError):
        logger.warning("Progressive learning capture failed", exc_info=True)
        return None

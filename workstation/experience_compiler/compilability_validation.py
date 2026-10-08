"""Validation-only admission of a mined candidate into ONE TaskRun.

Consumes, never grants: identity, authority, effect budget, lease, pending items,
uncertainty, verifier receipts and replay evidence all come from their owners
(``RunAdoptionOwner``, the validation-environment provider, ``controlled_replay``,
``validate_verifier_candidate``). Anything missing, failed, inconsistent or not
resolvable in the ArtifactStore denies the candidate; no evidence is synthesized and
the global promotion path (``ExperienceCompiler.promote``) is never reached.
"""
from __future__ import annotations

import logging
from copy import deepcopy
from dataclasses import replace
from typing import Any, Callable, Optional

from workstation.artifacts import ArtifactStore
from workstation.control_plane.verification import (
    VerificationContract,
    VerificationLifecycle,
    VerificationResult,
    VerificationStatus,
    validate_verifier_candidate,
)
from workstation.experience_compiler.causal import controlled_replay
from workstation.experience_compiler.lifecycle import get_validation_environment_provider
from workstation.experience_compiler.models import TransitionOutcome, TransitionSample
from workstation.operational_capabilities import CapabilityLifecycle, OperationalCapability
from workstation.recipes import digest
from workstation.run_adoption import (
    REPLAY_RECEIPT_SCHEMA,
    AdoptionOffer,
    RunAdoptionOwner,
    plan_item_adoption,
)
from workstation.run_closure import RunClosureProof, evaluate_run_local_closure

logger = logging.getLogger(__name__)

_READ_EFFECTS = {"read_only", "PURE_READ", "DISCOVERY"}


def _resolves(artifacts: ArtifactStore, ref: Any) -> bool:
    """A reference is evidence only if it resolves with intact bytes in the canonical store."""
    if not isinstance(ref, str) or not ref:
        return False
    try:
        artifacts.resolve_structured(ref)
    except (OSError, ValueError, KeyError):
        return False
    return True


def _owned_by_run_namespace(ref: Any, task_id: str) -> bool:
    """Evidence must live in the TaskRun's own artifact namespace, never another task's."""
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in str(task_id))
    return isinstance(ref, str) and ref.startswith(f"artifact://tasks/{safe}/")


def _families(candidate: OperationalCapability) -> tuple[str, str]:
    fc = candidate.formal_contract
    meta = candidate.learning_metadata or {}

    def pick(attr: str, meta_key: str, default: str) -> str:
        if fc is not None:
            value = fc.get(attr) if isinstance(fc, dict) else getattr(fc, attr, "")
            if value:
                return str(value)
        values = meta.get(meta_key) or []
        return str(values[0]) if values else default

    return (pick("operation_family", "operation_families", candidate.id),
            pick("target_family", "target_families", candidate.route))


def candidate_lineage_denials(candidate: OperationalCapability, task_id: str, run_id: str) -> list[str]:
    """Run-local candidates must be built exclusively from this TaskRun's own evidence."""
    origins = (candidate.provenance or {}).get("origins") or []
    if not origins:
        return ["lineage_unknown"]
    if any(not isinstance(o, dict) or str(o.get("task_id")) != str(task_id) or str(o.get("run_id")) != str(run_id)
           for o in origins):
        return ["cross_run_lineage"]
    run_ids = {str(r) for r in (candidate.learning_metadata or {}).get("run_ids", [])}
    if run_ids and run_ids != {str(run_id)}:
        return ["cross_run_lineage"]
    return []


def _first_verified_source_ref(candidate: OperationalCapability, artifacts: ArtifactStore,
                               task_id: str, run_id: str) -> str:
    for ref in candidate.source_trace_refs:
        try:
            sample = TransitionSample.from_dict(artifacts.read_json(ref))
        except Exception:
            continue
        if (sample.outcome == TransitionOutcome.VERIFIED_SUCCESS
                and str(sample.provenance.task_id) == str(task_id)
                and str(sample.provenance.run_id) == str(run_id)):
            return ref
    return ""


class _OwnerClosureView:
    """Answers the owner-side closure questions from facts the runtime reported."""

    def __init__(self, candidate: OperationalCapability, plan: Any, snapshot: Any, owner: RunAdoptionOwner,
                 verifier_ok: bool):
        self._proof = {
            "deterministic_representation": bool(candidate.implementation.get("steps")),
            "executable_primitive": all(owner.supports(t["tool"]) for t in plan.steps),
            "compatible_route": True,
            # Only constructed after plan_item_adoption() admitted authority + budget.
            "authority_policy_compatible": True,
            "verifier_readback": verifier_ok,
            "certified_dispatch": all(owner.supports(t["tool"]) for t in plan.steps),
            "uncertainty_clear": not snapshot.uncertain_mutations,
            "route": candidate.route,
        }
        self.has_uncertain_mutation = bool(snapshot.uncertain_mutations)

    def operational_closure_for_call(self, name: str, args: dict) -> dict:
        return self._proof


def validate_run_local_candidate(
    candidate: OperationalCapability,
    *,
    task_id: Optional[str],
    run_id: Optional[str],
    owner: Optional[RunAdoptionOwner],
    artifacts: ArtifactStore,
    corpus_artifacts: Optional[ArtifactStore] = None,
    contract_factory: Optional[Callable[[OperationalCapability], VerificationContract]] = None,
    decision_receipt_refs: tuple[str, ...] = (),
) -> tuple[bool, Optional[RunClosureProof], list[str], Optional[AdoptionOffer]]:
    """Return ``(valid, proof, reasons, offer)``. Fail closed on any missing owner evidence."""
    reasons: list[str] = []
    if not task_id or not run_id:
        return False, None, ["missing_canonical_identity"], None
    task_id, run_id = str(task_id), str(run_id)
    if owner is None:
        return False, None, ["no_runtime_owner"], None
    snapshot = owner.snapshot(task_id, run_id)
    if snapshot is None:
        return False, None, ["no_canonical_snapshot"], None

    meta = candidate.learning_metadata or {}
    if candidate.drift_state == "quarantined":
        reasons.append("candidate_quarantined")
    if meta.get("unresolved_counterexamples"):
        reasons.append("unresolved_counterexamples")
    if candidate.lifecycle == CapabilityLifecycle.PROMOTED:
        reasons.append("global_capability_is_not_run_local")
    reasons += candidate_lineage_denials(candidate, task_id, run_id)
    steps = candidate.implementation.get("steps", []) if isinstance(candidate.implementation, dict) else []
    if not steps:
        reasons.append("no_executable_steps")
    if not candidate.verifier_contract:
        reasons.append("missing_verifier_contract")
    if not meta.get("parameterization_quality"):
        reasons.append("single_example_candidate")
    if reasons:
        return False, None, reasons, None

    provider = get_validation_environment_provider()
    if provider is None or not (provider.verifier_evaluator and provider.safe_env_factory
                                and provider.replay_runner_factory):
        return False, None, ["validation_environment_unavailable"], None

    working = deepcopy(candidate)  # never mutate registry state while validating

    # 1. Verifier: owner-supplied contract, positive + discriminative negative receipts.
    try:
        contract = (contract_factory(working) if contract_factory
                    else VerificationContract.from_dict(working.verifier_contract))
        pos, neg = provider.verifier_evaluator(working, contract, task_id, run_id)
    except Exception as exc:
        logger.debug("verifier evaluation failed closed", exc_info=True)
        return False, None, [f"verifier_evaluation_error:{type(exc).__name__}"], None
    if not isinstance(pos, dict) or not isinstance(neg, dict):
        return False, None, ["verifier_receipts_unavailable"], None
    for label, receipt in (("positive", pos), ("negative", neg)):
        if not _resolves(artifacts, receipt.get("evidence_ref")):
            reasons.append(f"{label}_verifier_receipt_unresolvable")
        elif not _owned_by_run_namespace(receipt.get("evidence_ref"), task_id):
            reasons.append(f"{label}_verifier_receipt_foreign_run")
    first_vr_raw = pos.get("verification_result")
    if not isinstance(first_vr_raw, dict):
        reasons.append("first_verification_result_missing")
    if reasons:
        return False, None, reasons, None
    validated, v_reasons = validate_verifier_candidate(contract, [pos, neg])
    if v_reasons or validated.lifecycle != VerificationLifecycle.VALIDATED:
        return False, None, list(v_reasons) or ["verifier_not_validated"], None
    working.verifier_contract = validated.to_dict()
    working.learning_metadata["verifier_fingerprint"] = validated.fingerprint()
    working.learning_metadata["verifier_lifecycle"] = validated.lifecycle.value

    # 2. Controlled replay through the existing owner mechanism; positive only if canonical.
    replay_vr: Optional[VerificationResult] = None
    replay_ref = ""
    try:
        env = provider.safe_env_factory(working)
        runner = provider.replay_runner_factory(working, env)
        replayed = controlled_replay(working, env, runner)
    except Exception as exc:
        logger.debug("controlled replay failed closed", exc_info=True)
        return False, None, [f"controlled_replay_error:{type(exc).__name__}"], None
    evidence = next((e for e in reversed(replayed.validation_evidence)
                     if e.get("kind") == "controlled_replay"), None)
    if evidence is None or evidence.get("passed") is not True:
        return False, None, ["controlled_replay_failed"], None
    result = evidence.get("result") or {}
    try:
        replay_vr = VerificationResult.from_dict(result.get("verification_result") or {})
    except (TypeError, ValueError):
        return False, None, ["replay_verification_result_invalid"], None
    refs = list(result.get("evidence_refs") or ())
    if replay_vr.status != VerificationStatus.VERIFIED:
        reasons.append("replay_verification_not_verified")
    if not refs or not all(_resolves(artifacts, r) for r in refs):
        reasons.append("replay_evidence_unresolvable")
    elif not all(_owned_by_run_namespace(r, task_id) for r in refs):
        reasons.append("replay_evidence_foreign_run")
    if reasons:
        return False, None, reasons, None
    replay_ref = artifacts.store(task_id, f"run_local_replay_{candidate.id}.json", {
        "candidate_id": candidate.id, "task_id": task_id, "run_id": run_id,
        "environment": evidence.get("environment"),
        "compatibility_fingerprint": candidate.compatibility_fingerprint,
        "verifier_fingerprint": validated.fingerprint(),
        "verification_result": replay_vr.to_dict(), "evidence_refs": refs,
    }, schema=REPLAY_RECEIPT_SCHEMA).ref

    first_ref = _first_verified_source_ref(candidate, corpus_artifacts or artifacts, task_id, run_id)
    if not first_ref:
        return False, None, ["first_verified_evidence_missing"], None

    # 3. Next pending item through the same gates the runtime re-applies at the checkpoint.
    op_fam, tgt_fam = _families(candidate)
    offer = AdoptionOffer(
        offer_id="offer_" + digest([candidate.id, task_id, run_id])[:16], task_id=task_id, run_id=run_id,
        candidate_id=candidate.id, proof=None, steps=deepcopy(steps),  # type: ignore[arg-type]
        input_schema=deepcopy(candidate.input_schema), relations=list(meta.get("relations", [])),
        operation_family=op_fam, target_family=tgt_fam, route=candidate.route, scope=dict(candidate.scope or {}),
        decision_receipt_refs=list(decision_receipt_refs), replay_receipt_ref=replay_ref,
        verifier_receipt_refs=[pos["evidence_ref"], neg["evidence_ref"]], source_sample_refs=[first_ref],
    )
    plan, plan_reasons = plan_item_adoption(snapshot, offer, owner)
    if plan is None:
        return False, None, plan_reasons, None

    # 4. Proof through the owner's closure evaluator (never hand-built here).
    view = _OwnerClosureView(candidate, plan, snapshot, owner, verifier_ok=True)
    pre_validation_fp = replace(validated, lifecycle=VerificationLifecycle.CANDIDATE,
                                validation_evidence_refs=(), validation_receipts=()).fingerprint()
    ok, proof, closure_reasons = evaluate_run_local_closure(
        view, name=plan.steps[-1]["tool"], args={}, route=candidate.route, semantic_family=op_fam,
        semantic_fingerprint=candidate.semantic_fingerprint or candidate.compatibility_fingerprint,
        contract={"effect": candidate.effect, "target_family": tgt_fam},
        task_id=task_id, run_id=run_id, operation_id=f"op_runlocal_{candidate.id[:12]}",
        first_verified_ref=first_ref, replay_verified_ref=replay_ref,
        verifier_contract=validated.to_dict(),
        first_verification_result=first_vr_raw,
        replay_verification_result=replay_vr.to_dict(),
        required_predicates=set(validated.covered_predicates),
        remaining_items_ref=snapshot.remaining_items_ref, remaining_item_count=len(snapshot.pending_items),
        requested_authority=plan.required_authority, authorized_authority=snapshot.authority,
        requested_effects=plan.effects, effect_budget=list(snapshot.effect_budget),
        parameter_schema=candidate.input_schema, bindings=meta.get("bindings", {}),
        deterministic_ref=f"capability:{candidate.id}", executable_primitive_or_capability=candidate.id,
        source_trace_refs=list(candidate.source_trace_refs),
        has_uncertain_mutation=bool(snapshot.uncertain_mutations),
        first_verifier_fingerprint=pre_validation_fp,
    )
    if not ok or proof is None:
        return False, None, closure_reasons or ["closure_not_proven"], None
    offer.proof = proof
    return True, proof, [], offer

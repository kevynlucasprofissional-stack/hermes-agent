"""Bounded read-only recovery, using the existing verifier and source owner."""
from workstation.control_plane.verification import evaluate_verification


def bind_native_reprobe(compiler, objective, task, session_id):
    """Use native owner persistence for the already-established URL goal."""
    from workstation.control_plane.ir import Predicate, EQ
    goal = Predicate.from_dict(objective["operation_intent"]["goal"])
    if not isinstance(goal, EQ) or goal.path != "url" or objective["operation_intent"].get("target") != "native_browser":
        return
    operation_id = objective.get("operation_id")
    if not operation_id or task.current_run_id is None:
        return
    from workstation.control_plane.verification import VerificationContract, VerificationLifecycle, VerificationEvidence
    from workstation.execution_policy import EvidenceStrength
    compiler.authoritative_state_contract = VerificationContract(
        observer="workstation.browser_session_state", source_kind="browser_local_persistence",
        minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK, allowed_trust=("trusted_runtime",),
        covered_predicates=(goal.fingerprint(),), lifecycle=VerificationLifecycle.VALIDATED,
        temporal_basis="revision", max_age_seconds=30)
    def read():
        from tools.browser_workstation import read_native_browser_session_state
        from workstation.experience_compiler.state_abstraction import abstract_state
        try:
            observed = read_native_browser_session_state(task.id, session_id, str(task.current_run_id), str(goal.value),
                expected_operation_id=operation_id, require_owner_receipt=True)
        except (OSError, ValueError, RuntimeError):
            return []
        state = abstract_state("native_browser", observed).semantic_predicates
        ref = compiler.artifacts.store(task.id, "native_reprobe_observation.json", state)
        return [VerificationEvidence(evidence_id=ref.ref, artifact_ref=ref.ref,
            observer="workstation.browser_session_state", source_kind="browser_local_persistence",
            value=state, evidence_strength=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
            trust_class="trusted_runtime", resource_version=str(observed.get("revision", "")),
            observed_at=observed.get("saved_at", ""), covered_predicates=(goal.fingerprint(),),
            task_id=task.id, run_id=str(task.current_run_id), operation_id=operation_id)]
    compiler.authoritative_state_reader = read


def resolve_reprobe(compiler, intent, task_id, session_id):
    # Only an owner-bound reader is eligible. Request/model data cannot supply
    # a callable or convert an arbitrary tool into trusted observation.
    reader = getattr(compiler, "authoritative_state_reader", None)
    contract = getattr(compiler, "authoritative_state_contract", None)
    if not callable(reader) or contract is None:
        return None
    evidence = reader()
    if not evidence:
        return None
    state = evidence[0].value if hasattr(evidence[0], "value") else evidence[0].get("value")
    if not isinstance(state, dict) or not intent.goal.evaluate(state):
        return None
    verdict = evaluate_verification(contract, state, evidence,
        required_predicates={intent.goal.fingerprint()}, expected_task_id=task_id,
        expected_run_id=getattr(compiler, "canonical_run_id", None))
    if not verdict.verified:
        return None
    ref = compiler.artifacts.store(task_id, "known_reprobe_verification.json", verdict.to_dict(),
        schema="workstation.verification_result.v1")
    from workstation.telemetry import TelemetryEventType, emit_event
    emit_event(TelemetryEventType.VERIFICATION_COMPLETED, source_owner="workstation.known_recovery_verifier",
        task_id=task_id, run_id=getattr(compiler, "canonical_run_id", None), operation_id=intent.id,
        route="deterministic", status=verdict.status.value, evidence_refs=(ref.ref,),
        dedupe_key=f"reprobe-verification:{task_id}:{getattr(compiler, 'canonical_run_id', None)}:{intent.id}")
    return {"success": True, "routing_decision": "SATISFIED", "resolution": "REPROBE",
        "semantic_state": state, "verification_result": verdict.to_dict(), "verification_ref": ref.ref,
        "system2_calls": 0, "session_id": session_id}

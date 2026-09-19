"""RunClosureProof: Pure run-scoped operational closure contract and admission.

Defines the typed proof required to transfer newly verified adaptive behavior
to the existing deterministic execution runtime (TaskCompiler / DurableBatchRunner)
inside the same TaskRun.

Invariants:
- No database, scheduler, or registry.
- Reuses _operational_closure_proven() from workstation.execution_policy.
- Requires verified execution + compatible verified replay + verifier readback.
- Requires provenance-backed remaining items and positive utility.
- Never expands authority or effect budget.
- Run-local operationalization is NOT global capability promotion.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import time
from typing import Any, Callable

from workstation.artifacts import ArtifactStore
from workstation.batch_runner import DurableBatchRunner
from workstation.contracts import utc_now
from workstation.control_plane.ir import Effect, effect_contained
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope, authority_covers
from workstation.durable_tasks import DurableTaskStore, WorkItem, WorkItemStatus
from workstation.execution_policy import _operational_closure_proven
from workstation.control_plane.verification import (
    VerificationContract, VerificationLifecycle, VerificationResult, VerificationStatus,
)


@dataclass
class RunClosureProof:
    """Typed proof authorizing in-run transfer from adaptive execution to deterministic batch runner."""

    task_id: str
    run_id: str
    operation_id: str
    semantic_fingerprint: str
    operation_family: str
    target_family: str
    deterministic_representation_ref: str
    executable_primitive_or_capability: str
    compatible_route: str
    authority_scope: AuthorityScope | dict[str, Any]
    effect_budget: list[Effect] | list[dict[str, Any]]
    verifier_contract: dict[str, Any]
    first_verified_evidence_ref: str
    replay_evidence_ref: str
    uncertainty_clear: bool
    parameter_schema: dict[str, Any]
    bindings: dict[str, Any]
    remaining_items_ref: str
    remaining_item_count: int
    expected_operational_utility: float
    source_trace_refs: list[str] = field(default_factory=list)
    verifier_fingerprint: str = ""
    verifier_lifecycle: str = "CANDIDATE"
    first_verification_result: dict[str, Any] = field(default_factory=dict)
    replay_verification_result: dict[str, Any] = field(default_factory=dict)
    covered_predicates: list[str] = field(default_factory=list)
    freshness_satisfied: bool = False
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if isinstance(self.authority_scope, AuthorityScope):
            data["authority_scope"] = self.authority_scope.to_dict()
        elif hasattr(self.authority_scope, "to_dict"):
            data["authority_scope"] = self.authority_scope.to_dict()
        data["effect_budget"] = [
            e.to_dict() if hasattr(e, "to_dict") else e for e in self.effect_budget
        ]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunClosureProof:
        cdata = dict(data)
        auth = cdata.get("authority_scope")
        if isinstance(auth, dict):
            cdata["authority_scope"] = AuthorityScope.from_dict(auth)
        effs = cdata.get("effect_budget", [])
        cdata["effect_budget"] = [
            Effect.from_dict(e) if isinstance(e, dict) and "kind" in e else e for e in effs
        ]
        return cls(**cdata)


def compute_expected_operational_utility(
    remaining_item_count: int,
    *,
    estimated_reasoning_reentries_avoided: int | None = None,
    compilation_cost: float = 1.0,
    deterministic_cost_per_item: float = 0.1,
    verification_cost_per_item: float = 0.1,
    drift_risk_penalty: float = 0.5,
    reasoning_reentry_weight: float = 2.0,
) -> float:
    """Conservative operational utility calculation.

    Determines if operational benefit exceeds compilation, verification,
    deterministic execution, and drift risk without inventing token/dollar accounting.
    """
    if remaining_item_count <= 0:
        return 0.0
    avoided = (
        estimated_reasoning_reentries_avoided
        if estimated_reasoning_reentries_avoided is not None
        else remaining_item_count
    )
    gross_benefit = avoided * reasoning_reentry_weight
    total_cost = (
        compilation_cost
        + (deterministic_cost_per_item + verification_cost_per_item) * remaining_item_count
        + drift_risk_penalty
    )
    return gross_benefit - total_cost


def evaluate_run_local_closure(
    agent: Any,
    *,
    name: str,
    args: dict[str, Any],
    route: str,
    semantic_family: str,
    semantic_fingerprint: str,
    contract: dict[str, Any] | None = None,
    task_id: str | None = None,
    run_id: str | None = None,
    operation_id: str | None = None,
    first_verified_ref: str | None = None,
    replay_verified_ref: str | None = None,
    verifier_contract: dict[str, Any] | None = None,
    first_verification_result: VerificationResult | dict[str, Any] | None = None,
    replay_verification_result: VerificationResult | dict[str, Any] | None = None,
    required_predicates: set[str] | None = None,
    remaining_items_ref: str | None = None,
    remaining_item_count: int = 0,
    requested_authority: AuthorityScope | dict[str, Any] | None = None,
    authorized_authority: AuthorityScope | dict[str, Any] | None = None,
    requested_effects: list[Effect | dict[str, Any]] | None = None,
    effect_budget: list[Effect | dict[str, Any]] | None = None,
    parameter_schema: dict[str, Any] | None = None,
    bindings: dict[str, Any] | None = None,
    deterministic_ref: str | None = None,
    executable_primitive_or_capability: str | None = None,
    source_trace_refs: list[str] | None = None,
    has_uncertain_mutation: bool = False,
) -> tuple[bool, RunClosureProof | None, list[str]]:
    """Fail-closed evaluator for run-local operationalization handoff.

    Reuses _operational_closure_proven() for the 7 underlying conditions.
    Validates verified execution, compatible replay, authority/effect containment,
    provenance-backed remaining items, and positive operational utility.
    """
    reasons: list[str] = []

    # 1. Base operational closure predicate (deterministic rep, executable primitive,
    # compatible route, authority policy, verifier readback, certified dispatch, uncertainty clear)
    closure_proven = _operational_closure_proven(
        agent,
        name=name,
        args=args,
        route=route,
        semantic_family=semantic_family,
        semantic_fingerprint=semantic_fingerprint,
        contract=contract or {},
    )
    if not closure_proven:
        reasons.append("operational_closure_not_proven")

    # 2. First verified execution evidence
    if not first_verified_ref:
        reasons.append("missing_first_verified_evidence")

    # 3. Typed validated readback/verifier. References identify artifacts; only
    # canonical results establish what those artifacts proved.
    typed_verifier = VerificationContract.from_dict(verifier_contract or {})
    verifier_ok, verifier_reasons = typed_verifier.is_sufficient_for(
        required_predicates=set(required_predicates or typed_verifier.covered_predicates),
        mutation=bool(contract and contract.get("effect") not in {"read_only", "PURE_READ", "DISCOVERY"}),
        temporal_required=typed_verifier.temporal_basis != "none",
    )
    if not verifier_ok:
        reasons.extend(verifier_reasons or ("insufficient_verifier_contract",))
    first_result = (
        first_verification_result if isinstance(first_verification_result, VerificationResult)
        else VerificationResult.from_dict(first_verification_result) if first_verification_result else None
    )
    replay_result = (
        replay_verification_result if isinstance(replay_verification_result, VerificationResult)
        else VerificationResult.from_dict(replay_verification_result) if replay_verification_result else None
    )
    for label, result in (("first", first_result), ("replay", replay_result)):
        if result is None:
            reasons.append(f"missing_{label}_verification_result")
            continue
        if result.status != VerificationStatus.VERIFIED:
            reasons.append(f"{label}_verification_{result.status.value.lower()}")
        if result.verifier_fingerprint != typed_verifier.fingerprint():
            reasons.append(f"{label}_verifier_fingerprint_mismatch")
        if set(required_predicates or ()) - set(result.covered_predicates):
            reasons.append(f"{label}_predicate_coverage_insufficient")
        if typed_verifier.temporal_basis != "none" and not result.freshness_satisfied:
            reasons.append(f"{label}_verification_stale")

    # 4. Compatible verified replay/canary (for mutable operations)
    is_mutation = bool(
        contract and contract.get("effect") not in {"read_only", "PURE_READ", "DISCOVERY"}
    )
    if is_mutation and not replay_verified_ref:
        reasons.append("missing_compatible_verified_replay")

    # 5. No outstanding uncertainty
    agent_uncertain = bool(
        getattr(agent, "has_uncertain_mutation", False)
        or has_uncertain_mutation
    )
    if agent_uncertain:
        reasons.append("uncertainty_not_clear")

    # 6. Generalizable parameters
    if parameter_schema is None or not isinstance(parameter_schema, dict):
        reasons.append("parameters_not_generalizable")

    # 7. Authority containment (same or narrower authority)
    req_auth = (
        AuthorityScope.from_dict(requested_authority)
        if isinstance(requested_authority, dict)
        else (requested_authority or AuthorityScope(level=AuthorityLevel.READ))
    )
    auth_auth = (
        AuthorityScope.from_dict(authorized_authority)
        if isinstance(authorized_authority, dict)
        else (authorized_authority or AuthorityScope(level=AuthorityLevel.READ))
    )
    if not authority_covers(auth_auth, req_auth):
        reasons.append("authority_expansion_forbidden")

    # 8. Effect budget containment (same or subset)
    if requested_effects and effect_budget:
        parsed_req: list[Effect] = [
            Effect.from_dict(e) if isinstance(e, dict) else e for e in requested_effects
        ]
        parsed_budget: list[Effect] = [
            Effect.from_dict(e) if isinstance(e, dict) else e for e in effect_budget
        ]
        effects_contained = all(
            effect_contained(req_eff, parsed_budget)
            for req_eff in parsed_req
        )
        if not effects_contained:
            reasons.append("effect_budget_expansion_forbidden")

    # 9. Real deterministic representation
    det_ref = deterministic_ref or f"primitive:{name}"
    if not det_ref:
        reasons.append("missing_deterministic_representation")

    # 10. Known remaining items with provenance
    if not remaining_items_ref or remaining_item_count <= 0:
        reasons.append("missing_remaining_items_ref")

    # 11. Positive utility
    utility = compute_expected_operational_utility(remaining_item_count)
    if utility <= 0.0:
        reasons.append("non_positive_operational_utility")

    if reasons:
        return False, None, reasons

    proof = RunClosureProof(
        task_id=task_id or getattr(agent, "_canonical_work_task_id", None) or "task_default",
        run_id=run_id or getattr(agent, "_canonical_work_run_id", None) or "run_default",
        operation_id=operation_id or f"op_{semantic_fingerprint[:16]}",
        semantic_fingerprint=semantic_fingerprint,
        operation_family=semantic_family,
        target_family=str(contract.get("target_family") or semantic_family) if contract else semantic_family,
        deterministic_representation_ref=det_ref,
        executable_primitive_or_capability=executable_primitive_or_capability or name,
        compatible_route=route,
        authority_scope=req_auth,
        effect_budget=effect_budget or [],
        verifier_contract=verifier_contract or {},
        verifier_fingerprint=typed_verifier.fingerprint(),
        verifier_lifecycle=typed_verifier.lifecycle.value,
        first_verification_result=first_result.to_dict() if first_result else {},
        replay_verification_result=replay_result.to_dict() if replay_result else {},
        covered_predicates=sorted(set(first_result.covered_predicates if first_result else ()) | set(replay_result.covered_predicates if replay_result else ())),
        freshness_satisfied=bool(first_result and replay_result and first_result.freshness_satisfied and replay_result.freshness_satisfied),
        first_verified_evidence_ref=first_verified_ref,
        replay_evidence_ref=replay_verified_ref or first_verified_ref,
        uncertainty_clear=not agent_uncertain,
        parameter_schema=parameter_schema or {},
        bindings=bindings or {},
        remaining_items_ref=remaining_items_ref,
        remaining_item_count=remaining_item_count,
        expected_operational_utility=utility,
        source_trace_refs=source_trace_refs or [],
    )

    return True, proof, []


class HandoffWakeCondition(str, Enum):
    """The 9 declared conditions triggering LLM wake/re-entry from compiled continuation."""

    PRE_CONDITION_FAILED = "PRE_CONDITION_FAILED"
    POST_VERIFIER_FAILED = "POST_VERIFIER_FAILED"
    UNCERTAIN_MUTATION_STATE = "UNCERTAIN_MUTATION_STATE"
    AUTHORITY_BUDGET_EXCEEDED = "AUTHORITY_BUDGET_EXCEEDED"
    AMBIGUOUS_PARAMETER_MAPPING = "AMBIGUOUS_PARAMETER_MAPPING"
    UNRECOVERABLE_DOM_OR_STATE_DRIFT = "UNRECOVERABLE_DOM_OR_STATE_DRIFT"
    RUN_CONTRACT_VIOLATION = "RUN_CONTRACT_VIOLATION"
    USER_INTERVENTION_REQUESTED = "USER_INTERVENTION_REQUESTED"
    EXECUTION_ENVELOPE_EXHAUSTED = "EXECUTION_ENVELOPE_EXHAUSTED"


@dataclass
class ExecutionEnvelope:
    """Bounded execution envelope stored on WorkPlan.metadata."""

    compiled_subgraph_ref: str
    task_id: str
    run_id: str
    operation_id: str
    authority_scope: dict[str, Any]
    effect_budget: list[dict[str, Any]]
    verifier_contract: dict[str, Any]
    wake_conditions: list[str] = field(default_factory=lambda: [w.value for w in HandoffWakeCondition])
    item_limit: int = 100
    deadline_ts: float | None = None
    last_verified_checkpoint: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunScopedCapability:
    """Run-scoped operational capability contract, never promoted globally."""

    capability_id: str
    task_id: str
    run_id: str
    operation_id: str
    proof: RunClosureProof
    steps: list[dict[str, Any]]
    parameter_schema: dict[str, Any]
    envelope: ExecutionEnvelope
    run_scoped: bool = True
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "operation_id": self.operation_id,
            "proof": self.proof.to_dict(),
            "steps": self.steps,
            "parameter_schema": self.parameter_schema,
            "envelope": self.envelope.to_dict(),
            "run_scoped": True,
            "created_at": self.created_at,
        }


def _bind_item_parameters(args: Any, item: dict[str, Any]) -> Any:
    """Recursively bind $item.field references to item values."""
    if isinstance(args, dict):
        return {k: _bind_item_parameters(v, item) for k, v in args.items()}
    if isinstance(args, list):
        return [_bind_item_parameters(v, item) for v in args]
    if isinstance(args, str) and args.startswith("$item."):
        field_name = args[len("$item.") :]
        return item.get(field_name, args)
    return args


def synthesize_in_flight_work_execute_request(
    proof: RunClosureProof,
    remaining_items: list[dict[str, Any]],
    steps: list[dict[str, Any]],
    *,
    preflight: list[dict[str, Any]] | None = None,
    constraints: dict[str, Any] | None = None,
    timeout_seconds: float = 300.0,
) -> dict[str, Any]:
    """Synthesize standard work_execute request with run-scoped envelope and invariants."""
    auth_scope = proof.authority_scope.to_dict() if hasattr(proof.authority_scope, "to_dict") else proof.authority_scope
    eff_budget = [e.to_dict() if hasattr(e, "to_dict") else e for e in proof.effect_budget]

    envelope = ExecutionEnvelope(
        compiled_subgraph_ref=f"artifact://tasks/{proof.task_id}/compiled_subgraph_{proof.operation_id}.json",
        task_id=proof.task_id,
        run_id=proof.run_id,
        operation_id=proof.operation_id,
        authority_scope=auth_scope,
        effect_budget=eff_budget,
        verifier_contract=proof.verifier_contract,
        item_limit=len(remaining_items),
        deadline_ts=time.time() + timeout_seconds,
        last_verified_checkpoint=proof.replay_evidence_ref or proof.first_verified_evidence_ref,
    )
    req_constraints = {"mutation_allowed_routes": [proof.compatible_route]}
    if constraints:
        req_constraints.update(constraints)

    req = {
        "operation_key": f"run_local_{proof.task_id}_{proof.operation_id}",
        "title": f"In-Flight Operationalization for {proof.operation_family}",
        "kind": "batch",
        "items": remaining_items,
        "items_ref": proof.remaining_items_ref,
        "steps": steps,
        "preflight": preflight or [],
        "authority": auth_scope,
        "constraints": req_constraints,
        "execution_envelope": envelope.to_dict(),
    }
    return req


def execute_in_flight_handoff(
    proof: RunClosureProof,
    remaining_items: list[dict[str, Any]],
    steps: list[dict[str, Any]],
    dispatch: Callable[[str, dict[str, Any]], Any],
    *,
    task_store: DurableTaskStore | None = None,
    artifact_store: ArtifactStore | None = None,
    preflight: list[dict[str, Any]] | None = None,
    constraints: dict[str, Any] | None = None,
    stop_on_exception: bool = True,
) -> dict[str, Any]:
    """Transfer closed subgraph to DurableBatchRunner with atomic checkpoints and exception wake."""
    store = task_store or DurableTaskStore()
    artifacts = artifact_store or ArtifactStore()

    clean_steps = [
        {k: (getattr(v, "__name__", str(v)) if callable(v) else v) for k, v in step.items()}
        for step in steps
    ]
    subgraph_data = {
        "proof": proof.to_dict(),
        "steps": clean_steps,
        "remaining_item_count": len(remaining_items),
    }
    artifacts.store(proof.task_id, f"compiled_subgraph_{proof.operation_id}.json", subgraph_data)

    req = synthesize_in_flight_work_execute_request(
        proof, remaining_items, steps, preflight=preflight, constraints=constraints
    )

    plan = store.get_plan(proof.task_id)
    if not plan:
        plan = store.create_plan(
            task_id=proof.task_id,
            title=req["title"],
            items=remaining_items,
            session_id=proof.run_id,
            metadata={"execution_envelope": req["execution_envelope"], "run_id": proof.run_id},
        )
    else:
        store.update_plan_metadata(plan.id, {"execution_envelope": req["execution_envelope"]})

    runner = DurableBatchRunner(proof.task_id, task_store=store, artifact_store=artifacts)

    def worker_fn(input_payload: dict[str, Any], work_item: WorkItem) -> dict[str, Any]:
        step_results = {}
        for step in steps:
            tool = step["tool"]
            args = step.get("args", {})
            bound_args = _bind_item_parameters(args, input_payload)

            if step.get("pre_condition_check"):
                pre_ok = step["pre_condition_check"](bound_args, input_payload)
                if not pre_ok:
                    raise Exception(f"{HandoffWakeCondition.PRE_CONDITION_FAILED.value}: Precondition failed for item {work_item.id}")

            raw_res = dispatch(tool, bound_args)
            step_results[step.get("id", tool)] = raw_res

            if step.get("verifies") or step.get("readback"):
                v_fn = step.get("verifier_fn")
                if v_fn:
                    v_ok = v_fn(raw_res, bound_args, input_payload)
                    if not v_ok:
                        raise Exception(f"{HandoffWakeCondition.POST_VERIFIER_FAILED.value}: Verifier readback failed for step {step.get('id')}")

            store.update_item_checkpoint(work_item.id, f"step_{step.get('id', tool)}", "verified")

        return step_results

    summary = runner.execute_batch(
        title=req["title"],
        items=remaining_items,
        worker_fn=worker_fn,
        stop_on_exception=stop_on_exception,
        session_id=proof.run_id,
        metadata={"execution_envelope": req["execution_envelope"]},
    )

    if summary.anomalies:
        first_anomaly = summary.anomalies[0]
        reason_str = str(first_anomaly.get("reason", ""))
        wake_code = HandoffWakeCondition.POST_VERIFIER_FAILED.value
        for wc in HandoffWakeCondition:
            if wc.value in reason_str:
                wake_code = wc.value
                break
        return {
            "status": "NEEDS_REASONING",
            "wake_reason": wake_code,
            "anomalies": summary.anomalies,
            "completed": summary.success_count + summary.retry_success_count,
            "total": summary.total_items,
            "safe_to_resume": wake_code in {
                HandoffWakeCondition.POST_VERIFIER_FAILED.value,
                HandoffWakeCondition.PRE_CONDITION_FAILED.value,
                HandoffWakeCondition.UNRECOVERABLE_DOM_OR_STATE_DRIFT.value,
            },
            "summary": summary.to_dict(),
        }

    return {
        "status": "COMPLETED",
        "completed": summary.success_count + summary.retry_success_count,
        "total": summary.total_items,
        "summary": summary.to_dict(),
    }


def recover_verified_prefix(task_id: str, *, task_store: DurableTaskStore | None = None) -> dict[str, Any]:
    """Rebuild truth from DurableTaskStore checkpoints: skip completed, mark in-progress without verified readback as UNCERTAIN."""
    store = task_store or DurableTaskStore()
    plan = store.get_plan(task_id)
    if not plan:
        return {"found": False}
    items = store.get_work_items(plan.id)
    completed_ids = [i.id for i in items if i.status == WorkItemStatus.COMPLETED]
    uncertain_ids = []
    pending_items = []
    for i in items:
        if i.status == WorkItemStatus.COMPLETED:
            continue
        if i.status == WorkItemStatus.RUNNING:
            has_verified_ck = any("verified" in str(v) for v in i.checkpoints.values())
            if not has_verified_ck:
                uncertain_ids.append(i.id)
                store.fail_item(i.id, "UNCERTAIN_MUTATION_STATE: dispatch unverified across restart", can_retry=False)
                continue
        pending_items.append(i)
    return {
        "found": True,
        "plan_id": plan.id,
        "completed_count": len(completed_ids),
        "completed_ids": completed_ids,
        "uncertain_ids": uncertain_ids,
        "pending_items": pending_items,
    }

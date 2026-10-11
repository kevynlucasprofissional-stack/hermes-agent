"""Runtime-owned contracts for run-local adoption of freshly learned procedures.

The Online Compilability learning plane (``experience_compiler/compilability_monitor.py``)
only *proposes*: it mines a candidate, has it independently validated and records an
:class:`AdoptionOffer`. Everything that decides whether an offer may touch the world is
owned here, by the runtime side, and is re-read at the moment of use:

* canonical TaskRun identity, lease and revocation state (kanban task/run, ``classify_run_authority``);
* the policy-granted ``AuthorityScope`` ceiling and the admitted intent's effect budget;
* the real pending ``WorkItem`` set and outstanding uncertain mutations (``DurableTaskStore``);
* certified dispatch and independent readback.

The monitor never constructs any of these. :class:`RunLocalAdopter` is invoked by the
runtime at a safe checkpoint, executes the *next* equivalent pending item through the
existing ``execute_in_flight_handoff`` and counts it as reuse only after terminal,
independently read-back verification.
"""
from __future__ import annotations

import copy
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Protocol, Sequence

from workstation.artifacts import ArtifactStore
from workstation.control_plane.ir import CALL, CREATE, MOVE, Effect, effect_contained
from workstation.control_plane.lattice import (
    AuthorityLevel,
    AuthorityScope,
    authority_covers,
    extract_effect_authority_requirements,
    join_all,
)
from workstation.durable_tasks import DurableTaskStore, WorkItemStatus
from workstation.run_closure import RunClosureProof, execute_in_flight_handoff

logger = logging.getLogger(__name__)

REUSE_RECEIPT_SCHEMA = "workstation.run_local_reuse_receipt.v1"
REPLAY_RECEIPT_SCHEMA = "workstation.run_local_replay_receipt.v1"
VERIFICATION_RESULT_SCHEMA = "workstation.verification_result.v1"

_TERMINAL_PLAN_STATES = {"cancelled", "completed", "failed", "aborted"}


@dataclass(frozen=True)
class PendingRunItem:
    """One real, not-yet-completed work item of the canonical plan."""

    item_id: str
    item_index: int
    payload: dict[str, Any]
    status: str
    attempts: int
    has_checkpoints: bool
    operation_family: str = ""
    target_family: str = ""


@dataclass(frozen=True)
class CanonicalRunSnapshot:
    """What the runtime currently knows about one TaskRun. Never built by the learning plane."""

    task_id: str
    run_id: str
    plan_id: str
    authority: AuthorityScope
    effect_budget: tuple[Effect, ...]
    lease_valid: bool
    termination: str
    uncertain_mutations: tuple[dict[str, Any], ...]
    pending_items: tuple[PendingRunItem, ...]
    remaining_items_ref: str
    allowed_targets: frozenset[str]
    observed_at: float = field(default_factory=time.time)


class RunAdoptionOwner(Protocol):
    """Runtime-side authority for one agent/session. Implemented by the Hermes integration."""

    task_store: DurableTaskStore
    artifacts: ArtifactStore

    def snapshot(self, task_id: str, run_id: str) -> Optional[CanonicalRunSnapshot]: ...

    def supports(self, primitive: str) -> bool: ...

    def dispatch(self, tool: str, args: dict[str, Any]) -> Any: ...

    def readback(self, primitive: str, bound_args: dict[str, Any], raw: Any) -> Optional[dict[str, Any]]: ...

    def can_readback(self, primitive: str) -> bool: ...

    def system2_call_count(self) -> Optional[int]: ...


@dataclass
class AdoptionOffer:
    """A validated, run-scoped procedure waiting for a runtime checkpoint. Grants nothing."""

    offer_id: str
    task_id: str
    run_id: str
    candidate_id: str
    proof: RunClosureProof
    steps: list[dict[str, Any]]
    input_schema: dict[str, Any]
    relations: list[dict[str, Any]]
    operation_family: str
    target_family: str
    route: str
    scope: dict[str, Any] = field(default_factory=dict)
    decision_receipt_refs: list[str] = field(default_factory=list)
    replay_receipt_ref: str = ""
    verifier_receipt_refs: list[str] = field(default_factory=list)
    source_sample_refs: list[str] = field(default_factory=list)
    status: str = "ready"
    revoked_reason: str = ""


# --------------------------------------------------------------------------- effects

_READ_ONLY_PRIMITIVES = {
    "read_file", "fs_read", "fs_stat", "fs_hash", "hash_file", "stat", "process_observe",
    "browser_snapshot", "snapshot", "browser_navigate", "navigate", "browser_scroll", "scroll",
    "browser_extract_items", "wait",
}
_BROWSER_MUTATIONS = {"browser_click", "browser_type", "browser_press", "click", "fill", "press"}


def effects_for_step(primitive: str, args: dict[str, Any], scope: dict[str, Any]) -> Optional[list[Effect]]:
    """Owner table: effects a step can have, or ``None`` when they cannot be established."""
    if primitive in _READ_ONLY_PRIMITIVES:
        return []
    if primitive in {"write_file", "fs_write", "fs_mkdir", "mkdir"}:
        path = args.get("path")
        return [CREATE(str(path))] if path else None
    if primitive in {"fs_copy", "copy"}:
        dst = args.get("dst") or args.get("destination")
        return [CREATE(str(dst))] if dst else None
    if primitive in {"fs_move", "move"}:
        src, dst = args.get("src") or args.get("source"), args.get("dst") or args.get("destination")
        return [MOVE(str(src), str(dst))] if src and dst else None
    if primitive in _BROWSER_MUTATIONS:
        host = scope.get("host")
        return [CALL("browser." + primitive, str(host))] if host else None
    return None


_INPUT_REF = re.compile(r"\$inputs\.([A-Za-z0-9_]+)")


def bind_inputs(value: Any, inputs: dict[str, Any]) -> Any:
    """Replace ``$inputs.name`` with concrete values (whole-value keeps type, embedded stringifies)."""
    if isinstance(value, dict):
        return {k: bind_inputs(v, inputs) for k, v in value.items()}
    if isinstance(value, list):
        return [bind_inputs(v, inputs) for v in value]
    if isinstance(value, str):
        whole = _INPUT_REF.fullmatch(value)
        if whole:
            return inputs[whole.group(1)]
        return _INPUT_REF.sub(lambda m: str(inputs[m.group(1)]), value)
    return value


@dataclass
class ItemAdoptionPlan:
    item: PendingRunItem
    inputs: dict[str, Any]
    steps: list[dict[str, Any]]
    effects: list[Effect]
    required_authority: AuthorityScope


def plan_item_adoption(
    snapshot: Optional[CanonicalRunSnapshot],
    offer: AdoptionOffer,
    owner: RunAdoptionOwner,
) -> tuple[Optional[ItemAdoptionPlan], list[str]]:
    """Fail-closed gate list for adopting the *next* pending item. Empty reasons => plan."""
    if snapshot is None:
        return None, ["no_canonical_snapshot"]
    if not snapshot.pending_items:
        return None, ["no_pending_items"]
    reasons: list[str] = []
    if (snapshot.task_id, str(snapshot.run_id)) != (offer.task_id, str(offer.run_id)):
        reasons.append("run_identity_mismatch")
    if snapshot.termination:
        reasons.append("authority_" + snapshot.termination.lower())
    if not snapshot.lease_valid:
        reasons.append("lease_not_valid")
    if snapshot.uncertain_mutations:
        reasons.append("uncertain_mutation_outstanding")
    if reasons:
        return None, reasons

    item = snapshot.pending_items[0]
    if item.status != WorkItemStatus.PENDING.value or item.attempts or item.has_checkpoints:
        return None, ["next_item_not_fresh"]
    if (item.operation_family, item.target_family) != (offer.operation_family, offer.target_family):
        return None, ["item_not_equivalent"]
    if offer.target_family not in snapshot.allowed_targets and "*" not in snapshot.allowed_targets:
        return None, ["target_identity_unproven"]

    from workstation.experience_compiler.generalization import validate_inputs

    props = offer.input_schema.get("properties", {})
    if not props:
        return None, ["no_generalized_parameters"]
    inputs = {k: item.payload[k] for k in props if k in item.payload}
    for relation in offer.relations:  # relations the compiler itself proved: equal variables share a value
        if relation.get("relation") == "equal":
            left, right = relation.get("left"), relation.get("right")
            if left in inputs and right in props and right not in inputs:
                inputs[right] = inputs[left]
            elif right in inputs and left in props and left not in inputs:
                inputs[left] = inputs[right]
    try:
        validate_inputs(offer.input_schema, offer.relations, inputs)
    except Exception as exc:  # schema/relation violations all deny adoption
        return None, [f"parameters_invalid:{type(exc).__name__}"]

    steps: list[dict[str, Any]] = []
    effects: list[Effect] = []
    for step in offer.steps:
        if step.get("when"):
            return None, ["conditional_step_unsupported"]
        primitive = str(step.get("primitive", ""))
        args = bind_inputs(copy.deepcopy(step.get("args", {})), inputs)
        # A literal the candidate learned must agree with what THIS item asks for: a step that
        # would touch another target than the item's own is never "equivalent" work.
        if any(k in item.payload and item.payload[k] != v for k, v in args.items()):
            return None, ["bound_args_diverge_from_item"]
        step_effects = effects_for_step(primitive, args, offer.scope)
        if step_effects is None:
            return None, [f"effect_unmappable:{primitive}"]
        if not owner.supports(primitive):
            return None, [f"primitive_not_certified:{primitive}"]
        if step_effects and not owner.can_readback(primitive):
            return None, [f"readback_unavailable:{primitive}"]
        effects.extend(step_effects)
        steps.append({"id": step.get("id", primitive), "tool": primitive, "args": args,
                      "_effects": step_effects})

    required = join_all([extract_effect_authority_requirements(e) for e in effects]) if effects \
        else AuthorityScope(level=AuthorityLevel.READ)
    if not authority_covers(snapshot.authority, required):
        return None, ["authority_not_granted"]
    if effects:
        if not snapshot.effect_budget:
            return None, ["effect_budget_missing"]
        if not all(effect_contained(e, list(snapshot.effect_budget)) for e in effects):
            return None, ["effect_outside_budget"]
    return ItemAdoptionPlan(item, inputs, steps, effects, required), []


# --------------------------------------------------------------------------- adoption

class AdoptionSink(Protocol):
    """Receives offers and outcomes; implemented by the monitor (no authority)."""

    def ready_offers(self, task_id: str, run_id: str) -> list[AdoptionOffer]: ...

    def record_adoption(self, task_id: str, run_id: str, record: dict[str, Any]) -> None: ...


@dataclass
class AdoptionReport:
    status: str = "no_offer"
    items: list[dict[str, Any]] = field(default_factory=list)
    denied: list[str] = field(default_factory=list)
    all_items_completed: bool = False
    receipt_refs: list[str] = field(default_factory=list)


def _evidence_resolves(artifacts: ArtifactStore, ref: Any) -> bool:
    if not isinstance(ref, str) or not ref:
        return False
    try:
        artifacts.resolve_structured(ref)
    except (OSError, ValueError, KeyError):
        return False
    return True


class RunLocalAdopter:
    """Executes validated offers at a runtime checkpoint; one item at a time, verified before the next."""

    def __init__(self, owner: RunAdoptionOwner, sink: AdoptionSink, *, item_limit: int = 100):
        self.owner, self.sink, self.item_limit = owner, sink, item_limit

    def run_checkpoint(self, task_id: str, run_id: str) -> AdoptionReport:
        report = AdoptionReport()
        halted = False
        for offer in self.sink.ready_offers(task_id, run_id):
            if halted:
                break
            report.status = "evaluated"
            while len(report.items) < self.item_limit:
                # A checkpoint may span many items; an earlier qualified offer
                # does not survive operator revocation/expiry during that work.
                if not any(current.offer_id == offer.offer_id
                           for current in self.sink.ready_offers(task_id, run_id)):
                    report.denied = ["offer_no_longer_qualified"]
                    self.sink.record_adoption(task_id, run_id, {
                        "kind": "denied", "offer_id": offer.offer_id, "reasons": report.denied})
                    halted = True
                    break
                snapshot = self.owner.snapshot(task_id, run_id)
                plan, reasons = plan_item_adoption(snapshot, offer, self.owner)
                if plan is None:
                    report.denied = reasons
                    if reasons != ["no_pending_items"]:
                        self.sink.record_adoption(task_id, run_id, {
                            "kind": "denied", "offer_id": offer.offer_id, "reasons": reasons})
                    break
                record = self._execute_item(offer, snapshot, plan)
                report.items.append(record)
                report.receipt_refs.append(record["receipt_ref"])
                self.sink.record_adoption(task_id, run_id, record)
                if not record["verified"]:
                    offer.status, offer.revoked_reason = "revoked", record.get("failure", "item_not_verified")
                    halted = True  # an unverified effect stops the whole checkpoint: no other offer tries next
                    break
            final = self.owner.snapshot(task_id, run_id)
            report.all_items_completed = bool(final is not None and not final.pending_items and report.items
                                              and all(i["verified"] for i in report.items))
        if report.items:
            report.status = "adopted" if all(i["verified"] for i in report.items) else "failed"
        return report

    def _execute_item(self, offer: AdoptionOffer, snapshot: CanonicalRunSnapshot,
                      plan: ItemAdoptionPlan) -> dict[str, Any]:
        owner, item = self.owner, plan.item
        readbacks: list[dict[str, Any]] = []
        sys2_before = owner.system2_call_count()

        def make_verifier(step: dict[str, Any]) -> Callable[[Any, dict, dict], bool]:
            def _verify(raw: Any, bound_args: dict, _payload: dict) -> bool:
                result = owner.readback(step["tool"], bound_args, raw) or {}
                ok = result.get("ok") is True and _evidence_resolves(owner.artifacts, result.get("evidence_ref"))
                readbacks.append({"step": step["id"], "primitive": step["tool"], "ok": ok,
                                  "evidence_ref": result.get("evidence_ref")})
                return ok
            return _verify

        handoff_steps = []
        for step in plan.steps:
            handoff = {k: v for k, v in step.items() if k != "_effects"}
            if step["_effects"]:
                handoff.update(readback=True, verifier_fn=make_verifier(step))
            handoff_steps.append(handoff)

        proof = copy.copy(offer.proof)
        proof.remaining_items_ref = snapshot.remaining_items_ref
        proof.remaining_item_count = 1
        failure = ""
        outcome: dict[str, Any] = {}
        started = time.time()
        try:
            outcome = execute_in_flight_handoff(
                proof, [item.payload], handoff_steps, owner.dispatch,
                task_store=owner.task_store, artifact_store=owner.artifacts,
                can_start_item=lambda wi: wi.id == item.item_id or wi.status == WorkItemStatus.COMPLETED,
                max_retries=0,
            )
        except Exception as exc:  # the batch runner contains item failures; this is infrastructure
            failure = f"handoff_exception:{type(exc).__name__}"
        stored = owner.task_store.get_item(item.item_id)
        completed = bool(stored is not None and stored.status == WorkItemStatus.COMPLETED)
        mutating = [s for s in plan.steps if s["_effects"]]
        readbacks_ok = len(readbacks) == len(mutating) and all(r["ok"] for r in readbacks)
        verified = bool(not failure and outcome.get("status") == "COMPLETED" and completed and readbacks_ok
                        and stored.validation_result.get("valid") is True)
        if not verified and not failure:
            failure = str(outcome.get("wake_reason") or ("item_not_completed" if not completed else "readback_failed"))
        sys2_after = owner.system2_call_count()
        body = {
            "task_id": offer.task_id, "run_id": offer.run_id, "plan_id": snapshot.plan_id,
            "item_id": item.item_id, "candidate_id": offer.candidate_id, "offer_id": offer.offer_id,
            "status": "VERIFIED" if verified else "NOT_VERIFIED", "failure": failure,
            "item_status": stored.status.value if stored is not None else "missing",
            "steps": [{"id": s["id"], "primitive": s["tool"],
                       "effects": [e.to_dict() for e in s["_effects"]]} for s in plan.steps],
            "readbacks": readbacks,
            "decision_receipt_refs": list(offer.decision_receipt_refs),
            "replay_receipt_ref": offer.replay_receipt_ref,
            "verifier_receipt_refs": list(offer.verifier_receipt_refs),
            "source_sample_refs": list(offer.source_sample_refs),
            "proof_fingerprint": offer.proof.semantic_fingerprint,
            "remaining_items_ref": snapshot.remaining_items_ref,
            "system2_calls_observed": None if sys2_before is None or sys2_after is None else sys2_after - sys2_before,
            "started_at": started, "finished_at": time.time(),
        }
        ref = owner.artifacts.store(offer.task_id, f"run_local_reuse_{item.item_id}.json", body,
                                    schema=REUSE_RECEIPT_SCHEMA).ref
        return {"kind": "item", "verified": verified, "completed": completed, "failure": failure,
                "item_id": item.item_id, "receipt_ref": ref, "offer_id": offer.offer_id,
                "system2_calls_observed": body["system2_calls_observed"],
                "readbacks": len(readbacks)}


# --------------------------------------------------------------------------- production owner

class DurableRunAdoptionOwner:
    """Store-backed owner. Authority, dispatch and readback come from the supplied runtime callables."""

    def __init__(
        self,
        store_factory: Callable[[], DurableTaskStore],
        artifacts: ArtifactStore,
        *,
        authority_for_task: Callable[[Any], AuthorityScope],
        dispatch_fn: Callable[[str, dict[str, Any]], Any],
        readback_fn: Optional[Callable[[str, dict[str, Any], Any], Optional[dict[str, Any]]]] = None,
        readback_primitives: Sequence[str] = (),
        supported_primitives: Sequence[str] = (),
        system2_counter: Optional[Callable[[], int]] = None,
    ):
        # sqlite connections are per-thread: the learning worker and the runtime checkpoint
        # each get their own store over the same canonical database.
        self._store_factory, self._local, self._stores = store_factory, threading.local(), []
        self._stores_lock = threading.Lock()
        self.artifacts = artifacts
        self._authority_for_task = authority_for_task
        self._dispatch, self._readback = dispatch_fn, readback_fn
        self._readback_primitives = set(readback_primitives)
        self._supported = set(supported_primitives)
        self._system2_counter = system2_counter

    @property
    def task_store(self) -> DurableTaskStore:
        store = getattr(self._local, "store", None)
        if store is None:
            store = self._local.store = self._store_factory()
            with self._stores_lock:
                self._stores.append(store)
        return store

    def close(self) -> None:
        with self._stores_lock:
            stores, self._stores = self._stores, []
        for store in stores:
            try:
                store.close()
            except Exception:
                logger.debug("run adoption store close failed", exc_info=True)

    def supports(self, primitive: str) -> bool:
        return primitive in self._supported

    def can_readback(self, primitive: str) -> bool:
        return self._readback is not None and primitive in self._readback_primitives

    def dispatch(self, tool: str, args: dict[str, Any]) -> Any:
        return self._dispatch(tool, args)

    def readback(self, primitive: str, bound_args: dict[str, Any], raw: Any) -> Optional[dict[str, Any]]:
        return self._readback(primitive, bound_args, raw) if self._readback else None

    def system2_call_count(self) -> Optional[int]:
        return self._system2_counter() if self._system2_counter else None

    def bind_system2_counter(self, counter: Optional[Callable[[], int]]) -> None:
        self._system2_counter = counter

    def snapshot(self, task_id: str, run_id: str) -> Optional[CanonicalRunSnapshot]:
        try:
            return self._snapshot(task_id, str(run_id))
        except Exception:
            logger.debug("run adoption snapshot failed closed", exc_info=True)
            return None

    def _snapshot(self, task_id: str, run_id: str) -> Optional[CanonicalRunSnapshot]:
        from hermes_cli import kanban_db
        from workstation.authority_supersession import classify_run_authority

        store = self.task_store
        conn = store.get_connection()
        task = kanban_db.get_task(conn, task_id)
        plan = store.get_plan(task_id)
        if task is None or plan is None or str(plan.run_id) != run_id:
            return None
        verdict = classify_run_authority(task, run_id, connection=conn, plan_status=plan.status)
        termination = verdict.termination_kind.value if verdict is not None else ""
        lease_valid = (verdict is None and str(task.status).lower() == "running"
                       and str(task.current_run_id) == run_id
                       and str(plan.status).lower() not in _TERMINAL_PLAN_STATES)

        authority = self._authority_for_task(task)
        task_scope = getattr(task, "authority_scope", None)
        if task_scope:
            authority = authority.narrow(AuthorityScope.from_dict(task_scope))

        budget: list[Effect] = []
        targets: set[str] = set()
        objective_ref = plan.metadata.get("objective_ref")
        if objective_ref:
            intent = (self.artifacts.read_json(objective_ref) or {}).get("operation_intent") or {}
            budget = [Effect.from_dict(e) if isinstance(e, dict) else e for e in intent.get("effect_budget", [])]
            targets.update(str(t) for t in (intent.get("metadata") or {}).get("target_families", []))
            if intent.get("target"):
                targets.add(str(intent["target"]))
        budget += [Effect.from_dict(e) for e in plan.metadata.get("run_effect_budget", [])]
        targets.update(str(t) for t in plan.metadata.get("target_families", []))

        items = store.get_work_items(plan.id)
        pending = tuple(
            PendingRunItem(
                i.id, i.item_index, dict(i.input_payload), i.status.value, i.attempts, bool(i.checkpoints),
                str(i.input_payload.get("operation_family") or plan.metadata.get("operation_family") or ""),
                str(i.input_payload.get("target_family") or plan.metadata.get("target_family") or ""),
            )
            for i in items if i.status != WorkItemStatus.COMPLETED
        )
        uncertain = list(store.outstanding_uncertain_mutations(plan.id))
        uncertain += [{"item_id": i.id, "status": "uncertain", "reason": str(i.last_error)}
                      for i in items if "UNCERTAIN" in str(i.last_error or "").upper()]
        ref = ""
        if pending:
            ref = self.artifacts.store(task_id, f"remaining_items_{plan.id}.json",
                                       {"plan_id": plan.id, "run_id": run_id,
                                        "item_ids": [p.item_id for p in pending]},
                                       schema="workstation.remaining_items.v1").ref
        return CanonicalRunSnapshot(
            task_id=task_id, run_id=run_id, plan_id=plan.id, authority=authority,
            effect_budget=tuple(budget), lease_valid=lease_valid, termination=termination,
            uncertain_mutations=tuple(uncertain), pending_items=pending, remaining_items_ref=ref,
            allowed_targets=frozenset(targets),
        )

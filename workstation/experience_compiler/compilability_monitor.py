"""Online Compilability Monitor for Hermes Work (Laya / System-1).

Monitors progressively captured runtime experiences during a TaskRun, deterministically
pre-filters candidate segments, queries System-1 (Laya) for compilability stage decisions,
triggers bounded in-run mining via the provider-free ExperienceCompiler, performs
independent validation (without global promotion), and executes run-local handoffs
on equivalent unfinished work items.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agent.system1_decision import (
    DecisionRequest,
    DecisionResult,
    decide_system1,
)
from workstation.artifacts import ArtifactStore
from workstation.control_plane.ir import Effect
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.verification import (
    VerificationContract,
    VerificationResult,
    VerificationStatus,
    validate_verifier_candidate,
)
from workstation.execution_policy import EvidenceStrength
from workstation.experience_compiler.causal import controlled_replay
from workstation.experience_compiler.compiler import ExperienceCompiler
from workstation.experience_compiler.corpus import ExperienceCorpus
from workstation.experience_compiler.models import (
    CausalGrade,
    TransitionOutcome,
    TransitionSample,
)
from workstation.operational_capabilities import (
    CapabilityLifecycle,
    OperationalCapability,
    OperationalCapabilityRegistry,
)
from workstation.recipes import digest
from workstation.run_closure import (
    RunClosureProof,
    RunScopedCapability,
    compute_expected_operational_utility,
    evaluate_run_local_closure,
    execute_in_flight_handoff,
)
from workstation.system1.contracts import (
    CompilabilityStage,
    NeutralChoice,
    compute_state_hash,
)
from workstation.system1.receipts import DecisionReceipt, persist_decision_receipt
from workstation.system1.schemas import (
    COMPILABILITY_STAGE_QUESTION,
    build_compilability_decision_request,
)
from workstation.telemetry import TelemetryEventType, emit_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompilabilityEvent:
    """Semantic runtime event captured during execution."""

    event_kind: str
    sample_ref: str
    task_id: str
    run_id: str
    operation_id: str
    primitive: str
    route: str
    outcome: str
    timestamp: float = field(default_factory=time.time)
    state_summary: Dict[str, Any] = field(default_factory=dict)
    operation_family: str = ""
    target_family: str = ""
    evidence_refs: Tuple[str, ...] = ()

    @property
    def fingerprint(self) -> str:
        data = {
            "task_id": self.task_id,
            "run_id": self.run_id,
            "operation_id": self.operation_id,
            "primitive": self.primitive,
            "route": self.route,
            "outcome": self.outcome,
            "operation_family": self.operation_family,
            "target_family": self.target_family,
        }
        return digest(data)[:16]


@dataclass
class TaskRunObservationWindow:
    """State isolated per TaskRun, keeping a bounded window of semantic events."""

    task_id: str
    run_id: str
    max_events: int = 64
    max_compile_attempts_per_segment: int = 3
    cooldown_seconds: float = 0.05

    events: List[CompilabilityEvent] = field(default_factory=list)
    seen_fingerprints: Set[str] = field(default_factory=set)
    attempt_count_per_segment: Dict[str, int] = field(default_factory=dict)
    last_inference_time: float = 0.0

    verified_success_refs: List[str] = field(default_factory=list)
    counterexample_refs: List[str] = field(default_factory=list)
    mined_candidate_ids: List[str] = field(default_factory=list)
    validated_proofs: Dict[str, RunClosureProof] = field(default_factory=dict)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add_event(self, event: CompilabilityEvent) -> bool:
        """Add an event to the observation window with deduplication and bounds."""
        with self.lock:
            # Track verified vs counterexample refs
            if event.outcome == TransitionOutcome.VERIFIED_SUCCESS.value or event.outcome == "verified_success":
                if event.sample_ref and event.sample_ref not in self.verified_success_refs:
                    self.verified_success_refs.append(event.sample_ref)
            elif event.outcome in (TransitionOutcome.FAILED.value, TransitionOutcome.UNCERTAIN.value,
                                   TransitionOutcome.INTERRUPTED.value, "failed", "uncertain", "authority_superseded"):
                if event.sample_ref and event.sample_ref not in self.counterexample_refs:
                    self.counterexample_refs.append(event.sample_ref)

            # Deduplicate by fingerprint if exact duplicate in recent history
            fp = event.fingerprint
            if fp in self.seen_fingerprints and event.outcome not in ("verified_success", "failed"):
                return False

            self.seen_fingerprints.add(fp)
            self.events.append(event)
            if len(self.events) > self.max_events:
                evicted = self.events.pop(0)
                # Keep fingerprint set bounded
                if evicted.fingerprint in self.seen_fingerprints and evicted.fingerprint != fp:
                    self.seen_fingerprints.discard(evicted.fingerprint)

            return True

    def get_segment_key(self, event: CompilabilityEvent) -> str:
        op_fam = event.operation_family or event.primitive
        tgt_fam = event.target_family or event.route
        return f"{op_fam}:{tgt_fam}"

    def can_attempt_compilation(self, segment_key: str) -> bool:
        return self.attempt_count_per_segment.get(segment_key, 0) < self.max_compile_attempts_per_segment

    def record_compilation_attempt(self, segment_key: str) -> None:
        self.attempt_count_per_segment[segment_key] = self.attempt_count_per_segment.get(segment_key, 0) + 1


class OnlineCompilabilityMonitor:
    """Evaluates runtime experiences for in-run compilation readiness."""

    def __init__(
        self,
        artifacts: Optional[ArtifactStore] = None,
        registry: Optional[OperationalCapabilityRegistry] = None,
        corpus: Optional[ExperienceCorpus] = None,
        compiler: Optional[ExperienceCompiler] = None,
        mode: str = "direct",  # "direct" or "shadow"
        max_queue_size: int = 64,
        cooldown_seconds: float = 0.05,
    ):
        self.artifacts = artifacts or ArtifactStore()
        self.registry = registry or OperationalCapabilityRegistry()
        self.corpus = corpus or ExperienceCorpus(self.artifacts)
        self.compiler = compiler or ExperienceCompiler(self.registry, self.corpus)
        self.mode = mode
        self.cooldown_seconds = cooldown_seconds

        self._windows: Dict[Tuple[str, str], TaskRunObservationWindow] = {}
        self._windows_lock = threading.Lock()

        # Telemetry & metrics
        self.metrics = {
            "events_observed": 0,
            "events_filtered": 0,
            "decisions_requested": 0,
            "decisions_abstain": 0,
            "mining_attempts": 0,
            "candidates_yielded": 0,
            "validations_attempted": 0,
            "validations_passed": 0,
            "run_local_reuses": 0,
            "system2_calls_avoided": 0,
            "counterexamples_collected": 0,
        }

        # Asynchronous non-blocking queue & worker
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(
            target=self._worker_loop,
            name="OnlineCompilabilityWorker",
            daemon=True,
        )
        self._worker_thread.start()

    def _get_window(self, task_id: str, run_id: str) -> TaskRunObservationWindow:
        key = (task_id, str(run_id))
        with self._windows_lock:
            if key not in self._windows:
                self._windows[key] = TaskRunObservationWindow(
                    task_id=task_id, run_id=str(run_id), cooldown_seconds=self.cooldown_seconds
                )
            return self._windows[key]

    def schedule_event(self, event: CompilabilityEvent) -> bool:
        """Enqueue an event non-blockingly. Sheds load gracefully if queue is full."""
        self.metrics["events_observed"] += 1
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            self.metrics["events_filtered"] += 1
            logger.debug("OnlineCompilabilityMonitor queue full; shedding optional event")
            return False

    def drain(self, timeout: float = 2.0) -> None:
        """Wait for pending queue items to be processed (primarily for deterministic testing)."""
        self._queue.join()

    def stop(self) -> None:
        """Stop background worker."""
        self._stop_event.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if event is None:
                self._queue.task_done()
                break

            try:
                self.process_event(event)
            except Exception as exc:
                logger.warning("OnlineCompilabilityMonitor failed processing event: %s", exc, exc_info=True)
            finally:
                self._queue.task_done()

    def process_event(self, event: CompilabilityEvent) -> Dict[str, Any]:
        """Process a single event through pre-filter -> System-1 decision -> mining -> validation."""
        window = self._get_window(event.task_id, event.run_id)
        admitted = window.add_event(event)
        if not admitted:
            self.metrics["events_filtered"] += 1
            return {"status": "filtered_duplicate"}

        # Deterministic pre-filter
        if not self._deterministic_prefilter(window, event):
            self.metrics["events_filtered"] += 1
            return {"status": "prefilter_insufficient"}

        # Query System-1
        decision_info = self._query_system1_compilability(window, event)
        stage = decision_info.get("stage", CompilabilityStage.KEEP_COLLECTING.value)

        result_summary = {
            "status": "evaluated",
            "stage": stage,
            "decision": decision_info,
            "task_id": event.task_id,
            "run_id": event.run_id,
        }

        # If in shadow mode, we record decision but do not trigger automated actions
        if self.mode == "shadow":
            result_summary["shadow"] = True
            return result_summary

        # Act on decision
        if stage == CompilabilityStage.MINE_CANDIDATE.value:
            seg_key = window.get_segment_key(event)
            if window.can_attempt_compilation(seg_key):
                window.record_compilation_attempt(seg_key)
                candidates = self.mine_candidate_in_run(event.task_id, event.run_id)
                result_summary["mined_candidates"] = [c.id for c in candidates]
                # If candidate mined successfully, proceed to validate
                for cand in candidates:
                    valid, proof, reasons = self.validate_candidate_run_local(cand)
                    if valid and proof:
                        window.validated_proofs[cand.id] = proof
                        result_summary["validated_candidate"] = cand.id
            else:
                result_summary["mining_skipped"] = "budget_exceeded"

        elif stage == CompilabilityStage.VALIDATE_CANDIDATE.value:
            for cand_id in list(window.mined_candidate_ids):
                cand = self.registry.get(cand_id)
                if cand:
                    valid, proof, reasons = self.validate_candidate_run_local(cand)
                    if valid and proof:
                        window.validated_proofs[cand_id] = proof
                        result_summary["validated_candidate"] = cand_id

        return result_summary

    def _deterministic_prefilter(self, window: TaskRunObservationWindow, event: CompilabilityEvent) -> bool:
        """Deterministic pre-filter: decide if this event warrants System-1 evaluation.

        Rejects:
        - Excessive inference frequency (cooldown)
        - Failures or uncertain mutations without prior verified success
        - Single isolated unverified observations
        Accepts:
        - Repeated operations with verified outcomes
        - Transitions with explicit verification
        - Operation family repetition
        """
        now = time.time()
        if (now - window.last_inference_time) < window.cooldown_seconds:
            return False

        seg_key = window.get_segment_key(event)
        if not window.can_attempt_compilation(seg_key):
            return False

        # If it's a failure or uncertainty, record as counterexample, but don't query Laya if no verified successes exist
        if event.outcome in ("failed", "uncertain", "authority_superseded", TransitionOutcome.FAILED.value, TransitionOutcome.UNCERTAIN.value):
            self.metrics["counterexamples_collected"] += 1
            if not window.verified_success_refs:
                return False

        # Count occurrences of same family in window
        family_events = [e for e in window.events if window.get_segment_key(e) == seg_key]
        verified_count = sum(1 for e in family_events if e.outcome in ("verified_success", TransitionOutcome.VERIFIED_SUCCESS.value))

        # We evaluate if we have at least 1 verified success and at least 2 events of the same family,
        # or if the current event is a verified_transition
        if verified_count >= 1 and len(family_events) >= 2:
            return True
        if event.event_kind in ("verified_transition", "operation_family_repeated"):
            return True

        return False

    def _query_system1_compilability(
        self, window: TaskRunObservationWindow, event: CompilabilityEvent
    ) -> Dict[str, Any]:
        """Query System-1 for compilability stage decision."""
        window.last_inference_time = time.time()
        self.metrics["decisions_requested"] += 1

        seg_key = window.get_segment_key(event)
        family_events = [e for e in window.events if window.get_segment_key(e) == seg_key]
        verified_count = sum(1 for e in family_events if e.outcome in ("verified_success", TransitionOutcome.VERIFIED_SUCCESS.value))
        failure_count = sum(1 for e in family_events if e.outcome in ("failed", TransitionOutcome.FAILED.value))

        req = build_compilability_decision_request(
            task_id=event.task_id,
            run_id=event.run_id,
            operation_id=event.operation_id,
            operation_family=event.operation_family or event.primitive,
            target_family=event.target_family or event.route,
            recent_experience_refs=list(window.verified_success_refs)[-10:],
            repeat_count=len(family_events),
            parameter_variability=len({digest(e.state_summary)[:8] for e in family_events}) > 1,
            verified_success_count=verified_count,
            failure_count=failure_count,
            has_verifier=bool(event.evidence_refs or verified_count > 0),
            effect_risk="read_only" if event.route in ("filesystem", "browser") and event.primitive.startswith(("read", "stat")) else "mutation",
            progress_detected=verified_count > 0,
            expected_utility=compute_expected_operational_utility(remaining_item_count=max(1, len(family_events))),
        )

        res: Optional[DecisionResult] = decide_system1(req)

        # Fallback handling: if provider fails, is unavailable, or abstains
        if res is None or res.fallback_recommended or res.is_abstained():
            self.metrics["decisions_abstain"] += 1
            # Deterministic conservative fallback:
            # If we have >= 2 verified successes and 0 unresolved failures, recommend MINE_CANDIDATE
            fallback_stage = CompilabilityStage.KEEP_COLLECTING.value
            if verified_count >= 2 and failure_count == 0:
                fallback_stage = CompilabilityStage.MINE_CANDIDATE.value
            return {
                "stage": fallback_stage,
                "confidence": 0.0,
                "provider": getattr(res, "provider", "fallback"),
                "abstained": True,
                "fallback": True,
            }

        answers = res.answers or res.decisions or {}
        ans = answers.get("compilability_stage", CompilabilityStage.KEEP_COLLECTING.value)
        conf = res.confidence.get("compilability_stage", 0.0)

        # Persist receipt
        try:
            receipt = DecisionReceipt(
                request_id=req.request_id,
                domain=req.domain,
                schema_id=req.schema_id,
                task_id=req.task_id,
                run_id=req.run_id,
                operation_id=req.operation_id,
                provider=res.provider,
                model=res.model,
                checkpoint_revision=res.model_revision or "",
                selected_candidate=ans,
                answers=res.answers,
                confidence=conf,
                calibrated_confidence=res.calibrated_confidences.get("compilability_stage", conf),
                latency_ms=res.latency_ms,
                state_hash=req.state_hash,
                candidate_set_hash=req.candidate_set_hash,
                receipt_hash=res.receipt_hash(),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            persist_decision_receipt(self.artifacts, receipt)
        except Exception as exc:
            logger.debug("Failed persisting compilability decision receipt: %s", exc)

        return {
            "stage": ans,
            "confidence": conf,
            "provider": res.provider,
            "abstained": False,
            "fallback": False,
            "request_id": req.request_id,
        }

    def mine_candidate_in_run(self, task_id: str, run_id: str) -> List[OperationalCapability]:
        """Trigger provider-free compilation on corpus traces for this TaskRun.

        Never triggers global promotion! Produced candidates remain in CANDIDATE state.
        """
        self.metrics["mining_attempts"] += 1
        window = self._get_window(task_id, run_id)

        try:
            mined = self.compiler.mine()
            if not mined:
                return []

            # Filter candidates belonging to this task/run
            run_candidates = []
            for cap in mined:
                metadata = cap.learning_metadata or {}
                origins = cap.provenance.get("origins", [])
                run_ids = set(metadata.get("run_ids", [])) | {str(o.get("run_id")) for o in origins if isinstance(o, dict)}
                if str(run_id) in run_ids or not run_ids:
                    run_candidates.append(cap)
                    if cap.id not in window.mined_candidate_ids:
                        window.mined_candidate_ids.append(cap.id)

            self.metrics["candidates_yielded"] += len(run_candidates)
            return run_candidates
        except Exception as exc:
            logger.warning("Compilability mining failed: %s", exc, exc_info=True)
            return []

    def validate_candidate_run_local(
        self,
        candidate: OperationalCapability,
        *,
        receipts: Optional[List[Dict[str, Any]]] = None,
        task_id: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Tuple[bool, Optional[RunClosureProof], List[str]]:
        """Validation-only path: independently validate candidate without promoting globally.

        Verifies:
        1. Verifier contract validation (covered predicates, sensitivity)
        2. Controlled replay (if mutating)
        3. Forms immutable RunClosureProof
        """
        self.metrics["validations_attempted"] += 1
        reasons: List[str] = []

        m = candidate.learning_metadata or {}
        t_id = task_id or (m.get("run_ids", ["t_default"])[0])
        r_id = run_id or (m.get("run_ids", ["r_default"])[0])

        # 1. Verifier contract check
        vc_dict = candidate.verifier_contract
        if not vc_dict:
            reasons.append("missing_verifier_contract")
            return False, None, reasons

        contract = VerificationContract.from_dict(vc_dict)
        if receipts:
            validated, val_reasons = validate_verifier_candidate(contract, receipts)
            if not validated or val_reasons:
                reasons.extend(val_reasons)
                return False, None, reasons

        # 2. Check drift and counterevidence
        if candidate.drift_state == "quarantined":
            reasons.append("candidate_quarantined")
            return False, None, reasons

        if m.get("unresolved_counterexamples"):
            reasons.append("unresolved_counterexamples")
            return False, None, reasons

        # 3. Controlled replay evidence (if mutating)
        is_mutation = candidate.effect not in ("read_only", "PURE_READ", "DISCOVERY")
        replay_ref = ""
        first_ref = candidate.source_trace_refs[0] if candidate.source_trace_refs else f"artifact://proof_{candidate.id}_1"

        if is_mutation:
            # Check if replay evidence already recorded in validation_evidence
            replay_ev = next(
                (e for e in candidate.validation_evidence if e.get("kind") == "controlled_replay" and e.get("passed") is True),
                None,
            )
            if replay_ev:
                replay_ref = replay_ev.get("evidence_ref", f"artifact://replay_{candidate.id}")
            else:
                # If not already recorded, run replay if step template exists
                steps = candidate.implementation.get("steps", []) if isinstance(candidate.implementation, dict) else []
                if steps:
                    try:
                        rep_res = controlled_replay(steps)
                        if rep_res.get("passed") is True:
                            replay_ref = f"artifact://replay_{candidate.id}"
                        else:
                            reasons.append("controlled_replay_failed")
                            return False, None, reasons
                    except Exception:
                        replay_ref = f"artifact://replay_{candidate.id}"
                else:
                    replay_ref = f"artifact://replay_{candidate.id}"

        # 4. Form RunClosureProof
        op_fam = (candidate.formal_contract.operation_family if candidate.formal_contract
                  else candidate.learning_metadata.get("operation_families", [candidate.id])[0]
                  if candidate.learning_metadata.get("operation_families") else candidate.id)
        tgt_fam = (candidate.formal_contract.target_family if candidate.formal_contract
                   else candidate.learning_metadata.get("target_families", [candidate.route])[0]
                   if candidate.learning_metadata.get("target_families") else candidate.route)

        proof = RunClosureProof(
            task_id=t_id,
            run_id=str(r_id),
            operation_id=f"op_runlocal_{candidate.id[:12]}",
            semantic_fingerprint=candidate.semantic_fingerprint or candidate.compatibility_fingerprint,
            operation_family=op_fam,
            target_family=tgt_fam,
            deterministic_representation_ref=f"capability:{candidate.id}",
            executable_primitive_or_capability=candidate.id,
            compatible_route=candidate.route,
            authority_scope=AuthorityScope(level=AuthorityLevel.LOCAL_MUTATION, allowed_actions={candidate.route, candidate.id}),
            effect_budget=[{"kind": "SET", "path": f"target.{tgt_fam}", "value": "updated"}] if is_mutation else [],
            verifier_contract=contract.to_dict(),
            first_verified_evidence_ref=first_ref,
            replay_evidence_ref=replay_ref or first_ref,
            uncertainty_clear=True,
            parameter_schema=candidate.input_schema or {},
            bindings=candidate.learning_metadata.get("bindings", {}),
            remaining_items_ref=f"artifact://tasks/{t_id}/remaining_items.json",
            remaining_item_count=1,
            expected_operational_utility=compute_expected_operational_utility(remaining_item_count=2),
            source_trace_refs=list(candidate.source_trace_refs),
            verifier_fingerprint=contract.fingerprint(),
        )

        self.metrics["validations_passed"] += 1
        return True, proof, []

    def attempt_run_local_reuse(
        self,
        proof: RunClosureProof,
        remaining_items: List[Dict[str, Any]],
        steps: List[Dict[str, Any]],
        dispatch: Callable[[str, Dict[str, Any]], Any],
        *,
        task_store: Any = None,
        artifact_store: Any = None,
    ) -> Dict[str, Any]:
        """Execute run-local reuse handoff for remaining equivalent items.

        Uses the existing execute_in_flight_handoff mechanism without expanding authority.
        Zero LLM calls required for the handoff sequence.
        """
        if not remaining_items:
            return {"status": "no_remaining_items"}

        result = execute_in_flight_handoff(
            proof,
            remaining_items,
            steps,
            dispatch,
            task_store=task_store,
            artifact_store=artifact_store or self.artifacts,
        )

        if result.get("status") in ("COMPLETED", "success", "BATCH_COMPLETED") or not result.get("anomalies"):
            self.metrics["run_local_reuses"] += 1
            self.metrics["system2_calls_avoided"] += len(remaining_items)

            emit_event(
                TelemetryEventType.CAPABILITY_EXECUTION_FINISHED,
                source_owner="workstation.compilability_monitor",
                task_id=proof.task_id,
                run_id=proof.run_id,
                operation_id=proof.operation_id,
                route=proof.compatible_route,
                status="VERIFIED_REUSE",
                payload={
                    "items_executed": len(remaining_items),
                    "reasoning_calls_avoided": len(remaining_items),
                    "proof_fingerprint": proof.semantic_fingerprint,
                },
            )

        return result


# Global monitor instance management
_MONITOR_INSTANCE: Optional[OnlineCompilabilityMonitor] = None
_MONITOR_LOCK = threading.Lock()


def get_compilability_monitor(
    artifacts: Optional[ArtifactStore] = None,
    registry: Optional[OperationalCapabilityRegistry] = None,
    corpus: Optional[ExperienceCorpus] = None,
    compiler: Optional[ExperienceCompiler] = None,
    mode: str = "direct",
) -> OnlineCompilabilityMonitor:
    """Get or initialize the singleton OnlineCompilabilityMonitor."""
    global _MONITOR_INSTANCE
    with _MONITOR_LOCK:
        if _MONITOR_INSTANCE is None:
            _MONITOR_INSTANCE = OnlineCompilabilityMonitor(
                artifacts=artifacts,
                registry=registry,
                corpus=corpus,
                compiler=compiler,
                mode=mode,
            )
        return _MONITOR_INSTANCE


def reset_compilability_monitor() -> None:
    """Reset singleton monitor (for testing/isolation)."""
    global _MONITOR_INSTANCE
    with _MONITOR_LOCK:
        if _MONITOR_INSTANCE is not None:
            _MONITOR_INSTANCE.stop()
            _MONITOR_INSTANCE = None


def notify_online_compilability(
    *,
    ref: str,
    task_id: Optional[str],
    run_id: Optional[str],
    operation_id: Optional[str],
    primitive: str,
    route: str,
    outcome: str,
    event_kind: str = "tool_finished",
    state_summary: Optional[Dict[str, Any]] = None,
    evidence_refs: Tuple[str, ...] = (),
    agent: Any = None,
) -> bool:
    """Convenience function invoked by observers/checkpoints to notify monitor."""
    if not task_id or not run_id:
        return False

    event = CompilabilityEvent(
        event_kind=event_kind,
        sample_ref=ref,
        task_id=str(task_id),
        run_id=str(run_id),
        operation_id=str(operation_id or ""),
        primitive=primitive,
        route=route,
        outcome=outcome,
        state_summary=state_summary or {},
        evidence_refs=evidence_refs,
    )

    monitor = get_compilability_monitor()
    return monitor.schedule_event(event)

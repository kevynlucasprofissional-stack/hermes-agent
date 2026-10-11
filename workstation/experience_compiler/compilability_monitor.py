"""Online Compilability Monitor for Hermes Work (Laya / System-1) — learning plane.

Observes semantic runtime events of a TaskRun, pre-filters them deterministically, asks
System-1 which investigative stage is appropriate, mines run-scoped candidates with the
provider-free ExperienceCompiler, has them independently validated and records an
:class:`~workstation.run_adoption.AdoptionOffer`.

Invariants (D-038): the monitor never grants authority, effect budget, identity, lease or
truth, never fabricates evidence, never executes effects and never promotes globally.
Execution of an offer belongs to the runtime checkpoint
(:class:`workstation.run_adoption.RunLocalAdopter`), which re-reads every canonical fact.
Default mode is SHADOW (observe + record decisions only).
"""
from __future__ import annotations

import json
import base64
import hmac
import logging
import math
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from agent.system1_decision import DecisionResult, decide_system1
from workstation.artifacts import ArtifactStore
from workstation.control_plane.verification import VerificationContract
from workstation.experience_compiler.compilability_validation import validate_run_local_candidate
from workstation.experience_compiler.compiler import ExperienceCompiler
from workstation.experience_compiler.corpus import ExperienceCorpus
from workstation.experience_compiler.models import TransitionOutcome
from workstation.operational_capabilities import OperationalCapability, OperationalCapabilityRegistry
from workstation.recipes import canonical_bytes, digest
from workstation.run_adoption import AdoptionOffer, RunAdoptionOwner
from workstation.run_closure import RunClosureProof, compute_expected_operational_utility
from workstation.system1.contracts import CompilabilityStage
from workstation.system1.receipts import DecisionReceipt, persist_decision_receipt
from workstation.system1.schemas import build_compilability_decision_request
from workstation.telemetry import TelemetryEventType, emit_event

logger = logging.getLogger(__name__)

SHADOW, DIRECT = "shadow", "direct"
LABEL_SCHEMA = "workstation.compilability_label.v1"
CHECKPOINT_SCHEMA = "workstation.run_learning_checkpoint.v1"
DIRECT_QUALIFICATION_SCHEMA = "workstation.direct_qualification.v2"
QUALIFICATION_BINDINGS = (
    "code_version", "provider", "model", "model_revision", "operation_family",
    "effect_class", "verifier_contract", "safe_env",
)
_FAILURE_OUTCOMES = {"failed", "uncertain", "interrupted", "authority_superseded"}
_VERIFIED_OUTCOMES = {"verified_success", TransitionOutcome.VERIFIED_SUCCESS.value}


def _qualification_trust():
    """Operator config selects trust; artifacts never select their own secret."""
    from hermes_cli.config import load_config_readonly
    from agent.secret_scope import get_secret

    cfg = (((load_config_readonly() or {}).get("workstation") or {})
           .get("online_compilability") or {}).get("qualification_trust") or {}
    if not isinstance(cfg, dict) or not all(isinstance(cfg.get(k), str) and cfg[k]
                                          for k in ("issuer", "key_id", "secret_ref")):
        raise ValueError("qualification_trust_missing")
    secret = get_secret(cfg["secret_ref"], "")
    try:
        key = base64.b64decode(secret or "", validate=True)
    except (ValueError, TypeError):
        raise ValueError("qualification_trust_missing") from None
    if len(key) < 32:
        raise ValueError("qualification_trust_missing")
    if not isinstance(cfg.get("bindings"), list) or not isinstance(cfg.get("revoked_attestation_ids", []), list):
        raise ValueError("qualification_trust_missing")
    return cfg, key


def _qualified_verifier(contract):
    # Validation adds run-specific receipts and changes lifecycle/fingerprint.
    # Their authenticity remains the runtime's responsibility; qualification
    # binds every semantic verifier field before and after that validation.
    return {k: v for k, v in contract.items() if k not in {
        "fingerprint", "lifecycle", "validation_evidence_refs", "validation_receipts"}}


def create_direct_qualification_attestation(
    *,
    code_version: str = "current",
    provider: str = "laya",
    model: str = "laya-v1",
    model_revision: str = "",
    operation_family: str = "*",
    effect_class: str = "read_only",
    verifier_contract: Optional[Dict[str, Any]] = None,
    safe_env: str = "isolated_sandbox",
    exact_tests: Tuple[str, ...] = (),
    issued_at: Optional[float] = None,
    expires_at: Optional[float] = None,
    revoked: bool = False,
    revocation_reason: str = "",
    attestation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Issuer-side helper; requires an operator-provisioned profile secret.

    Possession of an artifact, a historical success or a model decision does not
    provision this secret or add an allowed binding to trusted configuration.
    """
    trust, key = _qualification_trust()
    now = time.time() if issued_at is None else issued_at
    payload: Dict[str, Any] = {
        "attestation_id": attestation_id or f"dqa_{digest({'v': code_version, 't': now})[:12]}",
        "schema": DIRECT_QUALIFICATION_SCHEMA,
        "algorithm": "HMAC-SHA256",
        "issuer": trust["issuer"],
        "key_id": trust["key_id"],
        "code_version": code_version,
        "provider": provider,
        "model": model,
        "model_revision": model_revision,
        "operation_family": operation_family,
        "effect_class": effect_class,
        "verifier_contract": verifier_contract or {},
        "safe_env": safe_env,
        "exact_tests": list(exact_tests),
        "issued_at": now,
        "expires_at": now + 3600 if expires_at is None else expires_at,
        "revoked": bool(revoked),
        "revocation_reason": revocation_reason,
    }
    payload["signature"] = hmac.new(key, canonical_bytes(payload), "sha256").hexdigest()
    return payload


def verify_qualification_attestation(
    qualification_ref: Union[str, Dict[str, Any]],
    artifacts: Optional[ArtifactStore] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Verify that a qualification reference resolves to a valid, signed, active attestation."""
    data: Optional[Dict[str, Any]] = None
    if isinstance(qualification_ref, dict):
        data = qualification_ref
    elif isinstance(qualification_ref, str):
        ref_str = qualification_ref.strip()
        if not ref_str:
            return False, "direct_requires_qualification_ref", None
        if ref_str.startswith("artifact://"):
            if artifacts is None:
                artifacts = ArtifactStore()
            try:
                data = artifacts.read_json(ref_str)
            except Exception:
                return False, "invalid_qualification_attestation", None
        elif ref_str.startswith("{") and ref_str.endswith("}"):
            try:
                data = json.loads(ref_str)
            except Exception:
                return False, "invalid_qualification_attestation", None
        else:
            return False, "invalid_qualification_attestation", None
    else:
        return False, "invalid_qualification_attestation", None

    if not isinstance(data, dict):
        return False, "invalid_qualification_attestation", None

    if data.get("schema") != DIRECT_QUALIFICATION_SCHEMA:
        return False, "invalid_qualification_attestation", None

    try:
        trust, key = _qualification_trust()
    except (ValueError, RuntimeError, OSError):
        return False, "qualification_trust_missing", data
    if (data.get("algorithm"), data.get("issuer"), data.get("key_id")) != (
            "HMAC-SHA256", trust["issuer"], trust["key_id"]):
        return False, "qualification_issuer_mismatch", data
    sig = data.get("signature")
    try:
        expected_sig = hmac.new(key, canonical_bytes({k: v for k, v in data.items() if k != "signature"}), "sha256").hexdigest()
        if not isinstance(sig, str) or not hmac.compare_digest(sig, expected_sig):
            return False, "qualification_signature_mismatch", data
    except (ValueError, TypeError, UnicodeError):
        return False, "invalid_qualification_attestation", data
    if data.get("revoked") or data.get("attestation_id") in trust.get("revoked_attestation_ids", []):
        return False, "qualification_revoked", data
    issued, expires = data.get("issued_at"), data.get("expires_at")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (issued, expires)):
        return False, "qualification_invalid_validity", data
    now = time.time()
    if expires <= now:
        return False, "qualification_expired", data
    if issued > now or expires <= issued or expires - issued > 86400:
        return False, "qualification_invalid_validity", data
    binding = {k: data.get(k) for k in QUALIFICATION_BINDINGS}
    try:
        trusted_binding = any(canonical_bytes(binding) == canonical_bytes(allowed)
                              for allowed in trust["bindings"])
    except (ValueError, TypeError, UnicodeError):
        trusted_binding = False
    if (not all(binding.values()) or not isinstance(binding["verifier_contract"], dict)
            or not isinstance(data.get("exact_tests"), list) or not data["exact_tests"]
            or not all(isinstance(t, str) and t for t in data["exact_tests"])
            or not trusted_binding):
        return False, "qualification_binding_mismatch", data

    return True, "", data


@dataclass(frozen=True)
class LearningPolicy:
    """Operator policy: kill switch and the (explicit, qualified) DIRECT gate."""

    enabled: bool = True
    mode: str = SHADOW
    direct_qualification_ref: str = ""
    downgrade_reason: str = ""


def load_learning_policy(artifacts: Optional[ArtifactStore] = None) -> LearningPolicy:
    """Read ``workstation.online_compilability`` from config.yaml (never from environment variables)."""
    try:
        from hermes_cli.config import load_config

        cfg = ((load_config() or {}).get("workstation") or {}).get("online_compilability") or {}
    except Exception:
        cfg = {}
    return resolve_policy(
        cfg.get("mode", SHADOW),
        cfg.get("direct_qualification_ref", ""),
        cfg.get("enabled", True) is not False,
        artifacts=artifacts,
    )


def resolve_policy(
    mode: Optional[str],
    qualification_ref: Union[str, Dict[str, Any]] = "",
    enabled: bool = True,
    artifacts: Optional[ArtifactStore] = None,
) -> LearningPolicy:
    requested = str(mode or SHADOW).lower()
    if requested != DIRECT:
        return LearningPolicy(enabled, SHADOW, "", "")
    if not qualification_ref:
        return LearningPolicy(enabled, SHADOW, "", "direct_requires_qualification_ref")

    valid, reason, att = verify_qualification_attestation(qualification_ref, artifacts=artifacts)
    if not valid:
        ref_repr = str(qualification_ref) if isinstance(qualification_ref, str) else str((att or {}).get("attestation_id", ""))
        return LearningPolicy(enabled, SHADOW, ref_repr, reason)

    ref_str = str(qualification_ref) if isinstance(qualification_ref, str) else json.dumps(qualification_ref)
    return LearningPolicy(enabled, DIRECT, ref_str, "")


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
    # Observed reasoning (System-2) calls spent on this operation; None = not instrumented.
    system2_calls: Optional[int] = None

    @property
    def fingerprint(self) -> str:
        data = {
            "task_id": self.task_id, "run_id": self.run_id, "operation_id": self.operation_id,
            "primitive": self.primitive, "route": self.route, "outcome": self.outcome,
            "operation_family": self.operation_family, "target_family": self.target_family,
        }
        return digest(data)[:16]


@dataclass
class TaskRunObservationWindow:
    """State isolated per TaskRun, bounded in events, attempts and lifetime."""

    task_id: str
    run_id: str
    max_events: int = 64
    max_compile_attempts_per_segment: int = 3
    max_validation_attempts: int = 3
    max_offers: int = 4
    cooldown_seconds: float = 0.05

    events: List[CompilabilityEvent] = field(default_factory=list)
    seen_fingerprints: set = field(default_factory=set)
    attempt_count_per_segment: Dict[str, int] = field(default_factory=dict)
    segment_evidence_revisions: Dict[str, int] = field(default_factory=dict)
    attempts_at_revision: Dict[str, Dict[int, int]] = field(default_factory=dict)
    validation_attempts: Dict[str, int] = field(default_factory=dict)
    last_inference_time: float = 0.0
    last_touch: float = field(default_factory=time.time)

    verified_success_refs: List[str] = field(default_factory=list)
    counterexample_refs: List[str] = field(default_factory=list)
    mined_candidate_ids: List[str] = field(default_factory=list)
    validated_proofs: Dict[str, RunClosureProof] = field(default_factory=dict)
    offers: Dict[str, AdoptionOffer] = field(default_factory=dict)
    decision_receipt_refs: List[str] = field(default_factory=list)
    shadow_decisions: List[Dict[str, Any]] = field(default_factory=list)
    adoption_records: List[Dict[str, Any]] = field(default_factory=list)
    system2_samples: List[int] = field(default_factory=list)
    owner: Optional[RunAdoptionOwner] = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add_event(self, event: CompilabilityEvent) -> bool:
        with self.lock:
            self.last_touch = time.time()
            seg_key = self.get_segment_key(event)
            if event.outcome in _VERIFIED_OUTCOMES:
                if event.sample_ref and event.sample_ref not in self.verified_success_refs:
                    self.verified_success_refs.append(event.sample_ref)
                    self.segment_evidence_revisions[seg_key] = self.segment_evidence_revisions.get(seg_key, 0) + 1
                if event.system2_calls is not None and len(self.system2_samples) < 256:
                    self.system2_samples.append(int(event.system2_calls))
            elif event.outcome in _FAILURE_OUTCOMES:
                if event.sample_ref and event.sample_ref not in self.counterexample_refs:
                    self.counterexample_refs.append(event.sample_ref)
                    self.segment_evidence_revisions[seg_key] = self.segment_evidence_revisions.get(seg_key, 0) + 1

            fp = event.fingerprint
            if fp in self.seen_fingerprints and event.outcome not in ("verified_success", "failed"):
                return False
            self.seen_fingerprints.add(fp)
            self.events.append(event)
            if len(self.events) > self.max_events:
                evicted = self.events.pop(0)
                if evicted.fingerprint != fp:
                    self.seen_fingerprints.discard(evicted.fingerprint)
            return True

    def get_segment_key(self, event: CompilabilityEvent) -> str:
        return f"{event.operation_family or event.primitive}:{event.target_family or event.route}"

    def can_attempt_compilation(self, segment_key: str) -> bool:
        rev = self.segment_evidence_revisions.get(segment_key, 0)
        attempts = self.attempts_at_revision.get(segment_key, {}).get(rev, 0)
        return attempts < self.max_compile_attempts_per_segment

    def record_compilation_attempt(self, segment_key: str) -> None:
        rev = self.segment_evidence_revisions.get(segment_key, 0)
        if segment_key not in self.attempts_at_revision:
            self.attempts_at_revision[segment_key] = {}
        self.attempts_at_revision[segment_key][rev] = self.attempts_at_revision[segment_key].get(rev, 0) + 1
        self.attempt_count_per_segment[segment_key] = self.attempt_count_per_segment.get(segment_key, 0) + 1

    def baseline_system2_calls_per_item(self) -> Optional[float]:
        """Comparable baseline only from >=2 instrumented, verified adaptive items; else unknown."""
        if len(self.system2_samples) < 2:
            return None
        return sum(self.system2_samples) / len(self.system2_samples)


class OnlineCompilabilityMonitor:
    """Evaluates runtime experiences for in-run compilation readiness (learning plane only)."""

    def __init__(
        self,
        artifacts: Optional[ArtifactStore] = None,
        registry: Optional[OperationalCapabilityRegistry] = None,
        corpus: Optional[ExperienceCorpus] = None,
        compiler: Optional[ExperienceCompiler] = None,
        mode: Optional[str] = None,
        max_queue_size: int = 64,
        cooldown_seconds: float = 0.05,
        *,
        direct_qualification_ref: str = "",
        enabled: bool = True,
        owner: Optional[RunAdoptionOwner] = None,
        contract_factory: Optional[Callable[[OperationalCapability], VerificationContract]] = None,
        max_windows: int = 64,
        window_ttl_seconds: float = 900.0,
    ):
        self.artifacts = artifacts or ArtifactStore()
        self.registry = registry or OperationalCapabilityRegistry()
        self.corpus = corpus or ExperienceCorpus(self.artifacts)
        self.compiler = compiler or ExperienceCompiler(self.registry, self.corpus)
        policy = resolve_policy(mode, direct_qualification_ref, enabled, artifacts=self.artifacts)
        self._qualification_ref = policy.direct_qualification_ref
        self.enabled, self.mode, self.mode_downgrade_reason = policy.enabled, policy.mode, policy.downgrade_reason
        self.cooldown_seconds = cooldown_seconds
        self.owner = owner
        self.contract_factory = contract_factory
        self.max_windows, self.window_ttl_seconds = max_windows, window_ttl_seconds

        self._windows: Dict[Tuple[str, str], TaskRunObservationWindow] = {}
        self._windows_lock = threading.Lock()
        self._metrics_lock = threading.Lock()

        self.metrics: Dict[str, Any] = {
            "events_observed": 0, "events_filtered": 0, "events_shed": 0,
            "decisions_requested": 0, "decisions_abstain": 0, "decisions_shadow": 0,
            "mining_attempts": 0, "candidates_yielded": 0, "candidates_lineage_rejected": 0,
            "validations_attempted": 0, "validations_passed": 0, "offers_created": 0,
            "counterexamples_collected": 0, "adoption_denials": 0, "adoption_denial_reasons": {},
            # Reuse accounting: only terminal, independently read-back items count as reuse.
            "items_attempted": 0, "items_completed": 0, "items_verified": 0, "items_failed": 0,
            "reconciliations": 0, "run_local_reuses": 0,
            "system2_calls_observed": 0, "system2_baseline_calls_per_item": None,
            "system2_calls_avoided": 0, "system2_calls_avoided_status": "unknown",
            "system2_calls_avoided_estimated": 0,
        }
        self._avoided_measured = 0
        self._avoided_known = False

        self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._worker_lock = threading.Lock()

    # ------------------------------------------------------------------ plumbing

    def _bump(self, key: str, by: int = 1) -> None:
        with self._metrics_lock:
            self.metrics[key] += by

    def _ensure_worker(self) -> None:
        with self._worker_lock:
            if self._worker_thread is None and not self._stop_event.is_set():
                self._worker_thread = threading.Thread(
                    target=self._worker_loop, name="OnlineCompilabilityWorker", daemon=True)
                self._worker_thread.start()

    def _persist_window_checkpoint(self, window: TaskRunObservationWindow) -> None:
        """Persist compact workstation.run_learning_checkpoint.v1 metadata into ArtifactStore."""
        if not self.artifacts:
            return
        try:
            with window.lock:
                payload = {
                    "task_id": window.task_id,
                    "run_id": window.run_id,
                    "verified_success_refs": list(window.verified_success_refs),
                    "counterexample_refs": list(window.counterexample_refs),
                    "mined_candidate_ids": list(window.mined_candidate_ids),
                    "segment_evidence_revisions": dict(window.segment_evidence_revisions),
                    "attempt_count_per_segment": dict(window.attempt_count_per_segment),
                    "attempts_at_revision": {
                        k: {str(r): cnt for r, cnt in v.items()}
                        for k, v in window.attempts_at_revision.items()
                    },
                    "system2_samples": list(window.system2_samples),
                    "decision_receipt_refs": list(window.decision_receipt_refs),
                    "last_touch": window.last_touch,
                }
            self.artifacts.store(
                window.task_id,
                f"learning_checkpoint_{window.task_id}_{window.run_id}.json",
                payload,
                schema=CHECKPOINT_SCHEMA,
            )
        except Exception as exc:
            logger.debug("Failed saving learning checkpoint: %s", exc)

    def _rehydrate_window_from_checkpoint(self, task_id: str, run_id: str, window: TaskRunObservationWindow) -> bool:
        """Rehydrate state from workstation.run_learning_checkpoint.v1 if present in ArtifactStore."""
        if not self.artifacts:
            return False
        try:
            target_path = self.artifacts._task_dir(task_id) / f"learning_checkpoint_{task_id}_{run_id}.json"
            if not target_path.exists():
                return False
            data = json.loads(target_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return False
            with window.lock:
                window.verified_success_refs = list(data.get("verified_success_refs", []))
                window.counterexample_refs = list(data.get("counterexample_refs", []))
                window.mined_candidate_ids = list(data.get("mined_candidate_ids", []))
                window.segment_evidence_revisions = {k: int(v) for k, v in (data.get("segment_evidence_revisions") or {}).items()}
                window.attempt_count_per_segment = {k: int(v) for k, v in (data.get("attempt_count_per_segment") or {}).items()}
                window.attempts_at_revision = {
                    k: {int(r): int(cnt) for r, cnt in v.items()}
                    for k, v in (data.get("attempts_at_revision") or {}).items()
                }
                window.system2_samples = [int(s) for s in data.get("system2_samples", [])]
                window.decision_receipt_refs = list(data.get("decision_receipt_refs", []))
            return True
        except Exception:
            return False

    def _get_window(self, task_id: str, run_id: str) -> TaskRunObservationWindow:
        key, now = (task_id, str(run_id)), time.time()
        with self._windows_lock:
            stale = [k for k, w in self._windows.items() if now - w.last_touch > self.window_ttl_seconds]
            for k in stale:
                self._persist_window_checkpoint(self._windows[k])
                del self._windows[k]
            if key not in self._windows:
                while len(self._windows) >= self.max_windows:
                    evict_k = min(self._windows, key=lambda k: self._windows[k].last_touch)
                    self._persist_window_checkpoint(self._windows[evict_k])
                    del self._windows[evict_k]
                window = TaskRunObservationWindow(
                    task_id=task_id, run_id=str(run_id), cooldown_seconds=self.cooldown_seconds)
                self._rehydrate_window_from_checkpoint(task_id, str(run_id), window)
                self._windows[key] = window
            window = self._windows[key]
            window.last_touch = now
            return window

    def schedule_event(self, event: CompilabilityEvent, owner: Optional[RunAdoptionOwner] = None) -> bool:
        """Enqueue non-blockingly. Disabled monitors and a full queue shed the event."""
        if not self.enabled or self._stop_event.is_set():
            return False
        self._bump("events_observed")
        if owner is not None:
            self._get_window(event.task_id, event.run_id).owner = owner
        self._ensure_worker()
        try:
            self._queue.put_nowait(event)
            return True
        except queue.Full:
            self._bump("events_shed")
            # DF-009: Preserve high-value references even under queue saturation
            if (
                event.outcome in _VERIFIED_OUTCOMES
                or event.outcome in _FAILURE_OUTCOMES
                or bool(event.sample_ref)
            ):
                window = self._get_window(event.task_id, event.run_id)
                window.add_event(event)
                self._persist_window_checkpoint(window)
            logger.debug("OnlineCompilabilityMonitor queue full; preserved high-value references")
            return False

    def drain(self, timeout: float = 2.0) -> bool:
        """Wait at most ``timeout`` seconds for queued events. Returns False if work remains."""
        deadline = time.monotonic() + max(0.0, timeout)
        while self._queue.unfinished_tasks:
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.01)
        return True

    def stop(self, timeout: float = 2.0) -> bool:
        """Stop the worker, persist checkpoints, and join within ``timeout``."""
        self._stop_event.set()
        with self._windows_lock:
            for w in list(self._windows.values()):
                self._persist_window_checkpoint(w)
        try:
            while True:
                self._queue.get_nowait()
                self._queue.task_done()
        except queue.Empty:
            pass
        thread = self._worker_thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(max(0.0, timeout))
            return not thread.is_alive()
        return True

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                event = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if not self._stop_event.is_set():
                    self.process_event(event)
            except Exception as exc:
                logger.warning("OnlineCompilabilityMonitor failed processing event: %s", exc, exc_info=True)
            finally:
                self._queue.task_done()

    # ------------------------------------------------------------------ event pipeline

    def process_event(self, event: CompilabilityEvent, owner: Optional[RunAdoptionOwner] = None) -> Dict[str, Any]:
        """Pre-filter -> System-1 decision -> (DIRECT only) mine -> validate -> record offer."""
        window = self._get_window(event.task_id, event.run_id)
        if owner is not None:
            window.owner = owner
        if not window.add_event(event):
            self._bump("events_filtered")
            return {"status": "filtered_duplicate"}
        if event.outcome in _VERIFIED_OUTCOMES or event.outcome in _FAILURE_OUTCOMES or bool(event.sample_ref):
            self._persist_window_checkpoint(window)
        if not self._deterministic_prefilter(window, event):
            self._bump("events_filtered")
            return {"status": "prefilter_insufficient"}

        decision = self._query_system1_compilability(window, event)
        stage = decision.get("stage", CompilabilityStage.KEEP_COLLECTING.value)
        summary: Dict[str, Any] = {"status": "evaluated", "stage": stage, "decision": decision,
                                   "task_id": event.task_id, "run_id": event.run_id}

        if self.mode != DIRECT:
            # SHADOW_FOR_EFFECTS: decisions recorded for calibration; effects remain restricted.
            self._bump("decisions_shadow")
            window.shadow_decisions.append({"stage": stage, "confidence": decision.get("confidence"),
                                            "request_id": decision.get("request_id")})
            del window.shadow_decisions[:-32]
            summary["shadow"] = True

        # OBSERVE_ACTIVE: safe candidate mining and preparatory validation happen regardless of effect mode
        # as long as stage warrants mining/validation.

        if stage in (CompilabilityStage.MINE_CANDIDATE.value, CompilabilityStage.POSSIBLE_RUN_LOCAL_REUSE.value):
            seg_key = window.get_segment_key(event)
            if window.can_attempt_compilation(seg_key):
                window.record_compilation_attempt(seg_key)
                candidates = self.mine_candidate_in_run(event.task_id, event.run_id)
                summary["mined_candidates"] = [c.id for c in candidates]
            else:
                summary["mining_skipped"] = "budget_exceeded"
        if stage in (CompilabilityStage.MINE_CANDIDATE.value, CompilabilityStage.VALIDATE_CANDIDATE.value,
                     CompilabilityStage.POSSIBLE_RUN_LOCAL_REUSE.value):
            for cand_id in list(window.mined_candidate_ids):
                cand = self.registry.get(cand_id)
                if cand is None or cand_id in window.offers:
                    continue
                if window.validation_attempts.get(cand_id, 0) >= window.max_validation_attempts:
                    continue
                window.validation_attempts[cand_id] = window.validation_attempts.get(cand_id, 0) + 1
                valid, proof, reasons = self.validate_candidate_run_local(
                    cand, task_id=event.task_id, run_id=event.run_id)
                if valid and proof is not None:
                    summary["validated_candidate"] = cand_id
                    summary["offer"] = window.offers[cand_id].offer_id
                else:
                    summary.setdefault("validation_denied", {})[cand_id] = reasons
        self._persist_window_checkpoint(window)
        return summary

    def _deterministic_prefilter(self, window: TaskRunObservationWindow, event: CompilabilityEvent) -> bool:
        """Cheap deterministic gate before any inference (cooldown, budget, evidence, repetition)."""
        if (time.time() - window.last_inference_time) < window.cooldown_seconds:
            return False
        seg_key = window.get_segment_key(event)
        if not window.can_attempt_compilation(seg_key):
            return False
        if event.outcome in _FAILURE_OUTCOMES or event.outcome in ("failed", "uncertain"):
            self._bump("counterexamples_collected")
            if not window.verified_success_refs:
                return False
        family_events = [e for e in window.events if window.get_segment_key(e) == seg_key]
        verified = sum(1 for e in family_events if e.outcome in _VERIFIED_OUTCOMES)
        if verified >= 1 and len(family_events) >= 2:
            return True
        return event.event_kind in ("verified_transition", "operation_family_repeated")

    def _query_system1_compilability(self, window: TaskRunObservationWindow, event: CompilabilityEvent) -> Dict[str, Any]:
        """Ask System-1. Abstention, timeout, invalid output or exceptions never authorize anything."""
        window.last_inference_time = time.time()
        self._bump("decisions_requested")
        seg_key = window.get_segment_key(event)
        family_events = [e for e in window.events if window.get_segment_key(e) == seg_key]
        verified = sum(1 for e in family_events if e.outcome in _VERIFIED_OUTCOMES)
        failures = sum(1 for e in family_events if e.outcome in ("failed", TransitionOutcome.FAILED.value))
        req = build_compilability_decision_request(
            task_id=event.task_id, run_id=event.run_id, operation_id=event.operation_id,
            operation_family=event.operation_family or event.primitive,
            target_family=event.target_family or event.route,
            recent_experience_refs=list(window.verified_success_refs)[-10:],
            repeat_count=len(family_events),
            parameter_variability=len({digest(e.state_summary)[:8] for e in family_events}) > 1,
            verified_success_count=verified, failure_count=failures,
            has_verifier=bool(event.evidence_refs or verified > 0),
            effect_risk="read_only" if event.route in ("filesystem", "browser") and event.primitive.startswith(
                ("read", "stat")) else "mutation",
            progress_detected=verified > 0,
            expected_utility=compute_expected_operational_utility(remaining_item_count=max(1, len(family_events))),
        )
        try:
            res: Optional[DecisionResult] = decide_system1(req)
        except Exception as exc:
            logger.debug("System-1 decision failed (%s); learning plane stays idle", exc)
            res = None

        if res is None or res.fallback_recommended or res.is_abstained():
            self._bump("decisions_abstain")
            return {"stage": CompilabilityStage.KEEP_COLLECTING.value, "confidence": 0.0,
                    "provider": getattr(res, "provider", "none"), "abstained": True, "fallback": True}

        answers = res.answers or res.decisions or {}
        stage = answers.get("compilability_stage", CompilabilityStage.KEEP_COLLECTING.value)
        if stage == CompilabilityStage.ABSTAIN.value:
            self._bump("decisions_abstain")
            return {"stage": CompilabilityStage.KEEP_COLLECTING.value, "confidence": 0.0,
                    "provider": res.provider, "abstained": True, "fallback": False}
        if stage not in {s.value for s in CompilabilityStage}:
            self._bump("decisions_abstain")
            return {"stage": CompilabilityStage.KEEP_COLLECTING.value, "confidence": 0.0,
                    "provider": res.provider, "abstained": True, "fallback": True, "invalid_stage": True}
        conf = res.confidence.get("compilability_stage", 0.0)
        receipt_ref = ""
        try:
            receipt_ref = persist_decision_receipt(DecisionReceipt(
                domain=req.domain, schema_id=req.schema_id, task_id=req.task_id, run_id=req.run_id,
                operation_id=req.operation_id, provider=res.provider, model=res.model or "",
                model_revision=res.model_revision, state_digest=req.state_hash,
                candidate_set_hash=req.candidate_set_hash, selected_candidate=stage,
                influence_mode=self.mode, answers=dict(res.answers or {}), confidence=dict(res.confidence or {}),
                calibrated_confidences=dict(getattr(res, "calibrated_confidences", {}) or {}),
                latency_ms=res.latency_ms or 0.0,
            ), self.artifacts)
            window.decision_receipt_refs.append(receipt_ref)
            del window.decision_receipt_refs[:-16]
        except Exception as exc:
            logger.debug("Failed persisting compilability decision receipt: %s", exc)
        return {"stage": stage, "confidence": conf, "provider": res.provider, "abstained": False,
                "fallback": False, "request_id": req.request_id, "receipt_ref": receipt_ref}

    # ------------------------------------------------------------------ mining / validation

    def mine_candidate_in_run(self, task_id: str, run_id: str) -> List[OperationalCapability]:
        """Compile only this TaskRun's own corpus samples (selected BEFORE compilation).

        Candidates stay CANDIDATE; nothing is promoted. A candidate whose lineage is not
        exclusively this run (e.g. a deduplicated merge with another run) is excluded
        from run-local use — absent metadata is never treated as authorization.
        """
        from workstation.experience_compiler.compilability_validation import candidate_lineage_denials

        self._bump("mining_attempts")
        window = self._get_window(task_id, run_id)
        try:
            # Other corpus instances (progressive capture, kernel) persist samples through the
            # shared artifact projection; index only THIS task's before selecting by run.
            self.corpus.refresh_task(task_id)
            mined = self.compiler.mine(task_id=task_id, run_id=str(run_id))
        except Exception as exc:
            logger.warning("Compilability mining failed: %s", exc, exc_info=True)
            return []
        run_candidates: List[OperationalCapability] = []
        for cap in mined or []:
            if candidate_lineage_denials(cap, task_id, str(run_id)):
                self._bump("candidates_lineage_rejected")
                continue
            run_candidates.append(cap)
            if cap.id not in window.mined_candidate_ids:
                window.mined_candidate_ids.append(cap.id)
        self._bump("candidates_yielded", len(run_candidates))
        return run_candidates

    def validate_candidate_run_local(
        self,
        candidate: OperationalCapability,
        *,
        task_id: Optional[str] = None,
        run_id: Optional[str] = None,
        owner: Optional[RunAdoptionOwner] = None,
    ) -> Tuple[bool, Optional[RunClosureProof], List[str]]:
        """Validation-only path: consume owner facts and canonical receipts; grant nothing."""
        self._bump("validations_attempted")
        window = self._get_window(task_id, run_id) if task_id and run_id else None
        resolved_owner = owner or (window.owner if window else None) or self.owner
        valid, proof, reasons, offer = validate_run_local_candidate(
            candidate, task_id=task_id, run_id=run_id, owner=resolved_owner, artifacts=self.artifacts,
            corpus_artifacts=getattr(self.corpus, "artifacts", None), contract_factory=self.contract_factory,
            decision_receipt_refs=tuple(window.decision_receipt_refs[-3:]) if window else (),
        )
        if not valid or proof is None or offer is None or window is None:
            return False, None, reasons or ["validation_denied"]
        with window.lock:
            if len(window.offers) >= window.max_offers:
                return False, None, ["offer_budget_exceeded"]
            for older in window.offers.values():  # newer, better-evidenced procedure replaces the same family
                if (older.operation_family, older.target_family) == (offer.operation_family, offer.target_family) \
                        and older.status == "ready":
                    older.status, older.revoked_reason = "superseded", "newer_candidate"
            window.validated_proofs[candidate.id] = proof
            window.offers[candidate.id] = offer
        self._bump("validations_passed")
        self._bump("offers_created")
        return True, proof, []

    # ------------------------------------------------------------------ adoption sink (no authority)

    def ready_offers(self, task_id: str, run_id: str) -> List[AdoptionOffer]:
        """Offers the runtime checkpoint may evaluate. SHADOW and disabled monitors expose none."""
        if not self.enabled or self.mode != DIRECT:
            return []
        valid, reason, attestation = verify_qualification_attestation(self._qualification_ref, self.artifacts)
        if not valid:
            self.mode, self.mode_downgrade_reason = SHADOW, reason
            return []
        with self._windows_lock:
            window = self._windows.get((task_id, str(run_id)))
        if window is None:
            return []
        with window.lock:
            return [o for o in window.offers.values() if o.status == "ready"
                    and o.operation_family == attestation["operation_family"]
                    and ("state_mutation" if o.proof.effect_budget else "read_only") == attestation["effect_class"]
                    and canonical_bytes(_qualified_verifier(o.proof.verifier_contract)) ==
                        canonical_bytes(_qualified_verifier(attestation["verifier_contract"]))]

    def record_adoption(self, task_id: str, run_id: str, record: Dict[str, Any]) -> None:
        """Account a checkpoint outcome. Only terminal, read-back-verified items count as reuse."""
        window = self._get_window(task_id, run_id)
        window.adoption_records.append(record)
        del window.adoption_records[:-64]
        if record.get("kind") == "denied":
            self._bump("adoption_denials")
            with self._metrics_lock:
                for reason in record.get("reasons", []):
                    bucket = self.metrics["adoption_denial_reasons"]
                    bucket[reason] = bucket.get(reason, 0) + 1
            return
        self._bump("items_attempted")
        if record.get("completed"):
            self._bump("items_completed")
        observed = record.get("system2_calls_observed")
        if record.get("verified"):
            self._bump("items_verified")
            self._bump("run_local_reuses")
            self._bump("system2_calls_avoided_estimated")  # unproven: one item != one avoided model call
            baseline = window.baseline_system2_calls_per_item()
            with self._metrics_lock:
                self.metrics["system2_baseline_calls_per_item"] = baseline
                if baseline is not None and observed is not None:
                    self._avoided_measured += max(0, round(baseline) - observed)
                    self._avoided_known = True
                    self.metrics["system2_calls_avoided"] = self._avoided_measured
                    self.metrics["system2_calls_avoided_status"] = "measured"
                if observed is not None:
                    self.metrics["system2_calls_observed"] += observed
            emit_event(
                TelemetryEventType.CAPABILITY_EXECUTION_FINISHED,
                source_owner="workstation.compilability_monitor", task_id=task_id, run_id=run_id,
                operation_id=record.get("item_id"), route=None, status="VERIFIED_REUSE",
                payload={"receipt_ref": record.get("receipt_ref"), "readbacks": record.get("readbacks")},
            )
        else:
            self._bump("items_failed")
            if record.get("failure", "").startswith(("UNCERTAIN", "handoff_exception")):
                self._bump("reconciliations")
        self._write_label(window, record)

    def _write_label(self, window: TaskRunObservationWindow, record: Dict[str, Any]) -> None:
        """Verifier-grounded label for later calibration; never the Laya confidence itself."""
        try:
            self.artifacts.store(window.task_id, f"compilability_label_{record.get('item_id')}.json", {
                "label": "verified_reuse" if record.get("verified") else "reuse_not_verified",
                "decision_receipt_refs": list(window.decision_receipt_refs),
                "reuse_receipt_ref": record.get("receipt_ref"), "run_id": window.run_id,
            }, schema=LABEL_SCHEMA)
        except Exception:
            logger.debug("compilability label not persisted", exc_info=True)


# ---------------------------------------------------------------------- singleton management
_MONITOR_INSTANCE: Optional[OnlineCompilabilityMonitor] = None
_MONITOR_LOCK = threading.Lock()


def get_compilability_monitor(
    artifacts: Optional[ArtifactStore] = None,
    registry: Optional[OperationalCapabilityRegistry] = None,
    corpus: Optional[ExperienceCorpus] = None,
    compiler: Optional[ExperienceCompiler] = None,
    mode: Optional[str] = None,
) -> OnlineCompilabilityMonitor:
    """Get or initialize the singleton monitor. Policy (SHADOW default, kill switch) comes from config."""
    global _MONITOR_INSTANCE
    with _MONITOR_LOCK:
        if _MONITOR_INSTANCE is None:
            policy = load_learning_policy()
            _MONITOR_INSTANCE = OnlineCompilabilityMonitor(
                artifacts=artifacts, registry=registry, corpus=corpus, compiler=compiler,
                mode=mode or policy.mode, direct_qualification_ref=policy.direct_qualification_ref,
                enabled=policy.enabled,
            )
        return _MONITOR_INSTANCE


def install_compilability_monitor(monitor: OnlineCompilabilityMonitor) -> OnlineCompilabilityMonitor:
    """Composition-root hook: make ``monitor`` the process monitor (stops a previous one)."""
    global _MONITOR_INSTANCE
    with _MONITOR_LOCK:
        previous, _MONITOR_INSTANCE = _MONITOR_INSTANCE, monitor
    if previous is not None and previous is not monitor:
        previous.stop()
    return monitor


def peek_compilability_monitor() -> Optional[OnlineCompilabilityMonitor]:
    """Existing monitor or None; never constructs one (checkpoints must not start the learning plane)."""
    with _MONITOR_LOCK:
        return _MONITOR_INSTANCE


def reset_compilability_monitor() -> None:
    """Reset singleton monitor (testing/isolation)."""
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
    owner: Optional[RunAdoptionOwner] = None,
    operation_family: str = "",
    target_family: str = "",
    system2_calls: Optional[int] = None,
) -> bool:
    """Entry point invoked by observers/checkpoints. Never blocks and never raises into the caller."""
    if not task_id or not run_id:
        return False
    event = CompilabilityEvent(
        event_kind=event_kind, sample_ref=ref, task_id=str(task_id), run_id=str(run_id),
        operation_id=str(operation_id or ""), primitive=primitive, route=route, outcome=outcome,
        state_summary=state_summary or {}, evidence_refs=evidence_refs,
        operation_family=operation_family, target_family=target_family, system2_calls=system2_calls,
    )
    try:
        return get_compilability_monitor().schedule_event(event, owner=owner)
    except Exception:
        logger.debug("online compilability notification dropped", exc_info=True)
        return False

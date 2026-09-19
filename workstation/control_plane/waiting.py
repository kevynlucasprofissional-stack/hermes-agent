"""AwaitCondition, CausalEventEnvelope, and Trigger Plane.

Enforces:
- EVENT WAKES. AUTHORITATIVE STATE CONFIRMS.
- TaskRun and operation fencing.
- Deduplication, cycle/loop circuit breaking, and zero LLM waiting waste.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any, Callable, Sequence
from uuid import uuid4

from workstation.artifacts import ArtifactStore
from workstation.contracts import utc_now
from workstation.control_plane.ir import Predicate, TRUE


class AwaitKind(str, Enum):
    WAITING_FOR_EVENT = "WAITING_FOR_EVENT"
    WAITING_FOR_TIMER = "WAITING_FOR_TIMER"
    WAITING_FOR_EXTERNAL_STATE = "WAITING_FOR_EXTERNAL_STATE"
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"


class TimeoutAction(str, Enum):
    FAIL = "FAIL"
    ASK_HUMAN = "ASK_HUMAN"
    WAKE_LLM = "WAKE_LLM"
    FALLBACK = "FALLBACK"
    CANCEL = "CANCEL"


@dataclass
class PollingPolicy:
    initial_interval: float = 1.0
    backoff: float = 1.5
    max_interval: float = 30.0
    deadline: str | None = None
    max_attempts: int = 10
    cost_budget: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PollingPolicy:
        return cls(**data)


@dataclass
class AwaitContinuation:
    """Canonical continuation structure for non-resident awaits surviving process restart."""
    task_id: str | None = None
    run_id: str | None = None
    operation_id: str | None = None
    intent_id: str | None = None
    intent_hash: str | None = None
    capability_pins: dict[str, Any] = field(default_factory=dict)
    contract_fingerprints: dict[str, str] = field(default_factory=dict)
    last_verified_state: dict[str, Any] = field(default_factory=dict)
    remaining_subgraph: list[dict[str, Any]] = field(default_factory=list)
    plan_id: str | None = None
    work_item_id: str | None = None
    deadline: float | None = None
    timeout_action: str = "WAKE_LLM"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AwaitContinuation:
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


def is_non_resident_wait(kind_or_condition: Any) -> bool:
    """True if wait must release the worker and use scheduled observer rather than local spin."""
    kind = kind_or_condition.kind if hasattr(kind_or_condition, "kind") else kind_or_condition
    if isinstance(kind, str):
        try:
            kind = AwaitKind(kind)
        except ValueError:
            return False
    return kind in {
        AwaitKind.WAITING_FOR_EVENT,
        AwaitKind.WAITING_FOR_TIMER,
        AwaitKind.WAITING_FOR_EXTERNAL_STATE,
        AwaitKind.WAITING_FOR_HUMAN,
        AwaitKind.WAITING_FOR_APPROVAL,
    }


@dataclass
class AwaitCondition:
    """Persistent wait specification surviving process restart."""

    wait_id: str
    kind: AwaitKind = AwaitKind.WAITING_FOR_EVENT
    predicate: Predicate = field(default_factory=TRUE)
    observer_type: str = ""
    correlation_id: str = ""
    continuation: dict[str, Any] | AwaitContinuation = field(default_factory=dict)
    task_id: str | None = None
    run_id: str | None = None
    operation_id: str | None = None
    capability_pins: dict[str, str] = field(default_factory=dict)
    created_state_version: str = ""
    deadline: str | None = None
    timeout_action: TimeoutAction = TimeoutAction.WAKE_LLM
    poll_policy: PollingPolicy | None = None
    temporal_semantics: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        cont = self.continuation.to_dict() if hasattr(self.continuation, "to_dict") else dict(self.continuation)
        return {
            "wait_id": self.wait_id,
            "kind": self.kind.value if isinstance(self.kind, AwaitKind) else str(self.kind),
            "predicate": self.predicate.to_dict(),
            "observer_type": self.observer_type,
            "correlation_id": self.correlation_id,
            "continuation": cont,
            "task_id": self.task_id,
            "run_id": self.run_id,
            "operation_id": self.operation_id,
            "capability_pins": dict(self.capability_pins),
            "created_state_version": self.created_state_version,
            "deadline": self.deadline,
            "timeout_action": self.timeout_action.value if isinstance(self.timeout_action, TimeoutAction) else str(self.timeout_action),
            "poll_policy": self.poll_policy.to_dict() if self.poll_policy else None,
            "temporal_semantics": self.temporal_semantics,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AwaitCondition:
        pred_raw = data.get("predicate", {})
        pred = Predicate.from_dict(pred_raw) if isinstance(pred_raw, dict) else TRUE()
        raw_kind = data.get("kind", AwaitKind.WAITING_FOR_EVENT.value)
        try:
            kind = AwaitKind(raw_kind)
        except ValueError:
            kind = AwaitKind.WAITING_FOR_EVENT
        raw_timeout = data.get("timeout_action", TimeoutAction.WAKE_LLM.value)
        try:
            timeout_action = TimeoutAction(raw_timeout)
        except ValueError:
            timeout_action = TimeoutAction.WAKE_LLM

        poll_raw = data.get("poll_policy")
        poll = PollingPolicy.from_dict(poll_raw) if isinstance(poll_raw, dict) else None

        cont_raw = data.get("continuation", {})
        if isinstance(cont_raw, dict) and any(k in cont_raw for k in ("plan_id", "intent_id", "remaining_subgraph", "capability_pins")):
            continuation = AwaitContinuation.from_dict(cont_raw)
        else:
            continuation = dict(cont_raw) if isinstance(cont_raw, dict) else cont_raw

        return cls(
            wait_id=str(data.get("wait_id", "")),
            kind=kind,
            predicate=pred,
            observer_type=str(data.get("observer_type", "")),
            correlation_id=str(data.get("correlation_id", "")),
            continuation=continuation,
            task_id=data.get("task_id"),
            run_id=data.get("run_id"),
            operation_id=data.get("operation_id"),
            capability_pins=dict(data.get("capability_pins", {})),
            created_state_version=str(data.get("created_state_version", "")),
            deadline=data.get("deadline"),
            timeout_action=timeout_action,
            poll_policy=poll,
            temporal_semantics=data.get("temporal_semantics"),
        )


class AwaitConditionStore:
    """Durable persistence for AwaitCondition records using ArtifactStore."""

    def __init__(self, artifacts: ArtifactStore | None = None, root: Path | str | None = None) -> None:
        self.artifacts = artifacts or ArtifactStore()
        self.root = Path(root) if root else self.artifacts.root.parent / "await_conditions"
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, condition: AwaitCondition) -> None:
        file_path = self.root / f"{condition.wait_id}.json"
        temp = file_path.with_name(f"{file_path.name}.tmp")
        with temp.open("w", encoding="utf-8") as f:
            json.dump(condition.to_dict(), f, indent=2)
        temp.replace(file_path)

    def get(self, wait_id: str) -> AwaitCondition | None:
        file_path = self.root / f"{wait_id}.json"
        if not file_path.exists():
            return None
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return AwaitCondition.from_dict(data)
        except Exception:
            return None

    def find_by_correlation(self, correlation_id: str) -> list[AwaitCondition]:
        results = []
        for p in self.root.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                cond = AwaitCondition.from_dict(data)
                if cond.correlation_id == correlation_id:
                    results.append(cond)
            except Exception:
                continue
        return results

    def delete(self, wait_id: str) -> None:
        file_path = self.root / f"{wait_id}.json"
        if file_path.exists():
            file_path.unlink()


@dataclass
class CausalEventEnvelope:
    """Normalized trigger event with causal lineage, provenance, and trust classification."""

    event_id: str
    event_type: str
    schema_version: int = 1
    source: str = ""
    trust_class: str = "trusted_internal"
    task_id: str | None = None
    session_id: str | None = None
    run_id: str | None = None
    operation_id: str | None = None
    resource_id: str | None = None
    resource_version: str | None = None
    correlation_id: str | None = None
    root_event_id: str | None = None
    parent_event_id: str | None = None
    causal_depth: int = 0
    observed_at: str = field(default_factory=utc_now)
    evidence_ref: str | None = None
    dedupe_key: str = ""
    ttl_expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CausalEventEnvelope:
        return cls(**data)


class TriggerCircuitBreaker:
    """Detects cycles and no-progress trigger storms, tripping before runaway loops."""

    def __init__(self, max_unproductive_cycles: int = 3) -> None:
        self.max_unproductive_cycles = max_unproductive_cycles
        self._reaction_counts: dict[tuple, int] = {}
        self._tripped: set[tuple] = set()

    def record_reaction(
        self,
        trigger_id: str,
        capability_id: str,
        resource_id: str,
        state_fingerprint: str,
        progress_made: bool = False,
    ) -> bool:
        """Record reaction. Returns True if execution allowed, False if circuit is tripped."""
        key = (trigger_id, capability_id, resource_id, state_fingerprint)
        if key in self._tripped:
            return False

        if progress_made:
            self._reaction_counts[key] = 0
            return True

        current = self._reaction_counts.get(key, 0) + 1
        self._reaction_counts[key] = current
        if current > self.max_unproductive_cycles:
            self._tripped.add(key)
            return False
        return True

    def is_tripped(
        self,
        trigger_id: str,
        capability_id: str,
        resource_id: str,
        state_fingerprint: str,
    ) -> bool:
        return (trigger_id, capability_id, resource_id, state_fingerprint) in self._tripped


class TriggerCoordinator:
    """Coordinates incoming causal events against persistent AwaitConditions."""

    def __init__(
        self,
        store: AwaitConditionStore,
        circuit_breaker: TriggerCircuitBreaker | None = None,
        resume_handler: Callable[[AwaitCondition, dict[str, Any]], bool] | None = None,
    ) -> None:
        self.store = store
        self.circuit_breaker = circuit_breaker or TriggerCircuitBreaker()
        self.resume_handler = resume_handler
        self._seen_dedupes: set[str] = set()

    def handle_event(
        self,
        event: CausalEventEnvelope,
        read_authoritative_state: Callable[[], dict[str, Any]],
        resume_fn: Callable[[AwaitCondition, dict[str, Any]], bool] | None = None,
    ) -> bool:
        """Process event. Returns True if an AwaitCondition was successfully satisfied and resumed."""
        # Deduplication check
        if event.dedupe_key and event.dedupe_key in self._seen_dedupes:
            return False

        # Correlation lookup
        if not event.correlation_id:
            return False

        conditions = self.store.find_by_correlation(event.correlation_id)
        if not conditions:
            return False

        active_resume = resume_fn or self.resume_handler
        any_resumed = False

        for cond in conditions:
            # TaskRun and Operation fence verification
            if cond.run_id and event.run_id and cond.run_id != event.run_id:
                continue
            if cond.task_id and event.task_id and cond.task_id != event.task_id:
                continue
            if cond.operation_id and event.operation_id and cond.operation_id != event.operation_id:
                continue

            # Rule 21.2: EVENT WAKES. AUTHORITATIVE STATE CONFIRMS.
            authoritative_state = read_authoritative_state()
            if not cond.predicate.evaluate(authoritative_state):
                # State does NOT confirm predicate -> reject resume!
                continue

            # Resumption execution: condition remains stored until resume is confirmed
            resumed = True
            if active_resume is not None:
                try:
                    resumed = bool(active_resume(cond, authoritative_state))
                except Exception:
                    resumed = False

            if resumed:
                self.store.delete(cond.wait_id)
                any_resumed = True

        if event.dedupe_key:
            self._seen_dedupes.add(event.dedupe_key)

        return any_resumed

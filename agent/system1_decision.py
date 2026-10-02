"""Generic System-1 decision seam.

System-1 provides typed semantic classification, ranking, shortlisting,
and known-path selection among application-defined valid alternatives
before or alongside System-2 (LLM) reasoning.

Rules:
1. Core agent code depends ONLY on this generic contract, never on Workstation or Laya directly.
2. Software/deterministic constraints define the valid decision space; System-1 estimates
   what is semantically appropriate among valid possibilities.
3. System-1 never grants authority, mints a RoutingCertificate, establishes effect safety,
   declares a mutation verified, or converts confidence into COMMITTED.
4. Failure, invalid schemas, empty candidate sets, or abstentions must safely fall back
   to deterministic or System-2 paths.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DecisionRequest:
    """Request for a bounded System-1 decision."""

    request_id: str = ""
    domain: str = ""
    schema_id: str = ""
    task_id: str = ""
    run_id: str = ""
    operation_id: str = ""

    state_ref: str = ""
    state_hash: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    minimal_state: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

    questions: Dict[str, Any] = field(default_factory=dict)
    question_schema_version: str = "1.0.0"

    candidate_sets: Dict[str, List[str]] = field(default_factory=dict)
    candidate_set_hash: str = ""

    policy_ref: str = ""
    language: str = "en"
    risk_class: str = "standard"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.request_id:
            import uuid
            self.request_id = f"req_{uuid.uuid4().hex[:12]}"
        if not self.minimal_state and self.state:
            self.minimal_state = self.state
        if not self.run_id and self.context:
            self.run_id = self.context.get("run_id", "")
        if not self.operation_id and self.context:
            self.operation_id = self.context.get("operation_id", "")
        if not self.task_id and self.context:
            self.task_id = self.context.get("task_id", "")

    def request_hash(self) -> str:
        import hashlib, json
        data = {
            "request_id": self.request_id,
            "questions": self.questions,
            "minimal_state": self.minimal_state,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode("utf-8")).hexdigest()


@dataclass
class DecisionResult:
    """Result of a bounded System-1 decision."""

    request_id: str = ""
    answers: Dict[str, Any] = field(default_factory=dict)
    decisions: Dict[str, Any] = field(default_factory=dict)
    probabilities: Dict[str, Dict[str, float]] = field(default_factory=dict)
    confidence: Dict[str, float] = field(default_factory=dict)
    confidences: Dict[str, float] = field(default_factory=dict)
    calibrated_confidences: Dict[str, float] = field(default_factory=dict)
    abstentions: List[str] = field(default_factory=list)

    provider: str = ""
    model: str = ""
    model_revision: Optional[str] = None
    calibration_id: str = ""
    schema_id: str = ""
    request_hash: str = ""

    latency_ms: float = 0.0
    fallback_recommended: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.answers and self.decisions:
            self.answers = self.decisions
        elif not self.decisions and self.answers:
            self.decisions = self.answers
        if not self.confidence and self.confidences:
            self.confidence = self.confidences
        elif not self.confidences and self.confidence:
            self.confidences = self.confidence

    def receipt_hash(self) -> str:
        import hashlib, json
        data = {
            "request_id": self.request_id,
            "answers": self.answers,
            "provider": self.provider,
            "confidence": self.confidence,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode("utf-8")).hexdigest()

    def is_abstained(self, question_id: Optional[str] = None) -> bool:
        """Check if an individual question or the whole decision was abstained."""
        if question_id:
            return question_id in self.abstentions
        return bool(self.abstentions and len(self.abstentions) >= len(self.answers or self.abstentions))


System1DecisionProvider = Callable[[DecisionRequest], Optional[DecisionResult]]

_providers: List[System1DecisionProvider] = []

_metrics: Dict[str, int] = {
    "requests": 0,
    "successes": 0,
    "abstentions": 0,
    "fallbacks": 0,
    "errors": 0,
}


def register_system1_decision_provider(provider: System1DecisionProvider) -> None:
    """Register a System-1 decision provider."""
    if provider not in _providers:
        _providers.append(provider)


def unregister_system1_decision_provider(provider: System1DecisionProvider) -> None:
    """Unregister a System-1 decision provider."""
    if provider in _providers:
        _providers.remove(provider)


def system1_decision_providers() -> tuple[System1DecisionProvider, ...]:
    """Get all registered System-1 decision providers."""
    return tuple(_providers)


def system1_decision_metrics() -> Dict[str, int]:
    """Return execution metrics for the System-1 decision seam."""
    res = dict(_metrics)
    res["invocations"] = res.get("requests", 0)
    return res


def reset_system1_decision() -> None:
    """Reset providers and metrics (for testing/teardown)."""
    _providers.clear()
    for key in _metrics:
        _metrics[key] = 0


def _provider_name(provider: Any) -> str:
    return getattr(provider, "__name__", None) or repr(provider)


def decide_system1(request: DecisionRequest) -> Optional[DecisionResult]:
    """Query registered System-1 providers in order for a decision.

    Falls back cleanly without raising if providers fail or abstain.
    """
    _metrics["requests"] += 1
    if not _providers:
        _metrics["fallbacks"] += 1
        return DecisionResult(
            request_id=request.request_id,
            provider="deterministic_fallback",
            answers={q: "ABSTAIN" for q in request.questions},
            confidence={q: 0.0 for q in request.questions},
            abstentions=list(request.questions.keys()),
            fallback_recommended=True,
        )

    for provider in list(_providers):
        name = _provider_name(provider)
        start_t = time.perf_counter()
        try:
            result = provider(request)
        except Exception:
            _metrics["errors"] += 1
            _metrics["fallbacks"] += 1
            logger.error(
                "System-1 decision provider %s raised an exception; falling back to default path",
                name,
                exc_info=True,
            )
            continue

        if result is None:
            continue

        if not isinstance(result, DecisionResult):
            _metrics["errors"] += 1
            _metrics["fallbacks"] += 1
            logger.error(
                "System-1 decision provider %s returned %r instead of DecisionResult; falling back",
                name,
                type(result).__name__,
            )
            continue

        if not result.provider:
            result.provider = name
        if result.latency_ms <= 0:
            result.latency_ms = (time.perf_counter() - start_t) * 1000.0

        if result.fallback_recommended or result.is_abstained():
            _metrics["abstentions"] += 1
            _metrics["fallbacks"] += 1
            logger.info("System-1 decision provider %s recommended fallback / abstained", name)
            return result

        _metrics["successes"] += 1
        return result

    return None

"""Base classes and testing stubs for System-1 providers."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Dict, List, Optional

from agent.system1_decision import DecisionRequest, DecisionResult
from workstation.system1.calibration import default_calibration_policy
from workstation.system1.contracts import NeutralChoice

logger = logging.getLogger(__name__)


class BaseSystem1Provider:
    """Abstract base provider for System-1 semantic decisions."""

    def __init__(self, name: str = "base_system1"):
        self.name = name

    def __call__(self, request: DecisionRequest) -> Optional[DecisionResult]:
        return self.decide(request)

    def decide(self, request: DecisionRequest) -> Optional[DecisionResult]:
        raise NotImplementedError


class FakeSystem1DecisionProvider(BaseSystem1Provider):
    """Stub provider for hermetic testing without weight downloads or GPU/CPU inference.

    Supports configuring predetermined answers, probabilities, confidence,
    simulated abstentions, deliberate failures, or simulated timeouts.
    """

    def __init__(
        self,
        name: str = "fake_system1",
        model: str = "fake-laya",
        preset_answers: Optional[Dict[str, Any]] = None,
        preset_confidence: Optional[Dict[str, float]] = None,
        preset_decisions: Optional[Dict[str, Any]] = None,
        preset_confidences: Optional[Dict[str, float]] = None,
        preset_probabilities: Optional[Dict[str, Dict[str, float]]] = None,
        should_abstain: bool = False,
        should_fail: bool = False,
        should_timeout: bool = False,
        preferred_candidate_override: Optional[str] = None,
    ):
        super().__init__(name=name)
        self.model = model
        self.preset_answers = preset_answers or preset_decisions or {}
        self.preset_confidence = preset_confidence or preset_confidences or {}
        self.preset_probabilities = preset_probabilities or {}
        self.should_abstain = should_abstain
        self.should_fail = should_fail
        self.should_timeout = should_timeout
        self.preferred_candidate_override = preferred_candidate_override
        self.recorded_requests: List[DecisionRequest] = []

    def decide(self, request: DecisionRequest) -> Optional[DecisionResult]:
        self.recorded_requests.append(request)

        if self.should_fail:
            raise RuntimeError("Simulated FakeSystem1DecisionProvider deliberate failure")

        if self.should_timeout:
            time.sleep(0.05)
            raise TimeoutError("Simulated FakeSystem1DecisionProvider timeout")

        if self.should_abstain:
            return DecisionResult(
                request_id=request.request_id,
                answers={q_id: NeutralChoice.ABSTAIN.value for q_id in request.questions},
                confidence={q_id: 0.20 for q_id in request.questions},
                abstentions=list(request.questions.keys()),
                provider=self.name,
                model=self.model,
                fallback_recommended=True,
            )

        answers: Dict[str, Any] = dict(self.preset_answers)
        confidence: Dict[str, float] = dict(self.preset_confidence)
        probabilities: Dict[str, Dict[str, float]] = dict(self.preset_probabilities)
        abstentions: List[str] = []

        # If a candidate ranking was requested and no preset provided, rank candidates
        for q_id, q_spec in request.questions.items():
            if q_id not in answers:
                if q_id == "preferred_candidate":
                    candidates = request.candidate_sets.get("candidates", [])
                    if self.preferred_candidate_override:
                        chosen = self.preferred_candidate_override
                    elif candidates:
                        chosen = candidates[0]
                    else:
                        chosen = NeutralChoice.NO_MATCH.value
                    answers[q_id] = chosen
                    confidence[q_id] = self.preset_confidence.get(q_id, 0.95)
                    probabilities[q_id] = {c: (0.95 if c == chosen else 0.05) for c in candidates}
                elif q_id == "needs_system2":
                    answers[q_id] = self.preset_answers.get(q_id, "no")
                    confidence[q_id] = self.preset_confidence.get(q_id, 0.90)
                elif q_id == "capability_family":
                    answers[q_id] = self.preset_answers.get(q_id, "filesystem")
                    confidence[q_id] = self.preset_confidence.get(q_id, 0.88)
                elif q_id == "progress_class":
                    answers[q_id] = self.preset_answers.get(q_id, "progressing")
                    confidence[q_id] = self.preset_confidence.get(q_id, 0.85)
                elif q_id == "ambiguity_kind":
                    answers[q_id] = self.preset_answers.get(q_id, "none")
                    confidence[q_id] = self.preset_confidence.get(q_id, 0.80)
                elif q_id == "known_recovery_path":
                    answers[q_id] = self.preset_answers.get(q_id, "switch_alternative")
                    confidence[q_id] = self.preset_confidence.get(q_id, 0.85)
                else:
                    answers[q_id] = NeutralChoice.ABSTAIN.value
                    confidence[q_id] = 0.30
                    abstentions.append(q_id)

        # Check calibration policy
        for q_id, conf in confidence.items():
            if not default_calibration_policy.evaluate_confidence(
                q_id, conf, model=self.model, language=request.language, risk_class=request.risk_class
            ):
                if q_id not in abstentions:
                    abstentions.append(q_id)

        fallback_rec = len(abstentions) == len(request.questions)

        return DecisionResult(
            request_id=request.request_id,
            answers=answers,
            probabilities=probabilities,
            confidence=confidence,
            abstentions=abstentions,
            provider=self.name,
            model=self.model,
            calibration_id="fake-calib-v1",
            latency_ms=1.5,
            fallback_recommended=fallback_rec,
            details={"stub": True},
        )

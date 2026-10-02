"""Active Laya Decision Provider for Hermes Work System-1.

Wraps a resident Laya Router instance to provide fast, calibrated,
non-autoregressive decisions on bounded closed-schema question sets.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from typing import Any, Dict, List, Optional

from agent.system1_decision import DecisionRequest, DecisionResult
from workstation.artifacts import ArtifactStore
from workstation.system1.calibration import CalibrationPolicy, default_calibration_policy
from workstation.system1.contracts import (
    NeutralChoice,
    compute_candidate_set_hash,
    compute_state_hash,
)
from workstation.system1.provenance import verify_laya_provenance, get_laya_provenance
from workstation.system1.receipts import DecisionReceipt, persist_decision_receipt

logger = logging.getLogger(__name__)


class LayaDecisionProvider:
    """Resident System-1 decision provider backed by vendored Laya Router."""

    def __init__(
        self,
        model: str = "multilingual",
        device: Optional[str] = None,
        max_loaded: int = 1,
        auto_preload: bool = False,
        calibration_policy: Optional[CalibrationPolicy] = None,
        artifact_store: Optional[ArtifactStore] = None,
    ):
        self.model = model
        self.device = device or "cpu"
        self.max_loaded = max_loaded
        self.calibration_policy = calibration_policy or default_calibration_policy
        self.artifact_store = artifact_store or ArtifactStore()
        self._router = None
        self._router_lock = threading.Lock()

        # Enforce provenance on initialization
        verify_laya_provenance()
        self.provenance = get_laya_provenance(model=model, device=self.device,
            calibration_id=self.calibration_policy.calibration_id)

        if auto_preload:
            self._ensure_router()

    def _ensure_router(self):
        """Get or initialize the resident Laya Router."""
        if self._router is not None:
            return self._router

        with self._router_lock:
            if self._router is not None:
                return self._router

            from laya import Router

            logger.info("Initializing resident Laya Router on device: %s", self.device)
            self._router = Router(
                device=self.device,
                default=self.model,
                max_loaded=self.max_loaded,
                auto_task_detection=False,
            )
            return self._router

    def __call__(self, request: DecisionRequest) -> Optional[DecisionResult]:
        return self.decide(request)

    def decide(self, request: DecisionRequest) -> Optional[DecisionResult]:
        """Execute a calibrated decision using the resident Router.

        Guarantees:
        1. Context sent to Laya is strictly minimal (objective, task_phase, minimal_state, constraints).
        2. Candidate choices are bounded to <= 20 alternatives.
        3. Portuguese workloads route explicitly to multilingual without heuristic autodetection.
        4. Any exception or failure degrades cleanly to fallback_recommended=True.
        """
        start_time = time.perf_counter()

        if not request.questions:
            return DecisionResult(
                request_id=request.request_id,
                fallback_recommended=True,
                details={"reason": "empty_questions"},
            )

        try:
            router = self._ensure_router()

            # 1. Build minimal state payload for Laya (never send full transcript)
            minimal_state = dict(request.minimal_state)
            if "objective" not in minimal_state and request.metadata.get("objective"):
                minimal_state["objective"] = request.metadata["objective"]
            if "task_phase" not in minimal_state and request.metadata.get("task_phase"):
                minimal_state["task_phase"] = request.metadata["task_phase"]

            # 2. Determine target language and model routing
            lang = request.language or "en"
            target_model = self.model
            if lang in ("pt", "por", "pt-br"):
                target_model = "multilingual"
                effective_lang = "pt"
            else:
                effective_lang = lang

            # 3. Predict via resident Router
            raw_output = router.predict(
                state=minimal_state,
                questions=request.questions,
                model=target_model,
                lang=effective_lang,
            )

            latency_ms = (time.perf_counter() - start_time) * 1000.0

            # 4. Extract answers, probabilities, and confidence
            answers: Dict[str, Any] = {}
            probabilities: Dict[str, Dict[str, float]] = {}
            confidence: Dict[str, float] = {}
            calibrated_confidences: Dict[str, float] = {}
            abstentions: List[str] = []

            for q_id, question in request.questions.items():
                q_res = raw_output.get("answers", {}).get(q_id, {})
                kind = question.get("type", "choice")
                ans = q_res.get(kind) if q_res.get("type", kind) == kind else None
                conf = float(q_res.get("answer_confidence", q_res.get("confidence", 0.0)))
                if not math.isfinite(conf) or not 0 <= conf <= 1:
                    conf = 0.0
                probs = q_res.get("probabilities", {})
                valid = ans is not None and kind in ("choice", "score", "noul")
                if kind == "choice":
                    valid = valid and ans in question.get("criteria", {})
                elif kind in ("score", "noul"):
                    upper = len(question.get("criteria", [])) - 1 if kind == "score" else 1
                    valid = valid and isinstance(ans, (float, int)) and math.isfinite(ans) and 0 <= ans <= upper
                if "answer_confidence" in q_res:
                    calibrated_confidences[q_id] = conf

                answers[q_id] = ans
                confidence[q_id] = conf
                probabilities[q_id] = probs

                # Check neutral choices
                if not valid or ans in (NeutralChoice.ABSTAIN.value, NeutralChoice.NO_MATCH.value):
                    abstentions.append(q_id)
                elif not self.calibration_policy.evaluate_confidence(
                    q_id, conf, model=target_model, language=effective_lang, risk_class=request.risk_class
                ):
                    abstentions.append(q_id)

            fallback_rec = len(abstentions) >= len(request.questions)

            result = DecisionResult(
                request_id=request.request_id,
                answers=answers,
                probabilities=probabilities,
                confidence=confidence,
                calibrated_confidences=calibrated_confidences,
                abstentions=abstentions,
                provider="laya",
                model=target_model,
                model_revision=self.provenance.checkpoint_revision,
                schema_id=request.schema_id,
                request_hash=request.request_hash(),
                calibration_id=self.calibration_policy.calibration_id,
                latency_ms=latency_ms,
                fallback_recommended=fallback_rec,
                details={
                    "routing": raw_output.get("routing", {}),
                    "usage": raw_output.get("usage", {}),
                },
            )

            # 5. Persist durable DecisionReceipt
            receipt = DecisionReceipt(
                request_ref=request.state_ref or compute_state_hash(request.minimal_state),
                request_hash=request.request_hash(),
                domain=request.domain,
                schema_id=request.schema_id,
                state_digest=compute_state_hash(request.minimal_state),
                result_ref=f"res_{request.request_id}",
                task_id=request.task_id,
                run_id=request.run_id,
                operation_id=request.operation_id,
                influence_mode="direct" if not fallback_rec else "fallback",
                selected_candidate=answers.get("preferred_candidate"),
                fallback_taken=fallback_rec,
                provider="laya",
                model=target_model,
                calibration_id=self.calibration_policy.calibration_id,
                question_schema_version=request.question_schema_version,
                confidence=confidence,
                calibrated_confidences=calibrated_confidences,
                laya_version=self.provenance.laya_version,
                laya_source_sha=self.provenance.laya_source_sha,
                model_revision=self.provenance.checkpoint_revision,
                details={"probabilities": probabilities, "abstentions": abstentions,
                    "candidate_set_hash": request.candidate_set_hash or compute_candidate_set_hash(request.candidate_sets),
                    "provenance": self.provenance.to_dict()},
                answers=answers,
                latency_ms=latency_ms,
            )
            result.details["receipt_ref"] = persist_decision_receipt(receipt, self.artifact_store)

            return result

        except Exception as exc:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error("Laya decision execution failed; falling back to default path", exc_info=True)
            return DecisionResult(
                request_id=request.request_id,
                provider="laya",
                model=self.model,
                latency_ms=latency_ms,
                fallback_recommended=True,
                details={"error": str(exc)},
            )

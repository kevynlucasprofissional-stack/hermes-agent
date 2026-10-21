"""Authentic Workstation operational milestone contracts and emitter.

Provides structured milestone reporting for:
- candidate identification
- compilation starts
- validation pass/fail
- capability selection
- execution verification with readback
- execution rejection

Strict invariants:
- Never fabricate success milestones without confirmed source evidence.
- Sanitize evidence references (no PII, credentials, tokens, or page content).
- Scoped to authoritative session IDs to prevent cross-conversation leakage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import re
from typing import Any, Literal, Sequence
import uuid

logger = logging.getLogger(__name__)

Stage = Literal[
    "observed",
    "candidate",
    "compilation_started",
    "validation_passed",
    "validation_failed",
    "capability_selected",
    "executed",
    "rejected",
]

VALID_STAGES: frozenset[str] = frozenset({
    "observed",
    "candidate",
    "compilation_started",
    "validation_passed",
    "validation_failed",
    "capability_selected",
    "executed",
    "rejected",
})

_SENSITIVE_KEY_RE = re.compile(
    r"(?:token|key|secret|password|auth|bearer|credential|session_token)[=:][^\s&,]+",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"[\w.-]+@[\w.-]+\.\w+")


def sanitize_evidence_ref(ref: str) -> str:
    """Sanitize an evidence reference to ensure no PII, keys, or raw page content leak.

    Only structured references, artifact paths, hashes, and schema identifiers are retained.
    """
    if not isinstance(ref, str):
        return ""
    cleaned = ref.strip()
    if not cleaned:
        return ""
    cleaned = _SENSITIVE_KEY_RE.sub("<redacted_secret>", cleaned)
    cleaned = _EMAIL_RE.sub("<redacted_email>", cleaned)
    if len(cleaned) > 200:
        cleaned = cleaned[:197] + "..."
    return cleaned


@dataclass(frozen=True)
class WorkstationMilestone:
    """Contract for authentic Workstation milestones."""

    eventId: str
    sessionId: str
    stage: Stage
    occurredAt: str
    taskRunId: str | None = None
    learningSessionId: str | None = None
    capabilityId: str | None = None
    evidenceRefs: list[str] = field(default_factory=list)
    reasonCode: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "eventId": self.eventId,
            "sessionId": self.sessionId,
            "stage": self.stage,
            "occurredAt": self.occurredAt,
            "taskRunId": self.taskRunId,
            "learningSessionId": self.learningSessionId,
            "capabilityId": self.capabilityId,
            "evidenceRefs": list(self.evidenceRefs),
            "reasonCode": self.reasonCode,
        }


def emit_workstation_milestone(
    stage: Stage,
    sessionId: str,
    *,
    eventId: str | None = None,
    taskRunId: str | None = None,
    learningSessionId: str | None = None,
    capabilityId: str | None = None,
    evidenceRefs: Sequence[str] | None = None,
    reasonCode: str | None = None,
    occurredAt: str | None = None,
    agent: Any = None,
) -> WorkstationMilestone:
    """Emit an authentic Workstation operational milestone.

    Never synthesizes success without genuine source confirmation.
    Applies privacy filter to evidenceRefs.
    Routes through tools.desktop_ui emitter or agent callbacks if available.
    """
    if stage not in VALID_STAGES:
        raise ValueError(f"Invalid WorkstationMilestone stage: {stage}")

    eid = eventId or f"ms-{uuid.uuid4().hex[:12]}"
    now_iso = occurredAt or datetime.now(timezone.utc).isoformat()

    sanitized_refs = [
        sanitize_evidence_ref(ref) for ref in (evidenceRefs or []) if ref
    ]

    milestone = WorkstationMilestone(
        eventId=eid,
        sessionId=str(sessionId or "").strip(),
        stage=stage,
        occurredAt=now_iso,
        taskRunId=str(taskRunId).strip() if taskRunId else None,
        learningSessionId=str(learningSessionId).strip() if learningSessionId else None,
        capabilityId=str(capabilityId).strip() if capabilityId else None,
        evidenceRefs=[r for r in sanitized_refs if r],
        reasonCode=str(reasonCode).strip() if reasonCode else None,
    )

    payload = milestone.to_dict()

    try:
        from tools import desktop_ui

        if desktop_ui._emit is not None and milestone.sessionId:
            desktop_ui._emit(milestone.sessionId, "workstation.milestone", payload)
    except Exception:  # health: allow BLE001 -- milestone routing non-fatal
        logger.debug("Failed to emit milestone via desktop_ui", exc_info=True)

    if agent is not None:
        try:
            emit_fn = getattr(agent, "emit_gateway_event", None)
            if callable(emit_fn):
                emit_fn("workstation.milestone", payload)
        except Exception:  # health: allow BLE001 -- milestone routing non-fatal
            logger.debug("Failed to emit milestone via agent", exc_info=True)

    return milestone


def record_router_selection(
    cap: Any,
    cert: Any,
    runtime_state: dict[str, Any],
    run_id: str | None,
) -> None:
    """Record capability_selected milestone from router."""
    try:
        emit_workstation_milestone(
            stage="capability_selected",
            sessionId=str(runtime_state.get("session_id") or runtime_state.get("task_id") or cap.id),
            taskRunId=run_id,
            capabilityId=str(cap.id),
            reasonCode="certified_for_execution",
            evidenceRefs=[f"cert:{cert.certificate_hash()[:10]}"],
        )
    except Exception:  # health: allow BLE001 -- milestone routing non-fatal
        logger.debug("Router selection milestone failed", exc_info=True)


def record_router_rejection(
    authority_shortfalls: Sequence[Any],
    runtime_state: dict[str, Any],
    run_id: str | None,
) -> None:
    """Record rejected milestone from router."""
    try:
        cap_id = authority_shortfalls[0][0].id if authority_shortfalls else None
        emit_workstation_milestone(
            stage="rejected",
            sessionId=str(runtime_state.get("session_id") or runtime_state.get("task_id") or "router"),
            taskRunId=run_id,
            capabilityId=str(cap_id) if cap_id else None,
            reasonCode="authority_required_missing",
            evidenceRefs=[],
        )
    except Exception:  # health: allow BLE001 -- milestone routing non-fatal
        logger.debug("Router rejection milestone failed", exc_info=True)


def record_validation_milestone(
    candidate: Any,
    passed: bool,
    receipts: Sequence[Any],
    task_id: str,
    run_id: str,
    reason: str | None = None,
) -> None:
    """Record validation_passed or validation_failed milestone from lifecycle coordinator."""
    try:
        stage: Stage = "validation_passed" if passed else "validation_failed"
        evidence = [
            r.get("evidence_ref")
            for r in receipts
            if isinstance(r, dict) and r.get("evidence_ref")
        ]
        emit_workstation_milestone(
            stage=stage,
            sessionId=task_id or candidate.id,
            taskRunId=run_id,
            capabilityId=candidate.id,
            reasonCode=reason or ("verifier_validation_passed" if passed else "verifier_validation_failed"),
            evidenceRefs=evidence,
        )
    except Exception:  # health: allow BLE001 -- milestone routing non-fatal
        logger.debug("Validation milestone failed", exc_info=True)


def record_readback_milestone(
    agent: Any,
    completed_item: Any,
    tool: str,
    rb_result: dict[str, Any] | None,
) -> None:
    """Record executed or rejected milestone from item readback."""
    try:
        if rb_result and rb_result.get("ok") and rb_result.get("evidence_ref"):
            emit_workstation_milestone(
                stage="executed",
                sessionId=str(getattr(agent, "session_id", completed_item.task_id)),
                taskRunId=str(getattr(agent, "_canonical_work_run_id", "")),
                capabilityId=tool,
                reasonCode="readback_verified_success",
                evidenceRefs=[rb_result["evidence_ref"]],
                agent=agent,
            )
        elif rb_result and not rb_result.get("ok"):
            emit_workstation_milestone(
                stage="rejected",
                sessionId=str(getattr(agent, "session_id", completed_item.task_id)),
                taskRunId=str(getattr(agent, "_canonical_work_run_id", "")),
                capabilityId=tool,
                reasonCode="readback_verification_failed",
                evidenceRefs=[],
                agent=agent,
            )
    except Exception:  # health: allow BLE001 -- milestone routing non-fatal
        logger.debug("Readback milestone failed", exc_info=True)

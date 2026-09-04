from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from workstation.contracts import ExecutionEvent, ExecutionEventKind, RiskLevel
from workstation.journal import ExecutionJournal
from workstation.perception import PerceptionView
from workstation.safety import SafetyDecision, classify_action


class DriftSeverity(str, Enum):
    NONE = "none"
    BENIGN = "benign"
    STRUCTURAL = "structural"
    BREAKING = "breaking"


class AdaptationAction(str, Enum):
    PROCEED = "proceed"
    RETRY_WITH_ADAPTED_TARGET = "retry_with_adapted_target"
    DISMISS_OVERLAY = "dismiss_overlay"
    RE_EXPLORE = "re_explore"
    REQUIRE_APPROVAL = "require_approval"
    HALT = "halt"


@dataclass(slots=True)
class DriftDiagnosis:
    severity: DriftSeverity
    expected_target: str
    actual_target: str | None = None
    confidence: float = 1.0
    reason: str = ""
    suggested_action: AdaptationAction = AdaptationAction.PROCEED
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity"] = self.severity.value
        data["suggested_action"] = self.suggested_action.value
        return data


class DriftGovernor:
    """V2 drift diagnosis and governed adaptation engine.

    Monitors browser execution against expected procedural steps, detects DOM
    mutations and structural drift, classifies severity, and governs whether
    automatic adaptation is safe or human approval is mandatory.
    """

    BREAKING_PATTERNS = frozenset({
        "captcha", "verify you are human", "access denied", "blocked",
        "cloudflare", "security check", "session expired", "403 forbidden", "404 not found"
    })

    OVERLAY_PATTERNS = frozenset({
        "cookie", "privacy policy", "consent", "we value your privacy",
        "accept all", "cookies", "notice", "newsletter"
    })

    def diagnose(
        self,
        expected_action: str,
        expected_target: str,
        perception: PerceptionView,
        expected_text: str = "",
    ) -> DriftDiagnosis:
        refs = perception.payload.get("refs", {})

        # Check for breaking page states first (bot guards, captchas, auth blocks)
        page_view_lower = perception.view.lower()
        for pattern in self.BREAKING_PATTERNS:
            if pattern in page_view_lower:
                return DriftDiagnosis(
                    severity=DriftSeverity.BREAKING,
                    expected_target=expected_target,
                    actual_target=None,
                    confidence=0.95,
                    reason=f"Breaking page condition detected: '{pattern}'",
                    suggested_action=AdaptationAction.REQUIRE_APPROVAL,
                    evidence={"trigger_pattern": pattern, "snapshot_id": perception.snapshot_id},
                )

        # 1. Exact ref match
        if expected_target in refs:
            actual = refs[expected_target]
            # Check if name/text matches
            if not expected_text or expected_text.lower() in str(actual.get("name", "")).lower():
                return DriftDiagnosis(
                    severity=DriftSeverity.NONE,
                    expected_target=expected_target,
                    actual_target=expected_target,
                    confidence=1.0,
                    reason="Exact target and content match",
                    suggested_action=AdaptationAction.PROCEED,
                )
            else:
                # Same ref, but label changed -> benign drift
                return DriftDiagnosis(
                    severity=DriftSeverity.BENIGN,
                    expected_target=expected_target,
                    actual_target=expected_target,
                    confidence=0.85,
                    reason=f"Target element exists but text shifted from '{expected_text}' to '{actual.get('name')}'",
                    suggested_action=AdaptationAction.PROCEED,
                    evidence={"actual": actual},
                )

        # 2. Ref not found: search by semantic label or role similarity
        best_candidate_ref: str | None = None
        best_similarity = 0.0

        for ref, data in refs.items():
            name = str(data.get("name", "")).lower()
            if expected_text and expected_text.lower() in name:
                sim = max(0.8, len(expected_text) / max(1, len(name)))
                if sim > best_similarity:
                    best_similarity = sim
                    best_candidate_ref = ref

        if best_candidate_ref and best_similarity >= 0.6:
            return DriftDiagnosis(
                severity=DriftSeverity.STRUCTURAL,
                expected_target=expected_target,
                actual_target=best_candidate_ref,
                confidence=best_similarity,
                reason=f"Original ref '{expected_target}' missing, but matching element found at ref '{best_candidate_ref}'",
                suggested_action=AdaptationAction.RETRY_WITH_ADAPTED_TARGET,
                evidence={"adapted_node": refs[best_candidate_ref]},
            )

        # 3. Check for blocking cookie consent or modal overlay (H-104 Red Team guard)
        has_overlay_keywords = any(p in page_view_lower for p in self.OVERLAY_PATTERNS)
        if has_overlay_keywords:
            for ref, data in refs.items():
                btn_name = str(data.get("name", "")).lower()
                btn_role = str(data.get("role", data.get("tag", ""))).lower()
                if btn_role in {"button", "link"} and any(w in btn_name for w in ["accept", "agree", "allow", "close", "dismiss", "got it", "i understand", "ok"]):
                    return DriftDiagnosis(
                        severity=DriftSeverity.BENIGN,
                        expected_target=expected_target,
                        actual_target=ref,
                        confidence=0.88,
                        reason=f"Cookie/privacy overlay detected blocking workflow; candidate dismiss button found at ref '{ref}' ('{data.get('name')}')",
                        suggested_action=AdaptationAction.DISMISS_OVERLAY,
                        evidence={"overlay_button": data},
                    )

        # 4. Not found anywhere
        return DriftDiagnosis(
            severity=DriftSeverity.STRUCTURAL,
            expected_target=expected_target,
            actual_target=None,
            confidence=0.4,
            reason=f"Target element '{expected_target}' ({expected_text}) not found in current perception view",
            suggested_action=AdaptationAction.RE_EXPLORE,
            evidence={"available_refs_count": len(refs)},
        )

    def govern(
        self,
        diagnosis: DriftDiagnosis,
        action: str,
        safety_decision: SafetyDecision | None = None,
    ) -> AdaptationAction:
        """Apply governance policy to decide the allowed execution path."""
        if safety_decision is None:
            safety_decision = classify_action(action)

        # High-risk or sensitive actions MUST NOT auto-adapt without explicit approval
        if safety_decision.approval_required or safety_decision.risk in {RiskLevel.HIGH, RiskLevel.CRITICAL}:
            if diagnosis.severity != DriftSeverity.NONE:
                return AdaptationAction.REQUIRE_APPROVAL

        if diagnosis.suggested_action == AdaptationAction.DISMISS_OVERLAY:
            return AdaptationAction.DISMISS_OVERLAY

        if diagnosis.severity == DriftSeverity.NONE:
            return AdaptationAction.PROCEED

        if diagnosis.severity == DriftSeverity.BENIGN:
            return AdaptationAction.PROCEED

        if diagnosis.severity == DriftSeverity.BREAKING:
            return AdaptationAction.REQUIRE_APPROVAL

        # Structural drift: allow retry if high confidence, else re-explore
        if diagnosis.severity == DriftSeverity.STRUCTURAL:
            if diagnosis.actual_target and diagnosis.confidence >= 0.75:
                return AdaptationAction.RETRY_WITH_ADAPTED_TARGET
            return AdaptationAction.RE_EXPLORE

        return AdaptationAction.HALT

    def record_drift(
        self,
        diagnosis: DriftDiagnosis,
        journal: ExecutionJournal,
        task_id: str,
        session_id: str,
    ) -> ExecutionEvent:
        """Emit a structured drift event into the ExecutionJournal."""
        event = ExecutionEvent(
            kind=ExecutionEventKind.RETRY if diagnosis.suggested_action == AdaptationAction.RETRY_WITH_ADAPTED_TARGET else ExecutionEventKind.ACTION,
            task_id=task_id,
            session_id=session_id,
            message=f"Drift [{diagnosis.severity.value}]: {diagnosis.reason} -> action {diagnosis.suggested_action.value}",
            risk=RiskLevel.MEDIUM if diagnosis.severity == DriftSeverity.STRUCTURAL else RiskLevel.LOW,
            metadata={"drift": diagnosis.to_dict()},
        )
        journal.append(event)
        return event

"""Experience to Skill Learning Loop infrastructure.

Captures anomalies and unexpected structures discovered during execution,
formats candidate lessons with raw evidence, and links them to regression
fixtures so skills evolve predictably and securely.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, UTC
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class CandidateLesson:
    lesson_id: str
    skill_name: str
    issue_description: str
    raw_evidence_ref: str
    regression_fixture: dict[str, Any]
    proposed_fix_description: str
    status: str = "candidate"  # candidate, verified, rejected, promoted
    source: str = "execution_anomaly"  # execution_anomaly, human_demonstration
    learning_session_id: Optional[str] = None
    question_context: Optional[dict[str, Any]] = None
    created_at: str = field(default_factory=_utc_now)
    promoted_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExperienceLessonCompiler:
    """Compiles execution experiences into candidate skill updates and regression fixtures."""

    def __init__(self, lessons_dir: Optional[Path] = None) -> None:
        if lessons_dir is not None:
            self.lessons_dir = Path(lessons_dir)
        else:
            self.lessons_dir = get_hermes_home() / "workstation" / "candidate_lessons"
        self.lessons_dir.mkdir(parents=True, exist_ok=True)

    def record_candidate_lesson(
        self,
        *,
        skill_name: str,
        issue_description: str,
        raw_evidence_ref: str,
        regression_fixture: dict[str, Any],
        proposed_fix_description: str,
    ) -> CandidateLesson:
        lesson_id = f"lesson_{uuid4().hex[:10]}"
        lesson = CandidateLesson(
            lesson_id=lesson_id,
            skill_name=skill_name,
            issue_description=issue_description,
            raw_evidence_ref=raw_evidence_ref,
            regression_fixture=regression_fixture,
            proposed_fix_description=proposed_fix_description,
        )

        path = self.lessons_dir / f"{lesson_id}.json"
        path.write_text(
            json.dumps(lesson.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("Recorded candidate lesson %s for skill %s", lesson_id, skill_name)
        return lesson

    def record_human_demonstration_candidate(
        self,
        *,
        skill_name: str,
        intent_description: str,
        learning_session_id: str,
        raw_evidence_ref: str,
        demonstration_summary: dict[str, Any],
        proposed_fix_description: str,
        question_context: Optional[dict[str, Any]] = None,
    ) -> CandidateLesson:
        """Record inert candidate lesson compiled from a human demonstration.

        Invariants (D-047 / HLM-MVP):
        - Source is explicitly 'human_demonstration'.
        - Status is 'candidate' (NEVER 'verified' or 'promoted').
        - NEVER treated as VERIFIED_SUCCESS.
        - Preserves raw evidence references and questions/corrections context.
        """
        # Idempotency check: if candidate already exists for this learning_session_id, return existing
        existing = self.find_candidate_by_learning_session(learning_session_id)
        if existing is not None:
            logger.info(
                "Idempotent reuse of candidate lesson %s for session %s",
                existing.lesson_id,
                learning_session_id,
            )
            return existing

        lesson_id = f"lesson_hd_{uuid4().hex[:10]}"
        lesson = CandidateLesson(
            lesson_id=lesson_id,
            skill_name=skill_name,
            issue_description=intent_description,
            raw_evidence_ref=raw_evidence_ref,
            regression_fixture=demonstration_summary,
            proposed_fix_description=proposed_fix_description,
            status="candidate",
            source="human_demonstration",
            learning_session_id=learning_session_id,
            question_context=question_context,
        )

        path = self.lessons_dir / f"{lesson_id}.json"
        path.write_text(
            json.dumps(lesson.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(
            "Recorded human demonstration candidate lesson %s for skill %s (session %s)",
            lesson_id,
            skill_name,
            learning_session_id,
        )
        try:
            from workstation.milestones import emit_workstation_milestone

            emit_workstation_milestone(
                stage="candidate",
                sessionId=learning_session_id,
                learningSessionId=learning_session_id,
                capabilityId=skill_name,
                reasonCode="demonstration_candidate_recorded",
                evidenceRefs=[f"lesson:{lesson_id}", raw_evidence_ref],
            )
        except Exception:
            logger.debug("Failed to emit milestone for candidate", exc_info=True)
        return lesson

    def find_candidate_by_learning_session(
        self, learning_session_id: str
    ) -> Optional[CandidateLesson]:
        """Find an existing candidate lesson created from a learning session ID."""
        if not learning_session_id:
            return None
        for lesson in self.list_candidate_lessons():
            if lesson.learning_session_id == learning_session_id:
                return lesson
        return None

    def compile_demonstration_session(
        self,
        session_dir: Path | str,
        *,
        skill_name: Optional[str] = None,
        intent_description: Optional[str] = None,
        proposed_fix_description: Optional[str] = None,
    ) -> CandidateLesson:
        """Compile a finalized learning session directory into an inert CandidateLesson.

        Idempotent: if a lesson for the session ID already exists, returns it.
        """
        dir_path = Path(session_dir)
        session_id = dir_path.name

        existing = self.find_candidate_by_learning_session(session_id)
        if existing is not None:
            return existing

        package_path = dir_path / "demonstration_package.json"
        manifest_path = dir_path / "learning_session.json"
        events_path = dir_path / "events.jsonl"
        questions_path = dir_path / "questions.jsonl"

        pkg_data: dict[str, Any] = {}
        if package_path.exists():
            try:
                pkg_data = json.loads(package_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pkg_data = {}

        manifest_data: dict[str, Any] = {}
        if manifest_path.exists():
            try:
                manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                manifest_data = {}

        actual_session_id = pkg_data.get("sessionId") or manifest_data.get("sessionId") or session_id
        corrections = pkg_data.get("humanCorrections", [])
        segments = pkg_data.get("segments", [])

        # Formulate intent description prioritizing human causal corrections
        intent = intent_description
        if not intent:
            c_texts = [c.get("userResponse", "") for c in corrections if c.get("userResponse")]
            if c_texts:
                intent = f"Demonstração humana com correções causais: {'; '.join(c_texts)[:240]}"
            else:
                intent = f"Demonstração humana na sessão {actual_session_id}"

        target_skill = skill_name or manifest_data.get("allowlistedOrigin") or "human_demonstration_workflow"
        fix_desc = proposed_fix_description or (
            "Incorporar sequência de ferramentas e alternativas comprovadas pelo operador "
            "com validação supervisionada."
        )

        summary = {
            "segments": segments,
            "events_count": pkg_data.get("eventsCount", manifest_data.get("eventsCount", 0)),
            "questions_count": pkg_data.get("questionsCount", manifest_data.get("questionsCount", 0)),
            "human_corrections": corrections,
            "evidence_refs": {
                "events_path": str(events_path.resolve()) if events_path.exists() else None,
                "questions_path": str(questions_path.resolve()) if questions_path.exists() else None,
                "session_dir": str(dir_path.resolve()),
            },
            "limitations": [
                "Demonstração humana em observação. Não validada em tempo de execução.",
                "Proibida promoção automática ou atribuição de status VERIFIED_SUCCESS.",
            ],
        }

        raw_ref = str(events_path.resolve()) if events_path.exists() else str(dir_path.resolve())

        try:
            from workstation.milestones import emit_workstation_milestone

            emit_workstation_milestone(
                stage="compilation_started",
                sessionId=pkg_data.get("storedSessionId") or manifest_data.get("storedSessionId") or actual_session_id,
                learningSessionId=actual_session_id,
                capabilityId=target_skill,
                reasonCode="demonstration_package_compiling",
                evidenceRefs=[f"dir:{dir_path.name}"],
            )
        except Exception:
            logger.debug("Failed to emit milestone for compilation_started", exc_info=True)

        return self.record_human_demonstration_candidate(
            skill_name=target_skill,
            intent_description=intent,
            learning_session_id=actual_session_id,
            raw_evidence_ref=raw_ref,
            demonstration_summary=summary,
            proposed_fix_description=fix_desc,
            question_context={"human_corrections": corrections, "questions_count": len(corrections)},
        )

    def list_candidate_lessons(
        self, skill_name: Optional[str] = None
    ) -> list[CandidateLesson]:
        lessons: list[CandidateLesson] = []
        for file in self.lessons_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                if skill_name is None or data.get("skill_name") == skill_name:
                    lessons.append(CandidateLesson(**data))
            except Exception:
                continue
        return lessons

    def synthesize_operational_proposal(
        self, lesson: CandidateLesson
    ) -> "OperationalCapability":
        """Synthesize an inert OperationalCapability draft from a CandidateLesson.

        Invariants (D-047 / HLM-MVP):
        - Lifecycle is ALWAYS DISCOVERED; never VALIDATED or PROMOTED.
        - Verifier contract and validation evidence are empty (inert proposal).
        - No TaskRun, WorkPlan or TransitionSample is created.
        - Provenance preserves learning_session_id and lesson_id for traceability.
        - Human corrections and unresolved limitations are preserved verbatim.
        """
        from workstation.operational_capabilities import (
            CapabilityLifecycle,
            OperationalCapability,
            OperationalCapabilityRegistry,
        )

        fixture = lesson.regression_fixture or {}
        segments = fixture.get("segments", []) if isinstance(fixture, dict) else []
        human_corrections = (
            fixture.get("human_corrections", []) if isinstance(fixture, dict) else []
        )
        limitations = fixture.get("limitations", []) if isinstance(fixture, dict) else []

        # Map segments to operational kernel primitives where possible.
        _SEGMENT_PRIMITIVE_MAP = {
            "tool_selection": "browser_click",
            "canvas_operation": "browser_click",
            "parameter_adjustment": "browser_type",
            "typography_adjustment": "browser_type",
            "asset_import": "navigate",
            "document_setup": "navigate",
        }
        steps: list[dict[str, Any]] = []
        manual_review_segments: list[str] = []
        for idx, segment in enumerate(segments):
            kind = segment.get("kind", "generic") if isinstance(segment, dict) else "generic"
            primitive = _SEGMENT_PRIMITIVE_MAP.get(kind)
            step_id = segment.get("id", f"step-{idx}") if isinstance(segment, dict) else f"step-{idx}"
            if primitive is None:
                manual_review_segments.append(step_id)
                steps.append(
                    {
                        "id": str(step_id),
                        "primitive": "manual_review_required",
                        "args": {"segment_kind": kind},
                    }
                )
            else:
                steps.append(
                    {
                        "id": str(step_id),
                        "primitive": primitive,
                        "args": {"segment_kind": kind},
                    }
                )

        cap_id = f"proposal_{lesson.lesson_id}"
        proposal = OperationalCapability(
            id=cap_id,
            name=lesson.issue_description or lesson.skill_name,
            version="0.1.0",
            effect="state_mutation",
            route="native_browser",
            preconditions=[],
            postconditions=[],
            verifier_contract={},
            dependencies=[],
            implementation={"type": "demonstration_proposal", "steps": steps},
            lifecycle=CapabilityLifecycle.DISCOVERED,
            provenance={
                "source": "human_demonstration_proposal",
                "learning_session_id": lesson.learning_session_id,
                "lesson_id": lesson.lesson_id,
                "raw_evidence_ref": lesson.raw_evidence_ref,
            },
            learning_metadata={
                "proposed_fix_description": lesson.proposed_fix_description,
                "human_corrections": list(human_corrections),
                "unresolved_uncertainties": list(limitations),
                "manual_review_required_steps": manual_review_segments,
                "segments_count": len(segments),
            },
            validation_evidence=[],
        )

        registry = OperationalCapabilityRegistry()
        existing = registry.get(cap_id, version="0.1.0")
        if existing is not None:
            return existing
        return registry.register(proposal, if_absent=True)

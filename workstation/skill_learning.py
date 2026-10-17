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
        return lesson

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

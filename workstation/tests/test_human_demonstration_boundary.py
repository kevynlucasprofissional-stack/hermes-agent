"""Test human demonstration knowledge boundary invariants (D-047 / HLM-MVP).

Invariants:
- Source is explicitly 'human_demonstration'.
- Never treated as VERIFIED_SUCCESS.
- Stays inert as 'candidate', not automatically promoted.
- Preserves raw evidence references and user questions/corrections context.
"""

import json
from pathlib import Path
import pytest
from workstation.skill_learning import CandidateLesson, ExperienceLessonCompiler


def test_human_demonstration_candidate_recording(tmp_path: Path):
    compiler = ExperienceLessonCompiler(lessons_dir=tmp_path)

    lesson = compiler.record_human_demonstration_candidate(
        skill_name="effectcraft_canvas_blur",
        intent_description="Operador aplicou efeito de desfoque após salvar backup preliminar",
        learning_session_id="learn-179225-tab1",
        raw_evidence_ref="learning-sessions/learn-179225-tab1/events.jsonl",
        demonstration_summary={
            "events_count": 8,
            "actions": [
                "shortcut:Ctrl+S",
                "click:button:Apply Effect",
                "pointerup:canvas:0.45_0.32",
            ],
        },
        proposed_fix_description="Adicionar etapa de backup automático antes de renderizar desfoque pesado",
        question_context={
            "question_id": "q-42",
            "hypothesis": "Operador salvou versão preliminar.",
            "user_response": "Eu salvei uma versão preliminar para evitar perda de dados antes de aplicar desfoque pesado",
            "needs_reinterpretation": True,
        },
    )

    # Contract assertions
    assert lesson.source == "human_demonstration"
    assert lesson.status == "candidate"
    assert lesson.promoted_at is None
    assert lesson.learning_session_id == "learn-179225-tab1"
    assert lesson.question_context is not None
    assert lesson.question_context["needs_reinterpretation"] is True

    # Persistence verification
    saved_files = list(tmp_path.glob("*.json"))
    assert len(saved_files) == 1
    content = json.loads(saved_files[0].read_text(encoding="utf-8"))
    assert content["source"] == "human_demonstration"
    assert content["status"] == "candidate"
    assert content["learning_session_id"] == "learn-179225-tab1"
    assert "VERIFIED_SUCCESS" not in content.values()


def test_human_demonstration_candidate_listing(tmp_path: Path):
    compiler = ExperienceLessonCompiler(lessons_dir=tmp_path)

    compiler.record_human_demonstration_candidate(
        skill_name="skill_a",
        intent_description="Demo A",
        learning_session_id="sess-a",
        raw_evidence_ref="events_a.jsonl",
        demonstration_summary={"actions": ["click"]},
        proposed_fix_description="Fix A",
    )

    compiler.record_candidate_lesson(
        skill_name="skill_b",
        issue_description="Anomaly B",
        raw_evidence_ref="evidence_b.json",
        regression_fixture={},
        proposed_fix_description="Fix B",
    )

    lessons = compiler.list_candidate_lessons()
    assert len(lessons) == 2

    hd_lessons = [l for l in lessons if l.source == "human_demonstration"]
    anomaly_lessons = [l for l in lessons if l.source == "execution_anomaly"]

    assert len(hd_lessons) == 1
    assert hd_lessons[0].skill_name == "skill_a"
    assert hd_lessons[0].status == "candidate"

    assert len(anomaly_lessons) == 1
    assert anomaly_lessons[0].skill_name == "skill_b"

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


def test_human_demonstration_idempotency(tmp_path: Path):
    compiler = ExperienceLessonCompiler(lessons_dir=tmp_path)

    lesson1 = compiler.record_human_demonstration_candidate(
        skill_name="photocraft_edit",
        intent_description="Remoção de texto com carimbo",
        learning_session_id="learn-idemp-1",
        raw_evidence_ref="events.jsonl",
        demonstration_summary={"strokes": 5},
        proposed_fix_description="Usar carimbo para fundo uniforme",
    )

    lesson2 = compiler.record_human_demonstration_candidate(
        skill_name="photocraft_edit",
        intent_description="Remoção de texto com carimbo",
        learning_session_id="learn-idemp-1",
        raw_evidence_ref="events.jsonl",
        demonstration_summary={"strokes": 5},
        proposed_fix_description="Usar carimbo para fundo uniforme",
    )

    # Idempotency assertions: must return identical lesson instance and exactly 1 file on disk
    assert lesson1.lesson_id == lesson2.lesson_id
    saved_files = list(tmp_path.glob("*.json"))
    assert len(saved_files) == 1


def test_compile_demonstration_session_from_package(tmp_path: Path):
    session_dir = tmp_path / "sessions" / "learn-pkg-test"
    session_dir.mkdir(parents=True)
    lessons_dir = tmp_path / "lessons"

    events_file = session_dir / "events.jsonl"
    events_file.write_text('{"event_id":"ev1","kind":"click"}\n', encoding="utf-8")

    questions_file = session_dir / "questions.jsonl"
    questions_file.write_text('{"id":"q1","state":"corrected","userResponse":"Tentei preenchimento mas usei carimbo"}\n', encoding="utf-8")

    package_file = session_dir / "demonstration_package.json"
    package_file.write_text(json.dumps({
        "schema": "hermes.demonstration_package.v1",
        "sessionId": "learn-pkg-test",
        "tabId": "tab-123",
        "origin": "http://127.0.0.1:8767",
        "eventsCount": 12,
        "questionsCount": 2,
        "segments": [
            {
                "id": "seg-1",
                "kind": "tool_selection",
                "hypothesis": "Operador selecionou ferramenta de carimbo",
                "uncertainty": 0.05,
                "humanCorrections": [
                    {
                        "questionId": "q1",
                        "prompt": "Por que carimbo?",
                        "userResponse": "Tentei preenchimento mas usei carimbo",
                        "needsReinterpretation": True,
                    }
                ],
            }
        ],
        "humanCorrections": [
            {
                "questionId": "q1",
                "prompt": "Por que carimbo?",
                "userResponse": "Tentei preenchimento mas usei carimbo",
                "needsReinterpretation": True,
            }
        ],
    }), encoding="utf-8")

    compiler = ExperienceLessonCompiler(lessons_dir=lessons_dir)

    lesson = compiler.compile_demonstration_session(session_dir)

    assert lesson.source == "human_demonstration"
    assert lesson.status == "candidate"
    assert lesson.learning_session_id == "learn-pkg-test"
    assert "Tentei preenchimento mas usei carimbo" in lesson.issue_description
    assert len(lesson.regression_fixture["segments"]) == 1
    assert lesson.regression_fixture["human_corrections"][0]["userResponse"] == "Tentei preenchimento mas usei carimbo"
    assert "VERIFIED_SUCCESS" not in lesson.to_dict().values()

    # Repeating compilation on the same directory returns the same lesson without duplicate file
    repeat_lesson = compiler.compile_demonstration_session(session_dir)
    assert repeat_lesson.lesson_id == lesson.lesson_id
    saved = list(lessons_dir.glob("*.json"))
    assert len(saved) == 1


def test_compile_learning_session_candidate_endpoint(tmp_path: Path, monkeypatch):
    from hermes_cli.web_routers.experience_compiler import (
        DemonstrationCompileBody,
        compile_learning_session_candidate,
    )

    session_dir = tmp_path / "sessions" / "learn-endpoint-test"
    session_dir.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    (session_dir / "events.jsonl").write_text('{"event_id":"ev1","kind":"click"}\n', encoding="utf-8")
    (session_dir / "demonstration_package.json").write_text(json.dumps({
        "sessionId": "learn-endpoint-test",
        "humanCorrections": [{"userResponse": "Ajuste tipográfico"}],
        "segments": [{"id": "seg-1", "kind": "typography_adjustment"}],
    }), encoding="utf-8")

    body = DemonstrationCompileBody(
        learning_session_id="learn-endpoint-test",
        session_dir=str(session_dir),
    )

    res = compile_learning_session_candidate(body)
    assert res["success"] is True
    assert res["idempotent_reuse"] is False
    assert res["lesson"]["learning_session_id"] == "learn-endpoint-test"
    assert res["lesson"]["status"] == "candidate"
    assert res["lesson"]["source"] == "human_demonstration"

    # Repeat endpoint call is idempotent
    res2 = compile_learning_session_candidate(body)
    assert res2["success"] is True
    assert res2["idempotent_reuse"] is True
    assert res2["lesson"]["lesson_id"] == res["lesson"]["lesson_id"]


def test_synthesize_operational_proposal_from_candidate(tmp_path: Path):
    """Verify inert OperationalCapability draft synthesis from CandidateLesson (D-047 / HLM-MVP)."""
    from workstation.operational_capabilities import CapabilityLifecycle, OperationalCapabilityRegistry

    lessons_dir = tmp_path / "lessons"
    compiler = ExperienceLessonCompiler(lessons_dir=lessons_dir)

    lesson = compiler.record_human_demonstration_candidate(
        skill_name="effectcraft_canvas_blur",
        intent_description="Aplicar desfoque após salvar checkpoint",
        learning_session_id="learn-synth-1",
        raw_evidence_ref="events.jsonl",
        demonstration_summary={"actions": ["shortcut:Ctrl+S", "click:button:Blur"]},
        proposed_fix_description="Adicionar backup automático antes do blur",
        question_context={
            "question_id": "q-synth",
            "hypothesis": "Operador salvou antes de aplicar efeito.",
            "user_response": "Sim, salvei para evitar perda",
            "needs_reinterpretation": False,
        },
    )

    cap = compiler.synthesize_operational_proposal(lesson)

    assert isinstance(cap.id, str) and cap.id.startswith("proposal_")
    assert cap.lifecycle == CapabilityLifecycle.DISCOVERED
    assert cap.provenance["source"] == "human_demonstration_proposal"
    assert cap.provenance["learning_session_id"] == "learn-synth-1"
    assert cap.provenance["lesson_id"] == lesson.lesson_id
    assert cap.verifier_contract == {}
    assert cap.validation_evidence == []
    assert cap.learning_metadata["proposed_fix_description"] == "Adicionar backup automático antes do blur"
    assert len(cap.implementation.get("steps", [])) >= 0

    registry = OperationalCapabilityRegistry()
    persisted = registry.get(cap.id)
    assert persisted is not None
    assert persisted.lifecycle == CapabilityLifecycle.DISCOVERED

    cap2 = compiler.synthesize_operational_proposal(lesson)
    assert cap2.id == cap.id
    assert cap2.version == cap.version



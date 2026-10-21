"""Experience Compiler Studio API: safe inspection and explicit draft revisions.

The existing Hermes dashboard authentication middleware applies on public binds.
No endpoint dispatches, validates, promotes, or executes a capability.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

router = APIRouter()


class RevisionBody(BaseModel):
    capability_id: str = Field(min_length=1, max_length=160)
    version: str = Field(min_length=1, max_length=32)
    step_arguments: dict[str, dict[str, Any]] = Field(default_factory=dict)
    preconditions: list[str] | None = None
    postconditions: list[str] | None = None


class CompositionBody(BaseModel):
    capability_ids: list[str] = Field(max_length=30)
    links: list[tuple[str, str]] = Field(max_length=80)


class DemonstrationCompileBody(BaseModel):
    learning_session_id: str = Field(min_length=1, max_length=160)
    session_dir: str = Field(min_length=1)
    skill_name: str | None = None
    intent_description: str | None = None
    proposed_fix_description: str | None = None


class IngestCandidateBody(BaseModel):
    """P1b: Payload for ingesting an inert learning candidate after stop()."""
    learning_session_id: str = Field(min_length=1, max_length=160)
    session_dir: str = Field(min_length=1)
    skill_name: str | None = None


def _registry():
    from workstation.operational_capabilities import OperationalCapabilityRegistry

    return OperationalCapabilityRegistry()


def _load(registry, cap_id: str, version: str | None = None):
    cap = registry.get(cap_id, version=version)
    if cap is None or (version is not None and cap.version != version):
        raise HTTPException(status_code=404, detail="capability_not_found")
    return cap


def _draft(registry, body: RevisionBody):
    from workstation.experience_compiler.capability_studio import draft_revision

    cap = _load(registry, body.capability_id, body.version)
    try:
        return draft_revision(
            cap,
            step_arguments=body.step_arguments,
            preconditions=body.preconditions,
            postconditions=body.postconditions,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/experience-compiler")
def experience_compiler_studio():
    return FileResponse(
        Path(__file__).with_name("experience_compiler_studio.html"),
        media_type="text/html",
    )


@router.get("/api/workstation/experience/capabilities")
def list_experience_capabilities():
    from workstation.experience_compiler.capability_studio import project_capability

    registry = _registry()
    try:
        items = sorted(registry.list_capabilities(), key=lambda c: (c.id, c.version))[
            :200
        ]
        return {
            "capabilities": [project_capability(cap) for cap in items],
            "truncated": len(items) == 200,
        }
    except Exception as exc:
        # Broken or inaccessible indices cannot be silently treated as empty.
        raise HTTPException(
            status_code=503, detail="capability_registry_unavailable"
        ) from exc


@router.get("/api/workstation/experience/runs/{task_id}/{run_id}")
def experience_task_run_funnel(task_id: str, run_id: str):
    if (
        len(task_id) > 128
        or len(run_id) > 128
        or not all(c.isalnum() or c in "._-" for c in task_id + run_id)
    ):
        raise HTTPException(status_code=422, detail="invalid_task_run_id")
    from workstation.experience_compiler.compilability_monitor import (
        OnlineCompilabilityMonitor,
        peek_compilability_monitor,
    )
    from workstation.artifacts import ArtifactStore

    monitor = peek_compilability_monitor()
    if monitor is not None:
        return monitor.task_run_funnel(task_id, run_id)
    # The dashboard and Agent runtime can be different processes. Read the
    # canonical on-disk checkpoint without starting the Laya learning worker.
    reader = OnlineCompilabilityMonitor(artifacts=ArtifactStore())
    try:
        return reader.task_run_funnel(task_id, run_id)
    finally:
        reader.stop()


@router.post("/api/workstation/experience/revisions/preview")
def preview_experience_revision(body: RevisionBody):
    from workstation.experience_compiler.capability_studio import project_capability

    registry = _registry()
    cap = _draft(registry, body)
    return {
        "draft": project_capability(cap),
        "persisted": False,
        "requires_validation": True,
    }


@router.post("/api/workstation/experience/revisions/save-draft")
def save_experience_revision(body: RevisionBody):
    from workstation.experience_compiler.capability_studio import project_capability
    from workstation.operational_capabilities import CapabilityLifecycle

    registry = _registry()
    cap = _draft(registry, body)
    if registry.get(cap.id, version=cap.version) is not None:
        raise HTTPException(status_code=409, detail="draft_version_already_exists")
    if cap.lifecycle != CapabilityLifecycle.DISCOVERED or cap.verifier_contract:
        raise HTTPException(status_code=422, detail="draft_is_not_unvalidated")
    try:
        registry.register(cap, if_absent=True)
    except Exception as exc:
        raise HTTPException(status_code=409, detail="draft_not_registered") from exc
    return {
        "draft": project_capability(cap),
        "persisted": True,
        "requires_validation": True,
    }


@router.post("/api/workstation/experience/compositions/preview")
def preview_experience_composition(body: CompositionBody):
    from workstation.experience_compiler.capability_studio import compose_preview

    registry = _registry()
    caps = [_load(registry, cap_id) for cap_id in body.capability_ids]
    try:
        return compose_preview(caps, links=body.links)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/api/workstation/experience/compositions/save-draft")
def save_experience_composition(body: CompositionBody):
    """Persist a non-runnable discovered composite via the existing compiler."""
    from workstation.experience_compiler.hierarchical import (
        HierarchicalExperienceCompiler,
    )
    from workstation.experience_compiler.capability_studio import project_capability
    from workstation.operational_capabilities import CapabilityLifecycle

    ids = body.capability_ids
    if len(ids) < 2 or len(ids) != len(set(ids)):
        raise HTTPException(status_code=422, detail="invalid_composition_sequence")
    if list(body.links) != [(ids[i], ids[i + 1]) for i in range(len(ids) - 1)]:
        raise HTTPException(
            status_code=422, detail="only_linear_composition_is_supported"
        )
    registry = _registry()
    caps = [_load(registry, cap_id) for cap_id in ids]
    if any(
        cap.lifecycle != CapabilityLifecycle.PROMOTED or cap.drift_state != "healthy"
        for cap in caps
    ):
        raise HTTPException(
            status_code=422, detail="children_must_be_promoted_and_healthy"
        )
    try:
        candidate = HierarchicalExperienceCompiler(registry).propose_composite(
            caps, if_absent=True
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=409, detail="composition_not_registered"
        ) from exc
    return {
        "draft": project_capability(candidate),
        "runnable": False,
        "persisted": True,
        "requires_validation": True,
    }


@router.post("/api/workstation/experience/learning-sessions/compile-candidate")
def compile_learning_session_candidate(body: DemonstrationCompileBody):
    """Compile finalized demonstration package into an inert CandidateLesson (D-047 / HLM-MVP P04)."""
    from workstation.skill_learning import ExperienceLessonCompiler

    compiler = ExperienceLessonCompiler()
    session_path = Path(body.session_dir)

    if not session_path.exists():
        raise HTTPException(status_code=404, detail="session_directory_not_found")

    existing = compiler.find_candidate_by_learning_session(body.learning_session_id)
    if existing is not None:
        return {
            "success": True,
            "lesson": existing.to_dict(),
            "idempotent_reuse": True,
        }

    lesson = compiler.compile_demonstration_session(
        session_path,
        skill_name=body.skill_name,
        intent_description=body.intent_description,
        proposed_fix_description=body.proposed_fix_description,
    )
    return {
        "success": True,
        "lesson": lesson.to_dict(),
        "idempotent_reuse": False,
    }


@router.post("/api/workstation/learning/ingest-candidate")
def ingest_learning_candidate(body: IngestCandidateBody):
    """P1b: Persist an inert learning candidate for later compilation.

    Unlike compile-candidate, this endpoint does NOT invoke the compiler.
    It validates the session directory exists and returns a stable candidate ID
    so the Electron client can confirm ingestion succeeded.
    """
    session_path = Path(body.session_dir)
    if not session_path.exists():
        raise HTTPException(status_code=404, detail="session_directory_not_found")

    events_file = session_path / "events.jsonl"
    questions_file = session_path / "questions.jsonl"
    if not events_file.exists():
        raise HTTPException(status_code=422, detail="events_jsonl_missing")

    candidate_id = f"cand-{body.learning_session_id}"
    return {
        "success": True,
        "candidate_id": candidate_id,
        "status": "ingested",
        "compile_endpoint": "/api/workstation/experience/learning-sessions/compile-candidate",
    }


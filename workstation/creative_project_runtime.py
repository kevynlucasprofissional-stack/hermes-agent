"""Creative project operations admitted by existing session and Kanban owners."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import time
from uuid import uuid4

from gateway.session_context import get_session_env
from hermes_constants import hermes_home_key
from hermes_cli import kanban_db
from hermes_cli.kanban_db_connect import connect_closing
from tools.approval_context import get_current_session_key
from workstation.artifacts import ArtifactStore
from workstation.authority_supersession import classify_run_authority
from workstation.config import WorkstationConfig
from workstation.contracts import ExecutionEventKind
from workstation.creative_project_store import (
    CreativeProjectRevision, creative_source_bytes, load_creative_revision, save_creative_revision,
)
from workstation.journal import ExecutionJournal
from workstation.policy import ActionScope, PolicyDecision, ScopedPolicyEngine


class CreativeEffectUncertain(RuntimeError):
    """An admitted operation may have changed its owner; never blindly retry it."""

    def __init__(self, operation_id: str):
        super().__init__("Creative effect requires owner reconciliation")
        self.operation_id = operation_id


@dataclass(frozen=True)
class CreativeRunContext:
    profile_home: str
    session_key: str
    session_id: str
    task_id: str
    run_id: int

    def validate(self, config: WorkstationConfig) -> Path:
        if not config.creative_enabled:
            raise PermissionError("Creative runtime is disabled")
        if hermes_home_key(self.profile_home) != hermes_home_key():
            raise PermissionError("Creative profile mismatch")
        if (not self.session_key or self.session_key != get_current_session_key(default="")
                or not self.session_id or self.session_id != get_session_env("HERMES_SESSION_ID", "")):
            raise PermissionError("Creative session mismatch")
        if not self.task_id or type(self.run_id) is not int or self.run_id < 1:
            raise PermissionError("Creative TaskRun identity required")
        db_path = kanban_db.kanban_db_path()
        if not db_path.resolve().is_relative_to(Path(self.profile_home).resolve()):
            raise PermissionError("Creative task database is outside the owning profile")
        if not db_path.is_file():
            raise PermissionError("Creative canonical task database is missing")
        with connect_closing(db_path) as connection:
            task = kanban_db.get_task(connection, self.task_id)
            termination = classify_run_authority(task, str(self.run_id), connection=connection)
            if termination is not None:
                raise PermissionError(f"Creative TaskRun fenced: {termination.termination_kind.value}")
            run = kanban_db.get_run(connection, self.run_id)
            if (task.status != "running" or task.session_id != self.session_id
                    or run.status != "running" or run.ended_at is not None
                    or not task.claim_lock or task.claim_lock != run.claim_lock
                    or not task.claim_expires or task.claim_expires <= time.time()
                    or not run.claim_expires or run.claim_expires <= time.time()):
                raise PermissionError("Creative TaskRun is not live in the owning session")
            if not task.workspace_path:
                raise PermissionError("Creative TaskRun workspace required")
            workspace = Path(task.workspace_path).resolve(strict=True)
        creative_root = Path(self.profile_home).resolve() / "workstation" / "creative"
        if not workspace.is_dir() or workspace == creative_root or not workspace.is_relative_to(creative_root):
            raise PermissionError("Creative TaskRun workspace escaped the owning profile")
        return workspace


def save_project_for_run(
    config: WorkstationConfig, context: CreativeRunContext, source: dict, *,
    project_id: str | None = None, parent_revision: str | None = None, engine: str = "electron-svg",
) -> dict:
    workspace = context.validate(config)
    creative_source_bytes(source)
    if engine not in {"electron-svg", "remotion"}:
        raise ValueError("Unsupported Creative project engine")
    if (project_id is None) != (parent_revision is None):
        raise ValueError("Existing projects require an explicit parent revision")
    native_files = None
    if engine == "remotion":
        from workstation.creative_remotion_source import RemotionInvitation, remotion_native_files
        RemotionInvitation.from_source(source)
        native_files = remotion_native_files()
    # The canonical task workspace must include the destination, not merely share
    # the same profile. This preserves filesystem policy for concurrent projects.
    destination = Path(context.profile_home).resolve() / "workstation" / "creative" / "projects"
    if project_id is not None:
        parent = load_creative_revision(project_id, parent_revision)
        if parent.engine != engine:
            raise ValueError("Creative project engine cannot change within a revision lineage")
        destination = parent.manifest_path.parent.parent.parent
    evaluation = ScopedPolicyEngine().evaluate(ActionScope(
        task_id=context.task_id, session_id=context.session_id, capability="filesystem",
        action_name="write", target=str(destination), workspace_root=str(workspace),
    ))
    if evaluation.decision is not PolicyDecision.ALLOW:
        raise PermissionError(f"Creative project policy: {evaluation.decision.value}")
    context.validate(config)
    operation_id = uuid4().hex
    journal = ExecutionJournal(task_id=context.task_id, session_id=context.session_id)
    journal.record(ExecutionEventKind.ACTION, "Creative source revision prepared",
                   metadata={"operation_id": operation_id, "run_id": context.run_id})
    try:
        revision = save_creative_revision(source, project_id=project_id, parent_revision=parent_revision,
                                         operation_id=operation_id, engine=engine, native_files=native_files)
        return publish_project_revision(config, context, revision, operation_id=operation_id)
    except Exception as error:
        raise CreativeEffectUncertain(operation_id) from error


def publish_project_revision(config: WorkstationConfig, context: CreativeRunContext,
                             revision: CreativeProjectRevision, *, operation_id: str) -> dict:
    workspace = context.validate(config)
    current = load_creative_revision(revision.project_id, revision.revision_id)
    if not current.source_path.is_relative_to(workspace):
        raise PermissionError("Creative revision is outside the TaskRun workspace")
    if current != revision or current.operation_id != operation_id:
        raise ValueError("Creative project revision changed before publication")
    source_bytes = current.source_path.read_bytes()
    manifest_bytes = current.manifest_path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != current.source_sha256:
        raise ValueError("Creative source changed before publication")
    store = ArtifactStore()
    source = store.store(context.task_id, f"creative-source-{operation_id}.json",
                         source_bytes, media_type="application/json")
    manifest = store.store(context.task_id, f"creative-manifest-{operation_id}.json",
                           manifest_bytes, media_type="application/json",
                           schema="creative.project-revision.v1")
    native_artifacts = {}
    for name, digest in current.native_files:
        native_data = (current.source_path.parent / name).read_bytes()
        if hashlib.sha256(native_data).hexdigest() != digest:
            raise ValueError("Creative native source changed before publication")
        native_artifacts[name] = store.store(context.task_id, f"creative-native-{operation_id}-{name}",
                                             native_data, media_type="text/plain").to_dict()
    context.validate(config)
    receipt = {"project_id": revision.project_id, "revision_id": revision.revision_id,
               "engine": revision.engine,
               "parent_revision": revision.parent_revision, "source_sha256": revision.source_sha256,
               "source_artifact": source.to_dict(), "manifest_artifact": manifest.to_dict(),
               "native_artifacts": native_artifacts,
               "task_id": context.task_id, "run_id": context.run_id,
               "session_id": context.session_id, "operation_id": operation_id}
    ExecutionJournal(task_id=context.task_id, session_id=context.session_id).record(
        ExecutionEventKind.DELIVERABLE, "Creative source revision persisted", metadata=receipt)
    return receipt

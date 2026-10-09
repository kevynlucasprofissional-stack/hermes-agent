from dataclasses import replace

import pytest

from gateway.session_context import scoped_current_session_id
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from hermes_cli import kanban_db
from hermes_cli.kanban_db_connect import connect_closing
from tools.approval_context import reset_current_session_key, set_current_session_key
from workstation.artifacts import ArtifactStore
from workstation.config import WorkstationConfig
from workstation.creative_project_runtime import CreativeRunContext, save_project_for_run
from workstation.journal import ExecutionJournal


def _task(home):
    workspace = home / "workstation" / "creative" / "projects"
    workspace.mkdir(parents=True)
    with connect_closing() as connection:
        task_id = kanban_db.create_task(connection, title="Creative invitation", session_id="durable-session",
                                       workspace_kind="dir", workspace_path=str(workspace))
        task = kanban_db.claim_task(connection, task_id, ttl_seconds=300)
    assert task is not None
    return CreativeRunContext(str(home), "approval-key", "durable-session", task_id, task.current_run_id)


def test_real_task_run_persists_source_artifacts_and_correct_session_journal(tmp_path, monkeypatch):
    home = tmp_path / "a"
    monkeypatch.setenv("HERMES_KANBAN_DB", str(home / "kanban.db"))
    home_token = set_hermes_home_override(home)
    session_token = set_current_session_key("approval-key")
    try:
        with scoped_current_session_id("durable-session"):
            context = _task(home)
            config = WorkstationConfig({"creative": {"enabled": True}})
            first = save_project_for_run(config, context, {"title": "invitation"})
            second = save_project_for_run(config, context, {"title": "variation"},
                                          project_id=first["project_id"], parent_revision=first["revision_id"])
            assert second["parent_revision"] == first["revision_id"]
            assert second["source_sha256"] != first["source_sha256"]
            resolved = ArtifactStore().resolve_structured(first["source_artifact"]["ref"])
            assert resolved["sha256"] == first["source_sha256"]
            events = ExecutionJournal(task_id=context.task_id, session_id="durable-session").read_events()
            assert all(event.session_id == "durable-session" for event in events)
            assert events[-1].metadata["run_id"] == context.run_id
            assert events[-1].metadata["operation_id"] == second["operation_id"]
    finally:
        reset_current_session_key(session_token)
        reset_hermes_home_override(home_token)


def test_disabled_wrong_session_profile_stale_and_terminal_runs_refuse_before_project_io(tmp_path, monkeypatch):
    home = tmp_path / "a"
    monkeypatch.setenv("HERMES_KANBAN_DB", str(home / "kanban.db"))
    home_token = set_hermes_home_override(home)
    session_token = set_current_session_key("approval-key")
    try:
        with scoped_current_session_id("durable-session"):
            context = _task(home)
            config = WorkstationConfig({"creative": {"enabled": True}})
            for rejected, settings in ((context, WorkstationConfig({})),
                                       (replace(context, session_id="approval-key"), config),
                                       (replace(context, run_id=context.run_id + 1), config)):
                with pytest.raises(PermissionError):
                    save_project_for_run(settings, rejected, {"title": "must not save"})
            token_b = set_hermes_home_override(tmp_path / "b")
            try:
                with pytest.raises(PermissionError, match="profile"):
                    save_project_for_run(config, context, {})
                assert not (tmp_path / "b").exists()
            finally:
                reset_hermes_home_override(token_b)
            assert context.validate(config).is_dir()
            different_workspace = home / "workstation" / "creative" / "another-project"
            different_workspace.mkdir()
            with connect_closing() as connection:
                connection.execute("UPDATE tasks SET workspace_path=? WHERE id=?",
                                   (str(different_workspace), context.task_id))
                connection.commit()
            with pytest.raises(PermissionError, match="policy"):
                save_project_for_run(config, context, {"title": "outside task workspace"})
            assert list((home / "workstation" / "creative" / "projects").iterdir()) == []
            with connect_closing() as connection:
                connection.execute("UPDATE tasks SET status='done' WHERE id=?", (context.task_id,))
                connection.commit()
            with pytest.raises(PermissionError, match="not live"):
                save_project_for_run(config, context, {})
            assert list((home / "workstation" / "creative" / "projects").iterdir()) == []
            assert not (home / "workstation" / "artifacts").exists()
    finally:
        reset_current_session_key(session_token)
        reset_hermes_home_override(home_token)

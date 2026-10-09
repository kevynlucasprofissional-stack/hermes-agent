from pathlib import Path

import pytest

from gateway.session_context import scoped_current_session_id
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from tools.approval_context import reset_current_session_key, set_current_session_key
from workstation.config import WorkstationConfig
from workstation.creative_project_runtime import CreativeEffectUncertain, save_project_for_run
from workstation.creative_remotion_source import RemotionInvitation
from workstation.journal import ExecutionJournal
from workstation.tests.test_creative_project_runtime import _task


def test_partial_native_write_is_uncertain_and_never_published(tmp_path, monkeypatch):
    home = tmp_path / "profile"
    monkeypatch.setenv("HERMES_KANBAN_DB", str(home / "kanban.db"))
    ht, st = set_hermes_home_override(home), set_current_session_key("approval-key")
    original_open = Path.open

    def fail_native(path, *args, **kwargs):
        if path.name == "Invitation.tsx" and args and args[0] == "xb":
            raise OSError("injected disk failure")
        return original_open(path, *args, **kwargs)

    try:
        with scoped_current_session_id("durable-session"):
            context = _task(home)
            monkeypatch.setattr(Path, "open", fail_native)
            with pytest.raises(CreativeEffectUncertain) as caught:
                save_project_for_run(WorkstationConfig({"creative": {"enabled": True}}), context,
                    RemotionInvitation("Hermes", "Invitation", "08 October").to_source(), engine="remotion")
            project_root = home / "workstation" / "creative" / "projects"
            assert len(list(project_root.rglob("source.creative.json"))) == 1
            assert not list(project_root.rglob("manifest.json"))
            events = ExecutionJournal(task_id=context.task_id, session_id="durable-session").read_events()
            assert events[-1].metadata["operation_id"] == caught.value.operation_id
            assert not (home / "workstation" / "artifacts").exists()
    finally:
        reset_current_session_key(st)
        reset_hermes_home_override(ht)

"""Real process lifecycle tests; Python helper does not qualify a media engine."""
import hashlib
from pathlib import Path
import sqlite3
import sys
import threading

import pytest

from gateway.session_context import scoped_current_session_id
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from tools.approval_context import reset_current_session_key, set_current_session_key
from tools.process_registry import ProcessRegistry
from workstation.config import WorkstationConfig
from workstation.creative_apps import CreativeAppManifest
from workstation.creative_video_process import run_media_command
from workstation.tests.test_creative_project_runtime import _task


@pytest.fixture
def media_context(tmp_path, monkeypatch):
    home = tmp_path / "profile"
    monkeypatch.setenv("HERMES_KANBAN_DB", str(home / "kanban.db"))
    ht = set_hermes_home_override(home)
    st = set_current_session_key("approval-key")
    registry = ProcessRegistry()
    try:
        with scoped_current_session_id("durable-session"):
            context = _task(home)
            executable = Path(sys.executable).resolve()
            helper = CreativeAppManifest(1, "ffmpeg", str(executable),
                hashlib.sha256(executable.read_bytes()).hexdigest(), "test-helper:not-a-media-build")
            yield WorkstationConfig({"creative": {"enabled": True}}), context, helper, registry
    finally:
        registry.kill_all()
        reset_current_session_key(st)
        reset_hermes_home_override(ht)


def test_command_readback_preserves_header_beyond_wait_tail(media_context):
    config, context, helper, registry = media_context
    result = run_media_command(config, context, helper,
        ("-u", "-c", "print('HEADER'); print('x' * 5000)"), registry=registry)
    assert result["output"].startswith("HEADER\n")
    assert len(result["output"]) > 5000
    assert not registry._running


def test_live_run_authority_loss_reaps_owned_child(media_context):
    config, context, helper, registry = media_context
    changed = threading.Event()

    def revoke_fixture():
        # External owner state transition is injected at the DB boundary to test
        # actual repeated readback while the real helper remains alive.
        with sqlite3.connect(str(Path(context.profile_home) / "kanban.db")) as connection:
            connection.execute("UPDATE tasks SET status='done' WHERE id=?", (context.task_id,))
        changed.set()

    timer = threading.Timer(0.5, revoke_fixture)
    timer.start()
    try:
        with pytest.raises(PermissionError):
            run_media_command(config, context, helper,
                ("-u", "-c", "import time; time.sleep(60)"), registry=registry)
        assert changed.is_set()
        assert not registry._running
        assert all(session.process.poll() is not None for session in registry._finished.values())
    finally:
        timer.cancel()
        timer.join()

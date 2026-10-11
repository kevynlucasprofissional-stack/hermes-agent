"""Tests for HyperFrames motion video render adapter and verification."""
import hashlib
import json
from pathlib import Path
import sys

import pytest

from gateway.session_context import scoped_current_session_id
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from tools.approval_context import reset_current_session_key, set_current_session_key
from tools.process_registry import ProcessRegistry
from workstation.config import WorkstationConfig
from workstation.creative_apps import CreativeAppManifest
from workstation.creative_hyperframes_render import (
    HyperFramesRenderRequest,
    render_hyperframes_video,
)
from workstation.creative_project_runtime import CreativeEffectUncertain
from workstation.creative_project_store import save_creative_revision
from workstation.creative_studio_service import HyperFramesInstallation
from workstation.creative_video_process import CreativeVideoEngines
from workstation.tests.test_creative_project_runtime import _task


@pytest.fixture
def render_fixture(tmp_path, monkeypatch):
    home = tmp_path / "profile"
    monkeypatch.setenv("HERMES_KANBAN_DB", str(home / "kanban.db"))
    ht = set_hermes_home_override(home)
    st = set_current_session_key("approval-key")
    registry = ProcessRegistry()
    try:
        with scoped_current_session_id("durable-session"):
            context = _task(home)
            from hermes_platform.resolver import locate_command
            ffmpeg_loc = locate_command("ffmpeg")
            ffprobe_loc = locate_command("ffprobe")
            if not ffmpeg_loc.found or not ffprobe_loc.found:
                pytest.skip("ffmpeg and ffprobe required for render test")
            ffmpeg_exe = Path(ffmpeg_loc.command[0]).resolve()
            ffprobe_exe = Path(ffprobe_loc.command[0]).resolve()
            ffmpeg_hash = hashlib.sha256(ffmpeg_exe.read_bytes()).hexdigest()
            ffprobe_hash = hashlib.sha256(ffprobe_exe.read_bytes()).hexdigest()

            ffmpeg_manifest = CreativeAppManifest(
                1, "ffmpeg", str(ffmpeg_exe), ffmpeg_hash, "local:ffmpeg"
            )
            ffprobe_manifest = CreativeAppManifest(
                1, "ffprobe", str(ffprobe_exe), ffprobe_hash, "local:ffprobe"
            )
            engines = CreativeVideoEngines(ffmpeg=ffmpeg_manifest, ffprobe=ffprobe_manifest)
            config = WorkstationConfig({"creative": {"enabled": True, "hyperframes_enabled": True}})
            yield config, context, engines, registry, home
    finally:
        registry.kill_all()
        reset_current_session_key(st)
        reset_hermes_home_override(ht)


def test_render_requires_hyperframes_engine(render_fixture):
    config, context, engines, registry, home = render_fixture
    # Revision with default electron-svg engine
    rev = save_creative_revision({"width": 100, "height": 100})
    py_exe = Path(sys.executable).resolve()
    py_hash = hashlib.sha256(py_exe.read_bytes()).hexdigest()

    installation = HyperFramesInstallation(
        engine="hyperframes",
        node_executable=py_exe,
        node_sha256=py_hash,
        cli_entrypoint=py_exe,
        cli_entrypoint_sha256=py_hash,
        package_version="0.8.143",
    )
    request = HyperFramesRenderRequest(project_id=rev.project_id, revision_id=rev.revision_id)

    with pytest.raises(ValueError, match="HyperFrames render requires engine='hyperframes'"):
        render_hyperframes_video(config, context, installation, request, engines, registry=registry)


def test_render_failure_raises_creative_effect_uncertain_without_orphans(render_fixture):
    config, context, engines, registry, home = render_fixture
    hf_metadata = {"width": 1920, "height": 1080, "fps": 30, "duration": 60}
    native_files = {
        "index.html": b"<!DOCTYPE html><html><body>Render Test</body></html>",
        "hyperframes.json": json.dumps(hf_metadata).encode("utf-8"),
    }
    rev = save_creative_revision(hf_metadata, engine="hyperframes", native_files=native_files)

    # CLI script that simulates render command failing
    failing_script = home / "fail_render.py"
    failing_script.write_text("import sys; sys.exit(1)\n", encoding="utf-8")
    py_exe = Path(sys.executable).resolve()
    py_hash = hashlib.sha256(py_exe.read_bytes()).hexdigest()
    script_hash = hashlib.sha256(failing_script.read_bytes()).hexdigest()

    installation = HyperFramesInstallation(
        engine="hyperframes",
        node_executable=py_exe,
        node_sha256=py_hash,
        cli_entrypoint=failing_script,
        cli_entrypoint_sha256=script_hash,
        package_version="0.8.143",
    )
    request = HyperFramesRenderRequest(project_id=rev.project_id, revision_id=rev.revision_id)

    with pytest.raises(CreativeEffectUncertain) as exc:
        render_hyperframes_video(config, context, installation, request, engines, registry=registry)

    assert exc.value.operation_id
    assert not registry._running

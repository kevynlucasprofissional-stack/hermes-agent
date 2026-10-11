from dataclasses import replace
import hashlib
from pathlib import Path
import sys

import pytest

from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from hermes_platform.resolver import locate_command
from tools.approval_context import reset_current_session_key, set_current_session_key
from workstation.artifacts import ArtifactStore
from workstation.config import WorkstationConfig
from workstation.creative_apps import CreativeAppManifest, probe_creative_app
from workstation.creative_process import CreativeExecutionScope


def test_probe_requires_engine_specific_readback_and_preserves_evidence(tmp_path):
    home = tmp_path / "profile"
    workspace = home / "workstation" / "creative" / "project"
    workspace.mkdir(parents=True)
    ht = set_hermes_home_override(home)
    st = set_current_session_key("health-session")
    scope = CreativeExecutionScope(str(home), "health-session", "health-task", str(workspace))
    enabled = WorkstationConfig({"creative": {"enabled": True}})
    binary = Path(sys.executable).resolve()
    manifest = CreativeAppManifest(1, "node", str(binary), hashlib.sha256(binary.read_bytes()).hexdigest(),
                                   "fixture:wrong-engine")
    try:
        receipt = probe_creative_app(enabled, scope, manifest)
        assert receipt["exit_code"] == 0
        assert receipt["health"] == "down" and receipt["version"] is None
        persisted = ArtifactStore().resolve_structured(receipt["artifact_ref"])
        assert persisted["sha256"] == receipt["artifact_sha256"]
        assert persisted["content"]["process_id"] == receipt["process_id"]
        with pytest.raises(ValueError):
            probe_creative_app(enabled, scope, replace(manifest, schema_version=2))
        with pytest.raises(ValueError):
            probe_creative_app(enabled, scope, replace(manifest, engine="shell"))
        with pytest.raises(ValueError):
            probe_creative_app(enabled, scope, replace(manifest, provider_ref="https://user:secret@example.com"))
    finally:
        reset_current_session_key(st)
        reset_hermes_home_override(ht)


def test_installed_node_has_real_cli_health_without_installing(tmp_path):
    resolution = locate_command("node")
    if not resolution.found:
        pytest.skip("Node is an optional locally installed engine")
    home = tmp_path / "profile"
    workspace = home / "workstation" / "creative" / "project"
    workspace.mkdir(parents=True)
    ht = set_hermes_home_override(home)
    st = set_current_session_key("node-session")
    binary = Path(resolution.command[0]).resolve()
    manifest = CreativeAppManifest(1, "node", str(binary), hashlib.sha256(binary.read_bytes()).hexdigest(),
                                   "local:node")
    try:
        receipt = probe_creative_app(WorkstationConfig({"creative": {"enabled": True}}),
                                    CreativeExecutionScope(str(home), "node-session", "node-task", str(workspace)),
                                    manifest)
        assert receipt["health"] == "ok" and receipt["version"].startswith("v")
        assert receipt["probe_kind"] == "cli_version"
    finally:
        reset_current_session_key(st)
        reset_hermes_home_override(ht)

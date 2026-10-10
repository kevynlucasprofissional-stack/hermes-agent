from pathlib import Path
import os
import subprocess

import yaml

from hermes_platform.resolver import LookupContext
from workstation.capabilities import RuntimeCapabilityRegistry
from workstation.config import WorkstationConfig, load_workstation_config


def test_discovery_is_opt_in_and_never_executes(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Passive discovery must not execute code")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr("workstation.creative_runtime.locate_command", forbidden)
    for raw in ({}, {"creative": {"enabled": "true"}},
                {"workstation": {"enabled": False}, "creative": {"enabled": True}}):
        config_file = tmp_path / "workstation.yaml"
        config_file.write_text(yaml.safe_dump(raw), encoding="utf-8")
        observations = RuntimeCapabilityRegistry.inspect_creative(load_workstation_config(config_file))
        assert observations and all(o.status == "disabled" for o in observations)
        assert all(o.executable is None and o.health == "not_checked" for o in observations)


def test_discovery_uses_explicit_search_scope_without_claiming_health(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Presence must not probe or spawn")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    engine = tmp_path / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
    engine.write_bytes(b"not a real executable; must never be launched")
    engine.chmod(0o755)
    config = WorkstationConfig({"creative": {"enabled": True}})
    context = LookupContext(path=str(tmp_path), pathext=".EXE")
    first = RuntimeCapabilityRegistry.inspect_creative(config, context=context)
    found = next(o for o in first if o.engine == "ffmpeg")
    assert found.status == "present"
    assert Path(found.executable).resolve() == engine.resolve()
    assert found.version is None and found.health == "not_checked"
    empty = RuntimeCapabilityRegistry.inspect_creative(config, context=LookupContext(path=""))
    assert all(o.status == "missing" and o.executable is None for o in empty)
    again = RuntimeCapabilityRegistry.inspect_creative(config, context=context)
    assert again == first

"""Behavior contracts for explicit Workstation adapter bootstrap truth."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

import workstation
from workstation.integrations.hermes import adapter


def test_workstation_disabled_does_not_install(monkeypatch):
    calls = []
    monkeypatch.setattr(adapter, "install_workstation_adapter", lambda: calls.append(True))

    status = workstation.bootstrap_workstation_adapter("disabled")

    assert status.mode == "disabled"
    assert status.installed is False
    assert calls == []


def test_workstation_expected_install_succeeds(monkeypatch):
    monkeypatch.setattr(adapter, "install_workstation_adapter", lambda: None)

    status = workstation.bootstrap_workstation_adapter("required")

    assert status.mode == "required"
    assert status.installed is True
    assert status.error is None


def test_workstation_expected_install_failure_fails_closed(monkeypatch):
    def fail():
        raise ValueError("broken adapter")

    monkeypatch.setattr(adapter, "install_workstation_adapter", fail)

    with pytest.raises(RuntimeError, match="required Workstation supervision"):
        workstation.bootstrap_workstation_adapter("required")

    status = workstation.workstation_adapter_status()
    assert status.mode == "required"
    assert status.installed is False
    assert "broken adapter" in (status.error or "")


def test_workstation_optional_failure_is_explicitly_degraded(monkeypatch):
    def fail():
        raise ValueError("optional adapter unavailable")

    monkeypatch.setattr(adapter, "install_workstation_adapter", fail)

    status = workstation.bootstrap_workstation_adapter("degraded")

    assert status.mode == "degraded"
    assert status.installed is False
    assert "optional adapter unavailable" in (status.error or "")


def test_non_workstation_hermes_import_does_not_bootstrap_product(tmp_path):
    env = dict(os.environ)
    env["HERMES_HOME"] = str(tmp_path)
    completed = subprocess.run(
        [sys.executable, "-c", "import run_agent, sys; assert 'workstation' not in sys.modules"],
        cwd=os.getcwd(), env=env, text=True, capture_output=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout

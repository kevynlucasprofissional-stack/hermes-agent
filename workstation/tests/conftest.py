"""Workstation contracts always use an ephemeral personal installation."""
import pytest
import atexit
import os
import shutil
import tempfile

# Fixtures run after collection: isolate import-time logger/store side effects too.
_session_home = tempfile.mkdtemp(prefix="hermes-workstation-tests-")
os.environ["HERMES_HOME"] = os.path.join(_session_home, "hermes")
os.environ["HERMES_WORKSTATION_HOME"] = os.path.join(_session_home, "workstation")
os.environ["HERMES_KANBAN_DB"] = os.path.join(_session_home, "hermes", "kanban.db")
os.environ["HERMES_TEST_ISOLATION"] = _session_home
atexit.register(shutil.rmtree, _session_home, True)


@pytest.fixture(autouse=True)
def isolated_workstation_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes"))
    monkeypatch.setenv("HERMES_WORKSTATION_HOME", str(tmp_path / "workstation"))
    monkeypatch.setenv("HERMES_KANBAN_DB", str(tmp_path / "hermes" / "kanban.db"))


@pytest.fixture
def direct_qualification_issuer(monkeypatch, request):
    """Test operator provisions trust explicitly; production never auto-provisions."""
    import base64
    import agent.secret_scope
    import hermes_cli.config
    from workstation.experience_compiler import compilability_monitor as monitor

    trust = {"issuer": "test-operator", "key_id": "test-key",
             "secret_ref": "WORKSTATION_DIRECT_QUALIFICATION_KEY", "bindings": [],
             "revoked_attestation_ids": []}
    config = {"workstation": {"online_compilability": {"qualification_trust": trust}}}
    monkeypatch.setattr(hermes_cli.config, "load_config_readonly", lambda: config)
    original_secret = agent.secret_scope.get_secret
    monkeypatch.setattr(agent.secret_scope, "get_secret", lambda name, default=None:
                        base64.b64encode(b"test-only-key-never-used-in-production").decode()
                        if name == trust["secret_ref"] else original_secret(name, default))
    original_issue = monitor.create_direct_qualification_attestation

    def issue(**kwargs):
        kwargs = {"model_revision": "test-revision", "operation_family": "read_status",
                  "verifier_contract": {"observer": "test-independent-reader"},
                  "exact_tests": ("test-controlled-replay",), **kwargs}
        attestation = original_issue(**kwargs)
        trust["bindings"].append({k: attestation[k] for k in monitor.QUALIFICATION_BINDINGS})
        return attestation

    monkeypatch.setattr(monitor, "create_direct_qualification_attestation", issue)
    if hasattr(request.module, "create_direct_qualification_attestation"):
        monkeypatch.setattr(request.module, "create_direct_qualification_attestation", issue)
    return trust

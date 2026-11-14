"""CLI contract: task-bound WhatsApp canary is read-only and fail-closed."""
import json
import pytest


def test_requires_explicit_owner_ids(capsys):
    from workstation.scripts.wa_opc011_canary_readonly import main
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_rejects_ambiguous_owner_ids(capsys):
    from workstation.scripts.wa_opc011_canary_readonly import main
    result = main(["--task-id", "default", "--session-id", "active"])
    assert result == 2
    assert json.loads(capsys.readouterr().out)["reason"] == "TASK_IDENTITY_REQUIRED"


def test_calls_native_probe_only_with_explicit_identity(monkeypatch, capsys):
    from workstation.scripts import wa_opc011_canary_readonly as canary
    from workstation.integrations.hermes import adapter
    called = []
    monkeypatch.setattr(adapter, "install_workstation_adapter", lambda: called.append("adapter"))
    monkeypatch.setattr(canary, "probe_native_schema", lambda **kw: (
        called.append(kw) or {"status": "HOLD", "reason": "CANARY_CHAT_NOT_SELECTED",
                               "can_send": False, "independently_verified": False}
    ))
    result = canary.main(["--task-id", "wa-opc011-test-1", "--session-id", "session-1"])
    output = json.loads(capsys.readouterr().out)
    assert result == 0
    assert output["reason"] == "CANARY_CHAT_NOT_SELECTED"
    assert called == ["adapter", {"task_id": "wa-opc011-test-1", "session_id": "session-1"}]


def test_probe_failure_does_not_leak_exception(monkeypatch, capsys):
    from workstation.scripts import wa_opc011_canary_readonly as canary
    from workstation.integrations.hermes import adapter
    monkeypatch.setattr(adapter, "install_workstation_adapter", lambda: None)
    def throw(**kw):
        raise RuntimeError("secret-credential-and-private-contact")
    monkeypatch.setattr(canary, "probe_native_schema", throw)
    status = canary.main(["--task-id", "wa-opc011-test-1", "--session-id", "session-1"])
    captured = capsys.readouterr().out
    assert status == 1
    assert json.loads(captured)["reason"] == "NATIVE_PROBE_ERROR"
    assert "secret-credential" not in captured

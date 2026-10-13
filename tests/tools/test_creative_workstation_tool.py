"""HWH-01: Desktop-only Creative UI tool contract (no TaskRun mutation)."""
import json

from tools import desktop_ui


def test_creative_tool_is_exposed_only_in_the_desktop_ui_toolset():
    from toolsets import TOOLSETS
    from tools.creative_workstation_tool import open_creative_workstation as handler

    assert callable(handler)
    assert "open_creative_workstation" in TOOLSETS["desktop_ui"]["tools"]
    assert "open_creative_workstation" not in TOOLSETS["browser"]["tools"]


def test_open_creative_uses_scoped_desktop_event(monkeypatch):
    from tools.creative_workstation_tool import open_creative_workstation

    events = []
    monkeypatch.setattr(desktop_ui, "emit", lambda event, payload: events.append((event, payload)) or True)
    receipt = json.loads(open_creative_workstation())
    assert events == [("creative.open", {})]
    assert receipt == {"success": True, "status": "requested", "app": "creative-workstation"}


def test_open_creative_fails_closed_when_desktop_is_absent(monkeypatch):
    from tools.creative_workstation_tool import open_creative_workstation

    monkeypatch.setattr(desktop_ui, "emit", lambda *_: False)
    assert "only available in the hermes desktop" in open_creative_workstation().lower()


def test_open_creative_does_not_fake_ack_on_emit_error(monkeypatch):
    from tools.creative_workstation_tool import open_creative_workstation

    def fault(*_):
        raise ConnectionError("desktop disconnected")

    monkeypatch.setattr(desktop_ui, "emit", fault)
    result = open_creative_workstation()
    assert "desktop disconnected" in result
    assert '"success": true' not in result.lower()

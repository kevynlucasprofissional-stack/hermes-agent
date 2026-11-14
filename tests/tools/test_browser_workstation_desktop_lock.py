"""Desktop-origin Browser Use must not escape the native Workstation Browser."""
import json

import model_tools
from gateway.session_context import clear_session_vars, set_session_vars
from tools import browser_use_cli


def test_desktop_tool_definition_does_not_expose_external_browser():
    tokens = set_session_vars(platform="desktop", source="desktop", session_id="new-desktop-chat")
    try:
        definition = {"type": "function", "function": {"name": "browser_exec"}}
        assert model_tools._rewrite_browser_exec(definition, {"browser_exec", "terminal"}) is None
    finally:
        clear_session_vars(tokens)


def test_new_desktop_task_rejects_browser_exec_before_daemon_spawn(monkeypatch):
    tokens = set_session_vars(platform="desktop", source="desktop", session_id="new-desktop-chat")
    try:
        def forbidden_cli():
            raise AssertionError("external browser CLI must never be resolved")

        monkeypatch.setattr(browser_use_cli, "_find_cli", forbidden_cli)
        result = browser_use_cli.browser_exec("print('external browser launched')", task_id="new-task")
        assert "error" in json.loads(result)
        assert "Workstation" in json.loads(result)["error"]
    finally:
        clear_session_vars(tokens)


def test_non_desktop_tool_definition_preserves_browser_use():
    tokens = set_session_vars(platform="telegram", source="telegram", session_id="other-chat")
    try:
        definition = {"type": "function", "function": {"name": "browser_exec"}}
        assert model_tools._rewrite_browser_exec(definition, {"browser_exec", "terminal"}) == definition
    finally:
        clear_session_vars(tokens)

def test_desktop_with_native_disabled_still_cannot_launch_external_browser(monkeypatch):
    monkeypatch.setenv("HERMES_WORKSTATION_BROWSER", "0")
    tokens = set_session_vars(platform="desktop", source="desktop", session_id="disabled-native-chat")
    try:
        definition = {"type": "function", "function": {"name": "browser_exec"}}
        assert model_tools._rewrite_browser_exec(definition, {"browser_exec", "terminal"}) is None

        def forbidden_cli():
            raise AssertionError("disabled native browser must not enable an external daemon")

        monkeypatch.setattr(browser_use_cli, "_find_cli", forbidden_cli)
        result = browser_use_cli.browser_exec("print('never run')", task_id="new-task")
        assert "Workstation" in json.loads(result)["error"]
    finally:
        clear_session_vars(tokens)

def test_cached_tool_definitions_do_not_cross_disabled_desktop_and_cli(monkeypatch):
    monkeypatch.setenv("HERMES_WORKSTATION_BROWSER", "0")
    desktop = set_session_vars(platform="desktop", source="desktop", session_id="desktop")
    try:
        desktop_key = model_tools._tool_defs_cache_key(None, None, False)
    finally:
        clear_session_vars(desktop)

    other = set_session_vars(platform="telegram", source="telegram", session_id="telegram")
    try:
        other_key = model_tools._tool_defs_cache_key(None, None, False)
    finally:
        clear_session_vars(other)
    assert desktop_key != other_key

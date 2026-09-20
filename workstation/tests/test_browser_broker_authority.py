"""Workstation Browser authority-switch contracts for H-079."""

from __future__ import annotations

import json

import pytest

from gateway.browser_control_broker import get_browser_control_broker
from gateway.session_context import clear_session_vars, set_session_vars
from tools.browser_extension_router import routed_browser_handler
from workstation.integrations.hermes import browser_controller


@pytest.fixture(autouse=True)
def clean_broker():
    broker = get_browser_control_broker()
    broker.reset()
    browser_controller._CONTROLLERS.clear()
    yield broker
    broker.reset()
    browser_controller._CONTROLLERS.clear()


@pytest.mark.parametrize(
    "action,args",
    [
        ("browser_navigate", {"url": "https://example.test"}),
        ("browser_click", {"ref": "e1"}),
        ("browser_type", {"ref": "e2", "text": "hello"}),
        ("browser_press", {"key": "Enter"}),
        ("browser_select", {"ref": "e3", "value": "one"}),
        ("browser_scroll", {"direction": "down"}),
        ("browser_extension_open_options", {"extension_id": "a" * 32}),
    ],
)
def test_generic_router_executes_each_workstation_mutation_once(
    monkeypatch, clean_broker, action, args,
):
    calls = []
    fallbacks = []
    monkeypatch.setattr(browser_controller, "workstation_browser_enabled", lambda: True)
    monkeypatch.setattr(browser_controller, "workstation_controller_available", lambda **kw: True)
    monkeypatch.setattr(browser_controller, "workstation_route_is_bound", lambda *a: True)
    monkeypatch.setattr(
        browser_controller,
        "dispatch_workstation_browser_authoritative",
        lambda name, payload, **context: calls.append((name, payload, context)) or json.dumps({"ok": True}),
    )
    tokens = set_session_vars(platform="desktop", source="desktop", session_id="session-1")
    try:
        result = routed_browser_handler(
            action, args, task_id="task-1", session_id="session-1", run_id="run-1",
            fallback=lambda: fallbacks.append(True) or "legacy",
        )
    finally:
        clear_session_vars(tokens)

    assert json.loads(result) == {"ok": True}
    assert calls == [(action, args, {
        "task_id": "task-1", "session_id": "session-1", "run_id": "run-1",
    })]
    assert fallbacks == []


def test_unbound_offline_task_uses_allowed_fallback(monkeypatch, clean_broker):
    monkeypatch.setattr(browser_controller, "workstation_browser_enabled", lambda: True)
    monkeypatch.setattr(browser_controller, "workstation_controller_available", lambda **kw: False)
    monkeypatch.setattr(browser_controller, "workstation_route_is_bound", lambda *a: False)
    monkeypatch.setattr(browser_controller, "workstation_routing_enabled", lambda: True)
    tokens = set_session_vars(platform="desktop", source="desktop", session_id="session-1")
    try:
        result = routed_browser_handler(
            "browser_navigate", {"url": "https://example.test"}, task_id="task-new",
            session_id="session-1", fallback=lambda: "legacy",
        )
    finally:
        clear_session_vars(tokens)
    assert result == "legacy"


def test_bound_offline_task_fails_closed(monkeypatch, clean_broker):
    from gateway.browser_control_broker import ControllerRejected

    monkeypatch.setattr(browser_controller, "workstation_browser_enabled", lambda: True)
    monkeypatch.setattr(browser_controller, "workstation_controller_available", lambda **kw: False)
    monkeypatch.setattr(browser_controller, "workstation_route_is_bound", lambda *a: True)
    monkeypatch.setattr(
        browser_controller,
        "dispatch_workstation_browser_authoritative",
        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("controller down")),
    )
    tokens = set_session_vars(platform="desktop", source="desktop", session_id="session-1")
    try:
        with pytest.raises(ControllerRejected, match="controller down"):
            routed_browser_handler(
                "browser_click", {"ref": "e1"}, task_id="task-1", session_id="session-1",
                fallback=lambda: pytest.fail("bound task must not fall back"),
            )
    finally:
        clear_session_vars(tokens)

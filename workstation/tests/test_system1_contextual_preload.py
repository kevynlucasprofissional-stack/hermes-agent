"""Contextual model preload is optional, once-per-backend and never a Browser effect."""
import threading
from unittest.mock import patch

from workstation.system1.contextual_preload import maybe_preload_after_browser_tool
from workstation.system1.laya_provider import LayaDecisionProvider


class FakeRouter:
    loaded = []

    def __init__(self):
        self.count = 0
        self.started = threading.Event()
        self.release = threading.Event()

    def load(self, name):
        self.count += 1
        self.started.set()
        assert self.release.wait(timeout=3)
        self.loaded.append(name)


def _provider(router):
    p = object.__new__(LayaDecisionProvider)
    p.model = "multilingual"
    p._router = None
    p._router_lock = threading.Lock()
    p._preload_lock = threading.Lock()
    p._preload_state = "idle"
    p._ensure_router = lambda: router
    return p


def test_preload_deferred_under_memory_pressure():
    p = _provider(FakeRouter())
    assert p.schedule_preload(4 * 1024 ** 3) == "deferred_memory"
    assert p._preload_state == "idle"


def test_preload_single_worker_even_for_many_tabs():
    router = FakeRouter()
    p = _provider(router)
    assert p.schedule_preload(6 * 1024 ** 3) == "scheduled"
    assert router.started.wait(timeout=2)
    assert p.schedule_preload(6 * 1024 ** 3) == "loading"
    router.release.set()
    assert p._preload_lock.acquire(timeout=2)
    p._preload_lock.release()
    # A concurrent thread may still be returning; take the outcome after its
    # result has become visible, without sleeping or holding the test open.
    from tests.waiting import wait_until
    assert wait_until(lambda: p._preload_state == "ready", timeout=3)
    assert router.count == 1
    assert p.schedule_preload(6 * 1024 ** 3) == "ready"


def test_observer_denied_or_failed_browser_action_cannot_preload():
    with patch("agent.system1_decision.system1_decision_providers") as providers:
        for result, dispatched in [(dict(success=True), False), ("not json", True),
                                    (dict(success=False), True)]:
            assert maybe_preload_after_browser_tool("browser_navigate", result, dispatched=dispatched) != "scheduled"
        assert maybe_preload_after_browser_tool("browser_snapshot", {"success": True},
                                               dispatched=True) == "not_applicable"
        providers.assert_not_called()


def test_successful_navigate_uses_same_registered_laya_provider():
    router = FakeRouter()
    p = _provider(router)
    with patch("agent.system1_decision.system1_decision_providers", return_value=(p,)), \
         patch("psutil.virtual_memory") as memory:
        memory.return_value.available = 6 * 1024 ** 3
        assert maybe_preload_after_browser_tool(
            "browser_navigate", '{"success":true,"runtime":"electron-chromium","task_id":"qa"}', dispatched=True,
        ) == "scheduled"
        assert router.started.wait(timeout=2)
        assert maybe_preload_after_browser_tool(
            "browser_tab_activate", {"success": True, "runtime": "electron-chromium", "task_id": "qa"}, dispatched=True,
        ) == "loading"
        router.release.set()
    from tests.waiting import wait_until
    assert wait_until(lambda: p._preload_state == "ready", timeout=3)
    assert router.count == 1

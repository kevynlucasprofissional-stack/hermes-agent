import pytest
from workstation.browser_session import (
    BrowserControlLeaseManager,
    BrowserControlMode,
    HumanTakeoverActiveError,
)


@pytest.fixture(autouse=True)
def reset_lease_manager():
    mgr = BrowserControlLeaseManager.get_instance()
    mgr._leases.clear()
    if hasattr(mgr, "_parent_map"):
        mgr._parent_map.clear()
    if hasattr(mgr, "_children_map"):
        mgr._children_map.clear()
    yield
    mgr._leases.clear()
    if hasattr(mgr, "_parent_map"):
        mgr._parent_map.clear()
    if hasattr(mgr, "_children_map"):
        mgr._children_map.clear()


def test_subagent_child_task_independent_lease_and_fence_token():
    mgr = BrowserControlLeaseManager.get_instance()
    parent_task = "task_parent_100"
    child_task = "task_parent_100_sub_c1"

    mgr.register_child_task(child_task, parent_task)
    assert mgr.get_parent_task(child_task) == parent_task
    assert child_task in mgr.get_child_tasks(parent_task)

    parent_lease = mgr.get_lease(parent_task)
    child_lease = mgr.get_lease(child_task)

    # Must have distinct fence tokens (no token copying)
    assert parent_lease.fence_token != child_lease.fence_token

    # Using parent fence token on child must be rejected as stale/mismatched
    with pytest.raises(HumanTakeoverActiveError, match="Stale fence token"):
        mgr.assert_action_allowed(child_task, "browser_navigate", fence_token=parent_lease.fence_token)

    # Using child fence token succeeds
    mgr.assert_action_allowed(child_task, "browser_navigate", fence_token=child_lease.fence_token)


def test_human_takeover_on_parent_propagates_to_child_runs():
    mgr = BrowserControlLeaseManager.get_instance()
    parent_task = "task_parent_200"
    child_task = "task_parent_200_sub_c2"

    mgr.register_child_task(child_task, parent_task)

    # Initially both are AGENT
    mgr.assert_action_allowed(child_task, "browser_navigate")

    # Parent requests human takeover
    mgr.request_human_control(parent_task, "User solving MFA")

    # Child destructive action blocked due to parent takeover
    with pytest.raises(HumanTakeoverActiveError, match="parent task"):
        mgr.assert_action_allowed(child_task, "browser_navigate")

    # Non-destructive action on child remains allowed
    mgr.assert_action_allowed(child_task, "browser_snapshot")

    # Resume parent agent control
    mgr.resume_agent_control(parent_task)

    # Child can execute destructive action again
    mgr.assert_action_allowed(child_task, "browser_navigate")


def test_two_concurrent_child_runs_isolation():
    mgr = BrowserControlLeaseManager.get_instance()
    parent_task = "task_parent_300"
    child_1 = "task_parent_300_sub_child1"
    child_2 = "task_parent_300_sub_child2"

    mgr.register_child_task(child_1, parent_task)
    mgr.register_child_task(child_2, parent_task)

    # Human takeover on Child 1 only
    mgr.request_human_control(child_1, "Manual inspection of child 1")

    # Child 1 blocked
    with pytest.raises(HumanTakeoverActiveError):
        mgr.assert_action_allowed(child_1, "browser_navigate")

    # Child 2 is NOT blocked
    mgr.assert_action_allowed(child_2, "browser_navigate")


def test_delegate_tool_stamps_canonical_child_task_id_and_lineage(monkeypatch):
    from types import SimpleNamespace
    from tools.delegate_tool import _build_child_preserving_parent_tools

    monkeypatch.setattr(
        "run_agent.AIAgent",
        lambda **kw: SimpleNamespace(session_id="child_sub_sess_1", **kw),
    )

    parent = SimpleNamespace(
        session_id="parent_session_123",
        _canonical_work_task_id="task_parent_root",
        _canonical_work_run_id="run_root",
        model="test-model",
        provider="mock",
        base_url="",
        api_key="sk-test",
        prefill_messages=None,
        _client_kwargs={},
    )

    child = _build_child_preserving_parent_tools(
        task_index=0,
        goal="Search docs",
        context=None,
        toolsets=["browser"],
        model=None,
        max_iterations=5,
        task_count=1,
        parent_agent=parent,
        role="leaf",
    )

    assert hasattr(child, "_canonical_work_task_id")
    assert child._canonical_work_task_id.startswith("task_parent_root_sub_")
    assert child._parent_canonical_work_task_id == "task_parent_root"

    # Lineage registered in BrowserControlLeaseManager via workstation browser route
    from tools.browser_workstation import workstation_routed_browser_handler
    monkeypatch.setenv("HERMES_WORKSTATION_BROWSER", "1")
    monkeypatch.setattr("tools.browser_workstation.workstation_controller_available", lambda force=False: True)
    monkeypatch.setattr("tools.browser_workstation._dispatch", lambda *a, **k: "ok")

    workstation_routed_browser_handler("browser_snapshot", {}, fallback=lambda: "fallback", task_id=child._canonical_work_task_id)

    mgr = BrowserControlLeaseManager.get_instance()
    assert mgr.get_parent_task(child._canonical_work_task_id) == "task_parent_root"


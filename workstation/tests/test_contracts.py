from workstation.contracts import BrowserTaskReport, DiscoveredTask, ExecutionEvent, ExecutionEventKind
from workstation.routing import BrowserBackend, BrowserRoutingContext, BrowserRoutingPolicy
from workstation.safety import classify_action


def test_discovered_task_requires_lineage():
    task = DiscoveredTask(
        title="Renew domain",
        parent_task_id="t_parent",
        discovered_by="browser-worker",
        reason="Expiry shown in Trello card",
        origin_session_id="s_1",
    )
    task.validate()


def test_bound_browser_never_fails_over():
    policy = BrowserRoutingPolicy(enabled=True)
    assert policy.choose(BrowserRoutingContext(bound_to_internal=True, heavy_adaptive_flow=True)) is BrowserBackend.INTERNAL


def test_routing_disabled_means_internal_only():
    policy = BrowserRoutingPolicy(enabled=False)
    assert policy.choose(BrowserRoutingContext(public_read_only=True)) is BrowserBackend.INTERNAL


def test_sensitive_action_requires_approval():
    decision = classify_action("publish")
    assert decision.approval_required is True


def test_report_maps_to_kanban_metadata():
    report = BrowserTaskReport(task_id="t1", session_id="s1", objective="x", result="done", completed=True)
    metadata = report.to_kanban_metadata()
    assert metadata["workstation"]["session_id"] == "s1"


def test_execution_event_serializes_enums():
    event = ExecutionEvent(kind=ExecutionEventKind.ACTION, task_id="t1", session_id="s1", message="clicked")
    assert event.to_dict()["kind"] == "action"


def test_default_config_is_fail_closed_for_lan():
    from workstation.config import load_workstation_config
    cfg = load_workstation_config()
    assert cfg.lan_enabled is False
    assert cfg.lan_requires_auth is True

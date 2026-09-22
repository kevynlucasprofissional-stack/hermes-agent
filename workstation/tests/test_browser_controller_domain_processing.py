from __future__ import annotations

from workstation.integrations.hermes.browser_controller import WorkstationBrowserController


def test_extract_items_processing_stays_at_workstation_controller(monkeypatch):
    """The generic broker result reaches the Workstation domain processor once."""
    calls = []

    def process(raw_result, args, kw):
        calls.append((raw_result, args, kw))
        return '{"artifact_ref":"artifact://items"}'

    monkeypatch.setattr(
        "workstation.integrations.hermes.browser_controller.process_extracted_items_durably",
        process,
    )
    controller = object.__new__(WorkstationBrowserController)

    result = controller._process_browser_action_result(
        "browser_extract_items", {"items": []}, {"limit": 3}, {"task_id": "task"}
    )

    assert result == '{"artifact_ref":"artifact://items"}'
    assert calls == [({"items": []}, {"limit": 3}, {"task_id": "task"})]


def test_non_extract_result_is_preserved_for_broker_completion():
    controller = object.__new__(WorkstationBrowserController)

    assert controller._process_browser_action_result("browser_snapshot", "raw", {}, {}) == "raw"
    assert controller._process_browser_action_result("browser_snapshot", {"ok": True}, {}, {}) == '{"ok": true}'

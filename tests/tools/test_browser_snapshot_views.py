"""D-049 B1.1 — browser_snapshot opt-in view projection contracts.

These tests validate that the model-facing schema exposes the compact view
parameters, that the workstation payload forwards them verbatim to the
Electron runtime, and that the legacy projection preserves backwards
compatibility when no view is requested.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tools import browser_tool, browser_workstation
from tools.registry import registry


def _snapshot_schema() -> dict[str, Any]:
    entry = registry.get_entry("browser_snapshot")
    assert entry is not None, "browser_snapshot must be registered"
    return entry.schema


class TestBrowserSnapshotViewSchema:
    """Schema exposure: view parameters are present and constrained."""

    def test_view_enum_is_exposed(self) -> None:
        schema = _snapshot_schema()
        props = schema["parameters"]["properties"]
        assert "view" in props
        assert props["view"]["type"] == "string"
        assert set(props["view"]["enum"]) == {"summary", "action_map", "focus", "content"}

    def test_focus_ref_is_string(self) -> None:
        props = _snapshot_schema()["parameters"]["properties"]
        assert "focus_ref" in props
        assert props["focus_ref"]["type"] == "string"

    def test_focus_neighbors_bounds(self) -> None:
        props = _snapshot_schema()["parameters"]["properties"]
        assert "focus_neighbors" in props
        assert props["focus_neighbors"]["type"] == "integer"
        assert props["focus_neighbors"]["minimum"] == 0
        assert props["focus_neighbors"]["maximum"] == 10

    def test_max_chars_bounds(self) -> None:
        props = _snapshot_schema()["parameters"]["properties"]
        assert "max_chars" in props
        assert props["max_chars"]["type"] == "integer"
        assert props["max_chars"]["minimum"] == 200
        assert props["max_chars"]["maximum"] == 12000

    def test_legacy_full_parameter_unchanged(self) -> None:
        props = _snapshot_schema()["parameters"]["properties"]
        assert "full" in props
        assert props["full"]["type"] == "boolean"
        assert props["full"].get("default") is False


class TestBrowserSnapshotViewRouting:
    """View parameters flow through _fallback_call into browser_snapshot."""

    def test_fallback_call_passes_view_kwargs(self) -> None:
        """View params travel as extra_kw from the registry's kw dict, not from args."""
        adapter = browser_tool._fallback_call(
            "browser_snapshot",
            {"full": False},
            ("user_task", "view", "focus_ref", "focus_neighbors", "max_chars"),
        )
        captured: dict[str, Any] = {}

        def fake_snapshot(**kwargs: Any) -> str:
            captured.update(kwargs)
            return json.dumps({"success": True, "snapshot": "ok"})

        with patch.object(browser_tool, "browser_snapshot", side_effect=fake_snapshot):
            adapter(
                {"full": False},
                {
                    "task_id": "t1",
                    "view": "action_map",
                    "focus_ref": "@e3",
                    "focus_neighbors": 2,
                    "max_chars": 800,
                },
            )

        assert captured["view"] == "action_map"
        assert captured["focus_ref"] == "@e3"
        assert captured["focus_neighbors"] == 2
        assert captured["max_chars"] == 800
        assert captured["task_id"] == "t1"

    def test_fallback_call_omits_missing_view_kwargs(self) -> None:
        adapter = browser_tool._fallback_call(
            "browser_snapshot",
            {"full": False},
            ("user_task", "view", "focus_ref", "focus_neighbors", "max_chars"),
        )
        captured: dict[str, Any] = {}

        def fake_snapshot(**kwargs: Any) -> str:
            captured.update(kwargs)
            return json.dumps({"success": True, "snapshot": "ok"})

        with patch.object(browser_tool, "browser_snapshot", side_effect=fake_snapshot):
            adapter({"full": True}, {"task_id": "t2"})

        assert captured["view"] is None
        assert captured["focus_ref"] is None
        assert captured["focus_neighbors"] is None
        assert captured["max_chars"] is None
        assert captured["full"] is True


class TestProjectModelBrowserPayloadViews:
    """Projection: view payloads bypass element deduplication; legacy path unchanged."""

    def test_view_payload_skips_element_dedup(self) -> None:
        payload = {
            "success": True,
            "view": "action_map",
            "text": "@e1 button \"Submit\"\n@e2 link \"Help\"",
            "truncated": False,
            "elements": [{"ref": "@e1", "role": "button", "label": "Submit"}],
        }
        projected = browser_workstation.project_model_browser_payload(payload)
        assert projected is payload  # identity preserved; no mutation
        assert projected["view"] == "action_map"
        assert projected["elements"] == payload["elements"]

    def test_legacy_payload_still_deduplicates_elements(self) -> None:
        """Legacy dedup requires the exact formatInventory grammar inside the
        'Interactive elements:' section; without it the projection fails open."""
        snapshot_text = (
            "Interactive elements:\n"
            "- [@e1] button \"Submit\"\n"
            "- [@e2] textbox \"Email\" value=\"a@b.c\"\n"
            "\nPage text:\nSome body text."
        )
        payload = {
            "success": True,
            "snapshot": snapshot_text,
            "element_count": 2,
            "elements": [
                {"ref": "@e1", "role": "button", "label": "Submit", "tag": "BUTTON", "disabled": False},
                {"ref": "@e2", "role": "textbox", "label": "Email", "value": "a@b.c", "tag": "INPUT", "disabled": False},
            ],
        }
        projected = browser_workstation.project_model_browser_payload(payload)
        assert isinstance(projected, dict)
        # Legacy path replaces the redundant list with element_index metadata
        assert "element_index" in projected
        assert projected.get("element_count") == 2

    def test_non_dict_payload_passthrough(self) -> None:
        assert browser_workstation.project_model_browser_payload("plain") == "plain"
        assert browser_workstation.project_model_browser_payload(None) is None
from __future__ import annotations

import json
from uuid import uuid4
import pytest

from workstation.artifacts import ArtifactStore
from workstation.durable_tasks import DurableTaskStore
from workstation.browser_projection import process_extracted_items_durably


def test_browser_extract_items_durable_processing(tmp_path, monkeypatch):
    """Scenario: browser_extract_items processes items into ArtifactStore, creates WorkPlan, and returns compact summary."""
    task_id = f"test_extract_{uuid4().hex[:6]}"
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    # Mock raw extraction data with 10 items (9 valid, 1 anomaly with empty title)
    raw_items = [
        {"title": f"Product {i}", "url": f"https://example.com/p/{i}", "price": f"R$ {i * 10},00"}
        for i in range(1, 10)
    ]
    # Injected anomaly: item with empty title
    raw_items.append({"title": "", "url": "https://example.com/p/10", "price": "R$ 100,00"})

    raw_response = {
        "success": True,
        "runtime": "electron-chromium",
        "count": len(raw_items),
        "selector_used": "div.product-card",
        "url": "https://example.com/shop",
        "title": "Shop Page",
        "items": raw_items,
    }

    result_str = process_extracted_items_durably(
        raw_result=raw_response,
        args={"limit": 20, "output_artifact": True},
        kw={"task_id": task_id},
    )

    summary = json.loads(result_str)
    assert summary["success"] is True
    assert summary["total_extracted"] == 10
    assert summary["valid_count"] == 9
    assert summary["anomalies_count"] == 1
    assert summary["selector_used"] == "div.product-card"

    # Verify that raw items array is NOT in the summary returned to LLM
    assert "items" not in summary
    assert len(summary["sample_preview"]) == 2

    # Verify that artifact was stored with SHA-256 reference
    artifact_ref = summary["artifact_ref"]
    assert artifact_ref.startswith("artifact://")
    store = ArtifactStore()
    stored_data = store.read_json(artifact_ref)
    assert stored_data["count"] == 10
    assert len(stored_data["items"]) == 10

    # Verify durable WorkPlan was created in kanban_db
    with DurableTaskStore() as durable_store:
        plan = durable_store.get_plan(task_id)
        assert plan is not None
        assert plan.total_items == 10
        remaining_items = durable_store.resume_plan(task_id)
        assert len(remaining_items) == 1
        assert remaining_items[0].status.value == "failed"


def test_browser_extract_items_small_raw_mode():
    """Scenario: small extractions (<= 5 items) with output_artifact=False return raw json directly."""
    raw_items = [{"title": "Item 1", "url": "https://example.com/1"}]
    raw_response = {
        "success": True,
        "count": 1,
        "selector_used": "article",
        "items": raw_items,
    }

    result_str = process_extracted_items_durably(
        raw_result=raw_response,
        args={"limit": 5, "output_artifact": False},
        kw={"task_id": "test_small"},
    )

    data = json.loads(result_str)
    assert "items" in data
    assert len(data["items"]) == 1


def test_schema_invalid_with_title_present_marks_items_failed(tmp_path, monkeypatch):
    """G1 Problem 2: schema_valid=false must prevent WorkItem completion even when title is present.

    The Electron runtime returns schema_valid=false but the items have valid titles.
    The projection must NOT mark these items as complete/conforming to the schema.
    """
    task_id = f"test_schema_invalid_{uuid4().hex[:6]}"
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    raw_items = [
        {"title": "Product A", "url": "https://example.com/a", "price": "10.00"},
        {"title": "Product B", "url": "https://example.com/b", "price": "20.00"},
    ]
    raw_response = {
        "success": True,
        "count": 2,
        "selector_used": "div.product",
        "url": "https://example.com/shop",
        "title": "Shop",
        "items": raw_items,
        "schema_valid": False,
        "schema_errors": ["$: unsupported schema keywords: $ref"],
    }

    result_str = process_extracted_items_durably(
        raw_result=raw_response,
        args={"limit": 20, "output_artifact": True, "schema": {"type": "object", "$ref": "#/defs/X"}},
        kw={"task_id": task_id},
    )

    summary = json.loads(result_str)
    assert summary["schema_status"] == "invalid"
    assert summary["valid_count"] == 0, "No item should be marked valid when schema_valid=false"

    with DurableTaskStore() as durable_store:
        remaining = durable_store.resume_plan(task_id)
        assert len(remaining) == 2
        for item in remaining:
            assert item.status.value != "completed", (
                f"Item {item.id} must not be completed when schema is invalid"
            )


def test_schema_verdict_absent_marks_status_unknown(tmp_path, monkeypatch):
    """G1 Problem 2: missing schema_valid verdict must produce 'unknown' status, not approval."""
    task_id = f"test_schema_unknown_{uuid4().hex[:6]}"
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    raw_items = [{"title": "Item X", "url": "https://example.com/x"}]
    raw_response = {
        "success": True,
        "count": 1,
        "selector_used": "article",
        "items": raw_items,
        # schema_valid is intentionally absent
    }

    result_str = process_extracted_items_durably(
        raw_result=raw_response,
        args={"limit": 20, "output_artifact": True, "schema": {"type": "object", "required": ["title"]}},
        kw={"task_id": task_id},
    )

    summary = json.loads(result_str)
    assert summary["schema_status"] == "unknown"
    assert summary["valid_count"] == 0, "Items must not be marked valid when verdict is absent"


def test_schema_valid_without_required_title_completes_items(tmp_path, monkeypatch):
    """G1 Problem 2: when schema is valid and does not require title, items should complete.

    The SemanticValidator's hardcoded required_fields=['title'] must not override
    a user-supplied schema that does not require title.
    """
    task_id = f"test_schema_no_title_{uuid4().hex[:6]}"
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    raw_items = [
        {"name": "Widget A", "sku": "WGT-001"},
        {"name": "Widget B", "sku": "WGT-002"},
    ]
    raw_response = {
        "success": True,
        "count": 2,
        "selector_used": "li.widget",
        "items": raw_items,
        "schema_valid": True,
    }

    result_str = process_extracted_items_durably(
        raw_result=raw_response,
        args={
            "limit": 20,
            "output_artifact": True,
            "schema": {"type": "object", "required": ["name", "sku"], "properties": {"name": {"type": "string"}, "sku": {"type": "string"}}},
        },
        kw={"task_id": task_id},
    )

    summary = json.loads(result_str)
    assert summary["schema_status"] == "valid"
    assert summary["valid_count"] == 2, "Items conforming to a valid schema should complete"

    with DurableTaskStore() as durable_store:
        remaining = durable_store.resume_plan(task_id)
        assert len(remaining) == 0, "All items should be completed when schema is valid"


def test_no_schema_requested_preserves_semantic_validation(tmp_path, monkeypatch):
    """G1 Problem 2: when no schema is requested, semantic validation (title) still applies."""
    task_id = f"test_no_schema_{uuid4().hex[:6]}"
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))

    raw_items = [
        {"title": "Good Item", "url": "https://example.com/good"},
        {"title": "", "url": "https://example.com/bad"},
    ]
    raw_response = {
        "success": True,
        "count": 2,
        "selector_used": "div.item",
        "items": raw_items,
    }

    result_str = process_extracted_items_durably(
        raw_result=raw_response,
        args={"limit": 20, "output_artifact": True},
        kw={"task_id": task_id},
    )

    summary = json.loads(result_str)
    assert summary["schema_status"] == "not_requested"
    assert summary["valid_count"] == 1
    assert summary["anomalies_count"] == 1

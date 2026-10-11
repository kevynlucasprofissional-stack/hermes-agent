"""Tests for typed CreativeOperations on HyperFrames projects."""
import json
from pathlib import Path

import pytest

from gateway.session_context import scoped_current_session_id
from hermes_constants import reset_hermes_home_override, set_hermes_home_override
from tools.approval_context import reset_current_session_key, set_current_session_key
from workstation.config import WorkstationConfig
from workstation.creative_operations import (
    CreativeOperation,
    apply_creative_operation,
    inspect_project,
    parse_html_tree,
    render_html_tree,
    sanitize_attributes,
    sanitize_styles,
)
from workstation.creative_project_store import (
    CreativeConflictError,
    save_creative_revision,
)
from workstation.tests.test_creative_project_runtime import _task


@pytest.fixture
def op_context(tmp_path, monkeypatch):
    home = tmp_path / "profile"
    monkeypatch.setenv("HERMES_KANBAN_DB", str(home / "kanban.db"))
    ht = set_hermes_home_override(home)
    st = set_current_session_key("approval-key")
    try:
        with scoped_current_session_id("durable-session"):
            context = _task(home)
            config = WorkstationConfig({"creative": {"enabled": True, "hyperframes_enabled": True}})
            yield config, context, home
    finally:
        reset_current_session_key(st)
        reset_hermes_home_override(ht)


def test_html_parser_and_renderer_roundtrip():
    original = "<html><body><div id=\"root\" class=\"app\"><h1 data-hf-id=\"h1\">Title</h1></div></body></html>"
    root = parse_html_tree(original)
    rendered = render_html_tree(root)
    assert 'data-hf-id="h1"' in rendered
    assert "Title" in rendered
    assert 'class="app"' in rendered


def test_add_and_update_element_sequential_workflow(op_context):
    config, context, home = op_context
    hf_meta = {"width": 1920, "height": 1080, "fps": 30, "duration": 60}
    initial_html = "<!DOCTYPE html><html><body><div id=\"root\"></div></body></html>"
    native = {
        "index.html": initial_html.encode("utf-8"),
        "hyperframes.json": json.dumps(hf_meta).encode("utf-8"),
    }
    rev1 = save_creative_revision(hf_meta, engine="hyperframes", native_files=native)

    # 1. Inspect initial project
    inspection = inspect_project(rev1)
    assert inspection["project_id"] == rev1.project_id
    assert inspection["engine"] == "hyperframes"
    assert inspection["etag"] == rev1.etag

    # 2. Add an element via CreativeOperation
    add_op = CreativeOperation(
        kind="add_element",
        project_id=rev1.project_id,
        parent_revision_id=rev1.revision_id,
        if_match=rev1.etag,
        params={
            "tag": "h1",
            "element_id": "hf-title",
            "text": "Human Draft Title",
            "styles": {"color": "#ffffff", "font-size": "48px"},
        },
    )
    rev2, details2 = apply_creative_operation(config, context, add_op)
    assert rev2.parent_revision == rev1.revision_id
    assert rev2.etag != rev1.etag
    assert details2["added_element_id"] == "hf-title"

    # Read back index.html and verify added element
    html2 = (rev2.manifest_path.parent / "index.html").read_text(encoding="utf-8")
    assert 'data-hf-id="hf-title"' in html2
    assert "Human Draft Title" in html2
    assert "color: #ffffff" in html2

    # 3. Agent modifies the element text
    update_op = CreativeOperation(
        kind="update_element",
        project_id=rev2.project_id,
        parent_revision_id=rev2.revision_id,
        if_match=rev2.etag,
        params={
            "element_id": "hf-title",
            "text": "Agent Enhanced Title",
        },
    )
    rev3, details3 = apply_creative_operation(config, context, update_op)
    assert rev3.parent_revision == rev2.revision_id
    assert details3["updated_element_id"] == "hf-title"

    html3 = (rev3.manifest_path.parent / "index.html").read_text(encoding="utf-8")
    assert "Agent Enhanced Title" in html3
    assert "Human Draft Title" not in html3

    # 4. Set style on the element
    style_op = CreativeOperation(
        kind="set_style",
        project_id=rev3.project_id,
        parent_revision_id=rev3.revision_id,
        if_match=rev3.etag,
        params={
            "element_id": "hf-title",
            "styles": {"letter-spacing": "2px", "text-transform": "uppercase"},
        },
    )
    rev4, details4 = apply_creative_operation(config, context, style_op)
    assert rev4.parent_revision == rev3.revision_id
    html4 = (rev4.manifest_path.parent / "index.html").read_text(encoding="utf-8")
    assert "text-transform: uppercase" in html4


def test_malicious_script_and_event_injection_blocked(op_context):
    config, context, home = op_context
    hf_meta = {"width": 1920, "height": 1080}
    native = {
        "index.html": b"<html><body><div id='root'></div></body></html>",
        "hyperframes.json": json.dumps(hf_meta).encode("utf-8"),
    }
    rev1 = save_creative_revision(hf_meta, engine="hyperframes", native_files=native)

    # Forbidden script tag
    with pytest.raises(ValueError, match="Tag <script> is forbidden"):
        apply_creative_operation(
            config,
            context,
            CreativeOperation(
                kind="add_element",
                project_id=rev1.project_id,
                parent_revision_id=rev1.revision_id,
                params={"tag": "script", "text": "alert('xss')"},
            ),
        )

    # Forbidden event handlers (e.g. onerror, onload)
    with pytest.raises(ValueError, match="Executable attribute 'onerror' is forbidden"):
        apply_creative_operation(
            config,
            context,
            CreativeOperation(
                kind="add_element",
                project_id=rev1.project_id,
                parent_revision_id=rev1.revision_id,
                params={"tag": "img", "attributes": {"onerror": "alert(1)", "src": "x"}},
            ),
        )

    # Forbidden javascript: URL scheme
    with pytest.raises(ValueError, match="Dangerous URL scheme"):
        apply_creative_operation(
            config,
            context,
            CreativeOperation(
                kind="add_element",
                project_id=rev1.project_id,
                parent_revision_id=rev1.revision_id,
                params={"tag": "a", "attributes": {"href": "javascript:alert(1)"}},
            ),
        )

    # Forbidden CSS expression
    with pytest.raises(ValueError, match="Dangerous expression"):
        sanitize_styles({"width": "expression(alert(1))"})


def test_etag_conflict_in_concurrent_edits(op_context):
    config, context, home = op_context
    hf_meta = {"width": 1920, "height": 1080}
    native = {
        "index.html": b"<html><body><div id='root'></div></body></html>",
        "hyperframes.json": json.dumps(hf_meta).encode("utf-8"),
    }
    rev1 = save_creative_revision(hf_meta, engine="hyperframes", native_files=native)

    # Edit A from human
    op_a = CreativeOperation(
        kind="add_element",
        project_id=rev1.project_id,
        parent_revision_id=rev1.revision_id,
        if_match=rev1.etag,
        params={"tag": "p", "text": "Human Edit"},
    )
    rev_a, _ = apply_creative_operation(config, context, op_a)

    # Concurrent Edit B from agent still holding old rev1.etag
    op_b = CreativeOperation(
        kind="add_element",
        project_id=rev1.project_id,
        parent_revision_id=rev_a.revision_id,
        if_match=rev1.etag,  # Stale ETag!
        params={"tag": "p", "text": "Agent Concurrent Edit"},
    )
    with pytest.raises(CreativeConflictError, match="409 Conflict"):
        apply_creative_operation(config, context, op_b)

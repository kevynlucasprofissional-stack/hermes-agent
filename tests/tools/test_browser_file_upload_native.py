"""Desktop native file selection remains focus-independent and authority-scoped."""

import json

import pytest

from gateway.session_context import clear_session_vars, set_session_vars


def _in_session(source, callback):
    tokens = set_session_vars(platform=source, source=source, session_id="file-upload-chat")
    try:
        return callback()
    finally:
        clear_session_vars(tokens)


def test_upload_is_model_visible_in_desktop_toolset():
    from workstation.integrations.hermes.adapter import install_workstation_adapter
    from model_tools import get_tool_definitions

    install_workstation_adapter()

    def inspect():
        defs = get_tool_definitions(
            enabled_toolsets=["desktop_ui"], quiet_mode=True,
            skip_tool_search_assembly=True,
        )
        by_name = {entry["function"]["name"]: entry for entry in defs}
        assert "browser_file_upload" in by_name
        props = by_name["browser_file_upload"]["function"]["parameters"]["properties"]
        assert "files" in props and "selector" in props

    _in_session("desktop", inspect)


def test_upload_rejects_non_desktop_even_with_explicit_handler_call(monkeypatch):
    from tools import workstation_browser_upload_tool as upload

    monkeypatch.setattr(
        upload, "_native_upload",
        lambda **kwargs: pytest.fail("non-Desktop request reached native upload"),
    )

    def reject():
        result = json.loads(upload.handle_browser_file_upload(
            {"files": ["C:/tmp/test.jpg"]}, session_id="file-upload-chat",
            task_id="other-task", tool_call_id="call-0",
        ))
        assert result["error_code"] == "DESKTOP_SESSION_REQUIRED"

    _in_session("telegram", reject)


def test_upload_forwards_task_session_run_and_operation_to_native_route(monkeypatch):
    from tools import workstation_browser_upload_tool as upload

    calls = []

    def fake_route(**kwargs):
        calls.append(kwargs)
        return '{"status":"selected","file_count":1}'

    monkeypatch.setattr(upload, "_native_upload", fake_route)

    def invoke():
        result = json.loads(upload.handle_browser_file_upload(
            {"files": ["C:/fixtures/test.jpg"], "selector": 'input[type="file"][accept*="image"]'},
            session_id="file-upload-chat", task_id="task-123",
            run_id="run-123", tool_call_id="call-123",
        ))
        assert result == {"status": "selected", "file_count": 1}

    _in_session("desktop", invoke)
    assert len(calls) == 1
    assert calls[0]["action"] == "browser_file_upload"
    assert calls[0]["args"] == {
        "files": ["C:/fixtures/test.jpg"],
        "selector": 'input[type="file"][accept*="image"]',
    }
    assert (calls[0]["task_id"], calls[0]["session_id"],
            calls[0]["run_id"], calls[0]["operation_id"]) == (
                "task-123", "file-upload-chat", "run-123", "call-123")


@pytest.mark.parametrize("args", [
    {"files": []},
    {"files": ["C:/ok.jpg"], "allowed_roots": ["C:/"]},
    {"files": ["C:/ok.jpg"], "selector": 23},
])
def test_upload_rejects_malformed_args_before_native_dispatch(monkeypatch, args):
    from tools import workstation_browser_upload_tool as upload

    monkeypatch.setattr(
        upload, "_native_upload",
        lambda **kwargs: pytest.fail("invalid request reached native upload"),
    )

    def reject():
        result = json.loads(upload.handle_browser_file_upload(
            args, session_id="file-upload-chat",
        ))
        assert result["error_code"] == "INVALID_ARGUMENT"

    _in_session("desktop", reject)

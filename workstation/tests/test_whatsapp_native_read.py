"""Read-only WhatsApp BrowserTask DOM contracts, no real UI or sends."""
import json

from workstation.integrations.hermes.whatsapp_native_read import read_current_chat
from tools.whatsapp_catalog_adapter import read_messages_for_model


def test_native_read_bounded_messages_not_send():
    calls=[]
    def console(*, expression):
        calls.append(expression)
        return {"success":True, "runtime":"electron-chromium", "task_id":"owned-task",
                "result":{"originOk":True,"chatOpen":True,"messages":[
                    {"text":"Incoming hi","direction":"unknown","time_label":"09:21"},
                    {"text":"WA-HYB C11","direction":"outbound","time_label":"09:22"},
                ]}}
    result=read_current_chat(console=console,limit=2)
    assert result["success"] is True
    assert result["count"]==2
    assert result["messages"][0]["direction"]=="unknown"
    assert len(calls)==1
    assert "click(" not in calls[0] and "insertText" not in calls[0]


def test_native_read_does_not_claim_success_without_open_chat():
    got=read_current_chat(console=lambda **kw: {
        "success":True, "runtime":"electron-chromium","task_id":"owned-task",
        "result":{"originOk":True,"chatOpen":False,"messages":[]}})
    assert got["success"] is False
    assert got["error_code"]=="READ_CHAT_NOT_OPEN"


def test_name_directed_tool_routes_to_native_read(monkeypatch):
    import tools.browser_workstation as native
    calls=[]
    monkeypatch.setattr(native, "whatsapp_read_messages_named",
        lambda **kw: calls.append(kw) or {"success":True,"messages":[
            {"direction":"unknown","text":"Synthetic message","time_label":"13:04"}]})
    out=json.loads(read_messages_for_model(
        {"target_name":"Kevyn ACIRV","limit":4},session_id="test-session",tool_call_id="read-1"))
    assert out["success"] is True
    assert out["count"]==1
    assert calls==[{"target_name":"Kevyn ACIRV","limit":4,"session_id":"test-session",
                    "operation_id":"read-1"}]

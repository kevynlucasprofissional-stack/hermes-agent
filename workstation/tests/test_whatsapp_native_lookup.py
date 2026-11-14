"""Deterministic WhatsApp name lookup: exact chat, no send, no CRM dependency."""
import pytest

from workstation.integrations.hermes.whatsapp_native_lookup import (
    NativeNameLookupError, find_open_contact_by_name,
)


def _driver(*, ambiguous=False, wrong_name=False, missing_phone=False,
            require_enter=False, lost_focus=False, missing_close=False,
            close_loses_chat=False):
    state = {"phase": "ready", "clicks": [], "presses": [], "types": [],
             "snapshots": 0, "inspections": 0}
    common = {"success": True, "runtime": "electron-chromium",
              "task_id": "owned-task", "tab_id": "owned-tab",
              "url": "https://web.whatsapp.com/"}

    def snapshot():
        state["snapshots"] += 1
        elements = [{"ref": "search", "role": "textbox",
                     "label": "Pesquisar ou começar uma nova conversa"}]
        if state["phase"] == "typed" and (not require_enter or "Enter" in state["presses"]):
            elements.append({"ref": "contact", "role": "gridcell",
                             "label": "Kevyn ACIRV 15:10 último recado"})
            if ambiguous:
                elements.append({"ref": "contact2", "role": "gridcell",
                                 "label": "Kevyn ACIRV 15:11 outro contato"})
            elements.append({"ref": "group", "role": "gridcell",
                             "label": "VCOM 15:12 Kevyn ACIRV está no grupo"})
        if state["phase"] in {"chat", "drawer"}:
            elements.append({"ref": "header", "testid": "conversation-info-header-button"})
        if state["phase"] == "drawer" and not missing_close:
            elements.append({"ref": "close", "role": "button", "tag": "button",
                             "label": "Fechar"})
        return {**common, "elements": elements}

    def navigate(**kwargs):
        assert kwargs["url"] == "https://web.whatsapp.com/"
        return common

    def type_text(**kwargs):
        assert kwargs == {"ref": "search", "text": "Kevyn ACIRV"}
        state["types"].append(kwargs)
        state["phase"] = "typed"
        return common

    def inspect(**kwargs):
        state["inspections"] += 1
        selector = kwargs["selector"]
        if selector.startswith('input[aria-label='):
            rows = [] if lost_focus and selector.endswith(':focus') else [{"text": "", "attributes": {
                "aria-label": "Pesquisar ou começar uma nova conversa"}}]
        elif "cell-frame-title" in selector:
            rows = [{"attributes": {"title": "Kevyn ACIRV"}}]
            if ambiguous:
                rows.append({"attributes": {"title": "Kevyn ACIRV"}})
        elif "conversation-info-header-chat-title-name" in selector:
            rows = [] if state["phase"] == "closed" else [
                {"text": "Outro" if wrong_name else "Kevyn ACIRV",
                 "attributes": {"data-testid": "conversation-info-header-chat-title-name"}}
            ]
            if "conversation-compose-box-input" in selector and state["phase"] != "closed":
                rows.append({"text": "", "attributes": {
                    "data-testid": "conversation-compose-box-input"}})
        elif "section-about-and-phone-number" in selector:
            rows = [] if missing_phone else [
                {"text": "+55 11 99999-5506",
                 "attributes": {"data-testid": "container_with_separator"}}
            ]
        else:
            raise AssertionError(selector)
        return {**common, "schema_valid": True, "items": rows, "count": len(rows)}

    def click(*, ref):
        state["clicks"].append(ref)
        if ref == "contact":
            state["phase"] = "chat"
        elif ref == "header":
            state["phase"] = "drawer"
        elif ref == "close":
            state["phase"] = "closed" if close_loses_chat else "chat"
        else:
            raise AssertionError("wrong chat")
        return common

    def press(*, key):
        state["presses"].append(key)
        return common

    return state, dict(
        name="Kevyn ACIRV", navigate=navigate, snapshot=snapshot,
        type_text=type_text, click=click, inspect=inspect, press=press,
        ready_timeout=.1,
    )


def test_whatsapp_exact_contact_phone_from_drawer_not_group():
    state, args = _driver()
    phone = find_open_contact_by_name(**args)
    assert phone == "5511999995506"
    assert state["clicks"] == ["contact", "header", "close"]
    assert state["presses"] == []
    assert state["types"] and state["types"][0]["text"] == "Kevyn ACIRV"
    assert state["snapshots"] == 4  # readiness + match + opened chat + drawer close
    assert state["inspections"] >= 4


def test_whatsapp_enter_only_when_search_field_has_focus():
    state, args = _driver(require_enter=True)
    assert find_open_contact_by_name(**args) == "5511999995506"
    assert state["presses"] == ["Enter"]
    assert state["clicks"] == ["contact", "header", "close"]


def test_whatsapp_lost_search_focus_does_not_press_enter():
    state, args = _driver(require_enter=True, lost_focus=True)
    with pytest.raises(NativeNameLookupError, match="NATIVE_SEARCH_FOCUS_LOST"):
        find_open_contact_by_name(**args)
    assert state["presses"] == []
    assert state["clicks"] == []


def test_whatsapp_two_exact_candidates_never_click():
    state, args = _driver(ambiguous=True)
    with pytest.raises(NativeNameLookupError, match="NATIVE_NAME_AMBIGUOUS"):
        find_open_contact_by_name(**args)
    assert state["clicks"] == []


def test_whatsapp_wrong_open_header_never_read_phone():
    state, args = _driver(wrong_name=True)
    with pytest.raises(NativeNameLookupError, match="NATIVE_CHAT_NAME_MISMATCH"):
        find_open_contact_by_name(**args)
    assert state["clicks"] == ["contact"]
    assert state["presses"] == []

def test_whatsapp_missing_drawer_close_never_uses_escape():
    state, args = _driver(missing_close=True)
    with pytest.raises(NativeNameLookupError, match="NATIVE_DRAWER_CLOSE_NOT_UNIQUE"):
        find_open_contact_by_name(**args)
    assert state["clicks"] == ["contact", "header"]
    assert state["presses"] == []


def test_whatsapp_drawer_close_must_preserve_composer():
    state, args = _driver(close_loses_chat=True)
    with pytest.raises(NativeNameLookupError, match="NATIVE_CHAT_LOST_AFTER_DRAWER_CLOSE"):
        find_open_contact_by_name(**args)
    assert state["clicks"] == ["contact", "header", "close"]
    assert state["presses"] == []

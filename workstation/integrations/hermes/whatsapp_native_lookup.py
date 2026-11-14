"""Deterministic WhatsApp Web name -> phone resolution on the owned BrowserTask.

Only UI search/navigation, never composition or message dispatch. The phone is
returned privately to the existing native one-click sender.
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable


class NativeNameLookupError(Exception):
    pass


def find_open_contact_by_name(
    *, name: str, navigate: Callable[..., dict[str, Any]],
    snapshot: Callable[..., dict[str, Any]],
    type_text: Callable[..., dict[str, Any]],
    click: Callable[..., dict[str, Any]],
    inspect: Callable[..., dict[str, Any]],
    press: Callable[..., dict[str, Any]],
    ready_timeout: float = 40.0,
) -> str:
    """Return a verified full international number; keep the chat open.

    Expects a unique exact contact under WhatsApp's 'Conversas' search rows.
    The contact-info drawer is the phone-number authority, not a CRM name.
    """
    if not isinstance(name, str) or not 3 <= len(name.strip()) <= 100:
        raise NativeNameLookupError("INVALID_TARGET_NAME")
    name = name.strip()
    pinned: tuple[str, str] | None = None

    def validate(result: dict[str, Any]) -> dict[str, Any]:
        nonlocal pinned
        if not isinstance(result, dict) or result.get("success") is not True:
            raise NativeNameLookupError("NATIVE_SEARCH_UNAVAILABLE")
        if (result.get("runtime") != "electron-chromium"
                or not str(result.get("url") or "").startswith("https://web.whatsapp.com/")):
            raise NativeNameLookupError("NATIVE_OWNER_UNVERIFIED")
        if "task_id" in result and "tab_id" in result:
            identity = (str(result["task_id"]), str(result["tab_id"]))
            if pinned and pinned != identity:
                raise NativeNameLookupError("NATIVE_CONTEXT_CHANGED")
            pinned = identity
        return result

    def elements() -> list[dict[str, Any]]:
        response = validate(snapshot())
        return [x for x in response.get("elements") or [] if isinstance(x, dict)]

    def refs(items: list[dict[str, Any]], testid: str) -> list[str]:
        return [str(x["ref"]) for x in items
                if x.get("ref") and (x.get("testid")
                   or (x.get("attributes") or {}).get("data-testid")) == testid]

    validate(navigate(url="https://web.whatsapp.com/"))
    deadline = time.monotonic() + ready_timeout
    search_ref = None
    while time.monotonic() < deadline:
        # A full action-map snapshot is costly while WhatsApp initializes.
        # Inspect just the search input until mounted, then take one fresh
        # snapshot to obtain an actionable, tab-owned ref.
        found = validate(inspect(
            selector='input[aria-label="Pesquisar ou começar uma nova conversa"]',
            attributes=["aria-label"],
        ))
        if found.get("schema_valid") is not True or found.get("count") != len(found.get("items") or []):
            raise NativeNameLookupError("NATIVE_SEARCH_INSPECTION_INVALID")
        if found["count"] > 1:
            raise NativeNameLookupError("NATIVE_SEARCH_BOX_AMBIGUOUS")
        if found["count"] == 1:
            snapshot_items = elements()
            candidates = [
                x for x in snapshot_items
                if x.get("ref") and (x.get("role") == "textbox"
                    or x.get("tag") in {"input", "INPUT"})
                and "Pesquisar ou começar uma nova conversa" in str(
                    x.get("label") or x.get("name") or x.get("text") or "")
            ]
            if len(candidates) == 1:
                search_ref = str(candidates[0]["ref"])
                break
        time.sleep(.35)
    if not search_ref:
        raise NativeNameLookupError("NATIVE_SEARCH_BOX_UNAVAILABLE")

    # The native actionability resolver handles WhatsApp's transient scale
    # before typing. One operation only: no retry after an uncertain mutation.
    validate(type_text(ref=search_ref, text=name))
    match_ref = None
    enter_used = False
    search_deadline = time.monotonic() + 5.0
    while time.monotonic() < search_deadline:
        snapshot_items = elements()
        # Gridcell label is contact title + timestamp/message. A contact name
        # must start the row and be followed by a separator, never just a
        # substring in a group message (e.g. 'Kevyn ACIRV está no grupo').
        matches = [
            x for x in snapshot_items if x.get("ref")
            and x.get("role") == "gridcell"
            and re.match(r"^" + re.escape(name) + r"(?=\s|$)",
                         str(x.get("label") or x.get("text") or ""))
        ]
        if len(matches) > 1:
            raise NativeNameLookupError("NATIVE_NAME_AMBIGUOUS")
        if len(matches) == 1:
            match_ref = str(matches[0]["ref"])
            break
        if not enter_used and time.monotonic() + 3.0 >= search_deadline:
            # Some WhatsApp builds require Enter to apply the search.
            # Verify keyboard focus before pressing: Enter in a composer
            # could send a draft if WhatsApp changed focus unexpectedly.
            focused = validate(inspect(
                selector='input[aria-label="Pesquisar ou começar uma nova conversa"]:focus',
                attributes=["aria-label"],
            ))
            if len(focused.get("items") or []) != 1:
                raise NativeNameLookupError("NATIVE_SEARCH_FOCUS_LOST")
            validate(press(key="Enter"))
            enter_used = True
        time.sleep(.25)
    if not match_ref:
        raise NativeNameLookupError("NATIVE_CONTACT_NOT_FOUND")

    # The snapshot may contain a gridcell with prefix-match 'Name Jr'; check
    # the actual chat-list title, excluding groups and message search hits.
    candidates = validate(inspect(
        selector='[data-testid^="list-item-"] [data-testid="cell-frame-title"] span[title]',
        attributes=["title"],
    ))
    exact = [x for x in candidates.get("items") or []
             if (x.get("attributes") or {}).get("title") == name]
    if len(exact) != 1:
        raise NativeNameLookupError(
            "NATIVE_NAME_AMBIGUOUS" if len(exact) > 1 else "NATIVE_CONTACT_NOT_FOUND"
        )
    validate(click(ref=match_ref))
    # The chat header can mount after the search result was clicked on cold SPA
    # loads. This is a maximum, not a fixed delay; warm chats proceed at once.
    deadline = time.monotonic() + 15.0
    header_ref = None
    while time.monotonic() < deadline:
        rows = validate(inspect(
            selector='[data-testid="conversation-info-header-chat-title-name"]',
            attributes=["data-testid"],
        ))
        titles = [str(x.get("text") or "").strip() for x in rows.get("items") or []]
        if titles == [name]:
            header_items = elements()
            hs = refs(header_items, "conversation-info-header-button")
            if len(hs) == 1:
                header_ref = hs[0]
                break
        time.sleep(.25)
    if not header_ref:
        raise NativeNameLookupError("NATIVE_CHAT_NAME_MISMATCH")

    validate(click(ref=header_ref))
    phone_deadline = time.monotonic() + 5.0
    digits = ""
    while time.monotonic() < phone_deadline:
        rows = validate(inspect(
            selector='[data-testid="section-about-and-phone-number"] + '
                     '[data-testid="container_with_separator"]',
            attributes=["data-testid"],
        ))
        values = [str(row.get("text") or "") for row in rows.get("items") or []]
        if len(values) == 1:
            digits = "".join(ch for ch in values[0] if ch.isdecimal())
            if re.fullmatch(r"[1-9][0-9]{9,14}", digits):
                break
        time.sleep(.3)
    if not re.fullmatch(r"[1-9][0-9]{9,14}", digits):
        raise NativeNameLookupError("NATIVE_CONTACT_PHONE_UNAVAILABLE")
    # Escape closes the entire chat on WhatsApp Web, not merely the drawer.
    # Use the drawer's native close button, then prove the target conversation
    # and its composer remain mounted before handing off to the sender.
    close_candidates = [
        x for x in elements()
        if x.get("ref")
        and str(x.get("label") or "").strip().casefold() in {"fechar", "close"}
        and (str(x.get("role") or "").casefold() == "button"
             or str(x.get("tag") or "").casefold() == "button")
    ]
    if len(close_candidates) != 1:
        raise NativeNameLookupError("NATIVE_DRAWER_CLOSE_NOT_UNIQUE")
    validate(click(ref=str(close_candidates[0]["ref"])))
    still_open = validate(inspect(
        selector='[data-testid="conversation-info-header-chat-title-name"], '
                 '[data-testid="conversation-compose-box-input"]',
        attributes=["data-testid"],
    ))
    rows = still_open.get("items") or []
    title_ok = sum(
        (x.get("attributes") or {}).get("data-testid")
        == "conversation-info-header-chat-title-name"
        and str(x.get("text") or "").strip() == name
        for x in rows
    ) == 1
    composer_ok = sum(
        (x.get("attributes") or {}).get("data-testid")
        == "conversation-compose-box-input"
        for x in rows
    ) == 1
    if not (title_ok and composer_ok):
        raise NativeNameLookupError("NATIVE_CHAT_LOST_AFTER_DRAWER_CLOSE")
    return digits

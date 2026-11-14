"""Open a WhatsApp chat by number, verify phone in its UI before any compose/upload.

All action callbacks are scoped to the owned Hermes BrowserTask. Does not send.
"""
from __future__ import annotations

import re
import time
from typing import Any, Callable


class VerifiedPhoneError(Exception):
    pass


def open_verified_phone_chat(
    *, phone: str, navigate: Callable[..., dict[str, Any]],
    snapshot: Callable[..., dict[str, Any]],
    inspect: Callable[..., dict[str, Any]],
    click: Callable[..., dict[str, Any]],
    console: Callable[..., dict[str, Any]] | None = None,
    timeout_seconds: float = 26.0,
) -> str:
    phone = re.sub(r"\D", "", phone)
    if not re.fullmatch(r"[1-9]\d{10,14}", phone):
        raise VerifiedPhoneError("PHONE_INVALID")
    pinned: tuple[str, str] | None = None

    def verified(value: dict[str, Any]) -> dict[str, Any]:
        nonlocal pinned
        if not isinstance(value, dict) or value.get("success") is not True:
            raise VerifiedPhoneError("NATIVE_BROWSER_UNAVAILABLE")
        if value.get("runtime") != "electron-chromium" or not str(value.get("url") or "").startswith("https://web.whatsapp.com/"):
            raise VerifiedPhoneError("NATIVE_BROWSER_CONTEXT_INVALID")
        if value.get("task_id") and value.get("tab_id"):
            owner = (str(value["task_id"]), str(value["tab_id"]))
            if pinned is not None and owner != pinned:
                raise VerifiedPhoneError("BROWSER_OWNER_CHANGED")
            pinned = owner
        return value

    def rows(selector: str, attrs: list[str]) -> list[dict[str, Any]]:
        res=verified(inspect(selector=selector, attributes=attrs))
        items = res.get("items")
        if (res.get("schema_valid") is not True or not isinstance(items,list)
                or len(items) >= 64 or res.get("count") != len(items)):
            raise VerifiedPhoneError("PHONE_INSPECTION_INCOMPLETE")
        return items


    def click_button(find_refs: Callable[[dict[str, Any]], list[str]],
                     *, missing_code: str) -> None:
        # Wait *before* dispatch if the page overlay covers the header.
        # A target_obscured error is classified as pre-effect by Chromium, but
        # its durable admission can still block subsequent mutation IDs.
        # Therefore never replay a browser_click, even after that error.
        if console is not None and missing_code == "PHONE_HEADER_BUTTON_NOT_UNIQUE":
            script = """(function() {
                if (location.origin !== 'https://web.whatsapp.com')
                    return {origin_ok:false,ready:false};
                const nodes=document.querySelectorAll(
                    '[data-testid="conversation-info-header-button"]');
                if (nodes.length !== 1) return {origin_ok:true,ready:false};
                const btn=nodes[0],box=btn.getBoundingClientRect();
                const hit=document.elementFromPoint(
                    box.left+box.width/2,box.top+box.height/2);
                return {origin_ok:true,ready:box.width>0 && box.height>0 &&
                    !!hit && (hit===btn || btn.contains(hit))};
            })()"""
            ready_deadline=time.monotonic()+9.0
            while True:
                response=console(expression=script)
                check=response.get("result") if isinstance(response,dict) else None
                if (not isinstance(response,dict) or response.get("success") is not True
                        or response.get("runtime") != "electron-chromium"
                        or not isinstance(check,dict) or check.get("origin_ok") is not True):
                    raise VerifiedPhoneError("PHONE_HEADER_HITTEST_UNAVAILABLE")
                if (pinned is not None and response.get("task_id")
                        and str(response["task_id"]) != pinned[0]):
                    raise VerifiedPhoneError("BROWSER_OWNER_CHANGED")
                if check.get("ready") is True:
                    break
                if time.monotonic() >= ready_deadline:
                    raise VerifiedPhoneError("PHONE_HEADER_OBSCURED")
                time.sleep(.25)
        snap=verified(snapshot())
        refs=find_refs(snap)
        if len(refs)!=1:
            raise VerifiedPhoneError(missing_code)
        try:
            verified(click(ref=refs[0]))
        except VerifiedPhoneError:
            raise
        except Exception as exc:
            # Any click-response error is terminal; no automatic retry.
            label=str(getattr(exc,"error_code","") or str(exc)).lower()
            if label in {"target_obscured","target_outside_viewport"} or (
                label=="capability_missing"
                and str(exc).lower() in {"target_obscured","target_outside_viewport"}
            ):
                raise VerifiedPhoneError("PHONE_CLICK_PRE_EFFECT_REJECTED") from exc
            raise VerifiedPhoneError("PHONE_CLICK_UNCERTAIN") from exc

    verified(navigate(url=f"https://web.whatsapp.com/send?phone={phone}"))
    deadline=time.monotonic()+max(0.0,timeout_seconds)
    title=""
    while time.monotonic()<deadline:
        current=rows(
            '[data-testid="conversation-info-header"],'
            '[data-testid="conversation-info-header-chat-title-name"],'
            '[data-testid="conversation-compose-box-input"]',
            ["data-testid", "data-chat-id"],
        )
        titles=[str(x.get("text") or "").strip() for x in current
                if x["attributes"].get("data-testid")=="conversation-info-header-chat-title-name"]
        has_comp=sum(x["attributes"].get("data-testid")=="conversation-compose-box-input" for x in current)==1
        ids=[re.sub(r"\D","",str(x["attributes"].get("data-chat-id") or "").split("@")[0])
             for x in current if x["attributes"].get("data-testid")=="conversation-info-header"]
        if any(x and x!=phone for x in ids):
            raise VerifiedPhoneError("PHONE_CHAT_MISMATCH")
        if len(titles)==1 and has_comp:
            title=titles[0]
            break
        time.sleep(.2)
    if not title:
        raise VerifiedPhoneError("PHONE_CHAT_NOT_READY")
    if re.sub(r"\D","",title)==phone and not any(ch.isalpha() for ch in title):
        return title
    # Even if WhatsApp renders a saved name, never trust it as phone identity:
    # verify the exact phone in the contact info panel.
    click_button(
        lambda snap: [
            str(x["ref"]) for x in snap.get("elements") or []
            if x.get("testid")=="conversation-info-header-button" and x.get("ref")
        ],
        missing_code="PHONE_HEADER_BUTTON_NOT_UNIQUE",
    )
    phone_deadline=time.monotonic()+5
    actual=""
    while time.monotonic()<phone_deadline:
        detail=rows(
            '[data-testid="section-about-and-phone-number"] + '
            '[data-testid="container_with_separator"]',
            ["data-testid"],
        )
        if len(detail)==1:
            actual=re.sub(r"\D","",str(detail[0].get("text") or ""))
            if actual:
                break
        time.sleep(.2)
    if actual!=phone:
        raise VerifiedPhoneError("PHONE_CONTACT_INFO_MISMATCH")
    click_button(
        lambda snap: [
            str(x["ref"]) for x in snap.get("elements") or []
            if x.get("ref")
            and str(x.get("label") or "").strip().casefold() in {"fechar","close"}
            and str(x.get("role") or "").casefold()=="button"
        ],
        missing_code="PHONE_DRAWER_CLOSE_NOT_UNIQUE",
    )
    after=rows(
        '[data-testid="conversation-info-header-chat-title-name"],'
        '[data-testid="conversation-compose-box-input"]', ["data-testid"],
    )
    if (sum(x["attributes"].get("data-testid")=="conversation-info-header-chat-title-name"
            and str(x.get("text") or "").strip()==title for x in after)!=1
        or sum(x["attributes"].get("data-testid")=="conversation-compose-box-input" for x in after)!=1):
        raise VerifiedPhoneError("PHONE_CHAT_LOST_AFTER_DRAWER")
    return title

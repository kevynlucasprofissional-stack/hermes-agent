"""Verified image + caption via the same Hermes-owned Chromium BrowserTask."""
from __future__ import annotations

import hashlib
import re
import time
from typing import Any, Callable

from workstation.integrations.hermes.whatsapp_verified_phone import (
    VerifiedPhoneError, open_verified_phone_chat,
)
from workstation.integrations.hermes.whatsapp_native_send_bridge import MESSAGE_ID_PATTERN


def native_send_image_once(
    *, phone: str, caption: str, media_path: str,
    navigate: Callable[..., dict[str, Any]], snapshot: Callable[..., dict[str, Any]],
    inspect: Callable[..., dict[str, Any]], click: Callable[..., dict[str, Any]],
    type_text: Callable[..., dict[str, Any]],
    upload: Callable[..., dict[str, Any]], timeout: float = 12,
) -> dict[str, Any]:
    phase = "OPEN_CHAT"
    dispatched = False

    def stop(code: str, *, uncertain: bool = False) -> dict[str, Any]:
        return {
            "state": "UNCERTAIN" if (uncertain or dispatched) else "FAILED",
            "sent": False, "error_code": code,
            "failure_phase": "POST_SEND" if dispatched else phase,
            "independently_verified": False,
        }

    def valid(res: Any) -> dict[str, Any]:
        if not isinstance(res, dict) or res.get("success") is not True:
            raise ValueError("NATIVE_BROWSER_UNAVAILABLE")
        return res

    def read(selector: str, attrs: list[str]) -> list[dict[str, Any]]:
        result=valid(inspect(selector=selector, attributes=attrs))
        items=result.get("items")
        if (result.get("schema_valid") is not True or not isinstance(items,list)
                or len(items)>=64 or result.get("count")!=len(items)):
            raise ValueError("NATIVE_INSPECTION_INVALID")
        return items

    def action(snapshot_data: dict[str, Any], label: str) -> list[str]:
        return [
            str(x.get("ref"))
            for x in snapshot_data.get("elements") or []
            if x.get("ref") and (
                str(x.get("testid") or "").casefold()==label.casefold()
                or str(x.get("label") or "").strip().casefold()==label.casefold()
            )
        ]

    try:
        title=open_verified_phone_chat(
            phone=phone,navigate=navigate,snapshot=snapshot,
            inspect=inspect,click=click)
        phase="BASELINE"
        old_ids=set()
        for item in read('[data-id]:has([data-testid="msg-container"])', ["data-id"]):
            mid=(item.get("attributes") or {}).get("data-id")
            if isinstance(mid,str):
                old_ids.add(mid)
        phase="ATTACH_MENU"
        current=valid(snapshot())
        attach=action(current,"Anexar")
        if len(attach)!=1:
            attach=action(current,"attach-menu-plus")
        if len(attach)!=1:
            return stop("ATTACH_BUTTON_NOT_UNIQUE")
        valid(click(ref=attach[0]))
        file_inputs=read('input[type="file"]', ["type","accept","multiple"])
        images=[x for x in file_inputs if "image/" in str((x.get("attributes") or {}).get("accept") or "")]
        if len(images)!=1:
            return stop("IMAGE_FILE_INPUT_NOT_UNIQUE")
        phase="UPLOAD_SELECTION"
        selected=upload(files=[media_path])
        if (not isinstance(selected,dict) or selected.get("success") is not True
                or selected.get("status")!="selected" or selected.get("file_count")!=1):
            return stop("FILE_SELECTION_UNVERIFIED", uncertain=True)
        phase="PREVIEW"
        deadline=time.monotonic()+8
        caption_ref=None
        while time.monotonic()<deadline:
            fresh=valid(snapshot())
            refs=[
                str(x.get("ref"))
                for x in fresh.get("elements") or []
                if x.get("ref") and (
                    str(x.get("testid") or "")=="media-caption-input"
                    or ("legenda" in str(x.get("label") or "").casefold()
                        and str(x.get("role") or "").casefold() in {"textbox","input"})
                )
            ]
            if len(refs)==1:
                caption_ref=refs[0]
                break
            time.sleep(.2)
        if not caption_ref:
            return stop("MEDIA_CAPTION_INPUT_NOT_FOUND",uncertain=True)
        phase="CAPTION"
        valid(type_text(ref=caption_ref,text=caption))
        deadline=time.monotonic()+2.5
        caption_verified=False
        while time.monotonic()<deadline:
            found=read(
                '[data-testid="media-caption-input"],'
                '[contenteditable="true"][aria-label*="legenda"],'
                '[contenteditable="true"][aria-label*="Legenda"]',
                ["data-testid","aria-label"],
            )
            if len(found)==1 and str(found[0].get("text") or "")==caption:
                caption_verified=True
                break
            time.sleep(.1)
        if not caption_verified:
            return stop("MEDIA_CAPTION_MISMATCH",uncertain=True)
        phase="SEND"
        snap=valid(snapshot())
        candidates=action(snap,"Enviar")
        # Preview may expose a testid instead of an accessible button label.
        if not candidates:
            candidates=action(snap,"send")
        if len(candidates)!=1:
            return stop("MEDIA_SEND_BUTTON_NOT_UNIQUE",uncertain=True)
        # Exactly one click; never retry when the outcome becomes uncertain.
        dispatched=True
        clicked=click(ref=candidates[0])
        if not isinstance(clicked,dict) or clicked.get("success") is not True:
            return stop("MEDIA_CLICK_OUTCOME_UNKNOWN",uncertain=True)
        phase="RECEIPT"
        receipt_deadline=time.monotonic()+max(2,timeout)
        while time.monotonic()<receipt_deadline:
            messages=read('[data-id]:has([data-testid="msg-container"])',["data-id"])
            matches=[]
            for item in messages:
                attrs=item.get("attributes") or {}
                mid=attrs.get("data-id")
                if (isinstance(mid,str) and mid not in old_ids
                        and MESSAGE_ID_PATTERN.fullmatch(mid)
                        and caption in str(item.get("text") or "")):
                    matches.append(mid)
            if len(matches)>1:
                return stop("MEDIA_RECEIPT_AMBIGUOUS",uncertain=True)
            if len(matches)==1:
                mid=matches[0]
                detail=read(
                    f'[data-id="{mid}"] span.selectable-text, '
                    f'[data-id="{mid}"] [data-testid="msg-meta"] [aria-label]',
                    ["class","aria-label"],
                )
                bodies=[str(x.get("text") or "") for x in detail
                        if "selectable-text" in str((x.get("attributes") or {}).get("class") or "")]
                ack=[str((x.get("attributes") or {}).get("aria-label") or "").strip().lower()
                     for x in detail if (x.get("attributes") or {}).get("aria-label")]
                ackmap={"sent":"sent","enviado":"sent","enviada":"sent",
                        "delivered":"delivered","entregue":"delivered",
                        "read":"read","lida":"read","lido":"read"}
                if bodies==[caption] and len(ack)==1 and ack[0] in ackmap:
                    # Require that the new message also contains image content.
                    image=read(f'[data-id="{mid}"] img',["src","alt"])
                    if len(image)<1:
                        return stop("MEDIA_RECEIPT_WITHOUT_IMAGE",uncertain=True)
                    return {
                        "state":"OBSERVED","sent":False,
                        "error_code":"DOM_RECEIPT_ONLY","failure_phase":"POST_SEND",
                        "message_data_id":"sha256:"+hashlib.sha256(mid.encode()).hexdigest(),
                        "ack_label":ackmap[ack[0]],"header_verified":True,
                        "independently_verified":False,
                    }
            time.sleep(.2)
        return stop("MEDIA_RECEIPT_TIMEOUT",uncertain=True)
    except VerifiedPhoneError as exc:
        return stop(str(exc))
    except (ValueError,TypeError) as exc:
        code=str(exc)
        return stop(code if re.fullmatch(r"[A-Z_]{3,64}",code) else "MEDIA_NATIVE_ERROR")
    except Exception:
        return stop("MEDIA_NATIVE_ERROR",uncertain=dispatched or phase not in {"OPEN_CHAT","BASELINE","ATTACH_MENU"})

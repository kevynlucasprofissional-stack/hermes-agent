"""Read-only live WhatsApp campaign recipient verification.

Uses the same BrowserTask callbacks and exact phone validation as production.
Never composes, uploads, clicks Send, or persists a campaign checkpoint.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from tools.browser_workstation import _dispatch
from workstation.integrations.hermes.whatsapp_campaign_manifest import load_campaign
from workstation.integrations.hermes.whatsapp_verified_phone import (
    VerifiedPhoneError, open_verified_phone_chat,
)

SOURCE = (
    r"C:\Github\ACIRV-Notebook\000-Arquivos-originais"
    r"\AÇÕES COMUNICAÇÃO\10.11.26 Oficina Performe + Loja Virtual"
)


def run() -> int:
    campaign = load_campaign(SOURCE)
    phone = campaign.contacts[0].phone
    session = "wa-campaign-phone-smoke-" + uuid4().hex[:12]
    counts: dict[str, int] = {}

    def step(action: str, payload: dict) -> dict:
        number = counts.get(action, 0)
        counts[action] = number + 1
        operation = hashlib.sha256(
            f"{session}|{action}|{number}".encode()
        ).hexdigest()
        raw = _dispatch(
            action, payload, session_id=session, run_id=session,
            operation_id=operation, model_facing=False,
            session_scope_only=True,
        )
        return json.loads(raw) if isinstance(raw, str) else raw

    def safe_click(**kwargs):
        if counts.get("browser_click",0)==0:
            expression = """(function(){
                const header=document.querySelector('[data-testid="conversation-info-header"]');
                const btn=document.querySelector('[data-testid="conversation-info-header-button"]');
                const rect=btn?.getBoundingClientRect();
                const hit=rect?document.elementFromPoint(rect.left+rect.width/2,rect.top+rect.height/2):null;
                return {
                    headerIdPresent:!!header?.getAttribute('data-chat-id'),
                    headerIdMatches:String(header?.getAttribute('data-chat-id')||'').split('@')[0]==__PHONE__,
                    buttonCount:document.querySelectorAll('[data-testid="conversation-info-header-button"]').length,
                    hitTestPass:!!btn&&!!hit&&(btn===hit||btn.contains(hit)),
                    obstructionTestid:hit?.getAttribute('data-testid')||null,
                    obstructionTag:hit?.tagName||null,
                    composerCount:document.querySelectorAll('[data-testid="conversation-compose-box-input"]').length
                };
            })()""".replace("__PHONE__",json.dumps(phone))
            observation=step("browser_console",{"expression":expression})
            print("HEADER_DIAGNOSTIC",json.dumps(observation.get("result"),ensure_ascii=False))
        try:
            return step("browser_click", kwargs)
        except Exception as exc:
            print(json.dumps({
                "click_error_code":getattr(exc,"error_code",None),
                "click_error_type":type(exc).__name__,
                "click_state_changed":getattr(exc,"state_changed",None),
                "click_error_summary":str(exc)[:55],
            }))
            raise

    try:
        title = open_verified_phone_chat(
            phone=phone,
            navigate=lambda **kw: step("browser_navigate", kw),
            snapshot=lambda **kw: step("browser_snapshot", {"full":False}),
            inspect=lambda **kw: step("browser_extract_items", {
                "mode":"inspect", "selector":kw["selector"],
                "limit":64, "attributes":kw["attributes"]}),
            click=safe_click,
        )
        output = {
            "success":True, "contact_index":0, "title_present":bool(title),
            "verified_phone_suffix":phone[-4:],
            "calls":counts, "text_composed":False, "media_selected":False,
            "clicked_send":False,
        }
    except VerifiedPhoneError as exc:
        # Inspect DOM only; report selector shape and masked identity diagnostics.
        if str(exc)=="PHONE_CONTACT_INFO_MISMATCH":
            expr="""(function(){
                const section=document.querySelectorAll('[data-testid="section-about-and-phone-number"]');
                const sep=document.querySelectorAll('[data-testid="container_with_separator"]');
                const adj=document.querySelectorAll('[data-testid="section-about-and-phone-number"] + [data-testid="container_with_separator"]');
                const arr=Array.from(section).map(x=>({
                    text_length:(x.innerText||'').length,
                    text_digits:(x.innerText||'').replace(/\\D/g,'').length,
                    adjacent_count:x.nextElementSibling?.getAttribute('data-testid'),
                    descendants:Array.from(x.querySelectorAll('[data-testid]')).slice(0,8).map(y=>y.getAttribute('data-testid')),
                }));
                return {section_count:section.length,sep_count:sep.length,
                    adjacent_count:adj.length,section_info:arr,
                    chat_info_drawer:document.querySelectorAll('[data-testid="chat-info-drawer"]').length};
            })()"""
            res=step("browser_console",{"expression":expr})
            print("PANEL_DIAGNOSTIC",json.dumps(res.get("result"),ensure_ascii=False))
        output = {
            "success":False, "contact_index":0,
            "error_code":str(exc), "calls":counts,
            "text_composed":False, "media_selected":False,
            "clicked_send":False,
        }
    print(json.dumps(output,ensure_ascii=False))
    return 0 if output["success"] else 2


if __name__ == "__main__":
    raise SystemExit(run())

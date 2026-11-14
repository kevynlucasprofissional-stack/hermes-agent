"""Bounded, read-only extraction of current WhatsApp chat in the owned BrowserTask."""
from __future__ import annotations

from typing import Any, Callable

# A fixed, reviewable native DOM read. No user-supplied JavaScript, no events,
# no changes to WhatsApp. The last 50 mounted bubbles are returned in order.
_READ_DOM = r"""(function(){
  if(location.origin !== 'https://web.whatsapp.com')
    return {originOk:false,chatOpen:false,messages:[]};
  const root=document.querySelector('[data-testid="conversation-panel-messages"]');
  const rows=root?Array.from(root.querySelectorAll('[data-id]:has([data-testid="msg-container"])')):[];
  const items=rows.slice(-50).map(el=>{
    const chunks=Array.from(el.querySelectorAll('span.selectable-text'))
      .map(x=>String(x.innerText||x.textContent||'').trim()).filter(Boolean);
    const labels=Array.from(el.querySelectorAll('[data-testid="msg-meta"] [aria-label]'))
      .map(x=>String(x.getAttribute('aria-label')||'').trim().toLowerCase());
    const ack=labels.find(x=>['enviada','enviado','sent','entregue','delivered','lida','lido','read'].includes(x))||'';
    const text=chunks.join('\n').slice(0,1500);
    const time=String(el.querySelector('[data-testid="msg-meta"]')?.textContent||'')
      .match(/\b\d{1,2}:\d{2}\b/)?.[0]||'';
    return {text, direction:ack?'outbound':'unknown', ack, time_label:time};
  }).filter(x=>x.text);
  return {originOk:true,chatOpen:!!document.querySelector('[data-testid="conversation-compose-box-input"]'),
    messages:items};
})()"""


def read_current_chat(*, console: Callable[..., dict[str, Any]],
                      limit: int = 20) -> dict[str, Any]:
    if type(limit) is not int or not 1 <= limit <= 50:
        return {"success": False, "error_code": "INVALID_READ_LIMIT"}
    result = console(expression=_READ_DOM)
    if (not isinstance(result, dict) or result.get("success") is not True
            or result.get("runtime") != "electron-chromium"
            or not isinstance(result.get("task_id"), str) or not result["task_id"]):
        return {"success": False, "error_code": "NATIVE_READ_UNAVAILABLE"}
    payload = result.get("result")
    if (not isinstance(payload, dict) or payload.get("originOk") is not True
            or payload.get("chatOpen") is not True):
        return {"success": False, "error_code": "READ_CHAT_NOT_OPEN"}
    raw = payload.get("messages")
    if not isinstance(raw, list) or len(raw) > 50:
        return {"success": False, "error_code": "NATIVE_READ_INVALID"}
    messages = []
    for row in raw[-limit:]:
        if not isinstance(row, dict):
            return {"success": False, "error_code": "NATIVE_READ_INVALID"}
        text = row.get("text")
        direction = row.get("direction")
        if not isinstance(text, str) or direction not in {"inbound", "outbound", "unknown"}:
            return {"success": False, "error_code": "NATIVE_READ_INVALID"}
        if text:
            messages.append({"direction":direction,"text":text[:1500],
                             "time_label":str(row.get("time_label") or "")[:5]})
    return {"success":True,"messages":messages,"count":len(messages),
            "mode":"native_dom_read_only","persisted":False}

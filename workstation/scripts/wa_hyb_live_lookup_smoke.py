"""Authenticated native WhatsApp name-route smoke. No message composition/send.

Run ONLY when Hermes Desktop AI Control is active. The real browser resolves
the requested contact, but the backend sender is intercepted *before* any
composition or send click. No CRM writes and no WhatsApp send logs.
"""
from __future__ import annotations

import json
from uuid import uuid4

import workstation.integrations.hermes.whatsapp_browser_executor as executor
from tools.browser_workstation import whatsapp_send_message


def main() -> int:
    call = "wa-hyb-live-smoke-" + uuid4().hex[:12]
    observed: dict[str, str] = {}

    def never_dispatch(**kwargs):
        observed["phone_suffix"] = str(kwargs["phone_digits"])[-4:]
        observed["opened_name"] = str(kwargs.get("opened_chat_name") or "")
        return {"state": "FAILED", "sent": False,
                "error_code": "DRY_RUN_STOP_BEFORE_COMPOSE"}

    original = executor.whatsapp_send_message
    try:
        executor.whatsapp_send_message = never_dispatch
        result = whatsapp_send_message(
            target_name="Kevyn ACIRV", message="NO-SEND-DIAGNOSTIC",
            session_id=call, run_id=call, operation_id=call,
        )
    finally:
        executor.whatsapp_send_message = original
    print(json.dumps({
        "name_route_pass": (result.get("error_code") == "DRY_RUN_STOP_BEFORE_COMPOSE"
                            and observed.get("opened_name") == "Kevyn ACIRV"
                            and observed.get("phone_suffix") == "5506"),
        "safe_error_code": result.get("error_code"),
        "phone_suffix": observed.get("phone_suffix"),
        "message_composed": False, "send_clicked": False,
    }, ensure_ascii=False))
    return 0 if result.get("error_code") == "DRY_RUN_STOP_BEFORE_COMPOSE" else 2


if __name__ == "__main__":
    raise SystemExit(main())

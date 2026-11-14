"""Isolated synthetic repro: verify composer text before a WhatsApp send click.

The native executor belongs to another active M3 claim. Keep this case
strict xfail until its owner implements the production pre-dispatch verifier.
No Browser Runtime, CDP, authenticated account, or external effect is used.
"""

import pytest

from workstation.integrations.hermes.whatsapp_browser_executor import whatsapp_send_message


@pytest.mark.xfail(strict=True, reason="M3 owner: composer content is not yet checked before the click")
def test_wrong_composer_text_cannot_dispatch_even_with_correct_recipient():
    phone = "5511999990000"
    requested = "Synthetic requested text"
    prepared = "Synthetic DIFFERENT text"
    clicked = []

    before = {
        "elements": [
            {
                "attributes": {
                    "data-testid": "conversation-info-header",
                    "data-chat-id": f"{phone}@c.us",
                },
                "text": "Synthetic Contact",
            },
            {
                "attributes": {
                    "data-testid": "conversation-compose-box-input",
                    "contenteditable": "true",
                },
                "role": "textbox",
                "text": prepared,
            },
            {
                "attributes": {"data-testid": "send", "aria-label": "Enviar"},
                "role": "button",
                "ref": "@synthetic-send",
            },
        ],
    }

    def fake_click(*, ref):
        clicked.append(ref)
        return {"success": True}

    result = whatsapp_send_message(
        browser_navigate=lambda **_: {"success": True},
        browser_snapshot=lambda **_: before,
        browser_click=fake_click,
        phone_digits=phone,
        message=requested,
        contact_name_hint="Synthetic Contact",
        delivery_timeout_seconds=0.02,
        persist=False,
    )

    assert clicked == [], (
        "The executor clicked Send although the visible composer contained "
        "a different message. This is not a confirmed send."
    )
    assert result["sent"] is False
    assert result["state"] == "REVIEW_REQUIRED"

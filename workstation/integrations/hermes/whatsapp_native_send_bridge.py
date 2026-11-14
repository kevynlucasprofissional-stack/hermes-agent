"""Fast native-BrowserTask WhatsApp send: one destination read, one click, one receipt."""
from __future__ import annotations

import hashlib
import re
import time
from typing import Any, Callable

MESSAGE_ID_PATTERN = re.compile(r"(?:[0-9A-Fa-f]{22,64}|(?:true|false)_[0-9]{6,16}@[A-Za-z0-9.-]+_[A-Za-z0-9_-]{1,128})")


def native_send_once(
    *,
    browser_navigate: Callable[..., Any],
    browser_snapshot: Callable[..., Any],
    browser_click: Callable[..., Any],
    browser_inspect: Callable[..., Any],
    browser_type: Callable[..., Any],
    phone: str,
    message: str,
    session_context_verified: bool,
    timeout_seconds: float,
    chat_ready_timeout_seconds: float = 90.0,
    opened_chat_name: str | None = None,
) -> dict[str, Any]:
    dispatched = False
    phase = "PRE_SEND"

    def stop(code: str, state: str | None = None) -> dict[str, Any]:
        return {
            "sent": False,
            "state": state or ("UNCERTAIN" if dispatched else "FAILED"),
            "error_code": code,
            "failure_phase": "POST_SEND" if dispatched else phase,
            "independently_verified": False,
        }

    if not session_context_verified:
        return stop("SESSION_CONTEXT_REQUIRED")

    # Pin the native owner, not its URL: WhatsApp rewrites /send?phone=...
    # during chat loading without changing the BrowserTask or destination.
    pinned: dict[str, str | None] = {"task": None, "tab": None}

    def validate(result: Any) -> dict[str, Any]:
        if not isinstance(result, dict) or result.get("success") is not True:
            raise ValueError("NATIVE_BROWSER_UNAVAILABLE")
        url = str(result.get("url") or "")
        if (result.get("runtime") != "electron-chromium"
                or not url.startswith("https://web.whatsapp.com/")
                or not result.get("tab_id") or not result.get("task_id")):
            raise ValueError("NATIVE_OWNER_UNVERIFIED")
        if pinned["tab"] is not None and (
            result["tab_id"] != pinned["tab"]
            or result["task_id"] != pinned["task"]
        ):
            raise ValueError("NATIVE_CONTEXT_CHANGED")
        pinned.update(task=str(result["task_id"]), tab=str(result["tab_id"]))
        return result

    def inspect(selector: str, attrs: list[str]) -> list[dict[str, Any]]:
        response = validate(browser_inspect(selector=selector, attributes=attrs))
        items = response.get("items")
        if (response.get("schema_valid") is not True or not isinstance(items, list)
                or response.get("count") != len(items) or len(items) >= 64):
            raise ValueError("INSPECTION_INCOMPLETE")
        if any(not isinstance(item, dict) or not isinstance(item.get("attributes"), dict)
               for item in items):
            raise ValueError("INSPECTION_INVALID")
        return items

    def snap() -> dict[str, Any]:
        return validate(browser_snapshot())

    def digits(value: Any) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    def testid(element: dict[str, Any]) -> str:
        return str(element.get("testid") or (element.get("attributes") or {}).get("data-testid") or "")

    def refs(snapshot: dict[str, Any], wanted: str) -> list[str]:
        return [
            str(element["ref"])
            for element in snapshot.get("elements") or []
            if isinstance(element, dict) and element.get("ref") and testid(element) == wanted
        ]

    try:
        phase = "NAVIGATE"
        if opened_chat_name is not None:
            if not isinstance(opened_chat_name, str) or not opened_chat_name.strip():
                return stop("NATIVE_CONTACT_NAME_INVALID")
            # The native name lookup has already opened this exact chat and
            # read its full phone in the contact-info drawer on the same
            # BrowserTask. Never redirect to an inferred CRM name or self-chat.
            latest = snap()
        else:
            nav = browser_navigate(url=f"https://web.whatsapp.com/send?phone={phone}")
            if not isinstance(nav, dict) or nav.get("success") is False or nav.get("error"):
                return stop("NAVIGATION_FAILED")
            latest = validate(nav) if nav.get("runtime") == "electron-chromium" else snap()

        phase = "VERIFY_CHAT"
        # Keep identity inspection independent from message history: a chat
        # with many messages must not saturate the native 64-item limit.
        selector = (
            '[data-testid="conversation-info-header"], '
            '[data-testid="conversation-info-header-chat-title-name"], '
            '[data-testid^="list-item-"]:has([data-testid="message-yourself-row"]):has([data-testid="you-label"]) [data-testid="cell-frame-title"], '
            '[data-testid="conversation-compose-box-input"]'
        )
        attributes = [
            "data-testid", "data-chat-id", "data-id", "data-recipient-id",
            "data-direction", "aria-label",
        ]

        def check_chat_identity(rows: list[dict[str, Any]]) -> str | None:
            headers = [
                row for row in rows
                if row["attributes"].get("data-testid") == "conversation-info-header"
            ]
            chat_ids = [
                digits(str(row["attributes"].get("data-chat-id") or "").split("@", 1)[0])
                for row in headers
            ]
            # An explicit different native chat ID always blocks sending.
            if any(chat_id and chat_id != phone for chat_id in chat_ids):
                return "RECIPIENT_CHAT_MISMATCH"
            # Duplicate DOM wrappers do not imply duplicate recipients.
            # Chat identity alone is not readiness; the message composer must
            # also exist before the sender advances to COMPOSE.
            composers = [
                row for row in rows
                if row["attributes"].get("data-testid") == "conversation-compose-box-input"
            ]
            if len(composers) != 1:
                return "CHAT_NOT_READY"
            if opened_chat_name is not None:
                titles = [str(row.get("text") or "").strip() for row in rows
                          if row["attributes"].get("data-testid")
                          == "conversation-info-header-chat-title-name"]
                return None if titles == [opened_chat_name] else "CHAT_IDENTITY_UNVERIFIED"
            if headers and all(chat_id == phone for chat_id in chat_ids):
                return None

            # The live self-chat omits data-chat-id. Its visible chat header
            # and self-row contain the full phone; the composer aria-label
            # independently names that same destination.
            # Composer aria-label describes the input on real WhatsApp Web.
            # It may be generic ("Digite uma mensagem"), not a phone number.
            # Only use its number as supporting evidence for the sidebar case.
            composer_matches_phone = digits(composers[0]["attributes"].get("aria-label")) == phone
            own_rows = [
                row for row in rows
                if row["attributes"].get("data-testid") == "cell-frame-title"
            ]
            own_label_matches = (
                len(own_rows) == 1 and digits(own_rows[0].get("text")) == phone
            )
            # Exact phone-only active headers are valid when WhatsApp omits
            # the self-label. A conflicting named title still fails closed.
            header_text = str(headers[0].get("text") or "") if len(headers) == 1 else ""
            header_label_matches = (
                len(headers) == 1 and digits(header_text) == phone
                and ("voc" in header_text.casefold()
                     or not any(ch.isalpha() for ch in header_text))
            )
            return None if (header_label_matches or
                            (own_label_matches and composer_matches_phone)) else "CHAT_IDENTITY_UNVERIFIED"

        # WhatsApp is an SPA: navigation completion is not conversation readiness.
        # Wait for a unique composer AND proof of the target chat in the same
        # native tab. No fixed delay on the fast path; never send on timeout.
        ready_started = time.monotonic()
        ready_deadline = ready_started + max(0.0, float(chat_ready_timeout_seconds))
        while True:
            rows = inspect(selector, attributes)
            identity_error = check_chat_identity(rows)
            if identity_error is None:
                break
            if identity_error == "RECIPIENT_CHAT_MISMATCH":
                return stop(identity_error)
            if time.monotonic() >= ready_deadline:
                return stop("CHAT_READINESS_TIMEOUT" if identity_error == "CHAT_NOT_READY" else identity_error)
            # Adaptive polling: prompt response for warm chats, inexpensive
            # checks during long cold starts. Deadline is a maximum, not a delay.
            elapsed = time.monotonic() - ready_started
            time.sleep(0.15 if elapsed < 2.0 else 0.4 if elapsed < 12.0 else 0.75 if elapsed < 30.0 else 1.0)

        before: set[str] = set()
        # Snapshot message IDs separately from the small recipient proof.
        # The pre/post message window remains capped by the native inspector.
        for row in inspect(
            '[data-id]:has([data-testid="msg-container"])',
            ["data-id"],
        ):
            message_id = row["attributes"].get("data-id")
            if message_id is None:
                continue
            if not isinstance(message_id, str) or not MESSAGE_ID_PATTERN.fullmatch(message_id):
                return stop("MESSAGE_ID_INVALID")
            before.add(message_id)

        phase = "COMPOSE"
        # Navigation's snapshot may precede the WhatsApp SPA redirect.
        # Resolve the composer from the now-verified chat, not the stale page.
        latest = snap()
        composers = refs(latest, "conversation-compose-box-input")
        if len(composers) != 1:
            return stop("COMPOSER_NOT_UNIQUE")
        typed = browser_type(ref=composers[0], text=message)
        if not isinstance(typed, dict) or typed.get("success") is not True:
            return stop("COMPOSITION_FAILED")
        # Native inventory only exports `value` for HTML inputs, not the
        # WhatsApp contenteditable DIV. Verify its actual DOM text through the
        # isolated native inspector instead of trusting a snapshot label/value.
        composed_deadline = time.monotonic() + 1.5
        while True:
            composed = inspect('[data-testid="conversation-compose-box-input"]', ["data-testid"])
            if len(composed) == 1 and str(composed[0].get("text") or "") == message:
                break
            if time.monotonic() >= composed_deadline:
                return stop("COMPOSED_MESSAGE_MISMATCH")
            time.sleep(0.1)

        # The send icon appears only after WhatsApp accepts the draft; obtain
        # a fresh native inventory after the DOM has the exact message.
        # In WhatsApp the send icon may be a non-interactive SVG/span. The
        # native inventory marks its actionable footer button instead.
        # React may render that button just after the draft DOM changes.
        send_deadline = time.monotonic() + 1.5
        while True:
            latest = snap()
            send_controls = [
                str(element["ref"])
                for element in latest.get("elements") or []
                if isinstance(element, dict) and element.get("ref") and element.get("sendControl") is True
            ]
            sends = send_controls if send_controls else (
                refs(latest, "send") + refs(latest, "compose-btn-send")
            )
            if len(sends) > 1:
                return stop("SEND_BUTTON_AMBIGUOUS")
            if sends:
                break
            if time.monotonic() >= send_deadline:
                return stop("SEND_BUTTON_NOT_FOUND")
            time.sleep(0.1)

        # Exactly one send click. The returned Browser snapshot and message receipt
        # are the postcondition; no second click or sender-history sampling.
        phase = "SEND"
        dispatched = True
        clicked = browser_click(ref=sends[0])
        if not isinstance(clicked, dict) or clicked.get("success") is not True:
            return stop("CLICK_OUTCOME_UNKNOWN", "UNCERTAIN")
        validate(clicked) if clicked.get("runtime") == "electron-chromium" else snap()

        phase = "RECEIPT"
        deadline = time.monotonic() + max(float(timeout_seconds), 0.1)
        while time.monotonic() < deadline:
            after_rows = inspect(
                '[data-id]:has([data-testid="msg-container"])',
                ["data-id", "data-recipient-id", "data-direction"],
            )
            matches: dict[str, dict[str, Any]] = {}
            for row in after_rows:
                attrs = row["attributes"]
                message_id = attrs.get("data-id")
                if not isinstance(message_id, str) or not MESSAGE_ID_PATTERN.fullmatch(message_id):
                    return stop("MESSAGE_ID_INVALID", "UNCERTAIN")
                # WhatsApp lazily mounts older messages after the baseline.
                # A new DOM wrapper is NOT necessarily a newly sent message.
                # Only candidate wrappers containing our exact draft proceed
                # to message-scoped body + ACK verification below.
                if message_id not in before and message in str(row.get("text") or ""):
                    matches[message_id] = attrs
            if len(matches) > 1:
                return stop("CONCURRENT_MESSAGES_AMBIGUOUS", "UNCERTAIN")
            if len(matches) == 1:
                message_id, attrs = next(iter(matches.items()))
                recipient_id = attrs.get("data-recipient-id")
                if recipient_id and digits(str(recipient_id).split("@", 1)[0]) != phone:
                    return stop("OUTBOUND_RECIPIENT_MISMATCH", "UNCERTAIN")
                direction = str(attrs.get("data-direction") or "").casefold()
                if direction and direction not in {"outbound", "outgoing"}:
                    return stop("OUTBOUND_DIRECTION_MISMATCH", "UNCERTAIN")
                # WhatsApp's live message wrappers omit both optional fields;
                # the new ID, exact body and message-scoped sent/read ACK below
                # establish the observed outbound receipt for the verified chat.

                detail = inspect(
                    f'[data-id="{message_id}"] span.selectable-text, '
                    f'[data-id="{message_id}"] [data-testid="msg-meta"] [aria-label]',
                    ["class", "aria-label"],
                )
                bodies = [row for row in detail if "selectable-text" in str(row["attributes"].get("class") or "")]
                acks = [row for row in detail if row["attributes"].get("aria-label")]
                if len(bodies) == 1 and len(acks) == 1:
                    body = str(bodies[0].get("text") or "")
                    label = str(acks[0]["attributes"].get("aria-label") or "").strip().casefold()
                    ack_values = {
                        "read": {"read", "lida", "lido"},
                        "delivered": {"delivered", "entregue"},
                        "sent": {"sent", "enviada", "enviado"},
                    }
                    ack = next((name for name, values in ack_values.items() if label in values), "")
                    if body != message:
                        return stop("OUTBOUND_MESSAGE_MISMATCH", "UNCERTAIN")
                    if ack:
                        return {
                            "sent": False,
                            "state": "OBSERVED",
                            "ack_label": ack,
                            "message_data_id": "sha256:" + hashlib.sha256(message_id.encode()).hexdigest(),
                            "header_verified": True,
                            "independently_verified": False,
                            "error_code": "DOM_RECEIPT_ONLY",
                            "failure_phase": "POST_SEND",
                        }
            time.sleep(0.1)

        return stop("DOM_RECEIPT_TIMEOUT", "UNCERTAIN")
    except ValueError as exc:
        # Preserve explicit internal validation codes, never raw exception
        # text from the Browser (which may contain private DOM content).
        code = str(exc)
        if not dispatched and code in {
            "NATIVE_BROWSER_UNAVAILABLE", "NATIVE_OWNER_UNVERIFIED",
            "NATIVE_CONTEXT_CHANGED", "INSPECTION_INCOMPLETE",
            "INSPECTION_INVALID",
        }:
            return stop(code)
        return stop("POSTCLICK_NATIVE_CONTEXT_UNCERTAIN" if dispatched else "NATIVE_PREFLIGHT_FAILED")
    except Exception:
        return stop("POSTCLICK_NATIVE_CONTEXT_UNCERTAIN" if dispatched else "NATIVE_PREFLIGHT_FAILED")

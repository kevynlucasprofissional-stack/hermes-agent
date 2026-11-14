import json
from pathlib import Path


PHONE = "556492470988"
JID = f"{PHONE}@c.us"
MESSAGE = "Mensagem exata para teste"


def _native_result(*, chat_id=JID, sent=True, message_id="a" * 32,
                   header_count=1, self_row_phone=PHONE, composer_phone=PHONE,
                   include_self_fallback=True, header_text="", transient_identity=False,
                   include_receipt_metadata=True, composer_label=None, identity_initial_empty_reads=0,
                   history_count=0, inspect_url=None, inspect_tab_id="tab-A",
                   nav_composer_ready=True, ready_timeout_seconds=0.05,
                   composer_initial_empty_reads=0, composed_dom_text=None,
                   composer_late_reads=0, send_controls=None,
                   send_button_late_reads=0, late_history_after_click=0,
                   duplicate_canary_after_click=False,
                   opened_chat_name=None, opened_chat_title=None):
    from workstation.integrations.hermes.whatsapp_native_send_bridge import native_send_once

    clicks = []
    inspections = []
    composed = False
    send_snapshots = 0

    def snapshot(text=""):
        nonlocal send_snapshots
        send_elements = ([{"testid": "send", "ref": "send"}] if send_controls is None else
                         [{"ref": f"send-{i}", "role": "button", "label": "Enviar",
                           "sendControl": True} for i in range(send_controls)])
        if composed:
            send_snapshots += 1
            if send_snapshots <= send_button_late_reads:
                send_elements = []
        return {
            "success": True,
            "runtime": "electron-chromium",
            "task_id": "session-A",
            "tab_id": "tab-A",
            "url": f"https://web.whatsapp.com/send?phone={PHONE}",
            "elements": [
                {"testid": "conversation-info-header-button", "ref": "header"},
                {"testid": "conversation-compose-box-input", "ref": "composer", "text": text},
                *send_elements,
            ],
        }

    def inspect(*, selector, attributes):
        inspections.append(selector)
        if selector == '[data-testid="conversation-compose-box-input"]':
            compose_reads = sum(s == selector for s in inspections)
            content = (MESSAGE if composed_dom_text is None else composed_dom_text) if composed else ""
            if compose_reads <= composer_late_reads:
                content = ""
            rows = [{"text": content, "attributes": {"data-testid": "conversation-compose-box-input"}}]
        elif "conversation-info-header" in selector:
            rows = [{"text": header_text, "attributes": {
                "data-testid": "conversation-info-header",
                "data-chat-id": chat_id,
            }} for _ in range(header_count)]
            if header_count != 1 and include_self_fallback:
                rows.append({"text": self_row_phone, "attributes": {
                    "data-testid": "cell-frame-title"}})
            rows.append({"text": "", "attributes": {
                "data-testid": "conversation-compose-box-input",
                "aria-label": composer_label if composer_label is not None else
                              "Mensagem para " + composer_phone}})
            if opened_chat_name is not None:
                rows.append({"text": opened_chat_title or opened_chat_name,
                             "attributes": {
                                 "data-testid": "conversation-info-header-chat-title-name"}})
            identity_reads = sum("conversation-info-header" in q for q in inspections)
            if identity_reads <= composer_initial_empty_reads:
                rows = [row for row in rows if row["attributes"].get("data-testid") != "conversation-compose-box-input"]
            if (transient_identity and identity_reads == 1) or identity_reads <= identity_initial_empty_reads:
                rows = []
        elif selector.startswith('[data-id]:has'):
            rows = [{"text": "", "attributes": {
                "data-id": f"{i:032x}", "data-testid": "msg-container",
            }} for i in range(history_count)]
            if clicks:
                rows.extend({"text": f"Unrelated older message {i}", "attributes": {
                    "data-id": f"{i + 1000:032x}", "data-testid": "msg-container",
                }} for i in range(late_history_after_click))
                if duplicate_canary_after_click:
                    rows.append({"text": MESSAGE, "attributes": {
                        "data-id": "b" * 32, "data-testid": "msg-container",
                    }})
            if sent and clicks:
                rows.append({"text": MESSAGE, "attributes": {
                    "data-id": message_id,
                    "data-testid": "msg-container",
                    "data-direction": "outbound" if include_receipt_metadata else None,
                    "data-recipient-id": JID if include_receipt_metadata else None,
                }})
        elif "span.selectable-text" in selector and "msg-meta" in selector:
            rows = [
                {"text": MESSAGE, "attributes": {"class": "selectable-text"}},
                {"text": "", "attributes": {"aria-label": "sent"}},
            ]
        else:
            raise AssertionError(f"unexpected selector: {selector}")
        return {
            "success": True, "schema_valid": True, "runtime": "electron-chromium",
            "task_id": "session-A", "tab_id": inspect_tab_id,
            "url": inspect_url or f"https://web.whatsapp.com/send?phone={PHONE}",
            "items": rows, "count": len(rows),
        }

    def click(*, ref):
        clicks.append(ref)
        return snapshot(MESSAGE if ref == "send" else "")

    def type_text(*, ref, text):
        nonlocal composed
        assert ref == "composer"
        assert text == MESSAGE
        composed = True
        # Real inventory omits contenteditable text/value, even after typing.
        return {**snapshot(), "elements": [
            {"testid": "conversation-compose-box-input", "ref": "composer", "label": "Digite uma mensagem"},
            {"testid": "send", "ref": "send"},
        ]}

    result = native_send_once(
        browser_navigate=lambda **kwargs: (
            (_ for _ in ()).throw(AssertionError("must reuse opened chat"))
            if opened_chat_name is not None else
            ({**snapshot(), "elements": []} if not nav_composer_ready else snapshot())
        ),
        browser_snapshot=lambda: snapshot(),
        browser_click=click,
        browser_inspect=inspect,
        browser_type=type_text,
        phone=PHONE,
        message=MESSAGE,
        session_context_verified=True,
        timeout_seconds=0.5,
        chat_ready_timeout_seconds=ready_timeout_seconds,
        opened_chat_name=opened_chat_name,
    )
    return result, clicks, inspections


def test_named_chat_reuses_verified_open_conversation_without_reopening():
    result, clicks, _ = _native_result(
        chat_id=None, opened_chat_name="Kevyn ACIRV",
        opened_chat_title="Kevyn ACIRV",
    )
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]


def test_named_chat_conflicting_header_blocks_before_typing():
    result, clicks, _ = _native_result(
        chat_id=None, opened_chat_name="Kevyn ACIRV",
        opened_chat_title="Outro Contato",
    )
    assert result["state"] == "FAILED"
    assert result["error_code"] == "CHAT_IDENTITY_UNVERIFIED"
    assert clicks == []


def test_whatsapp_redirect_during_load_keeps_same_native_tab_and_exact_chat():
    # WhatsApp can replace /send?phone=... with its SPA home route after navigation.
    result, clicks, _ = _native_result(
        chat_id=None, header_text="+55 64 9247-0988 (Você)",
        composer_label="Digite uma mensagem", inspect_url="https://web.whatsapp.com/",
    )
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]


def test_delayed_composer_uses_fresh_snapshot_after_chat_identity():
    result, clicks, _ = _native_result(
        chat_id=None, header_text="+55 64 9247-0988 (Você)",
        composer_label="Digite uma mensagem", inspect_url="https://web.whatsapp.com/",
        nav_composer_ready=False,
    )
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]


def test_native_tab_change_still_fails_before_composition():
    result, clicks, _ = _native_result(inspect_tab_id="other-tab")
    assert result["state"] == "FAILED"
    assert result["error_code"] == "NATIVE_CONTEXT_CHANGED"
    assert clicks == []


def test_redirect_cannot_mask_wrong_active_recipient():
    result, clicks, _ = _native_result(
        chat_id="5511999999999@c.us", inspect_url="https://web.whatsapp.com/",
    )
    assert result["state"] == "FAILED"
    assert result["error_code"] == "RECIPIENT_CHAT_MISMATCH"
    assert clicks == []


def test_default_readiness_window_covers_measured_whatsapp_cold_start():
    from inspect import signature
    from workstation.integrations.hermes.whatsapp_native_send_bridge import native_send_once

    # Log 14 exhausted the previous 30 s limit without reaching composer.
    assert signature(native_send_once).parameters["chat_ready_timeout_seconds"].default == 90.0


def test_chat_load_after_30_seconds_does_not_timeout(monkeypatch):
    # Simulate a slow WhatsApp SPA using virtual time. Never actually wait
    # or send a message. The only click here is a local mock assertion.
    from types import SimpleNamespace
    from workstation.integrations.hermes import whatsapp_native_send_bridge as bridge

    elapsed = [0.0]
    monkeypatch.setattr(bridge, "time", SimpleNamespace(
        monotonic=lambda: elapsed[0],
        sleep=lambda seconds: elapsed.__setitem__(0, elapsed[0] + seconds),
    ))
    result, clicks, _ = _native_result(
        identity_initial_empty_reads=85,
        ready_timeout_seconds=90.0,
    )
    assert 30 < elapsed[0] < 90
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]


def test_chat_still_aborts_at_max_wait_without_typing_or_click(monkeypatch):
    from types import SimpleNamespace
    from workstation.integrations.hermes import whatsapp_native_send_bridge as bridge

    elapsed = [0.0]
    monkeypatch.setattr(bridge, "time", SimpleNamespace(
        monotonic=lambda: elapsed[0],
        sleep=lambda seconds: elapsed.__setitem__(0, elapsed[0] + seconds),
    ))
    result, clicks, _ = _native_result(
        identity_initial_empty_reads=1000,
        ready_timeout_seconds=90.0,
    )
    assert 90 <= elapsed[0] <= 92
    assert result["state"] == "FAILED"
    assert result["error_code"] == "CHAT_READINESS_TIMEOUT"
    assert result["failure_phase"] == "VERIFY_CHAT"
    assert clicks == []


def test_chat_ready_waits_for_real_header_and_composer_after_navigation():
    # 12 empty native DOM reads: the SPA finishes rendering after >1 second.
    result, clicks, inspections = _native_result(
        chat_id=None, header_text="+55 64 9247-0988 (Voce)",
        identity_initial_empty_reads=12, ready_timeout_seconds=3.0,
    )
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]
    assert sum("conversation-info-header" in q for q in inspections) == 13


def test_chat_ready_waits_for_composer_even_with_valid_header():
    result, clicks, inspections = _native_result(
        composer_initial_empty_reads=3, ready_timeout_seconds=1.0,
    )
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]
    assert sum("conversation-info-header" in q for q in inspections) == 4


def test_chat_never_sends_when_dom_never_becomes_ready():
    result, clicks, _ = _native_result(
        identity_initial_empty_reads=100, ready_timeout_seconds=0.1,
    )
    assert result["state"] == "FAILED"
    assert result["error_code"] == "CHAT_READINESS_TIMEOUT"
    assert result["failure_phase"] == "VERIFY_CHAT"
    assert clicks == []


def test_send_resolves_actionable_footer_button_with_nested_icon():
    # Current WhatsApp UI: the icon is non-interactive, while the enclosing
    # button is the only actionable element emitted by native inventory.
    result, clicks, _ = _native_result(send_controls=1)
    assert result["state"] == "OBSERVED"
    assert clicks == ["send-0"]


def test_send_button_render_delay_waits_without_retyping_or_double_click():
    result, clicks, _ = _native_result(send_controls=1, send_button_late_reads=3)
    assert result["state"] == "OBSERVED"
    assert clicks == ["send-0"]


def test_send_missing_button_fails_without_click():
    result, clicks, _ = _native_result(send_controls=0)
    assert result["state"] == "FAILED"
    assert result["error_code"] == "SEND_BUTTON_NOT_FOUND"
    assert result["failure_phase"] == "COMPOSE"
    assert clicks == []


def test_send_duplicate_footer_buttons_fail_without_click():
    result, clicks, _ = _native_result(send_controls=2)
    assert result["state"] == "FAILED"
    assert result["error_code"] == "SEND_BUTTON_AMBIGUOUS"
    assert result["failure_phase"] == "COMPOSE"
    assert clicks == []


def test_contenteditable_verified_from_dom_when_inventory_has_no_value():
    # Regression for log 12: WhatsApp DIV has no value/text in native inventory;
    # the isolated DOM inspector exposes its actual content.
    result, clicks, inspections = _native_result()
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]
    assert '[data-testid="conversation-compose-box-input"]' in inspections


def test_contenteditable_react_render_delay_waits_without_retyping():
    result, clicks, inspections = _native_result(composer_late_reads=3)
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]
    assert inspections.count('[data-testid="conversation-compose-box-input"]') == 4


def test_contenteditable_incorrect_draft_never_clicks_send():
    result, clicks, _ = _native_result(composed_dom_text=MESSAGE + " ALTERADO")
    assert result["state"] == "FAILED"
    assert result["error_code"] == "COMPOSED_MESSAGE_MISMATCH"
    assert result["failure_phase"] == "COMPOSE"
    assert clicks == []


def test_late_mounted_unrelated_history_does_not_block_receipt():
    # Regression for real log 16: stale virtualized wrappers mount after click.
    result, clicks, _ = _native_result(late_history_after_click=4)
    assert result["state"] == "OBSERVED"
    assert result["ack_label"] == "sent"
    assert clicks == ["send"]


def test_two_exact_canary_messages_remain_ambiguous_post_click():
    result, clicks, _ = _native_result(duplicate_canary_after_click=True)
    assert result["state"] == "UNCERTAIN"
    assert result["error_code"] == "CONCURRENT_MESSAGES_AMBIGUOUS"
    assert result["failure_phase"] == "POST_SEND"
    assert clicks == ["send"]


def test_fast_native_send_uses_chat_id_and_one_send_click_without_sender_history():
    result, clicks, inspections = _native_result()

    assert result["state"] == "OBSERVED"
    assert result["error_code"] == "DOM_RECEIPT_ONLY"
    assert clicks == ["send"]
    assert len(inspections) == 5


def test_identity_read_is_not_truncated_by_long_message_history():
    # 62 historical messages + header/composer exceed the native 64-item cap
    # if identity and history are queried together.
    result, clicks, inspections = _native_result(history_count=62)
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]
    assert len(inspections) == 5


def test_oversized_history_returns_specific_preflight_error_without_click():
    result, clicks, _ = _native_result(history_count=64)
    assert result["state"] == "FAILED"
    assert result["error_code"] == "INSPECTION_INCOMPLETE"
    assert result["failure_phase"] == "VERIFY_CHAT"
    assert clicks == []


def test_fast_native_send_accepts_current_whatsapp_message_id_shape():
    result, clicks, inspections = _native_result(
        message_id=f"true_{PHONE}@c.us_ABC123",
    )
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]


def test_fast_native_send_stops_on_wrong_chat_before_typing_or_clicking():
    result, clicks, inspections = _native_result(chat_id="5511999999999@c.us")

    assert result["state"] == "FAILED"
    assert result["error_code"] == "RECIPIENT_CHAT_MISMATCH"
    assert clicks == []
    assert len(inspections) == 1


def test_model_facing_send_requires_canonical_taskrun_not_session_only(monkeypatch):
    from tools.browser_tool import _handle_whatsapp_send_message

    calls = []
    monkeypatch.setattr(
        "tools.browser_workstation.whatsapp_send_message",
        lambda **kwargs: calls.append(kwargs),
    )
    args = {
        "recipient_ref": {"source": "hermes_local", "contact_id": 1},
        "expected_recipient_name": "Você",
        "message": MESSAGE,
    }
    result = json.loads(_handle_whatsapp_send_message(
        args, session_id="session-A", tool_call_id="call-A",
    ))

    assert result["state"] == "REVIEW_REQUIRED"
    assert result["error_code"] == "TASKRUN_AUTHORITY_REQUIRED"
    assert result["failure_phase"] == "VERIFY_TASKRUN"
    assert calls == []


def test_wrapper_resolves_recipient_once_and_accepts_session_scope(monkeypatch):
    import tools.browser_workstation as bridge
    import workstation.integrations.hermes.whatsapp_recipient_resolution as resolution
    import workstation.integrations.hermes.whatsapp_browser_executor as executor

    ref = {"source": "hermes_local", "contact_id": 1}
    recipient = resolution.ResolvedRecipient(
        ref, PHONE, f"+55 64 9247-0988 (Você)", Path("readonly.sqlite"),
    )
    lookups = []
    def resolve(value):
        lookups.append(value)
        return recipient
    monkeypatch.setattr(resolution, "resolve_recipient_reference", resolve)

    calls = []
    monkeypatch.setattr(executor, "whatsapp_send_message",
                        lambda **kwargs: (calls.append(kwargs) or {
                            "sent": False, "state": "OBSERVED", "error_code": "DOM_RECEIPT_ONLY",
                        }))
    monkeypatch.setattr(
        "workstation.integrations.hermes.whatsapp_contact_intake.promote_verified_contact",
        lambda *args, **kwargs: True,
    )
    result = bridge.whatsapp_send_message(
        recipient_ref=ref,
        expected_recipient_name="Você",
        message=MESSAGE,
        task_id=None,
        kanban_card_id=None,
        session_id="session-A",
        run_id="call-A",
        operation_id="call-A",
    )

    assert result["state"] == "OBSERVED"
    assert lookups == [ref]
    assert len(calls) == 1
    assert calls[0]["session_context_verified"] is True
    assert calls[0].get("expected_author") is None


def test_fast_native_send_without_header_uses_exact_self_chat_ui_proof():
    result, clicks, _ = _native_result(header_count=0)
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]


def test_fast_native_send_without_header_rejects_wrong_self_chat_composer():
    result, clicks, _ = _native_result(header_count=0, composer_phone="5511999999999")
    assert result["state"] == "FAILED"
    assert result["error_code"] == "CHAT_IDENTITY_UNVERIFIED"
    assert clicks == []


def test_fast_native_send_accepts_duplicate_headers_with_same_exact_chat_id():
    # Duplicated DOM wrappers are not two recipients; matching IDs are enough.
    result, clicks, _ = _native_result(
        header_count=2, include_self_fallback=False,
    )
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]


def test_live_self_chat_header_without_chat_id_uses_header_and_composer():
    # Observed live WhatsApp DOM: header contains the number, chat-id is absent.
    result, clicks, _ = _native_result(
        chat_id=None, header_text=f"+55 64 9247-0988 (Voc?)",
    )
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]


def test_real_chat_header_can_take_three_native_reads_to_render():
    # Pre-send navigation may resolve before WhatsApp renders the active chat.
    result, clicks, inspections = _native_result(
        chat_id=None, header_text="+55 64 9247-0988 (Voce)",
        identity_initial_empty_reads=3, ready_timeout_seconds=1.0,
    )
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]
    assert sum("conversation-info-header" in q for q in inspections) == 4


def test_live_self_chat_transient_header_ready_on_next_read():
    result, clicks, inspections = _native_result(
        chat_id=None, header_text=f"+55 64 9247-0988 (Voc?)",
        transient_identity=True, ready_timeout_seconds=1.0,
    )
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]
    assert sum("conversation-info-header" in q for q in inspections) == 2


def test_observed_new_message_without_optional_dom_direction_or_recipient():
    # Live WhatsApp message wrappers omit data-direction/data-recipient-id.
    result, clicks, _ = _native_result(include_receipt_metadata=False)
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]


def test_fast_native_send_rejects_conflicting_duplicate_headers():
    result, clicks, _ = _native_result(chat_id="5511999999999@c.us", header_count=2)
    assert result["state"] == "FAILED"
    assert clicks == []


def test_live_self_chat_header_with_generic_composer_aria_label():
    # WhatsApp's contenteditable label describes the field, not the addressee.
    result, clicks, _ = _native_result(
        chat_id=None,
        header_text=f"+55 64 9247-0988 (Voc{chr(234)})",
        composer_label="Digite uma mensagem",
    )
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]


def test_exact_phone_in_active_header_does_not_require_self_label():
    # The exact trusted destination in the active header is sufficient;
    # WhatsApp may omit the optional "Você" suffix.
    result, clicks, _ = _native_result(
        chat_id=None, header_text="+55 64 9247-0988",
        composer_label="Digite uma mensagem",
    )
    assert result["state"] == "OBSERVED"
    assert clicks == ["send"]


def test_generic_composer_without_matching_active_header_must_fail():
    result, clicks, _ = _native_result(
        chat_id=None, header_text="Outra pessoa",
        composer_label="Digite uma mensagem",
    )
    assert result["state"] == "FAILED"
    assert result["error_code"] == "CHAT_IDENTITY_UNVERIFIED"
    assert clicks == []


def test_generic_composer_and_matching_sidebar_alone_do_not_prove_active_chat():
    result, clicks, _ = _native_result(
        header_count=0, composer_label="Digite uma mensagem",
    )
    assert result["state"] == "FAILED"
    assert result["error_code"] == "CHAT_IDENTITY_UNVERIFIED"
    assert clicks == []


def test_generic_composer_and_number_in_other_header_do_not_prove_self_chat():
    result, clicks, _ = _native_result(
        chat_id=None, header_text=f"+55 64 9247-0988 (Contato)",
        composer_label="Digite uma mensagem",
    )
    assert result["state"] == "FAILED"
    assert result["error_code"] == "CHAT_IDENTITY_UNVERIFIED"
    assert clicks == []

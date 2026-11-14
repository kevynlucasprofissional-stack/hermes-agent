"""Owner-scoped, read-only WhatsApp metadata probing (no sends or PII)."""

from workstation.integrations.hermes.whatsapp_native_schema_probe import probe_native_schema


def _response(items, *, task="task-1", url="https://web.whatsapp.com/"):
    return {
        "success": True, "runtime": "electron-chromium",
        "task_id": task, "tab_id": "tab-1", "url": url,
        "count": len(items), "items": items, "schema_valid": True,
    }


def _item(testid, **attrs):
    return {"tag": "div", "text": "SECRET MESSAGE", "attributes": {
        "data-testid": testid, **attrs,
    }}


def test_requires_bound_identity_before_native_call():
    called = []
    result = probe_native_schema(
        task_id="", session_id="session", dispatcher=lambda **kw: called.append(kw)
    )
    assert result["status"] == "HOLD"
    assert result["reason"] == "TASK_IDENTITY_REQUIRED"
    assert not called


def test_home_screen_is_hold_and_does_not_return_dom_text():
    calls = []
    def fake(**kw):
        calls.append(kw)
        return _response([_item("wa-web-main-screen")])
    result = probe_native_schema(task_id="task-1", session_id="session-1", dispatcher=fake)
    assert result["reason"] == "CANARY_CHAT_NOT_SELECTED"
    assert result["can_send"] is False
    assert result["independently_verified"] is False
    assert len(calls) == 1
    assert calls[0]["action"] == "browser_extract_items"
    assert calls[0]["args"]["mode"] == "inspect"
    assert "SECRET MESSAGE" not in str(result)


def test_detects_correlated_structural_fields_without_certifying_delivery():
    sample = [
        _item("conversation-info-header", **{"data-chat-id": "15550000001@c.us"}),
        _item("msg-container", **{
            "data-id": "true_15550000001@c.us_123",
            "data-recipient-id": "15550000001@c.us",
            "data-direction": "outbound",
            "data-ack": "sent",
        }),
    ]
    result = probe_native_schema(
        task_id="task-1", session_id="session-1",
        dispatcher=lambda **kw: _response(sample)
    )
    assert result["status"] == "SCHEMA_OBSERVED"
    assert result["reason"] == "CANARY_RECEIPT_NOT_ATTESTED"
    assert result["matching_outbound_shapes"] == 1
    assert not result["can_send"] and not result["independently_verified"]
    assert "15550000001" not in str(result)
    assert "SECRET MESSAGE" not in str(result)


def test_wrong_browser_origin_and_owner_fail_closed():
    for payload in (
        _response([], url="https://example.com"),
        _response([], task="another-task"),
        {**_response([]), "runtime": "external-chrome"},
    ):
        result = probe_native_schema(
            task_id="task-1", session_id="session-1", dispatcher=lambda **kw: payload
        )
        assert result["status"] == "HOLD"
        assert result["reason"] == "NATIVE_OWNER_ORIGIN_UNVERIFIED"


def test_missing_ack_or_recipient_never_counts_as_structured_receipt():
    sample = [
        _item("conversation-info-header", **{"data-chat-id": "15550000001@c.us"}),
        _item("msg-container", **{"data-id": "true_15550000001@c.us_123"}),
    ]
    result = probe_native_schema(
        task_id="task-1", session_id="session-1",
        dispatcher=lambda **kw: _response(sample)
    )
    assert result["status"] == "HOLD"
    assert result["reason"] == "OUTBOUND_SCHEMA_INCOMPLETE"
    assert result["matching_outbound_shapes"] == 0


def test_incomplete_or_ambiguous_inventory_fails_closed():
    for response in (
        {**_response([]), "count": 65},
        {**_response([]), "schema_valid": False},
        {**_response([]), "success": False},
    ):
        result = probe_native_schema(
            task_id="task-1", session_id="session-1", dispatcher=lambda **kw: response
        )
        assert result["status"] == "HOLD"
        assert result["reason"] == "INSPECTION_INCOMPLETE"


def _real_dom_response(first: bool):
    header = _item("conversation-info-header")
    wrappers = [
        _item("conv-msg-AC05AF5BEF8EDE09A85ABA25C25EDC7C", **{
            "data-id": "AC05AF5BEF8EDE09A85ABA25C25EDC7C"}),
        _item("conv-msg-3EB0A803FD2AA061ED7021", **{
            "data-id": "3EB0A803FD2AA061ED7021"}),
    ]
    labels = [
        {"tag": "span", "text": "SECRET MESSAGE", "attributes": {"aria-label": "Lida"}},
        {"tag": "span", "text": "SECRET MESSAGE", "attributes": {"aria-label": "Read"}},
    ]
    return _response([header, *wrappers, *labels] if first else wrappers)


def test_real_dom_ancestral_ids_and_descendant_statuses_are_observed_but_hold():
    calls = []
    def dispatcher(**kw):
        calls.append(kw)
        return _real_dom_response(first=len(calls) == 1)

    result = probe_native_schema(task_id="task-1", session_id="session-1", dispatcher=dispatcher)

    assert result["status"] == "HOLD"
    assert result["reason"] == "RECIPIENT_DIRECTION_UNVERIFIED"
    assert result["message_nodes_with_ids"] == 2
    assert result["message_nodes_with_status"] == 2
    assert result["status_label_counts"] == {"read": 2}
    assert result["matching_outbound_shapes"] == 0
    assert result["can_send"] is False
    assert result["independently_verified"] is False
    assert len(calls) == 2
    assert '[data-id]:has([data-testid="msg-container"])' in calls[0]["args"]["selector"]
    assert '[data-id] [data-testid="msg-meta"] [aria-label]' in calls[0]["args"]["selector"]
    assert ':has([data-testid="msg-meta"] [aria-label])' in calls[1]["args"]["selector"]
    assert "SECRET MESSAGE" not in str(result)
    assert "AC05AF5B" not in str(result)


def test_real_dom_does_not_accept_unrelated_ancestral_ids_or_generic_metadata():
    sample = [
        _item("conversation-info-header"),
        _item("conv-msg-SOMETHING", **{"data-id": "A19D7C8B445F9800"}),
        _item("msg-meta", **{"aria-label": "Read"}),
    ]
    calls = []
    def dispatcher(**kw):
        calls.append(kw)
        return _response(sample)

    result = probe_native_schema(task_id="task-1", session_id="session-1", dispatcher=dispatcher)
    assert result["status"] == "HOLD"
    assert result["message_nodes_with_ids"] == 0
    assert result["matching_outbound_shapes"] == 0


def test_real_dom_status_inspect_owner_or_tab_drift_is_hold():
    calls = []
    def dispatcher(**kw):
        calls.append(kw)
        if len(calls) == 1:
            return _real_dom_response(first=True)
        return {**_real_dom_response(first=False), "tab_id": "wrong-tab"}

    result = probe_native_schema(task_id="task-1", session_id="session-1", dispatcher=dispatcher)
    assert result["status"] == "HOLD"
    assert result["reason"] == "NATIVE_OWNER_ORIGIN_UNVERIFIED"
    assert result["can_send"] is False


def test_real_dom_duplicate_message_ids_are_ambiguous():
    duplicated = [
        _item("conversation-info-header"),
        _item("conv-msg-AC05AF5BEF8EDE09A85ABA25C25EDC7C", **{
            "data-id": "AC05AF5BEF8EDE09A85ABA25C25EDC7C"}),
        _item("conv-msg-AC05AF5BEF8EDE09A85ABA25C25EDC7C", **{
            "data-id": "AC05AF5BEF8EDE09A85ABA25C25EDC7C"}),
    ]
    result = probe_native_schema(
        task_id="task-1", session_id="session-1",
        dispatcher=lambda **kw: _response(duplicated)
    )
    assert result["status"] == "HOLD"
    assert result["reason"] == "INSPECTION_AMBIGUOUS"
    assert result["matching_outbound_shapes"] == 0


def test_inspect_at_page_limit_is_not_trusted_as_complete():
    response = _response([_item("wa-web-main-screen") for _ in range(64)])
    result = probe_native_schema(
        task_id="task-1", session_id="session-1", dispatcher=lambda **kw: response
    )
    assert result["status"] == "HOLD"
    assert result["reason"] == "INSPECTION_INCOMPLETE"


def test_read_label_without_message_parent_link_remains_incomplete():
    calls = []
    def dispatcher(**kw):
        calls.append(kw)
        return _real_dom_response(first=len(calls) == 1) if len(calls) == 1 else _response([])
    result = probe_native_schema(task_id="task-1", session_id="session-1", dispatcher=dispatcher)
    assert result["status"] == "HOLD"
    assert result["reason"] == "OUTBOUND_SCHEMA_INCOMPLETE"
    assert result["message_nodes_with_ids"] == 2
    assert result["message_nodes_with_status"] == 0
    assert result["matching_outbound_shapes"] == 0


def _real_dom_with_identity(panel_phone: str | None, composer_phone: str):
    data = _real_dom_response(first=True)
    if panel_phone is not None:
        data["items"].append({
            "tag": "span", "text": panel_phone,
            "attributes": {"data-testid": "contact-info-subtitle selectable-text"},
        })
    data["items"].append({
        "tag": "div", "text": "",
        "attributes": {
            "data-testid": "conversation-compose-box-input",
            "aria-label": f"Digite uma mensagem para {composer_phone}",
        },
    })
    data["count"] = len(data["items"])
    return data


def test_real_ui_recipient_phone_crosscheck_is_observed_not_authority():
    from workstation.integrations.hermes.whatsapp_native_schema_probe import probe_native_schema

    calls = []
    def dispatcher(**kwargs):
        calls.append(kwargs)
        return (_real_dom_with_identity("+1 202 555 0147", "+1 202 555 0147")
                if len(calls) == 1 else _real_dom_response(first=False))

    result = probe_native_schema(task_id="task-1", session_id="session-1", dispatcher=dispatcher)
    assert result["ui_recipient_phone_consistent"] is True
    assert result["reason"] == "RECIPIENT_DIRECTION_UNVERIFIED"
    assert result["matching_outbound_shapes"] == 0
    assert result["can_send"] is False
    assert "555" not in str(result)
    assert "contact-info-subtitle" in calls[0]["args"]["selector"]
    assert "conversation-compose-box-input" in calls[0]["args"]["selector"]


def test_real_ui_recipient_mismatch_and_missing_panel_fail_closed():
    for panel, composer in (
        ("+1 202 555 0147", "+1 202 555 0174"),
        (None, "+1 202 555 0147"),
        ("+1 202 555 0147 / +1 202 555 0174", "+1 202 555 0147"),
    ):
        calls = []
        def dispatcher(**kwargs):
            calls.append(kwargs)
            return (_real_dom_with_identity(panel, composer)
                    if len(calls) == 1 else _real_dom_response(first=False))
        result = probe_native_schema(task_id="task-1", session_id="session-1", dispatcher=dispatcher)
        assert result["ui_recipient_phone_consistent"] is False
        assert result["status"] == "HOLD"
        assert result["can_send"] is False
        assert result["matching_outbound_shapes"] == 0


def test_historical_author_match_identifies_outbound_samples_without_send_authority():
    from workstation.integrations.hermes.whatsapp_native_schema_probe import assess_historical_author_direction

    def messages(name, n):
        return [f"[10:{i:02d}, 12/11/2026] {name}: " for i in range(n)]

    result = assess_historical_author_direction(
        own_chat_authors=messages("My own display name", 5),
        status_chat_authors=messages("My own display name", 2),
        no_status_chat_authors=messages("Other contact", 3),
    )
    assert result == {
        "status": "HISTORICAL_AUTHOR_MATCH",
        "reason": "HISTORICAL_TEXT_ONLY_NOT_A_SEND_RECEIPT",
        "self_author_samples": 5,
        "outbound_author_samples": 2,
        "other_author_samples": 3,
        "can_send": False,
        "independently_verified": False,
    }
    assert "My own" not in str(result)
    assert "Other contact" not in str(result)


def test_historical_author_direction_rejects_missing_or_changed_own_author():
    from workstation.integrations.hermes.whatsapp_native_schema_probe import assess_historical_author_direction

    fixed = dict(
        status_chat_authors=["[10:00, 12/11/2026] Own: ", "[10:01, 12/11/2026] Own: "],
        no_status_chat_authors=["[10:02, 12/11/2026] Other: ", "[10:03, 12/11/2026] Other: "],
    )
    for own in (
        [],
        ["[10:00, 12/11/2026] Own: "],
        ["[10:00, 12/11/2026] Own: ", "[10:01, 12/11/2026] Unrelated: "],
    ):
        result = assess_historical_author_direction(own_chat_authors=own, **fixed)
        assert result["status"] == "HOLD"
        assert result["reason"] in {"SELF_AUTHOR_UNVERIFIED", "HISTORICAL_SAMPLE_INSUFFICIENT"}
        assert result["can_send"] is False


def test_historical_author_direction_rejects_ambiguity_or_misidentified_group():
    from workstation.integrations.hermes.whatsapp_native_schema_probe import assess_historical_author_direction

    own = ["[10:00, 12/11/2026] Own: ", "[10:01, 12/11/2026] Own: "]
    for s, n in (
        (["[10:02, 12/11/2026] Other: "]*2, ["[10:04, 12/11/2026] Own: "]*2),
        (["[10:02, 12/11/2026] Own: "]*2, ["[10:04, 12/11/2026] Own: "]*2),
        (["[10:02, 12/11/2026] Own: ", "[10:03, 12/11/2026] Other: "],
         ["[10:04, 12/11/2026] Other: "]*2),
    ):
        result = assess_historical_author_direction(
            own_chat_authors=own, status_chat_authors=s, no_status_chat_authors=n
        )
        assert result["status"] == "HOLD"
        assert result["reason"] == "HISTORICAL_AUTHOR_AMBIGUOUS"
        assert not result["can_send"]


def test_historical_author_direction_rejects_malformed_or_too_small_sample():
    from workstation.integrations.hermes.whatsapp_native_schema_probe import assess_historical_author_direction

    own = ["[10:00, 12/11/2026] Own: "]*2
    for status in (
        ["message without author", "[10:02, 12/11/2026] Own: "],
        ["[10:02, 12/11/2026] Own: "],
    ):
        result = assess_historical_author_direction(
            own_chat_authors=own, status_chat_authors=status,
            no_status_chat_authors=["[10:05, 12/11/2026] Other: "]*3,
        )
        assert result["status"] == "HOLD"
        assert result["reason"] in {"HISTORICAL_AUTHOR_FORMAT_UNVERIFIED",
                                    "HISTORICAL_SAMPLE_INSUFFICIENT"}
        assert result["independently_verified"] is False

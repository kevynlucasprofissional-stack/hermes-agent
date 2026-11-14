"""Causal DOM receipt gate for an explicitly authorized self-chat canary."""

from workstation.integrations.hermes.whatsapp_causal_receipt import assess_causal_dom_receipt


A = "A" * 32
B = "B" * 32
C = "C" * 32
MARK = "WA-OPC-011-CANARY-20261112-NONCE"


def row(id, body="", ack="", author="Local Owner"):
    return {"id": id, "body": body, "ack": ack, "author": author}


def check(before=None, after=None, **kw):
    return assess_causal_dom_receipt(
        before=before if before is not None else [row(A, "historic text", "read")],
        after=after if after is not None else [row(A, "historic text", "read"), row(B, MARK, "read")],
        marker=MARK,
        expected_author="Local Owner",
        self_chat_verified=True,
        click_once_confirmed=True,
        **kw,
    )


def test_new_id_matching_body_author_and_ack_yields_dom_only_proof():
    result = check()
    assert result["status"] == "CAUSAL_DOM_RECEIPT_OBSERVED"
    assert result["reason"] == "DOM_STATUS_NOT_INDEPENDENT_SERVER_ACK"
    assert result["ack"] == "read"
    assert result["new_matching_messages"] == 1
    assert result["can_send"] is False
    assert result["independently_verified"] is False
    assert MARK not in str(result)
    assert "Local Owner" not in str(result)


def test_existing_marker_or_reused_id_cannot_be_relabelled_new():
    for before, after in [
        ([row(A, MARK, "read")], [row(A, MARK, "read")]),
        ([row(A, "old", "read")], [row(A, MARK, "read")]),
    ]:
        result = check(before=before, after=after)
        assert result["status"] == "HOLD" and not result["can_send"]


def test_wrong_direction_or_missing_ack_or_ambiguous_new_items_hold():
    samples = [
        [row(A, "old", "read"), row(B, MARK, "")],
        [row(A, "old", "read"), row(B, MARK, "delivered", author="Other")],
        [row(A, "old", "read"), row(B, MARK, "read"), row(C, MARK, "read")],
        [row(A, "old", "read"), row(B, MARK, "unknown")],
    ]
    for after in samples:
        result = check(after=after)
        assert result["status"] == "HOLD", result
        assert result["can_send"] is False


def test_duplicate_ids_and_invalid_id_fail_closed():
    for after in [
        [row(A, "old"), row(B, MARK, "read"), row(B, "other")],
        [row(A, "old"), row("not-opaque", MARK, "read")],
    ]:
        result = check(after=after)
        assert result["status"] == "HOLD"
        assert result["independently_verified"] is False


def test_unauthorized_self_chat_or_click_must_hold():
    for key in ("self_chat_verified", "click_once_confirmed"):
        kw = {"self_chat_verified": True, "click_once_confirmed": True}
        kw[key] = False
        result = assess_causal_dom_receipt(
            before=[row(A, "old")], after=[row(A, "old"), row(B, MARK, "read")],
            marker=MARK, expected_author="Local Owner", **kw
        )
        assert result["status"] == "HOLD" and not result["can_send"]

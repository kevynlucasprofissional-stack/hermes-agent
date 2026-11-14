"""Tests for WhatsApp Browser Executor — consolidated primitive per contract I-3 and P1 80/20.

Validates:
- Phone & message validation guards (MASKED_PHONE, TEMPLATE_PLACEHOLDER_LEAK).
- Immediate (<1s) fast-fail on invalid phone popup modal.
- Formal state transitions: PREPARED, DISPATCHING, OBSERVED, CONFIRMED, UNCERTAIN, FAILED, REVIEW_REQUIRED.
- Zero false positives: sent=True ONLY when delivery proof is confirmed.
- Persistence to whatsapp_control.db.
"""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock
import pytest

from workstation.integrations.hermes.whatsapp_browser_executor import (
    MAX_ATTACHMENT_SIZE_BYTES,
    STATE_CONFIRMED,
    STATE_FAILED,
    STATE_OBSERVED,
    STATE_REVIEW_REQUIRED,
    STATE_UNCERTAIN,
    WhatsAppSendError,
    _validate_attachment_file,
    _validate_message,
    _validate_phone,
    persist_send_result,
    whatsapp_read_messages,
    whatsapp_send_attachment,
    whatsapp_send_message,
)


class TestPhoneValidation:
    def test_valid_digits(self) -> None:
        assert _validate_phone("5564999733281") == "5564999733281"

    def test_strips_whitespace(self) -> None:
        assert _validate_phone("  5564999733281  ") == "5564999733281"

    def test_rejects_masked_phone(self) -> None:
        with pytest.raises(WhatsAppSendError, match="MASKED_PHONE"):
            _validate_phone("5564****3281")

    def test_rejects_non_numeric(self) -> None:
        with pytest.raises(WhatsAppSendError, match="MASKED_PHONE"):
            _validate_phone("+55 64 99973-3281")

    def test_rejects_empty(self) -> None:
        with pytest.raises(WhatsAppSendError, match="MASKED_PHONE"):
            _validate_phone("")


class TestMessageValidation:
    def test_valid_message(self) -> None:
        assert _validate_message("Olá, João!") == "Olá, João!"

    def test_rejects_unresolved_placeholder_nome(self) -> None:
        with pytest.raises(WhatsAppSendError, match="TEMPLATE_PLACEHOLDER_LEAK"):
            _validate_message("Olá, {NOME}!")

    def test_rejects_unresolved_placeholder_handlebars(self) -> None:
        with pytest.raises(WhatsAppSendError, match="TEMPLATE_PLACEHOLDER_LEAK"):
            _validate_message("Olá, {{name}}!")

    def test_rejects_unresolved_placeholder_lowercase(self) -> None:
        with pytest.raises(WhatsAppSendError, match="TEMPLATE_PLACEHOLDER_LEAK"):
            _validate_message("Olá, {nome}!")

    def test_rejects_empty_message(self) -> None:
        with pytest.raises(WhatsAppSendError, match="EMPTY_MESSAGE"):
            _validate_message("   ")

    def test_allows_resolved_template(self) -> None:
        assert _validate_message("Olá, Maria!") == "Olá, Maria!"


class TestWhatsappSendMessagePreValidation:
    """Pre-validation rejects bad inputs before any browser call."""

    def test_masked_phone_raises_before_browser_calls(self) -> None:
        nav = MagicMock()
        snap = MagicMock()
        click = MagicMock()

        with pytest.raises(WhatsAppSendError, match="MASKED_PHONE"):
            whatsapp_send_message(
                browser_navigate=nav,
                browser_snapshot=snap,
                browser_click=click,
                phone_digits="5564****3281",
                message="Hello",
                persist=False,
            )
        nav.assert_not_called()
        snap.assert_not_called()
        click.assert_not_called()

    def test_unresolved_placeholder_raises(self) -> None:
        with pytest.raises(WhatsAppSendError, match="TEMPLATE_PLACEHOLDER_LEAK"):
            whatsapp_send_message(
                browser_navigate=MagicMock(),
                browser_snapshot=MagicMock(),
                browser_click=MagicMock(),
                phone_digits="5564999733281",
                message="Olá, {NOME}!",
                persist=False,
            )


class TestWhatsappSendMessageNavigation:
    """Navigation and conversation-ready detection."""

    def test_navigation_failure_returns_state_failed(self) -> None:
        nav = MagicMock(side_effect=RuntimeError("browser down"))
        snap = MagicMock()
        click = MagicMock()

        result = whatsapp_send_message(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564999733281",
            message="Hello",
            delivery_timeout_seconds=0.1,
            persist=False,
        )
        assert result["sent"] is False
        assert result["state"] == STATE_FAILED
        assert result["error_code"] == "NAVIGATION_FAILED"
        snap.assert_not_called()
        click.assert_not_called()

    def test_no_conversation_open_on_timeout(self) -> None:
        nav = MagicMock(return_value={"success": True})
        snap = MagicMock(return_value={"elements": [
            {"attributes": {"data-testid": "pane-side"}, "text": "Chats"}
        ]})
        click = MagicMock()

        result = whatsapp_send_message(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564999733281",
            message="Hello",
            delivery_timeout_seconds=0.3,
            persist=False,
        )
        assert result["sent"] is False
        assert result["state"] == STATE_FAILED
        assert result["error_code"] == "NO_CONVERSATION_OPEN"
        click.assert_not_called()


class TestWhatsappSendMessageInvalidPhonePopup:
    """Fast-fail (<1s) detection when phone is invalid or not registered on WhatsApp."""

    def test_fast_fail_on_invalid_phone_modal_elements(self) -> None:
        nav = MagicMock(return_value={"success": True})
        # Modal appears immediately in first snapshot
        invalid_modal_snap = {
            "elements": [
                {
                    "attributes": {"data-testid": "popup-contents"},
                    "text": "O número de telefone compartilhado por link é inválido.",
                },
                {
                    "attributes": {"data-testid": "popup-controls-ok"},
                    "role": "button",
                    "text": "OK",
                    "ref": "@e_popup_ok",
                },
            ]
        }
        snap = MagicMock(return_value=invalid_modal_snap)
        click = MagicMock(return_value={"success": True})

        result = whatsapp_send_message(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564999999999",
            message="Teste de popup inválido",
            delivery_timeout_seconds=10.0,  # Must NOT wait 10s!
            persist=False,
        )

        assert result["sent"] is False
        assert result["state"] == STATE_FAILED
        assert result["error_code"] == "INVALID_PHONE_NUMBER"
        # Dismiss button was clicked
        click.assert_called_once_with(ref="@e_popup_ok")
        # Only polled once for the fast-fail!
        assert snap.call_count == 1

    def test_fast_fail_on_invalid_phone_snap_text(self) -> None:
        nav = MagicMock(return_value={"success": True})
        invalid_snap_text = {
            "snapshot": 'dialog "Aviso"\n  text "Número não encontrado no WhatsApp"\n  [@e55] button "OK"'
        }
        snap = MagicMock(return_value=invalid_snap_text)
        click = MagicMock(return_value={"success": True})

        result = whatsapp_send_message(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564888888888",
            message="Hello",
            delivery_timeout_seconds=5.0,
            persist=False,
        )

        assert result["sent"] is False
        assert result["state"] == STATE_FAILED
        assert result["error_code"] == "INVALID_PHONE_NUMBER"
        click.assert_called_once_with(ref="@e55")


class TestWhatsappSendMessageHeaderCheck:
    """Header verification against contact_name_hint (Destinatário incorreto)."""

    def _make_conversation_ready_snapshot(self, header_text: str) -> dict:
        return {"elements": [
            {
                "attributes": {"data-testid": "conversation-info-header", "data-chat-id": "5564999733281@c.us"},
                "text": header_text,
                "ref": "@e10",
            },
            {
                "attributes": {"data-testid": "send", "aria-label": "Enviar"},
                "role": "button",
                "ref": "@e20",
            },
        ]}

    def test_header_mismatch_returns_review_required(self) -> None:
        nav = MagicMock(return_value={"success": True})
        snap = MagicMock(return_value=self._make_conversation_ready_snapshot("Maria Silva"))
        click = MagicMock()

        result = whatsapp_send_message(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564999733281",
            message="Hello",
            contact_name_hint="João Silva",
            delivery_timeout_seconds=1.0,
            persist=False,
        )
        assert result["sent"] is False
        assert result["state"] == STATE_REVIEW_REQUIRED
        assert result["error_code"] == "HEADER_MISMATCH"
        assert result["header_verified"] == "Maria Silva"
        # Zero click on recipient mismatch
        click.assert_not_called()

    def test_header_match_proceeds_to_confirmed(self) -> None:
        nav = MagicMock(return_value={"success": True})
        ready_snap = self._make_conversation_ready_snapshot("João Silva")
        post_send_snap = {"elements": [
            {"attributes": {"data-testid": "conversation-info-header", "data-chat-id": "5564999733281@c.us"}, "text": "Carlos"},
            {"attributes": {"data-testid": "ptt-in-button"}, "text": ""},
            {"attributes": {"data-testid": "msg-container", "data-id": "true_5564999733281@c.us_ABC", "data-direction": "outbound", "data-recipient-id": "5564999733281@c.us", "data-ack": "sent"}, "text": "Hello João"},
        ]}
        snap = MagicMock(side_effect=[ready_snap, post_send_snap])
        click = MagicMock(return_value={"success": True})

        result = whatsapp_send_message(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564999733281",
            message="Hello João",
            contact_name_hint="João Silva",
            delivery_timeout_seconds=2.0,
            persist=False,
        )
        assert result["sent"] is True
        assert result["state"] == STATE_CONFIRMED
        assert result["message_data_id"].startswith("sha256:")
        assert result["ack_label"] == "sent"
        assert result["header_verified"] == "João Silva"
        assert result["composer_empty_after"] is True
        click.assert_called_once_with(ref="@e20")


class TestWhatsappSendMessagePostSendVerification:
    """Zero false positives: post-send confirmation and timeout handling."""

    def test_post_click_timeout_returns_state_uncertain(self) -> None:
        nav = MagicMock(return_value={"success": True})
        ready_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header", "data-chat-id": "5564999733281@c.us"}, "text": "Carlos"},
                {"attributes": {"data-testid": "send", "aria-label": "Enviar"}, "ref": "@e20"},
            ]
        }
        # Post-send snapshot: composer emptied, but NO message ack / data-id proof arrives
        empty_composer_no_proof_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header", "data-chat-id": "5564999733281@c.us"}, "text": "Carlos"},
            {"attributes": {"data-testid": "ptt-in-button"}, "text": ""},
            ]
        }
        snap = MagicMock(side_effect=[ready_snap, empty_composer_no_proof_snap, empty_composer_no_proof_snap])
        click = MagicMock(return_value={"success": True})

        result = whatsapp_send_message(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564999733281",
            message="Msg with timeout",
            delivery_timeout_seconds=0.4,
            persist=False,
        )

        # STRICT 80/20 INVARIANT: Never mark sent=True without delivery proof!
        assert result["sent"] is False
        assert result["state"] == STATE_UNCERTAIN
        assert result["error_code"] == "DELIVERY_TIMEOUT"
        assert result["composer_empty_after"] is True

    def test_verify_delivery_disabled_returns_observed(self) -> None:
        nav = MagicMock(return_value={"success": True})
        ready_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header", "data-chat-id": "5564999733281@c.us"}, "text": "Test User"},
                {"attributes": {"data-testid": "send", "aria-label": "Send"}, "ref": "@e20"},
            ]
        }
        snap = MagicMock(return_value=ready_snap)
        click = MagicMock(return_value={"success": True})

        result = whatsapp_send_message(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564999733281",
            message="Quick msg",
            verify_delivery=False,
            persist=False,
        )
        assert result["sent"] is False
        assert result["state"] == STATE_UNCERTAIN
        assert result.get("composer_empty_after") is not True

    def test_send_button_not_found_fails(self) -> None:
        nav = MagicMock(return_value={"success": True})
        snap = MagicMock(return_value={
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header", "data-chat-id": "5564999733281@c.us"}, "text": "No Send Button"},
            ]
        })
        click = MagicMock()

        result = whatsapp_send_message(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564999733281",
            message="No button",
            delivery_timeout_seconds=0.2,
            persist=False,
        )
        assert result["sent"] is False
        assert result["state"] == STATE_FAILED
        assert result["error_code"] == "SEND_BUTTON_NOT_FOUND"

    def test_click_stale_ref_fails(self) -> None:
        nav = MagicMock(return_value={"success": True})
        snap = MagicMock(return_value={
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header", "data-chat-id": "5564999733281@c.us"}, "text": "Stale Ref Chat"},
                {"attributes": {"data-testid": "send", "aria-label": "Enviar"}, "ref": "@e_stale"},
            ]
        })
        click = MagicMock(side_effect=RuntimeError("Element @e_stale is stale"))

        result = whatsapp_send_message(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564999733281",
            message="Stale test",
            delivery_timeout_seconds=0.5,
            persist=False,
        )
        assert result["sent"] is False
        assert result["state"] == STATE_UNCERTAIN
        assert result["error_code"] == "CLICK_OUTCOME_UNKNOWN"


class TestWhatsappSendMessagePersistence:
    """Persistence into whatsapp_control.db."""

    def test_persistence_records_confirmed_send(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        sqlite3.connect(db_file).close()
        nav = MagicMock(return_value={"success": True})
        ready_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header", "data-chat-id": "5564999733281@c.us"}, "text": "João Silva"},
                {"attributes": {"data-testid": "send", "aria-label": "Enviar"}, "ref": "@e20"},
            ]
        }
        post_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header", "data-chat-id": "5564999733281@c.us"}, "text": "Carlos"},
            {"attributes": {"data-testid": "ptt-in-button"}, "text": ""},
                {"attributes": {"data-testid": "msg-container", "data-id": "true_5564999733281@c.us_999", "data-direction": "outbound", "data-recipient-id": "5564999733281@c.us", "data-ack": "sent"}, "text": "Mensagem persistida"},
            ]
        }
        snap = MagicMock(side_effect=[ready_snap, post_snap])
        click = MagicMock(return_value={"success": True})

        result = whatsapp_send_message(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564999733281",
            message="Mensagem persistida",
            contact_name_hint="João Silva",
            task_id="task-p1-test",
            session_id="session-p1-test",
            run_id="run-p1-test",
            operation_id="op-p1-test",
            db_path=db_file,
            persist=True,
            delivery_timeout_seconds=2.0,
        )

        assert result["sent"] is True
        assert result["state"] == STATE_CONFIRMED
        assert "log_id" in result

        # Verify directly in SQLite
        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM whatsapp_send_logs").fetchall()
            assert len(rows) == 1
            row = dict(rows[0])
            assert row["phone_digits"] == "[redacted]"
            assert row["message_body"] == "[redacted]"
            assert "5564999733281" not in repr(row)
            assert "Mensagem persistida" not in repr(row)
            assert row["state"] == STATE_CONFIRMED
            assert row["sent"] == 1
            assert row["message_data_id"].startswith("sha256:")
            assert row["task_id"] == "task-p1-test"
            assert row["session_id"] == "session-p1-test"

    def test_persistence_records_uncertain_send(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        res = {
            "sent": False,
            "state": STATE_UNCERTAIN,
            "error_code": "DELIVERY_TIMEOUT",
            "composer_empty_after": True,
        }
        log_id = persist_send_result(
            res,
            phone_digits="5564999733281",
            message="Tentativa incerta",
            db_path=db_file,
        )
        assert log_id is not None

        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            row = dict(conn.execute("SELECT * FROM whatsapp_send_logs WHERE id=?", (log_id,)).fetchone())
            assert row["state"] == STATE_UNCERTAIN
            assert row["sent"] == 0
            assert row["error_code"] == "DELIVERY_TIMEOUT"


class TestWhatsappReadMessages:
    """Reading messages from active chat with snapshot-first extraction and deduplicated persistence."""

    def test_read_messages_no_conversation_open(self) -> None:
        snap = MagicMock(return_value={"elements": []})
        result = whatsapp_read_messages(browser_snapshot=snap, persist=False)
        assert result["success"] is False
        assert result["error_code"] == "NO_CONVERSATION_OPEN"
        assert result["count"] == 0

    def test_read_messages_header_mismatch(self) -> None:
        snap = MagicMock(return_value={
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "Carlos Santos"}
            ]
        })
        result = whatsapp_read_messages(browser_snapshot=snap, contact_name_hint="Maria", persist=False)
        assert result["success"] is False
        assert result["error_code"] == "HEADER_MISMATCH"
        assert result["header_verified"] == "Carlos Santos"

    def test_read_messages_inbound_and_outbound_extraction(self) -> None:
        snap = MagicMock(return_value={
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "João Silva"},
                {
                    "attributes": {
                        "data-id": "false_5564999733281@c.us_3EB011",
                        "data-testid": "msg-container",
                        "class": "message-in",
                    },
                    "text": "Olá Kevyn, tudo bem?\n14:30",
                },
                {
                    "attributes": {
                        "data-id": "true_5564999733281@c.us_3EB022",
                        "data-testid": "msg-container",
                        "class": "message-out",
                        "aria-label": "Tudo ótimo por aqui! 14:31, Lida",
                    },
                    "text": "Tudo ótimo por aqui!\n14:31",
                },
            ]
        })
        result = whatsapp_read_messages(browser_snapshot=snap, persist=False)
        assert result["success"] is True
        assert result["header_verified"] == "João Silva"
        assert result["count"] == 2

        inbound = result["messages"][0]
        assert inbound["direction"] == "inbound"
        assert inbound["text"] == "Olá Kevyn, tudo bem?"
        assert inbound["time_label"] == "14:30"
        assert inbound["whatsapp_msg_id"] == "false_5564999733281@c.us_3EB011"

        outbound = result["messages"][1]
        assert outbound["direction"] == "outbound"
        assert outbound["text"] == "Tudo ótimo por aqui!"
        assert outbound["time_label"] == "14:31"
        assert outbound["ack"] == "read"
        assert outbound["whatsapp_msg_id"] == "true_5564999733281@c.us_3EB022"

    def test_read_messages_deduplication_and_persistence(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        snap = MagicMock(return_value={
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "João Silva"},
                {
                    "attributes": {
                        "data-id": "false_5564999733281@c.us_3EB0AAA",
                        "data-testid": "msg-container",
                        "class": "message-in",
                    },
                    "text": "Primeira mensagem\n10:00",
                },
                {
                    "attributes": {
                        "data-id": "true_5564999733281@c.us_3EB0BBB",
                        "data-testid": "msg-container",
                        "class": "message-out",
                        "aria-label": "Resposta enviada, Entregue",
                    },
                    "text": "Resposta enviada\n10:01",
                },
            ]
        })

        # First read: persists 2 messages
        res1 = whatsapp_read_messages(browser_snapshot=snap, db_path=db_file, persist=True)
        assert res1["success"] is True
        assert res1["persisted_count"] == 2
        assert res1["updated_count"] == 0

        # Check DB directly
        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            contacts = conn.execute("SELECT * FROM contacts").fetchall()
            assert len(contacts) == 1
            assert contacts[0]["display_name"] == "João Silva"

            conversations = conn.execute("SELECT * FROM conversations").fetchall()
            assert len(conversations) == 1
            assert conversations[0]["last_message_preview"] == "Resposta enviada"

            messages = conn.execute("SELECT * FROM messages").fetchall()
            assert len(messages) == 2

        # Second read: exact same messages -> 0 new messages (deduplication!)
        res2 = whatsapp_read_messages(browser_snapshot=snap, db_path=db_file, persist=True)
        assert res2["success"] is True
        assert res2["persisted_count"] == 0
        assert res2["updated_count"] == 0

        with sqlite3.connect(db_file) as conn:
            messages = conn.execute("SELECT * FROM messages").fetchall()
            assert len(messages) == 2  # No duplicate rows!

    def test_read_messages_ack_upgrade(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        snap1 = MagicMock(return_value={
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "Cliente VIP"},
                {
                    "attributes": {
                        "data-id": "true_5564999733281@c.us_3EB0ACK",
                        "data-testid": "msg-container",
                        "class": "message-out",
                        "aria-label": "Enviada",
                    },
                    "text": "Mensagem aguardando leitura\n11:00",
                },
            ]
        })
        res1 = whatsapp_read_messages(browser_snapshot=snap1, db_path=db_file, persist=True)
        assert res1["persisted_count"] == 1

        with sqlite3.connect(db_file) as conn:
            row = conn.execute("SELECT delivered_at, viewed_at FROM messages WHERE whatsapp_msg_id = 'true_5564999733281@c.us_3EB0ACK'").fetchone()
            assert row[1] is None  # viewed_at is None initially

        # Later snapshot: same message is now "Lida" (read)
        snap2 = MagicMock(return_value={
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "Cliente VIP"},
                {
                    "attributes": {
                        "data-id": "true_5564999733281@c.us_3EB0ACK",
                        "data-testid": "msg-container",
                        "class": "message-out",
                        "aria-label": "Lida",
                    },
                    "text": "Mensagem aguardando leitura\n11:00",
                },
            ]
        })
        res2 = whatsapp_read_messages(browser_snapshot=snap2, db_path=db_file, persist=True)
        assert res2["persisted_count"] == 0
        assert res2["updated_count"] == 1

        with sqlite3.connect(db_file) as conn:
            row = conn.execute("SELECT delivered_at, viewed_at FROM messages WHERE whatsapp_msg_id = 'true_5564999733281@c.us_3EB0ACK'").fetchone()
            assert row[1] is not None  # viewed_at upgraded to CURRENT_TIMESTAMP!


class TestWhatsappSendAttachmentValidation:
    """Pre-validation for file attachment parameters before any browser action."""

    def test_rejects_nonexistent_file(self) -> None:
        with pytest.raises(WhatsAppSendError, match="FILE_NOT_FOUND"):
            _validate_attachment_file("C:/nonexistent/file/doc.pdf")

    def test_rejects_empty_file(self, tmp_path) -> None:
        empty_file = tmp_path / "empty.pdf"
        empty_file.write_bytes(b"")
        with pytest.raises(WhatsAppSendError, match="EMPTY_FILE"):
            _validate_attachment_file(empty_file)

    def test_rejects_unsupported_extension(self, tmp_path) -> None:
        bad_file = tmp_path / "script.exe"
        bad_file.write_bytes(b"payload")
        with pytest.raises(WhatsAppSendError, match="UNSUPPORTED_MEDIA_TYPE"):
            _validate_attachment_file(bad_file)

    def test_accepts_valid_image_and_document(self, tmp_path) -> None:
        img_file = tmp_path / "photo.png"
        img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)
        p, size, ctype = _validate_attachment_file(img_file)
        assert p.exists()
        assert size > 0
        assert ctype == "image"

        doc_file = tmp_path / "report.pdf"
        doc_file.write_bytes(b"%PDF-1.4" + b"\x00" * 100)
        p, size, ctype = _validate_attachment_file(doc_file)
        assert ctype == "document"

    def test_send_attachment_prevalidates_phone_and_file(self, tmp_path) -> None:
        valid_file = tmp_path / "test.pdf"
        valid_file.write_bytes(b"%PDF-1.4 sample")

        with pytest.raises(WhatsAppSendError, match="MASKED_PHONE"):
            whatsapp_send_attachment(
                browser_navigate=MagicMock(),
                browser_snapshot=MagicMock(),
                browser_click=MagicMock(),
                phone_digits="5564****3281",
                file_path=valid_file,
                persist=False,
            )

    def test_send_attachment_prevalidates_caption_leak(self, tmp_path) -> None:
        valid_file = tmp_path / "test.pdf"
        valid_file.write_bytes(b"%PDF-1.4 sample")

        with pytest.raises(WhatsAppSendError, match="TEMPLATE_PLACEHOLDER_LEAK"):
            whatsapp_send_attachment(
                browser_navigate=MagicMock(),
                browser_snapshot=MagicMock(),
                browser_click=MagicMock(),
                phone_digits="5564999733281",
                file_path=valid_file,
                caption="Aqui está seu relatório, {NOME}!",
                persist=False,
            )


class TestWhatsappSendAttachmentExecution:
    """Execution and delivery verification for send_attachment."""

    def test_send_attachment_fast_fail_on_invalid_phone(self, tmp_path) -> None:
        valid_file = tmp_path / "doc.pdf"
        valid_file.write_bytes(b"%PDF-1.4")
        nav = MagicMock(return_value={"success": True})
        invalid_snap = {
            "elements": [
                {"attributes": {"data-testid": "popup-controls-ok"}, "role": "button", "ref": "@e_dismiss"},
            ],
            "snapshot": 'dialog "Número não encontrado no WhatsApp"',
        }
        snap = MagicMock(return_value=invalid_snap)
        click = MagicMock(return_value={"success": True})

        result = whatsapp_send_attachment(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564888888888",
            file_path=valid_file,
            delivery_timeout_seconds=2.0,
            persist=False,
        )
        assert result["sent"] is False
        assert result["state"] == STATE_FAILED
        assert result["error_code"] == "INVALID_PHONE_NUMBER"
        click.assert_called_once_with(ref="@e_dismiss")

    def test_send_attachment_happy_path_confirmed(self, tmp_path) -> None:
        valid_file = tmp_path / "photo.png"
        valid_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        db_file = tmp_path / "whatsapp_control.db"

        nav = MagicMock(return_value={"success": True})
        ready_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "João Silva"},
                {"attributes": {"data-testid": "attach-menu-plus"}, "role": "button", "ref": "@e_attach"},
            ]
        }
        preview_snap = {
            "elements": [
                {"attributes": {"data-testid": "media-caption-input"}, "role": "textbox", "ref": "@e_caption"},
                {"attributes": {"data-testid": "send", "aria-label": "Enviar"}, "role": "button", "ref": "@e_send"},
            ]
        }
        post_snap = {
            "elements": [
                {"attributes": {"data-testid": "ptt-in-button"}, "text": ""},
                {"attributes": {"data-testid": "msg-meta", "data-id": "true_att_999", "aria-label": "Entregue"}},
            ]
        }

        snap = MagicMock(side_effect=[ready_snap, preview_snap, preview_snap, post_snap])
        click = MagicMock(return_value={"success": True})
        upload = MagicMock(return_value={"success": True})
        type_fn = MagicMock(return_value={"success": True})

        result = whatsapp_send_attachment(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            browser_file_upload=upload,
            browser_type=type_fn,
            phone_digits="5564999733281",
            file_path=valid_file,
            caption="Segue o comprovante",
            contact_name_hint="João",
            delivery_timeout_seconds=2.0,
            db_path=db_file,
            persist=True,
        )

        assert result["sent"] is True
        assert result["state"] == STATE_CONFIRMED
        assert result["message_data_id"] == "true_att_999"
        assert result["content_type"] == "image"
        upload.assert_called_once_with(files=[str(valid_file.resolve())])
        type_fn.assert_called_once_with(ref="@e_caption", text="Segue o comprovante")

        # Verify DB persistence
        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            logs = conn.execute("SELECT * FROM whatsapp_send_logs").fetchall()
            assert len(logs) == 1
            assert logs[0]["content_type"] == "image"
            assert logs[0]["media_path"] == str(valid_file.resolve())

            msgs = conn.execute("SELECT * FROM messages").fetchall()
            assert len(msgs) == 1
            assert msgs[0]["content_type"] == "image"
            assert msgs[0]["content_text"] == "Segue o comprovante"
            assert msgs[0]["whatsapp_msg_id"] == "true_att_999"

    def test_send_attachment_timeout_uncertain(self, tmp_path) -> None:
        valid_file = tmp_path / "doc.pdf"
        valid_file.write_bytes(b"%PDF-1.4" + b"\x00" * 50)

        nav = MagicMock(return_value={"success": True})
        ready_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "João Silva"},
                {"attributes": {"data-testid": "attach-menu-plus"}, "role": "button", "ref": "@e_attach"},
            ]
        }
        preview_snap = {
            "elements": [
                {"attributes": {"data-testid": "send", "aria-label": "Enviar"}, "role": "button", "ref": "@e_send"},
            ]
        }
        timeout_snap = {
            "elements": [
                {"attributes": {"data-testid": "ptt-in-button"}, "text": ""},
            ]
        }

        snap = MagicMock(side_effect=[ready_snap, preview_snap, preview_snap, timeout_snap, timeout_snap])
        click = MagicMock(return_value={"success": True})
        upload = MagicMock(return_value={"success": True})

        result = whatsapp_send_attachment(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            browser_file_upload=upload,
            phone_digits="5564999733281",
            file_path=valid_file,
            delivery_timeout_seconds=0.3,
            persist=False,
        )

        assert result["sent"] is False
        assert result["state"] == STATE_UNCERTAIN
        assert result["error_code"] == "DELIVERY_TIMEOUT"


class TestWhatsappBrowserWorkstationToolsIntegration:
    """Integration of read_messages and send_attachment in tools.browser_workstation."""

    def test_browser_workstation_read_messages_tool(self, monkeypatch) -> None:
        from tools import browser_workstation

        fake_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "Contato Teste"},
                {
                    "attributes": {"data-id": "false_5564_111", "data-testid": "msg-container"},
                    "text": "Mensagem via tool\n12:00",
                },
            ]
        }
        monkeypatch.setattr(browser_workstation, "_dispatch", lambda action, args, **kw: fake_snap)

        res = browser_workstation.whatsapp_read_messages(persist=False)
        assert res["success"] is True
        assert res["chat_title"] == "Contato Teste"
        assert res["count"] == 1
        assert res["messages"][0]["text"] == "Mensagem via tool"

    def test_browser_workstation_send_attachment_tool(self, tmp_path, monkeypatch) -> None:
        from tools import browser_workstation

        doc_file = tmp_path / "comprovante.pdf"
        doc_file.write_bytes(b"%PDF-1.4 sample content")

        ready_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "Contato Teste"},
                {"attributes": {"data-testid": "attach-menu-plus"}, "ref": "@e_att"},
            ]
        }
        preview_snap = {
            "elements": [
                {"attributes": {"data-testid": "send", "aria-label": "Enviar"}, "ref": "@e_snd"},
            ]
        }
        post_snap = {
            "elements": [
                {"attributes": {"data-testid": "ptt-in-button"}, "text": ""},
                {"attributes": {"data-testid": "msg-meta", "data-id": "true_att_tool_99", "aria-label": "Entregue"}},
            ]
        }

        snaps = [ready_snap, preview_snap, preview_snap, post_snap]
        def fake_dispatch(action, args, **kw):
            if action == "browser_snapshot":
                return snaps.pop(0) if snaps else post_snap
            return {"success": True}

        monkeypatch.setattr(browser_workstation, "_dispatch", fake_dispatch)

        res = browser_workstation.whatsapp_send_attachment(
            phone_digits="5564999733281",
            file_path=str(doc_file),
            delivery_timeout_seconds=2.0,
            persist=False,
        )
        assert res["sent"] is True
        assert res["state"] == STATE_CONFIRMED
        assert res["message_data_id"] == "true_att_tool_99"

# M3 causal regression contracts: all snapshots synthetic; no network or external WhatsApp effect.
def _m3_ready(*, phone="5564999733281", old=None):
    elements = [
        {"attributes": {"data-testid": "conversation-info-header", "data-chat-id": f"{phone}@c.us"}, "text": "Carlos"},
        {"attributes": {"data-testid": "send", "aria-label": "Enviar"}, "ref": "@send"},
    ]
    if old is not None:
        elements.append(old)
    return {"elements": elements}


def _m3_bubble(message_id, *, phone="5564999733281", body="Mensagem nova", direction="outbound", ack="sent"):
    return {"attributes": {
        "data-testid": "msg-container",
        "data-id": message_id,
        "data-direction": direction,
        "data-recipient-id": f"{phone}@c.us",
        "data-ack": ack,
    }, "text": body}


def _m3_run(ready, after, **kwargs):
    # Full post-action browser snapshots retain the verified conversation identity.
    after = {**after, "elements": [_m3_ready()["elements"][0], *after.get("elements", [])]}
    return whatsapp_send_message(
        browser_navigate=MagicMock(return_value={"success": True}),
        browser_snapshot=MagicMock(side_effect=[ready] + [after] * 10),
        browser_click=MagicMock(return_value={"success": True}),
        phone_digits="5564999733281",
        message="Mensagem nova",
        delivery_timeout_seconds=0.05,
        persist=False,
        **kwargs,
    )


@pytest.mark.parametrize("bubble", [
    _m3_bubble("true_5564999733281@c.us_OLD"),
    _m3_bubble("true_5564999733281@c.us_NEW", phone="5564888888888"),
    _m3_bubble("true_5564999733281@c.us_NEW", body="Outra mensagem"),
    _m3_bubble("false_5564999733281@c.us_NEW", direction="inbound"),
])
def test_m3_rejects_stale_wrong_target_body_or_inbound(bubble):
    old = bubble if "OLD" in bubble["attributes"]["data-id"] else None
    result = _m3_run(_m3_ready(old=old), {
        "elements": [
            {"attributes": {"data-testid": "ptt-in-button"}},
            bubble,
        ],
    })
    assert result["sent"] is False
    assert result["state"] == STATE_UNCERTAIN


def test_m3_confirms_only_one_new_correlated_outbound_with_ack():
    old = _m3_bubble("true_5564999733281@c.us_OLD", body="Mensagem antiga")
    new = _m3_bubble("true_5564999733281@c.us_NEW")
    result = _m3_run(_m3_ready(old=old), {"elements": [
        {"attributes": {"data-testid": "ptt-in-button"}}, old, new,
    ]})
    assert result["sent"] is True
    assert result["state"] == STATE_CONFIRMED


def test_m3_rejects_generic_msg_meta_and_duplicate_candidates():
    duplicate_a = _m3_bubble("true_5564999733281@c.us_A")
    duplicate_b = _m3_bubble("true_5564999733281@c.us_B")
    for elements in (
        [{"attributes": {"data-testid": "msg-meta", "data-id": "true_5564999733281@c.us_A", "aria-label": "Entregue"}}],
        [duplicate_a, duplicate_b],
    ):
        result = _m3_run(_m3_ready(), {"elements": [
            {"attributes": {"data-testid": "ptt-in-button"}}, *elements,
        ]})
        assert result["sent"] is False
        assert result["state"] == STATE_UNCERTAIN


def test_m3_post_dispatch_click_error_stays_uncertain():
    result = whatsapp_send_message(
        browser_navigate=MagicMock(return_value={"success": True}),
        browser_snapshot=MagicMock(return_value=_m3_ready()),
        browser_click=MagicMock(side_effect=TimeoutError("click returned too late")),
        phone_digits="5564999733281", message="Mensagem nova",
        delivery_timeout_seconds=0.05, persist=False,
    )
    assert result["state"] == STATE_UNCERTAIN
    assert result["sent"] is False


def test_m3_no_delivery_verification_never_infers_composer_empty():
    result = _m3_run(_m3_ready(), _m3_ready(), verify_delivery=False)
    assert result["sent"] is False
    assert result.get("composer_empty_after") is not True
    assert result["state"] == STATE_UNCERTAIN


def test_m3_persisted_intent_precedes_click_and_blocks_restart_duplicate(tmp_path):
    db = tmp_path / "control.db"
    sqlite3.connect(db).close()
    clicked = []
    def click(*, ref):
        with sqlite3.connect(db) as conn:
            row = conn.execute("SELECT state, operation_id, message_digest FROM whatsapp_send_logs").fetchone()
        assert row and row[0] in ("PREPARED", "DISPATCHING")
        assert row[1] == "op-m3-1"
        assert row[2]
        clicked.append(ref)
        return {"success": True}
    kw = dict(
        browser_navigate=MagicMock(return_value={"success": True}),
        browser_snapshot=MagicMock(side_effect=[_m3_ready(), {"elements": []}] * 10),
        browser_click=click, phone_digits="5564999733281", message="Mensagem nova",
        db_path=db, persist=True, operation_id="op-m3-1",
        task_id="task-m3", session_id="session-m3", run_id="run-m3",
        delivery_timeout_seconds=0.05,
    )
    first = whatsapp_send_message(**kw)
    assert clicked == ["@send"]
    assert first["state"] == STATE_UNCERTAIN
    kw["browser_snapshot"] = MagicMock()
    second = whatsapp_send_message(**kw)
    assert second["sent"] is False
    assert second["state"] == STATE_UNCERTAIN
    assert clicked == ["@send"]
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM whatsapp_send_logs WHERE operation_id='op-m3-1'").fetchone()[0] == 1

def test_m3_invalid_phone_popup_english_fails_before_dispatch():
    nav = MagicMock(return_value={"success": True})
    invalid = {"elements": [
        {"attributes": {"data-testid": "popup-contents"},
         "text": "The phone number shared via URL is invalid"},
        {"attributes": {"data-testid": "popup-controls-ok"},
         "text": "OK", "role": "button", "ref": "@ok"},
    ]}
    snap = MagicMock(return_value=invalid)
    click = MagicMock(return_value={"success": True})
    result = whatsapp_send_message(
        browser_navigate=nav,
        browser_snapshot=snap,
        browser_click=click,
        phone_digits="5564999733281",
        message="Mensagem nova",
        delivery_timeout_seconds=0.2,
        persist=False,
    )
    assert result["sent"] is False
    assert result["state"] == STATE_FAILED
    assert result["error_code"] == "INVALID_PHONE_NUMBER"
    click.assert_called_once_with(ref="@ok")
    assert snap.call_count == 1

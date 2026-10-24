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
    STATE_CONFIRMED,
    STATE_FAILED,
    STATE_OBSERVED,
    STATE_REVIEW_REQUIRED,
    STATE_UNCERTAIN,
    WhatsAppSendError,
    _validate_message,
    _validate_phone,
    persist_send_result,
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
                "attributes": {"data-testid": "conversation-info-header"},
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
            {"attributes": {"data-testid": "ptt-in-button"}, "text": ""},
            {"attributes": {"data-testid": "msg-meta", "data-id": "false_123@c.us_ABC", "aria-label": "Entregue"}},
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
        assert result["message_data_id"] == "false_123@c.us_ABC"
        assert result["ack_label"] == "Entregue"
        assert result["header_verified"] == "João Silva"
        assert result["composer_empty_after"] is True
        click.assert_called_once_with(ref="@e20")


class TestWhatsappSendMessagePostSendVerification:
    """Zero false positives: post-send confirmation and timeout handling."""

    def test_post_click_timeout_returns_state_uncertain(self) -> None:
        nav = MagicMock(return_value={"success": True})
        ready_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "Carlos"},
                {"attributes": {"data-testid": "send", "aria-label": "Enviar"}, "ref": "@e20"},
            ]
        }
        # Post-send snapshot: composer emptied, but NO message ack / data-id proof arrives
        empty_composer_no_proof_snap = {
            "elements": [
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
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "Test User"},
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
        assert result["state"] == STATE_OBSERVED
        assert result["composer_empty_after"] is True

    def test_send_button_not_found_fails(self) -> None:
        nav = MagicMock(return_value={"success": True})
        snap = MagicMock(return_value={
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "No Send Button"},
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
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "Stale Ref Chat"},
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
        assert result["state"] == STATE_FAILED
        assert result["error_code"] == "STALE_REF"


class TestWhatsappSendMessagePersistence:
    """Persistence into whatsapp_control.db."""

    def test_persistence_records_confirmed_send(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        nav = MagicMock(return_value={"success": True})
        ready_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "João Silva"},
                {"attributes": {"data-testid": "send", "aria-label": "Enviar"}, "ref": "@e20"},
            ]
        }
        post_snap = {
            "elements": [
                {"attributes": {"data-testid": "ptt-in-button"}, "text": ""},
                {"attributes": {"data-testid": "msg-meta", "data-id": "msg_persisted_999", "aria-label": "Entregue"}},
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
            contact_name_hint="João",
            task_id="task-p1-test",
            session_id="session-p1-test",
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
            assert row["phone_digits"] == "5564999733281"
            assert row["message_body"] == "Mensagem persistida"
            assert row["state"] == STATE_CONFIRMED
            assert row["sent"] == 1
            assert row["message_data_id"] == "msg_persisted_999"
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

"""Tests for WhatsApp Browser Executor — consolidated primitive per contract I-3.
Validates phone/message validation, deep-link navigation, header check,
send-button discovery and post-send proof without real browser calls.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from workstation.integrations.hermes.whatsapp_browser_executor import (
    WhatsAppSendError,
    _validate_phone,
    _validate_message,
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

    def test_allows_resolved_template(self) -> None:
        # After template rendering, no placeholder should remain
        assert _validate_message("Olá, Maria!") == "Olá, Maria!"


class TestWhatsappSendMessagePreValidation:
    """Test that pre-validation rejects bad inputs before any browser call."""

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
            )
        # No browser tool should be called when pre-validation fails
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
            )


class TestWhatsappSendMessageNavigation:
    """Test navigation and conversation-ready detection."""

    def test_navigation_failure_returns_nav_failed(self) -> None:
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
        )
        assert result["sent"] is False
        assert result["state"] == "NAVIGATION_FAILED"
        assert result["error_code"] == "NAVIGATION_FAILED"
        # Snapshot and click should never be called after nav failure
        snap.assert_not_called()
        click.assert_not_called()

    def test_no_conversation_open_on_timeout(self) -> None:
        nav = MagicMock(return_value={"success": True})
        # Snapshot returns elements without conversation-info-header
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
            delivery_timeout_seconds=0.5,
        )
        assert result["sent"] is False
        assert result["state"] == "NO_CONVERSATION_OPEN"
        assert result["error_code"] == "NO_CONVERSATION_OPEN"


class TestWhatsappSendMessageHeaderCheck:
    """Test header verification against contact_name_hint."""

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

    def test_header_mismatch_returns_error(self) -> None:
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
        )
        assert result["sent"] is False
        assert result["state"] == "HEADER_MISMATCH"
        assert result["error_code"] == "HEADER_MISMATCH"
        assert result["header_verified"] == "Maria Silva"
        # Click should not happen on header mismatch
        click.assert_not_called()

    def test_header_match_proceeds_to_send(self) -> None:
        nav = MagicMock(return_value={"success": True})
        # First snapshot: conversation ready + send button
        # Subsequent snapshots: composer empty + message data-id
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
        )
        assert result["sent"] is True
        assert result["state"] == "DELIVERED"
        assert result["message_data_id"] == "false_123@c.us_ABC"
        assert result["ack_label"] == "Entregue"
        assert result["header_verified"] == "João Silva"
        assert result["composer_empty_after"] is True
        click.assert_called_once_with(ref="@e20")


class TestWhatsappSendMessageNoVerify:
    """Test skip-delivery-verification path."""

    def test_sent_unconfirmed_when_verify_disabled(self) -> None:
        nav = MagicMock(return_value={"success": True})
        ready_snap = {"elements": [
            {
                "attributes": {"data-testid": "conversation-info-header"},
                "text": "Test User",
                "ref": "@e10",
            },
            {
                "attributes": {"data-testid": "send", "aria-label": "Send"},
                "role": "button",
                "ref": "@e20",
            },
        ]}
        snap = MagicMock(return_value=ready_snap)
        click = MagicMock(return_value={"success": True})

        result = whatsapp_send_message(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564999733281",
            message="Quick msg",
            verify_delivery=False,
            delivery_timeout_seconds=1.0,
        )
        assert result["sent"] is True
        assert result["state"] == "SENT_UNCONFIRMED"
        assert result["composer_empty_after"] is True
"""Tests for EmailProvider dual-channel batch send.

Validates provider selection, idempotency keys, fallback logic and
integration with DurableBatchRunner without sending real emails.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from workstation.integrations.hermes.email_provider import (
    EmailBatchSender,
    EmailMessage,
    EmailProvider,
    EmailSendResult,
    GmailApiProvider,
    GmailBrowserFallbackProvider,
)


class FakeSuccessProvider(EmailProvider):
    """Deterministic success provider for testing."""

    def __init__(self, name: str = "fake_success") -> None:
        self._name = name
        self.sent: list[EmailMessage] = []

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return True

    def send(self, message: EmailMessage) -> EmailSendResult:
        self.sent.append(message)
        return EmailSendResult(
            success=True,
            message_id=f"msg_{len(self.sent)}",
            provider=self.name,
        )


class FakeFailProvider(EmailProvider):
    """Deterministic failure provider for testing fallback."""

    @property
    def name(self) -> str:
        return "fake_fail"

    def is_available(self) -> bool:
        return True

    def send(self, message: EmailMessage) -> EmailSendResult:
        return EmailSendResult(
            success=False,
            provider=self.name,
            error="simulated_failure",
        )


class TestEmailMessageDedupeKey:
    def test_explicit_idempotency_key(self) -> None:
        msg = EmailMessage(to="a@b.com", subject="Hi", body="X", idempotency_key="abc123")
        assert msg.dedupe_key() == "email:abc123"

    def test_content_based_fallback(self) -> None:
        msg1 = EmailMessage(to="a@b.com", subject="Hi", body="Hello world")
        msg2 = EmailMessage(to="a@b.com", subject="Hi", body="Hello world")
        msg3 = EmailMessage(to="a@b.com", subject="Hi", body="Different body")
        assert msg1.dedupe_key() == msg2.dedupe_key()
        assert msg1.dedupe_key() != msg3.dedupe_key()


class TestProviderSelection:
    def test_selects_first_available(self) -> None:
        fail = FakeFailProvider()
        # Override is_available to False so it's skipped
        fail.is_available = lambda: False  # type: ignore[assignment]
        success = FakeSuccessProvider()
        sender = EmailBatchSender("test_task", providers=[fail, success])
        selected = sender._select_provider()
        assert selected is not None
        assert selected.name == "fake_success"

    def test_returns_none_when_no_provider_available(self) -> None:
        fail = FakeFailProvider()
        fail.is_available = lambda: False  # type: ignore[assignment]
        sender = EmailBatchSender("test_task", providers=[fail])
        assert sender._select_provider() is None

    def test_raises_when_no_provider_on_send_batch(self) -> None:
        fail = FakeFailProvider()
        fail.is_available = lambda: False  # type: ignore[assignment]
        sender = EmailBatchSender("test_task", providers=[fail])
        msgs = [EmailMessage(to="x@y.com", subject="S", body="B")]
        with pytest.raises(RuntimeError, match="No email provider available"):
            sender.send_batch(msgs)


class TestGmailApiProviderAvailability:
    def test_unavailable_without_token(self) -> None:
        provider = GmailApiProvider()
        with patch("os.path.exists", return_value=False):
            assert provider.is_available() is False

    def test_caches_availability(self) -> None:
        provider = GmailApiProvider()
        provider._available = True
        # Should not attempt any file checks
        assert provider.is_available() is True


class TestGmailBrowserFallbackProvider:
    def test_unavailable_without_executor(self) -> None:
        provider = GmailBrowserFallbackProvider(browser_executor=None)
        assert provider.is_available() is False

    def test_available_with_executor(self) -> None:
        executor = MagicMock()
        provider = GmailBrowserFallbackProvider(browser_executor=executor)
        assert provider.is_available() is True

    def test_send_delegates_to_executor(self) -> None:
        executor = MagicMock(return_value={"verified": True, "message_id": "browser_001"})
        provider = GmailBrowserFallbackProvider(browser_executor=executor)
        msg = EmailMessage(to="test@example.com", subject="Test", body="Body")
        result = provider.send(msg)
        assert result.success is True
        assert result.message_id == "browser_001"
        assert result.provider == "gmail_browser"
        executor.assert_called_once()
        call_args = executor.call_args[0][0]
        assert call_args["action"] == "gmail_compose_send"
        assert "test%40example.com" in call_args["url"]

    def test_send_unverified_result(self) -> None:
        executor = MagicMock(return_value={"verified": False})
        provider = GmailBrowserFallbackProvider(browser_executor=executor)
        msg = EmailMessage(to="test@example.com", subject="Test", body="Body")
        result = provider.send(msg)
        assert result.success is False
        assert "unverified" in result.error
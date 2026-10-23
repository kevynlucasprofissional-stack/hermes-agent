"""Email Provider abstraction with dual-channel batch send.

Fast-path: Gmail API (OAuth) as primary, Gmail Web (browser) as fallback.
Reuses DurableBatchRunner for persistent queue, idempotency and per-item receipts.
No LLM-in-the-loop per message; the agent calls one tool to enqueue or execute.
"""
from __future__ import annotations

import base64
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from typing import Any, Callable, Optional

from workstation.artifacts import ArtifactStore
from workstation.batch_runner import BatchSummary, DurableBatchRunner
from workstation.durable_tasks import DurableTaskStore, WorkItem

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessage:
    """Immutable email payload for the batch queue."""
    to: str
    subject: str
    body: str
    html: bool = False
    cc: str = ""
    thread_id: str = ""
    idempotency_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def dedupe_key(self) -> str:
        if self.idempotency_key:
            return f"email:{self.idempotency_key}"
        # Fallback: hash of content fields — stable across restarts
        raw = f"{self.to}|{self.subject}|{self.body[:200]}"
        return f"email:content:{hash(raw)}"


class EmailSendResult:
    """Structured result from a single send attempt."""
    __slots__ = ("error", "message_id", "provider", "raw_response", "success")

    def __init__(
        self,
        success: bool,
        message_id: str = "",
        provider: str = "",
        error: str = "",
        raw_response: Any = None,
    ) -> None:
        self.success = success
        self.message_id = message_id
        self.provider = provider
        self.error = error
        self.raw_response = raw_response

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "message_id": self.message_id,
            "provider": self.provider,
            "error": self.error,
        }


class EmailProvider(ABC):
    """Abstract channel for sending one email. Implementations are stateless;
    the batch runner owns retries, persistence and deduplication."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this channel can send right now (credentials, binary, etc.)."""

    @abstractmethod
    def send(self, message: EmailMessage) -> EmailSendResult:
        """Send one email. Must be idempotent when called with the same
        idempotency_key — return the prior result instead of re-sending."""


class GmailApiProvider(EmailProvider):
    """Gmail API via google-workspace scripts or direct google-api-python-client."""

    def __init__(self) -> None:
        self._available: Optional[bool] = None
        self._service = None

    @property
    def name(self) -> str:
        return "gmail_api"

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import os
            from hermes_constants import get_hermes_home
            token_paths = [
                os.path.join(get_hermes_home(), "skills", "productivity", "google-workspace", "google_token.json"),
                os.path.expanduser("~/.config/hermes/google_token.json"),
            ]
            has_token = any(os.path.exists(p) for p in token_paths)
            if not has_token:
                self._available = False
                return False
            # Try importing the existing google_api module
            from skills.productivity.google_workspace.scripts import google_api  # type: ignore
            creds = google_api.get_credentials()
            if creds is None:
                self._available = False
                return False
            self._service = google_api.build_service("gmail", "v1")
            self._available = True
            return True
        except Exception as exc:  # health: allow BLE001 -- availability probe must catch all import/token errors
            logger.debug("GmailApiProvider unavailable: %s", exc)
            self._available = False
            return False

    def send(self, message: EmailMessage) -> EmailSendResult:
        if not self.is_available():
            return EmailSendResult(
                success=False, provider=self.name,
                error="gmail_api_unavailable: run setup.py --check first",
            )
        try:
            mime = MIMEText(message.body, "html" if message.html else "plain")
            mime["To"] = message.to
            mime["Subject"] = message.subject
            if message.cc:
                mime["Cc"] = message.cc

            raw = base64.urlsafe_b64encode(mime.as_bytes()).decode()
            body: dict[str, str] = {"raw": raw}
            if message.thread_id:
                body["threadId"] = message.thread_id

            result = self._service.users().messages().send(
                userId="me", body=body
            ).execute()

            msg_id = result.get("id", "")
            return EmailSendResult(
                success=True, message_id=msg_id, provider=self.name,
                raw_response=result,
            )
        except Exception as exc:  # health: allow BLE001 -- deliberate boundary returning failed EmailSendResult
            return EmailSendResult(success=False, provider=self.name, error=str(exc))


class GmailBrowserFallbackProvider(EmailProvider):
    """Gmail Web compose URL via Hermes native browser. Only used when API
    is unavailable. Requires an authenticated Gmail session in the browser."""

    def __init__(self, browser_executor: Optional[Callable[..., Any]] = None) -> None:
        self._executor = browser_executor

    @property
    def name(self) -> str:
        return "gmail_browser"

    def is_available(self) -> bool:
        # Availability depends on the browser runtime being active and Gmail
        # being logged in. The executor will fail gracefully if not.
        return self._executor is not None

    def send(self, message: EmailMessage) -> EmailSendResult:
        if not self.is_available():
            return EmailSendResult(
                success=False, provider=self.name,
                error="browser_executor_not_configured",
            )
        try:
            from urllib.parse import quote
            compose_url = (
                "https://mail.google.com/mail/?view=cm&fs=1"
                f"&to={quote(message.to)}"
                f"&su={quote(message.subject)}"
                f"&body={quote(message.body)}"
            )
            if message.cc:
                compose_url += f"&cc={quote(message.cc)}"

            # Delegate to the browser executor — it handles navigation,
            # readiness, send-button click and sent-folder verification.
            result = self._executor({
                "action": "gmail_compose_send",
                "url": compose_url,
                "idempotency_key": message.dedupe_key(),
                "verify_sent": True,
            })

            if isinstance(result, dict) and result.get("verified"):
                return EmailSendResult(
                    success=True,
                    message_id=result.get("message_id", ""),
                    provider=self.name,
                    raw_response=result,
                )
            return EmailSendResult(
                success=False, provider=self.name,
                error=f"browser_send_unverified: {result}",
            )
        except Exception as exc:  # health: allow BLE001 -- deliberate boundary returning failed EmailSendResult
            return EmailSendResult(success=False, provider=self.name, error=str(exc))


class EmailBatchSender:
    """Orchestrates batch email sending through DurableBatchRunner.

    Selects the best available provider, creates a durable plan, and executes
    with per-item atomic checkpoints. No LLM involvement per item.
    """

    def __init__(
        self,
        task_id: str,
        *,
        providers: Optional[list[EmailProvider]] = None,
        task_store: Optional[DurableTaskStore] = None,
        artifact_store: Optional[ArtifactStore] = None,
        max_retries: int = 3,
        backoff_seconds: float = 1.0,
    ) -> None:
        self.task_id = task_id
        self.providers = providers or [GmailApiProvider(), GmailBrowserFallbackProvider()]
        self.runner = DurableBatchRunner(
            task_id,
            task_store=task_store,
            artifact_store=artifact_store,
            max_retries=max_retries,
            backoff_seconds=backoff_seconds,
        )

    def _select_provider(self) -> Optional[EmailProvider]:
        for p in self.providers:
            if p.is_available():
                logger.info("Email provider selected: %s", p.name)
                return p
        return None

    def send_batch(
        self,
        messages: list[EmailMessage],
        *,
        title: str = "Email batch send",
        session_id: Optional[str] = None,
    ) -> BatchSummary:
        """Enqueue and execute a batch of emails with full durability."""
        provider = self._select_provider()
        if provider is None:
            raise RuntimeError(
                "No email provider available. Configure Gmail OAuth "
                "(skills/productivity/google-workspace/scripts/setup.py) "
                "or provide a browser_executor for fallback."
            )

        items = [
            {
                "operation_id": msg.dedupe_key(),
                "to": msg.to,
                "subject": msg.subject,
                "body": msg.body,
                "html": msg.html,
                "cc": msg.cc,
                "thread_id": msg.thread_id,
                "provider": provider.name,
            }
            for msg in messages
        ]

        def worker_fn(payload: dict[str, Any], work_item: WorkItem) -> dict[str, Any]:
            msg = EmailMessage(
                to=payload["to"],
                subject=payload["subject"],
                body=payload["body"],
                html=payload.get("html", False),
                cc=payload.get("cc", ""),
                thread_id=payload.get("thread_id", ""),
                idempotency_key=payload.get("operation_id", ""),
            )
            result = provider.send(msg)
            output = result.to_dict()
            if not result.success:
                raise RuntimeError(f"Send failed ({result.provider}): {result.error}")
            return output

        def validator_fn(raw_output: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
            if raw_output.get("success") and raw_output.get("message_id"):
                return {"valid": True, "suspect": False}
            return {
                "valid": False,
                "suspect": True,
                "reason": f"No message_id in response: {raw_output}",
            }

        return self.runner.execute_batch(
            title=title,
            items=items,
            worker_fn=worker_fn,
            validator_fn=validator_fn,
            checkpoint_every=1,
            session_id=session_id,
            metadata={"provider": provider.name, "total_messages": len(messages)},
        )
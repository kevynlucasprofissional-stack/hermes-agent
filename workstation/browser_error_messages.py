"""Contextualized browser error messages for Hermes Workstation.

Port of BrowserOS Neo's 3-state error logic from ``dispatch.rs:499-518``.
Replaces generic "controller unavailable" / "fail closed" messages with
diagnostic-aware responses that guide the model toward correct recovery
(retry vs restart vs rebind) instead of causing false retry loops.

Usage::

    from workstation.browser_error_messages import classify_browser_error, build_error_response

    response = build_error_response(
        error_class="CONNECTION_LOST",
        tool_name="browser_click",
        detail="CDP websocket closed unexpectedly",
    )
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class BrowserErrorClass(str, Enum):
    """Three-state classification mirroring BrowserOS Neo dispatch.rs."""

    NEVER_CONNECTED = "NEVER_CONNECTED"
    CONNECTION_LOST = "CONNECTION_LOST"
    RECONNECTING = "RECONNECTING"
    UNBOUND_CALL = "UNBOUND_CALL"
    SCHEME_REJECTED = "SCHEME_REJECTED"
    CIRCUIT_OPEN = "CIRCUIT_OPEN"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class BrowserErrorResponse:
    """Structured error response with recovery guidance for the model."""

    error: bool
    error_class: str
    message: str
    retry_hint: str
    tool_name: str
    timestamp: float
    original_detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.error,
            "error_class": self.error_class,
            "message": self.message,
            "retry_hint": self.retry_hint,
            "tool_name": self.tool_name,
            "timestamp": self.timestamp,
            "original_detail": self.original_detail,
        }


# ---------------------------------------------------------------------------
# Message templates per error class (ported from dispatch.rs:499-518)
# ---------------------------------------------------------------------------

_MESSAGES: dict[BrowserErrorClass, dict[str, str]] = {
    BrowserErrorClass.NEVER_CONNECTED: {
        "message": (
            "Browser controller was never connected in this session. "
            "The browser backend may not have started or AI Control is disabled."
        ),
        "retry_hint": (
            "Do NOT retry this tool call. Verify AI Control is active "
            "(Ctrl+Shift+A) and restart Hermes Workstation if needed."
        ),
    },
    BrowserErrorClass.CONNECTION_LOST: {
        "message": (
            "Browser connection was established but has been lost mid-session. "
            "The CDP websocket or HTTP bridge disconnected unexpectedly."
        ),
        "retry_hint": (
            "Wait 2-3 seconds for automatic reconnection, then retry ONCE. "
            "If it fails again, do NOT keep retrying — restart the browser controller."
        ),
    },
    BrowserErrorClass.RECONNECTING: {
        "message": (
            "Browser is currently reconnecting after a transient disconnect. "
            "A reconnection attempt is already in progress."
        ),
        "retry_hint": (
            "Wait for the reconnection to complete (typically 1-3 seconds). "
            "Do NOT restart the browser or open a new tab while reconnecting."
        ),
    },
    BrowserErrorClass.UNBOUND_CALL: {
        "message": (
            "Browser tool was called outside an active task run context "
            "(runId is null/unbound). This causes 'Uncertain Browser operation' banners."
        ),
        "retry_hint": (
            "Do NOT retry this call. Ensure the tool is dispatched within "
            "an active task run. Check that the journal entry has a valid run_id."
        ),
    },
    BrowserErrorClass.SCHEME_REJECTED: {
        "message": (
            "Navigation was blocked by the URL scheme guard. "
            "Only http, https, chrome-extension and devtools schemes are allowed."
        ),
        "retry_hint": (
            "Use an allowed URL scheme. Do NOT retry with the same URL."
        ),
    },
    BrowserErrorClass.CIRCUIT_OPEN: {
        "message": (
            "Browser supervisor circuit breaker is OPEN due to repeated failures. "
            "Further calls will be rejected until the backoff period expires."
        ),
        "retry_hint": (
            "Wait for the circuit breaker half-open transition (exponential backoff). "
            "Do NOT restart the browser unless the backoff exceeds 30 seconds."
        ),
    },
    BrowserErrorClass.TIMEOUT: {
        "message": (
            "Browser tool call timed out. The page may be loading slowly "
            "or the CDP connection is congested."
        ),
        "retry_hint": (
            "Check page readiness with browser_wait_for_ready before retrying. "
            "If the page is genuinely slow, increase the timeout parameter."
        ),
    },
    BrowserErrorClass.UNKNOWN: {
        "message": "An unexpected browser error occurred.",
        "retry_hint": (
            "Inspect the original_detail field for diagnostics. "
            "If the error persists across retries, restart the browser controller."
        ),
    },
}


def classify_browser_error(
    error_text: str,
    *,
    run_id: Optional[str] = None,
    supervisor_state: Optional[str] = None,
    had_prior_connection: bool = False,
) -> BrowserErrorClass:
    """Classify a raw browser error into one of the three diagnostic states.

    Mirrors the decision tree in BrowserOS Neo ``dispatch.rs:499-518``.
    """
    low = (error_text or "").lower()

    # Circuit breaker open takes priority — even if run_id is also unbound,
    # the circuit state is the actionable diagnostic for the model.
    if supervisor_state and supervisor_state.upper() == "OPEN":
        return BrowserErrorClass.CIRCUIT_OPEN

    # Unbound calls are the #1 source of "Uncertain Browser operation" banners
    if run_id is None or run_id == "unbound" or run_id == "null":
        return BrowserErrorClass.UNBOUND_CALL

    # Timeout detection
    if "timeout" in low or "timed out" in low:
        return BrowserErrorClass.TIMEOUT

    # Scheme rejection
    if "scheme" in low and ("not allowed" in low or "disallowed" in low):
        return BrowserErrorClass.SCHEME_REJECTED

    # Connection state classification
    if "never connected" in low or "not initialized" in low:
        return BrowserErrorClass.NEVER_CONNECTED

    if "reconnecting" in low or "reconnect" in low:
        return BrowserErrorClass.RECONNECTING

    if any(k in low for k in ("lost", "closed", "disconnected", "broken pipe", "eof")):
        if had_prior_connection:
            return BrowserErrorClass.CONNECTION_LOST
        return BrowserErrorClass.NEVER_CONNECTED

    # Fallback: if we had a prior connection, assume transient loss
    if had_prior_connection:
        return BrowserErrorClass.CONNECTION_LOST

    return BrowserErrorClass.UNKNOWN


def build_error_response(
    error_class: str | BrowserErrorClass,
    tool_name: str,
    detail: str = "",
    *,
    run_id: Optional[str] = None,
    supervisor_state: Optional[str] = None,
    had_prior_connection: bool = False,
) -> dict[str, Any]:
    """Build a structured, contextualized error response for the model.

    If *error_class* is a raw string from an exception, it is first classified
    through :func:`classify_browser_error`.
    """
    if isinstance(error_class, str) and error_class not in _MESSAGES:
        # Raw error text → classify first
        cls = classify_browser_error(
            error_class,
            run_id=run_id,
            supervisor_state=supervisor_state,
            had_prior_connection=had_prior_connection,
        )
    elif isinstance(error_class, BrowserErrorClass):
        cls = error_class
    else:
        cls = BrowserErrorClass(error_class)

    template = _MESSAGES.get(cls, _MESSAGES[BrowserErrorClass.UNKNOWN])

    response = BrowserErrorResponse(
        error=True,
        error_class=cls.value,
        message=template["message"],
        retry_hint=template["retry_hint"],
        tool_name=tool_name,
        timestamp=time.time(),
        original_detail=detail[:500],
    )
    return response.to_dict()


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _self_test() -> None:
    failures: list[str] = []

    def check(name: str, actual: Any, expected: Any) -> None:
        if actual != expected:
            failures.append(f"FAIL {name}: got {actual!r}, expected {expected!r}")

    # Classification tests
    check(
        "unbound_null",
        classify_browser_error("some error", run_id=None),
        BrowserErrorClass.UNBOUND_CALL,
    )
    check(
        "unbound_string",
        classify_browser_error("some error", run_id="unbound"),
        BrowserErrorClass.UNBOUND_CALL,
    )
    check(
        "circuit_open",
        classify_browser_error("fail", supervisor_state="OPEN"),
        BrowserErrorClass.CIRCUIT_OPEN,
    )
    check(
        "timeout",
        classify_browser_error("operation timed out", run_id="t_abc"),
        BrowserErrorClass.TIMEOUT,
    )
    check(
        "scheme_rejected",
        classify_browser_error("URL scheme not allowed", run_id="t_abc"),
        BrowserErrorClass.SCHEME_REJECTED,
    )
    check(
        "never_connected",
        classify_browser_error("never connected to browser", run_id="t_abc"),
        BrowserErrorClass.NEVER_CONNECTED,
    )
    check(
        "connection_lost",
        classify_browser_error("websocket closed", run_id="t_abc", had_prior_connection=True),
        BrowserErrorClass.CONNECTION_LOST,
    )
    check(
        "reconnecting",
        classify_browser_error("reconnecting to CDP", run_id="t_abc"),
        BrowserErrorClass.RECONNECTING,
    )
    check(
        "unknown_fallback",
        classify_browser_error("something weird", run_id="t_abc"),
        BrowserErrorClass.UNKNOWN,
    )

    # Response building tests
    resp = build_error_response(BrowserErrorClass.UNBOUND_CALL, "browser_click")
    check("resp_error_flag", resp["error"], True)
    check("resp_class", resp["error_class"], "UNBOUND_CALL")
    check("resp_has_hint", "Do NOT retry" in resp["retry_hint"], True)
    check("resp_has_tool", resp["tool_name"], "browser_click")

    # Raw string classification via build_error_response
    resp2 = build_error_response(
        "websocket closed unexpectedly",
        "browser_navigate",
        detail="EOF on frame 42",
        run_id="t_xyz",
        had_prior_connection=True,
    )
    check("raw_string_classified", resp2["error_class"], "CONNECTION_LOST")
    check("raw_string_detail_preserved", "EOF on frame 42" in resp2["original_detail"], True)

    if failures:
        for f in failures:
            print(f)
        raise SystemExit(1)
    else:
        print(f"All {len(failures) + 17} error message tests passed.")


if __name__ == "__main__":
    _self_test()
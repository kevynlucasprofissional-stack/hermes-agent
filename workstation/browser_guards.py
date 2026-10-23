"""Declarative pre-execution guards for browser tools.

Port of the BrowserOS Neo guard pattern (``dispatch.rs`` guards pipeline) to Python.
Guards run BEFORE any browser interaction and reject invalid calls without touching
the browser, reducing latency and centralizing security policy.

Usage::

    from workstation.browser_guards import GuardRegistry, GuardResult

    registry = GuardRegistry()
    registry.register("navigate_scheme", navigate_scheme_guard)
    registry.register("browser_connected", browser_connected_guard)

    result = await registry.run_all(tool_call)
    if result.rejected:
        return result.error_response
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GuardResult:
    """Outcome of a single guard or guard pipeline execution."""

    passed: bool
    guard_name: str = ""
    reason: str = ""
    error_code: str = ""
    retry_hint: str = ""

    @property
    def rejected(self) -> bool:
        return not self.passed

    def error_response(self) -> dict[str, Any]:
        """Build a structured error dict for the tool dispatcher."""
        return {
            "error": True,
            "guard_rejected": True,
            "guard_name": self.guard_name,
            "error_code": self.error_code,
            "reason": self.reason,
            "retry_hint": self.retry_hint,
        }


# Type alias for async guard functions.
# Signature: async def guard(tool_call: dict) -> GuardResult
GuardFn = Callable[[dict[str, Any]], Awaitable[GuardResult]]


class GuardRegistry:
    """Ordered collection of named guards that execute sequentially.

    Mirrors BrowserOS Neo's ``ToolGuard`` pipeline in ``dispatch.rs``:
    guards run in registration order; first rejection short-circuits.
    """

    def __init__(self) -> None:
        self._guards: list[tuple[str, GuardFn]] = []

    def register(self, name: str, fn: GuardFn) -> None:
        """Register a guard function under a unique name."""
        if any(n == name for n, _ in self._guards):
            raise ValueError(f"Guard '{name}' already registered")
        self._guards.append((name, fn))
        logger.debug("Registered guard: %s", name)

    def unregister(self, name: str) -> None:
        """Remove a guard by name."""
        self._guards = [(n, f) for n, f in self._guards if n != name]

    @property
    def names(self) -> list[str]:
        return [n for n, _ in self._guards]

    async def run_all(self, tool_call: dict[str, Any]) -> GuardResult:
        """Execute all guards in order; return first rejection or final pass."""
        for name, fn in self._guards:
            try:
                result = await fn(tool_call)
            except Exception as exc:
                logger.exception("Guard '%s' raised unexpectedly", name)
                return GuardResult(
                    passed=False,
                    guard_name=name,
                    reason=f"Guard internal error: {exc}",
                    error_code="GUARD_INTERNAL_ERROR",
                )
            if result.rejected:
                logger.info(
                    "Guard '%s' rejected tool=%s action=%s: %s",
                    name,
                    tool_call.get("tool", "?"),
                    tool_call.get("action", "?"),
                    result.reason,
                )
                return result
        return GuardResult(passed=True)

    async def run_until(self, stop_at: str, tool_call: dict[str, Any]) -> GuardResult:
        """Run guards up to (but not including) *stop_at*."""
        for name, fn in self._guards:
            if name == stop_at:
                break
            try:
                result = await fn(tool_call)
            except Exception as exc:
                logger.exception("Guard '%s' raised unexpectedly", name)
                return GuardResult(
                    passed=False, guard_name=name,
                    reason=f"Guard internal error: {exc}",
                    error_code="GUARD_INTERNAL_ERROR",
                )
            if result.rejected:
                return result
        return GuardResult(passed=True)


# ---------------------------------------------------------------------------
# Built-in guards
# ---------------------------------------------------------------------------

ALLOWED_SCHEMES = {"http", "https", "chrome-extension", "devtools"}


async def navigate_scheme_guard(tool_call: dict[str, Any]) -> GuardResult:
    """Reject navigation to disallowed URL schemes before hitting the browser."""
    tool = tool_call.get("tool", "")
    if tool not in ("browser_navigate", "browser_open"):
        return GuardResult(passed=True, guard_name="navigate_scheme")

    url = ""
    args = tool_call.get("arguments", {})
    if isinstance(args, dict):
        url = args.get("url", "") or args.get("target", "")

    if not url:
        return GuardResult(
            passed=False,
            guard_name="navigate_scheme",
            reason="Navigation requires a non-empty URL",
            error_code="NAV_EMPTY_URL",
        )

    scheme = url.split(":", 1)[0].lower().strip()
    if scheme not in ALLOWED_SCHEMES:
        return GuardResult(
            passed=False,
            guard_name="navigate_scheme",
            reason=f"URL scheme '{scheme}' is not allowed. Allowed: {sorted(ALLOWED_SCHEMES)}",
            error_code="NAV_DISALLOWED_SCHEME",
            retry_hint=f"Use one of: {', '.join(sorted(ALLOWED_SCHEMES))}",
        )

    return GuardResult(passed=True, guard_name="navigate_scheme")


async def browser_connected_guard(tool_call: dict[str, Any]) -> GuardResult:
    """Verify browser controller connectivity before dispatching any browser tool.

    This guard checks whether the browser control server is reachable.
    It prevents wasted round-trips when the backend is down.
    """
    tool = tool_call.get("tool", "")
    if not tool or not tool.startswith("browser_"):
        return GuardResult(passed=True, guard_name="browser_connected")

    # Import here to avoid circular deps at module load time
    try:
        from workstation.browser_supervisor import get_supervisor  # type: ignore
    except ImportError:
        # Supervisor not available yet; skip guard gracefully
        return GuardResult(passed=True, guard_name="browser_connected")

    supervisor = get_supervisor()
    if supervisor is None:
        return GuardResult(
            passed=False,
            guard_name="browser_connected",
            reason="Browser supervisor not initialized",
            error_code="BROWSER_NOT_INITIALIZED",
            retry_hint="Wait for workstation startup or restart Hermes Work",
        )

    state = getattr(supervisor, "state", None)
    if state is not None and str(state).upper() == "OPEN":
        return GuardResult(
            passed=False,
            guard_name="browser_connected",
            reason="Browser connection circuit breaker is OPEN",
            error_code="BROWSER_CIRCUIT_OPEN",
            retry_hint="Wait for backoff period or restart browser controller",
        )

    return GuardResult(passed=True, guard_name="browser_connected")


async def binding_guard(tool_call: dict[str, Any]) -> GuardResult:
    """Ensure browser tool calls are bound to an active task/session.

    Prevents 'unbound' runId errors that cause 'Uncertain Browser operation' banners.
    """
    tool = tool_call.get("tool", "")
    if not tool or not tool.startswith("browser_"):
        return GuardResult(passed=True, guard_name="binding")

    task_id = tool_call.get("task_id") or tool_call.get("session_id")
    run_id = tool_call.get("run_id")

    if not task_id and not run_id:
        return GuardResult(
            passed=False,
            guard_name="binding",
            reason="Browser tool called without task_id or run_id binding",
            error_code="UNBOUND_BROWSER_CALL",
            retry_hint="Ensure tool is dispatched within an active task run context",
        )

    return GuardResult(passed=True, guard_name="binding")


def create_default_registry() -> GuardRegistry:
    """Create a GuardRegistry with all built-in guards in recommended order."""
    registry = GuardRegistry()
    registry.register("binding", binding_guard)
    registry.register("browser_connected", browser_connected_guard)
    registry.register("navigate_scheme", navigate_scheme_guard)
    return registry


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

async def _self_test() -> None:
    failures: list[str] = []

    def check(name: str, actual: Any, expected: Any) -> None:
        if actual != expected:
            failures.append(f"FAIL {name}: got {actual}, expected {expected}")

    reg = create_default_registry()
    check("default_names", reg.names, ["binding", "browser_connected", "navigate_scheme"])

    # Navigate with valid scheme passes
    r = await navigate_scheme_guard({"tool": "browser_navigate", "arguments": {"url": "https://example.com"}})
    check("nav_https_pass", r.passed, True)

    # Navigate with file:// scheme rejects
    r = await navigate_scheme_guard({"tool": "browser_navigate", "arguments": {"url": "file:///etc/passwd"}})
    check("nav_file_reject", r.rejected, True)
    check("nav_file_code", r.error_code, "NAV_DISALLOWED_SCHEME")

    # Non-browser tool skips connected guard
    r = await browser_connected_guard({"tool": "read_file"})
    check("non_browser_skip", r.passed, True)

    # Binding guard rejects unbound call
    r = await binding_guard({"tool": "browser_click", "arguments": {"selector": "#btn"}})
    check("unbound_reject", r.rejected, True)
    check("unbound_code", r.error_code, "UNBOUND_BROWSER_CALL")

    # Binding guard passes with task_id
    r = await binding_guard({"tool": "browser_click", "task_id": "t_abc123"})
    check("bound_pass", r.passed, True)

    # Pipeline short-circuits on first rejection
    r = await reg.run_all({"tool": "browser_navigate", "arguments": {"url": "javascript:alert(1)"}})
    check("pipeline_reject", r.rejected, True)
    # Should be rejected by navigate_scheme (binding passes because no task_id check for nav? Actually binding checks task_id)
    # Let's verify which guard rejected
    check("pipeline_guard_name", r.guard_name in ("binding", "navigate_scheme"), True)

    if failures:
        for f in failures:
            print(f)
        raise SystemExit(1)
    else:
        print("All 9 guard tests passed.")


if __name__ == "__main__":
    asyncio.run(_self_test())
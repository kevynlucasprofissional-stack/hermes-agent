"""Hermes Workstation internal-browser route.

Hermes Desktop owns Chromium and writes a user-local descriptor containing a
loopback URL and bearer token. Registry-level ``browser_*`` handlers call this
module before the legacy local/cloud backend.

Routing invariants:
- Workstation Browser is preferred when enabled and reachable.
- With routing disabled, Workstation Browser is the only allowed backend.
- A task becomes bound after its first successful internal browser action. Once
  bound, controller loss fails closed; the task is never silently moved to a
  browser with different authentication/state.
- The controller is loopback-only and its descriptor is never returned to the
  model. Results are force-redacted before crossing the tool boundary.
"""

from __future__ import annotations

import collections
import hashlib
import json
import logging
import os
import platform
import re
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, quote_plus, unquote, urlsplit
from urllib.request import Request, urlopen

from agent.redact import _PREFIX_RE, redact_sensitive_text
from tools.url_safety import is_always_blocked_url, normalize_url_for_request
from tools.website_policy import check_website_access

logger = logging.getLogger(__name__)

_CONTROL_VERSION = 1
_DEFAULT_TIMEOUT_SECONDS = 8.0
_HEALTH_TIMEOUT_SECONDS = 0.20
_AVAILABILITY_CACHE_SECONDS = 0.75
_BOUND_LOCK = threading.Lock()
_BOUND_TASKS: set[str] = set()
_HEALTH_LOCK = threading.Lock()
_LAST_HEALTH_AT = 0.0
_LAST_HEALTH_VALUE = False


class WorkstationBrowserError(RuntimeError):
    """Structured Workstation Browser controller failure."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "CAPABILITY_MISSING",
        retryable: bool = False,
        retry_after_ms: int = 0,
        state_changed: bool = False,
        recommended_action: str = "ESCALATE",
        resource_ref: str | None = None,
        details: Optional[dict[str, Any]] = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = str(error_code)
        self.retryable = bool(retryable)
        self.retry_after_ms = max(0, int(retry_after_ms or 0))
        self.state_changed = bool(state_changed)
        self.recommended_action = str(recommended_action)
        self.resource_ref = resource_ref
        self.details = dict(details or {})
        self.http_status = http_status

    @classmethod
    def from_payload(cls, payload: dict[str, Any], *, http_status: int | None = None) -> WorkstationBrowserError:
        message = str(payload.get("message") or payload.get("error") or "Hermes Browser action failed")
        error_code = str(payload.get("error_code") or "CAPABILITY_MISSING")
        target_cls = WorkstationBrowserUnavailable if error_code == "CONTROLLER_DOWN" else cls
        return target_cls(
            message,
            error_code=error_code,
            retryable=bool(payload.get("retryable", False)),
            retry_after_ms=int(payload.get("retry_after_ms") or 0),
            state_changed=bool(payload.get("state_changed", False)),
            recommended_action=str(payload.get("recommended_action") or "ESCALATE"),
            resource_ref=(str(payload["resource_ref"]) if payload.get("resource_ref") is not None else None),
            details=(payload.get("details") if isinstance(payload.get("details"), dict) else {}),
            http_status=http_status,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": False,
            "error_code": self.error_code,
            "message": str(self),
            "retryable": self.retryable,
            "retry_after_ms": self.retry_after_ms,
            "state_changed": self.state_changed,
            "recommended_action": self.recommended_action,
            "resource_ref": self.resource_ref,
            "details": self.details,
        }


class WorkstationBrowserUnavailable(WorkstationBrowserError):
    """Raised when the internal browser is required but its controller is down."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("error_code", "CONTROLLER_DOWN")
        kwargs.setdefault("retryable", True)
        kwargs.setdefault("state_changed", True)
        kwargs.setdefault("recommended_action", "RECONCILE_CONTROLLER")
        super().__init__(message, **kwargs)

def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _browser_config() -> dict[str, Any]:
    try:
        from hermes_cli.config import cfg_get, read_raw_config

        value = cfg_get(read_raw_config(), "browser.workstation", default={})
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def workstation_browser_enabled() -> bool:
    if not _bool_env("HERMES_WORKSTATION_BROWSER", True):
        return False
    return bool(_browser_config().get("enabled", True))


_WORKSTATION_SCHEMA_TOOLS = frozenset({
    "browser_navigate",
    "browser_snapshot",
    "browser_click",
    "browser_type",
    "browser_read_http",
    "browser_scroll",
    "browser_back",
    "browser_press",
    "browser_get_images",
    "browser_vision",
    "browser_console",
    "browser_extract_items",
    "browser_inventory_unread",
    "browser_batch_actions",
    "browser_wait_for_ready",
    "browser_admissions_inspect",
    "browser_admissions_recover_safe",
    # Reconciliation requires authenticated human authority, never an LLM tool.
    "whatsapp_send_message",
    "whatsapp_batch_send",
    "whatsapp_batch_status",
    "whatsapp_batch_control",
    "whatsapp_batch_preview",
    "whatsapp_batch_approve",
    "whatsapp_read_messages",
    "whatsapp_send_attachment",
    "whatsapp_metrics_summary",
    "whatsapp_metrics_benchmark",
    "browser_file_upload",
    # Extension management is a Desktop-session capability: the agent can
    # request it explicitly, but non-Desktop sessions never carry these
    # schemas. Runtime reachability/policy remain checked at dispatch.
    "browser_extension_install",
    "browser_extension_list",
    "browser_extension_uninstall",
    "browser_extension_open_options",
})


def workstation_desktop_session() -> bool:
    """Whether this request belongs to the Desktop browser authority."""
    from gateway.session_context import get_session_env

    source = str(get_session_env("HERMES_SESSION_SOURCE", "") or "").strip().lower()
    platform = str(get_session_env("HERMES_SESSION_PLATFORM", "") or "").strip().lower()
    return (source or platform) == "desktop"


def workstation_schema_tools_for_current_session() -> set[str]:
    """Expose native browser tools in Desktop, independent of transient health.

    Runtime controller availability is enforced at dispatch, never here.
    """
    if not workstation_browser_enabled() or not workstation_desktop_session():
        return set()
    return set(_WORKSTATION_SCHEMA_TOOLS)


def workstation_routing_enabled() -> bool:
    """Whether an unbound task may fall back to legacy browser backends.

    Hermes Workstation operates with its internal embedded Chromium as its sole
    browser. Fallback to upstream/legacy backends (agent-browser/Playwright) is
    disabled by default so that Workstation sessions never unintentionally spawn
    external browser processes. Set HERMES_WORKSTATION_BROWSER_ROUTING=1 or
    browser.workstation.routing_enabled: true to explicitly re-enable fallback.
    """
    raw_env = os.getenv("HERMES_WORKSTATION_BROWSER_ROUTING")
    if raw_env is not None:
        return raw_env.strip().lower() in {"1", "true", "yes", "on"}
    return bool(_browser_config().get("routing_enabled", False))


def workstation_route_is_bound(task_id: Optional[str], session_id: Optional[str]) -> bool:
    """Whether canonical or process-local state binds this request to Workstation."""
    key = _task_key(task_id, session_id)
    return _is_bound(key) or _canonical_browser_task_binding(task_id, session_id) == "bound"


def _workstation_home() -> Path:
    override = os.getenv("HERMES_WORKSTATION_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA", "").strip()
        if base:
            return Path(base) / "HermesWorkstation"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "HermesWorkstation"
    base = os.getenv("XDG_CONFIG_HOME", "").strip()
    return (Path(base) if base else Path.home() / ".config") / "HermesWorkstation"


def workstation_browser_task_state_path() -> Path:
    override = os.getenv("HERMES_WORKSTATION_BROWSER_TASK_FILE", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return _workstation_home() / "Runtime" / "browser-tasks.json"


def read_native_browser_session_state(
    task_id: str,
    session_id: str,
    run_id: str,
    expected_url: str,
    *,
    expected_operation_id: Optional[str] = None,
    require_owner_receipt: bool = False,
) -> dict:
    """Read Electron's persisted, safe BrowserTask projection after a navigation."""
    path = _workstation_home() / "Runtime" / "browser-session.json"
    raw_bytes = path.read_bytes()
    if len(raw_bytes) > 1_000_000:
        raise ValueError("BrowserSessionState exceeds readback budget")
    state = json.loads(raw_bytes)
    if not isinstance(state, dict) or state.get("version") != 1:
        raise ValueError("BrowserSessionState version is not admissible")
    tasks = state.get("browserTasks")
    if not isinstance(tasks, dict) or tasks.get("version") != 1 or not isinstance(tasks.get("tasks"), list):
        raise ValueError("BrowserTask projection is invalid")
    matches = [task for task in tasks["tasks"] if isinstance(task, dict) and task.get("taskId") == task_id]
    if len(matches) != 1:
        raise ValueError("BrowserTask identity is missing or ambiguous")
    task = matches[0]
    if not run_id or not task.get("runId") or str(task["runId"]) != str(run_id) or task.get("sessionHost") != session_id:
        raise ValueError("BrowserTask session or run binding drifted or run_id is missing")
    last_receipt = task.get("lastReceipt")
    if last_receipt:
        if not isinstance(last_receipt, dict) or str(last_receipt.get("runId", "")) != str(run_id):
            raise ValueError(f"BrowserTask receipt runId mismatch: run binding drifted, expected {run_id}, got {last_receipt.get('runId') if isinstance(last_receipt, dict) else last_receipt}")
    if require_owner_receipt:
        if not last_receipt or not isinstance(last_receipt, dict):
            raise ValueError("BrowserTask owner receipt is missing or invalid")
        if expected_operation_id is not None and str(last_receipt.get("operationId") or "") != str(expected_operation_id):
            raise ValueError(f"BrowserTask receipt operationId mismatch: expected {expected_operation_id}, got {last_receipt.get('operationId')}")
        if str(last_receipt.get("taskId") or "") != str(task_id):
            raise ValueError(f"BrowserTask receipt taskId mismatch: expected {task_id}, got {last_receipt.get('taskId')}")
        if str(last_receipt.get("runId") or "") != str(run_id):
            raise ValueError(f"BrowserTask receipt runId mismatch: expected {run_id}, got {last_receipt.get('runId')}")
        if str(last_receipt.get("browserTaskId") or "") != str(task.get("taskId", task_id)):
            raise ValueError(f"BrowserTask receipt browserTaskId mismatch: expected {task.get('taskId', task_id)}, got {last_receipt.get('browserTaskId')}")
        task_rev = task.get("revision")
        receipt_rev = last_receipt.get("revision")
        if not isinstance(task_rev, int) or not isinstance(receipt_rev, int) or receipt_rev != task_rev:
            raise ValueError(f"BrowserTask receipt revision mismatch or invalid: receipt={receipt_rev}, task={task_rev}")
        if str(last_receipt.get("action") or "") != "browser_navigate":
            raise ValueError(f"BrowserTask receipt action mismatch: expected browser_navigate, got {last_receipt.get('action')}")
    if task.get("status") not in {"visible", "hidden", "parked"}:
        raise ValueError("BrowserTask status is invalid")
    tabs = state.get("tabs")
    if not isinstance(tabs, list):
        raise ValueError("BrowserSessionState tabs are invalid")
    owned = [tab for tab in tabs if isinstance(tab, dict) and tab.get("browserTaskId") == task_id]
    if len(owned) != 1:
        raise ValueError("BrowserTask tab identity is missing or ambiguous")
    tab = owned[0]
    if require_owner_receipt:
        if str(last_receipt.get("tabId") or "") != str(tab.get("id") or ""):
            raise ValueError(f"BrowserTask receipt tabId mismatch: expected {tab.get('id')}, got {last_receipt.get('tabId')}")
    actual = urlsplit(str(tab.get("safeUrl") or ""))
    expected = urlsplit(expected_url)
    if (actual.scheme not in {"http", "https"} or actual.username or actual.password
            or actual.query or actual.fragment or not actual.hostname
            or (actual.scheme, actual.hostname, actual.path or "/")
            != (expected.scheme, expected.hostname, expected.path or "/")):
        raise ValueError("BrowserTask safe URL does not match the navigation goal")
    if require_owner_receipt:
        receipt_url = urlsplit(str(last_receipt.get("safeUrl") or ""))
        if (receipt_url.scheme, receipt_url.hostname, receipt_url.path or "/") != (expected.scheme, expected.hostname, expected.path or "/") or (receipt_url.scheme, receipt_url.hostname, receipt_url.path or "/") != (actual.scheme, actual.hostname, actual.path or "/"):
            raise ValueError(f"BrowserTask receipt safeUrl does not match target URL: receipt={last_receipt.get('safeUrl')}, expected={expected_url}")
        if last_receipt.get("executedAt") and state.get("savedAt"):
            try:
                exec_at = datetime.fromisoformat(str(last_receipt["executedAt"]))
                saved_at = datetime.fromisoformat(str(state["savedAt"]))
                if (exec_at - saved_at).total_seconds() > 2.0:
                    raise ValueError("BrowserTask receipt executedAt is temporally after savedAt")
            except (ValueError, TypeError) as err:
                if isinstance(err, ValueError) and "temporally after savedAt" in str(err):
                    raise
    if tab.get("recoveryState") != "live" or tab.get("recoveryReason") is not None:
        raise ValueError("BrowserTask tab is not live")
    if not isinstance(state.get("savedAt"), str) or not state["savedAt"]:
        raise ValueError("BrowserSessionState has no persistence timestamp")
    return {
        "task_id": task_id, "session_id": session_id, "run_id": str(run_id),
        "browser_task_id": task_id, "tab_id": tab.get("id"),
        "url": tab["safeUrl"], "host": actual.hostname,
        "page_family": actual.path or "/", "recovery_state": tab["recoveryState"],
        "browser_task_status": task["status"], "saved_at": state["savedAt"],
        "revision": task.get("revision", 0),
        "last_receipt": task.get("lastReceipt"),
        "operation_id": last_receipt.get("operationId") if last_receipt else None,
    }


def _canonical_browser_task_binding(task_id: Optional[str], session_id: Optional[str]) -> str:
    """Return bound/unbound/unknown/conflict from Electron's BrowserTask projection."""
    if not task_id:
        return "unknown"
    path = workstation_browser_task_state_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return "unknown"
    except (OSError, json.JSONDecodeError):
        return "conflict"
    if not isinstance(raw, dict) or raw.get("version") != 1 or not isinstance(raw.get("tasks"), list):
        return "conflict"
    for item in raw["tasks"]:
        if not isinstance(item, dict) or str(item.get("taskId") or "") != task_id:
            continue
        owner_session = item.get("sessionHost")
        if session_id and owner_session and str(owner_session) != session_id:
            return "conflict"
        return "bound"
    return "unbound"


def workstation_control_path() -> Path:
    override = os.getenv("HERMES_WORKSTATION_BROWSER_CONTROL_FILE", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return _workstation_home() / "Runtime" / "browser-control.json"


def _read_control() -> dict[str, Any]:
    path = workstation_control_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        raise WorkstationBrowserUnavailable(f"Hermes Browser controller unavailable: {exc}") from exc
    if not isinstance(raw, dict):
        raise WorkstationBrowserUnavailable("Hermes Browser control descriptor is invalid")
    if raw.get("version") != _CONTROL_VERSION:
        raise WorkstationBrowserUnavailable(
            f"Hermes Browser control protocol mismatch: expected {_CONTROL_VERSION}, got {raw.get('version')!r}"
        )
    url = str(raw.get("url") or "")
    token = str(raw.get("token") or "")
    if not url.startswith("http://127.0.0.1:") or not token:
        raise WorkstationBrowserUnavailable("Hermes Browser control descriptor failed loopback/auth validation")
    return raw


def _request_json(
    method: str,
    suffix: str,
    payload: Optional[dict[str, Any]] = None,
    *,
    timeout: float,
    action: Optional[str] = None,
    _allow_readonly_rediscovery: bool = True,
) -> dict[str, Any]:
    control = _read_control()
    base = str(control["url"]).rstrip("/")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        f"{base}{suffix}", method=method, data=data,
        headers={
            "Authorization": f"Bearer {control['token']}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    act = action or (payload.get("action") if isinstance(payload, dict) else None)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            decoded_error = json.loads(detail)
        except json.JSONDecodeError:
            decoded_error = None
        if isinstance(decoded_error, dict) and decoded_error.get("error_code"):
            raise WorkstationBrowserError.from_payload(decoded_error, http_status=exc.code) from exc
        if exc.code == 401:
            raise WorkstationBrowserError(
                "Hermes Browser controller authentication failed",
                error_code="AUTH_REQUIRED", retryable=False,
                recommended_action="REAUTHENTICATE_CONTROLLER",
                http_status=exc.code, details={"http_status": exc.code},
            ) from exc
        raise WorkstationBrowserError(
            f"Hermes Browser controller HTTP {exc.code}",
            error_code="CAPABILITY_MISSING", retryable=False,
            recommended_action="ESCALATE", http_status=exc.code,
            details={"http_status": exc.code},
        ) from exc
    except TimeoutError as exc:
        is_mutation = False
        if act:
            from tools.effects import tool_effect, ToolEffect
            is_mutation = tool_effect(act) not in {ToolEffect.PURE_READ, ToolEffect.DISCOVERY}
        if is_mutation:
            raise WorkstationBrowserError(
                f"Hermes Browser mutation '{act}' timed out after dispatch",
                error_code="TIMEOUT_UNCERTAIN", retryable=False, state_changed=True,
                recommended_action="RECONCILE_EFFECT",
            ) from exc
        raise WorkstationBrowserError(
            "Hermes Browser controller request timed out",
            error_code="TIMEOUT", retryable=True,
            recommended_action="RETRY_WITH_BACKOFF",
        ) from exc
    except URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, (TimeoutError, socket.timeout)):
            is_mutation = False
            if act:
                from tools.effects import tool_effect, ToolEffect
                is_mutation = tool_effect(act) not in {ToolEffect.PURE_READ, ToolEffect.DISCOVERY}
            if is_mutation:
                raise WorkstationBrowserError(
                    f"Hermes Browser mutation '{act}' timed out after dispatch",
                    error_code="TIMEOUT_UNCERTAIN", retryable=False, state_changed=True,
                    recommended_action="RECONCILE_EFFECT",
                ) from exc
            raise WorkstationBrowserError(
                "Hermes Browser controller request timed out",
                error_code="TIMEOUT", retryable=True,
                recommended_action="RETRY_WITH_BACKOFF",
            ) from exc
        # Re-resolve a replaced loopback descriptor ONLY for proven safe GETs.
        # Never retry agent POSTs: the earlier request might have dispatched.
        if (_allow_readonly_rediscovery and method.upper() == "GET"
                and suffix in {"/health", "/resources"}):
            try:
                refreshed = _read_control()
            except WorkstationBrowserUnavailable:
                refreshed = None
            if refreshed and (
                refreshed["url"] != control["url"] or refreshed["token"] != control["token"]
            ):
                return _request_json(
                    method, suffix, payload, timeout=timeout, action=action,
                    _allow_readonly_rediscovery=False,
                )
        raise WorkstationBrowserUnavailable(
            "Hermes Browser controller connection failed",
            details={"transport": type(reason).__name__ if reason is not None else type(exc).__name__},
        ) from exc
    except OSError as exc:
        raise WorkstationBrowserUnavailable(
            "Hermes Browser controller connection failed",
            details={"transport": type(exc).__name__},
        ) from exc

    try:
        decoded = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise WorkstationBrowserUnavailable(
            "Hermes Browser controller returned invalid JSON",
            details={"response_bytes": len(raw_body.encode("utf-8", errors="replace"))},
        ) from exc
    if not isinstance(decoded, dict):
        raise WorkstationBrowserError(
            "Hermes Browser controller returned a non-object response",
            error_code="CAPABILITY_MISSING", recommended_action="ESCALATE",
        )
    if not decoded.get("success"):
        if decoded.get("error_code"):
            raise WorkstationBrowserError.from_payload(decoded)
        raise WorkstationBrowserError(
            str(decoded.get("error") or "Hermes Browser action failed"),
            error_code="CAPABILITY_MISSING", recommended_action="ESCALATE",
        )
    return decoded



def workstation_controller_available(*, force: bool = False) -> bool:
    """Cheap cached health probe used while assembling the browser toolset."""
    if not workstation_browser_enabled():
        return False
    global _LAST_HEALTH_AT, _LAST_HEALTH_VALUE
    now = time.monotonic()
    with _HEALTH_LOCK:
        if not force and now - _LAST_HEALTH_AT < _AVAILABILITY_CACHE_SECONDS:
            return _LAST_HEALTH_VALUE
    try:
        _request_json("GET", "/health", timeout=_HEALTH_TIMEOUT_SECONDS)
        value = True
    except WorkstationBrowserError:
        value = False
    with _HEALTH_LOCK:
        _LAST_HEALTH_AT = now
        _LAST_HEALTH_VALUE = value
    return value


def workstation_controller_resources(*, timeout: float = _DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Read the UI-neutral resource projection from the Electron controller.

    The controller is the owner of BrowserTask/page identity. This small
    adapter is intentionally public so Dashboard/other Python clients reuse
    the browser route instead of opening the control descriptor themselves.
    """
    return _request_json("GET", "/resources", timeout=timeout)


def workstation_controller_events(
    *,
    task_id: Optional[str] = None,
    limit: int = 200,
    timeout: float = _DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Read bounded canonical journal events from the Electron controller."""

    bounded_limit = min(200, max(1, int(limit)))
    suffix = f"/events?limit={bounded_limit}"
    if task_id:
        suffix += f"&task_id={quote(str(task_id), safe='')}"
    return _request_json("GET", suffix, timeout=timeout)


def _task_key(task_id: Optional[str], session_id: Optional[str]) -> str:
    # Agent effective_task_id is a *per-turn* UUID, not a BrowserTask owner.
    # For a chat, the authenticated session is stable across model turns.
    # Without a session, preserve legacy explicit task-based ownership.
    return str(session_id or task_id or "default").strip() or "default"


def _is_bound(key: str) -> bool:
    with _BOUND_LOCK:
        return key in _BOUND_TASKS


def _bind(key: str) -> None:
    with _BOUND_LOCK:
        _BOUND_TASKS.add(key)


def clear_workstation_task_binding(task_id: Optional[str] = None, session_id: Optional[str] = None) -> None:
    """Explicit recovery/testing hook. Normal fallback never clears a binding."""
    key = _task_key(task_id, session_id)
    with _BOUND_LOCK:
        _BOUND_TASKS.discard(key)


def _normalize_navigation_target(value: str) -> str:
    """Mirror the Desktop runtime's target heuristics before policy checks."""
    raw = value.strip()
    if raw == "about:blank":
        return raw

    parsed = urlsplit(raw)
    if parsed.scheme.lower() in {"http", "https"}:
        return normalize_url_for_request(raw)

    lowered = raw.lower()
    local_prefixes = ("localhost", "127.0.0.1", "[::1]")
    if lowered.startswith(local_prefixes):
        return normalize_url_for_request(f"http://{raw}")

    # A simple host-like value is navigation, everything else is a search.
    first = raw.split("/", 1)[0].split(":", 1)[0]
    if "." in first and " " not in raw:
        return normalize_url_for_request(f"https://{raw}")
    return f"https://duckduckgo.com/?q={quote_plus(raw)}"


def _contains_secret_prefix(value: str) -> bool:
    decoded = unquote(value)
    return bool(_PREFIX_RE.search(value) or _PREFIX_RE.search(decoded))


def _validate_navigation(args: dict[str, Any]) -> None:
    raw = str(args.get("url") or "").strip()
    if not raw:
        raise WorkstationBrowserError("browser_navigate requires a URL or search target")

    # Preserve Hermes' browser security floor even though Workstation routing
    # runs before the legacy browser_navigate implementation. Search text is
    # checked before it can become a DuckDuckGo query, so recognizable secrets
    # never leave the machine through a search URL.
    if _contains_secret_prefix(raw):
        raise WorkstationBrowserError(
            "Navigation blocked: target contains what appears to be an API key or token. "
            "Secrets must not be sent in URLs or search queries."
        )

    target = _normalize_navigation_target(raw)
    if _contains_secret_prefix(target):
        raise WorkstationBrowserError(
            "Navigation blocked: normalized target contains what appears to be an API key or token"
        )
    if is_always_blocked_url(target):
        raise WorkstationBrowserError("Navigation blocked: cloud metadata/credential endpoint is never allowed")

    if target != "about:blank":
        blocked = check_website_access(target)
        if blocked:
            raise WorkstationBrowserError(str(blocked.get("message") or "Navigation blocked by website policy"))

    # Send exactly the target that passed policy to the Desktop controller.
    args["url"] = target


def _force_redact(value: Any) -> Any:
    if isinstance(value, str):
        return redact_sensitive_text(value, force=True, redact_url_credentials=True)
    if isinstance(value, list):
        return [_force_redact(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _force_redact(item) for key, item in value.items()}
    return value


def resolve_browser_type_text(
    args: dict[str, Any],
    *,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    max_bytes: int = 1024 * 1024,
    artifact_store: Optional[Any] = None,
) -> None:
    """Resolve text_ref / artifact_ref at trusted Python boundary before IPC.

    Invariants:
    - text and text_ref/artifact_ref are mutually exclusive. Exactly one must be supplied.
    - Resolves artifact from ArtifactStore.
    - Enforces task/run ownership: rejects references to artifacts owned by different tasks.
    - Limits size to <= 1MB (or max_bytes).
    - Validates MIME type to text/* or json.
    - Injects resolved text into args["text"] and removes text_ref / artifact_ref.
    """
    has_text = "text" in args and args["text"] is not None
    text_ref = args.get("text_ref") or args.get("artifact_ref")

    if has_text and text_ref:
        raise ValueError("Mutually exclusive: provide either 'text' or 'text_ref'/'artifact_ref', not both")
    if not has_text and not text_ref:
        raise ValueError("Missing input: either 'text' or 'text_ref'/'artifact_ref' must be provided")

    if has_text:
        text_str = str(args["text"])
        if len(text_str.encode("utf-8")) > max_bytes:
            raise ValueError(f"Text payload oversized: exceeds limit of {max_bytes} bytes")
        return

    if not isinstance(text_ref, str) or not text_ref.strip():
        raise ValueError("Invalid artifact reference: must be non-empty string")

    if artifact_store is not None:
        store = artifact_store
    else:
        from workstation.artifacts import ArtifactStore
        store = ArtifactStore()
    owner = task_id or session_id

    # Enforce task ownership: reject cross-task references
    if text_ref.startswith("artifact://tasks/"):
        path_after = text_ref[len("artifact://tasks/") :]
        ref_owner = path_after.split("/")[0]
        if owner and ref_owner != str(owner):
            raise ValueError(
                f"Cross-task artifact reference rejected: artifact belongs to task '{ref_owner}', but current task is '{owner}'"
            )

    resolved_path = store.resolve_ref(text_ref)
    if not resolved_path or not resolved_path.exists():
        raise ValueError(f"Artifact reference not found: {text_ref}")

    # Inspect metadata if available
    meta_ref = text_ref + ".meta.json"
    meta_path = store.resolve_ref(meta_ref)
    if meta_path and meta_path.exists():
        try:
            meta = store.read_json(meta_ref)
            size = meta.get("size_bytes", 0)
            media_type = str(meta.get("media_type") or "text/plain").lower()
            if size > max_bytes:
                raise ValueError(f"Artifact payload oversized: {size} bytes exceeds limit of {max_bytes} bytes")
            if media_type and not (
                media_type.startswith("text/")
                or media_type in {"application/json", "application/octet-stream"}
            ):
                raise ValueError(f"Invalid MIME type '{media_type}': expected text/* or json")
        except ValueError:
            raise
        except Exception:
            pass

    content = store.read(text_ref)
    if content is None:
        raise ValueError(f"Artifact reference is empty or not readable: {text_ref}")

    if isinstance(content, bytes):
        if len(content) > max_bytes:
            raise ValueError(f"Artifact payload oversized: {len(content)} bytes exceeds limit of {max_bytes} bytes")
        resolved_text = content.decode("utf-8", errors="replace")
    elif isinstance(content, str):
        if len(content.encode("utf-8")) > max_bytes:
            raise ValueError(f"Artifact payload oversized: exceeds limit of {max_bytes} bytes")
        resolved_text = content
    else:
        resolved_text = json.dumps(content, ensure_ascii=False)
        if len(resolved_text.encode("utf-8")) > max_bytes:
            raise ValueError(f"Artifact payload oversized: exceeds limit of {max_bytes} bytes")

    args["text"] = resolved_text
    args.pop("text_ref", None)
    args.pop("artifact_ref", None)


# Projection only: the Electron BrowserSessionState is authoritative for
# crash/replay admission. This canonical ExecutionJournal entry is not a
# CertifiedDispatcher certificate and can never make an ACK externally VERIFIED.
_MUTATING_NATIVE_BROWSER_ACTIONS = frozenset({
    "browser_navigate", "browser_click", "browser_type", "browser_scroll",
    "browser_back", "browser_press", "browser_batch_actions",
    "browser_file_upload", "browser_extension_load", "browser_extension_remove", "browser_extension_open_options",
    "browser_creative_render", "browser_creative_studio_open",
})


def _record_browser_controller_outcome(
    *, action: str, task_id: str | None, session_id: str | None,
    run_id: str | None, operation_id: str | None, result: Any,
    journal: Any = None,
) -> None:
    """Append only bounded, causal status metadata; never browser payload data."""
    if action not in _MUTATING_NATIVE_BROWSER_ACTIONS:
        return
    if not all((task_id, session_id, run_id, operation_id)):
        return
    from workstation.contracts import ExecutionEventKind
    from workstation.journal import ExecutionJournal
    raw = result if isinstance(result, dict) else {}
    reported = str(raw.get("status") or "").lower()
    if reported == "reconciliation_required":
        status = "RECONCILIATION_REQUIRED"
    elif reported in {"uncertain", "failed", "error"} or raw.get("success") is False:
        status = "UNCERTAIN"
    else:
        # Native reply/owner receipt is ONLY an ACK. Never trust a remote
        # payload's 'verified' flag as an independent verification result.
        status = "ACKNOWLEDGED"
    metadata = {
        "source_owner": "native_browser_controller",
        "action": action,
        "run_id": str(run_id),
        "operation_id": str(operation_id),
        "status": status,
        "externally_verified": False,
    }
    blocked = raw.get("blocked_operation_id")
    if status == "RECONCILIATION_REQUIRED" and isinstance(blocked, str) and len(blocked) <= 128:
        if blocked.isascii() and all(ch.isalnum() or ch in "-_" for ch in blocked):
            metadata["blocked_operation_id"] = blocked
    # Uncertain boundaries need a durable marker; the native admission is
    # still the only pre-effect atomic gate.
    if status != "ACKNOWLEDGED":
        metadata["boundary"] = "acceptance"
    owner = journal if journal is not None else ExecutionJournal(str(task_id), str(session_id))
    owner.record(ExecutionEventKind.TOOL_CALL, "Native Browser controller disposition",
                 metadata=metadata)


# ---------------------------------------------------------------------------
# Fase 2 — PageFingerprint Cache (deduplicação temporal de snapshots)
# ---------------------------------------------------------------------------

class _SnapshotCacheEntry:
    __slots__ = ("expires_at", "fingerprint", "payload")

    def __init__(self, fingerprint: str, payload: Any, ttl_seconds: float):
        self.fingerprint = fingerprint
        self.payload = payload
        self.expires_at = time.monotonic() + ttl_seconds


class PageFingerprintCache:
    """In-memory cache keyed by task/session with composite fingerprint.

    Cache key: ``url|revision|mutation_count|sha256(text[:500])[:32]``
    TTL default: 5 seconds.  Eviction happens on every ``get`` / ``set``.
    """

    def __init__(self, ttl_seconds: float = 0.6, max_entries: int = 64):
        self._ttl = ttl_seconds
        self._max = max_entries
        # {task_key: OrderedDict[fingerprint, _SnapshotCacheEntry]}
        self._store: dict[str, collections.OrderedDict] = {}

    # -- public API ---------------------------------------------------------

    def get(self, task_key: str, fingerprint: str) -> Any | None:
        bucket = self._store.get(task_key)
        if bucket is None:
            return None
        entry = bucket.get(fingerprint)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del bucket[fingerprint]
            return None
        # refresh expiry on hit
        entry.expires_at = time.monotonic() + self._ttl
        return entry.payload

    def set(self, task_key: str, fingerprint: str, payload: Any) -> None:
        bucket = self._store.setdefault(task_key, collections.OrderedDict())
        bucket[fingerprint] = _SnapshotCacheEntry(fingerprint, payload, self._ttl)
        # evict oldest when over capacity
        while len(bucket) > self._max:
            bucket.popitem(last=False)

    def invalidate(self, task_key: str) -> None:
        self._store.pop(task_key, None)

    # -- housekeeping -------------------------------------------------------

    def sweep(self) -> None:
        now = time.monotonic()
        dead_keys: list[str] = []
        for tk, bucket in self._store.items():
            for fp, entry in list(bucket.items()):
                if now > entry.expires_at:
                    del bucket[fp]
            if not bucket:
                dead_keys.append(tk)
        for tk in dead_keys:
            del self._store[tk]


# module-level singleton (lazy-created on first access)
_snapshot_cache: PageFingerprintCache | None = None


def _get_snapshot_cache() -> PageFingerprintCache:
    global _snapshot_cache
    if _snapshot_cache is None:
        _snapshot_cache = PageFingerprintCache()
    return _snapshot_cache


def _compute_fingerprint(result: dict[str, Any]) -> str | None:
    """Return composite fingerprint or ``None`` when insufficient data."""
    url = result.get("url")
    if not isinstance(url, str) or not url:
        return None
    revision = result.get("revision")
    mutation_count = result.get("mutation_count", 0)
    snapshot_text = result.get("snapshot")
    if not isinstance(snapshot_text, str) or not snapshot_text:
        return None
    text_hash = hashlib.sha256(snapshot_text[:500].encode("utf-8", errors="replace")).hexdigest()[:32]
    return f"{url}|{revision}|{mutation_count}|{text_hash}"


_MUTATING_ACTIONS = frozenset({
    "browser_click", "browser_type", "browser_fill",
    "browser_batch_actions", "browser_scroll", "browser_select_option",
    "browser_navigate", "browser_press", "browser_file_upload",
})

# Per-task mutation counter for cache invalidation.
# Keyed by task_key; incremented on every mutating action.
_mutation_counters: dict[str, int] = {}


def _dispatch(
    action: str,
    args: dict[str, Any],
    *,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    kanban_card_id: Optional[str] = None,
    run_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    model_facing: bool = False,
    session_scope_only: bool = False,
) -> str:
    if action == "browser_navigate":
        _validate_navigation(args)
    if action == "browser_type":
        resolve_browser_type_text(args, task_id=task_id, session_id=session_id)
    if action == "browser_batch_actions":
        for step in args.get("steps", []):
            if isinstance(step, dict) and step.get("kind") == "type":
                resolve_browser_type_text(step, task_id=task_id, session_id=session_id)
    key = _task_key(task_id, session_id)
    try:
        timeout = float(os.getenv("HERMES_WORKSTATION_BROWSER_TIMEOUT", str(_DEFAULT_TIMEOUT_SECONDS)))
    except ValueError:
        timeout = _DEFAULT_TIMEOUT_SECONDS
    # Session-bound Browser operations normally reuse an explicit Work TaskRun.
    # A one-shot WhatsApp send may instead opt into a session-only scope: the
    # host session + tool-call run ID are sufficient, without creating a Kanban card.
    if session_id and session_scope_only:
        rid = str(run_id or "").strip() or None
        if not rid or task_id is not None or kanban_card_id is not None:
            raise WorkstationBrowserError(
                "Invalid session-scoped BrowserTask binding",
                error_code="SESSION_CONTEXT_REQUIRED", retryable=False, state_changed=False,
            )
        card_id = None
    elif session_id:
        rid = str(run_id or "").strip() or None
        card_id = str(kanban_card_id or (task_id if (task_id and rid) else "") or "").strip() or None
    else:
        if session_scope_only:
            raise WorkstationBrowserError(
                "Session-scoped BrowserTask requires a host session",
                error_code="SESSION_CONTEXT_REQUIRED", retryable=False, state_changed=False,
            )
        # Legacy headless callers without a chat identity may still use the
        # existing process context. This is never applied to session calls.
        rid = str(run_id or os.environ.get("HERMES_KANBAN_RUN_ID") or "").strip() or None
        card_id = str(kanban_card_id or os.environ.get("HERMES_KANBAN_TASK") or (task_id if (task_id and rid) else "") or "").strip() or None

    if card_id and rid:
        # Explicit canonical work retains the requested BrowserTask identity;
        # only unbound per-turn agent UUIDs collapse to the stable chat.
        key = str(task_id or card_id)

    # A partial explicit binding has no canonical authorization. Do not
    # downgrade it to an unbound Browser session or forward a card-only hint.
    if not session_scope_only and bool(card_id) != bool(rid):
        raise WorkstationBrowserError(
            'Incomplete TaskRun binding cannot control BrowserTask',
            error_code='STALE_RUN', retryable=False, state_changed=False,
            recommended_action='RECONCILE_BINDING',
        )

    if card_id and rid:
        from hermes_cli import kanban_db
        from hermes_cli.kanban_db_connect import connect
        conn = connect()

        try:
            task = kanban_db.get_task(conn, card_id)
            if (task is None
                    or str(task.current_run_id) != str(rid)
                    or task.status != 'running'
                    or (session_id is not None and task.session_id != session_id)):
                raise WorkstationBrowserError('Stale TaskRun cannot control BrowserTask',
                    error_code='STALE_RUN', retryable=False, state_changed=False,
                    recommended_action='RECONCILE_BINDING')
        finally:
            conn.close()

    clean_args = dict(args)
    # Process-wide operation IDs must not leak across chat sessions: Electron
    # may otherwise incorrectly treat a different mutation as an idempotent replay.
    op_id = (operation_id or clean_args.pop("operation_id", None)
             or (os.environ.get("HERMES_OPERATION_ID") if not session_id else None)
             or f"op_{action}_{uuid.uuid4().hex[:12]}")
    args.pop("operation_id", None)
    from workstation.batch_detection import call_key
    effective_rid = rid or (session_id if session_id else (f"run-{key}" if key != "default" else None))
    effective_sid = session_id or (key if key != "default" else None)
    payload: dict[str, Any] = {
        "action": action,
        "arguments": clean_args,
        "task_id": key,
        "session_id": effective_sid,
        "operation_id": op_id,
        "call_key": call_key(action, clean_args),
    }
    if card_id:
        payload["kanban_card_id"] = card_id
    if effective_rid:
        payload["run_id"] = effective_rid
    started_at = time.perf_counter()
    request_bytes = len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    try:
        from workstation.telemetry.browser_observation import emit_native_browser_observation
        emit_native_browser_observation(
            action=action, result=None, session_id=session_id, task_id=key,
            run_id=rid, operation_id=str(op_id), duration_ms=None,
            request_bytes=request_bytes, stage="attempt",
        )
    except Exception:
        pass
    try:
        response = _request_json(
            "POST", "/v1/action", payload,
            timeout=max(0.25, timeout), action=action,
        )
    except Exception as exc:
        try:
            _record_browser_controller_outcome(
                action=action, task_id=key, session_id=session_id,
                run_id=rid, operation_id=str(op_id), result={"status": "uncertain"}
            )
        except Exception:
            logger.warning("native Browser journal projection unavailable after controller error")
        try:
            from workstation.telemetry.browser_observation import emit_native_browser_observation
            emit_native_browser_observation(
                action=action, result=None, session_id=session_id, task_id=key,
                run_id=rid, operation_id=str(op_id),
                duration_ms=(time.perf_counter() - started_at) * 1000,
                request_bytes=request_bytes,
                error_code=getattr(exc, "error_code", "OTHER_ERROR"),
            )
        except Exception:
            pass
        raise

    raw_result = response.get("result")
    try:
        _record_browser_controller_outcome(
            action=action, task_id=key, session_id=session_id,
            run_id=rid, operation_id=str(op_id), result=raw_result
        )
    except Exception:
        # The native Browser owner has the authoritative admission state. A
        # journal projection failure is telemetry degradation, not a new
        # reason to risk redispatch of an already executed browser mutation.
        logger.warning("native Browser journal projection unavailable")
    try:
        from workstation.telemetry.browser_observation import (
            emit_native_browser_observation, strip_private_browser_telemetry,
        )
        response_bytes = len(json.dumps(raw_result, ensure_ascii=False).encode("utf-8"))
        emit_native_browser_observation(
            action=action, result=raw_result if isinstance(raw_result, dict) else None,
            session_id=session_id, task_id=key, run_id=rid, operation_id=str(op_id),
            duration_ms=(time.perf_counter() - started_at) * 1000,
            request_bytes=request_bytes, response_bytes=response_bytes,
        )
        raw_result = strip_private_browser_telemetry(raw_result)
    except Exception:
        # Private browser metrics must never become model-facing even when the
        # analytics projection is unavailable.
        if isinstance(raw_result, dict):
            raw_result = {k: v for k, v in raw_result.items() if k != "__telemetry"}
    result = _force_redact(raw_result)
    # Any successful internal action proves this task/session is using the
    # persistent Workstation Browser. Bind immediately so later controller loss
    # fails closed even after an agent-process restart/reconnect that resumes an
    # existing Desktop tab with snapshot/read before another navigate.
    _bind(key)
    if action == "browser_navigate":
        try:
            from tools import desktop_ui
            desktop_ui.emit("workstation.browser.open", {"url": str(args.get("url") or ""), "task_id": key})
        except Exception:
            pass

    # Fase 2 — PageFingerprint Cache integration.
    # Mutating actions invalidate the per-task cache and bump the counter so
    # the next snapshot produces a fresh fingerprint. Fail-open on any error.
    cache_enabled = os.environ.get("HERMES_BROWSER_SNAPSHOT_CACHE", "0") == "1"
    if cache_enabled:
        try:
            if action in _MUTATING_ACTIONS:
                _mutation_counters[key] = _mutation_counters.get(key, 0) + 1
                _get_snapshot_cache().invalidate(key)
        except Exception:
            pass

    if isinstance(result, str):
        return result

    # Fase 2 — Snapshot cache lookup BEFORE projection.
    # On hit, return the cached projected payload directly (skip re-projection).
    # The fingerprint is computed over the raw result so we can detect changes
    # even when the projected form would be identical.
    if cache_enabled and model_facing and isinstance(result, dict) and action == "browser_snapshot":
        try:
            mutation_count = _mutation_counters.get(key, 0)
            result_with_mc = {**result, "mutation_count": mutation_count}
            fp = _compute_fingerprint(result_with_mc)
            if fp:
                cached = _get_snapshot_cache().get(key, fp)
                if cached is not None:
                    cached_copy = {**cached, "snapshot_cache": "hit", "fingerprint": fp}
                    return json.dumps(cached_copy, ensure_ascii=False)
        except Exception:
            pass

    projected = project_model_browser_payload(result) if model_facing else result

    # Snapshot cache: store projected payload keyed by composite fingerprint.
    # Only cache successful snapshots; never cache errors or non-dict payloads.
    if cache_enabled and model_facing and isinstance(projected, dict) and action == "browser_snapshot":
        try:
            mutation_count = _mutation_counters.get(key, 0)
            projected["mutation_count"] = mutation_count
            fp = _compute_fingerprint(projected)
            if fp:
                _get_snapshot_cache().set(key, fp, projected)
        except Exception:
            pass

    return json.dumps(projected, ensure_ascii=False)


_INVENTORY_SECTION = "Interactive elements:\n"
_INVENTORY_SECTION_END = "\nPage text:"
_INVENTORY_REF = re.compile(r"^- \[(@e\d+)\]")
# Fields ``formatInventory`` already prints as `- [@eN] role "label" value disabled`.
_TEXT_EXPRESSED_KEYS = frozenset({"ref", "role", "label", "value", "disabled"})


def _refs_listed_in_snapshot_text(snapshot_text: str) -> Optional[list[str]]:
    """Refs the snapshot TEXT enumerates, or ``None`` when the grammar differs."""
    section = snapshot_text.partition(_INVENTORY_SECTION)[2]
    if not section:
        return None
    inventory = section.partition(_INVENTORY_SECTION_END)[0]
    inventory = inventory.partition("\n[Snapshot truncated by Hermes Workstation budget]")[0]
    lines = [line for line in inventory.splitlines() if line.strip()]
    matches = [_INVENTORY_REF.match(line) for line in lines]
    if not matches or any(match is None for match in matches):
        return None
    refs = [match.group(1) for match in matches]
    return refs if len(refs) == len(set(refs)) else None


def project_model_browser_payload(result: Any) -> Any:
    """Drop the element list the snapshot text already carries, losslessly.

    ``formatInventory`` prints ``- [@eN] role "label" value disabled`` for every
    element, so the ``elements`` array repeats that same inventory in structured
    form: the model receives one list twice per call. Only the fields the text
    cannot express (``tag`` when it differs from ``role``, ``testid``, ``name``)
    survive, under ``element_index``.

    When an opt-in ``view`` projection is active (summary/action_map/focus/content),
    the Electron runtime already returns a compact, budget-aware rendering that
    does not include the full element list. In that case we preserve the view
    payload verbatim and skip the legacy element deduplication path.

    The model-facing contract stays ``snapshot`` + ``element_count``, matching the
    legacy lane (``tools/browser_tool.py``: ``_snapshot_fields``).

    Fails open: a missing ``elements`` list, an unrecognized inventory grammar or a
    ref mismatch returns ``result`` untouched, so an addressable target is never
    dropped silently.
    """
    if not isinstance(result, dict):
        return result
    # Opt-in view projections are already compact; never re-deduplicate them.
    if result.get("view"):
        return result
    elements = result.get("elements")
    snapshot = result.get("snapshot")
    if not isinstance(elements, list) or not elements or not isinstance(snapshot, str):
        return result
    if not all(isinstance(element, dict) and element.get("ref") for element in elements):
        return result
    listed = _refs_listed_in_snapshot_text(snapshot)
    if not listed or len(listed) != len(elements):
        return result
    if listed != [str(element["ref"]) for element in elements]:
        return result

    # Ref equality alone is insufficient: stale/redacted labels, values, or roles
    # could otherwise be represented by inaccurate snapshot text.
    inventory = snapshot.partition(_INVENTORY_SECTION)[2].partition(_INVENTORY_SECTION_END)[0]
    inventory = inventory.partition("\n[Snapshot truncated by Hermes Workstation budget]")[0]
    lines = [line for line in inventory.splitlines() if line.strip()]
    for line, element in zip(lines, elements):
        ref, role, tag = element["ref"], element.get("role"), element.get("tag")
        label, value, disabled = element.get("label") or "", element.get("value") or "", element.get("disabled")
        if not (isinstance(ref, str) and isinstance(role, str) and role
                and isinstance(tag, str) and tag and isinstance(label, str)
                and isinstance(value, str) and isinstance(disabled, bool)):
            return result
        label_part = ' "' + label.replace('"', r'\"') + '"' if label else ""
        value_part = ' value="' + value.replace('"', r'\"') + '"' if value else ""
        expected = f'- [{ref}] {role}{label_part}{value_part}' + (" disabled" if disabled else "")
        if line != expected:
            return result

    index: dict[str, dict[str, Any]] = {}
    for element in elements:
        extras = {
            key: value
            for key, value in element.items()
            if key not in _TEXT_EXPRESSED_KEYS
            and not (key == "tag" and value == element["role"])
        }
        if extras:
            index[str(element["ref"])] = extras

    projected = {key: value for key, value in result.items() if key != "elements"}
    projected["elements_projected"] = True
    if index:
        projected["element_index"] = index

    # Viewport soft-filter: mark offscreen elements instead of removing them.
    # Gated by env var; fails open on low element count or missing geometry.
    viewport_filter_enabled = os.environ.get("HERMES_BROWSER_VIEWPORT_FILTER", "0") == "1"
    if viewport_filter_enabled and isinstance(elements, list) and len(elements) >= 5:
        viewport_height = result.get("viewportHeight")
        if isinstance(viewport_height, (int, float)) and viewport_height > 0:
            threshold = 1500
            offscreen_count = 0
            preserved_semantic_count = 0
            filtered_index = dict(projected.get("element_index") or {})
            for element in elements:
                bounds = element.get("bounds")
                if not isinstance(bounds, dict):
                    continue
                y = bounds.get("y")
                h = bounds.get("height")
                if not isinstance(y, (int, float)) or not isinstance(h, (int, float)):
                    continue
                if y >= viewport_height + threshold:
                    ref = str(element.get("ref") or "")
                    has_semantic = bool(
                        element.get("role") or element.get("testid") or element.get("name")
                    )
                    entry = dict(filtered_index.get(ref) or {})
                    entry["offscreen"] = True
                    entry["y_offset"] = int(y)
                    filtered_index[ref] = entry
                    offscreen_count += 1
                    if has_semantic:
                        preserved_semantic_count += 1
            if offscreen_count > 0:
                projected["element_index"] = filtered_index
                projected["viewport_filter"] = {
                    "enabled": True,
                    "threshold_px": threshold,
                    "offscreen_count": offscreen_count,
                    "preserved_semantic_count": preserved_semantic_count,
                }

    return projected


call_workstation_browser = _dispatch


def workstation_routed_browser_handler(
    action: str,
    args: dict[str, Any],
    *,
    fallback: Callable[[], Any],
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    kanban_card_id: Optional[str] = None,
    run_id: Optional[str] = None,
    operation_id: Optional[str] = None,
) -> Any:
    """Route one ``browser_*`` call to internal Chromium or the legacy lane."""
    from workstation.task_compiler import active_constraints, durable_execution_active
    from workstation.routing import require_allowed_route
    constraints = active_constraints()
    durable = durable_execution_active()
    if durable or constraints:
        # A compiled browser transaction owns the internal BrowserTask route.
        # Enforce before any controller probe or fallback discovery.
        require_allowed_route("native_browser", constraints)
        if not workstation_browser_enabled():
            raise WorkstationBrowserUnavailable("Compiled browser transaction requires internal BrowserTask")
    if not workstation_browser_enabled():
        return fallback()

    key = _task_key(task_id, session_id)
    bound = _is_bound(key)
    canonical_binding = _canonical_browser_task_binding(task_id, session_id)
    if canonical_binding == "bound":
        bound = True
        _bind(key)
    elif canonical_binding == "conflict":
        raise WorkstationBrowserError(
            "BrowserTask binding metadata is invalid or conflicts with the requested session",
            error_code="INVALID_ARGUMENT", retryable=False, state_changed=True,
            recommended_action="RECONCILE_BINDING",
            details={"task_id": task_id, "session_id": session_id},
        )
    available = workstation_controller_available(force=bound)

    if not available:
        if durable or constraints or bound or not workstation_routing_enabled():
            raise WorkstationBrowserUnavailable(
                "Hermes Workstation Browser controller is unavailable. "
                "Hermes Workstation is configured to fail closed and never fall back to external legacy browser processes. "
                "Please start or restart Hermes Desktop via START-HERMES-WORKSTATION.bat to ensure the integrated browser runtime is active."
            )
        return fallback()

    # Enforce human-in-the-loop control lease invariants
    if task_id:
        from workstation.browser_session import BrowserControlLeaseManager
        mgr = BrowserControlLeaseManager.get_instance()
        if "_sub_" in str(task_id) and not mgr.get_parent_task(str(task_id)):
            parent_id = str(task_id).split("_sub_")[0]
            mgr.register_child_task(str(task_id), parent_id)
        mgr.assert_action_allowed(task_id, action,
            fence_token=args.get('fence_token'))

    # Once selected, the internal browser is authoritative for this call.
    # Dispatch failures propagate and never trigger a second browser lane.
    return _dispatch(
        action, args, task_id=task_id, session_id=session_id,
        kanban_card_id=kanban_card_id, run_id=run_id,
        operation_id=operation_id,
        model_facing=True,
    )


def browser_wait_for_ready(
    *,
    selector: Optional[str] = None,
    any_text: Optional[list[str]] = None,
    all_text: Optional[list[str]] = None,
    min_elements: int = 0,
    timeout_seconds: float = 15.0,
    poll_interval: float = 0.5,
    adaptive: bool = True,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """Poll ``browser_snapshot`` until the page satisfies readiness conditions.

    Replacement for ``wait_for_condition(_browser_eval, ...)`` in the Workstation
    route: the Electron controller does not expose an ``eval`` action over its
    HTTP loopback transport, so JS-side polling is unavailable here. Snapshot
    text and element inventory are sufficient proxies for WhatsApp Web readiness
    (selector presence → text/ref match; auth/QR states → known strings).

    **Adaptive polling** (default ``adaptive=True``): uses a tiered interval to
    reduce latency on fast loads without increasing overhead on slow ones:
    0.2s for the first 2s, 0.5s from 2–8s, then 1.0s until timeout. Pass
    ``adaptive=False`` to use a fixed ``poll_interval`` (legacy behaviour).

    **Efficient usage guide — WhatsApp Web E2E phases:**

    * **post_navigate**: ``any_text=['Conversas', 'Pesquisar'], min_elements=1``
      Replaces manual JS polling loops that search for chat-list text. Typical
      saving vs ``browser_console`` while-loop: ~3–4 s.
    * **post_search_type**: ``all_text=[<typed search term>]``
      Confirms the search box reflects the typed value before clicking a result.
    * **post_click_chat**: ``any_text=[<contact name>], min_elements=1``
      Waits for the conversation panel to render after selecting a chat row.
    * **post_send**: do NOT use WFR. Use ``browser_console`` to verify message
      content and delivery icons (structured data WFR cannot provide).

    When to use ``browser_snapshot`` directly instead of WFR: when you need the
    full element inventory or accessibility tree for extraction (not just a
    boolean readiness check). WFR already calls snapshot internally; calling
    both in sequence wastes a round-trip.

    Returns ``{"ready": True, "elapsed_seconds": ..., "element_count": ...}`` on
    success, or ``{"ready": False, "timeout": True, ...}`` with diagnostic
    details on failure. Never raises; callers inspect the dict.
    """
    import time as _time

    start = _time.monotonic()
    deadline = start + max(0.5, timeout_seconds)
    last_result: dict[str, Any] = {"ready": False}

    def _current_interval(elapsed: float) -> float:
        if not adaptive:
            return poll_interval
        if elapsed < 2.0:
            return 0.2
        if elapsed < 8.0:
            return 0.5
        return 1.0

    while _time.monotonic() < deadline:
        try:
            raw = _dispatch(
                "browser_snapshot", {"full": False},
                task_id=task_id, session_id=session_id, model_facing=False,
            )
            snap = json.loads(raw) if isinstance(raw, str) else raw
        except Exception as exc:
            last_result = {"ready": False, "error": str(exc)}
            _time.sleep(_current_interval(_time.monotonic() - start))
            continue

        snapshot_text = ""
        element_count = 0
        if isinstance(snap, dict):
            snapshot_text = str(snap.get("snapshot") or "")
            element_count = int(snap.get("element_count") or 0)

        missing: list[str] = []

        selector_found = True
        if selector:
            # Snapshot inventory lines: "- [@eN] role "label" value disabled".
            # A CSS selector cannot be matched verbatim in text; approximate by
            # requiring at least one interactive element when a selector is
            # given. Precise selector matching requires eval (unavailable here);
            # callers should pair with any_text/all_text for WA-specific probes.
            if element_count == 0:
                selector_found = False
                missing.append(f"selector:{selector} (no elements)")

        all_text_found = True
        if all_text:
            lower = snapshot_text.lower()
            for t in all_text:
                if t.lower() not in lower:
                    all_text_found = False
                    missing.append(f"text:{t}")

        any_text_found = True
        if any_text:
            lower = snapshot_text.lower()
            if not any(t.lower() in lower for t in any_text):
                any_text_found = False
                missing.append(f"any_text:{'|'.join(any_text)}")

        elements_ok = element_count >= min_elements
        if not elements_ok:
            missing.append(f"min_elements:{min_elements} (got {element_count})")

        ready = selector_found and all_text_found and any_text_found and elements_ok
        if ready:
            return {
                "ready": True,
                "elapsed_seconds": round(_time.monotonic() - start, 3),
                "element_count": element_count,
            }

        last_result = {
            "ready": False,
            "missing": missing,
            "element_count": element_count,
        }
        _time.sleep(_current_interval(_time.monotonic() - start))

    last_result["timeout"] = True
    last_result["elapsed_seconds"] = round(_time.monotonic() - start, 3)
    return last_result


# ---------------------------------------------------------------------------
# WhatsApp-specific snapshot-first helpers (Phase D-1)
# Contract spec: workstation/context/browser-tools-contract-spec.md
# Finding F1: browser_console runs in isolated context; snapshot is authoritative.
# ---------------------------------------------------------------------------

def _compute_snapshot_hash(snapshot: dict[str, Any]) -> str:
    """Stable hash of snapshot text prefix + element_count for cache invalidation."""
    import hashlib
    text = str(snapshot.get("snapshot") or "")[:500]
    count = int(snapshot.get("element_count") or 0)
    return hashlib.sha256(f"{count}|{text}".encode()).hexdigest()[:16]


def _classify_wa_state(
    snapshot: dict[str, Any],
    *,
    consecutive_empty: int = 0,
) -> dict[str, Any]:
    """Classify WhatsApp Web state from snapshot text (snapshot-first, no eval).

    Returns dict with keys: ready (bool), state (str), error_code (str|None).
    States: LOGGED_IN, QR_SCREEN, LOADING, STALE_SNAPSHOT.
    """
    text = str(snapshot.get("snapshot") or "")
    lower = text.lower()
    element_count = int(snapshot.get("element_count") or 0)

    # Stale detection: 3+ consecutive polls with zero elements
    if consecutive_empty >= 3 and element_count == 0:
        return {"ready": False, "state": "STALE_SNAPSHOT", "error_code": "STALE_SNAPSHOT"}

    # QR screen markers
    qr_markers = ["use seu telefone", "scan the qr", "qr code", "escanear"]
    if any(m in lower for m in qr_markers):
        return {"ready": False, "state": "QR_SCREEN", "error_code": "QR_SCREEN_DETECTED"}

    # Loading markers
    loading_markers = ["carregando", "loading"]
    if element_count < 5 and any(m in lower for m in loading_markers):
        return {"ready": False, "state": "LOADING", "error_code": None}

    # Logged-in markers: chat list visible + sufficient elements
    logged_in_markers = ["conversas", "chats", "pesquisar"]
    has_textbox = "[@e" in text and "textbox" in lower
    if any(m in lower for m in logged_in_markers) and element_count >= 10 and has_textbox:
        return {"ready": True, "state": "LOGGED_IN", "error_code": None}

    # Ambiguous / still loading
    if element_count < 5:
        return {"ready": False, "state": "LOADING", "error_code": None}

    return {"ready": False, "state": "LOADING", "error_code": None}


def whatsapp_wait_for_ready(
    *,
    timeout_seconds: float = 30.0,
    poll_interval: float = 1.0,
    require_logged_in: bool = True,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """Wait until WhatsApp Web is usable (logged-in, chat list visible).

    Snapshot-first implementation (Finding F1): uses ``browser_snapshot`` as the
    sole authority for readiness. ``browser_console`` is NOT used because it
    executes in an isolated frame where WA DOM selectors are invisible.

    Integrates with the adaptive polling tiers from ``browser_wait_for_ready``
    when called with default intervals. Adds QR-screen detection and snapshot
    cache to avoid redundant re-classification on stable DOMs.

    Returns
    -------
    dict
        On success: ``{"ready": True, "state": "LOGGED_IN", "elapsed_seconds": ...,
        "element_count": ..., "snapshot_revision": ...}``.
        On failure: ``{"ready": False, "state": ..., "error_code": ..., ...}``.
        Never raises.
    """
    import time as _time

    start = _time.monotonic()
    deadline = start + max(0.5, timeout_seconds)
    prev_hash: Optional[str] = None
    prev_state: Optional[dict[str, Any]] = None
    consecutive_empty = 0
    snapshot_revision = 0
    last_result: dict[str, Any] = {"ready": False}

    while _time.monotonic() < deadline:
        try:
            raw = _dispatch(
                "browser_snapshot", {"full": False},
                task_id=task_id, session_id=session_id, model_facing=False,
            )
            snap = json.loads(raw) if isinstance(raw, str) else raw
        except Exception as exc:
            last_result = {"ready": False, "state": "ERROR", "error_code": "CONTROLLER_UNAVAILABLE", "error": str(exc)}
            _time.sleep(poll_interval)
            continue

        snapshot_revision += 1
        current_hash = _compute_snapshot_hash(snap)

        # Cache hit: same DOM → reuse previous classification
        if current_hash == prev_hash and prev_state is not None:
            element_count = int(snap.get("element_count") or 0)
            if element_count == 0:
                consecutive_empty += 1
            else:
                consecutive_empty = 0
            # Re-check stale even on cache hit
            if consecutive_empty >= 3:
                return {
                    "ready": False, "state": "STALE_SNAPSHOT",
                    "error_code": "STALE_SNAPSHOT",
                    "elapsed_seconds": round(_time.monotonic() - start, 3),
                    "element_count": 0, "snapshot_revision": snapshot_revision,
                }
            if prev_state.get("ready"):
                return {
                    **prev_state,
                    "elapsed_seconds": round(_time.monotonic() - start, 3),
                    "element_count": int(snap.get("element_count") or 0),
                    "snapshot_revision": snapshot_revision,
                }
            last_result = {**prev_state, "snapshot_revision": snapshot_revision}
            _time.sleep(poll_interval)
            continue

        # Cache miss: re-classify
        prev_hash = current_hash
        element_count = int(snap.get("element_count") or 0)
        consecutive_empty = 0 if element_count > 0 else consecutive_empty + 1

        state = _classify_wa_state(snap, consecutive_empty=consecutive_empty)
        prev_state = state

        if state.get("ready"):
            return {
                **state,
                "elapsed_seconds": round(_time.monotonic() - start, 3),
                "element_count": element_count,
                "snapshot_revision": snapshot_revision,
            }

        # Early exit on QR when login is required
        if require_logged_in and state.get("error_code") == "QR_SCREEN_DETECTED":
            return {
                **state,
                "elapsed_seconds": round(_time.monotonic() - start, 3),
                "element_count": element_count,
                "snapshot_revision": snapshot_revision,
            }

        last_result = {
            **state,
            "element_count": element_count,
            "snapshot_revision": snapshot_revision,
        }
        _time.sleep(poll_interval)

    last_result["timeout"] = True
    last_result["elapsed_seconds"] = round(_time.monotonic() - start, 3)
    last_result.setdefault("error_code", "LOADING_TIMEOUT")
    return last_result


def _extract_search_ref(snapshot: dict[str, Any]) -> Optional[str]:
    """Extract @eN ref for the WhatsApp search textbox from snapshot text."""
    text = str(snapshot.get("snapshot") or "")
    # Match pattern: [@eN] textbox "...Pesquisar..." or "...Search..."
    pattern = r'\[(@e\d+)\]\s+textbox\s+"[^"]*(?:Pesquisar|Search)[^"]*"'
    match = re.search(pattern, text, re.IGNORECASE)
    return match.group(1) if match else None


def _parse_search_results(
    snapshot: dict[str, Any],
    *,
    max_results: int = 5,
) -> list[dict[str, str]]:
    """Parse search result gridcells from snapshot text into structured refs."""
    text = str(snapshot.get("snapshot") or "")
    results: list[dict[str, str]] = []
    # Match gridcell rows: [@eN] gridcell "label text"
    pattern = r'\[(@e\d+)\]\s+gridcell\s+"([^"]+)"'
    for match in re.finditer(pattern, text):
        ref = match.group(1)
        label = match.group(2)
        # Skip non-result entries (e.g., section headers)
        if len(label.strip()) < 3:
            continue
        results.append({"ref": ref, "label": label, "type": "chat"})
        if len(results) >= max_results:
            break
    return results


def _verify_conversation_header(
    snapshot: dict[str, Any],
    *,
    contact_name_hint: Optional[str] = None,
) -> dict[str, Any]:
    """Verify conversation header matches expected contact (snapshot-first)."""
    text = str(snapshot.get("snapshot") or "")
    # Extract header text: [@eN] header "Name"
    pattern = r'\[@e\d+\]\s+header\s+"([^"]+)"'
    match = re.search(pattern, text)
    if not match:
        return {"verified": False, "header_text": None, "error_code": "NO_CONVERSATION_OPEN"}

    header_text = match.group(1)
    if contact_name_hint and contact_name_hint.lower() not in header_text.lower():
        return {"verified": False, "header_text": header_text, "error_code": "HEADER_MISMATCH"}

    return {"verified": True, "header_text": header_text, "error_code": None}


def _is_composer_empty(snapshot: dict[str, Any]) -> bool:
    """Check if composer is empty by button revert signal (not innerText).

    Per contract spec / batch-send §6: zero-width nodes keep innerText non-empty.
    The reliable signal is the send button reverting to 'Mensagem de voz'.
    """
    text = str(snapshot.get("snapshot") or "")
    lower = text.lower()
    return "mensagem de voz" in lower or "voice message" in lower


def _extract_delivery_proof(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Extract delivery proof from last message data-id + aria-label."""
    text = str(snapshot.get("snapshot") or "")
    # Match: data-id="..." aria-label="Entregue|Lida|..."
    pattern = r'data-id="([^"]+)"[^[]*aria-label="([^"]+)"'
    matches = list(re.finditer(pattern, text))
    if not matches:
        return {"delivered": False, "message_data_id": None, "ack_label": None}

    last = matches[-1]
    return {
        "delivered": True,
        "message_data_id": last.group(1),
        "ack_label": last.group(2),
    }


def _validate_phone_digits(phone: str) -> bool:
    """Reject masked or non-numeric phone digits."""
    if not phone:
        return False
    stripped = phone.replace("+", "").replace(" ", "").replace("-", "")
    return stripped.isdigit() and "*" not in phone


def _validate_message_body(message: str) -> bool:
    """Reject messages with unreplaced template placeholders."""
    return "{NOME}" not in message and "{nome}" not in message


# ---------------------------------------------------------------------------
# Windows desktop app launcher (standalone, outside browser dispatcher)
# Contract spec: workstation/context/browser-tools-contract-spec.md §4
# ---------------------------------------------------------------------------

def windows_app_launch(
    *,
    app_name: str,
    exe_path: Optional[str] = None,
    bring_to_front: bool = True,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    """Launch a Windows desktop app and verify its window is visible.

    Standalone implementation using ``subprocess.run`` + PowerShell. Does NOT
    use the browser dispatcher. Verifies ``MainWindowHandle != 0`` to confirm
    the window actually surfaced (not just a background process). Optionally
    brings the window to foreground via ``ShowWindow(SW_RESTORE)`` +
    ``SetForegroundWindow``.

    Returns
    -------
    dict
        On success: ``{"launched": True, "pid": int, "window_handle": int,
        "window_title": str, "brought_to_front": bool}``.
        On failure: ``{"launched": False, "error_code": str, ...}``.
        Never raises.
    """
    import platform
    if platform.system() != "Windows":
        return {"launched": False, "error_code": "NOT_WINDOWS",
                "error": f"Platform is {platform.system()}, not Windows"}

    import subprocess
    import time as _time

    # Step 1: Launch the app
    launch_cmd: list[str]
    if exe_path:
        launch_cmd = ["powershell", "-NoProfile", "-Command",
                       f"Start-Process -FilePath '{exe_path}'"]
    else:
        # Try Start-Apps first, fall back to Start-Process by name
        launch_cmd = ["powershell", "-NoProfile", "-Command",
                       f"Start-Process '{app_name}'"]

    try:
        subprocess.run(launch_cmd, capture_output=True, timeout=5, check=False)
    except Exception as exc:
        return {"launched": False, "error_code": "LAUNCH_FAILED",
                "error": str(exc)}

    # Step 2: Find process with MainWindowHandle != 0
    proc_name = Path(exe_path).stem if exe_path else app_name.replace(".exe", "")
    ps_script = (
        f"Get-Process -Name '*{proc_name}*' -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.MainWindowHandle -ne 0 }} | "
        f"Select-Object -First 1 Id, MainWindowHandle, MainWindowTitle | "
        f"ConvertTo-Json -Compress"
    )
    deadline = _time.monotonic() + max(1.0, timeout_seconds)
    pid: Optional[int] = None
    handle: Optional[int] = None
    title: Optional[str] = None

    while _time.monotonic() < deadline:
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=5, check=False,
            )
            if result.stdout.strip():
                info = json.loads(result.stdout.strip())
                if isinstance(info, dict) and info.get("Id"):
                    pid = int(info["Id"])
                    handle = int(info.get("MainWindowHandle", 0))
                    title = str(info.get("MainWindowTitle", ""))
                    break
        except Exception:
            pass
        _time.sleep(0.5)

    if pid is None or handle is None or handle == 0:
        return {"launched": False, "error_code": "WINDOW_NOT_VISIBLE",
                "app_name": app_name, "timeout_seconds": timeout_seconds}

    # Step 3: Bring to front if requested
    brought = False
    if bring_to_front:
        fg_script = (
            f"Add-Type -TypeDefinition '"
            f"using System; using System.Runtime.InteropServices;"
            f"public class Win32 {{"
            f"[DllImport(\"user32.dll\")] public static extern bool ShowWindow(IntPtr h, int n);"
            f"[DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr h);"
            f"}}';"
            f"$h = [IntPtr]{handle};"
            f"[Win32]::ShowWindow($h, 9) | Out-Null;"
            f"[Win32]::SetForegroundWindow($h) | Out-Null;"
            f"Write-Host 'OK'"
        )
        try:
            fg_result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", fg_script],
                capture_output=True, text=True, timeout=5, check=False,
            )
            brought = "OK" in (fg_result.stdout or "")
        except Exception:
            brought = False

    return {
        "launched": True,
        "pid": pid,
        "window_handle": handle,
        "window_title": title or "",
        "brought_to_front": brought,
    }


def whatsapp_send_message(
    *,
    message: str,
    recipient_ref: Optional[dict[str, Any]] = None,
    target_name: Optional[str] = None,
    expected_recipient_name: Optional[str] = None,
    phone_digits: Optional[str] = None,
    contact_name_hint: Optional[str] = None,
    delivery_timeout_seconds: float = 5.0,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    kanban_card_id: Optional[str] = None,
    run_id: Optional[str] = None,
    operation_id: Optional[str] = None,
    batch_item_key: Optional[str] = None,
    use_native_bridge: bool = True,
) -> dict[str, Any]:
    """Native WhatsApp single-send operation.
    recipient_ref selects one trusted contact. The active Hermes session and
    tool-call ID scope the BrowserTask; a Kanban card or TaskRun is not required
    for this one-shot operation. The message is dispatched once and the native
    chat is checked for one new outbound bubble with the exact recipient and text.

    Uses the consolidated primitive in workstation.integrations.hermes.whatsapp_browser_executor.
    States: OBSERVED, UNCERTAIN, or FAILED before send.

    Returns
    -------
    dict
        On observed send: state OBSERVED with message_data_id, ack_label and header_verified.
        On failure / uncertain: ``{"sent": False, "state": ..., "error_code": ..., ...}``.
        Never raises.
    """
    from workstation.integrations.hermes.whatsapp_browser_executor import (
        whatsapp_send_message as _executor_send_message,
        WhatsAppSendError,
        STATE_FAILED,
        sanitize_send_result,
    )
    from workstation.integrations.hermes.whatsapp_recipient_resolution import (
        RecipientResolutionError,
        resolve_recipient_reference,
    )
    from workstation.integrations.hermes.whatsapp_native_lookup import NativeNameLookupError
    from workstation.integrations.hermes.whatsapp_verified_phone import (
        VerifiedPhoneError, open_verified_phone_chat,
    )
    import hashlib

    if (not isinstance(session_id, str) or not session_id.strip()
            or not isinstance(operation_id, str) or not operation_id.strip()):
        return {"sent": False, "state": STATE_FAILED,
                "error_code": "SESSION_CONTEXT_REQUIRED", "failure_phase": "PRE_SEND"}
    # Direct one-shot sends use the trusted Hermes session as BrowserTask owner
    # and the runtime tool-call ID as a fresh run/operation scope.
    if task_id is None and kanban_card_id is None:
        run_id = run_id or operation_id
    elif not task_id or not run_id:
        return {"sent": False, "state": STATE_FAILED,
                "error_code": "TASKRUN_AUTHORITY_REQUIRED", "failure_phase": "PRE_SEND"}
    elif kanban_card_id and task_id != kanban_card_id:
        return {"sent": False, "state": STATE_FAILED,
                "error_code": "INVALID_BROWSER_SCOPE", "failure_phase": "PRE_SEND"}

    snapshot_index = 0
    inspect_index = 0
    click_index = 0
    type_index = 0

    def _step_id(action: str, index: int = 0) -> str:
        identity = ("whatsapp_send_message", task_id, session_id, kanban_card_id, run_id, operation_id, action, index)
        return hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()

    session_scope_only = task_id is None and kanban_card_id is None

    def _browser_step(action: str, arguments: dict[str, Any], index: int = 0):
        return _dispatch(
            action, arguments, task_id=task_id, session_id=session_id,
            kanban_card_id=kanban_card_id, run_id=run_id,
            operation_id=_step_id(action, index), model_facing=False,
            session_scope_only=session_scope_only,
        )

    def _nav(url: str):
        raw = _browser_step("browser_navigate", {"url": url})
        return json.loads(raw) if isinstance(raw, str) else raw

    def _snap(full: bool = False):
        nonlocal snapshot_index
        raw = _browser_step("browser_snapshot", {"full": full}, snapshot_index)
        snapshot_index += 1
        return json.loads(raw) if isinstance(raw, str) else raw

    def _inspect(*, selector: str, attributes: list[str]):
        nonlocal inspect_index
        raw = _browser_step("browser_extract_items", {
            "mode": "inspect", "selector": selector,
            "limit": 64, "attributes": attributes,
        }, inspect_index)
        inspect_index += 1
        return json.loads(raw) if isinstance(raw, str) else raw

    def _click(ref: str):
        nonlocal click_index
        raw = _browser_step("browser_click", {"ref": ref}, click_index)
        click_index += 1
        return json.loads(raw) if isinstance(raw, str) else raw

    def _type(*, ref: str, text: str):
        nonlocal type_index
        raw = _browser_step(
            "browser_type", {"ref": ref, "text": text, "clear": True, "mode": "insert_text"},
            type_index,
        )
        type_index += 1
        return json.loads(raw) if isinstance(raw, str) else raw

    def _press(key: str):
        raw = _browser_step("browser_press", {"key": key})
        return json.loads(raw) if isinstance(raw, str) else raw

    def _console(*, expression: str):
        raw = _browser_step("browser_console", {"expression": expression})
        return json.loads(raw) if isinstance(raw, str) else raw

    failure_phase = "RESOLVE_RECIPIENT"
    try:
        recipient = None
        self_alias_requested = False
        opened_verified_title = None
        if target_name is not None:
            if (recipient_ref is not None or expected_recipient_name is not None
                    or phone_digits is not None or contact_name_hint is not None):
                raise RecipientResolutionError("AMBIGUOUS_RECIPIENT_REFERENCE")
            from workstation.integrations.hermes.whatsapp_native_lookup import (
                find_open_contact_by_name,
            )
            phone_digits = find_open_contact_by_name(
                name=target_name, navigate=_nav, snapshot=_snap,
                type_text=_type, click=_click, inspect=_inspect, press=_press,
            )
            contact_name_hint = target_name
        elif recipient_ref is not None:
            if phone_digits is not None or contact_name_hint is not None:
                raise RecipientResolutionError("AMBIGUOUS_RECIPIENT_REFERENCE")
            recipient = resolve_recipient_reference(recipient_ref)
            # For model-facing sends, the literal user-requested name must
            # match the trusted source. Never promote a fuzzy search result.
            if expected_recipient_name is not None:
                import unicodedata
                def canonical_name(value: str) -> str:
                    decomposed = unicodedata.normalize("NFKD", value)
                    folded = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
                    return " ".join(folded.casefold().split())
                normalized_request = canonical_name(expected_recipient_name) if isinstance(expected_recipient_name, str) else ""
                normalized_source = canonical_name(str(recipient.display_name or ""))
                # The user's own chat has a special verified label:
                # "+<own number> (Voc?)". Treat literal "Voc?" as exact
                # only for the known hermes_local/1 self-contact, and
                # the native chat header binds the selected phone before typing.
                if (normalized_request == "voce"
                        and recipient_ref.get("source") == "hermes_local"
                        and recipient_ref.get("contact_id") == 1):
                    import re
                    label_match = re.fullmatch(
                        r"(.+?)\s*\(([^()]{2,12})\)",
                        str(recipient.display_name or "").strip(), flags=re.IGNORECASE,
                    )
                    if (label_match is not None
                            and canonical_name(label_match.group(2)) == "voce"
                            and re.fullmatch(r"[+0-9\s().-]+", label_match.group(1))
                            and "".join(ch for ch in label_match.group(1) if ch.isdigit())
                                == recipient.phone_digits):
                        self_alias_requested = True
                if (not 3 <= len(expected_recipient_name or "") <= 128
                        or (normalized_request != normalized_source and not self_alias_requested)):
                    return {"sent": False, "state": STATE_FAILED,
                            "error_code": "RECIPIENT_NAME_MISMATCH",
                            "failure_phase": "PRE_SEND"}
            phone_digits = recipient.phone_digits
            contact_name_hint = recipient.display_name
        elif phone_digits is None:
            raise RecipientResolutionError("INVALID_RECIPIENT_REFERENCE")
        else:
            # Campaign phone comes from Alvos.json and its TaskRun, not a model-
            # generated contact alias. Verify WhatsApp's actual recipient
            # number in its native chat UI before composing.
            opened_verified_title = open_verified_phone_chat(
                phone=str(phone_digits), navigate=_nav, snapshot=_snap,
                inspect=_inspect, click=_click,
                console=_console,
            )

        # Session + tool-call identity is supplied by the host, not by model
        # arguments. The native sender verifies the exact chat and new message.
        session_context_verified = bool(session_id and operation_id)
        if not session_context_verified:
            return {"sent": False, "state": STATE_FAILED,
                    "error_code": "SESSION_CONTEXT_REQUIRED", "failure_phase": "PRE_SEND"}

        # A canonical WhatsApp TaskRun cannot silently change recipient
        # after the first accepted reference, even if the model rewrites both
        # recipient_ref and expected_recipient_name on a subsequent call.
        if (recipient is not None or target_name is not None) and task_id and run_id:
            from workstation.integrations.hermes.whatsapp_target_binding import (
                TargetBindingError, bind_recipient_for_run,
            )
            from workstation.integrations.hermes.whatsapp_browser_executor import (
                get_default_db_path,
            )
            target_db = get_default_db_path()
            if target_db is None:
                return {"sent": False, "state": STATE_FAILED,
                        "error_code": "TARGET_BINDING_UNAVAILABLE",
                        "failure_phase": "PRE_SEND"}
            try:
                same_target = bind_recipient_for_run(
                    db_path=target_db, session_id=session_id,
                    run_id=(str(run_id) + ":batch:" + batch_item_key
                            if batch_item_key is not None else str(run_id)),
                    phone_digits=phone_digits,
                )
            except TargetBindingError as exc:
                return {"sent": False, "state": STATE_FAILED,
                        "error_code": str(exc),
                        "failure_phase": "PRE_SEND"}
            if not same_target:
                return {"sent": False, "state": STATE_FAILED,
                        "error_code": "TARGET_CHANGED_REAUTH_REQUIRED",
                        "failure_phase": "PRE_SEND"}

        failure_phase = "EXECUTE_SEND"
        result = _executor_send_message(
            browser_navigate=_nav,
            browser_snapshot=_snap,
            browser_click=_click,
            browser_inspect=_inspect if use_native_bridge else None,
            browser_type=_type if use_native_bridge else None,
            opened_chat_name=target_name or opened_verified_title,
            session_context_verified=session_context_verified,
            approval_fingerprint=None,
            phone_digits=phone_digits,
            message=message,
            contact_name_hint=contact_name_hint,
            verify_delivery=True,
            delivery_timeout_seconds=delivery_timeout_seconds,
            task_id=task_id,
            session_id=session_id,
            run_id=run_id,
            operation_id=operation_id,
            # M1 source DB is read-only provenance; use canonical control DB for send logs.
        )
        result = sanitize_send_result(result, phone_digits=phone_digits, message=message)
        if recipient is not None:
            result["recipient_ref"] = recipient.public_reference
            if recipient.public_reference.get("source") == "hermes_local":
                from workstation.integrations.hermes.whatsapp_contact_intake import (
                    promote_verified_contact,
                )
                # Promote only after the native chat ID and new outbound
                # message receipt were observed for this exact contact.
                verified = promote_verified_contact(
                    recipient.public_reference, phone_digits=phone_digits,
                    receipt_state=result.get("state", ""),
                )
                result["contact_sync"] = (
                    "NATIVE_VERIFIED" if verified else "PENDING_NATIVE_VERIFICATION"
                )
        return result
    except RecipientResolutionError as exc:
        return {"sent": False, "state": STATE_FAILED, "error_code": exc.error_code,
                "failure_phase": "PRE_SEND"}
    except (NativeNameLookupError, VerifiedPhoneError) as exc:
        return {"sent": False, "state": STATE_FAILED,
                "error_code": str(exc), "failure_phase": "RESOLVE_RECIPIENT"}
    except WhatsAppSendError as exc:
        return {
            "sent": False,
            "state": STATE_FAILED,
            "error_code": exc.error_code,
            "error": sanitize_send_result(str(exc), phone_digits=phone_digits or "", message=message),
        }
    except Exception as exc:
        # Never return an exception message: native errors may contain
        # recipient data or message content. Keep the safe stage/code only.
        import re
        native_code = getattr(exc, "error_code", None)
        if not isinstance(native_code, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", native_code):
            native_code = "DISPATCH_FAILED"
        before_send = failure_phase != "EXECUTE_SEND"
        return {
            "sent": False,
            "state": "UNCERTAIN" if not before_send else STATE_FAILED,
            "error_code": native_code,
            "failure_phase": failure_phase,
            "error_type": type(exc).__name__,
        }


def whatsapp_batch_send(
    *,
    recipients: Optional[list[dict[str, Any]]] = None,
    job_id: Optional[str] = None,
    campaign_slug: Optional[str] = None,
    step_code: Optional[str] = None,
    require_authorization: bool = False,
    approval_token: Optional[str] = None,
    approval_threshold: int = 1,
    require_approval: Optional[bool] = None,
    rate_limit_delay_seconds: float = 3.0,
    max_messages: Optional[int] = None,
    max_consecutive_failures: int = 3,
    delivery_timeout_seconds: float = 10.0,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db_path: Optional[str] = None,
) -> dict[str, Any]:
    """Execute or resume a batch of WhatsApp messages with persistent checkpointing."""
    from workstation.integrations.hermes.whatsapp_batch_executor import (
        whatsapp_batch_send as _executor_batch_send,
    )

    def _nav(url: str):
        return _dispatch("browser_navigate", {"url": url}, task_id=task_id, session_id=session_id, model_facing=False)

    def _snap(full: bool = False):
        raw = _dispatch("browser_snapshot", {"full": full}, task_id=task_id, session_id=session_id, model_facing=False)
        return json.loads(raw) if isinstance(raw, str) else raw

    def _click(ref: str):
        return _dispatch("browser_click", {"ref": ref}, task_id=task_id, session_id=session_id, model_facing=False)

    try:
        return _executor_batch_send(
            browser_navigate=_nav,
            browser_snapshot=_snap,
            browser_click=_click,
            recipients=recipients,
            job_id=job_id,
            campaign_slug=campaign_slug,
            step_code=step_code,
            require_authorization=require_authorization,
            approval_token=approval_token,
            approval_threshold=approval_threshold,
            require_approval=require_approval,
            rate_limit_delay_seconds=rate_limit_delay_seconds,
            max_messages=max_messages,
            max_consecutive_failures=max_consecutive_failures,
            delivery_timeout_seconds=delivery_timeout_seconds,
            task_id=task_id,
            session_id=session_id,
            db_path=db_path,
        )
    except Exception as exc:
        return {
            "error": str(exc),
            "status": "FAILED",
        }


def whatsapp_batch_preview(
    *,
    recipients: list[dict[str, Any]],
    campaign_slug: Optional[str] = None,
    step_code: Optional[str] = None,
    message_template: Optional[str] = None,
    require_authorization: bool = False,
    sample_size: int = 3,
    db_path: Optional[str] = None,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """Dry-run inspection of batch recipients before sending (zero browser calls)."""
    from workstation.integrations.hermes.whatsapp_batch_executor import (
        whatsapp_batch_preview as _executor_batch_preview,
    )
    return _executor_batch_preview(
        recipients=recipients,
        campaign_slug=campaign_slug,
        step_code=step_code,
        message_template=message_template,
        require_authorization=require_authorization,
        sample_size=sample_size,
        db_path=db_path,
    )


def whatsapp_batch_approve(
    *,
    manifest_hash: str,
    campaign_slug: Optional[str] = None,
    step_code: Optional[str] = None,
    total_eligible: int = 0,
    approved_by: str = "operator",
    db_path: Optional[str] = None,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """Issue a deterministic approval token bound to the batch manifest hash."""
    from workstation.integrations.hermes.whatsapp_batch_executor import (
        whatsapp_batch_approve as _executor_batch_approve,
    )
    return _executor_batch_approve(
        manifest_hash=manifest_hash,
        campaign_slug=campaign_slug,
        step_code=step_code,
        total_eligible=total_eligible,
        approved_by=approved_by,
        db_path=db_path,
    )


def whatsapp_batch_status(
    *,
    job_id: str,
    db_path: Optional[str] = None,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """Inspect progress, counters, and status of a batch execution."""
    from workstation.integrations.hermes.whatsapp_batch_executor import (
        whatsapp_batch_status as _executor_batch_status,
    )
    return _executor_batch_status(job_id=job_id, db_path=db_path)


def whatsapp_batch_control(
    *,
    job_id: str,
    action: str,
    db_path: Optional[str] = None,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """Control execution of a batch job: pause, cancel, or resume."""
    from workstation.integrations.hermes.whatsapp_batch_executor import (
        whatsapp_batch_cancel,
        whatsapp_batch_pause,
        whatsapp_batch_resume,
    )

    act = (action or "").strip().lower()
    if act == "pause":
        return whatsapp_batch_pause(job_id=job_id, db_path=db_path)
    elif act == "cancel":
        return whatsapp_batch_cancel(job_id=job_id, db_path=db_path)
    elif act == "resume":
        def _nav(url: str):
            return _dispatch("browser_navigate", {"url": url}, task_id=task_id, session_id=session_id, model_facing=False)

        def _snap(full: bool = False):
            raw = _dispatch("browser_snapshot", {"full": full}, task_id=task_id, session_id=session_id, model_facing=False)
            return json.loads(raw) if isinstance(raw, str) else raw

        def _click(ref: str):
            return _dispatch("browser_click", {"ref": ref}, task_id=task_id, session_id=session_id, model_facing=False)

        return whatsapp_batch_resume(
            job_id=job_id,
            browser_navigate=_nav,
            browser_snapshot=_snap,
            browser_click=_click,
            task_id=task_id,
            session_id=session_id,
            db_path=db_path,
        )
    else:
        return {"error": f"Unknown batch control action '{action}'. Use 'pause', 'cancel', or 'resume'."}


def whatsapp_search_contact(
    *,
    query: str,
    max_results: int = 5,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """Search WhatsApp contacts/chats by name or phone suffix (snapshot-first).

    Uses the search textbox ref extracted from ``browser_snapshot`` and
    ``browser_type`` to enter the query. Results are parsed from snapshot
    gridcells — never from ``browser_console`` (Finding F1).

    Returns
    -------
    dict
        On success: ``{"found": True, "results": [...], "search_ref": "@eN",
        "result_count": N}``.
        On failure: ``{"found": False, "error_code": "...", ...}``.
        Never raises.
    """
    # Step 1: get current snapshot and extract search ref
    try:
        raw = _dispatch(
            "browser_snapshot", {"full": False},
            task_id=task_id, session_id=session_id, model_facing=False,
        )
        snap = json.loads(raw) if isinstance(raw, str) else raw
    except Exception as exc:
        return {
            "found": False,
            "error_code": "CONTROLLER_UNAVAILABLE",
            "error": str(exc),
        }

    search_ref = _extract_search_ref(snap)
    if not search_ref:
        return {
            "found": False,
            "error_code": "SEARCH_INPUT_NOT_FOUND",
            "recommended_action": "reload_page",
        }

    # Step 2: type query into search box via browser_type
    try:
        _dispatch(
            "browser_type",
            {"ref": search_ref, "text": query, "mode": "plain_text_paste"},
            task_id=task_id, session_id=session_id, model_facing=False,
        )
    except Exception as exc:
        return {
            "found": False,
            "error_code": "TYPE_FAILED",
            "error": str(exc),
            "search_ref": search_ref,
        }

    # Step 3: wait briefly for results to render, then re-snapshot
    import time as _time
    _time.sleep(0.6)

    try:
        raw2 = _dispatch(
            "browser_snapshot", {"full": False},
            task_id=task_id, session_id=session_id, model_facing=False,
        )
        snap2 = json.loads(raw2) if isinstance(raw2, str) else raw2
    except Exception as exc:
        return {
            "found": False,
            "error_code": "CONTROLLER_UNAVAILABLE",
            "error": str(exc),
            "search_ref": search_ref,
        }

    # Step 4: parse results from updated snapshot
    results = _parse_search_results(snap2, max_results=max_results)

    if not results:
        return {
            "found": False,
            "error_code": "NO_RESULTS",
            "search_ref": search_ref,
            "result_count": 0,
        }

    return {
        "found": True,
        "results": results,
        "search_ref": search_ref,
        "result_count": len(results),
    }


def whatsapp_read_messages_current(
    *, limit: int, session_id: str, operation_id: str,
) -> dict[str, Any]:
    """Inspect only the already-open, session-owned WhatsApp chat."""
    from workstation.integrations.hermes.whatsapp_native_read import read_current_chat
    if not isinstance(session_id, str) or not session_id or not operation_id:
        return {"success": False, "error_code": "SESSION_CONTEXT_REQUIRED"}
    def native_console(*, expression: str) -> dict[str, Any]:
        raw = _dispatch(
            "browser_console", {"expression": expression},
            session_id=session_id, run_id=operation_id,
            operation_id=operation_id + "-current-read",
            model_facing=False, session_scope_only=True,
        )
        return json.loads(raw) if isinstance(raw, str) else raw
    try:
        return read_current_chat(console=native_console, limit=limit)
    except Exception:
        return {"success": False, "error_code": "NATIVE_READ_UNAVAILABLE"}


def whatsapp_read_messages_named(
    *, target_name: str, limit: int = 20,
    session_id: str, operation_id: str,
) -> dict[str, Any]:
    """Open the exact WhatsApp contact in the owned BrowserTask and read its DOM.

    Read-only external effect: never types in a conversation, never clicks Send,
    and never persists message text or recipient numbers.
    """
    from workstation.integrations.hermes.whatsapp_native_lookup import (
        NativeNameLookupError, find_open_contact_by_name,
    )
    from workstation.integrations.hermes.whatsapp_native_read import read_current_chat
    import hashlib

    if not isinstance(session_id, str) or not session_id or not operation_id:
        return {"success": False, "error_code": "SESSION_CONTEXT_REQUIRED"}
    sequence: dict[str, int] = {}

    def step(action: str, args: dict[str, Any]) -> dict[str, Any]:
        i = sequence.get(action, 0)
        sequence[action] = i + 1
        identity = hashlib.sha256(
            f"{session_id}|{operation_id}|{action}|{i}".encode()
        ).hexdigest()
        raw = _dispatch(
            action, args, task_id=None, session_id=session_id,
            run_id=operation_id, operation_id=identity,
            model_facing=False, session_scope_only=True,
        )
        return json.loads(raw) if isinstance(raw, str) else raw

    try:
        resolved = find_open_contact_by_name(
            name=target_name,
            navigate=lambda **kw: step("browser_navigate", kw),
            snapshot=lambda **kw: step("browser_snapshot", {"full": kw.get("full", False)}),
            type_text=lambda **kw: step("browser_type", {
                "ref": kw["ref"], "text": kw["text"], "clear": True, "mode": "insert_text"}),
            click=lambda **kw: step("browser_click", kw),
            inspect=lambda **kw: step("browser_extract_items", {
                "mode": "inspect", "selector": kw["selector"], "limit": 64,
                "attributes": kw["attributes"]}),
            press=lambda **kw: step("browser_press", kw),
        )
        if not resolved:
            return {"success": False, "error_code": "NATIVE_CONTACT_PHONE_UNAVAILABLE"}
        result = read_current_chat(
            console=lambda **kw: step("browser_console", kw), limit=limit,
        )
        if result.get("success"):
            result["target_verified"] = True
            result["target_name"] = target_name
        return result
    except NativeNameLookupError as exc:
        return {"success": False, "error_code": str(exc)}
    except Exception as exc:
        return {"success": False, "error_code": "NATIVE_READ_UNAVAILABLE",
                "error_type": type(exc).__name__}


def whatsapp_read_messages(
    *,
    limit: int = 20,
    contact_name_hint: Optional[str] = None,
    contact_id: Optional[int] = None,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db_path: Optional[str | Path] = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Read recent messages from the currently active WhatsApp Web conversation.

    Snapshot-first, deduplicated, and integrated with contacts, conversations, and messages.
    """
    from workstation.integrations.hermes.whatsapp_browser_executor import (
        whatsapp_read_messages as _executor_read_messages,
    )

    def _snap(full: bool = False):
        raw = _dispatch("browser_snapshot", {"full": full}, task_id=task_id, session_id=session_id, model_facing=False)
        return json.loads(raw) if isinstance(raw, str) else raw

    try:
        return _executor_read_messages(
            browser_snapshot=_snap,
            limit=limit,
            contact_name_hint=contact_name_hint,
            contact_id=contact_id,
            db_path=db_path,
            persist=persist,
        )
    except Exception as exc:
        return {
            "success": False,
            "error_code": "DISPATCH_FAILED",
            "error": str(exc),
            "messages": [],
            "count": 0,
        }


def whatsapp_campaign_check_optout(
    *, phone_digits: str, task_id: str, session_id: str,
    run_id: str, operation_id: str,
) -> dict[str, Any]:
    """Inspect recent mounted messages for explicit unsubscribe requests."""
    from workstation.integrations.hermes.whatsapp_verified_phone import (
        VerifiedPhoneError, open_verified_phone_chat,
    )
    from workstation.integrations.hermes.whatsapp_native_read import read_current_chat
    import hashlib
    import unicodedata

    counts: dict[str, int] = {}
    def step(action: str, args: dict[str, Any]) -> dict[str, Any]:
        n=counts.get(action,0)
        counts[action]=n+1
        eid=hashlib.sha256(
            f"{operation_id}|{task_id}|{run_id}|{session_id}|{action}|{n}".encode()
        ).hexdigest()
        raw=_dispatch(
            action,args,task_id=task_id,kanban_card_id=task_id,
            session_id=session_id,run_id=run_id,operation_id=eid,
            model_facing=False,
        )
        return json.loads(raw) if isinstance(raw,str) else raw
    try:
        open_verified_phone_chat(
            phone=phone_digits,
            navigate=lambda **kw: step("browser_navigate",kw),
            snapshot=lambda **kw: step("browser_snapshot",{"full":False}),
            inspect=lambda **kw: step("browser_extract_items",{
                "mode":"inspect","selector":kw["selector"],"limit":64,
                "attributes":kw["attributes"]}),
            click=lambda **kw: step("browser_click",kw),
        )
        recent=read_current_chat(
            console=lambda **kw: step("browser_console",kw),limit=50,
        )
        if not recent.get("success"):
            return {"state":"HOLD","error_code":"OPT_OUT_READ_UNAVAILABLE"}
        def fold(value: str) -> str:
            s=unicodedata.normalize("NFKD",value.lower())
            return "".join(c for c in s if not unicodedata.combining(c)).strip()
        stop_phrases={
            "sair","stop","cancelar","descadastrar","pare",
            "nao quero mais receber mensagens","me remova da lista",
            "nao me envie mais mensagens","por favor nao entre em contato",
        }
        if any(fold(str(msg.get("text") or "")) in stop_phrases
               for msg in recent["messages"] if msg.get("direction")!="outbound"):
            return {"state":"OPT_OUT"}
        return {"state":"CLEAR","messages_checked":recent["count"]}
    except VerifiedPhoneError as exc:
        return {"state":"HOLD","error_code":str(exc)}
    except Exception:
        return {"state":"HOLD","error_code":"OPT_OUT_CHECK_FAILED"}


def whatsapp_send_image_verified(
    *, phone_digits: str, caption: str, media_path: str,
    task_id: str, session_id: str, run_id: str, operation_id: str,
) -> dict[str, Any]:
    """Send one verified image/caption inside an authorized campaign TaskRun."""
    from workstation.integrations.hermes.whatsapp_native_media import native_send_image_once
    from workstation.integrations.hermes.whatsapp_browser_executor import _validate_attachment_file

    if not all(isinstance(v,str) and v for v in (
        task_id, session_id, run_id, operation_id, caption, phone_digits, media_path,
    )):
        return {"state": "FAILED", "error_code": "MEDIA_CONTEXT_REQUIRED"}
    try:
        resolved,size,content_type = _validate_attachment_file(media_path)
        if not content_type.startswith("image/"):
            return {"state":"FAILED","error_code":"MEDIA_IMAGE_REQUIRED"}
    except Exception:
        return {"state":"FAILED","error_code":"MEDIA_FILE_INVALID"}
    counts: dict[str,int] = {}

    def step(action: str, args: dict[str,Any]) -> dict[str,Any]:
        index=counts.get(action,0)
        counts[action]=index+1
        eid=hashlib.sha256(
            f"{task_id}|{session_id}|{run_id}|{operation_id}|{action}|{index}".encode()
        ).hexdigest()
        raw=_dispatch(action,args,task_id=task_id,kanban_card_id=task_id,
                      run_id=run_id,session_id=session_id,operation_id=eid,
                      model_facing=False)
        return json.loads(raw) if isinstance(raw,str) else raw

    import hashlib
    return native_send_image_once(
        phone=phone_digits,caption=caption,media_path=str(resolved),
        navigate=lambda **kw: step("browser_navigate",kw),
        snapshot=lambda **kw: step("browser_snapshot",{"full":False}),
        inspect=lambda **kw: step("browser_extract_items",{
            "mode":"inspect","selector":kw["selector"],"limit":64,
            "attributes":kw["attributes"]}),
        click=lambda **kw: step("browser_click",kw),
        type_text=lambda **kw: step("browser_type",{
            "ref":kw["ref"],"text":kw["text"],"clear":True,"mode":"insert_text"}),
        upload=lambda **kw: step("browser_file_upload",{
            "files":kw["files"],"selector":'input[type="file"][accept*="image/"]'}),
    )


def whatsapp_send_attachment(
    *,
    phone_digits: str,
    file_path: str,
    caption: Optional[str] = None,
    contact_name_hint: Optional[str] = None,
    verify_delivery: bool = True,
    delivery_timeout_seconds: float = 15.0,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    db_path: Optional[str | Path] = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Send an attachment (image, document, audio, video) via WhatsApp Web.

    Validates file existence, size (<50MB), allowed extension, and optional caption.
    Uses native file upload, clicks send in preview, and verifies delivery proof.
    """
    from workstation.integrations.hermes.whatsapp_browser_executor import (
        whatsapp_send_attachment as _executor_send_attachment,
        WhatsAppSendError,
        STATE_FAILED,
    )

    def _nav(url: str):
        return _dispatch("browser_navigate", {"url": url}, task_id=task_id, session_id=session_id, model_facing=False)

    def _snap(full: bool = False):
        raw = _dispatch("browser_snapshot", {"full": full}, task_id=task_id, session_id=session_id, model_facing=False)
        return json.loads(raw) if isinstance(raw, str) else raw

    def _click(ref: str):
        return _dispatch("browser_click", {"ref": ref}, task_id=task_id, session_id=session_id, model_facing=False)

    def _type(ref: str, text: str):
        return _dispatch("browser_type", {"ref": ref, "text": text}, task_id=task_id, session_id=session_id, model_facing=False)

    def _upload(files: list[str]):
        return _dispatch("browser_file_upload", {"files": files}, task_id=task_id, session_id=session_id, model_facing=False)

    try:
        return _executor_send_attachment(
            browser_navigate=_nav,
            browser_snapshot=_snap,
            browser_click=_click,
            browser_file_upload=_upload,
            browser_type=_type,
            phone_digits=phone_digits,
            file_path=file_path,
            caption=caption,
            contact_name_hint=contact_name_hint,
            verify_delivery=verify_delivery,
            delivery_timeout_seconds=delivery_timeout_seconds,
            task_id=task_id,
            session_id=session_id,
            db_path=db_path,
            persist=persist,
        )
    except WhatsAppSendError as exc:
        return {
            "sent": False,
            "state": STATE_FAILED,
            "error_code": exc.error_code,
            "error": str(exc),
        }
    except Exception as exc:
        return {
            "sent": False,
            "state": STATE_FAILED,
            "error_code": "DISPATCH_FAILED",
            "error": str(exc),
        }


def whatsapp_metrics_summary(
    *,
    campaign_id: Optional[str] = None,
    job_id: Optional[str] = None,
    operation_name: Optional[str] = None,
    db_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Retrieve aggregate telemetry and reliability metrics for WhatsApp operations."""
    from workstation.integrations.hermes.whatsapp_metrics import get_metrics_summary
    return get_metrics_summary(
        campaign_id=campaign_id,
        job_id=job_id,
        operation_name=operation_name,
        db_path=db_path,
    )


def whatsapp_metrics_benchmark(
    *,
    campaign_id: Optional[str] = None,
    db_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """Compare current WhatsApp execution metrics against the 23/10/2026 baseline session."""
    from workstation.integrations.hermes.whatsapp_metrics import compare_against_baseline
    return compare_against_baseline(
        campaign_id=campaign_id,
        db_path=db_path,
    )

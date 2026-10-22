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
    # Extension management is a Desktop-session capability: the agent can
    # request it explicitly, but non-Desktop sessions never carry these
    # schemas. Runtime reachability/policy remain checked at dispatch.
    "browser_extension_install",
    "browser_extension_list",
    "browser_extension_uninstall",
    "browser_extension_open_options",
})


def workstation_schema_tools_for_current_session() -> set[str]:
    """Schemas structurally owned by a Desktop/Workstation session.

    Surface capability belongs to the session source, not to a 200 ms
    controller health probe. Returning these names does *not* claim the
    controller is reachable; workstation_routed_browser_handler() keeps
    the authoritative health/recovery/fail-closed decision at dispatch.
    """
    if not workstation_browser_enabled():
        return set()
    try:
        from gateway.session_context import get_session_env
    except Exception:
        return set()
    source = str(get_session_env("HERMES_SESSION_SOURCE", "") or "").strip().lower()
    platform = str(get_session_env("HERMES_SESSION_PLATFORM", "") or "").strip().lower()
    surface = source or platform
    if surface != "desktop":
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
    "browser_extension_load", "browser_extension_remove", "browser_extension_open_options",
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
    # A Browser session is not a Kanban TaskRun. Do not infer authority from
    # the only task matching a session, from the task's latest run, or from
    # process-wide env vars that can survive a chat switch. Session-bound
    # callers must supply the exact card/run identifiers at the call site.
    if session_id:
        rid = str(run_id or "").strip() or None
        card_id = str(kanban_card_id or (task_id if (task_id and rid) else "") or "").strip() or None
    else:
        # Legacy headless callers without a chat identity may still use the
        # existing process context. This is never applied to session calls.
        rid = str(run_id or os.environ.get("HERMES_KANBAN_RUN_ID") or "").strip() or None
        card_id = str(kanban_card_id or (task_id if (task_id and rid) else "") or os.environ.get("HERMES_KANBAN_TASK") or "").strip() or None

    if card_id and rid:
        # Explicit canonical work retains the requested BrowserTask identity;
        # only unbound per-turn agent UUIDs collapse to the stable chat.
        key = str(task_id or card_id)

    # A partial explicit binding has no canonical authorization. Do not
    # downgrade it to an unbound Browser session or forward a card-only hint.
    if bool(card_id) != bool(rid):
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
    payload: dict[str, Any] = {
        "action": action,
        "arguments": clean_args,
        "task_id": key,
        "session_id": session_id,
        "operation_id": op_id,
        "call_key": call_key(action, clean_args),
    }
    if card_id:
        payload["kanban_card_id"] = card_id
    if rid:
        payload["run_id"] = rid
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
    if isinstance(result, str):
        return result
    return json.dumps(project_model_browser_payload(result) if model_facing else result, ensure_ascii=False)


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
    phone_digits: str,
    message: str,
    contact_name_hint: Optional[str] = None,
    verify_delivery: bool = True,
    delivery_timeout_seconds: float = 10.0,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> dict[str, Any]:
    """Send a WhatsApp message via deep link and verify delivery (snapshot-first).

    Validates inputs (no masked phones, no unreplaced placeholders), navigates
    via ``browser_navigate`` to the WA send URL, verifies the conversation
    header matches ``contact_name_hint``, clicks the send button obtained from
    the snapshot, and proves delivery by detecting a new ``data-id`` with an
    ack ``aria-label`` in the messages panel. Composer emptiness is checked by
    button revert signal ('Mensagem de voz'), never by innerText (batch-send §6).

    Returns
    -------
    dict
        On success: ``{"sent": True, "state": "DELIVERED", "message_data_id": ...,
        "ack_label": ..., "header_verified": ..., "composer_empty_after": True}``.
        On failure: ``{"sent": False, "state": ..., "error_code": ..., ...}``.
        Never raises.
    """
    # Pre-validation
    if not _validate_phone_digits(phone_digits):
        return {"sent": False, "state": "INVALID_INPUT", "error_code": "MASKED_PHONE"}
    if not _validate_message_body(message):
        return {"sent": False, "state": "INVALID_INPUT", "error_code": "TEMPLATE_PLACEHOLDER_LEAK"}

    import time as _time
    from urllib.parse import quote

    # Step 1: Deep link navigation
    url = f"https://web.whatsapp.com/send?phone={phone_digits}&text={quote(message)}"
    try:
        _dispatch(
            "browser_navigate", {"url": url},
            task_id=task_id, session_id=session_id, model_facing=False,
        )
    except Exception as exc:
        return {"sent": False, "state": "NAVIGATION_FAILED", "error_code": "CONTROLLER_UNAVAILABLE", "error": str(exc)}

    # Step 2: Wait for conversation header to appear
    deadline = _time.monotonic() + 8.0
    header_snap = None
    while _time.monotonic() < deadline:
        try:
            raw = _dispatch("browser_snapshot", {"full": False}, task_id=task_id, session_id=session_id, model_facing=False)
            header_snap = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            _time.sleep(0.5)
            continue
        hdr = _verify_conversation_header(header_snap, contact_name_hint=None)
        if hdr.get("verified"):
            break
        _time.sleep(0.5)
    else:
        return {"sent": False, "state": "NO_CONVERSATION_OPEN", "error_code": "NO_CONVERSATION_OPEN"}

    # Step 3: Header mismatch check
    if contact_name_hint:
        hdr_check = _verify_conversation_header(header_snap, contact_name_hint=contact_name_hint)
        if not hdr_check.get("verified"):
            return {
                "sent": False, "state": "HEADER_MISMATCH",
                "error_code": "HEADER_MISMATCH",
                "header_text": hdr_check.get("header_text"),
            }

    # Step 4: Find and click send button from snapshot
    send_ref = None
    snap_text = str(header_snap.get("snapshot") or "")
    import re as _re
    for m in _re.finditer(r'\[(@e\d+)\]\s+button\s+"[^"]*(?:Enviar|Send)[^"]*"', snap_text, _re.IGNORECASE):
        send_ref = m.group(1)
        break
    if not send_ref:
        return {"sent": False, "state": "SEND_BUTTON_NOT_FOUND", "error_code": "NO_CONVERSATION_OPEN"}

    try:
        _dispatch("browser_click", {"ref": send_ref}, task_id=task_id, session_id=session_id, model_facing=False)
    except Exception as exc:
        return {"sent": False, "state": "CLICK_FAILED", "error_code": "CONTROLLER_UNAVAILABLE", "error": str(exc)}

    # Step 5: Post-send verification
    if not verify_delivery:
        return {"sent": True, "state": "SENT_UNCONFIRMED", "header_verified": hdr_check.get("header_text") if contact_name_hint else None}

    proof_deadline = _time.monotonic() + max(1.0, delivery_timeout_seconds)
    while _time.monotonic() < proof_deadline:
        _time.sleep(0.5)
        try:
            raw_post = _dispatch("browser_snapshot", {"full": False}, task_id=task_id, session_id=session_id, model_facing=False)
            post_snap = json.loads(raw_post) if isinstance(raw_post, str) else raw_post
        except Exception:
            continue
        composer_empty = _is_composer_empty(post_snap)
        proof = _extract_delivery_proof(post_snap)
        if proof.get("delivered") and composer_empty:
            return {
                "sent": True, "state": "DELIVERED",
                "message_data_id": proof.get("message_data_id"),
                "ack_label": proof.get("ack_label"),
                "header_verified": hdr_check.get("header_text") if contact_name_hint else None,
                "composer_empty_after": True,
            }

    return {
        "sent": True, "state": "SENT_UNCONFIRMED",
        "error_code": "DELIVERY_TIMEOUT",
        "header_verified": hdr_check.get("header_text") if contact_name_hint else None,
        "composer_empty_after": _is_composer_empty(post_snap) if 'post_snap' in dir() else None,
    }


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

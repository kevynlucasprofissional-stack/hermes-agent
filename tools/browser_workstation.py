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
import socket
import sys
import threading
import time
import uuid
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
        details: Optional[Dict[str, Any]] = None,
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
    def from_payload(cls, payload: Dict[str, Any], *, http_status: int | None = None) -> "WorkstationBrowserError":
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

    def to_dict(self) -> Dict[str, Any]:
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


def _browser_config() -> Dict[str, Any]:
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


def read_native_browser_session_state(task_id: str, session_id: str, run_id: str, expected_url: str) -> dict:
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
    if task.get("lastReceipt"):
        last_receipt = task["lastReceipt"]
        if not isinstance(last_receipt, dict) or str(last_receipt.get("runId", "")) != str(run_id):
            raise ValueError("BrowserTask receipt run binding drifted")
    if task.get("status") not in {"visible", "hidden", "parked"}:
        raise ValueError("BrowserTask status is invalid")
    tabs = state.get("tabs")
    if not isinstance(tabs, list):
        raise ValueError("BrowserSessionState tabs are invalid")
    owned = [tab for tab in tabs if isinstance(tab, dict) and tab.get("browserTaskId") == task_id]
    if len(owned) != 1:
        raise ValueError("BrowserTask tab identity is missing or ambiguous")
    tab = owned[0]
    actual = urlsplit(str(tab.get("safeUrl") or ""))
    expected = urlsplit(expected_url)
    if (actual.scheme not in {"http", "https"} or actual.username or actual.password
            or actual.query or actual.fragment or not actual.hostname
            or (actual.scheme, actual.hostname, actual.path or "/")
            != (expected.scheme, expected.hostname, expected.path or "/")):
        raise ValueError("BrowserTask safe URL does not match the navigation goal")
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
    }


def _canonical_browser_task_binding(task_id: Optional[str], session_id: Optional[str]) -> str:
    """Return bound/unbound/unknown/conflict from Electron's BrowserTask projection."""
    if not task_id:
        return "unknown"
    path = workstation_browser_task_state_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
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


def _read_control() -> Dict[str, Any]:
    path = workstation_control_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
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
    payload: Optional[Dict[str, Any]] = None,
    *,
    timeout: float,
    action: Optional[str] = None,
) -> Dict[str, Any]:
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
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
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
    except (TimeoutError, socket.timeout) as exc:
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


def workstation_controller_resources(*, timeout: float = _DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
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
) -> Dict[str, Any]:
    """Read bounded canonical journal events from the Electron controller."""

    bounded_limit = min(200, max(1, int(limit)))
    suffix = f"/events?limit={bounded_limit}"
    if task_id:
        suffix += f"&task_id={quote(str(task_id), safe='')}"
    return _request_json("GET", suffix, timeout=timeout)


def _task_key(task_id: Optional[str], session_id: Optional[str]) -> str:
    return str(task_id or session_id or "default").strip() or "default"


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


def _validate_navigation(args: Dict[str, Any]) -> None:
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
    args: Dict[str, Any],
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


def _dispatch(
    action: str,
    args: Dict[str, Any],
    *,
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    kanban_card_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> str:
    if action == "browser_navigate":
        _validate_navigation(args)
    if action == "browser_type":
        resolve_browser_type_text(args, task_id=task_id, session_id=session_id)
    key = _task_key(task_id, session_id)
    try:
        timeout = float(os.getenv("HERMES_WORKSTATION_BROWSER_TIMEOUT", str(_DEFAULT_TIMEOUT_SECONDS)))
    except ValueError:
        timeout = _DEFAULT_TIMEOUT_SECONDS
    session_card_id = ""
    try:
        from gateway.session_context import get_session_env
        session_card_id = get_session_env("HERMES_KANBAN_TASK", "")
    except Exception:
        pass
    card_id = (kanban_card_id or session_card_id or os.environ.get("HERMES_KANBAN_TASK") or "").strip() or None
    rid = (run_id or os.environ.get("HERMES_KANBAN_RUN_ID") or "").strip() or None

    if not card_id and task_id:
        card_id = str(task_id).strip() or None

    if not card_id and session_id:
        try:
            from hermes_cli import kanban_db
            from hermes_cli.kanban_db_connect import connect
            conn = connect()
            try:
                tasks = kanban_db.list_tasks(conn, status=None)
                active = [t for t in tasks if t.session_id == session_id and t.status not in {'done', 'cancelled'}]
                if len(active) == 1:
                    card_id = active[0].id
                    if not rid and active[0].current_run_id:
                        rid = str(active[0].current_run_id)
            finally:
                conn.close()
        except Exception:
            pass

    if card_id and not rid:
        try:
            from hermes_cli import kanban_db
            from hermes_cli.kanban_db_connect import connect
            conn = connect()
            try:
                ktask = kanban_db.get_task(conn, card_id)
                if ktask and ktask.current_run_id:
                    rid = str(ktask.current_run_id)
            finally:
                conn.close()
        except Exception:
            pass

    if card_id and not task_id:
        key = card_id

    if card_id and rid:
        from hermes_cli import kanban_db
        from hermes_cli.kanban_db_connect import connect
        conn = connect()

        try:
            task = kanban_db.get_task(conn, card_id)
            if task and (str(task.current_run_id) != str(rid) or task.status in {'done', 'cancelled'}):
                raise WorkstationBrowserError('Stale TaskRun cannot control BrowserTask',
                    error_code='STALE_RUN', retryable=False, state_changed=False,
                    recommended_action='RECONCILE_BINDING')
        finally:
            conn.close()
    payload: Dict[str, Any] = {
        "action": action,
        "arguments": dict(args),
        "task_id": key,
        "session_id": session_id,
    }
    if card_id:
        payload["kanban_card_id"] = card_id
    if rid:
        payload["run_id"] = rid
    from workstation.batch_detection import call_key
    op_id = args.get("operation_id") or os.environ.get("HERMES_OPERATION_ID") or f"op_{action}_{uuid.uuid4().hex[:12]}"
    payload["operation_id"] = op_id
    payload["call_key"] = call_key(action, args)
    response = _request_json(
        "POST",
        "/v1/action",
        payload,
        timeout=max(0.25, timeout),
        action=action,
    )
    result = _force_redact(response.get("result"))
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
    return json.dumps(result, ensure_ascii=False)


call_workstation_browser = _dispatch


def workstation_routed_browser_handler(
    action: str,
    args: Dict[str, Any],
    *,
    fallback: Callable[[], Any],
    task_id: Optional[str] = None,
    session_id: Optional[str] = None,
    kanban_card_id: Optional[str] = None,
    run_id: Optional[str] = None,
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
        BrowserControlLeaseManager.get_instance().assert_action_allowed(task_id, action,
            fence_token=args.get('fence_token'))

    # Once selected, the internal browser is authoritative for this call.
    # Dispatch failures propagate and never trigger a second browser lane.
    return _dispatch(
        action, args, task_id=task_id, session_id=session_id,
        kanban_card_id=kanban_card_id, run_id=run_id,
    )

"""CW-047 creative web app lifecycle management and loopback launch service.

Supervises local static servers for PhotoCraft and EffectCraft, binding strictly
to 127.0.0.1, verifying readiness via per-instance HMAC-safe nonces, and managing
reusable instances in the canonical ProcessRegistry.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import secrets
import shlex
import socket
import subprocess
import sys
import threading
import time
from typing import Any, Callable, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from hermes_constants import get_hermes_home
from hermes_cli._subprocess_compat import windows_hide_flags
from tools.approval import check_all_command_guards
from tools.process_registry import ProcessRegistry, process_registry
from workstation.creative_web_app_spec import (
    APPS, CreativeWebApp, managed_loopback_url, matches_managed_loopback_url, prebuilt_site_root
)

logger = logging.getLogger(__name__)

DEFAULT_CREATIVE_BASE_PORT = 8765
DEFAULT_CREATIVE_MAX_PORT = 8899
WEB_APP_READY_TIMEOUT = 10.0
WEB_APP_HEALTH_TIMEOUT = 2.0

PREFERRED_CREATIVE_PORTS = {
    "photocraft": 8765,
    "effectcraft": 8766,
    "filmcraft": 8767,
}


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Check if loopback port is available for binding strictly on host."""
    if not isinstance(port, int) or isinstance(port, bool) or not (1024 <= port <= 65535):
        return False
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if os.name != "nt":
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
            return True
        except OSError:
            return False


class CreativeWebAppError(RuntimeError):
    """Structured error for creative web app lifecycle failures."""


@dataclass(frozen=True)
class CreativeWebAppInstance:
    engine: str
    process_id: str
    port: int
    url: str
    nonce: str
    root: Path
    created_at: str


@dataclass(frozen=True)
class CreativeWebAppLaunchReceipt:
    status: str  # verified | uncertain | missing_dist | user_control_active | failed | refused
    engine: str
    url: str = ""
    port: int = 0
    observed_url: str = ""
    reason: str = ""
    reused: bool = False
    dispatch_attempted: bool = False

    def safe_dict(self) -> dict:
        return {
            "status": self.status,
            "engine": self.engine,
            "url": self.url,
            "port": self.port,
            "observed_url": self.observed_url,
            "reason": self.reason,
            "reused": self.reused,
            "dispatch_attempted": self.dispatch_attempted,
        }


_INSTANCES_LOCK = threading.Lock()
_ACTIVE_INSTANCES: dict[str, CreativeWebAppInstance] = {}


def discover_web_app_dist(engine: str) -> Path | None:
    """Locate prebuilt web dist for engine from config or standard paths.

    Never compiles, installs, or downloads.
    """
    if engine not in APPS:
        return None

    candidates: list[Path] = []

    # 1. Environment variable override: e.g. HERMES_PHOTOCRAFT_WEB_DIST
    env_key = f"HERMES_{engine.upper()}_WEB_DIST"
    env_val = os.environ.get(env_key, "").strip()
    if env_val:
        candidates.append(Path(env_val))

    # 2. Hermes Home standard path: ~/.hermes/workstation/creative/engines/{engine}/web-dist
    home = get_hermes_home()
    candidates.append(home / "workstation" / "creative" / "engines" / engine / "web-dist")

    # 3. In-repo candidate directories if pre-staged
    candidates.append(Path.cwd() / "external-engines" / engine / "packaging" / "web")
    candidates.append(Path.cwd() / "web-dist" / engine)

    for c in candidates:
        try:
            resolved = c.expanduser().resolve()
            if resolved.is_dir() and (resolved / "index.html").is_file():
                return prebuilt_site_root(resolved)
        except (OSError, RuntimeError, ValueError):
            continue

    return None


def allocate_creative_port(
    host: str = "127.0.0.1",
    start_port: int = DEFAULT_CREATIVE_BASE_PORT,
    max_port: int = DEFAULT_CREATIVE_MAX_PORT,
) -> int:
    """Find and verify an available loopback TCP port strictly on 127.0.0.1."""
    if host != "127.0.0.1":
        raise ValueError("Loopback port allocation strictly requires 127.0.0.1")

    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if os.name != "nt":
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                probe.bind((host, port))
                return port
            except OSError:
                continue

    raise CreativeWebAppError(f"No available loopback port in range {start_port}-{max_port}")


def probe_creative_web_app_health(
    instance: CreativeWebAppInstance,
    *,
    registry: Optional[ProcessRegistry] = None,
    timeout: float = WEB_APP_HEALTH_TIMEOUT,
) -> bool:
    """Verify that instance process is alive and responds with expected engine and nonce."""
    if registry is None:
        registry = process_registry

    poll = registry.poll(instance.process_id)
    if poll.get("status") in {"exited", "error"}:
        return False

    url = f"http://127.0.0.1:{instance.port}/__hermes_health"
    req = Request(
        url,
        headers={
            "User-Agent": "Hermes-Creative-Probe/1.0",
            "X-Hermes-Creative-Nonce": instance.nonce,
        },
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("ready") is True and data.get("engine") == instance.engine
    except (URLError, OSError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        return False

    return False


def start_creative_web_app_server(
    engine: str,
    *,
    dist_root: Optional[Path] = None,
    port: Optional[int] = None,
    registry: Optional[ProcessRegistry] = None,
    timeout: float = WEB_APP_READY_TIMEOUT,
) -> CreativeWebAppInstance:
    if engine not in APPS:
        raise ValueError(f"Unknown creative web app engine: {engine}")

    root = dist_root or discover_web_app_dist(engine)
    if root is None:
        raise CreativeWebAppError(f"missing_prebuilt_web_dist:{engine}")

    valid_root = prebuilt_site_root(root)
    if port is not None:
        assigned_port = port
    else:
        pref = PREFERRED_CREATIVE_PORTS.get(engine)
        if pref is not None and is_port_available(pref):
            assigned_port = pref
        else:
            assigned_port = allocate_creative_port()
    nonce = secrets.token_hex(24)

    argv = [
        sys.executable,
        "-m",
        "workstation.creative_web_static_server",
        "--engine",
        engine,
        "--root",
        str(valid_root),
        "--port",
        str(assigned_port),
    ]
    command = shlex.join(argv)

    approval = check_all_command_guards(command, "local", has_host_access=True)
    if not approval.get("approved", False):
        raise PermissionError(f"Creative web server execution denied by command guards: {command}")

    # Build clean child environment with essential platform variables
    env = {
        key: os.environ[key]
        for key in (
            "SYSTEMROOT",
            "WINDIR",
            "PATH",
            "PATHEXT",
            "USERPROFILE",
            "HOME",
            "HOMEDRIVE",
            "HOMEPATH",
            "LOCALAPPDATA",
            "APPDATA",
            "TEMP",
            "TMP",
            "LANG",
            "LC_ALL",
        )
        if key in os.environ
    }
    repo_root = str(Path(__file__).resolve().parent.parent)
    existing_pp = os.environ.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{repo_root}{os.pathsep}{existing_pp}" if existing_pp else repo_root
    env["HERMES_CREATIVE_LAUNCH_NONCE"] = nonce
    env["PYTHONUNBUFFERED"] = "1"

    if registry is None:
        registry = process_registry

    proc = subprocess.Popen(
        argv,
        cwd=str(valid_root),
        env=env,
        shell=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=windows_hide_flags(),
    )

    try:
        session = registry.adopt_local(
            proc,
            command=command,
            cwd=str(valid_root),
            task_id=f"creative_{engine}_{assigned_port}",
            owner_task_id=f"creative_{engine}",
            session_key=f"session_creative_{engine}",
            notify_on_complete=False,
        )
        session.persist_on_release = True
    except BaseException:
        proc.kill()
        proc.wait(timeout=5)
        if proc.stdout:
            proc.stdout.close()
        raise

    process_id = session.id
    instance = CreativeWebAppInstance(
        engine=engine,
        process_id=process_id,
        port=assigned_port,
        url=managed_loopback_url(assigned_port),
        nonce=nonce,
        root=valid_root,
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    # Poll readiness
    start_time = time.monotonic()
    ready = False
    while time.monotonic() - start_time < timeout:
        poll_res = registry.poll(process_id)
        if poll_res.get("status") in {"exited", "error"}:
            exit_code = poll_res.get("exit_code")
            output = poll_res.get("output", "")
            raise CreativeWebAppError(
                f"Creative web server exited prematurely (code {exit_code}): {output[:500]}"
            )
        if probe_creative_web_app_health(instance, registry=registry, timeout=0.5):
            ready = True
            break
        time.sleep(0.15)

    if not ready:
        registry.kill_process(process_id, source="creative.web_app_readiness_timeout")
        raise CreativeWebAppError(f"Creative web server for {engine} failed readiness within {timeout}s")

    return instance


def get_or_launch_creative_web_app(
    engine: str,
    *,
    dist_root: Optional[Path] = None,
    registry: Optional[ProcessRegistry] = None,
    timeout: float = WEB_APP_READY_TIMEOUT,
) -> tuple[CreativeWebAppInstance, bool]:
    """Get healthy running instance or launch a new one. Returns (instance, reused)."""
    with _INSTANCES_LOCK:
        existing = _ACTIVE_INSTANCES.get(engine)
        if existing is not None:
            if probe_creative_web_app_health(existing, registry=registry):
                return existing, True
            # Process died or became unhealthy; clean it up
            try:
                if registry is None:
                    registry = process_registry
                registry.kill_process(existing.process_id, source="creative.web_app_stale_cleanup")
            except (KeyError, OSError, RuntimeError) as exc:
                logger.debug("Failed to kill stale process %s: %s", existing.process_id, exc)
            _ACTIVE_INSTANCES.pop(engine, None)

        instance = start_creative_web_app_server(
            engine,
            dist_root=dist_root,
            registry=registry,
            timeout=timeout,
        )
        _ACTIVE_INSTANCES[engine] = instance
        return instance, False


def stop_creative_web_app_server(
    engine: str,
    *,
    registry: Optional[ProcessRegistry] = None,
) -> bool:
    with _INSTANCES_LOCK:
        instance = _ACTIVE_INSTANCES.pop(engine, None)
        if instance is None:
            return False
        if registry is None:
            registry = process_registry
        registry.kill_process(instance.process_id, source="creative.web_app_stop")
        return True


def clear_active_instances() -> None:
    """Testing helper to clear internal tracking."""
    with _INSTANCES_LOCK:
        _ACTIVE_INSTANCES.clear()


def open_and_verify_creative_web_app(
    app: CreativeWebApp,
    dispatch: Callable[[str, dict], Any],
    independent_read: Callable[[], Any] | None = None,
    *,
    registry: Optional[ProcessRegistry] = None,
    dist_root: Optional[Path] = None,
) -> CreativeWebAppLaunchReceipt:
    # 1. Check if dist is available
    root = dist_root or discover_web_app_dist(app.key)
    if root is None:
        return CreativeWebAppLaunchReceipt(
            status="missing_dist",
            engine=app.key,
            reason=f"missing_prebuilt_web_dist:{app.key}",
        )

    # 2. Get or start server instance
    try:
        instance, reused = get_or_launch_creative_web_app(
            app.key,
            dist_root=root,
            registry=registry,
        )
    except Exception as exc:
        logger.exception("Failed to launch creative web server for %s", app.key)
        return CreativeWebAppLaunchReceipt(
            status="failed",
            engine=app.key,
            reason=f"server_launch_failed:{type(exc).__name__}:{exc}",
        )

    from workstation.prefabs.engine import _has_error, _as_data, extract_controller_url

    # 3. If instance is reused, probe active browser state to prevent destructive reload of unsaved work
    if reused:
        try:
            observation = independent_read() if independent_read else dispatch("browser_snapshot", {"full": False})
        except Exception as exc:  # health: allow BLE001 -- snapshot observation boundary caught and mapped to launch receipt
            observation = {"error": f"snapshot_exception:{type(exc).__name__}"}

        if _has_error(observation):
            obs_data = _as_data(observation)
            obs_reason = str(obs_data.get("reason", "") or obs_data.get("error", ""))
            if "USER_CONTROL_ACTIVE" in obs_reason or "user_control_active" in obs_reason:
                return CreativeWebAppLaunchReceipt(
                    status="user_control_active",
                    engine=app.key,
                    url=instance.url,
                    port=instance.port,
                    reason="user_control_active",
                    reused=True,
                    dispatch_attempted=False,
                )
        else:
            observed_url = extract_controller_url(observation, allowed_loopback_port=instance.port)
            if matches_managed_loopback_url(observed_url, instance.port):
                return CreativeWebAppLaunchReceipt(
                    status="verified",
                    engine=app.key,
                    url=instance.url,
                    port=instance.port,
                    observed_url=observed_url,
                    reason=f"creative_{app.key}_already_active_preserved",
                    reused=True,
                    dispatch_attempted=False,
                )

    # 4. Check for human lease / navigate
    try:
        ack = dispatch("browser_navigate", {"url": instance.url})
    except Exception as exc:  # health: allow BLE001 -- tool dispatch boundary caught and mapped to launch receipt
        err_msg = str(exc)
        if "USER_CONTROL_ACTIVE" in err_msg or "user_control_active" in err_msg:
            return CreativeWebAppLaunchReceipt(
                status="user_control_active",
                engine=app.key,
                url=instance.url,
                port=instance.port,
                reason="user_control_active",
                reused=reused,
                dispatch_attempted=True,
            )
        return CreativeWebAppLaunchReceipt(
            status="uncertain",
            engine=app.key,
            url=instance.url,
            port=instance.port,
            reason=f"dispatch_exception:{type(exc).__name__}",
            reused=reused,
            dispatch_attempted=True,
        )

    # Check ack for errors or human lease
    if _has_error(ack):
        ack_data = _as_data(ack)
        reason = str(ack_data.get("reason", "") or ack_data.get("error", ""))
        if "USER_CONTROL_ACTIVE" in reason or "user_control_active" in reason:
            return CreativeWebAppLaunchReceipt(
                status="user_control_active",
                engine=app.key,
                url=instance.url,
                port=instance.port,
                reason="user_control_active",
                reused=reused,
                dispatch_attempted=True,
            )
        return CreativeWebAppLaunchReceipt(
            status="uncertain",
            engine=app.key,
            url=instance.url,
            port=instance.port,
            reason=f"browser_navigate_error:{reason}",
            reused=reused,
            dispatch_attempted=True,
        )

    # 5. Independent readback observation via browser_snapshot
    try:
        observation = independent_read() if independent_read else dispatch("browser_snapshot", {"full": False})
    except Exception as exc:  # health: allow BLE001 -- snapshot observation boundary caught and mapped to launch receipt
        return CreativeWebAppLaunchReceipt(
            status="uncertain",
            engine=app.key,
            url=instance.url,
            port=instance.port,
            reason=f"snapshot_exception:{type(exc).__name__}",
            reused=reused,
            dispatch_attempted=True,
        )

    if _has_error(observation):
        return CreativeWebAppLaunchReceipt(
            status="uncertain",
            engine=app.key,
            url=instance.url,
            port=instance.port,
            reason="browser_snapshot_error",
            reused=reused,
            dispatch_attempted=True,
        )

    # Extract controller-owned URL from snapshot
    observed_url = extract_controller_url(observation, allowed_loopback_port=instance.port)

    # Validate with matches_managed_loopback_url
    if not matches_managed_loopback_url(observed_url, instance.port):
        return CreativeWebAppLaunchReceipt(
            status="uncertain",
            engine=app.key,
            url=instance.url,
            port=instance.port,
            observed_url=observed_url,
            reason=f"observed_url_mismatch:{observed_url}",
            reused=reused,
            dispatch_attempted=True,
        )

    return CreativeWebAppLaunchReceipt(
        status="verified",
        engine=app.key,
        url=instance.url,
        port=instance.port,
        observed_url=observed_url,
        reason=f"creative_{app.key}_open_verified",
        reused=reused,
        dispatch_attempted=True,
    )

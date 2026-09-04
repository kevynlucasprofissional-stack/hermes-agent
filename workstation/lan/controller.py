"""Hermes Workstation LAN & Tailscale controller.

Provides network discovery, authentication preflight, fail-closed non-loopback
binding, and authenticated access URL/QR generation reusing the official
Hermes Dashboard backend.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from typing import Any, Mapping

from workstation.config import WorkstationConfig, load_workstation_config


@dataclass(frozen=True, slots=True)
class TailscaleInfo:
    available: bool
    ip: str | None = None
    hostname: str | None = None
    online: bool = False


@dataclass(frozen=True, slots=True)
class LanAccessInfo:
    lan_ip: str
    lan_url: str
    bind_host: str
    port: int
    auth_configured: bool
    tailscale: TailscaleInfo
    tailscale_url: str | None
    qr_payload: str


def auth_preflight_check(
    env: Mapping[str, str] | None = None,
    config: Mapping[str, Any] | None = None,
) -> bool:
    """Check whether a valid authentication secret is configured.
    
    Checks environment variables (HERMES_GATEWAY_TOKEN, API_SERVER_KEY,
    HERMES_AUTH_TOKEN) and configuration mappings.
    """
    env_source = os.environ if env is None else env
    for key in ("HERMES_GATEWAY_TOKEN", "API_SERVER_KEY", "HERMES_AUTH_TOKEN"):
        val = env_source.get(key, "").strip()
        if val:
            return True

    if config is not None:
        gateway = config.get("gateway", {})
        if isinstance(gateway, dict):
            if str(gateway.get("api_key", "")).strip():
                return True
            auth = gateway.get("auth", {})
            if isinstance(auth, dict) and str(auth.get("token", "")).strip():
                return True
        dashboard = config.get("dashboard", {})
        if isinstance(dashboard, dict) and str(dashboard.get("token", "")).strip():
            return True

    return False


def get_configured_token(
    env: Mapping[str, str] | None = None,
    config: Mapping[str, Any] | None = None,
) -> str | None:
    """Retrieve the primary configured token if present."""
    env_source = os.environ if env is None else env
    for key in ("HERMES_GATEWAY_TOKEN", "API_SERVER_KEY", "HERMES_AUTH_TOKEN"):
        val = env_source.get(key, "").strip()
        if val:
            return val

    if config is not None:
        gateway = config.get("gateway", {})
        if isinstance(gateway, dict):
            token = str(gateway.get("api_key", "")).strip()
            if token:
                return token
            auth = gateway.get("auth", {})
            if isinstance(auth, dict):
                token = str(auth.get("token", "")).strip()
                if token:
                    return token
        dashboard = config.get("dashboard", {})
        if isinstance(dashboard, dict):
            token = str(dashboard.get("token", "")).strip()
            if token:
                return token

    return None


def get_lan_bind_host(cfg: WorkstationConfig, has_auth: bool | None = None) -> str:
    """Determine the bind host (0.0.0.0 vs 127.0.0.1) under fail-closed security invariants."""
    if not cfg.lan_enabled:
        return "127.0.0.1"

    if has_auth is None:
        has_auth = auth_preflight_check()

    if not has_auth:
        raise PermissionError(
            "Hermes Workstation refuses LAN mode: authentication token is not configured. "
            "Set HERMES_GATEWAY_TOKEN or configure gateway.auth.token before binding to non-loopback."
        )

    return "0.0.0.0"


def detect_lan_ipv4() -> str:
    """Detect local machine's primary non-loopback IPv4 address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually transmit packets; connects routing table
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def detect_tailscale() -> TailscaleInfo:
    """Detect if Tailscale is installed and connected to a Tailnet."""
    tailscale_bin = shutil.which("tailscale")
    if not tailscale_bin:
        return TailscaleInfo(available=False)

    try:
        result = subprocess.run(
            [tailscale_bin, "status", "--json"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode != 0:
            # Fallback to ip -4
            ip_res = subprocess.run(
                [tailscale_bin, "ip", "-4"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if ip_res.returncode == 0:
                ip = ip_res.stdout.strip().splitlines()[0]
                return TailscaleInfo(available=True, ip=ip, online=True)
            return TailscaleInfo(available=True, online=False)

        data = json.loads(result.stdout)
        self_node = data.get("Self", {})
        tailscale_ips = self_node.get("TailscaleIPs", [])
        ipv4 = next((ip for ip in tailscale_ips if "." in ip), None)
        hostname = self_node.get("HostName") or data.get("CurrentTailnet", {}).get("Name")
        online = bool(self_node.get("Online", True))

        return TailscaleInfo(
            available=True,
            ip=ipv4,
            hostname=hostname,
            online=online,
        )
    except Exception:
        return TailscaleInfo(available=False)


def render_ascii_qr(payload: str) -> str:
    """Render a clean text block representing the QR payload for terminal/desktop logs."""
    border = "=" * (len(payload) + 12)
    return (
        f"{border}\n"
        f"  HERMES WORKSTATION AUTHENTICATED ACCESS\n"
        f"  Scan / Open: {payload}\n"
        f"{border}"
    )


def get_workstation_access_info(
    port: int = 9119,
    env: Mapping[str, str] | None = None,
    config: Mapping[str, Any] | None = None,
    cfg: WorkstationConfig | None = None,
) -> LanAccessInfo:
    """Aggregate LAN, Tailscale, auth, and access URL info."""
    if cfg is None:
        cfg = load_workstation_config()

    has_auth = auth_preflight_check(env=env, config=config)
    token = get_configured_token(env=env, config=config)
    bind_host = get_lan_bind_host(cfg, has_auth=has_auth)

    lan_ip = detect_lan_ipv4()
    tailscale = detect_tailscale()

    token_suffix = f"?token={token}" if token else ""
    lan_url = f"http://{lan_ip}:{port}/{token_suffix}"
    tailscale_url = f"http://{tailscale.ip}:{port}/{token_suffix}" if tailscale.ip else None

    qr_payload = tailscale_url if (tailscale.online and tailscale_url) else lan_url

    return LanAccessInfo(
        lan_ip=lan_ip,
        lan_url=lan_url,
        bind_host=bind_host,
        port=port,
        auth_configured=has_auth,
        tailscale=tailscale,
        tailscale_url=tailscale_url,
        qr_payload=qr_payload,
    )

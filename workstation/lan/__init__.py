"""Workstation LAN & Tailscale control plane integration."""
from .controller import (
    LanAccessInfo,
    TailscaleInfo,
    auth_preflight_check,
    detect_lan_ipv4,
    detect_tailscale,
    get_lan_bind_host,
    get_workstation_access_info,
)

__all__ = [
    "LanAccessInfo",
    "TailscaleInfo",
    "auth_preflight_check",
    "detect_lan_ipv4",
    "detect_tailscale",
    "get_lan_bind_host",
    "get_workstation_access_info",
]

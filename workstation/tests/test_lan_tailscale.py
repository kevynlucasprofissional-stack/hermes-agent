import json
import pytest
from unittest.mock import patch, MagicMock

from workstation.config import WorkstationConfig
from workstation.lan.controller import (
    LanAccessInfo,
    TailscaleInfo,
    auth_preflight_check,
    detect_lan_ipv4,
    detect_tailscale,
    get_lan_bind_host,
    get_workstation_access_info,
    render_ascii_qr,
)


def test_auth_preflight_check():
    assert auth_preflight_check(env={}, config={}) is False
    assert auth_preflight_check(env={"HERMES_GATEWAY_TOKEN": "secret-token"}) is True
    assert auth_preflight_check(env={"API_SERVER_KEY": "api-secret"}) is True
    assert auth_preflight_check(env={}, config={"gateway": {"api_key": "gw-key"}}) is True
    assert auth_preflight_check(env={}, config={"gateway": {"auth": {"token": "gw-token"}}}) is True
    assert auth_preflight_check(env={}, config={"dashboard": {"token": "dash-token"}}) is True


def test_get_lan_bind_host_fail_closed():
    # LAN disabled -> 127.0.0.1
    cfg_disabled = WorkstationConfig({"lan": {"enabled": False, "require_auth": True}})
    assert get_lan_bind_host(cfg_disabled, has_auth=False) == "127.0.0.1"

    # LAN enabled but no auth -> PermissionError
    cfg_enabled = WorkstationConfig({"lan": {"enabled": True, "require_auth": True}})
    with pytest.raises(PermissionError, match="refuses LAN mode"):
        get_lan_bind_host(cfg_enabled, has_auth=False)

    # LAN enabled with auth -> 0.0.0.0
    assert get_lan_bind_host(cfg_enabled, has_auth=True) == "0.0.0.0"


def test_detect_lan_ipv4():
    ip = detect_lan_ipv4()
    assert isinstance(ip, str)
    assert len(ip.split(".")) == 4


def test_detect_tailscale_when_not_installed():
    with patch("shutil.which", return_value=None):
        info = detect_tailscale()
        assert info.available is False
        assert info.online is False
        assert info.ip is None


def test_detect_tailscale_when_installed_and_online():
    mock_status = {
        "Self": {
            "TailscaleIPs": ["100.80.90.100", "fd7a:115c:a1e0::1"],
            "HostName": "my-workstation",
            "Online": True
        },
        "CurrentTailnet": {"Name": "example.ts.net"}
    }
    with patch("shutil.which", return_value="/usr/bin/tailscale"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(mock_status))
            info = detect_tailscale()
            assert info.available is True
            assert info.online is True
            assert info.ip == "100.80.90.100"
            assert info.hostname == "my-workstation"


def test_get_workstation_access_info():
    cfg = WorkstationConfig({"lan": {"enabled": True, "require_auth": True}})
    env = {"HERMES_GATEWAY_TOKEN": "my-token-123"}
    info = get_workstation_access_info(port=9119, env=env, cfg=cfg)

    assert info.auth_configured is True
    assert info.bind_host == "0.0.0.0"
    assert "token=my-token-123" in info.lan_url
    assert str(info.port) in info.lan_url

    qr = render_ascii_qr(info.qr_payload)
    assert info.qr_payload in qr

"""Read-only recovery must refresh discovery, never retry a mutating POST."""
from __future__ import annotations

from urllib.error import URLError
from unittest.mock import patch

import pytest

from tools import browser_workstation as browser


class Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"success":true,"runtime":"electron-chromium"}'


def test_readonly_get_rediscovers_changed_authenticated_controller():
    old = {"url": "http://127.0.0.1:7001", "token": "old", "version": 1}
    new = {"url": "http://127.0.0.1:7002", "token": "new", "version": 1}
    requests = []

    def transport(request, timeout):
        requests.append((request.full_url, request.get_method()))
        if len(requests) == 1:
            raise URLError(ConnectionRefusedError("stale loopback"))
        return Response()

    with patch.object(browser, "_read_control", side_effect=[old, new, new]), \
         patch.object(browser, "urlopen", side_effect=transport):
        result = browser._request_json("GET", "/health", timeout=1)

    assert result["success"] is True
    assert requests == [
        ("http://127.0.0.1:7001/health", "GET"),
        ("http://127.0.0.1:7002/health", "GET"),
    ]


def test_mutation_post_is_not_retried_after_transport_failure():
    old = {"url": "http://127.0.0.1:7001", "token": "old", "version": 1}
    transport_calls = []

    def transport(request, timeout):
        transport_calls.append(request.get_method())
        raise URLError(ConnectionRefusedError("uncertain dispatch"))

    with patch.object(browser, "_read_control", return_value=old), \
         patch.object(browser, "urlopen", side_effect=transport):
        with pytest.raises(browser.WorkstationBrowserUnavailable):
            browser._request_json(
                "POST", "/control", {"action": "browser_click"}, timeout=1,
                action="browser_click",
            )
    assert transport_calls == ["POST"]


def test_agent_tool_catalog_does_not_advertise_human_only_reconciliation():
    assert 'browser_admissions_reconcile' not in browser._WORKSTATION_SCHEMA_TOOLS
    assert 'browser_admissions_inspect' in browser._WORKSTATION_SCHEMA_TOOLS

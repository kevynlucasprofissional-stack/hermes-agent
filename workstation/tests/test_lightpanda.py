from workstation.lightpanda import LightpandaAdapter, LightpandaConfig
from workstation.routing import BrowserBackend, BrowserRoutingContext, BrowserRoutingPolicy


def test_lightpanda_fail_closed_boundary():
    adapter = LightpandaAdapter(LightpandaConfig(enabled=True))

    # Bound to internal must NEVER route to lightpanda
    assert adapter.can_handle(BrowserRoutingContext(bound_to_internal=True, public_read_only=True, headless_ok=True)) is False

    # Authenticated task must NEVER route to lightpanda
    assert adapter.can_handle(BrowserRoutingContext(requires_auth=True, public_read_only=True, headless_ok=True)) is False

    # Task requiring visible state must NEVER route to lightpanda
    assert adapter.can_handle(BrowserRoutingContext(requires_visible_state=True, public_read_only=True, headless_ok=True)) is False

    # Only public read-only and headless-ok task qualifies
    assert adapter.can_handle(BrowserRoutingContext(public_read_only=True, headless_ok=True)) is True


def test_routing_policy_chooses_lightpanda_for_stateless():
    policy = BrowserRoutingPolicy(enabled=True)
    backend = policy.choose(BrowserRoutingContext(public_read_only=True, headless_ok=True))
    assert backend == BrowserBackend.LIGHTPANDA

    # But if bound, always internal
    bound_backend = policy.choose(BrowserRoutingContext(bound_to_internal=True, public_read_only=True, headless_ok=True))
    assert bound_backend == BrowserBackend.INTERNAL


def test_lightpanda_handles_decompression(monkeypatch):
    import gzip
    from unittest.mock import MagicMock
    import urllib.request

    adapter = LightpandaAdapter(LightpandaConfig(enabled=True))
    raw_html = b"<html><head><title>Gzip Page</title></head><body><h1>Compressed Content Here</h1></body></html>"
    compressed = gzip.compress(raw_html)

    mock_headers = MagicMock()
    mock_headers.get.side_effect = lambda k, default="": {"Content-Encoding": "gzip", "Content-Type": "text/html; charset=utf-8"}.get(k, default)
    mock_headers.get_content_charset.return_value = "utf-8"

    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    mock_resp.geturl.return_value = "https://example.com/public-docs"
    mock_resp.headers = mock_headers
    mock_resp.read.return_value = compressed
    mock_resp.__enter__.return_value = mock_resp

    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: mock_resp)

    result = adapter.execute_read("https://example.com/public-docs")
    assert result.success is True
    assert result.title == "Gzip Page"
    assert "Compressed Content Here" in result.text


def test_lightpanda_aborts_on_auth_redirect(monkeypatch):
    from unittest.mock import MagicMock
    import urllib.request

    adapter = LightpandaAdapter(LightpandaConfig(enabled=True))

    mock_headers = MagicMock()
    mock_headers.get.return_value = ""
    mock_headers.get_content_charset.return_value = "utf-8"

    mock_resp = MagicMock()
    mock_resp.getcode.return_value = 200
    # Redirected to Google accounts auth wall
    mock_resp.geturl.return_value = "https://accounts.google.com/signin/v2/identifier"
    mock_resp.headers = mock_headers
    mock_resp.read.return_value = b"<html><body>Sign In</body></html>"
    mock_resp.__enter__.return_value = mock_resp

    monkeypatch.setattr(urllib.request, "urlopen", lambda *args, **kwargs: mock_resp)

    result = adapter.execute_read("https://example.com/private-dashboard")
    assert result.success is False
    assert "AuthRedirectEncountered" in (result.error or "")


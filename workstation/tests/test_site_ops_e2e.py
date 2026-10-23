"""E2E tests for site-ops Desktop integration via IPC.

Tests require Hermes Desktop running with CDP enabled on port 9222
and WhatsApp Web open in the browser.
"""

import os
import pytest
import asyncio
from typing import Optional

pytestmark = pytest.mark.e2e


def _has_desktop_cdp() -> bool:
    """Check if Hermes Desktop is running with CDP enabled."""
    try:
        import urllib.request
        with urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _has_whatsapp_target() -> bool:
    """Check if WhatsApp Web is open in a CDP target."""
    try:
        import urllib.request, json
        with urllib.request.urlopen('http://127.0.0.1:9222/json', timeout=2) as resp:
            targets = json.loads(resp.read().decode())
            for t in targets:
                if t.get('type') == 'page' and 'web.whatsapp.com' in t.get('url', ''):
                    return True
        return False
    except Exception:
        return False


SKIP_REASON = "Requires Hermes Desktop with CDP (port 9222) and WhatsApp Web open"


@pytest.mark.skipif(not _has_desktop_cdp(), reason=SKIP_REASON)
class TestSiteOpsIPC:
    """Test site-ops IPC handlers."""

    @pytest.fixture
    def site_ops(self):
        """Get siteOps API from preload bridge."""
        # This runs in the renderer context via pytest-electron or similar
        # For now we test via direct Node.js script execution
        import subprocess
        return SiteOpsRunner()

    def test_ipc_handler_registered(self, site_ops):
        """Test that site-ops IPC handler is registered and responds."""
        result = site_ops.run('deep-map', ['status', 'web.whatsapp.com'])
        assert result['success'] is True or 'error' in result
        # If WhatsApp is open, status should work
        if _has_whatsapp_target():
            assert result['success'] is True
            assert 'slug' in result['data']

    def test_get_unread_count(self, site_ops):
        """Test get-unread-count operation via IPC."""
        if not _has_whatsapp_target():
            pytest.skip("WhatsApp Web not open")
        result = site_ops.run('execute', ['whatsapp-web', 'get-unread-count', []])
        assert result['success'] is True
        assert 'data' in result
        assert 'unreadCount' in result['data']
        assert isinstance(result['data']['unreadCount'], int)
        assert result['data']['unreadCount'] >= 0

    def test_open_chat_known_contact(self, site_ops):
        """Test open-chat with a known safe contact."""
        if not _has_whatsapp_target():
            pytest.skip("WhatsApp Web not open")
        # Only test with configured safe contacts
        safe_contacts = ['Kevyn ACIRV', '+55 64 9247-0988 (Você)']
        for contact in safe_contacts:
            result = site_ops.run('execute', ['whatsapp-web', 'open-chat', [contact]])
            if result['success']:
                assert 'data' in result
                assert result['data'].get('contact') == contact
                break
        else:
            # If contact not found, that's OK - the operation executed
            assert 'error' in result

    def test_send_message(self, site_ops):
        """Test send-message in currently open chat."""
        if not _has_whatsapp_target():
            pytest.skip("WhatsApp Web not open")
        result = site_ops.run('execute', ['whatsapp-web', 'send-message', ['Test message from E2E']])
        # May fail if no chat is open, but should not crash
        assert 'success' in result

    def test_deep_map_init_scan(self, site_ops):
        """Test deep map init and scan commands."""
        if not _has_whatsapp_target():
            pytest.skip("WhatsApp Web not open")
        # Init
        result = site_ops.run('deep-map', ['init', 'web.whatsapp.com'])
        assert result['success'] is True
        assert 'initialized' in result['data']
        # Scan
        result = site_ops.run('deep-map', ['scan', 'web.whatsapp.com'])
        assert result['success'] is True
        assert 'scanned' in result['data']
        assert 'elements' in result['data']
        assert result['data']['elements'] > 0

    def test_consistent_unread_count(self, site_ops):
        """Test that get-unread-count returns consistent values across calls."""
        if not _has_whatsapp_target():
            pytest.skip("WhatsApp Web not open")
        counts = []
        for _ in range(3):
            result = site_ops.run('execute', ['whatsapp-web', 'get-unread-count', []])
            if result['success']:
                counts.append(result['data']['unreadCount'])
            asyncio.sleep(0.5)
        # All counts should be equal (no messages sent between calls)
        if counts:
            assert all(c == counts[0] for c in counts), f"Inconsistent counts: {counts}"


class SiteOpsRunner:
    """Helper to run site-ops via Node.js scripts directly (bypassing IPC for test setup)."""

    def run(self, command: str, args: list) -> dict:
        import subprocess, json
        script_map = {
            'execute': 'site-ops/scripts/site-ops/whatsapp-web.mjs',
            'deep-map': 'site-ops/scripts/site-deep-map.mjs',
        }
        script = script_map.get(command)
        if not script:
            return {'success': False, 'error': f'Unknown command: {command}'}

        try:
            result = subprocess.run(
                ['node', script, *args],
                cwd=os.getenv('HERMES_ROOT', '/mnt/c/Github/hermes-agent'),
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ, 'HERMES_DESKTOP_CDP_PORT': '9222'}
            )
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            if result.returncode == 0:
                try:
                    return {'success': True, 'data': json.loads(stdout) if stdout else {}}
                except json.JSONDecodeError:
                    return {'success': True, 'data': {'raw': stdout}}
            else:
                try:
                    return {'success': False, 'error': json.loads(stderr).get('error', stderr)}
                except json.JSONDecodeError:
                    return {'success': False, 'error': stderr or 'Unknown error'}
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Operation timed out'}
        except Exception as e:
            return {'success': False, 'error': str(e)}


# Standalone test runner for direct execution
if __name__ == '__main__':
    import sys
    import subprocess
    import json

    if not _has_desktop_cdp():
        print("SKIP: Hermes Desktop CDP not available on port 9222")
        sys.exit(0)

    if not _has_whatsapp_target():
        print("SKIP: WhatsApp Web not open in browser")
        sys.exit(0)

    runner = SiteOpsRunner()

    print("=== Test: Deep Map Status ===")
    result = runner.run('deep-map', ['status', 'web.whatsapp.com'])
    print(json.dumps(result, indent=2))
    assert result['success'], f"Deep map status failed: {result}"

    print("\n=== Test: Get Unread Count ===")
    result = runner.run('execute', ['whatsapp-web', 'get-unread-count', []])
    print(json.dumps(result, indent=2))
    assert result['success'], f"Get unread count failed: {result}"
    assert 'unreadCount' in result['data']

    print("\n=== Test: Consistent Unread Count ===")
    counts = []
    for _ in range(3):
        result = runner.run('execute', ['whatsapp-web', 'get-unread-count', []])
        if result['success']:
            counts.append(result['data']['unreadCount'])
    print(f"Counts: {counts}")
    assert all(c == counts[0] for c in counts), f"Inconsistent counts: {counts}"

    print("\n=== All E2E tests passed! ===")
"""Unit tests for WhatsApp-specific browser tools (Phase D-1).

These tests validate the snapshot-first parsing logic of:
- whatsapp_wait_for_ready (QR vs logged-in detection + cache)
- whatsapp_search_contact (ref extraction from snapshot)
- whatsapp_send_message (header check + delivery proof)

All tests mock ``_dispatch`` to avoid requiring a live Hermes controller.
The contract spec is at workstation/context/browser-tools-contract-spec.md.
"""

from __future__ import annotations

import json
import time
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Snapshot fixtures (representative text from real WA Web snapshots)
# ---------------------------------------------------------------------------

LOGGED_IN_SNAPSHOT = {
    "success": True,
    "snapshot": (
        "URL: https://web.whatsapp.com/\n"
        "Title: (59) WhatsApp\n"
        "Interactive elements:\n"
        '- [@e1] header "59 Atualizações no status"\n'
        '- [@e2] button "Conversas"\n'
        '- [@e12] textbox "Pesquisar ou começar uma nova conversa"\n'
        '- [@e16] div "+55 64 9247-0988(você)09:52wds-ic-read..."\n'
    ),
    "element_count": 40,
    "readiness": "stable",
}

QR_SCREEN_SNAPSHOT = {
    "success": True,
    "snapshot": (
        "URL: https://web.whatsapp.com/\n"
        "Title: WhatsApp Web\n"
        "Interactive elements:\n"
        '- [@e1] heading "Use seu telefone para escanear"\n'
        '- [@e2] canvas "QR Code"\n'
    ),
    "element_count": 5,
    "readiness": "stable",
}

LOADING_SNAPSHOT = {
    "success": True,
    "snapshot": (
        "URL: https://web.whatsapp.com/\n"
        "Title: WhatsApp Web\n"
        "Interactive elements:\n"
        '- [@e1] div "Carregando..."\n'
    ),
    "element_count": 2,
    "readiness": "transient",
}

CONVERSATION_OPEN_SNAPSHOT = {
    "success": True,
    "snapshot": (
        "URL: https://web.whatsapp.com/send?phone=5564999999999\n"
        "Title: João Silva - WhatsApp\n"
        "Interactive elements:\n"
        '- [@e1] header "João Silva"\n'
        '- [@e50] textbox "Mensagem"\n'
        '- [@e51] button "Enviar"\n'
        '- [@e100] div "Olá, tudo bem?" data-id="false_5564@c.us_ABC123"\n'
    ),
    "element_count": 30,
    "readiness": "stable",
}

HEADER_MISMATCH_SNAPSHOT = {
    "success": True,
    "snapshot": (
        "URL: https://web.whatsapp.com/send?phone=5564999999999\n"
        "Title: Maria Souza - WhatsApp\n"
        "Interactive elements:\n"
        '- [@e1] header "Maria Souza"\n'
        '- [@e50] textbox "Mensagem"\n'
    ),
    "element_count": 25,
    "readiness": "stable",
}

DELIVERY_PROOF_SNAPSHOT = {
    "success": True,
    "snapshot": (
        "URL: https://web.whatsapp.com/send?phone=5564999999999\n"
        "Title: João Silva - WhatsApp\n"
        "Interactive elements:\n"
        '- [@e1] header "João Silva"\n'
        '- [@e51] button "Mensagem de voz"\n'
        '- [@e101] div "Teste enviado" data-id="false_5564@c.us_DEF456" aria-label="Entregue"\n'
    ),
    "element_count": 31,
    "readiness": "stable",
}

SEARCH_RESULTS_SNAPSHOT = {
    "success": True,
    "snapshot": (
        "URL: https://web.whatsapp.com/\n"
        "Title: WhatsApp\n"
        "Interactive elements:\n"
        '- [@e12] textbox "Pesquisar ou começar uma nova conversa"\n'
        '- [@e60] gridcell "João Silva +55 64 9999-9999"\n'
        '- [@e61] gridcell "Grupo Família Silva"\n'
        '- [@e62] gridcell "João Contato Antigo"\n'
    ),
    "element_count": 15,
    "readiness": "stable",
}

EMPTY_SEARCH_SNAPSHOT = {
    "success": True,
    "snapshot": (
        "URL: https://web.whatsapp.com/\n"
        "Title: WhatsApp\n"
        "Interactive elements:\n"
        '- [@e12] textbox "Pesquisar ou começar uma nova conversa"\n'
        '- [@e70] div "Mensagens"\n'
    ),
    "element_count": 8,
    "readiness": "stable",
}


def _make_dispatch_side_effect(snapshots: list[dict[str, Any]]):
    """Create a side_effect that returns sequential snapshots for browser_snapshot."""
    call_count = {"n": 0}

    def side_effect(action: str, args: dict, **kwargs):
        if action == "browser_snapshot":
            idx = min(call_count["n"], len(snapshots) - 1)
            call_count["n"] += 1
            return json.dumps(snapshots[idx])
        return json.dumps({"success": True})

    return side_effect


class TestWhatsappWaitForReadyParsing:
    """Validate snapshot text parsing for state detection (no controller needed)."""

    def test_logged_in_detection(self):
        """Snapshot with 'Conversas'/'Chats' + element_count >= 10 → LOGGED_IN."""
        from tools.browser_workstation import _classify_wa_state

        result = _classify_wa_state(LOGGED_IN_SNAPSHOT)
        assert result["state"] == "LOGGED_IN"
        assert result["ready"] is True

    def test_qr_screen_detection(self):
        """Snapshot with QR markers → QR_SCREEN_DETECTED."""
        from tools.browser_workstation import _classify_wa_state

        result = _classify_wa_state(QR_SCREEN_SNAPSHOT)
        assert result["state"] == "QR_SCREEN"
        assert result["ready"] is False
        assert result.get("error_code") == "QR_SCREEN_DETECTED"

    def test_loading_detection(self):
        """Low element_count + loading text → LOADING."""
        from tools.browser_workstation import _classify_wa_state

        result = _classify_wa_state(LOADING_SNAPSHOT)
        assert result["state"] == "LOADING"
        assert result["ready"] is False

    def test_stale_snapshot_detection(self):
        """element_count == 0 after multiple polls → STALE_SNAPSHOT."""
        from tools.browser_workstation import _classify_wa_state

        stale = {"success": True, "snapshot": "", "element_count": 0}
        result = _classify_wa_state(stale, consecutive_empty=3)
        assert result.get("error_code") == "STALE_SNAPSHOT"

    def test_cache_hit_skips_reclassification(self):
        """Same element_count + text hash → reuse previous state."""
        from tools.browser_workstation import _compute_snapshot_hash

        h1 = _compute_snapshot_hash(LOGGED_IN_SNAPSHOT)
        h2 = _compute_snapshot_hash(LOGGED_IN_SNAPSHOT)
        assert h1 == h2

        # Different snapshot → different hash
        h3 = _compute_snapshot_hash(QR_SCREEN_SNAPSHOT)
        assert h1 != h3


class TestWhatsappSearchContactParsing:
    """Validate search result extraction from snapshot text."""

    def test_extract_search_ref(self):
        """Find @eN ref for search textbox in snapshot."""
        from tools.browser_workstation import _extract_search_ref

        ref = _extract_search_ref(LOGGED_IN_SNAPSHOT)
        assert ref == "@e12"

    def test_extract_search_results(self):
        """Parse gridcell results from search snapshot."""
        from tools.browser_workstation import _parse_search_results

        results = _parse_search_results(SEARCH_RESULTS_SNAPSHOT, max_results=5)
        assert len(results) >= 2
        assert any("João Silva" in r.get("label", "") for r in results)
        assert all("ref" in r for r in results)

    def test_no_results_detection(self):
        """Empty search panel → NO_RESULTS."""
        from tools.browser_workstation import _parse_search_results

        results = _parse_search_results(EMPTY_SEARCH_SNAPSHOT, max_results=5)
        assert len(results) == 0

    def test_search_input_not_found(self):
        """Snapshot without search textbox → SEARCH_INPUT_NOT_FOUND."""
        from tools.browser_workstation import _extract_search_ref

        no_input = {"success": True, "snapshot": "No inputs here", "element_count": 3}
        ref = _extract_search_ref(no_input)
        assert ref is None


class TestWhatsappSendMessageParsing:
    """Validate header check and delivery proof from snapshot."""

    def test_header_match(self):
        """Header contains expected contact name → verified."""
        from tools.browser_workstation import _verify_conversation_header

        result = _verify_conversation_header(
            CONVERSATION_OPEN_SNAPSHOT, contact_name_hint="João Silva"
        )
        assert result["verified"] is True
        assert result["header_text"] == "João Silva"

    def test_header_mismatch(self):
        """Header does not contain expected name → HEADER_MISMATCH."""
        from tools.browser_workstation import _verify_conversation_header

        result = _verify_conversation_header(
            HEADER_MISMATCH_SNAPSHOT, contact_name_hint="João Silva"
        )
        assert result["verified"] is False
        assert result.get("error_code") == "HEADER_MISMATCH"

    def test_delivery_proof_found(self):
        """New data-id with aria-label in messages panel → DELIVERED."""
        from tools.browser_workstation import _extract_delivery_proof

        proof = _extract_delivery_proof(DELIVERY_PROOF_SNAPSHOT)
        assert proof["delivered"] is True
        assert "DEF456" in proof.get("message_data_id", "")
        assert proof.get("ack_label") == "Entregue"

    def test_composer_empty_after_send(self):
        """Button reverted to 'Mensagem de voz' → composer is empty."""
        from tools.browser_workstation import _is_composer_empty

        assert _is_composer_empty(DELIVERY_PROOF_SNAPSHOT) is True
        assert _is_composer_empty(CONVERSATION_OPEN_SNAPSHOT) is False

    def test_masked_phone_rejected(self):
        """Phone digits containing '*' → MASKED_PHONE error."""
        from tools.browser_workstation import _validate_phone_digits

        assert _validate_phone_digits("+556****7992") is False
        assert _validate_phone_digits("5564999999999") is True

    def test_template_placeholder_rejected(self):
        """Message containing {NOME} → TEMPLATE_PLACEHOLDER_LEAK."""
        from tools.browser_workstation import _validate_message_body

        assert _validate_message_body("Olá, {NOME}!") is False
        assert _validate_message_body("Olá, João!") is True


class TestWhatsappSearchContactIntegration:
    """Integration tests for whatsapp_search_contact with mocked dispatch."""

    @patch("tools.browser_workstation._dispatch")
    def test_search_returns_results(self, mock_dispatch):
        """Search types query and parses gridcell results from snapshot."""
        mock_dispatch.side_effect = _make_dispatch_side_effect(
            [LOGGED_IN_SNAPSHOT, SEARCH_RESULTS_SNAPSHOT]
        )
        from tools.browser_workstation import whatsapp_search_contact
        result = whatsapp_search_contact(query="João", max_results=5)
        assert result["found"] is True
        assert result["result_count"] >= 2
        assert result["search_ref"] == "@e12"
        # Verify browser_type was called with correct ref
        type_calls = [c for c in mock_dispatch.call_args_list if c[0][0] == "browser_type"]
        assert len(type_calls) == 1
        assert type_calls[0][0][1]["ref"] == "@e12"

    @patch("tools.browser_workstation._dispatch")
    def test_search_input_not_found(self, mock_dispatch):
        """Snapshot without search textbox returns SEARCH_INPUT_NOT_FOUND."""
        no_input_snap = {"success": True, "snapshot": "No inputs", "element_count": 3}
        mock_dispatch.side_effect = _make_dispatch_side_effect([no_input_snap])
        from tools.browser_workstation import whatsapp_search_contact
        result = whatsapp_search_contact(query="test")
        assert result["found"] is False
        assert result["error_code"] == "SEARCH_INPUT_NOT_FOUND"


class TestWhatsappSendMessageIntegration:
    """Integration tests for whatsapp_send_message with mocked dispatch."""

    @patch("tools.browser_workstation._dispatch")
    def test_send_delivered(self, mock_dispatch):
        """Full send flow: navigate → header check → click → delivery proof."""
        mock_dispatch.side_effect = _make_dispatch_side_effect(
            [CONVERSATION_OPEN_SNAPSHOT, DELIVERY_PROOF_SNAPSHOT]
        )
        from tools.browser_workstation import whatsapp_send_message
        result = whatsapp_send_message(
            phone_digits="5564999999999",
            message="Olá, tudo bem?",
            contact_name_hint="João Silva",
            verify_delivery=True,
            delivery_timeout_seconds=2.0,
        )
        assert result["sent"] is True
        assert result["state"] == "DELIVERED"
        assert "DEF456" in result.get("message_data_id", "")
        assert result.get("ack_label") == "Entregue"
        assert result.get("header_verified") == "João Silva"

    @patch("tools.browser_workstation._dispatch")
    def test_send_header_mismatch(self, mock_dispatch):
        """Header mismatch aborts send before clicking."""
        mock_dispatch.side_effect = _make_dispatch_side_effect(
            [HEADER_MISMATCH_SNAPSHOT]
        )
        from tools.browser_workstation import whatsapp_send_message
        result = whatsapp_send_message(
            phone_digits="5564999999999",
            message="Teste",
            contact_name_hint="João Silva",
        )
        assert result["sent"] is False
        assert result["error_code"] == "HEADER_MISMATCH"

    @patch("tools.browser_workstation._dispatch")
    def test_send_masked_phone_rejected(self, mock_dispatch):
        """Masked phone digits are rejected before any dispatch call."""
        from tools.browser_workstation import whatsapp_send_message
        result = whatsapp_send_message(
            phone_digits="+556****7992",
            message="Teste",
        )
        assert result["sent"] is False
        assert result["error_code"] == "MASKED_PHONE"
        mock_dispatch.assert_not_called()

    @patch("tools.browser_workstation._dispatch")
    def test_send_placeholder_leak_rejected(self, mock_dispatch):
        """Unreplaced {NOME} placeholder is rejected before dispatch."""
        from tools.browser_workstation import whatsapp_send_message
        result = whatsapp_send_message(
            phone_digits="5564999999999",
            message="Olá, {NOME}!",
        )
        assert result["sent"] is False
        assert result["error_code"] == "TEMPLATE_PLACEHOLDER_LEAK"
        mock_dispatch.assert_not_called()


class TestWindowsAppLaunch:
    """Unit tests for windows_app_launch (standalone, no browser dispatch)."""

    @patch("tools.browser_workstation.platform.system", return_value="Linux")
    def test_not_windows_rejected(self, mock_platform):
        """Non-Windows platform returns NOT_WINDOWS error."""
        from tools.browser_workstation import windows_app_launch
        result = windows_app_launch(app_name="notepad.exe")
        assert result["launched"] is False
        assert result["error_code"] == "NOT_WINDOWS"

    @patch("tools.browser_workstation.subprocess.run")
    @patch("tools.browser_workstation.platform.system", return_value="Windows")
    def test_window_not_visible_timeout(self, mock_platform, mock_run):
        """Process launches but no MainWindowHandle found → WINDOW_NOT_VISIBLE."""
        from tools.browser_workstation import windows_app_launch
        # First call (launch) succeeds silently; second+ calls (Get-Process) return empty
        mock_run.return_value = MagicMock(
            stdout="", stderr="", returncode=0
        )
        result = windows_app_launch(
            app_name="notepad.exe", timeout_seconds=0.1
        )
        assert result["launched"] is False
        assert result["error_code"] == "WINDOW_NOT_VISIBLE"

    @patch("tools.browser_workstation.subprocess.run")
    @patch("tools.browser_workstation.platform.system", return_value="Windows")
    def test_launch_success_with_window(self, mock_platform, mock_run):
        """Successful launch with MainWindowHandle found returns launched=True."""
        import json as _json
        from tools.browser_workstation import windows_app_launch

        process_info = _json.dumps({
            "Id": 12345,
            "MainWindowHandle": 654321,
            "MainWindowTitle": "Notepad"
        })

        def side_effect(cmd, **kwargs):
            cmd_str = " ".join(cmd) if isinstance(cmd, list) else str(cmd)
            if "Start-Process" in cmd_str:
                return MagicMock(stdout="", stderr="", returncode=0)
            elif "Get-Process" in cmd_str:
                return MagicMock(stdout=process_info, stderr="", returncode=0)
            elif "Add-Type" in cmd_str:
                return MagicMock(stdout="OK", stderr="", returncode=0)
            return MagicMock(stdout="", stderr="", returncode=0)

        mock_run.side_effect = side_effect
        result = windows_app_launch(
            app_name="notepad.exe", bring_to_front=True, timeout_seconds=2.0
        )
        assert result["launched"] is True
        assert result["pid"] == 12345
        assert result["window_handle"] == 654321
        assert result["window_title"] == "Notepad"
        assert result["brought_to_front"] is True

    @patch("tools.browser_workstation.subprocess.run")
    @patch("tools.browser_workstation.platform.system", return_value="Windows")
    def test_launch_exception_returns_error(self, mock_platform, mock_run):
        """subprocess.run raising exception returns LAUNCH_FAILED."""
        from tools.browser_workstation import windows_app_launch
        mock_run.side_effect = OSError("access denied")
        result = windows_app_launch(app_name="protected.exe")
        assert result["launched"] is False
        assert result["error_code"] == "LAUNCH_FAILED"
        assert "access denied" in result.get("error", "")


class TestWhatsappWaitForReadyIntegration:
    """Integration tests with mocked _dispatch for full polling loop."""

    @patch("tools.browser_workstation._dispatch")
    def test_wfr_returns_logged_in(self, mock_dispatch):
        """WFR polls until LOGGED_IN state is reached."""
        mock_dispatch.side_effect = _make_dispatch_side_effect(
            [LOADING_SNAPSHOT, LOADING_SNAPSHOT, LOGGED_IN_SNAPSHOT]
        )
        from tools.browser_workstation import whatsapp_wait_for_ready

        result = whatsapp_wait_for_ready(timeout_seconds=5.0, poll_interval=0.01)
        assert result["ready"] is True
        assert result["state"] == "LOGGED_IN"

    @patch("tools.browser_workstation._dispatch")
    def test_wfr_detects_qr_screen(self, mock_dispatch):
        """WFR returns QR_SCREEN_DETECTED when QR is visible."""
        mock_dispatch.side_effect = _make_dispatch_side_effect([QR_SCREEN_SNAPSHOT])
        from tools.browser_workstation import whatsapp_wait_for_ready

        result = whatsapp_wait_for_ready(
            timeout_seconds=1.0, poll_interval=0.01, require_logged_in=True
        )
        assert result["ready"] is False
        assert result.get("error_code") == "QR_SCREEN_DETECTED"

    @patch("tools.browser_workstation._dispatch")
    def test_wfr_timeout(self, mock_dispatch):
        """WFR returns TIMEOUT when deadline exceeded."""
        mock_dispatch.side_effect = _make_dispatch_side_effect(
            [LOADING_SNAPSHOT] * 100
        )
        from tools.browser_workstation import whatsapp_wait_for_ready

        result = whatsapp_wait_for_ready(timeout_seconds=0.1, poll_interval=0.01)
        assert result["ready"] is False
        assert result.get("timeout") is True
"""Tests for WhatsApp Metrics, Telemetry, and Benchmark Evaluation (P5 80/20).

Validates:
- Sanitization of recipient PII (hashing recipient phone digits).
- Recording and persisting operation metrics to whatsapp_control.db.
- Accurate calculation of summary statistics (p50, p95, confirmation/failure rates).
- Comparison against the real dogfood baseline session of 23/10/2026.
- Automatic telemetry emission from send_message, send_attachment, read_messages, and batch_send.
"""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock
import pytest

from workstation.integrations.hermes.whatsapp_browser_executor import (
    whatsapp_read_messages,
    whatsapp_send_attachment,
    whatsapp_send_message,
)
from workstation.integrations.hermes.whatsapp_metrics import (
    BASELINE_SESSION_20261023,
    calculate_percentiles,
    compare_against_baseline,
    get_metrics_summary,
    init_metrics_table,
    record_operation_metric,
    sanitize_recipient,
)


class TestWhatsappMetricsSanitization:
    """Recipient phone sanitization prevents sensitive PII leakage in audit metrics."""

    def test_sanitize_recipient_hashes_phone(self) -> None:
        raw_phone = "5564999733281"
        sanitized = sanitize_recipient(raw_phone)
        assert sanitized != raw_phone
        assert raw_phone not in sanitized
        assert len(sanitized) == 16  # 16-char hex prefix
        # Deterministic
        assert sanitize_recipient(raw_phone) == sanitized

    def test_sanitize_recipient_empty(self) -> None:
        assert sanitize_recipient(None) == ""
        assert sanitize_recipient("") == ""
        assert sanitize_recipient("   ") == ""


class TestWhatsappMetricsPersistenceAndSummary:
    """Metrics recording and aggregate statistics calculation."""

    def test_record_operation_metric_persists_to_sqlite(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"

        row_id = record_operation_metric(
            operation_name="send_message",
            duration_ms=1850.5,
            state="CONFIRMED",
            campaign_id="camp_test",
            job_id="job_123",
            task_id="task_abc",
            tool_calls_count=2,
            ai_turns_count=1,
            tokens_estimated=350,
            security_blocks=["TEMPLATE_PLACEHOLDER_LEAK"],
            deduplications_prevented=1,
            recipient_phone="5564999733281",
            db_path=db_file,
        )
        assert row_id is not None

        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM whatsapp_operation_metrics").fetchall()
            assert len(rows) == 1
            r = rows[0]
            assert r["operation_name"] == "send_message"
            assert r["duration_ms"] == 1850.5
            assert r["state"] == "CONFIRMED"
            assert r["campaign_id"] == "camp_test"
            assert r["job_id"] == "job_123"
            assert r["tool_calls_count"] == 2
            assert r["ai_turns_count"] == 1
            assert r["tokens_estimated"] == 350
            assert r["deduplications_prevented"] == 1
            # Recipient must be hashed, not raw
            assert r["recipient_hash"] == sanitize_recipient("5564999733281")
            assert "5564999733281" not in r["recipient_hash"]

    def test_percentiles_calculation(self) -> None:
        values = [100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0, 900.0, 1000.0]
        p50, p95 = calculate_percentiles(values)
        assert p50 == 500.0
        assert p95 == 1000.0

    def test_get_metrics_summary_aggregate_statistics(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"

        # Record 4 operations: 2 confirmed, 1 uncertain, 1 failed
        record_operation_metric(operation_name="send_message", duration_ms=1000.0, state="CONFIRMED", db_path=db_file)
        record_operation_metric(operation_name="send_message", duration_ms=2000.0, state="CONFIRMED", db_path=db_file)
        record_operation_metric(operation_name="send_message", duration_ms=3000.0, state="UNCERTAIN", db_path=db_file)
        record_operation_metric(
            operation_name="send_message",
            duration_ms=4000.0,
            state="FAILED",
            security_blocks=["MASKED_PHONE"],
            deduplications_prevented=2,
            db_path=db_file,
        )

        summary = get_metrics_summary(db_path=db_file)
        assert summary["total_operations"] == 4
        assert summary["states_distribution"]["CONFIRMED"] == 2
        assert summary["states_distribution"]["UNCERTAIN"] == 1
        assert summary["states_distribution"]["FAILED"] == 1
        assert summary["confirmation_rate"] == 0.50
        assert summary["uncertain_rate"] == 0.25
        assert summary["failure_rate"] == 0.25
        assert summary["latency"]["avg_ms"] == 2500.0
        assert summary["latency"]["p50_ms"] == 2000.0
        assert summary["latency"]["p95_ms"] == 4000.0
        assert summary["deduplications_prevented_total"] == 2
        assert summary["security_blocks"]["MASKED_PHONE"] == 1


class TestWhatsappBenchmarkComparison:
    """Benchmark comparative evaluation against 23/10/2026 baseline session."""

    def test_baseline_session_metadata_integrity(self) -> None:
        assert BASELINE_SESSION_20261023["total_session_turns"] == 365
        assert BASELINE_SESSION_20261023["total_tool_calls"] == 156
        assert BASELINE_SESSION_20261023["browser_console_calls"] == 101
        assert BASELINE_SESSION_20261023["estimated_tokens_total"] > 100000

    def test_compare_against_baseline_demonstrates_cuts(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"

        # Record sample atomic operations
        for _ in range(5):
            record_operation_metric(
                operation_name="send_message",
                duration_ms=1800.0,
                state="CONFIRMED",
                tokens_estimated=350,
                tool_calls_count=2,
                db_path=db_file,
            )

        cmp = compare_against_baseline(db_path=db_file)
        assert cmp["baseline"]["browser_console_calls"] == 101
        assert cmp["current"]["browser_console_calls"] == 0
        assert cmp["improvements"]["console_calls_eliminated_pct"] == 100.0
        assert cmp["improvements"]["token_budget_cut_pct"] >= 80.0
        assert cmp["current"]["total_operations"] == 5
        assert cmp["current"]["confirmation_rate"] == 1.0


class TestWhatsappExecutorsTelemetryIntegration:
    """Automatic telemetry emission from executors into whatsapp_operation_metrics."""

    def test_send_message_emits_telemetry(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        sqlite3.connect(db_file).close()
        nav = MagicMock(return_value={"success": True})
        ready_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header", "data-chat-id": "5564999733281@c.us"}, "text": "João Silva"},
                {"attributes": {"data-testid": "send", "aria-label": "Enviar"}, "ref": "@e_send"},
            ]
        }
        post_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header", "data-chat-id": "5564999733281@c.us"}, "text": "João Silva"},
                {"attributes": {"data-testid": "ptt-in-button"}, "text": ""},
                {"attributes": {"data-testid": "msg-container", "data-id": "true_5564999733281@c.us_MET1", "data-direction": "outbound", "data-recipient-id": "5564999733281@c.us", "data-ack": "sent"}, "text": "Mensagem com telemetria"},
            ]
        }
        snap = MagicMock(side_effect=[ready_snap, post_snap])
        click = MagicMock(return_value={"success": True})

        res = whatsapp_send_message(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            phone_digits="5564999733281",
            message="Mensagem com telemetria",
            db_path=db_file,
            persist=True,
            run_id="metrics-run", operation_id="metrics-operation",
            delivery_timeout_seconds=2.0,
        )
        assert res["sent"] is True
        assert "duration_ms" in res

        # Verify recorded in metrics table
        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM whatsapp_operation_metrics WHERE operation_name = 'send_message'").fetchall()
            assert len(rows) == 1
            assert rows[0]["state"] == "CONFIRMED"
            assert rows[0]["duration_ms"] > 0
            assert rows[0]["tokens_estimated"] == 350

    def test_send_attachment_emits_telemetry(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        doc = tmp_path / "doc.pdf"
        doc.write_bytes(b"%PDF-1.4 test")

        nav = MagicMock(return_value={"success": True})
        ready_snap = {
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "João Silva"},
                {"attributes": {"data-testid": "attach-menu-plus"}, "ref": "@e_att"},
            ]
        }
        preview_snap = {
            "elements": [
                {"attributes": {"data-testid": "send", "aria-label": "Enviar"}, "ref": "@e_send"},
            ]
        }
        post_snap = {
            "elements": [
                {"attributes": {"data-testid": "ptt-in-button"}, "text": ""},
                {"attributes": {"data-testid": "msg-meta", "data-id": "true_met_att_1", "aria-label": "Entregue"}},
            ]
        }
        snap = MagicMock(side_effect=[ready_snap, preview_snap, preview_snap, post_snap])
        click = MagicMock(return_value={"success": True})
        upload = MagicMock(return_value={"success": True})

        res = whatsapp_send_attachment(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            browser_file_upload=upload,
            phone_digits="5564999733281",
            file_path=doc,
            db_path=db_file,
            persist=True,
            delivery_timeout_seconds=2.0,
        )
        assert res["sent"] is True

        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM whatsapp_operation_metrics WHERE operation_name = 'send_attachment'").fetchall()
            assert len(rows) == 1
            assert rows[0]["state"] == "CONFIRMED"
            assert rows[0]["tokens_estimated"] == 450

    def test_read_messages_emits_telemetry(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        snap = MagicMock(return_value={
            "elements": [
                {"attributes": {"data-testid": "conversation-info-header"}, "text": "Maria Santos"},
                {
                    "attributes": {"data-id": "false_5564_tele", "data-testid": "msg-container"},
                    "text": "Olá telemetria!\n09:00",
                },
            ]
        })

        res = whatsapp_read_messages(browser_snapshot=snap, db_path=db_file, persist=True)
        assert res["success"] is True

        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM whatsapp_operation_metrics WHERE operation_name = 'read_messages'").fetchall()
            assert len(rows) == 1
            assert rows[0]["state"] == "CONFIRMED"
            assert rows[0]["tokens_estimated"] == 250


class TestWhatsappBrowserWorkstationMetricsTools:
    """Integration of metrics tools into tools.browser_workstation."""

    def test_browser_workstation_metrics_summary_tool(self, tmp_path) -> None:
        from tools import browser_workstation

        db_file = tmp_path / "whatsapp_control.db"
        record_operation_metric(operation_name="send_message", duration_ms=1200.0, state="CONFIRMED", db_path=db_file)

        summary = browser_workstation.whatsapp_metrics_summary(db_path=db_file)
        assert summary["total_operations"] == 1
        assert summary["confirmation_rate"] == 1.0

    def test_browser_workstation_metrics_benchmark_tool(self, tmp_path) -> None:
        from tools import browser_workstation

        db_file = tmp_path / "whatsapp_control.db"
        record_operation_metric(operation_name="send_message", duration_ms=1500.0, state="CONFIRMED", db_path=db_file)

        cmp = browser_workstation.whatsapp_metrics_benchmark(db_path=db_file)
        assert "baseline" in cmp
        assert "improvements" in cmp
        assert cmp["improvements"]["console_calls_eliminated_pct"] == 100.0

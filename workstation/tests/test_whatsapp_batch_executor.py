"""Tests for WhatsApp Batch Executor — persistent execution queue per contract P2 80/20.

Validates:
- Deterministic 1-by-1 processing with persistent checkpoints.
- Skipping masked phones, ambiguous identities, opt-outs, and placeholder leaks.
- Isolated failures do not halt the remaining batch.
- UNCERTAIN operations are never auto-repeated.
- Pause, cancel, and resume without duplicating sent messages.
- Operational limits (max_messages, max_consecutive_failures auto-pause).
"""
from __future__ import annotations

import sqlite3
from unittest.mock import MagicMock

from workstation.integrations.hermes.whatsapp_batch_executor import (
    ITEM_STATUS_CONFIRMED,
    ITEM_STATUS_FAILED,
    ITEM_STATUS_UNCERTAIN,
    JOB_STATUS_CANCELLED,
    JOB_STATUS_COMPLETED,
    JOB_STATUS_PAUSED,
    whatsapp_batch_cancel,
    whatsapp_batch_pause,
    whatsapp_batch_resume,
    whatsapp_batch_send,
    whatsapp_batch_status,
)


def _seed_existing_approval_fixture(db_file, manifest_hash: str, eligible: int = 2) -> str:
    """Simulate a PRE-EXISTING host-authenticated token in a temp fixture DB.

    This does not call the production issuer or grant agents the ability to mint
    approval. It isolates manifest-tamper and synthetic executor verification.
    """
    from workstation.integrations.hermes.whatsapp_batch_executor import init_batch_tables, now_iso
    token = "appr_synthetic_host_fixture"
    with sqlite3.connect(db_file) as conn:
        init_batch_tables(conn)
        conn.execute(
            "INSERT INTO whatsapp_batch_authorizations "
            "(approval_token, manifest_hash, total_eligible, approved_by, approved_at, status) "
            "VALUES (?, ?, ?, ?, ?, 'active')",
            (token, manifest_hash, eligible, "synthetic-host-fixture", now_iso()),
        )
        conn.commit()
    return token


def _native_ready(phone: str, name: str):
    """Synthetic projection with exact destination identity, not a display-name guess."""
    return {"elements": [
        {"attributes": {"data-testid": "conversation-info-header",
                        "data-chat-id": f"{phone}@c.us"}, "text": name},
        {"attributes": {"data-testid": "send", "aria-label": "Enviar"},
         "ref": "@e_send"},
    ]}


def _native_post(phone: str, name: str, body: str):
    """New outbound bubble with independent identity/direction/body/ACK attributes."""
    return {"elements": [
        {"attributes": {"data-testid": "conversation-info-header",
                        "data-chat-id": f"{phone}@c.us"}, "text": name},
        {"attributes": {"data-testid": "ptt-in-button"}, "text": ""},
        {"attributes": {"data-testid": "msg-container",
                        "data-id": f"true_{phone}@c.us_fixture_new",
                        "data-recipient-id": f"{phone}@c.us",
                        "data-direction": "outbound", "data-ack": "sent"},
         "text": body},
    ]}


def _mock_successful_browser(contact_names: list[str] | None = None):
    """Synthetic causal browser, used only for deterministic unit tests."""
    from urllib.parse import parse_qs, urlsplit

    active = {"phone": "", "body": "", "name": "", "count": 0}
    next_contact = [0]

    def _nav_fn(url: str):
        query = parse_qs(urlsplit(url).query)
        active["phone"] = query["phone"][0]
        active["body"] = query["text"][0]
        index = next_contact[0]
        active["name"] = (contact_names[index] if contact_names and index < len(contact_names)
                          else "Contato")
        next_contact[0] += 1
        active["count"] = 0
        return {"success": True}

    nav = MagicMock(side_effect=_nav_fn)

    def snap():
        active["count"] += 1
        if active["count"] == 1:
            return _native_ready(active["phone"], active["name"])
        return _native_post(active["phone"], active["name"], active["body"])

    click = MagicMock(return_value={"success": True})
    return nav, snap, click


class TestWhatsappBatchSendBasics:
    def test_batch_send_happy_path(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        recipients = [
            {"contact_id": 101, "display_name": "João Silva", "phone_digits": "5564999733281", "message": "Olá João"},
            {"contact_id": 102, "display_name": "Maria Santos", "phone_digits": "5564988888888", "message": "Olá Maria"},
        ]
        nav, snap, click = _mock_successful_browser(["João Silva", "Maria Santos"])

        res = whatsapp_batch_send(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            recipients=recipients,
            rate_limit_delay_seconds=0.0,
            require_approval=False,
            db_path=db_file,
        )

        assert res["status"] == JOB_STATUS_COMPLETED
        assert res["total_items"] == 2
        assert res["processed_items"] == 2
        assert res["confirmed_items"] == 2
        assert res["failed_items"] == 0
        assert res["skipped_items"] == 0

        # Verify SQLite state
        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            items = conn.execute("SELECT * FROM whatsapp_batch_items WHERE job_id = ?", (res["job_id"],)).fetchall()
            assert len(items) == 2
            assert all(it["status"] == ITEM_STATUS_CONFIRMED for it in items)
            assert items[0]["phone_digits"] == "5564999733281"
            assert items[1]["phone_digits"] == "5564988888888"

    def test_batch_send_skips_invalid_contacts_and_continues(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        recipients = [
            # Masked phone
            {"contact_id": 1, "display_name": "Contato Mascarado", "phone_digits": "5564****3281", "message": "Olá"},
            # Ambiguous identity
            {"contact_id": 2, "display_name": "[nome]", "phone_digits": "5564999111111", "message": "Olá"},
            # Opted out
            {"contact_id": 3, "display_name": "Saiu do Fluxo", "phone_digits": "5564999222222", "message": "Olá", "status": "opted_out"},
            # Template placeholder leak
            {"contact_id": 4, "display_name": "Vazamento Template", "phone_digits": "5564999333333", "message": "Olá {NOME}!"},
            # Valid contact
            {"contact_id": 5, "display_name": "Carlos Válido", "phone_digits": "5564999444444", "message": "Olá Carlos!"},
        ]
        nav, snap, click = _mock_successful_browser(["Carlos Válido"])

        res = whatsapp_batch_send(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            recipients=recipients,
            rate_limit_delay_seconds=0.0,
            require_approval=False,
            db_path=db_file,
        )

        assert res["status"] == JOB_STATUS_COMPLETED
        assert res["total_items"] == 5
        assert res["processed_items"] == 5
        assert res["skipped_items"] == 4
        assert res["confirmed_items"] == 1

        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            items = conn.execute("SELECT * FROM whatsapp_batch_items WHERE job_id = ? ORDER BY id", (res["job_id"],)).fetchall()
            assert items[0]["error_code"] == "MASKED_PHONE"
            assert items[1]["error_code"] == "AMBIGUOUS_IDENTITY"
            assert items[2]["error_code"] == "OPTED_OUT"
            assert items[3]["error_code"] == "TEMPLATE_PLACEHOLDER_LEAK"
            assert items[4]["status"] == ITEM_STATUS_CONFIRMED

    def test_batch_send_isolated_failure_does_not_halt_batch(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"

        # Item 1: nav failure
        # Item 2: success
        # Item 3: invalid phone popup
        # Item 4: success
        nav = MagicMock(side_effect=[
            RuntimeError("nav dropped"),
            {"success": True},
            {"success": True},
            {"success": True},
        ])

        item2_ready = _native_ready("5564999222222", "Pessoa 2")
        item2_post = _native_post("5564999222222", "Pessoa 2", "Msg 2")

        item3_popup = {"elements": [{"attributes": {"data-testid": "popup-contents"}, "text": "Número não encontrado no WhatsApp"}, {"attributes": {"data-testid": "popup-controls-ok"}, "ref": "@e_ok"}]}

        item4_ready = _native_ready("5564999444444", "Pessoa 4")
        item4_post = _native_post("5564999444444", "Pessoa 4", "Msg 4")

        snap = MagicMock(side_effect=[
            item2_ready, item2_post,
            item3_popup,
            item4_ready, item4_post,
        ])
        click = MagicMock(return_value={"success": True})

        recipients = [
            {"contact_id": 1, "display_name": "Pessoa 1", "phone_digits": "5564999111111", "message": "Msg 1"},
            {"contact_id": 2, "display_name": "Pessoa 2", "phone_digits": "5564999222222", "message": "Msg 2"},
            {"contact_id": 3, "display_name": "Pessoa 3", "phone_digits": "5564999333333", "message": "Msg 3"},
            {"contact_id": 4, "display_name": "Pessoa 4", "phone_digits": "5564999444444", "message": "Msg 4"},
        ]

        res = whatsapp_batch_send(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            recipients=recipients,
            rate_limit_delay_seconds=0.0,
            require_approval=False,
            db_path=db_file,
            delivery_timeout_seconds=0.5,
        )

        assert res["status"] == JOB_STATUS_COMPLETED
        assert res["total_items"] == 4
        assert res["processed_items"] == 4
        assert res["failed_items"] == 2
        assert res["confirmed_items"] == 2


class TestWhatsappBatchUncertainAndResilience:
    def test_uncertain_operations_never_auto_repeated(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"

        # Item 1: Post-send proof times out -> UNCERTAIN
        # Item 2: Success -> CONFIRMED
        current_item = [-1]
        item_snap_count = [0]

        def _nav_fn(url: str):
            current_item[0] += 1
            item_snap_count[0] = 0
            return {"success": True}

        nav = MagicMock(side_effect=_nav_fn)

        ready_snap1 = _native_ready("5564999111111", "Pessoa 1")
        timeout_snap = {"elements": [{"attributes": {"data-testid": "ptt-in-button"}}]}  # No msg-meta!

        ready_snap2 = _native_ready("5564999222222", "Pessoa 2")
        post_snap2 = _native_post("5564999222222", "Pessoa 2", "Msg 2")

        def snap():
            idx = current_item[0]
            cnt = item_snap_count[0]
            item_snap_count[0] += 1
            if idx == 0:
                return ready_snap1 if cnt == 0 else timeout_snap
            else:
                return ready_snap2 if cnt == 0 else post_snap2

        click = MagicMock(return_value={"success": True})

        recipients = [
            {"contact_id": 1, "display_name": "Pessoa 1", "phone_digits": "5564999111111", "message": "Msg 1"},
            {"contact_id": 2, "display_name": "Pessoa 2", "phone_digits": "5564999222222", "message": "Msg 2"},
        ]

        res = whatsapp_batch_send(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            recipients=recipients,
            rate_limit_delay_seconds=0.0,
            require_approval=False,
            delivery_timeout_seconds=0.2,
            db_path=db_file,
        )

        assert res["uncertain_items"] == 1
        assert res["confirmed_items"] == 0
        assert res["status"] == JOB_STATUS_PAUSED

        # Check DB state: Item 1 has status 'uncertain'; item 2 must not dispatch
        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            items = conn.execute("SELECT * FROM whatsapp_batch_items WHERE job_id = ? ORDER BY id", (res["job_id"],)).fetchall()
            assert items[0]["status"] == ITEM_STATUS_UNCERTAIN
            assert items[1]["status"] == "queued"

        # An unresolved uncertain item must block all queued sends on resume.
        nav.reset_mock()
        resume_res = whatsapp_batch_resume(
            job_id=res["job_id"],
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            db_path=db_file,
        )
        assert resume_res["status"] == JOB_STATUS_PAUSED
        nav.assert_not_called()

    def test_batch_interruption_and_resume_without_duplicates(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        recipients = [
            {"contact_id": 1, "display_name": "Pessoa 1", "phone_digits": "5564999111111", "message": "Msg 1"},
            {"contact_id": 2, "display_name": "Pessoa 2", "phone_digits": "5564999222222", "message": "Msg 2"},
            {"contact_id": 3, "display_name": "Pessoa 3", "phone_digits": "5564999333333", "message": "Msg 3"},
            {"contact_id": 4, "display_name": "Pessoa 4", "phone_digits": "5564999444444", "message": "Msg 4"},
        ]
        nav1, snap1, click1 = _mock_successful_browser(["Pessoa 1", "Pessoa 2"])

        # Step 1: Run with max_messages = 2 (simulates pause/checkpoint)
        res1 = whatsapp_batch_send(
            browser_navigate=nav1,
            browser_snapshot=snap1,
            browser_click=click1,
            recipients=recipients,
            max_messages=2,
            rate_limit_delay_seconds=0.0,
            require_approval=False,
            db_path=db_file,
        )

        assert res1["status"] == JOB_STATUS_PAUSED
        assert res1["processed_items"] == 2
        assert res1["confirmed_items"] == 2

        # Step 2: Resume the batch
        # Exactly 2 remaining items should be processed
        nav2, snap2, click2 = _mock_successful_browser(["Pessoa 3", "Pessoa 4"])
        nav2_spy = MagicMock(side_effect=nav2)

        res2 = whatsapp_batch_resume(
            job_id=res1["job_id"],
            browser_navigate=nav2_spy,
            browser_snapshot=snap2,
            browser_click=click2,
            rate_limit_delay_seconds=0.0,
            db_path=db_file,
        )

        assert res2["status"] == JOB_STATUS_COMPLETED
        assert res2["total_items"] == 4
        assert res2["processed_items"] == 4
        assert res2["confirmed_items"] == 4
        # Navigation was called exactly 2 times for the 2 remaining contacts (never for the first 2)
        assert nav2_spy.call_count == 2


class TestWhatsappBatchControls:
    def test_pause_and_cancel_controls(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        recipients = [
            {"contact_id": 1, "display_name": "Pessoa 1", "phone_digits": "5564999111111", "message": "Msg 1"},
            {"contact_id": 2, "display_name": "Pessoa 2", "phone_digits": "5564999222222", "message": "Msg 2"},
        ]

        from workstation.integrations.hermes.whatsapp_batch_executor import create_batch_job
        job_id = create_batch_job(recipients=recipients, db_path=db_file)

        # Pause control
        pause_res = whatsapp_batch_pause(job_id, db_path=db_file)
        assert pause_res["action"] == "pause_requested"

        status_res = whatsapp_batch_status(job_id, db_path=db_file)
        assert status_res["stop_requested"] == 1

        # Cancel control
        cancel_res = whatsapp_batch_cancel(job_id, db_path=db_file)
        assert cancel_res["status"] == JOB_STATUS_CANCELLED

        status_res = whatsapp_batch_status(job_id, db_path=db_file)
        assert status_res["status"] == JOB_STATUS_CANCELLED

    def test_auto_pause_on_consecutive_failures(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        # Always fails navigation
        nav = MagicMock(side_effect=RuntimeError("disconnected"))
        snap = MagicMock()
        click = MagicMock()

        recipients = [
            {"contact_id": 1, "display_name": "Pessoa 1", "phone_digits": "5564999111111", "message": "Msg 1"},
            {"contact_id": 2, "display_name": "Pessoa 2", "phone_digits": "5564999222222", "message": "Msg 2"},
            {"contact_id": 3, "display_name": "Pessoa 3", "phone_digits": "5564999333333", "message": "Msg 3"},
        ]

        res = whatsapp_batch_send(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            recipients=recipients,
            max_consecutive_failures=2,
            rate_limit_delay_seconds=0.0,
            require_approval=False,
            db_path=db_file,
        )

        # Must auto-pause after 2 consecutive failures, leaving item 3 queued
        assert res["status"] == JOB_STATUS_PAUSED
        assert res["failed_items"] == 2
        assert res["processed_items"] == 2

        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            items = conn.execute("SELECT * FROM whatsapp_batch_items WHERE job_id = ? ORDER BY id", (res["job_id"],)).fetchall()
            assert items[0]["status"] == ITEM_STATUS_FAILED
            assert items[1]["status"] == ITEM_STATUS_FAILED
            assert items[2]["status"] == "queued"


class TestWhatsappBatchCampaignMirroring:
    def test_batch_mirrors_to_campaign_sends_table(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        with sqlite3.connect(db_file) as conn:
            conn.execute("CREATE TABLE campaigns (id INTEGER PRIMARY KEY, slug TEXT UNIQUE, name TEXT)")
            conn.execute("CREATE TABLE campaign_messages (id INTEGER PRIMARY KEY, campaign_id INTEGER, step_code TEXT)")
            conn.execute("CREATE TABLE campaign_enrollments (id INTEGER PRIMARY KEY, campaign_id INTEGER, contact_id INTEGER)")
            conn.execute("""
                CREATE TABLE campaign_sends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id INTEGER,
                    enrollment_id INTEGER,
                    contact_id INTEGER,
                    campaign_message_id INTEGER,
                    step_code TEXT,
                    channel TEXT,
                    status TEXT,
                    transport TEXT,
                    attempted_at TEXT,
                    sent_at TEXT,
                    confirmed_at TEXT,
                    evidence TEXT,
                    error_message TEXT,
                    updated_at TEXT
                )
            """)
            conn.execute("INSERT INTO campaigns VALUES (1, 'oficina-ia', 'Oficina IA')")
            conn.execute("INSERT INTO campaign_messages VALUES (10, 1, 'convite_oficina')")
            conn.execute("INSERT INTO campaign_enrollments VALUES (100, 1, 55)")
            conn.commit()

        nav, snap, click = _mock_successful_browser(["Raphael Valongo"])
        recipients = [
            {"contact_id": 55, "display_name": "Raphael Valongo", "phone_digits": "5564999555555", "message": "Olá Raphael"},
        ]

        res = whatsapp_batch_send(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            recipients=recipients,
            campaign_slug="oficina-ia",
            step_code="convite_oficina",
            rate_limit_delay_seconds=0.0,
            db_path=db_file,
        )

        assert res["status"] == JOB_STATUS_COMPLETED
        assert res["confirmed_items"] == 1

        with sqlite3.connect(db_file) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM campaign_sends WHERE campaign_id=1 AND contact_id=55").fetchone()
            assert row is not None
            assert row["status"] == "sent"
            assert row["transport"] == "whatsapp_web"
            assert row["sent_at"] is not None


class TestWhatsappBrowserWorkstationBatchIntegration:
    def test_browser_workstation_batch_tools(self, tmp_path) -> None:
        from tools.browser_workstation import (
            whatsapp_batch_control,
            whatsapp_batch_status as tool_batch_status,
        )

        db_file = tmp_path / "whatsapp_control.db"
        recipients = [
            {"contact_id": 1, "display_name": "Pessoa 1", "phone_digits": "5564999111111", "message": "Msg 1"},
        ]

        from workstation.integrations.hermes.whatsapp_batch_executor import create_batch_job
        job_id = create_batch_job(recipients=recipients, db_path=db_file)

        # Inspect status via tool wrapper
        st = tool_batch_status(job_id=job_id, db_path=str(db_file))
        assert st["job_id"] == job_id
        assert st["status"] == "PENDING"
        assert st["total_items"] == 1

        # Control via tool wrapper
        pause_res = whatsapp_batch_control(job_id=job_id, action="pause", db_path=str(db_file))
        assert pause_res["action"] == "pause_requested"

        cancel_res = whatsapp_batch_control(job_id=job_id, action="cancel", db_path=str(db_file))
        assert cancel_res["status"] == JOB_STATUS_CANCELLED


class TestWhatsappBatchPreviewAndApproval:
    def test_preview_dry_run_identifies_eligible_and_excluded(self, tmp_path) -> None:
        from workstation.integrations.hermes.whatsapp_batch_executor import whatsapp_batch_preview

        db_file = tmp_path / "whatsapp_control.db"
        with sqlite3.connect(db_file) as conn:
            conn.execute("CREATE TABLE campaigns (id INTEGER PRIMARY KEY, slug TEXT UNIQUE)")
            conn.execute("""
                CREATE TABLE campaign_sends (
                    id INTEGER PRIMARY KEY, campaign_id INTEGER, contact_id INTEGER, status TEXT
                )
            """)
            conn.execute("INSERT INTO campaigns VALUES (1, 'campanha-teste')")
            # Contact 10 was already sent; contact 20 is uncertain
            conn.execute("INSERT INTO campaign_sends VALUES (1, 1, 10, 'sent')")
            conn.execute("INSERT INTO campaign_sends VALUES (2, 1, 20, 'uncertain')")
            conn.commit()

        recipients = [
            {"contact_id": 1, "display_name": "Contato Válido 1", "phone_digits": "5564999111111", "message": "Olá Contato 1"},
            {"contact_id": 2, "display_name": "Contato Válido 2", "phone_digits": "5564999222222", "message": "Olá Contato 2"},
            {"contact_id": 3, "display_name": "Mascarado", "phone_digits": "5564****3333", "message": "Olá"},
            {"contact_id": 4, "display_name": "[nome]", "phone_digits": "5564999444444", "message": "Olá"},
            {"contact_id": 5, "display_name": "Template Vazado", "phone_digits": "5564999555555", "message": "Olá {NOME}!"},
            {"contact_id": 10, "display_name": "Já Enviado", "phone_digits": "5564999666666", "message": "Olá"},
            {"contact_id": 20, "display_name": "Incerto", "phone_digits": "5564999777777", "message": "Olá"},
        ]

        preview = whatsapp_batch_preview(
            recipients=recipients,
            campaign_slug="campanha-teste",
            db_path=db_file,
            sample_size=2,
        )

        assert preview["mode"] == "dry_run_preview"
        assert preview["total_contacts"] == 7
        assert preview["eligible_count"] == 2
        assert preview["excluded_count"] == 5

        # Check reasons breakdown
        breakdown = preview["reasons_breakdown"]
        assert breakdown["MASKED_PHONE"] == 1
        assert breakdown["AMBIGUOUS_IDENTITY"] == 1
        assert breakdown["TEMPLATE_PLACEHOLDER_LEAK"] == 1
        assert breakdown["ALREADY_SENT"] == 1
        assert breakdown["ALREADY_UNCERTAIN"] == 1

        # Check sample messages
        assert len(preview["sample_messages"]) == 2
        assert preview["sample_messages"][0]["contact_id"] == 1
        assert "phone_digits" not in preview["sample_messages"][0]
        assert preview["sample_messages"][0]["rendered_message"] == "[redacted]"
        assert preview["manifest_hash"] is not None

    def test_approval_gate_blocks_unauthorized_batch(self, tmp_path) -> None:
        db_file = tmp_path / "whatsapp_control.db"
        nav, snap, click = _mock_successful_browser(["Contato 1", "Contato 2"])

        recipients = [
            {"contact_id": 1, "display_name": "Contato 1", "phone_digits": "5564999111111", "message": "Msg 1"},
            {"contact_id": 2, "display_name": "Contato 2", "phone_digits": "5564999222222", "message": "Msg 2"},
        ]

        # 1. Attempt batch send without approval token
        res_blocked = whatsapp_batch_send(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            recipients=recipients,
            db_path=db_file,
            rate_limit_delay_seconds=0.0,
        )

        assert res_blocked["status"] == "APPROVAL_REQUIRED"
        assert res_blocked["approval_required"] is True
        assert "manifest_hash" in res_blocked
        # Zero browser navigation on blocked approval gate
        nav.assert_not_called()

        # 2. Issue approval token for this exact manifest hash
        from workstation.integrations.hermes.whatsapp_batch_executor import whatsapp_batch_approve
        auth_res = whatsapp_batch_approve(
            manifest_hash=res_blocked["manifest_hash"],
            total_eligible=res_blocked["eligible_count"],
            approved_by="supervisor_user",
            db_path=db_file,
        )

        assert auth_res["status"] == "DENIED"
        assert auth_res["error_code"] == "HUMAN_APPROVAL_ATTESTATION_REQUIRED"
        assert "approval_token" not in auth_res
        # Fixture simulates an independently authenticated host grant. The old
        # free-text approver cannot mint it; batch still verifies exact digest.
        token = _seed_existing_approval_fixture(
            db_file, res_blocked["manifest_hash"], res_blocked["eligible_count"],
        )

        # 3. Re-run passing the fixture approval token -> should proceed
        res_approved = whatsapp_batch_send(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            recipients=recipients,
            approval_token=token,
            db_path=db_file,
            rate_limit_delay_seconds=0.0,
        )

        assert res_approved["status"] == JOB_STATUS_COMPLETED
        assert res_approved["confirmed_items"] == 2

    def test_approval_gate_rejects_tampered_recipients_or_content(self, tmp_path) -> None:
        from workstation.integrations.hermes.whatsapp_batch_executor import (
            whatsapp_batch_approve,
            whatsapp_batch_preview,
        )

        db_file = tmp_path / "whatsapp_control.db"
        nav, snap, click = _mock_successful_browser()

        recipients_original = [
            {"contact_id": 1, "display_name": "Contato 1", "phone_digits": "5564999111111", "message": "Msg original"},
            {"contact_id": 2, "display_name": "Contato 2", "phone_digits": "5564999222222", "message": "Msg original"},
        ]

        # Get preview and approval for original list
        prev = whatsapp_batch_preview(recipients=recipients_original, db_path=db_file)
        denied = whatsapp_batch_approve(manifest_hash=prev["manifest_hash"], db_path=db_file)
        assert denied["status"] == "DENIED"
        token = _seed_existing_approval_fixture(db_file, prev["manifest_hash"])

        # Tampering 1: Changing message text
        recipients_tampered_text = [
            {"contact_id": 1, "display_name": "Contato 1", "phone_digits": "5564999111111", "message": "Msg ALTERADA SEM AUTORIZAÇÃO"},
            {"contact_id": 2, "display_name": "Contato 2", "phone_digits": "5564999222222", "message": "Msg original"},
        ]
        res_tampered1 = whatsapp_batch_send(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            recipients=recipients_tampered_text,
            approval_token=token,
            db_path=db_file,
            rate_limit_delay_seconds=0.0,
        )
        assert res_tampered1["status"] == "APPROVAL_INVALID"
        assert res_tampered1["error_code"] == "APPROVAL_INVALID"
        nav.assert_not_called()

        # Tampering 2: Adding extra recipient outside approved manifest
        recipients_tampered_list = [
            *recipients_original,
            {"contact_id": 3, "display_name": "Contato Infiltrado", "phone_digits": "5564999333333", "message": "Msg original"},
        ]
        res_tampered2 = whatsapp_batch_send(
            browser_navigate=nav,
            browser_snapshot=snap,
            browser_click=click,
            recipients=recipients_tampered_list,
            approval_token=token,
            db_path=db_file,
            rate_limit_delay_seconds=0.0,
        )
        assert res_tampered2["status"] == "APPROVAL_INVALID"
        nav.assert_not_called()

    def test_browser_workstation_preview_and_approve_tools(self, tmp_path) -> None:
        from tools.browser_workstation import (
            whatsapp_batch_approve as tool_approve,
            whatsapp_batch_preview as tool_preview,
        )

        db_file = tmp_path / "whatsapp_control.db"
        recipients = [
            {"contact_id": 1, "display_name": "Pessoa 1", "phone_digits": "5564999111111", "message": "Msg 1"},
            {"contact_id": 2, "display_name": "Pessoa 2", "phone_digits": "5564999222222", "message": "Msg 2"},
        ]

        prev = tool_preview(recipients=recipients, db_path=str(db_file))
        assert prev["mode"] == "dry_run_preview"
        assert prev["eligible_count"] == 2

        appr = tool_approve(manifest_hash=prev["manifest_hash"], approved_by="admin", db_path=str(db_file))
        assert appr["status"] == "DENIED"
        assert appr["error_code"] == "HUMAN_APPROVAL_ATTESTATION_REQUIRED"
        assert "approval_token" not in appr
        assert not db_file.exists()



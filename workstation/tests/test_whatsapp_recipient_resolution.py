"""Recipient references resolve privately against explicitly configured sources."""

import sqlite3

import pytest

from workstation.integrations.hermes.whatsapp_recipient_resolution import (
    RecipientResolutionError,
    resolve_recipient_reference,
)


@pytest.fixture
def recipient_source(tmp_path):
    path = tmp_path / "contacts.db"
    with sqlite3.connect(path) as conn:
        conn.executescript(
            "CREATE TABLE contacts (id INTEGER PRIMARY KEY, whatsapp_id TEXT, "
            "display_name TEXT, type TEXT, phone_raw TEXT, phone_number TEXT, phone_source TEXT);"
            "CREATE TABLE campaign_enrollments (id INTEGER PRIMARY KEY, campaign_id INTEGER, "
            "contact_id INTEGER, status TEXT, authorized_at TEXT, authorized_via TEXT);"
        )
        conn.execute(
            "INSERT INTO contacts VALUES (?, ?, ?, ?, ?, ?, ?)",
            (7, "15555550123@c.us", "Synthetic contact", "contact", "15555550123", None, "synthetic-import"),
        )
        conn.execute(
            "INSERT INTO campaign_enrollments VALUES (?, ?, ?, ?, ?, ?)",
            (11, 3, 7, "replied_authorized", "2026-10-24", "human-recorded"),
        )
    return path, {"synthetic": {"db_path": str(path), "allowed_phone_sources": ["synthetic-import"]}}


def test_individual_reference_keeps_phone_private(recipient_source):
    _, sources = recipient_source
    recipient = resolve_recipient_reference({"source": "synthetic", "contact_id": 7}, sources=sources)
    assert recipient.phone_digits == "15555550123"
    assert recipient.public_reference == {"source": "synthetic", "contact_id": 7}
    assert "15555550123" not in repr(recipient)


def test_campaign_reference_checks_contact_identity(recipient_source):
    _, sources = recipient_source
    recipient = resolve_recipient_reference(
        {"source": "synthetic", "campaign_id": 3, "enrollment_id": 11, "contact_id": 7}, sources=sources
    )
    assert recipient.phone_digits == "15555550123"
    with pytest.raises(RecipientResolutionError, match="RECIPIENT_IDENTITY_MISMATCH"):
        resolve_recipient_reference(
            {"source": "synthetic", "campaign_id": 3, "enrollment_id": 11, "contact_id": 8}, sources=sources
        )


@pytest.mark.parametrize("reference", [
    {"source": "untrusted", "contact_id": 7},
    {"source": "synthetic", "contact_id": 7, "db_path": "/arbitrary.db"},
])
def test_model_cannot_select_unconfigured_source_or_path(recipient_source, reference):
    _, sources = recipient_source
    with pytest.raises(RecipientResolutionError):
        resolve_recipient_reference(reference, sources=sources)


@pytest.mark.parametrize("column,value,code", [
    ("phone_raw", "1555****0123", "MASKED_PHONE"),
    ("phone_source", "unknown", "UNAUTHORIZED_RECIPIENT_SOURCE"),
    ("whatsapp_id", "15555550999@c.us", "RECIPIENT_IDENTITY_MISMATCH"),
])
def test_invalid_original_provenance_or_identity_is_rejected(recipient_source, column, value, code):
    path, sources = recipient_source
    with sqlite3.connect(path) as conn:
        conn.execute(f"UPDATE contacts SET {column} = ? WHERE id = 7", (value,))
    with pytest.raises(RecipientResolutionError, match=code) as error:
        resolve_recipient_reference({"source": "synthetic", "contact_id": 7}, sources=sources)
    assert "1555" not in str(error.value)


def test_cross_campaign_and_opt_out_do_not_resolve(recipient_source):
    path, sources = recipient_source
    with pytest.raises(RecipientResolutionError):
        resolve_recipient_reference(
            {"source": "synthetic", "campaign_id": 4, "enrollment_id": 11}, sources=sources
        )
    with sqlite3.connect(path) as conn:
        conn.execute("UPDATE campaign_enrollments SET status = 'opted_out' WHERE id = 11")
    with pytest.raises(RecipientResolutionError):
        resolve_recipient_reference(
            {"source": "synthetic", "campaign_id": 3, "enrollment_id": 11}, sources=sources
        )


def test_missing_database_is_not_created(tmp_path):
    path = tmp_path / "absent.db"
    with pytest.raises(RecipientResolutionError):
        resolve_recipient_reference(
            {"source": "synthetic", "contact_id": 7},
            sources={"synthetic": {"db_path": str(path), "allowed_phone_sources": ["synthetic-import"]}},
        )
    assert not path.exists()


def test_active_profile_configuration_is_used(recipient_source, monkeypatch):
    _, sources = recipient_source
    monkeypatch.setattr("hermes_cli.config.load_config_readonly", lambda: {"whatsapp": {"sources": sources}})
    recipient = resolve_recipient_reference({"source": "synthetic", "contact_id": 7})
    assert recipient.phone_digits == "15555550123"


def test_reference_to_wrapper_keeps_private_inputs_internal(recipient_source, monkeypatch):
    import json
    from tools.browser_workstation import whatsapp_send_message

    path, sources = recipient_source
    monkeypatch.setattr("hermes_cli.config.load_config_readonly", lambda: {"whatsapp": {"sources": sources}})
    captured = {}

    def sender(**kwargs):
        captured.update(kwargs)
        return {
            "sent": True, "state": "UNCERTAIN", "error_code": "RECONCILIATION_REQUIRED",
            "message_data_id": "true_15555550123@c.us_SYNTHETIC",
            "diagnostic": "https://web.whatsapp.com/send?phone=15555550123&text=private-body",
        }

    monkeypatch.setattr("workstation.integrations.hermes.whatsapp_browser_executor.whatsapp_send_message", sender)
    result = whatsapp_send_message(
        recipient_ref={"source": "synthetic", "contact_id": 7},
        expected_recipient_name="Synthetic Contact", message="private-body",
        task_id=None, session_id="synthetic-session",
        kanban_card_id=None, run_id="synthetic-call", operation_id="synthetic-call",
    )
    assert captured["phone_digits"] == "15555550123"
    # Source DB is read-only provenance; send logging belongs to the separate canonical control DB.
    assert "db_path" not in captured
    assert captured["task_id"] is None
    assert captured["session_id"] == "synthetic-session"
    assert captured["run_id"] == "synthetic-call"
    assert result["state"] == "UNCERTAIN"
    assert result["recipient_ref"] == {"source": "synthetic", "contact_id": 7}
    assert "15555550123" not in json.dumps(result)
    assert "private-body" not in json.dumps(result)


def test_invalid_reference_never_enters_executor(recipient_source, monkeypatch):
    from unittest.mock import Mock
    from tools.browser_workstation import whatsapp_send_message

    _, sources = recipient_source
    monkeypatch.setattr("hermes_cli.config.load_config_readonly", lambda: {"whatsapp": {"sources": sources}})
    sender = Mock()
    monkeypatch.setattr("workstation.integrations.hermes.whatsapp_browser_executor.whatsapp_send_message", sender)
    result = whatsapp_send_message(
        recipient_ref={"source": "untrusted", "contact_id": 7}, message="test",
        task_id="synthetic-task", session_id="synthetic-session", kanban_card_id="synthetic-task",
        run_id="synthetic-run", operation_id="synthetic-call",
    )
    assert result["sent"] is False
    assert result["error_code"] == "UNAUTHORIZED_RECIPIENT_SOURCE"
    sender.assert_not_called()


def test_registered_model_tool_is_reference_only_desktop_mutation(monkeypatch):
    import json
    import tools.browser_tool
    from tools.effects import ToolEffect
    from tools.registry import registry
    from toolsets import TOOLSETS
    entry = registry.get_entry("whatsapp_send_message")
    assert entry is not None
    assert entry.toolset == "desktop_ui"
    assert entry.effect == ToolEffect.MUTATION
    assert "whatsapp_send_message" in TOOLSETS["desktop_ui"]["tools"]
    assert "whatsapp_send_message" not in TOOLSETS["browser"]["tools"]
    definitions = registry.get_definitions(
        {"whatsapp_send_message"}, force_available={"whatsapp_send_message"}
    )
    assert len(definitions) == 1
    parameters = definitions[0]["function"]["parameters"]
    assert set(parameters["required"]) == {"message"}
    assert {"recipient_ref", "target_name", "expected_recipient_name"} <= set(parameters["properties"])
    assert "phone_digits" not in parameters["properties"]
    assert "db_path" not in parameters["properties"]

    captured = {}

    def send(**kwargs):
        captured.update(kwargs)
        return {"sent": False, "state": "UNCERTAIN", "error_code": "RECONCILIATION_REQUIRED"}

    monkeypatch.setattr("tools.browser_workstation.whatsapp_send_message", send)
    from workstation.task_compiler import execution_context
    payload = {
        "recipient_ref": {"source": "synthetic", "contact_id": 7},
        "expected_recipient_name": "Synthetic Contact",
        "message": "Synthetic body",
    }
    # Registered calls without a host admission cannot borrow a run.
    denied = json.loads(entry.handler(
        payload, session_id="synthetic-session", tool_call_id="synthetic-call",
    ))
    assert denied["error_code"] == "TASKRUN_AUTHORITY_REQUIRED"
    assert not captured

    with execution_context(
        lambda *a, **kw: None, "synthetic-session",
        canonical_task_id="synthetic-task", canonical_run_id="synthetic-run",
    ):
        result = json.loads(entry.handler(
            payload, session_id="synthetic-session", tool_call_id="synthetic-call",
        ))
    assert captured["recipient_ref"] == payload["recipient_ref"]
    assert captured["task_id"] == "synthetic-task"
    assert captured["kanban_card_id"] == "synthetic-task"
    assert captured["session_id"] == "synthetic-session"
    assert captured["run_id"] == "synthetic-run"
    assert captured["operation_id"] == "synthetic-call"
    assert result["state"] == "UNCERTAIN"
    captured.clear()
    with execution_context(
        lambda *a, **kw: None, "synthetic-session",
        canonical_task_id="synthetic-task", canonical_run_id="synthetic-run",
    ):
        named = json.loads(entry.handler(
            {"target_name": "Kevyn ACIRV", "message": "oi"},
            session_id="synthetic-session", tool_call_id="named-call",
        ))
    assert captured["target_name"] == "Kevyn ACIRV"
    assert captured["recipient_ref"] is None
    assert captured["run_id"] == "synthetic-run"
    assert named["state"] == "UNCERTAIN"
    captured.clear()
    invalid = json.loads(entry.handler({"phone_digits": "15555550123", "message": "Synthetic body"}))
    assert invalid["sent"] is False
    assert not captured


@pytest.mark.parametrize("column,value", [
    ("phone_raw", "1555****0123"),
    ("whatsapp_id", "15555550999@c.us"),
    ("phone_source", "not-authorized"),
])
def test_bad_reference_record_blocks_all_browser_actions(recipient_source, monkeypatch, column, value):
    from unittest.mock import Mock
    from tools.browser_workstation import whatsapp_send_message

    path, sources = recipient_source
    with sqlite3.connect(path) as conn:
        conn.execute(f"UPDATE contacts SET {column} = ? WHERE id = 7", (value,))
    monkeypatch.setattr("hermes_cli.config.load_config_readonly", lambda: {"whatsapp": {"sources": sources}})
    browser = Mock()
    monkeypatch.setattr("tools.browser_workstation._dispatch", browser)
    result = whatsapp_send_message(
        recipient_ref={"source": "synthetic", "contact_id": 7}, message="Synthetic body",
        task_id="synthetic-task", session_id="synthetic-session", kanban_card_id="synthetic-task",
        run_id="synthetic-run", operation_id="synthetic-call",
    )
    assert result["sent"] is False
    browser.assert_not_called()


def test_sanitizing_a_message_named_like_a_state_preserves_reconciliation():
    from workstation.integrations.hermes.whatsapp_browser_executor import sanitize_send_result

    result = sanitize_send_result(
        {"state": "UNCERTAIN", "sent": False, "error_code": "RECONCILIATION_REQUIRED", "diagnostic": "UNCERTAIN"},
        phone_digits="15555550123", message="UNCERTAIN",
    )
    assert result["state"] == "UNCERTAIN"
    assert result["error_code"] == "RECONCILIATION_REQUIRED"
    assert result["diagnostic"] == "[redacted]"


def test_control_database_has_no_implicit_fallback(monkeypatch, tmp_path):
    from workstation.integrations.hermes.whatsapp_browser_executor import get_default_db_path

    monkeypatch.setattr("hermes_cli.config.load_config_readonly", dict)
    monkeypatch.delenv("WHATSAPP_CONTROL_DB", raising=False)
    assert get_default_db_path() is None
    explicit = tmp_path / "explicit.db"
    monkeypatch.setenv("WHATSAPP_CONTROL_DB", str(explicit))
    assert get_default_db_path() == explicit
    profile = tmp_path / "profile.db"
    monkeypatch.setattr(
        "hermes_cli.config.load_config_readonly", lambda: {"whatsapp": {"control_db_path": str(profile)}}
    )
    assert get_default_db_path() == profile
    assert not explicit.exists()
    assert not profile.exists()


def test_legacy_configuration_failure_precedes_browser_effects(monkeypatch):
    from unittest.mock import Mock
    from workstation.integrations.hermes.whatsapp_browser_executor import whatsapp_send_message

    def broken_config():
        raise ValueError("invalid synthetic configuration")

    monkeypatch.setattr("hermes_cli.config.load_config_readonly", broken_config)
    navigate, snapshot, click = Mock(), Mock(), Mock()
    with pytest.raises(ValueError, match="invalid synthetic configuration"):
        whatsapp_send_message(
            browser_navigate=navigate, browser_snapshot=snapshot, browser_click=click,
            phone_digits="15555550123", message="Synthetic body",
        )
    navigate.assert_not_called()
    snapshot.assert_not_called()
    click.assert_not_called()


@pytest.mark.parametrize("surface,exposed", [("desktop", True), ("tui", False)])
def test_reference_schema_follows_session_surface(monkeypatch, surface, exposed):
    import tools.browser_tool
    from tools.browser_workstation import workstation_schema_tools_for_current_session
    from tools.registry import registry

    monkeypatch.setattr("tools.browser_workstation.workstation_browser_enabled", lambda: True)
    monkeypatch.setattr(
        "gateway.session_context.get_session_env",
        lambda key, default="": surface if key == "HERMES_SESSION_SOURCE" else default,
    )
    names = workstation_schema_tools_for_current_session()
    assert ("whatsapp_send_message" in names) is exposed
    definitions = registry.get_definitions(names & {"whatsapp_send_message"}, force_available=names)
    assert bool(definitions) is exposed

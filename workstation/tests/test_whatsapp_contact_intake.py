"""WA-MVP-02A: user-requested unsaved phone intake into canonical WhatsApp DB."""
import json
import sqlite3
from contextlib import closing

import pytest

from workstation.integrations.hermes import whatsapp_recipient_resolution as resolver

PHONE = "556492470988"
NAME = "Kevyn ACIRV"


@pytest.fixture
def control_db(tmp_path, monkeypatch):
    path = tmp_path / "control.sqlite"
    with closing(sqlite3.connect(path)) as conn:
        conn.execute("CREATE TABLE whatsapp_send_logs (id INTEGER PRIMARY KEY)")
        conn.commit()
    monkeypatch.setattr(
        "workstation.integrations.hermes.whatsapp_browser_executor.get_default_db_path",
        lambda: path,
    )
    return path


def test_unsaved_contact_registration_is_durable_idempotent_and_non_authorizing(control_db):
    from workstation.integrations.hermes.whatsapp_contact_intake import register_requested_contact
    a = register_requested_contact(phone="+55 (64) 9247-0988", display_name=NAME)
    b = register_requested_contact(phone="556492470988", display_name=NAME)
    assert a == b
    assert a["recipient_ref"]["source"] == "hermes_local"
    assert a["verification_state"] == "PENDING_NATIVE_VERIFICATION"
    assert PHONE not in json.dumps(a)
    assert "approved" not in json.dumps(a)
    with closing(sqlite3.connect(control_db)) as conn:
        rows = conn.execute(
            "SELECT phone_number, phone_source, whatsapp_id FROM contacts"
        ).fetchall()
        assert rows == [(PHONE, "user_requested_unverified", "pending:" + PHONE)]
    r = resolver.resolve_recipient_reference(a["recipient_ref"])
    assert r.phone_digits == PHONE
    assert r.display_name == NAME


@pytest.mark.parametrize("phone", ["6492470988", "+55 64 92XX-0988", "****0988", "1234", "", "+55 64 9247-0988 ext. 3"])
def test_invalid_phone_fails_without_registering(control_db, phone):
    from workstation.integrations.hermes.whatsapp_contact_intake import register_requested_contact, ContactIntakeError
    with pytest.raises(ContactIntakeError):
        register_requested_contact(phone=phone, display_name=NAME)
    with closing(sqlite3.connect(control_db)) as conn:
        exists = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='contacts'").fetchone()[0]
        assert exists == 0


def test_local_reference_drift_and_forged_source_fail_closed(control_db):
    from workstation.integrations.hermes.whatsapp_contact_intake import register_requested_contact
    ref = register_requested_contact(phone="+55 64 9247-0988", display_name=NAME)["recipient_ref"]
    with closing(sqlite3.connect(control_db)) as conn:
        conn.execute("UPDATE contacts SET phone_number=? WHERE id=?", ("5564999999999", ref["contact_id"]))
        conn.commit()
    with pytest.raises(resolver.RecipientResolutionError, match="RECIPIENT_IDENTITY_MISMATCH"):
        resolver.resolve_recipient_reference(ref)
    with pytest.raises(resolver.RecipientResolutionError):
        resolver.resolve_recipient_reference({**ref, "db_path": str(control_db)})


def test_contact_requires_real_observed_receipt_before_promoting(control_db):
    from workstation.integrations.hermes.whatsapp_contact_intake import (
        register_requested_contact, promote_verified_contact,
    )
    ref = register_requested_contact(phone="+55 64 9247-0988", display_name=NAME)["recipient_ref"]
    assert promote_verified_contact(ref, phone_digits=PHONE, receipt_state="UNCERTAIN") is False
    assert promote_verified_contact(ref, phone_digits="5564000000000", receipt_state="OBSERVED") is False
    assert promote_verified_contact(ref, phone_digits=PHONE, receipt_state="OBSERVED") is True
    with closing(sqlite3.connect(control_db)) as conn:
        row = conn.execute("SELECT phone_source, whatsapp_id FROM contacts").fetchone()
        assert row == ("whatsapp_native_verified", PHONE + "@c.us")


def test_model_registration_requires_taskrun_and_does_not_leak_phone(control_db):
    from tools.browser_tool import _handle_whatsapp_register_contact
    from workstation.task_compiler import execution_context

    payload = {"phone": "+55 64 9247-0988", "display_name": NAME}
    denied = json.loads(_handle_whatsapp_register_contact(payload, session_id="session", tool_call_id="call"))
    assert denied["error_code"] == "TASKRUN_AUTHORITY_REQUIRED"
    with execution_context(
        lambda *a, **kw: None, "session",
        canonical_task_id="card", canonical_run_id="run",
    ):
        result = json.loads(_handle_whatsapp_register_contact(
            payload, session_id="session", tool_call_id="call",
        ))
    assert result["recipient_ref"]["source"] == "hermes_local"
    assert PHONE not in json.dumps(result)
    assert result["verification_state"] == "PENDING_NATIVE_VERIFICATION"


def test_find_contacts_from_canonical_directory_is_read_only(control_db):
    from workstation.integrations.hermes.whatsapp_contact_intake import register_requested_contact
    from tools.whatsapp_catalog_adapter import find_contacts_for_model

    ref = register_requested_contact(phone="+55 64 9247-0988", display_name=NAME)["recipient_ref"]
    out = json.loads(find_contacts_for_model(
        {"source": "hermes_local", "query": "Kevyn"},
        session_id="session", tool_call_id="call",
    ))
    assert out["count"] == 1
    assert out["contacts"][0]["recipient_ref"] == ref
    assert PHONE not in json.dumps(out)



@pytest.mark.parametrize("link", [
    "https://wa.me/556492470988",
    "https://web.whatsapp.com/send?phone=556492470988",
    "https://api.whatsapp.com/send?phone=556492470988",
])
def test_phone_only_whatsapp_deeplink_uses_same_contact_directory(control_db, link):
    from workstation.integrations.hermes.whatsapp_contact_intake import register_requested_contact
    via_link = register_requested_contact(phone=link, display_name=NAME)
    via_number = register_requested_contact(phone="+55 64 9247-0988", display_name=NAME)
    assert via_link == via_number
    assert PHONE not in json.dumps(via_link)


@pytest.mark.parametrize("link", [
    "https://wa.me/556492470988?text=unauthorized",
    "https://web.whatsapp.com/send?phone=556492470988&text=unauthorized",
    "https://evil.example/send?phone=556492470988",
    "http://wa.me/556492470988",
])
def test_deeplink_with_text_or_foreign_origin_is_not_registered(control_db, link):
    from workstation.integrations.hermes.whatsapp_contact_intake import (
        register_requested_contact, ContactIntakeError,
    )
    with pytest.raises(ContactIntakeError):
        register_requested_contact(phone=link, display_name=NAME)
    with closing(sqlite3.connect(control_db)) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE name='contacts'"
        ).fetchone()[0] == 0


def test_registration_tool_is_mutating_not_a_sender():
    import tools.browser_tool
    from tools.registry import registry
    from tools.effects import ToolEffect
    from toolsets import TOOLSETS
    entry = registry.get_entry("whatsapp_register_contact")
    assert entry is not None
    assert entry.effect == ToolEffect.MUTATION
    assert "whatsapp_register_contact" in str(TOOLSETS["desktop_ui"])
    assert set(entry.schema["parameters"]["properties"]) == {"phone", "display_name"}
    assert entry.schema["parameters"]["additionalProperties"] is False

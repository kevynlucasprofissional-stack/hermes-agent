"""RED contracts for native WhatsApp discoverability and privacy (synthetic only).

These tests deliberately document currently failing integration/safety gates.
They must not be mistaken for a green implementation or a live WhatsApp test.
"""
import json


def test_native_read_and_preview_are_registered_in_agent_catalog():
    import tools.browser_tool  # noqa: F401 - populates registry
    from tools.registry import registry

    required = {"whatsapp_read_messages", "whatsapp_batch_preview"}
    exposed = {name for name in required if registry.get_toolset_for_tool(name)}
    assert exposed == required, f"Missing first-class tool registrations: {sorted(required - exposed)}"


def test_batch_preview_never_exposes_raw_phone_to_model(tmp_path):
    from workstation.integrations.hermes.whatsapp_batch_executor import whatsapp_batch_preview

    synthetic_phone = "15555550123"
    preview = whatsapp_batch_preview(
        recipients=[{
            "contact_id": 7,
            "display_name": "Synthetic test contact",
            "phone_digits": synthetic_phone,
            "message_body": "Synthetic invitation",
            "permission_status": "authorized",
        }],
        campaign_slug="synthetic-campaign",
        step_code="wa_1",
        require_authorization=True,
        db_path=tmp_path / "nonexistent.db",
    )
    assert synthetic_phone not in json.dumps(preview), "Raw recipient PII leaked in model-facing preview"


def test_batch_token_cannot_be_minted_by_unverified_operator_string(tmp_path):
    from workstation.integrations.hermes.whatsapp_batch_executor import whatsapp_batch_approve

    result = whatsapp_batch_approve(
        manifest_hash="a" * 64,
        campaign_slug="synthetic-campaign",
        step_code="wa_1",
        total_eligible=1,
        approved_by="unverified-model-supplied-name",
        db_path=tmp_path / "temporary-control.db",
    )
    assert result.get("status") != "APPROVED", "Unverified caller minted an active approval token"

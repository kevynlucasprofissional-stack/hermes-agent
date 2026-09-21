"""H-079.2 integration proof for the optional Anthropic SDK boundary."""

from __future__ import annotations


def test_real_anthropic_sdk_client_constructs_without_network() -> None:
    """The Workstation ``anthropic`` extra must support the real builder path.

    Construction is intentionally the entire integration boundary: no Messages
    request is issued and the credential is a non-secret test value.
    """
    import anthropic

    from agent.anthropic_adapter import build_anthropic_client

    client = build_anthropic_client(
        "sk-ant-api03-h0792-non-secret-test-key",
        "https://api.anthropic.com",
        timeout=1.0,
    )

    assert isinstance(client, anthropic.Anthropic)
    assert str(client.base_url).rstrip("/") == "https://api.anthropic.com"


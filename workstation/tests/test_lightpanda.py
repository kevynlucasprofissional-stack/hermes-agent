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

from workstation.perception import PerceptionEngine, PerceptionView


def test_perception_engine_summarize():
    engine = PerceptionEngine()
    raw_dom = {
        "snapshot_id": "snap-123",
        "tag": "body",
        "children": [
            {
                "tag": "header",
                "role": "banner",
                "children": [
                    {"tag": "h1", "text": "Acme Portal"},
                    {"tag": "a", "role": "link", "text": "Home", "selector": "#nav-home"},
                ],
            },
            {
                "tag": "main",
                "role": "main",
                "children": [
                    {
                        "tag": "form",
                        "selector": "#login-form",
                        "children": [
                            {"tag": "input", "role": "textbox", "name": "Email", "value": "test@test.com", "selector": "#email"},
                            {"tag": "input", "role": "textbox", "name": "Password", "selector": "#pwd"},
                            {"tag": "button", "role": "button", "text": "Sign In", "selector": "#btn-submit"},
                        ],
                    }
                ],
            },
        ],
    }

    view = engine.summarize(raw_dom, token_budget=500)
    assert view.snapshot_id == "snap-123"
    assert view.node_count >= 5
    assert view.interactive_count >= 4
    assert "[#1]" in view.view
    assert "Sign In" in view.view
    assert "test@test.com" in view.view
    assert view.truncated is False

    # Check provenance payload
    refs = view.payload["refs"]
    assert len(refs) >= 4
    submit_ref = [k for k, v in refs.items() if v.get("name") == "Sign In"][0]
    assert refs[submit_ref]["selector"] == "#btn-submit"


def test_perception_token_budget_truncation():
    engine = PerceptionEngine()
    # Create a large tree
    large_tree = {
        "tag": "div",
        "children": [
            {"tag": "button", "role": "button", "text": f"Button Number {i} with long description text"}
            for i in range(100)
        ],
    }
    # Tight token budget (e.g. 50 tokens = ~200 chars)
    view = engine.summarize(large_tree, token_budget=50)
    assert view.truncated is True
    assert "truncated" in view.view


def test_perception_view_diff():
    engine = PerceptionEngine()
    view_a = engine.summarize({
        "children": [
            {"ref": "1", "role": "button", "name": "Submit"},
            {"ref": "2", "role": "link", "name": "Cancel"},
        ]
    })
    view_b = engine.summarize({
        "children": [
            {"ref": "1", "role": "button", "name": "Submit", "value": "Loading..."},
            {"ref": "3", "role": "status", "name": "Success Message"},
        ]
    })

    diff = engine.diff(view_a, view_b)
    assert diff["added_count"] == 1
    assert diff["removed_count"] == 1
    assert diff["changed_count"] == 1
    assert diff["changed"][0]["ref"] == "1"


def test_perception_filters_hidden_nodes():
    # H-102 Red Team verification: hidden elements must not produce perception refs
    engine = PerceptionEngine()
    dom = {
        "tag": "body",
        "children": [
            {"tag": "button", "role": "button", "name": "Visible CTA"},
            {"tag": "div", "attributes": {"aria-hidden": "true"}, "children": [
                {"tag": "button", "role": "button", "name": "Hidden in modal backdrop"},
            ]},
            {"tag": "input", "attributes": {"type": "hidden", "name": "csrf_token", "value": "secret"}},
            {"tag": "span", "attributes": {"style": "display: none"}, "children": [
                {"tag": "a", "role": "link", "name": "Invisible link"},
            ]},
        ],
    }

    view = engine.summarize(dom)
    assert "Visible CTA" in view.view
    assert "Hidden in modal backdrop" not in view.view
    assert "csrf_token" not in view.view
    assert "Invisible link" not in view.view
    assert view.interactive_count == 1


def test_smart_budget_preserves_bottom_ctas():
    # H-103 Red Team verification: long article with CTA button at very bottom
    engine = PerceptionEngine()
    dom = {
        "tag": "main",
        "children": [
            {"tag": "p", "role": "text", "name": f"Long paragraph text block number {i} filling up token space..."}
            for i in range(50)
        ] + [
            {"tag": "button", "role": "button", "name": "Checkout and Complete Order", "selector": "#btn-checkout"}
        ],
    }

    # Low token budget that forces truncation
    view = engine.summarize(dom, token_budget=100)
    assert view.truncated is True
    assert "Checkout and Complete Order" in view.view, "Critical bottom CTA must be preserved despite content truncation"
    assert "smart-budget" in view.view


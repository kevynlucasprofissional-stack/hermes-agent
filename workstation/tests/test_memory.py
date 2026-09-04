import tempfile
from pathlib import Path
from workstation.memory import ProceduralMemory, ProcedureStep, WebProcedure


def test_procedure_serialization():
    step = ProcedureStep(action="click", target="#login-btn", expectation="redirect to dashboard")
    proc = WebProcedure(
        id="proc-1",
        name="Login Flow",
        site="https://example.com/login",
        intent="log into account",
        steps=[step],
        confidence=0.9,
    )
    data = proc.to_dict()
    assert data["name"] == "Login Flow"
    assert len(data["steps"]) == 1

    restored = WebProcedure.from_dict(data)
    assert restored.id == "proc-1"
    assert restored.steps[0].action == "click"
    assert restored.steps[0].target == "#login-btn"


def test_procedural_memory_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Path(tmpdir) / "procedures.json"
        mem = ProceduralMemory(storage_path=storage)

        # Empty initially
        assert mem.discover("example.com", "search products") == []

        # Record success
        steps = [
            {"action": "navigate", "target": "https://example.com"},
            {"action": "type", "target": "input[name=q]", "value": "shoes"},
            {"action": "click", "target": "button[type=submit]"},
        ]
        proc = mem.record_success("https://example.com", "search for shoes", steps)
        assert proc.site == "https://example.com"
        assert proc.success_count == 1
        assert proc.confidence >= 0.8

        # Discover
        results = mem.discover("example.com", "search shoes")
        assert len(results) == 1
        assert results[0].id == proc.id

        # Reinforce
        reinforced = mem.record_success("https://example.com", "search for shoes", steps)
        assert reinforced.id == proc.id
        assert reinforced.success_count == 2
        assert reinforced.confidence > 0.8

        # Record failure
        initial_confidence = reinforced.confidence
        mem.record_failure(proc.id, step_index=1, reason="input missing")
        updated = mem.get_procedure(proc.id)
        assert updated is not None
        assert updated.failure_count == 1
        assert updated.confidence < initial_confidence

        # Persistence check
        reloaded = ProceduralMemory(storage_path=storage)
        assert len(reloaded.list_procedures()) == 1
        assert reloaded.get_procedure(proc.id) is not None


def test_procedure_multi_facet_anchoring():
    # H-101 verification: CSS class/selector changed in SPA build, but testid and semantic role survive
    step = ProcedureStep(
        action="click",
        target="button.btn-primary-v1-obsolete",
        expectation="Confirm purchase",
        fallback_anchors=[
            {"type": "testid", "value": "checkout-submit"},
            {"type": "role_name", "value": "button:Place Order"},
            {"type": "text", "value": "Place Order"},
        ],
    )

    # Candidate elements on page after redesign
    available_elements = [
        {
            "ref": "node-42",
            "role": "button",
            "name": "Place Order Now",
            "attributes": {"data-testid": "checkout-submit", "class": "tailwind-hash-xyz-987"},
        },
        {
            "ref": "node-10",
            "role": "link",
            "name": "Cancel",
            "attributes": {},
        },
    ]

    resolved_ref = step.resolve_anchor(available_elements)
    assert resolved_ref == "node-42", "Must resolve to node-42 via data-testid anchor despite obsolete CSS selector"


def test_concurrent_procedure_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = Path(tmpdir) / "procedures.json"
        mem_agent1 = ProceduralMemory(storage_path=storage)
        mem_agent2 = ProceduralMemory(storage_path=storage)

        # Agent 1 saves workflow A
        p1 = mem_agent1.record_success("siteA.com", "Workflow A", [{"action": "click", "target": "#btnA"}])

        # Agent 2 saves workflow B without restarting
        p2 = mem_agent2.record_success("siteB.com", "Workflow B", [{"action": "click", "target": "#btnB"}])

        # Reload fresh instance
        reloaded = ProceduralMemory(storage_path=storage)
        procs = reloaded.list_procedures()
        assert len(procs) == 2
        proc_sites = {p.site for p in procs}
        assert "siteA.com" in proc_sites
        assert "siteB.com" in proc_sites


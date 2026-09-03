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

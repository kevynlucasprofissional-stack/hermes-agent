"""Tests for Browser Lowering and Artifact Data Plane (Phase P3).

Verifies:
- browser_console traces are marked opaque_adaptive_execution, non-replayable, and rejected from candidate_steps.
- plain_text_paste semantic primitive replaces console for rich editor.
- browser_type accepts owned artifact text_ref / artifact_ref.
- cross-task, oversized, and invalid MIME artifact references are rejected.
"""
import json
import pytest
from types import SimpleNamespace

from workstation.artifacts import ArtifactStore
from workstation.memory import ProceduralMemory
from workstation.operational_kernel import OperationalKernel
from workstation.procedure_trace import candidate_steps, learn_verified_trace, record_trace
from tools.browser_workstation import resolve_browser_type_text


@pytest.fixture
def temp_artifacts(tmp_path):
    art_dir = tmp_path / "artifacts"
    art_dir.mkdir(parents=True, exist_ok=True)
    return ArtifactStore(root_dir=art_dir)


def test_browser_console_trace_is_opaque_and_not_auto_promotable(temp_artifacts, monkeypatch):
    """Console executions are opaque, non-replayable, and rejected from candidate steps and auto-promotion."""
    monkeypatch.setattr("workstation.artifacts.ArtifactStore", lambda: temp_artifacts)
    agent = SimpleNamespace(
        session_id="session_test",
        _canonical_work_task_id="task_console_test",
        _canonical_work_run_id="run_console_test",
        _current_operation_id="op_console_test",
        _work_procedure_trace=[],
        _conversation_root_id=lambda: "task_console_test",
    )

    args = {"script": "document.querySelector('textarea.desc').value = 'Updated Card';"}
    raw_res = json.dumps({"result": "Updated Card", "runtime": "electron-chromium"})

    record_trace(agent, "browser_console", args, raw_res)

    assert len(agent._work_procedure_trace) == 1
    trace = agent._work_procedure_trace[0]

    assert trace["tool"] == "browser_console"
    assert trace["action"] == "opaque_adaptive_execution"
    assert trace["execution_class"] == "opaque_adaptive_execution"
    assert trace["replayable"] is False

    # Rejected from candidate_steps
    steps = candidate_steps([trace])
    assert steps == []

    # Rejected from routine learning / promotion
    candidate = learn_verified_trace(
        ProceduralMemory(),
        [trace],
        {"persisted": True},
        {"kind": "trello_card"},
        scope={"host": "trello.com", "route": "native_browser"},
        fingerprint="fp_console",
    )
    assert candidate is None


def test_plain_text_paste_semantic_primitive_replaces_console_for_rich_editor(temp_artifacts, monkeypatch):
    """plain_text_paste is selected as first-class semantic primitive and lowers correctly."""
    monkeypatch.setattr("workstation.artifacts.ArtifactStore", lambda: temp_artifacts)

    # 1. OperationalKernel lowers plain_text_paste correctly to browser_type with mode=plain_text_paste
    kernel = OperationalKernel(artifacts=temp_artifacts)
    call = kernel.lower_primitive(
        "plain_text_paste",
        inputs={"ref": "@e3", "text": "Card Description in ProseMirror", "semantic_anchor": {"type": "testid", "value": "card-desc"}},
        route="native_browser",
    )
    assert call["tool"] == "browser_type"
    assert call["args"]["mode"] == "plain_text_paste"
    assert call["args"]["text"] == "Card Description in ProseMirror"
    assert call["args"]["semantic_anchor"]["value"] == "card-desc"

    # 2. Trace recorded for semantic paste is replayable and semantic
    agent = SimpleNamespace(
        session_id="session_test",
        _canonical_work_task_id="task_paste_test",
        _canonical_work_run_id="run_paste_test",
        _current_operation_id="op_paste_test",
        _work_procedure_trace=[],
        _conversation_root_id=lambda: "task_paste_test",
    )

    args = {
        "ref": "@e3",
        "text": "Card Description",
        "mode": "plain_text_paste",
        "semantic_anchor": {"type": "testid", "value": "card-desc"},
    }
    raw_res = json.dumps({"status": "ok", "runtime": "electron-chromium", "semantic_effect": "paste_text"})

    record_trace(agent, "browser_type", args, raw_res)

    assert len(agent._work_procedure_trace) == 1
    trace = agent._work_procedure_trace[0]
    assert trace["execution_class"] == "semantic"
    assert trace["replayable"] is True

    steps = candidate_steps([trace])
    assert len(steps) == 1
    assert steps[0]["action"] == "type"
    assert steps[0]["target"] == "card-desc"
    assert steps[0]["anchor_type"] == "testid"


def test_browser_type_accepts_owned_artifact_text_ref(temp_artifacts, monkeypatch):
    """browser_type resolves owned artifact references into args['text'] before IPC dispatch."""
    monkeypatch.setattr("workstation.artifacts.ArtifactStore", lambda: temp_artifacts)

    large_text = "Detailed markdown report:\n" + ("- item bullet line\n" * 50)
    ref = temp_artifacts.store(
        task_id="task_123",
        name="large_description.md",
        content=large_text,
        media_type="text/markdown",
    )

    # 1. Resolve with text_ref
    args = {
        "ref": "@e1",
        "text_ref": ref.ref,
        "mode": "plain_text_paste",
    }
    resolve_browser_type_text(args, task_id="task_123")
    assert args["text"] == large_text
    assert "text_ref" not in args
    assert "artifact_ref" not in args

    # 2. Resolve with artifact_ref alias
    args2 = {
        "ref": "@e1",
        "artifact_ref": ref.ref,
        "mode": "plain_text_paste",
    }
    resolve_browser_type_text(args2, task_id="task_123")
    assert args2["text"] == large_text
    assert "artifact_ref" not in args2


def test_artifact_text_ref_rejects_cross_task_or_oversized_payload(temp_artifacts, monkeypatch):
    """Strict admission checks for artifact data plane: mutual exclusivity, cross-task isolation, size limit, and MIME."""
    monkeypatch.setattr("workstation.artifacts.ArtifactStore", lambda: temp_artifacts)

    ref_task_a = temp_artifacts.store(
        task_id="task_A",
        name="doc_a.txt",
        content="Confidential Task A Data",
        media_type="text/plain",
    )

    # 1. Mutual exclusivity: both text and text_ref provided
    with pytest.raises(ValueError, match="Mutually exclusive"):
        resolve_browser_type_text(
            {"ref": "@e1", "text": "Inline", "text_ref": ref_task_a.ref},
            task_id="task_A",
        )

    # 2. Neither provided
    with pytest.raises(ValueError, match="Missing input"):
        resolve_browser_type_text(
            {"ref": "@e1"},
            task_id="task_A",
        )

    # 3. Cross-task rejection: Task B attempting to read Task A's artifact
    with pytest.raises(ValueError, match="Cross-task artifact reference rejected"):
        resolve_browser_type_text(
            {"ref": "@e1", "text_ref": ref_task_a.ref},
            task_id="task_B",
        )

    # 4. Oversized payload rejection (> 1MB)
    ref_oversized = temp_artifacts.store(
        task_id="task_A",
        name="oversized.txt",
        content="A" * (1024 * 1024 + 50),
        media_type="text/plain",
    )
    with pytest.raises(ValueError, match="oversized"):
        resolve_browser_type_text(
            {"ref": "@e1", "text_ref": ref_oversized.ref},
            task_id="task_A",
        )

    # 5. Invalid MIME type rejection
    ref_binary = temp_artifacts.store(
        task_id="task_A",
        name="image.png",
        content=b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR",
        media_type="image/png",
    )
    with pytest.raises(ValueError, match="Invalid MIME type"):
        resolve_browser_type_text(
            {"ref": "@e1", "text_ref": ref_binary.ref},
            task_id="task_A",
        )

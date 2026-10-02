from types import SimpleNamespace
from workstation.artifacts import ArtifactStore
from workstation.experience_compiler.corpus import ExperienceCorpus
from workstation.experience_compiler.models import TransitionOutcome, Verification
from workstation.experience_compiler.progressive import capture_progressive
from workstation.integrations.hermes.tool_observer import workstation_raw_post_tool_observer
from workstation.task_compiler import execution_context


def test_post_tool_capture_during_run_is_durable_and_not_verified(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    agent = SimpleNamespace(valid_tool_names={"work_execute"}, _canonical_work_task_id="t",
        _canonical_work_run_id="r", _current_operation_id="op", session_id="s",
        _conversation_root_id=lambda: "s")
    workstation_raw_post_tool_observer("read_file", {"path": "file"}, "call", {"exists": True, "password": "never-copy", "text": "raw-document"},
        .01, {"agent": agent, "dispatched": True})
    store = ArtifactStore()
    samples = ExperienceCorpus(store, discover=True).query(task_id="t", run_id="r")
    assert len(samples) == 1 and samples[0].outcome is TransitionOutcome.OBSERVED
    assert samples[0].verification.status != "VERIFIED"
    assert "never-copy" not in samples[0].to_json() and "raw-document" not in samples[0].to_json()
    # Rehydration requires neither the agent nor its transcript.
    reconstructed = ExperienceCorpus(ArtifactStore(store.root), discover=True)
    assert reconstructed.query()[0].provenance.operation_id == "op"


def test_durable_tool_path_and_terminal_preference_preserve_counterevidence(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from workstation.task_compiler import _execution_active
    agent = SimpleNamespace(valid_tool_names={"work_execute"}, _canonical_work_task_id="t", _canonical_work_run_id="r",
        _current_operation_id="op", session_id="s", _conversation_root_id=lambda: "s")
    token = _execution_active.set(True)
    try:
        workstation_raw_post_tool_observer("write_file", {}, "c", {"error": "write failed"}, .1, {"agent": agent})
    finally:
        _execution_active.reset(token)
    store = ArtifactStore()
    capture_progressive(store, task_id="t", run_id="r", operation_id="op", primitive="write_file", route="filesystem",
        outcome="verified_success", state={"exists": True}, verification=Verification(status="VERIFIED", evidence_refs=["owner:proof"]))
    corpus = ExperienceCorpus(store, discover=True)
    assert corpus.query()[0].outcome is TransitionOutcome.VERIFIED_SUCCESS
    assert len(corpus.query(include_history=True)) == 2
    assert corpus.query(outcome="failed")[0].outcome is TransitionOutcome.FAILED

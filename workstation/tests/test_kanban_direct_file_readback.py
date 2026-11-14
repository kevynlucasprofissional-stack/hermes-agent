"""Real direct file-write evidence through observer -> readback -> canonical DONE."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from hermes_cli import kanban_db
from tools.file_tools import read_file_tool, write_file_tool
from workstation.contracts import AcceptanceContract, IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.direct_file_readback import capture_file_write_readback, verify_file_write_receipts
from workstation.integrations.hermes.completion_admission import workstation_completion_admission
from workstation.integrations.hermes.tool_observer import (
    workstation_pre_dispatch_hook, workstation_raw_post_tool_observer,
)
from workstation.kanban import WorkstationKanbanBridge


PROMPT = "Primeiro grave um arquivo de QA, depois confirme seu conteudo persistido."


def _bound_run():
    bridge = WorkstationKanbanBridge()
    session_id = "file-readback-integration"
    envelope = MessageEnvelope(MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK,
                               session_id, PROMPT, correlation_id="file-1")
    task_id = bridge.promote_request_if_multistep(
        PROMPT, session_id=session_id, envelope=envelope,
        acceptance_contract=AcceptanceContract(policy="evidence"),
    )
    assert task_id
    with bridge.get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        assert task.status == "running" and task.current_run_id is not None
        run_id = str(task.current_run_id)
    agent = SimpleNamespace(
        session_id=session_id,
        _conversation_root_id=lambda: session_id,
        _canonical_work_task_id=task_id,
        _canonical_work_run_id=run_id,
        _work_tool_observations=[],
        _work_mutation_evidence={},
        _work_mutation_shapes={},
        _work_completed_mutations={},
        _work_mutation_sem_families={},
        _work_capabilities={},
        valid_tool_names=set(),  # This path checks real post-execution evidence.
    )
    return bridge, agent, task_id, run_id


def _write(agent, path, *, content="alpha\nbeta", call_id="write-1"):
    args = {"path": str(path), "content": content}
    context = {"agent": agent, "dispatched": True}
    workstation_pre_dispatch_hook("write_file", args, call_id, context)
    raw = write_file_tool(path=str(path), content=content, task_id="default")
    assert json.loads(raw).get("verified") is True, raw
    workstation_raw_post_tool_observer("write_file", args, call_id, raw, 0.01, context)
    return args, raw


def _backend_write(agent, path, *, content, call_id):
    # Only in the multiple-write verifier unit test: invoke the exact atomic
    # storage backend; the E2E test above exercises the guarded public tool.
    from tools.file_tools import _get_file_ops
    args = {"path": str(path), "content": content}
    context = {"agent": agent, "dispatched": True}
    workstation_pre_dispatch_hook("write_file", args, call_id, context)
    raw = _get_file_ops("default").write_file(str(path), content).to_dict()
    assert raw.get("verified") is True, raw
    raw["resolved_path"] = str(path)
    workstation_raw_post_tool_observer("write_file", args, call_id, raw, 0.01, context)


def _admit(agent, task_id, run_id):
    return workstation_completion_admission(task_id, run_id, {
        "agent": agent, "session_id": agent.session_id,
        "turn_result": {"completed": True, "failed": False, "interrupted": False,
                        "final_response": "Arquivo gravado e confirmado no disco."},
    })


def test_real_file_write_produces_independent_receipt_and_canonical_done(tmp_path):
    bridge, agent, task_id, run_id = _bound_run()
    path = tmp_path / "artifact.txt"
    _write(agent, path)
    assert path.read_text(encoding="utf-8") == "alpha\nbeta"
    receipt = agent._work_tool_observations[0].get("file_readback")
    assert receipt and receipt["task_id"] == task_id and receipt["run_id"] == run_id
    assert _admit(agent, task_id, run_id).admitted is True
    with bridge.get_connection() as conn:
        task = kanban_db.get_task(conn, task_id)
        run = kanban_db.latest_run(conn, task_id)
        assert task.status == "done" and run.status == "done"
        outcome = run.metadata["workstation"]["outcome"]
        assert outcome["status"] == "verified_completed"
        assert outcome["verifier_results"][0]["verifier"] == "direct_write_file_readback"


def test_post_write_modification_fails_completion_and_does_not_rewrite(tmp_path):
    bridge, agent, task_id, run_id = _bound_run()
    path = tmp_path / "artifact.txt"
    _write(agent, path)
    path.write_text("changed by somebody else", encoding="utf-8")
    outcome = _admit(agent, task_id, run_id)
    assert outcome.admitted is False
    assert path.read_text(encoding="utf-8") == "changed by somebody else"
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, task_id).status != "done"


def test_no_receipt_is_not_a_success_and_does_not_repeat_mutation(tmp_path):
    bridge, agent, task_id, run_id = _bound_run()
    path = tmp_path / "artifact.txt"
    path.write_text("created", encoding="utf-8")
    agent._work_tool_observations.append({
        "call_id": "unverified-write", "tool": "write_file",
        "effect": "MUTATION", "status": "completed",
    })
    admission = _admit(agent, task_id, run_id)
    assert admission.admitted is False
    assert path.read_text(encoding="utf-8") == "created"
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, task_id).status != "done"


def test_failed_or_unrelated_effects_cannot_borrow_valid_file_receipt(tmp_path):
    _, agent, task_id, run_id = _bound_run()
    path = tmp_path / "artifact.txt"
    _write(agent, path)
    agent._work_tool_observations.append({
        "call_id": "external-write", "tool": "browser_click",
        "effect": "MUTATION", "status": "completed",
    })
    refs, verifiers, pending = verify_file_write_receipts(
        agent._work_tool_observations, task_id=task_id,
        session_id=agent.session_id, run_id=run_id, trace_truncated=False,
    )
    assert refs and verifiers and pending


@pytest.mark.parametrize("mismatch", ["wrong-run", "wrong-session", "failed-write"])
def test_owner_or_failed_write_receipt_rejected(tmp_path, mismatch):
    _, agent, task_id, run_id = _bound_run()
    path = tmp_path / "artifact.txt"
    args = {"path": str(path), "content": "x"}
    path.write_text("x", encoding="utf-8")
    raw = {"verified": True, "resolved_path": str(path)}
    receipt = capture_file_write_readback(
        "write_file", args, raw, task_id=task_id,
        run_id=run_id, session_id=agent.session_id, call_id="call",
    )
    assert receipt
    if mismatch == "failed-write":
        raw["verified"] = False
        assert capture_file_write_readback(
            "write_file", args, raw, task_id=task_id,
            run_id=run_id, session_id=agent.session_id, call_id="no",
        ) is None
    else:
        observed = [{"call_id": "call", "tool": "write_file",
                     "effect": "MUTATION", "status": "completed", "file_readback": receipt}]
        _, _, pending = verify_file_write_receipts(
            observed, task_id=task_id,
            session_id="incorrect" if mismatch == "wrong-session" else agent.session_id,
            run_id="incorrect" if mismatch == "wrong-run" else run_id,
            trace_truncated=False,
        )
        assert pending


def test_two_writes_to_same_file_use_last_persisted_state(tmp_path):
    bridge, agent, task_id, run_id = _bound_run()
    path = tmp_path / "artifact.txt"
    _backend_write(agent, path, content="first", call_id="write-1")
    _backend_write(agent, path, content="final", call_id="write-2")
    assert path.read_text(encoding="utf-8") == "final"
    assert _admit(agent, task_id, run_id).admitted is True
    with bridge.get_connection() as conn:
        assert kanban_db.get_task(conn, task_id).status == "done"


def test_identical_writes_have_distinct_bound_receipts(tmp_path):
    bridge, agent, task_id, run_id = _bound_run()
    path = tmp_path / "artifact.txt"
    _backend_write(agent, path, content="same", call_id="same-call-1")
    _backend_write(agent, path, content="same", call_id="same-call-2")
    refs = [row["file_readback"]["evidence_ref"] for row in agent._work_tool_observations]
    assert len(set(refs)) == 2
    assert _admit(agent, task_id, run_id).admitted is True

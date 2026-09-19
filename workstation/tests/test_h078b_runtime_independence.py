"""Test suite verifying runtime independence of Hermes Workstation kernel (H-078B).

Validates that an alternate / foreign Reasoner (not AIAgent, zero run_agent imports)
can drive the Workstation kernel through the decoupled generic lifecycle, admission,
and observation contracts without any coupling to run_agent.py.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
import pytest

from agent.turn_ingress import TurnIngress, TurnOrigin, TurnTrustClass
from agent.turn_admission import admit_turn
from agent.tool_batch_admission import (
    BatchAdmissionAction,
    admit_tool_batch,
)
from agent.scoped_execution import scoped_execution
from agent.pre_dispatch import dispatch_pre_authorized_checkpoint
from agent.post_tool import dispatch_raw_post_tool_observation
from agent.completion_admission import admit_completion
from agent.task_completion_admission import admit_task_completion
from workstation.batch_detection import call_key
from workstation.integrations.hermes.adapter import install_workstation_adapter


class AlternateReasoner:
    """A foreign / alternate reasoner completely distinct from AIAgent."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.valid_tool_names = {"read_file", "write_file", "work_execute", "browser_navigate"}
        self.operational_closure_for_call = lambda name, args: {
            "deterministic_representation": True,
            "executable_primitive": True,
            "compatible_route": True,
            "authority_policy_compatible": True,
            "verifier_readback": True,
            "certified_dispatch": True,
            "uncertainty_clear": True,
        }

    def _conversation_root_id(self) -> str:
        return self.session_id


@pytest.fixture(autouse=True)
def setup_adapter():
    install_workstation_adapter()


def test_alternate_reasoner_drives_workstation_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    import sys
    assert "run_agent" not in sys.modules

    reasoner = AlternateReasoner("alternate-session-42")

    # 1. Turn Ingress & Admission
    ingress = TurnIngress(
        origin=TurnOrigin.HUMAN,
        trust_or_authority_class=TurnTrustClass.AUTHENTICATED_USER,
        session_id=reasoner.session_id,
        content="Migrate 50 accounts to new database",
    )
    turn_ctx = SimpleNamespace(content=ingress.content)
    admit_turn(reasoner, turn_ctx, ingress=ingress)

    # Assert canonical Workstation intent and task binding established on alternate reasoner
    assert getattr(reasoner, "_message_envelope", None) is not None
    assert reasoner._message_envelope.session_id == reasoner.session_id

    # 2. Batch Admission for tool calls: benign read calls require no intervention
    batch = [
        SimpleNamespace(
            id="call_read_1",
            function=SimpleNamespace(name="read_file", arguments='{"path": "accounts.csv"}'),
        )
    ]
    batch_res = admit_tool_batch(reasoner, batch, {"task_id": "alt_task_1"})
    assert batch_res is None or all(
        d.action == BatchAdmissionAction.EXECUTE for d in batch_res.decisions
    )

    # 3. Scoped Execution & Persistence Boundary
    messages = []
    with scoped_execution(reasoner, "alt_task_1", messages):
        # Dispatch pre-authorized checkpoint
        pre_checkpoint_args = {"path": "accounts.csv"}
        dispatch_pre_authorized_checkpoint(
            "read_file",
            pre_checkpoint_args,
            "call_read_1",
            {"agent": reasoner, "task_id": "alt_task_1"},
        )

        # Execute the tool (simulated read)
        simulated_raw_result = json.dumps({"status": "ok", "rows": 50})

        # Dispatch raw post-tool observation
        dispatch_raw_post_tool_observation(
            "read_file",
            pre_checkpoint_args,
            "call_read_1",
            simulated_raw_result,
            0.05,
            {"agent": reasoner, "task_id": "alt_task_1", "dispatched": True},
        )

        messages.append({
            "role": "tool",
            "name": "read_file",
            "tool_call_id": "call_read_1",
            "content": simulated_raw_result,
        })

    # Operational references envelope preserved
    assert len(messages) == 1

    # 4. Completion Admission
    completion_decision = admit_completion(
        "alt_task_1",
        "run_1",
        {"session_id": reasoner.session_id, "last_tool_result": simulated_raw_result},
    )
    assert completion_decision is not None
    assert completion_decision.admitted is True

    # 5. Task Completion Admission
    from unittest.mock import MagicMock
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = [json.dumps({"policy": "advisory"})]
    ws_completion_payload = {
        "acceptance_approved": True,
        "outcome": {
            "task_id": "alt_task_1",
            "session_id": reasoner.session_id,
            "status": "verified_completed",
            "objective": "Migrate accounts",
            "summary": "50 accounts migrated successfully",
        },
    }
    task_completion_decision = admit_task_completion(
        mock_conn,
        "alt_task_1",
        ws_completion_payload,
        owned=None,
        hybrid_owned=False,
    )
    assert task_completion_decision is True
    assert "run_agent" not in sys.modules


def test_alternate_reasoner_blocks_uncertain_mutation(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    reasoner = AlternateReasoner("alternate-session-uncertain")

    # Ingress with human authority
    ingress = TurnIngress(
        origin=TurnOrigin.HUMAN,
        trust_or_authority_class=TurnTrustClass.AUTHENTICATED_USER,
        session_id=reasoner.session_id,
        content="Update configuration",
    )
    turn_ctx = SimpleNamespace(content=ingress.content)
    admit_turn(reasoner, turn_ctx, ingress=ingress)

    # Inject uncertain mutation evidence using canonical call_key
    args = {"path": "data.txt", "content": "updated"}
    key = call_key("write_file", args)
    reasoner._work_mutation_evidence = {
        key: {"status": "uncertain"}
    }

    batch = [
        SimpleNamespace(
            id="call_write_1",
            function=SimpleNamespace(name="write_file", arguments=json.dumps(args)),
        )
    ]
    batch_res = admit_tool_batch(reasoner, batch, {"task_id": "alt_task_uncertain"})
    assert batch_res is not None
    assert len(batch_res.decisions) == 1
    assert batch_res.decisions[0].action == BatchAdmissionAction.HANDOFF


def test_alternate_reasoner_triggers_progressive_compilation(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    reasoner = AlternateReasoner("alternate-session-compile")

    # Repetitive homogeneous mutations with proven operational closure
    batch = [
        SimpleNamespace(
            id=f"call_write_{i}",
            function=SimpleNamespace(
                name="write_file",
                arguments=json.dumps({"path": f"item_{i}.txt", "content": f"data_{i}", "target_family": "item_record"}),
            ),
        )
        for i in range(3)
    ]
    batch_res = admit_tool_batch(reasoner, batch, {"task_id": "alt_task_compile"})
    assert batch_res is not None
    assert any(d.action == BatchAdmissionAction.SYNTHETIC_RESULT for d in batch_res.decisions)
    assert any(d.reason == "require_compile" for d in batch_res.decisions)

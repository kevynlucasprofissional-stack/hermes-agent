"""Tests for workstation.milestones contract, evidence sanitizer, and emitter."""
import pytest
from unittest.mock import MagicMock

from workstation.milestones import (
    VALID_STAGES,
    WorkstationMilestone,
    emit_workstation_milestone,
    sanitize_evidence_ref,
)


def test_valid_stages_frozenset():
    expected = {
        "observed",
        "candidate",
        "compilation_started",
        "validation_passed",
        "validation_failed",
        "capability_selected",
        "executed",
        "rejected",
    }
    assert VALID_STAGES == expected


def test_sanitize_evidence_ref_redacts_secrets_and_pii():
    # Token / password redaction
    assert sanitize_evidence_ref("https://api.example.com?token=supersecret123") == "https://api.example.com?<redacted_secret>"
    assert sanitize_evidence_ref("auth:bearer:abcxyz987") == "<redacted_secret>"
    assert sanitize_evidence_ref("password=mypassword,user=admin") == "<redacted_secret>,user=admin"

    # Email redaction
    assert sanitize_evidence_ref("user:operator@company.com:session") == "user:<redacted_email>:session"

    # Clean refs stay intact
    assert sanitize_evidence_ref("lesson:lesson_hd_12345") == "lesson:lesson_hd_12345"
    assert sanitize_evidence_ref("events:events.jsonl") == "events:events.jsonl"
    assert sanitize_evidence_ref("readback:hash_abcdef1234") == "readback:hash_abcdef1234"

    # Overly long text is truncated
    long_ref = "evidence:" + "a" * 250
    sanitized = sanitize_evidence_ref(long_ref)
    assert len(sanitized) <= 200
    assert sanitized.endswith("...")


def test_emit_workstation_milestone_valid():
    ms = emit_workstation_milestone(
        stage="candidate",
        sessionId="sess_test_1",
        taskRunId="tr_42",
        learningSessionId="learn_1",
        capabilityId="photocraft.layer_crop",
        reasonCode="demonstration_segmented",
        evidenceRefs=["lesson:lesson_hd_1", "https://api?token=secret"],
    )

    assert isinstance(ms, WorkstationMilestone)
    assert ms.stage == "candidate"
    assert ms.sessionId == "sess_test_1"
    assert ms.taskRunId == "tr_42"
    assert ms.learningSessionId == "learn_1"
    assert ms.capabilityId == "photocraft.layer_crop"
    assert ms.reasonCode == "demonstration_segmented"
    assert ms.evidenceRefs == ["lesson:lesson_hd_1", "https://api?<redacted_secret>"]

    d = ms.to_dict()
    assert d["stage"] == "candidate"
    assert d["sessionId"] == "sess_test_1"
    assert d["evidenceRefs"] == ["lesson:lesson_hd_1", "https://api?<redacted_secret>"]


def test_emit_workstation_milestone_invalid_stage_raises():
    with pytest.raises(ValueError, match="Invalid WorkstationMilestone stage"):
        emit_workstation_milestone(
            stage="invalid_stage_xyz",  # type: ignore[arg-type]
            sessionId="sess_1",
        )


def test_emit_routes_to_desktop_ui_and_agent(monkeypatch):
    mock_emit = MagicMock()
    from tools import desktop_ui
    monkeypatch.setattr(desktop_ui, "_emit", mock_emit)

    mock_agent = MagicMock()
    mock_agent.emit_gateway_event = MagicMock()

    ms = emit_workstation_milestone(
        stage="validation_passed",
        sessionId="sess_123",
        capabilityId="test_cap",
        evidenceRefs=["evidence:canary_pass.json"],
        agent=mock_agent,
    )
    assert ms.stage == "validation_passed"

    # desktop_ui._emit called with (sid, 'workstation.milestone', payload)
    mock_emit.assert_called_once()
    args, _ = mock_emit.call_args
    assert args[0] == "sess_123"
    assert args[1] == "workstation.milestone"
    assert args[2]["stage"] == "validation_passed"
    assert args[2]["capabilityId"] == "test_cap"

    # agent.emit_gateway_event called with ('workstation.milestone', payload)
    mock_agent.emit_gateway_event.assert_called_once()
    a_args, _ = mock_agent.emit_gateway_event.call_args
    assert a_args[0] == "workstation.milestone"
    assert a_args[1]["stage"] == "validation_passed"


def test_record_helpers(monkeypatch):
    from workstation.milestones import (
        record_readback_milestone,
        record_router_rejection,
        record_router_selection,
        record_validation_milestone,
    )
    mock_emit = MagicMock()
    from tools import desktop_ui
    monkeypatch.setattr(desktop_ui, "_emit", mock_emit)

    # 1. Router selection
    mock_cap = MagicMock(id="cap_1")
    mock_cert = MagicMock(certificate_hash=lambda: "abcdef123456")
    record_router_selection(mock_cap, mock_cert, {"session_id": "s_1"}, "tr_1")
    assert mock_emit.call_count == 1
    assert mock_emit.call_args[0][2]["stage"] == "capability_selected"

    # 2. Router rejection
    mock_emit.reset_mock()
    record_router_rejection([(mock_cap, "READ")], {"session_id": "s_1"}, "tr_1")
    assert mock_emit.call_count == 1
    assert mock_emit.call_args[0][2]["stage"] == "rejected"

    # 3. Validation milestone
    mock_emit.reset_mock()
    record_validation_milestone(mock_cap, True, [{"evidence_ref": "ev_1"}], "s_1", "tr_1")
    assert mock_emit.call_count == 1
    assert mock_emit.call_args[0][2]["stage"] == "validation_passed"

    # 4. Readback milestone (executed)
    mock_emit.reset_mock()
    mock_agent = MagicMock(session_id="s_1", _canonical_work_run_id="tr_1")
    mock_item = MagicMock(task_id="t_1")
    record_readback_milestone(mock_agent, mock_item, "write_file", {"ok": True, "evidence_ref": "ref_1"})
    assert mock_emit.call_count == 1
    assert mock_emit.call_args[0][2]["stage"] == "executed"


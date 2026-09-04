import tempfile
from pathlib import Path
from workstation.contracts import RiskLevel
from workstation.drift import AdaptationAction, DriftGovernor, DriftSeverity
from workstation.journal import ExecutionJournal
from workstation.perception import PerceptionEngine
from workstation.safety import SafetyDecision


def test_drift_diagnosis_exact_match():
    engine = PerceptionEngine()
    view = engine.summarize({
        "children": [
            {"ref": "btn-1", "role": "button", "name": "Submit Order"},
        ]
    })
    governor = DriftGovernor()
    diag = governor.diagnose(expected_action="click", expected_target="btn-1", perception=view, expected_text="Submit Order")
    assert diag.severity == DriftSeverity.NONE
    assert diag.suggested_action == AdaptationAction.PROCEED


def test_drift_diagnosis_benign_label_shift():
    engine = PerceptionEngine()
    view = engine.summarize({
        "children": [
            {"ref": "btn-1", "role": "button", "name": "Confirm & Submit"},
        ]
    })
    governor = DriftGovernor()
    diag = governor.diagnose(expected_action="click", expected_target="btn-1", perception=view, expected_text="Submit Order")
    assert diag.severity == DriftSeverity.BENIGN
    assert diag.suggested_action == AdaptationAction.PROCEED


def test_drift_diagnosis_structural_adapted_target():
    engine = PerceptionEngine()
    view = engine.summarize({
        "children": [
            {"ref": "btn-new-99", "role": "button", "name": "Proceed to Checkout"},
        ]
    })
    governor = DriftGovernor()
    diag = governor.diagnose(expected_action="click", expected_target="old-btn-id", perception=view, expected_text="Checkout")
    assert diag.severity == DriftSeverity.STRUCTURAL
    assert diag.actual_target == "btn-new-99"
    assert diag.suggested_action == AdaptationAction.RETRY_WITH_ADAPTED_TARGET

    action = governor.govern(diag, action="click")
    assert action == AdaptationAction.RETRY_WITH_ADAPTED_TARGET


def test_drift_breaking_page_requires_approval():
    engine = PerceptionEngine()
    view = engine.summarize({
        "children": [
            {"role": "text", "text": "Cloudflare security check: Please verify you are human to continue"},
        ]
    })
    governor = DriftGovernor()
    diag = governor.diagnose(expected_action="click", expected_target="btn-1", perception=view, expected_text="Next")
    assert diag.severity == DriftSeverity.BREAKING
    assert diag.suggested_action == AdaptationAction.REQUIRE_APPROVAL

    action = governor.govern(diag, action="click")
    assert action == AdaptationAction.REQUIRE_APPROVAL


def test_drift_governance_safety_boundary():
    governor = DriftGovernor()
    # Even if structural drift has high confidence, sensitive high-risk action requires human approval
    engine = PerceptionEngine()
    view = engine.summarize({
        "children": [{"ref": "pay-now", "role": "button", "name": "Complete Purchase"}]
    })
    diag = governor.diagnose("click", "old-pay-btn", view, "Purchase")
    assert diag.severity == DriftSeverity.STRUCTURAL

    decision = SafetyDecision("pay", RiskLevel.HIGH, True, "Approval required for purchase")
    action = governor.govern(diag, action="pay", safety_decision=decision)
    assert action == AdaptationAction.REQUIRE_APPROVAL


def test_drift_recording_to_journal():
    with tempfile.TemporaryDirectory() as tmpdir:
        journal_file = Path(tmpdir) / "journal.jsonl"
        journal = ExecutionJournal("t-drift", "s-1", file_path=journal_file)

        governor = DriftGovernor()
        engine = PerceptionEngine()
        view = engine.summarize({"children": [{"ref": "2", "role": "button", "name": "OK"}]})
        diag = governor.diagnose("click", "1", view, "Confirm")

        event = governor.record_drift(diag, journal, task_id="t-drift", session_id="s-1")
        assert "Drift [structural]" in event.message
        assert len(journal.read_events()) == 1


def test_drift_detects_blocking_cookie_overlay():
    # H-104 Red Team verification: Cookie / privacy consent modal blocking the target
    engine = PerceptionEngine()
    view = engine.summarize({
        "children": [
            {"role": "text", "text": "We value your privacy. This site uses cookies to ensure optimal experience."},
            {"ref": "cookie-accept-btn", "role": "button", "name": "Accept All Cookies"},
            {"ref": "some-other-link", "role": "link", "name": "Learn more"},
        ]
    })

    governor = DriftGovernor()
    diag = governor.diagnose(
        expected_action="click",
        expected_target="non-existent-nav-target",
        perception=view,
        expected_text="Dashboard",
    )
    assert diag.suggested_action == AdaptationAction.DISMISS_OVERLAY
    assert diag.actual_target == "cookie-accept-btn"

    # Governance permits dismissing overlay to unblock interaction
    action = governor.govern(diag, action="click")
    assert action == AdaptationAction.DISMISS_OVERLAY


def test_expanded_financial_safety_boundaries():
    from workstation.safety import classify_action
    # Financial and destructive actions must always require approval
    for sensitive_action in [
        "checkout",
        "placeOrder",
        "wire_transfer",
        "subscribe",
        "delete_account",
        "grant_admin",
    ]:
        decision = classify_action(sensitive_action)
        assert decision.approval_required is True, f"{sensitive_action} must require approval"


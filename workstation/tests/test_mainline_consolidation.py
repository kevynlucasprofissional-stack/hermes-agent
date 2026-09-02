from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTEXT = ROOT / "workstation" / "context"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_mainline_gate_has_a_complete_disposition_ledger() -> None:
    gate = read("workstation/context/MAINLINE_CONSOLIDATION.md")

    assert "## Gate result" in gate
    assert "**PASS**" in gate
    assert "material `NEEDS INVESTIGATION`: **0**" in gate

    for pr_number in range(1, 13):
        assert f"#{pr_number}" in gate

    for branch in (
        "bot/js-autofix",
        "diagnostic/impl2-ui-platform-baseline",
        "diagnostic/impl2-ui-platform-candidate",
        "docs/impl4-promotion-closure",
        "feat/workstation-integrated-mvp-dogfood",
        "fix/workstation-bootstrap-installer",
        "impl3/workstation-browser-capability",
        "impl4-browser-task-lifecycle",
        "noop",
        "validation/impl2-canonical-source",
        "validation/impl3-browser-session-capability",
        "validation/impl3-final",
        "validation/impl3-focused-final",
        "workstation/browser-session-state-stabilize",
        "workstation-validation",
        "wp/codex/browser-session-state-core",
    ):
        assert f"`{branch}`" in gate

    for disposition in (
        "ALREADY ON MAIN",
        "HISTORICAL EVIDENCE ONLY",
        "SUPERSEDED",
        "CLOSE PR",
        "REJECTED/DO NOT PROMOTE",
    ):
        assert disposition in gate


def test_gate_is_canonical_and_precedes_integrated_mvp() -> None:
    index = read("workstation/context/README.md")
    decisions = read("workstation/context/DECISIONS.md")
    roadmap = read("workstation/ROADMAP.md")

    assert (CONTEXT / "MAINLINE_CONSOLIDATION.md").is_file()
    assert "MAINLINE_CONSOLIDATION.md" in index
    assert "D-012" in decisions
    assert "Mainline Consolidation Review" in decisions

    browser_state = roadmap.index("## V1 #1 — BrowserSessionState")
    gate = roadmap.index("## Mainline Consolidation Gate")
    integrated_mvp = roadmap.index("### 1.5. Integrated Dogfood MVP")
    hardening = roadmap.index("2. Build the contextual Chat Browser View")
    assert browser_state < gate < integrated_mvp < hardening


def test_promoted_browser_session_state_is_not_described_as_pending() -> None:
    current = read("workstation/context/CURRENT_STATE.md")
    delta = read("workstation/UPSTREAM_DELTA.md")

    assert "H010_CLASSIFICATION=VALIDATED" in current
    assert "e0a99ef3aba6e6d2b65c30cf3c908ee1d49c4d29" in current
    assert "HW-013 is validated and promoted" in delta

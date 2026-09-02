from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTEXT_ROOT = REPO_ROOT / "workstation" / "context"


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_workstation_context_is_reachable_from_repo_agent_guide():
    guide = _text(REPO_ROOT / "AGENTS.md")
    assert "workstation/context/README.md" in guide


def test_context_read_order_reaches_canonical_workstation_documents():
    index = _text(CONTEXT_ROOT / "README.md")

    required_context = {
        "CURRENT_STATE.md",
        "DECISIONS.md",
        "CONSTRAINTS.md",
        "MAINLINE_CONSOLIDATION.md",
        "TESTING.md",
        "KNOWN_ISSUES.md",
    }
    required_canonical = {
        "ARCHITECTURE.md",
        "ROADMAP.md",
        "SOURCE_MATRIX.md",
        "UPSTREAM.md",
        "UPSTREAM_DELTA.md",
        "PATCH_MANIFEST.md",
    }

    for name in required_context:
        assert (CONTEXT_ROOT / name).is_file(), name
        assert name in index, name

    for name in required_canonical:
        assert (REPO_ROOT / "workstation" / name).is_file(), name
        assert name in index, name


def test_decisions_encode_workstation_state_ownership_boundaries():
    decisions = _text(CONTEXT_ROOT / "DECISIONS.md")

    for invariant in (
        "BrowserTask",
        "WebContentsView",
        "BrowserSessionState",
        "Browser Hub",
        "SessionDB",
        "BrowserRuntime",
    ):
        assert invariant in decisions, invariant

    normalized = decisions.lower().replace("-", " ")
    assert "fail closed" in normalized


def test_context_separates_current_state_from_target_and_known_issues():
    current = _text(CONTEXT_ROOT / "CURRENT_STATE.md")
    issues = _text(CONTEXT_ROOT / "KNOWN_ISSUES.md")

    assert "## Working now" in current
    assert "## Partially implemented" in current
    assert "## Not implemented yet" in current
    assert "## Manual validation already observed" in current
    assert "## Latest automated validation state" in current
    assert "Causality status" in issues

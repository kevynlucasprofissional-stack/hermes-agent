import pytest
from workstation.artifacts import ArtifactStore
from workstation.experience_compiler.corpus import ExperienceCorpus
from workstation.experience_compiler.models import (
    CausalGrade,
    TransitionOutcome,
    TransitionSample,
)
from workstation.experience_compiler.opportunity_audit import (
    OPPORTUNITY_AUDIT_SCHEMA,
    import_historical_conversation_markdown,
    generate_compilability_opportunity_audit,
)


def test_import_historical_conversation_markdown_creates_held_unverified_transitions(tmp_path):
    artifacts = ArtifactStore(tmp_path / "artifacts")
    corpus = ExperienceCorpus(artifacts, discover=False)

    sample_md = """# Dogfood Run 2026-09-22
User asked: "Crie um card no Trello para onboarding"
Agent executed:
1. Navegou para https://trello.com/b/board1
2. Clicou em "Adicionar cartão"
3. Digitou título "Onboarding Novo Membro"
Resultado reportado: Cartão criado com sucesso.
"""
    result = import_historical_conversation_markdown(
        sample_md,
        source_path="dogfood/2026-09-22-test.md",
        corpus=corpus,
        artifacts=artifacts,
    )

    assert result["imported_count"] >= 1
    assert result["provenance_source"] == "dogfood/2026-09-22-test.md"
    # Unverified narrative markdown must never enter corpus as VERIFIED_SUCCESS
    samples = corpus.query()
    assert len(samples) >= 1
    assert all(s.outcome != TransitionOutcome.VERIFIED_SUCCESS for s in samples)
    assert all(s.causal_grade == CausalGrade.OBSERVED_ONCE for s in samples)


def test_import_historical_conversation_links_with_existing_receipts(tmp_path):
    artifacts = ArtifactStore(tmp_path / "artifacts")
    corpus = ExperienceCorpus(artifacts, discover=False)

    # Store a real execution receipt
    receipt_ref = artifacts.store("task-retro-1", "receipt_nav.json", {
        "action": "browser_navigate",
        "url": "https://trello.com/b/board1",
        "runtime": "electron-chromium",
        "success": True,
    }).ref

    sample_md = f"""# Verified Run
Agent navigated with receipt: {receipt_ref}
Completed step successfully.
"""
    result = import_historical_conversation_markdown(
        sample_md,
        source_path="dogfood/verified_run.md",
        corpus=corpus,
        artifacts=artifacts,
    )

    assert result["imported_count"] >= 1
    assert result["linked_receipt_count"] >= 1
    samples = corpus.query()
    linked = [s for s in samples if s.verification and s.verification.evidence_refs]
    assert len(linked) >= 1
    assert linked[0].outcome == TransitionOutcome.VERIFIED_SUCCESS


def test_generate_compilability_opportunity_audit_produces_v1_schema(tmp_path):
    artifacts = ArtifactStore(tmp_path / "artifacts")
    corpus = ExperienceCorpus(artifacts, discover=False)

    benchmark_cases = [
        {
            "case_id": "case_trello_card",
            "name": "Create Trello card",
            "verified_in_corpus": True,
            "validated": True,
            "promoted": True,
            "run_local_reused": True,
        },
        {
            "case_id": "case_chatgpt_prompt",
            "name": "Open ChatGPT and prompt",
            "verified_in_corpus": False,
            "validated": False,
            "promoted": False,
            "run_local_reused": False,
            "reasons": ["unverified_narrative_markdown"],
        },
        {
            "case_id": "case_unrepeatable_random",
            "name": "Random search test",
            "verified_in_corpus": False,
            "validated": False,
            "promoted": False,
            "run_local_reused": False,
            "is_true_negative": True,
            "reasons": ["non_deterministic_input"],
        },
    ]

    audit = generate_compilability_opportunity_audit(
        benchmark_cases,
        corpus=corpus,
        artifacts=artifacts,
    )

    assert audit["schema"] == OPPORTUNITY_AUDIT_SCHEMA
    assert audit["denominator"] == 3

    counts = audit["counts"]
    assert counts["eligible"] >= 1
    assert counts["detected"] >= 1
    assert counts["promoted"] == 1
    assert counts["run_local_reused"] == 1
    assert counts["held"] >= 1
    assert counts["true_negative"] == 1
    assert "missed" in counts
    assert "unknown" in counts

    stored_ref = audit.get("audit_artifact_ref")
    assert stored_ref and stored_ref.startswith("artifact://tasks/")

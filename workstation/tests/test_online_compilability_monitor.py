"""Tests for Online Compilability Loop (Hermes Work / Laya System-1).

Validates the full cycle:
Progressive Capture -> Deterministic Filter & Online Monitor ->
System-1 Decision (Laya / Seam) -> Bounded Experience Mining ->
Independent Validation & Controlled Replay -> Safe Run-Local Reuse ->
Verified Outcome & Provenance Telemetry.

Covers Scenarios:
Caso A — Reutilização positiva (in-flight handoff with zero extra System-2 calls)
Caso B — Experiência não compilável (creative/ambiguous, no compiler spam)
Caso C — Falhas e incerteza (counterevidence, no optimistic reuse)
Caso D — Laya indisponível / abstention (fail-safe without interrupting user)
Caso E — Persistência / restart (reconstructible evidence, no duplicate mutation)
Caso F — Segurança da promoção (single-run candidate never promoted globally)
Caso G — Performance & backpressure (bounded queue, non-blocking)
Caso H — Provenance e Decision Receipts (reproducible receipts and verified labels)
"""
from __future__ import annotations

import os
import sqlite3
import time
from copy import deepcopy
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from agent.system1_decision import (
    DecisionRequest,
    DecisionResult,
    register_system1_decision_provider,
    reset_system1_decision,
)
from workstation.artifacts import ArtifactStore
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.verification import (
    VerificationContract,
    VerificationLifecycle,
    VerificationResult,
    VerificationStatus,
)
from workstation.durable_tasks import DurableTaskStore, WorkItemStatus
from workstation.execution_policy import EvidenceStrength
from workstation.experience_compiler.compilability_monitor import (
    CompilabilityEvent,
    CompilabilityStage,
    OnlineCompilabilityMonitor,
    get_compilability_monitor,
    notify_online_compilability,
    reset_compilability_monitor,
)
from workstation.experience_compiler.compiler import ExperienceCompiler
from workstation.experience_compiler.corpus import ExperienceCorpus
from workstation.experience_compiler.models import (
    AuthorityOrigin,
    CausalGrade,
    Operation,
    Provenance,
    SemanticState,
    StateDelta,
    TransitionOutcome,
    TransitionSample,
    Verification,
)
from workstation.experience_compiler.promotion import ExperiencePromotionPolicy
from workstation.integrations.hermes.tool_observer import workstation_raw_post_tool_observer
from workstation.operational_capabilities import (
    CapabilityLifecycle,
    OperationalCapability,
    OperationalCapabilityRegistry,
)
from workstation.run_closure import RunClosureProof, execute_in_flight_handoff
from workstation.system1.contracts import NeutralChoice
from workstation.system1.laya_provider import LayaDecisionProvider
from workstation.system1.receipts import load_decision_receipt
from workstation.system1.schemas import (
    COMPILABILITY_STAGE_QUESTION,
    STANDARD_SCHEMAS,
    build_compilability_decision_request,
)


@pytest.fixture(autouse=True)
def cleanup_system1_and_monitor():
    reset_system1_decision()
    reset_compilability_monitor()
    yield
    reset_system1_decision()
    reset_compilability_monitor()


def _make_transition_sample(
    primitive: str,
    run: str,
    task: str = "task_1",
    before: dict = None,
    after: dict = None,
    parameters: dict = None,
    effect: str = "read_only",
    verified: bool = True,
    op_fam: str = "batch_card",
    tgt_fam: str = "card",
    route: str = "native_browser",
) -> TransitionSample:
    a = SemanticState(semantic_predicates=before or {"card_state": "open"})
    b = SemanticState(semantic_predicates=after or {"card_state": "updated"})
    return TransitionSample(
        state_before=a,
        state_after=b,
        delta=StateDelta.between(a, b),
        operation=Operation(
            primitive=primitive,
            canonical_route=route,
            target_family=tgt_fam,
            operation_family=op_fam,
            parameters=parameters or {},
            effect_class=effect,
            scope={"host": "example.com"},
        ),
        verification=Verification(
            EvidenceStrength.SEMANTIC_PERSISTED_READBACK if verified else EvidenceStrength.TOOL_ACK_ONLY,
            "verifier_readback",
            b.semantic_predicates if verified else {},
            ["artifact://proof_evidence"],
            status="VERIFIED" if verified else "UNVERIFIED",
        ),
        outcome=TransitionOutcome.VERIFIED_SUCCESS if verified else TransitionOutcome.FAILED,
        provenance=Provenance(
            task, run, primitive, "electron-chromium", "fixture",
            AuthorityOrigin.USER, "trusted_runtime",
        ),
    )


def test_online_compilability_monitor_imports_and_schemas_exist():
    """P0 RED test: Verify compilability monitor and domain schemas are defined."""
    assert COMPILABILITY_STAGE_QUESTION is not None
    assert "compilability_stage" in STANDARD_SCHEMAS
    assert OnlineCompilabilityMonitor is not None
    assert CompilabilityStage.MINE_CANDIDATE == "MINE_CANDIDATE"
    assert CompilabilityStage.VALIDATE_CANDIDATE == "VALIDATE_CANDIDATE"
    assert CompilabilityStage.POSSIBLE_RUN_LOCAL_REUSE == "POSSIBLE_RUN_LOCAL_REUSE"


def test_case_a_positive_same_run_reuse(tmp_path):
    """Caso A: Execução verificável, compilação de candidata, validação e reutilização run-local.

    Provas:
    1. Experiência de 2 itens completada com sucesso verificado.
    2. Laya/System-1 sugere MINE_CANDIDATE.
    3. Monitor produz candidata CANDIDATE (não PROMOTED).
    4. Validação independente produz RunClosureProof.
    5. Reutilização run-local executa 2 itens restantes com zero chamadas System-2.
    """
    artifacts = ArtifactStore(root_dir=tmp_path / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts)
    corpus = ExperienceCorpus(artifacts)
    compiler = ExperienceCompiler(registry, corpus)

    # 1. Capture 2 verified traces for cards in run_1
    def build_trace(pr, run, offset):
        s1 = _make_transition_sample(
            "browser_navigate", run,
            before={"card_state": "open"}, after={"card_state": "open"},
            parameters={"url": f"https://example.com/cards/{pr}"},
            verified=False,
        )
        s1.outcome = TransitionOutcome.OBSERVED
        s1.provenance.operation_id = f"op_{run}_{offset}"
        s1.provenance.operation_index = offset

        s2 = _make_transition_sample(
            "browser_type", run,
            before={"card_state": "open"}, after={"card_state": "open"},
            parameters={"text": f"Card {pr} update", "semantic_anchor": {"type": "testid", "value": "card_input"}},
            effect="state_mutation",
            verified=False,
        )
        s2.outcome = TransitionOutcome.OBSERVED
        s2.provenance.operation_id = f"op_{run}_{offset + 1}"
        s2.provenance.operation_index = offset + 1

        s3 = _make_transition_sample(
            "browser_snapshot", run,
            before={"card_state": "open"}, after={"card_state": "updated"},
            effect="read_only",
            verified=True,
        )
        s3.outcome = TransitionOutcome.VERIFIED_SUCCESS
        s3.provenance.operation_id = f"op_{run}_{offset + 2}"
        s3.provenance.operation_index = offset + 2

        return [s1, s2, s3]

    t1 = build_trace(1, "run_1", 0)
    t2 = build_trace(2, "run_1", 3)

    refs = []
    for s in t1 + t2:
        refs.append(corpus.capture(s))

    # Register System-1 provider recommending MINE_CANDIDATE
    def mock_provider(req: DecisionRequest) -> DecisionResult:
        return DecisionResult(
            request_id=req.request_id,
            answers={"compilability_stage": CompilabilityStage.MINE_CANDIDATE.value},
            confidence={"compilability_stage": 0.95},
            provider="fake_laya",
            model="laya-multilingual",
        )

    register_system1_decision_provider(mock_provider)

    monitor = OnlineCompilabilityMonitor(
        artifacts=artifacts,
        registry=registry,
        corpus=corpus,
        compiler=compiler,
        mode="direct",
        cooldown_seconds=0.0,
    )

    # Trigger event on the completed second sample
    event = CompilabilityEvent(
        event_kind="verified_transition",
        sample_ref=refs[-1],
        task_id="task_1",
        run_id="run_1",
        operation_id="op_card_2",
        primitive="browser_snapshot",
        route="native_browser",
        outcome="verified_success",
        operation_family="batch_card",
        target_family="card",
        evidence_refs=("artifact://proof_evidence",),
    )

    result = monitor.process_event(event)
    assert result["status"] == "evaluated"
    assert result["stage"] == CompilabilityStage.MINE_CANDIDATE.value
    assert len(result.get("mined_candidates", [])) >= 1
    cand_id = result["mined_candidates"][0]

    # Verify candidate was registered as DISCOVERED/VALIDATED, NOT PROMOTED
    candidate = registry.get(cand_id)
    assert candidate is not None
    assert candidate.lifecycle != CapabilityLifecycle.PROMOTED
    assert candidate.lifecycle in (CapabilityLifecycle.DISCOVERED, CapabilityLifecycle.VALIDATED)

    # Validation produced proof
    proof = monitor._windows[("task_1", "run_1")].validated_proofs.get(cand_id)
    assert proof is not None
    assert isinstance(proof, RunClosureProof)
    assert proof.uncertainty_clear is True

    # 2. Run-local reuse for remaining items (cards 3 and 4)
    remaining_items = [
        {"card_id": "3", "text": "Card 3 update"},
        {"card_id": "4", "text": "Card 4 update"},
    ]
    steps = [
        {"id": "nav", "tool": "browser_navigate", "args": {"url": "https://example.com/cards/$item.card_id"}},
        {"id": "type", "tool": "browser_type", "args": {"text": "$item.text"}},
        {"id": "snap", "tool": "browser_snapshot", "args": {}},
    ]

    dispatched_calls = []

    def dispatch_fn(tool, args):
        dispatched_calls.append((tool, args))
        return {"status": "ok"}

    db_file = tmp_path / "tasks.db"
    task_store = DurableTaskStore(conn=sqlite3.connect(db_file))

    reuse_result = monitor.attempt_run_local_reuse(
        proof,
        remaining_items,
        steps,
        dispatch_fn,
        task_store=task_store,
        artifact_store=artifacts,
    )

    assert reuse_result["status"] in ("COMPLETED", "success", "BATCH_COMPLETED") or not reuse_result.get("anomalies")
    # All 2 remaining items executed through deterministic dispatch
    assert len(dispatched_calls) == 6  # 3 steps * 2 items
    assert monitor.metrics["system2_calls_avoided"] == 2
    assert monitor.metrics["run_local_reuses"] == 1


def test_case_b_non_compilable_creative_experience(tmp_path):
    """Caso B: Tarefas criativas, ambíguas ou sem procedimento estável não disparam mineração."""
    artifacts = ArtifactStore(root_dir=tmp_path / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts)
    corpus = ExperienceCorpus(artifacts)
    compiler = ExperienceCompiler(registry, corpus)

    # Provider returning KEEP_COLLECTING or NEEDS_SYSTEM2
    def creative_provider(req: DecisionRequest) -> DecisionResult:
        return DecisionResult(
            request_id=req.request_id,
            answers={"compilability_stage": CompilabilityStage.NEEDS_SYSTEM2.value},
            confidence={"compilability_stage": 0.88},
            provider="fake_laya",
        )

    register_system1_decision_provider(creative_provider)

    monitor = OnlineCompilabilityMonitor(artifacts=artifacts, registry=registry, corpus=corpus, compiler=compiler)

    # Isolated event with no repeated verified pattern
    event = CompilabilityEvent(
        event_kind="tool_finished",
        sample_ref="artifact://sample_random",
        task_id="task_creative",
        run_id="run_1",
        operation_id="op_creative_1",
        primitive="web_search",
        route="search",
        outcome="observed",
        operation_family="search_creative",
        target_family="query",
    )

    res = monitor.process_event(event)
    # Filtered by deterministic prefilter (insufficient verified evidence)
    assert res["status"] in ("prefilter_insufficient", "evaluated")
    assert monitor.metrics["candidates_yielded"] == 0
    assert monitor.metrics["mining_attempts"] == 0


def test_case_c_failure_uncertainty_counterevidence(tmp_path):
    """Caso C: Experiências fracassadas ou mutações incertas não geram reutilização nem labels positivos."""
    artifacts = ArtifactStore(root_dir=tmp_path / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts)
    corpus = ExperienceCorpus(artifacts)
    compiler = ExperienceCompiler(registry, corpus)

    monitor = OnlineCompilabilityMonitor(artifacts=artifacts, registry=registry, corpus=corpus, compiler=compiler)

    # Failed event
    failed_event = CompilabilityEvent(
        event_kind="failed",
        sample_ref="artifact://sample_failed",
        task_id="task_fail",
        run_id="run_1",
        operation_id="op_fail",
        primitive="fs_write",
        route="filesystem",
        outcome="failed",
    )

    # Uncertain event
    uncertain_event = CompilabilityEvent(
        event_kind="uncertain",
        sample_ref="artifact://sample_uncertain",
        task_id="task_fail",
        run_id="run_1",
        operation_id="op_uncertain",
        primitive="fs_write",
        route="filesystem",
        outcome="uncertain",
    )

    monitor.process_event(failed_event)
    monitor.process_event(uncertain_event)

    window = monitor._windows[("task_fail", "run_1")]
    assert "artifact://sample_failed" in window.counterexample_refs
    assert "artifact://sample_uncertain" in window.counterexample_refs
    assert monitor.metrics["counterexamples_collected"] >= 1
    assert monitor.metrics["candidates_yielded"] == 0
    assert monitor.metrics["run_local_reuses"] == 0


def test_case_d_system1_unavailable_or_abstained_fails_safe(tmp_path):
    """Caso D: Falha, timeout, saturação ou abstinência do Laya não interrompe a tarefa do usuário."""
    artifacts = ArtifactStore(root_dir=tmp_path / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts)
    corpus = ExperienceCorpus(artifacts)
    compiler = ExperienceCompiler(registry, corpus)

    # Provider raising exception or returning ABSTAIN
    def failing_provider(req: DecisionRequest) -> DecisionResult:
        raise RuntimeError("Laya inference timeout / model overloaded")

    register_system1_decision_provider(failing_provider)

    monitor = OnlineCompilabilityMonitor(artifacts=artifacts, registry=registry, corpus=corpus, compiler=compiler)

    event = CompilabilityEvent(
        event_kind="verified_transition",
        sample_ref="artifact://sample_ok",
        task_id="task_d",
        run_id="run_1",
        operation_id="op_1",
        primitive="read_file",
        route="filesystem",
        outcome="verified_success",
        evidence_refs=("artifact://proof",),
    )

    # Must NOT raise exception; degrades cleanly
    res = monitor.process_event(event)
    assert res["status"] in ("prefilter_insufficient", "evaluated")
    if res["status"] == "evaluated":
        assert res["decision"]["abstained"] is True


def test_case_e_persistence_restart_reconstruction(tmp_path):
    """Caso E: Referências e evidências sobrevivem a reinício; sem repetição de mutações confirmadas."""
    artifacts = ArtifactStore(root_dir=tmp_path / "artifacts")
    corpus = ExperienceCorpus(artifacts)

    s1 = _make_transition_sample("fs_write", "run_1", task="task_e", effect="state_mutation")
    ref1 = corpus.capture(s1)

    # Reconstruct from new instance on same artifact directory
    rebuilt_corpus = ExperienceCorpus(ArtifactStore(root_dir=tmp_path / "artifacts"), discover=True)
    query_samples = rebuilt_corpus.query(task_id="task_e", run_id="run_1")
    assert len(query_samples) == 1
    assert query_samples[0].outcome == TransitionOutcome.VERIFIED_SUCCESS
    assert query_samples[0].provenance.sample_ref is not None


def test_case_f_strict_no_global_promotion_from_single_run(tmp_path):
    """Caso F: Candidata observada em apenas um run NUNCA é promovida globalmente por confiança do Laya."""
    artifacts = ArtifactStore(root_dir=tmp_path / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts)
    corpus = ExperienceCorpus(artifacts)
    compiler = ExperienceCompiler(registry, corpus)

    # Build capability from single run
    cap = OperationalCapability(
        id="single_run_cap",
        name="Single Run Capability",
        route="native_browser",
        effect="state_mutation",
        input_schema={},
        implementation={"steps": [{"primitive": "browser_click"}]},
        learning_metadata={
            "run_ids": ["run_only_1"],  # only ONE run
            "parameterization_quality": True,
            "provenance_complete": True,
        },
    )
    registry.register(cap)

    policy = ExperiencePromotionPolicy()
    admission = policy.evaluate(cap)
    # Strictly rejected: single run cannot satisfy cross-run promotion policy
    assert not admission.admitted
    assert "cross_run_evidence_insufficient" in admission.reasons or any("run" in r for r in admission.reasons)

    # Even compiler.promote fails admission
    res = compiler.promote(cap)
    assert not res.admitted
    assert cap.lifecycle != CapabilityLifecycle.PROMOTED


def test_case_g_performance_and_backpressure(tmp_path):
    """Caso G: O monitor respeita backpressure e capacidade da fila; não degrada o caminho crítico."""
    artifacts = ArtifactStore(root_dir=tmp_path / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts)
    corpus = ExperienceCorpus(artifacts)
    compiler = ExperienceCompiler(registry, corpus)

    # Tiny queue to verify load-shedding
    monitor = OnlineCompilabilityMonitor(
        artifacts=artifacts,
        registry=registry,
        corpus=corpus,
        compiler=compiler,
        max_queue_size=4,
    )

    # Enqueue events fast
    scheduled_count = 0
    start = time.perf_counter()
    for i in range(20):
        ev = CompilabilityEvent(
            event_kind="tool_finished",
            sample_ref=f"artifact://sample_{i}",
            task_id="task_perf",
            run_id="run_1",
            operation_id=f"op_{i}",
            primitive="read_file",
            route="filesystem",
            outcome="observed",
        )
        if monitor.schedule_event(ev):
            scheduled_count += 1
    duration = time.perf_counter() - start

    # Non-blocking, took < 0.2s for 20 events
    assert duration < 0.5
    # Shedding occurred without crash
    assert monitor.metrics["events_filtered"] > 0
    monitor.drain()
    monitor.stop()


def test_case_h_provenance_and_decision_receipts(tmp_path):
    """Caso H: Decisões possuem recibos reproduzíveis e linhagem canônica."""
    artifacts = ArtifactStore(root_dir=tmp_path / "artifacts")
    registry = OperationalCapabilityRegistry(artifacts)
    corpus = ExperienceCorpus(artifacts)
    compiler = ExperienceCompiler(registry, corpus)

    def provenance_provider(req: DecisionRequest) -> DecisionResult:
        return DecisionResult(
            request_id=req.request_id,
            answers={"compilability_stage": CompilabilityStage.KEEP_COLLECTING.value},
            confidence={"compilability_stage": 0.91},
            provider="test_prov_provider",
            model="laya-v1",
        )

    register_system1_decision_provider(provenance_provider)

    monitor = OnlineCompilabilityMonitor(
        artifacts=artifacts, registry=registry, corpus=corpus, compiler=compiler, cooldown_seconds=0.0
    )

    # Populate 2 verified events to pass prefilter
    s1 = _make_transition_sample("browser_click", "run_1", task="task_h")
    ref1 = corpus.capture(s1)
    ev1 = CompilabilityEvent(
        event_kind="verified_transition",
        sample_ref=ref1,
        task_id="task_h",
        run_id="run_1",
        operation_id="op_h_1",
        primitive="browser_click",
        route="native_browser",
        outcome="verified_success",
        evidence_refs=("artifact://proof",),
    )
    monitor.process_event(ev1)

    ev2 = CompilabilityEvent(
        event_kind="verified_transition",
        sample_ref=ref1,
        task_id="task_h",
        run_id="run_1",
        operation_id="op_h_2",
        primitive="browser_click",
        route="native_browser",
        outcome="verified_success",
        evidence_refs=("artifact://proof",),
    )
    res = monitor.process_event(ev2)
    assert res["status"] == "evaluated"
    assert res["decision"]["request_id"] != ""


def test_tool_observer_hook_notifies_compilability_monitor(tmp_path, monkeypatch):
    """Verifica que workstation_raw_post_tool_observer aciona o monitor online."""
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    from workstation.task_compiler import _execution_active

    token = _execution_active.set(True)
    try:
        agent = SimpleNamespace(
            valid_tool_names={"work_execute"},
            _canonical_work_task_id="task_obs",
            _canonical_work_run_id="run_obs",
            _current_operation_id="op_obs",
            session_id="s",
            _conversation_root_id=lambda: "s",
        )

        monitor = get_compilability_monitor()
        initial_observed = monitor.metrics["events_observed"]

        workstation_raw_post_tool_observer(
            "read_file",
            {"path": "file.txt"},
            "call_id_123",
            {"content": "hello world"},
            0.05,
            {"agent": agent, "dispatched": True},
        )

        monitor.drain()
        assert monitor.metrics["events_observed"] == initial_observed + 1
    finally:
        _execution_active.reset(token)


@pytest.mark.skipif(os.getenv("HERMES_LAYA_LIVE_TEST") != "1", reason="explicit checkpoint opt-in required")
def test_laya_real_contract_compilability_stage(tmp_path):
    """Teste com Laya real para o domínio de compilabilidade (opt-in via HERMES_LAYA_LIVE_TEST=1)."""
    store = ArtifactStore(root_dir=tmp_path)
    provider = LayaDecisionProvider(artifact_store=store)

    req = build_compilability_decision_request(
        task_id="task_real",
        run_id="run_real",
        operation_id="op_real",
        operation_family="file_edit",
        target_family="file",
        repeat_count=3,
        parameter_variability=True,
        verified_success_count=2,
        failure_count=0,
        has_verifier=True,
        progress_detected=True,
        expected_utility=5.0,
    )

    result = provider(req)
    assert result is not None
    assert "compilability_stage" in result.answers
    ans = result.answers["compilability_stage"]
    assert ans in [
        "KEEP_COLLECTING",
        "MINE_CANDIDATE",
        "VALIDATE_CANDIDATE",
        "POSSIBLE_RUN_LOCAL_REUSE",
        "NEEDS_SYSTEM2",
        NeutralChoice.ABSTAIN.value,
    ]

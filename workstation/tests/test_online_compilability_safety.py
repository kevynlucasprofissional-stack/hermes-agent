"""Online Compilability Loop — safety (D-038, C1-C6) and real TaskRun adoption.

The fixture is a real TaskRun: a kanban task/run, a DurableTaskStore plan with real pending
items, real filesystem effects, the batch runner as the adaptive executor, the real
monitor/worker/mining/validation/closure/handoff code and the production checkpoint
``workstation_run_local_checkpoint``. Only the System-1 model and the SafeEnvironment
replay runner (owner seams) are test doubles. No test calls ``attempt_run_local_reuse``.
"""
from __future__ import annotations

import hashlib
import threading
import time
from types import SimpleNamespace

import pytest

from agent.system1_decision import DecisionResult, register_system1_decision_provider, reset_system1_decision
from workstation.artifacts import ArtifactStore
from workstation.batch_runner import DurableBatchRunner
from workstation.contracts import IntentAuthority, MessageEnvelope, MessageOrigin
from workstation.control_plane.ir import CREATE
from workstation.control_plane.lattice import AuthorityLevel, AuthorityScope
from workstation.control_plane.verification import (
    VerificationContract,
    VerificationResult,
    VerificationStatus,
)
from workstation.durable_tasks import DurableTaskStore, WorkItemStatus
from workstation.execution_policy import EvidenceStrength
from workstation.experience_compiler.causal import SafeEnvironment
from workstation.experience_compiler.compilability_monitor import (
    DIRECT,
    CompilabilityEvent,
    SHADOW,
    OnlineCompilabilityMonitor,
    install_compilability_monitor,
    load_learning_policy,
    notify_online_compilability,
    reset_compilability_monitor,
)
from workstation.experience_compiler.compiler import ExperienceCompiler
from workstation.experience_compiler.corpus import ExperienceCorpus
from workstation.experience_compiler.lifecycle import (
    ValidationEnvironmentProvider,
    register_validation_environment_provider,
)
from workstation.experience_compiler.models import (
    AuthorityOrigin,
    Operation,
    Provenance,
    SemanticState,
    StateDelta,
    TransitionOutcome,
    TransitionSample,
    Verification,
)
from workstation.experience_compiler.promotion import ExperiencePromotionPolicy
from workstation.integrations.hermes.run_local_adoption import workstation_run_local_checkpoint
from workstation.kanban import WorkstationKanbanBridge
from workstation.operational_capabilities import CapabilityLifecycle, OperationalCapabilityRegistry
from workstation.run_adoption import DurableRunAdoptionOwner
from workstation.system1.contracts import CompilabilityStage

CONTENTS = ("alpha", "beta", "gamma")
OP_FAMILY, TGT_FAMILY = "write_report", "report_file"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class TaskRunFixture:
    """A canonical TaskRun with real pending items and a real filesystem effect surface."""

    def __init__(self, tmp_path, monkeypatch, *, n_items=7, run_label="main", budget=True,
                 authority=AuthorityScope(AuthorityLevel.LOCAL_MUTATION, {"*"}, {"*"})):
        home = tmp_path / ("hermes_" + run_label)
        home.mkdir(exist_ok=True)
        monkeypatch.setenv("HERMES_HOME", str(home))
        self.root = tmp_path / ("fs_" + run_label)
        self.root.mkdir()
        self.artifacts = ArtifactStore(root_dir=tmp_path / ("artifacts_" + run_label))
        self.registry = OperationalCapabilityRegistry(self.artifacts)
        self.corpus = ExperienceCorpus(self.artifacts)
        self.compiler = ExperienceCompiler(self.registry, self.corpus)
        self.authority = authority

        bridge = WorkstationKanbanBridge()
        content = f"Crie {n_items} relatorios em out ({run_label})"
        envelope = MessageEnvelope(MessageOrigin.HUMAN, IntentAuthority.CREATE_WORK, "sess-" + run_label, content)
        self.task_id = bridge.promote_request_if_multistep(content, session_id=envelope.session_id, envelope=envelope)
        from hermes_cli import kanban_db
        with bridge.get_connection() as conn:
            self.run_id = str(kanban_db.get_task(conn, self.task_id).current_run_id)
        self.envelope = envelope

        objective = {"operation_intent": {
            "effect_budget": [CREATE("out").to_dict()] if budget else [], "target": TGT_FAMILY,
            "goal": {"type": "EXISTS", "path": "out"}}}
        objective_ref = self.artifacts.store(self.task_id, "objective.json", objective).ref
        self.items = [{"path": f"out/report_{i}.txt", "content": CONTENTS[i % 3],
                       "operation_family": OP_FAMILY, "target_family": TGT_FAMILY} for i in range(n_items)]
        self.store = DurableTaskStore()
        self.plan = self.store.create_plan(
            self.task_id, "reports", self.items, run_id=self.run_id,
            metadata={"run_id": self.run_id, "objective_ref": objective_ref})

        self.dispatch_log: list[tuple[str, str]] = []
        self.readback_ok = True
        self.system2_calls = 0
        self.owner = DurableRunAdoptionOwner(
            DurableTaskStore, self.artifacts,
            authority_for_task=lambda task: self.authority,
            dispatch_fn=self.dispatch, readback_fn=self.readback,
            readback_primitives=("write_file",), supported_primitives=("write_file", "read_file"),
        )
        self.agent = SimpleNamespace(
            _canonical_work_task_id=self.task_id, _canonical_work_run_id=self.run_id,
            _run_adoption_owner=self.owner, session_id=envelope.session_id)

    # -- certified dispatch / independent readback (the world) --------------------------------
    def dispatch(self, tool, args):
        self.dispatch_log.append((tool, args["path"]))
        path = self.root / args["path"]
        if tool == "write_file":
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(args["content"], encoding="utf-8")
            return {"status": "ok"}
        return {"status": "ok", "content": path.read_text(encoding="utf-8")}

    def readback(self, primitive, bound_args, raw):
        path = self.root / bound_args["path"]
        ok = self.readback_ok and path.is_file() and path.read_text(encoding="utf-8") == bound_args["content"]
        ref = self.artifacts.store(self.task_id, f"rb_{_sha(bound_args['path'])[:10]}.json",
                                   {"path": bound_args["path"], "matched": ok}).ref
        return {"ok": ok, "evidence_ref": ref}

    # -- adaptive execution of the first k items (the runtime doing System-2 work) -------------
    def sample(self, prim, idx, item, verified):
        before = SemanticState(semantic_predicates={"exists": False})
        after = SemanticState(semantic_predicates={"exists": True})
        return TransitionSample(
            state_before=before, state_after=after, delta=StateDelta.between(before, after),
            operation=Operation(
                primitive=prim, canonical_route="filesystem", target_family=TGT_FAMILY,
                operation_family=OP_FAMILY, effect_class="read_only" if verified else "state_mutation",
                parameters={"path": item["path"]} if verified else {"path": item["path"], "content": item["content"]},
                scope={"root": "out"}),
            verification=Verification(
                EvidenceStrength.SEMANTIC_PERSISTED_READBACK, "fs_readback",
                {"exists": True} if verified else {}, [f"artifact://tasks/{self.task_id}/ev_{idx}"],
                status="VERIFIED" if verified else "INCONCLUSIVE", observer="fs_observer",
                source_kind="filesystem", trust_class="trusted_runtime"),
            outcome=TransitionOutcome.VERIFIED_SUCCESS if verified else TransitionOutcome.OBSERVED,
            provenance=Provenance(self.task_id, self.run_id, f"op_{idx}_{prim}", "local-fs", "fixture",
                                  AuthorityOrigin.USER, "trusted_runtime", operation_index=idx))

    def run_adaptive(self, k, *, notify=True, instrument=True):
        counter = {"n": 0}

        def worker(payload, work_item):
            self.system2_calls += 1  # one reasoning round spent on this adaptive item
            n = counter["n"] = counter["n"] + 2
            self.dispatch("write_file", payload)
            raw = self.dispatch("read_file", payload)
            self.corpus.capture(self.sample("write_file", n, payload, False))
            ref = self.corpus.capture(self.sample("read_file", n + 1, payload, True))
            if notify:
                notify_online_compilability(
                    ref=ref, task_id=self.task_id, run_id=self.run_id, operation_id=f"op_{n + 1}_read_file",
                    primitive="read_file", route="filesystem", outcome="verified_success",
                    event_kind="verified_transition", operation_family=OP_FAMILY, target_family=TGT_FAMILY,
                    evidence_refs=(ref,), owner=self.owner, system2_calls=1 if instrument else None)
            return raw

        runner = DurableBatchRunner(self.task_id, task_store=self.store, artifact_store=self.artifacts, max_retries=0)
        return runner.execute_batch("reports", self.items, worker_fn=worker,
                                    can_start_item=lambda it: it.item_index <= k)

    def statuses(self):
        return [i.status for i in self.store.get_work_items(self.plan.id)]

    def written(self):
        return sorted(p.name for p in (self.root / "out").glob("*.txt"))

    def checkpoint(self, api_call_count=7):
        return workstation_run_local_checkpoint(SimpleNamespace(agent=self.agent, api_call_count=api_call_count))


# -- owner seams for validation (verifier + SafeEnvironment replay), real sandbox effects ---------

def verification_contract(_candidate):
    return VerificationContract(
        covered_predicates=("exists",), effect_classes=("read_only", "state_mutation"), observer="fs_observer",
        source_kind="filesystem", minimum_evidence=EvidenceStrength.SEMANTIC_PERSISTED_READBACK,
        allowed_trust=("trusted_runtime",), require_read_after_write=True, transition_claim=True)


def _vr(fingerprint, refs):
    return VerificationResult(VerificationStatus.VERIFIED, fingerprint, tuple(refs), ("exists",),
                              True, True, True, True, True, "verified", "2026-10-08T00:00:00Z")


def install_validation_env(fx, tmp_path, *, replay="pass", evaluator="pass"):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir(exist_ok=True)

    def store_ev(name, body, task=None):
        return fx.artifacts.store(task or fx.task_id, name, body).ref

    def verifier_evaluator(cand, contract, task_id, run_id):
        if evaluator == "raise":
            raise RuntimeError("verifier backend down")
        target = sandbox / "probe_pos.txt"
        target.write_text("x", encoding="utf-8")
        pos_ref = store_ev("verifier_pos.json", {"observed": target.read_text(), "task": task_id},
                           task="someone_elses_task" if evaluator == "foreign" else None)
        neg_ref = store_ev("verifier_neg.json", {"observed_missing": not (sandbox / "absent.txt").exists()})
        pos = {"kind": "positive_replay", "passed": True, "phase": "validation", "evidence_ref": pos_ref,
               "verification_result": _vr(contract.fingerprint(), [pos_ref]).to_dict()}
        neg = {"kind": "negative_control", "passed": True, "phase": "validation", "evidence_ref": neg_ref}
        return pos, neg

    def replay_runner_factory(cand, env):
        def runner(steps, deadline):
            if replay == "raise":
                raise RuntimeError("replay sandbox crashed")
            if replay == "fail":
                return {"passed": False}
            binding = dict(cand.learning_metadata["bindings"][0])
            for step in steps:
                args = {k: (binding[v[len("$inputs."):]] if isinstance(v, str) and v.startswith("$inputs.") else v)
                        for k, v in step["args"].items()}
                if step["primitive"] == "write_file":
                    (sandbox / args["path"].replace("/", "_")).write_text(args["content"], encoding="utf-8")
            ref = store_ev("replay_result.json", {"candidate": cand.id, "sandbox": True})
            foreign = store_ev("replay_foreign.json", {"candidate": cand.id}, task="someone_elses_task")
            refs = {"no_refs": [], "ghost_ref": ["artifact://tasks/ghost/replay_missing.json"],
                    "foreign_ref": [foreign]}.get(replay, [ref])
            fp = "0" * 64 if replay == "wrong_fp" else cand.learning_metadata["verifier_fingerprint"]
            return {"passed": True, "verification_result": _vr(fp, refs).to_dict(), "evidence_strength": 2,
                    "evidence_refs": refs, "predicates": {"exists": True}}
        return runner

    register_validation_environment_provider(ValidationEnvironmentProvider(
        verifier_evaluator=verifier_evaluator, replay_runner_factory=replay_runner_factory,
        safe_env_factory=lambda cand: SafeEnvironment("temp_filesystem", "sandbox-" + cand.id, lambda *_: True)))


def laya(stage):
    def provider(req):
        if stage == "raise":
            raise RuntimeError("laya timeout")
        if stage == "abstain":
            return DecisionResult(request_id=req.request_id, answers={"compilability_stage": "ABSTAIN"},
                                  confidence={"compilability_stage": 0.0}, provider="fake_laya")
        return DecisionResult(request_id=req.request_id, answers={"compilability_stage": stage},
                              confidence={"compilability_stage": 0.9}, provider="fake_laya", model="m")
    return provider


def make_monitor(fx, *, mode=DIRECT, **kwargs):
    from workstation.experience_compiler.compilability_monitor import create_direct_qualification_attestation
    direct_ref = create_direct_qualification_attestation(code_version="fixture", provider="laya") if mode == DIRECT else ""
    monitor = OnlineCompilabilityMonitor(
        artifacts=fx.artifacts, registry=fx.registry, corpus=fx.corpus, compiler=fx.compiler, mode=mode,
        direct_qualification_ref=direct_ref,
        cooldown_seconds=0.0, contract_factory=verification_contract, **kwargs)
    install_compilability_monitor(monitor)
    return monitor


@pytest.fixture(autouse=True)
def _isolation():
    reset_system1_decision()
    reset_compilability_monitor()
    register_validation_environment_provider(None)
    yield
    reset_system1_decision()
    reset_compilability_monitor()
    register_validation_environment_provider(None)


@pytest.fixture
def fx(tmp_path, monkeypatch):
    fixture = TaskRunFixture(tmp_path, monkeypatch)
    yield fixture
    fixture.owner.close()
    fixture.store.close()


def learn(fx, tmp_path, k=3, *, stage=CompilabilityStage.POSSIBLE_RUN_LOCAL_REUSE.value, **env):
    """Adaptive run of k items, observed by the real worker, until the monitor is idle."""
    install_validation_env(fx, tmp_path, **env)
    register_system1_decision_provider(laya(stage))
    monitor = make_monitor(fx)
    fx.run_adaptive(k)
    assert monitor.drain(10.0)
    return monitor


# ================================================================== C4 policy / containment

def test_shadow_is_default_and_direct_requires_explicit_qualification():
    assert OnlineCompilabilityMonitor(artifacts=None, mode=None).mode == SHADOW
    assert load_learning_policy().mode == SHADOW
    downgraded = OnlineCompilabilityMonitor(mode="direct")
    assert downgraded.mode == SHADOW and downgraded.mode_downgrade_reason == "direct_requires_qualification_ref"
    arbitrary = OnlineCompilabilityMonitor(mode="direct", direct_qualification_ref="receipt-1")
    assert arbitrary.mode == SHADOW and arbitrary.mode_downgrade_reason == "invalid_qualification_attestation"
    from workstation.experience_compiler.compilability_monitor import create_direct_qualification_attestation
    valid_att = create_direct_qualification_attestation(code_version="v1", provider="laya")
    assert OnlineCompilabilityMonitor(mode="direct", direct_qualification_ref=valid_att).mode == DIRECT


def test_kill_switch_stops_the_learning_plane_without_threads():
    monitor = OnlineCompilabilityMonitor(enabled=False)
    event = CompilabilityEvent("verified_transition", "r", "t", "1", "o", "p", "filesystem", "verified_success")
    assert monitor.schedule_event(event) is False
    assert monitor._worker_thread is None and monitor.ready_offers("t", "1") == []


def test_shadow_for_effects_actively_mines_while_restricting_offers(fx, tmp_path):
    """DF-007 / DF1: In SHADOW_FOR_EFFECTS, OBSERVE_ACTIVE still performs candidate mining, but ready_offers remains empty."""
    install_validation_env(fx, tmp_path)
    register_system1_decision_provider(laya(CompilabilityStage.POSSIBLE_RUN_LOCAL_REUSE.value))
    monitor = make_monitor(fx, mode=SHADOW)
    fx.run_adaptive(3)
    assert monitor.drain(10.0)
    window = monitor._windows[(fx.task_id, fx.run_id)]
    assert monitor.metrics["decisions_shadow"] >= 1 and window.shadow_decisions
    # Active observation: mining occurred because canonical verified evidence existed
    assert monitor.metrics["mining_attempts"] > 0
    # Effect restriction: unpromoted/unqualified mutation offers are NOT available for autonomous execution
    assert monitor.ready_offers(fx.task_id, fx.run_id) == []
    assert fx.checkpoint() is None and fx.statuses().count(WorkItemStatus.COMPLETED) == 3



@pytest.mark.parametrize("behavior", ["raise", "abstain"])
def test_laya_failure_or_abstention_never_authorizes_learning_and_main_path_continues(fx, tmp_path, behavior):
    install_validation_env(fx, tmp_path)
    register_system1_decision_provider(laya(behavior))
    monitor = make_monitor(fx)
    summary = fx.run_adaptive(3)
    assert summary.success_count == 3 and not summary.anomalies  # foreground work unaffected
    assert monitor.drain(10.0)
    assert monitor.metrics["decisions_abstain"] >= 1
    assert monitor.metrics["mining_attempts"] == 0 and monitor.ready_offers(fx.task_id, fx.run_id) == []


def test_invalid_stage_from_laya_is_ignored(fx, tmp_path):
    monitor = learn(fx, tmp_path, stage="DO_WHATEVER")
    assert monitor.metrics["mining_attempts"] == 0


def test_saturation_and_shutdown_never_deadlock(fx):
    release = threading.Event()

    def blocking(req):
        release.wait(5)
        return DecisionResult(request_id=req.request_id, answers={"compilability_stage": "KEEP_COLLECTING"},
                              confidence={"compilability_stage": 0.5}, provider="slow")
    register_system1_decision_provider(blocking)
    monitor = OnlineCompilabilityMonitor(artifacts=fx.artifacts, registry=fx.registry, corpus=fx.corpus,
                                         compiler=fx.compiler, mode=SHADOW, max_queue_size=2, cooldown_seconds=0.0)
    results = []
    started = time.monotonic()
    for i in range(10):
        results.append(monitor.schedule_event(CompilabilityEvent(
            event_kind="verified_transition", sample_ref=f"r{i}", task_id=fx.task_id, run_id=fx.run_id,
            operation_id=f"o{i}", primitive="p", route="filesystem", outcome="verified_success",
            operation_family="f", target_family="t")))
    assert time.monotonic() - started < 2.0  # producers never block
    assert not all(results) and monitor.metrics["events_shed"] >= 1
    assert monitor.drain(0.2) is False  # bounded wait, not queue.join()
    release.set()
    assert monitor.stop(timeout=3.0) is True


def test_windows_are_bounded_and_evicted():
    monitor = OnlineCompilabilityMonitor(max_windows=3, window_ttl_seconds=0.05)
    for i in range(10):
        monitor._get_window(f"task{i}", "1")
    assert len(monitor._windows) <= 3
    time.sleep(0.1)
    monitor._get_window("fresh", "1")
    assert list(monitor._windows) == [("fresh", "1")]


# ================================================================== C1 validation / authority

def mined_candidate(fx, tmp_path, *, k=3, **env):
    monitor = learn(fx, tmp_path, k=k, stage=CompilabilityStage.KEEP_COLLECTING.value, **env)
    candidates = monitor.mine_candidate_in_run(fx.task_id, fx.run_id)
    assert candidates, "scoped mining must yield the run-local candidate"
    return monitor, candidates[-1]


@pytest.mark.parametrize("replay,reason", [("raise", "controlled_replay_error"), ("fail", "controlled_replay_failed"),
                                          ("no_refs", "controlled_replay_failed"),
                                          ("ghost_ref", "replay_evidence_unresolvable"),
                                          ("foreign_ref", "replay_evidence_foreign_run"),
                                          ("wrong_fp", "controlled_replay_failed")])
def test_replay_exception_failure_or_missing_refs_yield_no_proof(fx, tmp_path, replay, reason):
    monitor, cand = mined_candidate(fx, tmp_path, replay=replay)
    ok, proof, reasons = monitor.validate_candidate_run_local(cand, task_id=fx.task_id, run_id=fx.run_id)
    assert not ok and proof is None and any(r.startswith(reason) for r in reasons), reasons
    assert monitor.ready_offers(fx.task_id, fx.run_id) == []


def test_missing_validation_environment_and_forged_evidence_yield_no_proof(fx, tmp_path):
    monitor, cand = mined_candidate(fx, tmp_path)
    cand.validation_evidence.append({"kind": "controlled_replay", "passed": True,
                                     "evidence_ref": "artifact://replay_forged"})
    register_validation_environment_provider(None)
    ok, proof, reasons = monitor.validate_candidate_run_local(cand, task_id=fx.task_id, run_id=fx.run_id)
    assert not ok and proof is None and reasons == ["validation_environment_unavailable"]
    install_validation_env(fx, tmp_path)  # forged URI in the candidate is not consulted nor accepted
    ok, proof, reasons = monitor.validate_candidate_run_local(cand, task_id=fx.task_id, run_id=fx.run_id)
    assert ok and "forged" not in str(proof.replay_evidence_ref)
    assert fx.artifacts.resolve_structured(proof.replay_evidence_ref)["schema"] == "workstation.run_local_replay_receipt.v1"


def test_verifier_receipt_from_another_run_is_rejected(fx, tmp_path):
    monitor, cand = mined_candidate(fx, tmp_path, evaluator="foreign")
    ok, proof, reasons = monitor.validate_candidate_run_local(cand, task_id=fx.task_id, run_id=fx.run_id)
    assert not ok and proof is None and "positive_verifier_receipt_foreign_run" in reasons


def test_target_outside_the_admitted_intent_denies(fx, tmp_path):
    monitor, cand = mined_candidate(fx, tmp_path)
    ref = fx.artifacts.store(fx.task_id, "objective3.json", {"operation_intent": {
        "effect_budget": [CREATE("out").to_dict()], "target": "some_other_target"}}).ref
    fx.store.update_plan_metadata(fx.plan.id, {"objective_ref": ref})
    ok, _, reasons = monitor.validate_candidate_run_local(cand, task_id=fx.task_id, run_id=fx.run_id)
    assert not ok and "target_identity_unproven" in reasons


def test_verifier_failure_yields_no_proof(fx, tmp_path):
    monitor, cand = mined_candidate(fx, tmp_path, evaluator="raise")
    ok, proof, reasons = monitor.validate_candidate_run_local(cand, task_id=fx.task_id, run_id=fx.run_id)
    assert not ok and proof is None and reasons[0].startswith("verifier_evaluation_error")


def test_no_canonical_identity_or_owner_means_no_proof(fx, tmp_path):
    monitor, cand = mined_candidate(fx, tmp_path)
    assert monitor.validate_candidate_run_local(cand)[2] == ["missing_canonical_identity"]
    monitor.owner = None
    monitor._get_window(fx.task_id, fx.run_id).owner = None
    assert monitor.validate_candidate_run_local(cand, task_id=fx.task_id, run_id=fx.run_id)[2] == ["no_runtime_owner"]
    ok, proof, reasons = monitor.validate_candidate_run_local(cand, task_id="other-task", run_id="9", owner=fx.owner)
    assert not ok and proof is None


@pytest.mark.parametrize("authority,budget,reason", [
    (AuthorityScope(AuthorityLevel.READ, {"*"}, {"*"}), True, "authority_not_granted"),
    (AuthorityScope(AuthorityLevel.LOCAL_MUTATION, {"*"}, {"elsewhere"}), True, "authority_not_granted"),
    (AuthorityScope(AuthorityLevel.LOCAL_MUTATION, {"*"}, {"*"}), False, "effect_budget_missing"),
])
def test_authority_or_budget_below_what_the_procedure_needs_denies(tmp_path, monkeypatch, authority, budget, reason):
    fx2 = TaskRunFixture(tmp_path, monkeypatch, authority=authority, budget=budget)
    try:
        monitor, cand = mined_candidate(fx2, tmp_path)
        ok, proof, reasons = monitor.validate_candidate_run_local(cand, task_id=fx2.task_id, run_id=fx2.run_id)
        assert not ok and proof is None and reason in reasons, reasons
        assert monitor.ready_offers(fx2.task_id, fx2.run_id) == [] and fx2.checkpoint() is None
    finally:
        fx2.owner.close()
        fx2.store.close()


def test_budget_that_does_not_contain_the_effect_denies(fx, tmp_path):
    monitor, cand = mined_candidate(fx, tmp_path)
    objective = {"operation_intent": {"effect_budget": [CREATE("elsewhere").to_dict()], "target": TGT_FAMILY}}
    ref = fx.artifacts.store(fx.task_id, "objective2.json", objective).ref
    fx.store.update_plan_metadata(fx.plan.id, {"objective_ref": ref})
    ok, _, reasons = monitor.validate_candidate_run_local(cand, task_id=fx.task_id, run_id=fx.run_id)
    assert not ok and "effect_outside_budget" in reasons


def test_uncertain_outstanding_mutation_denies(fx, tmp_path):
    monitor, cand = mined_candidate(fx, tmp_path)
    nxt = fx.store.get_work_items(fx.plan.id)[3]
    fx.store.update_item_checkpoint(nxt.id, "step_0_dispatch", metadata={"mutation_identity": {"operation_id": "x"}})
    ok, _, reasons = monitor.validate_candidate_run_local(cand, task_id=fx.task_id, run_id=fx.run_id)
    assert not ok and "uncertain_mutation_outstanding" in reasons


def test_diverging_item_target_or_family_is_not_equivalent_work(fx, tmp_path):
    monitor, cand = mined_candidate(fx, tmp_path)
    item = fx.store.get_work_items(fx.plan.id)[3]
    conn = fx.store.get_connection()
    import json
    conn.execute("UPDATE work_items SET input_payload=? WHERE id=?",
                 (json.dumps({**item.input_payload, "operation_family": "something_else"}), item.id))
    conn.commit()
    ok, _, reasons = monitor.validate_candidate_run_local(cand, task_id=fx.task_id, run_id=fx.run_id)
    assert not ok and "item_not_equivalent" in reasons


# ================================================================== C2 scoped mining

def test_mining_is_scoped_to_the_task_run_before_compilation(fx, tmp_path, monkeypatch):
    other = TaskRunFixture(tmp_path, monkeypatch, run_label="other")
    other.corpus = fx.corpus  # same corpus/artifact projection: contamination must come from scoping alone
    other.artifacts = fx.artifacts
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "hermes_main"))
    try:
        for n, item in enumerate(other.items[:3]):
            fx.corpus.capture(other.sample("write_file", 2 * n, {**item, "content": "OTHER"}, False))
            fx.corpus.capture(other.sample("read_file", 2 * n + 1, item, True))
        monitor, cand = mined_candidate(fx, tmp_path)
        assert cand.learning_metadata["run_ids"] == [fx.run_id]
        assert {o["task_id"] for o in cand.provenance["origins"]} == {fx.task_id}
        assert "OTHER" not in str(cand.input_schema) + str(cand.implementation)
        scoped = fx.compiler.mine(task_id=other.task_id, run_id=other.run_id)
        assert all({o["task_id"] for o in c.provenance["origins"]} == {other.task_id} for c in scoped)
    finally:
        other.owner.close()
        other.store.close()


def test_candidate_merged_with_another_run_is_not_run_local(fx, tmp_path):
    monitor, cand = mined_candidate(fx, tmp_path)
    cand.learning_metadata["run_ids"] = sorted({fx.run_id, "someone-elses-run"})
    ok, proof, reasons = monitor.validate_candidate_run_local(cand, task_id=fx.task_id, run_id=fx.run_id)
    assert not ok and proof is None and reasons == ["cross_run_lineage"]
    cand.learning_metadata["run_ids"], cand.provenance = [fx.run_id], {"origins": []}
    assert monitor.validate_candidate_run_local(cand, task_id=fx.task_id, run_id=fx.run_id)[2] == ["lineage_unknown"]


# ================================================================== C3/C6 automatic end to end

def test_taskrun_learns_then_automatically_adopts_and_verifies_next_items(fx, tmp_path):
    monitor = learn(fx, tmp_path, k=3)
    assert fx.statuses().count(WorkItemStatus.COMPLETED) == 3
    offers = monitor.ready_offers(fx.task_id, fx.run_id)
    assert len(offers) == 1 and offers[0].proof.run_id == fx.run_id
    # No helper is invoked by the test: the production boundary performs the adoption.
    adaptive_dispatches = len(fx.dispatch_log)
    report = fx.checkpoint(api_call_count=7)
    assert report.status == "adopted" and report.all_items_completed
    assert fx.statuses().count(WorkItemStatus.COMPLETED) == 7
    assert fx.written() == [f"report_{i}.txt" for i in range(7)]
    for i in range(7):
        assert (fx.root / "out" / f"report_{i}.txt").read_text() == CONTENTS[i % 3]
    # exactly the 4 remaining items were dispatched by adoption (write + read), none re-executed
    adopted = fx.dispatch_log[adaptive_dispatches:]
    assert sorted({p for _, p in adopted}) == [f"out/report_{i}.txt" for i in range(3, 7)]
    assert [p for t, p in fx.dispatch_log if t == "write_file"].count("out/report_0.txt") == 1
    # terminal verified receipts with independent readback
    assert all(r["verified"] and r["readbacks"] == 1 for r in report.items)
    receipt = fx.artifacts.resolve_structured(report.items[0]["receipt_ref"])
    assert receipt["schema"] == "workstation.run_local_reuse_receipt.v1"
    body = receipt["content"]
    assert body["status"] == "VERIFIED" and body["readbacks"][0]["ok"] and body["decision_receipt_refs"]
    assert fx.artifacts.resolve_structured(body["replay_receipt_ref"])
    # honest metrics
    m = monitor.metrics
    assert (m["items_attempted"], m["items_completed"], m["items_verified"], m["run_local_reuses"]) == (4, 4, 4, 4)
    assert m["system2_baseline_calls_per_item"] == 1.0 and m["system2_calls_avoided_status"] == "measured"
    assert m["system2_calls_avoided"] == 4
    # idempotent: a second boundary neither re-dispatches nor re-counts
    before = len(fx.dispatch_log)
    assert fx.checkpoint(api_call_count=8) is None or not fx.checkpoint().items
    assert len(fx.dispatch_log) == before and monitor.metrics["items_verified"] == 4


def test_single_run_candidate_is_never_promoted_globally(fx, tmp_path):
    learn(fx, tmp_path, k=3)
    assert fx.checkpoint().all_items_completed
    for cap in fx.registry.list_capabilities():
        assert cap.lifecycle != CapabilityLifecycle.PROMOTED
        assert ExperiencePromotionPolicy().evaluate(cap).admitted is False


def test_possible_reuse_without_a_validated_candidate_executes_nothing(fx, tmp_path):
    monitor = learn(fx, tmp_path, k=3, replay="fail")
    assert monitor.ready_offers(fx.task_id, fx.run_id) == []
    before = len(fx.dispatch_log)
    assert fx.checkpoint() is None and len(fx.dispatch_log) == before
    assert fx.statuses().count(WorkItemStatus.COMPLETED) == 3


@pytest.mark.parametrize("change", ["cancelled", "superseded", "policy_revoked"])
def test_cancelled_superseded_or_revoked_runs_execute_no_effects(fx, tmp_path, change):
    monitor = learn(fx, tmp_path, k=3)
    assert monitor.ready_offers(fx.task_id, fx.run_id)
    conn = fx.store.get_connection()
    if change == "cancelled":
        conn.execute("UPDATE tasks SET status='cancelled' WHERE id=?", (fx.task_id,))
    elif change == "superseded":
        conn.execute("UPDATE tasks SET current_run_id=? WHERE id=?", (int(fx.run_id) + 50, fx.task_id))
    else:
        conn.execute("UPDATE task_runs SET outcome='POLICY_REVOKED' WHERE id=?", (int(fx.run_id),))
    conn.commit()
    before = len(fx.dispatch_log)
    report = fx.checkpoint()
    assert len(fx.dispatch_log) == before and not (report and report.items)
    assert fx.statuses().count(WorkItemStatus.COMPLETED) == 3
    assert monitor.metrics["adoption_denials"] >= 1 and monitor.metrics["items_verified"] == 0


def test_outstanding_uncertainty_blocks_adoption_and_nothing_is_retried(fx, tmp_path):
    monitor = learn(fx, tmp_path, k=3)
    nxt = fx.store.get_work_items(fx.plan.id)[3]
    fx.store.update_item_checkpoint(nxt.id, "step_0_dispatch", metadata={"mutation_identity": {"operation_id": "x"}})
    before = len(fx.dispatch_log)
    report = fx.checkpoint()
    assert len(fx.dispatch_log) == before and not (report and report.items)
    assert "uncertain_mutation_outstanding" in monitor.metrics["adoption_denial_reasons"]


def test_result_without_independent_readback_is_not_counted_and_never_retried(fx, tmp_path):
    monitor = learn(fx, tmp_path, k=3)
    fx.readback_ok = False
    report = fx.checkpoint()
    assert report.status == "failed" and len(report.items) == 1 and not report.items[0]["verified"]
    m = monitor.metrics
    assert m["items_verified"] == 0 and m["run_local_reuses"] == 0 and m["items_failed"] == 1
    assert m["system2_calls_avoided"] == 0 and m["system2_calls_avoided_estimated"] == 0
    writes = [p for t, p in fx.dispatch_log if t == "write_file"]
    assert writes.count("out/report_3.txt") == 1  # failed mutation never re-dispatched (no retries)
    assert monitor.ready_offers(fx.task_id, fx.run_id) == []  # offer revoked
    before = len(fx.dispatch_log)
    fx.readback_ok = True
    assert fx.checkpoint() is None and len(fx.dispatch_log) == before


def test_system2_savings_are_unknown_without_instrumented_baseline_never_inferred_from_item_count(fx, tmp_path):
    install_validation_env(fx, tmp_path)
    register_system1_decision_provider(laya(CompilabilityStage.POSSIBLE_RUN_LOCAL_REUSE.value))
    monitor = make_monitor(fx)
    fx.run_adaptive(3, instrument=False)
    assert monitor.drain(10.0)
    report = fx.checkpoint()
    assert report.all_items_completed and monitor.metrics["items_verified"] == 4
    assert monitor.metrics["system2_baseline_calls_per_item"] is None
    assert monitor.metrics["system2_calls_avoided_status"] == "unknown"
    assert monitor.metrics["system2_calls_avoided"] == 0
    assert monitor.metrics["system2_calls_avoided_estimated"] == 4  # labelled estimate, not a measurement


def test_the_production_boundary_invokes_the_adoption_checkpoint(monkeypatch):
    from workstation.integrations.hermes import operational_resolution as boundary
    from workstation.integrations.hermes import run_local_adoption as binding
    calls = []
    monkeypatch.setattr(binding, "workstation_run_local_checkpoint", lambda ctx: calls.append(ctx))
    ctx = SimpleNamespace(agent=SimpleNamespace(), session_id="s")
    assert boundary.workstation_operational_resolution(ctx) is None
    assert calls == [ctx]

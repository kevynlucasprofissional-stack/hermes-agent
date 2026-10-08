# Online Compilability Loop — post-implementation independent audit (2026-10-08)

**Branch:** `workstation/laya-direct-system1`. **Implementation:** `c969fbf190db0eea1e41170a20b5113404bf6749`. **Audited HEAD:** `b13a2424c275fdc1894e051dd2f4765b0534e998`.
**Verdict:** PARTIALLY IMPLEMENTED / P0 SAFETY AND E2E GATES OPEN / **NOT QUALIFIED** / DO NOT MERGE MAIN.
**Evidence:** static review of implementation, test sources, and provided development log; this review did not execute tests. The development log states 11/11 new tests, 71/71 selected regression tests and 14/14 local qualification gates including a real Laya contract test. Those numbers neither supersede independent safety criteria nor prove autonomous production behavior. CI `37783114603` on `c969fbf` completed FAILURE; `37794367952` on `b13a2424` was IN_PROGRESS at review. Recheck statuses on exact final HEAD.

## Findings: severity, exact owner and falsifiable failure mode

| Priority | Code owner | Finding / corrective requirement |
|---|---|---|
| P0 | `workstation/experience_compiler/compilability_monitor.py:validate_candidate_run_local()` | When controlled replay raises or candidate has no steps, code may synthesize `artifact://replay_...`; missing source refs may be replaced with synthetic `first_ref`. **Never mint successful replay/proof evidence**. Missing, failed or exception replay must deny mutating reuse. Obtain real persisted verifier/replay receipts and check scope/fingerprint. |
| P0 | Same `validate_candidate_run_local()` | Constructs `AuthorityScope(level=LOCAL_MUTATION, allowed_actions={candidate.route,candidate.id})`, synthetic `effect_budget`, task/run default identifiers, `uncertainty_clear=True`, and synthetic remaining-items ref. Learning plane is **not** authority owner. Derive policy-granted scope, effect budget, active lease, canonical TaskRun identity, target, pending item set, and actual uncertainty/readback strictly from owning runtime/TaskCompiler/Policy/Verifier. |
| P1 | `OnlineCompilabilityMonitor.process_event()` | Branches handle `MINE_CANDIDATE` and `VALIDATE_CANDIDATE`; **no automatic `POSSIBLE_RUN_LOCAL_REUSE` continuation**. Existing `attempt_run_local_reuse()` only runs when explicitly called with proof, steps, items and dispatcher. Integrate safe adoption with existing TaskRun runner/closure. |
| P1 | `mine_candidate_in_run()` | Calls global `self.compiler.mine()`, then filters candidates by run; accepts empty origin IDs. Scope canonical sample selection **before mining** with task/run/tenant boundaries and exclude unresolved counterexamples. Do not modify global cross-run promotion rules. |
| P1 | `OnlineCompilabilityMonitor(mode='direct')`, singleton and `_query_system1_compilability()` | Default direct mode plus deterministic fallback to `MINE_CANDIDATE` after Laya abstention can activate uncalibrated learning. Default SHADOW/no side-effects; explicit rollout + calibration/kill switch to unlock bounded direct mode. Abstention/timeout never authorizes effect/adoption. |
| P1 | `attempt_run_local_reuse()` | Success counted when returned anomalies absent, even without proven terminal status. `system2_calls_avoided += len(remaining_items)` measures items, not model calls. Require verified per-item terminal receipts/readback and observed comparison baseline; otherwise metrics unknown/estimated. |
| P2 | Monitor queue / windows | `drain(timeout)` calls unbounded `queue.join()`; singleton worker stop lacks guaranteed join; per-task/run windows have no clear TTL/cap. Implement bounded join/shutdown, cancellation, eviction, resource budgets and foreground latency measurements. |
| P2 | `workstation/tests/test_online_compilability_monitor.py` | Positive `test_case_a_positive_same_run_reuse` manually calls `monitor.process_event()` and `monitor.attempt_run_local_reuse()` using `fake_laya`, synthetic remaining items, steps and fake dispatcher. Demonstrates components under simulation, **not** actual observer → TaskRun automatic adoption. Live Laya typed contract tests answer shape, not decision quality. |

## Invariants and architectural ownership

- Laya/System-1 selects semantic next stage, never authority or truth; `answer_confidence` is not calibrated compilability.
- `ExperienceCorpus`/provider-free `ExperienceCompiler.compile()/mine()` remain candidate-mining owners; do not rewrite or duplicate them.
- `workstation/run_closure.py:RunClosureProof/RunScopedCapability/execute_in_flight_handoff`, `task_compiler.py`, Policy, runtime and verifier own safe adoption, effect permissions, leases, readbacks and completion.
- `ExperienceValidationPromotionCoordinator.process_candidate()` may reach `ExperienceCompiler.promote()`: do not use that path for temporary run-local validation.
- Causal evidence and actual verifier/replay refs must be canonical/persisted; failure, UNCERTAIN, cancellation, lease expiry or authority supersession block adoption, never become positive labels.
- H-079 upstream-first, H-081 real-provider/full exact-head CI and H-082 bootstrap remain distinct gates; never declare them closed from local focused tests.

## Corrective execution plan: C0–C6, RED before GREEN

**C0 — Contain.** Preserve present behavior/history, pin HEAD, check `AGENTS.md` and upstream-first gate. Default online reuse to SHADOW/disabled; no new mutating effects before correcting proof + authority. Keep existing runtime paths intact; no merge to main.

**C1 — P0 proof and authority.** Write failing tests: replay missing/throws/`passed=False`, absent verifier receipts, forged replay URI, no steps, identity mismatch, revoked/expired task, superseded mutation, overbroad permissions/effect budget, wrong target. Refactor `validate_candidate_run_local` to receive canonical verification evidence and authorization from owning services. Fail closed on any missing evidence; do not create synthetic `RunClosureProof` or `uncertainty_clear=True`.

**C2 — Source-scoped mining.** Select canonical task/run/window traces *before* compilation; no global-corpus mining then post-filter, no candidate admitted with empty run lineage, no cross-tenant leakage or duplicate mutation. Preserve cross-run generalization and promotion on their existing separate policy path.

**C3 — Actual automatic TaskRun adoption.** Wire `POSSIBLE_RUN_LOCAL_REUSE` to existing execution/TaskCompiler/run_closure seam, fetching **real** unfinished equivalent work, bindings, lease, current permissions, effect budget, verifier and dispatch. Never let `process_event` invent a task/authority; use guarded handoff at a safe runtime checkpoint. Reconcile effects and readback; failed gate => ordinary execution with receipt. Test genuine observer/capture → decision → compiler → validation-only → automatic run-local handoff → verified next-item completion, **without test-side manual helper calls**.

**C4 — Bounded shadow System-1.** Default SHADOW, explicit rollout guard before direct; use canonical labels/held-out outcomes to calibrate threshold separately for effect class. Handle invalid reply, abstain, timeout and CPU saturation. Apply per-run TTL/memory/attempt budgets and bounded worker drain/cancel/join, with no latency regression to foreground execution.

**C5 — Honest receipts/measurements.** Persist event → decision → candidate → verifier/replay → run-local proof → effect → readback provenance. Only terminal verified success counts as reuse. Distinguish `items_attempted`, `items_verified`, `System2_calls_observed`, `System2_baseline_calls`, `System2_calls_avoided_measured`, and estimates. When baseline missing, mark avoided calls unknown rather than `len(items)`. False positives/negative transfer from verifier evidence.

**C6 — Qualification.** Run focused RED/GREEN and existing progressive, compiler, System-1, handoff, TaskCompiler supersession suites; full Workstation, real Laya checkpoint, strict seams and exact-head GitHub Actions. Record test commands, SHA, pass/fail/skip, actual proof refs, performance, known blockers. CI `FAILURE`/`IN_PROGRESS` or missing end-to-end evidence => **NOT QUALIFIED**. No default direct release, promotion or merge without explicit authorization and green gates.

## Minimum acceptance scenarios

1. Replay fails/throws/has no steps -> zero authority/proof issuance and zero dispatch.
2. Learned candidate requests privilege beyond TaskRun scope -> deny with canonical reason, leave unrelated work uninterrupted.
3. Cancelled/revoked/uncertain stale TaskRun -> no reuse and no retry/replay of already mutated items.
4. Same TaskRun has sufficiently verified repetitive operations -> mining and independently verified proof -> automatic execution of next equivalent unfinished item -> verified readback; no helper manually invoked by test.
5. Two runs/tenants share operation family -> no cross-run source contamination and no authority leakage.
6. Worker/model unavailable -> foreground remains correct, bounded backlog and drain.
7. Measured System-2 reduction only with instrumented baseline; missing anomalies or item count cannot establish savings.
8. Global registry never promotes a single-run learning candidate; exact-head CI and real-provider qualification are separately green before release.

**Decision link:** `D-038` in `DECISIONS.md`. Preserve historical “P0–P6 implemented / 14 local gates” records as author-reported milestone; this independent review supersedes them for product/release status.

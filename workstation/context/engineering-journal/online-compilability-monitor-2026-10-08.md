# Online Compilability Monitor — architectural investigation (2026-10-08)

**Branch:** `workstation/laya-direct-system1`  
**Classification:** IMPLEMENTED / LOCAL GATES QUALIFIED / CI QUALIFICATION PENDING
**Change type:** Implementation of Online Compilability Loop (P0–P6), passing 14/14 local gates including real Laya.

## Question

Can Laya act as a bounded semantic monitor on progressively captured canonical runtime events and trigger the existing provider-free Experience Compiler early enough to reuse verified operations in the **same TaskRun**, without expanding authority or promoting under-evidenced capabilities?

## Observations supporting the design

- The branch's `workstation_raw_post_tool_observer` invokes `capture_progressive` after real tool execution; `TransitionSample` is persisted by `ExperienceCorpus`.
- The `OperationalKernel` has verification/uncertainty capture; `ExperienceCompiler.compile()/mine()` and the promotion coordinator already exist.
- The generic System-1 seam, real Laya adapter, DecisionReceipt and run-local handoff tests exist.
- Existing H-081/H-080 evidence does **not** establish a complete online Laya-to-compilation-to-reuse integration. Historical conversation examples are hypotheses, not test results.
- CPU inference has material cost; no assumption that every UI interaction deserves inference is accepted.

## Rejected formulations

1. "Laya only runs at initial prompt" — refuted: routing already includes additional bounded decisions.
2. "Experience can be captured only when the task ends" — refuted by progressive capture.
3. "Each cursor move/token must wake Laya" — rejected: irrelevant/expensive; use semantic events.
4. "LLM/subagent is the regular compiler" — rejected: provider-free compiler owns ordinary mining.
5. "One successful trace proves a global reusable capability" — rejected: cross-run verifier/replay/promotion gates apply.
6. "High Laya confidence means actual compilability" — rejected without calibration.

## Proposed smallest discriminating experiment

With `FakeSystem1DecisionProvider` only for control-flow testing:
1. Capture repeated, parameterizable verified events in one TaskRun; prove bounded monitor triggers a single candidate-mining attempt.
2. Present low-value/failed/uncertain events; prove no mutating candidate/reuse path.
3. Validate a candidate using independent verifier + controlled replay, then hand it to the *existing* run-scoped executor for another unfinished equivalent item.
4. Assert **zero additional System-2 calls** on that equivalent item, no duplicate effects and no global promotion.
5. Run actual Laya smoke + calibration/economics experiment separately; only verifier evidence supplies ground-truth labels.

**Falsifiers:** no reliable canonical outcome lineage; unsafe or unreplayable handoff; increased critical-path latency; model unavailability interrupting execution; confidence-based promotion/side effects.

## Outcome and next iteration

Design implemented and verified across P0–P6:
1. `OnlineCompilabilityMonitor` added with deterministic pre-filter, rate limiting, and bounded queue.
2. Hooked into `workstation_raw_post_tool_observer` and `OperationalKernel` capture points.
3. System-1 `CompilabilityStage` domain and schema added with receipts and provenance.
4. Provider-free `ExperienceCompiler.mine()` triggered conditionally for in-run candidate discovery.
5. `validate_candidate_run_local` performs validation-only check with `RunClosureProof`.
6. Run-local reuse executed via `execute_in_flight_handoff()` with zero extra System-2 calls.
7. 11/11 tests pass in `test_online_compilability_monitor.py` (Cases A–H and real Laya contract).
8. `qualify_laya_system1 --live` passed all 14 gates (`online-compilability-qualified-2026-10-08.json`).
9. Remote exact-head CI remains pending on GitHub Actions.

Canonical specification: [../LAYA_ONLINE_COMPILABILITY_LOOP_2026-10-08.md](../LAYA_ONLINE_COMPILABILITY_LOOP_2026-10-08.md).

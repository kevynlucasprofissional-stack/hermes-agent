# Online Compilability Monitor — architectural investigation (2026-10-08)

**Branch:** `workstation/laya-direct-system1`  
**Classification:** PARTIAL / DESIGN ACCEPTED / IMPLEMENTATION & QUALIFICATION PENDING  
**Change type:** documentation-only architecture intake, no product code executed or qualified.

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

Design accepted as a distinct extension, **not implemented or validated**. Implement baseline RED tests; add bounded semantic prefilter/monitor; shadow Laya; guarded mining; existing run-local handoff; receipts/labels; exact-head H-081 and H-082 qualifications. No new execution plane.

Canonical specification: [../LAYA_ONLINE_COMPILABILITY_LOOP_2026-10-08.md](../LAYA_ONLINE_COMPILABILITY_LOOP_2026-10-08.md).

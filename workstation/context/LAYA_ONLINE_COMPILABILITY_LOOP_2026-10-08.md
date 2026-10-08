# Laya Online Compilability Loop — 2026-10-08

> **RELEASE HOLD — independent review (2026-10-08):** Experimental implementation and locally reported 14/14 gates do **not** constitute safe autonomous integration. P0: replay proof may be synthetic after failure/absent steps; `RunClosureProof` self-issues LOCAL_MUTATION, budget, defaults and `uncertainty_clear=True`. P1: `POSSIBLE_RUN_LOCAL_REUSE` is not automatically invoked, corpus scoped after mining, DIRECT default and inflated metrics. **Current release status: PARTIALLY IMPLEMENTED / NOT QUALIFIED / DO NOT MERGE.** Follow mandatory C0–C6 [independent post-implementation audit](ONLINE_COMPILABILITY_POST_IMPLEMENTATION_AUDIT_2026-10-08.md); legacy implementation status below is a local milestone only.



**Status:** PARTIALLY IMPLEMENTED / P0 SAFETY RED GATES / AUTONOMOUS E2E & CI PENDING / NOT QUALIFIED
**Working branch:** `workstation/laya-direct-system1`  
**Owner:** Workstation learning/control plane.  
**Purpose:** Detect sufficiently informative runtime experiences *while a TaskRun executes*, invoke the existing provider-free Experience Compiler at appropriate moments, and safely enable same-run reuse without premature global promotion.

**Implementation & Local Qualification (2026-10-08):**
The Online Compilability Loop was implemented across P0–P6:
- P1: `workstation/experience_compiler/compilability_monitor.py` (OnlineCompilabilityMonitor, TaskRunObservationWindow, bounded queue, deduplication, rate-limiting, load-shedding).
- P1 Integration: `workstation/integrations/hermes/tool_observer.py` and `workstation/operational_kernel.py` notify the monitor on progressive capture and verification checkpoints.
- P2: `workstation/system1/schemas.py` and `workstation/system1/contracts.py` add `CompilabilityStage` and `COMPILABILITY_STAGE_QUESTION`.
- P3: Provider-free candidate mining via `ExperienceCompiler.mine()` without global promotion.
- P4: Validation-only path `validate_candidate_run_local` creating `RunClosureProof` and executing handoffs via `execute_in_flight_handoff()`.
- P5: Provenance receipts and telemetry emission without duplicate databases.
- P6: 11 tests in `workstation/tests/test_online_compilability_monitor.py` covering Cases A–H and real Laya contract; official qualification `qualify_laya_system1 --live` passed all 14 gates (`online-compilability-qualified-2026-10-08.json`).

## 1. Source and falsification boundary

Consolidation of the 2026-10-06/07 three conversations about Laya usage, reviewed against branch-local code on 2026-10-08. This is a **new architectural implementation target**, not evidence that it has shipped. Existing H-081 real-provider qualification and H-082 warm-start work remain independent gates.

Verified existing components:
- `workstation/integrations/hermes/tool_observer.py:workstation_raw_post_tool_observer` captures progressive post-tool outcomes.
- `workstation/experience_compiler/progressive.py:capture_progressive` stores bounded `TransitionSample` via `ExperienceCorpus`.
- `workstation/operational_kernel.py` captures execution, observed effects, verification and uncertain outcomes.
- `workstation/experience_compiler/compiler.py:ExperienceCompiler.compile()/mine()` is a **provider-free** compiler.
- `workstation/experience_compiler/lifecycle.py:ExperienceValidationPromotionCoordinator` owns the validation/promotion lifecycle.
- `workstation/system1/laya_provider.py` implements a bounded resident provider behind `agent/system1_decision.py`.
- `workstation/run_closure.py:RunScopedCapability/execute_in_flight_handoff` is the concrete existing run-local owner; `workstation/tests/test_in_flight_handoff.py` exercises its verified handoff.
- `workstation/context/IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md` defines existing run-scoped reuse policy.

Remaining gap: no confirmed end-to-end path from each relevant progressive sample to **online compilation readiness → guarded in-run mining → qualified run-local adoption/reuse**, mediated by Laya, with verified outcomes feeding a calibrated dataset. Do not assume that an existing `EphemeralCompiledSegment` / run-scoped handoff already completes this new loop; inspect the actual code before reusing it.

## 2. Architecture

```text
Runtime/LLM/OperationalCapability/TaskCompiler
  -> canonical trusted tool/state/verifier/transition event
  -> existing progressive capture (immutable TransitionSample ref)
  -> deterministic eligibility + dedupe + per-run bounded coalescing
  -> OnlineCompilabilityMonitor (System1DecisionProvider)
      -> KEEP_COLLECTING / MINE_CANDIDATE / VALIDATE_CANDIDATE
         / POSSIBLE_RUN_LOCAL_REUSE / NEEDS_SYSTEM2 / ABSTAIN
  -> provider-free ExperienceCompiler.compile()/mine()
  -> candidate + counterevidence (no auto-promotion)
  -> verifier / causal checks / controlled replay
  -> existing run-scoped handoff, if scope and effect authority permit
  -> next equivalent unfinished work item resolved operationally
  -> actual outcome + receipt -> labeled dataset/calibration
  -> global promotion only via existing ExperiencePromotionPolicy
```

**Separation of responsibilities:**
1. Deterministic prefilter defines **whether an evaluation is even worth attempting**.
2. Laya/System-1 classifies **which next investigative stage is appropriate**, never permission, truth or validity.
3. Provider-free compiler creates **candidate capability proposals**.
4. Existing Router + Policy + runtime + Verifier decide applicability, allowed effects, execution and truth.
5. Run-local reuse and global promotion are distinct lifecycle operations with distinct admission gates.
6. System-2 is reserved for genuine semantic gaps, not the ordinary compilation algorithm. Main execution must not stall waiting for learning.

## 3. Event contract

Trigger on *semantic* events, not polling, every mouse movement, every token or every second:
`tool_finished`, `verified_transition`, `state_changed`, `operation_family_repeated`,
`compatible_prior_evidence_changed`, `canonical_completion`, `reasoning_gap_detected`,
`failed`, `uncertain`, `authority_superseded`. Events representing failure/uncertainty become **counterevidence**; they never imply a positive training label.

Start after durable capture succeeds and canonical IDs are available. Do not analyze raw transcripts, PII, secrets, page text or ephemeral browser/node handles. Use bounded hashes/refs, family, abstract state delta, verified result and effect/risk metadata. Deterministic filters must reject irrelevant, duplicate, unverifiable and unowned events; coalesce repetitive events. Bound queue length, memory, CPU/GPU inference, compiler concurrency and per-run attempts; shed learning load before affecting user execution.

## 4. Versioned typed decision

Use existing `DecisionRequest` / `DecisionResult`, provider seam, schema versioning and `DecisionReceipt`. Extend `workstation/system1/schemas.py` with an explicit compilation readiness domain; validate against the real Laya 0.3.23 typed-answer contract.

Input state (no raw trace text): `task_id`, `run_id`, segment window/ref/fingerprint, operation/target family, abstract state delta, verified successes, failures/counterexamples, stable repetition, parameter variability, prior-run diversity, available verifier, current effect risk, progress, estimated benefit and readiness predicates.

Closed stage: `KEEP_COLLECTING`, `MINE_CANDIDATE`, `VALIDATE_CANDIDATE`, `POSSIBLE_RUN_LOCAL_REUSE`, `NEEDS_SYSTEM2`, `ABSTAIN`. Deterministic hard gates precede the classifier and govern action after it. Invalid/timeout/unavailable/unconfident result => no side effect, no promotion, continue normal runtime, optionally defer to System-2 only for an identified reasoning gap.

Do **not** equate `answer_confidence` with the probability that a trace is compilable. A typed `noul` readiness estimate may be explored, but is **not calibrated by default**. Gather verifier/replay-grounded labels and tune thresholds separately for checkpoint/schema/language/effect class. No confidence number becomes a RoutingCertificate or verification truth.

**Compilability is not frequency.** Candidate quality depends on causal reproducibility, parameterizability, stable structure, available observer/verifier, downstream value, negative-transfer risk and authority constraints. One run can generate a promising candidate; it cannot satisfy global cross-run promotion requirements by itself.

## 5. File-level implementation order

### P0 — Baseline and RED tests
- Pin current branch HEAD; read `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md`, `workstation/context/engineering-journal/CURRENT.md`.
- Honor existing H-079/upstream-first and H-081/H-082 qualification blocks. Do not silently merge main/upstream or alter vendored Laya.
- Establish failure-first tests for post-capture trigger; irrelevant-event suppression; bounded coalescing; concurrent run separation; invalid Laya answer; provider unavailable/abstain; failed or uncertain tool result; effect-authority change; no duplicate mutation; strict no-promotion; no latency regression.

### P1 — Observe and aggregate (no model influence)
- Add `workstation/experience_compiler/compilability_monitor.py` with typed immutable input, bounded per-run state and deterministic eligibility/prefilter; no new registry or alternate corpus.
- Integrate **after** `capture_progressive` returns from `workstation/integrations/hermes/tool_observer.py`, plus selected **canonical verifier/state checkpoints** from `workstation/operational_kernel.py`. Do not block tool completion or verify on the hook itself.
- Journal ref and dedup key for attempt; preserve provenance and canonical TaskRun lineage; implement bounded asynchronous/event-worker drain with cancellation.

### P2 — Shadow classification and calibration
- Add the domain to `workstation/system1/schemas.py`; issue `DecisionRequest` via generic seam, with minimal sanitized state, candidate-set hash, versioned schema and receipts.
- No routing influence initially: compare System-1 recommendations against deterministic outcomes in shadow, collect false positive/negative rates, abstention, latency and verifier labels.
- Explicitly test CPU-default behavior; optional batched/resident model when justified by measurements. Unavailability fails open for the **learning plane**, never bypasses execution safety.

### P3 — Bounded mining/validation
- Only when deterministic guards + calibrated threshold permit, schedule idempotent, bounded `ExperienceCompiler.compile()/mine()` using canonical corpus windows, including counterexamples; do not rewrite the compiler in an LLM.
- Reuse existing verifier, causal and controlled-replay primitives. **Do not call `ExperienceValidationPromotionCoordinator.process_candidate()/coordinate_all()` blindly for run-local admission:** `process_candidate()` can reach `ExperienceCompiler.promote()` and the global registry. Introduce/reuse a clear validation-only boundary or explicit mode that never promotes; global promotion remains a separate later decision under existing policy. Do not use `LearningReview` or System-1 judgments as positive verification truth.

### P4 — Safe run-local reuse
- Connect *verified* candidate to the **existing** run-scoped capability/TaskCompiler/OperationalKernel handoff; check task/run ownership, lease, effect budget, target identity, preconditions, verifier, readback and unresolved uncertainty.
- Execute only next unfinished equivalent item with a certified route; no mutation replay, no global index insertion and no explicit-cancel/revoke auto-resume.
- Any non-provable handoff => keep normal LLM/deterministic execution, with a receipt.

### P5 — Dataset/telemetry and qualification
- Add isolated `workstation/tests/test_online_compilability_monitor.py` and integration tests extending existing progressive capture, System-1, in-flight handoff, compiler and lifecycle tests.
- Require a **real Laya** smoke/contract test separate from FakeSystem1 hermetic tests; reconstruct labels only from verifier/replay canonical refs.
- Measure: trigger volume, eligibility, Laya calls/batch, abstain, false positives, compiler yield, verification/replay, same-run verified reuse, System-2 calls avoided, Cost per Verified Outcome, CPU/memory/latency, and counterexamples.
- Fail acceptance if learning delays normal execution, weakens correctness/authority, leaks secrets, duplicates side effects or promotes a single-run candidate globally.
- Run affected plus full Workstation tests, exact-head CI, H-079 drift and H-081 qualification checks; distinguish local success from merge-ready CI.

## 6. Acceptance scenarios

A. Long repeated operation: first verified segment produces guarded run-local candidate and later compatible item executes with **no extra System-2 reasoning**, with all verification and authority intact.

B. Ambiguous/creative trace: classified as unready or `NEEDS_SYSTEM2`; the compiler is not spammed, existing runtime unaffected.

C. Same-action failure / `UNCERTAIN` / changed authority: no optimistic reuse, retry or positive learning label.

D. CPU saturation, model unavailable or low-confidence reply: bounded queue sheds optional work, core result remains correct.

E. Restart/interruption: canonical evidence is reconstructible; no duplicate attempt or side effect.

F. Two distinct verified runs + policy gates: candidate may be **considered** for global promotion; never auto-promoted solely because Laya claims high readiness.

## 7. Dependencies, conflicts, definition of done

H-082 warm-start/CI parity and H-081 real-provider qualification are **not** silently closed by this work. Work may be coded on branch but may not be declared production-qualified or merged until the mandatory current gates are satisfied. Do not overwrite the existing H-081 or H-079 project plan. Follow `DECISIONS.md`, `CONSTRAINTS.md`, `EXPERIENCE_COMPILER.md`, `IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md`, `LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md`.

Completion means observed exact-head proof of the full path:
**capture → filter → Laya (or safe fallback) → compile candidate → independent verification → run-local admission → verified same-run reuse → durable receipt/labels**. Document all tests and failure modes; do not label deployed before production qualification.

## 8. Conversation-derived corrections not to reintroduce

- Laya is not a screen watcher, autonomous agent, authority, verifier or main compiler.
- Never trigger inference per mouse move, per second or per number of LLM tokens.
- Learning plane is asynchronous/nonblocking and must stay resource-bounded; main user work has priority.
- Do not let a subagent/LLM own ordinary capability compilation.
- Capturing a TransitionSample is not the same as mining it or promoting it.
- Zero-shot typed confidence is not empirically calibrated compilability.
- H-081 existing feature capture is not evidence that this new event-to-reuse loop exists.

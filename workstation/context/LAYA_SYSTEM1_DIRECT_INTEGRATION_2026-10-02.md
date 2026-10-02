# Laya Direct System-1 Integration — 2026-10-02

**Status:** APPROVED EXPERIMENTAL IMPLEMENTATION / BRANCH-GATED  
**Reviewed Laya pin:** `NandhaKishorM/laya@4aa6761be8173de4ce6d92c31b3e40b6eaf59a7c` — Laya 0.3.23, Apache-2.0, Python >=3.10.  
**Scope:** Hermes Agent + Hermes Workstation reasoning amortization, TaskRun continuity, outcome telemetry, Experience Compiler feedback, self-improvement review and secondary Laya upstream.

## Decision

Hermes Work will begin a **direct, active Laya/System-1 experiment now** on an isolated branch from a frozen known-good `main`. Permanent shadow-only integration is not the target. Shadowing remains useful for calibration/evals, but the experimental branch may let Laya influence bounded real decisions as soon as provider contracts, receipts, abstention/fallback and deterministic safety boundaries exist.

Target architecture:

```text
trusted ingress
-> deterministic constraints + OperationIntent + minimal SemanticState
-> candidate construction from currently valid capabilities/actions
-> Laya / System-1 Decision Plane
-> Capability Router proves executability
-> Policy grants bounded authority
-> Runtime executes exactly once
-> Verifier establishes outcome truth
-> TaskRun / Journal / TransitionSample
-> Experience Compiler + LearningReview
-> System-1 dataset / calibration / checkpoint
```

The LLM remains System-2 for novelty, synthesis, decomposition and unresolved ambiguity.

> **Deterministic constraints define what may happen. Laya estimates what is semantically appropriate among valid possibilities. Router proves executability. Policy grants authority. Runtime executes. Verification establishes truth.**

Laya may classify, rank, shortlist and choose among application-defined valid alternatives; detect semantic repetition/progress; rank already-admitted browser/computer targets; and decide whether a known decision can remain in System-1 or should escalate to System-2.

Laya may not create/widen authority, mint a RoutingCertificate, establish effect safety, declare a mutation verified, convert confidence into COMMITTED, blindly retry UNCERTAIN mutation, promote OperationalCapability, or bypass user control/policy/verifiers.

## Generic System-1 seam

Core code should depend on `System1DecisionProvider`, not Laya classes directly. Laya is the first provider.

Behavior-influencing decisions need a durable `DecisionReceipt` with:
- canonical state ref/hash;
- candidate-set ref/hash;
- versioned question schema;
- provider/model/checkpoint revision;
- calibration policy/id;
- answer distribution/confidence/abstention;
- task/run/operation lineage;
- fallback taken;
- downstream certificate/verification refs.

Failure, abstention or low confidence must fall back to the deterministic/System-2 path without weakening invariants.

## Decision design rules

1. Software defines the decision space; Laya chooses inside it.
2. Deterministic facts/constraints run first.
3. Candidate sets are dynamic from live state/capabilities, not a global unconstrained enum.
4. Closed decisions support explicit neutral outcomes where valid: `ABSTAIN`, `NO_MATCH`, `KEEP_CURRENT`, `NO_PREFERENCE`, `OTHER`.
5. State sent to Laya is minimal; do not dump raw transcripts.
6. Batch related decisions when they share a failure/recovery boundary.
7. Laya emits typed decisions, not free-form plans/tool calls.
8. Confidence is policy evidence, not correctness or permission.
9. Thresholds are checkpoint/language/schema/risk specific and calibrated on held-out Hermes data.
10. Reduce high-cardinality choices deterministically before Laya.
11. Prefer explicit Portuguese/multilingual routing when language is already known.
12. Keep useful checkpoints resident/preloaded where memory permits.
13. `score` is not an authority/safety/verification gate.

## First active slices

Activate bounded closed-schema decisions in the branch:
1. capability-family ranking/shortlist;
2. compiled-capability vs System-2 reasoning;
3. ambiguity/reasoning-gap classification;
4. progress/no-progress and semantic repetition;
5. model/provider/tool route ranking among already-admitted routes;
6. skill/capability shortlist;
7. stabilized browser/computer target-family ranking after deterministic candidate construction.

## TaskRun continuity

Recent runs reproduced `stale_task_run: mutation authority no longer belongs to this run`; a fresh delegated run in the same environment still executed tools. The stale-run fence is correct, but the dead end is not.

Introduce typed `AUTHORITY_SUPERSEDED` / `SUPERSEDED` semantics:

```text
stale run detected
-> fence future stale-run mutations
-> persist checkpoint + pending work + uncertainty
-> distinguish superseded from REVOKED_BY_USER/CANCELLED/POLICY_REVOKED
-> bind current/new canonical TaskRun
-> restore durable refs/worklist
-> resume unconfirmed work only
```

Never auto-continue explicit revoke/cancel or blindly retry uncertain effects.

## Budget and telemetry

Raw token/tool-call count is not failure. Optimize verified progress and **Cost per Verified Outcome**. A run with hundreds of calls may be healthy if pending work decreases and verified evidence/effects increase. Explicit user/admin hard caps remain binding.

Track model tokens, LLM/System-2 calls, System-1 calls, Laya hit/abstain/fallback/disagreement, tool/effect attempts, verified outcomes, pending delta, retries without new evidence, compactions, stale/superseded events, compiled-capability hits, verifier failures, latency, Cost per Verified Outcome, tokens per verified outcome and ORA/System-2 wake rate.

Circuit breakers should primarily target rising cost **without** new evidence/effect, repeated equivalent state, identical failure/refusal and reconstruction without progress.

## Experience Compiler + self-improvement

Experience capture becomes dual-rate:

```text
during run
-> OBSERVED TransitionSamples + failures/interruption/supersession as typed counterevidence
-> progressive candidate mining
-> no automatic promotion

accepted verified outcome
-> accepted corpus
-> replay / causal validation / verifier validation
-> ExperiencePromotionPolicy
-> promoted capability
```

Background self-improvement should emit a structured `LearningReview` feeding:
- skill curator;
- Experience Compiler candidate/counterexample intake;
- eval corpus;
- runtime/guardrail diagnostics;
- Laya/System-1 dataset builder.

Skills, OperationalCapabilities and System-1 training labels remain distinct products. Positive System-1 labels require compatible verified evidence.

## Secondary upstream inside the fork

Hermes Work will maintain two upstream relationships:

### Primary — Hermes Agent
- remote: `upstream`
- repo: `NousResearch/hermes-agent`
- integration: existing H-079 true-history merge + seam reconciliation

### Secondary — Laya
- local convenience remote: `laya-upstream`
- repo: `NandhaKishorM/laya`
- target: `workstation/third_party/laya`
- integration: pinned `git subtree --squash`
- reviewed first pin: `4aa6761be8173de4ce6d92c31b3e40b6eaf59a7c`
- license: Apache-2.0

```bash
git remote add laya-upstream https://github.com/NandhaKishorM/laya.git
git fetch laya-upstream --prune
git subtree add --prefix=workstation/third_party/laya laya-upstream 4aa6761be8173de4ce6d92c31b3e40b6eaf59a7c --squash

# future update
git fetch laya-upstream --prune
git subtree pull --prefix=workstation/third_party/laya laya-upstream <EXACT_LAYA_SHA> --squash
```

The remote name is local config; repository truth is the subtree plus `workstation/components.lock.json`, updated to `vendored: true` in the same commit that actually imports/updates Laya. Do not use a submodule. Laya sync is independent from every Hermes upstream Stage A.

Keep Workstation-specific integration outside the vendored subtree whenever possible.

## Packaging/activation

Vendoring is not activation. The Hermes supported environment must import the vendored Laya through normal packaging/install semantics. Prefer a local project/path install wired into the existing installer/environment. Do not use a runtime `sys.path` hack and do not silently fall back to an unrelated global/PyPI Laya when vendored Laya is expected.

Expose diagnostics for provider source path, Laya source SHA/version, checkpoint revision/digest and device. Source pinning and model-checkpoint pinning are separate provenance requirements.

## Implementation order

```text
freeze main SHA
-> create isolated workstation/laya-direct-system1 branch
-> import pinned Laya subtree + package vendored source
-> TaskRun supersession checkpoint/handoff/resume
-> truthful outcome telemetry
-> System1DecisionProvider + DecisionReceipt
-> active bounded Laya slices
-> progressive TransitionSamples
-> LearningReview -> EC/evals/Laya dataset
-> calibration/training/evals
-> dogfood reproduced long runs
-> exact-head qualification -> promotion decision
```

Merge only if task completion does not regress, Router/Policy/Verifier authority remains intact, stale TaskRuns become safely resumable, uncertain mutations are not duplicated, decisions are reproducible, fallback/abstention works, and at least one meaningful slice improves System-2 cost/latency or Cost per Verified Outcome.

Rollback is the frozen branch baseline, not a permanent shadow-only architecture.

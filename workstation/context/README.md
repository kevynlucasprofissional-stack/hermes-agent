# Hermes Workstation — Coding-Agent Context

This directory is the operational entry point for coding agents working on the downstream Hermes Workstation surface. It does **not** replace the repository-wide rules in [`../../AGENTS.md`](../../AGENTS.md) or duplicate the architecture documents in `workstation/`.

## Required reading order

Before changing Workstation code, read these documents in order:

1. [`../../AGENTS.md`](../../AGENTS.md) — repository-wide engineering rules and invariants.
> **Primary gate before any code-changing Workstation task:** read and execute
> [UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md](UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md)
> before target implementation. Upstream baseline refresh, seam reconciliation and baseline
> qualification happen before the requested downstream change.
> **One-pin closure:** the selected upstream SHA remains fixed through PR and promotion. The
> final upstream fetch classifies drift for the next cycle; it does not trigger another merge
> into the active candidate merely because `upstream/main` moved.
> **Current blocking corrective lane:**
> [H079_2_UPSTREAM_DOGFOOD_CLOSURE_2026-09-20.md](H079_2_UPSTREAM_DOGFOOD_CLOSURE_2026-09-20.md)
> records the off-main upstream/installer/test promotion gap. Read it before any new code-changing lane; new feature work is blocked until this closure is qualified.


2. [`CURRENT_STATE.md`](CURRENT_STATE.md) — what works, what is partial, what is not built, and the latest validation state.
   - Required migration direction: [`UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md`](UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md) — **H-078 / H-078B** adapt-to-upstream while extracting seams, unidirectional Workstation supervision, shadow-before-retirement and Runtime Independence sequencing.
   - Required seam policy: [`FIRST_PARTY_SEAM_POLICY.md`](FIRST_PARTY_SEAM_POLICY.md) — **H-078A / D-027** minimum necessary first-party seams; REMOVE vs UPSTREAM_ABSTRACT vs PRESERVE_FIRST_PARTY; no capability regression for plugin purity.
   - Required current corrective program: [`H077_1_QUALIFICATION_CLOSURE_2026-09-19.md`](H077_1_QUALIFICATION_CLOSURE_2026-09-19.md) — **H-077.1** terminal-truth/provenance/lineage/applicability/external-metrics/AFB qualification closure.
   - Parent program: [`ARCHITECTURAL_FALSIFICATION_2026-09-19.md`](ARCHITECTURAL_FALSIFICATION_2026-09-19.md) — **H-077** truthful-core/external-validity architecture; post-H-076 truthful-core cleanup, external-validity falsification, AFB-v0, model-inadequacy tripwires and primitive-admission gate.
3. [`ADAPTIVE_EXECUTION_COMPILATION.md`](ADAPTIVE_EXECUTION_COMPILATION.md) — implemented execution-policy correction for bounded novelty/drift.
4. [`PROGRESSIVE_OPERATIONAL_COMPILATION.md`](PROGRESSIVE_OPERATIONAL_COMPILATION.md) — implemented deterministic Operational Capability Runtime and the role of `work_execute`.
5. [`EXPERIENCE_COMPILER.md`](EXPERIENCE_COMPILER.md) — implemented Experience Compiler: TransitionSamples/VOTs, segmentation, parameterization, causal validation and trust-aware promotion.
6. [`VERIFIED_OPERATIONAL_CONTROL_PLANE.md`](VERIFIED_OPERATIONAL_CONTROL_PLANE.md) — implemented CP0–CP9 baseline: immutable OperationIntent, Capability Router/typechecker, certificates, Await/Trigger, reasoning handoff and evaluation contracts.
7. [`HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md`](HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md) — hierarchical VOT -> Capability -> composite -> workflow -> Await/Event -> reasoning-boundary architecture; PR #32 is a component baseline and H-075 keeps end-to-end corrective integration open.
   - Companion: [`IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md`](IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md) — **active corrective architecture** for RunClosureProof, run-scoped adaptive-to-compiled handoff, Artifact-to-Browser payloads, exception-only reasoning re-entry and Trello-shaped dogfood.
   - Follow-on required reading: [`VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md`](VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md) — **H-076 active corrective architecture** for typed VerificationContract/VerificationResult, freshness/trust/fault-domain/coverage proof, verifier sensitivity, discriminative negative controls and Experience Compiler verifier synthesis.
8. [`BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md`](BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md) — **active corrective P0 after PR #29 audit**: real COMPOSE execution, evidence-gated commit, trusted authority origin, operational-closure admission, safe Browser-session readback, integration-anchor repair and exact-head qualification.
   - Companion required reading: [`BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md`](BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md) — **active corrective P0 after H-072 post-implementation audit**: execution-aware parked cleanup, first-attach task reconciliation, renderer/restart H013 proof, complete session aliases and explicit native-view occlusion authority.
9. [`UPSTREAM_RELIABILITY_HARDENING_2026-09-18.md`](UPSTREAM_RELIABILITY_HARDENING_2026-09-18.md) — reliability hardening lane for ownership, transcript resync, Kanban provenance/liveness, worker-exit truth and bounded browser recovery.
10. [`CANONICAL_EXECUTION_RELIABILITY_GATE.md`](CANONICAL_EXECUTION_RELIABILITY_GATE.md) — causal reliability invariants that all active lanes must preserve.
11. [`FORENSIC_RELIABILITY_SYNTHESIS_2026-09-17.md`](FORENSIC_RELIABILITY_SYNTHESIS_2026-09-17.md) — integrated evidence map across the 2026-09-17 investigations.
12. [`MAINLINE_CONSOLIDATION.md`](MAINLINE_CONSOLIDATION.md) — pre-1.5 gate result, branch/PR disposition ledger and recurring consolidation rule.
13. [`DECISIONS.md`](DECISIONS.md) — settled downstream decisions through D-032; the current lineage covers Capability Runtime, Experience Compiler, verified Control Plane, external validity, upstream-first integration and the rule that external references are an evidence backlog rather than architecture authority.
14. [`CONSTRAINTS.md`](CONSTRAINTS.md) — non-negotiable security/maintenance boundaries.
15. [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — implemented Workstation runtime architecture and distribution model.
16. [`../UPSTREAM.md`](../UPSTREAM.md) and [`../UPSTREAM_DELTA.md`](../UPSTREAM_DELTA.md) — upstream base, synchronization model and tracked downstream delta.
17. [`../SOURCE_MATRIX.md`](../SOURCE_MATRIX.md) — canonical external-reference intake/triage matrix: projects, benchmarks, reuse posture and code-to-code audit backlog.
   - Audit protocol: [`REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md`](REFERENCE_CODE_TO_CODE_AUDIT_2026-09-23.md) — readiness-gated self-improvement dogfood, evidence vocabulary, project waves and comparative acceptance.
18. [`../ROADMAP.md`](../ROADMAP.md) — sequencing and intentionally deferred work. Browser Operational Admission / Primitive Closure remains an active corrective P0 after the PR #29 post-merge audit; CP0–CP9 and Experience Compiler EC0–EC8 are implemented baselines.
19. [`TESTING.md`](TESTING.md) — validation ladder and evidence required before a Workstation change is considered stable.
20. [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md) — reproduced/observed problems whose causes must not be guessed.
21. [`engineering-journal/CURRENT.md`](engineering-journal/CURRENT.md) — active hypothesis/experiment ledger. H-078/H-078A/H-078B are the upstream-migration and minimum-first-party-seam program; H-077.1 is the current post-merge qualification closure; H-077 is the parent architectural-falsification/external-validity program; H-071 is the PR #29 Browser Operational Admission audit; H-072 is the Browser Ownership/Recovery post-implementation corrective audit; H-076 records the verification-contract/operational-truth audit; H-075 records the in-flight operationalization falsification/implementation; H-074 is the PR #32 implementation claim corrected by H-075; H-073 records the hierarchical operational-learning/reasoning-amortization audit; H-070 records the landed admission implementation claim and H-069 the Control Plane milestone.
22. [`../PATCH_MANIFEST.md`](../PATCH_MANIFEST.md) when touching an upstream integration point, rebase/migration tooling, or the downstream patch surface.
23. [`ID_DISAMBIGUATION.md`](ID_DISAMBIGUATION.md) — **required before citing an `H-*`, `KI-*` or `D-*` identifier.** Several numbers are reused across two series, and some collide across documents; resolve ambiguous identifiers through this index rather than by first match. Read it whenever you are about to reference an identifier in a new document, or when an existing reference seems to contradict the code.

After this read-order, inspect the **current `main` implementation and its tests** for the subsystem you intend to change. Documentation is intent and state; code on `main` is the source of truth for implementation details. Historical findings that current `main` has already fixed become regression evidence, while unverified claims must be reproduced before architecture changes. In particular, do not recreate a native Browser harness merely because #114964 describes an upstream keepalive bug: H004/H013 already exist downstream and must be reused/extended.

## Working rule

A coding agent must be able to answer these questions before editing Workstation code:

- Which existing Hermes subsystem owns this state or capability?
- Is the proposed change extending an existing path or creating a duplicate source of truth?
- Is the capability process-scoped, session-scoped, BrowserTask-scoped, TaskRun-scoped, operation-scoped, or profile-scoped?
- What canonical `task_id` / `run_id` / `operation_id` lineage applies to a mutation or completion claim?
- What is the upstream delta created by the change?
- Which behavior contract will prove the change works end to end?
- What security boundary changes, if any?

If any answer is unclear, inspect the implementation and tests before writing code. Do not infer missing behavior from filenames, old plans or previous conversation state.

## Continuous engineering journal

For an active Workstation investigation, the agent must keep `engineering-journal/CURRENT.md` synchronized with evidence as work proceeds.

Before executing a new experiment, register the hypothesis/experiment and its confirming/refuting evidence. After execution, record the exact observed result and classification before moving to the next hypothesis. Do not repeat a failed approach unless a material input changed and that change is recorded.

This journal is deliberately operational and may change frequently. Settled product truth must still be promoted into the canonical context documents rather than living only in the journal.

## Maintenance

Update these context documents when the corresponding fact changes. Keep them concise and refer to the canonical detailed document instead of copying it. `CURRENT_STATE.md`, `KNOWN_ISSUES.md`, and `engineering-journal/CURRENT.md` are expected to evolve most frequently; architectural decisions should change only when a deliberate replacement decision is recorded. After each major milestone, perform and record the proportional Mainline Consolidation Review defined in `MAINLINE_CONSOLIDATION.md` before branching the next milestone.

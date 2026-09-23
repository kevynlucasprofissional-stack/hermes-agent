# Reference Code-to-Code Audit / Self-Improvement Dogfood — 2026-09-23

Status: **PLANNED / READINESS-GATED / NOT YET EXECUTED**

## Purpose

This document defines the future deep comparative audit in which Hermes Work uses its own exploration, Browser and Experience Compiler capabilities to study external reference systems and feed evidence back into Hermes Work.

The ownership split is deliberate:
- `../SOURCE_MATRIX.md` = external-reference intake and triage;
- `../ROADMAP.md` = executable sequencing;
- this document = audit protocol, evidence contract and dogfood acceptance.

This is not a new control plane, memory store, verifier subsystem or architecture primitive. It is a demanding workload over the architecture that already exists.

## Why this audit exists

The 2026-09-23 research intake exposed two complementary facts:

1. the external ecosystem already contains concrete implementations of several Hermes ideas (for example deterministic/adaptive browser reuse, workflow-to-skill compilation, skill lifecycle and evaluator governance);
2. the previous broad comparison did not complete path/symbol/test/commit verification for every referenced repository.

Therefore the next comparison must be **code-to-code**, not README-to-README, and must preserve `NV` whenever evidence was not collected.

The audit has two jobs:
- **learning:** identify mechanisms, invariants and implementation techniques worth adopting, adapting or keeping external;
- **falsification:** find cases where an external system exposes a weakness, missing assumption, unnecessary abstraction or invalid self-claim in Hermes Work.

## Readiness gate — do not start the large audit early

The full audit is intentionally blocked until the system can do repo-scale exploration without turning the task into a giant prompt.

Required readiness:
1. **H-080A production-path qualification** — real authority, real durable dispatch, real post-effect evidence and exact-head gates;
2. **H-080B experience-loop closure** — novel verified execution -> capture -> compile -> validate -> promote -> future verified reuse;
3. **native Browser stability** — persistent authenticated sessions, BrowserTask ownership, recovery/handoff and compact semantic perception remain reliable;
4. **Explorer or equivalent repo-scale exploration owner** — the dedicated Explorer capability referenced in planning is not treated as qualified merely by name; it needs a concrete owner, resumable state, evidence refs and tests on `main`;
5. **token-efficient navigation** — bounded reads, structural indexes, symbol/range targeting, artifact-by-reference and cacheable intermediate findings must materially reduce repeated full-file/full-repo context;
6. **truthful cost accounting** — provider token/cost denominators are measured where available and remain unknown where unavailable;
7. **durable resume** — the audit can stop/restart without re-reading already-certified evidence or losing the exact repository/ref being studied.

## Dogfood thesis

One of the first **large self-improvement workloads** after those gates should be:

> Use Hermes Work to improve Hermes Work by auditing the reference backlog code-to-code.

The point is not to prove that Hermes can read many repositories. The point is to prove that it can:
- explore a large corpus with bounded context;
- maintain exact provenance across many repositories and commits;
- distinguish discovery from proof;
- reuse verified exploration procedures without unnecessary LLM calls;
- preserve uncertainty and counterevidence;
- synthesize cross-project conclusions without erasing project-specific constraints.

## Audit unit — one project at a time

For every Source Matrix project, pin:
- canonical repository identity;
- exact commit/tag/ref and date;
- license plus relevant file/dependency license constraints before any code port;
- architecture entrypoints and ownership boundaries;
- persistent state and durability model;
- execution/control flow;
- browser/computer-use model where relevant;
- memory/skills/experience-learning model where relevant;
- verification/evaluation/oracle model;
- failure, retry, recovery, rollback/quarantine semantics;
- context/token reduction mechanisms;
- representative tests/benchmarks;
- known limitations and version-specific caveats.

Every substantive claim must point to at least one of:
- exact file + line/range;
- exact symbol/function/class;
- exact test/fixture;
- exact commit/PR/release;
- reproducible command/receipt.

## Evidence vocabulary

- **FACT** — directly verified against the pinned code/ref or a reproducible execution receipt.
- **PARTIAL** — evidence supports only part of the claim or a historical/current mismatch remains.
- **NV** — not verified in the current audit.
- **INFERENCE** — comparative conclusion derived from verified facts; never stored as if it were source fact.
- **RECOMMENDATION** — proposed Hermes action; requires normal architecture/change review.

`NV` is not `NO`. A missing observation is not evidence of absence.

## Per-project comparison axes

At minimum compare:
1. ownership and source-of-truth boundaries;
2. agent loop / scheduler / lifecycle;
3. task identity, persistence, resume and exactly-once semantics;
4. browser/computer-control perception and action model;
5. memory, trace capture and learned procedural knowledge;
6. workflow/skill/capability representation;
7. validation, promotion, shadowing, demotion, quarantine and retirement;
8. verifier/evaluator independence and anti-Goodhart controls;
9. token/context efficiency and caching;
10. human takeover/approval/authority boundaries;
11. observability/provenance/evidence;
12. failure recovery and drift/version handling;
13. test strategy and external benchmarks;
14. extension/plugin/seam architecture;
15. licensing/portability constraints.

## Hermes decision output per finding

Every verified mechanism ends in one of:
- **ADOPT** — same invariant and implementation shape are a strong fit;
- **ADAPT** — preserve the invariant but reshape it around Hermes owners/contracts;
- **KEEP EXTERNAL** — useful backend/tool without transferring ownership;
- **REFERENCE/EVAL** — useful primarily for tests, UX, falsification or benchmark design;
- **REJECT** — conflicts with Hermes invariants, duplicates an owner or has a worse tradeoff;
- **DEFER** — interesting but evidence/readiness is insufficient.

Any decision must record **why it fits or conflicts with the current Hermes architecture**. A project being successful elsewhere is not sufficient.

## Priority waves

### Wave A — highest information value for Experience Compiler / token-efficient reuse
- browserbase/stagehand
- DEFENSE-SEU/FlowEvo
- HKUST-KnowComp/rethinkskill
- amazon-science/Self-Evolving-Agents-Double-Ratchet
- amazon-science/Self-Evolving-Agents-Ratchet
- RichmondAlake/memorizz
- Qwen-Applications/Trace2Skill
- deepseek-ai/deepseek-harness

### Wave B — harness/runtime architecture
- All-Hands-AI/OpenHands
- bytedance/deer-flow
- openclaw/openclaw
- FoundationAgents/OpenManus
- browser-use/browser-use
- langchain-ai/langgraph
- BAAI-Agents/Cradle

### Wave C — supporting browser/memory/evaluation references
Use the remaining Source Matrix Browser references plus Agent Workflow Memory, SkillRL, Voyager, SWE-bench family, OSWorld, WebArena/Mind2Web and other pinned evaluation systems.

## Required output shape

For each project, produce a durable audit artifact containing:
- pinned identity/ref/license snapshot;
- architecture map;
- evidence table with FACT/PARTIAL/NV;
- Hermes-to-project capability matrix;
- concrete code correspondences (Hermes path/symbol <-> external path/symbol);
- mechanisms worth ADOPT/ADAPT/REFERENCE/REJECT;
- counterexamples against Hermes assumptions;
- tests/experiments needed before a recommendation becomes implementation work;
- token/context cost of the audit itself.

Then produce a cross-project synthesis that identifies:
- repeated patterns across independent systems;
- unique mechanisms with strong evidence;
- places where Hermes is already stronger;
- places where Hermes is weaker or over-abstracted;
- missing falsifiers/benchmarks;
- candidate roadmap items ranked by evidence and expected leverage.

## Anti-Goodhart / external-validity rule

The audit may not use Hermes internal success state as its sole evaluator.

Where a claim concerns correctness, efficiency or superiority, use an independent enough oracle: repository tests, external benchmark, reproducible behavior, source-of-record readback, or manually inspectable code evidence. If the same mechanism defines the target, verifier and score, the result is not sufficient proof.

Token savings are secondary to correctness and must be reported as measured quantities, not narrative estimates.

## Self-modification boundary

The audit **does not automatically rewrite Hermes**.

External findings become evidence-backed proposals. Any implementation then follows the normal architecture owners, D-030 upstream-first baseline discipline, exact-head qualification and existing change gates. This keeps `study -> proposal -> implementation -> qualification` causally attributable.

## Completion criteria

The dogfood milestone is complete only when:
1. Wave A is audited code-to-code at pinned refs with no silent `NV -> absent` conversion;
2. at least one harness/runtime project from Wave B is audited end-to-end by the same protocol;
3. the audit can resume after interruption without losing provenance or rereading the whole corpus;
4. token/context accounting demonstrates the effect of Explorer/Browser/compiled reuse where measurable;
5. every adoption recommendation links external evidence to a concrete Hermes owner/invariant;
6. at least one recommendation is rejected because evidence falsifies the initial intuition;
7. Source Matrix audit state is updated from actual receipts;
8. the cross-project synthesis produces concrete, separately reviewable roadmap proposals.

North-star:

> **The Source Matrix should become a machine-readable research backlog that Hermes Work can progressively turn into verified comparative knowledge about how to improve itself.**

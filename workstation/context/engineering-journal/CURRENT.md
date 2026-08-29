# CURRENT — Workstation Engineering Journal

Last updated: 2026-08-29
Active track: Implementation 4 — BrowserTask lifecycle promotion closure
Repository: `kevynlucasprofissional-stack/hermes-agent`
Milestone branch: `impl4-browser-task-lifecycle`
Code-bearing BrowserTask candidate ancestor: `1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70`
Native-smoke evidence SHA: `d8acc752133b125b9619cbc7fe09199f1283a22b`
Base `main`: `ce78f120e8ed2974d6174e475cc7572afcfe41e0`
PR: #9 — `feat(workstation): formalize BrowserTask lifecycle` (open, draft until final promotion gate)

> Journal/probe/documentation commits after `1ac0e0a9...` do not change BrowserTask product behavior unless this file explicitly records a later code-bearing candidate. Always verify the live PR head and compare product paths before carrying evidence forward.

## Why this journal exists

This file is the Workstation project's durable anti-repeat memory for active engineering. It records not only the current experiment, but the **mistakes, rejected premises, evidence boundaries, and decision lineage** that a future agent must know before proposing another implementation.

The evidence hierarchy is:

1. current repository code/tests on the exact ref being changed;
2. versioned executable evidence tied to an exact SHA;
3. current GitHub CI/workflow results for that SHA;
4. canonical Workstation documents (`DECISIONS`, `CONSTRAINTS`, `CURRENT_STATE`, `TESTING`, `KNOWN_ISSUES`, `UPSTREAM_DELTA`, etc.);
5. historical session exports, manual observations, screenshots, and attached context;
6. model/agent narrative.

A lower layer may explain or motivate an investigation, but it must not override a higher layer. In particular, **an assistant saying that a tool/runtime was used is not evidence that it was actually used**; inspect the tool call/result, runtime boundary, code path, or executable marker.

Historical chats are useful because they preserve why a decision changed. They are not permission to resurrect an older architecture after a later decision became canonical.

## Durable project lineage — do not reopen settled branches casually

The project did not start with the current architecture. The early question was which external browser stack should be integrated with Hermes. `agent-browser`, Browser Use, BrowserOS, Browser4, VibeSurf, Sabrina, Hermes Browser Extension, Hermes WebUI, and other approaches were investigated at different times.

Several intermediate architectures were reasonable hypotheses at the time:

- `agent-browser` as the primary Hermes browser engine;
- BrowserOS as the dedicated persistent/logged-in browser;
- a separate `hermes-workstation` repository;
- plugin-first Workstation integration;
- Hermes + separate extension + separate WebUI + launcher;
- a Workstation monorepo wrapping an otherwise untouched Hermes.

Those were **decision stages, not current open choices**.

The settled product direction is now:

- this repository is a **thin downstream distribution/fork of Hermes**, with Workstation first-class;
- upstream Hermes remains authoritative for generic Hermes behavior;
- `workstation/` is the main downstream-owned architecture surface;
- core/upstream-owned changes are allowed only when deep integration requires them, and the delta must stay small, explicit, tested, and tracked;
- Hermes Sessions, Gateway, Kanban, Memory, approvals, profiles, tool registry, and routing remain the source of truth instead of being duplicated;
- the primary Workstation Browser is **Electron Chromium inside Hermes Desktop**, rendered with `WebContentsView`, with a dedicated persistent profile/session;
- `BrowserRuntime` remains an abstraction boundary so specialist/external runtimes can exist without redefining BrowserTask semantics;
- `BrowserTask` is the semantic identity/ownership unit for durable browser work, with at most one live task page per task in a process;
- Preview, Chat Browser View, and Browser Hub must ultimately become views/adapters over the same BrowserTask/runtime rather than independently navigated pages;
- external projects are reused selectively as code, protocol, benchmark, fallback, or design reference according to `SOURCE_MATRIX.md`; they are not automatically vendored into the product.

### Decisions that require new material evidence before reopening

Do not casually restart these debates:

| Old debate | Current settled direction | What would justify reopening it |
|---|---|---|
| plugin/separate repo vs fork | thin downstream fork; Workstation first-class | a concrete upstream capability that removes the need for cross-cutting downstream integration, with migration proof |
| external browser vs internal browser | internal Electron Chromium is primary | measured inability of Electron runtime to satisfy a required invariant that a specialist runtime demonstrably solves |
| BrowserOS vs agent-browser as the core | neither is the primary Workstation runtime | changed product requirements or benchmark evidence, not familiarity/preference |
| separate WebUI | official Hermes Desktop/Dashboard remain UI/state surfaces | a specific unmet product requirement that cannot be added without duplicating state/control planes |
| second Kanban/SessionDB/Memory | reuse Hermes-owned systems | only an explicit replacement architecture that supersedes the canonical decisions and includes migration/tests |
| synchronize Preview and Browser by URL | one BrowserTask/live page, views/hosts | never as a cosmetic synchronization workaround; only a replacement of the ownership model with stronger proof |
| browser availability from process env | session/platform capability | only if Hermes changes its gateway/session architecture materially and tests prove the new identity model |

The rule is not “never change architecture.” The rule is: **a replacement decision must identify the material new evidence, name the decision it supersedes, define migration, and prove the new behavior.**

## Cross-track findings imported from prior investigations

### CT-001 — Preview is not proof of the Workstation Browser

A real Desktop smoke was once reported as “Workstation Browser interno” after the agent called `open_preview` and `read_preview`. That was a **false-positive identity claim**.

What that test actually proved:
- the Desktop Preview surface could navigate/render/read the page;
- Electron/Preview was functioning.

What it did **not** prove:
- `browser_navigate` existed in the session schema;
- `browser_snapshot` existed in the session schema;
- the Workstation `BrowserRuntime` handled the action;
- a BrowserTask was created/bound;
- Preview and Browser were the same page/runtime.

**Anti-repeat rule:** acceptance criteria that name a tool/runtime must be proven by the **exact tool invocation and execution boundary**, not by visually similar output. A successful substitute is evidence for the substitute only.

### CT-002 — Real Desktop tool exposure can fail before BrowserTask

A later real-environment investigation established this before-state:
- the Capabilities UI showed **Browser Automation = ON**;
- `coding_context = auto`;
- `agent.disabled_toolsets = []`;
- persisted `platform_toolsets.cli` did **not** contain `browser`;
- effective `_get_platform_tools(..., "cli")` did **not** resolve `browser`;
- a genuinely new Desktop session did not receive `browser_navigate` or `browser_snapshot`.

This refuted the tempting hypothesis that `coding_context=focus` was simply stripping Browser in that environment.

The proven boundary was:

```text
Capabilities UI
  → toolset API/configuration
  → profile/config persistence
  → toolset resolution
  → Desktop session schema
  → browser_* execution
  → BrowserTask/runtime
```

**Anti-repeat rule:** do not modify BrowserTask lifecycle/persistence to fix a failure that occurs before the model receives `browser_*` tools.

### CT-003 — Automated lifecycle tests and native lifecycle evidence are different claims

Passing pure or mocked tests did not prove a real `WebContentsView`, native Windows process restart, or renderer identity behavior.

The distinction is now explicit:
- pure tests prove lifecycle logic/serialization;
- mocked runtime tests prove adapter contracts;
- build/typecheck proves compilation;
- process launch proves launch;
- H-004 native probe proves the actual Windows/Electron/Chromium lifecycle contract.

**Anti-repeat rule:** never upgrade a lower-layer green result into a stronger claim than that layer can observe.

### CT-004 — CI must test committed source, not an auto-repaired checkout

An earlier Workstation install path could mutate/repair tracked source before validation, creating a false-green risk.

Durable policy:
- committed downstream source is canonical;
- normal install validates integration read-only;
- runtime state lives outside tracked source where appropriate;
- install must not dirty the checkout;
- migration/rebase helpers are separate from normal validation.

### CT-005 — A red broad Windows gate needs causality, not storytelling

Durable method:
1. reproduce exact base and candidate;
2. same OS/toolchain/dependency install/commands;
3. compare failure **signatures/classes**, not only counts;
4. keep scoped outcomes independently visible;
5. preserve final red when any required broad suite is red;
6. never delete/allowlist coverage to manufacture green.

### CT-006 — GUI/browser surface identity belongs to the session

Implementation 3 established:
- GUI/Desktop surface identity is session/platform state, not a process-global env proxy;
- controller reachability is execution state, not surface existence;
- tool-definition caching must include session-surface capability to avoid Desktop↔TUI leakage.

### CT-007 — Old BrowserClaw experiments are historical motivation, not the current architecture

Earlier BrowserClaw experiments inform requirements/failure modes; they are not permission to reintroduce BrowserClaw as the primary Workstation browser after the internal-runtime decision.

## Long-term product north star — context, not current scope

The broader direction is Hermes as a persistent execution/orchestration layer for recurring work. This remains a north star, not permission for scope creep into full Kanban automation, Execution Reports, LAN/mobile, Browser Memory, Perception Engine V2, Browser4, Lightpanda, or domain workflows before browser-foundation gates are satisfied.

## Objective

Close Implementation 4 with durable evidence for the real Windows lifecycle contract without expanding into Browser Hub, Chat Browser View, Preview unification, complete BrowserSessionState, or Implementation 5+ work.

Required native lifecycle contract:

`create/navigate → hide or park → re-expose without replacement navigation → explicit destroy → real process restart → logical restore/recovery`

## Current conclusion

The Implementation 4 BrowserTask lifecycle contract is **technically validated** on real Windows/Electron/Chromium.

Native evidence was produced by `probes/h004-native-browser-task-smoke.mjs` at repository head `d8acc752133b125b9619cbc7fe09199f1283a22b`, with BrowserTask product code byte-equivalent to registered code-bearing ancestor `1ac0e0a9...`.

Environment:
- Windows release `10.0.26200`;
- outer Node `v24.14.1`;
- Electron `40.10.2`;
- Electron embedded Node `24.15.0`.

Result:
- `H004_LIVE_DESTROY_PASS`;
- `H004_RESTART_PASS`;
- `H004_CLASSIFICATION=VALIDATED`.

No product fix was required by the native investigation. Pre-H004 failures were validation-harness defects, not BrowserTask defects.

## Hypothesis ledger

### H-001 — BrowserTask lifecycle caused the V9 native-smoke timeout

Classification: **REFUTED**.

Evidence: V9 printed `HARNESS_BOOT` but never `HARNESS_READY`; product runtime import had not occurred.

### H-002 — Electron 40.10.2 / Windows cannot reach `app.ready`

Classification: **REFUTED**.

Evidence: bare Electron readiness probe reached ready and created a BrowserWindow with exit code 0.

### H-003 — V9 readiness stall is caused by top-level `await app.whenReady()` in its ESM main path

Classification: **VALIDATED**.

Experiment: `probes/h003-esm-ready.mjs`.

Evidence:
- TLA case: boot → internal timeout; exit 3;
- `.then(...)` case: boot → ready → BrowserWindow → PASS; exit 0.

Conclusion: V9 was a harness bootstrap defect. Product runtime already uses non-blocking readiness registration.

### H-004 — With the validated readiness bootstrap, the real BrowserTask lifecycle satisfies the Implementation 4 acceptance contract

Classification: **VALIDATED**.

Experiment: `probes/h004-native-browser-task-smoke.mjs`.

#### A — live page identity

Observed:
- task `impl4-h004-live-task`;
- tab id stayed `a27236b9-4aaf-4adc-9556-7ee14f5c4274`;
- real `webContentsId` stayed `3`;
- owner page count stayed `1`;
- URL and renderer sentinel survived hide/show and park/show;
- hide produced logical `hidden` without destroying page;
- park produced logical `parked` without destroying page.

#### B — explicit destroy

Observed:
- `destroyTask` returned true;
- prior WebContents destroyed;
- task not listed;
- zero remaining task-owned tabs;
- no automatic replacement page.

#### C — real process restart / logical recovery

Process 1:
- PID `30968`;
- task persisted as `parked` / `fresh`;
- structural persistence contained neither page URL secret nor renderer secret.

Process 2:
- PID `37440`;
- same task restored `parked` / `restored`;
- zero eager task pages before show;
- first show created exactly one task page;
- same task id retained;
- recovery became `recreated`.

Practical conclusion: **Implementation 4 native lifecycle acceptance behavior is proven.**

### H-005 — Final Workstation CI red after documentation closure represented a BrowserTask/product regression

Origin: final-head `Workstation CI` run `33265646758` failed after H-004 and documentation closure.

Expected if product regression:
- failing contract would involve BrowserTask/runtime behavior, integration anchors, or code paths affected by Implementation 4.

Refuting evidence:
- `core-patch-dry-run` passed;
- 23/24 Workstation contract tests passed;
- the sole failure was `test_context_separates_current_state_from_target_and_known_issues`;
- failure fingerprint: missing literal heading `## Not implemented yet` in `CURRENT_STATE.md` after a documentation rewrite combined the tested sections.

Classification: **REFUTED AS PRODUCT REGRESSION / VALIDATED AS DOCUMENTATION CONTRACT REGRESSION**.

Correction:
- restore separate canonical headings `## Partially implemented` and `## Not implemented yet`;
- do not weaken the test.

Anti-repeat implication:
- canonical documentation has executable contracts too;
- before restructuring canonical headings/sections, inspect `workstation/tests/test_context_docs.py` and related context contract tests;
- a documentation-only change is still capable of failing CI and must go through the same verification loop.

## Experiment / failure ledger

| ID | Attempt / fingerprint | What happened | Classification | Anti-repeat lesson |
|---|---|---|---|---|
| E-001 | PowerShell interpolation with `$code:` / `$ExpectedBranch:` | ParserError before test | Harness defect | Use `${name}:` when `:` follows an interpolated PowerShell variable. |
| E-002 | Assume Electron/esbuild at root `.bin` | Dependency discovery failed despite `npm ci` | Harness defect | Inspect workspace ownership before hard-coding executable paths. |
| E-003 | PowerShell parameter `$Args` | Arguments swallowed; tools printed usage | Harness defect | Never shadow automatic `$Args`. |
| E-004 | native stderr + `$ErrorActionPreference='Stop'` | Normal esbuild stderr became `NativeCommandError` | Harness defect | stderr is not failure; gate on exit status. |
| E-005 | `Start-Process` exit code on Windows PowerShell 5.1 | successful run exposed unusable/null exit status | Harness defect | Prefer Node `child_process` for native orchestration. |
| E-006 | arbitrary bundled `.mjs` as Electron target | launch did not prove valid app-entry semantics | Harness defect | Use a valid Electron app directory. |
| E-007 | V9 + top-level `await app.whenReady()` | boot marker printed; ready marker never printed | Harness defect | Never attribute pre-runtime timeout to BrowserTask. |
| E-008 | H-002 bare CommonJS readiness | ready + BrowserWindow succeeded | Control evidence | General Electron/Windows startup is healthy. |
| E-009 | H-003 ESM paired control | TLA fails; `.then(...)` passes | Root-cause evidence | Register readiness non-blockingly on this Windows/Electron path. |
| E-010 | H-004 real BrowserTask lifecycle | live identity, explicit destroy, two-process restart, lazy recovery, secret isolation all pass | Acceptance evidence | Reuse the versioned probe; do not reconstruct ad hoc runners. |
| E-011 | Preview described as Workstation Browser validation | visually successful page was wrong lane | False-positive validation | Exact tool/runtime boundary, not visual similarity, proves identity. |
| E-012 | exact `browser_navigate` + `browser_snapshot` requested while absent | test correctly stopped rather than substituting | Correct fail-closed behavior | Capability absence is a result; do not substitute and call it passed. |
| E-013 | coding focus blamed for Browser absence | environment showed `coding_context=auto` | Refuted hypothesis | Remove plausible explanations after direct contradiction. |
| E-014 | Capabilities UI ON but resolved CLI toolsets lacked `browser` | new Desktop session lacked tools | Cross-layer discrepancy | Trace UI → API → persistence → resolution → schema before changing runtime. |
| E-015 | unit/adapter lifecycle tests treated as native smoke | mocks could not prove native restart/page identity | Evidence-boundary error | Match claim to observing layer; H-004 later supplied native proof. |
| E-016 | installer repaired source before validation | mutated checkout could hide missing committed integration | Resolved validation-design defect | Test committed tree; keep repair/migration separate. |
| E-017 | broad Windows red interpreted without exact baseline | base/candidate shared failure classes | Causality lesson | Controlled A/B + signatures; baseline-equivalent red remains red. |
| E-018 | GUI capability tied to process env/reachability/cache | Desktop surface could disappear/leak across session types | Resolved ownership-model defect | Session-scoped surface identity; runtime reachability is execution state. |
| E-019 | documentation rewrite removed tested canonical heading | Workstation CI failed 1/24 although product code unchanged | Documentation contract regression | Inspect context-doc tests before restructuring canonical docs; documentation-only commits still require CI. |

## Stable anti-patterns / rules learned

1. Do not change product code because a validation harness failed before reaching the product boundary.
2. Instrument explicit markers at process boot, Electron ready, product import and each lifecycle milestone.
3. Prefer one orchestration layer with explicit timeout/exit semantics; on Windows use Node `child_process`, not stacked PowerShell wrappers.
4. Compare against a smallest known-good control and vary one material factor at a time.
5. Build success proves compilation only; process launch proves launch only; require behavior evidence.
6. Do not use top-level `await app.whenReady()` in native Workstation validation harnesses on the current Windows/Electron target.
7. Never repeat an experiment unless the materially changed input/assumption is recorded here first.
8. Never call `close-tab` or UI X equivalent to `destroyTask`; test explicit task destruction directly.
9. Do not use Task Manager PID disappearance as the canonical destroy invariant; use WebContents destruction + ownership/state evidence.
10. Once a reusable regression probe exists, improve that probe rather than creating an untracked replacement unless necessary.
11. Carry native smoke to a later documentation-only SHA only after Git proves relevant product/probe code unchanged.
12. Do not infer tool/runtime identity from screen location; inspect actual invocation/route/runtime identifiers.
13. Do not substitute Preview/web search/other browser lane when acceptance explicitly requires Workstation `browser_*`.
14. Never confuse Preview with Workstation Browser while separate lanes remain.
15. Locate the first broken boundary before fixing downstream components.
16. Label statements observed fact / hypothesis / inference / proven cause; reclassify when contradicted.
17. Typecheck, unit, mocked runtime, native smoke, and full E2E are distinct evidence classes.
18. A UI toggle is not proof backend configuration persisted.
19. Session, process, BrowserTask, profile, and renderer state have different owners/lifetimes; name owner before storing/caching/restoring.
20. Do not create parallel SessionDB/Kanban/Memory/browser state/control planes.
21. Do not synchronize duplicate browser pages by URL to imitate a shared BrowserTask; fix ownership.
22. Profile persistence and BrowserSessionState are different; renderer object identity never survives process restart.
23. Bound BrowserTasks fail closed; do not silently switch to a different stateful runtime.
24. Never allow install/CI to auto-heal tracked source before validation.
25. Broad pre-existing red requires controlled baseline/candidate evidence and remains red until fixed.
26. Keep diagnostic suites independent enough to collect evidence, while preserving final failure when required suites fail.
27. Prefer extending existing primitives over creating duplicate state owners.
28. Do not reopen superseded architecture debates without material new evidence.
29. One implementation/hypothesis cycle at a time: reproduce → isolate → smallest complete change → focused validation → correction → regressions → exact-SHA gates → docs → next.
30. In TDD corrective work, RED fails for intended reason; GREEN is smallest fix; REFACTOR only after green.
31. A checkpoint is memory, not a stop condition.
32. Before claiming a full Workstation browser path, separately prove configuration persistence, session schema exposure, exact tool execution, BrowserTask behavior, host/view unification, restart recovery, and profile persistence.
33. Canonical documentation is part of the tested product contract. Before renaming/removing required headings, fields, tables, or markers, inspect `workstation/tests` for structural assertions and run the relevant contracts after the edit.

## Remaining promotion work

1. Freeze documentation/tooling after correcting E-019.
2. Compare the final head against `d8acc752...`; only documentation changes may differ if H-004 evidence is carried forward.
3. Observe Workstation/Docker/focused Windows outcomes on the exact final head; keep broad KI-006 failures red/classified rather than hidden.
4. Perform final PR audit for scope, invariants, upstream delta and unresolved material review issues.
5. Mark PR ready and merge only if all promotion gates are satisfied.

## Continuous update protocol

Before an experiment/change:
- register hypothesis/experiment ID when causal uncertainty exists;
- state confirming/refuting evidence;
- identify the product boundary marker;
- search this journal for the same fingerprint/premise/already-refuted hypothesis;
- inspect relevant executable contracts, including documentation contracts, before restructuring tested surfaces;
- state what material input changed if repeating a prior approach.

Immediately after:
- record exact output/error fingerprint;
- classify the hypothesis (`VALIDATED`, `PARTIAL`, `REFORMULATED`, `REFUTED`, `INCONCLUSIVE`);
- record practical implication;
- identify the next materially relevant action;
- promote stable product truth into canonical docs instead of leaving it only here.

No experiment is complete until this file is updated. A checkpoint is never permission to stop; it is memory for the next action.

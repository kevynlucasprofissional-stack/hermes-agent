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

These findings came from the broader Hermes/Workstation investigation history and are kept here so the same reasoning errors are not repeated in later implementations.

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

A later test explicitly required `browser_navigate` + `browser_snapshot` and prohibited substitutes. Those native tools were absent, and the correct behavior was to report that absence rather than silently substitute Preview.

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

At the point captured by that investigation, the discrepancy existed **before BrowserTask**. Plausible explanations included optimistic UI state, wrong profile/scope persistence, or UI/backend reading different state, but those explanations were hypotheses until individually demonstrated.

**Anti-repeat rule:** do not modify `createTask`, `showTask`, `hideTask`, `parkTask`, `destroyTask`, or BrowserTask persistence to fix a failure that occurs before the model receives `browser_*` tools.

**Important scope distinction:** H-004 below directly validates the real Electron BrowserTask runtime and lifecycle. CT-002 concerns the higher-level **Hermes session/toolset path**. A direct runtime smoke can validate BrowserTask while the Chat/session tool-exposure path still requires its own regression evidence before anyone claims the full `Chat → browser_* → BrowserTask` chain is proven.

Before a future full-path Chat/Desktop claim, prove in order:

1. the selected profile/toolset state persists correctly;
2. effective resolution includes `browser` where intended;
3. a new Desktop session schema contains the required `browser_*` tools;
4. the exact `browser_navigate` and `browser_snapshot` calls execute through the intended Workstation route;
5. only then use that path as evidence for Chat-driven BrowserTask behavior.

### CT-003 — Automated lifecycle tests and native lifecycle evidence are different claims

At one point `CREATE → NAVIGATE → HIDE → SHOW → PARK → SHOW → DESTROY → RESTART` was interpreted through unit/runtime-adapter tests. Those tests were valuable, but passing mocks did not prove a real `WebContentsView`, native Windows process restart, or renderer identity behavior.

The distinction is now explicit:

- pure tests prove lifecycle logic/serialization;
- mocked runtime tests prove adapter contracts;
- build/typecheck proves compilation;
- process launch proves launch;
- H-004 native probe proves the actual Windows/Electron/Chromium lifecycle contract.

**Anti-repeat rule:** never upgrade a lower-layer green result into a stronger claim than that layer can observe.

### CT-004 — CI must test committed source, not an auto-repaired checkout

An earlier Workstation install path could mutate/repair tracked source before validation. That creates a dangerous false green: the test harness can hide a missing downstream integration by fixing it before testing it.

The durable policy is:

- committed downstream source is canonical;
- normal install validates integration in read-only/check mode;
- installer/runtime state lives outside tracked source where appropriate;
- install must not dirty the checkout;
- migration/rebase helpers are separate from normal validation.

**Anti-repeat rule:** a validator that first repairs the thing being validated cannot prove the committed tree was correct.

### CT-005 — A red broad Windows gate needs causality, not storytelling

Broad Desktop suites exposed Windows portability/test assumptions that pre-existed some Workstation changes. The correct response was not to call every red a regression, nor to dismiss every red as baseline.

Durable method:

1. reproduce the exact base and candidate;
2. same OS/toolchain/dependency install/commands;
3. compare failure **signatures/classes**, not only counts;
4. keep scoped outcomes independently visible so one suite does not mask another;
5. preserve a final red aggregator when any required broad suite is red;
6. never delete/allowlist coverage merely to manufacture green.

A baseline-equivalent failure can establish non-causality for a scoped change. It does **not** turn the broad gate into a pass.

### CT-006 — GUI/browser surface identity belongs to the session

Implementation 3 corrected a deeper modeling mistake: whether a Desktop/GUI session should know a surface is a property of the **session/platform contract**, not of `HERMES_DESKTOP` or another process-global environment proxy.

Likewise:

- controller reachability answers “can execution happen now?”;
- it must not answer “does this valid Desktop surface exist?”;
- process-wide cached `check_fn` results must not encode per-session surface identity;
- tool-definition caching must include the relevant session-surface capability so Desktop results cannot leak into TUI/CLI.

**Anti-repeat rule:** always ask which identity/scope owns a fact — process, profile, Hermes session, BrowserTask, renderer/view, or runtime health — before choosing where to store/cache/gate it.

### CT-007 — Old BrowserClaw experiments are historical motivation, not the current architecture

Earlier BrowserClaw automation demonstrated useful capabilities but also exposed the operational problems that motivated deeper Workstation integration: external browser identity, context recovery, unclear continuation state, and brittle separation between the agent's task and the browser session.

Treat those experiments as evidence for product requirements and failure modes, not as a reason to reintroduce BrowserClaw as the primary Workstation browser after the internal-runtime decision.

For long-running autonomous work, the workflow itself should define:

- objective/completion condition;
- current state/checkpoint;
- next materially relevant action;
- evidence required to call the task complete;
- recovery/abort conditions.

For an assigned multi-step objective, “there is no new user message” is not itself a completion condition. Continue until the objective is satisfied or a real blocking boundary is reached, while recording checkpoints instead of turning checkpoints into stop points.

## Long-term product north star — context, not current scope

The broader automation plans explain why this browser foundation matters. The intended direction is Hermes as a persistent **execution/orchestration layer** for recurring work: reports, task/Kanban analysis and organization, browser workflows, reusable agent profiles, and other repeatable processes.

The durable workflow-design lessons from those plans are:

- define the user-facing workflow before choosing architecture;
- modularize reusable capabilities as skills/contracts rather than one giant prompt;
- make workflows increasingly deterministic where possible;
- each workflow should define prerequisites, inputs, procedure, per-step validation, expected result, known failures, recovery/abort behavior, and evidence;
- separate execution state from domain state;
- the more deterministic the operational procedure becomes, the less it depends on an expensive model improvising every step.

This is the **north star**, not permission for scope creep. During the browser-foundation phase, do not jump ahead into complete Kanban automation, Execution Reports, LAN/mobile, Browser Memory, Perception Engine V2, Browser4, Lightpanda, or domain-specific agent workflows before the foundation gates in the roadmap are satisfied.

## Objective

Close Implementation 4 with durable evidence for the real Windows lifecycle contract without expanding into Browser Hub, Chat Browser View, Preview unification, complete BrowserSessionState, or Implementation 5+ work.

Required native lifecycle contract:

`create/navigate → hide or park → re-expose without replacement navigation → explicit destroy → real process restart → logical restore/recovery`

## Current conclusion

The Implementation 4 BrowserTask lifecycle contract is **technically validated** on real Windows/Electron/Chromium.

Native evidence was produced by `probes/h004-native-browser-task-smoke.mjs` at repository head `d8acc752133b125b9619cbc7fe09199f1283a22b`, with the BrowserTask product code still byte-equivalent to the registered code-bearing ancestor `1ac0e0a9...`.

Observed environment:
- Windows release: `10.0.26200`;
- outer Node: `v24.14.1`;
- Electron: `40.10.2`;
- Electron embedded Node: `24.15.0`.

Observed native result:
- `H004_LIVE_DESTROY_PASS`;
- `H004_RESTART_PASS`;
- `H004_CLASSIFICATION=VALIDATED`.

No product fix was required by the native investigation. The repeated pre-H004 failures were validation-harness defects, not BrowserTask defects.

Promotion is still a separate integration step: canonical docs must be finalized, the final PR head must be proven code-equivalent to the smoke SHA for the relevant product/probe paths, automated gates must be observed on the final head, and the PR must pass one last audit before merge.

## Hypothesis ledger

### H-001 — BrowserTask lifecycle caused the V9 native-smoke timeout

Classification: **REFUTED**.

Evidence:
- V9 printed `HARNESS_BOOT` but never `HARNESS_READY`;
- BrowserTask runtime import occurred only after `await app.whenReady()`.

Conclusion: the timeout happened before BrowserTask product code executed.

### H-002 — Electron 40.10.2 / Windows cannot reach `app.ready`

Classification: **REFUTED**.

Evidence:
- bare Electron CommonJS probe ran on the target machine;
- inherited `ELECTRON_*` variables: none;
- workspace Electron 40.10.2 reached ready and created a real BrowserWindow;
- exit code 0.

Conclusion: general Windows/Electron startup is healthy.

### H-003 — V9 readiness stall is caused by top-level `await app.whenReady()` in its ESM main path

Classification: **VALIDATED**.

Experiment: `probes/h003-esm-ready.mjs`.

Paired-control evidence on the exact target environment:
- TLA case: `H003_TLA_BOOT` → `H003_TLA_INTERNAL_TIMEOUT`; exit 3;
- `.then(...)` case: `H003_THEN_BOOT` → `H003_THEN_READY` → BrowserWindow → PASS; exit 0;
- classification: `H003_CLASSIFICATION=VALIDATED`.

Conclusion: V9 was a harness bootstrap defect. The Workstation runtime already uses non-blocking `void app.whenReady().then(...)`, so no product fix was justified.

### H-004 — With the validated readiness bootstrap, the real BrowserTask lifecycle satisfies the Implementation 4 acceptance contract

Classification: **VALIDATED**.

Experiment: `probes/h004-native-browser-task-smoke.mjs`.

#### A — live page identity

Observed:
- task: `impl4-h004-live-task`;
- tab id remained `a27236b9-4aaf-4adc-9556-7ee14f5c4274`;
- real `webContentsId` remained `3`;
- owner page count remained exactly `1`;
- URL remained the same through hide/show and park/show;
- renderer sentinel remained the same through hide/show and park/show;
- `hideTask` changed logical status to `hidden` without destroying the page;
- `parkTask` changed logical status to `parked` without destroying the page;
- re-exposure did not perform replacement navigation.

Result: `H004_LIVE_DESTROY_PASS` after the destroy phase.

#### B — explicit destroy

Observed:
- `destroyTask` returned `true`;
- prior real WebContents reported destroyed;
- task no longer listed;
- remaining task-owned tabs: `0`;
- no replacement page appeared.

Result: PASS.

#### C — real process restart / logical recovery

Process 1:
- PID `30968`;
- task `impl4-h004-restart-task` persisted as `parked` / `fresh` before exit;
- structural state path was under the isolated temporary Workstation root;
- URL secret and renderer secret were absent from BrowserTask structural persistence.

Process 2:
- PID `37440` (different OS process);
- same logical task restored as `parked` / `recoveryState: restored`;
- task-owned page count before first show: `0`;
- first show created exactly one task-owned page;
- same logical task id retained;
- `recoveryState` became `recreated`;
- resulting `ownerTaskId` matched `impl4-h004-restart-task`.

Result:
- `H004_RESTART_PASS`;
- `H004_CLASSIFICATION=VALIDATED`;
- conclusion emitted by probe: real Electron BrowserTask lifecycle passed live identity, explicit destroy, real restart, lazy logical recovery, and structural secret-isolation checks.

Practical conclusion: **Implementation 4's native lifecycle acceptance behavior is proven.**

## Experiment / failure ledger

| ID | Attempt / fingerprint | What happened | Classification | Anti-repeat lesson |
|---|---|---|---|---|
| E-001 | PowerShell interpolation with `$code:` / `$ExpectedBranch:` | ParserError before test | Harness defect | Use `${name}:` when `:` follows an interpolated PowerShell variable. |
| E-002 | Assume Electron/esbuild at root `.bin` | Dependency discovery failed despite `npm ci` | Harness defect | Inspect workspace ownership before hard-coding executable paths. |
| E-003 | PowerShell parameter `$Args` | Arguments swallowed; tools printed usage | Harness defect | Never shadow automatic `$Args`. |
| E-004 | native stderr + `$ErrorActionPreference='Stop'` | Normal esbuild stderr became `NativeCommandError` | Harness defect | stderr is not failure; gate on exit status. |
| E-005 | `Start-Process` exit code on Windows PowerShell 5.1 | successful run exposed unusable/null exit status | Harness defect | Prefer Node `child_process` for native orchestration. |
| E-006 | arbitrary bundled `.mjs` as Electron target | launch did not prove valid app-entry semantics | Harness defect | Use a valid Electron app directory (`package.json` + main). |
| E-007 | V9 + top-level `await app.whenReady()` | boot marker printed; ready marker never printed; timeout | Harness defect | Never attribute pre-runtime timeout to BrowserTask. |
| E-008 | H-002 bare CommonJS readiness | ready + BrowserWindow succeeded | Control evidence | General Electron/Windows startup is healthy. |
| E-009 | H-003 ESM paired control | TLA fails; `.then(...)` passes | Root-cause evidence | Register readiness non-blockingly on this Windows/Electron path. |
| E-010 | H-004 real BrowserTask lifecycle | live identity, explicit destroy, two-process restart, lazy recovery and secret isolation all pass | Acceptance evidence | Use this versioned probe for future regression reproduction; do not reconstruct ad hoc runners. |
| E-011 | `open_preview`/`read_preview` described as Workstation Browser validation | visually successful page was the Preview lane, not proof of `browser_*`/BrowserTask | False-positive validation | Tool/runtime identity must come from the actual call/result boundary, not narrative or visual similarity. |
| E-012 | exact `browser_navigate` + `browser_snapshot` requested while absent | correct run stopped instead of substituting Preview/Computer Use/web search | Correct fail-closed test behavior | When acceptance names an exact capability, absence is a result; do not substitute and call it passed. |
| E-013 | hypothesis that coding focus removed Browser | real environment showed `coding_context=auto` | Refuted hypothesis | Record refutations explicitly; do not preserve a plausible explanation after direct configuration evidence contradicts it. |
| E-014 | Capabilities UI ON while persisted/resolved CLI toolsets lacked `browser` | new Desktop session lacked native browser tools | Cross-layer integration discrepancy; root cause not proven in captured evidence | Trace UI → API → profile persistence → resolution → session schema before changing downstream runtime behavior. |
| E-015 | lifecycle unit/adapter tests treated as if they were the requested native smoke | mocks passed but native Electron restart/page identity remained unproven at that time | Evidence-boundary error | Match each claim to the lowest layer that can actually observe it; H-004 later supplied native proof. |
| E-016 | normal installer repaired tracked integration before validation | mutated checkout could hide missing committed integration | Resolved validation-design defect | Test the committed tree; keep migration/repair paths separate and assert checkout cleanliness. |
| E-017 | broad Windows red status interpreted without exact baseline causality | candidate and base shared failure classes; runner counts could differ | Causality/diagnostic lesson | Use controlled A/B and failure signatures; baseline-equivalent red is still red. |
| E-018 | GUI surface capability tied to process env/reachability/cache | valid Desktop tool surface could disappear or leak across session types | Resolved ownership-model defect | Surface identity is session-scoped; reachability is execution state; process-wide cache cannot encode per-session identity. |

## Stable anti-patterns / rules learned

1. Do not change product code because a validation harness failed before reaching the product boundary.
2. Instrument explicit markers at process boot, Electron ready, product import and each lifecycle milestone.
3. Prefer one orchestration layer with explicit timeout/exit semantics; on Windows this track uses Node `child_process`, not stacked PowerShell wrappers.
4. Compare against a smallest known-good control and vary one material factor at a time.
5. Build success proves compilation only; process launch proves launch only; require behavior evidence.
6. Do not use top-level `await app.whenReady()` in native Workstation validation harnesses on the current Windows/Electron target.
7. Never repeat an experiment unless the materially changed input/assumption is recorded here first.
8. Never call `close-tab` or a UI X equivalent to `destroyTask`; explicit BrowserTask destruction is tested through `destroyTask`.
9. Do not use Task Manager PID disappearance as the canonical destroy invariant; use WebContents destruction + ownership/state evidence.
10. Once a reusable regression probe exists, improve that probe rather than creating an untracked replacement unless the old probe cannot represent the new hypothesis.
11. A smoke result may be carried to a later documentation-only SHA only after a Git comparison proves that the relevant product code and the executed probe are unchanged; record that equivalence explicitly.
12. Do not infer tool/runtime identity from where content appeared on screen. Inspect the exact tool invocation, route/backend, returned runtime/task/tab identifiers, and product boundary.
13. Do not substitute Preview, web search, Browser Use, Computer Use, or another browser lane when a test explicitly requires Workstation `browser_*`; report capability absence instead.
14. Never confuse Preview with the Workstation Browser while they remain separate lanes. `open_preview`/`read_preview`/`drive_preview` are compatibility/UI contracts, not evidence of BrowserTask unless/until the architecture actually routes them onto the unified runtime.
15. Before fixing a symptom, locate the first broken boundary in the chain. A BrowserTask change cannot repair a tool that never entered the session schema.
16. Always label statements as observed fact, hypothesis, inference, or proven cause. A plausible hypothesis must be removed/reclassified when contradicted by evidence.
17. Typecheck, unit tests, mocked runtime tests, native smoke, and full E2E are different evidence classes. Never promote one into another by wording.
18. A UI toggle is not proof that backend configuration persisted. Read the API/config/profile and the consumer's resolved state.
19. Session-scoped capability, process-scoped environment, BrowserTask-scoped identity, profile-scoped browser state, and renderer-scoped page state are different lifetimes. Name the owner before storing, caching, or restoring state.
20. Do not create parallel SessionDB/Kanban/Memory/browser state/control planes to make integration easier. Extend existing owners and preserve one source of truth.
21. Do not “sync” two independently navigated browser pages to imitate a shared BrowserTask. Fix ownership/hosting so there is one live semantic page.
22. Profile persistence and BrowserSessionState are different. Cookies/localStorage/IndexedDB belong to the browser profile; safe logical task/tab metadata belongs to Workstation state; renderer object identity never survives process restart.
23. Bound BrowserTasks fail closed. Do not silently fail over to a runtime with different page/auth state after binding.
24. Never allow installation/CI to auto-heal tracked source before validation. The committed tree is what must be proven.
25. A broad pre-existing red gate is investigated with controlled baseline/candidate evidence; it is never hidden, disabled, or relabeled green.
26. Keep diagnostic suites independent enough that one failure does not prevent collecting evidence from another, but preserve a final failing outcome when any required suite fails.
27. Prefer extending existing primitives (`taskTabs`, `ownerTaskId`, Hermes Sessions/Kanban/Memory/tool registry) over inventing a second abstraction that owns the same state.
28. Do not reopen superseded architecture debates merely because an older context recommended them. Verify the latest canonical decision and the material evidence that would be needed to replace it.
29. One implementation/hypothesis cycle at a time: reproduce/define the gap → isolate responsibility → smallest complete change → focused validation → corrections in loop → regressions → exact-SHA gates → documentation → only then next implementation.
30. In TDD corrective work, RED must fail for the intended reason; GREEN is the smallest fix; REFACTOR comes only after green. Do not refactor while the causal test is still red.
31. A checkpoint is memory, not a stop condition. Continue the assigned investigation/implementation until the objective is resolved or a genuine blocking boundary is demonstrated.
32. Before claiming a full Workstation browser path, separately prove configuration persistence, session schema exposure, exact tool execution, BrowserTask behavior, host/view unification, restart recovery, and profile persistence. Passing one does not imply the others.

## Remaining promotion work

1. Update canonical `CURRENT_STATE.md`, `KNOWN_ISSUES.md`, `TESTING.md`, and `UPSTREAM_DELTA.md` with the accepted evidence/boundary.
2. Freeze documentation/tooling.
3. Compare the final head against `d8acc752...`; only documentation changes may differ if H-004 evidence is carried forward.
4. Observe Workstation/Docker/focused Windows outcomes on the exact final head; keep broad KI-006 failures red/classified rather than hidden.
5. Perform final PR audit for scope, invariants, upstream delta and unresolved material review issues.
6. Mark PR ready and merge only if all promotion gates are satisfied.

## Continuous update protocol

Before an experiment:
- register hypothesis/experiment ID;
- state confirming and refuting evidence;
- identify the product boundary marker;
- search this journal for the same fingerprint, premise, tool boundary, or already-refuted hypothesis;
- state what material input changed if repeating a prior approach.

Immediately after:
- record exact output/error fingerprint;
- classify the hypothesis (`VALIDATED`, `PARTIAL`, `REFORMULATED`, `REFUTED`, `INCONCLUSIVE`);
- record practical implication;
- identify the next materially relevant hypothesis/action;
- promote stable product truth into the appropriate canonical document instead of leaving it only here.

No experiment is complete until this file is updated. A checkpoint is never permission to stop; it is memory for the next action.

# CURRENT — Workstation Engineering Journal

Last updated: 2026-08-29
Active track: Implementation 4 — BrowserTask lifecycle native Windows acceptance
Repository: `kevynlucasprofissional-stack/hermes-agent`
Milestone branch: `impl4-browser-task-lifecycle`
Code-bearing BrowserTask candidate ancestor: `1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70`
Base `main`: `ce78f120e8ed2974d6174e475cc7572afcfe41e0`
PR: #9 — `feat(workstation): formalize BrowserTask lifecycle` (open, draft)

> Journal/probe commits after `1ac0e0a9...` are validation-memory/tooling commits only unless this file explicitly records a later code-bearing candidate. Always verify the live PR head before an experiment.

## Objective

Close the remaining real-Windows acceptance boundary for Implementation 4 without expanding into Browser Hub, Chat Browser View, Preview unification, complete BrowserSessionState, or Implementation 5+ work.

Required native lifecycle contract:

`create/navigate → hide or park → re-expose without replacement navigation → explicit destroy → real process restart → logical restore/recovery`

## Current evidence model

### Already supported

- BrowserTask pure lifecycle tests pass.
- Runtime adapter tests pass with Electron mocked.
- Take Control / Release Control regression is logically covered.
- Renderer crash recovery is logically covered.
- Active-task destruction / remaining-task logical activation is covered.
- BrowserTask persistence excludes page URLs and page-scoped secrets.
- Workstation CI and Docker validation were green on the code-bearing candidate.
- Broad Windows suites retain documented baseline failures; they must not be hidden or weakened.
- Bare Electron 40.10.2 reaches `ready` on the target Windows machine.
- In the exact target environment, ESM top-level `await app.whenReady()` stalls while ESM `app.whenReady().then(...)` reaches readiness.

### Still required

A real Electron/Chromium Windows BrowserTask lifecycle smoke using a bootstrap path that does not block Electron readiness.

## Hypothesis ledger

### H-001 — BrowserTask lifecycle caused the V9 native-smoke timeout

Origin: first native harness attempts.

Refuting evidence:
- V9 printed `HARNESS_BOOT` but never `HARNESS_READY`;
- BrowserTask runtime import occurred only after `await app.whenReady()`.

Classification: **REFUTED**

Conclusion: the timeout happened before BrowserTask product code executed. Do not modify Implementation 4 product code in response to V9.

### H-002 — Electron 40.10.2 / Windows cannot reach `app.ready`

Experiment: bare Electron CommonJS probe with no Hermes, BrowserTask, Workstation runtime, esbuild, ESM, HTTP server, or WebContentsView.

Observed evidence:
- target branch/head were correct;
- inherited `ELECTRON_*` variables: none;
- workspace Electron 40.10.2;
- exit code 0;
- bare Electron reached readiness and created a real BrowserWindow.

Classification: **REFUTED**

Conclusion: general Windows/Electron startup is healthy.

### H-003 — V9 readiness stall is caused by top-level `await app.whenReady()` in its ESM main path

Origin: V9 stalled between `HARNESS_BOOT` and `HARNESS_READY`; H-002 proved general Electron readiness works.

Confirming experiment: `probes/h003-esm-ready.mjs`, two ESM mini-apps differing materially only in readiness control flow.

Observed on Windows 10.0.26200 / Electron 40.10.2:
- TLA case: `H003_TLA_BOOT`, then `H003_TLA_INTERNAL_TIMEOUT`; exit 3;
- `.then(...)` case: `H003_THEN_BOOT` → `H003_THEN_READY` → BrowserWindow created → PASS; exit 0;
- result matrix: TLA fail / THEN pass;
- probe classification: `VALIDATED`.

Attempted refutation:
- Electron supports ESM main processes generally;
- the problem is therefore not “ESM is unsupported”;
- the paired control proves the material discriminator is the blocking readiness pattern in this exact environment, not ESM alone.

Classification: **VALIDATED**

Conclusion: V9 was a harness bootstrap defect. The Workstation runtime itself already uses the non-blocking `void app.whenReady().then(...)` pattern, so no product fix is justified by this failure.

Practical implication:
- native validation harnesses must never use top-level `await app.whenReady()` in this Windows/Electron path;
- use non-blocking readiness registration and explicit boundary markers.

### H-004 — With the validated readiness bootstrap, the real BrowserTask lifecycle satisfies the Implementation 4 acceptance contract

Origin: H-003 removed the harness blocker and leaves the original native lifecycle question unanswered.

Expected confirming evidence:
1. `H004_BOOT` and `H004_READY` occur before runtime operations;
2. real `WorkstationBrowserRuntime` imports and uses real Electron `WebContentsView`;
3. one BrowserTask owns one real task page;
4. hide/show and park/show preserve taskId, task-owned tab ID, WebContents identity/id, URL and renderer sentinel;
5. explicit `destroyTask` destroys the prior WebContents and leaves no task-owned entry;
6. two distinct Electron PIDs prove a real restart;
7. restart restores the same logical task as parked/restored with zero eager task pages;
8. first show lazily creates exactly one task page and sets recovery to recreated;
9. persisted BrowserTask structural state contains neither page URL secret nor renderer/typed secret.

Evidence that refutes or reformulates H-004:
- any lifecycle invariant fails after `H004_READY` and `H004_RUNTIME_IMPORTED`;
- task page duplicates;
- page replacement on hide/show or park/show;
- destroy leaves ownership/page alive;
- restart loses logical task identity or eagerly duplicates pages;
- secret leakage into BrowserTask structural state.

Classification: **ACTIVE — REGISTERED BEFORE EXECUTION**

Experiment: `probes/h004-native-browser-task-smoke.mjs`.

Probe implementation checkpoint:
- probe is versioned on the milestone branch;
- outer Node probe syntax was checked successfully before publication;
- probe rejects execution if `apps/desktop/electron` changed after the registered code-bearing ancestor, preventing stale evidence;
- probe uses Node child-process orchestration, a valid temporary Electron app, CommonJS bundle output, and non-blocking `app.whenReady().then(...)`;
- probe imports the real Workstation runtime only after `H004_READY`, then records `H004_RUNTIME_IMPORTED` before lifecycle operations;
- no product source file is modified by the probe.

Execution status: **PENDING PHYSICAL WINDOWS RUN**.

Scope rule: a failure before `H004_RUNTIME_IMPORTED` is a probe/bootstrap failure; a failure after product runtime entry must be localized before deciding whether it is product or probe.

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
| E-009 | H-003 ESM paired control | TLA fails; `.then(...)` passes | Root-cause evidence | In this target environment, register readiness non-blockingly; do not top-level-await it. |

## Stable anti-patterns / rules learned

1. Do not change product code because a validation harness failed before reaching the product boundary.
2. Instrument explicit markers at process boot, Electron ready, product import and each lifecycle milestone.
3. Prefer one orchestration layer with explicit timeout/exit semantics; on Windows this track uses Node `child_process`, not stacked PowerShell wrappers.
4. Compare against a smallest known-good control and vary one material factor at a time.
5. Build success proves compilation only; process launch proves launch only; require behavior evidence.
6. Do not use top-level `await app.whenReady()` in native Workstation validation harnesses on the current Windows/Electron target.
7. Never repeat an experiment unless the material changed input/assumption is recorded here first.
8. Never call `close-tab` or UI X equivalent to `destroyTask`; explicit BrowserTask destruction must be tested through `destroyTask`.
9. Do not use Task Manager PID disappearance as the canonical destroy invariant; use WebContents destruction + ownership/state evidence.

## Native-smoke acceptance details

### A — Live identity
- same `taskId`;
- same task-owned tab ID;
- same real `WebContents` / `webContents.id` across hide/show and park/show;
- same URL;
- renderer JS sentinel survives;
- exactly one page owns the task.

### B — Explicit destroy
- `destroyTask(taskId)` succeeds;
- prior real WebContents is destroyed;
- task removed from lifecycle metadata;
- zero remaining entries own the task;
- no replacement page appears.

### C — Real restart
- two distinct Electron OS PIDs;
- process 1 persists logical metadata and exits;
- process 2 restores same taskId as `parked` / `recoveryState: restored` with zero eager live task pages;
- first show lazily creates exactly one new page for same task;
- recovery becomes `recreated`;
- never claim WebContents identity or renderer JS heap survives restart.

## Promotion boundary

Implementation 4 remains **NOT PROMOTED** until:
1. H-004/native Windows lifecycle smoke passes on the final code-bearing behavior;
2. code/docs are frozen;
3. canonical docs and especially `UPSTREAM_DELTA.md` reflect final state;
4. relevant gates are rerun on the exact final SHA;
5. final audit finds no material issue inside Implementation 4 scope;
6. only then PR #9 is marked ready and merged.

## Continuous update protocol

Before an experiment:
- register hypothesis/experiment ID;
- state confirming and refuting evidence;
- identify the product boundary marker.

Immediately after:
- record exact output/error fingerprint;
- classify hypothesis;
- record practical implication;
- identify the next materially relevant hypothesis.

No experiment is complete until this file is updated. A checkpoint is never permission to stop; it is memory for the next action.
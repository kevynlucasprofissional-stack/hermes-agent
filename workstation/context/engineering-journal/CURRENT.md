# CURRENT — Workstation Engineering Journal

Last updated: 2026-08-29
Active track: Implementation 4 — BrowserTask lifecycle native Windows acceptance
Repository: `kevynlucasprofissional-stack/hermes-agent`
Milestone branch: `impl4-browser-task-lifecycle`
Last code-bearing candidate SHA observed before journal commits: `1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70`
Base `main`: `ce78f120e8ed2974d6174e475cc7572afcfe41e0`
PR: #9 — `feat(workstation): formalize BrowserTask lifecycle` (open, draft)

## Objective

Close the remaining real-Windows acceptance boundary for Implementation 4 without expanding into Browser Hub, Chat Browser View, Preview unification, complete BrowserSessionState, or other Implementation 5+ work.

Required native lifecycle contract:

`create/navigate → hide or park → re-expose without replacement navigation → explicit destroy → real process restart → logical restore/recovery`

## Current evidence model

### Already supported by automated/current-head evidence

- BrowserTask pure lifecycle tests pass.
- Runtime adapter tests pass with Electron mocked.
- Take Control / Release Control regression is logically covered.
- Renderer crash recovery is logically covered.
- Active-task destruction / remaining-task logical activation is covered.
- BrowserTask persistence excludes page URLs and page-scoped secrets.
- Workstation CI and Docker validation are green on the code-bearing candidate.
- Broad Windows suites retain documented baseline failures; they must not be hidden or weakened.

### Still required

A real Electron/Chromium Windows lifecycle smoke. Mocked `WebContents` / `WebContentsView` are insufficient.

## Hypothesis ledger

### H-001 — BrowserTask lifecycle caused the native smoke timeout

Origin: first native harness attempts.

Expected if true:
- Electron reaches app readiness;
- BrowserTask runtime executes;
- timeout/error occurs during `createTask`, `showTask`, navigation, hide/park/show, destroy, or restart logic.

Refuting evidence:
- V9 printed `HARNESS_BOOT` but never printed `HARNESS_READY`;
- the BrowserTask runtime import happened only after `await app.whenReady()` in that harness.

Classification: **REFUTED**

Conclusion: the observed V9 timeout occurred before BrowserTask code executed. Do not modify Implementation 4 product code in response to that timeout.

### H-002 — Electron 40.10.2 / Windows environment cannot reach `app.ready`

Origin: V9 stopped between `HARNESS_BOOT` and `HARNESS_READY`.

Experiment: bare Electron CommonJS probe with no Hermes, BrowserTask, Workstation runtime, esbuild, ESM, HTTP server, or WebContentsView.

Observed evidence:
- branch/head/origin all matched `1ac0e0a9...` at execution time;
- inherited `ELECTRON_*` variables: none;
- Electron executable: workspace Electron 40.10.2;
- probe exit code: 0;
- probe classification: `H-002 CLASSIFICATION: REFUTADA`;
- bare Electron reached readiness and could create a real BrowserWindow.

Classification: **REFUTED**

Conclusion: Windows/Electron readiness works in a minimal CommonJS app. The V9 stall is specific to the harness/bootstrap path.

### H-003 — V9 deadlocks because an ESM main entry uses top-level `await app.whenReady()`

Origin: difference between V9 and the successful H-002 bare probe plus Electron lifecycle semantics.

Why plausible:
- V9 uses an ESM `main.mjs` bundle and performs top-level `await app.whenReady()`;
- H-002 uses CommonJS and `app.whenReady().then(...)` and succeeds;
- Electron documents that `ready` is emitted only after the main process has run its first event-loop tick;
- Electron's ESM documentation highlights distinct asynchronous main-entry semantics before `ready`;
- ecosystem reports exist warning about top-level-await / ready deadlocks in Electron ESM main bundles.

Evidence that would support it:
- on the same Electron executable, an ESM mini-app with top-level `await app.whenReady()` stalls, while an otherwise equivalent ESM mini-app using `app.whenReady().then(...)` reaches ready.

Evidence that would refute it:
- both ESM forms reach ready under the same environment, or the `.then(...)` form stalls identically.

Classification: **ACTIVE / NOT YET VALIDATED**

Next discriminating experiment: one two-case bare Electron probe comparing ESM-TLA vs ESM-callback with no Hermes imports.

## Experiment / failure ledger

| ID | Attempt / fingerprint | What happened | Classification | Anti-repeat lesson |
|---|---|---|---|---|
| E-001 | PowerShell interpolation with `$code:` / `$ExpectedBranch:` | ParserError before test execution | Harness defect | Use `${name}:` when a variable is immediately followed by `:` in double-quoted PowerShell strings. |
| E-002 | Assume Electron/esbuild binaries live at root `node_modules/.bin` | Dependency discovery failed although `npm ci` succeeded | Harness defect | Resolve workspace-owned executables from `apps/desktop` first; inspect package ownership before hard-coding paths. |
| E-003 | PowerShell function parameter named `$Args` | Native executable arguments were swallowed; tools printed usage | Harness defect | Never shadow PowerShell automatic `$Args`; use an explicit name such as `$CommandArgs`. |
| E-004 | `$ErrorActionPreference='Stop'` + native stderr pipeline | Normal esbuild stderr became `NativeCommandError` | Harness defect | Do not interpret native stderr as process failure; gate on process exit code. |
| E-005 | `Start-Process` exit-code handling under Windows PowerShell 5.1 | Successful esbuild run produced unusable/null exit code | Harness defect | Prefer Node `child_process.spawn` for native orchestration and timeouts in this validation path. |
| E-006 | Direct Electron invocation with arbitrary bundled `.mjs` | Process started but did not prove app entry semantics | Harness design defect | Invoke a valid temporary Electron app directory with `package.json` + `main` entry. |
| E-007 | V9 valid Electron mini-app + top-level `await app.whenReady()` | `HARNESS_BOOT` printed; `HARNESS_READY` never printed; 45s timeout | Investigation evidence | Do not attribute this to BrowserTask; runtime import had not executed. Test ESM readiness semantics independently first. |
| E-008 | H-002 bare CommonJS Electron readiness probe | Exit 0; bare Electron reaches ready; no inherited `ELECTRON_*` vars | Investigation evidence | General Electron/Windows startup is not the blocker; narrow investigation to V9 bootstrap differences. |

## Stable anti-patterns discovered

1. Do not change product code because a validation harness failed before reaching the product boundary.
2. Instrument boundary markers before attributing a timeout to the subsystem under test.
3. For native tools on Windows, prefer one orchestration layer with explicit exit-code and timeout semantics; avoid stacking PowerShell pipelines, `.cmd` shims, and `Start-Process` unless required.
4. Before writing a new runner, compare it against the smallest known-good control and vary one material factor at a time.
5. A successful build only proves the harness compiled; it does not prove Electron executed the intended path.
6. A process launch only proves the executable started; require explicit markers for boot, ready, subsystem entry, and lifecycle milestones.
7. Never repeat an experiment unless the changed assumption/input is recorded here.

## Native-smoke evidence requirements once bootstrap is solved

### A — Live identity

For one BrowserTask in one Electron process:
- same `taskId`;
- same task-owned tab ID;
- same real `WebContents` / `webContents.id` across hide/show and park/show;
- same URL;
- renderer JS sentinel survives;
- exactly one page owns the task.

### B — Explicit destroy

- `destroyTask(taskId)` succeeds;
- previous real WebContents is destroyed;
- task removed from lifecycle metadata;
- zero remaining entries own the task;
- no replacement page is created automatically.

### C — Real restart

Use two distinct Electron OS processes sharing only the intended persistent Workstation state root:
- process 1 persists logical task metadata and exits;
- process 2 restores same `taskId` as `parked` / `recoveryState: restored` with no eager live page;
- first show/use lazily creates exactly one new page for same task;
- `recoveryState` becomes `recreated`;
- never claim WebContents identity or renderer JS heap survives restart.

## Promotion boundary

Implementation 4 remains **NOT PROMOTED** until:

1. native Windows lifecycle smoke passes on the final PR head;
2. code/docs are frozen;
3. `CURRENT_STATE.md`, `KNOWN_ISSUES.md`, `TESTING.md` as needed, and especially `UPSTREAM_DELTA.md` reflect the final state;
4. relevant gates are rerun on the exact final SHA;
5. final audit finds no material known issue inside Implementation 4 scope;
6. only then PR #9 is marked ready and merged.

## Update protocol

Before the next experiment:
- add its hypothesis/experiment ID above;
- record confirming and refuting evidence in advance.

Immediately after the experiment:
- record exact observed output/error fingerprint;
- classify the hypothesis;
- record the practical implication;
- identify the next materially relevant hypothesis.

No experiment is considered complete until this file has been updated.

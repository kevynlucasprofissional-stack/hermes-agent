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
- identify the product boundary marker.

Immediately after:
- record exact output/error fingerprint;
- classify hypothesis;
- record practical implication;
- identify the next materially relevant hypothesis.

No experiment is complete until this file is updated. A checkpoint is never permission to stop; it is memory for the next action.

# Workstation Testing

A Workstation change is stable only when its **behavioral contract** is proven at the lowest useful layer and the relevant integration path remains green. Typecheck or source-shape checks alone are not proof.

## Validation ladder

Use the smallest focused gate first, then expand only after it passes:

1. **Pure/unit behavior** — extracted logic, state transitions, serialization, routing decisions, host/geometry helpers.
2. **Workstation contracts** — `workstation/tests/` for Python-side routing/config/integration contracts.
3. **Desktop UI tests** — renderer behavior through Vitest/React tests when UI state or actions change.
4. **Desktop platform tests** — Electron/main-process behavior for `WebContentsView`, BrowserRuntime, host ownership, persistence, and IPC contracts.
5. **Desktop typecheck/build gates** — compile changed contracts across renderer/preload/main boundaries.
6. **Windows Desktop E2E/smoke** — required for claims depending on real Electron/Windows composition, restart, profile persistence, or native view behavior.

Do not replace executable behavior tests with source greps. Source-shape tests are acceptable for bootstrap/build policy but are not substitutes for runtime behavior.

## Existing Workstation gates

### `Workstation CI`

- component lock validation;
- third-party license validation;
- `workstation/tests/`;
- downstream integration-anchor check in read-only `--check` mode.

### `Workstation Browser Windows`

- Node/Python setup;
- read-only committed-integration validation;
- normal `workstation\\install.cmd` execution;
- clean-checkout assertion after install;
- Desktop typecheck;
- focused BrowserTask lifecycle/runtime step;
- Desktop UI tests;
- Desktop platform/Electron tests;
- final aggregator that remains red if a scoped or broad required outcome is red.

The UI and platform steps may continue after failure only so both outcomes are observable. This is diagnostic non-masking, not failure tolerance.

### Desktop Browser schema capability

`tests/tui_gateway/test_workstation_browser_schema_capability.py` proves:

- Desktop capability survives a false controller reachability probe;
- Desktop tool-definition cache state cannot leak into TUI;
- process-global `HERMES_DESKTOP` cannot grant TUI capability;
- Desktop source identity is sufficient without that env flag;
- the forced Workstation set remains narrow (`browser_exec` is not promoted).

### BrowserTask pure lifecycle

`apps/desktop/electron/workstation-browser-task.test.ts` proves:

- hide and park preserve the logical live page;
- destroy is explicit;
- one logical record exists per task;
- switching the visible task parks the previous task;
- malformed/duplicate persisted metadata is pruned;
- restart restoration is parked and page recovery is lazy;
- persisted task structure excludes page-scoped secret content.

### BrowserTask runtime adapter

`apps/desktop/electron/workstation-browser-runtime-task.test.ts` exercises the real `WorkstationBrowserRuntime` with Electron mocked and proves:

- `ownerTaskId` is idempotent in the Chromium tab primitive;
- hide/park/show retain the same WebContents and URL within one process;
- explicit task destroy closes the owned page;
- restart restores logical metadata first and creates one page only when shown again;
- renderer crash recovery creates one replacement page under the same task.

## BrowserTask lifecycle policy

BrowserTask tests must distinguish **logical task persistence** from **process-local page identity**:

- within one Electron process, `create -> hide -> show` and `create -> park -> show` retain the same live page object and current URL;
- `hide`/`park` do not close the WebContents;
- `destroyTask` is the operation that removes the task and closes its owned page;
- repeated creation for the same `taskId` does not allocate a second page;
- if a page crashes/disappears while the logical task remains, recovery may create exactly one replacement and records that recovery;
- after Desktop process restart, metadata restores as parked before any page is recreated; showing/using the task may lazily recreate one page under the same task id;
- tests never claim that renderer JavaScript heap or a WebContents object survives process restart.

Use the pure lifecycle test first, then the runtime-adapter test, then the real Windows smoke.

## Implementation 4 real Windows acceptance evidence

The required narrow native smoke is versioned at:

`workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs`

Validated execution:

- repository head: `d8acc752133b125b9619cbc7fe09199f1283a22b`;
- code-bearing BrowserTask ancestor: `1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70`;
- Windows: `10.0.26200`;
- Electron: `40.10.2`;
- outer Node: `v24.14.1`;
- Electron Node: `24.15.0`.

Observed native markers:

- `H004_READY` before product import;
- `H004_RUNTIME_IMPORTED` before lifecycle operations;
- `H004_LIVE_DESTROY_PASS`;
- `H004_RESTART_PASS`;
- `H004_CLASSIFICATION=VALIDATED`.

The smoke used real `BrowserWindow`, real `WebContentsView`, real renderer execution, and two distinct Electron OS processes. It proved:

1. same task id, task-owned tab id, WebContents identity/id, URL and renderer sentinel across hide/show and park/show;
2. exactly one page owned the task throughout the live lifecycle;
3. explicit `destroyTask` destroyed the page and removed logical/page ownership without automatic replacement;
4. restart restored the same logical task as parked/restored with zero eager pages;
5. first show after restart created exactly one page and recorded `recreated`;
6. BrowserTask structural persistence excluded the test page URL secret and renderer secret.

This smoke is sufficient for the **Implementation 4 lifecycle boundary only**. It does not validate future Chat Browser View, Browser Hub, Preview unification, host transfer/resize, complete BrowserSessionState, or complete SessionDB/Kanban/run linkage.

### Native smoke carry-forward rule

A native smoke may be associated with a later final documentation-only head without rerunning the physical Electron test only when all of the following are proven:

1. the smoke SHA and final head are in a direct ancestry relationship;
2. Git comparison shows no change in the product files whose behavior was exercised;
3. the executed smoke probe itself is unchanged;
4. changes after the smoke are documentation-only and cannot affect runtime/bootstrap/dependency resolution;
5. automated gates are observed on the exact final head;
6. the equivalence is recorded in the final evidence/report.

If any runtime, dependency, workflow, probe, or product path changes after the smoke, rerun the native smoke on the new head.

## Implementation 4 promotion closure

Implementation 4 was promoted through PR #9 with accepted head `75d10d35d4757496390debf8e4b4f9efb44c5432` and merge commit `fada723f43613e5e0f061cab24445573ac298998`.

### Controlled Windows causality comparison

A native-Windows side-by-side run used the same toolchain/install/commands against:

- baseline: `ce78f120e8ed2974d6174e475cc7572afcfe41e0`;
- candidate: `2ffee2335b6aba071e7b63457a047cd9334d4d92`.

Observed:
- baseline UI legacy: 5 failed files / 11 failed tests;
- candidate UI legacy: 5 failed files / 9 failed tests;
- baseline platform/Electron legacy: 11 failed files / 33 failed tests;
- candidate platform/Electron legacy: 10 failed files / 28 failed tests;
- all remaining candidate failures matched an identical baseline failure or a variant of the same causal class;
- candidate-specific BrowserTask tests passed 2 files / 16 tests;
- candidate typecheck passed.

Verdict: `WINDOWS_BASELINE_COMPARISON=PASS_WITH_KI-006_RED`.

### Exact-final-head evidence

Git comparison proved that changes from controlled candidate `2ffee...` to accepted head `75d10d35...` were limited to contributor-attribution mapping and Workstation engineering-journal material. BrowserTask product/runtime/probe/workflow/dependency code did not change.

On `75d10d35...`:
- `Workstation CI` passed;
- Docker Build/Test/Publish passed;
- contributor attribution passed after the missing mapping was added;
- Windows committed-integration validation passed;
- normal Workstation install passed and kept the checkout clean;
- Desktop typecheck passed;
- focused BrowserTask lifecycle tests passed;
- broad UI/platform diagnostics ran;
- the final Windows aggregator remained red, preserving KI-006 instead of masking it.

Because no material code changed after the controlled A/B, the final-head Windows red is classified `KI-006_ONLY_BY_CONTROLLED_EQUIVALENCE`, not as a new Implementation 4 regression.

The promotion merge was executed with `expected_head_sha=75d10d35d4757496390debf8e4b4f9efb44c5432`; `main` was then verified at `fada723f43613e5e0f061cab24445573ac298998` with parents `ce78f120e8ed2974d6174e475cc7572afcfe41e0` and `75d10d35d4757496390debf8e4b4f9efb44c5432`.

## Native validation harness policy

The Implementation 4 investigation produced reusable harness lessons that are now regression knowledge:

- instrument explicit markers for process boot, Electron readiness, product import, and each lifecycle boundary;
- do not attribute a timeout to product code before the product-entry marker occurs;
- use Node `child_process` for Windows native orchestration in this path instead of stacking PowerShell native pipelines and `.cmd` wrappers;
- gate process success on exit status, not stderr output;
- use a valid temporary Electron application entry;
- on the current Windows/Electron 40.10.2 target, do not block module evaluation with top-level `await app.whenReady()`; the paired H-003 control proved `.then(...)` reaches readiness while TLA stalls in that environment;
- once a versioned probe exists, reuse/improve it instead of reconstructing ad hoc runners.

Operational history is kept in `engineering-journal/CURRENT.md`.

## Baseline comparison for pre-existing failures

When a broad gate is already red on `main` and blocks causality for a narrowly scoped change, reproduce the exact main base and candidate with the same OS/toolchain/install/commands. Compare failure signatures rather than failure counts.

A baseline/candidate A/B may establish that a failure is pre-existing and that the scoped change is non-regressive, but it must not be described as a green broad gate. Keep the permanent gate red until its underlying issue is fixed.

For the current Windows baseline see KI-006 in `KNOWN_ISSUES.md`.

## Required browser-foundation invariants

As corresponding implementations land, tests must establish relationships rather than freeze incidental values:

- GUI/Desktop browser surface capability is session-scoped;
- controller reachability affects execution/recovery, not whether a valid session surface is known;
- BrowserTask can hide/show/park without replacing a live page;
- destroy is explicit and different from hide;
- task-bound controller loss is fail-closed;
- routing-disabled stays internal-only;
- future Chat Browser View and Browser Hub reference the same BrowserTask/runtime;
- only one host owns the live `WebContentsView` at a time;
- future host transfer/resize does not overlap;
- multiple BrowserTasks remain isolated;
- BrowserSessionState restoration preserves safe logical metadata without credentials;
- Chromium profile persistence is tested separately from logical task/session restoration;
- future Preview compatibility in Workstation mode does not create an independent duplicate lane.

## Later full browser-foundation smoke

The final broader browser foundation, after later surfaces exist, must also cover Chat Browser View ↔ Browser Hub shared task/page behavior, human control, resize/maximize/restore, second-task isolation, profile login persistence, controller-loss fail-closed behavior, and Preview compatibility.

Those later steps must remain future work; the narrower Implementation 4 pass must not be used to mark them complete.

## Failure policy

A red gate is investigated, not disabled. Never make CI green by deleting coverage, weakening a valid expectation, or turning a baseline-equivalent failure into a claimed pass. Record what failed, establish causality, and use the smallest test that corresponds to the actual risk.
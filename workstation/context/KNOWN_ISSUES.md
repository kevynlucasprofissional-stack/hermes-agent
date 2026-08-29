# Workstation Known Issues

This file records observed/reproduced gaps and the evidence boundary around them. A listed symptom is **not** permission to assume a root cause; verify current `main` and any explicitly named candidate before changing code.

## KI-002 — Preview and Workstation Browser are separate browser lanes

**Observed:** Preview and the main Browser surface can show different independently navigated pages for what the user regards as one web task.

**Do not fix by:** synchronizing URLs between two pages.

**Target invariant:** Workstation-mode Preview compatibility and Browser Hub/Chat Browser View reference one BrowserTask/live page.

**Implementation 4 status:** unchanged. The BrowserTask lifecycle deliberately does not collapse Preview into the Workstation runtime.

## KI-003 — Complete logical BrowserSessionState does not survive restart

**Observed on current `main`:** the Chromium profile persists but logical tab/task maps are memory-only, so restarting Desktop loses those mappings.

**Implementation 4 narrowed this gap:** safe BrowserTask metadata is versioned and atomically persisted. Restored tasks normalize to `parked` / `recoveryState: restored` and lazily receive one replacement page when used. Real Windows/Electron smoke validated that behavior.

This does **not** yet persist the complete browser session model: ordinary/manual tab ordering, active generic tab, richer URL/title restoration, controller/session/run/Kanban linkage, and all host state remain incomplete.

**Important boundary:** a `WebContentsView` and its JavaScript heap are process-local. Restart recovery means logical BrowserTask restoration plus controlled page recreation/reconnection, not serialization/resurrection of the same renderer object.

**Remaining target invariant:** a safe, versioned BrowserSessionState restores all intended logical metadata separately from Chromium profile/auth state, with explicit recovery semantics for process-local page objects.

## KI-004 — Native browser surface can overlap another Desktop pane

**Observed:** during bootstrap validation, independent Preview and Workstation Browser surfaces could visually overlap and resizing changed the overlap.

**Current evidence:** the Browser renderer already uses `ResizeObserver` and `getBoundingClientRect`, so “add another resize observer” is not an established fix.

**Target invariant:** one live `WebContentsView` host at a time plus an explicit host/viewport ownership contract; validate resize, maximize/restore, sidebar/pane changes, and host transfer.

**Implementation 4 status:** lifecycle semantics now make a later single-host transfer contract easier to express, but Chat/Hub/Preview host unification is not implemented here. This issue remains open.

## KI-006 — Broad Windows Desktop suites contain pre-existing portability/test failures

**Observed:** after the canonical-source installer reached a clean install and passing Desktop typecheck, the broad UI and Electron/platform suites remained red on Windows.

**Causality status:** **not caused by the Workstation canonical-source / BrowserTask changes based on controlled baseline evidence.** Baseline and candidate diagnostics share the same structural failure classes around Windows path/permission assumptions, SSH ControlPath/Include assumptions, POSIX virtualenv layout, Darwin staging, and PowerShell timing. Runner flake can change raw failure counts without changing those classes.

**Current policy:** keep the broad workflow red while these failures exist. UI and platform suites run independently and a final aggregator preserves failure if either is red. A green focused BrowserTask step does not convert the broad red gate into a pass.

**Required action:** fix the underlying Windows portability/test assumptions in a separate scoped implementation with baseline regression tests. Do not weaken or delete those suites merely to make Workstation CI green.

## KI-007 — `Session not found` / exported `session: null`

**Observed:** session export/logging from the browser validation cycle included a consistent message `session_id` while the exported session object was `null`, and logs previously included HTTP 404 `Session not found`.

**Causality status:** **unproven**. Preview/browser behavior has independent reproduced gaps, so this issue must not be used as their explanation without a causal trace.

**Required proof before any SessionDB/Gateway change:** reproduce on current `main` → identify endpoint/caller/session id → determine lineage/compression/rotation expectations → identify the responsible line/race → add regression test → only then change core.

## Resolved regression classes

### KI-005 — BrowserTask lifecycle was implicit on current `main`

**Original symptom:** `ownerTaskId`, `taskTabs`, parking, and attach/detach existed, but there was no complete first-class `show`/`hide`/`park`/`destroy` BrowserTask contract.

**Resolved candidate behavior:** PR #9 formalizes BrowserTask around the existing `taskTabs`/`BrowserEntry.ownerTaskId` ownership primitives without introducing a second page store. `hide` and `park` preserve a live page, `show` re-exposes it, repeated task creation is idempotent, missing pages recover under the same logical task, and `destroyTask` is explicit.

**Automated regression coverage:**
- `apps/desktop/electron/workstation-browser-task.test.ts`;
- `apps/desktop/electron/workstation-browser-runtime-task.test.ts`;
- focused BrowserTask step in `Workstation Browser Windows`.

**Real native evidence:** `workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs` ran on Windows `10.0.26200`, Electron `40.10.2`, repository head `d8acc752133b125b9619cbc7fe09199f1283a22b` and emitted:
- `H004_LIVE_DESTROY_PASS`;
- `H004_RESTART_PASS`;
- `H004_CLASSIFICATION=VALIDATED`.

The native smoke proved same-page identity across hide/show and park/show, explicit destruction, two-process logical restart restoration/recreation, exactly-one-page ownership, and structural secret isolation.

**Carry-forward rule:** the native result may be associated with a later final documentation-only head only after Git comparison proves the relevant Desktop product files and H-004 probe are unchanged. Promotion of the PR is a separate integration gate and does not change the fact that the KI-005 behavior itself is now validated.

### KI-001 — Desktop Browser capability could disappear from the model schema

**Resolved behavior:** Desktop/GUI Browser surface capability is derived from active Gateway session context instead of process-global Desktop identity or controller reachability. Selected Workstation-routed browser schemas remain present during controller startup/reachability races, while controller health/recovery governs execution. The tool-definition cache includes the session capability fingerprint so Desktop results cannot leak into TUI/CLI.

**Security/ownership boundary:** only the narrow set of actions actually routed through the embedded Workstation Browser is force-preserved, and only when those names are already selected by active toolsets. `browser_exec` is not promoted. TUI/CLI sessions do not gain Desktop capability merely from `HERMES_DESKTOP=1`.

**Regression coverage:** `tests/tui_gateway/test_workstation_browser_schema_capability.py`.

### RI-001 — Normal Workstation install rewrote tracked source before validation

**Resolved behavior:** the normal installer treats the committed downstream tree as canonical. It validates integration in read-only mode, installs isolated dependencies, prepares runtime state outside tracked source, and compares Git status before/after installation.

**Evidence:** canonical-source validation on Implementation 2 and subsequent Workstation CI/Windows install gates.

## Closing an issue here

When an issue is fixed, move it to the resolved section with the validated behavior and test/evidence boundary. Do not delete the historical symptom if it documents a regression class that future tests protect.

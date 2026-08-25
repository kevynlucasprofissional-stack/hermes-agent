# Workstation Known Issues

This file records observed/reproduced gaps and the evidence boundary around them. A listed symptom is **not** permission to assume a root cause; verify current `main` and any explicitly named candidate before changing code.

## KI-002 — Preview and Workstation Browser are separate browser lanes

**Observed:** Preview and the main Browser surface can show different independently navigated pages for what the user regards as one web task.

**Do not fix by:** synchronizing URLs between two pages.

**Target invariant:** Workstation-mode Preview compatibility and Browser Hub/Chat Browser View reference one BrowserTask/live page.

**Implementation 4 status:** unchanged. The BrowserTask lifecycle candidate deliberately does not collapse Preview into the Workstation runtime yet.

## KI-003 — Complete logical BrowserSessionState does not survive restart

**Observed on current `main`:** the Chromium profile persists but logical tab/task maps are memory-only, so restarting Desktop loses those mappings.

**Implementation 4 candidate:** safe BrowserTask metadata is now versioned and atomically persisted. Restored tasks are normalized to `parked` and lazily receive one replacement page when used. This narrows the original gap, but it does **not** yet persist the complete browser session model: ordinary/manual tab ordering, active generic tab, richer URL/title restoration, controller/session/run/Kanban linkage, and all host state remain incomplete.

**Important boundary:** a `WebContentsView` and its JavaScript heap are process-local. Restart recovery means logical BrowserTask restoration plus controlled page recreation/reconnection, not serialization/resurrection of the same renderer object.

**Remaining target invariant:** a safe, versioned BrowserSessionState restores all intended logical metadata separately from Chromium profile/auth state, with explicit recovery semantics for any process-local page objects.

## KI-004 — Native browser surface can overlap another Desktop pane

**Observed:** during bootstrap validation, independent Preview and Workstation Browser surfaces could visually overlap (for example, pages showing Example Domain and Instagram at the same time) and resizing changed the overlap.

**Current evidence:** the Browser renderer already uses `ResizeObserver` and `getBoundingClientRect`, so “add another resize observer” is not an established fix.

**Target invariant:** one live `WebContentsView` host at a time plus an explicit host/viewport ownership contract; validate resize, maximize/restore, sidebar/pane changes, and host transfer.

**Implementation 4 status:** lifecycle semantics now make a later single-host transfer contract easier to express, but Chat/Hub/Preview host unification is not implemented here. This issue remains open.

## KI-005 — BrowserTask lifecycle is implicit on current `main`

**Observed on current `main`:** `ownerTaskId`, `taskTabs`, parking, and attach/detach exist, but there is no complete first-class `show`/`hide`/`park`/`destroy` contract. A hidden page can remain alive while the agent lacks a semantic operation to re-expose the same task without navigating again.

**Implementation 4 candidate resolution:** PR #9 introduces a first-class BrowserTask lifecycle around the existing `taskTabs`/`ownerTaskId` ownership primitives. `hide` and `park` preserve a live page, `show` re-exposes it, repeated task creation is idempotent, missing pages recover under the same logical task, and `destroyTask` is explicit. Focused lifecycle and runtime-adapter regression tests were added.

**Acceptance boundary:** keep this issue open until one final PR #9 head has the focused BrowserTask gate recorded and the required real Windows Desktop lifecycle smoke passes. Automated mocks/typechecks alone are not sufficient evidence for the native behavior claim. When accepted, move this item to Resolved regression classes with the exact candidate SHA/run/smoke evidence.

## KI-006 — Broad Windows Desktop suites contain pre-existing portability/test failures

**Observed:** after the canonical-source installer reached a clean install and passing Desktop typecheck, the broad UI and Electron/platform suites remained red on Windows.

**Causality status:** **not caused by Implementation 2 based on controlled A/B evidence.** Exact `main` base `a894464ba7f0f455cea28ca56a33a6b178b0a9af` and canonical-source candidate `9fd19c6ef73dc80ae9301eb983dbf2fdda7d6ef1` were run with the same Windows/Node commands. Baseline diagnostic `32815134750` and candidate diagnostic `32815214866` both fail the same UI test because the `../routes` mock in `src/app/contrib/surfaces.test.tsx` does not export `BROWSER_ROUTE`. Both platform diagnostics also share the same structural failure classes around POSIX permission bits, Windows path normalization/8.3 aliases, SSH ControlPath/Include assumptions, POSIX virtualenv layout, Darwin staging, and PowerShell handoff timing. Runner flake can change the raw failure count without changing those shared categories.

**Current policy:** keep the broad workflow red while these failures exist. The UI and platform suites run independently and a final aggregator preserves failure if either is red, so one failure does not hide the other. Implementation 4 additionally exposes its BrowserTask regression files as a separate named outcome in the same Windows job; a green focused BrowserTask step does not convert the broad red gate into a pass.

**Required action:** fix the underlying Windows portability/test assumptions in a separate, scoped implementation with baseline regression tests. Do not weaken or delete those suites merely to make Workstation CI green.

## KI-007 — `Session not found` / exported `session: null`

**Observed:** session export/logging from the browser validation cycle included a consistent message `session_id` while the exported session object was `null`, and logs previously included HTTP 404 `Session not found`.

**Causality status:** **unproven**. Preview/browser behavior has independent reproduced gaps, so this issue must not be used as their explanation without a causal trace.

**Required proof before any SessionDB/Gateway change:** reproduce on current `main` → identify endpoint/caller/session id → determine lineage/compression/rotation expectations → identify the responsible line/race → add regression test → only then change core.

## Resolved regression classes

### KI-001 — Desktop Browser capability could disappear from the model schema

**Resolved behavior:** Desktop/GUI Browser surface capability is derived from the active Gateway session context instead of process-global Desktop identity or controller reachability. Selected Workstation-routed browser schemas remain present during controller startup/reachability races, while controller health/recovery still governs execution. The tool-definition cache includes the session capability fingerprint so Desktop results cannot leak into TUI/CLI.

**Security/ownership boundary:** only the narrow set of actions actually routed through the embedded Workstation Browser is force-preserved, and only when those names are already selected by the active toolsets. `browser_exec` is not promoted. TUI/CLI sessions do not gain the Desktop capability even if `HERMES_DESKTOP=1` exists in the process environment.

**Regression coverage:** `tests/tui_gateway/test_workstation_browser_schema_capability.py` exercises a false browser probe in a Desktop session, same-process Desktop→TUI cache isolation, rejection of process-env-only Desktop identity, and Desktop capability without the process env flag.

### RI-001 — Normal Workstation install rewrote tracked source before validation

**Resolved behavior:** the normal installer now treats the committed downstream tree as canonical. It validates `apply_core_integration.py --check` in read-only mode, no longer invokes the Electron compatibility mutator or source integration patcher, installs Python dependencies into the repository `.venv`, installs Node workspaces from the lockfile, prepares runtime state outside tracked source, and compares Git status before/after installation.

**Evidence:** canonical-source candidate `9fd19c6ef73dc80ae9301eb983dbf2fdda7d6ef1`, `Workstation Browser Windows` run `32813688219`: committed integration validation, normal install, checkout-clean assertion, and Desktop typecheck all passed. `Workstation CI` run `32813688213` also passed the Workstation contracts. The final Implementation 2 canonical-source result is committed on downstream `main` at `2864da0eba97742af67420a799c767264bea62e8`.

## Closing an issue here

When an issue is fixed, replace the open description with the validated behavior/test evidence or move it to the resolved section. Do not simply delete the historical symptom if it documents a regression class that future tests protect.
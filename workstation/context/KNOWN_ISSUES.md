# Workstation Known Issues

This file records observed/reproduced gaps and the evidence boundary around them. A listed symptom is **not** permission to assume a root cause; verify current `main` before changing code.

## KI-001 — Desktop Browser capability can disappear from the model schema

**Observed:** a real Desktop session could use Preview tools while the model reported that it did not have a tool for the main Browser surface.

**Current evidence:** `browser_*` is registered and Workstation routing exists. Availability/reachability checks participate in schema collection, and registry availability is cached process-wide. The repository-wide `AGENTS.md` explicitly states that GUI surface identity is session-scoped rather than a `check_fn`/process-env property.

**Required proof before closure:** trace Desktop platform → Gateway toolsets → registry → schema, then test a GUI session with the relevant process env absent and with controller startup/reachability transitions.

## KI-002 — Preview and Workstation Browser are separate browser lanes

**Observed:** Preview and the main Browser surface can show different independently navigated pages for what the user regards as one web task.

**Do not fix by:** synchronizing URLs between two pages.

**Target invariant:** Workstation-mode Preview compatibility and Browser Hub/Chat Browser View reference one BrowserTask/live page.

## KI-003 — Logical tabs and task mappings do not survive restart

**Observed:** the Chromium profile persists but the runtime's logical tab/task maps are memory-only, so restarting Desktop loses those tabs/mappings.

**Target invariant:** safe, versioned BrowserSessionState restores logical metadata separately from Chromium profile/auth state.

## KI-004 — Native browser surface can overlap another Desktop pane

**Observed:** during bootstrap validation, independent Preview and Workstation Browser surfaces could visually overlap (for example, pages showing Example Domain and Instagram at the same time) and resizing changed the overlap.

**Current evidence:** the Browser renderer already uses `ResizeObserver` and `getBoundingClientRect`, so “add another resize observer” is not an established fix.

**Target invariant:** one live `WebContentsView` host at a time plus an explicit host/viewport ownership contract; validate resize, maximize/restore, sidebar/pane changes, and host transfer.

## KI-005 — BrowserTask lifecycle is implicit

**Observed:** `ownerTaskId`, `taskTabs`, parking, and attach/detach exist, but there is no complete first-class `show`/`hide`/`park`/`destroy` contract. A hidden page can remain alive while the agent lacks a semantic operation to re-expose the same task without navigating again.

**Target invariant:** hide and park preserve the page/task, show rehosts the same page, destroy is explicit.

## KI-006 — Broad Windows Desktop suites contain pre-existing portability/test failures

**Observed:** after the canonical-source installer reached a clean install and passing Desktop typecheck, the broad UI and Electron/platform suites remained red on Windows.

**Causality status:** **not caused by Implementation 2 based on controlled A/B evidence.** Exact `main` base `a894464ba7f0f455cea28ca56a33a6b178b0a9af` and canonical-source candidate `9fd19c6ef73dc80ae9301eb983dbf2fdda7d6ef1` were run with the same Windows/Node commands. Baseline diagnostic `32815134750` and candidate diagnostic `32815214866` both fail the same UI test because the `../routes` mock in `src/app/contrib/surfaces.test.tsx` does not export `BROWSER_ROUTE`. Both platform diagnostics also share the same structural failure classes around POSIX permission bits, Windows path normalization/8.3 aliases, SSH ControlPath/Include assumptions, POSIX virtualenv layout, Darwin staging, and PowerShell handoff timing. Runner flake can change the raw failure count without changing those shared categories.

**Current policy:** keep the broad workflow red while these failures exist. UI and platform suites run independently and a final aggregator preserves failure if either is red, so one failure does not hide the other.

**Required action:** fix the underlying Windows portability/test assumptions in a separate, scoped implementation with baseline regression tests. Do not weaken or delete those suites merely to make Workstation CI green.

## KI-007 — `Session not found` / exported `session: null`

**Observed:** session export/logging from the browser validation cycle included a consistent message `session_id` while the exported session object was `null`, and logs previously included HTTP 404 `Session not found`.

**Causality status:** **unproven**. Preview/browser behavior has independent reproduced gaps, so this issue must not be used as their explanation without a causal trace.

**Required proof before any SessionDB/Gateway change:** reproduce on current `main` → identify endpoint/caller/session id → determine lineage/compression/rotation expectations → identify the responsible line/race → add regression test → only then change core.

## Resolved regression classes

### RI-001 — Normal Workstation install rewrote tracked source before validation

**Resolved behavior:** the normal installer now treats the committed downstream tree as canonical. It validates `apply_core_integration.py --check` in read-only mode, no longer invokes the Electron compatibility mutator or source integration patcher, installs Python dependencies into the repository `.venv`, installs Node workspaces from the lockfile, prepares runtime state outside tracked source, and compares Git status before/after installation.

**Evidence:** canonical-source candidate `9fd19c6ef73dc80ae9301eb983dbf2fdda7d6ef1`, `Workstation Browser Windows` run `32813688219`: committed integration validation, normal install, checkout-clean assertion, and Desktop typecheck all passed. `Workstation CI` run `32813688213` also passed the Workstation contracts. The final consolidated Implementation 2 commit must preserve these checks when revalidated.

## Closing an issue here

When an issue is fixed, replace the open description with the validated commit/test evidence or move it to the resolved section. Do not simply delete the historical symptom if it documents a regression class that future tests protect.

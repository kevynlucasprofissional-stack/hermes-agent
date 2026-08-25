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

## KI-006 — Windows Browser workflow is not green at the bootstrap baseline

**Observed:** the bootstrap head passed Workstation CI and Docker build, but `Workstation Browser Windows` failed at Desktop typecheck after dependency installation; UI/platform steps were skipped.

**Required action:** inspect the exact compiler error and fix the cause. Do not weaken or skip the typecheck to obtain a green workflow.

## KI-007 — `Session not found` / exported `session: null`

**Observed:** session export/logging from the browser validation cycle included a consistent message `session_id` while the exported session object was `null`, and logs previously included HTTP 404 `Session not found`.

**Causality status:** **unproven**. Preview/browser behavior has independent reproduced gaps, so this issue must not be used as their explanation without a causal trace.

**Required proof before any SessionDB/Gateway change:** reproduce on current `main` → identify endpoint/caller/session id → determine lineage/compression/rotation expectations → identify the responsible line/race → add regression test → only then change core.

## Closing an issue here

When an issue is fixed, replace the open description with the validated commit/test evidence or move it to a short resolved section. Do not simply delete the historical symptom if it documents a regression class that future tests protect.
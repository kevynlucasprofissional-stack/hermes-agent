# Browser Ownership & Recovery Reconciliation — 2026-09-18

## Status

**IMPLEMENTATION LANDED / CORRECTIVE P0 REOPENED (2026-09-19)** — The 2026-09-18 patch closed the original wiring/runtime defects and its focused test evidence is retained, but a post-implementation audit found residual cleanup, first-attach, session-alias and product-E2E gaps. Do not classify this lane as fully qualified until the corrective gate below passes.

This lane is complementary to
[BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md](BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md).
Browser Operational Admission answers whether Hermes can safely express, authorize,
dispatch and verify an operation. This document answers a different question:

> When a chat owns BrowserTask T, do Chat UI, Browser Hub, BrowserTask state,
> logical/physical tab recovery and the one native Chromium viewport converge on
> that same identity before and after restart?

The audit found that persistence is not simply "losing the browser". The dominant
failure is reconciliation across existing owners after chat switching and process restart.

## User-visible symptoms

1. native Browser flashes when the pointer moves over other chat rows;
2. after restart a chat can reopen with Browser on `Blank Page`;
3. the agent can continue using the correct BrowserTask while the user sees
   `about:blank`;
4. Browser Hub can show tasks as `Parked` while an agent is actively using one.

These form one cross-layer failure class.

## Validated code findings

### BOR-001 — tooltip poppers are treated as native-view occluders

`apps/desktop/src/app/browser/index.tsx` and
`apps/desktop/src/app/chat/right-rail/workstation-browser-pane.tsx` both observe
overlay DOM and call `setVisible(false|true)`. Their selectors include
`[data-radix-popper-content-wrapper]`.

Radix tooltips also create that wrapper, and chat rows use `OverflowTip`/`Tip`.
Ordinary hover can therefore remove and re-add the native `WebContentsView`.

**Correction:** use one explicit/shared native-view occlusion contract. Tooltips
must never hide Browser. Real menus/dialogs/selects that need to cover native
Chromium should opt into an explicit marker such as
`data-native-view-occluder="true"` or an equivalent centralized helper.
Do not mask this with debounce.

### BOR-002 — restart intentionally restores BrowserTasks as parked metadata

`workstation-browser-task.ts::restore()` preserves logical ownership but restores
tasks as `parked/restored`. BrowserTask-owned tabs use `browser-task-lazy`
recovery in BrowserSessionState. This is valid because WebContents identity is
process-local.

### BOR-003 — `ensure()` can foreground `about:blank` while a task tab is pending

If the logical active BrowserTask tab is not yet a live entry,
`WorkstationBrowserRuntime.ensure()` can create/activate `about:blank`.
The persisted task/safe URL can still exist, but the visible viewport points at
the fallback.

**Correction:** `about:blank` is a true empty fallback and must not win foreground
ownership over the recoverable task explicitly requested by the current Browser surface.

### BOR-004 — controller activity can coexist with `Parked`

`entryForTask()` can materialize a task entry for controller execution. If it is
not both active and attached, the lifecycle projection parks it. A live page can
therefore receive snapshot/click/type/navigate while task status remains `parked`.

**Correction:** visibility and execution activity are orthogonal. Preserve
`visible|hidden|parked` as presentation truth and derive/project
`working|waiting|idle|human_control|failed` from existing execution owners.

### BOR-005 — `preferredTaskId` exists in runtime/tests but is dropped by product wiring

`WorkstationBrowserRuntime.attach(window, bounds, host, preferredTaskId?)` and
current tests already support chat-specific task selection.

But:
- preload exposes `attach(bounds, host)`;
- `WorkstationBrowserBridge` exposes `attach(bounds, host)`;
- `WorkstationBrowserPane` calls `bridge.attach(bounds, 'chat')`.

**Correction:** complete bridge/preload/UI wiring and resolve preferred task through
existing canonical session/lineage identity helpers. Do not add a second map.

### BOR-006 — preferredTaskId alone is insufficient after restart

After restart a task-owned tab can exist only in `pendingSessionTabs`. The semantic
operation Chat needs is:

~~~text
attach/show BrowserTask T for session S
  -> resolve T from canonical ownership
  -> reuse healthy live entry OR materialize its one pending restored tab
  -> restore safe URL metadata
  -> activate T
  -> reconcile task visibility
  -> attach the one native viewport to the requesting host
~~~

Strengthen the existing attach path or add one narrow task-bound attach/show
primitive. Do not make the renderer compose several lifecycle mutations.

### BOR-007 — detach and visibility are not host-fenced

`setBounds(... expectedHost)` already recognizes that Chat and Hub can share one
BrowserWindow. `detach()` and `setVisible()` lack equivalent fencing.

A stale Chat cleanup can therefore detach/hide a viewport just acquired by Hub,
or vice versa.

**Correction:** stale `detach('chat')`/`setVisible(...,'chat')` must be no-op
when the viewport owner is Hub, and vice versa.

### BOR-008 — Browser Hub conflates visibility with activity

TaskRail primarily treats `visible` as Active and `parked` as Background.
That describes viewport state, not whether Hermes is working.

A task must be able to be `parked + working` without contradiction or foreground theft.

## Canonical ownership model

Do not create a new Browser/session state owner.

Existing authorities remain:
- BrowserTask lifecycle — logical Browser task ownership/status;
- BrowserSessionState — durable safe task/tab recovery metadata;
- Electron runtime — live WebContents/tab/viewport state;
- session/preview stores — whether the user's chat contains Browser surface;
- TaskRun/session/journal owners — execution activity.

The work is reconciliation between them.

Prefer deriving durable presentation intent from existing session-scoped preview
state + active session before inventing a persisted `desiredPresentation` field.

## Canonical invariant

For chat **C** associated with BrowserTask **T**:

> If C is active and C's Browser surface is open, there is at most one live page
> for T; T is the preferred task of that viewport; Chat UI, Browser Hub,
> BrowserTask, activeTabId and viewportHost deterministically converge on the
> same task/tab identity, including after restart.

Additional invariants:
1. background activity never steals foreground;
2. explicit user transfer may move the one viewport;
3. visibility is neither lifecycle nor execution activity;
4. tooltip never owns native-view occlusion;
5. stale host cleanup cannot affect a newer owner;
6. lazy recovery materializes at most one page per BrowserTask;
7. unsafe URL metadata is never promoted into recovery;
8. compaction/fork aliases reuse canonical identity helpers;
9. no external/legacy Browser fallback is introduced.

## Implementation order

### P0.1 — Explicit native-view occlusion
Centralize duplicated Chat/Hub logic, remove generic popper authority, and mark
only real native-view occluders.

### P0.2 — Host fencing
Extend bridge/preload/main/runtime so
`detach(expectedHost)` and `setVisible(visible, expectedHost)` cannot affect
another host. Preserve sender-window checks too.

### P0.3 — Preferred-task wiring
Propagate `preferredTaskId` through types, preload and Chat Browser pane into the
existing runtime path. Resolve through existing session lineage semantics.

### P0.4 — Task-bound lazy recovery
When Chat requests T, recover exactly one pending task tab, preserve safe metadata,
activate it before attach, and do not foreground fallback `about:blank`.

### P0.5 — Boot/chat-switch reconciler
Reconcile:
`active session -> Browser surface -> BrowserTask -> pending/live tab -> activeTabId -> viewportHost`.

Background actions update activity/projections but never steal foreground.

### P0.6 — Hub activity truth
Expose visibility and execution activity independently using existing owners.

### P0.7 — Product-level regression gate
Test renderer/preload/runtime seams, not only direct runtime calls.

## Required regression contracts

1. `OverflowTip` hover does not call `setVisible(false)`;
2. real menu/dialog/select occluder does hide/restore native view;
3. stale Chat cleanup cannot detach/hide Hub and vice versa;
4. Chat A/Browser A -> Chat B/Browser B -> Chat A restores A with one page;
5. A/B sequence survives process restart and lazy recovery;
6. requested recoverable task wins over fallback `about:blank`;
7. exactly one WebContents is materialized per restored BrowserTask;
8. background controller work can be `parked + working` without foreground theft;
9. when its own Browser pane is active, recovered task converges pane/Hub/task state;
10. parent-session/compaction aliases still resolve the correct task;
11. explicit Chat <-> Hub transfer remains correct;
12. hide/show, park/show, destroy, H004 and H013 remain green;
13. no duplicate Browser/session/task store is introduced.

## Validation ladder

Focused renderer RED/GREEN -> focused Electron runtime/session-state tests ->
Desktop typecheck -> affected Desktop UI/Electron suites -> H004 native BrowserTask
smoke -> H013 integrated Desktop/Browser E2E -> Workstation/Work100 when affected.

A direct runtime test of `attach(... preferredTaskId)` is necessary but
insufficient because the defect is at the production wiring seam.

## Explicit non-solutions

Do not:
- debounce tooltip hover;
- eagerly resurrect every parked task;
- let background work steal foreground;
- redefine `parked` as execution-idle;
- add a parallel Browser/session/presentation database;
- treat `about:blank` as authoritative over a requested recoverable task;
- weaken safe URL restoration;
- bind durable ownership to transient WebContents IDs;
- duplicate Chat/Hub occlusion observers with different selector lists.

## Exit criterion

Close only when the product proves:

~~~text
Chat A -> Browser A
Chat B -> Browser B
restart Hermes Work
open Chat B -> Browser B coherent
switch Chat A -> Browser A coherent
background Browser activity -> Hub activity without foreground theft
hover tooltips -> no Browser flicker
Chat <-> Hub transfer -> no stale cleanup blanking viewport
~~~

with one BrowserTask owner, one native Chromium runtime, bounded lazy recovery and
no regression in Browser Operational Admission, H004/H013 or TaskRun fencing.

## Post-implementation audit — 2026-09-19

Audit baseline: current `main@6328894c0a5f51a61da772593842c25d377d553f`.

The architecture direction remains correct, but the prior closure claim was too strong.

### BOR-009 — bulk cleanup can destroy active parked work

`TaskRail` derives execution activity and can correctly render
`parked + working`. However `BrowserView.handleClearParked()` calls
`bridge.clearParkedTasks()`, and runtime `clearParkedTasks()` filters only
`task.status === 'parked'` before destroying every match.

A single idle parked task can therefore make the Clear action available while another
parked task is still working/waiting/under human control; the backend bulk clear then
destroys both.

**Required correction:** the destruction boundary itself must be execution-aware.
Do not rely only on renderer filtering.

### BOR-010 — first renderer attach can still be task-unbound

`WorkstationBrowserPane` starts with `EMPTY_STATE.tasks=[]`, computes no
`preferredTaskId`, and may call `attach(bounds, 'chat', undefined)` before the
first runtime state response reveals restored BrowserTasks. The runtime can create/
attach a fallback blank and only then receive a second task-bound attach.

The direct recovery test does not exercise this because it supplies
`preferredTaskId` from the start.

**Required correction:** resolve/retrieve the matching BrowserTask before the first
visible Chat attach after restart. Eventual convergence is insufficient if the user
can see an intermediate blank.

### BOR-011 — product restart proof is incomplete

Current H013 proves real Electron viewport/load behavior, but does not yet encode the
new `preferredTaskId` attach contract or reproduce:

`A -> B -> process restart -> cold renderer mount on B -> switch A`.

**Required correction:** extend H013 rather than creating another Browser harness.

### BOR-012 — session alias proof is incomplete

The Chat resolver uses `lineageAliases()`, whose canonical index covers live
`id` and `_lineage_root_id`. Explicit `parent_session_id` behavior is not
proven for BrowserTask lookup.

**Required correction:** reuse/extend canonical session identity helpers and add a
behavioral regression. Do not add a Browser-specific parallel alias registry.

### BOR-013 — native-view occlusion is centralized but not fully explicit

`data-native-view-occluder="true"` exists, but generic role/slot selectors remain
parallel authorities.

**Required correction:** make deliberate opt-in marking the authoritative occlusion
contract unless a narrower documented exception is demonstrably required.

### Corrective exit criterion

This lane closes only when all of the following are true:

1. bulk clear preserves working/waiting/human-controlled parked tasks;
2. a recoverable BrowserTask is selected before the first visual Chat attach;
3. extended H013 proves A/B restart through renderer + preload + IPC + runtime;
4. live/root/parent session aliases converge on one BrowserTask;
5. only explicit occluders can hide native Chromium;
6. H004/H013/affected Desktop tests are green on the candidate head;
7. no second Browser/session/task state owner was introduced.

The separate Browser Operational Admission CI failure must be tracked separately, but
repository-wide "100% green" wording is prohibited while exact-head required workflows
remain red or pending.

## Implementation & Validation Summary (2026-09-18)

1. **Native-View Occlusion Centralization (BOR-001):**
   - Created `apps/desktop/src/app/browser/native-view-occlusion.ts` with selector `[data-native-view-occluder="true"], [role="dialog"], [role="menu"]`. Stripped all authority from `[data-radix-popper-content-wrapper]`.
   - Added `data-native-view-occluder="true"` to `dialog.tsx`, `dropdown-menu.tsx`, `context-menu.tsx`, `select.tsx`, and `popover.tsx`.
   - Wired `useNativeViewOcclusion(bridge, host)` in both `workstation-browser-pane.tsx` and Browser Hub `index.tsx`.
2. **Host Fencing across IPC & Runtime (BOR-007):**
   - Extended IPC handlers and runtime methods `detach(expectedHost?)` and `setVisible(visible, expectedHost?)` in `apps/desktop/electron/workstation-browser-runtime.ts`.
   - Rejects stale calls if `expectedHost !== viewportHost`. Ensures `attach()` always sets `viewVisible = true` to prevent inheriting stale hidden state.
3. **Preferred-Task Wiring (BOR-005):**
   - Extended `WorkstationBrowserBridge` and preload to pass `preferredTaskId` through `attach(bounds, host, preferredTaskId?)`.
   - `workstation-browser-pane.tsx` matches active session, parent session, and lineage roots to select `preferredTaskId` deterministically and reattaches when switching chats.
4. **Task-Bound Lazy Recovery (BOR-002, BOR-003, BOR-006):**
   - Restructured `WorkstationBrowserRuntime.attach()`: materializes `preferredTaskId` from `pendingSessionTabs` via `rawEntryForTask(preferredTaskId, true)` before physical fallback blank creation.
   - Restores safe URL metadata and discards ephemeral unnavigated `about:blank`.
   - Fails closed against cross-session leakage when a chat attaches without an owned task.
5. **Separation of Visibility and Activity (BOR-004, BOR-008):**
   - In `task-rail.tsx`, implemented `getTaskExecutionActivity` deriving `working | waiting | human_control | idle` from `$sessionDotStateById` and session lineage without conflating viewport visibility (`visible | parked`).
   - Added `Working` section in TaskRail and preserved parked working tasks against premature clearing.
6. **Verification Results:**
   - Vitest suite: 88 passed across 9 test files (100% green).
   - Dedicated regressions: `native-view-occlusion.test.ts` (7/7 passed), `task-rail.test.ts` (5/5 passed), `workstation-browser-runtime-task.test.ts` (28/28 passed), `workstation-browser-runtime-recovery.test.ts` (2/2 passed).
   - TypeScript check: 0 errors across `.` (`tsconfig.json`), `tsconfig.electron.json`, `tsconfig.e2e.json`.
   - H004 native browser smoke probe: passed all phases (`H004_CLASSIFICATION=VALIDATED`).
   - Work100 regression suite: 30 PASS, 0 FAIL, 0 COVERAGE_GAP, 0 NOT_RUN_ENVIRONMENT.

# Browser Ownership & Recovery Reconciliation — 2026-09-18

## Status

**P0 OPEN / code-level root causes validated / implementation not yet applied.**

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

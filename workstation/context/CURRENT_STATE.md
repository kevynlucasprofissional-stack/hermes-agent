# Current State

Snapshot date: 2026-08-25. Base: downstream `main` after the Workstation bootstrap merge.

This file describes **observed implementation state**, not the target architecture. When it disagrees with code on current `main`, inspect the code and update this file.

## Working now

- Hermes Workstation is integrated into this downstream fork and the Desktop application can expose a dedicated `Browser` route.
- The internal browser runtime uses Electron Chromium through `WebContentsView` with a persistent Electron session/partition.
- Manual Browser navigation, tab creation/activation/close, back/forward/reload, pause/resume, focus, and human/agent control ownership are implemented.
- The Workstation controller is localhost-bound and token-authenticated.
- `browser_*` routing already attempts the Workstation controller before fallback and has tests for bound fail-closed behavior and routing-disabled/internal-only behavior.
- The browser profile preserves Chromium-managed site state such as cookies/localStorage/IndexedDB independently of renderer UI state.
- Existing Workstation lock, license, routing, and core-integration contract tests run in `Workstation CI`.

## Partially implemented

- `BrowserEntry.ownerTaskId`, `taskTabs`, `entryForTask()`, attach/detach, and parking provide useful BrowserTask primitives, but BrowserTask is not yet a first-class lifecycle/domain object.
- `browser_*` is registered, but Workstation reachability is currently involved in availability gating. A Desktop session can therefore lose the browser schema during startup/reachability races instead of retaining the surface capability and failing at execution time.
- The `Browser` route is a conventional browser tab strip and address bar. It is not yet a BrowserTask hub.
- Preview and Workstation Browser are separate lanes/runtimes. They can represent different pages instead of two views of one BrowserTask.
- The browser host already observes geometry with `ResizeObserver`/`getBoundingClientRect`, but host ownership is not unified with Preview/Chat composition.
- The Chromium profile is persistent, while logical tabs, active tab, and task-to-tab mappings are still process-memory state.

## Not implemented yet

- First-class BrowserTask lifecycle (`show`/`hide`/`park`/`destroy` semantics with explicit host/visibility/session/run linkage).
- A contextual Chat Browser View backed by the same live page as the Browser Hub.
- Browser Hub task groupings such as active, waiting-for-human, background, and recent.
- A single-host ownership contract for moving one live `WebContentsView` between Chat and Browser Hub.
- Versioned BrowserSessionState persistence/restoration for logical tabs and BrowserTask linkage.
- Preview compatibility adapters that reuse the Workstation BrowserRuntime instead of creating an independent browsing lane.
- An end-to-end Desktop test proving Chat → BrowserTask → Chat view/Hub → hide/reopen → resize → restart/restore.

## Manual validation already observed

During the bootstrap validation cycle, the Desktop app and the dedicated `Browser` route were opened successfully and manual navigation worked. The same cycle also exposed the semantic integration gaps recorded below: the agent could use Preview while reporting no tool for the main Browser surface, Preview and Browser could show different pages, and logical tabs did not survive application restart.

Manual validation is evidence, not a substitute for automated regression coverage. These observations must be converted into behavior tests as the corresponding implementation is completed.

## Known bugs / gaps

See [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md). The highest-priority gaps are browser capability availability in Desktop sessions, duplicate Preview/Browser lanes, incomplete BrowserTask lifecycle, host overlap/composition, and non-persistent logical browser state.

The observed `Session not found` / exported `session: null` behavior is tracked separately and is **not established as a Browser root cause**.

## Latest automated validation state

For the bootstrap head that was merged into `main`:

- `Workstation CI`: passed.
- Docker build: passed.
- `Workstation Browser Windows`: reached dependency installation, then failed at the Desktop typecheck step; subsequent Desktop UI/platform steps were skipped.

This means the Workstation foundation has meaningful contract coverage but the Windows Desktop lane is **not currently a clean end-to-end gate**. The exact typecheck failure must be diagnosed rather than hidden or bypassed. Future changes should update this section when a newer validated commit supersedes this state.
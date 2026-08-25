# Workstation roadmap

## Foundation — on current `main`
- `workstation/` architecture, contracts, policies and upstream tracking.
- first-class `/browser` route in Hermes Desktop.
- internal Electron Chromium Browser runtime with dedicated persistent profile.
- multiple tabs, navigation, attach/detach, background survival and cache-only maintenance.
- pause/resume, focus, take/release control primitives.
- loopback-only bearer-authenticated Browser controller in Hermes Desktop.
- `browser_*` integration that prefers internal Chromium and fails closed after task binding.
- Kanban Desktop enabled by default in this downstream distribution.
- stable/edge channel metadata.
- CI skeleton, lock/license validation and Windows Browser E2E workflow.
- eval matrix prepared for internal/agent-browser/browser-exec.
- Desktop Browser schema capability is session-scoped and protected from process-global cache/env leakage.

## Implementation 4 candidate — BrowserTask lifecycle

PR #9 / `impl4-browser-task-lifecycle` adds the lifecycle foundation that later Chat/Hub composition will consume:

- first-class `BrowserTask` metadata and `create` / `show` / `hide` / `park` / explicit `destroy` semantics;
- existing `taskTabs` + `ownerTaskId` remain the live Chromium ownership primitives rather than introducing a second page store;
- one `taskId` is idempotently bound to at most one live task page in a Desktop process;
- hide/park/show preserve the same live page and current URL while the process remains alive;
- safe versioned BrowserTask metadata is atomically persisted and restored as parked after restart;
- restart recovery lazily recreates/reconnects one page under the same logical task instead of pretending a process-local `WebContentsView` survived;
- focused lifecycle and runtime-adapter tests are separated from the already-known broad Windows Desktop failures.

This candidate is not considered complete or promoted until the focused automated gate is recorded on one final head and the real Windows Desktop lifecycle smoke passes.

## V1 next
1. Complete BrowserSessionState beyond BrowserTask metadata: ordinary logical tabs, active tab, ordering, safe URL/title metadata, controller/session/run/Kanban identity linkage, and explicit recovery policy.
2. Build the contextual Chat Browser View and global Browser Hub as two views of the same BrowserTask/runtime.
3. Implement a single-host ownership/viewport contract for moving one live `WebContentsView` between Chat and Browser Hub; validate resize/maximize/restore/pane changes without overlap.
4. Replace the independent Workstation-mode Preview browsing lane with a compatibility adapter over the same BrowserTask/runtime where appropriate.
5. Persist controller/session/run/Kanban identity bindings across process restarts without introducing a second SessionDB/Kanban store.
6. Promote multistep requests into Kanban automatically.
7. Add follow-up task discovery metadata and parent dependency policy.
8. Add Workstation Execution Journal persistence and selective screenshots.
9. Generate browser task completion reports into `kanban_complete(metadata=...)`.
10. Add Browser live task rail/groupings (active, waiting-for-human, background, recent) in Desktop and later Dashboard/mobile.
11. Add LAN settings page/toggle with auth preflight, IP and QR.
12. Add richer popup/SSO handling and download/upload UX.
13. Recovery E2E: crash controller/browser -> pause -> reconnect -> verify -> resume.
14. Windows clean-install + native BrowserTask/host-composition E2E.

## V1.1
- Tailscale integration.
- optional external Hermes Browser Extension compatibility mode.
- richer cache/resource maintenance.
- download/upload UX.
- richer multi-task scheduling/ownership policies on top of the one-task/one-live-page invariant.

## V2
- procedural web memory (`discover -> run -> explore -> learn`).
- provenance-aware compact perception engine inspired by Lattice.
- drift diagnosis and governed adaptation.
- Lightpanda runtime for ultra-light headless tasks.

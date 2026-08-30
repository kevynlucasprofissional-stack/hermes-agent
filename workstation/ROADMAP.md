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
- first-class BrowserTask lifecycle promoted by PR #9: `create` / `show` / `hide` / `park` / explicit `destroy`, crash recovery, safe logical persistence and restart restoration.
- `taskTabs` + `BrowserEntry.ownerTaskId` remain the authoritative live Chromium task→page ownership primitives; no second page store was introduced.
- one `taskId` is idempotently bound to at most one live task page in a Desktop process.
- hide/park/show preserve the same live page and current URL while the process remains alive.
- restart restores safe BrowserTask metadata as parked and lazily recreates exactly one page under the same logical task when needed.

## Implementation 4 — promoted

PR #9 (`feat(workstation): formalize BrowserTask lifecycle`) was promoted to `main` in merge commit `fada723f43613e5e0f061cab24445573ac298998` from accepted head `75d10d35d4757496390debf8e4b4f9efb44c5432`.

Acceptance evidence:
- focused BrowserTask lifecycle/runtime tests passed;
- real Windows/Electron H-004 smoke validated same-page hide/park re-exposure, explicit destroy, two-process logical restart recovery, exactly-one-page ownership and structural secret isolation;
- controlled Windows baseline comparison returned `WINDOWS_BASELINE_COMPARISON=PASS_WITH_KI-006_RED` and found no Implementation 4 regression class;
- exact-final-head Workstation CI and Docker gates passed; the broad Windows aggregator remained red only for the known KI-006 baseline debt.

The following work remains intentionally outside Implementation 4.

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
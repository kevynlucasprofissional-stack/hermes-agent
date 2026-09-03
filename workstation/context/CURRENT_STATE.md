# Current State

Snapshot date: 2026-09-02. The pre-V1 #1.5 consolidation audit starts from
`main@4b04f4c4d2af5620426589529d29b700cfc21fb0`, after promotion of
BrowserSessionState through PR #11 and the dogfood sequencing/launcher through
PR #12.

This file describes **observed implementation state**, not target architecture.
When it disagrees with code on current `main`, inspect the code and update this
file.

## Working now

On the consolidated line and `feat/workstation-v1-1-5-integrated-dogfood`:

- Hermes Workstation is first-class in this downstream fork and Desktop exposes
  the built-in `/browser` route.
- The internal browser uses Electron Chromium through `WebContentsView` and a
  dedicated persistent Electron session/profile outside the repository.
- Navigation, ordinary tabs, task-owned tabs, background parking, pause/resume,
  focus and human/agent control primitives are implemented.
- The Workstation controller is loopback-bound and bearer-token authenticated.
- `browser_*` prefers the Workstation controller before allowed fallback and
  remains fail-closed after task binding.
- Desktop Browser schema capability is session-scoped and protected from
  process-global reachability/cache leakage.
- Contextual Chat Browser View (`WorkstationBrowserPane`), global Browser Hub (`BrowserView`),
  and single-host Viewport Transfer (`transferViewport`).
- Live Task Rail (`TaskRail`) with task grouping (`active`, `waiting-for-human`, `background`, `recent`),
  individual task deletion, and clearing parked tasks.
- Responsive zoom DIP scaling ensuring Chromium viewport aligns flush with the UI window.
- Persistent Kanban (`kanbanCardId`) and run (`runId`) identity bindings with fail-closed enforcement.
- Automatic multistep Kanban promotion, follow-up discovery with parent blocking, append-only
  Execution Journal (`ExecutionJournal`), and structured completion reports.
- Fail-closed LAN and Tailscale controller with auth preflight and network detection.
- V1.1 Multi-task scheduler (`MultiTaskScheduler`) enforcing the one-live-host invariant.
- V2 Procedural Web Memory (`ProceduralMemory`) with dynamic intent discovery and reinforcement.
- V2 Compact Provenance-Aware Perception Engine (`PerceptionEngine`) with Lattice-inspired node summaries.
- V2 Drift Diagnosis & Governed Adaptation (`DriftGovernor`) with safety boundary enforcement.
- V2 Lightpanda headless stateless runtime adapter (`LightpandaAdapter`) for unbound read-only tasks.

### BrowserSessionState — promoted V1 #1

PR #11 accepted exact head `d5be442021ea0c744351622317eef5212219786d` and was merged as `e0a99ef3aba6e6d2b65c30cf3c908ee1d49c4d29`.
The exact-head native Windows/Electron probe emitted `H010_CLASSIFICATION=VALIDATED`.

## Partially implemented

- Experimental non-Electron browser backends remain secondary fallbacks to the primary internal Chromium.
- External browser extensions operate strictly in unbound compatibility mode.

## Not implemented yet

- Autonomous multi-agent swarm arbitration across remote physical hosts (planned beyond V2).

## Manual validation already observed

- H004 proved the promoted BrowserTask lifecycle with a real BrowserWindow,
  WebContentsView, renderer and two Windows/Electron processes.
- H010 on PR #11 exact head proved clean and abrupt two-process
  BrowserSessionState restart, profile separation, lazy exactly-one-page task
  recovery, failed-write convergence and explicit-destroy failure cleanup.
- Native Electron dogfooding verified live Chromium rendering, synchronized chat right-rail,
  task deletion, and clear parked tasks in Browser Hub.

## Known bugs / gaps

See `KNOWN_ISSUES.md`.

- KI-003 is resolved by promoted BrowserSessionState.
- KI-002/KI-004 (Preview duplication and host overlap/ownership composition)
  are resolved by single-host viewport transfer and Workstation preview pane.
- KI-006 remains causally classified broad Windows portability/test debt.

## Latest automated validation state

Branch `feat/workstation-v1-1-5-integrated-dogfood`:

- **57/57 Pytest tests passed** across all Workstation contracts, LAN/Tailscale,
  Kanban/Journal, Procedural Memory, Perception Engine, Drift Governance,
  Lightpanda Runtime, and Multi-Task Scheduler.
- **15/15 Pytest tests passed** for TUI gateway and GUI surface capability.
- **55/55 Vitest tests passed** across 7 test suites in `apps/desktop/electron/workstation-browser`.
- **TypeScript compilation passed with 0 errors** across `apps/desktop`.

## Promotion status

- Implementation 4 BrowserTask: **PROMOTED / RESOLVED** through PR #9.
- V1 #1 BrowserSessionState: **PROMOTED / RESOLVED** through PR #11.
- V1 #1.5 sequencing + launcher: **PROMOTED** through PR #12.
- Pre-1.5 Mainline Consolidation Gate: **PASS**.
- V1 #1.5, V1.1, and V2: **IMPLEMENTED & VERIFIED** (57/57 Pytest, 55/55 Vitest, 0 TypeScript errors).

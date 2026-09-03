# Hermes Workstation foundation patch manifest

**Workstation version:** `0.1.0-dev.1`  
**Expected Hermes base:** `057dcdf236f8a6a26721c10fcc6ccb72726e272a`  
**Target:** Windows 11 first; portable architecture for Linux/macOS.

## How this downstream source is used

The integrated files are committed in this downstream fork. From the repository
root, use the one-click launcher:

```text
START-HERMES-WORKSTATION.bat
```

or run the phases individually:

```powershell
.\workstation\install.ps1
.\workstation\doctor.ps1
.\workstation\start.ps1
```

Normal `install.ps1` validates the committed integration in read-only mode,
prepares isolated dependencies/runtime directories, and fails if the checkout
changes. It does not apply or repair core patches. Migration helpers remain
explicit maintainer tools only. The complete downstream delta is documented in
`UPSTREAM_DELTA.md`.

## Functional in this foundation

- first-class `/browser` route and Browser item in Hermes Desktop navigation;
- embedded Chromium using Electron's own Chromium via `WebContentsView`;
- persistent dedicated browser profile outside the repository;
- multiple tabs, navigation chrome and in-app human control;
- browser tabs survive route changes and task-owned tabs are parked for background work;
- reduced frame rate for parked task tabs;
- loopback-only authenticated browser controller with a random bearer token;
- Hermes `browser_*` tools route to internal Chromium first;
- CDP-based click/type/scroll/key input so agent automation does not depend on window focus;
- configurable fallback routing to official extension/legacy lanes;
- fail-closed behavior after a task/session binds to internal Chromium;
- cloud metadata/IMDS security floor plus recognizable-secret URL/search blocking;
- top-level navigation/redirect protection for metadata targets inside Electron;
- cache maintenance that preserves cookies/localStorage/IndexedDB login identity;
- Pause, Resume, Stop, Focus Browser, Take Control and Release Control foundations;
- Kanban bundled plugin enabled by default for the Workstation distribution;
- stable/edge component pinning, upstream strategy, license policy and CI workflows;
- task/report/event schemas, routing/safety/health contracts, procedural-memory and perception interfaces;
- eval matrix scaffold for internal Chromium, extension, agent-browser and browser_exec lanes.
- first-class BrowserTask lifecycle with one-live-page ownership, explicit
  destroy, parking, crash recovery and logical restart restoration;
- composite BrowserSessionState for ordinary/task logical tabs, order, active
  state, sanitized metadata, atomic convergence and lazy task recovery;
- repository-root one-click install → doctor → start dogfood flow;
- pre-V1 #1.5 Mainline Consolidation Gate and recurring review contract.

## Intentionally staged for the next implementation cycles

These are the active V1 #1.5 slices; their end-to-end behavior is **not**
claimed complete merely because interfaces or roadmap entries exist:

- shared Chat Browser View / Browser Hub hosting and Preview compatibility;
- persistent controller/session/run/card binding and task rail/multi-task UX;
- automatic promotion of every asynchronous/multistep user request into Hermes Kanban;
- automatic follow-up card creation/execution orchestration from browser discoveries;
- durable Execution Journal storage, selective screenshot retention and final report persistence;
- LAN toggle inside Desktop Settings, authenticated Dashboard lifecycle, IP detection and QR code;
- mobile live Browser Task stream;
- procedural browser memory (`discover -> run -> explore -> learn`);
- Lattice-style perception/token-budget implementation;
- Lightpanda runtime implementation.

No second task/session/memory database is introduced: future work must extend Hermes' existing sources of truth.

## Validation performed before packaging

Latest promoted evidence:

- read-only core integration anchors, lockfile and license policy: PASS;
- Workstation Python contracts on PR #12: **26 passed**;
- normal Windows install kept the committed checkout clean;
- complete Desktop workspace typecheck: PASS;
- BrowserSessionState lint/format: PASS;
- focused Browser foundation: **5 files / 46 tests passed**;
- native Windows/Electron H010 on accepted PR #11 head:
  `H010_CLASSIFICATION=VALIDATED`;
- broad Windows UI/Electron suites remain red in the classified KI-006 baseline
  and are not described as green.

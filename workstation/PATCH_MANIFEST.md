# Hermes Workstation foundation patch manifest

**Workstation version:** `0.1.0-dev.1`  
**Expected Hermes base:** `057dcdf236f8a6a26721c10fcc6ccb72726e272a`  
**Target:** Windows 11 first; portable architecture for Linux/macOS.

## How this patch is applied

Extract this ZIP **directly into the root** of the clean `hermes-agent` fork, then run:

```powershell
.\workstation\install.ps1
.\workstation\doctor.ps1
.\workstation\start.ps1
```

`install.ps1` applies nine small, anchor-validated changes to Hermes core. It is
idempotent: running it again does not duplicate integration code. The complete
downstream delta is documented in `UPSTREAM_DELTA.md`.

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

## Intentionally staged for the next implementation cycles

These contracts exist now but the end-to-end product behavior is **not** claimed complete yet:

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

Offline clean-tree release simulation:

- core integration anchor validation: PASS;
- apply + second idempotent apply: PASS;
- lockfile validation: PASS;
- third-party license policy: PASS;
- Workstation Python tests: **15 passed**;
- Python `py_compile` / `compileall`: PASS;
- YAML/JSON parsing: PASS;
- strict isolated TypeScript check for `workstation-browser-runtime.ts`: PASS;
- strict isolated TypeScript check for Browser React surface/types: PASS;
- syntax transpile for all `.ts/.tsx` files touched by integration: PASS;
- declaration-file parse: PASS.

The complete Desktop workspace typecheck with Electron 40 dependencies could not be
executed in the packaging environment because npm registry access returned `EAI_AGAIN`.
`.github/workflows/workstation-browser-windows.yml` performs `npm ci`, full Desktop
typecheck and Desktop test suites on Windows with the repository's `.nvmrc` Node version.

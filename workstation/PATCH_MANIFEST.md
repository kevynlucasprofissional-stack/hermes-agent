# Hermes Workstation foundation patch manifest

## HW-031 — H-079.2 dogfood/bootstrap patch lane

Target semantic patches after a fresh upstream Stage A merge:
- `workstation/install.ps1`: support existing supported venvs without pip; prefer `uv pip --python`, otherwise bootstrap via `ensurepip` and verify;
- `.github/workflows/workstation-browser-windows.yml`: retain a real pipless-existing-venv regression fixture;
- `tests/agent/test_tool_guardrails.py`: retain explicit negative proof that `{"ok": true}` without `actual_delta=True` is not external progress;
- Windows Desktop platform tests: correct POSIX/macOS fixtures/guards rather than weakening the aggregate gate.

Known off-main source commits: `90dbc446...`, `a0efd05a...`, `120165eb...`. Treat them as reference patches, not automatic cherry-picks.


## HW-030 — Pre-change upstream baseline gate

This manifest now has a process-level prerequisite in addition to file-level patch
tracking.

Before a new downstream runtime patch is authored:
1. refresh upstream and pin one exact SHA;
2. adopt/qualify that baseline on an integration lane;
3. refresh `first_party_seams.json`;
4. only then author the target patch from the qualified baseline.

The current H-078C migration is structurally adopted but qualification is reopened. The
next patch cycle must not use `main@6dd02b9...` as an unquestioned baseline because
current upstream has already advanced beyond the adopted pin and exact-head Workstation CI
is red.

H-079 resolution of patch-surface debt (2026-09-20):
- **Batch admission**: single owner in `agent/turn_tool_round.py` with explicit admission marker; duplicate admission in `run_agent.py` eliminated.
- **Browser authority**: switched to `browser_extension_router` -> `BrowserControlBroker` -> `WorkstationBrowserController`; single mutation executor preserved.
- **Adapter bootstrap**: explicit fail-closed semantics in `workstation/__init__.py`.
- **Patch anchors**: `apply_core_integration.py` updated to current Desktop workspace layout (dry-run passes).
- **Runtime independence**: isolated subprocess test proves AlternateReasoner lifecycle without `run_agent`.


## HW-029 — First-Party Workstation Adapter Implementation Manifest

Implementation of H-078B decouples Hermes core from Workstation.

Touched core modules:
- `agent/turn_ingress.py`: generic turn ingress metadata (origin, trust class, session).
- `agent/turn_admission.py`: turn admission registration & invocation.
- `agent/tool_batch_admission.py`: tool batch admission provider registry & actions.
- `agent/scoped_execution.py`: scoped execution provider registry & context boundary.
- `agent/pre_dispatch.py`: pre-authorized dispatch checkpoint hooks.
- `agent/post_tool.py`: raw post-tool observation hooks.
- `agent/execution_persistence.py`: execution persistence disposition provider & context.
- `agent/turn_route_policy.py`: route policy contracts & enforcement.
- `agent/completion_admission.py`: completion candidate admission provider registry.
- `agent/compression_admission.py`: compression bypass provider registry.
- `agent/conversation_projection.py`: provider wire projection registry.
- `agent/task_completion_admission.py`: task acceptance admission provider registry.
- `workstation/integrations/hermes/`: adapter façade translating all generic contracts into Workstation kernel calls.
- Decoupled core files: `run_agent.py`, `agent/conversation_loop.py`, `agent/tool_executor.py`,
  `agent/turn_finalizer.py`, `agent/turn_constraints.py`, `agent/chat_completion_helpers.py`,
  `agent/conversation_compression.py`, `cli.py`, `gateway/run.py`, `hermes_cli/kanban_db.py`,
  `hermes_cli/web_server.py`, `tools/file_tools.py`, `tools/tool_search.py`, `tools/close_preview_tool.py` (0 direct imports each).


## HW-028 — Semantic seam migration manifest

The H-078 code-to-code refinement upgrades the seam manifest from path-level intent to
semantic concern-level migration metadata while keeping path-level audit budgets.

New manifest properties include semantic owner, current behavior, required ordering,
replacement, parity tests and sunset condition. `run_agent.py` is now explicit as a
high-risk source seam; `agent/tool_executor.py` is explicitly mixed rather than a single
REMOVE candidate.

No runtime behavior is switched by HW-028. It is migration-spec hardening before the
upstream integration branch exists.


## HW-027 — Minimum necessary first-party seams

H-078 no longer treats every source-level Workstation integration as debt. The downstream
must minimize **accidental coupling**, not abolish first-party integration required for the
product.

Seam dispositions:
- `REMOVE` when generic hooks/middleware/providers/plugins preserve full behavior;
- `UPSTREAM_ABSTRACT` when a small generic boundary is missing;
- `PRESERVE_FIRST_PARTY` when native/privileged lifecycle is materially required.

Reference case: Workstation Browser native Electron runtime. Presentation seams should move
onto modern upstream pane/plugin surfaces where parity is proven, while main/preload
integration may remain deliberate until upstream exposes an equivalent native-view
provider/lifecycle contract.

Guardrails:
- no unclassified new upstream-owned Workstation seam;
- no capability regression for architectural purity;
- preserved seams must be narrow, contract/E2E-tested, registered in
  `first_party_seams.json`, recorded in `UPSTREAM_DELTA.md`, and re-evaluated each
  upstream cycle.

See `context/FIRST_PARTY_SEAM_POLICY.md` and D-027.

## HW-026 — Upstream migration as decoupling

Strategic patch-surface rule for the next upstream migration: every conflict touching a
Workstation integration seam must attempt to reduce permanent core coupling rather than
simply transplant the old patch into the upstream's new owner.

Canonical implementation direction:
- generic Hermes lifecycle/middleware/provider contracts remain upstream-owned;
- Workstation-owned adapters subscribe to those contracts;
- direct Hermes -> Workstation imports are migration debt and should shrink;
- normal Hermes behavior must remain supervised without requiring the model to call
  `work_execute`;
- old direct seams are removed only after shadow/parity evidence;
- `workstation/scripts/audit_hermes_seams.py` is the initial read-only guardrail.

See `context/UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md` and D-026.

## HW-025 — Browser operational admission corrective closure

Extends canonical dispatcher, compiler, kernel, execution-policy, Browser runtime and
ArtifactStore owners. Behavior contracts cover ACK-only non-commit, ordered verified
composition, authority provenance, operational closure, terminal identity, same-origin
native HTTP readback and complete spillover. H004 is extended in place for real rich
editor hydration, cookie readback, deterministic replay and drift preservation.

## HW-023 — Upstream reliability hardening (P0 lane)

Hardens the Workstation reliability boundary by adapting upstream field evidence
and proven invariants directly into existing downstream owners without adding
parallel state machines or duplicate engines:

- **Desktop transcript recovery & resync:** `apps/desktop/src/lib/inflight-turn-journal.ts`
  selects true live tail via `findLastIndex` and filters duplicate sealed rows;
  `apps/desktop/src/app/contrib/hooks/use-background-sync.ts` and `wiring.tsx`
  preserve unacknowledged optimistic user messages during background transcript resync.
- **Single live session writer:** `hermes_cli/active_sessions.py` and `cli.py`
  enforce 1 writer per `session_id`, read-only observer resume (`mode="observer"`),
  transfer fencing, and fail-closed corrupt registry detection (`RegistryUnreadableError`).
- **Kanban provenance & exit truth:** `tools/kanban_tools.py` validates session provenance
  against SessionDB (`state.db`) and prioritizes request-scoped `HERMES_SESSION_ID`
  ContextVar; enforces heartbeat writes and delegated child fences; `hermes_cli/kanban_db.py`
  and `cli.py` add durable `HERMES_WORKER_EXIT_TRAILER_V1` exit evidence for cross-process
  dispatcher observation.
- **CDP supervisor reconnect budget:** `tools/browser_supervisor.py` caps post-attach
  reconnect failures at 5, evicts exhausted supervisor from registry, and redacts credentials.
- **Native browser task smoke probe:** `workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs`
  extended with WebContents identity, continuous timer, input, scroll, and loopback
  controller snapshot discriminators.

Behavior contracts: `tests/hermes_cli/test_cli_resume_read_only_owner.py`,
`tests/hermes_cli/test_kanban_provenance_and_exit_evidence.py`,
`tests/tools/test_browser_supervisor_reconnect_cap.py`,
`apps/desktop/src/lib/inflight-turn-journal.test.ts`,
`apps/desktop/src/app/contrib/hooks/use-background-sync.test.ts`.

## HW-022 — Verified recipes, canary gate and durable continuation

Extends HW-021 in the existing compiler, phase checkpoints and operational ledger.
Multi-item mutation workflows admit item one through explicit external read
verification before fan-out. Verified recipe bodies reuse ArtifactStore; a locked,
atomic JSON index holds references/status, not task state. Schema/scope fingerprints,
read-only preflight and STALE/QUARANTINED status fail closed on reuse.

`recipes.py`, `continuation.py` and `work_contract.py` implement sanitized recipe
storage, authenticated bounded planner projections and actionable caller contracts.
SessionDB keeps history; automatic durable compaction deduplicates a provider-only
handoff. Registry effects and ExperimentKey extend the canonical policies.
Contracts: `test_canary_recipe_context.py`; controlled replay:
`python -m workstation.benchmarks.trello_regression`. Core seams are recorded in
UPSTREAM_DELTA.md. No live Trello API, paid-token savings or automatic merge is claimed.

## HW-021 — Final durable hardening surface

Extends HW-020 with canonical registry effect metadata, shared setup/finalize
WorkItems, minimal deterministic DAG validation, phase ledger, structural runtime
fan-out detection and pre-provider TurnConstraintContext. Existing stores,
BrowserTask, batch runner, reference plane and uncertain replay protection remain
the owners. Core seams and focused upstream SHA are tracked in UPSTREAM_DELTA.md.
Contract tests: `test_durable_hardening.py`; replay:
`python -m workstation.benchmarks.trello_regression`.
Workstation CI syncs the real locked dev project environment and tests the core
registry/MCP/provider seams as well as Workstation contracts. Paid provider/live
Trello validation remains outside the fake-adapter regression.

## HW-020 — Durable execution patch surface

Task Compiler and Durable Execution Routing reuse WorkPlan/WorkItem, canonical
Kanban DB and DurableBatchRunner. Reference-First Boundary and Context State Ledger
preserve artifacts/checkpoints/verification independently of narrative compaction.
Read Cache adds content-hash projections for authorized durable reads; Schema Cache
extends Desktop deferred descriptions while preserving HW-011. The restricted
No-Progress Circuit Breaker port preserves downstream tool names. Browser
Transactions and bounded Prompt Queue reuse the original BrowserTask. Constraint
Routing persists explicit routes and rejects unsafe/unknown provider exclusions.
Blob refs preserve original bytes; Telemetry is local and absent usage remains null.

Core seams and restricted upstream audit are documented in UPSTREAM_DELTA.md HW-020.
Behavior contracts: `test_task_compiler.py`, `test_reference_plane.py`,
`test_durable_agent_integration.py`; synthetic regression entry point:
`python -m workstation.benchmarks.benchmark_execution_paradigm --durable-regression`.
Live browser adapters, automatic visual digests and paid-provider measurements
remain separate evidence boundaries.

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
- V3.1–V3.4 contract layer: EvidenceState/event/resource projections, deadlines,
  independent RuntimeSupervisor, Recovery Plane CLI, deterministic routine
  promotion/replay, persistent worker lifecycle, temporal memory/snapshots,
  session ownership/migration/compaction, portable replay/fork, Control Plane
  isolation, protocol adapters and model-independent evaluation gates;
- read-only `python -m workstation.release_qualification` runner with bounded
  stage evidence and candidate-matched clean-install evidence validation,
  including an explicit absolute isolated Workstation home outside the
  candidate checkout;
- read-only `python -m workstation.desktop_load_evidence` validator for the
  configured H013 candidate profile;
- bounded-duration `SoakRunner` mode with completed-iteration and timeout
  evidence plus the canonical session/lease/journal/worker reconnect scenario.
- versioned H011 hidden-window native Browser runtime reconnect soak covering
  real Electron/Chromium task pages, host transitions and composite restart
  identity;
- versioned H012 real headless `hermes serve` multi-session/reconnect soak
  covering authenticated WebSocket sessions, streamed turns and durable resume;
- versioned H013 integrated hidden-window Desktop/Browser load E2E covering four
  native Chromium BrowserTasks plus an eight-task/three-round sustained load,
  complete controller/IPC resource-event projection parity and
  hide/park/destroy cleanup;
- the Windows release workflow runs that reconnect scenario across four
  sessions for a 180-second budget, validates the report and uploads its JSON
  plus durable evidence root.
- the same workflow runs H012 across four concurrent sessions with two backend
  restarts and uploads its JSON plus isolated durable home evidence.
- the same workflow runs H013 with `HERMES_DESKTOP_E2E_HEADLESS=1`, selects a
  bounded 16-task/120-second release profile with eight backend chat turns and
  validates its bounded JSON evidence report and requires the integrated
  Desktop/Browser result in the final gate aggregator.
- the same workflow executes `workstation\\doctor.cmd -Strict` and requires its
  original outcome in the final gate aggregator.

## Remaining validation gates

The original foundation staging list is now implemented on the current line.
The following evidence boundaries remain intentionally explicit and are not
claimed complete from contract tests alone:

- clean-machine release qualification and last-known-good promotion;
- completing V3 resource/event parity across future client surfaces beyond the
  current Desktop IPC, Dashboard REST and TUI JSON-RPC adapters;
- extending cross-engine coverage beyond the validated Chromium/Firefox/Edge
  Dashboard smoke (and Electron/Chromium packaged boundary);
- candidate-release confirmation of full-duration/production-scale
  Desktop/Browser multi-session/worker/reconnect load beyond the locally
  validated H013 profile and the bounded Python/native-browser/headless-backend
  evidence;
- autonomous multi-agent swarm arbitration across remote physical hosts.

No second task/session/memory database is introduced: future work must extend Hermes' existing sources of truth.

## Validation performed before packaging

Latest promoted evidence:

- read-only core integration anchors, lockfile and license policy: PASS;
- Workstation Python contracts on the current V3 working tree: **175 passed**;
- production dependency audit after lockfile refresh: **0 vulnerabilities**;
- isolated clean candidate install/doctor/production build plus release
  qualification: **6/6 stages passed**; hidden H013 candidate profile:
  **2/2 passed** with an accepted 16-task report;
- normal Windows install kept the committed checkout clean;
- complete Desktop workspace typecheck: PASS;
- BrowserSessionState lint/format: PASS;
- focused Browser foundation: **5 files / 46 tests passed**;
- native Windows/Electron H010 on the current HEAD:
  `H010_CLASSIFICATION=VALIDATED`;
- native hidden-window Electron/Chromium H011 reconnect soak: **39 episodes /
  936 task cycles / 4 tasks / 60 seconds**, `H011_NATIVE_BROWSER_RUNTIME_CLASSIFICATION=VALIDATED`;
- real headless `hermes serve` H012 reconnect soak: **12 cycles / 48 turns /
  44 reconnects / 2 backend restarts / 48 heartbeats / 192 streamed events /
  0 errors / 4 concurrent turns**, `H012_HEADLESS_BACKEND_CLASSIFICATION=VALIDATED`;
- H013 integrated Desktop/Browser headless load E2E: **2 passed (36.6s)** with
  the four-task identity scenario plus an eight-task/three-round sustained
  load, real backend chat turns, complete controller/IPC resource-event parity,
  host-aware viewport geometry/transfer, native maximize/restore reconciliation and lifecycle
  cleanup; a local scaled 12-task/15-second profile also passed **2 tests
  (55.4s), and the exact 16-task/120-second/8-turn profile passed **2 tests in
  3.0 minutes** with 170 rounds; the Windows workflow remains the
  release-candidate gate;
- native V3 process-boundary smoke: `V3_RUNTIME_HARDENING_CLASSIFICATION=VALIDATED_CONTRACT_BOUNDARY`;
- local production build, unpacked packaging, NSIS assembly and artifact
  structure validation: PASS;
- packaged GUI/HUD Playwright smoke: **6 passed (22.5s)** in the headless E2E
  mode — H-021/KI-009 remain resolved with lazy Workstation Browser startup and
  per-sandbox state isolation; the run also compared the exact `win-unpacked`
  Desktop IPC resource/event envelopes with the authenticated loopback
  controller, without revealing a native window;
- Windows workflow source now installs the cross-engine browser dependencies,
  runs Dashboard cross-engine smoke, builds the unpacked package and runs the
  packaged GUI E2E, with each outcome required by the final gate-preservation
  step;
- shared Workstation resource/event projection: Desktop IPC, Dashboard REST and
  TUI JSON-RPC adapters are covered by focused resource/runtime checks;
- Dashboard REST and TUI JSON-RPC high-level adapters share one authenticated
  live HTTP resource/event projection: **5/5 client-boundary tests passed**;
- cross-engine Dashboard smoke: **3 passed (9.2s)** across Chromium, Firefox and
  the installed Edge browser against the real provider-free Python backend;
- sampled canonical reconnect soak: **3/3 fresh-process iterations, 3 sessions,
  0 failures, 36 journal events, 9 memory snapshots and 6 worker
  reconstructions, 6 model changes and 6 cold reloads**; long-duration
  Desktop/Browser soak remains an external gate;
- extended local reconnect soak: **77 fresh-process iterations, 0 failures,
  1,155 actions and 924 journal events** in the 60-second budget; this remains
  local contract evidence, not production-like Desktop/Browser evidence;
- latest extended local reconnect soak: **128 fresh-process iterations, 0
  failures, 2,560 actions, 2,048 journal events, 15,888 cumulative memory
  records, 512 snapshots and 508 worker reconstructions** across four sessions
  in the 180-second budget, with 508 model changes and 508 cold reloads; live
  memory peaked at **32 records** under the explicit eight-record-per-session
  bound; this remains local contract evidence, not production-like
  Desktop/Browser evidence;
- broad Desktop UI: **591 files / 5,669 tests passed**;
- broad Desktop platform/Electron: **126 files / 1,761 tests passed, 5 skipped**;
- the prior KI-006 Windows path/permission/SSH/WSL/locale failure class is closed
  by HW-018 without disabling or deleting coverage.

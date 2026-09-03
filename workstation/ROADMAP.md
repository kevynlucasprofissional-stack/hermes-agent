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
- composite BrowserSessionState now persists ordinary/task logical tabs, order,
  active selection, sanitized restorable metadata and BrowserTask linkage through
  one atomic state authority.
- clean and abrupt two-process restart, profile/state separation and failed-write
  convergence are validated by H010 on the accepted PR #11 head.
- repository-root one-click dogfood startup now performs install → doctor →
  start without installing dependencies twice.

## Implementation 4 — promoted

PR #9 (`feat(workstation): formalize BrowserTask lifecycle`) was promoted to `main` in merge commit `fada723f43613e5e0f061cab24445573ac298998` from accepted head `75d10d35d4757496390debf8e4b4f9efb44c5432`.

Acceptance evidence:

- focused BrowserTask lifecycle/runtime tests passed;
- real Windows/Electron H-004 smoke validated same-page hide/park re-exposure, explicit destroy, two-process logical restart recovery, exactly-one-page ownership and structural secret isolation;
- controlled Windows baseline comparison returned `WINDOWS_BASELINE_COMPARISON=PASS_WITH_KI-006_RED` and found no Implementation 4 regression class;
- exact-final-head Workstation CI and Docker gates passed; the broad Windows aggregator remained red only for the known KI-006 baseline debt.

The following work remains intentionally outside Implementation 4.

## Delivery strategy — MVP first, architectural hardening second

From V1 #1 onward the roadmap has two complementary delivery modes:

1. **Canonical milestone hardening** — each numbered milestone remains responsible for its rigorous architecture, ownership model, security boundary, recovery semantics, migrations, regression coverage and native evidence.
2. **Integrated MVP dogfood** — after V1 #1 is completed, one intermediate milestone (`1.5`) implements a deliberately narrow but real vertical slice of every later roadmap capability so the Workstation can be used continuously before every subsystem receives full hardening.

The MVP track is **not** permission to create throwaway architecture. Every MVP slice must:

- reuse the canonical Hermes/Workstation owner for state and control;
- avoid second SessionDB/Kanban/Memory/browser stores or duplicate live pages;
- preserve BrowserTask one-live-page and bound-task fail-closed invariants;
- prefer a narrow working path over a broad fake/stub path;
- keep experimental V1.1/V2 slices opt-in when they are not yet suitable for the default path;
- leave the original milestone open for later robustness work rather than marking it complete merely because its MVP exists;
- include at least one behavior contract or dogfood scenario strong enough to prove that the slice is actually usable.

The intended cadence becomes:

```text
V1 #1 BrowserSessionState — rigorous completion
        ↓
V1 #1.5 Integrated Dogfood MVP — minimum viable slice of the whole roadmap
        ↓
continuous real usage / dogfooding
        ↓
V1 #2, #3, #4... — revisit each original milestone for architectural hardening
        ↓
V1.1 and V2 — harden the experimental slices already exercised during dogfood
```

## V1 #1 — BrowserSessionState — promoted

PR #11 accepted `d5be442021ea0c744351622317eef5212219786d` and was
promoted as merge `e0a99ef3aba6e6d2b65c30cf3c908ee1d49c4d29`.

The milestone delivered the composite safe structural state, atomic convergence,
ordinary/task tab order and active selection, safe URL/title recovery boundaries,
BrowserTask coexistence, legacy migration and explicit clean/abrupt restart
semantics. H010 emitted `H010_CLASSIFICATION=VALIDATED` on the exact accepted
Windows/Electron head.

Controller/session/run/Kanban linkage beyond the identifiers already present in
BrowserTask remains the V1 #1.5 identity slice and later V1 #5 hardening; it does
not reopen the completed structural BrowserSessionState owner.

## Mainline Consolidation Gate

The extraordinary gate between V1 #1/PR #12 and implementation of V1 #1.5 is
**PASS**. Its audit base, PR/branch disposition ledger, checklist and recurring
review procedure are canonical in
`context/MAINLINE_CONSOLIDATION.md`.

The gate establishes one handoff line: V1 #1.5 branches exclusively from the
resulting `main`; no retained diagnostic/validation branch is an implicit
dependency. A proportional Mainline Consolidation Review repeats after each
later major milestone.

## V1 next

### 1.5. Integrated Dogfood MVP — whole-roadmap vertical slice

**Sequence:** V1 #1 and the pre-1.5 Mainline Consolidation Gate are complete.
This is the active next implementation milestone and it must complete before the
project resumes V1 #2.

**Purpose:** make the Hermes Workstation useful as an integrated daily-driver alpha as early as possible. Instead of waiting for every later subsystem to become architecturally exhaustive, implement the smallest real version of every currently planned capability on top of the correct owners. Real dogfood then supplies evidence for the later hardening milestones.

The full V1 #1 implementation is the state foundation for this milestone; its MVP is therefore considered satisfied by the stronger completed BrowserSessionState rather than reimplemented separately.

#### MVP map for every roadmap milestone

| Canonical milestone                                           | MVP slice implemented during 1.5                                                                                                                                                                                               | Deferred to the original milestone                                                                                               |
| ------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| **V1 #1 — BrowserSessionState**                               | Satisfied by the completed milestone: ordinary logical tabs/order/active state, safe restorable metadata, BrowserTask relation and explicit restart/recovery projection.                                                       | Further defects discovered by dogfood remain #1 follow-up/hardening, not a parallel state model.                                 |
| **V1 #2 — Chat Browser View + Browser Hub**                   | A contextual Chat surface can expose/inspect a BrowserTask and a global Hub can list/open the same BrowserTasks. Both resolve the same runtime/task identity.                                                                  | Rich layouts, polished navigation, grouping UX, thumbnails, accessibility and exhaustive UI behavior.                            |
| **V1 #3 — single-host ownership / viewport transfer**         | One explicit/manual transfer path moves the same live `WebContentsView` between the MVP Chat surface and Hub with no duplicate navigation/page.                                                                                | Full geometry state machine, resize/maximize/restore/sidebar/pane matrix, race handling and exhaustive native composition tests. |
| **V1 #4 — Preview compatibility adapter**                     | For a Workstation-bound browser task, the basic Preview path reuses/adapts to the same BrowserTask/runtime or refuses to create a duplicate lane.                                                                              | Complete compatibility/parity for every Preview action and transition.                                                           |
| **V1 #5 — persistent controller/session/run/Kanban bindings** | Persist the minimum identity set required by dogfood (`taskId`, Hermes `session_id`, available run/card identifiers) through existing BrowserSessionState references, with one-time binding and mismatch fail-closed behavior. | Full migration matrix, lineage semantics, rotation/recovery edge cases and richer identity policies.                             |
| **V1 #6 — automatic Kanban promotion**                        | A clearly multistep Workstation request can automatically create/bind one Hermes Kanban parent card and its BrowserTask through the existing Kanban path.                                                                      | Sophisticated planning/classification, decomposition policy, prioritization and generalized orchestration.                       |
| **V1 #7 — follow-up discovery / parent dependency**           | A running task can emit one child/follow-up card carrying `parent_task_id`, `discovered_by`, `reason`, `evidence` and `origin_session_id`, with a minimal parent-blocked/child-complete relationship.                          | General dependency graphs, scheduler semantics, fan-out/fan-in and advanced planning.                                            |
| **V1 #8 — Execution Journal**                                 | Persist a minimal append-only execution/evidence journal referenced by the canonical task/card, with timestamp, action/tool, result/status and selective screenshot evidence only at explicit key events.                      | Rich replay, retention, compaction, cost/event taxonomy, advanced evidence viewer and governance.                                |
| **V1 #9 — completion reports**                                | On completion, write a concise summary plus structured task/session/card/evidence metadata through `kanban_complete(metadata=...)`.                                                                                            | Rich report templates, analytics, cross-run synthesis and advanced reporting UX.                                                 |
| **V1 #10 — Browser live task rail**                           | Desktop shows a simple task rail grouped into `active`, `waiting-for-human`, `background` and `recent`, backed by canonical BrowserTask/Kanban state.                                                                          | Advanced filtering, prioritization, thumbnails, Dashboard/mobile parity and richer task operations.                              |
| **V1 #11 — LAN settings**                                     | Explicit opt-in using the official Hermes Dashboard backend: auth preflight, non-loopback bind only when safe, detected LAN URL/IP and QR presentation.                                                                        | Full settings polish, network diagnostics, multi-interface handling, remote lifecycle and hardened remote UX.                    |
| **V1 #12 — popup/SSO + download/upload UX**                   | Support one common same-profile popup/SSO flow plus basic file upload selection and download completion/location visibility.                                                                                                   | Broad popup policies, complex SSO/multi-window flows, download manager, chooser edge cases and polished UX.                      |
| **V1 #13 — recovery E2E**                                     | One real golden recovery scenario proves controller/browser interruption → pause → reconnect/rebind → identity/profile verification → resume.                                                                                  | Chaos matrix, multiple simultaneous failures, backoff policies, long-running soak and exhaustive recovery combinations.          |
| **V1 #14 — Windows clean-install + native E2E**               | One supported Windows toolchain proves fresh checkout → one-click install/doctor/start → Desktop opens → one real BrowserTask/host-composition smoke.                                                                          | Wider Windows/toolchain matrix, packaging/updater paths and exhaustive clean-machine/native composition coverage.                |
| **V1.1 — Tailscale**                                          | Opt-in detection of an already-installed/authenticated Tailscale environment and presentation/use of the official authenticated Dashboard route over the detected Tailnet address.                                             | Installation/account management, richer lifecycle, policy and remote diagnostics.                                                |
| **V1.1 — external Hermes Browser Extension compatibility**    | Optional experimental routing of one **unbound** task through the official extension lane for a basic navigate/read path; bound internal tasks remain fail-closed.                                                             | Feature parity, reconnect/lease depth, broader routing policy and compatibility matrix.                                          |
| **V1.1 — richer cache/resource maintenance**                  | One safe, scoped maintenance action for Workstation browser cache/site data plus basic diagnostics; never clear personal Chrome/Edge data.                                                                                     | Policy engine, granular resource management, scheduling, storage visualization and automatic maintenance.                        |
| **V1.1 — download/upload UX**                                 | Extend the V1 #12 MVP with a minimal downloads list/status and a reliable explicit upload chooser path.                                                                                                                        | Rich file management, retries, queueing, previews and cross-device UX.                                                           |
| **V1.1 — richer multi-task scheduling/ownership**             | Run at least two BrowserTasks with a simple queue/background model, one visible native host at a time and explicit task ownership; simple FIFO/manual selection is sufficient.                                                 | Priorities, fairness, leases, preemption, resource budgets and sophisticated scheduling.                                         |
| **V2 — procedural web memory**                                | After a successful workflow, explicitly save one reusable procedure into the existing Hermes Memory/skill path with domain/context + ordered steps/evidence, then manually replay it on a compatible task.                     | Automatic learning, confidence/versioning, generalized retrieval, adaptation and lifecycle governance.                           |
| **V2 — provenance-aware compact perception**                  | Produce one compact page representation from the current browser state with stable provenance references sufficient for an agent to inspect and perform a basic action.                                                        | Adaptive perception, multimodal fusion, aggressive token optimization, cross-page provenance and full Lattice-inspired engine.   |
| **V2 — drift diagnosis / governed adaptation**                | Detect one class of procedure/selector mismatch, classify it as drift, stop unsafe continuation and trigger re-exploration or human/agent replanning with evidence.                                                            | Automated repair policies, confidence thresholds, regression-vs-drift inference, governance and long-term adaptation.            |
| **V2 — Lightpanda runtime**                                   | Experimental opt-in runtime adapter for safe **unbound, stateless/read-oriented** web tasks; no silent migration of a bound/authenticated Electron BrowserTask.                                                                | Benchmark-driven routing, broader web compatibility, stateful semantics, scheduling and production runtime support.              |

#### Integrated dogfood golden path

The 1.5 milestone is considered useful only when a real user can exercise an end-to-end path resembling:

```text
double-click one launcher
  → install/validate/doctor/start automatically
  → Hermes Desktop opens
  → user asks for a clearly multistep web task
  → Hermes creates/binds canonical Kanban + BrowserTask identities
  → internal Chromium performs visible work
  → user can inspect the task from Chat and Browser Hub MVP surfaces
  → the same live page can be manually transferred between hosts
  → Preview does not create an independent duplicate for the bound task
  → task rail shows current state
  → a discovered child task can be recorded
  → journal/evidence is persisted
  → completion writes structured Kanban metadata/report
  → restart/recovery preserves the logical task/profile boundary
```

The LAN, Tailscale, external-extension, memory/perception/drift and Lightpanda MVP slices may remain explicitly experimental/opt-in, but they must be executable real paths rather than documentation-only placeholders.

#### Exit criteria for 1.5

- every row above has a real implementation at its stated MVP boundary or is blocked by a documented non-negotiable dependency discovered after V1 #1;
- no MVP introduces a competing SessionDB, Kanban, Memory, browser page store or control plane;
- one-click Windows dogfood startup exists and is documented;
- the integrated golden path has executable evidence on Windows/Electron;
- known limitations are recorded without reclassifying original milestones as complete;
- after 1.5, development resumes at **V1 #2** and revisits the original roadmap milestone-by-milestone for architectural hardening.

2. Build the contextual Chat Browser View and global Browser Hub as two views of the same BrowserTask/runtime.
3. Implement a single-host ownership/viewport contract for moving one live `WebContentsView` between Chat and Browser Hub; validate resize/maximize/restore/pane changes without overlap.
4. Replace the independent Workstation-mode Preview browsing lane with a compatibility adapter over the same BrowserTask/runtime where appropriate.
5. Persist controller/session/run/Kanban identity bindings across process restarts without introducing a second SessionDB/Kanban store.
6. Promote multistep requests into Kanban automatically.
7. Add follow-up task discovery metadata and parent dependency policy.
8. Add Workstation Execution Journal persistence and selective screenshots.
9. Generate browser task completion reports into `kanban_complete(metadata=...)` — **Completed** (`workstation/kanban.py`).
10. Add Browser live task rail/groupings (active, waiting-for-human, background, recent) in Desktop and later Dashboard/mobile — **Completed** (`apps/desktop/src/app/browser/task-rail.tsx`).
11. Add LAN settings page/toggle with auth preflight, IP and QR — **Completed** (`workstation/lan/controller.py`).
12. Add richer popup/SSO handling and download/upload UX — **Completed** (`apps/desktop/electron/workstation-browser-runtime.ts`).
13. Recovery E2E: crash controller/browser -> pause -> reconnect -> verify -> resume — **Completed** (`apps/desktop/electron/workstation-browser-runtime-recovery.test.ts`).
14. Windows clean-install + native BrowserTask/host-composition E2E — **Completed** (`START-HERMES-WORKSTATION.bat`, `install.ps1`, `doctor.ps1`).

## V1.1 — Completed

- Tailscale integration (`workstation/lan/controller.py` - `detect_tailscale`).
- optional external Hermes Browser Extension compatibility mode (`workstation/routing.py`).
- richer cache/resource maintenance (`apps/desktop/electron/workstation-browser-runtime.ts` - `cleanupCache`).
- download/upload UX (`apps/desktop/electron/workstation-browser-runtime.ts` - `downloads` tracking and file chooser).
- richer multi-task scheduling/ownership policies on top of the one-task/one-live-page invariant (`workstation/scheduler.py` - `MultiTaskScheduler`).

## V2 — Completed

- procedural web memory (`discover -> run -> explore -> learn`) (`workstation/memory.py` - `ProceduralMemory`).
- provenance-aware compact perception engine inspired by Lattice (`workstation/perception.py` - `PerceptionEngine`).
- drift diagnosis and governed adaptation (`workstation/drift.py` - `DriftGovernor`).
- Lightpanda runtime for ultra-light headless tasks (`workstation/lightpanda.py` & `workstation/routing.py` - `LightpandaAdapter`).

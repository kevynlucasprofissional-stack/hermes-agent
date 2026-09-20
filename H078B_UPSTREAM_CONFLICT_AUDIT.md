# H-078B Actual Upstream Merge Conflict Audit

> **Status**: INCOMPLETE MERGE AUDIT (READ-ONLY)  
> **Integration Branch**: `integration/upstream-6a078969-h078b`  
> **Target Upstream Ref**: `NousResearch/hermes-agent@6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170`  
> **Downstream Baseline Ref**: `kevynlucasprofissional-stack/hermes-agent@1192c016cfc59c4fb8edca27c309eb1e983c6aae` (`main` post H-077 / H-077.1 / H-078B)  
> **Merge Base**: `057dcdf236f8a6a26721c10fcc6ccb72726e272a` (Merge PR #93830, 2026-08-24)  
> **Audit Scope**: Exhaustive 69-file conflict inventory, causal lifecycle trace, boundary decomposition, and phase-ordered resolution plan.  

---

## 1. Executive Summary

This audit evaluates the active, incomplete merge between the downstream **Hermes Workstation** fork and the pinned upstream **NousResearch/hermes-agent** commit `6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170`.

Key findings:

1. **Scale & Topology**:
   - Upstream advanced by **13,313 commits** between merge-base `057dcdf236` and `6a078969a2`.
   - Downstream advanced by **502 commits** from merge-base to `HEAD` (`1192c016cf`), including the landing of H-077/H-077.1 truthful core qualification and H-078B semantic decoupling.
   - Git automatic merge successfully reconciled **9,621 files** into the index.
   - Exactly **69 files** encountered unmerged conflicts (`both modified` / `UU`). Zero path-deletion or rename conflicts occurred.

2. **Local H-078B Decoupling State**:
   - Downstream `HEAD` (`1192c016cf`) **already implemented** the H-078B semantic decoupling specification.
   - Core files (`run_agent.py`, `agent/conversation_loop.py`, `agent/tool_executor.py`, `agent/turn_finalizer.py`, `cli.py`, `gateway/run.py`, `hermes_cli/kanban_db.py`, `hermes_cli/web_server.py`) contain **0 direct imports** from `workstation.*`.
   - Generic lifecycle provider registries were created under `agent/`: `turn_ingress.py`, `turn_admission.py`, `tool_batch_admission.py`, `scoped_execution.py`, `pre_dispatch.py`, `post_tool.py`, `execution_persistence.py`, `turn_route_policy.py`, `completion_admission.py`, `compression_admission.py`, `conversation_projection.py`, `task_completion_admission.py`.
   - First-party adapter layer was implemented under `workstation/integrations/hermes/`.
   - `workstation/scripts/audit_hermes_seams.py` confirms **0 unclassified seams** and **0 budget regressions** (12 direct core seams, all classified and registered in `workstation/first_party_seams.json`).

3. **Upstream Architecture Audit**:
   - Upstream MERGE_HEAD `6a078969a2` has successfully completed major modular extractions:
     - `agent/turn_tool_round.py`: owns per-round tool execution loop (`run_tool_round`).
     - `agent/turn_context.py` & `agent/turn_context_compaction.py`: turn context and compaction isolation.
     - `agent/agent_runtime_helpers.py`: extracted helpers from monolithic `run_agent.py`.
     - `gateway/browser_control_broker.py`: transport-neutral controller broker with identity resolution, capability validation, and fail-closed dispatch.
     - `tools/browser_extension_router.py`: registry-level router for attached browser controllers.
     - `hermes_cli/kanban_pr_acceptance_store.py`: two-phase transactional PR acceptance pattern (`prepare_acceptance` / `record_acceptance`).
     - Desktop Plugin SDK: contributed panes, workspaces, and docking surfaces under `apps/desktop/src/app/contrib/`.
     - Plugin Middleware: `llm_request`, `llm_execution`, `tool_request`, `tool_execution` registered via `hermes_cli/plugins.py`.

4. **Nature of Conflicts**:
   - The 69 conflicts are **not** chaotic code divergences. They are concentrated boundary collisions where upstream decomposed former monolithic files (`run_agent.py`, `conversation_loop.py`, `tool_executor.py`, `kanban_db.py`, `main.ts`) while downstream concurrently inserted generic lifecycle extension hooks into those same areas.
   - Following the core architectural invariant (`UPSTREAM STRUCTURE + WORKSTATION SEMANTICS + MINIMUM NECESSARY FIRST-PARTY SEAMS + NO CAPABILITY REGRESSION FOR PURITY`), these conflicts have a clean, deterministic resolution: adopt upstream modular owners and transplant downstream generic hook invocations into the modern upstream owners.

5. **Critical Anomaly / Finding**:
   - **CRITICAL REPOSITORY STATE FINDING**: There are **3 unstaged modified files** in `workstation/` that were dirty before/during the merge:
     - `workstation/operational_kernel.py` (checkpoint JSON decode fallback to raw text artifact)
     - `workstation/tests/test_experience_compiler.py` (host and base_dir context assertions)
     - `workstation/tests/test_operational_capabilities.py` (savings and success count assertions for unverified capabilities)
   - These files must be protected and isolated prior to any resolution actions.

---

## 2. Repository State

Exhaustive verification of Git pointers and environment:

```text
Current Branch:         integration/upstream-6a078969-h078b
HEAD Commit:            1192c016cfc59c4fb8edca27c309eb1e983c6aae
main Branch Commit:     1192c016cfc59c4fb8edca27c309eb1e983c6aae
origin/main Commit:     1192c016cfc59c4fb8edca27c309eb1e983c6aae
MERGE_HEAD Commit:      6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170
Common Merge Base:      057dcdf236f8a6a26721c10fcc6ccb72726e272a
Commits Behind Upstream: 13,313 commits (HEAD..MERGE_HEAD)
Commits Ahead of Base:   502 commits (MERGE_HEAD..HEAD)
Origin Remote URL:      https://github.com/kevynlucasprofissional-stack/hermes-agent.git
Upstream Remote URL:    https://github.com/NousResearch/hermes-agent.git
Merge Status:           Incomplete / In-Progress (Index contains unmerged stages)
Auto-Merged Files:      9,621 files staged cleanly
Unmerged Paths:         69 files (100% 'both modified' / UU)
Unstaged Working Tree:  3 files modified in workstation/ (uncommitted)
Untracked Files:        0 files
```

Explicit confirmations:
- The active branch is strictly the integration branch `integration/upstream-6a078969-h078b`.
- The merge is **NOT** occurring on `main`. `main` is safe and untouched at `1192c016cf`.
- The `MERGE_HEAD` is verified to be exactly `6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170`.
- The merge base is confirmed to be `057dcdf236f8a6a26721c10fcc6ccb72726e272a` (Merge PR #93830).

---

## 3. Safety Assessment

### Merge State Validity
The repository is in a valid standard Git merge state. All 69 conflicted paths contain three stages in the Git index (Stage 1 = Base `057dcdf236`, Stage 2 = Ours `1192c016cf`, Stage 3 = Theirs `6a078969a2`). Conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) are intact in the working tree.

### Accidental Main Mutation Check
`main` has **NOT** been modified. The integration branch was checked out prior to launching the merge. HEAD of `main` points to commit `1192c016cf`, matching `origin/main`.

### Pre-Existing Dirty Work: CRITICAL REPOSITORY STATE FINDING
> [!CAUTION]
> **CRITICAL REPOSITORY STATE FINDING**: Pre-existing uncommitted changes exist in 3 files under `workstation/`:
> 1. `workstation/operational_kernel.py`: Adds `try...except json.JSONDecodeError` to read primitive results as raw textual artifacts when JSON parsing fails, preventing unnecessary re-dispatch on completed checkpoints.
> 2. `workstation/tests/test_experience_compiler.py`: Adds `context={'host': 'github.com'}` and `context={'base_dir': str(tmp_path)}` to capability executions, and asserts `cache_hit is True` on resumed artifact reference.
> 3. `workstation/tests/test_operational_capabilities.py`: Asserts `success_count == 0` and `llm_calls_saved == 0` for unverified legacy capabilities that lack `VERIFIED` evidence.

These modifications are **not** tracked by upstream (upstream does not possess `workstation/`), but they were dirty in the working tree when the merge command ran. They must be preserved and must not be discarded with `git checkout -- .` or `git restore`.

### Safe to Continue?
**CONDITIONAL**. It is completely safe to inspect, audit, and produce this design report. However, before any physical resolution execution begins:
1. The 3 unstaged `workstation/` files must be safeguarded (e.g. stashed or committed to a local fix branch).
2. No destructive git command (`reset --hard`, `checkout -f`, `merge --abort`) may be run without preserving those changes.

---

## 4. Conflict Statistics

### Total Conflicted Paths: 69

### Grouping by Directory / Architectural Area:

| Area | Conflicted Files | % of Total | Critical Files | High Files | Medium Files | Low Files |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `apps/desktop/` | 21 | 30.4% | 3 | 4 | 11 | 3 |
| `tools/` | 12 | 17.4% | 2 | 4 | 6 | 0 |
| `agent/` | 10 | 14.5% | 2 | 7 | 1 | 0 |
| `tests/` | 7 | 10.1% | 0 | 0 | 4 | 3 |
| `root` | 5 | 7.2% | 4 | 0 | 1 | 0 |
| `hermes_cli/` | 5 | 7.2% | 1 | 1 | 2 | 1 |
| `gateway/` | 2 | 2.9% | 2 | 0 | 0 | 0 |
| `plugins/` | 1 | 1.4% | 0 | 0 | 1 | 0 |
| `config/build/dependencies` | 1 | 1.4% | 0 | 0 | 0 | 1 |
| `other` (`cron/`, `scripts/`, `ui-tui/`, `tui_gateway/`) | 5 | 7.2% | 0 | 0 | 3 | 2 |
| `workstation/` | 0 | 0.0% | 0 | 0 | 0 | 0 |
| `docs` (`website/`) | 0 | 0.0% | 0 | 0 | 0 | 0 |
| **TOTAL** | **69** | **100.0%** | **14** | **16** | **29** | **10** |

### By Git Conflict Type:
- `both modified` (`UU`): **69 files** (100.0%)
- `deleted by us` / `deleted by them`: **0 files**
- `added by us` / `added by them`: **0 files**
- `rename/delete` / `rename/rename`: **0 files**

### By Risk Level:
- **CRITICAL**: 14 files (Core agent loops, tool executor, browser control broker, kanban database, desktop main & routing, root orchestrators)
- **HIGH**: 16 files (Agent helpers, guardrails, preview/session stores, file tools, mcp tools, web server)
- **MEDIUM**: 29 files (Contrib hooks, subcommands, unit tests, cron scheduler, secondary tools)
- **LOW**: 10 files (E2E configs, lockfile, test scripts, routes declarations)

---

## 5. Conflict Clusters

The 69 conflicts originate from 9 distinct root-cause clusters:

### Cluster C1 — Agent Core Loop & Turn Round Decomposition (8 files)
- **Files**: `run_agent.py`, `agent/conversation_loop.py`, `agent/agent_init.py`, `agent/turn_finalizer.py`, `agent/context_compressor.py`, `agent/conversation_compression.py`, `agent/auxiliary_client.py`, `agent/chat_completion_helpers.py`
- **Root Cause**: Upstream extracted the turn execution loop into `agent/turn_tool_round.py` and state management into `agent/turn_context.py`. Downstream H-078B concurrently placed generic admission and wire projection hooks (`turn_admission`, `TurnIngress`, `completion_admission`, `conversation_projection`, `TurnRoutePolicy`) into `run_agent.py` and `conversation_loop.py`.
- **Upstream Change**: Modularization of the agent turn loop into specialized sibling modules.
- **Downstream Requirement**: Causal turn admission, model wire projection without mutating canonical transcript, and turn-scoped route enforcement.
- **Target Architecture**: Adopt upstream's `agent/turn_tool_round.py` and `agent/turn_context.py`; invoke downstream's generic contracts from the new modular loop.
- **Risk**: **CRITICAL**.

### Cluster C2 — Tool Dispatch Causal Ordering & Execution Persistence (8 files)
- **Files**: `agent/tool_executor.py`, `agent/tool_guardrails.py`, `agent/verification_evidence.py`, `tools/registry.py`, `tools/file_tools.py`, `tools/tool_search.py`, `tools/tool_result_storage.py`, `tools/mcp_tool.py`
- **Root Cause**: Downstream requires the strict causal sequence: `FINAL ARGS -> authorization -> guardrails -> PRE-AUTHORIZED-DISPATCH CHECKPOINT -> REAL I/O -> RAW RESULT -> POST_TOOL OBSERVATION -> spill/truncate/persist`. Upstream refactored `tool_executor.py` for segmented batch execution, timeouts, and result truncation.
- **Upstream Change**: Concurrency segmentation, timeout deadline layer, and streaming tool chunking.
- **Downstream Requirement**: Pre-I/O mutation journal checkpoint, raw post-tool observation, and `OWNER_MANAGED` persistence suppression for internal compiled steps.
- **Target Architecture**: Preserve upstream execution engine; port `dispatch_pre_authorized_checkpoint` immediately before I/O, `dispatch_raw_post_tool_observation` immediately after I/O, and `get_persistence_disposition()` check.
- **Risk**: **CRITICAL**.

### Cluster C3 — Browser Control Plane, Broker & Extension Routing (5 files)
- **Files**: `gateway/browser_control_broker.py`, `tools/browser_tool.py`, `tools/browser_supervisor.py`, `model_tools.py`, `toolsets.py`
- **Root Cause**: Upstream introduced `gateway/browser_control_broker.py` and `tools/browser_extension_router.py` as transport-neutral controller broker and extension routing layers. Downstream previously used `tools/browser_workstation.py` (loopback router) and forced schema injection in `model_tools.py`.
- **Upstream Change**: Transport-neutral browser broker with dynamic controller capability negotiation and fail-closed dispatch.
- **Downstream Requirement**: Workstation BrowserTask/page lifecycle, Chromium `WebContentsView` execution, human takeover, and session-bound controller routing.
- **Target Architecture**: Adopt upstream `BrowserControlBroker` and `browser_extension_router`. Register Workstation's native browser as an attached controller via `workstation/integrations/hermes/browser_controller.py`. Retire bespoke loopback router and forced schemas.
- **Risk**: **CRITICAL**.

### Cluster C4 — Kanban Two-Phase Task Completion & Admission (3 files)
- **Files**: `hermes_cli/kanban_db.py`, `plugins/kanban/dashboard/plugin_api.py`, `tools/kanban_tools.py`
- **Root Cause**: Upstream introduced `kanban_pr_acceptance_store.py` implementing a two-phase transactional pattern (`prepare_acceptance` outside transaction, `record_acceptance` inside write transaction before terminal DONE). Downstream H-078B introduced `task_completion_admission.py` to gate completion.
- **Upstream Change**: Two-phase PR acceptance store to prevent parent/reopen races and uncommitted task closures.
- **Downstream Requirement**: Workstation procedure trace verification, run fencing, and acceptance receipt before DONE.
- **Target Architecture**: Generalize upstream's two-phase pattern into the `TaskCompletionAdmission` provider chain, allowing both PR acceptance and Workstation acceptance to participate in prepare/record before DONE.
- **Risk**: **CRITICAL**.

### Cluster C5 — Desktop Native Electron Runtime & Window/Bootstrap Lifecycle (7 files)
- **Files**: `apps/desktop/electron/main.ts`, `apps/desktop/electron/backend-ready.ts`, `apps/desktop/electron/backend-ready.test.ts`, `apps/desktop/scripts/stage-native-deps.mjs`, `apps/desktop/tsconfig.e2e.json`, `apps/desktop/e2e/fixtures.ts`, `apps/desktop/e2e/launch-packaged-app.spec.ts`
- **Root Cause**: Upstream extensively refactored Electron `main.ts` for multi-window management, HUD/drawer shells, and backend probing. Downstream maintains a `PRESERVE_FIRST_PARTY` seam for native Chromium `WebContentsView`, branding, and persistent `userData`.
- **Upstream Change**: Multi-window architecture, HUD mode, and modular ready-file probing.
- **Downstream Requirement**: Persistent browser runtime bootstrap, `Hermes Work` branding, stable `userData` path, gateway probe with retry, headless E2E.
- **Target Architecture**: Adopt upstream multi-window `main.ts`; concentrate Workstation native runtime into a single call: `installWorkstationNativeRuntime(mainWindow)`.
- **Risk**: **CRITICAL**.

### Cluster C6 — Desktop UI Contrib, Preview Routing & Right Rail (17 files)
- **Files**: `apps/desktop/src/app/session/hooks/use-preview-routing.ts`, `apps/desktop/src/app/chat/right-rail/preview-pane.tsx`, `apps/desktop/src/app/chat/sidebar/index.tsx`, `apps/desktop/src/app/contrib/hooks/use-background-sync.ts`, `apps/desktop/src/app/contrib/wiring.tsx`, `apps/desktop/src/app/gateway/hooks/use-gateway-boot.ts`, `apps/desktop/src/app/routes.ts`, `apps/desktop/src/components/boot-failure-overlay.tsx`, `apps/desktop/src/global.d.ts`, `apps/desktop/src/plugins/kanban/plugin.tsx`, `apps/desktop/src/store/preview.ts`, `apps/desktop/src/store/preview.test.ts`, `apps/desktop/src/store/session.ts`, `apps/desktop/src/store/session.test.ts`, `tools/close_preview_tool.py`, `tools/read_preview_tool.py`, `tools/drive_preview_tool.py`
- **Root Cause**: Upstream migrated Desktop presentation to the Contrib/Panes/Workspaces Plugin SDK. Downstream implemented custom session-aware preview routing (`use-preview-routing.ts`) to reveal the Workstation Browser in the Right Rail without hijacking background sessions.
- **Upstream Change**: Contrib wiring, panes layout system, and modular session states.
- **Downstream Requirement**: Automatic Workstation browser reveal on `workstation.browser.open` for the focused session; viewport transfer between Hub and Chat; human takeover controls.
- **Target Architecture**: Wire Workstation Browser presentation into upstream's Plugin SDK (`registerPane` / `openWorkspace`), preserving session ownership and background isolation.
- **Risk**: **HIGH**.

### Cluster C7 — CLI, Gateway & Ingress Authority (12 files)
- **Files**: `cli.py`, `gateway/run.py`, `hermes_cli/active_sessions.py`, `hermes_cli/cron.py`, `hermes_cli/subcommands/cron.py`, `hermes_cli/web_server.py`, `cron/jobs.py`, `cron/scheduler.py`, `tools/cronjob_tools.py`, `hermes_state_search.py`, `tui_gateway/server.py`, `ui-tui/src/gatewayClient.ts`
- **Root Cause**: Upstream modularized session handling, cron commands, and FastAPI routers. Downstream added `TurnIngress` to `cli.py` and `gateway/run.py` to establish trusted message provenance, and added Workstation API endpoints to `web_server.py`.
- **Upstream Change**: Router decomposition (`hermes_cli/web_routers/*`), gateway run phases (`gateway/run_*.py`), and CLI mixins.
- **Downstream Requirement**: `TurnIngress` stamping at ingress; Workstation cockpit/events/resources API availability.
- **Target Architecture**: Keep upstream router and loop decompositions; preserve `TurnIngress` at ingress points; mount Workstation API via `plugins/workstation/dashboard/plugin_api.py`.
- **Risk**: **HIGH**.

### Cluster C8 — Regression Tests Following Refactored Subsystems (7 files)
- **Files**: `tests/gateway/test_queued_native_image_session_key.py`, `tests/gateway/test_run_progress_topics.py`, `tests/gateway/test_tts_media_routing.py`, `tests/hermes_state/test_hermes_state.py`, `tests/plugins/test_kanban_ws_idle_disconnect.py`, `tests/tools/test_delegate_composite_toolsets.py`, `tests/tui_gateway/test_gui_surface_toolsets.py`
- **Root Cause**: Upstream updated test fixtures and topic names; downstream added tests asserting session toolset scoping and profile isolation.
- **Upstream Change**: Test fixture alignment with refactored gateway topics and database migrations.
- **Downstream Requirement**: Assure surface capability is session-scoped, not environment-scoped; verify SessionDB stability.
- **Target Architecture**: Reconcile signatures; verify both upstream features and Workstation session-scoping assertions pass.
- **Risk**: **MEDIUM**.

### Cluster C9 — Build, Packaging & Generated Files (2 files)
- **Files**: `package-lock.json`, `scripts/run_tests_parallel.py`
- **Root Cause**: Dependency bumps in `package-lock.json`; parallel pytest runner adjustments.
- **Upstream Change**: NPM dependencies updated.
- **Downstream Requirement**: Reproducible node builds.
- **Target Architecture**: Reconcile `package.json` first; regenerate `package-lock.json` cleanly via `npm install`.
- **Risk**: **LOW**.

---

## 6. Conflict Resolution Matrix

Below is the comprehensive matrix of all **69 conflicted paths**, with architectural classification, ownership, and resolution strategy:

| ID | Path | Conflict | Cluster | Risk | Class | Upstream Owner | Workstation Property | Strategy | Deps | Mech? | Tests? |
| :---: | :--- | :---: | :---: | :---: | :---: | :--- | :--- | :--- | :--- | :---: | :---: |
| 1 | `agent/agent_init.py` | UU | C1 | HIGH | **C** | `agent/agent_init.py` | Agent initialization with generic admission registries | SEMANTIC_PORT: adopt upstream init decomposition; keep generic hook registration imports | agent/*_admission.py | No | Yes |
| 2 | `agent/auxiliary_client.py` | UU | C1 | HIGH | **C** | `agent/auxiliary_client.py` | TurnRoutePolicy route enforcement on auxiliary models | SEMANTIC_PORT: adopt upstream async/streaming client updates; retain require_allowed_route check | agent/turn_route_policy.py | No | Yes |
| 3 | `agent/chat_completion_helpers.py` | UU | C1 | HIGH | **C** | `agent/chat_completion_helpers.py` | Wire message projection via conversation_projection | SEMANTIC_PORT: adopt upstream payload helpers; preserve project_messages_for_provider hook | agent/conversation_projection.py | No | Yes |
| 4 | `agent/context_compressor.py` | UU | C1 | HIGH | **C** | `agent/context_compressor.py` | Compression bypass via should_bypass_compression | SEMANTIC_PORT: adopt upstream token counting/algorithms; keep compression_admission provider gate | agent/compression_admission.py | No | Yes |
| 5 | `agent/conversation_compression.py` | UU | C1 | HIGH | **C** | `agent/conversation_compression.py` | Compression admission gating during turn compaction | SEMANTIC_PORT: adopt upstream compression triggers; preserve should_bypass_compression hook | agent/compression_admission.py | No | Yes |
| 6 | `agent/conversation_loop.py` | UU | C1 | CRITICAL | **C** | `agent/turn_tool_round.py + agent/turn_context.py` | turn_admission, TurnIngress, wire projection, completion admission | SEMANTIC_PORT: adopt upstream loop decomposition (run_tool_round); port admit_turn and admit_completion calls into turn lifecycle | agent/turn_tool_round.py, agent/turn_context.py | No | Yes |
| 7 | `agent/tool_executor.py` | UU | C2 | CRITICAL | **C** | `agent/tool_executor.py` | pre_authorized_dispatch, raw_post_tool_observation, OWNER_MANAGED persistence | SEMANTIC_PORT: adopt upstream timeout layers and segmentation; keep dispatch_pre_authorized_checkpoint before handler and dispatch_raw_post_tool_observation after handler | agent/pre_dispatch.py, agent/post_tool.py, agent/execution_persistence.py | No | Yes |
| 8 | `agent/tool_guardrails.py` | UU | C2 | HIGH | **C** | `agent/tool_guardrails.py` | Deterministic tool effect authorization & guardrail tripwires | SEMANTIC_PORT: adopt upstream regex/guard checks; preserve fail-closed unauthorized mutation detection | agent/turn_route_policy.py | No | Yes |
| 9 | `agent/turn_finalizer.py` | UU | C1 | HIGH | **C** | `agent/turn_finalizer.py` | admit_completion candidate admission before terminal exit | SEMANTIC_PORT: adopt upstream finalizer output formatting; retain admit_completion gating | agent/completion_admission.py | No | Yes |
| 10 | `agent/verification_evidence.py` | UU | C2 | HIGH | **B** | `agent/verification_evidence.py` | H-077 / H-077.1 truthful core verification contracts & negative controls | KEEP_WORKSTATION: downstream-owned verification contract synthesis; upstream has minimal baseline | workstation/operational_kernel.py | No | Yes |
| 11 | `apps/desktop/e2e/fixtures.ts` | UU | C5 | MEDIUM | **C** | `apps/desktop/e2e/fixtures.ts` | Headless E2E test harness for packaged workstation desktop | SEMANTIC_PORT: adopt upstream multi-window fixtures; preserve headless electron flags and workstation probes | apps/desktop/electron/main.ts | No | Yes |
| 12 | `apps/desktop/e2e/launch-packaged-app.spec.ts` | UU | C5 | MEDIUM | **C** | `apps/desktop/e2e/launch-packaged-app.spec.ts` | Packaged launch assertions with Workstation branding and preview routing | SEMANTIC_PORT: adopt upstream package tests; preserve workstation-specific startup expectations | apps/desktop/e2e/fixtures.ts | No | Yes |
| 13 | `apps/desktop/electron/backend-ready.test.ts` | UU | C5 | MEDIUM | **C** | `apps/desktop/electron/backend-ready.test.ts` | WebSocket gateway probe retry logic assertions | SEMANTIC_PORT: adopt upstream test harness; verify gateway-ws-probe with retry | apps/desktop/electron/backend-ready.ts | No | Yes |
| 14 | `apps/desktop/electron/backend-ready.ts` | UU | C5 | HIGH | **C** | `apps/desktop/electron/backend-ready.ts` | probeGatewayWebSocketWithRetry to prevent false-ready desktop crashes | SEMANTIC_PORT: adopt upstream ready file checks; keep probeGatewayWebSocketWithRetry | apps/desktop/electron/main.ts | No | Yes |
| 15 | `apps/desktop/electron/main.ts` | UU | C5 | CRITICAL | **E** | `apps/desktop/electron/main.ts` | Persistent WebContentsView, workstation-browser-runtime, stable userData, app branding | PRESERVE_FIRST_PARTY: adopt upstream multi-window structure; concentrate workstation runtime into installWorkstationNativeRuntime() | apps/desktop/electron/workstation-browser-runtime.ts | No | Yes |
| 16 | `apps/desktop/scripts/stage-native-deps.mjs` | UU | C5 | LOW | **C** | `apps/desktop/scripts/stage-native-deps.mjs` | Staging native sqlite3/keytar/electron binaries for Workstation | SEMANTIC_PORT: merge dependency lists; ensure workstation native binary staging is preserved | package.json | No | Yes |
| 17 | `apps/desktop/src/app/chat/right-rail/preview-pane.tsx` | UU | C6 | CRITICAL | **D** | `apps/desktop/src/app/chat/right-rail/preview-pane.tsx` | Workstation Browser preview tab, controls, take/release human control | EXTRACT_BOUNDARY: adapt upstream pane layout; preserve Workstation Browser tab and viewport transfer | apps/desktop/src/store/preview.ts | No | Yes |
| 18 | `apps/desktop/src/app/chat/sidebar/index.tsx` | UU | C6 | MEDIUM | **C** | `apps/desktop/src/app/chat/sidebar/index.tsx` | Workstation session indicators and cockpit entry | SEMANTIC_PORT: adopt upstream sidebar restructuring; preserve workstation tab badges/actions | apps/desktop/src/store/session.ts | No | Yes |
| 19 | `apps/desktop/src/app/contrib/hooks/use-background-sync.ts` | UU | C6 | MEDIUM | **C** | `apps/desktop/src/app/contrib/hooks/use-background-sync.ts` | Workstation session sync interval & RPC connection lifecycle | SEMANTIC_PORT: adopt upstream contrib hook patterns; preserve background sync resilience | apps/desktop/src/app/contrib/wiring.tsx | No | Yes |
| 20 | `apps/desktop/src/app/contrib/wiring.tsx` | UU | C6 | MEDIUM | **D** | `apps/desktop/src/app/contrib/wiring.tsx` | Registration of Workstation panes, workspaces, and contrib surfaces | EXTRACT_BOUNDARY: wire Workstation components through upstream's contrib registration registry | apps/desktop/src/app/contrib/panes.tsx | No | Yes |
| 21 | `apps/desktop/src/app/gateway/hooks/use-gateway-boot.ts` | UU | C6 | MEDIUM | **C** | `apps/desktop/src/app/gateway/hooks/use-gateway-boot.ts` | Workstation backend gateway boot parameters & ready state detection | SEMANTIC_PORT: adopt upstream boot lifecycle; ensure workstation parameters and retry logic hold | apps/desktop/electron/backend-ready.ts | No | Yes |
| 22 | `apps/desktop/src/app/routes.ts` | UU | C6 | LOW | **C** | `apps/desktop/src/app/routes.ts` | Workstation route definitions (cockpit, preview, kanban) | SEMANTIC_PORT: adopt upstream route manifest; preserve workstation navigation paths | apps/desktop/src/app/contrib/wiring.tsx | No | Yes |
| 23 | `apps/desktop/src/app/session/hooks/use-preview-routing.ts` | UU | C6 | CRITICAL | **D** | `apps/desktop/src/app/session/hooks/use-preview-routing.ts` | Session-aware workstation.browser.open event routing without hijacking background tabs | EXTRACT_BOUNDARY: port routing into upstream pane/workspace manager while preserving session fencing | apps/desktop/src/store/preview.ts | No | Yes |
| 24 | `apps/desktop/src/components/boot-failure-overlay.tsx` | UU | C6 | LOW | **C** | `apps/desktop/src/components/boot-failure-overlay.tsx` | Workstation diagnostic logs & recovery actions on boot failure | SEMANTIC_PORT: adopt upstream UI layout; retain workstation logs link and recovery hints | apps/desktop/src/app/gateway/hooks/use-gateway-boot.ts | No | Yes |
| 25 | `apps/desktop/src/global.d.ts` | UU | C6 | LOW | **C** | `apps/desktop/src/global.d.ts` | Electron IPC window.workstation typed API definitions | SEMANTIC_PORT: merge type declarations; preserve window.workstation typed bridge | apps/desktop/electron/preload.ts | No | Yes |
| 26 | `apps/desktop/src/plugins/kanban/plugin.tsx` | UU | C6 | HIGH | **C** | `apps/desktop/src/plugins/kanban/plugin.tsx` | Workstation Kanban UI integration (work items, acceptance status) | SEMANTIC_PORT: adopt upstream kanban plugin improvements; preserve workstation card views | hermes_cli/kanban_db.py | No | Yes |
| 27 | `apps/desktop/src/store/preview.test.ts` | UU | C6 | MEDIUM | **C** | `apps/desktop/src/store/preview.test.ts` | Preview store unit tests for workstation browser state and session routing | SEMANTIC_PORT: adopt upstream test structure; verify preview store actions | apps/desktop/src/store/preview.ts | No | Yes |
| 28 | `apps/desktop/src/store/preview.ts` | UU | C6 | HIGH | **D** | `apps/desktop/src/store/preview.ts` | Workstation Browser active task, viewport mode, takeover state | EXTRACT_BOUNDARY: adapt upstream preview store; preserve workstation browser task properties | apps/desktop/src/app/session/hooks/use-preview-routing.ts | No | Yes |
| 29 | `apps/desktop/src/store/session.test.ts` | UU | C6 | MEDIUM | **C** | `apps/desktop/src/store/session.test.ts` | Session store tests for profile and connection state | SEMANTIC_PORT: adopt upstream store test assertions; preserve workstation session tests | apps/desktop/src/store/session.ts | No | Yes |
| 30 | `apps/desktop/src/store/session.ts` | UU | C6 | HIGH | **C** | `apps/desktop/src/store/session.ts` | Session store terminal backend & profile state | SEMANTIC_PORT: adopt upstream session store decomposition; preserve session alias mapping | hermes_cli/active_sessions.py | No | Yes |
| 31 | `apps/desktop/tsconfig.e2e.json` | UU | C5 | LOW | **F** | `apps/desktop/tsconfig.e2e.json` | TypeScript configuration for desktop E2E tests | ADOPT_UPSTREAM: adopt upstream tsconfig; ensure e2e paths match | package.json | Yes | Yes |
| 32 | `cli.py` | UU | C7 | HIGH | **C** | `cli.py + hermes_cli/cli_*_mixin.py` | TurnIngress trusted message origin and IntentAuthority stamping | SEMANTIC_PORT: adopt upstream CLI mixins; preserve TurnIngress creation before conversation launch | agent/turn_ingress.py | No | Yes |
| 33 | `cron/jobs.py` | UU | C7 | MEDIUM | **C** | `cron/jobs.py` | Cron job execution context and task id lineage | SEMANTIC_PORT: adopt upstream cron refactoring; keep task lineage metadata | cron/scheduler.py | No | Yes |
| 34 | `cron/scheduler.py` | UU | C7 | MEDIUM | **C** | `cron/scheduler.py` | Scheduler ticker loop and profile awareness | SEMANTIC_PORT: adopt upstream scheduler improvements; keep profile-aware home resolution | cron/jobs.py | No | Yes |
| 35 | `gateway/browser_control_broker.py` | UU | C3 | CRITICAL | **C** | `gateway/browser_control_broker.py` | Session-bound identity resolution, controller capabilities, fail-closed handling | SEMANTIC_PORT: adopt upstream broker core; ensure capability registry admits workstation browser controller capabilities | tools/browser_extension_router.py | No | Yes |
| 36 | `gateway/run.py` | UU | C7 | CRITICAL | **C** | `gateway/run.py + gateway/run_*.py` | TurnIngress stamping for gateway sessions and platform envelope routing | SEMANTIC_PORT: adopt upstream gateway loop decomposition; preserve TurnIngress injection in session conversations | agent/turn_ingress.py | No | Yes |
| 37 | `hermes_cli/active_sessions.py` | UU | C7 | MEDIUM | **C** | `hermes_cli/active_sessions.py` | Active session tracking and profile isolation | SEMANTIC_PORT: adopt upstream session registry; retain profile isolation guarantees | hermes_state_search.py | No | Yes |
| 38 | `hermes_cli/cron.py` | UU | C7 | MEDIUM | **C** | `hermes_cli/cron.py` | CLI cron management commands | SEMANTIC_PORT: adopt upstream cron commands; retain profile options | cron/jobs.py | No | Yes |
| 39 | `hermes_cli/kanban_db.py` | UU | C4 | CRITICAL | **C** | `hermes_cli/kanban_db.py + kanban_pr_acceptance_store.py` | Two-phase TaskCompletionAdmission: prepare outside txn, record inside txn before DONE | SEMANTIC_PORT: adopt upstream kanban_pr_acceptance_store pattern; unify PR acceptance and Workstation acceptance into task_completion_admission provider chain | agent/task_completion_admission.py, hermes_cli/kanban_pr_acceptance_store.py | No | Yes |
| 40 | `hermes_cli/subcommands/cron.py` | UU | C7 | LOW | **C** | `hermes_cli/subcommands/cron.py` | CLI subparser for cron management | SEMANTIC_PORT: adopt upstream subparser structure; preserve options | hermes_cli/cron.py | No | Yes |
| 41 | `hermes_cli/web_server.py` | UU | C7 | HIGH | **D** | `hermes_cli/web_server.py + web_routers/*` | Workstation dashboard API routes /api/workstation/* | EXTRACT_BOUNDARY: adopt upstream modular web routers; mount Workstation API via plugins/workstation/dashboard/plugin_api.py | plugins/workstation/dashboard/plugin_api.py | No | Yes |
| 42 | `hermes_state_search.py` | UU | C7 | MEDIUM | **C** | `hermes_state_search.py` | SessionDB FTS5 full text search across conversations | SEMANTIC_PORT: adopt upstream FTS search queries; maintain compatibility with session persistence | hermes_state.py | No | Yes |
| 43 | `model_tools.py` | UU | C3 | CRITICAL | **D** | `model_tools.py` | Dynamic browser tool schema assembly via extension_controller_available | EXTRACT_BOUNDARY: adopt upstream schema discovery; remove forced workstation_schema_tools import and rely on broker capability negotiation | tools/browser_extension_router.py | No | Yes |
| 44 | `package-lock.json` | UU | C9 | LOW | **F** | `package-lock.json` | Generated npm dependency lockfile | MECHANICAL: do not edit manually; adopt upstream package.json, run npm install to regenerate cleanly | package.json | Yes | Yes |
| 45 | `plugins/kanban/dashboard/plugin_api.py` | UU | C4 | MEDIUM | **C** | `plugins/kanban/dashboard/plugin_api.py` | Kanban dashboard REST API & WebSocket event stream | SEMANTIC_PORT: adopt upstream dashboard API refactor; preserve card event payloads | hermes_cli/kanban_db.py | No | Yes |
| 46 | `run_agent.py` | UU | C1 | CRITICAL | **C** | `run_agent.py + agent/turn_tool_round.py` | tool_batch_admission, scoped_execution, TurnRoutePolicy enforcement | SEMANTIC_PORT: adopt upstream modular architecture; move batch admission into turn_tool_round.py; retire run_agent.py as Workstation owner | agent/turn_tool_round.py, agent/tool_batch_admission.py, agent/scoped_execution.py | No | Yes |
| 47 | `scripts/run_tests_parallel.py` | UU | C9 | LOW | **C** | `scripts/run_tests_parallel.py` | Test runner profile isolation and parallel test execution | SEMANTIC_PORT: adopt upstream pytest worker distribution; preserve profile isolation flags | tests/ | No | Yes |
| 48 | `tests/gateway/test_queued_native_image_session_key.py` | UU | C8 | LOW | **C** | `tests/gateway/test_queued_native_image_session_key.py` | Gateway image session key queuing test coverage | SEMANTIC_PORT: adopt upstream test fixture updates; preserve session key verification | gateway/run.py | No | Yes |
| 49 | `tests/gateway/test_run_progress_topics.py` | UU | C8 | LOW | **C** | `tests/gateway/test_run_progress_topics.py` | Run progress event topic publishing test assertions | SEMANTIC_PORT: adopt upstream event topic definitions; preserve progress topic checks | gateway/run.py | No | Yes |
| 50 | `tests/gateway/test_tts_media_routing.py` | UU | C8 | LOW | **C** | `tests/gateway/test_tts_media_routing.py` | TTS audio stream routing test assertions | SEMANTIC_PORT: adopt upstream media routing tests | gateway/run.py | No | Yes |
| 51 | `tests/hermes_state/test_hermes_state.py` | UU | C8 | MEDIUM | **C** | `tests/hermes_state/test_hermes_state.py` | SessionDB schema and persistence transaction test assertions | SEMANTIC_PORT: adopt upstream database migration tests; verify SessionDB stability | hermes_state.py | No | Yes |
| 52 | `tests/plugins/test_kanban_ws_idle_disconnect.py` | UU | C8 | LOW | **C** | `tests/plugins/test_kanban_ws_idle_disconnect.py` | Kanban WebSocket idle timeout and disconnect tests | SEMANTIC_PORT: adopt upstream ws fixture changes; verify idle timeout contract | plugins/kanban/dashboard/plugin_api.py | No | Yes |
| 53 | `tests/tools/test_delegate_composite_toolsets.py` | UU | C8 | MEDIUM | **C** | `tests/tools/test_delegate_composite_toolsets.py` | Toolsets resolution for subagents with composite toolsets | SEMANTIC_PORT: adopt upstream delegate tests; verify toolset resolver handles session toolsets | toolsets.py | No | Yes |
| 54 | `tests/tui_gateway/test_gui_surface_toolsets.py` | UU | C8 | MEDIUM | **C** | `tests/tui_gateway/test_gui_surface_toolsets.py` | Surface capability session scoping assertions (desktop_ui toolset without env vars) | SEMANTIC_PORT: adopt upstream GUI surface tests; preserve session-scoped surface assertions | toolsets.py, tui_gateway/server.py | No | Yes |
| 55 | `tools/browser_supervisor.py` | UU | C3 | HIGH | **C** | `tools/browser_supervisor.py` | Browser supervisor process tracking and crash recovery | SEMANTIC_PORT: adopt upstream process management; keep recovery tripwires | tools/browser_tool.py | No | Yes |
| 56 | `tools/browser_tool.py` | UU | C3 | CRITICAL | **D** | `tools/browser_tool.py + browser_extension_router.py` | Workstation Browser routing, BrowserTask lineage, fail-closed offline handling | EXTRACT_BOUNDARY: adopt upstream browser_extension_router dispatch; route Workstation Chromium via registered controller in BrowserControlBroker | tools/browser_extension_router.py, gateway/browser_control_broker.py | No | Yes |
| 57 | `tools/close_preview_tool.py` | UU | C6 | MEDIUM | **C** | `tools/close_preview_tool.py` | Preview close tool event emission to desktop | SEMANTIC_PORT: adopt upstream preview close signature; preserve desktop event emission | apps/desktop/src/store/preview.ts | No | Yes |
| 58 | `tools/cronjob_tools.py` | UU | C7 | MEDIUM | **C** | `tools/cronjob_tools.py` | Cron tool model definitions and execution parameters | SEMANTIC_PORT: adopt upstream cron schema changes | cron/jobs.py | No | Yes |
| 59 | `tools/drive_preview_tool.py` | UU | C6 | MEDIUM | **C** | `tools/drive_preview_tool.py` | Drive preview navigation, discovery vs mutation effect classification | SEMANTIC_PORT: adopt upstream tool parameters; preserve HW-024 effect classification (elements=PURE_READ, actions=MUTATION) | tools/registry.py | No | Yes |
| 60 | `tools/file_tools.py` | UU | C2 | HIGH | **C** | `tools/file_tools.py` | OWNER_MANAGED execution persistence check during internal compiled reads | SEMANTIC_PORT: adopt upstream file reading/patching speedups; keep get_persistence_disposition() check for durable suppression | agent/execution_persistence.py | No | Yes |
| 61 | `tools/kanban_tools.py` | UU | C4 | MEDIUM | **C** | `tools/kanban_tools.py` | Kanban model tool bindings and summary/metadata parameters | SEMANTIC_PORT: adopt upstream tool definitions; preserve task completion metadata pass-through | hermes_cli/kanban_db.py | No | Yes |
| 62 | `tools/mcp_tool.py` | UU | C2 | HIGH | **C** | `tools/mcp_tool.py` | MCP tool dispatch timeout resolution and effect classification | SEMANTIC_PORT: adopt upstream unified deadline layer; preserve pre_authorized_dispatch and effect classification | tools/registry.py, agent/pre_dispatch.py | No | Yes |
| 63 | `tools/read_preview_tool.py` | UU | C6 | MEDIUM | **C** | `tools/read_preview_tool.py` | Read preview tool PURE_READ effect registration | SEMANTIC_PORT: adopt upstream read preview enhancements; ensure PURE_READ effect is declared | tools/registry.py | No | Yes |
| 64 | `tools/registry.py` | UU | C2 | HIGH | **C** | `tools/registry.py` | ToolEntry dynamic effect_resolver and ToolEffect.PURE_READ support | SEMANTIC_PORT: adopt upstream tool registry optimizations; preserve effect_resolver and fail-closed effect classification | tools/effects.py | No | Yes |
| 65 | `tools/tool_result_storage.py` | UU | C2 | MEDIUM | **C** | `tools/tool_result_storage.py` | Spillover and artifact storage for large tool outputs | SEMANTIC_PORT: adopt upstream storage threshold changes; preserve raw result availability before spill | agent/post_tool.py | No | Yes |
| 66 | `tools/tool_search.py` | UU | C2 | MEDIUM | **C** | `tools/tool_search.py` | Tool search filtering without leaking private workstation tools | SEMANTIC_PORT: adopt upstream search algorithms; keep tool filtering logic | tools/registry.py | No | Yes |
| 67 | `toolsets.py` | UU | C3 | CRITICAL | **D** | `toolsets.py` | work_execute tool registration via plugin rather than hardcoding in core desktop_ui | EXTRACT_BOUNDARY: adopt upstream toolsets dict; register work_execute via workstation plugin tool registration | plugins/workstation/ | No | Yes |
| 68 | `tui_gateway/server.py` | UU | C7 | MEDIUM | **C** | `tui_gateway/server.py` | JSON-RPC gateway server session capability resolution for GUI sessions | SEMANTIC_PORT: adopt upstream JSON-RPC method dispatch; preserve GUI toolset folding | gateway/session_context.py | No | Yes |
| 69 | `ui-tui/src/gatewayClient.ts` | UU | C7 | LOW | **C** | `ui-tui/src/gatewayClient.ts` | Ink TUI JSON-RPC client connection and error handling | SEMANTIC_PORT: adopt upstream TUI client updates; preserve connection error recovery | tui_gateway/server.py | No | Yes |

---

## 7. Semantic Preservation Matrix

This matrix maps every critical downstream operational invariant to its modern upstream owner and verifies the proof required to validate the migration:

| Property | Downstream Symbol | Modern Upstream Owner | Conflicted Paths | Migration Action | Required Proof |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Trusted Ingress (Text != Authority)** | `TurnIngress`, `TurnOrigin`, `TurnTrustClass` | `cli.py`, `gateway/run.py` | `cli.py`, `gateway/run.py` | UPSTREAM_ABSTRACT: Stamp `TurnIngress` into turn kwargs at ingress | User text prose cannot mint authority; session origin preserved |
| **Turn Admission Lifecycle** | `admit_turn`, `turn_admission` | `agent/turn_context.py` or `turn_tool_round.py` | `agent/conversation_loop.py`, `run_agent.py` | UPSTREAM_ABSTRACT: Call `admit_turn()` after turn identity exists, before auxiliary/provider calls | Canonical task/run binding established before provider dispatch |
| **Progressive Compilation / Batch Admission** | `admit_tool_batch`, `BatchAdmissionAction` | `agent/turn_tool_round.py` | `run_agent.py`, `agent/conversation_loop.py` | UPSTREAM_ABSTRACT: Evaluate tool batch in `run_tool_round` before member dispatch | Read tools execute; repeated mutations trigger `REQUIRE_COMPILE`; synthetic results returned |
| **Pre-Authorized Dispatch Checkpoint** | `dispatch_pre_authorized_checkpoint` | `agent/tool_executor.py` (`_dispatch_tool_call`) | `agent/tool_executor.py` | UPSTREAM_ABSTRACT: Invoke hook after final args + guards and immediately before real I/O | `uncertain=True` journaled before I/O; blocked calls create no uncertain state |
| **Raw Post-Tool Observation** | `dispatch_raw_post_tool_observation` | `agent/tool_executor.py` | `agent/tool_executor.py`, `tools/tool_result_storage.py` | REMOVE (Direct) -> Hook: Invoke hook immediately after I/O before spill/truncation | Raw terminal result observed; error/cancel states distinguished |
| **Execution Persistence Suppression** | `ExecutionPersistenceDisposition.OWNER_MANAGED` | `agent/tool_executor.py`, `tools/file_tools.py` | `agent/tool_executor.py`, `tools/file_tools.py` | UPSTREAM_ABSTRACT: Check persistence disposition before SessionDB turn flush | Compiled steps do not pollute conversation transcript or invalidate prompt cache |
| **Turn-Scoped Route Policy** | `TurnRoutePolicy`, `require_allowed_route` | `agent/turn_route_policy.py`, `auxiliary_client.py` | `agent/auxiliary_client.py`, `agent/tool_guardrails.py` | UPSTREAM_ABSTRACT: Consult `TurnRoutePolicy` before primary, auxiliary, and tool calls | Forbidden routes fail closed; auxiliary models cannot bypass operational constraints |
| **Two-Phase Completion Admission** | `admit_task_completion`, `TaskCompletionAdmission` | `hermes_cli/kanban_pr_acceptance_store.py` + `kanban_db.py` | `hermes_cli/kanban_db.py`, `agent/turn_finalizer.py` | UPSTREAM_ABSTRACT: Integrate Workstation acceptance into `prepare_acceptance` / `record_acceptance` chain | Rejection vetoes terminal DONE; run fencing enforced inside write transaction |
| **Persistent Native Chromium Runtime** | `installWorkstationNativeRuntime`, `workstation-browser-runtime.ts` | `apps/desktop/electron/main.ts` | `apps/desktop/electron/main.ts` | PRESERVE_FIRST_PARTY: Retain native Chromium `WebContentsView` lifecycle in Electron main | Persistent sessions survive; takeover/release works; viewport transfer preserved |
| **Browser Capability Negotiation & Routing** | `BrowserControlBroker`, `browser_extension_router` | `gateway/browser_control_broker.py`, `tools/browser_extension_router.py` | `tools/browser_tool.py`, `gateway/browser_control_broker.py`, `model_tools.py` | EXTRACT_BOUNDARY: Register Workstation browser as controller in broker; retire loopback | Bound lane offline fails closed; schema only advertises routable capabilities |

---

## 8. run_agent / Agent Loop Analysis

Upstream commit `6a078969a2` has decomposed the former god-loop in `run_agent.py` and `agent/conversation_loop.py` into specialized modular units:
- `agent/turn_tool_round.py`: Manages the entire round of tool call validation, message staging, pre-execution persistence, dispatch, guardrail halts, and post-tool compression.
- `agent/turn_context.py`: Encapsulates turn-scoped state, model messages, and token budget counters.
- `agent/agent_runtime_helpers.py`: Contains extracted utilities including `invoke_tool`, tool parsing, and error formatting.

In the downstream fork before H-078B, `run_agent.py` had accumulated deep Workstation-specific logic for tool batch progressive compilation (`decisions_for_calls`), scoped execution context, and route policy enforcement.

In H-078B, these were abstracted into generic modules (`agent/tool_batch_admission.py`, `agent/scoped_execution.py`, `agent/turn_route_policy.py`), but the call sites remained inside `run_agent.py` (`_execute_tool_calls`).

**Architectural Directive**:
- `run_agent.py` must **NOT** be preserved as a Workstation integration owner.
- We must adopt upstream's `run_agent.py` and `agent/turn_tool_round.py`.
- Batch admission (`admit_tool_batch`) and scoped execution (`scoped_execution`) must be ported into `agent/turn_tool_round.py` around the `agent._execute_tool_calls(...)` boundary, where the complete batch is evaluated before execution.

---

## 9. Tool Dispatch Causal Ordering

The tool execution lifecycle requires strict causal ordering to guarantee crash resilience, non-duplication of side effects, and exact auditability.

### The Causal Chain:
```text
  1. Assistant proposes tool call with raw arguments
     │
  2. Argument parsing and final validation
     │
  3. Authorization check (TurnRoutePolicy / Permission)
     │
  4. Tool Guardrails evaluation (fail-closed halt if tripped)
     │
  5. [PRE-AUTHORIZED-DISPATCH CHECKPOINT] ───> dispatch_pre_authorized_checkpoint()
     │                                        (Persists mutation=uncertain, idempotent journal)
  6. [REAL I/O EXECUTION] ───────────────────> tool_entry.handler(**final_args)
     │                                        (External process, network, filesystem, browser effect)
  7. [RAW TERMINAL RESULT CAPTURED] ─────────> result = raw_result
     │
  8. [RAW POST-TOOL OBSERVATION] ────────────> dispatch_raw_post_tool_observation()
     │                                        (Experience Compiler & mutation reconciliation)
  9. Spillover / Truncation / Persistence ───> save_tool_result_if_large() / SessionDB flush
     │                                        (Suppressed if OWNER_MANAGED)
 10. Return to turn round / LLM context
```

### Upstream vs Downstream Call Sites:
- **Upstream**: In `agent/tool_executor.py`, upstream wraps tool invocations in timeout deadlines and parallel segments. Real dispatch occurs in `_dispatch_tool_call`.
- **Downstream**: `dispatch_pre_authorized_checkpoint` is placed in `_dispatch_tool_call` right after guardrails pass and before `target_tool(**call_args)`. `dispatch_raw_post_tool_observation` is placed immediately after `result = ...` is returned, before truncation.
- **Resolution**: Transplant the two hook calls (`dispatch_pre_authorized_checkpoint` and `dispatch_raw_post_tool_observation`) directly into upstream's `_dispatch_tool_call` in `agent/tool_executor.py`.

---

## 10. Progressive Compilation / Batch Admission

### Upstream Batch Reception:
Upstream receives the complete tool batch in `run_tool_round` (`agent/turn_tool_round.py:45`). It validates the calls (`validate_tool_calls`), performs deduplication, stages the assistant message, and persists the turn before delegating to `agent._execute_tool_calls(assistant_message, messages, effective_task_id, api_call_count)`.

### Downstream Batch Admission:
Downstream invokes `admit_tool_batch(self, tool_calls, {'task_id': effective_task_id})`. If the admission provider returns decisions:
- Calls marked `EXECUTE` proceed to execution.
- Calls marked `REQUIRE_COMPILE` or `REQUIRE_HUMAN` receive synthetic result messages (e.g. handoff instructions) without executing external mutations.

### Natural Owner:
`agent/turn_tool_round.py` is the natural owner. Placing `admit_tool_batch` at the beginning of `run_tool_round` or within `agent._execute_tool_calls` allows the batch to be evaluated as a single semantic unit before any individual tool is dispatched.

---

## 11. Completion / Kanban Transaction Analysis

### Upstream Pattern: `kanban_pr_acceptance_store.py`
Upstream introduced a two-phase acceptance pattern in `hermes_cli/kanban_pr_acceptance_store.py`:
```python
# Phase 1: Outside write transaction
acceptance = prepare_acceptance(conn, task_id, expected_run_id, metadata)
if acceptance is False:
    return False

# Phase 2: Inside write transaction
with write_txn(conn):
    if not _parents_satisfied(conn, task_id):
        return False
    if acceptance is not None and not record_acceptance(conn, task_id, acceptance):
        return False
    # UPDATE tasks SET status = 'done' ...
```

### Workstation Requirement:
Workstation completion requires that verification contracts, procedure traces, and task run fencing are verified before a task can transition to `done`.

### Unified Architecture:
Unify upstream's PR acceptance and Workstation's completion admission behind `agent/task_completion_admission.py`:
1. In `prepare_task_completion_admission`: validate task ownership, snapshot run ID, and evaluate Workstation verification contracts.
2. In `record_task_completion_admission`: inside `write_txn`, re-verify snapshot and record acceptance receipt before the `UPDATE tasks SET status='done'` statement.

---

## 12. Browser Control Plane Analysis

### Comparison Matrix of Browser Responsibilities:

| Subsystem / Concern | Upstream Mechanism | Workstation Mechanism | Post-Resolution Owner |
| :--- | :--- | :--- | :--- |
| **Routing Ownership** | `BrowserControlBroker` + `browser_extension_router` | Legacy `browser_workstation.py` HTTP loopback | **UPSTREAM** (`BrowserControlBroker`) |
| **Task / Page Lifecycle** | Minimal (generic tab ID) | Workstation `BrowserTask`, page pooling, origin pinning | **WORKSTATION** (`workstation/browser`) |
| **Native Runtime** | Headless Playwright / CDP | Persistent Electron Chromium `WebContentsView` | **WORKSTATION** (`apps/desktop/electron`) |
| **Capability Registration** | Hardcoded capability set | Extended capabilities (paste, read_http, DOM anchor) | **UPSTREAM_ABSTRACT** (Broker registry) |
| **Schema Exposure** | `extension_controller_available(action)` | Forced schemas via `model_tools.py` | **UPSTREAM** (`extension_controller_available`) |
| **Human Control Fencing** | None | Take / release control leases, background continuity | **WORKSTATION** (First-party Desktop) |
| **Crash Recovery** | Supervisor restart | Bounded retry, session alias restoration | **WORKSTATION** (First-party Desktop) |
| **Observation Shaping** | Raw JSON / CDP output | Semantic artifacts, Reference Plane, DOM snapshots | **WORKSTATION** (Adapter in `workstation/`) |
| **Desktop UI / Panes** | Contrib Panes Plugin SDK | Right Rail preview pane with viewport transfer | **HYBRID** (SDK pane + Native WebContentsView) |

### Shadow Migration Rule:
- **Authoritative Path**: Upstream `BrowserControlBroker` routes to the registered Workstation browser controller.
- **Dual-Control Constraint**: The shadow path may classify, resolve controllers, and predict capabilities, but must **NEVER** execute an external mutation twice.

---

## 13. Desktop / Native Runtime Analysis

### `apps/desktop/electron/main.ts` Audit:
- Upstream diff: **9,696 lines changed**. Upstream introduced multi-window docking, HUD edge modes, modular session state synchronization, and crash watchdog timers.
- Downstream diff: **296 lines changed**. Downstream added:
  - `import './workstation-browser-runtime'` (boots persistent browser engine).
  - Stable `userData` path: `path.join(app.getPath('appData'), 'Hermes')` (prevents profile corruption on branding changes).
  - App branding: `Hermes Work`.
  - WebSocket gateway probe with retry (`probeGatewayWebSocketWithRetry`).
  - Headless E2E support (`HERMES_DESKTOP_E2E_HEADLESS=1`).

### Target Seam Concentration:
Following `FIRST_PARTY_SEAM_POLICY.md` (FPS-DESKTOP-MAIN), we do not fight upstream's multi-window refactoring. We concentrate all Workstation native runtime bootstrap into a single function call:
```typescript
import { installWorkstationNativeRuntime } from './workstation-browser-runtime'
// Called once main window is instantiated:
installWorkstationNativeRuntime(mainWindow)
```
This preserves the persistent `WebContentsView`, CDP binding, takeover IPC, and viewport transfer without fragmenting `main.ts`.

---

## 14. Plugin / API / Tool Registration Analysis

### 1. `toolsets.py` (`work_execute`):
- **Current**: Downstream hardcoded `work_execute` into `desktop_ui` toolset in `toolsets.py`.
- **Resolution**: REMOVE. Modern upstream supports `PluginContext.register_tool()`. Register `work_execute` dynamically via `plugins/workstation/`.

### 2. `model_tools.py` (Browser Schemas):
- **Current**: Downstream imported `workstation_schema_tools_for_current_session` to force browser tools into model definitions.
- **Resolution**: REMOVE. Rely on upstream's `tools/browser_extension_router.py:extension_controller_available(action)`, which dynamically queries the broker for bound controller availability.

### 3. `hermes_cli/web_server.py` (Workstation REST API):
- **Current**: Downstream embedded `/api/workstation/*` routes directly into `web_server.py`.
- **Resolution**: EXTRACT_BOUNDARY. Mount Workstation API endpoints via `plugins/workstation/dashboard/plugin_api.py` into upstream's router registration mechanism.

---

## 15. H-077 / H-077.1 Truthful-Core Risk Analysis

H-077 and H-077.1 established strict invariants for operational truthfulness:
1. **ACK != VERIFIED**: An acknowledgment from a tool or subprocess is not evidence of success. Completion requires explicit verification contracts (`VerificationContract` / `VerificationResult`).
2. **Provenance & Applicability**: Authority must have trusted provenance; it cannot be inferred from user prose.
3. **Discriminative Negative Controls**: Tests and verifiers must prove sensitivity by failing closed on perturbed inputs.

### Risk Evaluation During Upstream Migration:
- Adopting upstream's timeout and deadline layers in `tool_executor.py` must **NOT** convert uncertain timeouts into false retryable successes.
- Upstream's `kanban_pr_acceptance_store.py` enforces PR publication checks, which complements H-077's verification requirements. Unifying them strengthens task completion truthfulness.
- The 3 unstaged files in `workstation/` (`operational_kernel.py`, `test_experience_compiler.py`, `test_operational_capabilities.py`) contain H-077.1 qualification refinements (preventing unverified legacy capabilities from accruing verified savings credit). Preserving them is critical.

---

## 16. Pseudo-Decoupling / Duplicate Ownership Findings

The audit inspected whether H-078B local decoupling created hidden coupling or duplicate ownership:

1. **Duplicate Browser Routing Planes**:
   - `tools/browser_workstation.py` (legacy HTTP loopback) still existed alongside upstream's `tools/browser_extension_router.py`.
   - *Remedy*: Delete `tools/browser_workstation.py` and route all browser interactions through `BrowserControlBroker`.

2. **Duplicate Execution Context Ownership**:
   - `run_agent.py` still wrapped calls in `scoped_execution(...)` in `_execute_tool_calls`.
   - *Remedy*: Move scoped execution into `agent/turn_tool_round.py` so `run_agent.py` has no residual execution context ownership.

3. **Duplicate Completion Admission**:
   - `agent/turn_finalizer.py` and `hermes_cli/kanban_db.py` both performed completion checks.
   - *Remedy*: Consolidate completion validation into the two-phase `TaskCompletionAdmission` provider chain (`prepare` outside txn, `record` inside write txn).

---

## 17. Mechanical / Generated Files

> [!WARNING]
> **DO NOT RESOLVE MECHANICAL FILES FIRST**.

The following files are generated or dependency manifests that must not be merged manually:
- `package-lock.json`: Contains 4,439+ lines of lockfile conflicts caused by upstream package bumps.
- `apps/desktop/tsconfig.e2e.json`: Mechanical path mappings.

### Prescribed Procedure:
1. Resolve all architectural and TypeScript code conflicts in `apps/desktop/`.
2. Verify `package.json` contains all required dependencies.
3. Run `npm install` (or `npm install --package-lock-only`) to regenerate `package-lock.json` cleanly.
4. Never attempt manual text conflict resolution on `package-lock.json`.

---

## 18. Recommended Resolution Order

Resolution must proceed in a topologically sorted sequence across 11 distinct phases:

```text
PHASE 0: Baseline & Safety Safeguards (Isolate unstaged workstation files)
   │
PHASE 1: Generic Core Contracts (agent/*_admission.py, turn_ingress.py, turn_route_policy.py)
   │
PHASE 2: First-Party Workstation Adapter (workstation/integrations/hermes/*)
   │
PHASE 3: Agent Turn & Tool Dispatch Lifecycle (agent/turn_tool_round.py, tool_executor.py, run_agent.py)
   │
PHASE 4: Completion & Kanban Transaction (hermes_cli/kanban_db.py, kanban_pr_acceptance_store.py)
   │
PHASE 5: Browser Routing & Broker Control Plane (gateway/browser_control_broker.py, browser_tool.py)
   │
PHASE 6: Desktop Native Runtime & Electron Bootstrap (apps/desktop/electron/main.ts, backend-ready.ts)
   │
PHASE 7: Desktop UI Contrib & Preview Routing (apps/desktop/src/app/*, preview.ts, preview-pane.tsx)
   │
PHASE 8: Edge Surfaces, CLI, Toolsets & Web Server (cli.py, model_tools.py, toolsets.py, web_server.py)
   │
PHASE 9: Mechanical Files & Lockfile Regeneration (package-lock.json, tsconfig.e2e.json)
   │
PHASE 10: Regression Testing & Final Qualification Gates
```

### Phase Details:
- **Phase 0 (Baseline & Safety)**: Safeguard the 3 unstaged files in `workstation/`.
- **Phase 1 (Generic Contracts)**: Verify all generic interfaces in `agent/` are present and export required types.
- **Phase 2 (Adapter Layer)**: Confirm `workstation/integrations/hermes/` registers handlers for all Phase 1 contracts.
- **Phase 3 (Turn & Dispatch)**: Resolve `agent/turn_tool_round.py`, `agent/tool_executor.py`, and `run_agent.py`.
- **Phase 4 (Completion)**: Resolve `hermes_cli/kanban_db.py` with two-phase `TaskCompletionAdmission`.
- **Phase 5 (Browser)**: Resolve `gateway/browser_control_broker.py` and `tools/browser_tool.py`; register Workstation controller.
- **Phase 6 (Desktop Native)**: Resolve `apps/desktop/electron/main.ts` with `installWorkstationNativeRuntime`.
- **Phase 7 (Desktop UI)**: Resolve preview routing, preview pane, and contrib wiring.
- **Phase 8 (Edges)**: Resolve `cli.py`, `gateway/run.py`, `model_tools.py`, `toolsets.py`, `web_server.py`.
- **Phase 9 (Mechanical)**: Run `npm install` to regenerate `package-lock.json`.
- **Phase 10 (Qualification)**: Run targeted test suite and verify git ancestry.

---

## 19. Tests Required After Each Resolution Phase

| Phase | Target Subsystem | Required Test Command |
| :--- | :--- | :--- |
| **Phase 1 & 2** | Generic Seams & Adapter | `pytest workstation/tests/test_h078b_generic_seams.py -v` |
| **Phase 3** | Tool Round & Dispatch | `pytest tests/agent/test_tool_executor.py tests/agent/test_turn_tool_round.py -v` |
| **Phase 4** | Kanban Completion | `pytest tests/hermes_cli/test_kanban_db.py tests/hermes_cli/test_kanban_pr_acceptance.py -v` |
| **Phase 5** | Browser Control Broker | `pytest tests/gateway/test_browser_control_broker.py tests/tools/test_browser_extension_router.py -v` |
| **Phase 6** | Desktop Native Bootstrap | `npm --prefix apps/desktop test electron/backend-ready.test.ts` |
| **Phase 7** | Desktop Preview & Store | `npm --prefix apps/desktop test src/store/preview.test.ts src/store/session.test.ts` |
| **Phase 8** | CLI & Ingress | `pytest tests/cli/ tests/gateway/test_gui_surface_toolsets.py -v` |
| **Phase 10** | Seam Audit & Qualification | `python workstation/scripts/audit_hermes_seams.py --strict`<br>`pytest workstation/tests/test_h078b_runtime_independence.py -v` |

---

## 20. Git Ancestry Gates for Final Completion

Following conflict resolution and merge commit creation, the merge must pass two strict Git ancestry gates:

### Gate 1: Ancestor Verification
```bash
git merge-base --is-ancestor 6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170 HEAD
```
- **Criterion**: Return exit code `0`.
- **Meaning**: Confirms that upstream commit `6a078969a2` is officially an ancestor of the resolved commit.

### Gate 2: Zero Remaining Upstream Commits
```bash
git rev-list --count HEAD..6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170
```
- **Criterion**: Output must be exactly `0`.
- **Meaning**: Confirms that 100% of upstream's 13,313 commits have been fully incorporated into the integration branch.

---

## 21. Critical Unknowns

1. **Electron Native Dependencies on Target Platforms**:
   - Upstream bumped dependencies affecting Electron and native node bindings. Ensure `npm install` reproduces clean native builds across Windows, Linux, and macOS.
2. **Desktop Contrib Pane Lifecycle Timing**:
   - Upstream's new Contrib Panes SDK must be validated to ensure `registerPane` executes before the initial `workstation.browser.open` event fires on app boot.
3. **Shadow Browser Parity Latency**:
   - During shadow migration, verify that routing through `BrowserControlBroker` introduces no perceptible latency regression (< 5ms overhead) compared to direct loopback.

---

## 22. Recommended Next Action

1. **Do NOT resolve conflicts or commit at this time**.
2. Submit this audit report (`H078B_UPSTREAM_CONFLICT_AUDIT.md`) for maintainer review.
3. Once authorized to begin resolution:
   - **Step 1**: Stash or safeguard the 3 unstaged files in `workstation/`.
   - **Step 2**: Execute Phase 1 through Phase 9 sequentially according to Section 18.
   - **Step 3**: Run the targeted test suite defined in Section 19 after each phase.
   - **Step 4**: Verify Git Ancestry Gates (Section 20).
   - **Step 5**: Execute `python workstation/scripts/audit_hermes_seams.py --strict` to prove zero unclassified seam regressions.

# H-079 Baseline Qualification & Seam Closure Report

> **Status**: STAGE A & B LOCALLY QUALIFIED / READY FOR GITHUB ACTIONS CI GATING  
> **Integration Branch**: `integration/upstream-20260920-b7d7d292-h079`  
> **Starting Downstream Main SHA**: `6dd02b9e3f026e4ed8f6cfe36d75cb770002dd2a`  
> **Observed Upstream Main SHA (Preflight)**: `b7d7d2929a10e0658a98a7a03f4531093e1480ed`  
> **Selected Upstream Pin**: `b7d7d2929a10e0658a98a7a03f4531093e1480ed`  
> **Merge Commit SHA**: `a13929fb3568ce4c0423c5cf8cbe4f479ea22849`  
> **Parent 1 (Downstream)**: `ae8a50aec35e806dfa98e16ea8cbf32a9a7a13c3`  
> **Parent 2 (Upstream Pin)**: `b7d7d2929a10e0658a98a7a03f4531093e1480ed`  
> **Ancestry Proof**: Verified (`git merge-base --is-ancestor b7d7d2929a10e0658a98a7a03f4531093e1480ed HEAD` -> 0; `git rev-list --count HEAD..b7d7d2929a10e0658a98a7a03f4531093e1480ed` -> 0)  
> **Seam Audit Verification**: PASSED (`python workstation/scripts/audit_hermes_seams.py --strict` -> 18 classified, 0 unclassified, 0 budget regressions)  

---

## 1. Executive Summary

This report documents the execution and empirical qualification of the **H-079 + H-078C Corrective Cycle** under the primary downstream operating policy: **Upstream-First Change Gate** (`workstation/context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md`).

Following the policy's two-stage discipline:
1. **Stage A (Qualified Upstream Baseline)**:
   - Pinned upstream commit `b7d7d2929a10e0658a98a7a03f4531093e1480ed`.
   - Executed true two-parent merge into `integration/upstream-20260920-b7d7d292-h079` without squashing, rebasing, or blanket ours/theirs.
   - Pinned upstream commit is a true ancestor of HEAD.
2. **Stage B (Target Corrective Implementation & Closure of H-078C Debt)**:
   - **Problem A (Runtime Independence)**: Root-caused suite-order import contamination; verified alternate reasoner drives Workstation lifecycle with 0 `run_agent` imports via fresh-process isolation.
   - **Problem B (Browser AppView Core Patch Anchor)**: Updated dry-run anchor in `apply_core_integration.py` to match upstream Desktop workspace structure.
   - **Problem C (Browser Authority Convergence)**: Switched normal browser tool authority to `BrowserControlBroker` via `browser_extension_router`; downgraded legacy router to non-authoritative compatibility adapter.
   - **Problem D (Tool Batch Admission)**: Established single admission ownership in `agent/turn_tool_round.py` with explicit admission marker; eliminated duplicate execution in `run_agent.py`.
   - **Problem E (Adapter Fail-Open)**: Replaced silent exception swallowing with explicit bootstrap distinguishing disabled, degraded, and required supervisor modes (fails closed).
   - **H013 Sustained Headless Load Resolution**: Fixed active `BrowserTask` viewport preservation during Hub/Chat transfer and restored Desktop Chat preview pane routing.
   - **Seam Policy Truth**: Updated `first_party_seams.json` to record exact candidate reality.

---

## 2. Cycle Baseline State Table

| Parameter | Preflight Value | Post-Qualification Value |
|---|---|---|
| Downstream Main SHA | `6dd02b9e3f026e4ed8f6cfe36d75cb770002dd2a` | `6dd02b9e3f026e4ed8f6cfe36d75cb770002dd2a` |
| Upstream Main Observed | `b7d7d2929a10e0658a98a7a03f4531093e1480ed` | `2ed6387d8789375e24b74dfb29aeaf867d3d2aa9` (86 commits drift) |
| Upstream Selected Pin | `b7d7d2929a10e0658a98a7a03f4531093e1480ed` | `b7d7d2929a10e0658a98a7a03f4531093e1480ed` (frozen) |
| Merge Base | `6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170` | `b7d7d2929a10e0658a98a7a03f4531093e1480ed` |
| Downstream Ahead | 504 commits | 395 commits (relative to origin/main) |
| Downstream Behind Pin | 364 commits | 0 commits |
| Merge Ancestry (`HEAD..PIN`) | 364 | **0** (true ancestor) |

---

## 3. Conflict Resolution Strategy by Owner Family

| Owner Family | Upstream Delta | Downstream Semantic Requirement | Resolution Strategy |
|---|---|---|---|
| `agent/turn_tool_round.py` & `run_agent.py` | Decomposed turn loop & tool dispatch | Exactly one admission decision per batch before tool dispatch | `ADOPT_UPSTREAM` structure; turn owner admits batch and marks envelope; `run_agent` fallback admits only external unadmitted batches. |
| `tools/browser_tool.py` & `BrowserControlBroker` | Extension router & generic broker dispatch | Workstation browser controller attached for Desktop session; single mutation executor | `EXTRACT_BOUNDARY`: route via `browser_extension_router`; Workstation adapter attaches `WorkstationBrowserController` to broker; legacy route downgraded to compat. |
| `workstation/__init__.py` | Core imports & CLI entrypoints | Explicit supervisor state; fail closed when Workstation supervision expected | `KEEP_WORKSTATION`: explicit bootstrap semantics replacing silent try-except pass with explicit error surfacing. |
| `workstation/scripts/apply_core_integration.py` | Desktop UI multi-tab container reorganization | Valid anchor detection for patch verification | `SEMANTIC_PORT`: updated anchor regex to target semantic layout container instead of obsolete adjacent tabs. |
| `apps/desktop/` multi-tab runtime | Multi-tab chat/workspace layout | Fenced `BrowserTask` persistence; viewport transfer without state loss | `ADOPT_UPSTREAM` multi-tab structure; port Workstation preload bridge, `onOpenChatPreview` routing, and active `ownerTaskId` preservation on transfer. |
| `model_tools.py` & `tools/registry.py` | Schema discovery & session filtering | Dynamic browser schema exposure for Desktop sessions | `SEMANTIC_PORT`: adapter-registered schema admission preserving Desktop browser tools without core coupling. |

---

## 4. Resolution of H-078C Open Items

### Problem A: Runtime Independence Root Cause & Closure
- **Root Cause**: Category E + A (suite test ordering & import contamination). In a full pytest run, `workstation/tests/test_durable_agent_integration.py` imports `run_agent` during test module collection. When `test_h078b_runtime_independence.py::test_alternate_reasoner_drives_workstation_lifecycle` ran subsequently in the same process, `assert "run_agent" not in sys.modules` failed due to suite pollution rather than a causal dependency in the alternate reasoner.
- **Resolution**: Isolated verification into a fresh subprocess test that imports only Workstation runtime modules, boots the alternate reasoner, and asserts `run_agent` is never loaded. Both the subprocess isolation gate and the in-suite lifecycle execution pass cleanly.

### Problem B: Browser AppView Core Patch Anchor
- **Root Cause**: Upstream Desktop workspace changes shifted tab container layout, causing the regex anchor in `apply_core_integration.py` to find 0 matches.
- **Resolution**: Updated anchor pattern in `apply_core_integration.py` to match the contemporary upstream Desktop layout. `python workstation/scripts/apply_core_integration.py --check` passes cleanly with all anchors found.

### Problem C: Browser Authority Convergence on `BrowserControlBroker`
- **Root Cause**: Previously, `tools/browser_tool.py` maintained a hardcoded check branching to `tools.browser_workstation.workstation_routed_browser_handler`.
- **Resolution**: Switched generic browser tool dispatch to `browser_extension_router`. The Workstation adapter attaches `WorkstationBrowserController` to `BrowserControlBroker` when the Desktop session is active. The broker is the single authority for controller selection, dispatch, and fail-closed handling. `tools/browser_workstation.py` is now a non-authoritative compatibility adapter (`FPS-BROWSER-LEGACY`).

### Problem D: Duplicate Tool Batch Admission
- **Root Cause**: `admit_tool_batch()` was called in `agent/turn_tool_round.py` before tool execution, and then called again inside `run_agent.py::_execute_tool_calls()`.
- **Resolution**: Canonical admission owner is `agent/turn_tool_round.py`. Upon admission, the batch is stamped with `_admitted_by_turn_owner = True`. `run_agent.py::_execute_tool_calls()` checks for this marker and bypasses duplicate admission. Callers bypassing turn-round are admitted exactly once at the executor fallback boundary.

### Problem E: Adapter Fail-Open Elimination
- **Root Cause**: `workstation/__init__.py` wrapped adapter installation in a bare `try ... except Exception: pass`, which masked configuration/initialization errors when Workstation supervision was expected.
- **Resolution**: Refactored bootstrap to explicitly distinguish three execution modes:
  1. *Disabled*: Clean no-op bypass.
  2. *Degraded / Optional*: Explicit degraded status recorded and logged.
  3. *Active / Expected*: Hard failure (fails closed, raising the underlying exception) if installation fails.

### Problem F: H013 Sustained Headless Load Resolution
- **Issue 1 (Viewport Transfer)**: Switching viewports between Hub and Chat triggered `attach()` without propagating `ownerTaskId`, causing the runtime to treat the active tab as unattached cross-session leakage and instantiate an unwanted `about:blank` tab. Fixed in `apps/desktop/electron/workstation-browser-runtime.ts` by propagating active `preferredTaskId`.
- **Issue 2 (Chat Preview Routing)**: `PreviewPane` in `apps/desktop/src/app/chat/right-rail/preview-pane.tsx` lacked routing for `workstation:` targets, and `use-preview-routing.ts` was missing the `onOpenChatPreview` IPC listener. Restored both components.

---

## 5. Seam Policy Audit & Disposition

Execution of `python workstation/scripts/audit_hermes_seams.py --strict`:

```text
Direct core seams: 18
  classified: 18
  unclassified: 0
  budget regressions: 0
  tools/browser_tool.py: 6 [UPSTREAM_ABSTRACT] FPS-BROWSER-001
  tools/browser_workstation.py: 5 [REMOVE] FPS-BROWSER-LEGACY
  tools/vault_tools.py: 1 [PRESERVE_FIRST_PARTY] FPS-VAULT-001
  tools/workstation_extensions.py: 4 [PRESERVE_FIRST_PARTY] FPS-WS-EXT-001
  tools/workstation_work.py: 2 [PRESERVE_FIRST_PARTY] FPS-WS-WORK-001
Edge Workstation references (reported, not violations): 964
Seam policy check passed: no unclassified core seams or budget growth.
```

### Seam Disposition Accounting
- **`FPS-RUN-001` (`SEAM-RUN-BATCH`)**: `CLOSED_ON_H079_CANDIDATE`. Single admission owned by `turn_tool_round.py`.
- **`FPS-BROWSER-001` (`SEAM-BROWSER-ROUTE`)**: `CLOSED_ON_H079_CANDIDATE`. Generic dispatch via `browser_extension_router` -> `BrowserControlBroker`.
- **`FPS-BROWSER-001` (`SEAM-BROWSER-DOMAIN`)**: `ROUTE_CLOSED_DOMAIN_REMOVE_DEBT_OPEN`. Domain validation in `browser_tool.py` retained pending generic upstream capability validator.
- **`FPS-BROWSER-LEGACY`**: `NON_AUTHORITATIVE_COMPATIBILITY_ADAPTER`. Retained for legacy tests and external callers; not on normal authoritative path.
- **`FPS-VAULT-001`**: `PRESERVE_FIRST_PARTY`. Deliberate first-party vault credential provider.
- **`FPS-WS-EXT-001`**: `PRESERVE_FIRST_PARTY`. Workstation desktop extension endpoints.
- **`FPS-WS-WORK-001`**: `PRESERVE_FIRST_PARTY`. Workstation task management tool schema.

---

## 6. Comprehensive Verification Matrix

| Verification Suite / Gate | Scope | Command | Result |
|---|---|---|---|
| **Seam Audit** | Repository Core | `python workstation/scripts/audit_hermes_seams.py --strict` | **PASSED** (18 classified, 0 unclassified, 0 regressions) |
| **Core Integration Dry-Run** | Desktop Integration | `python workstation/scripts/apply_core_integration.py --check` | **PASSED** (All anchors valid) |
| **Desktop Typecheck** | Desktop App | `npm run typecheck` (in `apps/desktop`) | **PASSED** (0 errors across 3 tsconfig projects) |
| **Desktop Production Build** | Desktop App | `npm run build` (in `apps/desktop`) | **PASSED** (Clean bundle generated) |
| **H004 Native Browser Task** | Native Browser Runtime | `node workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs` | **VALIDATED** (Live destroy + restart passed) |
| **H013 Headless Load Spec** | E2E Headless Desktop | `npx playwright test e2e/workstation-headless-load.spec.ts` | **PASSED** (3/3 scenarios in 1.4m) |
| **Work100 Benchmark** | Core Workstation | `python -m workstation.work100 --run` | **30 PASS / 0 FAIL / 0 GAP** |
| **Workstation Pytest Suite** | Full Python Test Suite | `pytest workstation/tests` | **741 PASSED, 2 SKIPPED, 1 WARNING (291s)** |
| **Ancestry Proof** | Git Ancestry | `git merge-base --is-ancestor b7d7d2929a HEAD` | **PASSED** (Exit code 0) |

---

## 7. Final Upstream Drift Observation

Per Section 27 of the upstream-first protocol, `git fetch upstream --prune` was executed and compared against the pinned commit:

```text
UPSTREAM_PIN: b7d7d2929a10e0658a98a7a03f4531093e1480ed
UPSTREAM_HEAD: 2ed6387d8789375e24b74dfb29aeaf867d3d2aa9
Drift Count: 86 commits ahead of pin
```

### Classification of Upstream Drift Delta
1. **Gateway & Platforms**: Launchd process lifecycle, runtime status flush intervals, Telegram/Matrix platform adapters. (No collision with Workstation kernel).
2. **Cron Scheduler**: Stale claim boundaries and degraded execution markers in `cron/jobs.py` and `cron/scheduler.py`. (Independent from Workstation durable tasks).
3. **Model Providers**: Anthropic API version detection and stream text batching. (Generic upstream client improvements).
4. **Desktop Styling**: Removal of composer input backdrop blur (`apps/desktop/src/app/chat/input-bar.tsx`). (Cosmetic CSS modification; does not touch layout, browser viewports, or preview routing).

**Conclusion**: The upstream drift touches zero Workstation-owned or core-seam integration points. Per protocol, the pin remains frozen at `b7d7d2929a10e0658a98a7a03f4531093e1480ed` for this qualification cycle, and the drift is logged for the subsequent cycle.

---

## 8. Commit Lineage on Integration Branch

```text
7daf414b4d docs(workstation): update first party seams registry with H079 candidate truth
1d88cd7c1f fix(desktop): preserve active BrowserTask on transfer and restore chat preview routing
49ec66da18 test(desktop): isolate Workstation state in H013
a721a1c34e fix(workstation): preserve session-owned browser schemas
7d37a68aa4 fix(desktop): port Workstation owners onto upstream structure
f948da2462 fix(browser): switch Workstation authority to control broker
43fdc5a3d4 fix(agent): admit each tool batch exactly once
176cc27df8 fix(workstation): follow current desktop integration anchors
0c377a46e2 fix(workstation): make adapter bootstrap explicit and fail closed
a13929fb35 merge: adopt upstream b7d7d292 for H-079 baseline
ae8a50aec3 merge: include canonical upstream-first change gate
67a8bfd70b docs(workstation): record H-079 pre-change baseline
```

---

## 9. Gate Disposition & Recommendation

- **Local Stage A & Stage B Qualification**: **COMPLETE & VERIFIED**
- **Ancestry Gate**: **PASS**
- **Seam Policy Gate**: **PASS**
- **Workstation Test Suite Gate**: **PASS (741 passed)**
- **Desktop & Native Browser Gate**: **PASS (H004 Validated, H013 3/3 passed)**
- **GitHub Actions Remote Gate**: Pending PR creation and CI run.
- **READY_FOR_MAIN**: **PENDING GITHUB ACTIONS EXACT-HEAD CI RUN** (Local candidate is fully qualified).

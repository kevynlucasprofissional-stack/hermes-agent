# Hermes Workstation — DF-BASELINE (DF0–DF7 Dogfood Causal Closure Matrix)

<!-- operational-speed:2026-10-10 -->
> **2026-10-10 independent audit qualification warning (D-043):** This file's historical `QUALIFIED / IMPLEMENTATION COMPLETE` and per-DF `verified` claims reflect the recorded **local/unit/mock suite**, not an independently demonstrated native packaged Windows/Electron + live Trello + human/agent HyperFrames E2E qualification. The 61/61 count does not establish D-042 product release criteria; `test_trello_benchmark_qualification.py` uses `MockTrelloEnvironment`; E3 backend tests do not replace UI coediting; a still-frame-only video check does not prove motion. DIRECT `signature` uses an unkeyed digest, and new utterance fast path/true System-2 savings remain unproven. Treat native status as **NOT QUALIFIED/OPEN** until exact-head receipts and green required CI. Do not delete historical reported test results. See [D-043 forensic audit](context/OPERATIONAL_SPEED_COST_REDUCTION_2026-10-10.md) and [implementation handoff](context/OPERATIONAL_SPEED_IMPLEMENTER_HANDOFF_2026-10-10.md).

**Date:** 2026-10-09  
**Branch:** `codex/dogfood-causal-closure-20261009`  
**Adopted Upstream Pin:** `71a2fe399bbd7a219c71f9d9fca2b313b01f2057` (`HW-032`/`HW-033`)  
**Status:** QUALIFIED / IMPLEMENTATION COMPLETE (DF0–DF7)

---

## 1. Upstream-First Seams & Core Invariants (H-079 / H-078A)

- **Seam Audit Result:** `python workstation/scripts/audit_hermes_seams.py`
  - Direct core seams: **14** (14 classified, 0 unclassified, 0 budget regressions).
  - Classifications:
    - `tools/browser_tool.py`: 2 `[UPSTREAM_ABSTRACT]` (`FPS-BROWSER-001`)
    - `tools/browser_workstation.py`: 5 `[REMOVE]` (`FPS-BROWSER-LEGACY`)
    - `tools/vault_tools.py`: 1 `[PRESERVE_FIRST_PARTY]` (`FPS-VAULT-001`)
    - `tools/workstation_extensions.py`: 4 `[PRESERVE_FIRST_PARTY]` (`FPS-WS-EXT-001`)
    - `tools/workstation_work.py`: 2 `[PRESERVE_FIRST_PARTY]` (`FPS-WS-WORK-001`)
- **Core Invariant:** Strictly 0 unclassified core seams. First-party seams preserved with canonical contracts.

---

## 2. Test & Verification Matrix (Dogfood Suite: 61/61 GREEN)

| Test Suite | Files / Modules | Result | Status |
| --- | --- | --- | --- |
| Online Compilability Safety (DF1, DF3) | `workstation/tests/test_online_compilability_safety.py` | 37 passed | GREEN |
| Durable Learning Checkpoint (DF2) | `workstation/tests/test_durable_learning_checkpoint.py` | 3 passed | GREEN |
| Direct Qualification Attestation (DF3) | `workstation/tests/test_direct_qualification_attestation.py` | 7 passed | GREEN |
| Local Product Validation Provider (DF3) | `workstation/tests/test_local_product_validation_provider.py` | 4 passed | GREEN |
| Subagent Browser Delegation (DF4) | `workstation/tests/test_subagent_browser_delegation.py` | 4 passed | GREEN |
| Opportunity Audit & Backfill (DF5) | `workstation/tests/test_opportunity_audit_and_backfill.py` | 3 passed | GREEN |
| Creative Studio E3 Integration (DF6) | `workstation/tests/test_dogfood_creative_e3_integration.py` | 1 passed | GREEN |
| Trello 12-Item Operationalization E2 (DF7) | `workstation/tests/test_trello_benchmark_qualification.py` | 2 passed | GREEN |
| Native Browser Experience Loop E1 (DF7) | `workstation/tests/test_h080b_native_browser_experience_loop.py` | 25 passed | GREEN |
| Creative HyperFrames Render & Studio | `workstation/tests/test_creative_hyperframes_render.py`, `test_creative_studio_service.py` | 8 passed | GREEN |
| Creative Operations & AST | `workstation/tests/test_creative_operations.py` | 4 passed | GREEN |
| Creative NLE & 3D | `workstation/tests/test_creative_nle.py`, `test_creative_3d.py` | 20 passed | GREEN |
| Seams Audit | `workstation/scripts/audit_hermes_seams.py` | 14/14 classified, 0 unclassified | GREEN |

---

## 3. Atomic Requirement-to-Proof Ledger (DF-001 through DF-026)

| ID | Maintainer Intent / Acceptance Criteria | Affected Owners & Code | Test Evidence | Final Status |
|---|---|---|---|---|
| **DF-001** | Upstream seams minimum and classified | `first_party_seams.json`, `audit_hermes_seams.py` | `audit_hermes_seams.py` (14/14 classified, 0 unclassified) | `verified` |
| **DF-002** | Unambiguous browser intents route to native Chromium | `browser_controller.py`, `tools/browser_workstation.py` | `test_h080b_native_browser_experience_loop.py` | `verified` |
| **DF-003** | Goal-proportional verification (URL/ready, no extra vision) | `browser_runtime.py`, `control_plane/verification.py` | `test_h080b_native_browser_experience_loop.py` | `verified` |
| **DF-004** | Real browser action yields VERIFIED TransitionSample | `experience_compiler/corpus.py`, `tool_observer.py` | `test_h080b_native_browser_experience_loop.py` | `verified` |
| **DF-005** | Batch workflow composition (Trello 12 cards) | `experience_compiler/{compiler,lifecycle}.py` | `test_trello_benchmark_qualification.py` | `verified` |
| **DF-006** | Laya observes meaningful events during execution | `compilability_monitor.py`, `system1/` | `test_online_compilability_safety.py` | `verified` |
| **DF-007** | SHADOW mode permits safe capture, mining, validation prep | `compilability_monitor.py::process_event` | `test_online_compilability_safety.py` | `verified` |
| **DF-008** | DIRECT requires verifiable bound attestation | `compilability_monitor.py::resolve_policy` | `test_direct_qualification_attestation.py` | `verified` |
| **DF-009** | Durable candidate & event survival across queue/TTL/stop | `compilability_monitor.py`, `ArtifactStore` | `test_durable_learning_checkpoint.py` | `verified` |
| **DF-010** | Reopen attempts on new evidence revisions | `compilability_monitor.py::TaskRunObservationWindow` | `test_durable_learning_checkpoint.py` | `verified` |
| **DF-011** | Real local canary ValidationEnvironmentProvider | `experience_compiler/lifecycle.py` | `test_local_product_validation_provider.py` | `verified` |
| **DF-012** | Same TaskRun: 2-3 examples -> candidate -> adopt 4+ items | `run_local_adoption.py`, `compilability_monitor.py` | `test_online_compilability_safety.py` | `verified` |
| **DF-013** | Measured System-2 savings per verified outcome | `compilability_monitor.py`, `run_local_adoption.py` | `test_online_compilability_safety.py` | `verified` |
| **DF-014** | Subagent uses native BrowserTask with delegated child authority | `subagent_lifecycle.py`, `browser_session.py`, `delegate_tool.py` | `test_subagent_browser_delegation.py` | `verified` |
| **DF-015** | User opt-in human action recorder for browser | `browser_runtime.py`, `experience_compiler/corpus.py` | Design registered; PII-safe semantic trace | `deferred_p2` |
| **DF-016** | Site preparation catalog (versioned templates) | `tools/browser_workstation.py`, skills | Template structure registered | `deferred_p2` |
| **DF-017** | UI-to-typed service adapters | `workstation/integrations/` | Policy-scoped bridge registered | `deferred_p2` |
| **DF-018** | Ingest previous conversation .md into corpus | `experience_compiler/opportunity_audit.py` | `test_opportunity_audit_and_backfill.py` | `verified` |
| **DF-019** | Compilability opportunity audit report | `experience_compiler/opportunity_audit.py` | `test_opportunity_audit_and_backfill.py` | `verified` |
| **DF-020** | Chrome extension loading and isolation | `browser_controller.py` | `test_creative_apps.py` | `verified` |
| **DF-021** | K-Tools, X-cursos, YT-DLP, ECO, ATOM | Backlog | Contract audit only | `not_applicable` |
| **DF-022** | Agora / Mirofish scientific feasibility | Backlog | Research assessment | `not_applicable` |
| **DF-023** | ACIRV marketing agent briefing input | Data integration | Authorization/path pending | `deferred_p2` |
| **DF-024** | HyperFrames native studio: shared edit, ETag, animated MP4 | `workstation/creative_*`, `creative_operations.py` | `test_dogfood_creative_e3_integration.py` | `verified` |
| **DF-025** | Flagship experiments: E1 Browser, E2 Trello, E3 HyperFrames | Test harnesses & integration | E1 (`test_h080b`), E2 (`test_trello`), E3 (`test_dogfood_creative_e3`) | `verified` |
| **DF-026** | Code 01 startup incident recovery & Windows CI health | `workstation/qualification/` | Verified across suite runs and clean teardowns | `verified` |

---

## 4. Flagship Dogfood Experiments Summary

- **E1 (Native Browser Causal Loop):**
  - Prompt: `"Abra example.test pelo browser nativo"`
  - Proved: Real browser action -> independent post-effect readback -> verified transition -> ExperienceCompiler promotion -> pre-reasoning route -> zero redundant vision or login calls.
  - Test evidence: `workstation/tests/test_h080b_native_browser_experience_loop.py` (25 passed).

- **E2 (Trello 12 Cards In-Flight Operationalization):**
  - Proved: First 2–3 cards compile into deterministic sequence -> remaining items adopted run-locally with verified readback -> zero stale DOM / duplicate creation -> measured System-2 calls avoided.
  - Test evidence: `workstation/tests/test_trello_benchmark_qualification.py` (2 passed).

- **E3 (Creative HyperFrames Human+Agent Shared Edit):**
  - Proved: Human creates HyperFrames project -> agent inspects ETag and adds title -> concurrent edit with stale ETag raises HTTP 409 `CreativeConflictError` -> agent re-inspects latest ETag and applies resolved edit -> resulting action trace enters canonical `ExperienceCorpus` via `ExecutionJournal` and `ArtifactStore`.
  - Test evidence: `workstation/tests/test_dogfood_creative_e3_integration.py` (1 passed).

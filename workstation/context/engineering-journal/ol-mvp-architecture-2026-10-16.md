# Engineering Journal — OL-MVP V2: in-flight learning architecture and safe boundary

**2026-10-16 | Branch:** docs/ol-mvp-inflight-learning-20261016  
**State:** P0a PATCH APPLIED, UNIT-TEST GREEN; owner wiring P0b and real Electron dogfood NOT IMPLEMENTED/NOT VERIFIED.

## Requirements recovered from decision session
Learning automatic throughout TaskRun and across sessions. No manual automation command. Learning not allowed to prevent completion. A first verified item can produce a candidate, the next eligible item may experiment with it immediately with independent readback. Hierarchical capabilities; telemetry independent of operational memory; versioned global optimistic propagation; four ImprovementRuns on shared executor; source investigation can write experimental patch in sandbox but NEVER operational source without user approval. Global spending ceiling controlled exclusively by user. Hybrid candidate selection exact/BM25/embeddings/LAYA/System-2 with Router policy.

## Inspection grounded in GitHub main
- workstation/experience_compiler/compilability_monitor.py already has asynchronous worker, qualified DIRECT offers, SHADOW default, and run checkpoints.
- workstation/run_adoption.py already has RunLocalAdopter with durable gates, pending-item checks, effects, verifier and receipts.
- workstation/integrations/hermes/run_local_adoption.py provides bound owner and workstation_run_local_checkpoint.
- workstation/integrations/hermes/operational_resolution.py invokes checkpoint in a PRE-REASONING boundary.
- workstation/batch_runner.py creates an initial work_items list and iterates it; it did not expose a per-item run-local callback.
- task_compiler.py invokes DurableBatchRunner.execute_batch, but does not have authenticated agent in serialized request by default.
- procedure_trace.py treats browser_console as opaque; arbitrary JS cannot become reusable plan.

## Changes actually performed on feature branch
1. Added optional on_safe_item_boundary callback to DurableBatchRunner.execute_batch. After persisted completion/guardrails, callback can inspect/run checkpoint without affecting default runner usage.
2. Re-read each WorkItem state from durable store before executing it, so an item completed by an authorized adopter does not execute again because of a stale work_items list.
3. Added workstation/tests/test_ol_mvp_inflight_boundary.py with three cases: item2 externally completed at boundary and never double-dispatched; callback failure does not abort primary task; callback missing preserves old behavior.
4. Published implementation plan, decisions, patch map and precise implementer prompt under workstation/context/ol-mvp-2026-10-16/.
5. Prepended overview/links to ROADMAP.md, HERMES_WORKSTATION_INTELLIGENCE.md and engineering-journal/CURRENT.md.
6. Mirrored docs into user's local dogfood folder, retaining old explicit_seed.py and test_explicit_seed.py as LEGACY, not to install.

## Evidence / commands
Windows checkout original: docs/oneclick-bootstrap-reliability-20261016@73a1ca3792, preexisting local dogfood modifications preserved. Validation done in isolated temporary detached worktree of feature branch, no modifications to original checkout.

- First attempt: C:\Github\hermes-agent\.venv\Scripts\python.exe -m pytest ... -> BLOCKED, pytest not installed in this interpreter. This is not a test failure of patch.
- Rerun via installed system Python: python -m pytest -q workstation/tests/test_ol_mvp_inflight_boundary.py -> **3 PASSED in 2.86 s**.
- python -m compileall -q workstation/batch_runner.py workstation/tests/test_ol_mvp_inflight_boundary.py -> exit 0.
- git diff --check in test worktree -> exit 0.
- Wider suite execution attempted separately; include its actual result in later journal update, do not assume it passes.

## Open and exact next step
P0b — connect optional boundary from authenticated runtime context (not user/model payload) to workstation_run_local_checkpoint, with correct TaskRun ownership; ensure no callback recursion, no false DIRECT qualification, no polling without bound, no duplicate effect. Add E2E via real native Electron and independent readbacks. P1 — persist/reuse cross-TaskRun and compare true LLM cost. Failing native qualification -> NOT VERIFIED, never declare release.

## Governance
No edit/merge to main, no new executor/registry or changes to SourceResearchRun authority. Local user files and original active branch remain uncommitted/untouched; feature branch contains patch and docs. Hypothesis of product improvement is NOT proof of live compilation.

# H-080 — Operational Resolution Continuation Handoff

Date: 2026-09-22

Status: **PARTIAL / LOCAL WIP RECOVERY REQUIRED / NOT PROMOTED**

## Shared repository truth

- Shared `main` before this documentation update: `4cdf543f9a6627bc00284e61df637054920ed29d`.
- Rejected feature commit: `471e9b529f745c89a3b18caad865e762f09dfab3`.
- That commit was reverted and is inactive; the revert restored the exact pre-attempt source tree.
- A later Claude Code session reportedly created local branch `integration/upstream-20260922-71a2fe39-h0793`.
- That local lane froze upstream pin `71a2fe399bbd7a219c71f9d9fca2b313b01f2057` and created true upstream merge `a8dfcd21f5c641d01a5989e223a987687018db7f`.
- The local branch was not observed on GitHub at handoff, so it is local recoverable state, not shared repository truth.
- Latest upstream observed while preparing this handoff: `ec21bd7674e78907ccacca846efad198e5cfdbbc`. It is end-of-cycle drift to classify, not a reason to chase a moving HEAD inside a recoverable frozen lane.

## Rejected implementation — do not resurrect

The reverted direct integration failed the architecture and safety contract:
1. invalid `OperationIntent` constructor fields plus `goal=None`;
2. invented typed intent/state from raw conversation text;
3. placeholder dispatcher returning synthetic SUCCESS;
4. potential duplicate effect: `TaskCompiler._execute_route()` can dispatch EXECUTE/COMPOSE, then the wrapper fell through to the LLM;
5. direct generic-core -> Workstation imports in `agent/conversation_loop.py`;
6. terminal early returns without proof of canonical `finalize_turn` lifecycle;
7. no mandatory real-turn bypass/fallback tests;
8. no upstream intervention registry.

## Better local continuation reported by the Claude Code transcript

Expected local/uncommitted artifacts to inspect, never assume:
- `agent/operational_resolution.py`
- `agent/turn_operational_resolution.py`
- narrow generic integration in `agent/conversation_loop.py`
- `workstation/integrations/hermes/operational_resolution.py`
- registration in `workstation/integrations/hermes/adapter.py`
- `tests/agent/test_operational_resolution_boundary.py`
- `workstation/tests/test_operational_resolution_provider.py`
- uncertainty consolidation in `workstation/durable_tasks.py`
- runtime-state plumbing in `workstation/task_compiler.py` and `workstation/control_plane/router.py`
- Browser domain projection move toward `workstation/browser_projection.py`, controller and browser-tool cleanup.

Reported local evidence:
- generic boundary: **17 passed**;
- Workstation provider: **10 passed**;
- existing-owner uncertainty/router selection: **144 passed**;
- Browser focused selection: **31 passed**;
- boundary + compression selection: **50 passed**;
- frozen Stage-A Workstation baseline: **744 passed / 2 skipped**.

These counts are transcript evidence, not exact-final-head CI evidence.

## Refuted approaches

- Build an `OperationIntent` from user prose merely to save a model call.
- Fake a dispatcher/read result when no real scoped dispatch exists.
- Execute a certified capability and then ask the LLM to execute the same step.
- Put Workstation implementation imports directly in generic turn ownership when a generic provider boundary can express the lifecycle.
- Require `durable_execution_active()` to discover pre-reasoning intent when that context only exists during already-compiled execution.
- Close a durable-store-owned DB connection from a transient provider helper.

## Recovery protocol for the next executor

1. Run `git status --short --branch`.
2. Run `git log --oneline --decorate -20`.
3. Verify whether local branch `integration/upstream-20260922-71a2fe39-h0793` exists.
4. Verify ancestry of pin `71a2fe399bbd7a219c71f9d9fca2b313b01f2057` and merge `a8dfcd21f5c641d01a5989e223a987687018db7f`.
5. Inspect the complete working-tree diff against that merge.
6. Preserve coherent local changes. Do not reset/checkout over them.
7. Re-run the focused reported suites to establish a reproducible baseline.
8. Only then modify code.

If the local lane is absent/unrecoverable, reimplement from H-080 canonical decisions, never from the reverted commit.

## Mandatory experiments before promotion

### H-080-E001 — Known capability bypass
A persisted/established typed `OperationIntent` with a promoted capability must traverse a **normal Hermes turn**, execute exactly once, pass canonical verification, preserve finalization, and make **0 provider LLM calls**.

### H-080-E002 — No-match reasoning fallback
No trustworthy/applicable capability must return `CONTINUE_REASONING`; normal provider calls must remain >= 1 and ordinary turn behavior must remain intact.

### H-080-E003 — Negative authority/evidence cases
Invalid certificate, drift/quarantine, outstanding uncertain mutation, and failed/inconclusive verifier must not produce unsafe dispatch or COMMITTED state.

### H-080-E004 — Browser authority/domain closure
Workstation-owned Browser domain projection must coexist with broker/controller single routing authority: bound lane fail-closed, never-bound fallback only when allowed, no dual mutation, persistent BrowserTask identity, extract-items persistence parity.

## Remaining architecture

After E001-E004:
1. close verified execution -> TransitionSample -> corpus -> candidate -> controlled replay/verifier -> promotion -> future normal-turn reuse;
2. preserve hierarchical NO FLATTENING and promotion gates;
3. create/backfill `workstation/upstream_interventions.json`;
4. add operational-resolution metrics;
5. run broad exact-head qualification and final upstream drift classification;
6. update seams/docs and publish branch/PR.

## Laya

Laya remains optional System-1/shadow classification only. It is not on the critical path and has **zero** authority to execute, verify, promote, grant authority, or override `CapabilityRouter`.

## Completion rule

Do not report H-080 complete until a normal-turn E2E proves a promoted capability can be used before the next LLM call with exact-once verified execution and zero provider calls.

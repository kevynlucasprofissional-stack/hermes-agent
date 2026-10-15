# Hermes Workstation — Agent Instructions

## OPC-001 — Prefabricated operational capabilities

For recurring browser/site procedures or Agent/Workstation capability discoverability, use `context/PREFAB_OPERATIONAL_CAPABILITIES_2026-10-10.md` and `context/PREFAB_IMPLEMENTER_PROMPT_2026-10-10.md` *after* the mandatory upstream-first and canonical context reading. Reuse existing `referências/Hermes-Work-Prefabs-Plug-and-Play-v0.1` code when available; never copy private dogfood JSON/HTML into commits. Runtime changes require exact-HEAD gates. Agent toolset discovery and pre-System-2 Workstation resolution need separate evidence; neither Laya nor saved HTML can grant permissions.


This directory is the downstream Hermes Workstation product layer. Repository-wide rules in the root `AGENTS.md` remain authoritative.

## Multi-agent shared-branch rule — ACTIVE 2026-10-13

For simultaneous agents on the current Hermes Workstation MVP, FIRST read `context/AGENT_COLLABORATION_PROTOCOL.md` and `context/workstation-hub-mvp/TEAM_BOARD.md`. All agents work in the same `C:\Github\hermes-agent` checkout on `feat/hermes-workstation-mvp-20261013`, claim disjoint files with `python workstation/scripts/multi_agent_coordination.py claim`, heartbeat progress, and release after integration. The designated integrator alone performs Git staging/commits/push and edits canonical board/policies. Never create another branch/worktree merely to fix an MVP sub-task. This changes coordination only: upstream-first Stage A, human leases, TaskRun/session authority, TDD and exact-head CI are still mandatory.


## Primary operating gate: synchronize before downstream implementation

Before editing Workstation runtime code or any upstream-owned integration point, execute
the canonical
[`UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md`](context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md).

The mandatory engineering order is:

```text
UPSTREAM PREFLIGHT
-> PIN
-> BASELINE SYNC
-> SEAM RECONCILIATION
-> BASELINE QUALIFICATION
-> TARGET CHANGE
-> TARGET QUALIFICATION
-> FINAL UPSTREAM DRIFT CHECK
```

Do not combine a stale-baseline feature implementation with later conflict resolution.
Do not begin target coding while required exact-head Workstation baseline gates are red.
A passing seam inventory does not close seams marked REMOVE; their actual authority path
must be verified.

Before editing anything under `workstation/` or any Workstation-owned integration point elsewhere in the repository, read [`context/README.md`](context/README.md) and follow its required reading order. Then inspect the current `main` code and tests for the subsystem being changed.

Do not create parallel SessionDB, Kanban, Memory, approval, or Browser state systems. Keep the upstream delta explicit and preserve the Browser/session/security invariants recorded in the Workstation context.

## Mandatory stop-and-resume handoff for unfinished Workstation missions

Whenever a Workstation implementation mission ends without **all** acceptance gates verified,
the implementing agent MUST return a single user-copyable **RESUME PROMPT** in its final
response, even if it also publishes a PR. The prompt must make the next session executable,
not instruct it to audit the repository from scratch.

The resume prompt MUST state:
- Exact repository, isolated worktree, branch, base/head commit, staged/uncommitted changes,
  and the latest remote PR URL; verify these rather than guessing them.
- Implemented behavior with source paths/symbols, and what is **not** implemented.
- RED reproduction and latest GREEN/regression/native/CI evidence, with commands,
  output counts, and any failing test by exact name (including baseline failures).
- Original invariant and the single next highest-priority reproducible failure.
- Ordered next actions, tests, source owners, security gates, dependencies, and expected
  proof. Explicitly forbid reverting user edits, inventing evidence, weakening leases,
  retrying unknown mutations, or restoring historical Kanban without scoped approval.
- Instructions to continue until qualification, and, if stopping again, to generate
  another independently usable, updated resume prompt with exact current identifiers.

Persist a factual engineering journal entry where applicable. Never claim background
continuation, a future delivery, an approved merge, or complete qualification while
CI/native evidence is missing. Prefer one precise next gate over repeating an open-ended
research plan.

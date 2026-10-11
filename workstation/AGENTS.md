# Hermes Workstation — Agent Instructions

## OPC-001 — Prefabricated operational capabilities

For recurring browser/site procedures or Agent/Workstation capability discoverability, use `context/PREFAB_OPERATIONAL_CAPABILITIES_2026-10-10.md` and `context/PREFAB_IMPLEMENTER_PROMPT_2026-10-10.md` *after* the mandatory upstream-first and canonical context reading. Reuse existing `referências/Hermes-Work-Prefabs-Plug-and-Play-v0.1` code when available; never copy private dogfood JSON/HTML into commits. Runtime changes require exact-HEAD gates. Agent toolset discovery and pre-System-2 Workstation resolution need separate evidence; neither Laya nor saved HTML can grant permissions.


This directory is the downstream Hermes Workstation product layer. Repository-wide rules in the root `AGENTS.md` remain authoritative.

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
# Hermes Workstation — Agent Instructions

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
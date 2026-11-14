# Hermes Workstation — Agent Instructions

## Retired project-local multi-agent control

The project-local P0/P1/P2 multi-agent coordinator, admission layer and Claude hooks were retired by the maintainer on 2026-10-28. The old .hermes-collab directory and engineering journals are retained as HISTORICAL evidence, not an active ownership service. Do not run removed scripts. Before editing a shared checkout, inspect Git dirty/untracked work and coordinate directly with other active writers. Direct terminal/Desktop Commander/Claude access does not enforce cross-agent claims. The separate local-mcp-bridge is not automatically connected to this Hermes checkout and does not universally fence raw writes.

## OPC-001 — Prefabricated operational capabilities

For recurring browser/site procedures or Agent/Workstation capability discoverability, use `context/PREFAB_OPERATIONAL_CAPABILITIES_2026-10-10.md` and `context/PREFAB_IMPLEMENTER_PROMPT_2026-10-10.md` *after* the relevant Workstation context reading. Reuse existing `referências/Hermes-Work-Prefabs-Plug-and-Play-v0.1` code when available; never copy private dogfood JSON/HTML into commits. Runtime changes require relevant behavior and regression evidence; exact-head upstream qualification applies only to an explicitly selected synchronization/release lane. Agent toolset discovery and pre-System-2 Workstation resolution need separate evidence; neither Laya nor saved HTML can grant permissions.


This directory is the downstream Hermes Workstation product layer. Repository-wide rules in the root `AGENTS.md` remain authoritative.

## Branch selection and multi-agent coordination

The shared-branch cycle opened on 2026-10-13 is closed. `main` is the canonical branch for current Workstation work. Treat `feat/hermes-workstation-mvp-20261013` as historical; never switch to it because this or another old document names it. A future cycle may use a different branch only when the current task or maintainer explicitly defines it. Preserve the shared checkout, inspect all dirty/untracked work and active claims before an authorized branch change, use a normal switch, and stop if Git reports a conflict. Never force, reset, or stash automatically.

For concurrent changes, inspect real current writers and coordinate explicit handoff before modifying overlapping files. Historical .hermes-collab records are retained for audit only; they are not executable protection. Preserve Browser/session authority, leases and security invariants unrelated to this retired system.


## Optional Stage A / H-079 upstream synchronization

Stage A is an **optional maintenance and synchronization workflow**, not an admission gate for local development. Agents may implement features, fix bugs, refactor and test even when upstream has moved, no new pin was selected, or Stage A/exact-head baseline qualification is pending or red. No task-scoped waiver is required merely to start coding.

For awareness, consult [the upstream synchronization status](UPSTREAM.md), [downstream delta](UPSTREAM_DELTA.md), and [the archived H-079 procedure](context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md). A dated report is useful context, not proof of live freshness. Do not require a fetch, merge, pin, CI run or synchronization report update before ordinary implementation; if status is unknown, state that rather than guessing.

When upstream synchronization is deliberately requested, keep its merge, seam reconciliation and qualification independently auditable. Do not claim a baseline or release is upstream-qualified without evidence. Continue preserving current work, Browser/session authority, security controls, scoped regression tests and all target-specific acceptance requirements. CI or release gates may still be required for the **particular deliverable**, independently of Stage A.

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

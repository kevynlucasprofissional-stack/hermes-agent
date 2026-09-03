# Post-Gate Hygiene Audit — 2026-09-02

## Scope

Audit of `main@87656baa2a6c55ce4dc2902978df7c8a68c2745e`, the single commit added after the extraordinary Mainline Consolidation Gate merge `ebbf43ba64b5412fd8159ab8a80b1d086c1dacad` and before V1 #1.5 implementation.

## Finding

Commit `87656baa...` added eight root-level files with message `Acho que são logs de uma sessão`:

- `impl4-windows-final.log`
- `impl4_h002_bare_electron_probe.ps1`
- `run_impl4_native_smoke_v9.mjs`
- `run_impl4_native_smoke_v9.ps1`
- `runtime.ts`
- `runtime_utf8.ts`
- `session.ts`
- `session_utf8.ts`

These files are not canonical Workstation source and are not required versioned evidence for the current product line.

Classification:

- `impl4-windows-final.log` — raw historical CI/session output; residue.
- `impl4_h002_bare_electron_probe.ps1` — historical Implementation 4 diagnostic pinned to branch `impl4-browser-task-lifecycle` and SHA `1ac0e0a9...`; superseded diagnostic residue.
- `run_impl4_native_smoke_v9.mjs` / `.ps1` — historical Implementation 4 harness pinned to the same superseded candidate; residue. The maintained versioned native probes are under `workstation/context/engineering-journal/probes/`.
- `runtime.ts` / `runtime_utf8.ts` — root-level copies of Browser Runtime source; non-canonical and stale relative to `apps/desktop/electron/workstation-browser-runtime.ts`.
- `session.ts` / `session_utf8.ts` — root-level copies of BrowserSessionState source; non-canonical and stale relative to `apps/desktop/electron/workstation-browser-session-state.ts`.

## Decision

Remove all eight files without rewriting the published `main` history. Preserve canonical source and maintained probes in their existing locations.

This cleanup does not reopen the product conclusions of the Mainline Consolidation Gate; it restores repository hygiene after a post-Gate accidental commit. V1 #1.5 must branch from a `main` descendant containing this cleanup before new product implementation proceeds.

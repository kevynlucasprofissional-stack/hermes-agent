# H-079.2 Pre-Change Audit

- DOWNSTREAM_BASE: `964c13361e95a49e680deb2b16479d5f85c63011`
- NEW_UPSTREAM_PIN: `118984d7a02f8a8baec11255002cbbab7c202e06`
- MERGE_BASE: `c1488ac947c9bc33fd65ec464548dc9d8edd6122`
- AHEAD (`upstream/main..origin/main`): `547`
- BEHIND (`origin/main..upstream/main`): `484`
- Integration branch: `integration/upstream-20260920-118984d7-h0792`

## Delta and affected owners

The upstream delta spans the agent runtime, provider adapters, gateway, CLI/state,
Desktop Electron and renderer owners, tests, packaging, plugin catalog, and docs. The
canonical file-level inventory is reproducible with:

```text
git diff --name-only origin/main...118984d7a02f8a8baec11255002cbbab7c202e06
```

Critical owners affected by the fresh upstream delta include `agent/*` (including
Anthropic construction and turn/finalization paths), `gateway/*`, `run_agent` adjacent
runtime paths, `hermes_state*`, `hermes_cli/*`, and `apps/desktop/*`. Browser,
Workstation native runtime, Kanban, installer, and first-party adapter seams therefore
require explicit post-merge reconciliation even where upstream has no direct
`workstation/` path.

## Seam impact

All registered core-to-Workstation seams remain in scope for strict audit. Particular
attention is required for one-batch/one-admission, BrowserControlBroker mutation
authority, bound BrowserTask routing, adapter fail-closed behavior, raw post-tool
observation, execution persistence, and H-077 verification boundaries. The registry
must be updated only from the merged candidate's actual authority paths.

## Local preservation

Pre-existing untracked `workstation/dogfood/readme.md` is user-owned and excluded from
this cycle. `test-tmp-h0771/` was observed with restricted traversal and is not modified.

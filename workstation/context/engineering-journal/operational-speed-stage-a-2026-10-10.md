# Operational speed — Stage A integration, 2026-10-10

Status: IN PROGRESS / NOT QUALIFIED. Target runtime implementation remains blocked.

Baseline: `origin/main@f21e803b3525b70ee6be2305e579c1cc1f930e74`.
Immutable upstream pin: `66605471e9f0b0832abbefaf625ce08e948ca540`.
Common ancestor: `71a2fe399bbd7a219c71f9d9fca2b313b01f2057`.
The true merge began with 55 conflicted paths. This worktree is separate from
the dirty dogfood checkout and from the RED-evidence branch.

## Reconciliation decisions and checks

- SEMANTIC_PORT: retain canonical batch admission, scoped execution, mutation
  checkpoints, BrowserTask ownership and first-party native Browser IPC while
  adopting upstream agent/tool owners and observability.
- ADOPT_UPSTREAM: retired `tools.lazy_deps` installer. The only downstream
  addition was the unused `system1.laya` table entry; no caller uses that entry.
  Preserve approved Laya extras, local noneditable source and provenance checks.
- SEMANTIC_PORT: upstream Desktop configuration/identity owners, with public
  Hermes Work identity and stable Hermes executable. Native Browser preview,
  occluder attributes, restart hydration and hybrid Kanban invalidation coexist
  with upstream preview adoption and event cursors.
- KEEP_WORKSTATION: established portrait icon assets and packaged-app smoke.
- REMOVE: the old Windows site-packages helper has no runtime caller after the
  upstream switch to probing/spawning the selected interpreter without PYTHONPATH.
- Dependency resolution RED: `uv lock` rejects the merged exact pins
  `trace-upload: huggingface-hub==1.24.0` and `system1-laya: ==1.33.0`.
  Reconcile to the already pinned Laya version 1.33.0 for both extras. Trace upload
  uses HfApi whoami/create_repo/upload_file; its behavior contracts must pass.
- Main CI failure reproduced remotely: the Workstation install command omitted
  `--extra workstation-laya`. Its correction remains separately inspectable.

Python `compileall` for agent/tools/gateway/hermes_cli/tui_gateway/workstation
exited 0 after Python conflict composition. This is syntax evidence only.

## Observed results (working candidate, not exact-head qualification)

`uv lock` resolved 329 packages after pin reconciliation. Locked `uv sync
--python 3.14 --group dev --extra anthropic --extra workstation-laya` installed
117 packages in this worktree's own venv. Upstream supports Python 3.14 at runtime;
the older requires-python floor exists only to let legacy installations update.
The root user's venv and Node installation were not replaced.

Isolated `npm ci --ignore-scripts --no-audit --no-fund` installed 1329 packages.
Desktop typecheck and production build passed. The build stamp correctly reports
the still-uncommitted candidate as dirty; this is not exact-HEAD packaged evidence.

Prepared NSIS/MSI inputs extend the existing upstream preparation/consumption
owner. RED: declaring NSIS/MSI accepted missing toolsets. GREEN: 12 packaging
contracts pass, including missing supplier, byte tampering and changed WiX
descriptor rejection without repair/download. Native installer parity remains open.

- Initial Workstation run: 892 passed, 6 failed, 4 skipped, 321.4s. Five failures
  were old named-board fixtures; explicit create_board repairs passed all five
  tests in 8.1s. The obsolete Python branding source-inspection test moved to the
  actual CJS/TypeScript owner contract, which passed.
- Durable core seams + trace upload: 344 passed, 1 skipped, 55.0s.
- BrowserTask, resources, session, admission, recovery, viewport runtime contracts:
  89 passed across nine files, 10.32s. These are contracts, not real Chromium proof.
- Product identity, screenshot monitor and native update handoff: 15 passed,
  3 platform skips. SSH reconciliation: 85 passed, 4 platform skips; explicit mux
  fixtures preserve the correct Windows no-mux runtime default.
- Strict seam inventory: 14 classified, 0 unclassified, 0 growth. Core integration
  anchors pass. These checks do not establish behavioral parity on their own.
- Native installer RED: Python 3.14 venv rejected by the former <3.14 assertion.
  Version contract reconciled to >=3.14,<3.15; full installer GREEN pending.

The audit branch `8e64b38a81adcf8a01dc2ed05aa3eb078adc9f9f` contains 23 commits
beyond the main used for Stage A, including existing HyperFrames and learning
runtime. Reconciled through true merge `88a6166`, with both sections retained in
five documentary conflicts; runtime composed automatically without conflicts.
The RED attestation reproduction remains preserved on the separate evidence branch.

## Remaining gates

Local native smoke passed: four real Electron/Chromium BrowserTasks aligned across
controller and IPC (7.0s test, 1.0m including bootstrap). The inference provider and
pages are local fixtures. This build preceded the audit-branch merge and is not
final-candidate E1 or product-economics evidence. Audit-branch Desktop typecheck passes.

Diff hygiene: remove inherited whitespace findings in code and ordinary docs;
preserve original dogfood notes and captured evidence byte-for-byte. The Windows
formatting gate explicitly excludes only those historical records, not runtime.
The intentional conflict-marker fixture constructs identical marker bytes at
runtime so diff hygiene does not misclassify its Python source as an unresolved merge.

Exact-head Actions, clean-machine installer and final native product proof remain
pending. No P0–P3 target runtime implementation
is authorized by a local focused GREEN alone. No external Trello write was made.

No product latency, token, model-call or monetary savings have been measured.

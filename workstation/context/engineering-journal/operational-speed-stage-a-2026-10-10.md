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

## Local closure attempt at code candidate 749e2f9

Code SHA: `749e2f92785fbc9bb84c0737d6cd730f55aa9aa6`. Draft PR #66:
https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/66

- Official Workstation runner: **970 passed, 0 failed, 4 skipped**, 122 files,
  565.5s with four workers. This is local regression evidence, not product latency.
- Full Electron contracts: **3556 passed, 34 failed, 138 skipped**, 308.81s.
  Rechecks with the prepared Python 3.14 and Windows PowerShell module path
  distinguish environment problems from incomplete upstream fixture composition.
  Repaired fixtures preserve production publication, artifact and path checks.
  Native SDK side-by-side packaging proof passes after copying required modules;
  channel manifest recorder contracts pass using their explicit version sidecar.
- Full UI: **10753 passed, 3 failed, 1 skipped**, 938.95s. RED failures were six
  missing translations and two host-locale expectations inconsistent with the
  established downstream en-US transcript format. GREEN: all 87 tests in the
  three affected files pass (6.82s); the full UI suite was not rerun after repair.
- Desktop typecheck and production build pass at this code candidate. Build
  stamp records the clean code SHA; renderer build 9.94s is a build duration,
  not an application performance measurement.
- Integrated native smoke at clean code `749e2f9`: **1 passed**, four real
  Electron/Chromium BrowserTasks aligned across controller and IPC, 7.0s test /
  31.0s including bootstrap. Local pages and mock inference provider; this
  supersedes the pre-audit smoke for this narrow contract, not full product E1.
- Desktop failures still open: checkout source handoff times out at 30s after
  fixing reentrant fixture transport; repair-lock race times out; update-marker
  lock cleanup reports EBUSY; Windows remote probe rejects its configured path;
  native PTY cleanup reports EPERM; symlink tests lack Windows symlink privilege;
  three simulated-Linux entry config tests fail on Windows; three Git review
  tests return empty/null. A diagnostic direct Git call confirmed inherited
  EDITOR rejection by simple-git, but clearing editor variables did not close
  those tests. Signing verification also timed out in the prepared environment.
  None of these failures is relabeled VERIFIED or silently skipped.
- Controlled Trello benchmark completes seven local fixture scenarios. The
  corrected known 12-item path reports 2 mock-provider calls, 53 tool calls,
  0 replayed mutations, and 1 cache hit in the known case. Tokens, cache tokens
  and monetary cost are null. `baseline_modeled` uses 14 modeled calls; it is
  not a measured before-run and cannot establish savings or calls avoided.

GitHub accepted pushes but rejected dispatch of both `workstation-ci.yml` and
`workstation-browser-windows.yml` at `921e224` with **HTTP 422: Actions has been
disabled for this repository**. Read-only Actions permissions reported enabled
and workflows active; that does not override the actual dispatch rejection.
Repository/account-side investigation is required. The user has been informed.
No exact-head CI ran, no gate exception was granted, and no main merge occurred.
Final upstream fetch after local qualification still resolves to the fixed pin
`66605471e9f0b0832abbefaf625ce08e948ca540`; no second upstream merge was started.

| FASE | BASE_SHA | HEAD_SHA | ARQUIVOS | RED | GREEN | EVIDÊNCIA NATIVA | LATÊNCIA | CHAMADAS LLM | CUSTO | BLOQUEIOS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Stage A integration | f21e803 | 749e2f9 | upstream merge + baseline fixture/CI/docs reconciliation | dependency conflict, installer range, 34 Electron + 3 UI failures | Workstation 970; focused UI 87; typecheck/build; SDK fixture | Electron smoke recorded separately below; full E1/E2/E3 open | product UNKNOWN | real UNKNOWN; benchmark provider mocked | UNKNOWN | Actions HTTP 422, remaining Desktop failures, clean-machine installer, H-079 |

P0.2 RED evidence remains on separate commit `d6ba10c7`: 7 passed / 2 failed
demonstrating forged DIRECT attestations. It has not been hidden inside the
baseline suite. Authenticated correction and P0–P3 remain pending the mandatory
qualified-baseline gate. Original dogfood files and concurrent user work remain
outside this isolated branch.

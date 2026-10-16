# One-click Windows bootstrap — 2026-10-15

## Follow-up de usuário 2026-10-16 — log real falha no Record (KNOWN INCIDENT / NOT YET FIXED)
O estado `NOT WINDOWS-QUALIFIED` registrado acima para PR #90 era procedente: merge para `main` ocorreu 2026-10-15 sem aquela evidência. Windows com Python 3.14 e Node 26.7.0 validou upstream, completou `uv pip install -e .`, `npm ci` (1.342 pacotes; 39 audit findings), importou `hermes_cli`, mas falhou `-Action Check` e `-Action Record` com `Could not validate cached install: Checked 77 packages ...`. O bootstrap impediu Doctor/start. Causa provável: native stderr do `uv pip check` transformado em erro sob `$ErrorActionPreference="Stop"` no Windows PowerShell 5.1; requer reprodução discriminante (uv exit 0 vs não zero).
O código confere acoplamento de todos os manifests em único fingerprint: qualquer drift implica reinstalar editable Python **e** npm workspaces. Decisão D-046 / KI-044: P0 tratar saída informativa separadamente do status real; P1 fingerprints/stamps Python+Node separados e reparo incremental; CI Windows exato + H-079 before release. [Kit com scripts completos](../oneclick-bootstrap-2026-10-16/README.md), [prompt](../oneclick-bootstrap-2026-10-16/IMPLEMENTER_PROMPT.md). **Esta nota não relata implementação do fix nem testes nativos passados.**


Status: **IMPLEMENTED ON ISOLATED BRANCH / NOT WINDOWS-QUALIFIED / NOT READY FOR MAIN**.

## Scope and baseline

- Downstream: `kevynlucasprofissional-stack/hermes-agent`.
- Branch: `fix/oneclick-bootstrap-windows-prerequisites-20261015` based on `main@b80d10a4d6d4536b65df52eb4e011ad8d5eef672`.
- Upstream tip observed for preflight: `NousResearch/hermes-agent@73b9f2af7b87a619f42396710c332be04353aef2`.
- Historical adopted pin checked as ancestor of downstream main: `66605471e9f0b0832abbefaf625ce08e948ca540`.
- The repository's H-079 Stage A synchronization, baseline qualification, seam reconciliation, and final drift classification **were not executed for this change**. Existing exact-head checks were not a complete green Windows release receipt. Promotion remains blocked until those are completed; this draft is not an exception or release authorization.

## Behavior implemented

- `START-HERMES-WORKSTATION.bat` enters one persistent parent PowerShell session.
- `workstation/scripts/oneclick_bootstrap.ps1` hashes upstream lock/toolchain/bootstrap inputs; if unchanged *and* the managed environment is healthy, bypasses upstream package installation. Otherwise starts `setup-hermes.ps1 -RuntimeOnly` in a **child PowerShell**, isolating its `exit 0`, then probes and applies the PM-composed environment to the parent launcher session.
- The existing `setup-hermes.ps1` / `pm/lock.json` are the source of truth for Python 3.14, Node 26, npm, Git, uv and other required/optional upstream tools. PM stages verified downloads without requiring a global Python, Node or Git install. Source lockfiles are not regenerated.
- The Workstation's existing `oneclick_dependency_gate.ps1` is consulted next. Missing/changed inputs cause `workstation/install.ps1` to create its dedicated `.venv`, install editable Hermes and run `npm ci`; on a healthy stamp, it runs the installer in validation-only mode. An install stamp is recorded **only after** dependency health checks pass.
- Python health requires the 3.14 interpreter, installed `hermes-agent` distribution and real runtime imports. If `uv` is available, `uv pip check` checks the installed Workstation dependency graph.
- npm workspaces can hoist Electron. The gate accepts either valid location but requires `dist/electron.exe` and root CLI shims before skipping installation.
- Strict Doctor and Desktop launcher run in child PowerShell processes inheriting the parent PM-composed PATH. The environment is scoped to the launcher process, not persisted to system PATH or the registry.
- Errors return non-zero and preserve diagnostic output; the .bat pauses on failure. Existing runtime/profile/browser state is not deleted.

## Qualification still required (Windows native)

1. PowerShell parser check (Windows PowerShell 5.1); clean checkout on Windows 11 x64 without system Python/Node/Git/uv; verify managed downloads from pinned SHA256 artifacts, environment checks, `npm ci`, Doctor and an actual Electron window.
2. Repeat unchanged: verify both upstream and Workstation dependency stages are skipped while the desktop still opens.
3. Delete one installed Python dependency; launch and confirm repair. Delete an npm workspace shim or Electron binary; launch and confirm repair.
4. Change a dependency lock input in an isolated disposable checkout; verify invalidation and installation **without source-file modification**.
5. Exercise an existing Python 3.14 .venv with no pip; ensure the uv path works, and exercise an interrupted download / unavailable network with explicit non-zero failure and successful retry.
6. Check Windows ARM64 if a runner/device is available, non-ASCII profile paths, existing browser profiles, long paths and a checkout without `.git`.
7. Run focused Workstation tests, desktop/native Electron E2E and exact-head Windows GitHub Actions qualification. Execute H-079 Stage A and document the exact chosen upstream pin and drift before promotion.

Constraints: a .bat is Windows-only; PowerShell/Windows system components and an internet connection for uncached artifacts are needed. Security restrictions, unsupported CPU/OS, external service downtime and optional tool failures cannot be bypassed automatically. A one-click **fresh-install success** must not be claimed before Windows evidence.

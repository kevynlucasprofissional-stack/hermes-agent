# One-Click Windows reliability — implementation kit (2026-10-16)

**Status: DOCUMENTED / IMPLEMENTATION ASSETS STAGED / NOT APPLIED TO RUNTIME / NOT WINDOWS-QUALIFIED.**
Baseline inspected: `main@d2ab172a43b1d4719dbf9572078fb4b5fda5da0c`. Source incident: user's Windows 11 terminal, Python 3.14, Node 26.7.0, npm, Git, 77 uv packages and 1,342 npm packages. Pull request [#90](https://github.com/kevynlucasprofissional-stack/hermes-agent/pull/90) was merged 2026-10-15 despite its own qualification checklist remaining open.

## Scope and source-of-truth

| Artifact | Source replacement / use | Status |
|---|---|---|
| [oneclick_dependency_gate_p0.ps1](oneclick_dependency_gate_p0.ps1) | Full replacement for `workstation/scripts/oneclick_dependency_gate.ps1`, initial hotfix ONLY | Draft, not deployed |
| [oneclick_dependency_gate_v2.ps1](oneclick_dependency_gate_v2.ps1) | Full replacement for same gate, split Python/Node readiness | Draft, not deployed |
| [install_v2.ps1](install_v2.ps1) | Full replacement for `workstation/install.ps1`, selective installer switches | Draft, not deployed |
| [oneclick_bootstrap_v2.ps1](oneclick_bootstrap_v2.ps1) | Full replacement for `workstation/scripts/oneclick_bootstrap.ps1`, selective repair/record flow | Draft, not deployed |
| [IMPLEMENTER_PROMPT.md](IMPLEMENTER_PROMPT.md) | Paste into coding agent after the documentation branch is fetched | Operating instructions |

These source-based drafts were generated against **one exact baseline**. The implementer must compare the target source before transplant; never replace a newer file blindly. The v2 drafts are a code starting point and **not proof** that all Windows/CI tests pass.

## Diagnosis: observed versus inferred

**Observed:** the existing `workstation/install.ps1` completed editable `uv pip install -e .` and `npm ci`, and `hermes_cli` import passed. The dependency gate failed both before installation and during `-Action Record`, showing `[deps] Could not validate cached install: Checked 77 packages in 44ms` (then 6ms). `oneclick_bootstrap.ps1` treats any Check failure as a full Workstation repair and never reaches Doctor/start after Record failure. `npm ci` processed 1,342 packages, reported 39 vulnerabilities (8 low, 11 moderate, 18 high, 2 critical); warnings were **not** the immediate gate failure.

**Strong code-based hypothesis (requires native reproduction):** the gate's `$ErrorActionPreference = "Stop"` + `& uv pip check --python $VenvPython 2>$null` traps successful stderr from uv as a PowerShell 5.1 error before `$LASTEXITCODE` can be evaluated. The output `Checked 77 packages...` is consistent with success but does **not** prove an exit code of zero in the user's environment.

**Additional confirmed architectural inefficiency:** the gate currently uses **one composite fingerprint** across `pyproject.toml/uv.lock`, JS manifests and Node/npm. Any fingerprint change or probe failure causes both `uv pip install -e .` and `npm ci`; Python-only drift therefore rebuilds the JS workspace, and JS-only drift reinstalls editable Python.

## Decisions D-046 and issue KI-044

1. **Readiness not installation.** Healthy, unchanged warm start must validate offline and run Desktop without `uv pip install`, `npm ci` or package registry access. Missing/dirty/broken components follow explicit, scoped repair.
2. **Separate Python and Node fingerprints/stamps.** Python domain owns `pyproject.toml`, `uv.lock`, interpreter; JS domain owns npm manifests, npm lock and Node/npm runtime. A source-only edit is **not** a dependency change. Versions/manifest changes must invalidate their respective domain.
3. **A real native nonzero exit is a failure, stderr text alone is not.** Preserve diagnostics for an actual nonzero `uv pip check` and never bypass graph validation to make an environment look healthy.
4. **Repair only the failed domain.** Two independently recorded stamps; after failed repair, preserve healthy domain and user data. Do not run `npm audit fix --force`, delete node_modules/venv/profiles, or lower pins as a shortcut.
5. **Preserve user state and source cleanliness.** Reuse `HERMES_WORKSTATION_HOME` and existing Runtime/Browser path; maintain strict Doctor. Never silently mutate tracked checkout.
6. **Qualification before promotion.** Native Windows PowerShell 5.1 and Windows 11 actual launch, offline second run, negative fault injections, exact-head CI, H-079 upstream-first and seam check. No release claim without evidence.

## Recommended two-phase integration order

### P0 — prove and eliminate the false-negative

1. Capture `uv pip check --python .venv/Scripts/python.exe` on Windows PowerShell 5.1, record true `$LASTEXITCODE`, stdout and stderr. Reproduce original `-Action Record` failure in controlled environment; if `uv` returns real nonzero, diagnose actual package conflict rather than mask it.
2. Replace `workstation/scripts/oneclick_dependency_gate.ps1` with [P0 full file](oneclick_dependency_gate_p0.ps1), after exact source match. Run `-Action Record`, then `-Action Check`; both must exit 0 on a healthy installation. `Record` must never succeed for a deliberately broken Python graph.
3. Warm-launch twice, capture no-install expectation. Preserve logs as RED/GREEN and journal result. P0 must not introduce new flags or restructure the installer.

### P1 — split validation and repair

1. Start from the now-qualified P0 source; check semantic equivalence of draft [v2 gate](oneclick_dependency_gate_v2.ps1), adapt with actual native evidence. Copy it to `workstation/scripts/oneclick_dependency_gate.ps1`.
2. Apply [v2 installer](install_v2.ps1) to `workstation/install.ps1`: new `-SkipPythonDependencies` and `-SkipNodeDependencies`, while preserving `-SkipDependencies`, source validation and checkout cleanliness.
3. Apply [v2 bootstrap](oneclick_bootstrap_v2.ps1) to `workstation/scripts/oneclick_bootstrap.ps1`: call `CheckPython` and `CheckNode`; repair and `RecordPython`/`RecordNode` independently.
4. **Required hardening before release:** migrate a valid legacy composite stamp without needless reinstall **only after verifying its exact original hash and both domain health probes**; if an old stamp is absent/mismatched, first-run repair is allowed but must be reported. Ensure `require.resolve` operates in the desktop workspace, not just repo root. Validate a broken `uv`/interpreter/Node command produces a transparent diagnostic and nonzero exit. The v2 draft is not considered production-ready until this hardening and native tests are done.
5. Verify the caller working directory for `node -e require.resolve`; the entrypoint `oneclick_bootstrap.ps1` uses `Push-Location $Root`. Any independent gate invocation from another directory must resolve relative to `$Root`, not assume the current directory.
6. Only after parity proof consider `uv sync --locked` and specific Workstation Laya profile parity as a **separate** package-management change. The current installer uses `uv pip install --python ... -e .`; do not falsely label it locked. Do not remove npm dev packages blindly: `npm run dev --workspace apps/desktop` needs Vite/TypeScript/concurrently, and the root monorepo contains other workspaces.

## RED/GREEN and fault matrix

| Case | Expected result |
|---|---|
| Windows PS5.1, uv prints normal status to stderr, exit 0 | Healthy `Check` and `Record` pass; no false NativeCommandError |
| uv exits nonzero due to broken dependency graph | Check and Record fail with real uv reason |
| Unchanged warm start, offline/registries blocked | Neither `uv pip install` nor `npm ci`; Doctor and real Electron UI launch |
| `pyproject.toml` / `uv.lock` changed in disposable checkout | Only Python repair and Python stamp |
| npm `package-lock.json` changed in disposable checkout | Only Node repair and Node stamp |
| Python package removed / .venv unhealthy | Only Python repair or actionable fail, no Node reinstall |
| Electron executable/shim missing | Node repair only |
| Existing legacy success stamp | Safe verified migration; no unnecessary full reinstall |
| No stamp, ambiguous stale dependencies | Fail closed / repair; never invent success |
| Native interruption halfway through repair | No healthy stamp for failed domain; retry safe |
| Two consecutive double-click launches | No repeated install; source tracked files and user Browser profile unchanged |

## Engineering cautions

- Always test on real `powershell.exe` (Windows PowerShell 5.1), not only `pwsh` or a mocked stdout runner.
- A healthy `hermes_cli` import alone does not prove the editable distribution or dependency graph; retain distribution metadata + `uv pip check`.
- `npm ci` is legitimate during true fresh install, but 1,342 packages does not establish that every package is necessary in the **runtime**. Audit scope before slimming dependencies.
- The 39 npm audit findings are a separate security triage: inspect `npm audit --json` and `npm audit --omit=dev` with reproducible affected packages and scope; do not conflate with boot failure.
- Avoid concurrent double-click `npm ci`/Python repairs: serialize install/record if the native race can be reproduced; do not auto-delete locked files.
- Do not change `START-HERMES-WORKSTATION.bat`, `workstation/start.ps1`, `workstation/doctor.ps1`, PM/lockfiles merely to bypass the gate. Changes to these require their own failing evidence and scope approval.

## Release proof

Attach RED/GREEN logs, exact Git commit/branch, host Windows build, PowerShell version, Python/Node/npm/uv versions, both warm-start and failure-injection outcomes, cleanliness diff, native Electron proof, exact-head CI URL, upstream pin/seam classification, and disposition of remaining known issues. Until then: **NOT WINDOWS-QUALIFIED / NOT READY FOR MAIN**.

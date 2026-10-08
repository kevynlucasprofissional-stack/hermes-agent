# Workstation Bootstrap & Startup Reliability — 2026-10-07

**Status:** ACCEPTED DESIGN / IMPLEMENTATION REQUIRED  
**Target branch:** `workstation/laya-direct-system1`  
**Scope:** one-click Windows dogfood, dependency preparation, warm-start behavior, Laya environment parity.

## Incident and diagnosis

A normal one-click dogfood start failed before Hermes Desktop or System-1/Laya runtime code executed:

```text
START-HERMES-WORKSTATION.bat
-> workstation/install.cmd
-> workstation/install.ps1
-> uv pip install --python .venv/Scripts/python.exe -e .
-> GET https://pypi.org/simple/pillow-heif/
-> 3 retries / ~124.7s
-> timeout
-> install aborts
-> launcher aborts
```

This is **not a Laya decision-runtime failure** and not a Python 3.13 compatibility failure.

Observed repository facts:

- `START-HERMES-WORKSTATION.bat` always runs the install phase before doctor/start.
- `workstation/install.ps1` reuses an existing healthy `.venv`, but unless `-SkipDependencies` is passed it still runs `Install-HermesEditable`.
- With `uv` present, that path runs `uv pip install --python <venv-python> -e .`.
- The same install phase also runs `npm ci` unconditionally.
- `pillow-heif` is a normal core dependency on both `main` and the Laya branch.
- The branch `uv.lock` resolves `pillow-heif==1.5.0` and contains a CPython 3.13 Windows x64 wheel.
- `workstation/install.ps1` is identical between `main` and `workstation/laya-direct-system1`; the network-coupled startup defect was not introduced by Laya.
- The Laya branch adds `system1-laya` / `workstation-laya` extras, but the local one-click install path does not request them.
- H-081 CI already uses `uv sync --locked --python 3.11 --extra dev --extra workstation-laya`.
- H-081 closure evidence also uses `uv sync ... --extra workstation-laya`.

Therefore the branch has **two distinct bootstrap defects**:

1. **Warm-start network coupling:** a healthy previously prepared environment can fail to start merely because PyPI or npm registry access is slow/unavailable.
2. **Local/CI environment parity gap:** the branch's one-click local install path does not explicitly install the `workstation-laya` profile that H-081 qualification uses.

## Architectural decision

> **Dependency preparation is not application startup. A healthy Workstation warm start must be able to reach Desktop without contacting package registries.**

The one-click path may still validate local source/integration invariants on every launch. It must not resolve or reinstall dependencies unless local evidence says the prepared environment is absent, stale or broken.

## Required runtime split

```text
ONE-CLICK
  |
  +-> local source/integration validation (offline)
  |
  +-> environment readiness check (offline)
        |
        +-> HEALTHY + CURRENT
        |     -> skip Python dependency sync
        |     -> skip npm ci
        |
        +-> MISSING / STALE / BROKEN
              -> explicit repair/bootstrap path
              -> uv sync --locked with required Workstation profile
              -> npm ci only when Node workspace preparation is required
  |
  +-> doctor (validation, not package resolution)
  |
  +-> start Desktop
```

## Python environment contract

For this branch, the supported bootstrap/repair path must use the project lock rather than treating the repository as an unconstrained editable pip target.

Preferred shape:

```text
uv sync --locked --python <supported-python> --extra workstation-laya
```

Add `--extra dev` only where the test/development contract requires it. Normal product startup should not pull the full development profile merely to launch Desktop.

The implementation must preserve:

- repo-local isolated `.venv`;
- editable Hermes source semantics where supported by `uv sync`;
- supported Python `>=3.11,<3.14`;
- strict vendored-Laya provenance when the Workstation Laya provider is expected;
- no fallback to unrelated global/PyPI Laya;
- clean checkout / no tracked-source mutation;
- existing core-integration, component-lock and license validation.

## Warm-start readiness proof

The fast path must be deterministic, local and side-effect-light. It must prove enough to avoid false healthy states.

At minimum account for:

- supported `.venv` Python exists;
- `import hermes_cli` succeeds from that environment;
- prepared Python dependency state corresponds to the current dependency contract (`pyproject.toml` + `uv.lock` + required Workstation profile), using a deterministic install-state fingerprint or equivalent local proof;
- on this branch, `import laya` resolves from the approved vendored subtree and strict provenance passes;
- Node workspace preparation corresponds to the current `package-lock.json` / workspace contract;
- required local runtime files are present.

Do **not** make a registry request merely to decide whether the environment is current.

Ordinary source-code edits should not force dependency resolution when dependency metadata/locks did not change.

## Cold/repair behavior

Network access is legitimate when:

- `.venv` is absent;
- required packages/profile are missing;
- dependency metadata/lock changed;
- strict local health checks prove the environment broken;
- the user explicitly requests install/repair/update.

Registry timeout/retry controls such as `UV_HTTP_TIMEOUT` / `UV_HTTP_RETRIES` are useful mitigation for the repair path, but they are **not** the architectural fix for warm-start coupling.

Failure messages must distinguish:

- application/runtime failure;
- dependency environment missing/stale;
- PyPI/network failure;
- npm/network failure;
- Laya profile/provenance failure.

## Node environment contract

`npm ci` is dependency preparation, not warm startup.

Required behavior:

- unchanged healthy workspace -> no `npm ci`;
- missing/stale/broken workspace -> `npm ci`;
- package-lock/workspace dependency change -> `npm ci`;
- normal offline warm start -> no npm registry requirement.

## Required implementation order

```text
1. add RED regression tests for current warm-start behavior
2. define local Python + Node environment readiness/fingerprint contract
3. switch Python repair/bootstrap to uv sync --locked
4. make branch-local Workstation profile include workstation-laya
5. implement ensure-environment fast path
6. skip uv sync and npm ci on healthy unchanged warm starts
7. keep explicit install/repair commands available
8. make doctor validate the resulting state without package resolution
9. update launcher/readmes/help/error classification
10. run focused installer/bootstrap tests
11. run H-081 real-Laya/provenance qualification
12. run full affected Workstation/Desktop regressions
13. prove offline warm-start dogfood
14. exact-head CI + final drift classification
```

## Mandatory acceptance cases

1. **Healthy warm start, network blocked:** one-click reaches Desktop without PyPI/npm access.
2. **Healthy warm start, PyPI unavailable:** no failure because Python sync is not attempted.
3. **Healthy warm start, npm registry unavailable:** no failure because `npm ci` is not attempted.
4. **Clean machine / no `.venv`:** bootstrap runs lock-based sync and installs the required Workstation Laya profile.
5. **Laya missing or wrong provenance:** readiness fails and repair path restores/rejects it; never silently continues with an unrelated package.
6. **`uv.lock` or relevant dependency metadata changes:** readiness becomes stale and sync runs.
7. **`package-lock.json`/workspace dependency state changes:** Node readiness becomes stale and `npm ci` runs.
8. **Ordinary source edit only:** dependency sync does not run.
9. **Broken supported venv:** repair/failure is explicit and actionable.
10. **Checkout cleanliness:** install/start creates no unignored source artifacts or tracked edits.
11. **Current H-081 gates remain green:** vendored provenance, real checkpoint influence, no-System2 path, supersession, learning, receipts and telemetry do not regress.
12. **One-click does not double-install:** dependency preparation occurs at most when readiness requires it.

## Non-goals

- removing `pillow-heif`;
- weakening dependency pins/lock discipline;
- bypassing strict Laya provenance;
- using `-SkipInstall` blindly without readiness proof;
- making doctor mutate dependency state;
- hiding cold-install network failures;
- broad package-management redesign outside Workstation startup needs.

## Canonical principle

> **Warm start should validate what is already prepared; bootstrap should prepare what is missing. Conflating the two turns external registry availability into an application availability dependency.**

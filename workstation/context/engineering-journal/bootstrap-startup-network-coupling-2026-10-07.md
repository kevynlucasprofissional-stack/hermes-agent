# Bootstrap/startup network coupling investigation — 2026-10-07

**Branch:** `workstation/laya-direct-system1`  
**Classification:** VALIDATED  
**Product code changed in this investigation:** no; documentation/implementation plan only.

## Hypothesis

The observed one-click failure is caused by startup being coupled to dependency installation, not by Laya/System-1 runtime execution or Python 3.13 incompatibility.

## Confirming evidence

- Failure occurs in `workstation/install.ps1` during `uv pip install ... -e .`, before Desktop start.
- Exact failing request: PyPI simple index for `pillow-heif`; retries terminate on timeout.
- `uv.lock` contains `pillow-heif==1.5.0` with a CPython 3.13 Windows x64 wheel.
- `pillow-heif` exists in both main and branch dependency metadata.
- `workstation/install.ps1` has the same blob on `main` and the Laya branch.
- One-click always calls install; existing `.venv` does not suppress `uv pip install`.
- Install also runs `npm ci`, creating an equivalent warm-start registry dependency on the Node side.
- Branch CI uses `uv sync --locked --extra workstation-laya`; local one-click install does not request that profile.

## Refuting evidence that was looked for

The following would have refuted the hypothesis but was not observed:

- missing CPython 3.13 wheel for the locked HEIF package;
- Laya import/provenance exception before the package request;
- branch-specific modification to `install.ps1`;
- System-1 provider execution before the failure.

## Result

The hypothesis is **VALIDATED**.

The timeout is the trigger, but the product defect is architectural:

```text
normal warm start
-> unconditional dependency preparation
-> external registry becomes startup dependency
```

A second branch-specific gap is also validated:

```text
H-081 qualification environment
= uv sync --locked + workstation-laya

local one-click environment
= uv pip install -e .
```

This creates local/CI parity risk even when the registry is healthy.

## Decision / next experiment

Implement the canonical contract in
[`../WORKSTATION_BOOTSTRAP_STARTUP_RELIABILITY_2026-10-07.md`](../WORKSTATION_BOOTSTRAP_STARTUP_RELIABILITY_2026-10-07.md).

Next discriminating experiment:

> With outbound package-registry access blocked and an unchanged healthy prepared environment, the one-click launcher must reach Desktop without executing Python or Node dependency installation.

Then mutate `uv.lock`/dependency state in an isolated fixture and prove the same readiness layer correctly transitions to repair/bootstrap instead of falsely fast-pathing.

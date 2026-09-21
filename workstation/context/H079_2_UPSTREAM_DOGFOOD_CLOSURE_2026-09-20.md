# H-079.2 — Upstream Re-adoption + Dogfood Installer Closure

Date established: 2026-09-20  
Status: **ACTIVE CORRECTIVE CYCLE — BLOCKS NEW DOWNSTREAM FEATURE WORK**  
Parent policy: H-079 Upstream-First Change Gate  
Discovery baseline: `main@964c13361e95a49e680deb2b16479d5f85c63011`

## Executive finding

Current `main` has strong core Workstation evidence, but H-079 is not closed.

Three facts must be carried together:

1. **Core Workstation is green at the exact current main head**: 743 Workstation tests passed, 327 durable core-seam regressions passed, canary passed, and core-patch dry-run passed.
2. **The latest attempted upstream refresh did not reach `main`**: PR #40 merged `8d153b26...` into `integration/upstream-20260920-8d153b26-h0791`, not into `main`. The latest upstream pin actually ancestral to `main` remains `c1488ac947...`.
3. **The one-click dogfood installer still fails on current `main` when an existing supported `.venv` has no pip**. The installer accepts the venv and later unconditionally executes `python -m pip install -e .`, producing `No module named pip`.

The installer fix and the missing H-077 negative regression already exist on the integration branch, but are not ancestors of `main`. They are semantic source material for the next cycle, not a branch that should be merged wholesale after upstream has moved.

## Exact observed repository state

```text
downstream main:
964c13361e95a49e680deb2b16479d5f85c63011

latest upstream main observed:
641f7c810449d9af5c21b0a5ee33b29b192b4117

downstream vs latest upstream:
ahead: 547
behind: 622
merge-base: c1488ac947c9bc33fd65ec464548dc9d8edd6122

latest upstream pin actually ancestral to main:
c1488ac947c9bc33fd65ec464548dc9d8edd6122
```

The next code-changing intervention must begin with a fresh `upstream/main` fetch and a newly selected immutable pin. The observed SHA above is evidence, not a future hard-coded pin.

## Useful off-main work that must be re-adopted semantically

Integration branch: `integration/upstream-20260920-8d153b26-h0791`.

### Upstream refresh

`3db94236cf103841473cf94d8577626d181b5e8b` — `merge(upstream): refresh H-079 baseline to 8d153b26 with semantic conflict resolution`.

This merge is valid inside the integration branch, but `8d153b26...` is not an ancestor of current `main`.

### Dogfood installer fix

`90dbc446182362cc929e54cd1333e64d9532f37b` — `fix(workstation): self-heal pipless dogfood venv installs`.

Target behavior:

```text
existing supported .venv
  -> if uv exists: uv pip install --python <venv-python> -e .
  -> else if pip exists: python -m pip install -e .
  -> else: python -m ensurepip --upgrade -> verify pip -> pip install -e .
```

### H-077 negative regression

`a0efd05a9424b2f770a437fa3f5083876ae13547` — `test(guardrails): prove browser ACK is not external progress`.

Required invariant:

```text
browser_click -> {"ok": true}
without actual_delta=True
!= verified external progress
```

### Pipless-vend regression fixture

`120165eb1c7e7b38ffdbeeca5256aaf2a8dafde1` — `test(workstation): cover pipless existing venv dogfood install`.

The fixture intentionally creates `python -m venv --without-pip .venv` and exercises the real install path.

## Current dogfood failure on main

Observed one-click flow:

```text
Using existing isolated Python environment: C:\\Github\\hermes-agent\\.venv
Installing Hermes into .venv (editable mode)...
C:\\Github\\hermes-agent\\.venv\\Scripts\\python.exe: No module named pip
Hermes Python installation failed with exit code 1.
```

Current `workstation/install.ps1` validates the venv Python version, returns early, and later assumes pip exists. A valid Python venv and a pip-equipped venv are not equivalent, especially for uv-managed environments.

## Windows qualification status

The evaluated Windows workflow has strong positive product evidence: install, dependency audit, doctor, production build, reconnect soak, Dashboard cross-engine smoke, unpacked package, packaged GUI E2E, H013 integrated load, Browser foundation, BrowserSession restart, native Browser reconnect, and headless backend reconnect all passed.

The workflow still ended red because POSIX/macOS-specific tests were executed on Windows, including macOS media/TCC expectations, `/bin/sh`-based managed updater tests, and POSIX `lib/pythonX.Y/site-packages` expectations. This supports a cross-platform test-mismatch diagnosis, but it does not make the exact Windows release gate green.

## Anthropic integration closure

The Workstation CI correctly installs `--extra anthropic`, but the routing contract test `test_anthropic_messages_profile_resolves_to_messages_adapter` still mocks `agent.anthropic_adapter.build_anthropic_client`. This is acceptable as a unit test of provider routing, but it is not by itself an integration proof that the installed SDK can be constructed through the real adapter path.

H-079.2 should preserve the unit test and add at least one no-network integration contract that uses the installed Anthropic SDK and the real `build_anthropic_client` construction path with a dummy credential, asserting the resulting adapter/client type and configuration without issuing an API request.

Do not convert Anthropic into a core dependency; keep it an optional extra and install that extra only in the CI lanes that exercise it.

## Current qualification interpretation

```text
CORE WORKSTATION QUALIFIED AT EXACT HEAD: YES
UPSTREAM-FRESH BASELINE: NO
DOGFOOD INSTALLER QUALIFIED: NO
WINDOWS RELEASE GATE GREEN: NO
H-079.2 CLOSED: NO
READY FOR NEW DOWNSTREAM FEATURE WORK: NO
```

At discovery time, general CI and Nix for the exact head were still pending. Historical green receipts never transfer automatically to later heads.

## Required H-079.2 execution order

```text
1. fetch origin + upstream
2. record exact main/upstream/merge-base/ahead/behind
3. choose one fresh immutable upstream pin
4. branch from current main
5. true-history merge the new upstream pin
6. resolve conflicts semantically
7. rerun/reclassify first-party seams
8. re-adopt the pipless-venv installer behavior
9. restore the pipless regression fixture
10. restore the H-077 negative ACK-without-delta test
11. close Windows cross-platform test mismatches without hiding failures
12. full Workstation + Desktop/Browser qualification
13. exact-head GitHub Actions
14. final upstream drift classification
15. PR to main
16. merge only after required gates are green
```

Do not merge the old integration branch wholesale into current `main`; upstream has moved substantially and H-079 requires a fresh baseline first.

## Installer acceptance contract

A clean result proves: no venv -> create/install; existing venv with pip -> reuse; existing pipless venv with uv -> install through `uv pip`; existing pipless venv without uv -> `ensurepip` then install; broken/unsupported venv -> explicit failure/remediation; installer never dirties repository source.

## H-077 acceptance contract

Keep both directions explicit:

```text
{"ok": true} without actual_delta=True -> MUST NOT count as verified external progress
trusted/observed actual_delta=True -> MAY reset replay/progress state
```

Do not use the tool name itself as evidence that external state changed.

## Platform-test acceptance contract

Do not disable the Windows workflow or globally skip Desktop platform tests. Platform-specific contracts must use platform-correct fixtures/conditions; portable logic must remain tested on Windows; and the Windows release gate must be green before H-079.2 closure.

## Promotion rule

H-079.2 closes only when one exact candidate head simultaneously has: fresh upstream pin as ancestor; behind selected pin = 0; current seam audit; pipless dogfood regression green; positive and negative H-077 delta tests green; full Workstation green; Desktop/Browser gates green; Windows Browser green; general CI/Nix/Docker/required checks green; final upstream drift classified; and canonical docs/registry synchronized.

Anything less is **NOT READY FOR MAIN / NOT READY FOR NEW FEATURE WORK**.

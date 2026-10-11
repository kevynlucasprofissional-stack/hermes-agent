# Operational speed preflight — 2026-10-10

**Status: BLOCKED at preflight; evidence and regression tests only.** This records the operational-speed handoff preflight. No runtime implementation, product baseline measurement, native E1/E2/E3 run, or live Trello write was performed.

## Baseline and scope

- Audit branch/head: `codex/operational-speed-evidence-20261010` / `8e64b38a81adcf8a01dc2ed05aa3eb078adc9f9f`.
- Downstream `main`: `f21e803b3525b70ee6be2305e579c1cc1f930e74`.
- Selected immutable upstream pin: `NousResearch/hermes-agent@66605471e9f0b0832abbefaf625ce08e948ca540`; merge-base: `71a2fe399bbd7a219c71f9d9fca2b313b01f2057`.
- At observation, `main` was 857 commits ahead and 10,899 behind the selected pin.
- Required baseline Workstation CI run [37826432518](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/37826432518) failed `contracts`: 7 failures with `ModuleNotFoundError: laya`; 893 passed and 2 skipped. `core-patch` was green; durable/replay were skipped. The audit head had no runs in the inspected `gh run list` results.
- Stage A remains a separate active merge in `operational-speed-stage-a-20261010` (`HEAD=f21e803b`, `MERGE_HEAD=66605471...`); it began with 55 unresolved paths and is being reconciled separately. This entry does not claim Stage A resolved or qualified.
- The audit branch seam check reported 14 classified, 0 unclassified, 0 growth, 1,013 edge seams; exit code 0.

## Preflight experiment and result

The official native Windows runner was invoked against the focused qualification-attestation tests:

```text
rtk proxy "C:/Program Files/Git/bin/bash.exe" -c "HERMES_PYTHON=C:/Github/hermes-agent/.venv/Scripts/python.exe bash scripts/run_tests.sh workstation/tests/test_direct_qualification_attestation.py --tb=short -p no:cacheprovider"
```

Result: exit code 1, 7 passed and 2 failed. The failing regressions are `test_self_signed_attestation_cannot_enable_direct` and `test_rehashed_attestation_cannot_expand_qualified_scope`; both observed `DIRECT` where `SHADOW` was expected. This reproduces the attestation authenticity/scope defect in policy resolution. No external effects were attempted by this reproduction. No correction or green rerun is claimed.

An additional focused runner invocation on the baseline contract fixtures completed successfully:

```text
HERMES_PYTHON=C:/Github/hermes-agent/.venv/Scripts/python.exe bash scripts/run_tests.sh workstation/tests/test_operational_resolution_provider.py workstation/tests/test_e2e_operational_resolution.py workstation/tests/test_online_compilability_safety.py workstation/tests/test_online_compilability_monitor.py workstation/tests/test_opportunity_audit_and_backfill.py workstation/tests/test_creative_studio_service.py -j4 --tb=short -p no:cacheprovider
```

Result: exit code 0, 75 passed, 0 failed, 1 skipped; runner-reported duration 63.0s. These are existing contract fixtures, not real Trello, HyperFrames, Electron, or product-economics evidence; this does not close the attestation RED or baseline CI failure. Audit-base Desktop `npm run typecheck --workspace apps/desktop` exited 1 with `TS2307` for `blobatar/blob` at `src/sdk/index.ts:1942` and `blobatar/react` at `src/sdk/index.ts:1943`. The fresh worktree reused the root ancestor `node_modules` and had no candidate-local dependency installation, so classify this as an incomplete dependency environment/failed diagnostic, not native product verification.

## Measurement and qualification boundary

Product latency, provider/model calls, token counts, cache use, and cost per verified outcome are **UNKNOWN**. Test-suite duration is not product latency evidence. Native E1/E2/E3 and packaged Electron qualification were not run because the required baseline is red. No external Trello write authority was granted. No Laya/telemetry runtime implementation was changed; the telemetry owner is the existing `workstation/telemetry/` package.

| PHASE | BASE_SHA | HEAD_SHA | paths | RED before | GREEN after | native receipt | latency median/p95 | real model/tool calls | cost source | blockers | next |
|---|---|---|---|---|---|---|---|---|---|---|---|
| P0 preflight | `8e64b38a81adcf8a01dc2ed05aa3eb078adc9f9f` (audit test base; main gate separately at `f21e803b3525b70ee6be2305e579c1cc1f930e74`) | `8e64b38a81adcf8a01dc2ed05aa3eb078adc9f9f` | attestation test only; evidence docs | 2 focused tests observe DIRECT instead of expected SHADOW | none; seven other tests pass | none | UNKNOWN | UNKNOWN | UNKNOWN; no billing provenance | required main baseline CI failed; audit-base Desktop typecheck diagnostic failed with unresolved dependencies; product metrics and native runs absent | keep feature work blocked; reconcile/qualify Stage A and correct attestation policy |

The authorized lane remains evidence/tests/docs until a qualified baseline exists; it does not authorize operational-speed runtime changes.

# Online Compilability Loop — pre-change gate evidence

Date: 2026-10-08. Branch: `workstation/laya-direct-system1`.
Status: **BLOCKED BEFORE TARGET IMPLEMENTATION / NOT QUALIFIED**.

## Exact baseline and preservation

- Initial local HEAD: `3a8351233b7675024f97d1139382edf28c7e808d`.
- Refreshed implementation/reference HEAD: `3176d97db711a0454de17ca055be956763849838`.
- The 14 incoming commits touch 10 documentation files only. Fast-forward preserved local
  `workstation/dogfood/.obsidian/workspace.json`; no reset, stash, source merge or deletion.
- The initial checkout had inaccessible tracked `.test-tmp` paths reported as deletions.
  They were not staged, repaired or removed. Git lists 22,855 tracked paths under `.test-tmp`.
- No open PR was returned for this branch at inspection time.
- `main` remains `920fdda07a74e2f4a6e790fcc6bc3a2d2ab976a7`.

## Mandatory blockers

H-079 requires a qualified upstream-aligned baseline before target implementation.
H-081 is not qualified on the exact reference HEAD:
[run 37772751167](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/37772751167)
failed in `actions/checkout`, with `unable to create file ... Filename too long` under
`.test-tmp/h081-nonresume-affected/.../artifacts/work_...`.
Supported installation, exact-head verification, owner proofs/full regression and
dependency provenance steps were **skipped**. This is not a failing Laya assertion and
not successful provider qualification. Initial local HEAD also has a failed checkout:
[run 37642238581](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/37642238581).

`origin/main` also has a failed Install & Update E2E run at its exact SHA:
[run 37703151452](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/37703151452).
The legacy branch-protection API returned `404 Branch not protected`; this does not waive
repository qualification policy or establish that repository rulesets are absent.

H-082 bootstrap work remains separate and unimplemented by this change. No installer,
workflow, vendored Laya or runtime code was edited to bypass a prerequisite.

## Upstream snapshot and seam scope

After successful `git fetch upstream main` and `git fetch origin main workstation/laya-direct-system1`:

| Field | Observed value |
|---|---|
| DOWNSTREAM_MAIN_SHA | `920fdda07a74e2f4a6e790fcc6bc3a2d2ab976a7` |
| UPSTREAM_MAIN_SHA_OBSERVED | `99a45ecc17cc51c0488ec3b8ccf7eaf483f7203d` |
| CURRENT_PIN_SHA / merge-base | `71a2fe399bbd7a219c71f9d9fca2b313b01f2057` |
| Reference branch vs observed upstream | 803 ahead / 10,491 behind |
| Reference branch vs origin/main | 57 ahead / 2 behind |

The adopted pin is an ancestor; the observed upstream tip has not been adopted. No second
pin or upstream merge was introduced. Drift is **material/overlapping**, with changed
`agent/background_review.py`, `agent/turn_tool_round.py`, `tools/registry.py`,
`model_tools.py`, `run_agent.py`, `hermes_cli/kanban.py`, `pyproject.toml` and `uv.lock`.
This is a blocking overlap inventory, not a completed semantic migration/classification.
The prior H-081 corrective-lane drift exception does not qualify this new feature baseline.

Affected existing seams include `FPS-SYSTEM1-001` (generic decision/review contracts),
`SEAM-TOOL-POST-EFFECT`, `SEAM-TOOL-RAW-RESULT`, and existing runtime telemetry.
Strict seam inventory passes with 14 classified direct seams, zero unclassified and zero
budget regressions. The audit still lists `FPS-BROWSER-LEGACY` as REMOVE; inventory success
does not prove retirement/parity. Core integration anchor dry-run passes.

## Minimal implementation audit

- `workstation_raw_post_tool_observer` invokes `capture_progressive` but discards its return;
  there is no post-capture monitor call in the inspected owner.
- `capture_progressive` returns the canonical `ExperienceCorpus.capture` reference, or
  `None` for missing lineage/capture failure. Reuse this path.
- `ExperienceCorpus` already reconstructs bounded sample references from ArtifactStore.
- `OperationalKernel` already captures canonical verification/uncertainty transitions.
- `system1/schemas.py` has no compilability decision domain. The requested monitor and test
  files do not exist at the reference HEAD.
- `ExperienceCompiler.compile()/mine()` and run-local `RunScopedCapability`, `RunClosureProof`
  and `execute_in_flight_handoff()` already exist; preserve these owners.
- `ExperienceValidationPromotionCoordinator.process_candidate()` calls `compiler.promote()`;
  it cannot be used directly as the requested validation-only path.
- `origin/main` observer lacks even the branch's progressive hook; branch-local substrates
  must not be represented as already promoted to main.

The incoming documentation contains two D-037 headings. The online-loop heading and
`Dependency preparation is not Workstation startup` are separate decisions; the collision
is recorded in the identifier index without renumbering historical references.

## Verification scope and stopping boundary

The first official `qualify_laya_system1 --live` attempt failed in temporary-directory
access, JUnit writes and cleanup (`PermissionError` / `WinError 5`), before a JSON report
could be written. It is infrastructure failure, not a RED test for the missing loop.
The unchanged runner was then repeated outside the restricted sandbox with fresh temp state.
Its result is recorded separately below and does not override exact-head CI.

### Local measured result

Official command: `.venv/Scripts/python.exe -m workstation.scripts.qualify_laya_system1
--live --output workstation/qualification/online-compilability-baseline-2026-10-08.json`.
Result: **43 passed, 0 failed, 0 errors, 0 skipped**, plus strict seams passed.
[Structured report](online-compilability-baseline-2026-10-08.json) pins tested source HEAD
`3176d97db711a0454de17ca055be956763849838`. Only evidence/docs changed during verification.

Real provider: Laya `0.3.23`, source bytes verified against
`4aa6761be8173de4ce6d92c31b3e40b6eaf59a7c`, CPU, multilingual checkpoint revision
`7b928d828b7b0e022f929d9bd2e44165aa270148`. The real test selected `read_file`, with
calibrated confidence `0.9703` and a valid RoutingCertificate. The three-test real-contract
file took 49.375 seconds including startup/fixtures; this is **not inference-only latency**
and cannot select monitor frequency/batching. No checkpoint digest is asserted.
This checkpoint differs from the historical October 2 receipt; the current report is
authoritative for this local measurement, not a recalibration of the new decision domain.

Full Workstation, additional compiler/handoff suites, Desktop/installer and target-loop
A–H scenarios were not run: the pre-change blocker remains, and no target implementation
was started. Existing focused passes are not full qualification.

Final upstream/origin fetch after local qualification returned the same SHAs and counts
listed above. No new pin was selected and no main merge occurred.

P0 source audit is complete; **new RED tests were not written** because target coding is
blocked. P1–P6 are not implemented. No full-cycle demonstration, online-domain real-Laya
calibration, same-run reuse rate, false-positive rate, System-2 savings or before/after
performance measurement exists. Existing contract checks cannot supply those metrics.

Resume only after the mandatory baseline gates are qualified (or an explicit applicable
exception is documented). Keep checkout/H-081 remediation and H-082 installer correction
independently inspectable; then begin behavioral RED tests and shadow monitoring.

# H-081 checkout correction and resumed qualification

Date: 2026-10-08. Branch: `workstation/laya-direct-system1`.
Corrective source HEAD: `b849d919deb465c8e991218495f619a47d66bc40`.

## Corrected failure

H-081 could not execute its installation/tests because Windows checkout failed on
generated `.test-tmp` paths. The failure reproduced on the documentation-only head
`846111d9cb643ee68782e1bec9fe11af7a5a90e1` in
[run 37774360790](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/37774360790).

Commit `9bc903c6ddbe6c03b6cf4244b5c0e1f1d0cf85a0` had introduced 22,855 temporary
test artifacts. The longest relative path was 272 characters. Correction:

- Untrack only `.test-tmp` using `git rm -r --cached --quiet -- .test-tmp`.
- Ignore `/.test-tmp/` at the repository root.
- Preserve local working files and all historical commits. The original tree remains
  `9bc903c6dd:.test-tmp`, object `26d13b547430c5c3f1b979695eed87aa8b0f50e8`.
- Keep runtime, installer, dependencies, workflow and test assertions unchanged.

Precommit inspection confirmed exactly 22,855 staged deletions, all under `.test-tmp`,
zero remaining tracked entries, and effective ignore matching. Existing local directories
remain present. Preexisting dogfood workspace changes (15 added / 6 deleted lines) were
excluded. The inspected test runners/workflows contain no `.test-tmp/` fixture references.
`git diff --check` passed for the correction.

## Qualification evidence

[Corrective-head CI 37774683099](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/37774683099)
passed checkout, setup-uv, supported locked installation and exact-head verification;
then **FAILED** in full regression after 18m35s. The checkout correction is proven;
H-081 qualification is not closed. The subsequent strict dependency/license step was skipped.

[Original CI artifact](h081-ci-b849d919de/h081-local.json) records focused gates passing
(42 tests, 1 opt-in live skip), strict seam audit passing inside the runner, and full
regression failing (822 passed, 1 failed, 1 skipped, plus one timed-out file):

- `test_anthropic_sdk_construction.py` fails with `ModuleNotFoundError: anthropic`.
  The H-081 install omitted the existing `anthropic` extra, while Workstation CI explicitly
  installs it. The corrective workflow now adds this extra using the unchanged project lock.
- `test_canary_recipe_context.py` collects 31 tests, prints 23 success dots, and is killed
  at the unchanged 900-second file budget (903.27 seconds including termination overhead).
  The collected order places the 1,000-item fanout case next. This identifies the diagnostic
  target but does not establish the underlying cause without a stack/profile.
- Other slow files include durable hardening (654.91 seconds) and durable agent integration
  (378.86 seconds). Local/remote performance cannot be treated as equivalent.

The parallel runner excludes partial results of timed-out files from its summary; its
"no tests ran" bucket does not mean this file failed collection. No failure/timeout has
been relabeled as a pass. The next CI run keeps all tests, 4 workers and the 900-second
budget, with verbose names and `faulthandler_timeout=120` solely for diagnosis. A separate
local execution measures the implicated existing 1,000-item case with the same 900-second
bound. Neither the extra fix nor diagnostics claim to fix the observed performance failure.

The isolated local case passed: **1 passed in 80.08 seconds**, with 79.45 seconds in
the test call. [JUnit evidence](h081-canary-isolated-2026-10-08.xml) preserves its result.
It still executes all 1,000 items, proves zero executor model calls, and rejects confirmed
replay. This confirms local executability, not the remote four-worker performance budget
or the underlying cause of the CI timeout. No test count, fsync behavior or assertion changed.

The isolated local case passed: **1 passed in 80.08 seconds**, with 79.45 seconds in
the test call. [JUnit evidence](h081-canary-isolated-2026-10-08.xml) preserves its result.
It still executes all 1,000 items, proves zero executor model calls, and rejects confirmed
replay. This confirms local executability, not the remote four-worker performance budget
or the underlying cause of the CI timeout. No test count, fsync behavior or assertion changed.

The official local experiment uses `.venv/Scripts/python.exe -m
workstation.scripts.qualify_laya_system1 --live --full --output
workstation/qualification/h081-checkout-correction-2026-10-08.json`. The resulting
[structured report](h081-checkout-correction-2026-10-08.json) pins the corrective HEAD
above and reports `LOCAL_GATES_PASSED`:

- Focused owner gates: **43 passed, 0 failures/errors/skips**, including real Laya.
- Full Workstation: **101 files, 853 passed, 0 failed, 2 skipped**, 300.234 seconds.
- Strict seams: 14 classified, zero unclassified and zero budget growth.
- Component lock, license policy and core integration anchor checks: passed.

Real checkpoint revision: `7b928d828b7b0e022f929d9bd2e44165aa270148`, multilingual,
CPU, Laya `0.3.23`, verified source bytes at
`4aa6761be8173de4ce6d92c31b3e40b6eaf59a7c`. The existing ranking test selected
`read_file` with calibrated confidence `0.9703` and a valid RoutingCertificate.
This is a real existing-domain contract check, not calibration of the unimplemented
compilability domain. Full-suite skips remain skips; they are not counted as passes.

CI uses the current official `--full` mode without `--live`; live-provider evidence is
the separate local run on the same source commit. No combined qualification or success
for failed/skipped remote steps is inferred from the local result.

## Remaining pre-change boundary

This correction permits H-081 qualification to execute; it does not implement the Online
Compilability Loop or the H-082 installer correction. No new RED tests or target runtime
implementation were started while baseline qualification remained blocked.

The main checks were inspected individually. `contracts` and `core-patch-dry-run` passed
at `main@920fdda07a74e2f4a6e790fcc6bc3a2d2ab976a7` in
[Workstation CI 37170956670](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/37170956670).
The Install & Update E2E failure cited in the initial preflight is a distinct workflow;
it is not evidence that those Workstation checks failed. Nix was cancelled. No repository
rulesets were returned by the rulesets listing. Repository policy remains binding.

The latest observed upstream tip is `cbe5e53e2826b949e4ab33dbd6d045e339fa162b`;
corrective branch vs upstream is 805 ahead / 10,492 behind. Adopted pin/merge-base remains
`71a2fe399bbd7a219c71f9d9fca2b313b01f2057`. Since the earlier observation
`99a45ecc17cc51c0488ec3b8ccf7eaf483f7203d`, the one new upstream commit changes
Docker promotion workflow/release tooling, outside the target learning owners. The
accumulated overlap from the adopted pin still includes background review, tool-round
lifecycle, registry, model tools, run_agent, Kanban and dependency metadata. H-079 Stage A
has not been adopted/qualified for this new feature cycle; no exception was fabricated.
No upstream pin, branch ancestry or main state was changed by the checkout correction.

Final fetch before publishing the CI-profile correction returned the same upstream,
origin main and corrective branch SHAs recorded above. No further upstream drift was
observed in that fetch; the adopted pin remains unchanged.

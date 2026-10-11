# Browser optimization baseline evidence — 2026-10-10

**Observed:** 2026-10-10 21:55 America/Sao_Paulo (2026-10-11 00:55 UTC). This is a Browser-only development record. It does not qualify runtime or transfer an exception from another mission.

## Candidate and fixed upstream pin

- This documentation/patch-kit worktree: branch `codex/browser-optimization-preflight-20261010`, HEAD `025831f7b3892bb504320c3929ba964cdf3376e4` (PR #67 kit base).
- PR #66: open against `main`, head `217742e7bfc66310f9352155e4a0b1a30bab2b98`, GitHub reports mergeable and clean. It is the Stage A candidate; it is not `main`.
- Selected upstream pin: `66605471e9f0b0832abbefaf625ce08e948ca540`. True upstream merge: `3ece460ea686d9e1621bcd723e352fbe78e04b18`; the pin is an ancestor of the PR #66 candidate. Continue with this one pin; do not start a second upstream merge.
- Latest observed `upstream/main`: `c57331677d7fc46298a7159cf3a650853f0966c5`, 78 commits beyond the fixed pin. The reviewed path diff was empty for `tools/browser_tool.py`, `tools/registry.py`, `toolsets.py`, `agent/turn_tool_round.py`, `run_agent.py`, `browser_extension_router`, `browser_control_broker`, effects, `tool_executor`, `tool_guardrails`, `conversation_loop`, `tui_gateway/server`, and Desktop main/preload. Two one-line static cleanups were identified for next-cycle `ADOPT_UPSTREAM` review: `gateway/run_shutdown` removes an `# noqa: ASYNC220`, and `run_turn` removes an unused exception binding. No behavioral delta was identified. Record this movement as next-cycle drift; it does not alter this candidate.
- Exact remote/main inspection used for the Browser research note: `f21e803b3525b70ee6be2305e579c1cc1f930e74`. Do not substitute it for PR #66 or its Stage A evidence.

## Live Actions blocker and qualification status

- Read-only PR API: PR #66 is `open`, `mergeable=true`, `mergeable_state=clean`, head `217742e7bfc66310f9352155e4a0b1a30bab2b98`.
- Read-only commit checks: `check-runs` returned `total_count=0`; commit status returned `pending` with `total_count=0` and no statuses.
- Actions permissions endpoint returned `enabled=true`, which does not prove dispatch is executable. Root's two attempted workflow dispatches (`workstation-ci.yml` and `workstation-browser-windows.yml`, at `codex/operational-speed-stage-a-20261010`) each returned HTTP 422: `Actions has been disabled for this repository`. Do not retry dispatch while this blocker remains.
- Separate observed `main` CI run `37826432518`: 7 failed, all `ModuleNotFoundError: No module named 'laya'`; 893 passed, 2 skipped. PR #66's local report at code `749e2f9` was 970 passed / 4 skipped. Its UI report was 10,753 passed / 3 failed / 1 skipped; a repair covered only the 87-test slice. Electron's 3,556 passed / 34 failed / 138 skipped receipt is from other historical SHAs. These results are not a green exact-head Actions gate.
- Therefore BROW-00 is **HOLD / NOT QUALIFIED**. The Actions dispatch block is external to these tests. No other task's exception transfers to Browser.

## Isolated patch-kit tests

No dependency installation occurred. Vitest `4.1.10` was reused from `C:\Github\hermes-agent\node_modules`; the isolated worktree has no `node_modules`. The patch-kit now includes `patch-kit/vitest.config.mjs`, which sets the kit directory as root and aliases `vitest` to an existing package path supplied by the neutral development-only `VITEST_PACKAGE_ROOT` variable. Worker creation required an elevated retry because the sandbox returned `spawn EPERM`; the successful config uses one thread worker.

Reproduction from the repository root in PowerShell (with an existing Vitest package):

```powershell
$env:VITEST_PACKAGE_ROOT = 'C:\path\to\existing\node_modules\vitest'
rtk node 'C:\path\to\existing\node_modules\vitest\vitest.mjs' run `
  --config 'workstation\context\browser-optimization-kit\patch-kit\vitest.config.mjs' `
  --configLoader native
```

Initial reference-kit result: **3 test files passed, 8 tests passed**.

Then added malformed JSON-shaped step contracts in `patch-kit/batch-contract.test.ts`. Each case places a valid click before a malformed second step and requires whole-batch rejection before any owner check or effect:

- click missing `ref`;
- press with empty `key`;
- scroll with unsupported `direction`;
- type missing `text`.

RED result before reference-helper correction: **3 passed, 4 failed**. The first three malformed steps were accepted and returned `verified`; missing type text threw `TypeError` at `batch-contract.ts:54` instead of returning a rejection. The helper owner then changed only `patch-kit/batch-contract.ts` to validate the full JSON-shaped batch and context before authority/effects. GREEN result: **3 test files passed, 12 tests passed** using the persisted config above. This is a patch-kit reference correction, not OPT-01 runtime wiring, native Browser evidence, or an enabled product path.

Additional limit: a `checkpoint()` call after an effect does not by itself prove durable intent or crash recovery. Batch receipts and deltas remain subordinate to the existing BrowserTask, TaskRun, policy, and receipt owners.

The kit then added reference contracts for lossless snapshot reconstruction (including Unicode, long text, insertions/removals, trailing newline and truncated fallback), cache A→B→A identity isolation, and uncertain batch stop/no-retry. A sparse-array invariant was added as `patch-kit/batch-contract-input.test.ts`; it places a valid click at index 0 and leaves index 1 empty, requiring rejection at index 1 before any adapter callback. Final result: **4 Vitest files / 24 tests passed / 0 skipped**.

The sparse case was also run against a temporary copy of the original helper from `025831f7b3892bb504320c3929ba964cdf3376e4`, with no worktree edits. RED was reproduced: the baseline helper failed the zero-completion invariant (`completedSteps` expected 0, received 1), showing that the valid first step had already run before the sparse hole at index 1 was reported.

The isolated benchmark contract suite is **3 Node test files / 12 passed / 0 skipped**. It covers canonical path containment (including Windows cross-drive and directory-link escapes for test home, descriptor and output), direct controller response-envelope lookup, URLSearchParams encoding, measurement validation/grouping/duplicate rejection/percentiles, and loopback fixture smoke/state isolation. The first sandboxed Node run hit `spawn EPERM`; rerunning the same tests with elevated local process permission passed. No Browser process, user profile, credentials or native controller was used.

Reproduction commands from the isolated worktree root (reuse the existing Vitest package; do not install dependencies):

```powershell
$env:VITEST_PACKAGE_ROOT = 'C:\Github\hermes-agent\node_modules\vitest'
rtk node 'C:\Github\hermes-agent\node_modules\vitest\vitest.mjs' run `
  --config 'workstation\context\browser-optimization-kit\patch-kit\vitest.config.mjs' `
  --configLoader native

rtk node --test --test-concurrency=1 `
  workstation/context/browser-optimization-kit/benchmark/native-guards.test.mjs `
  workstation/context/browser-optimization-kit/benchmark/measurements.test.mjs `
  workstation/context/browser-optimization-kit/benchmark/fixture-server.test.mjs
```

## Benchmark harness review (reference-only)

The harness contains `benchmark/native-runner.mjs`, `benchmark/native-guards.mjs`, `benchmark/measurements.mjs`, `benchmark/summarize.mjs`, `benchmark/fixture-server.mjs`, deterministic fixture assets, and Node contract tests. It reuses the existing Desktop statistics helper at `apps/desktop/scripts/perf/lib/stats.mjs`; no statistics implementation or runtime owner was added. The parser groups only records matching evidence scope, run, candidate SHA, config, runtime version, scenario and operation, and rejects duplicate `(run_id, sample_id)` rows. Percentiles are derived only from observed numeric rows; modelled values are not emitted.

The fixture server binds only to `127.0.0.1`, supports an ephemeral port and keeps in-memory run-scoped state, labels output `FIXTURE_SMOKE`, and cannot claim H004/H013. The native runner records `qualification: NV`; `candidate_sha` and `runtime_version` are CLI-declared labels with `identity_provenance` marked `USER_DECLARED` and `build_attestation: NV`. The descriptor provides no independent build proof, so exact-head/runtime provenance remains NV. The runner summary explicitly says `MEASURED_NATIVE_SAMPLES_NOT_H004_H013_QUALIFICATION`. Native Browser, logged-in profile, tab-recovery resume and human takeover were **NOT RUN**; assisted takeover remains UNCERTAIN without an owner-issued human-control receipt and independent readback. No native performance metrics are claimed.

Review repairs in the isolated harness: test-home/descriptor/output paths are canonicalized before descriptor reads or output creation; symlink/junction escapes and Windows cross-drive containment are rejected; snapshot element lookup consumes the actual `{result: ...}` controller envelope; fixture query extras use URLSearchParams; and native VERIFIED measurements always require receipt and readback references. These repairs affect only the reference harness, not Hermes runtime or OPT-01 implementation.

## Exact file inventory and rollback

Modified existing files:

- Documentation/evidence: `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`, `workstation/context/engineering-journal/CURRENT.md`, `workstation/context/browser-optimization-kit/IMPLEMENTATION_PLAN.md`.
- Patch-kit: `patch-kit/batch-contract.ts`, `patch-kit/batch-contract.test.ts`, `patch-kit/extract-cache.test.ts`, `patch-kit/snapshot-delta.test.ts`.

New files:

- `workstation/context/browser-optimization-kit/BASELINE_EVIDENCE_2026-10-10.md`.
- `workstation/context/browser-optimization-kit/patch-kit/batch-contract-input.test.ts` and `patch-kit/vitest.config.mjs`.
- Under `workstation/context/browser-optimization-kit/benchmark/`: `fixture-server.mjs`, `measurements.mjs`, `native-guards.mjs`, `native-runner.mjs`, `summarize.mjs`, `fixtures/fixture.css`, `fixtures/fixture.mjs`, `fixtures/index.html`, `fixture-server.test.mjs`, `measurements.test.mjs`, and `native-guards.test.mjs`.

No Hermes runtime/browser owner, tool registration, Desktop runtime, profile, `main`, PR #66, or Stage A checkout was changed. Rollback is limited to reverting the preparation commits on `codex/browser-optimization-preflight-20261010` or closing its draft PR; retain the evidence record. No runtime rollback or PR #66/upstream-history rewrite is needed or authorized.

## Stage labels

- **BROW-00:** HOLD / NOT QUALIFIED until upstream-aligned baseline and required exact-head Actions are available and green.
- **BROW-01:** PREPARED / NOT MEASURED. Any later benchmark report must identify its exact candidate, environment, sample, counters and verified outcomes; no performance result is established here.
- **OPT-01/02/03/04 and other runtime work:** BLOCKED by BROW-00.
- **OPT-05:** separate privacy/consent HOLD. Any future proposal needs explicit user consent scoped to profile and origin, temporary isolated handling, data minimization, a defined retention/deletion path and rollback, and secret-free logs. No credential, cookie or DPAPI import is authorized by this research or test work.

## Final remote snapshot before promotion

After the final read-only fetch, isolated worktree `codex/browser-optimization-preflight-20261010` was still based on `025831f7b3892bb504320c3929ba964cdf3376e4` before the preparation commits. `origin/main` remained `f21e803b3525b70ee6be2305e579c1cc1f930e74`; `upstream/main` remained `c57331677d7fc46298a7159cf3a650853f0966c5`, 78 commits beyond the selected `66605471e9f0b0832abbefaf625ce08e948ca540` pin. The pin remains an ancestor of this candidate. The final path-specific diff against that pin was empty for the inspected Browser/runtime owners listed above; the two one-line `ADOPT_UPSTREAM` hygiene changes remain next-cycle observations only.

The original `C:\Github\hermes-agent` checkout was not edited or switched: its active branch was `codex/creative-d043-engine-neutral`, HEAD `56f5758d9b589f3bc04f5a4b4305d80d8fd459a7`, with pre-existing user changes/deletions. Its local `main` and `origin/main` both remained `f21e803b3525b70ee6be2305e579c1cc1f930e74`. No merge, pull, reset, checkout, or cleanup was performed there. Fetch updated only shared remote-tracking metadata after the sandbox denied `FETCH_HEAD` writes; no checkout files were touched.


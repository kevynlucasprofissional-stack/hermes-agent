# Workstation Testing

## H-079.2 exact-head dogfood and platform qualification gate — BLOCKING

Before H-079.2 can close, one exact candidate head must prove all of the following:

1. Fresh upstream pin is an ancestor and candidate is 0 behind that selected pin.
2. Strict seam audit and core integration dry-run pass.
3. Real installer matrix passes:
   - no venv;
   - existing venv with pip;
   - existing pipless venv with uv;
   - existing pipless venv without uv via `ensurepip`;
   - broken/unsupported venv explicit failure;
   - checkout remains clean.
4. H-077 guardrail proves both directions:
   - ACK/`{"ok": true}` without `actual_delta=True` does not reset verified progress;
   - trusted observed `actual_delta=True` may reset it.
5. Real Anthropic construction contract passes without network I/O: keep provider-routing unit mocks, but separately exercise the installed optional SDK through real `build_anthropic_client` construction.
6. Full Workstation suite and durable core seam regression suite pass.
7. Desktop typecheck/build/UI/platform tests pass with platform-correct fixtures.
8. H004/H013/browser authority and single-mutation-executor invariants remain green.
9. Workstation Browser Windows is green, not merely explained.
10. General CI, Nix, Docker and all required exact-head checks are green.
11. Final upstream drift is classified before promotion.

Historical receipts from `9e8127e...` or `964c133...` are regression evidence only; they do not qualify a later H-079.2 head.


## H-079 upstream-first baseline qualification gate — PRIMARY

No downstream target change may claim a valid test baseline until the upstream-first gate
has completed.

Required order:
1. fetch upstream and pin exact SHA;
2. true baseline integration + seam reconciliation;
3. baseline-focused tests;
4. full Workstation / affected upstream tests;
5. exact-head required GitHub Actions;
6. only then begin target implementation;
7. target-focused + regression tests;
8. final upstream drift classification before promotion.

A focused local pass cannot override a red exact-head baseline.

Current H-079 candidate qualification evidence (2026-09-20):
- Workstation test suite: 741 passed, 2 skipped, 1 warning (291s).
- Runtime independence: PASSED (isolated subprocess test proves AlternateReasoner loads 0 `run_agent` modules).
- Desktop dry-run: `apply_core_integration.py --check` passes with all anchors found.
- Desktop validation: `npm run typecheck` 0 errors, `npm run build` green, H013 E2E 3/3 passed in 1.4m.
- Native Browser task: H004 smoke probe VALIDATED (live destroy and restart passed).
- Seam audit: `audit_hermes_seams.py --strict` passes with 18 classified, 0 unclassified, 0 regressions.
- Candidate head is locally qualified across all tiers and pending exact-head CI evaluation.


## H-077.1 truthful-core qualification gate — IMPLEMENTATION COMPLETE / EXACT-HEAD CI PENDING (2026-09-19)

Canonical:
[H077_1_QUALIFICATION_CLOSURE_2026-09-19.md](H077_1_QUALIFICATION_CLOSURE_2026-09-19.md).

PR #36 focused/full receipts are retained as regression evidence, but post-merge
falsification found behaviors outside those tests.

Required RED/GREEN proof:
- TaskCompiler cannot validate/complete INCONCLUSIVE, FAILED, STALE or CONFLICT kernel
  results; VERIFIED closes the same path once;
- weak observation cannot inherit E3/trusted-owner/source/failure-domain provenance from
  VerificationContract requirements;
- wrong/missing task_id/run_id/operation_id fails when expected lineage is required;
- missing required tenant/target/resource/applicability context fails closed and prevents
  deterministic reuse;
- FCOR uses externally adjudicated certified outcomes and reports
  external_oracle_coverage separately;
- external correctness/reuse/recovery do not use optimistic missing-truth defaults;
- AFB-v0.1 rows are generated from real system result + independently executed hidden
  oracle, not hand-labelled;
- include counterfactual pair, source disagreement, lost ACK/non-idempotence,
  temporal MAINTAIN, composition emergence, semantic drift same schema, goal shift,
  dynamic queue and post-promotion holdout;
- normal Experience Compiler contradiction flow automatically marks model inadequacy and
  suspends promotion/generalization without inventing PRE;
- ACK, verified success and verified deterministic replay/savings are separate counters.

Qualification order:
focused H-077.1 -> H-076/H-075 regressions -> durable/control-plane regressions ->
full Workstation -> affected Browser/Electron gates if touched -> exact-head required CI.

Historical evidence includes PR #36's local 696 passed / 2 skipped and post-merge
Workstation CI observing 698 passing contract tests plus 255 durable seam regressions.
Those baselines do not replace the new negative controls.

## H-071 corrective local candidate receipt — 2026-09-19

- focused control-plane/admission: 27 passed;
- full Workstation: 607 passed, 0 failed, 2 skipped;
- Electron: 1791 passed, 0 failed, 5 skipped (127 passed / 1 skipped files);
- admission Vitest 4/4; Desktop typecheck and core-integration check passed;
- H004 validated; H013 2/2; Work100 30 PASS / 0 gaps / 0 failures.

Required exact-head GitHub Actions remain pending; local evidence does not by itself
authorize `QUALIFIED/CLOSED`.

## Browser Ownership & Recovery Reconciliation regression gate — CORRECTIVE QUALIFICATION OPEN (2026-09-19)

Canonical target:
[BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md](BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md).

### Prior green evidence retained

- `native-view-occlusion.test.ts`: tooltip popper regression and real-occluder behavior;
- `workstation-browser-runtime-task.test.ts`: host fencing, cross-session isolation,
  background foreground-preservation and BrowserTask lifecycle;
- `workstation-browser-runtime-recovery.test.ts`: direct runtime multi-task restart
  with known `preferredTaskId`;
- `task-rail.test.ts`: activity projection separate from viewport visibility;
- Desktop TypeScript typecheck: previously green;
- focused workstation-browser Vitest set: 88 passed across 9 files;
- H004 native BrowserTask smoke: validated;
- Work100: 30 PASS / 0 FAIL.

These are baseline evidence, not final product qualification.

### New required RED/GREEN behaviors

1. **Execution-aware Clear Parked**
   - construct at least one `parked + working` task and one `parked + idle` task;
   - invoke the real bulk-clear path through the public bridge/runtime boundary;
   - idle parked task may be destroyed;
   - working, waiting and human-controlled tasks must survive unchanged;
   - no renderer-only filtering is accepted as the safety boundary.

2. **No first visual blank after restart**
   - start from persisted BrowserTask metadata and session-scoped Browser preview intent;
   - mount the real `WorkstationBrowserPane`/renderer path with no preseeded local
     `state.tasks`;
   - prove the task is resolved before the first native Chat viewport attach;
   - a recoverable BrowserTask must never expose fallback `about:blank` as the
     foreground frame, even transiently.

3. **Integrated H013 restart A/B**
   - extend the H013 bridge type to
     `attach(bounds, host?, preferredTaskId?)`;
   - Chat A/Browser A and Chat B/Browser B must survive an actual Electron process
     restart;
   - renderer cold mount restores B, switching to A restores A;
   - exactly one live page per task;
   - stale `detach/setVisible` from the prior host cannot blank the new owner;
   - background work does not steal foreground.

4. **Canonical session alias coverage**
   - prove live id, `_lineage_root_id` and supported `parent_session_id` aliases
     all resolve the same BrowserTask;
   - reuse/extend canonical session identity helpers rather than adding a Browser-only
     alias registry.

5. **Explicit native-view occlusion authority**
   - tooltips and unrelated generic role/slot elements never hide Chromium;
   - only deliberately marked native-view occluders trigger hide/restore;
   - Chat and Hub continue using the same shared observer/contract.

### Qualification order

Focused renderer/runtime RED/GREEN -> Desktop typecheck -> affected UI/platform suites
-> H004 when runtime lifecycle is touched -> **extended H013 on real Electron** ->
Work100 -> exact candidate-head Workstation/Windows gates.

The Browser Operational Admission lane may remain independently red; classify such a
failure rather than misattributing it. However no document may claim repository-wide
"100% regressions green" while required exact-head workflows are failing or pending.

Do not close this lane from direct runtime tests that already know
`preferredTaskId`; the original residual risk is at the renderer discovery/first-attach
boundary.


## Browser Operational Admission / Primitive Closure P0 regression gate

Canonical target:
[BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md](BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md).

### Post-PR #29 corrective qualification gate — 2026-09-19

The prior focused/local suites are retained, but P0 closure now additionally requires
behavioral RED/GREEN proof for the audited failures. Do not use source-text/regex tests.

Required behaviors:
- a `ComposedDecision` whose capabilities were not executed cannot return operational
  success, VERIFIED or COMMITTED;
- real composition executes the certified plan in order/graph semantics, propagates
  drift/uncertainty and verifies the required postconditions before commit;
- `CertifiedDispatcher` receiving only `{"success": true}` and no accepted verifier
  remains ACKNOWLEDGED / NEEDS_VERIFICATION (or equivalent non-committed state);
- explicit contract-authorized ACK-only evidence is the only exception and is tested
  separately;
- request `trusted_authority` cannot mint authority, and bare task/session context
  without persisted trusted grant cannot mutate; requested scope can only narrow;
- three semantically equal mutations with **no executable/verifiable operational
  closure** yield at most `SUGGEST_COMPILE`;
- the same family with deterministic primitive/capability + authority/policy +
  verifier/readback + certified dispatch may reach `REQUIRE_COMPILE`;
- arbitrary `terminal` commands sharing `python -m`, `bash -c`, etc. never become
  mandatory compilation solely from that syntax;
- `browser_read_http` permits relative/same-origin GET/HEAD in the bound Browser
  session, rejects body/mutation methods, denies cross-origin by default and permits it
  only through explicit policy;
- destination safety covers literal and resolved private/link-local/metadata/loopback
  surfaces, including IPv6/DNS cases supported by the canonical URL-safety owner;
- caller-supplied headers cannot smuggle forbidden credentials/authority across origin;
- bound native Browser readback with controller/runtime unavailable fails closed and
  never falls back to process `requests.request`;
- large readback stores the **complete** payload in ArtifactStore/reference plane before
  producing a bounded inline projection;
- `python workstation/scripts/apply_core_integration.py --root . --check` passes on
  Linux and Windows with the current `browser_type` route/registration;
- a real Electron/WebContents fixture exercises contenteditable/rich-editor plain-text
  paste with exact newlines, delayed SPA hydration, session cookie, same-origin API
  readback, Save/persist/verify and deterministic replay/fan-out without intermediate
  planner calls;
- timeout-after-mutation remains UNCERTAIN and cannot blind retry; earlier confirmed
  item effects remain preserved under per-item drift.

Required qualification order:
1. focused Python through `scripts/run_tests.sh` (never direct pytest);
2. focused Electron/Vitest behavior tests and Desktop typecheck;
3. `apply_core_integration.py --check` on supported CI hosts;
4. affected Workstation and adjacent core suites;
5. H004/H013 when Browser lifecycle/recovery owners are touched;
6. Work100;
7. exact candidate-head GitHub Actions: required Workstation/Windows jobs all green;
8. only then update CURRENT_STATE / ROADMAP / journal / canonical P0 to QUALIFIED.

A local pass count is evidence, not a substitute for a failing/skipped product gate.

Minimum focused proof:
- `read_preview` PURE_READ; mixed-action tools classify subactions correctly;
- structural similarity alone never forces compilation across terminal/filesystem/browser;
- same-family proven fan-out retains compilation/canary behavior;
- rich-text plain-text paste preserves exact newline semantics and target reacquisition;
- browser readback is GET/HEAD-only, bounded, policy/same-origin constrained and spills large data by reference;
- trusted runtime authority cannot be broadened by route/request payload;
- routed mutation cannot bypass valid certificate + CertifiedDispatcher;
- mutable timeout becomes UNCERTAIN and blocks blind retry until reconciliation;
- transient empty SPA snapshots receive bounded re-observation without site-specific sleeps;
- generic Trello-like fixture proves edit -> paste -> save -> persisted readback -> verify;
- verified canary fans out equivalent items with zero intermediate planning calls;
- per-item drift preserves previous confirmed effects and returns bounded NEEDS_REASONING.

Required affected suites should include or extend:
`test_execution_policy.py`, `test_progressive_compilation.py`,
`test_task_compiler.py`, `test_capability_router.py`,
`test_control_plane_integration.py`, `test_browser_workstation_route.py`,
plus Electron `workstation-browser-runtime*.test.ts` coverage.

When Electron/controller product code changes, rerun H004 native browser smoke and
Work100 after focused RED/GREEN. Provider-free tests do not by themselves prove live
authenticated provider behavior.

## Verified Operational Control Plane regression gate — implemented baseline

Canonical target:
[VERIFIED_OPERATIONAL_CONTROL_PLANE.md](VERIFIED_OPERATIONAL_CONTROL_PLANE.md).

CP0–CP9 is implemented and contract-validated. Preserve the control-plane
behavioral contracts below as a regression baseline; source shape alone is never proof.

Required focused contracts:

- immutable/canonical OperationIntent hashing and explicit IntentRevision;
- existing WorkIntent behavior remains backward-compatible;
- MessageEnvelope/page/request prose cannot mint execution authority;
- typed predicate/effect IR normalization is deterministic and contains no
  arbitrary executable code;
- target mismatch, false precondition or unbound input prevents EXECUTE;
- postcondition must imply the intent goal;
- goal coverage does not excuse an extra forbidden effect;
- invariant-breaking plans are rejected even when the goal would be reached;
- intent permission without authority and authority without intent permission both
  reject mutation;
- verifier/evidence strength must meet AcceptanceContract;
- outstanding relevant uncertain mutation dominates and forces reconciliation;
- POSSIBLE_MATCH is never dispatchable;
- EXECUTE/COMPOSE require a valid Routing/Composition Certificate;
- stale/invalid certificate cannot reach side-effect dispatch;
- state/resource-version changes between route and dispatch invalidate/re-route;
- already-satisfied goal produces SATISFIED with zero mutation;
- deterministic future condition produces WAIT, not LLM polling;
- authority/preference gap produces ASK_HUMAN;
- semantic strategy gap produces WAKE_LLM with minimal OpenCondition;
- LLM output must pass Router admission before mutation;
- bounded composition proves causal links, pre/postcondition chaining, effect
  containment, invariant preservation, authority JOIN and verifier closure;
- intermediate threat/conflicting effect is rejected or deterministically reordered;
- composition budget exhaustion yields WAKE_LLM instead of unbounded search;
- semantic Skill family requirements resolve implementations without pinning
  physical IDs by default;
- large synthetic capability catalogs remain internal and do not grow provider
  tool schemas;
- approximate retrieval cannot authorize execution;
- AwaitCondition survives restart and resumes the exact fenced continuation;
- stale/duplicate events do not duplicate mutable effects;
- event arrival wakes but authoritative predicate=false prevents continuation;
- uncorrelated system events remain observation-only and never create work;
- causal trigger cycles/no-progress trip a circuit breaker;
- bounded polling/backoff consumes zero LLM calls while waiting;
- uncertain external-style dispatch reconciles before any retry;
- Router-vs-Capability-vs-Policy-vs-Observation failure attribution is preserved;
- shadow Router records proposed decisions without controlling production mutation;
- Router/Trigger/VOLC metrics keep unknown denominators as null.

Recommended focused files:
- `workstation/tests/test_operation_intent.py`;
- `workstation/tests/test_capability_router.py`;
- `workstation/tests/test_control_plane_composition.py`;
- `workstation/tests/test_await_trigger_plane.py`;
- extensions to `test_canonical_work_loop.py`, `test_events_pipeline.py`,
  `test_operational_capabilities.py`, `test_task_compiler.py`,
  `test_experience_compiler.py` and the existing policy/uncertainty owners.

Use deterministic unit tests plus property/metamorphic counterexamples. If a
property-testing dependency is not already justified by the repository, prefer a
small deterministic generator rather than adding a heavy dependency. Tests must
not read source text.

Canonical proof properties to encode explicitly:

~~~text
Router Soundness
Goal Non-Expansion
Authority Non-Escalation
Deterministic Closure
Verification Closure
Uncertainty Dominance
Event wakes; state confirms
LLM proposes; Router authorizes
No certificate; no dispatch
~~~

Follow root `AGENTS.md`: Python validation runs through
`scripts/run_tests.sh`, never direct `pytest`. Start with focused RED/GREEN,
then affected Workstation regressions, the full Workstation wrapper gate and
`python workstation/work100.py --run`. Run Desktop/Electron gates only when
their product/runtime paths are changed.

Roll out routing authority in test evidence stages:
adaptive baseline -> shadow Router -> low-risk Router -> mutating Router.
Do not use a unit-green Router as sufficient evidence to grant production mutation
authority.


A Workstation change is stable only when its **behavioral contract** is proven at the lowest useful layer and the relevant integration path remains green. Typecheck or source-shape checks alone are not proof.

## Verified Operational Control Plane Test Suite (CP0–CP9)

The Verified Operational Control Plane is validated through 5 dedicated test modules in `workstation/tests/`:

1. `test_operation_intent.py`:
   - Typed Predicate AST evaluation (`TRUE`, `FALSE`, `EQ`, `NEQ`, `EXISTS`, `ABSENT`, `AND`, `OR`, `NOT`, `IN`, `SUBSET`, `LT`, `LTE`, `GT`, `GTE`, `UNCHANGED`, `TRANSITION`).
   - Algebraic entailment (`entails`) and invariant preservation (`preserves_invariant`).
   - Effect AST and effect containment (`effect_contained`).
   - `OperationIntent` serialization and cryptographic hashing (`operation_intent_hash`).
   - Authority lattice (`AuthorityLevel`, `AuthorityScope`, `authority_covers`, `authority_join`).
2. `test_capability_router.py`:
   - `CapabilityRouter.route` evaluation across decision lattice (`SATISFIED`, `EXECUTE`, `COMPOSE`, `WAIT`, `ASK_HUMAN`, `WAKE_LLM`).
   - Strict 15-point `RoutingCertificate` validation (`NO VALID CERTIFICATE -> NO DISPATCH`).
   - Revalidation freshness checks before dispatch.
   - Metamorphic property tests (weakening preconditions/strengthening budgets maintains executability).
3. `test_control_plane_composition.py`:
   - Bounded backward chaining planner under depth, node, and time limits.
   - Causal threat detection (`detect_causal_threats`) and automatic plan reordering.
   - Fallback to `ReasoningDecision` when composition budget is exceeded.
4. `test_await_trigger_plane.py`:
   - `AwaitCondition` specification and persistence in `AwaitConditionStore`.
   - `TriggerCoordinator` enforcing *Event wakes; authoritative state confirms*.
   - Run fencing preventing stale event processing.
   - `TriggerCircuitBreaker` guarding against runaway poll/trigger loops.
   - `CertifiedDispatcher` idempotency and `DispatchStatus.UNCERTAIN` protection.
5. `test_control_plane_integration.py`:
   - Reasoning handoff (`OpenCondition`, `AttentionPacket`, `needs_reasoning`).
   - Router re-admission of LLM-proposed intents.
   - Semantic capability family resolution without physical pins.
   - `ShadowRouter` 0-mutation evaluation.
   - `FailureAttributor` root-cause classification (7 failure classes).
   - `VOLCMetrics` cost vector retention with unknown cost handling.
   - `TaskCompiler` and `tools/workstation_work.py` execution via `action="route"`.

Canonical test execution:
```bash
.\.venv\Scripts\python.exe scripts/run_tests_parallel.py workstation/tests/test_operation_intent.py workstation/tests/test_capability_router.py workstation/tests/test_control_plane_composition.py workstation/tests/test_await_trigger_plane.py workstation/tests/test_control_plane_integration.py
```

## AEPC-E002 semantic-homogeneity regression gate

The 2026-09-18 follow-up audit found that shape-equivalent browser calls can still
be over-grouped. The regression gate must prove **semantic family**, not merely
tool/schema repetition.

Required focused cases:

1. one long stateful native-browser turn executes at least three
   `browser_type` calls and at least three `browser_click`/equivalent mutable
   browser actions against different semantic targets, with observations between
   mutations; it must not enter `durable_compile_required` solely because the
   same tool shape recurs;
2. the test must vary semantic anchors/targets so it cannot pass by resetting a
   counter around navigation/snapshot boundaries;
3. a paired true homogeneous fan-out fixture with the same owner-declared
   operation, canonical route/provider and concrete target family must transition
   to `REQUIRE_COMPILE` on the configured third distinct mutation;
4. middleware-final arguments must still be rechecked before mutable I/O;
5. lost ACK/uncertain mutation must still require human/reconciliation and must
   never be retried to satisfy the adaptive test;
6. browser snapshot remains E1 and may not be promoted to E2 to make the test
   green;
7. `CompilationCandidate.successful_occurrences` must not count
   `executed_unverified` as verified success. Test the corrected name/semantics.

Anti-cheat conditions: do not raise the threshold, reset mutation counters on
snapshot/navigation, special-case `browser_*` as always adaptive, disable
TaskCompiler/canary, or weaken route/effect/TaskRun/lease/approval checks.

Run the new focused tests together with `test_execution_policy.py`,
`test_operational_capabilities.py`, `test_progressive_compilation.py`,
`test_task_compiler.py`, `test_readonly_preflight.py`,
`test_durable_agent_integration.py`, `test_durable_hardening.py`,
`test_browser_workstation_route.py` and `test_routines.py`; then run all
`workstation/tests`, adjacent executor/guardrail tests, Work100 and Desktop owner
contracts. Native packaged browser evidence remains a separate gate.

## Adaptive execution / progressive compilation regression gate

The implemented 2026-09-18 correction is specified in
[ADAPTIVE_EXECUTION_COMPILATION.md](ADAPTIVE_EXECUTION_COMPILATION.md).

Focused tests must prove both usability and safety:

- native Workstation Browser can perform a bounded
  navigate -> snapshot -> interact -> snapshot loop under one BrowserTask even
  when the enclosing prompt contains repeatability signals;
- the third-or-later distinct equivalent homogeneous mutation still triggers the
  compiler/canary policy before uncontrolled fan-out;
- a compilation candidate for one operation cannot contaminate an unrelated later
  mutation;
- browser tool constraints normalize to native_browser;
- guardrail effect classification consumes tools.effects and keeps arbitrary
  browser_console mutating;
- deterministic drift returns compact NEEDS_REASONING, preserves confirmed
  checkpoints and resumes without replay;
- uncertain dispatched effects remain unretriable until reconciliation;
- an adaptive -> candidate -> validated/promotion -> deterministic replay scenario
  shows fewer provider/LLM calls on compatible reuse and returns to reasoning on
  injected drift.

Extend the focused suites around test_task_compiler.py,
test_readonly_preflight.py, test_durable_agent_integration.py,
test_durable_hardening.py, test_browser_workstation_route.py,
test_routines.py and canonical-work-loop coverage before adding broader
product gates.

## Upstream reliability hardening regression gate

The parallel 2026-09-18 P0 lane is specified in
[UPSTREAM_RELIABILITY_HARDENING_2026-09-18.md](UPSTREAM_RELIABILITY_HARDENING_2026-09-18.md).
Run focused RED/GREEN tests for each slice before broad suites.

### P0.0 — native Browser current-main discriminator

Reuse the existing evidence surfaces instead of creating a parallel harness:

- `workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs`;
- `apps/desktop/electron/workstation-browser-task.test.ts`;
- H013 `apps/desktop/e2e/workstation-headless-load.spec.ts`.

Extend/rework H004 so current-main execution additionally proves timer progress,
typed input, scroll preservation, a post-hide/park real controller/browser action
against the same task-owned WebContents, and no external-browser fallback. If
this passes, BrowserTask keepalive is not the cause of the dogfood obstruction.

### P0.1 — transcript recovery/resync

- extend `apps/desktop/src/lib/inflight-turn-journal.test.ts` with the #115068
  sealed-interim + later-live-tail case and duplicate-id protection;
- extend `apps/desktop/src/app/contrib/hooks/use-background-sync.test.ts` with
  #115085 active/tile refresh during an unacknowledged optimistic user send;
- prove authoritative ACK later converges without duplicate user rows.

### P0.2 — session writer ownership

Add focused active-session/CLI/Desktop tests proving:

- writer A + observer B is allowed;
- writer A + writer B for the same `session_id` is refused;
- transfer cannot steal a foreign-owned live session;
- dead/released owner can be pruned then reacquired;
- registry read/corruption uncertainty fails closed;
- read-only resume never mutates the session.

Use #111493 as behavioral reference; adapt to downstream ownership paths.

### P0.3 — Kanban provenance/liveness/worker truth

- add a focused provenance regression equivalent to upstream #114785: stale
  process env X + request-scoped persisted session Y must produce Y; nonexistent
  ids are not persisted as valid provenance;
- extend `tests/cron/test_cron_kanban_env_isolation.py` and
  `tests/tools/test_delegate_kanban_isolation.py` for #114793: heartbeat is
  true only when claim + worker writes persist and delegated-child activity
  cannot refresh the parent worker;
- add worker-exit durable-evidence coverage for #114904 using this fork's actual
  one-shot path in `cli.py` and classifier in `hermes_cli/kanban_db.py`:
  embedded and separate dispatcher topology must classify the same exit alike;
  rate-limit remains neutral; clean exit while running remains protocol
  violation; signal/no-trailer remains crash; the machine trailer is absent
  from user-visible output.

### P0.4 — bounded fallback browser recovery

Extend `tests/tools/test_browser_supervisor.py` and/or the existing healthcheck
suite. After one successful attach, a permanently dead CDP endpoint must stop
after the configured consecutive-failure budget, evict its registry entry and
allow a later fresh supervisor. A successful reconnect resets the budget and CDP
credentials remain redacted.

### Implemented and verified P0 evidence (2026-09-18)

All P0 slices have landed on branch `fix/workstation-upstream-reliability-p0` and passed their dedicated regression suites:

- **P0.0 (Native Browser Smoke Probe):** `workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs`
  Deterministic discriminators added: `webContents` identity retention, JS timer increment across hide/park, input preservation, scroll preservation, and loopback controller snapshot action execution.
- **P0.1A & P0.1B (Desktop In-Flight Journal & Optimistic Resync):**
  - `npm run test:ui` in `apps/desktop`: 593 test files passed, 5676 tests passed.
  - `npm run test:desktop:platforms` in `apps/desktop`: 126 test files passed, 1783 tests passed.
  - Focused suites: `apps/desktop/src/lib/inflight-turn-journal.test.ts` (39 passed), `apps/desktop/src/app/contrib/hooks/use-background-sync.test.ts` (17 passed).
- **P0.2, P0.3, P0.4 (Active Sessions, Kanban Provenance/Exit Evidence, CDP Reconnect Cap):**
  - Command: `python -m pytest -v tests/hermes_cli/test_cli_resume_read_only_owner.py tests/hermes_cli/test_kanban_provenance_and_exit_evidence.py tests/tools/test_browser_supervisor_reconnect_cap.py`
  - Result: 17 passed in 4.03s.
- **Workstation Isolation Regression:**
  - Command: `python -m pytest -v tests/cron/test_cron_kanban_env_isolation.py tests/tools/test_delegate_kanban_isolation.py`
  - Result: 24 passed in 6.86s.
- **Workstation Python Full Suite:**
  - Command: `python -m pytest -q -o pythonpath=. workstation/tests`
  - Result: 492 passed, 2 skipped in 315.16s.
- **Work100 Execution Reliability Harness:**
  - Command: `python workstation/work100.py --run`
  - Result: 30 PASS / 0 FAIL / 0 gaps.

### Broad gate after focused green

After the affected focused tests pass, run the relevant Workstation Python suite,
Desktop UI/platform suites and typecheck. Native/E2E reruns are mandatory when
the product/runtime/probe paths exercised by H004/H013 change; documentation-only
heads may use the existing carry-forward rule only when Git proves equivalence.

### Observed evidence — implementation 365794e29d

Baseline: c04906aacee568bb6480287717c76afd230cf4a7. Native Windows Python,
provider-free fixtures and isolated HERMES_HOME; no live external mutation.

- Focused compiler/preflight/hardening/browser/routine/policy/progressive gate:
  **113 passed in 185.06s**. This precedes the final snapshot-strength regression
  and ordered-start refinement; both are covered in the final gate below.
- New policy/progressive + compiler gate after evidence-strength correction:
  **39 passed in 64.41s**.
- Final full Workstation and adjacent core gate:
  **570 passed, 2 skipped in 346.25s**, exit 0. The two existing Workstation
  skips remain; adjacent core contributes 79 passing tests.
- Canonical Work100: **30 PASS, 0 FAIL, 0 COVERAGE_GAP,
  0 NOT_RUN_ENVIRONMENT**, exit 0. This catalog result is separate from test counts.
- Desktop owner contracts: **2 files / 36 tests passed**, exit 0.
- git diff --check and git diff --cached --check: exit 0.

Final full gate (repository root):

```powershell
.venv\Scripts\python.exe -m pytest -q workstation/tests tests/agent/test_tool_guardrails.py tests/agent/test_stall_guards.py tests/agent/test_tool_dispatch_helpers.py tests/agent/test_tool_executor_checkpoint_paths.py tests/run_agent/test_tool_executor_contextvar_propagation.py -p no:cacheprovider --basetemp C:/Users/KEVYNL~1/AppData/Local/Temp/hermes-aepc-locked-final-21
```

Canonical gate (repository root; forward slashes keep PYTEST_ADDOPTS paths intact):

```powershell
$env:PYTEST_ADDOPTS='-p no:cacheprovider --basetemp C:/Users/KEVYNL~1/AppData/Local/Temp/hermes-aepc-locked-work100-22'
.venv\Scripts\python.exe -m workstation.work100 --run
```

Desktop contracts (cwd apps/desktop):

```powershell
node C:/Github/hermes-agent/node_modules/vitest/vitest.mjs run --project electron electron/workstation-browser-task.test.ts electron/session-windows.test.ts
```

Initial pytest setup WinError 5 was environmental and resolved by native execution
with external basetemp/no cacheprovider. Initial Work100 had 28 PASS / 2 FAIL
because Vitest could not start: missing Rolldown Windows binding and caniuse-lite.
Restored only @rolldown/binding-win32-x64-msvc@1.2.1 and
caniuse-lite@1.0.30001810 in ignored node_modules, matching installed metadata /
lockfile. No manifest/lockfile or product TS changes. The subsequent Work100 is
green. These contracts use Electron mocks; electron.exe and dist-electron/main.js
were absent. Native authenticated/packaged smoke remains NOT RUN / environment
blocked, not passed. Paid-provider token/cost savings remain unmeasured.

New regressions live in test_execution_policy.py, test_progressive_compilation.py
and the authenticated-controller loop in test_browser_workstation_route.py.
They cover scoped third-operation admission, final middleware arguments,
uncertainty across restart, exact automatic recipe/routine reuse, semantic anchor
reacquisition, owner-declared phases, E1/E2 distinction, seven confirmed steps
before drift, compact handoff and no lost-ACK replay. Simulated discovery uses
3 provider calls versus 0 on promoted replay. Efficiency fixtures additionally
exercise 8 -> 0 and null denominators; neither result measures paid-provider cost.

## Experience Compiler EC0–EC8 validation — 2026-09-18

Baseline: fetched main `2479b712f8a3912ff6df9066d1782e8b407b4177`.
All Python contract gates use Git Bash and `scripts/run_tests.sh`, native Windows
Python, `-j 4 --file-timeout 900`. Sandbox signal-pipe WinError 5 required
escalation; it was an execution-environment failure, not a product defect.

Focused command (final: 116 passed, 0 failed, 8 files, 62.5s):

```bash
scripts/run_tests.sh workstation/tests/test_experience_compiler.py workstation/tests/test_execution_policy.py workstation/tests/test_progressive_compilation.py workstation/tests/test_operational_capabilities.py workstation/tests/test_task_compiler.py workstation/tests/test_routines.py workstation/tests/test_browser_workstation_route.py workstation/tests/test_semantic_validation_and_capabilities.py -j 4 --file-timeout 900
```

Full command:

```bash
scripts/run_tests.sh workstation/tests -j 4 --file-timeout 900
```

First full run: 545 passed, 0 failed, 2 skipped, 56 files, 255.7s.
Expanded run: 547 passed, 0 failed, 2 skipped, 56 files, 230.3s.
Final full: **550 passed, 0 failed, 2 skipped, 56 files, 226.8s**.
The final strict observed-binding guard was checked by the focused regate after
the broad run's compiler file completed; no other product changes followed.
Compiler contracts include
40 tests: browser fixture replay, real temp-file write/hash readback, real subprocess
exit readback, learned filesystem/process composite, two atomic reuse flows,
strict unique anchors, corrupt-index refusal, task-run pins and causal C5 fixtures.
Automatic mining incorporates matching failure segments; missing predicates remain
unresolved evidence. Conditional browser replay is checked from the persisted
registry in both banner states. Source refs resolve to original corpus artifacts.
Large capability outputs use the existing reference plane; real large-file
readback and confirmed-result resume preserve compact context.
These prove contracts and local integration, not a live authenticated product task.

Work100 command: `.venv\Scripts\python.exe workstation/work100.py --run`.
Result: **30 PASS; 0 FAIL; 0 COVERAGE_GAP; 0 NOT_RUN_ENVIRONMENT**.
Repeated after final product changes with the same result.
The catalog includes two executed Electron contracts; this remains distinct from
native Windows/Desktop E2E. No TypeScript/Electron product source changed.
Standalone UI/typecheck/build gates were not required for this Python milestone.
Native environment: Electron is hoisted at
`node_modules/electron/dist/electron.exe`; the absent workspace-local binary is
not a blocker. `apps/desktop/dist/electron-main.mjs` exists. Existing H004 native
smoke passed after final Work100:

```text
node workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs
```

Exit 0; `H004_CLASSIFICATION=VALIDATED`, `H004_A_CONTROLLER_ACTION_PASS`,
`H004_LIVE_DESTROY_PASS`, `H004_RESTART_PASS`; Windows 10.0.26200 / Electron 40.10.2.
Real isolated profiles, live WebContentsView identity, explicit destruction,
two distinct restart processes, lazy recovery and structural secret isolation.
Its scope is BrowserTask lifecycle/recovery and secret isolation;
packaged/full Experience Compiler product E2E was not part of this qualification.
Paid-provider economics, global capability coverage and novelty remain unknown;
compiler metrics emit null for unsupported denominators. No destructive production
experiments or historical third-party mutations were replayed.

Adjacent owner command (8 passed, 0 failed, 2 files, 11.9s):

```bash
scripts/run_tests.sh tests/agent/test_tool_guardrails.py tests/agent/test_tool_executor_checkpoint_paths.py -j 4 --file-timeout 900
```

Final documentation gate:
`scripts/run_tests.sh workstation/tests/test_context_docs.py -j 4 --file-timeout 900`
— 4 passed, 0 failed (1.1s). Final `git diff --check` passed.

Canonical target:
[EXPERIENCE_COMPILER.md](EXPERIENCE_COMPILER.md).

Implemented focused behavior tests cover:
- TransitionSample normalization and semantic state deltas;
- ref-only Browser traces receiving derived semantic identity;
- capture/replay anchor-type consistency;
- segmentation of redundant observation/wait/scroll from a successful trace;
- cross-trace alignment and anti-unification;
- conservative precondition/effect/conditional-branch inference;
- success/failure contrast and Operational Slice reduction;
- observational C0-C2 versus replay/ablation C3-C5 causal grades;
- prohibition of destructive production ablation;
- provenance/taint-aware promotion;
- learned mutation not auto-promoting from raw validation count alone;
- immutable counterexample refinement/versioning;
- TaskRun-stable capability-version view;
- exact promoted replay with zero new operational-planning LLM calls;
- browser/filesystem lifecycle parity and cross-backend composition.

Python execution must follow the repository root `AGENTS.md`: use
`scripts/run_tests.sh`, never direct `pytest`, for current implementation
validation. Historical commands below are evidence records from prior runs and
are not the current invocation rule.

Expected focused files should include a dedicated
`workstation/tests/test_experience_compiler.py` (or a small cohesive package)
plus existing regression owners:
`test_execution_policy.py`, `test_progressive_compilation.py`,
`test_operational_capabilities.py`, `test_task_compiler.py`,
`test_routines.py`, `test_browser_workstation_route.py` and any Electron
runtime tests changed by semantic-state capture.

After focused green, run the full Workstation wrapper gate and
`python workstation/work100.py --run`; if Electron/browser product code changes,
run the corresponding Desktop Vitest/typecheck/native qualification required by
the existing ladder.

## Validation ladder

The read-only bootstrap regression is documented in
[`READONLY_DURABLE_PREFLIGHT.md`](READONLY_DURABLE_PREFLIGHT.md).
Run `test_readonly_preflight.py` and the existing compiler/canary/hardening tests;
then the complete Workstation suite, canonical core runner, Electron platform
suite and Desktop typecheck. Fake providers only; historical effects are never
replayed against Trello.

Use the smallest focused gate first, then expand only after it passes:

1. **Pure/unit behavior** — extracted logic, state transitions, serialization, routing decisions, host/geometry helpers.
2. **Workstation contracts** — `workstation/tests/` for Python-side routing/config/integration contracts.
3. **Desktop UI tests** — renderer behavior through Vitest/React tests when UI state or actions change.
4. **Desktop platform tests** — Electron/main-process behavior for `WebContentsView`, BrowserRuntime, host ownership, persistence, and IPC contracts.
5. **Desktop typecheck/build gates** — compile changed contracts across renderer/preload/main boundaries.
6. **Windows Desktop E2E/smoke** — required for claims depending on real Electron/Windows composition, restart, profile persistence, or native view behavior.

Do not replace executable behavior tests with source greps. Source-shape tests are acceptable for bootstrap/build policy but are not substitutes for runtime behavior.

## Existing Workstation gates

### `Workstation CI`

- component lock validation;
- third-party license validation;
- `workstation/tests/`;
- downstream integration-anchor check in read-only `--check` mode.

### `Workstation Browser Windows`

- Node/Python setup;
- read-only committed-integration validation;
- normal `workstation\\install.cmd` execution;
- clean-checkout assertion after install;
- production dependency audit with `npm audit --omit=dev --audit-level=moderate`;
- strict `workstation\\doctor.cmd -Strict` dependency/integration gate;
- four-session Workstation reconnect soak with JSON and durable evidence upload;
- Dashboard Playwright browser installation and provider-free cross-engine smoke;
- Desktop unpacked packaging and packaged GUI/HUD E2E smoke;
- isolated Workstation validation dependencies for the release qualification
  Python test runner;
- uploaded release and Desktop E2E evidence artifacts;
- Desktop typecheck;
- BrowserSessionState lint/format;
- focused BrowserSessionState resilience plus BrowserTask lifecycle/runtime step;
- H010 native clean/fault/abrupt restart probe;
- H011 native hidden-window Browser runtime reconnect soak;
- H012 real headless `hermes serve` multi-session/reconnect soak;
- H013 integrated hidden-window Desktop/Browser load E2E;
- Desktop UI tests;
- Desktop platform/Electron tests;
- final aggregator that remains red if a scoped or broad required outcome is red.

The UI and platform steps may continue after failure only so both outcomes are observable. This is diagnostic non-masking, not failure tolerance.

### Mainline Consolidation contracts

`workstation/tests/test_mainline_consolidation.py` protects the extraordinary
pre-1.5 gate record:

- all PRs #1–#12 and every branch observed at the audit base have a disposition;
- no material `NEEDS INVESTIGATION` remains;
- D-012 and the recurring Mainline Consolidation Review are canonical;
- roadmap order is BrowserSessionState → Gate → V1 #1.5 → V1 #2 hardening;
- promoted BrowserSessionState evidence is not described as pending.

The test protects the durable record; GitHub live state is still inspected and
recorded during an actual gate/review rather than mocked by source assertions.

### Desktop Browser schema capability

`tests/tui_gateway/test_workstation_browser_schema_capability.py` proves:

- Desktop capability survives a false controller reachability probe;
- Desktop tool-definition cache state cannot leak into TUI;
- process-global `HERMES_DESKTOP` cannot grant TUI capability;
- Desktop source identity is sufficient without that env flag;
- the forced Workstation set remains narrow (`browser_exec` is not promoted).

### BrowserTask pure lifecycle

`apps/desktop/electron/workstation-browser-task.test.ts` proves:

- hide and park preserve the logical live page;
- destroy is explicit;
- one logical record exists per task;
- switching the visible task parks the previous task;
- malformed/duplicate persisted metadata is pruned;
- restart restoration is parked and page recovery is lazy;
- persisted task structure excludes page-scoped secret content.

### BrowserTask runtime adapter

`apps/desktop/electron/workstation-browser-runtime-task.test.ts` exercises the real `WorkstationBrowserRuntime` with Electron mocked and proves:

- `ownerTaskId` is idempotent in the Chromium tab primitive;
- hide/park/show retain the same WebContents and URL within one process;
- explicit task destroy closes the owned page;
- restart restores logical metadata first and creates one page only when shown again;
- renderer crash recovery creates one replacement page under the same task.

### BrowserSessionState composite and resilience

`workstation-browser-session-state.test.ts`,
`workstation-browser-session-state-resilience.test.ts`, and
`workstation-browser-runtime-resilience.test.ts` prove:

- ordinary/task logical tab order and active selection round-trip without live
  page objects;
- safe URL/title metadata excludes credentials and suspicious path/query forms;
- BrowserTask metadata shares one composite persistence file and legacy state
  migrates once;
- malformed/newer state fails safely;
- atomic replacement never exposes partial JSON;
- after a failed task or session write, a later successful write converges both
  halves to the latest intended in-process projection;
- failed explicit destroy cannot be resurrected by a later session save;
- runtime cleanup converges even when the persistence boundary throws.

## V1 #1 real Windows acceptance evidence

The promoted probe is versioned at:

`workstation/context/engineering-journal/probes/h010-native-browser-session-state-smoke.mjs`

Validated exact head:

- repository head: `d5be442021ea0c744351622317eef5212219786d`;
- Windows: `10.0.26100`;
- Electron: `40.10.2`;
- outer Node: `v26.8.1`.

Observed markers include:

- `H010_PHASE_A_PASS` and `H010_PHASE_B_PASS`;
- `H010_NATIVE_FAULT_CONVERGENCE_PASS`;
- `H010_NATIVE_DESTROY_FAILURE_CLEANUP_PASS`;
- `H010_ABRUPT_PHASE1_DURABLE` and `H010_ABRUPT_RESTART_PASS`;
- `H010_CLASSIFICATION=VALIDATED`.

The probe used distinct Electron PIDs for restart, real WebContentsView/profile
behavior, a forced persistence failure seam and an abrupt non-clean first
process exit. It proved lazy exactly-one-page task recovery and profile/state
separation; it did not prove any later Chat/Hub/Preview or Kanban feature.

### Current working-tree rerun — 2026-09-12

The same versioned probe passed locally against checkout `HEAD`
`d77901a6857cf90f9401a90377de3b6ee5254bef`, on Windows `10.0.26200`, Electron
`40.10.2` and Node `v26.7.0`. It emitted all clean, fault, destroy and abrupt
restart pass markers and ended with `H010_CLASSIFICATION=VALIDATED`.

This rerun imported the current working-tree files while the checkout was
dirty, so it is native local evidence for the current code, not a substitute
for the workflow's clean-checkout/clean-machine promotion gate.

## Native Browser runtime reconnect soak

`workstation/context/engineering-journal/probes/h011-native-browser-runtime-soak.mjs`
uses real Electron `WebContentsView` instances in hidden `BrowserWindow`
hosts. It repeatedly navigates four task-owned pages, alternates `hub`/`chat`
host ownership, hides or parks the active task, validates resource/session/tab
identity, shuts the process down cleanly, and restores the composite
`BrowserSessionState` in a fresh process. Restart episodes first assert parked
lazy metadata, then explicitly warm the task pool for multi-task coverage.

The 2026-09-12 local run passed **39 episodes / 936 iterations / 4 tasks** in
the 60-second budget and emitted
`H011_NATIVE_BROWSER_RUNTIME_CLASSIFICATION=VALIDATED`. The probe is native
runtime evidence, not a claim of clean-machine release qualification or a full
agent/backend production workload; the Windows workflow runs it as a required
60-second gate and uploads the report plus durable JSON projection.

## Headless backend multi-session reconnect soak

`workstation/context/engineering-journal/probes/h012-headless-backend-reconnect-soak.py`
starts the real `hermes serve` headless backend, connects through its
authenticated production WebSocket gateway, drives concurrent desktop-shaped
sessions and streamed synthetic turns, then restarts the backend and resumes
the durable session identities from the same isolated `HERMES_HOME`. The
synthetic turn seam is deterministic and token-free; the backend process,
JSON-RPC transport, session persistence and concurrent dispatch are real.

The 2026-09-12 local workflow-shaped run passed **12 cycles / 48 turns / 44
reconnects / 2 backend restarts / 48 heartbeats**, with **192 streamed events**,
zero errors and a maximum of **4 concurrent turns**. It emitted
`H012_HEADLESS_BACKEND_CLASSIFICATION=VALIDATED`. This is stronger backend
boundary evidence, but it does not claim real-provider quality or a clean
machine/full Desktop-and-Browser production deployment; the Windows workflow
runs the same probe with a 120-second budget and retains its JSON evidence.

## Integrated Desktop/Browser headless load E2E

`apps/desktop/e2e/workstation-headless-load.spec.ts` runs the real dev Electron
shell with the real `hermes serve` backend from the mock-backend fixture while
keeping every native window hidden. It starts a deterministic local HTTP server,
drives four native Chromium BrowserTasks concurrently through the authenticated
controller, compares the complete `/resources` and `/events` projections with
Desktop IPC (including state, lineage, evidence and event payloads), and
exercises hide/park/destroy cleanup. The inference provider is synthetic and
token-free; Chromium, BrowserTask lifecycle, controller authentication and IPC
are real.

The local default run passed **2 tests in 36.6s** (a later formatted rerun
passed in 38.8s): the four-task identity/geometry scenario and a sustained
scenario with eight concurrent BrowserTasks, three navigation/snapshot rounds
and three real backend chat turns. Both exercised native host-aware transfer
and maximize/restore reconciliation with no visible Electron window.
The Windows release workflow runs the same H013 gate with an explicit
`HERMES_DESKTOP_E2E_HEADLESS=1` environment plus a larger bounded profile of
16 tasks, up to 300 rounds or 120 seconds, and 8 real backend chat turns. It
also emits a bounded JSON report and rejects missing or under-sized evidence
through the read-only `python -m workstation.desktop_load_evidence` validator
before the final aggregator; the clean-machine execution and this scaled
profile remain release-candidate evidence gates.
A local run of that exact 16-task/120-second/8-turn profile passed **2 tests in
3.0 minutes**, completing 170 rounds with 120,651 ms observed and no Electron
process remaining. It is local toolchain evidence, not clean-machine release
qualification.

## Host-aware viewport geometry

`apps/desktop/electron/workstation-browser-runtime-viewport.test.ts` covers the
shared-window geometry boundary: stale Chat/Hub `setBounds` calls are ignored
when their expected host is not the current owner, valid bounds are normalized
for Chromium zoom and clamped to the native content rectangle, transfer between
two `BrowserWindow` hosts preserves exactly one live view, and native window
resize/maximize/restore events reapply the active bounds. H013 validates that
matrix with a real hidden Electron/Chromium view; broader compositor-race and
clean-machine Windows evidence remain hardening gates.

## BrowserTask lifecycle policy

BrowserTask tests must distinguish **logical task persistence** from **process-local page identity**:

- within one Electron process, `create -> hide -> show` and `create -> park -> show` retain the same live page object and current URL;
- `hide`/`park` do not close the WebContents;
- `destroyTask` is the operation that removes the task and closes its owned page;
- repeated creation for the same `taskId` does not allocate a second page;
- if a page crashes/disappears while the logical task remains, recovery may create exactly one replacement and records that recovery;
- after Desktop process restart, metadata restores as parked before any page is recreated; showing/using the task may lazily recreate one page under the same task id;
- tests never claim that renderer JavaScript heap or a WebContents object survives process restart.

Use the pure lifecycle test first, then the runtime-adapter test, then the real Windows smoke.

## Implementation 4 real Windows acceptance evidence

The required narrow native smoke is versioned at:

`workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs`

Validated execution:

- repository head: `d8acc752133b125b9619cbc7fe09199f1283a22b`;
- code-bearing BrowserTask ancestor: `1ac0e0a9ecaaf1c53ee0f8abfc3d8a1d802cae70`;
- Windows: `10.0.26200`;
- Electron: `40.10.2`;
- outer Node: `v24.14.1`;
- Electron Node: `24.15.0`.

Observed native markers:

- `H004_READY` before product import;
- `H004_RUNTIME_IMPORTED` before lifecycle operations;
- `H004_LIVE_DESTROY_PASS`;
- `H004_RESTART_PASS`;
- `H004_CLASSIFICATION=VALIDATED`.

The smoke used real `BrowserWindow`, real `WebContentsView`, real renderer execution, and two distinct Electron OS processes. It proved:

1. same task id, task-owned tab id, WebContents identity/id, URL and renderer sentinel across hide/show and park/show;
2. exactly one page owned the task throughout the live lifecycle;
3. explicit `destroyTask` destroyed the page and removed logical/page ownership without automatic replacement;
4. restart restored the same logical task as parked/restored with zero eager pages;
5. first show after restart created exactly one page and recorded `recreated`;
6. BrowserTask structural persistence excluded the test page URL secret and renderer secret.

This smoke is sufficient for the **Implementation 4 lifecycle boundary only**. It does not validate future Chat Browser View, Browser Hub, Preview unification, host transfer/resize, complete BrowserSessionState, or complete SessionDB/Kanban/run linkage.

### Native smoke carry-forward rule

A native smoke may be associated with a later final documentation-only head without rerunning the physical Electron test only when all of the following are proven:

1. the smoke SHA and final head are in a direct ancestry relationship;
2. Git comparison shows no change in the product files whose behavior was exercised;
3. the executed smoke probe itself is unchanged;
4. changes after the smoke are documentation-only and cannot affect runtime/bootstrap/dependency resolution;
5. automated gates are observed on the exact final head;
6. the equivalence is recorded in the final evidence/report.

If any runtime, dependency, workflow, probe, or product path changes after the smoke, rerun the native smoke on the new head.

## Implementation 4 promotion closure

Implementation 4 was promoted through PR #9 with accepted head `75d10d35d4757496390debf8e4b4f9efb44c5432` and merge commit `fada723f43613e5e0f061cab24445573ac298998`.

### Controlled Windows causality comparison

A native-Windows side-by-side run used the same toolchain/install/commands against:

- baseline: `ce78f120e8ed2974d6174e475cc7572afcfe41e0`;
- candidate: `2ffee2335b6aba071e7b63457a047cd9334d4d92`.

Observed:

- baseline UI legacy: 5 failed files / 11 failed tests;
- candidate UI legacy: 5 failed files / 9 failed tests;
- baseline platform/Electron legacy: 11 failed files / 33 failed tests;
- candidate platform/Electron legacy: 10 failed files / 28 failed tests;
- all remaining candidate failures matched an identical baseline failure or a variant of the same causal class;
- candidate-specific BrowserTask tests passed 2 files / 16 tests;
- candidate typecheck passed.

Verdict: `WINDOWS_BASELINE_COMPARISON=PASS_WITH_KI-006_RED`.

### Exact-final-head evidence

Git comparison proved that changes from controlled candidate `2ffee...` to accepted head `75d10d35...` were limited to contributor-attribution mapping and Workstation engineering-journal material. BrowserTask product/runtime/probe/workflow/dependency code did not change.

On `75d10d35...`:

- `Workstation CI` passed;
- Docker Build/Test/Publish passed;
- contributor attribution passed after the missing mapping was added;
- Windows committed-integration validation passed;
- normal Workstation install passed and kept the checkout clean;
- Desktop typecheck passed;
- focused BrowserTask lifecycle tests passed;
- broad UI/platform diagnostics ran;
- the final Windows aggregator remained red, preserving KI-006 instead of masking it.

Because no material code changed after the controlled A/B, the final-head Windows red is classified `KI-006_ONLY_BY_CONTROLLED_EQUIVALENCE`, not as a new Implementation 4 regression.

The promotion merge was executed with `expected_head_sha=75d10d35d4757496390debf8e4b4f9efb44c5432`; `main` was then verified at `fada723f43613e5e0f061cab24445573ac298998` with parents `ce78f120e8ed2974d6174e475cc7572afcfe41e0` and `75d10d35d4757496390debf8e4b4f9efb44c5432`.

## Native validation harness policy

The Implementation 4 investigation produced reusable harness lessons that are now regression knowledge:

- instrument explicit markers for process boot, Electron readiness, product import, and each lifecycle boundary;
- do not attribute a timeout to product code before the product-entry marker occurs;
- use Node `child_process` for Windows native orchestration in this path instead of stacking PowerShell native pipelines and `.cmd` wrappers;
- gate process success on exit status, not stderr output;
- use a valid temporary Electron application entry;
- on the current Windows/Electron 40.10.2 target, do not block module evaluation with top-level `await app.whenReady()`; the paired H-003 control proved `.then(...)` reaches readiness while TLA stalls in that environment;
- once a versioned probe exists, reuse/improve it instead of reconstructing ad hoc runners.

Operational history is kept in `engineering-journal/CURRENT.md`.

## Baseline comparison for pre-existing failures

When a broad gate is already red on `main` and blocks causality for a narrowly scoped change, reproduce the exact main base and candidate with the same OS/toolchain/install/commands. Compare failure signatures rather than failure counts.

A baseline/candidate A/B may establish that a failure is pre-existing and that the scoped change is non-regressive, but it must not be described as a green broad gate. Keep the permanent gate red until its underlying issue is fixed.

For the current Windows baseline see KI-006 in `KNOWN_ISSUES.md`.

### KI-006 Windows portability closure

The follow-up HW-018 closure was validated on the current Windows working
tree with the same broad suites that exposed the historical debt:

- Desktop UI: **591 files / 5,669 tests passed** with Vitest bounded to
  `--maxWorkers=4` on the current Windows audit host;
- Desktop platform/Electron: **126 files / 1,778 tests passed, 5 skipped**;
- Desktop TypeScript typecheck: **0 errors**.

The closure preserves strict POSIX mode checks, explicit Windows ACL/no-mux
semantics, cross-platform path contracts, non-blocking WSL selection, Git cwd
cleanup and locale-deterministic UI formatting. No test file was deleted,
skipped solely to hide a failure, or weakened into a claimed pass.

### Dashboard/TUI resource and event adapter parity

`workstation/tests/test_client.py` includes a real authenticated loopback HTTP
controller and invokes both high-level surfaces against it for both projections:

- Dashboard's `/api/workstation/resources` handler;
- TUI's `workstation.resources` JSON-RPC handler.
- Dashboard's `/api/workstation/events` handler;
- TUI's `workstation.events` JSON-RPC handler.

Both surfaces must return the same normalized envelope and the same
browser/task/journal identities and event lineage for one logical session. The
current test file passes **5/5** and the full Workstation suite passes
**247/247**. This is adapter and transport evidence; it does not replace
packaged Electron, clean-machine or production soak evidence.

### Provider-free workload benchmark

`python -m workstation.workload_benchmark` produces deterministic structural
counters from synthetic fixtures. The versioned expected values live in
`workstation/benchmarks/workload_baseline.json` and are asserted by
`workstation/tests/test_workload_benchmark.py`. The benchmark covers inline vs.
reference-first tool results, deduplication, worker restart/ACK recovery,
operational compaction references, structured policy classifications and event
invalidation. It intentionally does not commit private databases or use
wall-clock thresholds.

## Required browser-foundation invariants

As corresponding implementations land, tests must establish relationships rather than freeze incidental values:

- GUI/Desktop browser surface capability is session-scoped;
- controller reachability affects execution/recovery, not whether a valid session surface is known;
- BrowserTask can hide/show/park without replacing a live page;
- destroy is explicit and different from hide;
- task-bound controller loss is fail-closed;
- routing-disabled stays internal-only;
- future Chat Browser View and Browser Hub reference the same BrowserTask/runtime;
- only one host owns the live `WebContentsView` at a time;
- future host transfer/resize does not overlap;
- multiple BrowserTasks remain isolated;
- BrowserSessionState restoration preserves safe logical metadata without credentials;
- Chromium profile persistence is tested separately from logical task/session restoration;
- future Preview compatibility in Workstation mode does not create an independent duplicate lane.

## Later full browser-foundation smoke

The final broader browser foundation, after later surfaces exist, must also cover Chat Browser View ↔ Browser Hub shared task/page behavior, human control, resize/maximize/restore, second-task isolation, profile login persistence, controller-loss fail-closed behavior, and Preview compatibility.

Those later steps must remain future work; the narrower Implementation 4 pass must not be used to mark them complete.

## Release qualification and bounded soak

Run the release gate from the candidate checkout:

```powershell
& .venv\Scripts\python.exe -m workstation.release_qualification --root . `
  --clean-install-evidence C:\path\to\clean-install-report.json `
  --report .\release-qualification.json
```

The runner first requires a clean candidate checkout, then executes ownership,
assets, Workstation smoke, native smoke and
migration locally, but accepts the `clean_install` stage only when an external
clean-machine report is marked accepted and carries the exact candidate
`HEAD` revision. It stops at the first failed or missing stage and bounds
subprocess output/time; it does not install, repair or promote a release.
The minimum accepted external evidence shape is:

```json
{"accepted": true, "candidate_revision": "<exact HEAD>", "workstation_home": "<absolute isolated path>", "stages": ["clean_install"]}
```

The Windows workflow allocates that home under `RUNNER_TEMP`, persists it via
`GITHUB_ENV` for both install and doctor, verifies its `Runtime` and `Browser`
directories and includes the path in the candidate-matched evidence. The
qualification runner rejects accepted reports that omit the field, use a
relative path or point inside the candidate checkout.

Local verification also materialized the current working tree as an isolated
synthetic candidate, ran the real install/`npm ci`/Desktop build and strict
doctor with an external Workstation home, and passed all six qualification
stages. The hidden H013 profile on that candidate passed **2/2** (16 tasks,
173 rounds, 120,262 ms, 8 chat turns) and the shared evidence validator accepted
the report. This is local candidate evidence; official clean-machine CI is
still required for promotion.

`SoakRunner.run_for_duration()` provides an iteration cap, elapsed duration,
completed-iteration count and explicit timeout state for a production-like
scenario harness. The Windows workflow runs the canonical four-session process
restart scenario for a 180-second budget with a 3,000-iteration cap, validates
zero failures/errors and at least one completed iteration, and uploads both its
JSON report and durable root. The canonical contract scenario can also be
sampled locally with:

```powershell
& .venv\Scripts\python.exe -m workstation.soak --duration 60 --iterations 1000
```

It executes each iteration in a fresh Python process and exercises multiple
session leases, durable session metadata, model changes, migration,
cold-session reload, memory snapshot/restore, journal append/read and worker
stop/reconstruct lineage. Those metrics make a soak report auditable. Neither
the CI contract soak nor a short local run turns into long-duration
Desktop/Browser production evidence; that remains a separate acceptance gate.

Latest local sample: **77 fresh-process iterations, 0 failures, 1,155 actions,
924 journal events, 26,796 memory records, 231 snapshots and 228 worker
reconstructions** across three sessions. `timed_out=true` is the expected
duration-budget marker when the runner stops after 60 seconds.

Latest extended local sample: **128 fresh-process iterations, 0 failures, 2,560
actions, 2,048 journal events, 15,888 cumulative memory records, 512 snapshots
and 508 worker reconstructions** across four sessions, with 508 model changes
and 508 cold reloads, in a 180-second budget. Live memory peaked at **32
records**, exactly the explicit eight-record-per-session bound. `timed_out=true`
remains the expected duration-budget marker; this is stronger local evidence
but does not promote the separate production-like Desktop/Browser soak gate.

## Failure policy

A full POSIX core run needs GNU coreutils and ripgrep for the executable-option
security probes. A different `sort` implementation does not establish GNU option
behavior. The canonical per-file runner retains isolated temporary roots and
uses a short prefix so AF_UNIX socket paths fit the operating-system limit.
Work100 uses the shared Hermes Node resolver, including managed installations.
Release qualification runs the complete Workstation suite through the same
per-file runner with four workers and zero retries. Its configured aggregate
timeout is unchanged; every file also receives that timeout as a hard bound.

A red gate is investigated, not disabled. Never make CI green by deleting coverage, weakening a valid expectation, or turning a baseline-equivalent failure into a claimed pass. Record what failed, establish causality, and use the smallest test that corresponds to the actual risk.

## Canonical Work Loop regressions

Run `python -m pytest -q workstation/tests` and affected Kanban/guardrails/cron/
SessionDB/verification-ledger tests. Use native Windows Python and a fresh
`--basetemp` outside the checkout: fixture project-root resolution can identify
Hermes instead of a nested synthetic project. Workstation conftest redirects
both homes and Kanban DB.

Key suites:
- `workstation/tests/test_canonical_work_loop.py`: 35 passed tests covering stale run late completion rejection, terminal parent reconciliation (Cases A & B), lineage persistence (`run_id`, `execution_key`, `operation_id`), 120-event streaming hash integrity benchmark, human takeover mutation revocation and fence invalidation, and end-to-end cockpit lineage projection.
- `workstation/tests/test_canonical_continuity.py`: 14 passed tests covering `db_path` str/Path connectivity, browser readiness contracts, and execution loop continuity.
- `python -m workstation.work100 --run`: 30 seed cases with 0 coverage gaps, executing 35 pytest tests and 36 Electron/desktop tests cleanly.

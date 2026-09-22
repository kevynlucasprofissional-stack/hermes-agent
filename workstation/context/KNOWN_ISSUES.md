# Workstation Known Issues

## KI-020 — Normal-turn Progressive Compilation pre-reasoning closure is not yet promoted [OPEN — LOCAL WIP EXISTS]

The Capability Runtime, Experience Compiler and routing substrate exist, but shared `main` does not yet prove that a normal Hermes turn can execute a promoted capability before the next provider LLM call.

A direct attempt (`471e9b529f745c89a3b18caad865e762f09dfab3`) was reverted because it fabricated an invalid intent, used a fake-success dispatcher fallback, could fall through to the LLM after deterministic dispatch, directly coupled generic core to Workstation, and lacked real-turn acceptance tests.

A subsequent Claude Code session reportedly implemented a generic `agent/` operational-resolution boundary plus Workstation provider on local branch `integration/upstream-20260922-71a2fe39-h0793`, with focused tests green. That branch was not observed on GitHub and the mandatory real-turn tests were not completed.

Closure requires all of:
- known promoted capability via a real normal turn => exact-once dispatch, canonical VERIFIED result, provider calls = 0;
- no match/insufficient trusted intent => normal provider reasoning;
- invalid certificate / drift / quarantine / uncertain mutation / verifier failure fail safe;
- canonical finalization preserved for SATISFIED / EXECUTED / WAIT / HANDOFF;
- `workstation/upstream_interventions.json` created/backfilled for active upstream interventions;
- exact-head focused+broad qualification and final upstream drift classification.



## KI-019 — Anthropic routing contract lacks a real SDK construction proof [CLOSED LOCALLY — CI PENDING]

Workstation CI correctly installs `--extra anthropic`, but the provider-routing test still mocks `build_anthropic_client`. Keep that unit test, and add a no-network integration contract that exercises the installed SDK through the real builder path with dummy credentials. Anthropic remains an optional extra, not a new core dependency.

Closed by `workstation/tests/test_anthropic_sdk_construction.py`; both routing-unit and real installed-SDK construction paths pass without network access.

## KI-018 — Windows release gate mixes POSIX/macOS fixtures into Windows execution [CLOSED LOCALLY — CI PENDING]

The Workstation Browser Windows workflow passes the major product/browser path but remains red because several tests assert POSIX/macOS behavior while running on Windows. Observed examples include macOS media/TCC exclusions, `/bin/sh` managed-update paths, and POSIX `lib/pythonX.Y/site-packages` layout.

Required action: make the tests platform-correct or conditionally scoped without hiding portable regressions. The release gate must become genuinely green.

Platform-correct fixtures now preserve portable assertions while scoping POSIX-only filesystem/shell behavior. Local Electron platform result: 2,453 passed / 40 skipped.

## KI-017 — One-click dogfood fails on an existing supported venv without pip [CLOSED LOCALLY — CI PENDING]

Reproduced on Windows: `workstation/install.ps1` accepts an existing supported `.venv` and later unconditionally runs `python -m pip install -e .`. uv-managed/pipless venvs therefore fail with `No module named pip`.

A semantic fix and a real `--without-pip` regression fixture exist on the old integration branch (`90dbc446...`, `120165eb...`) but are not ancestors of current main. Re-adopt them only after the fresh H-079.2 upstream merge.

Re-adopted after the fresh merge. The real pipless fixture installs with `uv`; no-uv fallback bootstraps and verifies pip; invalid existing interpreters fail before installation; doctor passes and tracked checkout state remains unchanged.


> **Identifier warning.** `KI-007`…`KI-010` are used by **two numbering scopes** in this file: the
> file-level registry and the self-contained "Canonical Work Loop Reliability Gaps" section at the
> end, which restarts its own numbering. `KI-012` is duplicated even within the file-level scope.
> Resolve an identifier through [`ID_DISAMBIGUATION.md`](ID_DISAMBIGUATION.md) before citing it.
> New issues take `KI-017` and above — do not reuse a retired number.

## KI-016 — Post-H-076/H-077 false-confidence residuals can still overstate operational truth [IMPLEMENTED — EXACT-HEAD CI PENDING]

Post-merge audit of `main@92a3acb51e87af85a9f380ee04d2cf47d7900ca5`
confirmed that PR #36 closed several original seams but not the full truth boundary.

Open residuals:
- TaskCompiler can validate/complete a kernel ACK whose canonical verification is not VERIFIED;
- evidence provenance/strength/trust/failure-domain can be backfilled from contract requirements;
- expected task/run lineage is accepted but not enforced;
- ValidityEnvelope can tolerate missing required context and is not yet reuse admission;
- external metrics can be optimistic when external oracle coverage is absent;
- AFB-v0 contains hand-labelled result rows rather than a fully generated external oracle path;
- explicit model-inadequacy quarantine is not fully automatic in normal compilation;
- success/replay/savings counters can count non-VERIFIED execution ACKs.

Still resolved from PR #36: routing-time ORA inflation, optimistic verified defaults,
unknown conditions, direct expected-value evidence, resource identity/version checks,
operation-id transition matching and boolean-verifier terminal truth.

Required action: H-077.1. No new state owner is required.

Canonical:
[H077_1_QUALIFICATION_CLOSURE_2026-09-19.md](H077_1_QUALIFICATION_CLOSURE_2026-09-19.md).

## KI-015 — "Verified" could encode correlated, stale or under-specified evidence [RESOLVED — H-076]

Post-PR #33 audit shows that the execution/control substrate is present, but verifier
semantics remain too shallow in several production paths.

Reproduced code-level risks:
- TaskCompiler can assign E3 when verifier metadata is absent in one fallback path;
- Router treats verifier dict presence as sufficiency and normally sets state_fresh=True;
- Dispatcher can accept executor-produced verification.accepted through its verifier
  callback;
- OperationalKernel can label learned work verified from same-surface semantic
  observation;
- RunClosureProof accepts a non-empty verifier_contract without proving validated
  lifecycle, freshness, fault-domain admissibility or predicate coverage;
- Experience Compiler reduces verifier knowledge mainly to effects/minimum evidence,
  losing reusable observer/extractor/relation/freshness/provenance detail.

Resolved behavior: H-076 removes undeclared E3 promotion, makes canonical
VerificationResult govern commit, requires validated/fresh/covered RunClosure proof,
preserves disagreement as CONFLICT, and requires separate positive/negative verifier
receipts. Full Workstation regression: **670 passed, 2 skipped**.

Canonical:
[VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md](VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md).

## KI-014 — Verified adaptive procedure stays in the LLM loop instead of handing off in-flight [RESOLVED — H-075, 2026-09-19]

**Resolution:**
Closed via in-flight operationalization handoff across Phases P1-P6:
1. **RunClosureProof & Utility Admission (`workstation/run_closure.py`):**
   - 21 canonical fields capturing lineage, semantic fingerprint, target family, route, verifier contract, authority containment, replay evidence, parameter bindings, and remaining equivalent work.
   - `evaluate_run_local_closure()` enforcing 10 admission conditions including positive operational utility threshold.
2. **Adaptive-to-Compiled Handoff & Prefix Recovery:**
   - Synthesizes `ExecutionEnvelope` and transfers remaining fan-out to `DurableBatchRunner` without LLM re-entry.
   - `RunScopedCapability` strictly fenced to `task_id`/`run_id`/`operation_id` and excluded from global registry.
   - `recover_verified_prefix()` recovers committed items from `DurableTaskStore` and prevents duplicate replay after mid-batch interruption.
3. **Browser Lowering & Artifact Data Plane (`tools/browser_workstation.py`, `apps/desktop/electron`):**
   - Browser lowering maps rich text editors to `browser_type` with `plain_text_paste` semantic primitive, rejecting opaque `browser_console` traces from promotion.
   - `resolve_browser_type_text()` resolves `text_ref`/`artifact_ref` at the trusted boundary, enforcing task ownership, <=1MB size, and text/json MIME type.
4. **Qualification Receipt:**
   - Qualified by 12-item Trello-shaped benchmark (`test_trello_benchmark_qualification.py`) demonstrating canary + replay, handoff of 10 items, large >50KB artifact ref resolution, deliberate anomaly handling with `AttentionPacket`, prefix recovery, and clean resumption of remaining items without duplicate replay.


## KI-013 — Operational knowledge hierarchy is not closed end to end [RESOLVED — H-075, 2026-09-19]

**Resolution:**
All open integration seams identified in the H-075 post-merge audit were resolved and verified across Phases P0, P4, and P5:
1. **P0 (Decision Seams, Final-Goal Verification, Conservative Derivation):**
   - `workstation/task_compiler.py`: Route decision branches (`WaitDecision`, `HumanDecision`, `ReasoningDecision`, `ComposedDecision`) strictly consume real dataclass fields.
   - `workstation/control_plane/composition.py`: Composed execution enforces authoritative final-goal verification, dependency satisfaction, verifier closure, and deterministic closure.
   - `workstation/experience_compiler/promotion.py`: `derive_formal_contract()` fails closed if candidate has multiple incompatible families or lacks trusted provenance authority.
2. **P4 (Durable CapabilityInvocations & Causal Hierarchical Promotion):**
   - `workstation/operational_kernel.py`: Invocations persisted durably to `ArtifactStore` and `ExecutionJournal` with lineage (`task_id`, `run_id`, `operation_id`, `authority_scope`) and child drift/pin verification across restarts via `load_invocations()`.
   - `workstation/experience_compiler/hierarchical.py`: `propose_composite()` marks candidates as `DISCOVERED`; promotion strictly enforces `ExperiencePromotionPolicy` with causal replay and counterexample verification.
3. **P5 (Non-Resident Await & Production Telemetry):**
   - `workstation/task_compiler.py`: Connected `WaitDecision` to `AwaitConditionStore` with `worker_released=True`, releasing worker processes on semantic waits and resuming via `handle_event()`.
   - `workstation/control_plane/metrics.py`: `ORAMetricsCollector` and `ORAMetrics` wired directly to `OperationalKernel.execute_capability` and `TaskCompiler` recording transitions, waits, routing events, and reasoning re-entry rates.
4. **Verification Receipts:**
   - 21 in-flight operationalization tests passing (`test_run_closure.py`, `test_in_flight_handoff.py`, `test_browser_lowering_and_artifacts.py`, `test_hierarchical_causal_promotion.py`, `test_non_resident_await_telemetry.py`, `test_trello_benchmark_qualification.py`).
   - Full workstation regression suite passing: **647 passed, 2 skipped in 287.92s**.


## KI-012 — Browser ownership/recovery residual gaps after first corrective implementation [REOPENED — 2026-09-19]

The 2026-09-18 patch resolved the original tooltip popper bug, added host fencing,
plumbed `preferredTaskId`, improved lazy recovery and separated activity from
visibility. Those changes are retained.

**Residual reproduced/code-audited gaps:**
1. `clearParkedTasks()` destroys every lifecycle task with `status === 'parked'`.
   TaskRail may simultaneously classify one of those tasks as `working`,
   `waiting` or `human_control`; therefore bulk cleanup can destroy active work.
2. The Chat Browser pane initializes from `EMPTY_STATE` and can perform its first
   `attach(..., 'chat', undefined)` before restored BrowserTasks are known. A
   transient `about:blank` can therefore be attached before a second task-bound
   reconciliation.
3. Focused recovery tests start with a known `preferredTaskId`. H013 has not yet
   proven the real renderer/preload/IPC/runtime cold-restart A/B sequence required
   by the canonical exit criterion.
4. Session identity proof covers live/root aliases but lacks an explicit
   `parent_session_id` behavioral regression for BrowserPane task resolution.
5. Native-view occlusion is centralized, but generic role/slot selectors still hold
   authority in addition to the explicit `data-native-view-occluder="true"` marker.

**Prior evidence retained:** 88 focused Vitest tests, Desktop typecheck, H004 native
Browser smoke and Work100 30/30. This evidence validates substantial implementation
pieces but is not sufficient to close the renderer/product invariant.

**Qualification note:** current main's Workstation CI also has an unrelated
Browser Operational Admission integration-anchor failure
(`browser tool route anchor missing for browser_type`). Do not attribute that
failure to KI-012, but do not describe the repository head as globally green.

**Closure requires:** execution-aware bulk cleanup, no first-frame blank for a
recoverable task, extended H013 renderer+restart proof, parent/root/live alias
coverage, explicit occluder authority and exact candidate-head evidence.

**Canonical plan:** [BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md](BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md).


## KI-011 — Durable compiler can obstruct stateful native-browser work [CORRECTIVE IMPLEMENTED — EXACT-HEAD CI PENDING — 2026-09-19]

**Current correction:** H-071 closes the reproduced code gaps: real verified composition,
ACK/evidence separation, trusted authority origin, operational-closure admission, strict
terminal identity, native same-origin readback without process fallback, repaired anchor
and real Electron dogfood. Local gates are green; required exact-head CI remains open.

**2026-09-18 post-PR #28 reopening:** authenticated Trello dogfooding on current
native Electron Chromium reproduced the product class after the earlier policy hardening.
The Browser can navigate/click/read; the remaining deadlock is between legacy admission,
primitive expressiveness, verified readback and the new Control Plane. Concrete findings:
`read_preview` effect misclassification; structural non-browser hard-force; missing
rich-text paste/readback primitives; legacy and Router admission paths coexisting;
request-authored route authority; non-mandatory CertifiedDispatcher; mutation-timeout
retry ambiguity; and transient empty SPA snapshots.

The previous AEPC correction remains valuable regression coverage, but it was not full
product closure. KI-011 now closes only with the P0 exit criteria in
[BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md](BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md).


**2026-09-19 post-PR #29 audit:** PR #29 landed useful primitives and focused fixes,
but closure remains open. Current main can (1) label a composition successful without
executing its capability plan, (2) promote ACK/`success=True` to VERIFIED/COMMITTED
without accepted verifier evidence, (3) synthesize broad mutation authority from
request/task/session context, (4) force compilation from semantic repetition without
proving operational closure, and (5) change Browser-session readback into process HTTP
fallback. `terminal` semantic families are also too broad for mandatory compilation.

Qualification is independently blocked: exact-head Workstation CI and Windows Workstation
jobs both failed `apply_core_integration.py --check` with
`browser tool route anchor missing for browser_type`, skipping later product gates.
The simulation-heavy dogfood tests remain regression coverage, not final native runtime
proof.

Closure now additionally requires H-071 and the post-PR #29 gate in TESTING.md.


**Implemented correction:** remote implementation
`9e7292ab7825e5ce1ea294490eec57ba1f286069` (documentation/evidence
`5e1b22527fd40d732ee4fa7a1035e6366953f6b7`; local pre-publish SHA
`365794e29d66cd63a6134c5c67ecc1ef603d70a6`) correctly replaces the global
mutation latch with operation-scoped admission, canonical effect classification,
native route normalization, compact reasoning handoff, checkpoint resume,
semantic E1 evidence and lost-ACK safety.

**Residual AEPC-E002:** audit of `main@c4234200145162eefb60f6070c9f170b4bf79321`
found that shape-equivalent calls can still be mistaken for one homogeneous
operation family. Native `browser_type`, `browser_click` and
`browser_press` do not currently declare a concrete mutation target/target
family, while `structural_signature()` abstracts scalar values. A long stateful
flow can therefore reach the third-call `REQUIRE_COMPILE` threshold even when
each UI action has a different semantic target. The original immediate obstruction
is fixed; long stateful-browser closure is not yet complete.

**Evidence:** focused gate 113 passed; final Workstation + adjacent core gate
570 passed / 2 skipped; Work100 30 PASS / 0 FAIL; Desktop contracts 36 passed.
The earlier focused count predates the additional snapshot-strength regression,
which is included in the final full gate. These are provider-free/controller
contracts. Electron executable and built main bundle are missing locally;
authenticated native/packaged browser smoke is still required before declaring
the original product symptom fully validated. Original reproduction is retained
below; its contributor list describes baseline `c04906aacee568bb6480287717c76afd230cf4a7`.

**Observed:** on an authenticated internal Electron Chromium session,
browser_navigate, browser_snapshot and browser_extract_items succeeded, while
subsequent mutating interaction was replaced by durable_compile_required.
Attempting to express the work as durable execution then exposed
PREFLIGHT_REQUIRED/verifier requirements unsuitable for the unknown stateful UI
step, plus a native_browser route-constraint namespace mismatch in one path.

**Confirmed architectural contributors at the audited baseline (historical):**

- prepare_turn_work() stores a broad _work_batch_candidate boolean;
- requires_compilation() can use that boolean to reject any later non-read /
  non-interactive effect, rather than only the repeated operation;
- unknown browser builtins conservatively become MUTATION in tools.effects,
  while another guardrail list can classify browser_console differently;
- route comparison does not universally normalize browser tool names to the
  canonical native_browser route;
- deterministic preflight assumes durable mutation/readback semantics that are
  correct for fan-out but too strong as a prerequisite for discovering a novel
  stateful UI workflow.

**Target invariant:** safe authorized novel work may make bounded adaptive
progress; `REQUIRE_COMPILE` needs positive semantic evidence of one repeated
operation family, not only structural call shape. Homogeneous repeated mutations
still require compiler/canary; learned stable segments progressively move to
compiled/routine execution.

**Closure regressions:** prove both (1) a long stateful browser flow containing
3+ `browser_type` / `browser_click` mutations against different semantic
targets remains adaptive, and (2) three distinct mutations with the same
owner-declared operation/provider/route/target family require compilation.

**Do not fix by:** raising the threshold, resetting counters on navigation,
hard-coding a browser exemption, making arbitrary browser JS read-only, disabling
canary, allowing blind retry, weakening TaskRun/browser leases, adding a second
memory or authority store, or globally bypassing work_execute.

**Canonical design:** 
[ADAPTIVE_EXECUTION_COMPILATION.md](ADAPTIVE_EXECUTION_COMPILATION.md).

## KI-012 — Upstream-derived ownership/resync/Kanban/recovery gaps [RESOLVED IN WORK P0 HARNESS — 2026-09-18]

**Resolution:** All confirmed P0 upstream reliability gaps have been resolved and
validated with dedicated RED/GREEN regression tests on branch
`fix/workstation-upstream-reliability-p0`.

**Evidence:**
- Focused Python regressions: 17 passed in 4.03s (`test_cli_resume_read_only_owner.py`,
  `test_kanban_provenance_and_exit_evidence.py`, `test_browser_supervisor_reconnect_cap.py`);
- Workstation Python suite: 492 passed, 2 skipped in 315.16s;
- Work100 reliability suite: 30 PASS / 0 FAIL;
- Desktop Vitest UI suite: 593 files passed, 5676 tests passed;
- Desktop Vitest Platforms: 126 files passed, 1783 tests passed;
- Native browser probe `h004-native-browser-task-smoke.mjs` hardened with timer,
  input, scroll, and loopback controller discriminators.

**Implemented resolutions:**

- `tools/browser_supervisor.py`: capped post-attach CDP reconnect failures at 5,
  evicted exhausted supervisor from registry, and redacted credentials in logs (#114897);
- `hermes_cli/active_sessions.py` & `cli.py`: enforced single live writer exclusivity
  per `session_id`, supported observer resume (`mode="observer"`), fenced lease transfer,
  and failed closed on corrupt registry (#111493);
- `apps/desktop/src/lib/inflight-turn-journal.ts`: selected true live tail via
  `findLastIndex` and deduplicated sealed interim rows via `withoutBaseIds` (#115068);
- `use-background-sync.ts`: preserved unacknowledged optimistic user messages during
  background transcript resync until gateway ACK (#115085);
- `tools/kanban_tools.py`: validated session provenance against SessionDB (`state.db`)
  and prioritized request-scoped `HERMES_SESSION_ID` ContextVar over ambient env (#114785);
- `tools/kanban_tools.py`: required both claim extension and worker heartbeat writes
  to succeed, and fenced delegated child tasks from heartbeating parent workers (#114793);
- `hermes_cli/kanban_db.py` & `cli.py`: added durable `HERMES_WORKER_EXIT_TRAILER_V1`
  evidence and fallback classification for cross-process dispatcher observation (#114904).

**Watchlist / Deferred references:**
- #114964 was verified as an existing invariant and re-validated with extended probes;
- #114986 remains watchlist-only (affected upstream `turnLeases` absent downstream);
- #115056 and Durable Delivery Rail remain planned for P1.


This file records observed/reproduced gaps and the evidence boundary around them. A listed symptom is **not** permission to assume a root cause; verify current `main` and any explicitly named candidate before changing code.

## KI-002 — Preview and Workstation Browser are separate browser lanes

**Observed:** Preview and the main Browser surface can show different independently navigated pages for what the user regards as one web task.

**Do not fix by:** synchronizing URLs between two pages.

**Target invariant:** Workstation-mode Preview compatibility and Browser Hub/Chat Browser View reference one BrowserTask/live page.

**Current status:** the MVP invariant is resolved. Chat Browser View, Browser
Hub and Workstation Preview reuse the same BrowserTask/runtime identity, and
the single-host transfer path is covered by
`apps/desktop/electron/workstation-browser-runtime-viewport.test.ts` plus the
packaged GUI smoke. Full Preview action parity, richer layouts and exhaustive
reconnect/compatibility coverage remain follow-up hardening rather than a
second browser lane.

## KI-004 — Native browser surface can overlap another Desktop pane

**Observed:** during bootstrap validation, independent Preview and Workstation Browser surfaces could visually overlap and resizing changed the overlap.

**Current evidence:** the Browser renderer already uses `ResizeObserver` and `getBoundingClientRect`, so “add another resize observer” is not an established fix.

**Target invariant:** one live `WebContentsView` host at a time plus an explicit host/viewport ownership contract; validate resize, maximize/restore, sidebar/pane changes, and host transfer.

**Current status:** the shared-surface overlap invariant is resolved.
`viewportHost` and `transferViewport()` move the same `WebContentsView` between
Hub and Chat, while host-aware `setBounds` rejects stale geometry from a
non-owner pane. The focused runtime tests cover host rejection, zoom/clamp
normalization and cross-window rehoming. The runtime also reconciles the active
view on native window resize/maximize/restore events, and H013 validates that
matrix against a real hidden Electron/Chromium view. More complex pane races,
compositor transitions and broader native composition evidence remain open
hardening work.

## KI-006 — Broad Windows Desktop suites contain pre-existing portability/test failures [RESOLVED]

**Observed:** after the canonical-source installer reached a clean install and passing Desktop typecheck, the broad UI and Electron/platform suites remained red on Windows.

**Causality status:** **not caused by the Workstation canonical-source / BrowserTask changes based on controlled baseline evidence.** A native-Windows side-by-side comparison used baseline `ce78f120e8ed2974d6174e475cc7572afcfe41e0` and Implementation 4 candidate `2ffee2335b6aba071e7b63457a047cd9334d4d92` under the same Windows/toolchain/install/test conditions.

Observed comparison:

- baseline UI legacy: 5 failed files / 11 failed tests;
- candidate UI legacy: 5 failed files / 9 failed tests;
- baseline platform/Electron legacy: 11 failed files / 33 failed tests;
- candidate platform/Electron legacy: 10 failed files / 28 failed tests;
- remaining candidate failures were identical baseline failures or variants of the same causal class around Windows path/permission assumptions, SSH ControlPath/Include assumptions, POSIX virtualenv layout, WSL/bridge timing, staging/file-mode assumptions, and locale-sensitive UI expectations;
- candidate-specific BrowserTask suite passed 2 files / 16 tests and candidate typecheck passed.

Controlled verdict: `WINDOWS_BASELINE_COMPARISON=PASS_WITH_KI-006_RED`.

The accepted PR head `75d10d35d4757496390debf8e4b4f9efb44c5432` changed no BrowserTask product/runtime/probe/workflow/dependency code after that controlled candidate; only contributor-attribution mapping and Workstation journal material were added. Its final Windows workflow again passed committed integration validation, install, checkout-clean, typecheck and focused BrowserTask diagnostics before the final broad aggregator remained red. No new Implementation 4 failure class was introduced.

On BrowserSessionState accepted head
`d5be442021ea0c744351622317eef5212219786d`, the scoped static checks,
5 focused files / 46 tests and H010 native probe all passed. The broad run had
one UI failure from a missing `BROWSER_ROUTE` test mock and 31 Electron failures
across unrelated POSIX path/mode/symlink/SSH/platform assumptions. This is the
current exact-head manifestation of the same KI-006 class, not a
BrowserSessionState failure.

**Resolution on the current working tree (HW-018, 2026-09-11):** the
underlying Windows contracts were fixed and validated without disabling or
deleting coverage:

- deterministic English locale formatting now keeps UI output stable across
  host locales, and the new-session Preview promotion preserves tabs when the
  stored session id arrives after the runtime session;
- POSIX fixture paths use an explicit path adapter, while Windows venv paths
  use Windows grammar;
- POSIX mode assertions now remain strict on POSIX and validate the Windows
  ACL-preserving/writable contract instead of requiring meaningless Node mode
  bits;
- Git path comparisons use native physical paths and non-repository probes
  avoid leaving Windows cwd handles locked;
- SSH ControlMaster tests opt into mux behavior explicitly, while no-mux
  behavior remains covered separately;
- WSL UNC selection no longer performs a blocking synchronous network share
  probe, and native staging tests verify the requested executable mode through
  an injected boundary.

Validation: Desktop UI **591 files / 5,669 tests passed**; Desktop
platform/Electron **126 files / 1,778 tests passed, 5 skipped**; Desktop
typecheck passed. The baseline comparison above remains historical evidence;
KI-006 is no longer an open failure on this working tree.

## KI-007 — `Session not found` / exported `session: null`

**Observed:** session export/logging from the browser validation cycle included a consistent message `session_id` while the exported session object was `null`, and logs previously included HTTP 404 `Session not found`.

**Causality status:** **unproven**. Preview/browser behavior has independent reproduced gaps, so this issue must not be used as their explanation without a causal trace.

**Required proof before any SessionDB/Gateway change:** reproduce on current `main` → identify endpoint/caller/session id → determine lineage/compression/rotation expectations → identify the responsible line/race → add regression test → only then change core.

**Current audit result (2026-09-15):** a deterministic provider-free regression
scenario now creates a session, binds task/browser metadata, persists
user/assistant/tool messages, finalizes, closes/reconnects through separate
handles, exports the session/lineage and exercises concurrent close/export plus
rotation-like writer activity. It passed in
`tests/hermes_state/test_ki007_session_export.py`; `export_session()` never
returned `session: null`. KI-007 therefore remains **NOT_REPRODUCED / evidence
gap**, and no SessionDB rewrite is justified.

## KI-008 — V3 product-level acceptance evidence is still open

**Observed:** the V3.1–V3.4 Python contract layer is implemented and validated,
including a Windows process-boundary smoke, and bounded native Browser plus
real headless-backend reconnect soaks now pass. The roadmap still requires
clean-machine release qualification, full event/resource parity beyond the
current clients and full-duration/production-scale Desktop/Browser load. The
Chromium/Firefox/Edge browser smoke is now validated separately when Edge is
available.

**Causality status:** **not a product failure; evidence boundary is explicit.**
The contract tests do not prove behavior that they do not exercise. The
historical KI-006 Desktop portability debt is resolved on the current working
tree, while the remaining V3 release evidence gates are still separate.

**Required action:** run the Windows clean-machine release workflow (which now
emits candidate-matched install/build evidence and the configured H013
hidden-window Desktop/Browser load gate, including its bounded 16-task/
120-second candidate profile (locally validated, but still unqualified on a
clean candidate) and the full-duration/production-scale
Desktop/Browser load gate on a candidate release, and extend client parity as new supported
surfaces are added, before promoting V3.1–V3.4 from “contract layer validated”
to fully accepted. Do not mark those gates green from unit-test coverage alone;
the bounded H011/H012 probes and local H013 integrated E2E are evidence, not a
substitute for the clean-machine/release-candidate gate.

## KI-009 — Packaged Desktop GUI E2E target initialization [RESOLVED]

**Original symptom:** the packaged Windows artifact loaded its real renderer,
but Playwright's Electron `beforeAll` waited for a detached Workstation
`WebContentsView` target and ended at the 90-second hook timeout.

**Resolution:** Workstation controller startup no longer creates a browser view
until the UI or a `browser_*` action needs one. The E2E fixture isolates
`HERMES_WORKSTATION_HOME`, injects the Electron loader for the custom packaged
executable and tolerates only 1 px of native subpixel geometry rounding.

**Evidence:** the original packaged GUI gate passed **5 passed (26.4s)**;
the latest run including the shared-resource identity check passed **6 passed
(28.3s)**.

## Resolved regression classes

### KI-010 — Vault paths were contained only after write [RESOLVED]

**Original symptom:** `VaultManager.write_note(..., subfolder=...)` created the
resolved directory and wrote the note before `relative_to(vault_dir)` proved
containment, allowing traversal/absolute-path side effects outside a custom or
default Vault root.

**Resolved behavior:** path input is parsed with host and Windows grammar,
containment is proved before directory/file mutation, symlinked files and
directories are excluded from scanning and mutation, and note replacement is
atomic. The process-wide canonical manager also runs a bounded debounced
watcher so external Markdown create/edit/rename/delete changes rebuild the
same index used by tools and Desktop RPC.

**Evidence:** `workstation/tests/test_vault.py` covers traversal, POSIX/Windows/
UNC absolute paths, malformed titles, normal/custom roots, file/directory
symlink escape where the host permits symlink creation, atomic CRUD and watcher
lifecycle/external changes.

### KI-003 — Complete logical BrowserSessionState did not survive restart

**Original symptom:** the persistent Chromium profile and BrowserTask-only
metadata existed, but ordinary logical tab ordering, active selection, safe
restorable metadata and one composite restart projection were incomplete.

**Resolved behavior:** PR #11 promoted one versioned atomic
BrowserSessionState containing ordinary/task logical tabs, order, active state,
sanitized URL/title metadata and the BrowserTask snapshot. It preserves the
latest intended composite across failed writes, migrates legacy task state once,
parks restored tasks and lazily recreates exactly one page.

Promotion:

- accepted head: `d5be442021ea0c744351622317eef5212219786d`;
- merge commit: `e0a99ef3aba6e6d2b65c30cf3c908ee1d49c4d29`;
- focused evidence: 5 files / 46 tests;
- native evidence: `H010_CLASSIFICATION=VALIDATED`, including clean and abrupt
  two-process restart, profile separation, failed-write convergence and
  explicit-destroy failure cleanup.

**Boundary retained:** a WebContentsView/renderer heap never survives process
restart. Controller/session/run/card identity expansion and host state belong to
V1 #1.5/V1 #5, not a second BrowserSessionState owner.

### KI-005 — BrowserTask lifecycle was implicit on pre-Implementation-4 `main`

**Original symptom:** `ownerTaskId`, `taskTabs`, parking, and attach/detach existed, but there was no complete first-class `show`/`hide`/`park`/`destroy` BrowserTask contract.

**Resolved behavior on current `main`:** PR #9 formalized BrowserTask around the existing `taskTabs`/`BrowserEntry.ownerTaskId` ownership primitives without introducing a second page store. `hide` and `park` preserve a live page, `show` re-exposes it, repeated task creation is idempotent, missing pages recover under the same logical task, and `destroyTask` is explicit.

Promotion:

- accepted PR head: `75d10d35d4757496390debf8e4b4f9efb44c5432`;
- merge commit on `main`: `fada723f43613e5e0f061cab24445573ac298998`.

**Automated regression coverage:**

- `apps/desktop/electron/workstation-browser-task.test.ts`;
- `apps/desktop/electron/workstation-browser-runtime-task.test.ts`;
- focused BrowserTask step in `Workstation Browser Windows`.

**Real native evidence:** `workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs` ran on Windows `10.0.26200`, Electron `40.10.2`, repository head `d8acc752133b125b9619cbc7fe09199f1283a22b` and emitted:

- `H004_LIVE_DESTROY_PASS`;
- `H004_RESTART_PASS`;
- `H004_CLASSIFICATION=VALIDATED`.

The native smoke proved same-page identity across hide/show and park/show, explicit destruction, two-process logical restart restoration/recreation, exactly-one-page ownership, and structural secret isolation.

**Carry-forward evidence:** Git comparison established that changes between the native-smoke/code-bearing evidence and the final accepted PR head did not alter the exercised BrowserTask product/runtime/probe behavior. Final-head Workstation CI and focused gates passed; broad Windows red retained only KI-006 baseline debt. KI-005 is therefore closed on promoted `main`.

### KI-001 — Desktop Browser capability could disappear from the model schema

**Resolved behavior:** Desktop/GUI Browser surface capability is derived from active Gateway session context instead of process-global Desktop identity or controller reachability. Selected Workstation-routed browser schemas remain present during controller startup/reachability races, while controller health/recovery governs execution. The tool-definition cache includes the session capability fingerprint so Desktop results cannot leak into TUI/CLI.

**Security/ownership boundary:** only the narrow set of actions actually routed through the embedded Workstation Browser is force-preserved, and only when those names are already selected by active toolsets. `browser_exec` is not promoted. TUI/CLI sessions do not gain Desktop capability merely from `HERMES_DESKTOP=1`.

**Regression coverage:** `tests/tui_gateway/test_workstation_browser_schema_capability.py`.

### RI-001 — Normal Workstation install rewrote tracked source before validation

**Resolved behavior:** the normal installer treats the committed downstream tree as canonical. It validates integration in read-only mode, installs isolated dependencies, prepares runtime state outside tracked source, and compares Git status before/after installation.

**Evidence:** canonical-source validation on Implementation 2 and subsequent Workstation CI/Windows install gates.

## Closing an issue here

When an issue is fixed, move it to the resolved section with the validated behavior and test/evidence boundary. Do not delete the historical symptom if it documents a regression class that future tests protect.

## Canonical Work Loop Reliability Gaps — RESOLVED (2026-09-17)

The canonical execution reliability gate resolved and verified the identified causal gaps:

### KI-007 — Stale run late completion could corrupt task state [RESOLVED]
**Resolved behavior:** `workstation/kanban.py::complete_task_with_report` enforces `expected_run_id` CAS checks. Stale runs from superseded attempts are rejected immediately before acceptance evaluation or mutation, and late reports cannot mutate canonical task state. Covered by `test_stale_run_late_completion_rejected`.

### KI-008 — Terminal parents left live descendants [RESOLVED]
**Resolved behavior:** `DurableTaskStore.update_plan_state` cascades terminal states (`interrupted`, `failed`, `cancelled`, `blocked`) to mark all live descendant items as `blocked`. Startup and periodic reconciliation is provided by `reconcile_terminal_plans()`. Covered by `test_terminal_parent_reconciliation_cases_a_and_b`.

### KI-009 — Missing canonical lineage across WorkPlans and reports [RESOLVED]
**Resolved behavior:** Canonical lineage fields (`run_id`, `execution_key`, `operation_id`) are now first-class on `WorkPlan`, `WorkItem`, `ExecutionEvent`, `BrowserTaskReport`, and `TaskOutcome`, with backward-compatible SQLite migrations. Exposed via `task_cockpit()`. Covered by `test_workplan_persists_canonical_lineage_run_and_execution_key` and `test_task_cockpit_exposes_canonical_lineage`.

### KI-010 — O(N^2) ExecutionJournal append scaling degradation [RESOLVED]
**Resolved behavior:** `ExecutionJournal.append()` utilizes `_get_last_record()` to achieve $O(1)$ streaming hash chaining without parsing the full journal file on each append. Verified under 120-event stress test in `test_journal_100_events_streaming_hash_integrity`.

All 30 seed cases in `work100.py` pass with 0 coverage gaps, and all 452
Workstation tests pass with 2 expected skips.

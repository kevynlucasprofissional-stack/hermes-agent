# CURRENT — Workstation Engineering Journal

## H-080B product lifecycle closure audit — 2026-09-23

Canonical detailed record:
[h080b-product-lifecycle-closure-2026-09-23.md](h080b-product-lifecycle-closure-2026-09-23.md).

The Codex H-080B vertical is accepted as a strong hermetic causal proof, but its meaning is narrowed: it proves the existing pieces can form the loop; it does not prove that normal product runtime automatically owns verifier validation, controlled replay and promotion.

Current Git truth at this entry:
- PR #45: open at `c23fe2233450b47d6d90ec9785376327e533bdef`; Workstation CI green; Windows workflow still in progress.
- PR #46: draft at `769002547428fa882ca1e5248387821482c70cd9`; still based on `72cfa4b389...`.
- PR #46 vs current PR #45: diverged, 2 ahead / 1 behind, merge-base `72cfa4b389...`.

Canonical decomposition:
```text
H-080B.1 verified Experience admission -> candidate        LOCALLY PROVEN
H-080B.2 automatic validation/replay/promotion lifecycle  OPEN
H-080B.3 real Electron/package/dogfood qualification      OPEN
H-081    Laya/System-1 shadow                              DEFERRED
```

Next implementation is constrained to:
1. reconcile PR #46 onto the promoted/current H-080A baseline;
2. add owner-issued Browser operation receipt/state revision + strict learnable run binding;
3. replace literal single-trace cardinality with one mutation + bounded read-only observations;
4. productize candidate validation/replay/promotion through a small coordinator over existing owners;
5. prove the vertical with real Electron against an isolated local server;
6. dogfood full automatic promotion and future provider-0 reuse.

No new executable ontology, database, authority plane, generated-script executor or Laya production routing is authorized in this lane.


## H-080B first native-browser vertical — 2026-09-23

Implementation: `workstation/h080b-native-browser-experience-loop@6d8806b868`, based on P0 `72cfa4b389`, frozen upstream `71a2fe399bbd7a219c71f9d9fca2b313b01f2057`. H-080B hermetic proof: normal Run A native route/accepted Experience; two compatible accepted run IDs; candidate `experience_bcc0974be58c73cf04a0b436@1.0.0`, semantic fingerprint `4bc13bdf68ea16aa4bb43d811045c7749a10e4e0c80f2c587849eb8597e6c141`, compatibility fingerprint `bcc0974be58c73cf04a0b436a0478b2830b5c369019940277fb62f6ed57a77d2`; validated browser-local readback verifier; positive replay and wrong-host negative control; promotion admitted; future normal Run C EXECUTE, nonempty certificate, exactly one native physical action, VERIFIED/accepted/COMMITTED, provider 0. Focused regression 122 passed; strict seam audit passed with 14 classified and no budget growth. P0 PR #45 exact-head contracts 779 passed but Windows aggregate red; branch CI/native packaged qualification pending. Laya DEFERRED.

## H-080B real-use audit — 2026-09-23

Detailed canonical audit:
[h080b-real-use-experience-loop-audit-2026-09-23.md](h080b-real-use-experience-loop-audit-2026-09-23.md).

New evidence changes the next-work priority:
- PR #45 implements the important H-080A causal path, but current exact-head CI is red and must be qualified truthfully;
- real native-browser conversations demonstrate route-selection and over-verification waste;
- production Experience capture is active, but real samples remain uncertain/inconclusive and have not produced a learned promoted capability;
- next feature work is one bounded browser-native H-080B capture -> verify -> compile -> validate -> promote -> future provider-0 vertical proof;
- Laya stays deferred until that causal loop works without it.

## H-080A — Production-path closure qualified locally (2026-09-23)

**Status:** CODE COMPLETE / LOCAL QUALIFICATION GREEN / EXACT-HEAD CI PENDING.
H-080B (Experience feedback loop) remains OPEN as a separate sub-lane.

Branch: `integration/upstream-20260922-71a2fe39-h0793`. Frozen pin unchanged:
`71a2fe399bbd7a219c71f9d9fca2b313b01f2057`.

### What closed each audit blocker

- **Authority (A):** new `workstation/integrations/hermes/effect_authority.py`
  derives a LOCAL_MUTATION ceiling from trusted ingress (envelope +
  canonical task/session binding). `_dispatch_intent` sets
  `compiler.trusted_authority` from it. TaskCompiler authority monkeypatch
  removed from all release E2E. Pinned by
  `workstation/tests/test_operational_effect_authority.py` (13 tests).
- **Real dispatch (B):** E001 split into E001F (filesystem verified success
  through the kernel's real `fs_write` + `fs_read` readback) and E001D
  (real `workstation_durable_dispatch` → `execute_tool_calls_sequential` →
  real `todo_list` → real `TodoStore`, exactly once, spies only).
- **Causal asserts (C):** `OperationalResolution.details` now carries
  capability id, certificate hash, verification status/accepted and dispatch
  status; E001F/E003VF assert them directly plus real filesystem state.
  `TaskCompiler._execute_route` also forwards `observer_args`,
  `observed_predicates`, `expected_operation_id` (observation config).
- **Scratch (D):** `test_zz_scratch_route_fixture.py` absorbed and removed.
- **Pre-seeded evidence (E):** objectives carry only observation
  configuration; the kernel's real observer produces post-effect evidence.
- **Metrics:** generic counters distinguish
  executed/satisfied/wait/handoff/continue_reasoning; unknowns stay `None`.

### Qualification receipts (this head, local)

- focused H-080 (boundary 17 + provider 10 + e2e 10 + authority 13): green;
- Browser focused (extract/controller/broker/extension-router): green;
- strict seam audit: 0 unclassified, 0 budget regressions;
- core integration check: green;
- todo tool owner tests: green;
- full `workstation/tests`: 2 pre-existing failures unrelated to this lane
  (missing optional `anthropic` package; stale `MockRouterWait` signature in
  the await-telemetry test) — separate lanes, not H-080A regressions.

Remaining before promotion: final upstream drift classification, PR, exact-head CI.

## H-080 — Production-path audit after E001/E003V repairs (2026-09-22)

**Status:** ARCHITECTURE ACCEPTED / CONTROL-PLANE E2E IMPROVED / PRODUCTION-PATH QUALIFICATION BLOCKED.

Canonical current audit:
[h080-production-path-audit-2026-09-22.md](h080-production-path-audit-2026-09-22.md).

Audited branch:
`integration/upstream-20260922-71a2fe39-h0793@89a745d2ee0346c7030134c10b24071ce9e234f1`.

### Corrections confirmed

- E001 now begins with a false goal state and cannot pass through `SATISFIED`.
- E003V is implemented and drives FAILED verification with no provider retry.
- upstream intervention registry now contains only the four upstream-owned files and correct feature provenance.
- `SEAM-OPERATIONAL-RESOLUTION` is registered.
- Browser authority/projection model remains healthy.
- branch had been reconciled with `main@df2222c...` and was 24 ahead / 0 behind at audit time.

### New production-path falsifications

**Authority is still injected in the E2E.**
The release test patches `TaskCompiler.execute` and writes an `EXTERNAL_REVERSIBLE` `trusted_authority` directly onto the compiler. Production route authority otherwise resolves through `self.trusted_authority -> canonical task.authority_scope -> READ`; canonical Kanban/task-admission owners currently do not provide that scope. Therefore the test proves an assisted authority path, not production authority propagation.

**Physical dispatch is still replaced.**
The E001 patches `workstation_durable_dispatch` to `_DispatchRecorder`. This proves the certified control plane reaches its dispatch callback exactly once, but not the actual Hermes tool execution chain (`tool scope -> execute_tool_calls_sequential -> guardrails -> raw-result capture`). The same fixture empties tool definitions and `valid_tool_names`, so it is not a realistic admitted production primitive.

**Causal claims exceed direct assertions.**
The runtime already returns routing decision, certificate, verification and dispatch record, but the E2E currently asserts mainly final response text, provider count and dispatch-callback count. Release evidence must assert `EXECUTE`, certificate, `VERIFIED`, `accepted`, `COMMITTED` directly; verifier-failure must directly prove not-COMMITTED.

**Verification evidence is pre-seeded before execution.**
The E001 objective contains trusted `verification_evidence` with `read_after_write=True` before the mutation runs. `OperationalKernel` consumes supplied evidence directly, so this can certify success without a real post-effect observer. Release evidence must remove that synthetic success evidence and use runtime-owned readback.

**Scratch artifact remains.**
`test_zz_scratch_route_fixture.py` is still present.

**Metrics report is stronger than telemetry.**
Generic operational metrics are steps/attempts/hits/misses/errors/self_reported. A hit is not synonymous with `EXECUTED+VERIFIED`. Use existing ORA/VOLC owners for truthful derived metrics.

### H-080A discriminating experiments

**E001P — production authority + real dispatcher**
- normal `AIAgent.run_conversation`;
- trusted authority arrives through the real production owner;
- no `TaskCompiler.execute` monkeypatch;
- real `workstation_durable_dispatch`;
- a real admitted, harmless primitive;
- actual tool executor/guardrails/raw-result path;
- physical effect exactly once;
- routing decision `EXECUTE`;
- certificate non-empty/valid;
- canonical verification `VERIFIED`, accepted;
- dispatch record `COMMITTED`;
- provider calls 0;
- canonical finalization preserved.

**E003VP — failed verification on production dispatch path**
- real dispatch crosses the physical boundary exactly once;
- verifier FAILED/INCONCLUSIVE;
- dispatch record not COMMITTED-success;
- no terminal EXECUTED-success;
- provider calls 0 for the same mutation;
- reconciliation/handoff semantics preserved.

### H-080B

Experience feedback-loop closure remains separate/open: novel verified execution -> corpus -> compile -> controlled replay -> verifier validation -> promotion -> future normal-turn reuse with zero provider calls.

### Upstream

Latest observed upstream: `d3b25b52ad1318c526bdb259b600eeca3d5f38e6`.
Compared with frozen pin `71a2fe399...`: 23 upstream commits, no overlap with the four H-080 upstream intervention owners. Current classification: `NON_OVERLAPPING`, to be repeated immediately before promotion.

Do not open/merge the PR until E001P/E003VP and exact-head qualification are green.

## H-079.2 — Promotion-gap audit after one-click dogfood failure (2026-09-20)

**Status:** SUPERSEDED BY 2026-09-21 CANDIDATE / EXACT-HEAD CI PENDING.

A real one-click Windows dogfood run falsified the assumption that the current `main` contained the pipless-venv installer repair. The run reused `C:\Github\hermes-agent\.venv`, then failed at `python -m pip install -e .` with `No module named pip`.

Repository audit established the promotion gap:
1. PR #40 merged upstream `8d153b26...` into an integration branch rather than `main`.
2. The installer repair (`90dbc446...`), H-077 negative test (`a0efd05a...`), and pipless fixture (`120165eb...`) descended from that branch and never became ancestors of main.
3. Current `main@964c133...` remains based on upstream pin `c1488ac947...`, while observed upstream has advanced to `641f7c8104...` (547 ahead / 622 behind downstream, merge-base at the old pin).
4. Core Workstation evidence remains strong at current main: 743 Workstation tests, 327 core seam regressions, canary and integration dry-run green.
5. Windows product/browser gates largely pass; the remaining red result is driven by POSIX/macOS test assumptions executed on a Windows runner. That diagnosis is evidence, not permission to call the release gate green.

Engineering interpretation:
```text
fix exists on another branch != fix shipped
valid integration merge != upstream pin ancestral to main
cross-platform mismatch explained != release gate green
core exact-head green != installer/product release qualified
```

2026-09-21 execution completed Stage A against upstream `118984d7a02f...`, then re-adopted the target fixes. The installer matrix additionally falsified the old interpreter probe: a non-Python executable named `python.exe` could return zero and reach `uv`; the probe now requires a Python-emitted marker and fails explicitly. Local qualification is green; exact-head Actions and final drift remain the closing experiment.


> **Identifier warning.** `H-046`…`H-051` and `H-054` are each used by **two different series** in
> this file, and `H-053` collides across documents. Resolve an identifier through
> [`../ID_DISAMBIGUATION.md`](../ID_DISAMBIGUATION.md) before citing it. New hypotheses take
> `H-080` and above — do not reuse a retired number.

## H-079 — Make upstream synchronization the first phase of every downstream change (2026-09-20)

**Status:** POLICY ESTABLISHED / MANDATORY FOR FUTURE CODE-CHANGE LANES.

H-078C proved that waiting for large divergence is expensive and that dependency-clean
downstream code can still sit on obsolete structural owners. The operating model is
therefore changed from periodic upstream migration to an **upstream-first change gate**.

The improved form is two-stage rather than continuously chasing upstream:
1. Stage A selects one exact current upstream SHA, performs a true history merge, reconciles
   seams and reaches a qualified baseline.
2. Stage B implements the requested downstream change on that frozen baseline.
3. Immediately before promotion, upstream drift is fetched/classified; relevant overlap
   reopens Stage A, non-overlap is recorded for the next cycle.

At policy creation, current upstream has already advanced 365 commits beyond the adopted
H-078C pin, so the next code-changing cycle must begin with Stage A again.

### H-079 Implementation & Baseline Qualification (2026-09-20)

**Status:** STAGE A & B LOCALLY QUALIFIED; SUPERSEDED BY MERGE TO MAIN — SEE THE POST-MERGE RECONCILIATION BELOW. The `b7d7d2929a` pin described in this entry was replaced by `c1488ac947` in `24a8501934`, and the exact-head baseline gate is currently **red**.

The H-079 + H-078C Corrective Cycle was executed under the upstream-first protocol:
1. **Stage A (Upstream Baseline Sync)**:
   - Pinned upstream commit `b7d7d2929a10e0658a98a7a03f4531093e1480ed`.
   - Executed real two-parent Git merge in `a13929fb35`.
   - Proved ancestry: `git merge-base --is-ancestor b7d7d2929a HEAD` returns 0.
2. **Stage B (H-078C Debt Closure)**:
   - *Runtime Independence*: Resolved test collection import pollution; isolated subprocess test proves alternate reasoner runs with 0 `run_agent` imports.
   - *Browser AppView Dry-Run*: Updated anchor pattern in `apply_core_integration.py` to match current Desktop layout; dry-run passes.
   - *Browser Control Broker Authority*: Switched normal `browser_tool` dispatch to `browser_extension_router` -> `BrowserControlBroker` -> `WorkstationBrowserController`; legacy router downgraded to compatibility adapter. Single mutation executor invariant preserved.
   - *Tool Batch Admission*: Owned exclusively by `agent/turn_tool_round.py` with admission marker; duplicate execution in `run_agent.py` eliminated.
   - *Adapter Bootstrap*: Replaced silent exception swallowing with explicit fail-closed bootstrap when Workstation supervision is expected.
   - *H013 Headless Load Spec*: Fixed active `BrowserTask` owner ID preservation on viewport transfer and restored Chat PreviewPane routing for `workstation:` targets. Spec passes 3/3 in 1.4m.
3. **Comprehensive Verification Matrix**:
   - Seams audit: 18 classified, 0 unclassified, 0 budget regressions (`audit_hermes_seams.py --strict`).
   - Workstation full pytest suite: 741 passed, 2 skipped, 1 warning (291s).
   - Desktop: `npm run typecheck` 0 errors, `npm run build` clean.
   - Probes: H004 native browser smoke probe VALIDATED; Work100 benchmark 30 PASS / 0 FAIL.
   - Upstream drift check: Observed 86 commits drift on upstream main (`2ed6387d87`), classified as non-overlapping with Workstation core. Pin frozen at `b7d7d2929a`.

### H-079 post-merge reconciliation and baseline regression (2026-09-20)

**Status:** REGRESSION CONFIRMED AND REPRODUCED / FIX ON BRANCH / BASELINE NOT QUALIFIED.

The candidate above was promoted. `24a8501934` merged a refreshed upstream baseline
(`c1488ac947`) into `main`, replacing the `b7d7d2929a` pin. Reconciliation of the state-carrying
documents against the new `main` surfaced a **real product regression** introduced by the
subsequent head commit.

1. **Regression (exact reproduction)**: `d0ade123c0` (`feat(browser): implement BrowserTask
   lifecycle and routing enhancements`) rewrote `BrowserRoutingPolicy.choose` in
   `workstation/routing.py`. The new body short-circuits on
   `internal_runtime_available` — a field defaulting to `True` whose only reader is that same
   branch — *before* any ladder condition. Every rung below it therefore became unreachable:
   `lightpanda`, `agent-browser` and `browser-exec` could never be selected. This is a capability
   regression of exactly the kind `FIRST_PARTY_SEAM_POLICY.md` forbids, and it contradicts
   `workstation/workstation.yaml` (also touched by that commit), which still declares
   `fallback_runtime: lightpanda` and routes `headless_scan`/low-power work to `lightpanda`.
2. **Evidence**: `Workstation CI` job `contracts` is green at the parent `9c9a00b84e` and red at
   `d0ade123c0` (`1 failed, 742 passed`). Reproduced locally:
   `test_lightpanda.py::test_routing_policy_chooses_lightpanda_for_stateless` fails
   (1 failed, 3 passed).
3. **Correction**: the ladder is restored on `fix/h079-baseline-reconciliation`. The
   `bound_to_any_runtime` fail-closed guard is kept (it is a correct superset of
   `bound_to_internal`, aligned with the "a bound BrowserTask never migrates silently"
   invariant); `internal_runtime_available` is removed. Both pre-existing contracts pass:
   `test_lightpanda.py` and `test_contracts.py` (the latter requires `enabled=False` -> INTERNAL,
   which is why `internal_only_when_disabled` is restored).
4. **Full ladder re-verified**: `scripts/run_tests.sh workstation/tests -j 4` — **741 passed,
   0 failed, 2 skipped**, 80 files.
5. **Drift re-measured** at reconciliation time: pin `c1488ac947`; upstream `main`
   `a4f9857ff5` (396 ahead of pin); 542 commits on `main` not in upstream. Upstream advanced by 2
   commits *during* the observation, so these are dated snapshots — the pin, not the observation,
   is the stable target.
6. **Consequence for the gate**: per H-079 ("do not begin target coding while required exact-head
   Workstation baseline gates are red"), no new downstream code-change cycle starts until this
   branch is merged and exact-head CI is green. The baseline is deliberately **not** recorded as
   qualified.

The earlier state documents naming `b7d7d2929a` are not rewritten: they are dated records of the
candidate stage. Their live successors (`ROADMAP.md`, `UPSTREAM.md`, `UPSTREAM_DELTA.md`,
`CURRENT_STATE.md`, `first_party_seams.json`) now carry the reconciled values.


## H-078B — Code-to-Code Upstream Migration / Semantic Decoupling — 2026-09-19

**Status:** COMPLETE / EMPIRICALLY VERIFIED / GREEN TEST LADDER.

The H-078B implementation has successfully retired `run_agent.py` as an integration owner and eliminated
all accidental Workstation coupling from the generic Hermes core.

Key achievements:
1. **Generic Core Abstractions Added (`agent/`)**:
   - `TurnIngress` (`origin`, `trust_or_authority_class`, `session_id`, `correlation_id`, `metadata`);
   - `admit_turn` (`agent.turn_admission`);
   - `admit_tool_batch` (`agent.tool_batch_admission`);
   - `scoped_execution` (`agent.scoped_execution`);
   - `dispatch_pre_authorized_checkpoint` (`agent.pre_dispatch`);
   - `dispatch_raw_post_tool_observation` (`agent.post_tool`);
   - `ExecutionPersistenceDisposition` (`agent.execution_persistence`);
   - `TurnRoutePolicy` (`agent.turn_route_policy`);
   - `admit_completion` (`agent.completion_admission`);
   - `should_bypass_compression` (`agent.compression_admission`);
   - `project_messages_for_provider` (`agent.conversation_projection`);
   - `admit_task_completion` (`agent.task_completion_admission`).
2. **First-Party Adapter Façade (`workstation/integrations/hermes/`)**:
   - Centralized `install_workstation_adapter()` registers all first-party providers with generic core registries;
   - Zero direct imports from `workstation` in `run_agent.py`, `conversation_loop.py`, `tool_executor.py`,
     `turn_finalizer.py`, `turn_constraints.py`, `chat_completion_helpers.py`, `conversation_compression.py`,
     `cli.py`, `gateway/run.py`, `kanban_db.py`, `web_server.py`, `file_tools.py`, `tool_search.py`, `close_preview_tool.py`.
3. **Causal Invariants Strictly Enforced**:
   - Pre-authorized checkpoint fires after final args + authorization, before real I/O;
   - Raw post-tool observation captures untruncated results and mutation metadata before truncation or spill;
   - Owner-managed persistence suppresses intermediate SessionDB flushes during durable compiled batches.
4. **Verification & Audit**:
   - `audit_hermes_seams.py --strict`: 18 classified core seams (all first-party tools), 0 unclassified, 0 budget regressions;
   - `workstation/tests/test_h078b_generic_seams.py`: 9/9 passed;
   - `workstation/tests/test_h078b_runtime_independence.py`: 3/3 passed (verifying foreign reasoner drives kernel with zero `run_agent` imports);
   - Regression suites passed: `test_h0771_qualification_closure.py`, `test_architectural_falsification.py`, `test_control_plane_integration.py`, `test_canonical_work_loop.py`, `test_canonical_continuity.py`, `test_durable_agent_integration.py`.


## H-078B — Deep code-to-code audit / semantic migration spec — 2026-09-19

**Status:** DOCUMENTATION + MACHINE-READABLE MIGRATION SPEC UPDATED; NO RUNTIME AUTHORITY
SWITCHED.

The first H-078 seam inventory was intentionally challenged against three exact trees. The
result reduced the apparent problem from "13k commits" to a bridge migration: only 129
paths were changed by both downstream and upstream, while 338 downstream paths do not
collide and 254 of those are under `workstation/`.

Key falsifications of the first H-078 draft:

1. file-level disposition is too coarse; `tool_executor.py` contains both REMOVE and
   UPSTREAM_ABSTRACT concerns;
2. `run_agent.py` was under-classified and is one of the largest semantic seams;
3. generic tool middleware is insufficient for uncertain-before-I/O because the checkpoint
   must occur after final args+authorization but before real I/O;
4. raw `post_tool_call` is sufficient for record/capture post-effect observation;
5. durable internal compiled steps require an explicit persistence/visibility disposition;
6. Progressive Compilation needs batch-level admission, not only per-tool middleware;
7. turn completion is an admission gate, not a notification;
8. upstream Kanban PR acceptance provides a reusable two-phase completion pattern;
9. Browser broker convergence is now preferable to preserving bespoke Hermes-side routing;
10. Browser native lifecycle is still Workstation-owned and remains a legitimate narrow
    first-party seam;
11. Browser mutation shadowing must be predictive only, never duplicate I/O;
12. `web_server.py` and `toolsets.py` are stronger REMOVE candidates than originally
    classified.

Repository changes in this refinement:

- `first_party_seams.json` -> v2 semantic concerns + causal ordering + parity/sunset;
- canonical H-078 migration document -> code-level extension points, owners and hard gates;
- ROADMAP / Intelligence / CURRENT_STATE / journal / upstream delta / decisions / policy
  updated to the same model.

No upstream merge is performed in this documentation lane. The next coding lane must first
reconcile H-078 with current main, then pin exactly one upstream SHA.


## H-078A — Minimum Necessary First-Party Seams — 2026-09-19

**Status:** ACTIVE REFINEMENT OF H-078.

The initial decoupling hypothesis was challenged by the historical Browser behavior:
some Workstation outcomes exist precisely because the downstream distribution owns
first-party lifecycle/UI seams. A fresh code audit reproduced the current path in which
internal Browser navigation emits `workstation.browser.open`, Desktop routing opens the
Workstation Browser beside the chat, and the native Electron runtime owns a persistent
BrowserTask-linked `WebContentsView`.

The same audit found stronger modern upstream extension surfaces: tool/LLM middleware,
lifecycle hooks, Browser providers, and a Desktop Plugin SDK capable of contributed
workspaces/panes and right-side docking. Therefore neither extreme is justified:

```text
plugin-only / zero seam     -> risks functional ceiling
deep scattered fork        -> recurring upstream integration tax
minimum first-party seams  -> selected direction
```

Decision D-027: remove accidental seams, create generic abstractions where needed, preserve
narrow first-party seams when privileged lifecycle is materially required. Never trade a
proven Workstation capability for architectural purity.

Implementation additions:
- `context/FIRST_PARTY_SEAM_POLICY.md`;
- `first_party_seams.json` initial classification registry;
- seam audit will classify/report deliberate vs unclassified coupling.

## H-078 — Upstream Migration as Decoupling / Supervisory Independence — 2026-09-19

**Status:** ACTIVE STRATEGIC MIGRATION PROGRAM.

Hypothesis accepted from the 2026-09-19 upstream/fork audit: merely porting the existing
Workstation patches into the upstream's new module layout would preserve the recurring
coupling tax. The migration should instead use every touched overlap to reduce direct
Hermes -> Workstation knowledge.

Observed current direct seams include:
- `agent/conversation_loop.py` -> Workstation turn preparation/routing/continuation;
- `agent/tool_executor.py` -> Workstation mutation/durable-execution/result capture;
- `agent/turn_finalizer.py` -> Workstation finalization/procedure learning;
- `tools/browser_tool.py` -> Workstation Browser routing/artifact/task helpers.

Countervailing evidence confirms a plausible extraction path already exists rather than
requiring new speculative infrastructure: current fork and modern upstream expose generic
plugin/lifecycle and middleware surfaces including `pre_tool_call/post_tool_call`,
`pre_verify`, API request/response hooks, `tool_request/tool_execution` and
`llm_request/llm_execution`.

Decision: H-078 / D-026. Workstation must supervise normal Hermes behavior without model
compliance. Old seams retire only after a Workstation-owned adapter proves shadow parity.

Initial implementation landed in this lane:
- canonical H-078 architecture document;
- expanded upstream strategy;
- coding-agent rule;
- seam-audit utility `workstation/scripts/audit_hermes_seams.py`.

Next experiment: pin the upstream SHA for the actual integration branch, run the seam
audit on the downstream baseline, then construct the overlap matrix with
ADOPT_UPSTREAM / KEEP_WORKSTATION / SEMANTIC_PORT / EXTRACT_BOUNDARY classifications.

Canonical:
[../UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md](../UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md).


## H-077.1 — Post-merge truthful-core qualification closure — 2026-09-19

**Status:** IMPLEMENTATION COMPLETE / QUALIFIED.  
**Audit baseline:** `main@92a3acb51e87af85a9f380ee04d2cf47d7900ca5`.

Resolved and verified:
- TaskCompiler terminal completion consumes canonical verification truth, not kernel ACK;
- VerificationContract judges an observation receipt but may not mint its evidence provenance;
- expected task/run/operation lineage enforced;
- derived validity envelope fails closed on missing required applicability dimensions;
- external metrics expose external adjudication coverage;
- external falsification uses independent oracle;
- execution ACK, verified success, and verified replay are separate accounting concepts.

Canonical:
[../H077_1_QUALIFICATION_CLOSURE_2026-09-19.md](../H077_1_QUALIFICATION_CLOSURE_2026-09-19.md).

## H-077 — Architectural falsification / external validity / post-H-076 residual audit (2026-09-19)

**Status:** IMPLEMENTATION COMPLETE / EXACT-HEAD QUALIFICATION PENDING.  
**Audit baseline:** `main@92a3acb51e87af85a9f380ee04d2cf47d7900ca5`.

**Hypothesis:** PR #36 fully qualified H-077.  
**Result:** refuted as a full qualification claim; core implementation retained.

Reproduced evidence:
- ACK/non-VERIFIED kernel result can be consumed by TaskCompiler as validated terminal completion;
- evidence provenance can still be inferred from verifier-contract requirements;
- expected task/run lineage is not enforced;
- ValidityEnvelope is fail-open for some missing required context and not yet reuse admission;
- external-validity denominators can hide low oracle coverage;
- AFB-v0 is adversarial regression coverage, not yet the fully generated hidden-oracle harness claimed;
- explicit model-inadequacy tripwire is not fully automatic in normal compilation;
- success/replay/savings accounting can remain optimistic for non-VERIFIED ACKs.

Decision: reopen KI-016 and execute H-077.1 inside existing owners. First blocking
experiment: prove TaskCompiler cannot complete an ACK whose canonical verification is
INCONCLUSIVE.

Canonical:
[../H077_1_QUALIFICATION_CLOSURE_2026-09-19.md](../H077_1_QUALIFICATION_CLOSURE_2026-09-19.md).

## H-077 — Truthful Core, AFB-v0, External Validity & Validity Envelope (2026-09-19) — CORE LANDED / QUALIFICATION REOPENED

**Classification:** CORE ARCHITECTURE PRESERVED / TRUTHFUL CORE HARDENED / AFB-v0 BENCHMARKED / EXTERNAL VALIDITY METRICS IMPLEMENTED / ZERO NEW PRIMITIVES CREATED.

**Baseline:** `main@378b5a2df35ac05fe37a606298502d7bb974786d` (formerly 670 passed, 2 skipped).
**Qualification Receipt:** Full Workstation suite: **696 passed, 2 skipped in 353.44s** (100% pass rate).

**Phased Implementation Summary:**
1. **P0 (Truthful Core Cleanup):**
   - **P0-A:** Removed optimistic `verified=True` default from `record_transition` and `on_transition`; removed transition/capability accounting from `on_routing_decision()` (now tracks `deterministic_routes_selected`).
   - **P0-B:** `OperationalKernel.verify_condition()` strictly fails closed (returns False on unknown/unsupported condition types or malformed JSON).
   - **P0-C:** Prohibited synthetic auto-evidence from `verification_expected`; missing evidence executes real declared observer or yields `INCONCLUSIVE`.
   - **P0-D:** `evaluate_verification()` strictly enforces `resource_binding` (`resource_id` matching and version checks, failing closed on mismatch or absence).
   - **P0-E:** Causal transition claims strictly require matching `expected_operation_id` against evidence `operation_id`.
   - **P0-F:** Deprecated boolean verifier callback fails closed as `INCONCLUSIVE` (cannot reach `COMMITTED`).
   - *P0 Tests:* `workstation/tests/test_truthful_core_p0.py` (10/10 passed).
2. **P1 (AFB-v0 Architectural Falsification Benchmark):**
   - Implemented 11 adversarial scenarios (A through K) with independent ground-truth oracles:
     * Scenario A: Phantom Oracle (external resource unmodified) -> caught via resource binding / version check.
     * Scenario B: Masked Drift (syntactic match, semantic break) -> caught via strict predicate evaluation.
     * Scenario C: Blind Concurrency (concurrent external mutation) -> caught via version mismatch.
     * Scenario D: Non-Discriminable Counterexample -> trips `model_inadequacy_non_discriminable_outcome`.
     * Scenario E: False Success by No-Op -> caught via missing operation ID / negative control rejection.
     * Scenario F: Broken Causal Dependency -> halts chain, unverified transition recorded.
     * Scenario G: Validity Envelope Violation -> rejected for out-of-envelope context reuse.
     * Scenario H: Hidden Assumption Violated -> fails closed on unexpected date format / timezone.
     * Scenario I: Side-Effect Hazard -> tracked via external validity audit.
     * Scenario J: Cumulative Drift Reuse Degradation -> tracked across N >= 10 reuses.
     * Scenario K: Read-Verify Race Condition -> caught via freshness / live re-probe version check.
   - *P1 Tests:* `workstation/tests/test_architectural_falsification.py` (12/12 passed).
3. **P2 (External Validity Metrics):**
   - Implemented `ExternalValidityMetrics` and `evaluate_external_validity()` in `workstation/evaluation.py`.
   - Metrics computed: FCOR (False Certification Overhang Rate), Certification Coverage, ReuseReliability(N), External Correctness, Oracle Agreement Rate, False Abstention Rate, Hidden-Assumption Robustness, Model-Inadequacy Detection Recall, False-Safe Rate, Unsafe Mutation Rate, Conflict Detection Recall, Recovery Correctness, Verifier Sensitivity, and ORA ratio.
   - Strict invariants: FCOR is never reported in isolation (`as_triad()` requires FCOR, Coverage, and ReuseReliability); no invented denominators (empty observations return `None`, not 0.0); no synthetic single 0-100 scores.
4. **P3 (Model-Inadequacy Tripwires):**
   - In `workstation/experience_compiler/causal.py`, counterexample refinement without discriminating features fires `model_inadequacy_non_discriminable_outcome`, sets `model_inadequacy_detected = True`, and quarantines the capability.
   - In `workstation/experience_compiler/promotion.py`, `ExperiencePromotionPolicy` enforces `'model_inadequacy': not m.get('model_inadequacy_detected', False)`.
   - In `workstation/control_plane/metrics.py`, `ORAMetrics` tracks `model_inadequacy_events` and reasons.
   - *P3 Tests:* `workstation/tests/test_model_inadequacy_tripwires.py` (4/4 passed).
5. **P4 (Derived Validity Envelope):**
   - Implemented `workstation/control_plane/validity_envelope.py` with immutable `ValidityEnvelope` and pure `derive_validity_envelope()` projecting boundaries from existing canonical owners (Intent, Capability, VerificationContract, Context).
   - Zero new storage or parallel control planes (D-025 compliant).
6. **P5 (Primitive Gate):**
   - NOVAS PRIMITIVES CRIADAS: nenhuma. All requirements implemented within existing owners.

Canonical:
[../ARCHITECTURAL_FALSIFICATION_2026-09-19.md](../ARCHITECTURAL_FALSIFICATION_2026-09-19.md).

---

## H-076 — Verification Contract Synthesis / operational truth audit (2026-09-19)

**Active implementation experiment (baseline `main@14ef1e3ed1f05bec41c70469e231d3b9354439d7`):**
Hypothesis: a pure typed contract/evaluator integrated at the existing Router,
Dispatcher, OperationalKernel, RunClosure and Experience Compiler seams removes the
confirmed self-certification paths without a second state owner. RED evidence is the
current code-level reproduction of F1-F8 (undeclared E3 at `task_compiler.py:760`,
presence-based routing, assumed freshness, executor bool callback, unconditional
invocation verification and non-empty-dict closure). Planned confirming evidence is
the H-076 focused behavior suite followed by the full Workstation regression. Result
classification is **CONFIRMED AND RESOLVED**.

Observed result: the first focused run was infrastructure-blocked by `WinError 5` in
pytest global temp. Native `.venv` Python plus isolated external `--basetemp` and no
cacheprovider resolved setup without product changes. Consolidated focused gate:
**109 passed**. The first full run produced **666 passed, 2 skipped, 4 failed**; all four
were legacy expectations contradicted by H-076 (boolean verifier callback,
unconditional invocation verification/ORA numerator, and an unannotated readback
fixture). After migrating those fixtures to canonical results or explicit owner
evidence, final regression passed **670 tests, 2 skipped in 287.52s**.

**Classification:** VERIFIER-COMPILER SUBSYSTEM FALSIFIED / VERIFICATION-SEMANTICS GAP RESOLVED / IMPLEMENTED & QUALIFIED.

**Baseline:** main@e010c8981a4bdeb89ac94479e0d7e891d48eadae after PR #33.

The three converging analyses established that Hermes already owns the right
verification surfaces but still lacks a typed, provenance-aware contract that proves
why an observation is admissible evidence for specific effects/postconditions/goals.

Post-merge falsification found:
- undeclared verifier metadata can still be promoted to E3 in TaskCompiler;
- same-surface semantic observation can share the mutation failure domain;
- Router verifier sufficiency is still presence-based and freshness is usually a
  boolean assumption rather than a revision/temporal proof;
- dispatcher callbacks can consume executor self-report verification;
- RunClosureProof admits any non-empty verifier_contract;
- Experience Compiler loses observer/extractor/relation/freshness/failure-domain
  identity when compiling verifier knowledge;
- causal replay quality inherits oracle quality.

**Refined hypothesis:** extend CapabilityFormalContract.verifier into a typed
VerificationContract and use a deterministic VerificationEvaluator. Experience
Compiler may propose verifier candidates, but discovery evidence cannot validate them.
Action and oracle are learned separately and bound only after separate falsification.

**Critical new property — Verifier Sensitivity:** a verifier must not only recognize a
correct effect; it must reject absence/corruption/staleness/conflict of the effect in
the failure modes relevant to the EffectClass.

Canonical:
[../VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md](../VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md).

---

## H-075 — In-Flight Operationalization falsification, implementation & qualification (2026-09-19)

**Classification:** IMPLEMENTED & QUALIFIED (Phases P0–P6 Complete, 21 In-Flight Tests Passed, 647 Full Suite Passed).

**Context & Falsification:**
On main@e36b0f0febed96240fa13bbcb78f1cc13c7c0b24:
- missing deterministic executor — REFUTED by DurableBatchRunner;
- missing checkpoints — REFUTED by TaskCompiler/OperationalKernel;
- missing closure predicate — REFUTED by _operational_closure_proven;
- missing rich-editor primitive — MOSTLY REFUTED by plain_text_paste;
- automatic adaptive-to-compiled in-run handoff — CONFIRMED GAP (NOW CLOSED);
- browser_console semantic transparency — CONFIRMED GAP (NOW CLOSED);
- ArtifactStore-to-Browser text reference — CONFIRMED GAP (NOW CLOSED);
- durable causal hierarchical promotion and production telemetry — CONFIRMED GAP (NOW CLOSED).

**Implementation Architecture (Phases P0–P6):**
- **P0 — Truth Seams & Contracts:**
  - `workstation/task_compiler.py`: Decision seams (`WaitDecision`, `HumanDecision`, `ReasoningDecision`, `ComposedDecision`) strictly consume real dataclass fields.
  - `workstation/control_plane/composition.py`: Composed execution requires authoritative final-goal verification, dependency satisfaction, and verifier closure.
  - `workstation/experience_compiler/promotion.py`: Conservative derivation failing closed on multiple/incompatible families or unproven authority origin.
  - Receipts: `test_control_plane_integration.py` (12 passed), `test_learned_capability_routing.py` (7 passed).
- **P1 — RunClosureProof & Utility Admission:**
  - `workstation/run_closure.py`: Implemented `RunClosureProof` with 21 canonical fields, `compute_expected_operational_utility()`, and `evaluate_run_local_closure()` enforcing 10 admission conditions.
  - Receipts: `test_run_closure.py` (2 passed).
- **P2 — Adaptive-to-Compiled Handoff & Prefix Recovery:**
  - `workstation/run_closure.py`: `HandoffWakeCondition`, `ExecutionEnvelope`, `RunScopedCapability`, `synthesize_in_flight_work_execute_request()`, `execute_in_flight_handoff()`, and `recover_verified_prefix()`.
  - `workstation/operational_capabilities.py` & `workstation/control_plane/router.py`: `RunScopedCapability` strictly excluded from global promoted index.
  - Receipts: `test_in_flight_handoff.py` (6 passed).
- **P3 — Browser Lowering & Artifact Data Plane:**
  - `tools/browser_workstation.py` & `tools/browser_tool.py`: `resolve_browser_type_text()` enforcing mutual exclusivity, ownership check, <=1MB size, and text/json MIME.
  - `workstation/artifacts.py`: `media_type` parameter added to `ArtifactStore.store()`.
  - `apps/desktop/electron/workstation-browser-runtime.ts`: `selectAll` fallback for rich editors.
  - `workstation/procedure_trace.py`: opaque adaptive execution tracking (rejecting `browser_console` from candidate steps).
  - Receipts: `test_browser_lowering_and_artifacts.py` (4 passed).
- **P4 — Durable Invocations & Causal Composite Promotion:**
  - `workstation/operational_kernel.py`: Invocations persisted to `ArtifactStore` and `ExecutionJournal` with lineage (`task_id`, `run_id`, `operation_id`, `authority_scope`); `load_invocations(task_id)` across restarts; child drift/pin enforcement.
  - `workstation/experience_compiler/hierarchical.py`: `propose_composite` marks candidate as `DISCOVERED`; `promote_composite` enforces `ExperiencePromotionPolicy` (causal replay and counterexample verification).
  - Receipts: `test_hierarchical_causal_promotion.py` (4 passed).
- **P5 — Non-Resident Await & Production Telemetry:**
  - `workstation/task_compiler.py`: Connected `WaitDecision` to `AwaitConditionStore` with `worker_released=True`, releasing worker processes on semantic waits and resuming via `handle_event()`.
  - `workstation/control_plane/metrics.py`: `ORAMetricsCollector` and `ORAMetrics` wired directly into `OperationalKernel.execute_capability` and `TaskCompiler` recording real transitions, waits, and reasoning re-entry rates.
  - Receipts: `test_non_resident_await_telemetry.py` (4 passed).
- **P6 — 12-Item Trello-Shaped Benchmark Qualification:**
  - `workstation/tests/test_trello_benchmark_qualification.py`: 12-item benchmark passing end-to-end with canary + replay, handoff of remaining 10 items, large >50KB artifact ref resolution, deliberate anomaly handling with `AttentionPacket`, prefix recovery, and clean resume without duplicate replays.
  - Full workstation suite regression: **647 passed, 2 skipped in 287.92s**.

Canonical:
[../IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md](../IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md).

---


## H-074 — Hierarchical Operational Learning / Operational Reasoning Amortization (P0–P4) implementation claim (2026-09-19) — SUPERSEDED BY H-075 AUDIT

**Historical classification at implementation time:** IMPLEMENTED / CONTRACT VALIDATED / 620 passed, 2 skipped, 0 failed. **H-075 supersedes the end-to-end closure claim:** those receipts prove components, not the currently open integration properties.

**Executive Invariant:**
Hermes must learn not only facts about the world, but verified ways of acting on it. The more an operational transformation proves stable, causal, reusable and verifiable, the less reasoning should be required to execute it again.

**Phased Implementation & Structural Closures:**
- **P0 — Truthful Control Plane Closure**:
  - `workstation/control_plane/dispatcher.py`: Added `DispatchStatus.NEEDS_VERIFICATION`. `CertifiedDispatcher.dispatch()` strictly fails closed without an authoritative verifier unless the capability formal contract explicitly authorizes ACK-only completion (`allow_ack_only=True` / `E0`).
  - `workstation/control_plane/composition.py`: Added `certificate_hash()`, `canonical_json()`, and `operation_id` to `CompositionCertificate`.
  - `workstation/task_compiler.py`: Replaced fake plan echoing in `_execute_route` with real sequential invocation of composed child capabilities via `OperationalKernel.execute_capability`. Removed synthetic wildcard authority minting (`request["trusted_authority"]` / `{"*"}`). Trusted authority is derived exclusively from immutable sources (`trusted_authority`, persisted Kanban Task, or ScopedPolicyEngine), and request authority can only narrow. Fixed `RoutingDecision` attribute accesses (`await_condition`, `scope`, `open_condition`, `attention_packet`, `requires_reconciliation`, `reason`).
  - `workstation/execution_policy.py`: In `semantic_target_family`, filtered out broad terminal runners (`terminal:python:-m`, `terminal:bash:-c`, `terminal:sh:-c`, etc.) lacking concrete target scripts/modules. Gated `REQUIRE_COMPILE` strictly on operational closure proof (`_operational_closure_proven`).
  - `tools/browser_tool.py`: Validated forbidden authority headers syntactically prior to network DNS resolution in `browser_read_http`.

- **P1 — Experience Compiler ↔ Capability Router Bridge**:
  - `workstation/experience_compiler/models.py`: Added `authority_ref` and `authority_scope` to `Provenance`.
  - `workstation/experience_compiler/promotion.py`: Implemented `derive_formal_contract(capability)` deriving typed preconditions (IR `EQ`), postconditions (IR `EQ`), canonical effects (IR `SET`/`CALL`), proven authority requirement from provenance, and verifier requirements. Returns `None` if authority origins are unproven/untrusted.
  - `workstation/experience_compiler/compiler.py`: Added `operation_families` and `target_families` to `learning_metadata`, populated `formal_contract` and `family_id` on compile and promote, and updated `cap.lifecycle = CapabilityLifecycle.PROMOTED` on promote.
  - `workstation/control_plane/router.py`: Dynamic index rebuild (`self._rebuild_index()`) on route, querying index with `target_family`, `operation_family`, and `family_id`. Promoted learned capabilities route deterministically to `ExecutableDecision` with a valid `RoutingCertificate` without LLM calls.

- **P2 — Non-Resident AwaitCondition**:
  - `workstation/control_plane/waiting.py`: Created `AwaitContinuation` holding durable subgraph, plan metadata, capability pins, contract fingerprints, and last verified state. Added `is_non_resident_wait()` to classify semantic waits (`WAITING_FOR_EVENT`, `WAITING_FOR_TIMER`, `WAITING_FOR_EXTERNAL_STATE`, `WAITING_FOR_HUMAN`, `WAITING_FOR_APPROVAL`) to release worker processes.
  - Hardened `TriggerCoordinator` with `run_id`, `task_id`, and `operation_id` fencing, evaluated predicates against authoritative state before wake ("EVENT WAKES. AUTHORITATIVE STATE CONFIRMS."), and ensured condition deletion occurs ONLY after resumption is confirmed (`resumed == True`).

- **P3 — Hierarchical Experience Compiler**:
  - `workstation/experience_compiler/models.py`: Defined `CapabilityInvocation` dataclass tracking capability identity, pinned version, typed inputs/outputs, state before/after, verified effects, authority scope, and lineage.
  - `workstation/operational_kernel.py`: Captured `CapabilityInvocation` upon verified execution in `self.invocations`. Defaulted composite output to include dependency outputs (`output["deps"]`).
  - `workstation/operational_capabilities.py`: In `from_dict`, lazily imported and parsed `CapabilityFormalContract` when `formal_contract` is a dictionary.
  - `workstation/experience_compiler/hierarchical.py`: Created `HierarchicalExperienceCompiler` to mine recurring sequences across runs (`mine_sequences`) and propose composite capabilities (`propose_composite`) with explicit `CapabilityDependency` (preserving child dependencies without flattening into micro-primitives). Enforced causal JOIN, authority JOIN, verifier closure, positive utility, and drift/quarantine propagation.

- **P4 — Operational Reasoning Amortization Metrics**:
  - `workstation/control_plane/metrics.py`: Created `WakeReason` enum and `ORAMetrics` dataclass computing `ora_ratio`, `composite_reuse_rate`, `wait_non_residency_rate`, `wake_llm_rate`, and wake reason breakdown, strictly preserving `None` / `null` for unknown denominators or unmeasured metrics.

**Receipts & Validation:**
- `workstation/tests/test_learned_capability_routing.py`: 4/4 passed.
- `workstation/tests/test_await_trigger_plane.py`: 10/10 passed.
- `workstation/tests/test_hierarchical_experience_compiler.py`: 4/4 passed.
- `workstation/tests/test_ora_metrics.py`: 3/3 passed.
- Full workstation test suite: `python -m pytest -q -o pythonpath=. workstation/tests`:
  **620 passed, 2 skipped, 0 failed in 235.36s**.

**Canonical Design Reference:**
[../HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md](../HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md).

---

## H-071 corrective implementation run — 2026-09-19

**Baseline:** clean, synchronized `main@6328894c0a5f51a61da772593842c25d377d553f`.

**Hypotheses / experiment order:**
1. reproduce the committed-source `apply_core_integration.py --check` anchor failure;
2. add behavioral RED coverage proving ACK without accepted evidence cannot commit and a
   composition plan echo is not execution;
3. repair dispatcher/composition through the existing CertifiedDispatcher and
   OperationalKernel owners, then qualify focused suites before proceeding to authority,
   operational closure, Browser-session HTTP hardening, integration metadata and native
   Electron proof;
4. retain exact command/results and classify any unavailable product/CI evidence honestly.

**Result:** P0-A..H implemented on branch `codex/browser-operational-admission-closure`.
ACK-only dispatch remains acknowledged; real composition executes in order and requires
per-step verification; authority cannot originate in request/session defaults; mandatory
compilation requires explicit operational closure; native readback is session-bound,
same-origin/reference-first/fail-closed; the integration anchor and real Electron fixture
are repaired.

**GREEN receipts:** focused Python 27/27; Workstation 607 passed / 2 skipped; Electron
1791 passed / 5 skipped; admission Vitest 4/4; Desktop typecheck; integration dry-run;
H004 `VALIDATED`; H013 2/2; Work100 30/30. Required exact-head CI remains pending, so
the candidate is implemented/local-qualified but not yet release-qualified.

---

## H-073 — Hierarchical operational learning / reasoning amortization architecture audit (2026-09-19)

**Classification:** ARCHITECTURE SYNTHESIS VALIDATED / FOUR INTEGRATION GAPS CONFIRMED / IMPLEMENTATION OPEN.

**Audit basis:** current `main` after Experience Compiler + Verified Operational
Control Plane implementation, with direct review of `experience_compiler/*`,
`operational_capabilities.py`, `operational_kernel.py`, `task_compiler.py`,
`control_plane/{router,composition,dispatcher,waiting}.py`, `kanban.py` and
their focused tests.

**Question:** does Hermes Work actually converge toward a system where repeated
verified action patterns progressively leave the LLM reasoning path, become
deterministic operational knowledge, compose into larger capabilities, wait without
resident reasoning, and wake the LLM only at unresolved semantic boundaries?

**Result:** **yes in architectural direction and substantial substrate; not yet as
one closed product loop.** The desired abstraction is a clarification/extension of
the current design, not a competing architecture.

### Confirmed findings

- **H-073-A — correct atomicity is VOT, not the smallest gesture.**
  The existing Experience Compiler definition is stronger than a literal
  microautomation model: learn the smallest semantically closed, parameterizable,
  executable and verifiable transition with positive reuse value. Do not create
  one capability per click/tool call by default.

- **H-073-B — real accepted experience already reaches automatic mining.**
  `workstation/kanban.py` projects accepted canonical runs into
  `ExperienceCorpus` and calls `ExperienceCompiler(...).mine()` after commit.
  This is not documentation-only.

- **H-073-C — learned capability and semantic Router are partially disconnected.**
  Experience Compiler emits learned `OperationalCapability` objects with learned
  pre/postconditions, verifier contract and fingerprints, but does not currently
  derive/populate `formal_contract`. CapabilityRouter skips capabilities lacking
  that typed formal contract. Exact fingerprint reuse works; broad semantic
  OperationIntent routing does not automatically consume every promoted learned
  capability.

- **H-073-D — runtime composition exists, hierarchical learned composition does not.**
  Capability dependencies and `CompositionEngine` exist, and a learned atomic
  capability can be reused inside larger flows. There is no first-class
  CapabilityInvocation corpus/miner that observes recurring A -> B -> C capability
  sequences and promotes a causally proven dependency-based composite.

- **H-073-E — persistent wait abstraction exists but production waiting remains resident.**
  `AwaitCondition` and `TriggerCoordinator` encode the right durable/event model,
  but TaskCompiler still uses `RuntimeEventBus.wait()` or bounded
  `time.sleep()` polling in the main step loop. The LLM can be absent, but a worker
  remains resident. TriggerCoordinator confirms/deletes a condition; it does not yet
  reconstruct and execute the stored continuation.

- **H-073-F — control-plane truth gaps block trustworthy hierarchy.**
  H-071 remains a prerequisite: false COMPOSE, ACK-as-verification and authority
  minting must be closed before composite learning can trust execution outcomes.
  Additional route branches must use the actual decision fields
  (`await_condition`, `scope`, `open_condition/attention_packet`) rather than
  stale accessor assumptions.

### Chosen synthesis

Preserve the existing architecture and complete this hierarchy:

~~~text
trusted primitives
  -> VOT / OperationalCapability
  -> Composite OperationalCapability
  -> Deterministic Workflow
  -> AwaitCondition / event
  -> OpenCondition / AttentionPacket
  -> WAKE_LLM only for unresolved semantics
~~~

The output vocabulary of one compilation level may become the observed vocabulary
of the next, but every level must independently prove semantic closure and causal
support. Frequency is candidate evidence, never promotion authority.

### Required implementation sequence

1. **P0:** close H-071 / Browser Operational Admission truth seams.
2. **P1:** derive conservative `CapabilityFormalContract` for eligible learned
   capabilities and prove `OperationIntent -> Router -> learned capability`.
3. **P2:** make AwaitCondition own non-resident continuation; persist/fence
   continuation, release executor, re-enter Router after event + authoritative
   state confirmation; scheduled polling only as fallback observer.
4. **P3:** capture CapabilityInvocation traces and reuse EC causal/replay/promotion
   machinery to create dependency-based composite candidates.
5. **P4:** add Operational Reasoning Amortization metrics and shadow rollout.

### Metric hypothesis

**ORA = verified semantic transitions executed with zero LLM intervention /
total verified semantic transitions.**

Desired trend: ORA rises and LLM calls per verified transition falls without
verification quality loss, increased uncertain mutation rate or hidden drift.

**Refuting evidence that would change this plan:** if current main already derives
formal contracts for learned candidates in a different canonical owner, already
performs non-resident continuation resume through AwaitCondition, or already mines
CapabilityInvocation sequences, this milestone must collapse into regression
proof instead of adding duplicate mechanisms. The audit found no such production
closure.

**Canonical specification:**
[../HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md](../HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md).

---

## H-072 — Browser Ownership & Recovery post-implementation audit (2026-09-19)

**Classification:** IMPLEMENTATION BASE RETAINED / CORRECTIVE P0 REOPENED / PRODUCT QUALIFICATION OPEN.

**Baseline retained:** commit family around `3c72763da79525587b97c09ad561b2b0ca2701de`
landed shared occlusion, host fencing, `preferredTaskId`, task-bound lazy recovery,
cross-session isolation and activity-vs-visibility projection. Focused evidence
(88 Vitest, typecheck, H004, Work100) remains useful.

**Post-implementation findings on `main@6328894c0a5f51a61da772593842c25d377d553f`:**
- **H-072-A — destructive bulk clear:** TaskRail can classify `parked + working`,
  but runtime `clearParkedTasks()` destroys all parked lifecycle tasks. One idle
  parked task can expose Clear and cause another working/waiting/human-controlled
  parked task to be destroyed.
- **H-072-B — first-frame blank race:** Chat pane local state starts with no tasks, so
  first `attach('chat')` may carry no `preferredTaskId`; fallback blank can become
  visible before the returned state triggers a second, task-bound attach.
- **H-072-C — E2E proof gap:** focused recovery tests inject the preferred task
  directly. H013 has not yet proven cold renderer discovery + A/B restart and its
  local bridge declaration does not yet include `preferredTaskId`.
- **H-072-D — alias proof gap:** live/root lineage is handled, but BrowserPane has no
  dedicated `parent_session_id` behavior proof.
- **H-072-E — occlusion authority too broad:** the shared selector still grants
  hide authority to generic roles/slots in addition to the explicit
  `data-native-view-occluder="true"` marker.
- **H-072-F — qualification wording exceeded evidence:** the ownership lane had strong
  focused evidence, but the exact renderer/restart product invariant was not proven.
  Current global main is also red in the separate Browser Operational Admission
  integration-anchor gate, so repository-wide "100% regressions green" is incorrect.

**Smallest discriminating experiments:**
1. H072-E001: parked-working + parked-idle through the real bulk-clear bridge; only
   idle may be destroyed.
2. H072-E002: cold BrowserPane mount from persisted BrowserTask with no preseeded
   renderer task state; assert first native attach is already task-bound.
3. H072-E003: extend H013 for Chat A/B -> process restart -> cold B restore -> switch A,
   including stale host cleanup and one-page-per-task.
4. H072-E004: live/root/parent alias matrix resolves one canonical BrowserTask.
5. H072-E005: only explicit native-view-occluder markers hide Chromium; tooltip and
   unrelated role/slot nodes do not.

**Refuting evidence:** H-072 may be narrowed if instrumentation proves first attach
cannot become visually observable, or if canonical execution state is unavailable at
the bulk-clear owner. Neither has been proven on current main.

**Closure:** all five experiments green at the appropriate renderer/runtime/E2E
layer, affected H004/H013/Work100 gates green, exact-head failures classified, and no
new state owner.

**Canonical plan:** [../BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md]

---

## H-071 — PR #29 post-merge operational truth audit (2026-09-19)

**Classification:** REPRODUCED CODE/CI GAPS / CORRECTIVE P0 REQUIRED / QUALIFICATION OPEN.

**Evidence base:** `main@24997c9af8256ac41001bdee9f827c643d5598e4`, PR #29 diff, current production code, focused tests and exact-head GitHub Actions jobs.

**Confirmed findings:**
- **H-071-A — false COMPOSE success:** `TaskCompiler._execute_route()` dispatches `ComposedDecision` with a callback that returns `{"success": True, "plan": [...]}` rather than executing the plan. Current dispatcher semantics can mark that path VERIFIED/COMMITTED.
- **H-071-B — ACK collapsed into verification:** `CertifiedDispatcher.dispatch()` initializes `verified=True`; absent `verifier_fn`, a success/ack result advances to VERIFIED/COMMITTED unless it explicitly contains an error. This violates the evidence-strength boundary.
- **H-071-C — authority trust root too broad:** `TaskCompiler._execute_route()` accepts request `trusted_authority` and may synthesize `EXTERNAL_REVERSIBLE + * + *` from bare task/session presence when no persisted grant is found.
- **H-071-D — mandatory compilation still lacks closure proof:** `execution_policy.decisions_for_calls()` can emit `REQUIRE_COMPILE` from `sem_fp && sem_count >= 3` without proving deterministic primitive/capability, verifier, authority/policy and certified-dispatch closure required by D-021.
- **H-071-E — Browser HTTP readback contract incomplete:** Electron does not enforce same-origin-by-default and uses partial literal-host blocking; Python `browser_read_http` can fall back to process `requests.request`, changing the authenticated Browser-session semantics. Full payload retention before inline truncation also needs proof.
- **H-071-F — terminal semantic family remains over-broad:** syntactic families such as `python:-m` / `bash:-c` can conflate unrelated arbitrary commands.
- **H-071-G — qualification failed on exact PR head:** Workstation CI `core-patch-dry-run` and Workstation Browser Windows `desktop-typecheck` both failed before downstream gates with `ERROR: browser tool route anchor missing for browser_type` from `python workstation/scripts/apply_core_integration.py --root . --check`. The local 599-pass/focused suites remain useful but do not establish exact-head product qualification.
- **H-071-H — current dogfood test is simulation-heavy:** the Python reference capability and fake Electron WebContents prove orchestration/strings, not real contenteditable/ProseMirror-like paste + authenticated same-origin readback.

**Corrective experiment order:**
1. RED tests for ACK-without-verifier and COMPOSE-without-execution;
2. implement real composition execution/non-terminal planning and evidence-gated commit;
3. RED tests for task/session-without-grant and request-authored trusted authority;
4. remove synthetic wildcard authority and source trust from canonical runtime context;
5. RED/GREEN operational-closure admission, including same-family/no-closure => SUGGEST and same-family/verified-closure => REQUIRE;
6. harden native Browser readback and remove bound-runtime process fallback;
7. repair core-integration `browser_type` anchor and rerun Linux/Windows checks;
8. real Electron/WebContents fixture for rich editor + delayed hydration + cookie + same-origin readback + verification + replay;
9. exact-head full gates, H004/Work100 where affected, then update status to qualified.

**Decision:** D-021 remains authoritative; this is implementation non-compliance, not a replacement architecture.

**Closure condition:** all corrective contracts green on the exact candidate head, no skipped required Workstation/Windows gates, and real runtime fixture demonstrates `novel discovery -> verified canary -> deterministic fan-out` without false verification, synthetic authority or compile deadlock.


## H-070 — Native Browser operational admission & primitive closure (2026-09-18)

**Classification:** IMPLEMENTATION LANDED; historical local qualification claim superseded by H-071. P0 is reopened until corrective/product gates pass.

**Observed & Diagnosed:** native Electron Chromium succeeds at Trello navigation/click/read, yet the
task reached `durable_compile_required <-> PREFLIGHT_REQUIRED` deadlock while the durable contract
demanded mutation authority + independent readback + verifier that the Browser Kernel could not faithfully
express for the discovered rich-text operation.

**Implementation & Verification:**
- **P0.1 Effect Truth:** `read_preview` and `read_window_below` explicitly registered as `ToolEffect.PURE_READ`. Added dynamic `effect_resolver` to `ToolEntry` in `tools/registry.py` and `tools/effects.py`. Multi-action `drive_preview` classifies `"elements"` as discovery/read and mutations as `MUTATION`.
- **P0.2 Semantic Admission:** Removed non-browser structural count fallback from `execution_policy.py`. Scoped `write_file`/`patch` to `filesystem.file:<normpath>` and `terminal` to command families (`terminal:<cmd>[:<sub>]`). Homogeneous repetition retains compilation gating only when positive semantic homogeneity exists.
- **P0.3 Browser Primitives:** In `workstation-browser-runtime.ts` and `tools/browser_tool.py`, implemented `browser_type(mode="plain_text_paste", semantic_anchor=...)` using DOM `ClipboardEvent("paste")` + `DataTransfer` with semantic anchor re-acquisition. Implemented `browser_read_http` (GET/HEAD only, private IP / RFC1918 / loopback blocking, ArtifactStore spillover for large payloads).
- **P0.4 Unified Admission:** Capability Router is the authoritative mutation-admission owner; legacy repetition detector serves as an advisory/learning signal.
- **P0.5 Trusted Authority:** Implemented `AuthorityScope.narrow(requested)` in `workstation/control_plane/lattice.py`. In `TaskCompiler._execute_route`, ambient authority is resolved from trusted task context; requested authority can ONLY narrow permissions; untrusted minting fails closed with `ASK_HUMAN`.
- **P0.6 Certified Dispatch & Uncertainty:** All route executions pass through `CertifiedDispatcher` enforcing `PREPARED -> DISPATCHED -> ACKNOWLEDGED -> VERIFIED -> COMMITTED`. Mutating browser timeout raises `TIMEOUT_UNCERTAIN` (`state_changed=True`, `retryable=False`), blocking blind retry. Electron runtime adds generic SPA readiness checks with bounded re-observation (< 1.2s total).
- **P0.7 Dogfood Reference Capability:** Verified in `test_browser_operational_admission.py` (13/13 passed) covering edit -> paste -> save -> readback -> verify with zero-planning fan-out.
- **P0.8 Qualification:** Full workstation suite: 62 test files, 599 tests passed, 0 failed, 2 skipped in 148.3s. Desktop Vitest admission suite: 4 passed. Zero lint/whitespace errors (`git diff --check` clean).

**Decision:** D-021.
**Canonical plan:** ../BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md.

## H-069 — Verified Operational Control Plane (CP0–CP9) implementation & contract validation (2026-09-18)

**Classification:** IMPLEMENTED / CONTRACT VALIDATED / 100% REGRESSIONS GREEN.

**Evidence base:** current `main` (baseline `2479b712f8a3912ff6df9066d1782e8b407b4177` and head `63fa4244a3c5c1a30ec766fc9023437f61fdff62`).
Canonical target: [../VERIFIED_OPERATIONAL_CONTROL_PLANE.md](../VERIFIED_OPERATIONAL_CONTROL_PLANE.md).

**Core Principle:**
> **THE LLM PROPOSES. THE ROUTER PROVES. THE POLICY AUTHORIZES. THE RUNTIME EXECUTES. THE VERIFIER CONFIRMS.**
> **NO VALID CERTIFICATE -> NO DISPATCH.**

**Implementation and Experimental Verification:**
- **CP0 (IR & OperationIntent):** Typed `Predicate` AST (`TRUE`, `FALSE`, `EQ`, `NEQ`, `EXISTS`, `ABSENT`, `AND`, `OR`, `NOT`, `IN`, `SUBSET`, `LT`, `LTE`, `GT`, `GTE`, `UNCHANGED`, `TRANSITION`), deterministic evaluation, algebraic entailment (`entails`), `Effect` AST (`SET`, `CREATE`, `DELETE`, `MOVE`, `CALL`, `SEND`), effect containment (`effect_contained`), invariant preservation (`preserves_invariant`), immutable `OperationIntent` with cryptographic SHA-256 digest, and `AuthorityScope` lattice. Tested in `test_operation_intent.py` (7 tests, GREEN).
- **CP1 (Formal Capability Contract):** `CapabilityFormalContract` added to `workstation/control_plane/contract.py`; `OperationalCapability` extended with `formal_contract`, `family_id`, `alias_of`, `superseded_by`; registry index and family search in `operational_capabilities.py`. Existing 12 capability tests remain 100% green.
- **CP2 (Capability Router & RoutingCertificate):** `CapabilityRouter` implemented in `workstation/control_plane/router.py`. Strictly checks 15 proof obligations (target match, inputs bound, preconditions, goal entailment, effect containment, invariant preservation, authority coverage, policy, approvals, verifier availability, evidence strength, state freshness, capability health, no outstanding uncertainty, and deterministic closure) before issuing `RoutingCertificate`. Tested in `test_capability_router.py` (9 tests, GREEN, including metamorphic invariant property tests).
- **CP3 (Bounded Backward Chaining & Threat Detection):** Directed backward search in `workstation/control_plane/composition.py` with strict depth, node, and wall-time budgets; `detect_causal_threats` identifies step conflicts and reorders or yields `ReasoningDecision`. Tested in `test_control_plane_composition.py` (5 tests, GREEN).
- **CP4 & CP5 (Certified Dispatcher & Trigger Plane):** `AwaitCondition` with typed criteria, `AwaitConditionStore` persisted via `ArtifactStore`, run-fenced `TriggerCoordinator` enforcing *Event wakes; authoritative state confirms*, `TriggerCircuitBreaker`, and `CertifiedDispatcher` enforcing idempotency and `DispatchStatus.UNCERTAIN` protection. Tested in `test_await_trigger_plane.py` (8 tests, GREEN).
- **CP6 (Reasoning Handoff):** `OpenCondition` and `AttentionPacket` in `workstation/reasoning_handoff.py` provide compact context handoff to LLM for unresolved propositions without prompt bloat or replay hallucinations. Tested in `test_control_plane_integration.py`.
- **CP7 (Semantic State Synthesis):** Integrated authoritative projection over canonical artifacts and environment state.
- **CP8 (Metrics, Failure Attribution & Shadow Router):** `ShadowRouter` (dispatches 0 mutations), `FailureAttributor` (classifying failures into 7 distinct root causes: `INTENT_ERROR`, `OBSERVATION_ERROR`, `ROUTING_ERROR`, `CAPABILITY_DRIFT`, `COMPOSITION_ERROR`, `POLICY_ERROR`, `RUNTIME_FAILURE`), and `VOLCMetrics` (Verified Outcome Lifetime Cost vector preserving unknown metrics as `None`). Tested in `test_control_plane_integration.py`.
- **CP9 (TaskCompiler & Tool Integration):** `workstation/task_compiler.py` supports `action="route"` and `operation_intent` parameter in `execute()`, routing through `CapabilityRouter` and dispatching via `CertifiedDispatcher`. Tool schema in `tools/workstation_work.py` updated with `"route"` action and intent properties. Tested in `test_control_plane_integration.py` (7 tests, GREEN).

**Test Results:**
- Dedicated Control Plane suite: 36 passed (5 files, 8.1s).
- Workstation regression suite: 116 passed (5 files, 29.2s).
- Work100 regression benchmark: 30 PASS, 0 FAIL, 0 COVERAGE_GAP, 0 NOT_RUN_ENVIRONMENT.
- Full compatibility with existing Kanban, ArtifactStore, RecipeStore, ProceduralMemory, and TaskRun contracts.

## H-068 — Experience Compiler / Verified Operational Transition learning boundary (2026-09-18)

Implementation experiments (base `2479b712f8a3912ff6df9066d1782e8b407b4177`):
- EC0 hypothesis: durable derived anchors repair identity without weakening policy.
  RED: 4 failures; GREEN with Progressive Compilation: 14 passed.
- EC1 hypothesis: bounded owner-state projections preserve semantic deltas and redact handles.
  RED: 3 failures; GREEN with Progressive Compilation: 17 passed.
- EC2 hypothesis: artifact refs suffice for corpus; state predicates distinguish branches.
  RED: 3 failures; GREEN: 10 passed.
- EC3 hypothesis: structural generalization plus negative examples yields conservative contracts.
  RED: 3 failures; GREEN: 13 passed.
- EC4 hypothesis: reverse dependencies prune incidental observations without claiming intervention.
  RED: 2 failures; GREEN: 15 passed.
- EC5 hypothesis: fixture-only replay/reduction raises causal grade separately from E strength.
  RED: 7 failures; GREEN with Operational Capability tests: 34 passed.
- EC6 hypothesis: independent admission and SQLite metadata pins prevent count-based learned authority.
  RED: 4 failures; GREEN: 38 passed with the existing capability contracts.
- EC7 hypothesis: consolidation emits existing capabilities with exact fingerprints and zero planning calls.
  RED: 2 failures; GREEN: 40 passed with capability contracts.
- EC8 hypothesis: real filesystem transitions replay through the same kernel and compose durably.
  Integration RED: atomic persistence/validation ordering failure; GREEN: 42 passed.
  Additional proof: real subprocess readback, learned cross-backend composite,
  atomic reuse in two larger flows, indexed corpus ordering and controlled C5.
All runs use `scripts/run_tests.sh` through Git Bash with native Windows Python.
Git Bash needed sandbox escalation after signal-pipe WinError 5; no product change for that failure.
Focused gates: 113 passed (8 files, 54.5s), then 114 passed (49.9s).
Final focused: 116 passed (8 files, 62.5s), including 40 compiler contracts.
First full gate: 545 passed, 2 skipped (56 files, 255.7s).
Expanded full gate: 547 passed, 2 skipped (56 files, 230.3s).
Final full: 550 passed, 0 failed, 2 skipped (56 files, 226.8s).
Post-review strict observed-binding admission was regated focused after the
broad suite's compiler file completed; other product code remained unchanged.
Exact qualification commands are recorded in TESTING.md.
Final review experiments:
- RED: 2 failures reproduced automatic mining dropping failures and missing
  predicates being misclassified as discriminating evidence. GREEN: 114 focused.
- RED: conditional replay failed after normalization/alignment. Fixed exact
  control identity in alignment and retained only the harmless boolean banner
  visibility flag/boolean delta in the canonical sanitizer; cookies/credentials
  remain excluded. GREEN: 61 across compiler/progressive/capability owners.
- RED: source_trace_refs lacked actual source sample URIs. Corpus now projects
  canonical sample_ref into provenance; candidate retains successful and negative
  source artifact refs. Persisted conditional replay covers both banner states.
  GREEN: 115 focused (57.0s).
- RED: real large filesystem read leaked 78KB inline through capability work_execute.
  Canonical reference-plane projection now externalizes large outputs; resume
  preserves the compact confirmed result. GREEN: 116 focused (41.1s).
- RED: legacy `$item.text` observation was admitted as an executable literal.
  Learned compilation now refuses unresolved observed binding expressions;
  samples remain in corpus until owner binding evidence exists. Declared manual
  capability variables keep their existing runtime contract. GREEN: 116 focused (62.5s).
Adjacent guardrails/checkpoint gate: 8 passed (2 files, 11.9s).
Work100: 30 PASS, 0 FAIL/COVERAGE_GAP/NOT_RUN_ENVIRONMENT, including Electron contracts.
Native Desktop environment correction: Electron exists in root node_modules
(hoisted), not apps/desktop/node_modules. Initial NOT RUN inference from the
workspace-local path was incorrect. Final Work100 again passed all 30 cases.
H004 native smoke: `node workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs`
returned exit 0 / `H004_CLASSIFICATION=VALIDATED`, live/controller/destroy and
restart markers passed. Windows 10.0.26200, Electron 40.10.2; restart PIDs
32148 -> 29168 preserved logical Task identity and recreated exactly one page.
Temporary fixture roots were resolved/checked and no concurrent H004 process
was found before running. Profiles were isolated; only loopback fixture pages.
Compiled main bundle exists. Smoke scope remains native BrowserTask lifecycle,
not full packaged/product Experience Compiler qualification.
No live provider mutations, destructive ablations or paid-provider savings claims.

Changed files: `experience_compiler/{models,state_abstraction,corpus,segmentation,
generalization,causal,promotion,compiler}.py`, its package entrypoint and
`tests/test_experience_compiler.py`; extended owners: `procedure_trace.py`,
`memory.py`, `operational_capabilities.py`, `operational_kernel.py`,
`task_compiler.py`, `kanban.py`, `recipes.py`; updated the specification, current state,
intelligence map, roadmap, testing document and context entrypoint.
Baseline: clean main fast-forwarded from `e1fb739d92c183048be7fc3dd9e3820df92f1846`
to fetched `2479b712f8a3912ff6df9066d1782e8b407b4177`. The authoritative
integration history is recorded in Git.
Remaining evidence debt: full product/packaged Desktop E2E, live authenticated browser qualification,
paid-provider economics and corpus-wide coverage/novelty denominators. Owner fixtures
must reset between interventions and honor deadlines. Raw observational provenance
does not automatically become trusted learned-mutation authority. Redacted legacy
text bindings require owner-supplied parameter evidence before learned compilation.

**Classification:** IMPLEMENTED / CONTRACT VALIDATED; native qualification separate.

**Evidence base:** current `main` after PR #26 plus the two 2026-09-18
state-transition / Experience Compiler investigations. Canonical target:
[../EXPERIENCE_COMPILER.md](../EXPERIENCE_COMPILER.md).

**Finding:** H-067 solved the deterministic execution substrate but not the
automatic consolidation problem. The correct next unit is not a raw tool call,
successful trace, script or whole workflow. It is a **Verified Operational
Transition (VOT)**: a semantically closed, parameterized and verifiable state
transition from which an OperationalCapability can be inferred.

**Current implementation confirmed:**
- semantic target family/fingerprint is implemented in `execution_policy.py`;
- OperationalCapability Registry/Resolver and Operational Kernel are implemented;
- `work_execute(capability_id, inputs)` and exact promoted replay are implemented;
- native Browser target metadata is structured and transient refs are not intended
  as durable identity.

**Historical gaps reproduced at the baseline and addressed by EC0–EC8:**
1. `procedure_trace.py` records actions with before/after refs, not normalized
   semantic TransitionSamples/state deltas.
2. `record_trace()` derives `arguments["semantic_anchor"]` after observing the
   previous Browser inventory but calls
   `semantic_operation_fingerprint(name, args)` using the original args. Ref-only
   Browser actions can therefore retain structural rather than semantic trace
   identity.
3. The same capture path can emit anchor `type="name"`; `candidate_steps()`
   currently admits only `role_name`, `testid`, `text`. This is a concrete
   capture/replay contract mismatch.
4. Current learning still collapses approximately
   `trace -> candidate_steps() -> experience_candidate()`; there is no
   cross-trace alignment, anti-unification, invariant/action-model inference,
   Operational Slice or causal validation first.
5. `OperationalCapabilityRegistry.record_validation()` defaults to
   `auto_promote_threshold=2`. Count-based validation alone is insufficient
   authority for experience-learned mutable capabilities.
6. There is no explicit causal-confidence dimension separate from E0-E3 effect
   evidence and no trust/taint-aware learned promotion policy.

**New architecture rule:** recurrence, generalization and causality are different
questions and must not collapse into one threshold.

~~~text
RECURRENCE
  -> pattern hypothesis

GENERALIZATION
  -> parameterized candidate

CAUSAL SUPPORT
  -> dependency slice + failures + replay/intervention

PROMOTION
  -> evidence + causal grade + provenance/taint + risk + utility
~~~

**Causal evidence target:** C0 one observation; C1 recurrent successes; C2
discriminative support against failures; C3 controlled replay; C4 safe ablation
supports step necessity/minimality; C5 invariance across materially distinct
compatible states/parameters. This axis is independent from E0-E3 effect evidence.

**Safety finding:** Experience -> persistent Capability is a trust boundary.
Repeated external/page text must not become trusted precondition/effect/authority.
TransitionSamples and candidates need origin, authority origin, trust class and
taint. Destructive production ablation is prohibited.

**Promotion finding:** capture broadly; promote narrowly. Learned mutation
promotion must not be granted by success count alone. A separate Experience
Compiler promotion admission must consider semantic closure, E0-E3, C0-C5,
provenance/taint, effect/risk, cross-run diversity, drift and expected reuse
utility.

**Required implementation sequence:** EC0 transition identity; EC1 semantic
state/provenance; EC2 corpus/segmentation/alignment; EC3 anti-unification/action
model; EC4 dependency/causal support; EC5 safe replay/ablation/counterexamples;
EC6 promotion/library snapshot; EC7 integration/economics; EC8 cross-backend proof.

**Do not repeat these rejected shortcuts:**
- LLM summary of a trace as the learning mechanism;
- successful trace == procedure;
- frequency == causal proof;
- validation count == promotion authority;
- fuzzy retrieval == mutation authority;
- destructive production experimentation;
- second Memory/Task/Evidence/Browser state owner.


## H-067 — Capability abstraction / Progressive Operational Compilation (2026-09-18)

**Classification:** IMPLEMENTED & VERIFIED across Python and Electron layers (Target architectural finding resolved).

**Evidence base:** current `main` plus AEPC-E002 and the 2026-09-18 abstraction
review. Canonical target:
[../PROGRESSIVE_OPERATIONAL_COMPILATION.md](../PROGRESSIVE_OPERATIONAL_COMPILATION.md).

**Finding:** AEPC-E002 correctly identifies the immediate false-positive class,
but fixing semantic homogeneity alone would leave the optimization boundary at
the wrong reusable unit. The current system still tends to treat compilation as
“convert repeated calls/work into `work_execute`”. The desired behavior is
“learn a deterministic operational capability once, validate it, then resolve
and reuse it automatically”.

**Observed foundations already present:**
- `ProceduralMemory`, `WebProcedure`, `ProcedureStep`;
- semantic fallback anchors and `resolve_anchor()`;
- `RecipeStore` exact compatibility lookup;
- `TaskCompiler`, DurableBatchRunner and WorkPlan/WorkItem checkpoints;
- `RoutinePromotionService` and `DeterministicRoutineRunner`;
- compact `NEEDS_REASONING` drift handoff;
- ExecutionJournal/ArtifactStore experience/evidence plane.

**Additional code-level discovery:** current `workstation/capabilities.py`
already defines `RuntimeCapabilityRegistry` for environment dependencies
(Python modules/system tools). It is not the new operational capability layer and
must not be repurposed accidentally. Current `tools/workstation_work.py`
registers `work_execute` explicitly as “decided repetitive work” with
graph/Recipe/Routine-oriented inputs; that schema is the concrete compatibility
surface to extend. Current `procedure_trace.py` writes
`operation_fingerprint = structural_signature(...)`, confirming that semantic
fingerprinting must be introduced below/alongside trace learning rather than only
inside the top-level guard.

**Decision implemented:** introduced a versioned Capability contract,
Capability Resolver and trusted Operational Kernel while extending existing stores.
Atomic capabilities are reusable by multiple composites. Capability replay
does not call the LLM on the success path.

**Required proof status:**
1. heterogeneous shape-identical browser actions remain adaptive; (PROVEN in `test_execution_policy.py`)
2. true homogeneous fan-out remains compiler/canary gated; (PROVEN in `test_execution_policy.py`)
3. exact promoted atomic Capability replay uses zero new LLM planning calls; (PROVEN in `test_operational_capabilities.py`)
4. two distinct composites reuse the same atomic Capability; (PROVEN in `test_operational_capabilities.py`)
5. drift escalates only the unresolved segment and does not replay confirmed mutable effects; (PROVEN in `test_operational_capabilities.py`)
6. filesystem/process capabilities use the same lifecycle and resolver; (PROVEN in `test_operational_capabilities.py`)
7. no second canonical state owner is introduced. (PROVEN)

**Rejected shortcuts strictly avoided:** threshold inflation, blanket browser exemption, counter
reset around snapshots, transient ref persistence, arbitrary generated-code
bypass, second memory/task/browser database, hidden LLM invocation from a
“deterministic” capability.

**Verified Test Evidence:**
- `workstation/tests/test_execution_policy.py`: 11 passed (including 4 AEPC-E002 regression tests).
- `workstation/tests/test_operational_capabilities.py`: 12 passed.
- `apps/desktop/electron/workstation-browser-runtime-task.test.ts`: 26 passed.

## AEPC-E002 — Structural similarity is not semantic homogeneity (2026-09-18)

**Classification:** RESOLVED & VERIFIED via H-067 (closed by semantic fingerprinting, refused call immunity, and verified success requirement).

**Audit head:** `main@c4234200145162eefb60f6070c9f170b4bf79321`.

**Published lineage:**
- baseline before correction: `c04906aacee568bb6480287717c76afd230cf4a7`;
- implementation on remote: `9e7292ab7825e5ce1ea294490eec57ba1f286069`;
- documentation/evidence on remote: `5e1b22527fd40d732ee4fa7a1035e6366953f6b7`;
- `365794e29d66cd63a6134c5c67ecc1ef603d70a6` was the local pre-publish
  implementation SHA and must not be cited as a remote GitHub commit.

**What the audit reconfirmed as correct:**
- `_work_batch_candidate` no longer controls dispatcher admission;
- `CompilationDecision` is operation-scoped;
- tools.effects is the effective taxonomy and browser_console remains MUTATION;
- mutable uncertainty is persisted before I/O and survives restart;
- middleware-final arguments are re-admitted before mutable dispatch;
- TaskRun/browser lease fencing, E1 snapshot semantics, compact NEEDS_REASONING,
  exact recipe/routine reuse and no blind retry remain intact;
- Workstation CI and Docker Build/Test/Publish passed on the audited lineage;
  packaged/authenticated Electron smoke remains a separate open product gate.

**Residual finding:** `workstation/batch_detection.py::structural_signature()`
abstracts scalar argument values. This is useful for discovering repeated shapes,
but the built-in `browser_type`, `browser_click` and `browser_press`
registrations do not currently provide concrete `mutation_target`,
`target_family_fields` or an equivalent owner contract. Consequently:

~~~text
browser_type(ref=@e1,  text="Continue")
browser_type(ref=@e37, text="next prompt")
browser_type(ref=@e92, text="third unrelated field")
~~~

can collapse to one structural family even though each action belongs to a
different evolving UI state/semantic target. The third distinct call can then
reach `REQUIRE_COMPILE`. The existing authenticated-controller regression only
contains one type and one press, so it proves removal of the immediate global
latch but does not prove a long stateful loop.

**Required architectural correction:**
1. distinguish structural similarity from semantic homogeneity;
2. make `REQUIRE_COMPILE` depend on positive semantic family evidence:
   canonical operation + canonical route/provider + owner-declared or safely
   derived target-family/contract identity;
3. if semantic family cannot be proven, shape repetition may produce
   `SUGGEST_COMPILE`/learning but must not independently block bounded adaptive
   execution;
4. retain threshold-three compiler/canary behavior for true same-family fan-out;
5. do not create a browser-wide exemption or reset counters around observations;
6. correct `CompilationCandidate.successful_occurrences`: an
   `executed_unverified` mutation is not verified success.

**Paired regression required:**

~~~text
A. long stateful Browser flow
navigate -> snapshot
type target A -> snapshot
click target B -> snapshot
type target C -> snapshot
click target D -> snapshot
type target E
=> no durable_compile_required from shape repetition alone

B. true homogeneous fan-out
same operation/provider/route/family target 1
same operation/provider/route/family target 2
same operation/provider/route/family target 3
=> third distinct mutation REQUIRE_COMPILE
~~~

The adaptive regression must not pass because of threshold inflation, counter
reset, browser-name exemption, disabled canary or weakened uncertainty/approval/
TaskRun/lease/evidence contracts.

**Closure:** focused AEPC suites + all Workstation tests + adjacent executor/
guardrail seams + Work100 + Desktop owner contracts must remain green. If product
browser code/runtime changes, run the packaged/native authenticated gate instead
of claiming it from mocks or loopback-only tests.

## H-066 — Upstream reliability hardening P0 implementation and contract validation (2026-09-18)

**Classification:** IMPLEMENTED & CONTRACT VERIFIED (P0.0, P0.1A, P0.1B, P0.2, P0.3A, P0.3B, P0.3C, P0.4).

**Delivery branch:** `fix/workstation-upstream-reliability-p0`.
**Audit base:** `main@03e06cfd8c94e5a7627c288c8eddfd5d4c5c8033` (after PR #24/#25 baseline `1ebb976ca56216c6cada8830799a2a1c9adbc6ef`).

**Objective:** implement and harden all confirmed P0 upstream reliability gaps without refactoring existing Workstation product owners or introducing parallel state engines.

**Implementation and Commit Ledger:**

1. **P0.0 — Native Browser Task Smoke Probe & Real Discriminators (#114964-derived):**
   - Commit: `2e3f5a058d` (`test(workstation): harden native browser task smoke probe with real discriminators`).
   - File: `workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs`.
   - Hardened the probe with real deterministic discriminators: live `webContents` id preservation, continuous JS timer counter advance, typed `<input>` value retention, scroll position retention across `hide -> show` and `park -> show`, loopback authenticated controller action execution (`browser_snapshot`, runtime `'electron-chromium'`), and explicit failure if any external browser fallback occurs.

2. **P0.1A — In-Flight Journal Recovery Tail & Interim Deduplication (#115068):**
   - Commit: `fd2651d7bd` (`fix(desktop): restore live projection tail and prevent interim row duplication in in-flight journal`).
   - Files: `apps/desktop/src/lib/inflight-turn-journal.ts`, `apps/desktop/src/lib/inflight-turn-journal.test.ts`.
   - Fixed `mergeInFlightMessages` to select the last live projection row using `findLastIndex` rather than `findIndex` (which erroneously selected sealed interim stream rows).
   - Wrapped interim row insertions with `withoutBaseIds(..., baseMessages)` to prevent re-inserting already-projected sealed rows.
   - Vitest: 39 tests passed in `inflight-turn-journal.test.ts`.

3. **P0.1B — Optimistic Pending User Message Retention on Resync (#115085):**
   - Commit: `ca90122d89` (`fix(desktop): preserve optimistic pending turn messages during background transcript resync`).
   - Files: `apps/desktop/src/app/contrib/hooks/use-background-sync.ts`, `apps/desktop/src/app/contrib/hooks/use-background-sync.test.ts`, `apps/desktop/src/app/contrib/wiring.tsx`.
   - Composed `preserveLocalPendingTurnMessages` into `reconcileActiveTranscript` and `reconcileTileTranscript` to retain unacknowledged optimistic user messages during background gateway polls.
   - Confirmed convergence without duplicate user rows upon authoritative gateway ACK.
   - Vitest: 17 tests passed in `use-background-sync.test.ts`.

4. **P0.2 — One Canonical Writer Per Session & Read-Only Resume (#111493):**
   - Commit: `511117ec19` (`fix(active_sessions): enforce one canonical writer per session and read-only observer resume`).
   - Files: `hermes_cli/active_sessions.py`, `cli.py`, `tests/hermes_cli/test_cli_resume_read_only_owner.py`.
   - Implemented strict one-writer exclusivity per `session_id` in `active_sessions.py` while permitting multiple observers (`mode="observer"`).
   - Added `_foreign_holder` and `live_session_owner` lookups.
   - Added transfer fencing to prevent stealing sessions owned by foreign live writers.
   - Implemented `RegistryUnreadableError` causing fail-closed rejection on registry corruption.
   - Updated `cli.py` to fall back to read-only observer resume mode when the requested session is owned by another live writer.
   - Tests: 7 unit + CLI tests passed in `test_cli_resume_read_only_owner.py`.

5. **P0.3A — Kanban Session Provenance Validation (#114785):**
   - Commit: `fd38773cd3` (`fix(kanban): validate session provenance, harden worker heartbeat, and record durable exit evidence`).
   - Files: `tools/kanban_tools.py`, `tests/hermes_cli/test_kanban_provenance_and_exit_evidence.py`.
   - Added `_persisted_session_id` read-only validation against SessionDB (`state.db`).
   - Preferred request-scoped `HERMES_SESSION_ID` ContextVar over ambient `os.environ`.
   - Rejected dangling or unpersisted session IDs from being stored as valid task provenance.

6. **P0.3B — Worker Heartbeat Durability & Child Delegation Fence (#114793):**
   - Commit: `fd38773cd3` (same).
   - File: `tools/kanban_tools.py`.
   - Hardened `heartbeat_current_worker_from_env`: returns `True` only when BOTH claim lease extension and worker heartbeat record write succeed.
   - Enforced child delegation fence: delegated child tasks (`HERMES_KANBAN_PARENT_TASK_ID`) cannot heartbeat or refresh the parent worker.

7. **P0.3C — Durable Worker Exit Evidence (#114904):**
   - Commit: `fd38773cd3` (same).
   - Files: `hermes_cli/kanban_db.py`, `cli.py`, `tests/hermes_cli/test_kanban_provenance_and_exit_evidence.py`.
   - Added `format_worker_exit_trailer`, `extract_worker_exit_trailer`, and `strip_worker_exit_trailer` (`HERMES_WORKER_EXIT_TRAILER_V1`).
   - Updated `_classify_worker_exit` to accept `task_id` and fall back to durable log trailer when in-memory PID is absent.
   - Updated `cli.py` single query runner to write machine-readable exit trailers.
   - Updated `read_worker_log` to strip exit trailers from human-visible logs.
   - Preserved downstream rate-limit neutrality, protocol-violation streak, and crash breaker policies.
   - Tests: 7 tests passed in `test_kanban_provenance_and_exit_evidence.py`.

8. **P0.4 — Bounded CDP Supervisor Reconnect Budget (#114897):**
   - Commit: `285675418b` (`fix(browser): cap post-attach CDP supervisor reconnect attempts and evict on terminal failure`).
   - Files: `tools/browser_supervisor.py`, `tests/tools/test_browser_supervisor_reconnect_cap.py`.
   - Added `MAX_POST_ATTACH_RECONNECT_FAILURES = 5`.
   - Tracked consecutive failures after initial attach (`_attached_once`); logged terminal warning with credential redaction (`_redact_cdp_error_text`).
   - Evicted supervisor from `SUPERVISOR_REGISTRY.remove(task_id, supervisor=self)` on terminal failure so subsequent requests can re-instantiate cleanly.
   - Reset failure budget on successful reconnection.
   - Tests: 3 tests passed in `test_browser_supervisor_reconnect_cap.py`.

**Verification and Evidence Gate:**
- Workstation Python tests: `python -m pytest -q -o pythonpath=. workstation/tests` -> 492 passed, 2 skipped (315s).
- Work100 reliability suite: `python workstation/work100.py --run` -> 30 PASS, 0 FAIL, 0 gaps.
- P0 Python regression suites: 17 passed in 4.03s.
- Delegation & cron isolation suites: 24 passed in 6.86s.
- Desktop UI suite: `npm run test:ui` -> 593 test files passed, 5676 tests passed.
- Desktop Platform suite: `npm run test:desktop:platforms` -> 126 test files passed, 1783 tests passed.
- Release qualification: isolated per-file runner on workstation/tests (-j 4, zero retries) verified with 474 passed, 2 expected skips.

## H-065 — Upstream reliability hardening code-to-PR gap audit (2026-09-18)

**Classification:** VALIDATED for the code-level gap map; P0.0 Browser keepalive
hypothesis REFORMULATED from “missing native E2E” to “reuse/extend existing native
evidence”.

**Audit base:** `main@03e06cfd8c94e5a7627c288c8eddfd5d4c5c8033` after the
documentation-only PR #24 intake. No product code was changed during this
investigation.

**Question:** which high-value upstream reliability PRs correspond to real missing
behavior in current Hermes Work, which are already covered by stronger downstream
owners, and which should become regression evidence instead of cherry-picks?

**Confirmed current-main evidence:**

1. **#114964 browser keepalive — invariant already exists; diagnostic extension only.**
   `workstation-browser-task.test.ts` already proves hide/show and park/show
   preserve one page in the lifecycle abstraction. More importantly,
   `engineering-journal/probes/h004-native-browser-task-smoke.mjs` historically
   used real Electron `BrowserWindow` + `WebContentsView` and proved the same
   task/tab/WebContents identity plus renderer sentinel across hide/show and
   park/show. H013 (`apps/desktop/e2e/workstation-headless-load.spec.ts`) already
   exercises the integrated Desktop/Browser/controller path and cleanup.
   **Implication:** do not invent a new browser state plane or a parallel harness.
   Rework/reuse H004 against current main and add only the missing discriminators:
   timer/input/scroll survival, a real controller action after hide/park, and an
   explicit no-external-fallback assertion. If that passes, BrowserTask is not the
   blocker and investigation moves to Adaptive Execution/TaskCompiler admission.

2. **#114897 bounded CDP reconnect — CONFIRMED OPEN.**
   `tools/browser_supervisor.py::CDPSupervisor._run` still reconnects forever
   after the first successful attach. It increments/logs attempts but has no
   terminal consecutive-failure budget or registry eviction.
   **Required fix:** bounded post-attach failures, reset on successful attach,
   terminal warning + registry removal, later `get_or_start` may create fresh
   supervisor. Applies to legacy/fallback supervisor; do not graft this WebSocket
   mechanism onto the Electron-native controller.

3. **#111493 one writer / read-only resume — CONFIRMED OPEN.**
   `hermes_cli/active_sessions.py` enforces a global active-session count but
   does not prevent two live writer leases from owning the same `session_id`.
   `transfer_active_session` can also retarget onto a foreign-owned live session.
   **Required fix:** one canonical writer, N observers; strict live-owner lookup;
   transfer fencing; read-only/observer resume when foreign-owned; unreadable
   ownership registry fails closed.

4. **#115068 in-flight journal recovery — CONFIRMED OPEN.**
   Current `mergeInFlightMessages` still chooses the first live-looking assistant
   projection with `findIndex`; a sealed interim row may retain an
   `assistant-stream-*` id and be selected before the truly live tail.
   **Required fix:** last live projection row + sealed-row id dedupe, preserving
   structured reasoning/tool parts and existing journal ownership.

5. **#115085 optimistic message survives resync — CONFIRMED OPEN.**
   `use-background-sync.ts` grafts authoritative refreshed messages and preserves
   assistant errors but does not compose `preserveLocalPendingTurnMessages`.
   **Required fix:** preserve unacknowledged local user intent during both active
   and tile transcript reconciliation, then converge without duplication after ACK.

6. **#114785 Kanban session provenance — CONFIRMED OPEN.**
   Current task creation can still derive session provenance from ambient/process
   state without first proving the id exists in the active profile's `state.db`.
   **Required fix:** read-only SessionDB validation; request-scoped ContextVar/
   gateway session context outranks process-global env; dangling ids are never
   persisted as valid provenance; canonical parent Task/TaskRun lineage remains
   authoritative when inherited.

7. **#114793 heartbeat truth/fence — CONFIRMED OPEN.**
   `heartbeat_current_worker_from_env` currently reports attempted activity
   rather than requiring both claim-extension and worker-heartbeat persistence to
   succeed, and it lacks the delegated-child fence from upstream.
   Existing cron/delegation isolation tests are present and should be extended.
   **Required fix:** boolean means durable success; delegated child cannot keep the
   parent worker alive; preserve `expected_run_id` fencing and warn once on
   inherited worker-scope rejection.

8. **#114904 dead-worker classification — PARTIAL / REAL MISSING SEAM.**
   Downstream already has stronger policy than the upstream patch in several
   respects: `expected_run_id`, protocol-violation streak, neutral rate-limit
   sentinel, crash grace and failure breaker. The missing seam is topology
   independence: `_recent_worker_exits` is process-local, so another dispatcher
   can see a dead PID without the exit code reaped elsewhere.
   **Required fix:** durable bounded worker-exit evidence/trailer and fallback
   classification from it. The current one-shot exit-code path lives in `cli.py`;
   this fork does **not** have the upstream `hermes_cli/quiet_single_query.py`
   layout. Port the contract, not the file topology.

9. **#114986 phantom Desktop turn lease — NOT APPLICABLE NOW / WATCHLIST.**
   Current downstream `apps/desktop/src/store/gateway.ts` does not have the
   upstream `turnLeases/retainGatewayForSessionTurn` mechanism that the PR fixes.
   No blind port.

10. **#115056 one-call snapshot — BENEFIT ALREADY STRUCTURALLY PRESENT / P1.**
    Native `snapshotForEntry()` already obtains its principal inventory with one
    `webContents.executeJavaScript(inventoryScript(...))` call. Future work should
    benchmark/import hit-test/occlusion, geometry and mutation-freshness ideas,
    not create a second native snapshot authority.

**Anti-repeat conclusion:** do not rerun the old premise “Hermes Work has no real
native hide/park evidence”. H004/H013 already invalidate that premise. Any new
native probe must explicitly state what additional discriminator it adds.

**Next implementation order:**

```text
P0.0 extend/revalidate H004/H013 on current main
  -> if native keepalive/controller fails: repair that exact boundary
  -> if it passes: do not touch BrowserTask; continue Adaptive Execution diagnosis

P0.1 #115068 + #115085 recovery/resync
P0.2 #111493 one-writer ownership
P0.3 #114785 + #114793 + #114904 Kanban truth
P0.4 #114897 bounded fallback supervisor recovery
P1 one Durable Delivery Rail
P1 #115056 snapshot quality benchmark
```

Canonical implementation plan:
`../UPSTREAM_RELIABILITY_HARDENING_2026-09-18.md`.

## AEPC-E001 — Adaptive execution and progressive compilation (2026-09-18)

Baseline audited after fetch: main/origin/main
`c04906aacee568bb6480287717c76afd230cf4a7`; tracked checkout initially clean.
Implementation commit: `365794e29d66cd63a6134c5c67ecc1ef603d70a6`.
The original native reproduction and hypothesis later in this journal are retained.

**Hypothesis confirmed:** repeatability prose was promoted to a turn-wide mutation
latch, although existing structural signatures already identify repeated operations.
Guardrail effect lists disagreed with tools.effects about browser_console, and
native route comparison mixed tool names with route names. Read-only controller
health did not establish that compiler admission was correctly scoped.

**Changes:** replaced admission authority with CompilationDecision and transient
operation-scoped CompilationCandidates; retained the repeatability hint for learning.
Third distinct equivalent writes still require TaskCompiler. The dispatcher rechecks
middleware-final arguments and records mutable uncertainty before I/O in the
existing ordered start section. Restart reads that ArtifactStore record. Canonical
TaskRun checks and BrowserControlLeaseManager remain mutation authorities.
Guardrail classification now consumes tools.effects; unknown effects and console
remain MUTATION. Explicit native tool/runtime mapping normalizes constraints.

Tool-owner registry contracts govern PREPARE/INTERACT/COMMIT/VERIFY, not planner
labels. Semantic snapshot evidence is E1, never persisted readback. External commit
needs persisted proof; the strict legacy graph cannot label native snapshot as E2.
Adaptive traces are bounded/sanitized artifact and journal references captured
during execution. Verified canonical acceptance seeds candidates in existing
ProceduralMemory; validation/promotion remains explicit. Revisions preserve prior
procedure content. RecipeStore automatically captures/locates exact verified
graphs. Promoted compatible native routines with structured semantic conditions
lower into existing WorkItem checkpoints and reacquire live click/type anchors.

NEEDS_REASONING includes compact state_ref, completed_until and safe_to_resume.
Seven confirmed read steps remain committed when step eight drifts; diagnosed
resume executes only eight. Lost mutable ACK leaves safe_to_resume false and
does not dispatch again. Routine resume checks procedure/version/content identity
and requires revalidation after drift. No task, scheduler, memory, evidence,
recipe, browser or approval database was duplicated.

**Changed-file inventory:**

- Agent/tool integration: agent/conversation_loop.py, agent/tool_executor.py,
  agent/tool_guardrails.py, agent/turn_finalizer.py, run_agent.py,
  tools/browser_workstation.py, tools/workstation_work.py.
- Workstation owners/projections: workstation/batch_detection.py,
  workstation/browser_transaction.py, workstation/contracts.py,
  workstation/durable_tasks.py, workstation/evaluation.py,
  workstation/execution_policy.py, workstation/kanban.py, workstation/memory.py,
  workstation/procedure_trace.py, workstation/reasoning_handoff.py,
  workstation/recipes.py, workstation/routines.py, workstation/routing.py,
  workstation/task_compiler.py, workstation/work_contract.py,
  workstation/work_intent.py.
- Tests: workstation/tests/test_execution_policy.py,
  workstation/tests/test_progressive_compilation.py,
  workstation/tests/test_browser_workstation_route.py,
  workstation/tests/test_durable_agent_integration.py,
  workstation/tests/test_durable_hardening.py,
  workstation/tests/test_readonly_preflight.py.
- Reconciled documents: workstation/context/ADAPTIVE_EXECUTION_COMPILATION.md,
  workstation/ROADMAP.md, workstation/context/CURRENT_STATE.md,
  workstation/context/KNOWN_ISSUES.md, workstation/context/TESTING.md,
  workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md and this journal.

**Intermediate evidence and failures (not erased):**

- Initial execution-policy pytest had 5 setup errors with WinError 5 before useful
  execution. Native Python + external basetemp / no cacheprovider resolved this
  environment problem; no product permission workaround was added.
- TDD policy stage: 5 failed in 0.32s (missing policy/route behavior); then
  5 passed in 0.19s. Early reasoning/progressive stage: 2 failed in 1.82s;
  initial compatible implementation/routine check: 4 passed in 0.64s.
- First broad focused gate: 4 failed / 99 passed in 97.64s. Four fixtures still
  treated the obsolete global latch as authority. Replaced their premises with
  concrete two-operation mutation history; independent discovery/delegation
  remains allowed. Did not reintroduce the global gate to satisfy those tests.
- Semantic transaction tests first lacked actual-url preflight, then exposed
  E1 evidence being discarded when merging dispatch/verifier records. Corrected
  the fixture URL and canonical record preference. One browser assertion tried
  to parse the untrusted-result wrapper as JSON; corrected the assertion to inspect
  raw controller output and preserved the security wrapper.
- Learning test initially produced no candidate because its verifier lacked a
  linked evidence_ref. Linked the artifact rather than weakening acceptance;
  7 progressive tests passed in 3.83s afterward.
- Review exposed final-argument admission and native-snapshot proof-strength gaps.
  Added regressions before final qualification, retained threshold three, moved
  pre-dispatch counting inside existing serialization, and recorded E1 honestly.
- Work100 initially reported 28 PASS / 2 FAIL: Vitest failed before tests on an
  incomplete node_modules tree. Missing native binding, then caniuse-lite, were
  restored at exact installed/lockfile versions. No manifest/lockfile changed.
  A first Copy-Item encountered an existing directory; copying package contents
  completed restoration. Canonical Work100 subsequently passed twice.
- Earlier PYTEST_ADDOPTS Windows backslashes were consumed by its argument parser.
  Final command uses forward slashes. Removed only the two generated temporary
  checkout directories after resolved-path containment checks; pre-existing
  inaccessible workstation/.pytest-tmp-consolidation was preserved.

**Executed qualification, exact results:**

Focused gate:

```powershell
.venv\Scripts\python.exe -m pytest -q workstation/tests/test_execution_policy.py workstation/tests/test_progressive_compilation.py workstation/tests/test_task_compiler.py workstation/tests/test_readonly_preflight.py workstation/tests/test_durable_agent_integration.py workstation/tests/test_durable_hardening.py workstation/tests/test_browser_workstation_route.py workstation/tests/test_routines.py -p no:cacheprovider --basetemp C:\Users\KEVYNL~1\AppData\Local\Temp\hermes-aepc-final-focused-18
```

Result: **113 passed in 185.06s**, exit 0. This precedes the additional final
snapshot-strength regression and serialization refinement. Policy/progressive/
compiler after the strength change: **39 passed in 64.41s**, exit 0.
Earlier full Workstation gates: **488 passed / 2 skipped in 458.17s**, then
**490 passed / 2 skipped in 480.32s**. Adjacent core alone: **79 passed in 14.02s**.

Final frozen-code gate, including all those paths:

```powershell
.venv\Scripts\python.exe -m pytest -q workstation/tests tests/agent/test_tool_guardrails.py tests/agent/test_stall_guards.py tests/agent/test_tool_dispatch_helpers.py tests/agent/test_tool_executor_checkpoint_paths.py tests/run_agent/test_tool_executor_contextvar_propagation.py -p no:cacheprovider --basetemp C:/Users/KEVYNL~1/AppData/Local/Temp/hermes-aepc-locked-final-21
```

Result: **570 passed, 2 skipped in 346.25s**, exit 0; all Workstation tests plus
79 adjacent core tests. The two pre-existing Workstation skips remain.

```powershell
$env:PYTEST_ADDOPTS='-p no:cacheprovider --basetemp C:/Users/KEVYNL~1/AppData/Local/Temp/hermes-aepc-locked-work100-22'
.venv\Scripts\python.exe -m workstation.work100 --run
```

Result: **30 PASS / 0 FAIL / 0 COVERAGE_GAP / 0 NOT_RUN_ENVIRONMENT**, exit 0.
Desktop direct gate (cwd apps/desktop):

```powershell
node C:/Github/hermes-agent/node_modules/vitest/vitest.mjs run --project electron electron/workstation-browser-task.test.ts electron/session-windows.test.ts
```

Result: **2 files / 36 tests passed**, exit 0 (401ms reported duration).
git diff --check and git diff --cached --check: exit 0 before implementation commit.
Documentation reconciliation occurred after qualification.

**Final classification:** KI-011 RESOLVED AT CONTRACT LAYER. Provider-free
authenticated HTTP-controller loop retains one BrowserTask/card/run and does not
enter a compiler/preflight refusal loop. New regressions cover the opposite
boundary too: third homogeneous mutation, owner-only transaction contracts,
console mutation, persistent uncertainty, exact scope selection, E1 versus E2,
compact drift and no confirmed-effect replay. Final qualification has no failing
test. Prior environment failures are classified above, not reported as green.

**Metrics / limitations:** simulated first discovery uses 3 provider calls versus
0 during promoted replay. The efficiency fixture independently exercises 8 -> 0,
estimated savings 8 in fixture units, and obstruction rate 0 for one explicitly
safe/authorized eligible task. Unknown denominators/measurements remain null.
No paid-provider token/cost savings were measured. Automatic routine lowering is
restricted to supported semantic native actions and structured condition contracts;
other formats require adaptation. No model similarity match grants execution.
Neither local electron.exe nor apps/desktop/dist-electron/main.js existed.
Native authenticated Chromium/packaged Desktop smoke is NOT RUN / environment
blocked; Vitest Electron mocks and loopback controller tests do not satisfy that
product gate. No real external application was mutated in qualification.
## Read-only durable preflight qualification (2026-09-17)

Current qualification base: main `2df145e80636355e9e590b15cce9b68d41012c56`.
The preflight implementation from PR #22 was merged by concurrent maintainer
activity; this investigation did not perform that merge. The follow-up extends
the current Canonical Work Loop owners rather than restoring an older branch.

Confirmed regression fixture: twelve fake card writes, independent API readback,
interruption and reconstructed SQLite checkpoints, exactly one write per card.
The 22 incident tests passed on native Windows Python 3.13.12. The added ledger
test keeps arbitrary terminal/browser execution scope unknown without owner
metadata; the browser tool name alone does not establish an external target.
No live Trello or historical mutation was touched.
No configuration switch or production mutation threshold changed.

Broad qualification exposed pre-existing fixtures which did not model current
conversation-root, read-connection, Hybrid activity or session toolset contracts.
Baseline comparisons reproduced those failures. Fixtures now exercise the real
contract. The per-file temporary root uses a shorter prefix to fit Unix socket
path limits; Work100 resolves Node through the existing managed-runtime owner.
GNU sort and ripgrep are installed in an isolated Linux test cache to exercise
the actual execution-option security probes, rather than skipping them.

Experiment in progress: full Python suite on Linux and the full native Windows
Workstation suite on this current-main base. Earlier candidate evidence:
472 Workstation tests passed, 1,783 Electron tests passed (5 skipped),
5,674 UI tests passed and Desktop typecheck passed. These earlier results do not
replace current-main qualification. The remote Windows aggregate gate exposed a
900-second smoke timeout and a missing Git merge base; neither gate was disabled.
Current-main Work100: 30 PASS, 0 FAIL, 0 COVERAGE_GAP and 0 NOT_RUN_ENVIRONMENT,
including the real Electron lifecycle contracts through the managed Node resolver.
Current-main POSIX Workstation run: 476 passed, 0 failed; one initial worker-event
fixture flake passed on the runner retry. Trace showed result notification racing
delivery notification because the executor completed immediately. The fixture now
blocks executor completion until delivery is observed, preserving both event types,
task correlation and the original two-second bounds. Five fresh-process runs of
all seven persistent-worker tests passed without retry (35 assertions).
Full current-main core run: 37,977 passed, 337 skipped and one failed in 1,066.4s.
The failure cancelled full dispatch during initialization of the unrelated topic
lookup thread pool, before the lease clock. The lease file passed all 12 tests
in both direct and canonical isolated runs. The fixture now initializes that pool
before timing dispatch, retaining the real path, one-second rejection deadline,
20ms lease budget and all fail-closed/no-goal/no-transcript assertions. A new full
core run is in progress; the earlier aggregate failure is not claimed green.
The first native Workstation run had 472 passed, two skipped and a Windows file
replacement access failure under a checkout-nested temporary directory. The
canonical isolated runner repeats it using independent OS temporary roots.
Desktop reruns exposed host saturation when multiple suites used default worker
counts; qualification now limits Desktop workers without changing test timeouts.

## H-064 — Canonical Work Loop (2026-09-17)

Continuation experiment: subscribe on the owning RuntimeEventBus before compiler
dispatch; filter task/correlation, then verify the real source after notification.
Immediate notifications must survive; unrelated notifications must not wake work;
timeout must retain incomplete state and release the subscription. External
sources retain bounded polling. Focused compiler/runtime gates will verify this.

Base: main/origin/main `edaa8cc8fd1180de05f92450caede853ec862daf`.
Existing `.workstation-audit/` is preserved. Hypothesis: report completion,
untracked critical events and expiry-free evidence bypass safety semantics.
Confirmed in kanban.py/events.py/runtime.py. Extend these owners, never stores.
Experiment: native pytest with isolated homes; 20 existing focused tests PASS.
Sandbox run failed before useful validation with WinError 5; native run required.
P0 expansion: 32 PASS, four failures exposed unsupported block kind `acceptance`;
corrected to canonical `needs_input`. Re-run before extending execution semantics.
Journal experiment: explicit malformed/altered/deleted-line detection; legacy
read without rewriting; hash chain and interprocess append lock. Artifact
experiment: JSON in .data resolves structurally; binary remains metadata;
changed bytes must fail integrity. Full program remains IN PROGRESS.

Observed continued evidence: 452 Workstation PASS / 2 expected skips after the
real two-process Trello import regression was corrected (the original test passed
a string to a Path-only database API); Work100 35 Python + 36 Electron platform
contracts PASS / 0 gaps; focused Electron owner tests 36 PASS; Desktop typecheck
and UI Vitest 29 PASS. Earlier evidence: 422 Workstation PASS / 2 pre-existing skips; upstream
owner gate 124 PASS; subsequent integrated gate 98 PASS; final policy/ledger/
multiwriter/continuity contracts 49 PASS; latest actual artifact read_file and
semantic recipe preflight plus P0 29 PASS. Work100 executes 31 covered tests PASS
but returns exit 1 for required cases 4/5/6/8/9 without coverage. No fabricated
skip/PASS. Native Desktop gates not run. Full scope and file ledger are in
`../CANONICAL_WORK_LOOP.md`. Safety contracts are implemented; full ingress,
publisher, event-wait/browser/handoff/lineage/UI parity remains outstanding.
Intermediate cron NameError corrected; verification fixtures passed when their
temporary projects were moved outside this checkout (project-root resolution).

## H-063 — Close Desktop gates before HW-022 promotion (2026-09-17)

Candidate `089704eb00`, main `a977651539`; no tracked dirty work or merge conflicts.
Windows run 35165832836 failed aggregate gate: runtime error fixture expects old
details, secret-file symlink rejection is bypassed by Windows early return, and
session-state test formatting fails. Experiment: align legacy error fixture with
compatibility metadata, emit typed human-control faults, reject Windows symlinks
without chmod, format the flagged test, then focused/typecheck and real CI.
Acceptance: exact structured recovery codes, symlink target untouched on Windows,
all affected Desktop gates green. Review workflow diff without relaxing guards;
only apply ci-reviewed after its documented checklist is satisfied.

Observed: four affected Electron files passed 89 tests. Strengthened runtime
assertion verifies USER_CONTROL_ACTIVE/WAIT_FOR_RELEASE and absence of compatibility
metadata on typed faults; follow-up two-file run passed 68 tests. Windows symlink
branch is covered both with real filesystem and injected platform, without chmod.
Prettier corrected the flagged session-state test; ESLint added six missing blank
lines in the resilience test. Existing typed error normalizer and BrowserTask lease
ownership remain canonical. Workflow review: HW-022 adds only three path filters
and a controlled replay; no permission widening, guard removal, custom eslint fixer
or composite action changes. Main has no branch protection (API 404); no merge
performed while the Desktop gate is red. Final typecheck and GitHub gates follow.

Windows follow-up 35175089324: corrected static/foundation/native contracts pass;
UI 5673 passed and Electron 1782 passed, 4 skipped. Aggregate remains FAILED:
release smoke runs the entire Python suite but times out at 300s; Dashboard
--skip-build has no prebuilt web_dist in a clean checkout; packaged boot test
matches unrelated shell words; load evidence invokes .venv from apps/desktop.
API step conclusion can be success under continue-on-error despite failed outcome;
only full workflow conclusion and the preserve-gate outcomes prove acceptance.

Next experiment: bounded Windows qualification timeout 900s (local full suite
already measured 448s), explicit canonical web workspace build, boot IPC terminal
state plus actual overlay visibility, and evidence validation from repository root.
No guards or test cases removed. Local cross-engine Dashboard: 3 passed; overlay
contracts: 8 passed. Reproducing the validator from apps/desktop also confirms a
module import failure; repository-root invocation succeeds, so changing only the
Python relative path is insufficient. The workflow restores cwd in finally.

Local packaged probe: requiring a terminal main boot state still timed out.
Trace proves backend.spawn/progress=84/running=true while provider-free onboarding
is visibly asking for setup; BOOT_FAKE delays progress but does not prevent backend
spawn (the fixture comment was inaccurate). Updated hypothesis: first launch must
reach visible setup, a recoverable failure surface, or completed boot with hidden
connecting overlay. Match those exact UI surfaces, not arbitrary shell words.
The separate sustained load E2E remains the proof of actual backend chat readiness.

Observed final packaged rebuild: 6 E2E passed in 13.9s, including setup/recovery
contract; E2E typecheck passes. Web workspace build produces the required dist;
three cross-engine tests and eight UI overlay contracts pass locally. Second
workflow review preserves all existing qualification/E2E thresholds and fail-closed
aggregation; only timeout, asset preparation and validator cwd are corrected.

## H-062 — Verified recipes, canary admission and durable planner context (2026-09-16)

Starting HEAD `a977651539dd4b793e26f96c6116bce187677cc9`; only existing
`.workstation-audit/` is untracked. No upstream comparison or general re-audit.
Hypothesis: item-one admission plus explicit read-to-mutation verification
prevents multiplying an invalid procedure; artifact-backed recipes and bounded
state projections remove repeated operational learning/narrative compaction.
Experiment: extend the existing compiler/checkpoints/ledger/registry, test A–Y,
then replay invalid/corrected/restarted fake Trello workloads and locked CI.
Acceptance: <=1 exposed item on invalid workflow, no confirmed mutation replay,
no executor LLM calls, deterministic <=4 KB handoffs, secret-free recipes,
provider-only projection and no old compaction replication.

Observed: initial focused contracts 22 passed. Existing acceptance then had
59 passes and 7 failures: mutable fixtures asserted success without an external
read relationship; those fixtures now declare verifies and retain restart/replay
invariants. Expanded focused contracts: 26 passed, including 1000 mutations,
no executor model calls, confirmed-step resume, provider projection and retained
SessionDB history. A later combined registry run exposed module-import cache
dependence in the builtin audit (70 passed, 1 audit failure); a clean subprocess
with isolated HERMES_HOME fixed the audit (1 passed). New scope/stale-resume/
read-progress/uncached-telemetry cases: 4 passed. Core seams: 254 passed,
1 unchanged Windows POSIX-0600 assertion; Linux CI remains authoritative.
An initial combined suite was interrupted after a long silent scale test;
separate suite with faulthandler identifies committed SQLite fsync in the
1000-item test, not a deadlock. No persistence guarantee was weakened.
Lock, license policy, compileall and core anchors pass. Three replay scenarios
passed: invalid workflow exposes 1 mutation, corrected completes 12, restart
recipe hits once; each uses 2 fake-provider calls and 0 executor model calls.
Full local Workstation suite: 387 passed, 2 Windows skips; subsequent focused
contracts and published-schema fake planner passed. Final experiment-identity
correction: 9 passed, 29 deselected; graph tool identity, step multiplicity and
verifier predicate changes now distinguish hypotheses without item-value identity.

Seven controlled replay scenarios passed. Invalid workflow: 1 mutation, zero
completed items and zero failed fan-out items (remaining items stay pending).
Corrected workflow: 12 completed, 53 physical tools, 3 shared setup calls,
2 fake-provider calls, zero executor LLM calls and zero replayed mutations.
Restarted recipe hit: 12 completed, zero new canary attempts, one recipe hit.
Stale preflight: zero mutations, one invalidation. Corrected/new-v2 repeats the
verified path; failed-after-stale still exposes only one item.
Corrected final provider wire: 1711 bytes, handoff 1439 bytes, duplicate compaction
bytes suppressed 2878, artifacts 1289737 bytes. Usage/cost remain unknown/null;
modeled baseline counters are not paid-provider evidence.

GitHub acceptance for implementation `334d5823554954875675e0d835b34d124ddfd9a4`:
[Workstation CI 35161635997](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/35161635997)
is GREEN: 393 Workstation contracts and 255 core seam tests passed on Ubuntu.
Both contracts and core-patch-dry-run passed, including the controlled replay.
The final documentation/experiment-identity follow-up must pass the same gate.
PR #19 remains a draft; no automatic main merge is authorized by this stage.

## H-051 — Final durable execution hardening (2026-09-16)

Audit: HEAD and fetched origin/main `17df394cfe3e913e6fce6f3130e3efc47e4592a2`;
focused upstream guardrail baseline `4716ec0ba4e212105f8f162c226f052b25f8a76b`.
Only the pre-existing `.workstation-audit/` directory is untracked.

Confirmed gaps: Workstation CI installed two individual dependencies;
compiler read policy used three names; shared setup/finalize and turn-provider
constraints were missing. Experiment: extend the registry effect contract,
reuse phase WorkItems/checkpoints in a bounded deterministic DAG, record
pre-compilation mutation refs, and prune provider fallbacks before probes.
Acceptance requires discovery, 100-item setup/restart, uncertain mutation,
finalize barriers, cycles, natural/runtime fan-out, provider rejection and
trusted progress tests; then full Workstation tests and a real GitHub run.
No green GitHub result is claimed before that run finishes.

Observed: initial focused existing contracts 31 passed; new A–M contracts 28
passed; expanded Workstation/core acceptance 377 passed, 2 skipped. Additional
registry/MCP/auxiliary tests initially had 238 passes plus four missing-asyncio
plugin cases and one Windows POSIX-0600 assertion. A separate project venv was
installed with `uv sync --locked --python 3.13 --extra dev` (87 installed
packages); core rerun: 242 passed, one POSIX-mode assertion failed on Windows.
The MCP cache permission implementation was not changed by this patch.

Replay `python -m workstation.benchmarks.trello_regression`: 12 completed cards,
2 fake-provider calls, 3 setup calls, 52 physical tools, 15 discovery calls,
12 mutations, 0 replayed mutations, 0 compactions, 21 cache hits; 2,687 inline
bytes, 1,359,646 artifact bytes, 2,556,086 bytes avoided. The modeled baseline
has 14 provider boundaries, 36 repeated setup calls and 2,558,773 raw-inline
bytes. Provider token usage remains unknown/null. CLI first exposed an unclosed
tool-owned DurableTaskStore connection during temporary cleanup; closing it in
the outer tool finally resolved the Windows handle failure, and CLI rerun passed.

Locked-environment acceptance rerun: 377 passed, 2 skipped. Latest focused
compiler/integration/hardening run: 54 passed; after the final dispatch-record
and mixed-discovery refinements, hardening tests alone: 34 passed. Compileall,
diff check, components lock, license policy and core integration anchors passed.
GitHub baseline run `35143874982` at `17df394cfe` confirms collection errors:
missing `requests` and `dotenv`. The new workflow runs the complete locked dev
environment and retains core seam regressions.

GitHub acceptance confirmed: [Workstation CI run 35148055997](https://github.com/kevynlucasprofissional-stack/hermes-agent/actions/runs/35148055997)
completed successfully for `f76368d6ba8566146098305b2b4bebf64581324b`.
On the clean Ubuntu runner, Workstation contracts: **363 passed**; core seam
regressions: **255 passed**. Both `contracts` and `core-patch-dry-run` jobs
succeeded, including locked dependency installation, lock/license validation
and downstream integration anchors. This supersedes the local-only evidence
and confirms that the Windows POSIX-permission case passes on CI.

## H-050 — Durable execution routing / reference boundary (2026-09-16)

Audit base: `3344e67fb67a3f9d2e89fa08707325807449d9b8`, equal to fetched
`origin/main`; restricted upstream comparison: `4e9d3c713a`.
Pre-existing Desktop main/launcher/branding-test edits and `.workstation-audit/`
are excluded from this change.

Hypothesis: existing DurableBatchRunner executes without a model, but has no
scoped agent compilation entry point and retries can reissue captured work.
Confirming contracts: 100 operations through AIAgent's real sequential
executor, one consolidated tool result, no provider calls, restart after 37
completed items, step checkpoint preservation and verifier failure escalation.

Initial focused run: 16 passed. Sandbox execution initially failed in pytest
temporary-directory setup with WinError 5; native access plus an isolated
HERMES_HOME resolved that environment boundary. Expanded run: 31 passed,
two failures: new telemetry test had not attached SessionDB (fixture corrected);
existing relay/checkpoint test expects POSIX `/approved/path` on Windows, while
the unchanged checkpoint resolver returns `C:\\approved\\path`.

Final acceptance: 344 passed, 2 skipped across Workstation, guardrails,
operational-reference compaction and browser schema capability tests. The full
conversation fake provider made two API calls for 100 underlying operations.
Read invalidation covers same size/restored mtime; resume by plan_id recovers
the objective and constraints without the transcript. Compileall, diff checks,
core integration anchors, dependency lock and license checks passed.

Synthetic production-compiler benchmark: modeled planner boundaries 100 -> 2;
inline bytes 6,002,400 -> 2,783; 99 completed and one reasoning exception;
201 physical tool calls, 197 cache hits and 74 checkpoint steps skipped.
Restart after 37 completed items replayed zero completed items. The sampled
artifact footprint is 296,290 bytes. These are structural counters, not paid
token savings. A soak run observed 23 journal events against 24 expected; the
final complete rerun passed, and no worker/soak implementation was changed.
No live browser, provider token savings or clean-machine release result is
claimed by these tests. Visual digests can be referenced when supplied;
automatic pixel reinjection remains outside this implementation.

Additional legacy check: 113 passed, 5 skipped, 12 failed across file tools,
read guards, staleness and tool discovery. All 12 failing cases also failed
with the original HEAD file_tools module loaded from a separate audit file;
they concern POSIX path expectations, platform-specific device guards and
legacy error assertions. That isolated baseline loader had three additional
fixture failures, so it is evidence of reproduction, not a clean baseline
suite claim. The legacy tests and platform resolver were left unchanged.
Separate tool-search/context-provider/staleness rerun: 43 passed.

Last updated: 2026-09-15
Active track: Workstation Knowledge Subsystem (Hermes Vault) & V3 Hardening
Repository: `kevynlucasprofissional-stack/hermes-agent`
Active feature branch: `main` plus current Workstation working tree
Journal entries:
- `v1-1-5-integrated-dogfood-mvp.md` (V1 #1.5 MVP verification)
- `v2-roadmap-completion.md` (Full roadmap completion: V1.1 and V2)
- `v3-runtime-hardening-closure.md` (V3.1–V3.4 contract-layer closure)
Status: 247/247 Workstation Pytest passing, Desktop typecheck passing; current-main audit closure appended below.

## H-049 — Workstation Browser Automation Ergonomics: Input Hygiene, Proactive Human Handoff, Canvas Awareness, and Batch Extraction

Status: PLANNED & SPECIFIED — dogfood evidence recorded; roadmap promoted; implementation staged
Origin: workstation browser real-world dogfood session (session `20260914_223624_261d02`)
Date / ref: 2026-09-14 / `feat/workstation-hybrid-kanban`

### Claim and decision

Real-world dogfooding of the Hermes Workstation Browser across 5 diverse web paradigms (Python.org documentation, G1 news portal, Mercado Livre & Amazon e-commerce, GitHub issue tracker, and Google Maps SPA) demonstrated that while the Chromium runtime and agent task decomposition are robust, agentic web automation encounters four specific friction points:

1. **Input Hygiene (`browser_type`)**: Typing into inputs with pre-existing values (e.g. GitHub's issue search prefilled with `is:issue state:open `) resulted in duplicated/malformed queries (`is:issue state:open is:issue state:open label:...`) because CDP key events lacked explicit selection/clearing guarantees across platforms.
2. **Auth & Verification Wall Handoff**: When encountering account verification gates (Mercado Livre `/gz/account-verification`), the agent spent turns trying URL workarounds before abandoning the site. A proactive Human Handoff banner in the UI should invite the user to complete verification in the persistent profile once and yield control back to the agent.
3. **Canvas / WebGL SPA Settlement (Google Maps)**: Canvas-rendered applications yielded an initial accessibility snapshot with `total_text_chars: 1, element_count: 0`. The agent was forced to inject 10+ raw `browser_console` JS scripts to scroll and inspect feed cards. The browser runtime should detect canvas/sparse trees and perform adaptive DOM feed settling before returning snapshots.
4. **Batch Extraction Overhead**: Extracting product grids (Amazon) and opening hours tables (Maps) required 9–15 sequential tool calls and large token context budgets. Introducing a high-level `browser_extract_items` primitive allows one-step extraction of structured cards/tables without custom scripts.

### Observed evidence (Session `20260914_223624_261d02`)

- **Python.org**: Successfully extracted Python 3.14.7 and synthesized changelog in 2 turns.
- **G1 Tecnologia**: Successfully navigated, clicked lead article (`@e5`), and summarized deepfake investigation.
- **Mercado Livre**: Blocked by `/gz/account-verification` (trace ID `cff34157-597e-425d-818c-b3d1c2acfb6a`); agent pivoted to Amazon.
- **Amazon.com.br**: Extracted 47 items via raw console script; required 3 subsequent scans to map ASINs and filter 27" 144Hz monitors, demonstrating the need for structured extraction.
- **GitHub**: Search combobox `@e18` duplicated query strings upon `browser_type`.
- **Google Maps**: Initial snapshot was empty (0 elements); agent successfully used `browser_console` with DOM feed queries and `feed.scrollTop = feed.scrollHeight` to map 21 cafeterias and extract weekly schedules.

### Subsystem roadmap (V3.5)

- **Step 1: Input Clearing in `workstation-browser-runtime.ts`**: Make `typeRef` ensure complete input clearing (`Ctrl/Cmd+A` with explicit `windowsVirtualKeyCode: 65`, `select()`, and DOM value reset) before typing.
- **Step 2: Verification Wall Detection & Takeover Event**: Detect auth/challenge URL patterns and emit human-takeover prompt.
- **Step 3: Adaptive DOM Settlement for SPAs**: Heuristic wait for feed containers (`div[role="feed"]`, `main`, etc.) when canvas is detected and accessibility count is <= 2.
- **Step 4: `browser_extract_items` Tool**: First-class structured card/table extractor returning clean JSON with titles, prices, ratings, and links in one call.

## H-048 — Hybrid Kanban must extend canonical Kanban without inheriting Agentic status semantics

Status: EXPERIMENTAL VERTICAL SLICE IMPLEMENTED
Origin: human + agent shared workspaces
Date / ref: 2026-09-14 / `feat/workstation-hybrid-kanban`

### Claim and decision

The established Agentic Kanban is a dispatcher-owned execution state machine.
The requested Trello-like surface is instead a human/agent organization view.
The accepted seam is therefore additive Hybrid entities in the existing
per-board `hermes_cli.kanban_db` database, with one domain service shared by
the authenticated plugin API and agent tool. Hybrid columns have no mapping to
`tasks.status`, so a Hybrid “Done” move cannot complete an Agentic task.

### Experiment and observed evidence

- Added `hybrid_boards`, `hybrid_columns`, `hybrid_cards` and
  `hybrid_activity` through the normal idempotent Kanban schema initialization;
  no SessionDB, BrowserTask, Journal or Electron-local store was created.
- `hermes_cli.hybrid_kanban` performs all writes in `kanban_db.write_txn`.
  It uses semantic placement (`before_id`/`after_id`), a negative temporary
  rank namespace followed by dense canonical reindexing, and optional entity
  revision checks for stale client commands.
- The Kanban plugin API and `kanban_hybrid` agent tool call that same service.
  Activity records `human` or `agent` actor provenance plus available session
  and source; the Electron view is a cache/projection with post-write
  invalidation and bounded polling.
- `python -m pytest tests/hermes_cli/test_hybrid_kanban.py
  workstation/tests/test_kanban_journal.py -q` passed **9 tests**. It proves
  persistence after reopening SQLite, ordering repair, stale rejection,
  human/agent provenance, agent-tool/domain convergence, and that a Hybrid
  “Done” move leaves an Agentic task outside the terminal state.
- `npm run typecheck` in `apps/desktop` passed after restoring locked workspace
  dependencies.

### Deliberate boundary / next experiment

This is not yet a claim of multi-user realtime or a full Trello clone. The
next hardening slice should add visual activity/card drawer, destructive
archive policy, horizontal column drag, and Hybrid event invalidation through
the existing plugin websocket rather than a new realtime service.

## H-047 — Hermes Vault: Local-First Agentic PKM Subsystem (Obsidian-Compatible Knowledge Core)

Status: PLANNED & DESIGNED — architectural specification recorded; roadmap promoted; execution staged
Origin: workstation knowledge management & human-agent co-authoring
Date / ref: 2026-09-14 / `main`

### Claim

A personal AI agent's effectiveness multiplies when user and agent share a single, local-first, durable knowledge base. By introducing **Hermes Vault**—a native, Obsidian-compatible Personal Knowledge Management (PKM) subsystem inside Hermes Workstation—the user and agent can co-author plain Markdown files with bidirectional wikilinks (`[[Note]]`), backlinks indexing, YAML frontmatter, and interactive graph views directly in Hermes Desktop.

### Observed evidence & technical alignment

- Analysis of native Obsidian installation (`C:\Program Files\Obsidian`) confirms that Obsidian's foundation is Electron + Chromium + local Markdown files + CodeMirror editor + D3 force-directed graph.
- Hermes Desktop (`apps/desktop`) shares the identical Electron Chromium foundation and already includes a sophisticated force-directed simulation engine in `apps/desktop/src/app/starmap` (`d3-force`, canvas rendering, physics, zoom, viewport).
- Hermes Agent already owns rich file inspection, search, and editing capabilities (`read_file`, `write_to_file`, `replace_file_content`, `grep_search`).
- Creating a native `/vault` route and Vault indexer eliminates the boundary between external note-taking tools and the agent's memory/actions, enabling the agent to synthesize web research, log decisions, link concepts, and maintain maps of content (MOCs) locally with zero vendor lock-in.

### Subsystem architecture

1. **Vault Engine & Local Indexer (`workstation/vault.py` + Desktop IPC/service)**:
   - Root directory resolution (default `~/.hermes/vault` or user-configured external directory, e.g. an existing Obsidian vault).
   - Local filesystem watcher for `.md` files.
   - AST / regex parser for `[[wikilinks]]`, `#tags`, headings (`[[Note#Heading]]`), and YAML frontmatter properties.
   - In-memory bidirectional link cache (forward links and backlinks index).
2. **Desktop UI & Editor (`apps/desktop/src/app/vault`)**:
   - Master-detail file tree explorer + tags panel.
   - Markdown editor with live preview, syntax highlighting, and callout rendering.
   - Autocomplete triggers on typing `[[`.
   - Side panel showing incoming backlinks and metadata properties.
3. **Knowledge Graph View**:
   - Visualizing interconnected notes as an interactive graph using the `starmap` force-simulation primitives.
4. **Agent-Vault Bridge Tools**:
   - `vault_search(query)`: FTS5 / BM25 search across vault markdown notes.
   - `vault_read(note)`: Read note content and metadata.
   - `vault_write(note, content)`: Create or update notes with frontmatter.
   - `vault_backlinks(note)`: Query references and connected notes.

## H-054 — Corpus hardening audit: retain only gaps reproducible on current `main`

Status: ACTIVE — evidence and focused reproductions in progress
Origin: real Hermes conversation corpus supplied for the Workstation hardening
audit
Audit base: `main@1ca169ca15626071c21122f3ea6801065de8d407` (2026-09-14)

### Scope and evidence boundary

The supplied corpus describes 50 conversations with repeated tool payloads,
long polling waits, compactions and tool-call limits. It is workload evidence,
not proof that an historical implementation still has the same defect. The
named corpus Markdown/CSV attachments were not present in this checkout during
the initial audit, so their stated aggregate figures are retained as the task
input but no per-conversation causal claim is made without the attachments or a
current reproduction.

### Initial gap matrix on the audit base

| Area | Classification | Current evidence / disposition |
| --- | --- | --- |
| Large tool-result spillover | PARTIAL | `tools.tool_result_storage` persists only oversized results and gives a text/path preview; it has no content-addressed reference, scope-safe stable-result reuse, or `unchanged` contract. `read_file` is deliberately exempted from spillover. |
| Inline budget / large outputs | PARTIAL | Per-result and per-turn character budgets exist, but no normalized `verbosity`/`inline_budget`/artifact contract governs all results. |
| Persistent-worker result durability | CONFIRMED_GAP | `workstation/workers.py` persists worker records and pending messages, while `WorkerResultEnvelope`s live only in `PersistentWorker._results`; reconstructed workers start with an empty result list. |
| WorkItems / exception-driven execution | PARTIAL | Persistent workers, journal and events exist; no durable WorkItem lifecycle or generic validator-to-anomaly escalation was found. |
| Structured operational errors | CONFIRMED_GAP | The Electron controller serializes action exceptions as `{ success: false, error: message }`, rather than a stable remediation contract. |
| BrowserTask lifecycle/restart | ALREADY_SOLVED | BrowserTask/BrowserSessionState single-page and lazy restart contracts are implemented and covered by focused/runtime/native evidence. |
| Controller descriptor reconciliation | PARTIAL | Controller startup writes a descriptor with the Electron PID, but the audited route still needs a current lifecycle/reconciliation proof before any extraction or rewrite is considered. |
| Human takeover | PARTIAL | Browser actions are blocked while `controlOwner === 'human'`; the present owner is runtime-global, so cross-host/task scoping needs focused validation before changing semantics. |
| Process ownership guardrails | ALREADY_SOLVED | `tools.process_registry` only tree-kills tracked spawned PIDs and verifies recorded process start time before signalling; no wildcard Chrome-kill path was found in that owner. |
| Event-driven waits | PARTIAL | `RuntimeEventBus` and worker blocking waits exist, but reusable condition-specific await projections have not yet been established. |
| Context compaction | PARTIAL | Workstation session lifecycle records compaction markers and bounded memory compaction exists, but the core conversation compactor still needs a separate trace before a non-recursive operational-reference change can be justified. |
| Session `null` / KI-007 | NOT_REPRODUCED | KI-007 remains causally unproven; no SessionDB/Gateway change is authorized without the documented reproduction gate. |
| Session forensic manifest | PARTIAL | Session/worker/resource identities are individually projected; no single redacted manifest export was established in this audit. |
| Capability preflight | PARTIAL | Worker/host/toolset capability sources exist, but no single WorkPlan projection has yet been found. |
| Toolset/schema handles | PARTIAL | Tool-definition caching/fingerprinting exists, but repeated discovery results have no consumer-visible delta handle. |
| Skill identity / collisions | ALREADY_SOLVED | Skill hashes and explicit ambiguous-name rejection are present; no silent collision reproduction was found. |
| Skill preflight | PARTIAL | Existing guard and install validation cover substantial input validation; model-visible preflight constraints require a separate skill-manager trace. |
| Effective configuration semantics | NOT_REPRODUCED | The historical unknown-key symptom was not reproduced in the audit window; no config-owner change is justified yet. |
| Typed host/process operations | PARTIAL | The tracked ProcessRegistry and host adapters cover high-value operations; shell-wide command paths still need a focused safety/capability audit before adding API surface. |
| Provenance/validators | PARTIAL | Perception, journal and evidence metadata exist, but no generic WorkItem validator escalation was found. |
| Experience promotion | PARTIAL | Procedure promotion is explicit; the requested skill/guardrail/regression triage needs a separately scoped evidence lifecycle. |
| Observability projection | ALREADY_SOLVED | EvidenceState, RuntimeEventBus, resources and Desktop projections already expose the canonical operational plane. |
| Corpus benchmark | CONFIRMED_GAP | No versioned baseline-vs-hardened benchmark for the supplied workload shape was found. |

### First focused experiments

1. Reconstruct a completed persistent worker and prove whether an unread result
   survives exactly once.
2. Exercise the existing result-persistence boundary twice with stable content,
   then verify whether the second delivery can be represented by a safe handle
   instead of reinjecting the raw body.
3. Exercise controller error normalization at the authenticated action boundary
   without changing BrowserTask ownership or fallback routing.

No new SessionDB, Kanban, Memory store, BrowserTask store, browser runtime,
agent core, scheduler or event bus is permitted by this investigation.

### Observed result — 2026-09-15

- Confirmed the worker-result gap with the pre-change implementation: a
  reconstructed `PersistentWorker` had an empty `_results` list even when the
  previous executor had completed.
- `WorkerMessage.work_item_id`, a durable result envelope, explicit consumer
  ACK and durable in-flight claim now extend the existing worker record. The
  result is persisted before journal/event publication; persistence failure
  leaves recovery work and never publishes `COMPLETED`.
- Large results already selected for spillover now receive scope-isolated
  content-addressed `result_ref`, `content_hash`, `artifact_ref`, byte count,
  cache status and `inline_truncated` metadata. Repeated content in the same
  task scope reuses the immutable artifact; a distinct scope receives a
  distinct reference. This is a representation cache, not an unsafe
  argument-only execution cache.
- The Electron controller keeps the compatible `error` string and now adds a
  structured recovery contract for stale refs, unbound tabs, human control,
  timeout, invalid arguments and controller loss. BrowserTask ownership and
  fail-closed routing remain unchanged.
- Focused validation: `43 passed` across
  `tests/tools/test_tool_result_storage.py` and
  `workstation/tests/test_persistent_workers.py`; Python compile check passed.
  Electron typecheck/runtime validation remains blocked locally because the
  existing shared `node_modules` cannot materialize its locked dev dependencies
  (`ENOTEMPTY` during npm install). No dependency directory was removed or
  repaired by this investigation.

## H-046 — Chrome Web Store support is not yet an agentic capability boundary

Status: PARTIALLY RESOLVED — governed agentic install slice validated; discovery/catalog and dedicated UI remain open
Origin: agentic extensions / canonical Kanban continuation
Date / ref: 2026-09-14 / `main@9291584e6f`

### Claim

The V2.1 roadmap label "Completed" implies that a Desktop agent can safely
request, approve, install, load, verify and use a Chrome Web Store extension.

### Observed evidence

- `workstation/extensions.py` can download, unpack and register a CRX, but is
  not registered as an agent tool and records no policy or journal events;
- `WorkstationBrowserRuntime.loadInstalledExtensions()` scans directories and
  calls `session.loadExtension()` best-effort during startup, discarding both
  success and failure identity; it exposes no controller/IPC operation for
  immediate load, verification, removal or options navigation;
- `ScopedPolicyEngine` has no extension capability/risk rule, and no existing
  call site joins the manager to Hermes' approval gate;
- the canonical `WorkstationKanbanBridge` already creates parent/child cards
  and journals follow-up creation, but its child card body/metadata omit the
  supplied discovery evidence.

### Implemented result and evidence

- Implemented the stated Desktop-session-only slice in
  `tools/workstation_extensions.py`: four explicit tools call the canonical
  manager, policy and approval gate. Non-Desktop sessions do not receive their
  schemas, even if the process was launched by Electron.
- `ChromeExtensionManager` now inspects manifests before persistence, rejects
  unsafe ZIP paths, atomically writes its registry, and classifies permissions.
- The Electron controller now loads, verifies and removes an extension on
  demand, and permits a verified extension's options page only through the
  controlled action. Startup restoration uses the same verifier instead of a
  silent best-effort load.
- `26 passed` across focused Python contracts (extension manager, policy,
  Kanban follow-up dependency and Desktop-session schema surface); Electron
  runtime focused test passed `19/19`; Desktop typecheck passed.

### Remaining boundary

This result proves a supplied Web Store URL/ID through policy, approval,
install, Electron load and verification. It deliberately does not claim that
the agent can search a marketplace or that the Desktop has a human extension
management UI; those require a separately scoped catalog/UI capability.

## H-041 — Current Windows H010 rerun validates BrowserSessionState on the live working tree

Status: VALIDATED — LOCAL NATIVE EVIDENCE; CLEAN-CHECKOUT QUALIFICATION STILL OPEN
Origin: continuation of the V3 roadmap acceptance audit
Date / ref: 2026-09-12 / `main@d77901a6857cf90f9401a90377de3b6ee5254bef`

### Claim

The versioned H010 native probe still validates the BrowserSessionState and
BrowserTask restart boundary on the current Windows/Electron toolchain after
the latest Workstation changes.

### Observed evidence

- `node workstation/context/engineering-journal/probes/h010-native-browser-session-state-smoke.mjs` passed before any visible Desktop window was opened;
- Windows `10.0.26200`, Electron `40.10.2`, outer Node `v26.7.0`;
- clean restart, failed-write convergence, explicit-destroy cleanup and abrupt
  restart all emitted their pass markers;
- phase A and phase B used distinct Electron PIDs, and phase B restored the
  durable logical state before lazily recreating exactly one task page;
- final marker: `H010_CLASSIFICATION=VALIDATED`.

### Boundary

The probe resolved `HEAD` to the SHA above but imported product files from the
current working tree. Because the checkout contains uncommitted Workstation
changes, this is strong local native evidence rather than clean-machine or
clean-checkout release evidence. The Windows workflow's exact-SHA and
clean-install gates remain authoritative for promotion.

## H-042 — Hidden native Browser runtime reconnect soak passes

Status: VALIDATED — NATIVE RUNTIME BOUNDARY; FULL PRODUCTION LOAD STILL OPEN
Origin: continuation of the V3.2/V3.4 soak acceptance audit
Date / ref: 2026-09-12 / `main@d77901a6857cf90f9401a90377de3b6ee5254bef`

### Claim

The Electron Workstation Browser can repeatedly recreate its runtime across
processes while retaining canonical BrowserTask/session/resource identity and
the one-live-page-per-task invariant under navigation and host transitions.

### Observed evidence

- versioned probe: `workstation/context/engineering-journal/probes/h011-native-browser-runtime-soak.mjs`;
- 60-second local run on Windows `10.0.26200`, Electron `40.10.2`, Node
  `v26.7.0`;
- 39 hidden Electron process episodes, 936 task cycles, four task identities,
  repeated local Chromium navigation, `hub`/`chat` host changes, hide/park
  transitions and resource lineage assertions;
- every episode passed, and the final durable `browser-session.json` retained
  exactly four unique BrowserTask records;
- final marker: `H011_NATIVE_BROWSER_RUNTIME_CLASSIFICATION=VALIDATED`.

### Boundary

The probe uses a local deterministic HTTP page and direct runtime APIs, with
all BrowserWindow instances created as `show: false` and all child processes
spawned with `windowsHide: true`. It is stronger than mocked Electron tests,
but it does not prove the full Hermes agent/backend workload, clean-machine
installation, or a long-duration production deployment. The Windows workflow
now runs the same probe for 60 seconds and uploads its JSON/durable projection.

> Journal/probe/documentation commits after `1ac0e0a9...` do not change BrowserTask product behavior unless this file explicitly records a later code-bearing candidate. Always verify live `main` and compare product paths before carrying evidence into a later implementation.

## H-043 — Real headless backend multi-session reconnect soak passes

Status: VALIDATED — BACKEND/AGENT TRANSPORT BOUNDARY; FULL DESKTOP/BROWSER LOAD STILL OPEN
Origin: continuation of the V3.2/V3.4 production-like load evidence audit
Date / ref: 2026-09-12 / `main@d77901a6857cf90f9401a90377de3b6ee5254bef`

### Claim

The shipped headless `hermes serve` backend can sustain concurrent desktop-shaped
WebSocket sessions, streamed agent turns and durable session resumption across
real backend process restarts without relying on Electron or an external model
provider.

### Observed evidence

- versioned probe: `workstation/context/engineering-journal/probes/h012-headless-backend-reconnect-soak.py`;
- local workflow-shaped run used the real `hermes serve` child process, the
  authenticated `/api/ws` gateway and an isolated `HERMES_HOME`;
- 12 cycles, 48 turns, 44 reconnects, 2 backend restarts, 48 heartbeats and
  192 streamed events passed with zero errors and four concurrent turns;
- every session resumed from its persisted stored identity after process restart;
- final marker: `H012_HEADLESS_BACKEND_CLASSIFICATION=VALIDATED`.

### Boundary

The synthetic turn seam is deterministic and token-free, so this evidence is
about real backend process/transport/session behavior rather than provider or
model quality. It does not prove clean-machine installation, native Browser
composition, remote-client parity or a long-duration full Desktop/Browser
deployment. The Windows workflow runs the same probe with a 120-second budget,
requires two restarts and uploads the JSON/durable home evidence.

## H-044 — Integrated Desktop/Browser headless load gate is validated locally

Status: **VALIDATED — LOCAL HIDDEN-WINDOW RUNTIME GREEN**
Origin: continuation of the V3.2/V3.4 Desktop/Browser production-load audit
Date / ref: 2026-09-12 / `main@d77901a6857cf90f9401a90377de3b6ee5254bef`

### Claim

The Windows release workflow now includes a hidden-window integrated Desktop/
Browser E2E. It uses the real dev Electron shell and real `hermes serve`
backend, drives four deterministic local Chromium pages through the authenticated
Workstation controller, compares controller resource/event projections against
Desktop IPC, and exercises BrowserTask hide/park/destroy lifecycle cleanup.

### Evidence boundary

The spec typechecks, the Desktop build succeeds, and the local runtime passed
**2 tests in 36.6s** after the fixture resolved the workspace-local Windows
`electron.exe`. The base run exercised four native tasks, controller/IPC
identity, host-aware viewport geometry/transfer, native maximize/restore
reconciliation, events and hide/park/destroy cleanup. The sustained run added
eight concurrent tasks, three navigation/snapshot rounds and three real chat
turns through the `hermes serve` backend.
The test sets
`HERMES_DESKTOP_E2E_HEADLESS=1` and asserts that every Electron window remains
hidden, so it did not open a user-visible window. The Windows workflow still
executes H013 as the clean release-candidate gate.

## H-045 — Windows worker persistence tolerates transient atomic-replace locks

Status: **VALIDATED — WINDOWS CONTRACT REGRESSION GREEN**
Origin: continuation of the Windows portability gate exposed by the full
Workstation suite
Date / ref: 2026-09-12 / `main@d77901a6857cf90f9401a90377de3b6ee5254bef`

### Claim

`WorkerRegistry` persistence retains its atomic temp-file replacement contract
while tolerating a short Windows sharing lock from security/indexing software.
The bounded retry is only for `PermissionError`; a persistent failure still
raises to the caller.

### Observed evidence

- the previously exposed full-suite `WinError 5` at `Path.replace()` is covered
  by the bounded retry in `workstation/workers.py`;
- focused persistent-worker tests: **4 passed**;
- complete Workstation regression after the change: **158 passed in 12.94s**.

## H-046 — Shared Desktop viewport geometry is host-aware

Status: **VALIDATED — FOCUSED RUNTIME CONTRACT GREEN**
Origin: KI-004 hardening audit after the H013 integrated E2E
Date / ref: 2026-09-12 / current Workstation working tree

### Claim

Chat and Browser Hub share one Electron `BrowserWindow`; therefore the sender
window cannot by itself identify which pane produced a resize update. The
Desktop bridge now carries an optional expected host and the runtime ignores a
host-aware `setBounds` call from a non-owner pane while retaining the existing
backward-compatible unqualified call path.

### Evidence

The focused viewport tests cover stale-host rejection, zoom/clamp/invalid-bound
normalization, native resize reconciliation and rehoming one live
`WebContentsView` between two native window hosts. H013 additionally exercised
the host-aware bridge and native maximize/restore path against the real
Electron/Chromium view while all windows remained hidden. The full Workstation
suite remains green; broader compositor-race, long-duration load and
clean-machine Windows matrices are still explicit evidence gates.

## H-047 — H013 sustained Desktop/Browser load expansion

Status: **VALIDATED — LOCAL HIDDEN-WINDOW LOAD REGRESSION GREEN**
Origin: continuation of the V3.2/V3.4 Desktop/Browser production-load audit
Date / ref: 2026-09-12 / current Workstation working tree

### Claim

The integrated Desktop/Browser gate can sustain multiple concurrent native
BrowserTasks across repeated controller navigation/snapshot rounds while the
same real `hermes serve` backend handles chat turns, without duplicating task
pages or exposing a native window.

### Evidence

The expanded `workstation-headless-load.spec.ts` passed **2 tests in 36.6s**:
the original four-task controller/IPC/geometry scenario and a second scenario
with **8 tasks × 3 rounds**, native task selection across Hub/Chat, **3 real
chat turns**, resource/event parity and explicit hide/park/destroy cleanup. The
run used `HERMES_DESKTOP_E2E_HEADLESS=1`; broader long-duration production load,
clean-machine qualification and compositor-race coverage remain open.

## H-052 — H013 full resource/event projection parity

Status: **VALIDATED — FULL RESOURCE/EVENT PARITY GREEN**
Origin: KI-008 current-client parity evidence boundary
Date / ref: 2026-09-12 / current Workstation working tree

### Claim

The integrated H013 controller/IPC assertions can compare the complete
resource state and event payload—not only resource identity—while ignoring
only call-generated timestamps that are expected to differ between snapshots.

### Confirming evidence expected

- browser task lineage, permissions, lifecycle state and evidence URIs match
  across controller and Desktop IPC;
- bounded event task lineage and event payloads match across both surfaces;
- the four-task and scaled profiles remain hidden and clean after the stronger
  assertions.

### Refuting evidence expected

- controller and IPC disagree on any canonical resource/event field;
- the comparison hides a semantic field rather than only generated timestamps;
- the stronger parity check causes task/page duplication or cleanup failure.

### Result

H013 now compares complete controller/IPC resource projections, including
permissions, state, lineage and evidence URIs, plus the full bounded event
payload. Both the default suite (**2 tests in 35.4s**) and the exact scaled
profile (**2 tests in 3.1 minutes**) passed. The scaled report recorded **16
tasks**, **150 completed rounds**, `observed_duration_ms=120075`, **8 chat
turns** and `accepted=true`; the post-run process check reported `no_electron`.
Only generated snapshot timestamps are excluded from comparison.

## H-053 — Clean-machine install and doctor profile isolation

Status: **VALIDATED — ISOLATED INSTALL/DOCTOR PROFILE GREEN**
Origin: KI-008 clean-machine release evidence audit
Date / ref: 2026-09-12 / current Workstation working tree

### Claim

The Windows release job can prove that installation and doctor validation use
the same fresh Workstation home when the workflow allocates an explicit
`RUNNER_TEMP` directory and both scripts resolve `HERMES_WORKSTATION_HOME`.

### Confirming evidence expected

- install and doctor report the same isolated home and leave the source
  checkout clean;
- the clean-install evidence records the isolated home and candidate revision;
- existing bootstrap/doctor contracts remain green without changing the
  default user-facing `%LOCALAPPDATA%` behavior.

### Refuting evidence expected

- doctor still reports a different profile than install;
- the isolated home is not created or the workflow cannot carry it between
  steps;
- existing local/default path contracts regress.

### Result

Using a fresh `HERMES_WORKSTATION_HOME` under the Windows temp directory,
`workstation\install.cmd -SkipDependencies` and `workstation\doctor.cmd
-Strict` both passed. Install created `Runtime` and `Browser`, doctor reported
the exact same home and `Browser\User Data` path, and the checkout remained
unchanged. The workflow now persists a unique `RUNNER_TEMP` home through
`GITHUB_ENV` and includes it in candidate-matched clean-install evidence.

## H-054 — Clean-install evidence must name the isolated Workstation home

Status: **VALIDATED — SHARED REPORT VALIDATOR GREEN**
Origin: H-053 install/doctor profile isolation audit
Date / ref: 2026-09-12 / current Workstation working tree

### Claim

Requiring a non-empty `workstation_home` field in accepted clean-install
evidence prevents the release qualification runner from accepting a report
whose `accepted` flag and revision match but whose runtime profile is unknown.

### Confirming evidence expected

- the workflow report carries the isolated home and the runner requires it;
- existing accepted/rejected evidence tests remain precise and the workflow
  still passes its source contract;
- local/default behavior remains unchanged when no explicit home is set.

### Refuting evidence expected

- a report without `workstation_home` still passes the clean-install stage;
- the new field requirement rejects a valid report produced by the workflow;
- the runner starts inspecting or mutating the external machine path.

### Result

`ReleaseQualificationRunner._check_clean_install()` now requires a non-empty
`workstation_home`. The Windows workflow records the same fresh
`RUNNER_TEMP` home used by install and doctor. The focused isolation,
bootstrap and documentation suite passed **27 tests**, and the real local
`install.cmd -SkipDependencies` → `doctor.cmd -Strict` run passed with matching
`Runtime`, `Browser` and `Browser\User Data` paths while leaving the checkout
unchanged.

## H-055 — Clean-install home must be absolute and outside the candidate

Status: **VALIDATED — SHARED REPORT VALIDATOR GREEN**
Origin: H-054 clean-install evidence contract hardening
Date / ref: 2026-09-12 / current Workstation working tree

### Claim

Requiring an absolute `workstation_home` outside the candidate checkout makes
the accepted clean-install report prove profile separation rather than merely
recording an arbitrary non-empty string.

### Confirming evidence expected

- relative paths and paths inside the candidate root are rejected;
- the workflow's absolute `RUNNER_TEMP` path and an external absolute path are
  accepted without probing or mutating that path;
- existing release qualification behavior remains fail-closed.

### Refuting evidence expected

- `.` or a candidate subdirectory is accepted as an isolated home;
- valid external Windows/POSIX absolute paths are rejected by platform-neutral
  validation;
- the runner starts treating the evidence path as a writable local resource.

### Result

`workstation.release_qualification` now rejects missing, relative and
candidate-contained `workstation_home` values while accepting an external
absolute path without reading or mutating it. The qualification/bootstrap/
documentation suite passed **30 tests**, including both valid and invalid
evidence cases.

## H-056 — Full Workstation regression after qualification hardening

Status: **VALIDATED — FULL SUITE GREEN**
Origin: regression after H-053 through H-055 release-evidence changes
Date / ref: 2026-09-12 / current Workstation working tree

### Evidence

The complete `workstation/tests` suite passed **163 tests in 16.08s** after
the doctor profile, clean-install report and absolute-home validation changes.
The result includes the new qualification cases and all prior Workstation
contracts; the candidate-release workflow itself remains an external gate.

## H-057 — Shared validation for the H013 release evidence report

Status: **VALIDATED — SHARED REPORT VALIDATOR GREEN**
Origin: H-051/H-050 candidate-load report audit
Date / ref: 2026-09-12 / current Workstation working tree

### Claim

A read-only Python validator shared by the release workflow and contract tests
can enforce the complete H013 profile without relying on duplicated, weaker
PowerShell field checks.

### Confirming evidence expected

- accepted reports must meet minimum tasks, requested rounds, duration and
  chat-turn values and must reach either the round or duration boundary;
- malformed, partial or under-sized reports fail with a useful reason;
- the validator performs no writes and the workflow still uploads the original
  report for review.

### Refuting evidence expected

- a report below the configured profile is accepted;
- valid reports with a larger profile are rejected unnecessarily;
- moving validation to Python changes the hidden-window H013 behavior.

### Result

`workstation.desktop_load_evidence` now enforces minimum tasks, requested
rounds, duration, chat turns and a reached stopping boundary without writing
to the report. Its focused suite plus the qualification/bootstrap/documentation
contracts passed **41 tests**. It also accepted the actual 16-task H013 report
(`150` rounds, `120075` ms, `8` chat turns), and the workflow invokes the same
validator before allowing the H013 gate to succeed.

## H-058 — Full Workstation regression after shared evidence validation

Status: **VALIDATED — FULL SUITE GREEN**
Origin: regression after H-057 shared H013 report validation
Date / ref: 2026-09-12 / current Workstation working tree

### Evidence

The complete `workstation/tests` suite passed **174 tests in 10.02s** after
the shared desktop-load evidence validator and its contract coverage were
added. The candidate-release workflow remains an external clean-machine gate.

## H-059 — H013 validator numeric-boundary regression

Status: **VALIDATED — FULL SUITE GREEN**
Origin: malformed-duration audit of H-057 shared evidence validator
Date / ref: 2026-09-12 / current Workstation working tree

### Evidence

The H013 report validator now rejects non-positive task/round/chat counts and
negative duration values before applying the round-or-duration boundary rule.
The focused validator/bootstrap/isolation contracts passed **38 tests**, and
the complete `workstation/tests` suite passed **175 tests in 9.64s**.

## H-060 — Clean candidate validation dependency boundary

Status: **VALIDATED — LOCAL CLEAN CANDIDATE GREEN / OFFICIAL CI STILL REQUIRED**
Origin: release qualification stopped at `workstation_smoke` because the
runtime-only `.venv` intentionally did not contain `pytest`
Date / ref: 2026-09-12 / current Workstation working tree

### Claim

The Windows release workflow must install its pinned validation dependencies
explicitly before invoking the read-only release qualification runner, while
keeping the normal runtime installation free of test tooling.

### Result

The workflow now installs `.[dev]` into the isolated candidate `.venv` after
the production install/build and before release qualification. A temporary
clean candidate with the current tree passed real install, `npm ci`, Desktop
production build and strict doctor, then passed all **6/6** release
qualification stages. Its hidden H013 profile passed **2/2** in **3.2 minutes**
and the shared validator accepted the report (`16` tasks, `173` rounds,
`120262` ms, `8` chat turns). This validates the local candidate path only;
the official Windows candidate workflow remains the promotion authority.

## H-061 — Production dependency advisory closure

Status: **VALIDATED — LOCKFILE-ONLY SECURITY REFRESH GREEN**
Origin: clean-candidate `npm ci` reported three production advisories
Date / ref: 2026-09-12 / current Workstation working tree

### Claim

The production dependency gate can close the reported transitive advisories
without forced upgrades or package-manifest churn, while preserving a
reproducible Desktop install and build.

### Result

The lockfile now refreshes `colord` 2.9.3→2.10.0, `sanitize-html`
2.17.6→2.17.7 and both vulnerable nested `nanoid` 3.3.17 entries→3.3.19.
`npm ci` completed successfully, `npm audit --omit=dev
--audit-level=moderate` reported **0 vulnerabilities**, and the Desktop
production build passed. The Windows workflow now runs this audit as a
required gate; development-only advisories remain outside the production
gate and are not silently forced to upgrade.

## H-049 — Parametric H013 production-load profile

Status: **VALIDATED — LOCAL SCALED PROFILE GREEN / CI PROFILE CONFIGURED**
Origin: KI-008 full-duration/production-scale Desktop/Browser evidence gate
Date / ref: 2026-09-12 / current Workstation working tree

### Claim

The existing integrated H013 harness can provide a reproducible larger release
profile if task count, sustained rounds and an optional duration budget are
controlled by explicit CI environment inputs, while the local default remains
bounded and fast.

### Confirming evidence expected

- default local behavior remains the validated four-task plus eight-task,
  three-round hidden-window suite;
- the release workflow can select a larger bounded task/round profile without
  changing source or introducing a second browser/runtime owner;
- the scaled profile preserves controller/IPC identity, native geometry,
  backend chat turns and explicit cleanup.

### Refuting evidence expected

- environment parsing permits invalid or unbounded values;
- scaled execution exposes a window, duplicates task pages or leaks tasks after
  cleanup;
- the release workflow cannot distinguish the bounded local profile from the
  stronger candidate-release evidence.

### Result

The H013 harness now validates explicit bounded integer inputs for task count,
round count, duration and chat turns. The default local profile is unchanged.
A local scaled run with **12 tasks**, a **15-second** duration budget and **4
chat turns** passed **2 tests in 55.4s** with hidden Electron cleanup reporting
`no_electron`. The Windows workflow selects **16 tasks**, up to **120 seconds**
and **8 chat turns**; that candidate-release execution remains external
evidence and is not claimed from the local run.

## H-050 — H013 scaled evidence report and release assertion

Status: **VALIDATED — REPORT-BASED LOCAL PROFILE GREEN / CI ASSERTION CONFIGURED**
Origin: H-049 scaled-load gate hardening
Date / ref: 2026-09-12 / current Workstation working tree

### Claim

An explicit H013 JSON report, checked by the Windows workflow, can distinguish
a complete scaled candidate run from a Playwright process that merely exits
successfully after a partial or under-sized load.

### Confirming evidence expected

- the report records requested and completed rounds, task count, duration and
  real chat-turn count;
- the workflow requires the report to be accepted and to satisfy the selected
  16-task/120-second/8-turn profile, while allowing either the requested round
  count or the duration budget to be the stopping boundary;
- report generation happens only after explicit task cleanup succeeds.

### Refuting evidence expected

- a missing or partial report can still pass the release step;
- the report claims completion before hide/park/destroy cleanup;
- local default runs become dependent on a CI-only report path.

### Result

The H013 suite now writes an optional report only after all explicit
hide/park/destroy operations leave zero tasks. A local report-backed run with
**10 tasks**, a **5-second** duration budget and **2 chat turns** passed **2
tests in 39.0s** and produced `accepted=true`, **13 completed rounds**,
`observed_duration_ms=5165` and `no_electron` after cleanup. The Windows step
now rejects a missing/under-sized report and requires the configured 16-task,
120-second, 8-turn profile; the candidate workflow still supplies the required
external release evidence.

## H-051 — Full configured H013 candidate-profile local run

Status: **VALIDATED — FULL CONFIGURED PROFILE GREEN / HIDDEN CLEANUP**
Origin: H-050 report-based scaled-load gate
Date / ref: 2026-09-12 / current Workstation working tree

### Claim

The exact H013 profile selected by the Windows release workflow—16 concurrent
BrowserTasks, a 120-second sustained duration budget and 8 real backend chat
turns—completes with the same identity, geometry and cleanup invariants on the
current Windows toolchain while remaining hidden.

### Confirming evidence expected

- the report is accepted, reaches the configured duration or round boundary,
  and records at least 16 tasks and 8 chat turns;
- all controller/IPC/resource/event and native geometry assertions remain green;
- explicit cleanup leaves no tasks and no Electron process remains afterward.

### Refuting evidence expected

- the full profile times out, loses task identity, leaks a page/task or reveals
  a native window;
- report validation cannot prove the configured load boundary.

### Result

The exact configured profile passed **2 tests in 3.0 minutes**: **16 tasks**,
**170 completed rounds**, `requested_duration_ms=120000`,
`observed_duration_ms=120651`, **8 real backend chat turns** and
`accepted=true`. Controller/IPC/resource/event, native geometry and explicit
cleanup assertions remained green; the post-run process check reported
`no_electron`. This is strong local Windows/toolchain evidence for the scaled
profile, but it does not promote clean-machine or release-candidate evidence.

## H-048 — H013 formatted rerun and final process cleanup

Status: **VALIDATED — REPEAT GREEN / NO ELECTRON LEFT RUNNING**
Origin: final regression after the H013 fixture/test formatting pass
Date / ref: 2026-09-12 / current Workstation working tree

### Evidence

After the mechanical Prettier correction, Desktop typecheck passed with zero
errors and the same hidden-window H013 suite passed **2 tests in 38.8s**. The
rerun covered the four-task controller/IPC scenario plus **8 tasks × 3 rounds**,
three real backend chat turns, native maximize/restore reconciliation and
hide/park/destroy cleanup. The post-test process check reported `no_electron`;
the 36.6s run in H-047 remains valid prior-run evidence, while the duration
variation is expected for this local Windows environment. Clean-machine,
full-duration/production-scale and broader compositor-race evidence remain
open gates.

## WP-02 — Mainline Consolidation Gate

## H-013 — Roadmap V3.1/V3.2 gaps require extensions over existing owners

Status: ACTIVE — REGISTERED BEFORE PRODUCT CHANGE
Origin: User objective / roadmap audit
Date / ref: 2026-09-10 / `main@d77901a685`

### Claim

The remaining V3.1/V3.2 roadmap work can be implemented as a set of typed,
testable extensions over `ExecutionJournal`, `ProceduralMemory` and
`WorkerRegistry`, without introducing a second SessionDB, Kanban, Memory,
BrowserTask page store or agent core.

### Confirming evidence expected

- current code has no EvidenceState, independent supervisor, Recovery Plane,
  promoted routine runner, persistent worker lifecycle or typed resource bus;
- new modules can persist only projections/operational metadata and retain
  existing owners for journal, memory and lineage;
- focused tests can prove stale-state, recovery, drift and worker-control
  invariants without replacing existing integration paths.

### Refuting evidence expected

An existing owner already provides the missing semantics, or the proposed
extension requires duplicating canonical task/session/memory/browser state or
changing the model tool schema during a conversation.

### Current classification

**PARTIALLY VALIDATED — implementation and integration evidence pending.**

### Practical implication

Implement one foundation task at a time. Do not mark V3.1/V3.2 complete until
native, multi-process and soak boundaries named by the roadmap are exercised.

## H-014 — V3 runtime contracts remain compatible with canonical owners

Status: PARTIALLY VALIDATED — REGISTERED BEFORE NATIVE GATES
Origin: V3.1–V3.4 implementation cycle
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

Evidence, event, resource, supervisor, recovery, routine, worker, memory,
session, replay, protocol and evaluation behavior can be added without
replacing Hermes SessionDB/Kanban/Memory/BrowserTask ownership or changing the
model tool schema.

### Observed evidence

- `python -m pytest workstation/tests -q -p no:cacheprovider`: **141 passed**;
- focused tests cover independent child-process restart, multi-process session
  lease rejection, stale evidence reconciliation, bounded event queues,
  durable worker queue/reconstruction, canonical journal delivery, Recovery
  Plane CLI quarantine, memory snapshots, side-effect-free replay and
  model-independent regression budgets;
- `python -m compileall -q workstation`: passed;
- all new durable projections use caller/HERMES_HOME paths and atomic replace;
- no new SessionDB, Kanban database, browser page store, scheduler or core
  model tool was introduced.

### Evidence still required

The Python contracts do not prove clean-machine installation, Electron/Desktop
composition, cross-engine browser behavior, or long-duration multi-process
soak. Those claims remain open until the native gates below complete.

### Practical implication

Treat the V3 modules as implementation-ready contracts, but do not promote the
V3.1–V3.4 roadmap headings to complete solely from unit/contract evidence.

## H-015 — Existing broad Windows Desktop red is outside the V3 Python delta

Status: OBSERVED — NO CAUSAL REGRESSION FOUND
Origin: native validation ladder
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Observed result

- `workstation\doctor.ps1`: passed environment, committed integration, lock and
  license checks;
- `apps\desktop\npm run typecheck`: passed with 0 errors after running with
  approved build-file access;
- `apps\desktop\npm test`: **7,389 passed, 36 failed, 5 skipped** across 717
  files. Failures are existing Windows path/permission/mode/SSH/WSL/locale and
  unrelated UI expectations; no changed V3 Python module is imported by those
  failing Desktop specs;
- versioned H010 native BrowserSessionState probe: **H010_CLASSIFICATION=VALIDATED**
  on Windows 10.0.26200 / Electron 40.10.2, including clean restart, failed
  write convergence, explicit destroy cleanup and abrupt restart.

### Classification

The broad Desktop red remains a pre-existing portability/test debt and is not
converted into a green claim. The native H010 result validates the existing
browser boundary only; it does not claim that Python V3 runtime contracts are
Electron-integrated.

### Practical implication

Keep KI-006 open for a separate baseline-controlled portability fix. V3
roadmap evidence must be reported by contract/native/soak boundary rather than
by the broad Desktop aggregate.

## H-016 — V3 process-boundary contracts pass the Windows smoke

Status: VALIDATED — CONTRACT BOUNDARY
Origin: V3.1/V3.2 acceptance probe
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Observed evidence

The versioned probe
`workstation/context/engineering-journal/probes/v3-runtime-hardening-smoke.py`
emitted:

- `V3_SUPERVISOR_START_PASS`;
- `V3_SUPERVISOR_RECOVERY_PASS` after terminating the child process;
- `V3_SESSION_OWNERSHIP_PASS` from a real second Python process;
- `V3_EVIDENCE_RECONCILIATION_PASS`;
- `V3_RUNTIME_HARDENING_CLASSIFICATION=VALIDATED_CONTRACT_BOUNDARY`.

### Boundary

This validates the independent supervisor, cross-process lease and evidence
state contracts on Windows. It does not substitute for Desktop/client wiring,
clean-machine release qualification, cross-engine browser testing or soak;
those remain explicit roadmap evidence gates.

### Preconditions closed

- PR #11 was accepted at exact head `d5be442...` after H010 emitted
  `H010_CLASSIFICATION=VALIDATED`; it merged as `e0a99ef3...`.
- PR #12 then merged that promoted main without rewriting either history. Its
  reconciled head `39e5178...` passed Workstation CI (26 contracts), exact
  Windows install/checkout-clean/diff/typecheck, 46 focused browser tests and
  the native H010 step; it merged as `4b04f4c...`.
- The broad Windows aggregator still reported the classified KI-006 baseline:
  one missing UI route mock and 31 unrelated POSIX/path/mode/SSH/platform
  failures. No BrowserSessionState/BrowserTask scoped test failed.

### G-001 — repository-wide disposition audit

**Hypothesis:** after #11/#12 promotion, no accepted product delta remains only
on a lateral branch; the remaining divergent refs are temporary diagnostics,
superseded source snapshots or reproducible formatter output.

**Confirming evidence required:** compare every GitHub branch to exact audit-base
main, inspect unique file/commit scope, close all superseded open PRs, and leave
zero material `NEEDS INVESTIGATION`.

**Observed result:**

- all ancestor refs classify `ALREADY ON MAIN`;
- PR #4/#5 diagnostic lines contain historical Windows evidence and obsolete
  snapshots only;
- PR #6 source was finalized/promoted by #7; its unique workflow is temporary;
- PR #8 is workflow-only historical validation;
- `bot/js-autofix` is one broad mechanical formatter commit and is
  `REJECTED/DO NOT PROMOTE` wholesale;
- comments carrying these dispositions were added and PRs #4/#5/#6/#8 were
  closed;
- no source/evidence needed for V1 #1.5 remains branch-only.

**Classification:** `VALIDATED`. The complete branch/PR table and checklist are
canonical in `../MAINLINE_CONSOLIDATION.md`.

### G-002 — canonical-document convergence

**Hypothesis:** promotion is incomplete while canonical documents still say
BrowserSessionState is a candidate or V1 #1 is next.

**Confirming evidence required:** update current state, decisions, constraints,
architecture/delta, roadmap, testing, known issues, patch manifest, README and
journal; protect ordering/disposition with executable contracts.

**Observed candidate result at `872cbc57ce919ca505650da4a7593fc73f4276bb`:**

- integration anchors, component lock and license policy passed;
- 29/29 Workstation contracts passed;
- Windows install/checkout-clean/diff/typecheck passed;
- BrowserSessionState lint/format, 5 files / 46 focused tests and native H010
  passed;
- local diff, integration, Markdown formatting and direct document-contract
  checks passed; the local canonical Python runner correctly refused because
  its `.venv` lacks pytest, so GitHub CI supplies that evidence.

**Classification:** `VALIDATED / READY TO PROMOTE`. V1 #1.5 may branch only
after this gate candidate is merged into `main`.

## H-017 — The committed Workstation installer preserves the working tree

Status: VALIDATED — DEPENDENCY-SKIPPING INSTALLATION GATE
Origin: V3.3 release-qualification boundary
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The dependency-skipping installation path validates committed integration,
component-lock and license gates, checks the Node toolchain, prepares runtime
directories and leaves repository source plus untracked checkout state
unchanged.

### Confirming evidence expected

- `workstation\install.ps1 -SkipDependencies` completes successfully;
- the installer’s source-cleanliness assertion reports no checkout mutation;
- the existing `workstation\doctor.ps1` remains green afterward.

### Refuting evidence expected

The installer mutates source or creates an unignored artifact, or one of the
committed integration/lock/license/toolchain checks fails on this workstation.

### Observed result

`powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File
workstation\install.ps1 -SkipDependencies` completed successfully. Integration,
component-lock, license and Node checks passed; runtime directories were
prepared under `%LOCALAPPDATA%\HermesWorkstation`; the installer reported that
committed source was not modified. Existing tracked edits and the untracked
user icon artifact were preserved.

### Additional full-install evidence

The normal `workstation\install.ps1` path also completed successfully:
editable Python installation, `npm ci` from the committed lockfile,
`hermes_cli` import and final checkout-clean assertion all passed. npm reported
13 dependency audit findings and deprecation warnings; no lockfile or source
change was made because automatic audit remediation would be an unreviewed
dependency change.

### Classification

`VALIDATED` for the local dependency-skipping and full-install paths. A truly
fresh machine/release artifact qualification, including packaging and runtime
launch, remains a separate gate.

## H-018 — The installed Desktop source produces a clean production build

Status: VALIDATED — LOCAL PRODUCTION BUILD GATE
Origin: V3.3 release-qualification boundary
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

With dependencies installed from the committed lockfile, the Desktop package
can execute its production build (renderer, bundled Electron main process and
native dependency staging) without changing tracked source or requiring an
uncommitted fallback.

### Confirming evidence expected

- `npm run build` completes in `apps\desktop`;
- the post-build assertion succeeds;
- tracked source remains unchanged after the build.

### Refuting evidence expected

The build fails, its post-build assertion is bypassed, or it changes tracked
source/assets unexpectedly.

### Observed result

`npm run build` completed successfully after a clean TypeScript build: Vite
transformed 15,142 modules, the Electron main/preload bundles were produced,
native `node-pty`/`get-windows` dependencies were staged, and
`assert-dist-built.mjs` passed. The build emitted the expected dirty-checkout
warning and Vite/deprecation notices, but no tracked source change.

### Classification

`VALIDATED` for the local production build path. Installer freshness, signed
release artifacts and runtime launch on a clean machine remain separate gates.

## H-019 — The packaged Desktop artifact is structurally launchable

Status: VALIDATED — LOCAL UNPACKED PACKAGING GATE
Origin: V3.3 release-qualification boundary
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The Desktop packaging pipeline can assemble an unpacked Windows artifact from
the built source without publishing or signing, and its output contains the
expected executable/runtime payload.

### Confirming evidence expected

- `npm run pack` completes with `--dir --publish never`;
- electron-builder emits an unpacked artifact and required native/runtime files;
- tracked source remains unchanged.

### Refuting evidence expected

Packaging fails, the artifact is incomplete, or packaging mutates tracked
source/assets unexpectedly.

### Observed result

`npm run pack` completed with electron-builder 26.15.3 for Windows x64 and
Electron 40.10.2. The unpacked artifact was assembled at
`apps\desktop\release\win-unpacked`, Electron integrity was updated, the
Hermes executable was stamped with the configured icon/identity, and signing
was explicitly skipped by the requested `--publish never`/directory mode.

### Classification

`VALIDATED` for unsigned local unpacked artifact assembly. Signed publication,
clean-machine installation and actual end-user launch remain separate gates.

## H-020 — The Windows NSIS release target can be assembled locally

Status: VALIDATED — LOCAL NSIS PACKAGING GATE
Origin: V3.3 release-qualification boundary
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The supported Windows NSIS target can be built from the current installed
dependencies without silently using a missing packaged runtime or changing
tracked source.

### Confirming evidence expected

- `npm run dist:win:nsis` completes;
- electron-builder emits a Windows installer artifact;
- the output is structurally consistent with the thin-installer policy and
  tracked source remains unchanged.

### Refuting evidence expected

The NSIS target fails, ships a stale/fat Hermes payload, or mutates tracked
source/assets unexpectedly.

### Observed result

`npm run dist:win:nsis` completed for Windows x64 and Electron 40.10.2,
producing `apps\desktop\release\Hermes-0.17.0-win-x64.exe` plus its blockmap.
The artifact validator then passed without rebuilding: the unpacked app,
thin-installer negative payload assertion, install stamp, renderer payload and
three `node-pty` native binaries were all present. The build used the
repository's explicit unsigned/local packaging mode.

### Classification

`VALIDATED` for local NSIS assembly and structural artifact validation. A
clean-machine install/launch, signed publication and cross-engine/long-soak
acceptance remain separate roadmap gates.

## H-021 — The packaged Desktop client launches and renders in isolation

Status: VALIDATED — PACKAGED GUI E2E GATE
Origin: V3.2 typed-resource/client evidence boundary
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The actual packaged Windows executable opens through the supported Electron
client path in a credential-free sandbox, renders the root UI and survives the
boot/HUD geometry smoke without requiring a provider or mutating user state.

### Confirming evidence expected

- `e2e/launch-packaged-app.spec.ts` passes against `release\win-unpacked\Hermes.exe`;
- the fixture uses isolated `HERMES_HOME`/userData and cleans up after the run;
- tracked source remains unchanged.

### Refuting evidence expected

The packaged client fails to launch/render, leaks into the user's normal state,
or the smoke requires an unavailable provider/credential.

### Observed result

The first failing runs were traced to the Workstation controller eagerly
restoring a detached `WebContentsView` on app startup. Electron exposed that
view as a page target without an owning `BrowserWindow`, so Playwright waited
forever for its frame tree while the real Hermes window was already loaded.
The controller now starts lazily, and the E2E fixture assigns a temporary
`HERMES_WORKSTATION_HOME` so global browser state cannot enter the test. The
packaged fixture also injects Playwright's Electron loader for its custom
executable path.

The final isolated run completed `5 passed (26.4s)`, including the Hermes title,
renderer DOM, HUD containment, boot state and screenshot artifact. The HUD
assertion retains the geometry checks and allows only a 1 px subpixel tolerance
for native Windows scaling.

### Classification

`VALIDATED / PROMOTED` for the packaged GUI E2E gate on this workstation. The
clean-machine release qualification, broader client wiring, cross-engine
coverage and production soak gates remain separate and are not implied by this
single packaged smoke.

## H-022 — BrowserTask resources can be consumed by multiple client surfaces

Status: PARTIALLY VALIDATED — CLIENT CONTRACT WIRED
Origin: V3.2 typed-resource/client evidence boundary
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

Desktop IPC, the Dashboard REST surface and the TUI gateway can consume one
versioned Workstation resource envelope derived from Electron BrowserTask/page
ownership and the canonical Execution Journal, without creating a second task
or journal store.

### Observed result

- Electron exposes `/resources` on the authenticated loopback controller and a
  matching `hermes:workstation-browser:resources` IPC method, plus bounded
  `/events` and `hermes:workstation-browser:events` projections;
- `BrowserView` consumes the IPC projection for its resource count, while the
  Dashboard `/workstation` page polls `/api/workstation/resources`;
- `workstation.resources` is registered as a read-only, pooled TUI JSON-RPC
  adapter over the same Python transport client, with `workstation.events`
  providing the bounded journal event view;
- task resources preserve BrowserTask/session/Kanban/run lineage, advertise
  control only when the controller is ready, and fail closed to `read` when
  evidence is unavailable;
- journal details are bounded to the latest 200 events in the primary resource
  projection; the existing task-journal inspection path remains the deep-log
  surface;
- the resource helper/runtime tests passed, Dashboard typecheck/lint passed,
  Python client tests passed, and the Desktop/Dashboard production builds
  completed;
- the rebuilt packaged Electron E2E completed `6 passed (28.3s)`, including the
  live IPC-versus-loopback resource identity comparison.

### Classification

`VALIDATED` for the implemented client contract and build boundaries. A live
two-surface session proving identical resources against one running task and a
long-duration soak remain open gates; cross-engine browser coverage is recorded
separately below.

## H-023 — Dashboard smoke passes in Chromium and Firefox

Status: VALIDATED — CROSS-ENGINE CLIENT SMOKE
Origin: V3.4 evaluation gate
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The built Dashboard served by the real Python backend can load the Workstation
resource page in both Chromium and Firefox without page-level errors, using an
isolated provider-free Hermes home.

### Observed result

- the first run exposed a missing Playwright Chromium headless-shell and an
  ambiguous shell/page heading selector; both were harness defects and were
  corrected without changing product behavior;
- after installing the matching local Playwright Chromium and Firefox
  runtimes, `npx playwright test -c playwright.dashboard.config.ts` completed
  **2 passed (9.3s)** — one test in each browser project;
- the backend was started with `hermes dashboard --skip-build` against a
  PID-qualified temporary `HERMES_HOME`, and global setup/teardown isolated the
  fixture from user state;
- the smoke covers the `/workstation` route, BrowserTask empty state and the
  absence of browser page exceptions. It does not claim Electron packaged
  behavior or Safari/WebKit support.

### Classification

`VALIDATED` for the initial Chromium/Firefox Dashboard smoke. Additional
supported engines and long-duration production-like soak remain separate gates.

## H-024 — Release evidence and canonical reconnect soak are executable

Status: PARTIALLY VALIDATED — LOCAL EVIDENCE RUNNER
Origin: V3.3/V3.4 release and evaluation gates
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

Release qualification and reconnect soak evidence can be collected through
bounded, read-only runners without treating a local dirty checkout as a clean
release or adding another SessionDB/worker/journal owner.

### Observed result

- `python -m workstation.release_qualification` records ordered stage evidence,
  bounds subprocess output/time and stops at the first missing or failed gate;
- the clean-install stage requires an accepted JSON report carrying the exact
  candidate `HEAD` revision, so the local runner cannot infer clean-machine
  evidence;
- the Windows Workstation workflow now performs a fresh install and Desktop
  production build, verifies the checkout stays clean, emits that evidence and
  feeds it back into the release qualification gate;
- `python -m workstation.soak --duration 10 --iterations 3 --sessions 3`
  completed **3/3 fresh-process iterations, 3 sessions, 0 failures, 36 journal
  events, 9 memory snapshots, 6 worker reconstructions, 6 model changes and 6
  cold reloads**, exercising session lease, model changes, migration, cold-session
  reload, memory snapshot/restore and worker stop/reconstruct lineage;
- `python -m workstation.soak --duration 60 --iterations 1000 --sessions 3`
  completed **77 fresh-process iterations, 0 failures, 1,155 actions, 924
  journal events, 26,796 memory records, 231 snapshots, 228 worker
  reconstructions, 228 model changes and 228 cold reloads**; `timed_out=true`
  records that the requested duration budget was reached, not a failed child;
- the complete Workstation suite after the client-parity addition completed
  **151 passed in 10.37s**.

### Classification

`VALIDATED` for bounded local evidence collection and contract-level
session/worker reconnect behavior. Clean-machine promotion and long-duration
Desktop/Browser production soak remain open acceptance gates.

## H-025 — HW-018 closes the KI-006 Windows portability class

Status: VALIDATED — BROAD WINDOWS SUITES GREEN
Origin: follow-up to H-015 baseline evidence
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Changed boundary

The implementation fixed the actual Desktop-owned portability assumptions
identified by H-015: deterministic UI locale formatting, session-scoped
Preview promotion, injected POSIX/Windows path grammars, platform-correct
permission assertions, native Git physical-path comparison and non-repository
probe behavior, explicit SSH mux/no-mux test contracts, non-blocking WSL UNC
selection and executable-mode staging seams.

### Confirming evidence

- Desktop UI: **591 files / 5,669 tests passed**;
- Desktop platform/Electron: **126 files / 1,760 tests passed, 5 skipped**;
- Desktop TypeScript typecheck: **0 errors**;
- no coverage was deleted or disabled to obtain the result.

### Classification

`KI-006=RESOLVED_ON_CURRENT_WORKING_TREE`. The old H-015 counts and the
Implementation 4 baseline comparison remain historical causality evidence;
the current broad suites no longer reproduce that failure class. V3 clean-
machine, deeper client-parity and long-duration production soak gates remain
independent and open.

## H-026 — Dashboard and TUI adapters share one authenticated resource boundary

Status: VALIDATED — HIGH-LEVEL CLIENT PARITY
Origin: V3.2 typed-resource/client evidence boundary
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The Dashboard REST handler and the TUI JSON-RPC handler can consume the same
versioned resource envelope for one BrowserTask/session/journal projection
through the shared authenticated controller client, without introducing a
client-owned persistence store.

### Observed result

- a real authenticated loopback HTTP controller boundary served one task,
  session and journal resource set;
- the Dashboard route and `workstation.resources` JSON-RPC method each issued
  one controller read and returned the exact same normalized envelope;
- the identity assertion covered the browser resource, task resource and
  execution-journal resource, including task/session lineage;
- `python -m pytest workstation/tests/test_client.py -q -p no:cacheprovider`
  completed **4 passed**, and the complete Workstation suite completed **151
  passed**.

### Classification

`VALIDATED` for the high-level Python client adapters and their live HTTP
transport boundary. Electron packaged two-surface rendering, future remote
clients and production-like soak remain separate gates; this evidence does
not claim those boundaries complete.

## H-027 — Dashboard and TUI adapters share bounded journal events

Status: VALIDATED — EVENT PROJECTION PARITY
Origin: V3.2 event/resource client evidence boundary
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

Dashboard REST, TUI JSON-RPC and Desktop IPC expose bounded operational journal
events from the canonical Electron Workstation runtime without creating a
second event store or leaking an unknown task's journal.

### Observed result

- the Electron runtime provides versioned `/events` responses with a maximum
  of 200 events and task-scoped filtering against known BrowserTasks;
- Desktop preload/IPC, Dashboard `/api/workstation/events` and TUI
  `workstation.events` are wired to that projection;
- the Dashboard renders the bounded recent-event list while the existing task
  journal remains the deep inspection surface;
- the real authenticated loopback adapter test compared both high-level
  surfaces and passed **5/5** client tests; the Electron runtime event test
  passed as part of **11/11** focused runtime/resource tests;
- the complete Workstation suite passed **152/152**, Desktop and web
  typechecks passed, the Dashboard production build passed, and the broad
  Desktop platform suite passed **1,761 tests with 5 skipped**.

### Classification

`VALIDATED` for the current Desktop IPC, Dashboard REST and TUI JSON-RPC event
projection. Remote-client expansion, packaged two-surface rendering and
production-like soak remain separate evidence gates.

## H-028 — Extended multi-session reconnect soak remains failure-free

Status: VALIDATED — EXTENDED LOCAL SOAK
Origin: V3.2/V3.4 session, worker and evaluation evidence gate
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The canonical Workstation reconnect scenario remains stable across a longer
local budget with multiple sessions, process restarts, model changes, cold
reloads, memory snapshots and persistent worker reconstruction.

### Observed result

- `python -m workstation.soak --duration 180 --iterations 3000 --sessions 4`
  completed **221 fresh-process iterations with 0 failures**;
- the run recorded **4,420 actions, 3,536 journal events, 391,170 memory
  records, 884 snapshots and 880 reconstructed workers** across four sessions;
- all four sessions were migrated, with 880 model changes and 880 cold reloads;
- the duration budget ended with the explicit expected marker `timed_out=true`;
- this strengthens local contract evidence but does not claim the separate
  production-like Desktop/Browser soak gate, clean-machine qualification or
  packaged two-surface rendering.

### Classification

`VALIDATED` for the extended local session/memory/worker/reconnect scenario;
external production-like and clean-machine evidence boundaries remain open.

## H-029 — Dashboard smoke passes in Chromium, Firefox and Edge

Status: VALIDATED — THREE-ENGINE DASHBOARD SMOKE
Origin: V3.4 cross-engine WebUI evaluation gate
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The provider-free Dashboard Workstation route renders without page-level errors
across the supported Chromium and Firefox projects and an installed Microsoft
Edge system browser, using one isolated Python backend.

### Observed result

- the Playwright configuration detects a supported Edge executable and adds an
  `msedge` project only when that browser is present;
- `npx playwright test --config=playwright.dashboard.config.ts` completed
  **3/3 tests in 9.2 seconds** across Chromium, Firefox and Edge;
- the smoke verified the Workstation heading, Browser tasks section, Recent
  events section and provider-free empty state, with no `pageerror` events;
- environments without a supported Edge installation continue to run the
  Chromium/Firefox baseline instead of failing due to an unavailable browser.

### Classification

`VALIDATED` for the current three-engine Dashboard smoke on this Windows host;
packaged Electron two-surface rendering and production-like Desktop/Browser
evidence remain separate gates.

## H-030 — Packaged artifact preserves resource and event identity across IPC

Status: VALIDATED — PACKAGED PROJECTION BOUNDARY
Origin: V3.2 typed resources/event client acceptance boundary
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The exact Windows `win-unpacked` Desktop artifact renders its packaged GUI/HUD
surfaces and exposes the same Workstation resource and event projections through
Desktop IPC and its authenticated loopback controller, without requiring a
visible native window.

### Observed result

- the packaged E2E fixture now sets `HERMES_DESKTOP_E2E_HEADLESS=1`; the main
  window remains hidden while its renderer, preload and controller initialize;
- the identity test compared schema/runtime, resource identities and event
  envelopes from IPC and `/resources` + `/events`;
- `npx playwright test e2e/launch-packaged-app.spec.ts --config=playwright.config.ts
  --workers=1` passed **6/6 in 22.5 seconds**, including renderer boot, HUD
  composer containment and screenshot capture;
- the run used the explicit headless E2E flag, so it validates packaged DOM,
  IPC, controller and geometry behavior but does not infer visible-window
  behavior on a user's desktop session.

### Classification

`VALIDATED` for the packaged GUI/HUD and IPC/controller boundary in headless
E2E; visible desktop-session behavior, clean-machine qualification and
production-like soak remain open evidence gates.

## H-031 — Windows gate tracks E2E harness changes

Status: VALIDATED — CI TRIGGER COVERAGE
Origin: V3.3 release qualification and V3.4 cross-engine evidence governance
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

Changes to the Desktop E2E harness and Playwright configurations cannot bypass
the Windows Workstation gate through the workflow path filter.

### Observed result

- `.github/workflows/workstation-browser-windows.yml` now includes
  `apps/desktop/e2e/**` and `apps/desktop/playwright*.config.ts` in its pull
  request paths;
- the canonical source contract test asserts both paths alongside the existing
  clean-install, build, UI and platform gate requirements;
- the bootstrap/context regression run passed **11/11**, and `git diff --check`
  passed.

### Classification

`VALIDATED` for CI trigger coverage of the current Desktop/Workstation E2E
harness; the workflow's external clean-machine execution remains a separate
release evidence gate.

## H-032 — Windows workflow executes browser and packaged evidence gates

Status: VALIDATED — RELEASE WORKFLOW COVERAGE
Origin: V3.3 upstream ownership/release qualification gate
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The Windows Workstation workflow exercises the cross-engine Dashboard smoke and
the packaged Desktop GUI boundary, rather than leaving those checks as local
manual commands.

### Observed result

- after clean-install evidence and the production build, the workflow installs
  the Chromium/Firefox Playwright browsers and runs the provider-free
  cross-engine config (Edge is auto-detected when present);
- it builds the unpacked Desktop artifact, runs `launch-packaged-app.spec.ts`
  with the fixture's headless mode, and uploads both E2E result directories;
- each new step has an explicit outcome ID and the final preservation step
  fails if cross-engine, packaging or packaged GUI E2E is not successful;
- the workflow path filter already includes the E2E/config files, and the
  canonical bootstrap/context regression run passed **11/11** with typecheck
  and `git diff --check` clean.

### Classification

`VALIDATED` for source-level CI coverage of the browser/release evidence gates;
the actual clean-machine workflow result still requires execution by the
external Windows runner on a candidate release.

## H-033 — Windows I/O tests tolerate legitimate Git/PowerShell startup cost

Status: VALIDATED — PLATFORM REGRESSION STABILITY
Origin: HW-018 Windows portability closure
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The broad Desktop platform suite remains green under concurrent Windows load;
tests that create Git clones/worktrees or invoke PowerShell have enough timeout
headroom to measure behavior instead of failing on the Vitest five-second
default.

### Observed result

- isolated reproductions of the two timeout sites passed within the normal
  path, while the broad run exposed their sensitivity under suite load;
- the Git worktree remote-tracking test and Windows hand-off-marker test now
  use explicit 15-second test budgets, preserving their assertions and cleanup;
- the full platform suite then passed **126 files / 1,761 tests**, with 5
  intentional skips; no coverage was deleted or disabled.

### Classification

`VALIDATED` as a Windows test-harness stability fix; the underlying Git,
PowerShell and cleanup behavior remains covered by the same assertions.

## H-034 — Release workflow command parity and full contract rerun

Status: VALIDATED — LOCAL RELEASE-CHECK PARITY
Origin: V3 release-evidence follow-up
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The newly wired Windows release-workflow commands remain executable against the
current checkout, and the complete Workstation contract suite is still green
after the workflow and Windows timeout-hardening changes.

### Observed result

- the exact workflow packaging command
  `npm run builder --workspace apps/desktop -- --dir --publish never` completed
  successfully without launching a visible Electron process;
- the canonical bootstrap/context contracts passed **11/11**;
- the release-qualification/isolation contracts passed **10/10** when run with
  the required native temporary-directory access;
- the complete Workstation suite passed **152/152**;
- `git diff --check --no-ext-diff --unified=0` passed and a final process check
  found no running Electron instance;
- an initial sandboxed isolation run reached 6 passing cases but four
  `tmp_path` fixtures failed before test execution with `WinError 5`; the
  authorized rerun reproduced all ten passes, so this is classified as an
  environment ACL limitation rather than a product or test-contract failure.

### Classification

`VALIDATED` for local command parity and Workstation contract integrity. The
external Windows clean-machine workflow and production-like long-duration soak
remain separate acceptance gates and are not inferred from this run.

## H-035 — Windows workflow retains bounded reconnect-soak evidence

Status: VALIDATED — RELEASE WORKFLOW COVERAGE
Origin: V3.2 long-lived runtime evidence gate
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The Windows release workflow now executes the canonical multi-session,
multi-process reconnect scenario and preserves enough structured output to
audit failures without converting a bounded contract run into a production
soak claim.

### Observed result

- the workflow invokes `workstation.soak` for four sessions with a 180-second
  duration budget and a 3,000-iteration cap;
- it validates zero failures/errors and requires at least one completed fresh
  process iteration before reporting success;
- the JSON report and durable soak root are uploaded as a separate artifact;
- the final outcome-preservation step requires the soak outcome to be
  `success`, alongside the existing UI/platform/browser/package gates;
- the canonical workflow source contract passed after updating its intentional
  aggregator-message expectation.

### Classification

`VALIDATED` for reproducible CI coverage of the bounded Workstation reconnect
contract. Clean-machine promotion, future-client parity and long-duration
production-like Desktop/Browser soak remain explicit external gates.

## H-036 — Release qualification failure no longer hides downstream evidence

Status: VALIDATED — DIAGNOSTIC NON-MASKING
Origin: V3 release-workflow hardening
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The Windows workflow can collect the soak, cross-engine and packaged GUI
results even when release qualification itself fails, while the final job
still fails on the original release outcome.

### Observed result

- the release qualification step now has an explicit `release_qualification`
  outcome and `continue-on-error: true`;
- the final preservation step reads that original outcome and requires
  `success`, so continuation is diagnostic only and cannot turn a red release
  gate green;
- the workflow source contract covers both the release outcome and the
  downstream soak outcome, and the documentation continues to distinguish
  bounded CI evidence from production acceptance.

### Classification

`VALIDATED` as failure-observability hardening. Required gates remain strict;
the change only prevents an early release-gate failure from masking later
evidence.

## H-037 — Operational memory compaction bounds reconnect soak growth

Status: VALIDATED — MEMORY RETENTION CONTRACT
Origin: V3.2/V3.4 long-lived runtime acceptance
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The canonical memory owner can compact operational task-context records by an
explicit workspace/type policy, persist that deletion safely, and expose a
bounded live-memory metric in the reconnect soak without pruning procedures or
unrelated memory kinds.

### Observed result

- `ProceduralMemory.compact_memory()` retains the newest records within an
  explicit scope and carries deletion IDs through merge-on-write so compacted
  records are not resurrected by the persistence merge path;
- focused memory/soak tests passed **6/6**, and the complete Workstation suite
  passed **154/154**;
- the final 180-second, four-session soak completed **128 fresh-process
  iterations with 0 failures and 0 errors**, including 512 snapshots, 508
  worker reconstructions/model changes/cold reloads and 2,048 journal events;
- cumulative memory work produced 15,888 records, while live memory peaked at
  **32 records**, exactly eight per session, proving the operational bound;
- the soak still reports `timed_out=true` at the duration budget and remains
  contract evidence rather than a production-like Desktop/Browser claim.

### Classification

`VALIDATED` for explicit operational-memory retention and bounded reconnect
soak behavior. User-facing procedures/facts remain untouched unless a caller
explicitly selects them for compaction; clean-machine promotion, future-client
parity and production-like Desktop/Browser soak remain external gates.

## H-038 — Windows soak gate enforces the operational memory bound

Status: VALIDATED — RELEASE GATE INVARIANT
Origin: V3.2/V3.4 bounded-memory follow-up
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The Windows release workflow does not merely check that the reconnect soak had
no failures; it also rejects reports that omit or exceed the explicit
eight-record-per-session operational memory bound.

### Observed result

- the soak validation calculates `memoryBound = session_count * 8` from the
  report and requires `max_live_memory_records` to be present and no greater
  than that bound;
- the source contract asserts the report metric and bound check, while the
  final workflow aggregator still requires the soak step's original outcome
  to be `success`;
- the final 180-second soak report contained `max_live_memory_records=32` for
  four sessions, satisfying the same invariant that CI now enforces.

### Classification

`VALIDATED` as a fail-closed release-workflow invariant. The check bounds
operational task context only; it does not imply a production-like
Desktop/Browser soak or alter the separate clean-machine evidence boundary.

## H-039 — Strict doctor closes the bootstrap gate without opening Desktop

Status: VALIDATED — WINDOWS BOOTSTRAP GATE
Origin: V1 #14 clean-install/start acceptance
Date / ref: 2026-09-11 / working tree on `main@d77901a685`

### Claim

The Windows release workflow now exercises a real strict bootstrap diagnostic
after installation, and a failed required dependency/integration check cannot
be reported as accepted clean-install evidence.

### Observed result

- `workstation\\doctor.ps1 -Strict` preserves the default warning-oriented
  diagnostic mode but returns exit code 1 when required Git/Node/npm/Python,
  `.venv`, integration, lock or license checks fail;
- the local strict doctor passed on the current checkout with Python 3.13,
  Node 26, npm, `.venv`, integration anchors, lock and license policy;
- the Windows workflow invokes `workstation\\doctor.cmd -Strict`, carries its
  original outcome into clean-install evidence and requires that outcome in
  the final aggregator;
- the doctor source contract and workflow/documentation contracts pass, and no
  Electron process is launched by this validation.

### Classification

`VALIDATED` for strict bootstrap diagnostics and failure propagation. The
one-click launcher still owns the user-facing install → doctor → start flow;
external clean-machine and visible Desktop-session acceptance remain separate
evidence gates.

## H-040 — Root launcher changes trigger the Windows gate

Status: VALIDATED — CI PATH COVERAGE
Origin: V1 #14 one-click bootstrap hardening
Date / ref: 2026-09-12 / working tree on `main@d77901a685`

### Claim

A change to the repository-root one-click Workstation launcher cannot bypass
the Windows validation workflow merely because the launcher is outside the
`workstation/` directory.

### Observed result

- `.github/workflows/workstation-browser-windows.yml` now includes
  `START-HERMES-WORKSTATION.bat` in its pull-request path filter;
- the canonical source test checks that filter alongside the launcher’s strict
  doctor delegation;
- the launcher remains source-only in this validation, so no visible Electron
  process is started.

### Classification

`VALIDATED` for CI trigger coverage of the one-click bootstrap entrypoint.
Actual clean-machine launcher execution and visible Desktop-session behavior
remain environment-specific acceptance gates.

## Why this journal exists

This file is the Workstation project's durable anti-repeat memory for active engineering. It records not only experiments, but the **mistakes, rejected premises, evidence boundaries, and decision lineage** that a future agent must know before proposing another implementation.

The evidence hierarchy is:

1. current repository code/tests on the exact ref being changed;
2. versioned executable evidence tied to an exact SHA;
3. current GitHub CI/workflow results for that SHA;
4. canonical Workstation documents (`DECISIONS`, `CONSTRAINTS`, `CURRENT_STATE`, `TESTING`, `KNOWN_ISSUES`, `UPSTREAM_DELTA`, etc.);
5. historical session exports, manual observations, screenshots, and attached context;
6. model/agent narrative.

A lower layer may explain or motivate an investigation, but it must not override a higher layer. In particular, **an assistant saying that a tool/runtime was used is not evidence that it was actually used**; inspect the tool call/result, runtime boundary, code path, or executable marker.

Historical chats are useful because they preserve why a decision changed. They are not permission to resurrect an older architecture after a later decision became canonical.

## Durable project lineage — do not reopen settled branches casually

The project did not start with the current architecture. The early question was which external browser stack should be integrated with Hermes. `agent-browser`, Browser Use, BrowserOS, Browser4, VibeSurf, Sabrina, Hermes Browser Extension, Hermes WebUI, and other approaches were investigated at different times.

Several intermediate architectures were reasonable hypotheses at the time:

- `agent-browser` as the primary Hermes browser engine;
- BrowserOS as the dedicated persistent/logged-in browser;
- a separate `hermes-workstation` repository;
- plugin-first Workstation integration;
- Hermes + separate extension + separate WebUI + launcher;
- a Workstation monorepo wrapping an otherwise untouched Hermes.

Those were **decision stages, not current open choices**.

The settled product direction is now:

- this repository is a **thin downstream distribution/fork of Hermes**, with Workstation first-class;
- upstream Hermes remains authoritative for generic Hermes behavior;
- `workstation/` is the main downstream-owned architecture surface;
- core/upstream-owned changes are allowed only when deep integration requires them, and the delta must stay small, explicit, tested, and tracked;
- Hermes Sessions, Gateway, Kanban, Memory, approvals, profiles, tool registry, and routing remain the source of truth instead of being duplicated;
- the primary Workstation Browser is **Electron Chromium inside Hermes Desktop**, rendered with `WebContentsView`, with a dedicated persistent profile/session;
- `BrowserRuntime` remains an abstraction boundary so specialist/external runtimes can exist without redefining BrowserTask semantics;
- `BrowserTask` is the semantic identity/ownership unit for durable browser work, with at most one live task page per task in a process;
- Preview, Chat Browser View, and Browser Hub must ultimately become views/adapters over the same BrowserTask/runtime rather than independently navigated pages;
- external projects are reused selectively as code, protocol, benchmark, fallback, or design reference according to `SOURCE_MATRIX.md`; they are not automatically vendored into the product.

### Decisions that require new material evidence before reopening

| Old debate                             | Current settled direction                                  | What would justify reopening it                                                                                      |
| -------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| plugin/separate repo vs fork           | thin downstream fork; Workstation first-class              | a concrete upstream capability that removes the need for cross-cutting downstream integration, with migration proof  |
| external browser vs internal browser   | internal Electron Chromium is primary                      | measured inability of Electron runtime to satisfy a required invariant that a specialist runtime demonstrably solves |
| BrowserOS vs agent-browser as the core | neither is the primary Workstation runtime                 | changed product requirements or benchmark evidence, not familiarity/preference                                       |
| separate WebUI                         | official Hermes Desktop/Dashboard remain UI/state surfaces | a specific unmet product requirement that cannot be added without duplicating state/control planes                   |
| second Kanban/SessionDB/Memory         | reuse Hermes-owned systems                                 | only an explicit replacement architecture that supersedes the canonical decisions and includes migration/tests       |
| synchronize Preview and Browser by URL | one BrowserTask/live page, views/hosts                     | never as a cosmetic synchronization workaround; only a replacement of the ownership model with stronger proof        |
| browser availability from process env  | session/platform capability                                | only if Hermes changes its gateway/session architecture materially and tests prove the new identity model            |

The rule is not “never change architecture.” A replacement decision must identify the material new evidence, name the decision it supersedes, define migration, and prove the new behavior.

## Cross-track findings imported from prior investigations

### CT-001 — Preview is not proof of the Workstation Browser

A real Desktop smoke was once reported as “Workstation Browser interno” after the agent called `open_preview` and `read_preview`. That was a **false-positive identity claim**.

What that test actually proved:

- the Desktop Preview surface could navigate/render/read the page;
- Electron/Preview was functioning.

What it did **not** prove:

- `browser_navigate` existed in the session schema;
- `browser_snapshot` existed in the session schema;
- the Workstation `BrowserRuntime` handled the action;
- a BrowserTask was created/bound;
- Preview and Browser were the same page/runtime.

**Anti-repeat rule:** acceptance criteria that name a tool/runtime must be proven by the **exact tool invocation and execution boundary**, not by visually similar output. A successful substitute is evidence for the substitute only.

### CT-002 — Real Desktop tool exposure can fail before BrowserTask

A real-environment investigation established this before-state:

- the Capabilities UI showed **Browser Automation = ON**;
- `coding_context = auto`;
- `agent.disabled_toolsets = []`;
- persisted `platform_toolsets.cli` did **not** contain `browser`;
- effective `_get_platform_tools(..., "cli")` did **not** resolve `browser`;
- a genuinely new Desktop session did not receive `browser_navigate` or `browser_snapshot`.

This refuted the tempting hypothesis that `coding_context=focus` was simply stripping Browser in that environment.

The proven boundary was:

```text
Capabilities UI
  → toolset API/configuration
  → profile/config persistence
  → toolset resolution
  → Desktop session schema
  → browser_* execution
  → BrowserTask/runtime
```

**Anti-repeat rule:** do not modify BrowserTask lifecycle/persistence to fix a failure that occurs before the model receives `browser_*` tools.

### CT-003 — Automated lifecycle tests and native lifecycle evidence are different claims

Passing pure or mocked tests did not prove a real `WebContentsView`, native Windows process restart, or renderer identity behavior.

- pure tests prove lifecycle logic/serialization;
- mocked runtime tests prove adapter contracts;
- build/typecheck proves compilation;
- process launch proves launch;
- H-004 native probe proves the actual Windows/Electron/Chromium lifecycle contract.

**Anti-repeat rule:** never upgrade a lower-layer green result into a stronger claim than that layer can observe.

### CT-004 — CI must test committed source, not an auto-repaired checkout

An earlier Workstation install path could mutate/repair tracked source before validation, creating a false-green risk.

Durable policy:

- committed downstream source is canonical;
- normal install validates integration read-only;
- runtime state lives outside tracked source where appropriate;
- install must not dirty the checkout;
- migration/rebase helpers are separate from normal validation.

### CT-005 — A red broad Windows gate needs causality, not storytelling

Durable method:

1. reproduce exact base and candidate;
2. same OS/toolchain/dependency install/commands;
3. compare failure **signatures/classes**, not only counts;
4. keep scoped outcomes independently visible;
5. preserve final red when any required broad suite is red;
6. never delete/allowlist coverage to manufacture green.

### CT-006 — GUI/browser surface identity belongs to the session

Implementation 3 established:

- GUI/Desktop surface identity is session/platform state, not a process-global env proxy;
- controller reachability is execution state, not surface existence;
- tool-definition caching must include session-surface capability to avoid Desktop↔TUI leakage.

### CT-007 — Old BrowserClaw experiments are historical motivation, not the current architecture

Earlier BrowserClaw experiments inform requirements/failure modes; they are not permission to reintroduce BrowserClaw as the primary Workstation browser after the internal-runtime decision.

## Long-term product north star — governed by the roadmap

The broader direction is Hermes as a persistent execution/orchestration layer
for recurring work. V1 #1.5 now authorizes only the narrow, executable slices
listed in the roadmap; it is not permission to claim their later hardening scope
or to create parallel owners.

## WP-01 / BrowserSessionState objective — resolved and promoted

Complete the canonical BrowserSessionState foundation beyond BrowserTask-only
metadata while preserving the current live-page owners and avoiding a second
page store, SessionDB, Kanban, or control plane.

Operational base verification on 2026-08-30:

- the initially checked local `main` ref was stale at
  `ce78f120e8ed2974d6174e475cc7572afcfe41e0`;
- after fetching, `origin/main` resolved to the packet base
  `46a6ef9e257b4add01d6eb7f2a95a82bb433ee89`;
- branch `wp/codex/browser-session-state-core` was created directly from that
  verified remote ref without moving local `main`.

Scope boundary: ordinary logical tabs, order, active logical/generic tab, safe
URL/title metadata, BrowserTask relationship, available identity linkage, and
explicit recovery metadata/policy. Chat Browser View, Browser Hub, Preview
unification, host transfer, SessionDB/Gateway semantics, Kanban implementation,
LAN/Tailscale, Browser Memory, and KI-007 remain out of scope.

### Historical candidate acceptance status (superseded by final promotion)

- Implementer-focused validation on candidate
  `9ce769ee54ab6a02cad77a266c87cb05a8cad3f6` passed the scoped
  BrowserSessionState/BrowserTask tests, Desktop typecheck and Workstation
  contracts recorded below.
- Independent verification **blocked** that candidate because arbitrary raw
  page titles could cross the durable boundary and because the possible
  `new browserTasks + previous sanitized tab projection` crash snapshots had
  not been exercised through runtime restart/recovery.
- At that checkpoint the writer-branch work was a corrective candidate, not an
  accepted or promoted implementation.
- Independent re-verification and native Electron restart acceptance were still
  pending at that checkpoint; H010 and the final PR #11 promotion below
  supersede those temporary blockers.

### H-007 — BrowserSessionState can be a safe structural projection of existing authorities

Origin: WP-01 requires restart-safe logical browser state beyond the promoted
BrowserTask metadata, but forbids a second live-page owner.

Hypothesis:

- `entries`, `taskTabs`, and `activeTabId` remain authoritative for live
  process-local pages, task bindings, ordering, and active page;
- `BrowserTaskLifecycle` remains authoritative for logical task lifecycle and
  task identity/linkage metadata;
- the Chromium profile remains authoritative for browser-managed site/auth
  state;
- a versioned BrowserSessionState file can persist only a sanitized structural
  projection of those owners and restore logical intent without serializing or
  owning `WebContentsView`, `WebContents`, renderer heap, or process identity.

Experiment (registered before code inspection):

1. trace every mutation/read of `entries`, `taskTabs`, `activeTabId`, and
   `BrowserTaskLifecycle` on exact `origin/main`;
2. inspect current persistence, recovery, and BrowserTask regression tests;
3. classify each field as process-, BrowserTask-, BrowserSessionState-,
   Hermes-session-, or Chromium-profile-scoped;
4. derive the smallest persistence/migration seam that writes atomically and
   reconciles through the existing runtime owners;
5. define adversarial URL/title inputs whose credentials, secret markers, or
   sensitive content must fail closed before entering structural JSON.

Confirming evidence:

- no existing durable ordinary-tab owner exists;
- one snapshot can be built from current owners and restored through their
  existing mutation paths;
- task-owned tabs reconcile by `taskTabs`/`ownerTaskId` without duplicate pages;
- corrupt/unknown versions are ignored safely and atomic replacement preserves
  the last valid snapshot.

Refuting/reformulating evidence:

- another durable owner already exists for any proposed field;
- restoration would require a second `WebContentsView` map or independent task
  binding;
- raw URL/title persistence cannot be bounded by an explicit safe-metadata
  policy;
- any required change crosses SessionDB, Gateway, Kanban, Preview, or host/UI
  ownership.

Classification: **VALIDATED**.

Observed authority trace on exact base `46a6ef9e257b4add01d6eb7f2a95a82bb433ee89`:

- `WorkstationBrowserRuntime.entries` is the sole process-local live-page map.
  Its `Map` insertion order is the current tab order, and each `BrowserEntry`
  exclusively owns one `WebContentsView` plus live loading/crash state.
- `taskTabs` is the task id → live tab id index; `BrowserEntry.ownerTaskId` is
  the reciprocal ownership marker. `createTab(..., ownerTaskId)` and
  `rawEntryForTask()` reconcile stale/destroyed mappings through those two
  primitives and never allocate a second live page for the same task.
- `activeTabId` is the sole process-local physical active-tab pointer. Attach,
  navigation and UI state derive from it; it is cleared when its entry is
  discarded or destroyed.
- `BrowserTaskLifecycle.tasks` owns logical BrowserTask status, recovery and
  available linkage (`panelHost`, `controlHost`, `sessionHost`,
  `localConnection`, `leaseState`). Its version-1 `browser-tasks.json` is the
  only durable state on the base, and it deliberately contains no page URL,
  title, renderer object, or typed/page secret.
- `session.fromPath(workstationBrowserProfilePath(), { cache: true })` owns the
  dedicated Chromium profile: cookies, localStorage, IndexedDB, cache and
  compatible browser authentication. It is not BrowserSessionState.
- request `session_id` reaches the Desktop controller, but the base runtime does
  not currently mutate SessionDB/Gateway semantics with it. WP-01 therefore
  preserves available BrowserTask linkage without inventing missing
  SessionDB/run/Kanban authority.

Scope classification:

- process-scoped: `WebContentsView`, `WebContents`, renderer heap/process
  identity, `entries`, `taskTabs`, physical `activeTabId`, loading/crash flags,
  attach/bounds/control-server handles;
- BrowserTask-scoped: task id, lifecycle status/parked state, task recovery,
  task timestamps and available host/session/connection/lease linkage;
- BrowserSessionState-scoped: logical tab ids, ordinary/task relationship,
  structural order, active logical/generic tab, sanitized URL/title metadata,
  and explicit page-recreation policy/status;
- Hermes-session-scoped: the externally supplied Hermes session identity and
  its SessionDB/Gateway lineage remain owned outside this runtime; WP-01 only
  preserves an already-available linkage string inside BrowserTask metadata;
- Chromium-profile-scoped: site storage, cookies, cache, browser auth and other
  Chromium-managed data under the dedicated profile path.

Minimal persistence/migration conclusion:

1. introduce one versioned `browser-session.json` containing sanitized logical
   tab state plus the existing BrowserTask snapshot;
2. expose a BrowserTask persistence adapter over that same atomic file, so
   `BrowserTaskLifecycle` remains the in-memory task authority and no second
   BrowserTask JSON source remains active;
3. import valid version-1 `browser-tasks.json` only when
   `browser-session.json` is absent, atomically commit the composite state, then
   remove the legacy file; never fall back to stale legacy data when a new file
   exists but is corrupt or from an unknown version;
4. restore ordinary tabs by recreating new process objects in persisted order,
   while BrowserTask tabs remain metadata-only recovery hints until the promoted
   lifecycle lazily recreates exactly one page;
5. derive every subsequent snapshot from current runtime/lifecycle owners;
   temporary restart hints contain structural metadata only and never own a
   page object.

Security conclusion:

- URL metadata is safe only after an explicit allowlist/sanitization step:
  `about:blank` or HTTP(S), no userinfo, no query/fragment, bounded length, and
  rejection of credential/secret/session markers or opaque token-like path
  material;
- **Historical title conclusion — SUPERSEDED BY H-009 FOR DURABLE TITLES:**
  title metadata was considered safe after bounded normalization and rejection
  of controls, URLs/email-like data, secret markers, assignments and opaque
  token-like material;
- unsafe URL/title values become `null`/blank recovery metadata; raw values are
  never copied into structural JSON.

Current canonical durable-title rule: **Arbitrary page-controlled titles never
cross BrowserSessionState persistence; `safeTitle` is always `null`. Live
`WebContents` titles remain available in-process.**

Practical implication: H-007 supports the scoped implementation; it does not
justify changes to SessionDB, Gateway, Kanban, Preview, UI hosts, LAN, or KI-007.

### H-008 — Composite persistence and owner-driven reconciliation satisfy WP-01

Hypothesis:

- a standalone, pure BrowserSessionState serializer/persistence module plus a
  narrow runtime adapter can cover ordinary tab/order/active restoration,
  BrowserTask coexistence, safe metadata and restart reconciliation without
  changing any current live-page or lifecycle authority;
- adversarial serialization and runtime restart tests can prove that secret
  material and Electron process objects never enter the JSON and that task
  pages remain singular/lazy.

Confirming evidence: focused pure/runtime tests cover ordinary/order/active,
safe URL/title, unknown/corrupt version, atomic replacement failure, legacy
migration, BrowserTask coexistence/no duplicates, restart, secret exclusion and
stale/crashed reconciliation while all promoted BrowserTask regressions remain
green.

Refuting evidence: duplicate task pages, eager task-page resurrection, loss of
ordinary order/active state, raw secret markers in JSON, two independently
writable task files after migration, or any required cross-scope change.

Classification: **ACTIVE — REGISTERED BEFORE PRODUCT CHANGE**.

Product boundary marker: product edits are limited to the Electron runtime,
BrowserTask persistence seam, a dedicated BrowserSessionState module/tests, and
the branch-local engineering journal.

Historical policy qualifier: H-008 ran before the independent durable-title
blocker and H-009 correction. Its references to safe-title restoration or
preservation record the then-current candidate behavior, not the canonical
durable-title contract. The experimental outcomes below remain chronological
evidence and are not rewritten.

#### H-008 experiment 1 — focused pure/runtime gate

Command:

`npm run test:desktop:platforms --workspace apps/desktop -- electron/workstation-browser-session-state.test.ts electron/workstation-browser-task.test.ts electron/workstation-browser-runtime-task.test.ts`

Sandbox result: runner bootstrap failed before tests with `spawn EPERM`; this was
a sandbox subprocess restriction, not product evidence. The identical command
was rerun with approved process execution.

Executed result: **24 passed / 4 failed across 3 files**; the new pure
BrowserSessionState file and promoted pure BrowserTask file both passed. All
four failures were isolated to the runtime adapter:

1. three restored safe-title assertions under the historical pre-H-009 policy
   received `New Tab` because the fake WebContents emits `did-navigate` before
   any page title and `updateEntrySafeMetadata()` replaced the persisted safe
   title with `null`;
2. same-process crashed BrowserTask recovery reused the pending logical tab id,
   while the promoted regression requires a visibly new replacement tab/page id
   after a crash (`assert.notEqual(owned[0].id, firstTab.id)`).

Classification: **PARTIAL / CORRECTIVE**. H-008's composite persistence premise
is not refuted; the pure security/version/migration/atomic contracts passed.
The runtime reconciliation needs two narrow corrections.

Material correction registered before change:

- under the historical pre-H-009 policy, retain a previously safe title while
  navigation has no non-empty title, but still clear/reject it when a non-empty
  unsafe title arrives;
- distinguish restart recovery (`restored` hint may retain its logical tab id)
  from a same-process stale/crashed page (`stale` hint must allocate a new tab
  id while reusing only sanitized URL/title metadata and preserving order).

#### H-008 experiment 2 — focused gate after corrective changes

Identical approved command result: **3 test files passed / 28 tests passed / 0
failed**.

Covered outcomes:

- ordinary tab persistence, ordering and active logical tab restoration;
- historical pre-H-009 safe URL/title preservation and adversarial
  userinfo/query/fragment, secret-marker, opaque-token, URL/email-title and
  process-object exclusion;
- unknown/corrupt version fail-closed behavior;
- atomic replacement failure preserving the previous valid snapshot and
  cleaning the temp file;
- one-shot legacy BrowserTask migration into the composite file;
- BrowserTask/ordinary coexistence, lazy restart recovery and no duplicate task
  pages;
- unexpected stale ordinary-page reconciliation;
- all promoted pure/runtime BrowserTask regression tests.

Classification: **VALIDATED AT FOCUSED PURE/RUNTIME LAYER**. Next evidence
boundary: Desktop TypeScript typecheck/lint and the broader Electron platform
suite; no native Windows identity claim is added by this mocked runtime gate.

#### H-008 experiment 3 — Desktop typecheck, first pass

Command: `npm run typecheck --workspace apps/desktop`.

Result: **failed with one TypeScript error** at
`workstation-browser-session-state.ts`: the optional `browserTaskId` property
was correctly runtime-validated but TypeScript did not preserve narrowing across
a second property access before `.trim()` (`TS2339: Property 'trim' does not
exist on type 'unknown'`).

Classification: **STATIC NARROWING DEFECT**. Registered correction: capture the
unknown property once in a local, validate that local, then trim the narrowed
value. No runtime/persistence behavior changes.

First correction result: **still failed with the same TS2339**. Capturing the
property was insufficient because the `null | undefined | unknown` union was
reintroduced by the ternary expression. Materially changed correction: use an
explicit `if (rawBrowserTaskId === null) ... else { guard; trim }` branch so the
custom type predicate narrows inside one control-flow block.

Second correction result: the BrowserTask id occurrence narrowed successfully;
typecheck then reported the same TS2339 class at the sibling optional
`activeTabId` ternary. Registered correction: apply the same explicit guarded
branch to `activeTabId` before another full rerun.

Final typecheck result: **PASS / exit 0** for all three Desktop TypeScript
configs (`tsc -p .`, `tsconfig.electron.json`, and `tsconfig.e2e.json`, all
`--noEmit`).

Classification: **STATIC CONTRACT VALIDATED**.

Formatting check result: Prettier reported the four modified TS/test files plus
unchanged `workstation-browser-task.test.ts`. Classification: **EXPECTED LOCAL
FORMAT CORRECTION + PRE-EXISTING UNTOUCHED DRIFT**. Only modified files will be
formatted; the promoted untouched regression file will not receive unrelated
churn.

Focused ESLint first result: **423 problems (147 errors / 276 warnings)** across
the two modified legacy runtime files plus the two new files. The output shows
the legacy runtime/test already violate the current global `curly` and padding
rules throughout untouched lines; auto-fixing those files would create broad
out-of-scope churn. The new files also contain fixable import-order,
curly/padding and one `no-control-regex` issue.

Classification: **MIXED — PRE-EXISTING LEGACY LINT DEBT + NEW-FILE LINT**.
Registered action: make both new files independently ESLint-clean, then retain
typecheck/tests as the executable contract for the narrowly modified legacy
files rather than mass-rewriting them.

New-file lint/format result after scoped fixes:

- `npx eslint electron/workstation-browser-session-state.ts electron/workstation-browser-session-state.test.ts`: **PASS / 0 errors / 0 warnings**;
- `npx prettier --check` for the same files: **PASS**.

The `no-control-regex` occurrence was replaced with explicit code-point checks
covering C0 plus DEL/C1 controls; the security policy is unchanged.

#### H-008 experiment 4 — post-format focused/typecheck rerun

- focused Electron gate: **3 files passed / 28 tests passed / 0 failed**;
- Desktop typecheck: **PASS / exit 0** across renderer, Electron and E2E TS
  configs.

#### H-008 experiment 5 — full Electron/platform suite

Command: `npm run test:desktop:platforms --workspace apps/desktop`.

Final rerun after the active-logical-tab adversary: **12 files failed / 109
passed / 1 skipped; 33 tests failed / 1694 passed / 5 skipped (1732 total)**.

The three WP-01/BrowserTask files passed inside the full run. Every reported
failure is outside the changed subsystem and matches a documented KI-006
Windows class: POSIX permission-bit assertions, Darwin staging mode, Windows
8.3/realpath normalization, SSH ControlPath/Include assumptions, WSL probe
timeouts, symlink privileges, Git temp cleanup/timeouts, and PowerShell handoff
timing. No BrowserSessionState/BrowserTask failure appeared.

Classification: **KI-006 BROAD RED / WP-01 NON-REGRESSIVE AT SCOPED GATE**.
The broad command remains correctly reported as exit 1; no test was disabled,
weakened or allowlisted.

#### H-008 experiment 6 — Workstation Python contracts

Required wrapper: `scripts/run_tests.sh workstation/tests`.

Harness resolution evidence:

1. WSL Bash was denied inside the sandbox (`CreateInstance/E_ACCESSDENIED`);
2. approved WSL execution then found no pytest-capable WSL venv;
3. the Windows `.venv` also lacked pytest;
4. a system Windows Python had pytest 9.0.2, but passing it through WSL produced
   the invalid mixed path `C:\\mnt\\c\\...` before collection;
5. Git Bash provided the correct MSYS→Windows path translation; its first
   sandboxed launch was denied a signal pipe, then the identical approved
   wrapper run executed normally.

Final exact wrapper result: **4 files / 24 tests passed / 0 failed** in 5.9s.
This includes context-document contracts, bootstrap canonical-source checks,
Workstation contracts and browser routing/fail-closed tests.

Classification: **WORKSTATION CONTRACTS VALIDATED**. The failed preliminary
attempts were harness/environment failures before test collection, not product
failures.

#### H-008 experiment 7 — interleaved ordinary/task ordering adversary

The BrowserTask coexistence test was strengthened to persist order
`ordinary A → lazy task T → ordinary B` and assert `A → T → B` after T's lazy
page recreation.

First result: **27 passed / 1 failed**. T was recreated once with correct id,
URL, title and ownership, but appeared as `A → B → T`.

Root cause evidence: `restoreSessionTabs()` establishes the full restored order
before iterating, but creation of A called `reconcileRestoredEntryOrder()` while
the loop had not yet registered T as pending. Seeing zero pending hints, the
helper cleared the restored order prematurely.

Classification: **VALID ORDERING DEFECT / H-008 CORRECTIVE**. Registered minimal
fix: never clear the restored-order hint while the outer session restoration is
active; after the complete loop, retain it only while a lazy/stale structural
hint remains.

Corrective result: **3 files / 28 tests passed / 0 failed**. The strengthened
coexistence case now restores `A → T → B`, T is still created lazily through
`BrowserTaskLifecycle`, and its persisted logical id maps to exactly one live
page. A final forward-version adversary also proved that an existing
`BrowserSessionState.version > 1` is neither interpreted nor overwritten and
never triggers fallback to the stale legacy BrowserTask file; malformed/current
version state still starts from a fresh sanitized projection.

Classification: **H-008 VALIDATED**. The ordering hint is transient process
coordination only; `entries`, `taskTabs` and `BrowserEntry.ownerTaskId` remain
the live page/ownership authorities, while the composite file remains the only
restart projection.

#### H-008 experiment 8 — active logical BrowserTask without eager page resurrection

Hypothesis: reusing only process-authoritative `activeTabId` during restoration
would lose a persisted active BrowserTask because its physical page must remain
lazy. A task-only state would also need a generic live fallback page without
changing the structural active selection.

Experiment: make a task tab active, persist/restart, assert that no task page is
alive before `showTask()`, inspect the composite `activeTabId`, then show the
task twice and inspect id/ownership/page count.

Evidence: the first audit found that the physical fallback could overwrite the
structural selection. The corrective retains one transient
`restoredLogicalActiveTabId` only while its lazy tab hint exists. It is not a
page store: `activeTabId` still owns the physical active `entries` member, and
any ordinary activation or task materialization consumes the hint.

Final focused result: **3 files / 29 tests passed / 0 failed**. Before
`showTask()`, zero task pages exist and `browser-session.json.activeTabId`
retains the task's logical tab id. After `showTask()`, that same id maps to one
live page and becomes the physical `activeTabId`; the second show remains
idempotent.

Final static/contract results:

- full Desktop TypeScript typecheck (renderer + Electron + E2E): **passed**;
- ESLint for both new BrowserSessionState files: **0 errors / 0 warnings**;
- Prettier check for both new BrowserSessionState files: **passed**;
- final Workstation wrapper rerun: **4 files / 24 tests passed / 0 failed** in 4.9s.

Historical classification at that candidate: **IMPLEMENTER-FOCUSED VALIDATION
ONLY / INDEPENDENTLY BLOCKED**. These scoped results remain useful evidence, but they did not prove
the durable-title boundary or material composite-write interruption states.
Native Electron restart was still pending and promotion was not authorized at
that point; the later H010 final result supersedes this state.

### H-009 — Durable-title denial and executable composite recovery can correct the candidate narrowly

Origin: independent verification of candidate `9ce769ee...` demonstrated that
`safeTitleMetadata("Recovery code 482913")` returned the raw recovery code and
correctly identified that one BrowserTask operation can durably publish new
BrowserTask metadata before the final tabs/active projection.

Hypothesis:

- durable BrowserSessionState can set every page-controlled title to `null`
  without weakening the live `WebContents.getTitle()` surface;
- URL persistence can retain its conservative structural policy while failing
  closed for explicit recovery/verification/OTP/PIN/magic/one-time credential
  path semantics;
- injecting failure through the existing BrowserSessionState filesystem seam
  can capture the C1 create, C2 recreate/show and C3 destroy intermediate files
  through the real `WorkstationBrowserRuntime` integration;
- each possible `new browserTasks + previous sanitized tab projection`
  snapshot will restart deterministically, preserve at-most-one ownership,
  remain secret-free and converge to one canonical composite file.

Confirming evidence:

- every raw title, including harmless display text and numeric/customer labels,
  serializes as `safeTitle: null` while the live runtime still reports its real
  page title;
- credential-bearing URL query/fragment/userinfo/JWT/signed material and the
  explicit authentication path classes never appear in serialized or reloaded
  state;
- C1/C2/C3 restart assertions prove logical task uniqueness, lazy page
  recreation, orphan removal, deterministic active/order reconciliation and a
  canonical final snapshot.

Refuting evidence:

- any raw page title or forbidden credential material appears in JSON or after
  reload;
- a recovered task is duplicated, eagerly materialized, rebound to two pages,
  resurrected after destroy, or cannot converge after a faulted projection;
- proving recovery requires a second state owner or transaction framework.

Classification: **ACTIVE — REGISTERED BEFORE CORRECTIVE PRODUCT CHANGE**.

Product boundary marker: edits remain limited to the existing
BrowserSessionState sanitizer/persistence seam, its runtime injection point,
focused pure/runtime regressions and this journal. Native Electron restart is
still a later acceptance layer, not implied by the mocked Electron runtime
fault tests.

#### H-009 experiment 1 — security boundary and C1/C2/C3 focused gate

Command:

`npm run test:desktop:platforms --workspace apps/desktop -- electron/workstation-browser-session-state.test.ts electron/workstation-browser-task.test.ts electron/workstation-browser-runtime-task.test.ts`

The first sandboxed launch failed before config load with `spawn EPERM`; the
identical approved command then executed normally.

Result: **3 files / 33 tests passed / 0 failed**.

Observed executable evidence:

- every page-controlled title, including the five credential examples,
  harmless display text and a customer-number label, became `safeTitle: null`;
- live fake-WebContents titles remained visible before process teardown, while
  restored titles fell back to `New Tab`;
- access-token query, OAuth code, fragment token, userinfo/password, JWT and
  presigned credential material were absent from serialized and reloaded JSON;
- explicit recovery/verification/OTP/temporary-PIN/magic-login/one-time path
  classes failed closed, while `/customers/482913` remained restorable;
- C1 captured new BrowserTask T plus the previous sanitized ordinary-tab
  projection, then restored T parked/lazy and materialized exactly one page;
- C2 captured recreated/visible BrowserTask metadata plus the previous lazy
  sanitized tab/active projection, then restarted parked/lazy and converged to
  one task/page binding with deterministic order and active selection;
- C3 captured durable task removal before the final runtime projection, pruned
  the orphan relationship during normalization, refused later `showTask(T)` and
  reconciled the remaining ordinary tab as active.

Classification: **VALIDATED AT FOCUSED PURE/MOCKED-RUNTIME LAYER**. The
possible `new browserTasks + previous sanitized tab projection` intermediate is
explicitly accepted and proven recoverable; it is not described as impossible.
Next evidence boundary: formatting/static checks, full focused
`workstation-browser` tests, Desktop typecheck and Workstation contracts.

#### H-009 experiment 2 — required corrective validation matrix

Final scoped JavaScript results after formatting:

- BrowserSessionState focused: **1 file / 9 tests passed / 0 failed**;
- BrowserTask pure: **1 file / 10 tests passed / 0 failed**;
- Browser runtime-task: **1 file / 14 tests passed / 0 failed**;
- all focused `workstation-browser` tests together: **3 files / 33 tests
  passed / 0 failed**;
- targeted adversarial security regression: **1 passed / 8 skipped** under the
  title filter;
- targeted C1/C2/C3 regressions: **3 passed / 11 skipped** under the crash
  boundary filter.

Static results:

- complete Desktop typecheck (`tsc -p .`, Electron and E2E configs): **PASS /
  exit 0**;
- ESLint for the two dedicated BrowserSessionState files: **0 errors / 0
  warnings**;
- Prettier check for the two dedicated BrowserSessionState files: **PASS**.

Workstation Python contract result:

- the first exact wrapper attempt correctly refused to run because the local
  `.venv` lacks pytest;
- rerunning the same repository wrapper with `HERMES_PYTHON` pointing to the
  installed pytest-capable Python produced **4 files / 24 tests passed / 0
  failed** in 6.6s;
- context-document contracts passed with the corrected candidate/non-promotion
  terminology.

Historical classification at that candidate: **CORRECTIVE CANDIDATE VALIDATED
AT REQUESTED AUTOMATED LAYERS / NATIVE ELECTRON RESTART PENDING / PROMOTION NOT
AUTHORIZED**.
The delivery commit freezes the exact Git head for independent verification;
this journal does not treat that delivery action as promotion or native
acceptance.

### H-010 — The native profile-cookie failure is a probe lifetime defect

Origin: the `Workstation Browser Windows` run for PR #11 head
`9177d5a1ebab23d9ce3e5fe9664afbb7fdd43ec5` reached the H010 product path.
Phase A passed structural persistence, safe metadata and BrowserTask ordering,
but phase B failed with `phaseB Chromium profile cookie missing`.

The same exact-head run also exposed two independent static issues: Prettier
reported the two resilience test files, while the focused BrowserSessionState
suite still passed 5 files / 46 tests. Those formatting failures are mechanical
and are not evidence about runtime behavior.

Hypothesis registered before changing the probe:

- H010 creates `h010_profile_cookie` without `expirationDate`; Electron therefore
  treats it as a session cookie, which is not required to survive termination of
  the Chromium session;
- the dedicated `session.fromPath(...)` profile may be healthy even though the
  probe incorrectly asks a session cookie to prove durable profile persistence;
- setting an explicit future `expirationDate`, verifying the cookie immediately
  in phase A, flushing storage, and retaining the existing two-process phase-B
  assertion will test the intended persistent-profile boundary.

Confirming evidence:

- phase A observes the explicitly persistent cookie before shutdown;
- phase B observes the same cookie from the same Workstation profile path in a
  different Electron process;
- the cookie value remains absent from `browser-session.json`;
- all other H010 phases continue to pass on the exact corrected SHA.

Refuting/reformulating evidence:

- an explicitly persistent cookie is visible in phase A but missing in phase B;
- the two processes resolve different Workstation browser profile paths;
- a product shutdown/session-path defect, rather than cookie lifetime, is needed
  to explain the failure.

Local correction evidence after the change:

- the PR branch was first reconciled with `main` at
  `ce448d829e95112fd08b21535c7a8426ee866035`, preserving the one-click
  launcher before any promotion attempt;
- the five-file Browser foundation selection passed **5 files / 46 tests / 0
  failed**;
- complete Desktop typecheck passed;
- exact BrowserSessionState ESLint selection passed with **0 errors / 0
  warnings** after mechanical layout cleanup;
- exact BrowserSessionState Prettier selection passed;
- `git diff --check` and committed Workstation integration validation passed;
- this Linux environment cannot supply the repository's pytest-capable Python
  offline, so the unchanged Python contracts were not represented as a fresh
  local run. Their existing exact-branch evidence remains recorded above and
  GitHub CI must independently rerun them.

Classification: **LOCAL CORRECTION VALIDATED / EXACT-SHA WINDOWS H010 PENDING**.
Product boundary marker: this correction changes only the versioned native probe
and formatting-only test layout. It does not change BrowserSessionState or
BrowserTask runtime semantics. A new exact-SHA Windows run is mandatory because
the native probe itself changes.

Exact-SHA Windows result for `b5910874b27a4bfb4b45485a6438adbfd72cdcfb`:

- checkout identity, clean install, checkout-clean assertion, diff check,
  typecheck, exact ESLint/Prettier and the 5-file / 46-test focused suite passed;
- phase A observed the explicitly persistent cookie and completed;
- phase B, in a different Electron process, observed the same cookie from the
  same dedicated profile, retained it outside `browser-session.json`, restored
  ordinary/task ordering and lazily recreated exactly one task page;
- the original `phaseB Chromium profile cookie missing` failure is therefore
  **resolved**, validating the session-cookie lifetime diagnosis;
- H010 then advanced into its independent failed-write/destroy phase. Failed
  write convergence passed, but the immediate post-`destroyTask` assertion saw
  the old native `WebContents` before Electron emitted `destroyed`.

Reclassification: **COOKIE HYPOTHESIS VALIDATED / NEW NATIVE TEARDOWN TIMING
BOUNDARY ISOLATED AS H-011**.

### H-011 — Native `WebContents.close()` completion is asynchronous

Origin: H010 at exact head `b5910874...` failed with
`destroy fault mode prior WebContents survived` immediately after the runtime
had removed the BrowserTask and page entry in process.

Hypothesis registered before changing product or probe:

- `discardEntry()` synchronously detaches the view, clears `taskTabs`, removes
  the `entries` owner and calls Electron `webContents.close()`;
- real Electron completes `close()` asynchronously and emits `destroyed`, while
  the focused fake marks itself destroyed synchronously;
- the native probe's immediate `isDestroyed()` assertion therefore conflates
  synchronous logical-owner removal with asynchronous Chromium teardown;
- the correct native contract is: immediately no runtime/task owner remains,
  then the old `WebContents` reaches `destroyed` within a bounded wait before
  task-id reuse and fresh-page assertions continue.

Confirming evidence:

- immediately after the failed persistence write, `listTasks()` omits the task
  and `state().tabs` omits its old tab;
- the captured native `WebContents` emits/reaches `destroyed` within a short
  bounded wait;
- subsequent durable convergence and same-id recreation produce one fresh,
  blank page with a different tab id;
- the rest of H010, including abrupt-process restart, remains green.

Refuting/reformulating evidence:

- the runtime still exposes the old task/tab after `destroyTask` returns;
- native destruction does not complete within the bound;
- same-id recreation overlaps the old renderer or inherits its URL;
- a product-side lifecycle change is required to prevent continued page work.

Classification: **ACTIVE — NATIVE TIMING HYPOTHESIS REGISTERED BEFORE CHANGE**.
Product boundary marker: first correct the probe to observe Electron's
documented `destroyed` event/state with a bounded wait. Do not weaken immediate
assertions about logical task/tab ownership or fresh recreation.

Native result at exact head `ad905ddee902efc7d66db76220f44e963030843b`:

- immediate logical task/tab removal passed;
- bounded native `WebContents` teardown passed;
- durable convergence and same-id fresh recreation passed;
- H-011 is therefore **VALIDATED**;
- the probe then exposed a separate harness exit-code issue in abrupt phase A,
  isolated below as H-012.

### H-012 — Electron `process.exit()` return overwrote the abrupt exit code

Origin: H010 at exact head `ad905dde...` emitted
`H010_ABRUPT_PHASE1_DURABLE` and then unexpectedly emitted
`H010_MODE_PASS abrupt1`; the parent observed exit code `0` instead of the
allowed sentinel `17`.

Hypothesis registered before changing the probe:

- Electron's Windows main-process `process.exit(17)` shim initiated exit but
  returned control to the async ready callback;
- the common success tail then executed `app.exit(0)`, replacing the intended
  abrupt sentinel with a normal success code;
- persisted BrowserSessionState had already passed its pre-termination checks,
  so this is an orchestration/exit-code defect after the product boundary;
- selecting the final exit code exactly once through `app.exit(...)`, without
  calling `runtime.destroy()`, should preserve the abrupt-state experiment.

Confirming evidence:

- abrupt phase A exits with code `17` after its durable marker;
- abrupt phase B starts under a different PID, restores the ordinary logical
  tab and parked BrowserTask, lazily creates exactly one task page, and passes;
- full H010 reaches `H010_CLASSIFICATION=VALIDATED`.

Refuting/reformulating evidence:

- phase A still exits `0`, times out, or performs the runtime's clean destroy;
- phase B cannot restore the durable task/tab projection;
- a product persistence change is required before phase B can pass.

Final exact-SHA result at `d5be442021ea0c744351622317eef5212219786d`:

- abrupt phase A emitted `H010_ABRUPT_PHASE1_DURABLE` and exited with the
  allowed non-zero sentinel;
- abrupt phase B ran under a distinct PID and emitted
  `H010_ABRUPT_RESTART_PASS`;
- clean restart, profile separation, failed-write convergence and
  explicit-destroy cleanup remained green;
- the probe emitted `H010_CLASSIFICATION=VALIDATED`.

Classification: **VALIDATED / HARNESS DEFECT CORRECTED**. No
BrowserSessionState product change was required for H-012. PR #11 then promoted
the exact head as merge `e0a99ef3aba6e6d2b65c30cf3c908ee1d49c4d29`.

## Implementation 4 objective — closed

Required native lifecycle contract:

`create/navigate → hide or park → re-expose without replacement navigation → explicit destroy → real process restart → logical restore/recovery`

Final conclusion: **validated and promoted to `main`**.

## Evidence ledger

### H-001 — BrowserTask lifecycle caused the V9 native-smoke timeout

Classification: **REFUTED**.

Evidence: V9 printed `HARNESS_BOOT` but never `HARNESS_READY`; product runtime import had not occurred.

### H-002 — Electron 40.10.2 / Windows cannot reach `app.ready`

Classification: **REFUTED**.

Evidence: bare Electron readiness probe reached ready and created a BrowserWindow with exit code 0.

### H-003 — V9 readiness stall is caused by top-level `await app.whenReady()` in its ESM main path

Classification: **VALIDATED**.

Experiment: `probes/h003-esm-ready.mjs`.

Evidence:

- TLA case: boot → internal timeout; exit 3;
- `.then(...)` case: boot → ready → BrowserWindow → PASS; exit 0.

Conclusion: V9 was a harness bootstrap defect. Product runtime already uses non-blocking readiness registration.

### H-004 — Real BrowserTask lifecycle satisfies the Implementation 4 acceptance contract

Classification: **VALIDATED**.

Experiment: `probes/h004-native-browser-task-smoke.mjs` at `d8acc752133b125b9619cbc7fe09199f1283a22b`.

Live identity evidence:

- task `impl4-h004-live-task`;
- tab id stayed `a27236b9-4aaf-4adc-9556-7ee14f5c4274`;
- real `webContentsId` stayed `3`;
- owner page count stayed `1`;
- URL and renderer sentinel survived hide/show and park/show;
- hide produced logical `hidden` without destroying page;
- park produced logical `parked` without destroying page.

Explicit destroy evidence:

- `destroyTask` returned true;
- prior WebContents destroyed;
- task not listed;
- zero remaining task-owned tabs;
- no automatic replacement page.

Real restart evidence:

- process 1 PID `30968`: task persisted `parked` / `fresh`, structural state excluded page URL secret and renderer secret;
- process 2 PID `37440`: same task restored `parked` / `restored`, zero eager pages before show, first show created exactly one task page under same task id, recovery became `recreated`.

Practical conclusion: **Implementation 4 native lifecycle acceptance behavior is proven.**

### H-005 — Documentation-closure Workstation CI red represented a BrowserTask/product regression

Classification: **REFUTED AS PRODUCT REGRESSION / VALIDATED AS DOCUMENTATION CONTRACT REGRESSION**.

Evidence:

- `core-patch-dry-run` passed;
- 23/24 Workstation contract tests passed;
- sole failure was `test_context_separates_current_state_from_target_and_known_issues`;
- fingerprint was missing literal heading `## Not implemented yet` after a documentation rewrite combined tested sections.

Correction:

- separate canonical headings restored;
- test was not weakened.

### H-006 — Final-head broad Windows red introduced a new Implementation 4 failure class

Classification: **REFUTED BY CONTROLLED EQUIVALENCE**.

Controlled native-Windows A/B:

- baseline `ce78f120e8ed2974d6174e475cc7572afcfe41e0`;
- candidate `2ffee2335b6aba071e7b63457a047cd9334d4d92`;
- result `WINDOWS_BASELINE_COMPARISON=PASS_WITH_KI-006_RED`;
- candidate-specific BrowserTask tests: 2 files / 16 tests passed;
- candidate had fewer legacy failures than baseline and every remaining failure was identical to baseline or a variant of the same KI-006 causal class.

Final accepted head `75d10d35d4757496390debf8e4b4f9efb44c5432` differed from `2ffee...` only by contributor-attribution mapping and Workstation journal material. No BrowserTask product/runtime/probe/workflow/dependency code changed. On that head, committed integration, install, checkout-clean, typecheck and BrowserTask focused steps passed; only the broad aggregator remained red.

Classification used at promotion: `KI-006_ONLY_BY_CONTROLLED_EQUIVALENCE`.

## Experiment / failure ledger

| ID    | Attempt / fingerprint                                                | What happened                                                                                  | Classification                      | Anti-repeat lesson                                                                                                                               |
| ----- | -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| E-001 | PowerShell interpolation with `$code:` / `$ExpectedBranch:`          | ParserError before test                                                                        | Harness defect                      | Use `${name}:` when `:` follows an interpolated PowerShell variable.                                                                             |
| E-002 | Assume Electron/esbuild at root `.bin`                               | Dependency discovery failed despite `npm ci`                                                   | Harness defect                      | Inspect workspace ownership before hard-coding executable paths.                                                                                 |
| E-003 | PowerShell parameter `$Args`                                         | Arguments swallowed; tools printed usage                                                       | Harness defect                      | Never shadow automatic `$Args`.                                                                                                                  |
| E-004 | native stderr + `$ErrorActionPreference='Stop'`                      | Normal esbuild stderr became `NativeCommandError`                                              | Harness defect                      | stderr is not failure; gate on exit status.                                                                                                      |
| E-005 | `Start-Process` exit code on Windows PowerShell 5.1                  | successful run exposed unusable/null exit status                                               | Harness defect                      | Prefer Node `child_process` for native orchestration.                                                                                            |
| E-006 | arbitrary bundled `.mjs` as Electron target                          | launch did not prove valid app-entry semantics                                                 | Harness defect                      | Use a valid Electron app directory.                                                                                                              |
| E-007 | V9 + top-level `await app.whenReady()`                               | boot marker printed; ready marker never printed                                                | Harness defect                      | Never attribute pre-runtime timeout to BrowserTask.                                                                                              |
| E-008 | H-002 bare CommonJS readiness                                        | ready + BrowserWindow succeeded                                                                | Control evidence                    | General Electron/Windows startup is healthy.                                                                                                     |
| E-009 | H-003 ESM paired control                                             | TLA fails; `.then(...)` passes                                                                 | Root-cause evidence                 | Register readiness non-blockingly on this Windows/Electron path.                                                                                 |
| E-010 | H-004 real BrowserTask lifecycle                                     | live identity, explicit destroy, two-process restart, lazy recovery, secret isolation all pass | Acceptance evidence                 | Reuse the versioned probe; do not reconstruct ad hoc runners.                                                                                    |
| E-011 | Preview described as Workstation Browser validation                  | visually successful page was wrong lane                                                        | False-positive validation           | Exact tool/runtime boundary, not visual similarity, proves identity.                                                                             |
| E-012 | exact `browser_navigate` + `browser_snapshot` requested while absent | test correctly stopped rather than substituting                                                | Correct fail-closed behavior        | Capability absence is a result; do not substitute and call it passed.                                                                            |
| E-013 | coding focus blamed for Browser absence                              | environment showed `coding_context=auto`                                                       | Refuted hypothesis                  | Remove plausible explanations after direct contradiction.                                                                                        |
| E-014 | Capabilities UI ON but resolved CLI toolsets lacked `browser`        | new Desktop session lacked tools                                                               | Cross-layer discrepancy             | Trace UI → API → persistence → resolution → schema before changing runtime.                                                                      |
| E-015 | unit/adapter lifecycle tests treated as native smoke                 | mocks could not prove native restart/page identity                                             | Evidence-boundary error             | Match claim to observing layer; H-004 later supplied native proof.                                                                               |
| E-016 | installer repaired source before validation                          | mutated checkout could hide missing committed integration                                      | Resolved validation-design defect   | Test committed tree; keep repair/migration separate.                                                                                             |
| E-017 | broad Windows red interpreted without exact baseline                 | base/candidate shared failure classes                                                          | Causality lesson                    | Controlled A/B + signatures; baseline-equivalent red remains red.                                                                                |
| E-018 | GUI capability tied to process env/reachability/cache                | Desktop surface could disappear/leak across session types                                      | Resolved ownership-model defect     | Session-scoped surface identity; runtime reachability is execution state.                                                                        |
| E-019 | documentation rewrite removed tested canonical heading               | Workstation CI failed 1/24 although product code unchanged                                     | Documentation contract regression   | Inspect context-doc tests before restructuring canonical docs; documentation-only commits still require CI.                                      |
| E-020 | contributor email unmapped at final promotion                        | repository-wide attribution check failed                                                       | Process gate, corrected             | Merge hygiene is part of promotion; fix the mapping instead of dismissing/bypassing the gate.                                                    |
| E-021 | post-merge canonical docs still said Impl4 was pending               | code/GitHub and `CURRENT_STATE`/`ROADMAP` disagreed after merge                                | Post-promotion documentation defect | Promotion is not complete until canonical state documents reflect the new `main`; correct via a separate docs closure and run context contracts. |
| E-022 | Windows broad Desktop portability debt                               | Historical UI/platform failures reduced to 0 after contract-aware fixes and full reruns        | KI-006 resolved                      | Preserve platform-specific behavior explicitly; never hide a broad failure by deleting or weakening coverage.                                    |

## Stable anti-patterns / rules learned

1. Do not change product code because a validation harness failed before reaching the product boundary.
2. Instrument explicit markers at process boot, Electron ready, product import and each lifecycle milestone.
3. Prefer one orchestration layer with explicit timeout/exit semantics; on Windows use Node `child_process`, not stacked PowerShell wrappers.
4. Compare against a smallest known-good control and vary one material factor at a time.
5. Build success proves compilation only; process launch proves launch only; require behavior evidence.
6. Do not use top-level `await app.whenReady()` in native Workstation validation harnesses on the current Windows/Electron target.
7. Never repeat an experiment unless the materially changed input/assumption is recorded here first.
8. Never call `close-tab` or UI X equivalent to `destroyTask`; test explicit task destruction directly.
9. Do not use Task Manager PID disappearance as the canonical destroy invariant; use WebContents destruction + ownership/state evidence.
10. Once a reusable regression probe exists, improve that probe rather than creating an untracked replacement unless necessary.
11. Carry native smoke to a later documentation-only SHA only after Git proves relevant product/probe code unchanged.
12. Do not infer tool/runtime identity from screen location; inspect actual invocation/route/runtime identifiers.
13. Do not substitute Preview/web search/other browser lane when acceptance explicitly requires Workstation `browser_*`.
14. Never confuse Preview with Workstation Browser while separate lanes remain.
15. Locate the first broken boundary before fixing downstream components.
16. Label statements observed fact / hypothesis / inference / proven cause; reclassify when contradicted.
17. Typecheck, unit, mocked runtime, native smoke, and full E2E are distinct evidence classes.
18. A UI toggle is not proof backend configuration persisted.
19. Session, process, BrowserTask, profile, and renderer state have different owners/lifetimes; name owner before storing/caching/restoring.
20. Do not create parallel SessionDB/Kanban/Memory/browser state/control planes.
21. Do not synchronize duplicate browser pages by URL to imitate a shared BrowserTask; fix ownership.
22. Profile persistence and BrowserSessionState are different; renderer object identity never survives process restart.
23. Bound BrowserTasks fail closed; do not silently switch to a different stateful runtime.
24. Never allow install/CI to auto-heal tracked source before validation.
25. Broad pre-existing red requires controlled baseline/candidate evidence and remains red until fixed.
26. Keep diagnostic suites independent enough to collect evidence, while preserving final failure when required suites fail.
27. Prefer extending existing primitives over creating duplicate state owners.
28. Do not reopen superseded architecture debates without material new evidence.
29. One implementation/hypothesis cycle at a time: reproduce → isolate → smallest complete change → focused validation → correction → regressions → exact-SHA gates → docs → next.
30. In TDD corrective work, RED fails for intended reason; GREEN is smallest fix; REFACTOR only after green.
31. A checkpoint is memory, not a stop condition.
32. Before claiming a full Workstation browser path, separately prove configuration persistence, session schema exposure, exact tool execution, BrowserTask behavior, host/view unification, restart recovery, and profile persistence.
33. Canonical documentation is part of the tested product contract. Before renaming/removing required headings, fields, tables, or markers, inspect `workstation/tests` for structural assertions and run the relevant contracts after the edit.
34. After a promotion merge, audit state-bearing documents against the new `main`; pre-merge wording such as “candidate”, “pending”, or an old main SHA becomes a real consistency defect once the merge lands.

## Promotion closure

Implementation 4 promotion sequence is complete:

1. H-004 real Windows/Electron lifecycle accepted;
2. controlled Windows baseline comparison classified remaining broad red as KI-006;
3. final PR head frozen at `75d10d35d4757496390debf8e4b4f9efb44c5432` with no product/runtime/probe change after causal validation;
4. exact-final-head Workstation CI, Docker, contributor attribution, install/typecheck/focused BrowserTask gates observed;
5. PR #9 marked ready;
6. merge executed with expected head SHA;
7. PR verified merged and `main` verified at `fada723f43613e5e0f061cab24445573ac298998`;
8. merge parents verified: `ce78f120...` + `75d10d35...`;
9. canonical state/roadmap/known-issues/testing/journal closure is being reconciled in `docs/impl4-promotion-closure` because the pre-merge wording became stale only after promotion.

No WP-01 / BrowserSessionState candidate work belongs in this historical
Implementation 4 closure branch.

## Continuous update protocol

Before an experiment/change:

- register hypothesis/experiment ID when causal uncertainty exists;
- state confirming/refuting evidence;
- identify the product boundary marker;
- search this journal for the same fingerprint/premise/already-refuted hypothesis;
- inspect relevant executable contracts, including documentation contracts, before restructuring tested surfaces;
- state what material input changed if repeating a prior approach.

Immediately after:

- record exact output/error fingerprint;
- classify the hypothesis (`VALIDATED`, `PARTIAL`, `REFORMULATED`, `REFUTED`, `INCONCLUSIVE`);
- record practical implication;
- identify the next materially relevant action;
- promote stable product truth into canonical docs instead of leaving it only here.

No experiment is complete until this file is updated. A checkpoint is never permission to stop; it is memory for the next action.

## 2026-09-15 — Current-main Workstation gap audit closure

Status: VALIDATED — focused contracts green; clean-candidate release evidence remains external

Audit base: started at `main@b6ac2d273a43e287122db377bcfa702af6e7553c`, then
rebased and revalidated on `origin/main@80d4ffce3cfba3ed03474a5b8ebcede4a7fc1770`
after its docs-only advancement. The audit found and closed the confirmed
host-independent path-policy failures, the Human Card → Agent Task delegation
gap, the unscoped human browser-control boundary, extension update last-known-
good handling, operational-reference loss risk in compaction, and the missing
provider-free workload baseline.

Evidence and ownership decisions:

- `workstation/path_utils.py` classifies Windows drive/UNC, POSIX absolute and
  relative syntax without applying the host OS's `abspath`; ReleaseQualification
  and ScopedPolicyEngine now remain fail-closed across host/target OSes.
- `hybrid_card_delegations` extends the canonical `hermes_cli.kanban_db`; it is
  not a second task database. Attempts, restart/idempotency, independent
  lifecycles, terminal writeback and compact evidence references are covered by
  `tests/hermes_cli/test_hybrid_kanban.py`.
- `BrowserHumanControlLease` is owned by `BrowserTask` and scoped by task,
  session, tab/page/profile and expiry. Restore clears process-local human
  authority; unrelated tasks remain runnable. Focused Electron lease contracts
  passed.
- `ChromeExtensionManager` journals promotion and retains the previous content
  until load/verification commit. Staging, replace, load, verification and
  restart recovery tests preserve v1 as last-known-good.
- The compactor emits a bounded operational-reference envelope beside the
  narrative summary. `workstation/benchmarks/workload_baseline.json` contains
  deterministic structural counters for refs, deduplication, worker ACK/restart,
  compaction, policy errors and event invalidation; no private `.db` is committed.
- KI-007 was not reproduced by the deterministic session/export/reconnect and
  concurrent close/export test, so SessionDB was deliberately not rewritten.

Validation on this working tree: `python -m pytest -q workstation/tests` passed
247 tests; the focused Hybrid/worker/policy/plugin contracts passed 78 tests;
extension/KI-007/benchmark/compaction contracts passed 17 tests; compaction
regressions passed 148 tests; Desktop typecheck passed; the Electron platform
suite passed 1,778 tests with 5 pre-existing skips; and strict doctor, lock,
license and integration-anchor checks passed. The full Desktop UI suite passed
591 files / 5,669 tests with `--maxWorkers=4`; the integrated Workstation
Browser E2E passed 2/2. Release promotion still requires the existing
clean-machine candidate workflow and branch-protection governance.

## 2026-09-15 — Post-implementation security/reliability red-team

Status: IN PROGRESS

Pinned audit base after explicit mainline consolidation:
`main@ce5d3260c9791eee24a9c07c389e95a6e4d38c57` (equal to `origin/main`).
The pre-existing dirty `feat/workstation-hybrid-kanban` work was preserved as
`ab8a269fc2` and merged into main as `ce5d3260c9`; its focused suite passed
24 tests before this audit resumed.

Initial evidence matrix (classification precedes corrective edits):

| ID | Finding | Initial classification | Current-main evidence / reproduction hypothesis | Required proof |
| --- | --- | --- | --- | --- |
| RT-001 | Compaction trust-boundary poisoning | CONFIRMED | `agent/context_compressor.py::_build_operational_reference_envelope` serializes every message/content and promotes regex matches, including `approval_state`, without a trusted structured source check. | Adversarial role/source matrix; structured trusted-runtime refs survive recursive compactions; raw text never becomes authority. |
| RT-002 | Structured browser errors end-to-end | CONFIRMED | `tools/browser_workstation.py::_request_json` converts HTTP/error JSON into textual `WorkstationBrowserError`, dropping code/retry/state/action/resource/details. | Electron→HTTP→Python→executor model-visible contract for all required codes plus incidental-word adversarial messages. |
| RT-003 | Bound BrowserTask after Core restart | CONFIRMED | `_BOUND_TASKS` is a process-local set and `_is_bound` consults no BrowserTask/resource projection. After restart, controller loss permits legacy fallback when routing is enabled. | Process-A binding followed by fresh-process/core-state B and controller loss must fail closed. |
| RT-004 | Persistent worker start overwrite | CONFIRMED | `WorkerRegistry.start_persistent_worker` unconditionally creates/replaces `_PersistentWorkerRecord` when no live in-process worker exists, ignoring a loaded durable record. | Restart then `start` preserves/rehydrates or emits explicit recovery error; lineage mismatch rejected. |
| RT-005 | Worker multi-process lost updates | CONFIRMED | Persistence uses only `threading.Lock`, writes the registry's in-memory snapshot, and atomically replaces JSON without interprocess locking/generation/merge. | Two real processes, distinct and same worker IDs, crash matrix and 100-item accounting. |
| RT-006 | Turn-budget spill metadata parity | PENDING | `agent/tool_executor.py` has two `maybe_persist_tool_result` call paths; arguments and security scope require direct comparison/testing. | Forced budget spill retains scope/hash/result/artifact refs. |
| RT-007 | Cross-turn result economy | PENDING | Content-addressed spill reports hit/miss, but that is not yet evidence of a safe execution cache or duplicate-context suppression. | Explicit cache-safe allowlist, source-version invalidation and session/security isolation or classification as intentionally unimplemented. |
| RT-008 | Production-path benchmark | PENDING | Existing structural workload baseline and newly consolidated benchmark modules require tracing against production executor/storage/event/worker/compactor paths. | 100-item deterministic scenario with restart, persistence failure, browser stale error, escalation and two compactions. |
| RT-009 | Controller descriptor recovery | PARTIAL | `_read_control` validates protocol/loopback/token but not PID identity and does not reconcile a stale descriptor; connection errors become textual unavailable errors. | Dead/mismatched PID, refused port, token mismatch and unrelated loopback service produce deterministic recovery or structured `CONTROLLER_DOWN`. |
| RT-010 | Process ownership vs raw terminal | PENDING | Existing `process_registry`, approval and threat/policy layers must be exercised before changing them. | Owned/unowned same-name process and Windows/POSIX wildcard-kill matrix. |
| RT-011 | Documentation authority conflict | CONFIRMED | `HERMES_WORKSTATION_INTELLIGENCE.md` claims canonical/single-source authority while `context/README.md` defines a distributed reading order that omits it; `CURRENT_STATE.md` still describes an uncommitted working tree and stale SHAs. | Unambiguous relative authority and final-SHA-only validation claims. |
| RT-012 | Governance/CI | PENDING | Repository workflows and remote branch protection have not yet been inspected on the pinned head. | Exact local CI coverage plus API-backed protection evidence or explicit manual owner actions. |

Next experiment RT-E001: execute the compactor directly with each untrusted
origin carrying forged operational labels. Confirming evidence is any forged
label appearing below the authoritative Operational References heading;
refuting evidence is complete absence for origins 1–6 with survival only from a
runtime-authenticated structured envelope.
# 2026-09-17 — Read-only durable bootstrap

Base: origin/main `1c6953d9f18b6d48459899cf327acd1c71dda579`.
Hypothesis: hybrid tools fail closed as MUTATION; repeated compile refusals
halt the agent before structured discovery can repair a plan. Existing
browser_extract_items, registry effects, compiler and checkpoints remain owners.
Experiment: fake 12-card provider, safe structured DOM inspection, discovery
before compilation, independent readback and process restart without replay.
No live Trello operations. Structural verifier admission must precede dispatch.
Observed: final fake-provider/compact-ledger focus 22 PASS; native Workstation
465 PASS / 2 existing skips; Ubuntu canonical Workstation runner 468 PASS / 0
failures (52 files). Later mapped-readback cases are included in the 22-test
focus and await the final full rerun. Electron 126 files / 1783 PASS / 5 existing
skips; UI 593 files / 5674 PASS; Desktop typecheck PASS; diff --check PASS.
Initial native full-core collection failed on missing ACP/POSIX-only fixtures;
Ubuntu locked CI extras and canonical per-file runner resolve that environment.
Full core suite remains in progress; no aggregate-green claim yet. No config
switch/threshold edits and no live provider actions. Git worktree pointer is
relative for Windows/Ubuntu interoperability; original dirty checkout preserved.

Core timing experiment: full Ubuntu runner observed one unchanged sequential
interrupt test at 12.79s against its 10s bound under 16-worker load. Neither that
test nor its middleware was modified. Hypothesis: scheduler/filesystem contention;
rerun the same file in isolation without changing its bound or runtime behavior.


## 2026-09-18 — Native-browser durable-compiler obstruction and progressive-compilation reformulation

Status: **VALIDATED root-cause class / architecture REFORMULATED; product fix still OPEN**

Observed dogfood sequence on the internal Workstation Browser:

1. authenticated Electron Chromium navigation succeeded;
2. browser_snapshot and structured extraction succeeded on the same page;
3. mutating browser interaction was replaced by durable_compile_required;
4. durable compilation asked for mutation authority + persistent readback/verifier
   semantics before the unknown stateful UI workflow had been discovered;
5. one compiled attempt failed route policy with
   "Route forbidden by task constraints: native_browser" even though the requested
   lane was the native browser;
6. an attempted authority-recording path could itself be intercepted, exposing a
   bootstrap/deadlock class.

Code inspection on current main identified the matching boundaries:

- workstation.work_intent.prepare_turn_work() stores
  agent._work_batch_candidate = batch_intent(...);
- workstation.task_compiler.requires_compilation() treats that broad flag as a
  reason to reject later non-read/non-interactive effects;
- workstation.batch_detection.detects_fan_out() already has a useful
  operation-level structural_signature(), but the resulting state is promoted
  to the broad boolean latch;
- tools.effects conservatively classifies unknown builtins as MUTATION while
  agent/tool_guardrails.py maintains overlapping classifications, including a
  disagreement around browser_console;
- route comparison can receive tool-name constraints while TaskCompiler evaluates
  the canonical route native_browser;
- RoutinePromotionService and DeterministicRoutineRunner already implement the
  desired high-level lifecycle: discover/validate/promote and return DRIFT on
  violated assumptions.

Classification:

- **VALIDATED:** native-browser controller/authenticated read path is not the root
  failure in this reproduction.
- **VALIDATED:** a request/session-scoped repeatability latch is too broad.
- **VALIDATED:** effect/route namespace inconsistency can produce false blocking.
- **REFORMULATED:** "LLM must not be CPU" remains correct, but compilation must be
  progressive optimization for understood repeated work, not a prerequisite for
  exploring a safe deterministic path.

Settled target promoted to canonical docs:
context/ADAPTIVE_EXECUTION_COMPILATION.md.

Required implementation hypothesis AEPC-E001:

> replacing the global latch with operation-scoped compilation policy, permitting
> bounded adaptive native-browser interaction, normalizing route/effect authority
> and adding compact NEEDS_REASONING escalation will restore workability while
> preserving fan-out/canary/uncertain-mutation protections.

Confirming evidence:

- adaptive browser regression completes without compiler/preflight refusal loop;
- homogeneous fan-out regression still requires TaskCompiler/canary;
- candidate scope isolation test passes;
- route/effect consistency tests pass;
- deterministic drift returns compact reasoning handoff and resumes without replay;
- existing durable/compiler/routine/canonical Work100 gates stay green.

Refuting evidence:

- any safe adaptive path bypasses an existing approval/fence/uncertain-mutation
  invariant;
- homogeneous fan-out can again proceed item-by-item through the LLM;
- deterministic resume replays a confirmed external effect;
- the fix requires a parallel task/memory/browser/authority store.

No live external mutation is required for the focused reproduction; use fake
providers plus existing internal-browser mocked/native contracts. A later native
Electron dogfood is required before declaring the browser path product-validated.

## 2026-09-18 — H-069: Verified Operational Control Plane (CP0–CP9)

Status: **IN PROGRESS**

Hypothesis:
> A deterministic executability typechecker / proof engine (Capability Router) that enforces
> typed Predicate/Effect IR, Goal Non-Expansion, Authority Non-Escalation, Invariant Preservation,
> and Preflight Revalidation before any mutable dispatch will eliminate unnecessary LLM calls
> (LLM waiting waste = 0) while strictly guaranteeing: NO VALID CERTIFICATE -> NO DISPATCH.
> Extending OperationalCapability, TaskCompiler, RuntimeEventBus, and reasoning_handoff
> backward-compatibly will preserve all existing Experience Compiler and Capability Runtime contracts.

Sub-phases tracked:
- CP0: IR + OperationIntent + canonical hash + IntentRevision
- CP1: CapabilityFormalContract + authority lattice + backward compatibility
- CP2: index + direct Router + CandidateMatch + RoutingCertificate
- CP3: bounded composition + CompositionCertificate + threat detection
- CP4: certified dispatch + state freshness + preflight revalidation
- CP5: persistent AwaitCondition + CausalEventEnvelope + temporal/polling + event fencing
- CP6: OpenCondition + AttentionPacket + Router re-admission after LLM
- CP7: Skill capability-family metadata + internal catalog behavior
- CP8: metrics + shadow mode + failure attribution + baseline comparison
- CP9: full integration, Work100 benchmark, canonical gates and documentation.

## 2026-09-18 — Browser ownership/recovery pre-implementation hypothesis (historical; promoted to H-072)

**Classification:** VALIDATED BY CURRENT-MAIN CODE AUDIT / IMPLEMENTATION OPEN.

**Observed cluster:** hover flicker; restart can leave Chat Browser on Blank Page;
agent can continue Browser work invisibly; Hub may report Parked during real work.

**Hypothesis:** persistence is not the primary loss boundary. The defect is incomplete
reconciliation across session-scoped preview intent, BrowserTask/BrowserSessionState
lazy recovery, activeTabId and one host-owned native viewport, plus an overly broad
native-view occlusion detector.

**Confirming evidence:**
1. Hub and Chat toggle setVisible from duplicated overlay observers containing generic
   `data-radix-popper-content-wrapper`;
2. tooltips use Radix portals/poppers and chat rows use `OverflowTip`;
3. BrowserTask restore => `parked/restored`; task tabs are lazy;
4. `ensure()` may create active `about:blank` while the logical task tab is pending;
5. `entryForTask()` can recover a controller page then park its projection if not attached;
6. runtime `attach(... preferredTaskId)` exists and task-switch tests pass;
7. preload/types/Chat pane omit that argument;
8. `setBounds` is host-fenced but `detach`/`setVisible` are not.

**Smallest experiments:** BOR-E001 explicit occluder contract; BOR-E002 production
preferredTaskId wiring; BOR-E003 host-fenced cleanup; BOR-E004 task-bound pending-tab
materialization across A/B restart; BOR-E005 independent activity projection.

**Practical implication:** fix one reconciliation invariant, not four symptoms.
Active chat + open Browser surface + matching BrowserTask must converge Chat UI, Hub,
task, active tab and viewport host on one identity without foreground theft.

Canonical target:
`../BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md`.

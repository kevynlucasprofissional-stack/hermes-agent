# Current State

## 2026-09-22 H-080 Published Implementation Audit — FEATURE BRANCH REAL / PROMOTION BLOCKED

Canonical audit:
`workstation/context/engineering-journal/h080-branch-quality-audit-2026-09-22.md`.

Repository truth:
- shared main at audit start: `bdd25751088427b83482331aa74a82d24d789cf4`;
- implementation branch: `integration/upstream-20260922-71a2fe39-h0793`;
- audited branch head: `9c217afbc84e89acb32f83043f800ad6df9eb55d`;
- frozen upstream pin: `71a2fe399bbd7a219c71f9d9fca2b313b01f2057`;
- true upstream merge: `a8dfcd21f5c641d01a5989e223a987687018db7f`;
- rejected attempt `471e9b5` remains reverted/inactive;
- branch is published on GitHub, but at audit time had no open PR and no GitHub Actions/status evidence on its head.

Classification:
```text
GENERIC PRE-REASONING BOUNDARY: IMPLEMENTED / DIRECTION ACCEPTED
DIRECT GENERIC->WORKSTATION COUPLING: AVOIDED
ESTABLISHED TYPED INTENT: IMPLEMENTED
RAW-PROSE INTENT SYNTHESIS: ABSENT
UNCERTAIN-MUTATION ROUTER INPUT: IMPLEMENTED
BROWSER DOMAIN PROJECTION OWNERSHIP: IMPROVED / ACCEPTED
NORMAL-TURN SATISFIED BYPASS: PROVEN IN TEST
NORMAL-TURN EXECUTE BYPASS: NOT YET PROVEN
VERIFIER-FAILURE E2E: MISSING (TEST IS PASS)
EXPERIENCE FEEDBACK LOOP: OPEN
SEAM-OPERATIONAL-RESOLUTION: REFERENCED BUT NOT REGISTERED
UPSTREAM INTERVENTION REGISTRY: PRESENT BUT PROVENANCE/SCOPE INCORRECT
EXACT-HEAD CI: ABSENT AT AUDITED HEAD
PROMOTION: BLOCKED
```

Critical correction:
`test_known_promoted_capability_bypasses_llm` currently begins with a semantic state that already satisfies its goal. That test proves `SATISFIED -> provider calls 0`, not `promoted capability EXECUTE -> exact-once dispatch -> VERIFIED/accepted -> COMMITTED -> provider calls 0`.

Required release proof remains:
```text
initial goal false
-> normal Hermes turn
-> promoted capability selected
-> EXECUTE
-> physical dispatch exactly once
-> canonical VERIFIED + accepted
-> COMMITTED
-> canonical finalizer
-> provider calls = 0
```

The branch should be repaired and qualified, not reverted or redesigned from scratch.

## 2026-09-21 H-079.2 Upstream Re-adoption + Dogfood Closure — LOCAL GREEN / EXACT-HEAD CI PENDING

Canonical: [H079_2_UPSTREAM_DOGFOOD_CLOSURE_2026-09-20.md](H079_2_UPSTREAM_DOGFOOD_CLOSURE_2026-09-20.md).

Exact observed state:
- downstream `main`: `964c13361e95a49e680deb2b16479d5f85c63011`;
- latest upstream observed: `641f7c810449d9af5c21b0a5ee33b29b192b4117`;
- compare: 547 downstream-only / 622 upstream-only commits; merge-base `c1488ac947...`;
- latest upstream pin actually ancestral to `main`: `c1488ac947...`;
- PR #40's `8d153b26...` merge is valid only on `integration/upstream-20260920-8d153b26-h0791`, not current `main`.

Exact-head positive evidence on current main:
- Workstation contract suite: **743 passed**;
- durable core seam regressions: **327 passed**;
- controlled canary/replay: PASS;
- core integration dry-run: PASS;
- Docker: PASS.

Current candidate truth:
- true upstream merges `3d1c18752975...` and `fde9e51...` adopt final pin `afc3b7c6f397...` with behind-selected-pin = 0;
- pipless install prefers `uv`, falls back through verified `ensurepip`, and rejects invalid existing interpreters before installation;
- H-077 negative/positive delta and real no-network Anthropic SDK construction contracts pass;
- full Workstation is 742 passed / 0 failed / 2 skipped; Desktop UI is 8,592 passed and Electron platform is 2,453 passed;
- H004 is VALIDATED; sustained H013 is 3/3 with accepted 16-task/120-second/8-turn evidence; Work100 is 30 PASS;
- exact-final-head GitHub Actions and final upstream drift still gate promotion.

Classification:
```text
CORE WORKSTATION: QUALIFIED AT EXACT HEAD
UPSTREAM FRESHNESS: SELECTED PIN ADOPTED / FINAL DRIFT PENDING
DOGFOOD INSTALLER: LOCAL MATRIX PASS
WINDOWS RELEASE GATE: LOCAL PLATFORM PASS / CI PENDING
H-079.2: PROMOTION PENDING
NEW FEATURE WORK: BLOCKED UNTIL H-079.2 CLOSURE
```


## 2026-09-20 H-079 Upstream-First Change Gate — PRIMARY OPERATING POLICY

Before any new downstream runtime adjustment or implementation, execute
[UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md](UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md).

Current policy:
```text
fresh upstream preflight
-> exact pin
-> qualified upstream-aligned baseline
-> seam reconciliation
-> target implementation
-> exact-head qualification
-> final upstream drift snapshot/classification for the next cycle
-> PR merge
-> local main fast-forward from origin/main
```

This is stricter than the old periodic-sync model and safer than continuously rebasing a
feature against moving upstream. Baseline synchronization and target work remain separate
and independently reviewable.

The pin is immutable for the entire promotion cycle. A final `upstream/main` fetch records a
new tip and its relevance to the **next** cycle; it does not authorize a second upstream merge
or invalidate a qualified candidate merely because upstream advanced.

Observed qualified baseline snapshot (2026-09-20; qualification applies only to the recorded SHA):
- `main@9e8127e247...`;
- adopted upstream pin `c1488ac947...` merged into `main` via merge commit `24a8501934...`;
- superseded pin: `b7d7d2929a...` (H-079 candidate pin, merged in `a13929fb35...`, replaced when `24a8501934...` landed);
- merge ancestry verified: `git merge-base 9e8127e247 2c0b2a980c` -> `c1488ac947...`;
- drift at `9e8127e247...` versus upstream snapshot `2c0b2a980c2d0e92f0452500089f5af91208f94c`: 544 downstream-only and 447 upstream-only commits;
- H-079 Stage A & B are merged to `main`.

**The exact-head baseline gate is GREEN.** `9e8127e247...` (PR #41, carrying the
browser-routing-ladder fix `1716062f32...`) passes `Workstation CI` (job `contracts`). The red run
was at `d0ade123c0...`, which that fix supersedes. The evidence is run `35536129052` and does not
automatically qualify later branch or main heads. Aggregate browser convergence is
**UNMEASURED**: no named acceptance check is cited for the former `FULL` claim; this is distinct
from the narrower Browser Authority Convergence evidence below.

## 2026-09-20 H-078C Items — CLOSED / PROMOTED TO MAIN

The open qualification debt from H-078C was resolved and verified on the H-079 candidate and
promoted to `main`:
- **Workstation Test Suite**: 741 passed, 2 skipped, 1 warning (291s).
- **Runtime Independence**: Fresh-process isolation test proves AlternateReasoner runs without importing `run_agent`.
- **Browser AppView Core Patch Anchor**: Semantic layout anchor updated; `apply_core_integration.py --check` passes cleanly.
- **Browser Authority Convergence**: Generic `browser_tool` routes through `browser_extension_router` -> `BrowserControlBroker` -> `WorkstationBrowserController`; single mutation executor invariant preserved; legacy router downgraded to non-authoritative compatibility adapter.
- **Tool Batch Admission**: Owned exclusively by `agent/turn_tool_round.py` with admission marker; duplicate execution eliminated in `run_agent.py`.
- **Adapter Bootstrap**: Explicit fail-closed semantics implemented when Workstation supervision is expected.
- **Desktop & Native Browser**: H004 native probe VALIDATED; Desktop typecheck 0 errors; Desktop production build clean; H013 sustained headless load spec passes 3/3 in 1.4m.
- **Seam Audit**: 18 classified, 0 unclassified, 0 budget regressions; `first_party_seams.json` synchronized with exact reality.

These items were promoted to `main` in `24a8501934...`. Exact-head CI was subsequently evaluated:
it was **red** at `d0ade123c0...` for the `BrowserRoutingPolicy` ladder regression described above,
and is **green** at the qualified head `9e8127e247...`. The H-078C closure items themselves were
not implicated in either run.


## 2026-09-19 H-078B Code-to-Code Migration & Semantic Decoupling — COMPLETE / ACTIVE

The H-078B semantic decoupling and code migration has been fully executed and empirically verified.

Current architectural state:
- **Zero Direct Workstation Imports in Core**:
  `run_agent.py` (0), `agent/conversation_loop.py` (0), `agent/tool_executor.py` (0),
  `agent/turn_finalizer.py` (0), `agent/turn_constraints.py` (0), `agent/chat_completion_helpers.py` (0),
  `agent/conversation_compression.py` (0), `cli.py` (0), `gateway/run.py` (0),
  `hermes_cli/kanban_db.py` (0), `hermes_cli/web_server.py` (0), `tools/file_tools.py` (0),
  `tools/tool_search.py` (0), `tools/close_preview_tool.py` (0).
- **Generic Core Lifecycles (`agent/`)**:
  Generic upstream-safe extension points provide turn ingress (`TurnIngress`), turn admission (`admit_turn`),
  batch admission (`admit_tool_batch`), scoped execution (`scoped_execution`), pre-authorized dispatch
  checkpoints (`dispatch_pre_authorized_checkpoint`), raw post-tool observations (`dispatch_raw_post_tool_observation`),
  persistence disposition (`ExecutionPersistenceDisposition`), turn route policy (`TurnRoutePolicy`),
  completion admission (`admit_completion`), compression bypass (`should_bypass_compression`),
  wire projection (`project_messages_for_provider`), and task completion admission (`admit_task_completion`).
- **First-Party Adapter Façade (`workstation/integrations/hermes/`)**:
  All Workstation capabilities (Progressive Compilation, durable dispatch, mutation journals,
  procedure traces, kanban completion contracts, browser capabilities, and continuation projections)
  are wired cleanly through generic registries upon installation (`install_workstation_adapter`).
- **Seam Audit Verification**:
  `workstation/scripts/audit_hermes_seams.py --strict` passes with:
  `Direct core seams: 18 (all classified first-party tools), unclassified: 0, budget regressions: 0`.
- **Runtime Independence Verified**:
  Verified via `workstation/tests/test_h078b_runtime_independence.py` that a foreign / alternate reasoner
  can drive the entire Workstation kernel through the generic lifecycle contracts without ever importing `run_agent.py`.
- **All Core Test Suites Green**:
  Passed H-077.1 qualification closure, architectural falsification, control plane integration,
  canonical work loop, continuity, durable agent integration, and generic seam suites.


## 2026-09-19 H-078A Minimum Necessary First-Party Seams — ACTIVE

H-078 was refined after a second code audit and the Browser/UX counterexample. The project
will **not** use "zero downstream source seams" as a success metric.

Modern upstream now exposes stronger generic hooks/middleware/providers and a Desktop
Plugin SDK with pane/workspace docking. These should absorb accidental Workstation
coupling wherever full parity exists.

At the same time, current Workstation Browser behavior still includes privileged native
Electron responsibilities that are not equivalent to a renderer plugin: persistent
`WebContentsView`, BrowserTask/page ownership, background continuity, human control,
stale-run fencing, Hub/Chat transfer, native IPC and recovery. Those are legitimate
first-party seam candidates until a generic upstream abstraction can preserve them.

New policy:
`REMOVE | UPSTREAM_ABSTRACT | PRESERVE_FIRST_PARTY`.

The initial classification registry is `workstation/first_party_seams.json`. It is a
starting inventory, not a claim that the audit is complete. The next upstream migration
must expand/revise it from the actual pinned-SHA overlap analysis.

No capability may be removed merely to improve diff purity.

Canonical:
[FIRST_PARTY_SEAM_POLICY.md](FIRST_PARTY_SEAM_POLICY.md).

## 2026-09-19 H-078 Upstream Migration as Decoupling — ACTIVE STRATEGIC LANE

The fork remains at `main@378b5a2df35ac05fe37a606298502d7bb974786d` while the
upstream continues to advance. The architecture decision is now settled: **the next
upstream migration must also reduce Workstation coupling**.

The Workstation will use Hermes as the first-party laboratory/reference agent while moving
toward a Workstation-owned runtime boundary. Generic Hermes core should not need
Workstation-specific knowledge. Instead, Workstation will consume generic lifecycle,
middleware and provider surfaces to observe and supervise normal Hermes behavior.

Current code audit confirms direct inward seams that must be retired progressively:
`agent/conversation_loop.py`, `agent/tool_executor.py`,
`agent/turn_finalizer.py`, and `tools/browser_tool.py` directly import Workstation
behavior. Product-edge integrations in Web/Kanban/Desktop are lower-priority adapter
boundaries rather than equivalent core coupling.

A key feasibility finding is that both the current fork and modern upstream already expose
generic `pre_tool_call/post_tool_call`, `pre_verify`, API request/response lifecycle and
behavior-changing `tool_request/tool_execution` and
`llm_request/llm_execution` middleware. These are the preferred bridge for a
Workstation-owned supervisory adapter.

Immediate H-078 work:
1. freeze one upstream SHA when migration execution starts;
2. generate seam inventory with `workstation/scripts/audit_hermes_seams.py`;
3. classify every overlap as ADOPT_UPSTREAM / KEEP_WORKSTATION / SEMANTIC_PORT /
   EXTRACT_BOUNDARY;
4. run new supervisory paths in shadow before removing old direct seams;
5. prove ordinary Hermes tool use remains supervised even when the model never calls
   `work_execute`.

Canonical:
[UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md](UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md).

## 2026-09-19 H-077.1 Truthful Core Qualification Closure — IMPLEMENTED / QUALIFIED

## 2026-09-19 H-077 Architectural Falsification / External Validity — QUALIFIED

Audited main: `92a3acb51e87af85a9f380ee04d2cf47d7900ca5` after PR #36.

Current classification: **H-077 core implemented / qualification partial**. Post-merge
falsification reproduced: ACK -> terminal completion through TaskCompiler; contract-
backfilled evidence provenance; unenforced task/run lineage; fail-open/diagnostic-only
ValidityEnvelope; optimistic external denominators without oracle coverage; AFB-v0
hand-labelled aggregation instead of a fully generated hidden-oracle harness; incomplete
automatic model-inadequacy integration; and optimistic success/replay accounting.

Canonical corrective plan:
[H077_1_QUALIFICATION_CLOSURE_2026-09-19.md](H077_1_QUALIFICATION_CLOSURE_2026-09-19.md).

PR #36 receipts remain useful regression evidence but no longer authorize a full
QUALIFIED claim.

## 2026-09-19 H-076 Verification Contract Synthesis — IMPLEMENTED & QUALIFIED

The post-PR #33 audit established the H-076 verification-semantics gap. PR #34 then
implemented the typed VerificationContract/VerificationResult path, conservative
admission, discriminative validation and verifier synthesis. Those pre-H-076 findings
remain historical rationale, not the current open boundary. The current open boundary
is H-077, documented above.

H-075 remains implemented and qualified as a handoff mechanism. H-076 now strengthens
the truth contract it consumes. Evidence: 109 focused tests; full Workstation
regression **670 passed, 2 skipped in 287.52s**.

Canonical:
[VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md](VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md).

## 2026-09-19 H-075 in-flight operationalization — IMPLEMENTED & QUALIFIED (Phases P0–P6 Passed)

The In-Flight Operationalization Handoff Gap (KI-014) and remaining operational knowledge hierarchy seams (KI-013) are fully closed and verified across Phases P0–P6:
1. **P0 (Truth Seams & Contracts):** Route decision branches strictly use real dataclass fields; composition requires authoritative final-goal verification; conservative derivation fails closed on incompatible families or unproven authority origins.
2. **P1 (RunClosureProof & Utility):** 21 canonical fields, 10 admission conditions in `evaluate_run_local_closure()`, positive expected operational utility threshold.
3. **P2 (Adaptive -> Compiled Handoff):** Synthesizes `ExecutionEnvelope` and transfers remaining batch to `DurableBatchRunner` without LLM re-entry; `RunScopedCapability` excluded from global promoted index; `recover_verified_prefix()` recovers committed items and prevents duplicate mutation replays.
4. **P3 (Browser Lowering & Artifact Data Plane):** Opaque `browser_console` marked non-replayable and rejected from candidate steps; rich editor lowered to `browser_type` with `plain_text_paste`; `resolve_browser_type_text()` resolves `text_ref`/`artifact_ref` at trusted boundary enforcing task ownership, <=1MB size, and text/json MIME.
5. **P4 (Durable Invocations & Causal Hierarchical Promotion):** Invocations persisted to `ArtifactStore` and `ExecutionJournal` with lineage; `load_invocations()` verifies pins/drift across restarts; composite mining marks candidate as `DISCOVERED` and requires `ExperiencePromotionPolicy` causal replay for promotion.
6. **P5 (Non-Resident Await & Production Telemetry):** `WaitDecision` creates `AwaitCondition` + `AwaitContinuation` in `AwaitConditionStore`, releasing worker processes (`worker_released=True`); `ORAMetrics` and `ORAMetricsCollector` wired into `OperationalKernel` and `TaskCompiler` recording real execution events.
7. **P6 (Trello-Shaped Benchmark):** 12-item benchmark passing end-to-end with canary + replay, handoff of 10 items, large artifact resolution, deliberate anomaly handling, recovery prefix, and clean resume without duplicate replays.

Evidence: 21 in-flight operationalization tests passed (100%); full workstation suite: **647 passed, 2 skipped in 287.92s**.

Canonical:
[IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md](IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md).


## 2026-09-19 H-071 corrective candidate — LOCAL GATES GREEN / EXACT-HEAD CI PENDING

P0-A..H are implemented on `codex/browser-operational-admission-closure` from clean
`main@6328894c0a5f51a61da772593842c25d377d553f`. Canonical owners remain unchanged.
Evidence: Workstation 607 passed / 2 skipped; Electron 1791 passed / 5 skipped;
typecheck, H004, H013 2/2, Work100 30/30 and integration dry-run green. Exact-head CI
remains the final qualification gate.

## 2026-09-19 Hierarchical Operational Learning — COMPONENT BASELINE LANDED & SEAMS CLOSED [H-075]

All remaining integration seams from PR #32 and post-merge audit are closed and verified via H-075 (Phases P0, P4, P5):

1. **P0 (Truthful Control Plane Closure):**
   - Added `certificate_hash()` to `CompositionCertificate`;
   - Hardened `CertifiedDispatcher.dispatch()` to fail closed (`NEEDS_VERIFICATION`) unless
     a verifier or explicit ACK-only acceptance contract is provided;
   - Real sequential child execution through `OperationalKernel` in `TaskCompiler._execute_route`
     without synthetic wildcard authority minting;
   - Gated `REQUIRE_COMPILE` in `execution_policy.py` on full operational closure, narrowing
     broad terminal command families (`terminal:python:-m`, `terminal:bash:-c`).

2. **P1 (Experience Compiler <-> Capability Router Bridge):**
   - Extended `Provenance` with `authority_ref` and `authority_scope`;
   - Implemented conservative deterministic `CapabilityFormalContract` derivation from
     verified experience in `promotion.py` and `compiler.py`;
   - Decoupled semantic identity with `family_id = f"{op_family}:{target_family}"`;
   - Rebuilt router index dynamically so `OperationIntent -> CapabilityRouter` routes to
     promoted learned capabilities, issuing a `RoutingCertificate` without LLM calls.

3. **P2 (Non-Resident AwaitCondition):**
   - Implemented `AwaitContinuation` holding durable subgraph, pins, and plan metadata;
   - Hardened `TriggerCoordinator` with run_id, task_id, and operation_id fencing;
   - Enforced "EVENT WAKES. AUTHORITATIVE STATE CONFIRMS." — false wakes reject resumption;
   - Atomic cleanup: conditions are only removed from store after resumption confirmation;
   - Classified external semantic waits (`is_non_resident_wait`) to release worker processes.

4. **P3 (Hierarchical Experience Compiler):**
   - `OperationalKernel` records `CapabilityInvocation` upon verified execution;
   - Created `HierarchicalExperienceCompiler` to mine recurring sequences across runs;
   - Validated causal JOIN, authority JOIN, and verifier closure;
   - Emits composite `OperationalCapability` preserving child dependencies (no flattening);
   - Drift propagation: quarantined or drifted children strictly block composite execution.

5. **P4 (Operational Reasoning Amortization Metrics):**
   - Implemented `ORAMetrics` with `ora_ratio`, `composite_reuse_rate`, `wait_non_residency_rate`,
     `wake_llm_rate`, and `WakeReason` breakdown;
   - Preserved `None` / `null` for unknown denominators and unmeasured metrics.

Evidence: Full workstation test suite passed (620 passed, 2 skipped, 0 failed in 235.36s).

Canonical reference:
[HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md](HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md).


## 2026-09-19 Browser Ownership & Recovery Reconciliation — IMPLEMENTATION LANDED / POST-IMPLEMENTATION AUDIT REOPENED

The 2026-09-18 implementation materially improved Browser ownership/recovery and its
focused regressions remain valid evidence. It is **not yet fully product-qualified**.

Landed baseline:
- `preferredTaskId` is plumbed through renderer/preload/IPC/runtime;
- host fencing protects `detach` and `setVisible` from cross-host stale cleanup;
- task-bound lazy recovery can materialize restored task tabs before the runtime's
  final blank fallback when a preferred task is already known;
- Chat without an owned task no longer silently inherits another session's task tab;
- Browser Hub projects execution activity separately from viewport visibility;
- tooltip popper wrappers no longer independently trigger the original hover flicker.

Post-implementation audit findings on
`main@6328894c0a5f51a61da772593842c25d377d553f`:
- **bulk clear mismatch:** TaskRail can classify `parked + working` correctly, but
  runtime `clearParkedTasks()` still destroys every parked task, so a visible Clear
  action enabled by one idle parked task can also destroy another working/waiting/
  human-controlled parked BrowserTask;
- **cold-mount blank window:** `WorkstationBrowserPane` begins with empty local
  Browser state, so its first attach can occur without `preferredTaskId`; the
  renderer may briefly attach/create an unowned `about:blank` before the returned
  task list triggers the second, task-bound attach;
- **qualification gap:** current H013 does not yet exercise the required real
  renderer restart flow and its local bridge type still omits `preferredTaskId`;
- **alias proof gap:** BrowserPane resolution is proven for live/root lineage but does
  not explicitly cover `parent_session_id` as a behavioral contract;
- **occlusion contract remains broader than intended:** generic roles/slots still have
  Chromium-hiding authority alongside `data-native-view-occluder="true"`;
- **global main is not fully green:** Workstation contract tests pass, but the
  separate Browser Operational Admission lane currently fails
  `apply_core_integration.py --check` on the `browser_type` anchor. This does not
  invalidate the ownership implementation, but it makes any repository-wide
  "100% regressions green" wording false.

Prior evidence retained, not treated as final closure: 88 focused Vitest tests,
Desktop typecheck, H004 and Work100 30/30.

Current classification: **corrective P0 open** until the renderer/restart E2E,
execution-aware cleanup and alias/occlusion contracts pass on the candidate head.

Canonical reference:
[BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md](BROWSER_OWNERSHIP_RECOVERY_RECONCILIATION_2026-09-18.md).


## 2026-09-19 Browser Operational Admission / Primitive Closure — IMPLEMENTATION LANDED / AUDIT REOPENED / QUALIFICATION BLOCKED

PR #29 (`main@24997c9af8256ac41001bdee9f827c643d5598e4`) landed real improvements:
explicit read effects, action-sensitive effect resolution, structural-only admission
relief, native plain-text paste, GET/HEAD Browser readback, authority narrowing,
effect-sensitive timeout uncertainty and bounded SPA re-observation. Those pieces remain
part of the current implementation.

A post-merge code/CI audit found that the stronger P0 invariants are **not yet closed**:

- `TaskCompiler._execute_route()` can handle `ComposedDecision` by dispatching a
  lambda that only returns `{"success": True, "plan": [...]}`; the plan can therefore
  be labeled successful/COMMITTED without executing its capabilities.
- `CertifiedDispatcher.dispatch()` initializes verification as true and treats a
  successful tool result as verified when no `verifier_fn` is supplied. This
  collapses ACK into verification and violates the E0-E3 evidence boundary.
- effective authority can still be synthesized from request `trusted_authority` or,
  when only task/session context exists, from broad
  `EXTERNAL_REVERSIBLE + allowed_actions={"*"} + allowed_resources={"*"}` defaults.
  Bare session/task existence is not a trusted grant.
- `execution_policy.py` still reaches `REQUIRE_COMPILE` from semantic repetition
  count alone. D-021 requires executable deterministic closure, verifier/readback,
  authority/policy compatibility and certified dispatch in addition to homogeneity.
- native `browser_read_http` is not yet same-origin-by-default/policy-gated, uses
  hand-rolled destination checks that do not cover the full canonical URL-safety
  surface, and the Python wrapper can fall back to process-level `requests.request`,
  which is not authenticated Browser-session readback.
- `terminal:<program>:<second-token>` families remain too broad for mandatory
  compilation of arbitrary command execution.
- the PR #29 focused/local suites are useful evidence, but exact-head GitHub Actions
  qualification is not green: both Workstation CI and Workstation Browser Windows
  failed `workstation/scripts/apply_core_integration.py --root . --check` with
  `ERROR: browser tool route anchor missing for browser_type`. Several later Windows
  product gates were skipped as a consequence.
- the current "dogfood" Browser proof is simulation-heavy; a real Electron/WebContents
  fixture is still required for rich editor paste, delayed hydration, same-origin
  authenticated readback, persisted verification and deterministic fan-out.

Current classification: **implementation base retained; P0 correction and product
qualification open**. Do not describe this milestone as CLOSED, fully contract-qualified
or 100% regressions green until the corrective gate in `TESTING.md` passes on the
exact candidate head.

Canonical P0:
[BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md](BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md).

Snapshot date: 2026-09-19.

The 2026-09-15 hardening snapshot below remains valid as implementation and test
history, but a 2026-09-17 forensic audit of current `main`, persisted Workstation
state and historical behavioral traces found a stronger cross-domain reliability
boundary that was not exercised by the existing green suites. The subsequent correction is
[ADAPTIVE_EXECUTION_COMPILATION.md](ADAPTIVE_EXECUTION_COMPILATION.md),
which now has implementation/contract evidence and retains a native qualification gate.

This file describes **observed implementation state**, not target architecture.
When it disagrees with code on current `main`, inspect the code and update this
file. “Implemented”, “contract layer validated” and “tests green” do not imply that
a product-level causal invariant has been proven across Task -> Run -> operation ->
evidence -> canonical commit -> projection.

## 2026-09-18 Verified Operational Control Plane (CP0–CP9) — IMPLEMENTED / CONTRACT VALIDATED

The Verified Operational Control Plane is implemented and verified across Python and Workstation layers.
See [VERIFIED_OPERATIONAL_CONTROL_PLANE.md](VERIFIED_OPERATIONAL_CONTROL_PLANE.md) for full specification and contract evidence.

`workstation/control_plane/` implements the deterministic executability proof engine and capability router:
- CP0: Typed Predicate AST, Effect AST, algebraic entailment (`entails`), effect containment, invariant preservation, and immutable `OperationIntent`.
- CP1: `CapabilityFormalContract` and library indexing by family/target (`OperationalCapability.formal_contract`, `family_id`).
- CP2: `CapabilityRouter` enforcing `NO VALID CERTIFICATE -> NO DISPATCH` via 15 proof obligations in `RoutingCertificate`.
- CP3: Bounded backward chaining with search budgets and causal threat detection (`detect_causal_threats`).
- CP4 & CP5: Typed `AwaitCondition`, persistent `AwaitConditionStore`, run-fenced `TriggerCoordinator`, `TriggerCircuitBreaker`, and `CertifiedDispatcher`.
- CP6: Minimal `OpenCondition` and `AttentionPacket` for bounded reasoning handoff without prompt bloat.
- CP7: Authoritative semantic state synthesis.
- CP8: `ShadowRouter` (0 mutations dispatched), `FailureAttributor` (7 failure classes), and `VOLCMetrics` (Verified Outcome Lifetime Cost).
- CP9: `TaskCompiler` and `tools/workstation_work.py` route integration.

36 dedicated control plane tests in `workstation/tests/` pass with 100% green status, with all regression suites green.

## 2026-09-18 Experience Compiler / Verified Operational Transitions — IMPLEMENTED / CONTRACT VALIDATED

The Experience Compiler now emits the existing OperationalCapability format from
bounded, semantically normalized experience. See
[EXPERIENCE_COMPILER.md](EXPERIENCE_COMPILER.md) for the specification and evidence.

`workstation/experience_compiler/` implements semantic before/after deltas,
artifact-derived corpus, segmentation/alignment, typed anti-unification and
relations, conservative action models with failures, reverse dependency slices,
causal grades, safe interventions and immutable refinement. Causal support and
effect evidence remain distinct. Exact replay uses the existing kernel without
operational-planning LLM calls.

Verified canonical completion mines candidates after commit. Derived anchors
participate in the capture fingerprint and replay requires unique exact semantic
identity. Learned success counts never grant promotion; independent admission
checks provenance/taint, C/E evidence, risk, diversity, drift and reuse utility.
TaskRun pins live in existing WorkPlan metadata; durable checkpoints prevent blind
replay after uncertain dispatch. Historically promoted learned contracts remain
immutable even after quarantine.

Validation covers browser, real temporary files, a real subprocess, a learned
cross-backend composite and two compositions reusing one learned atomic capability.
Interventions require owner-supplied isolated fixtures and bounded deadlines.
Default adaptive provenance remains observational and cannot auto-promote mutation.
Global coverage/novelty and paid-provider savings remain unknown, not estimated.
Native Desktop qualification is separate; see TESTING.md for exact gate status.

The Capability Runtime must be extended, not rebuilt. Existing TaskRun,
BrowserTask, ArtifactStore, ExecutionJournal, RecipeStore, ProceduralMemory,
OperationalCapabilityRegistry/Resolver, Operational Kernel, approvals,
uncertainty/reconciliation and canonical completion ordering remain owners.

## 2026-09-18 Progressive Operational Compilation & Operational Capability Runtime — IMPLEMENTED & VERIFIED

The deterministic capability-runtime substrate specified in
[PROGRESSIVE_OPERATIONAL_COMPILATION.md](PROGRESSIVE_OPERATIONAL_COMPILATION.md)
is implemented, verified, and integrated across Python and Electron layers.
It establishes the execution side of the progression: semantic operation identity,
OperationalCapability lifecycle/registry/resolver, Operational Kernel,
composition, direct/automatic exact reuse and zero-LLM deterministic replay.
The automatic trace-to-capability Experience Compiler layer is now implemented
and contract-validated in
[EXPERIENCE_COMPILER.md](EXPERIENCE_COMPILER.md). The next milestone is the
verified intent/router/await control plane.

Key implementations and verified invariants:
1. **AEPC-E002 Resolved (`workstation/execution_policy.py`, `workstation/batch_detection.py`, `workstation/procedure_trace.py`):**
   - Separated structural AST similarity (`structural_signature`) from semantic identity (`semantic_operation_fingerprint`, `semantic_target_family`).
   - Ephemeral DOM references (`@eN`) never constitute semantic identity. Unknown/ephemeral targets remain bounded `ALLOW_ADAPTIVE` / `SUGGEST_COMPILE` without escalating to `REQUIRE_COMPILE`.
   - Refused calls previewed in `decisions_for_calls()` never increment mutation dispatch counters.
   - `REQUIRE_COMPILE` strictly demands positive semantic homogeneity and verified successes (`verified_successes >= 3`), never triggering on exploratory `executed_unverified` turns.
2. **Native Browser Semantic Contract (`apps/desktop/electron/workstation-browser-runtime.ts`):**
   - `inventoryScript` extracts `testid` (`data-testid`, `data-test`, `data-qa`), `name`, `role`, `tag`, `label`.
   - `snapshotForEntry` returns structured `elements: Array<ElementTargetMetadata>` alongside formatted textual snapshots.
   - `pointScript` / `resolvePoint` extracts element target metadata (`ref`, `tag`, `role`, `name`, `testid`, `label`) before CDP dispatch.
   - `dispatchAction` for `browser_click` and `browser_type` returns `target` metadata and `semantic_effect` (`click`, `type`).
3. **Operational Capability Abstraction (`workstation/operational_capabilities.py`):**
   - `OperationalCapability` data model with semver, preconditions, postconditions, dependencies, input/output schemas, and lifecycle (`DISCOVERED`, `VALIDATED`, `PROMOTED`, `RETIRED`).
   - `OperationalCapabilityRegistry` backed by existing `ArtifactStore` and atomic index file. Reuses existing storage without creating duplicate stores.
   - `CapabilityResolver` with cycle detection (`CapabilityCycleError`), depth bounds (`CapabilityDepthExceededError`), and topological linearization.
4. **Deterministic Operational Kernel (`workstation/operational_kernel.py`):**
   - Filesystem primitives (`stat`, `read`, `write`, `patch`, `copy`, `move`, `hash_file`, `list_dir`, `mkdir`).
   - Browser primitives (`navigate`, `snapshot`, `click`, `fill`, `press`, `scroll`, `wait`, `extract`).
   - Dotted variable interpolation (`$inputs.<var>`, `$deps.<id>.<var>`, `$prev.<var>`).
   - Precondition & postcondition verification.
   - Drift quarantine and reasoning handoff via `workstation.reasoning_handoff.needs_reasoning`.
   - Zero LLM tokens paid on deterministic replay.
5. **Durable Task Integration (`tools/workstation_work.py`, `workstation/task_compiler.py`):**
   - `work_execute` schema expanded with `capability_id`, `capability_version`, `capability_inputs`.
   - `TaskCompiler.execute` supports direct execution by `capability_id` and automatic reuse of promoted capabilities via `operation_fingerprint`.

Verified test suites:
- `workstation/tests/test_execution_policy.py`: 11 passed (including 4 AEPC-E002 regression tests).
- `workstation/tests/test_operational_capabilities.py`: 12 passed.
- `apps/desktop/electron/workstation-browser-runtime-task.test.ts`: 26 passed.

Verified recipe selection is automatic by exact compatibility; promoted routines
with structured semantic conditions lower into existing WorkItem checkpoints.
Adaptive observations enter the existing artifact/journal owners during dispatch;
canonical acceptance can seed a versioned candidate, not automatic promotion.
Unknown effects remain mutating, native snapshot is E1 rather than persisted
readback, and outstanding mutable dispatch cannot blind-resume.

Final gate: 570 passed / 2 skipped in 346.25s across all Workstation tests and 79
adjacent executor/guardrail tests. Work100: 30 PASS / 0 FAIL / 0 gaps. Desktop
owner contracts: 36 passed. Focused gate: 113 passed before the final additional
snapshot-strength regression (included in the full gate). No TS product source
changed. Native Electron executable and built main bundle were absent, so no
authenticated native/packaged browser smoke or paid-provider savings is claimed.
See TESTING.md and the current engineering journal for commands and failure history.

## 2026-09-18 upstream reliability hardening — IMPLEMENTED AND CONTRACT VERIFIED (P0 LANE)

A direct PR-to-current-code comparison on `main@03e06cfd8c94e5a7627c288c8eddfd5d4c5c8033`
confirmed a second, compatible reliability lane. All confirmed P0 gaps have now been
implemented, tested with strict RED/GREEN regression suites, and verified on branch
`fix/workstation-upstream-reliability-p0`.

**Implemented and verified P0 resolutions:**

- **#114964 / P0.0 (Native Browser Keepalive Truth):** Hardened
  `workstation/context/engineering-journal/probes/h004-native-browser-task-smoke.mjs`
  with deterministic discriminators: live `webContents` id preservation, continuous
  JS timer advance, input value retention, scroll position survival across `hide -> show`
  and `park -> show`, and loopback controller snapshot action execution.
- **#115068 / P0.1A (In-Flight Turn Journal Tail):** Fixed `apps/desktop/src/lib/inflight-turn-journal.ts`
  to select the true live projection tail using `findLastIndex` and deduplicate sealed
  interim stream rows with `withoutBaseIds`. Verified with 39 vitest tests.
- **#115085 / P0.1B (Optimistic Message Resync):** Composed `preserveLocalPendingTurnMessages`
  into `use-background-sync.ts` (`reconcileActiveTranscript` and `reconcileTileTranscript`)
  and `wiring.tsx` to preserve unacknowledged user turns across background resyncs until
  authoritative gateway ACK. Verified with 17 vitest tests.
- **#111493 / P0.2 (One Canonical Session Writer):** Hardened `hermes_cli/active_sessions.py`
  and `cli.py` to enforce single live writer exclusivity per `session_id`, support
  read-only observer resume (`mode="observer"`), fence lease transfer against foreign
  live writers, and fail-closed (`RegistryUnreadableError`) on unreadable registries.
  Verified with 7 tests in `tests/hermes_cli/test_cli_resume_read_only_owner.py`.
- **#114785 / P0.3A (Kanban Session Provenance):** Validated session provenance against
  persisted SessionDB (`state.db`), prioritized request-scoped `HERMES_SESSION_ID`
  ContextVar over ambient environment, and rejected dangling session IDs from persistence.
- **#114793 / P0.3B (Worker Heartbeat Fence):** Hardened `tools/kanban_tools.py` so
  `heartbeat_current_worker_from_env` requires both claim extension and worker heartbeat
  writes to persist, and fenced delegated children from heartbeating parent workers.
- **#114904 / P0.3C (Durable Worker Exit Evidence):** Added `HERMES_WORKER_EXIT_TRAILER_V1`
  formatting and parsing in `hermes_cli/kanban_db.py`, emitted trailers in `cli.py`,
  and enabled topology-independent fallback classification in `_classify_worker_exit`.
  Verified with 7 tests in `tests/hermes_cli/test_kanban_provenance_and_exit_evidence.py`.
- **#114897 / P0.4 (Bounded CDP Reconnect):** Capped post-attach reconnect attempts in
  `tools/browser_supervisor.py` at `MAX_POST_ATTACH_RECONNECT_FAILURES = 5`, evicted
  exhausted supervisors from `SUPERVISOR_REGISTRY`, and redacted credentials in logs.
  Verified with 3 tests in `tests/tools/test_browser_supervisor_reconnect_cap.py`.

**Remaining lane status:**
- P1 lane (Durable Delivery Rail and snapshot quality/freshness benchmark) remains
  planned following P0 review.

Canonical plan:
[UPSTREAM_RELIABILITY_HARDENING_2026-09-18.md](UPSTREAM_RELIABILITY_HARDENING_2026-09-18.md).
Engineering evidence: H-065 and H-066 in
[engineering-journal/CURRENT.md](engineering-journal/CURRENT.md).

## 2026-09-17 forensic reliability audit — current boundary

The audit changes the interpretation of the existing implementation without
invalidating the many mechanisms that are already useful.

### Resolved and Verified Invariants (Canonical Execution Reliability Gate)

- **Run Fencing Enforcement:** `workstation/kanban.py::complete_task_with_report()` now requires and enforces `expected_run_id` CAS checks against `tasks.current_run_id`. Stale runs are rejected immediately before acceptance evaluation or mutation, preventing concurrency violations and state corruption.
- **Canonical Commit Before Journal:** `TASK_COMPLETED` is only recorded in `ExecutionJournal` after the canonical completion commit succeeds in SQLite. On CAS failure, an `acceptance_commit_failed` event is recorded and `False` is returned.
- **Canonical Lineage:** `ExecutionEvent`, `BrowserTaskReport`, `TaskOutcome`, and `EvidenceRef` carry first-class `run_id` and `operation_id`.
- **Plan Lineage & Execution Key:** `WorkPlan` and `WorkItem` persist canonical `run_id`, separate `execution_key`, and `operation_id` via additive schema migrations.
- **Database Connection Portability:** `hermes_cli.kanban_db.connect(db_path=...)` normalizes `Path(db_path)` supporting both `str` and `Path`.
- **Terminal Tree Consistency:** `DurableTaskStore.update_plan_state` cascades terminal parent states (`interrupted`, `failed`, `cancelled`, `blocked`) to mark all live descendant items as `blocked`. `reconcile_terminal_plans()` provides startup and periodic reconciliation sweeps.
- **Human Takeover & Fencing:** `BrowserControlLeaseManager` generates monotonic lease generations and `fence_token`s. Takeover revokes agent mutation authority (`browser_click`, `browser_type`, `navigate`, `submit`, etc.), and rejects stale fence tokens from previous runs.
- **Constant-Time Journal Chaining:** `ExecutionJournal.append()` operates in $O(1)$ constant time via `_get_last_record()` without parsing entire files, verified by a 120-event streaming benchmark.
- **Cockpit Auditability:** `task_cockpit()` exposes full canonical lineage (`run_id`, `execution_key`, `operation_id`, `workplan_id`, `human_card_id`, `acceptance_status`, `acceptance_approved`).

### Existing mechanisms that must be reused, not rebuilt

- TaskCompiler canary-before-fan-out, mutation verifiers, idempotency contracts,
  dispatch checkpoints, recipe staleness/quarantine and uncertain-mutation
  escalation;
- canonical Kanban Task/TaskRun state and CAS transitions;
- BrowserTask and scoped human-control leases;
- EvidenceState, RuntimeEventBus, RuntimeSupervisor and RecoveryPlane;
- WorkerRegistry and host capability adapters;
- Execution Journal and artifact/reference plane;
- Hybrid Human Card -> Agent Task delegation with separate lifecycles;
- existing compaction, routine promotion, no-progress and evaluation machinery.

### Current architectural interpretation

`One Hermes State` means **one authority per domain + shared causal identity +
explicit lineage + reconcilable projections**, not one physical SQLite database.
The immediate work is to make TaskRun and operation identity flow through the
existing owners and to enforce canonical commit/acceptance ordering.

## Working now

On `main` plus the current Workstation V3 hardening working tree:

- Hermes Vault rejects cross-platform absolute/traversal paths before side
  effects, excludes symlink escapes, writes atomically, and shares one bounded
  process-wide manager/watcher between agent tools and Desktop plugin RPC.
- Workstation Chromium advertises the actual `process.versions.chrome` engine
  without Electron/Hermes product tokens.
- Desktop display/installer/shortcut naming is `Hermes Work`; update identity,
  `hermes://`, executable/artifact naming, AUMID and the historical `Hermes`
  userData directory remain stable for upgrades.

- Hermes Workstation is first-class in this downstream fork and Desktop exposes
  the built-in `/browser` route.
- The internal browser uses Electron Chromium through `WebContentsView` and a
  dedicated persistent Electron session/profile outside the repository.
- Navigation, ordinary tabs, task-owned tabs, background parking, pause/resume,
  focus and human/agent control primitives are implemented.
- The Workstation controller is loopback-bound and bearer-token authenticated.
- `browser_*` prefers the Workstation controller before allowed fallback and
  remains fail-closed after task binding.
- Desktop Browser schema capability is session-scoped and protected from
  process-global reachability/cache leakage.
- Contextual Chat Browser View (`WorkstationBrowserPane`), global Browser Hub (`BrowserView`),
  and single-host Viewport Transfer (`transferViewport`).
- Host-aware viewport geometry propagation rejects stale resize updates from a
  non-owner Chat/Hub pane while preserving Chromium zoom/clamp normalization.
- Live Task Rail (`TaskRail`) with task grouping (`active`, `waiting-for-human`, `background`, `recent`),
  individual task deletion, and clearing parked tasks.
- Responsive zoom DIP scaling ensuring Chromium viewport aligns flush with the UI window.
- Persistent Kanban (`kanbanCardId`) and run (`runId`) identity bindings with fail-closed enforcement in covered paths; the 2026-09-17 audit shows Run continuity is not yet universal across Workstation completion/contracts.
- Automatic multistep Kanban promotion, follow-up discovery with parent blocking, append-only
  Execution Journal (`ExecutionJournal`), and structured completion reports.
- Fail-closed LAN and Tailscale controller with auth preflight and network detection.
- V1.1 Multi-task scheduler (`MultiTaskScheduler`) enforcing the one-live-host invariant, with lease timeouts, heartbeats, and orphan task reaping.
- V2 Procedural Web Memory (`ProceduralMemory`) with dynamic intent discovery, reinforcement, and resilient multi-facet fallback anchoring (testid -> role -> text -> selector).
- V2 Compact Provenance-Aware Perception Engine (`PerceptionEngine`) with Lattice-inspired node summaries, hidden node filtering, and tiered smart budgeting that guarantees CTA preservation.
- V2 Drift Diagnosis & Governed Adaptation (`DriftGovernor`) with blocking cookie/modal overlay detection (`DISMISS_OVERLAY`) and strict financial/irreversible action boundaries.
- V2 Lightpanda headless stateless runtime adapter (`LightpandaAdapter`) with transparent gzip/deflate decompression and fail-closed auth redirect detection.
- Windows Filesystem atomic resilience in Electron session persistence (fallback on `EPERM`/`EBUSY` via `copyFileSync`).
- Desktop UIX additions: high-contrast attention styling for human intervention in `TaskRail` and interactive Downloads drawer in `BrowserView`.
- **V2.1 Chrome Web Store Extensions**:
  - `ChromeExtensionManager` in `workstation/extensions.py` with official Chromium update endpoint CRX downloader (`clients2.google.com/service/update2/crx`).
  - Native ZIP/CRX unpacking with `Cr24` header stripping into `~/.hermes/workstation/extensions/<id>/`.
  - Automatic loading in Electron Chromium via `session.loadExtension(..., { allowFileAccess: true })`.
- **V2.5 Agent Runtime & System Capability Control Plane**:
  - `WorkerRegistry` in `workstation/workers.py`: discovery, readiness, and bounded subtask delegation for Codex, Claude Code, Antigravity, OpenCode, and K-Tools-Neo while retaining canonical Hermes task/session/card lineage in `ExecutionJournal`.
  - System Capability Layer in `workstation/host.py`: `HostCapabilityProvider` contract with `WindowsHostCapabilityProvider`, `LinuxHostCapabilityProvider`, and `KToolsNeoCapabilityAdapter`.
  - System Event -> Hermes Task Pipeline in `workstation/events.py`: `SystemEventPipeline` converting system/host events into Kanban tasks or task enrichments.
  - Scoped Autonomy Policy Engine in `workstation/policy.py`: `ScopedPolicyEngine` evaluating actions across `ALLOW`, `SANDBOX`, `REQUIRE_APPROVAL`, `DENY` with auditable decision logs.
- **V3 Cross-Platform Agentic Workstation**:
  - Omarchy Linux reference host adapter in `workstation/omarchy.py` with launcher normalization and system skills.
  - `CrossPlatformHostManager` in `workstation/cross_platform.py` unifying capabilities across Windows and Linux.
  - `AgenticBenchmarkRegistry` tracking 8 major agentic environments (Omarchy, Hermes upstream, OpenHands, OpenCode, Claude Code, Codex, Antigravity, BrowserOS) against core architectural criteria.
- **V3.1–V3.4 runtime-hardening contract layer**:
  - `EvidenceStateStore`, bounded `RuntimeEventBus`, typed resources, deadlines,
    cancellation, human handoff and budget/model routing in `workstation/runtime.py`.
  - Independent child-process `RuntimeSupervisor`, checkpoint rollback,
    `RecoveryPlane` and dependency-light `recovery_cli.py`.
  - Versioned routine promotion/replay, persistent WorkerRegistry queue/control,
    temporal memory/snapshots, session ownership/migration/compaction,
    portable replay/fork, protocol adapters, isolation and evaluation gates.
  - Persistent worker results use a durable envelope/ACK handoff over the
    existing worker record: an executor result is persisted before it is
    journaled or published, unread results survive reconstruction, and claimed
    work remains explicit recovery work when persistence cannot be confirmed.
    Large spillover results are content-addressed within task scope and expose
    a reference-first metadata contract without becoming an argument-only
    execution cache.
  - Shared resource/event client boundary: Electron BrowserTask/page ownership
    publishes versioned `/resources` and bounded `/events` projections; Desktop
    IPC, Dashboard REST and TUI JSON-RPC consume the same read-only contracts,
    with controller loss represented as degraded state and control permissions
    failing closed.
- **Chat / Browser UX Hardening & WhatsApp Web Compatibility**:
  - Runtime-derived Chromium User-Agent (`getStandardChromeUserAgent(process.versions.chrome)`) in `apps/desktop/electron/workstation-browser-runtime.ts` across `browserSession.setUserAgent()`, `webRequest.onBeforeSendHeaders`, and `WebContentsView` instances; it preserves the platform token without exposing `Electron` or `Hermes` and cannot age behind a hardcoded Chrome version.
  - Session-scoped preview/browser pinning via `$sessionPreviewTabs` in `apps/desktop/src/store/preview.ts`: creating a new chat session presents a clean workspace with no lingering lateral panels from prior sessions, and switching back seamlessly restores that session's browser panels.
  - Browser Hub lateral rail suppression: `isBrowserHubRoute()` in `preview.ts`, layout effect in `apps/desktop/src/app/browser/index.tsx`, and event filtering in `use-preview-routing.ts` eliminate dual-rail collision when visiting `/browser`.
  - Friendly automatic task names in Browser Hub: `TaskRail` resolves chat conversation titles (`s.id === task.sessionHost || s.parent_session_id === task.sessionHost`) and page tab titles/domains, replacing raw task IDs with meaningful human context.
- **Hybrid Kanban Real-time Invalidation & Full Lifecycle (H-053)**:
  - Canonical domain functions `delete_card`, `delete_column`, `delete_board`, and `get_board_activity` in `hermes_cli/hybrid_kanban.py` with dense reindexing.
  - Realtime WebSocket invalidation over `/events`: emits `hybrid_events` and `hybrid_cursor` on mutation, prompting instant query invalidation in Desktop UI and eliminating the 8-second polling latency.
  - Desktop UI: horizontal column drag-and-drop reordering (`moveHybridColumn`), rich card activity drawer with human vs. agent provenance badges, and complete deletion lifecycle.
- **Human card → Agent Task delegation**: `delegate_card` creates a separate
  canonical Agentic task in the same Kanban database, persists the
  `human_card_id` ↔ `agent_task_id` link, projects compact status/result/evidence
  metadata, and keeps both lifecycles independent across restart and retry.
- **Hybrid Card checklists**: multiple checklists and ordered items live in
  additive `hybrid_*` tables in the canonical Kanban database. Completion,
  reorder and deletion enforce optimistic revisions, emit provenance through
  `hybrid_activity`, survive restart and are exposed in the existing Desktop
  card drawer.
- **Scoped human browser control**: `BrowserHumanControlLease` is owned by the
  bound `BrowserTask` and carries task/session/tab/page/profile scope, timestamps,
  renewal and expiry; stale leases are cleared during restore and never block an
  unrelated task.
- **Extension update safety**: `ChromeExtensionManager` stages updates behind a
  promotion journal and retains last-known-good content until Electron load and
  verification commit.
- **Operational compaction envelope and workload benchmark**: compaction retains
  bounded task/session/worker/browser/result/approval/evidence identifiers, and
  `workstation/benchmarks/workload_baseline.json` records deterministic structural
  counters without private databases or wall-clock thresholds.
- Automated contract coverage on the 2026-09-15 snapshot included **247/247 Workstation Pytests passing** and clean Desktop typecheck. These remain implementation evidence, not proof that the newly identified cross-domain invariants are closed.

### BrowserSessionState — promoted V1 #1

PR #11 accepted exact head `d5be442021ea0c744351622317eef5212219786d` and was merged as `e0a99ef3aba6e6d2b65c30cf3c908ee1d49c4d29`.
The exact-head native Windows/Electron probe emitted `H010_CLASSIFICATION=VALIDATED`.

## Partially implemented / reliability-hardening required

- Canonical TaskRun identity exists but is not yet propagated/fenced through every Workstation completion, event, evidence and effect boundary.
- Terminal WorkPlan/WorkItem tree consistency is not yet proven universally.
- External mutable-operation uncertainty/reconciliation is strong in TaskCompiler but not yet established as a universal Workstation effect invariant.
- Exact-once terminal projection from Agent Task into every journal/UI/Hybrid view still needs cross-restart regression evidence.
- Experimental non-Electron browser backends remain secondary fallbacks to the primary internal Chromium.
- External browser extensions operate strictly in unbound compatibility mode.

## Not implemented yet

- Autonomous multi-agent swarm arbitration across remote physical hosts without a local controller (long-horizon exploration beyond V3).

## Manual validation already observed

- H004 proved the promoted BrowserTask lifecycle with a real BrowserWindow,
  WebContentsView, renderer and two Windows/Electron processes.
- H010 on PR #11 exact head proved clean and abrupt two-process
  BrowserSessionState restart, profile separation, lazy exactly-one-page task
  recovery, failed-write convergence and explicit-destroy failure cleanup.
- A 2026-09-12 local rerun of the same versioned H010 probe passed on the
  current Windows/Electron toolchain and current working-tree product files;
  it remains explicitly classified as local dirty-tree evidence until the
  clean-checkout workflow gate runs.
- Native Electron dogfooding verified live Chromium rendering, synchronized chat right-rail,
  task deletion, and clear parked tasks in Browser Hub.
- The versioned V3 process-boundary smoke emitted
  `V3_RUNTIME_HARDENING_CLASSIFICATION=VALIDATED_CONTRACT_BOUNDARY`, proving
  independent child recovery, cross-process session ownership rejection and
  stale-evidence reconciliation on Windows 10.0.26200 / Python 3.13.
- The packaged Desktop headless boundary smoke covered the renderer, HUD,
  Desktop IPC and authenticated loopback controller for both resource and event
  projections; the exact packaged artifact passed **6/6** without revealing a
  native window.
- The hidden native H011 Browser runtime soak passed **39 process episodes / 936
  task cycles / 4 tasks** in 60 seconds, including real Chromium navigation,
  hub/chat host changes, hide/park transitions, resource lineage and composite
  restart persistence. It is explicitly bounded to the native runtime.
- The real headless H012 backend soak passed **12 cycles / 48 turns / 44
  reconnects / 2 backend restarts / 48 heartbeats**, with 192 streamed events,
  zero errors and four concurrent turns through the authenticated WebSocket
  gateway. It uses the deterministic synthetic-turn seam and does not claim
  real-provider quality or clean-machine release qualification.

## Known bugs / gaps

See `KNOWN_ISSUES.md` and the active reliability gate.

- The 2026-09-17 confirmed execution-identity/completion/journal contradictions are active P0 work even though the underlying subsystem tests are green.
- KI-003 is resolved by promoted BrowserSessionState.
- KI-002/KI-004 (Preview duplication and host overlap/ownership composition)
  are resolved by single-host viewport transfer and Workstation preview pane.
- KI-006 is resolved on the current working tree by the HW-018 Windows
  portability closure; the historical baseline comparison remains below as
  provenance, not as an open failure.
- KI-009 is resolved: the packaged Desktop GUI Playwright smoke passes after
  lazy Workstation Browser startup and per-sandbox state isolation.
- V3 product-level clean-machine release qualification, event/resource parity
  for future client surfaces and candidate-release confirmation of the
  full-duration/production-scale Desktop/Browser profile remain evidence
  gates; the Python contract layer does not silently promote those claims. The
  Chromium/Firefox/Edge Dashboard smoke is validated when the supported Edge
  browser is present. The read-only
  `python -m workstation.release_qualification` runner now requires a clean
  checkout, makes the local/native/migration gates reproducible and refuses to
  infer clean-machine evidence; the Windows workflow emits the candidate-
  matched external clean-install report with an isolated `RUNNER_TEMP`
  absolute `workstation_home` outside the checkout that install and doctor
  share.
- A local isolated candidate snapshot completed install, `npm ci`, Desktop
  production build, strict doctor, release qualification **6/6** and the
  hidden H013 profile (**2 passed in 3.2 minutes; 16 tasks, 173 rounds,
  120,262 ms, 8 chat turns**). This is stronger local evidence, but its
  synthetic candidate is not the official clean-machine CI gate.

## Latest automated validation state

The following results are retained as evidence for the implementation boundaries
they actually exercised; they do **not** close the 2026-09-17 reliability gate.

- **247/247 Pytest tests passed** across the earlier Workstation contract snapshot, LAN/Tailscale,
  Kanban/Journal, Procedural Memory, Perception Engine, Drift Governance,
  Lightpanda Runtime, Multi-Task Scheduler, Chrome Extensions, Worker Registry,
  Host Capabilities, System Events Pipeline, Scoped Policy, Cross-Platform/Omarchy
  and V3.1–V3.4 contracts.
- **Production dependency audit:** `npm audit --omit=dev --audit-level=moderate`
  passed with **0 vulnerabilities** after the lockfile-only refresh of the
  affected transitive packages.
- **Desktop typecheck passed with 0 errors** across app, Electron and E2E configs.
- **Desktop focused resource/runtime tests:** 20/20 passed; Dashboard typecheck
  and the Python resource-client tests also pass.
- **Dashboard cross-engine smoke:** Chromium, Firefox and the installed Edge
  browser all passed the provider-free `/workstation` route smoke (`3 passed
  in 9.2s`).
- **Canonical reconnect soak sample:** 3/3 fresh-process iterations passed with
  3 sessions, 0 failures, 36 journal events, 9 memory snapshots and 6 worker
  reconstructions, 6 model changes and 6 cold reloads; long-duration
  Desktop/Browser soak remains open.
- **Desktop UI suite:** 591 files / 5,669 tests passed with Vitest bounded to
  `--maxWorkers=4` on the current Windows audit host. The targeted messaging
  file also passed 8/8.
- **Desktop platform/Electron suite:** 126 files / 1,778 tests passed, 5 skipped.
- **KI-006 closure:** Windows path/permission/SSH/WSL/staging/locale contracts
  pass without disabling the broad suites.
- **Client parity boundary:** Dashboard REST and TUI JSON-RPC each read the
  same authenticated controller projection; the live HTTP adapter test passed
  with identical browser/task/journal identities, while H013 compares the full
  controller/Desktop IPC resource projection.
- **Event parity boundary:** Dashboard REST and TUI JSON-RPC each read the
  bounded event projection for the same task; the Electron runtime test covers
  canonical journal ordering and limits, while H013 compares the full bounded
  controller/Desktop IPC event payload.
- **Packaged projection/UI boundary:** the exact `win-unpacked` artifact passed
  the complete headless packaged GUI/HUD smoke (**6/6**) plus IPC/controller
  resource and event identity checks; visible desktop-session reveal remains a
  separate environment-specific gate.
- **Local isolated candidate qualification:** a clean temporary candidate with
  real install, `npm ci`, production build and external Workstation home passed
  the release runner **6/6**; its hidden H013 candidate profile also passed
  **2/2** and its report was accepted by `workstation.desktop_load_evidence`.
  Official candidate CI remains required for release promotion.
- **Windows workflow coverage:** the release workflow now installs the required
  Playwright browsers, runs the strict Workstation doctor, runs cross-engine
  Dashboard smoke, builds the unpacked artifact, runs the four-session
  180-second reconnect soak, runs the native H011 Browser runtime soak, and
  runs the H012 real headless backend reconnect soak, packaged GUI E2E and H013
  integrated Desktop/Browser load E2E, with explicit final outcome checks and uploaded
  evidence artifacts. H013 selects a bounded 16-task/120-second candidate
  profile with eight real backend chat turns, writes a bounded JSON evidence
  report validated by `workstation.desktop_load_evidence`, and is rejected
  when that report is missing or under-sized.
- **60-second local soak:** 77 fresh-process iterations and 0 failures across
  3 sessions; the duration budget ended normally with `timed_out=true`.
- **Latest 180-second local soak:** 128 fresh-process iterations and 0 failures
  across 4 sessions, with 2,560 actions, 2,048 journal events, 15,888
  cumulative memory records, 512 snapshots, 508 worker reconstructions, 508
  model changes and 508 cold reloads; live memory peaked at **32 records**
  (the explicit 8-record-per-session bound), and the duration budget ended with
  `timed_out=true`.
- **Native H011 Browser runtime soak:** 39 hidden Electron process episodes and
  936 task cycles across 4 tasks passed in 60 seconds, with composite state and
  resource lineage preserved across reconnects.
- **Headless H012 backend soak:** 12 real `hermes serve` cycles, 48 streamed
  turns, 44 session reconnects, 2 backend process restarts, 48 heartbeats and
  zero errors passed with four concurrent sessions.
- **H013 integrated Desktop/Browser E2E:** the hidden-window four-task
  controller/IPC scenario plus the default sustained eight-task/three-round
  backend load passed locally in **2 tests / 38.8s** on the latest rerun
  (36.6s on the prior run), including native Chromium navigation, host-aware
  viewport geometry/transfer, native maximize/restore reconciliation, three
  real chat turns, complete resource/event projection parity and
  hide/park/destroy cleanup. A
  local scaled 12-task/15-second profile also passed **2 tests / 55.4s**. The
  exact Windows profile also passed locally: **16 tasks / 170 rounds / 120,651
  ms / 8 chat turns / 2 tests in 3.0 minutes**. The Windows workflow
  additionally selects that bounded 16-task/120-second profile and still
  requires the headless gate and clean-machine evidence.
- The isolated clean candidate also passed H013 **2/2 in 3.2 minutes**:
  16 tasks, 173 completed rounds, 120,262 ms and 8 backend chat turns; the
  resulting report passed the shared evidence validator.

## Promotion status

- Implementation 4 BrowserTask: **PROMOTED / RESOLVED** through PR #9.
- V1 #1 BrowserSessionState: **PROMOTED / RESOLVED** through PR #11.
- V1 #1.5 sequencing + launcher: **PROMOTED** through PR #12 as historical implementation work.
- Pre-1.5 Mainline Consolidation Gate: **PASS**.
- V1 #1.5, V1.1, V2, V2.1, V2.5, and V3: substantial implementation exists and prior scoped verification remains valid for those boundaries.
- V3.1–V3.4: **CONTRACT LAYER IMPLEMENTED & VALIDATED** for their tested boundaries; this does not imply cross-domain causal completion correctness.
- **Canonical Execution Reliability Gate (2026-09-17): ACTIVE / BLOCKS FURTHER FEATURE EXPANSION.**

## Canonical Work Loop hardening (2026-09-17)

The working tree extends canonical acceptance/intent/liveness/journal and durable
execution owners. The full product program is still IN PROGRESS. See
[implementation evidence](CANONICAL_WORK_LOOP.md) for exact scope, additive
migrations, compatibility boundaries and remaining integrations.

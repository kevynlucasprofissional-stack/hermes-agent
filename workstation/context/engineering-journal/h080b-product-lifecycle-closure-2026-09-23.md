# H-080B — Product Lifecycle Closure Audit

Date: 2026-09-23

Status: **VERTICAL CAUSAL PROOF ACCEPTED / H-080B.2 PRODUCT LIFECYCLE & RECEIPT ENFORCEMENT CLOSED & EMPIRICALLY VERIFIED / H-080B.3 NATIVE PRODUCT QUALIFICATION OPEN**

## Post-implementation deep audit — coordinator exists, closure does not

Audited implementation head:
`60d47e8c0426b84b36ea3a5304111f7997bbe8e9`

PR #46 is now directly based on PR #45 head `72d5e688509078f8f6aaa6ba0b6bdc609cf40ed3`. The base reconciliation, Browser receipt transport, strict run binding, semantic trace-slice admission and coordinator implementation are accepted as useful progress.

However, the post-implementation audit falsifies the claim that H-080B.2 is already closed.

### Finding A — coordinator-manufactured validation is not verifier evidence

The default coordinator path currently builds positive/negative validation artifacts and returns receipts marked `passed=True`.

This is not admissible as promotion-grade verifier sensitivity evidence because the same coordinator:
1. chooses the expected/divergent content;
2. writes the artifact;
3. labels the result as passed;
4. hands that label to `validate_verifier_candidate()`.

The old explicit test path is stronger: it builds real `VerificationEvidence`, runs `evaluate_verification()`, observes positive VERIFIED and negative non-VERIFIED, and only then creates sensitivity receipts.

Production must use the stronger semantics.

Required invariant:

```text
expected value / test description
!= evidence

actual owner-controlled verification decision
= evidence
```

No safe validation environment/evidence => candidate stays pending.

### Finding B — coordinator is not wired to normal runtime

`workstation/kanban.py` still performs approximately:

```text
ExperienceCorpus.accept_run()
-> ExperienceCompiler(...).mine()
-> candidate
-> journal "causal validation required"
```

There is no normal runtime call into `ExperienceValidationPromotionCoordinator`.

Therefore the current implementation proves:

```text
components can compose when fixture calls coordinator
```

not:

```text
product automatically owns candidate validation/replay/promotion
```

H-080B.2 remains open.

### Finding C — owner receipt is emitted but not yet causal proof

Electron now persists a `BrowserOwnerReceipt` and monotonic BrowserTask revision.

Promotion-grade readback currently verifies strict run binding but does not require the receipt to match expected:
- operationId;
- taskId;
- browserTaskId;
- tabId;
- revision;
- action;
- safeUrl.

`_verified_native_navigation()` then writes the trace operation ID into verifier evidence. Without the receipt comparison, the system can theoretically attribute state produced by operation B to trace operation A.

Required correction: receipt identity must be an enforced verifier precondition.

A second ordering defect exists in the compiled reuse path: `OperationalKernel.execute_capability()` currently calculates its canonical `operation_id` only after implementation steps and postconditions. Native learned mutation therefore can cross physical I/O before the kernel's expected operation identity exists. Move operation-id establishment before step dispatch and propagate it into the Browser mutation so certificate/dispatcher/kernel/owner/verifier can refer to one instance.

### Finding D — restart/idempotency remains process-local

The coordinator uses a `threading.Lock()`, which does not survive process restart and is not a durable lifecycle checkpoint.

Use existing:
- OperationalCapabilityRegistry;
- ArtifactStore;
- ExecutionJournal;

to persist/recover lifecycle progress. Do not add a new database.

### Accepted debt — do not derail the lane

The following are not blockers:
- explicit read-only Browser tool whitelist;
- coordinator `policy` constructor/API cleanup;
- broad candidate-discovery exception handling with logging;
- temporary duplicate receipt projection;
- general API/style cleanup.

Fix only if they become causal/product failures.

### Corrected classification

```text
H-080B.1 verified Experience -> candidate
  LOCALLY PROVEN
  promotion-grade receipt enforcement still open

H-080B.2 product validation/replay/promotion
  COORDINATOR IMPLEMENTED
  empirical verifier validation + normal-runtime wiring + restart-safe ownership OPEN

H-080B.3 real Electron/package/dogfood
  OPEN

H-081 Laya/System-1
  DEFERRED
```

### Exact-head qualification snapshot

At the audit:
- PR #45 Workstation CI: green;
- PR #45 Workstation Browser Windows: green;
- PR #46 Workstation CI: green;
- PR #46 Docker: green;
- PR #46 Windows: still running;
- PR #46 Nix: queued;
- PR #46 general `.github/workflows/ci.yaml`: failed immediately with zero jobs, while the workflow blob is unchanged from base.

Treat the zero-job workflow failure as a merge gate to rerun/diagnose, not as evidence requiring H-080B redesign.

### Corrective next step

Run one narrow hardening lane:

```text
enforce owner receipt identity
-> replace self-certified receipts with empirical verifier decisions
-> wire coordinator after mine()
-> persist restart-safe lifecycle progress
-> prove normal-runtime candidate -> promotion
-> exact-head gates
-> move to H-080B.3
```

No Laya, no second ontology, no promotion-gate weakening, no broad architecture rewrite.


## Why this journal exists

The first H-080B native-browser implementation materially advances Progressive Operational Compilation. It proves that the existing Workstation architecture can take a verified adaptive browser experience, compile it into an OperationalCapability, validate its verifier, replay it, promote it, and later reuse it in a normal turn with zero provider calls.

The audit after that implementation found an important semantic distinction:

> A complete causal loop demonstrated by an integration fixture is not yet the same thing as a normal product runtime that owns the entire lifecycle automatically.

This journal records that distinction and defines the next implementation lane without reopening the architecture.

## Exact Git truth at audit

Repository:
`kevynlucasprofissional-stack/hermes-agent`

PR #45:
- title: H-080A native pre-reasoning operational resolution production path;
- state: OPEN / mergeable;
- head: `integration/upstream-20260922-71a2fe39-h0793@c23fe2233450b47d6d90ec9785376327e533bdef`;
- Workstation CI: success at observed snapshot;
- Workstation Browser Windows: still in progress at observed snapshot;
- H-080A architecture is accepted; do not redesign it while qualification completes.

PR #46:
- title: H-080B verified native browser experience to learned reuse;
- state: OPEN / DRAFT / mergeable;
- head: `workstation/h080b-native-browser-experience-loop@769002547428fa882ca1e5248387821482c70cd9`;
- implementation commit: `6d8806b8684d2e492be125e8098c3764bca38c32`;
- current PR base SHA remains `72cfa4b389fe7fecf34e6483a2a88f4b1b52159b`.

Current relationship of PR #46 head to current PR #45 head:
```text
status: diverged
ahead_by: 2
behind_by: 1
merge_base: 72cfa4b389...
```

This means H-080B must be reconciled onto the promoted/current H-080A baseline before promotion.

## What the Codex implementation actually proves

The H-080B test is not a trivial helper test.

Run A:
```text
normal AIAgent turn
-> provider reasons
-> browser_navigate
-> Workstation native browser path
-> one physical native navigation boundary
-> persisted BrowserSessionState readback
-> canonical verified completion
-> ExperienceCorpus accepts a VERIFIED_SUCCESS revision
```

Two compatible accepted runs:
```text
verified Experience
-> ExperienceCompiler.mine()
-> learned OperationalCapability candidate
```

Validation path:
```text
owner readback verifier
-> positive validation
-> wrong-host negative control
-> validate_verifier()
-> controlled_replay()
-> ExperiencePromotionPolicy
-> promoted OperationalCapability
```

Run C:
```text
durable typed OperationIntent
-> pre-reasoning operational resolution
-> CapabilityRouter
-> RoutingCertificate
-> CertifiedDispatcher
-> OperationalKernel
-> native Browser effect exactly once
-> VERIFIED + accepted
-> COMMITTED
-> provider calls = 0
```

The architecture therefore supports the core thesis:

> Reasoning is used while competence is unknown; verified experience can be progressively compiled into deterministic operational competence.

## What the implementation does not prove yet

The normal product lifecycle does not yet automatically own the whole candidate-admission sequence.

Today the normal path is approximately:
```text
verified completion
-> ExperienceCorpus.accept_run()
-> ExperienceCompiler.mine()
-> candidate
-> causal validation required
```

The integration fixture then explicitly performs:
```text
validate_verifier()
-> controlled_replay()
-> promote()
```

Therefore the correct classification is:

```text
CAPTURE                                      production: YES
VERIFIED EXPERIENCE ADMISSION               bounded native vertical: YES
CANDIDATE COMPILATION                        YES
AUTOMATIC PRODUCT VALIDATE/REPLAY/PROMOTE    NO
FUTURE PROVIDER-0 REUSE AFTER PROMOTION      YES
REAL PACKAGED ELECTRON END-TO-END            NO
```

Do not describe Progressive Operational Compilation as product-closed while the middle lifecycle remains fixture-owned.

## Canonical H-080B decomposition

### H-080B.1 — Verified Experience Admission

Goal:
```text
real/adaptive effect
-> truthful post-effect evidence
-> canonical verified completion
-> accepted Experience
-> candidate OperationalCapability
```

Current status:
**LOCALLY PROVEN for the bounded native-browser vertical.**

Remaining qualification:
- reconcile onto current/promoted H-080A baseline;
- exact-head CI;
- real native Electron proof.

### H-080B.2 — Product Validation / Replay / Promotion Lifecycle

Goal:
```text
candidate
-> eligibility
-> owner-safe verifier validation
-> verifier sensitivity / negative control
-> controlled causal replay
-> ExperiencePromotionPolicy
-> promote OR remain candidate
```

Current status:
**OPEN.**

The product needs an owner for orchestration, not a second learning architecture.

### H-080B.3 — Native Product Qualification + Dogfood

Goal:
```text
real Electron BrowserTask
-> real native navigation
-> real persisted owner state/receipt
-> Experience acceptance
-> candidate
-> product-owned validation/promotion
-> future equivalent normal turn
-> provider 0
```

Current status:
**OPEN.**

Prefer a local isolated HTTP server for the release proof so the test controls state without relying on a public third-party service.

### H-081 — System-1 / Laya

Current status:
**DEFERRED.**

Laya is not needed to close H-080B and must not be introduced to hide deterministic-path gaps.

## Decision: one executable ontology remains

`OperationalCapability` remains the executable learned object.

Do not create:
- LearnedScript;
- BrowserSkill as another execution authority;
- another capability registry;
- another Experience DB;
- another Browser DB;
- another verifier DB;
- arbitrary generated-code eval;
- a Playwright browser process parallel to the Workstation native browser.

A browser-specific IR may exist later only as a representation inside `OperationalCapability.implementation` and only if a concrete need is proven.

## Product owner for validation/promotion

A small Workstation-owned **Experience Validation/Promotion Coordinator** is acceptable as orchestration.

It may:
- discover candidate capabilities already emitted by ExperienceCompiler;
- decide whether validation can safely run now;
- invoke `ExperienceCompiler.validate_verifier`;
- invoke `controlled_replay` in a `SafeEnvironment`;
- collect positive/negative/counterexample receipts;
- invoke the unchanged `ExperiencePromotionPolicy`;
- call the existing `OperationalCapabilityRegistry`;
- journal lifecycle evidence.

It may not:
- grant effect authority;
- create RoutingCertificates;
- certify its own effects;
- manufacture expected evidence;
- change verifier truth to make promotion pass;
- bypass policy;
- promote because recurrence count is high;
- become a new source of truth.

If validation is unavailable, unsafe, ambiguous or fails, the candidate stays unpromoted.

## Negative-control rule

The first fixture validates a browser verifier with a wrong-host control. That is useful in an isolated fixture.

Production must never deliberately navigate the user's live browser to a wrong/unsafe target merely to manufacture a negative control.

Allowed sources:
- isolated local test environment;
- owner-controlled sandbox;
- controlled replay environment;
- already-observed admissible historical counterexample;
- deterministic synthetic owner fixture when explicitly a test gate.

### Concrete operation-id seam observed in current code

Current code already attempts to send an operation identity at the Python -> Electron boundary:
- `tools/browser_workstation.py::_dispatch()` sets `payload['operation_id'] = call_key(action, args)`;
- `apps/desktop/electron/workstation-browser-runtime.ts::BrowserControlRequest` does not declare `operation_id`;
- `executeControlRequest()` therefore does not consume/persist/return that identity;
- `workstation/procedure_trace.py::record_trace()` separately uses `agent._current_operation_id` or generates an `observation_<uuid>`.

This can create two different notions of operation identity. The fix is **not** to treat deterministic `call_key(action,args)` as the canonical causal instance ID. A single per-execution `operation_id` must be established before physical I/O, then propagated unchanged through trace/provenance, controller payload, Electron owner receipt/state revision and verifier evidence. `call_key` may remain a structural/idempotency fingerprint where appropriate, but must not substitute for unique causal lineage across runs.

## Browser causality hardening

Current persisted BrowserSessionState is strong evidence of local post-effect state. The next step is stronger causal provenance.

Target flow:
```text
Electron receives operation_id
-> executes browser action
-> updates/persists BrowserTask and tab
-> emits/persists owner receipt/revision:
   operation_id
   task_id
   run_id
   browserTaskId
   tabId
   resulting_state_revision
   safe post-effect state
-> Python verifier validates receipt + state
```

This changes the causal claim from:
"the right state appeared soon after the operation"

to:
"the owner of the effect identifies which operation produced which state revision."

### Strict learnable run binding

For normal Browser UX, nullable run IDs may remain acceptable where the domain permits.

For promotion-grade learned evidence:
- `run_id` must be non-null;
- it must exactly match the canonical run;
- task/run/operation/browserTask/tab lineage must be unambiguous.

Global reusable competence deserves a stronger evidence threshold than ordinary UI continuity.

## Trace admission must be semantic

The first implementation uses `len(trace) == 1` to isolate the proof.

That is not the product abstraction.

Real use already shows why: the Reasoner can correctly navigate and then perform redundant read-only observation such as vision/snapshot.

Target rule:
```text
exactly one relevant mutable Browser operation
+ zero other mutable Browser operations
+ bounded admissible read-only observations
+ no unresolved uncertain effect
+ complete task/run/operation lineage
```

The Experience Compiler should operate on the causal/operational slice. Read-only observation noise must not invalidate otherwise reusable competence when the dependency graph proves that it is irrelevant.

## Verifier scope rule

Evidence can only prove the predicates its owner observes.

Examples:
```text
BrowserSessionState:
  can prove -> BrowserTask ownership, tab identity, safe URL, host/path, live recovery state
  cannot prove -> authenticated account identity, remote transaction success, remote persisted mutation
```

Do not silently upgrade local Browser state into a remote/server claim.

## Mandatory implementation order

### P0 — close the H-080A baseline

- inspect PR #45 exact-head required checks;
- fix only real regressions;
- do not redesign the accepted H-080A control plane;
- if promotion gates are green, merge/promote according to repository policy.

### P1 — reconcile H-080B topology

- update/rebase PR #46 onto promoted/current H-080A/main;
- preserve semantic commits rather than historical conflict locations;
- rerun seam/intervention classification;
- freeze the resulting baseline before feature continuation.

### P2 — strengthen Browser learning evidence

- propagate `operation_id` to the Electron effect owner where required;
- emit/persist owner operation receipt/state revision;
- require exact non-null run binding for learnable evidence;
- preserve sanitization and safeUrl behavior;
- add negative tests for stale/mismatched operation/task/run/revision.

### P3 — generalize adaptive admission safely

Replace literal single-trace cardinality with:
```text
one relevant mutation
+ bounded read-only observations
+ no second mutation
+ no uncertainty
```

Add falsification tests:
- navigate + snapshot should remain admissible when snapshot is read-only/noise;
- navigate + vision/read-only should not poison the candidate;
- navigate + second navigation must not collapse into one atomic learned capability;
- uncertain mutation must remain inadmissible.

### P4 — productize validation/promotion

Implement the coordinator over existing owners.

Required behaviors:
- candidate stays candidate until all promotion obligations pass;
- unavailable validation does not fake failure or success;
- validation receipts are persisted and attributable;
- negative control cannot mutate live user state;
- policy remains unchanged/fail-closed;
- idempotent/restart-safe lifecycle;
- no duplicate promotion race;
- drift/quarantine semantics preserved.

### P5 — real Electron vertical

Use a controlled local server and the real Electron/BrowserTask path.

Prove:
```text
AIAgent adaptive turn
-> real Electron navigation
-> real owner receipt + BrowserSessionState
-> canonical accepted Experience
-> candidate
-> automatic validation/replay/promotion
-> registry promoted capability
```

No fake physical controller in this release proof.

### P6 — future reuse dogfood

On a later equivalent typed intent:
- pre-reasoning route resolves before provider;
- exact matching promoted capability selected;
- valid RoutingCertificate;
- one physical native action;
- canonical VERIFIED + accepted;
- dispatch COMMITTED;
- provider calls = 0;
- canonical finalizer preserved.

Also prove:
- changed host/path outside learned scope does not reuse;
- stale/quarantined capability does not execute;
- verifier failure does not commit or blindly retry;
- absence of a trusted typed intent falls through to Reasoner.

### P7 — H-081 only after closure

Start System-1 work only after P0-P6 are green.

Initial Laya mode:
`SHADOW`.

Allowed suggestions:
- operation family;
- target family;
- capability shortlist;
- reasoning-likely-needed;
- risk/recovery hints;
- model/routing hint.

Forbidden:
- authority grant;
- RoutingCertificate issuance;
- mutation approval;
- canonical verification;
- capability promotion;
- overriding CapabilityRouter.

Canonical rule:
> Laya says where to look. Hermes Work proves whether it is applicable, authorized and true.

## Metrics for the next lane

Do not invent saved-token or success numbers.

Track through existing owners:
- candidates compiled;
- candidates entering validation;
- verifier validation pass/fail/unavailable;
- controlled replay pass/fail;
- promotion admitted/denied;
- time/calls from novel verified outcome to promoted competence;
- deterministic reuse hits;
- provider calls per verified outcome;
- drift/quarantine after promotion;
- candidate-to-promotion rate;
- read-only observation noise tolerance.

Unknown denominators remain `None`.

## Acceptance language

Until H-080B.2 and H-080B.3 are proven, use:

> **Progressive Operational Compilation has a validated deterministic substrate and a locally proven native-browser Experience vertical. Verified Experience admission and provider-zero reuse are demonstrated, while automatic product validation/promotion and packaged native qualification remain open.**

Do not use:
- "self-learning loop fully closed";
- "Experience Compiler automatically learns in production";
- "H-080B complete";
- "Laya is now the router".

## Final architecture invariant

```text
UPSTREAM STRUCTURE
+ WORKSTATION SEMANTICS
+ MINIMUM NECESSARY FIRST-PARTY SEAMS
+ ONE EXECUTABLE OPERATIONAL ONTOLOGY
+ OWNER-ISSUED EVIDENCE
+ NO CAPABILITY REGRESSION FOR PURITY
```

The next implementation is a closure and productization exercise, not an architectural restart.

# Architectural Decisions

**Reading this file.** Decisions are numbered in the order they were recorded and appear in
ascending numeric order (`D-001` … `D-030`). Read by decision number, not by position. `D-028`,
`D-029` and `D-030` were briefly prepended when they were added; they were moved into ascending
position on 2026-09-20. A replacement decision states which decision it supersedes — see
[Changing a decision](#changing-a-decision) below.

For identifier collisions in other canonical documents (`H-*` in the engineering journal,
`KI-*` in `KNOWN_ISSUES.md`), see [ID_DISAMBIGUATION.md](ID_DISAMBIGUATION.md).

These are settled decisions for the Hermes Workstation downstream architecture. They narrow implementation choices; they are not a substitute for the detailed design in [`../ARCHITECTURE.md`](../ARCHITECTURE.md).

## D-001 — Workstation is first-class in this downstream fork

Hermes Workstation is part of this fork's product architecture, not a temporary ZIP overlay. The committed `main` tree is the canonical integrated source for this downstream. Upstream synchronization remains deliberate and tracked.

## D-002 — Preserve Hermes upstream and extend existing ownership

Use Hermes Sessions, Gateway, tool registry/toolsets, approvals, memory, Kanban, profile handling, and browser routing instead of introducing parallel stores or control planes. Downstream edits to upstream-owned files must stay small, explicit, tested, and recorded in `UPSTREAM_DELTA.md`.

## D-003 — The internal browser is Electron Chromium

The primary Workstation Browser uses Electron's Chromium runtime through `WebContentsView` and a dedicated persistent Electron session/partition. Do not reuse the user's personal Chrome/Edge profile.

## D-004 — Browser profile state and BrowserSessionState are different

The Chromium profile owns browser-managed state such as cookies, localStorage, IndexedDB, cache, and compatible authentication state. Workstation BrowserSessionState owns only safe structural metadata such as logical tabs, active tab, BrowserTask linkage, URL/title/order/status, and related identifiers. Never conflate the two stores.

## D-005 — One BrowserTask owns one live page

A BrowserTask represents the durable semantic ownership of an automated web task. It may be hidden, parked, focused, or moved between hosts without navigating again. The same task must not be represented by two independently navigated live pages.

`taskTabs`/`ownerTaskId` remain the authoritative live-page binding inside the Electron process. BrowserTask lifecycle metadata wraps those existing primitives; it does not introduce a second map that owns `WebContentsView` instances.

`hide` and `park` never mean destroy. While the Electron process remains alive, a later `show` must re-expose the same live page and preserve its current URL/page state. `destroy` is an explicit lifecycle operation.

A `WebContentsView` object is process-local and is not serializable across a Desktop restart. Restart recovery therefore preserves the BrowserTask identity and safe metadata, normalizes the task to `parked`, and lazily recreates/reconnects one page under the same `taskId` when the task is used again. Do not describe that as preserving JavaScript heap or `WebContents` object identity across process restart.

## D-006 — Chat Browser View and Browser Hub are views of the same runtime

The contextual Chat Browser View and the global Browser Hub expose the same BrowserRuntime/BrowserTask state. A live `WebContentsView` has one active host at a time; the other surface represents the task with state/card/thumbnail rather than duplicating the page.

## D-007 — Do not create second SessionDB, Kanban, or Memory systems

BrowserTask may reference Hermes session/run/agent identifiers, but it does not own a replacement session database. Workstation planning/execution features must reuse the existing Kanban and Memory abstractions when those features are later introduced.

## D-008 — Bound Browser tasks fail closed

Once a task is bound to the Workstation Browser/controller, loss of that controller must not silently move the task to a different browser/runtime with different authentication or page state. Recovery is explicit. Unbound requests may use configured fallback according to routing policy.

## D-009 — Surface capability is session-scoped

Whether a Desktop/GUI session should know about a GUI/browser surface is a property of the session/platform contract, not of process environment variables or a process-wide cached reachability probe. Reachability may gate execution/recovery, but must not silently erase a valid session surface from the model schema.

## D-010 — BrowserRuntime remains an abstraction boundary

Do not make Workstation business logic depend irreversibly on one concrete browser implementation. Electron Chromium is the current primary runtime, while the BrowserRuntime/controller boundary should remain explicit enough for future specialist runtimes without duplicating state or changing BrowserTask semantics.

## D-011 — Main is tested as committed

Installation and CI must validate the source committed in this downstream `main`. Migration/rebase helpers may exist, but normal install/test paths must not silently rewrite tracked source before validation; otherwise a missing integration can be hidden by the test harness itself.

## D-012 — Main is the only milestone handoff line

Accepted product code, required tests/probes/workflows, current state, and the
decision record must be reachable from `main` before the next milestone starts.
Temporary validation branches and diagnostic PRs may preserve evidence, but they
are never implicit dependencies or alternate product lines.

The extraordinary pre-V1 #1.5 Mainline Consolidation Gate inventories and
classifies the repository's accumulated history. After each later major
milestone, a smaller Mainline Consolidation Review verifies promotion,
classifies new lateral work, reconciles canonical documents and confirms that
the next milestone can branch exclusively from `main`.

Known, causally classified debt may remain open when its scope and evidence are
explicit. An unclassified material delta, stale active predecessor, or required
artifact available only on another branch blocks the handoff.

## D-013 — V3 operational state is a projection, not a new canonical owner

EvidenceState, typed resources, event delivery, session lifecycle metadata,
worker persistence, Recovery Plane records and evaluation traces are
operational projections over Hermes' canonical SessionDB, Kanban, Memory,
BrowserTask and ExecutionJournal owners. They may persist identities, leases,
evidence and recovery copies, but they must not become a second task/session/
memory/browser database or agent core.

The independent supervisor is allowed to own runtime process liveness and
restart/rollback metadata. The Recovery Plane is allowed to quarantine optional
components. Neither is allowed to perform ordinary task work or weaken Policy
Engine/approval boundaries. External A2A/ACP/UHP protocols are adapters into
the canonical event/resource contracts, never alternative state owners.

## D-014 — Canonical TaskRun is the execution-attempt authority

A canonical Agent Task, its execution attempt, a compiled WorkPlan and a
BrowserTask are related identities with different lifecycles. They must not be
collapsed into a mega-entity and must not substitute for one another.

- `tasks.id` remains the canonical Agent Task responsibility identity.
- Existing Kanban `task_runs.id` / `tasks.current_run_id` remains the canonical
  execution-attempt authority. Do not add another Run store.
- WorkPlan/WorkItem own deterministic compiled-plan progress and must persist
  their canonical TaskRun lineage.
- A deterministic `work_<hash>` or equivalent durable-plan identity is an
  `execution_key`/plan identity, never a replacement canonical Task id.
- BrowserTask remains the durable semantic identity for browser work; its live
  page is a process-local lease. BrowserTask persistence may remain Task-scoped,
  while mutations are fenced by TaskRun/operation identity.
- Worker/process/browser handles are live operational evidence, not durable
  proof of successful outcome.

Every mutating Workstation effect must be attributable to one canonical TaskRun
or explicitly classified as a human/system action outside agent-run authority.
Legacy records that cannot be bound safely must be classified for reconciliation;
the runtime must not invent lineage from convenience or transcript prose.

## D-015 — Canonical commit precedes terminal journal and projections

Execution, acceptance, verification, canonical lifecycle commit and UI/journal
projection are separate stages.

For agent-owned completion:

1. the active TaskRun must still own the Task;
2. required acceptance/evidence must be satisfied;
3. the canonical Kanban transition must commit using the existing run-fencing
   mechanism (`expected_run_id` or its canonical successor);
4. only after that commit may `TASK_COMPLETED`, Human Card writeback or terminal
   UI/resource projections be emitted.

A failed/stale CAS is a superseded/rejected completion attempt, not a completed
Task. Human/manual override remains possible only as a separate explicit and
audited authority path.

For external mutable effects, timeout or loss of acknowledgement after dispatch
must enter an explicit uncertainty/reconciliation state. It must never be treated
as proof that the effect did not happen and must never authorize a blind retry.

These rules are the execution-level meaning of `One Hermes State`: one authority
per domain, shared causal lineage and reconcilable projections — **not** one
physical database.

## D-016 — Reliability gate precedes further feature expansion

The 2026-09-17 `CANONICAL_EXECUTION_RELIABILITY_GATE.md` is the immediate roadmap
handoff. Historical V1 #1.5 and all later feature/polish work remain preserved but
do not outrank the gate.

The gate is closed only by invariant/regression evidence, including real
restart/Windows/Electron paths where relevant. A green unit suite or an
"Implemented contract" label is not sufficient to promote product-level causal
reliability.

## D-017 — Adaptive execution precedes progressive compilation

Durable compilation is an optimization and reliability mechanism for understood
repetitive work; it is not a universal permission gate for every mutation inside
a request that happens to look repetitive.

Novel or drifted work may execute through a bounded ADAPTIVE mode under the
existing TaskRun, BrowserTask/worker/host lease, approval, policy and uncertainty
contracts. As stable operation segments are observed, the runtime progressively
moves them through compiled execution and the existing
Experience -> Candidate -> Validate -> Promote -> Routine lifecycle.

A compilation requirement is scoped to a concrete operation fingerprint/target
family, not to the whole session or turn. The current _work_batch_candidate-style
global latch is therefore not an architectural invariant and must be replaced by
operation-scoped policy.

AEPC-E002 clarifies what “operation-scoped” means: **structural call shape alone
does not establish one repeatable operation family**. `REQUIRE_COMPILE` needs
positive semantic homogeneity evidence across the operation and canonical
route/provider plus an owner-declared or safely derived target-family/contract
identity. When that evidence is absent, repeated shape may suggest compilation
or learning but may not, by itself, block bounded adaptive execution. This is
especially important for native `browser_type`, `browser_click` and
`browser_press` sequences whose semantic targets can change as page state
changes. Real same-family fan-out remains compiler/canary gated.

The deterministic runner must return a compact NEEDS_REASONING/drift handoff when
reality no longer matches its assumptions. It must not trap the agent in a
durable_compile_required <-> PREFLIGHT_REQUIRED refusal loop.

For stateful browser work, transient UI interaction and external commit are
distinct. Evidence strength is chosen at the effect boundary; independent
persisted readback is required where the risk/effect contract demands it, not for
every focus/type/open intermediate UI step.

tools.effects is the canonical effect taxonomy. Route policy compares canonical
route identities (native_browser for the internal Workstation Browser) after
tool-to-route normalization. Arbitrary browser_console remains potentially
mutating.

Detailed contract:
[ADAPTIVE_EXECUTION_COMPILATION.md](ADAPTIVE_EXECUTION_COMPILATION.md).

## D-018 — Capability is the reusable deterministic unit; work_execute is runtime infrastructure

D-017 remains valid: adaptive execution precedes progressive compilation. D-018
defines the reusable unit and execution layering that follows from that rule.

A **Capability** is the canonical abstraction between primitive Tool execution and
larger Recipe/Routine workflows. It represents versioned deterministic
operational knowledge with typed inputs, effects, scope, preconditions,
postconditions/verifiers, dependencies, provenance and validation lifecycle.

A Capability is not a Skill. Skills are LLM-facing knowledge/strategy and may
call capabilities. Capabilities may call other capabilities and trusted runtime
primitives. A promoted deterministic capability must not silently call a Skill or
LLM on its success path; drift returns compact NEEDS_REASONING to the adaptive
layer.

`work_execute` is the deterministic execution entry point/infrastructure, not a
global permission gate and not primarily an instruction forcing the model to
manually rewrite repeated work. Exact compatible promoted Capability/Recipe/
Routine reuse should be selected by the harness whenever possible.

The low-level execution substrate is a shared **Operational Kernel**. Browser,
filesystem, process/shell, HTTP/API and future desktop control are backends under
the same effect/evidence/policy/capability contracts. This architecture is not
browser-only.

Native Browser semantic identity must be recoverable and stable enough for
compilation. Transient element refs, tab ids, WebContents ids and arbitrary page
prose are not durable operation identity. Structural call similarity can support
discovery but cannot independently establish semantic homogeneity or mandatory
compilation.

Capability persistence/learning must extend existing RecipeStore,
ProceduralMemory, ExecutionJournal and ArtifactStore ownership where practical.
Do not introduce another canonical SessionDB, Kanban, TaskRun, BrowserTask or
Memory system merely to host capabilities.

1. **Discovery is never blocked by repetition heuristics:** Repeated call structure with distinct semantic targets or unverified exploratory status remains `ALLOW_ADAPTIVE` / `SUGGEST_COMPILE` and never escalates to `REQUIRE_COMPILE`.
2. **OperationalCapability is the deterministic abstraction:** `workstation/operational_capabilities.py` defines `OperationalCapability` with semver, preconditions, postconditions, dependencies, input/output schemas, and lifecycle (`DISCOVERED`, `VALIDATED`, `PROMOTED`, `RETIRED`).
3. **No duplicate persistence planes:** `OperationalCapabilityRegistry` reuses `ArtifactStore` and an atomic index file, integrating transparently with `RecipeStore` and `ProceduralMemory`.
4. **Deterministic Kernel:** `workstation/operational_kernel.py` executes filesystem, browser, and composite primitives without intermediate LLM calls, achieving zero LLM token cost on replay.
5. **Drift Quarantine & Reasoning Handoff:** If preconditions, execution, or postconditions drift, the capability is quarantined in the registry, and a compact handoff package is returned via `workstation.reasoning_handoff.needs_reasoning` yielding back to the LLM.

Detailed target and acceptance criteria:
[PROGRESSIVE_OPERATIONAL_COMPILATION.md](PROGRESSIVE_OPERATIONAL_COMPILATION.md).

## D-019 — Learned operational knowledge is a verified state transition, and promotion is evidence/causality gated

D-018 remains authoritative for the deterministic Capability Runtime. D-019
defines how adaptive experience may become a persistent OperationalCapability.

The canonical learned unit is a **Verified Operational Transition (VOT)**: the
smallest semantically closed, parameterizable, executable and verifiable state
transition with positive reuse value. Tool calls, raw traces and successful
trajectories are evidence inputs; none is automatically the reusable unit.

Experience learning is a pipeline, not a trace recorder:

~~~text
trace
  -> TransitionSamples
  -> semantic state abstraction
  -> boundary proposals
  -> cross-trace alignment
  -> parameterization / anti-unification
  -> conservative precondition/effect/branch inference
  -> dependency / Operational Slice
  -> causal support
  -> safe replay/ablation when policy permits
  -> counterexample refinement
  -> OperationalCapability Candidate
  -> promotion admission
~~~

The successful consolidation path must not require an LLM. The LLM remains for
novel intent, ambiguity and drift diagnosis, but it does not grant learned
capability promotion authority.

Passive recurrence establishes observational support, not causal proof.
Experience Compiler tracks a separate C0-C5 causal grade, while existing E0-E3
continues to represent strength of effect verification. Learned mutable
capabilities require both dimensions plus existing effect/approval policy.

Experience -> persistent Capability is a trust boundary. Provenance/trust/taint
must survive into TransitionSamples and candidates. Repeated page-provided prose
or other untrusted instructions never become trusted preconditions, effects or
authority simply through frequency.

The runtime should capture broadly and promote narrowly. Generic registry
success counts, including
`OperationalCapabilityRegistry.record_validation(..., auto_promote_threshold=2)`,
are not sufficient by themselves to auto-promote experience-learned mutations.
Promotion admission must additionally consider semantic closure, compatibility,
causal grade, evidence, provenance/taint, cross-run diversity, risk/blast radius,
drift and expected reuse utility.

A TaskRun executes against a stable capability-version view. New observations may
create candidates or run-local ephemeral compiled segments, but they must not
silently alter the meaning of a capability already selected for that TaskRun.

Counterexamples refine the smallest unsupported assumption and create a new
immutable candidate/version. Historical promoted behavior is never silently
rewritten in place.

Controlled replay/ablation is allowed only when the effect/environment is
sufficiently safe and reversible. The system must not perform destructive
production experimentation merely to increase causal confidence.

Canonical design:
[EXPERIENCE_COMPILER.md](EXPERIENCE_COMPILER.md).

## D-020 — OperationIntent is declarative; mutating routing requires a verified certificate

D-018 remains authoritative for deterministic OperationalCapabilities and D-019
remains authoritative for experience-to-Capability learning. D-020 defines the
selection/control boundary that follows from both.

The existing `WorkIntent` remains a transient classifier for execution class,
durability, risk, Browser/worker needs and acceptance policy. It must not be
silently redefined as the semantic goal contract.

A new immutable **OperationIntent** represents what must become true, not how to
do it. Its canonical contract includes target identity/family, desired-state
predicates, invariants, an EffectBudget, trusted authority reference, acceptance
requirements and TaskRun lineage. It contains no physical Capability ID, transient
Browser ref or procedural steps unless an explicit user/system constraint requires
a concrete implementation.

Intent permission and execution authority are independent requirements:

~~~text
IntentAllows(effect)
AND
AuthorityAllows(effect)
~~~

Never OR. Broad credentials do not expand the current intent, and a requested
effect does not manufacture authority.

The **Capability Router** is a deterministic bounded proof/typechecking engine,
not another agent. Approximate retrieval may propose candidates, but only symbolic
admission can authorize execution. Final decisions are:

~~~text
SATISFIED | EXECUTE | COMPOSE | WAIT | ASK_HUMAN | WAKE_LLM
~~~

`EXECUTE` and `COMPOSE` are dispatchable only when backed by a valid
`RoutingCertificate` / `CompositionCertificate`. The certificate must establish
target/input compatibility, current preconditions, goal coverage, effect
containment, invariant preservation, authority/policy/approval sufficiency,
verifier strength, state freshness, deterministic closure and absence of relevant
unreconciled uncertainty.

Canonical proof invariants:

- **Router Soundness** — every dispatchable decision satisfies all proof obligations;
- **Goal Non-Expansion** — semantic effects remain within the OperationIntent EffectBudget;
- **Authority Non-Escalation** — composition authority is the JOIN of child requirements
  and may not exceed granted authority;
- **Deterministic Closure** — no unresolved semantic branch remains for EXECUTE/COMPOSE;
- **Verification Closure** — effect verification satisfies the intent AcceptanceContract;
- **Uncertainty Dominance** — relevant unresolved dispatched mutation blocks new mutation.

The hard runtime rule is:

> **No valid certificate, no dispatch.**

Even a valid certificate applies to a versioned observed state. Critical
preconditions, TaskRun fencing, approval and state/resource freshness must be
revalidated immediately before mutable side effects. A stale certificate is
invalidated and routed/reconciled again.

The smallest persistent waiting unit is **AwaitCondition**, not the event itself.
An event is a wake hint; authoritative state confirms whether the condition is
true. AwaitCondition persists typed predicate, observer/correlation,
continuation, deadline/temporal semantics and TaskRun/operation fence through
existing owners. It must not create a parallel scheduler/task database.
Uncorrelated events remain observations and cannot mint work intent.

The smallest reasoning escalation is **OpenCondition** carried by a bounded
AttentionPacket over the existing reasoning-handoff owner. The LLM may propose a
resolution, but that proposal returns through Router admission before any
mutation:

> **LLM proposes; Router authorizes.**

Skills should normally depend on semantic capability families
(`requires_family`), not physical capability IDs. Exact physical pins are
reserved for semantics that require implementation identity.

Detailed target:
[VERIFIED_OPERATIONAL_CONTROL_PLANE.md](VERIFIED_OPERATIONAL_CONTROL_PLANE.md).


## D-021 — Mandatory compilation requires operational closure; Router is the mutation-admission owner

D-017 through D-020 remain authoritative. Live browser dogfooding established the
missing composition rule between them.

Hermes may only make compilation **mandatory** for an operation family when it has
positive semantic homogeneity **and** an executable deterministic closure: trusted
primitive(s), compatible authority/policy, sufficient verifier/readback and a certified
dispatch path. Structural repetition alone may propose learning/compilation but cannot
force unrelated work into `durable_compile_required`.

The legacy execution-policy detector is therefore an optimization/learning signal, not a
second independent mutation authority. Final mutation admission converges on
OperationIntent + trusted AuthorityScope + Policy/Approval + Capability Router +
CertifiedDispatcher. Adaptive execution remains bounded and policy-controlled when no
exact executable Capability exists.

Arbitrary `browser_console`, terminal or unknown-code execution does not become trusted
merely because the user authorized the high-level task. Recurring useful semantics must
instead be lowered into first-party typed primitives. Rich browser editors require a
deterministic plain-text paste semantic; persisted external verification requires a
narrow read-only Browser readback path rather than arbitrary page JavaScript.

OperationIntent/request data may **narrow** but never mint execution authority. Effective
AuthorityScope is derived from trusted ingress/TaskRun/policy/approval context.

Mutating route decisions must cross the certified dispatcher as the production
chokepoint. Timeout after possible mutation dispatch becomes UNCERTAIN until reconciled;
blind retry is forbidden. Browser observation must distinguish a transient empty SPA
snapshot from stable semantic state using bounded readiness, not site-specific sleeps.

### D-021 implementation compliance note — 2026-09-19

Post-PR #29 audit does **not** replace D-021; it found implementation paths that still
violate D-021 and must be corrected:

- `COMPOSE` is dispatchable only if the certified composition is actually executed and
  its required postconditions/verifiers close. Returning a plan description is not
  execution and cannot produce COMMITTED.
- dispatcher ACK and `success=True` are execution acknowledgements, not persisted
  verification by default. Without accepted verifier evidence, state remains
  ACKNOWLEDGED / NEEDS_VERIFICATION / UNCERTAIN as appropriate.
- trusted authority must be supplied by trusted ingress/TaskRun/policy/approval state,
  never by a model-facing request field and never by a permissive wildcard synthesized
  merely because a task/session exists.
- semantic recurrence cannot by itself produce `REQUIRE_COMPILE`. The runtime must
  prove operational closure: deterministic representation, compatible authority/policy,
  verifier/readback and certified dispatch.
- `browser_read_http` is a Browser-session readback capability, not a generic HTTP
  client. Bound native Browser use fails closed when that runtime is unavailable,
  defaults to same-origin, and may cross origin only through explicit policy.
- qualification claims require exact-head CI/product gates; focused/local green tests
  do not override a failing integration anchor or skipped downstream gates.

These are compliance requirements for the existing decision, not a new parallel
authority, verifier or Browser state system.

Canonical design:
[BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md](BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md).

## D-022 — Operational knowledge is hierarchical; compile semantic closure, not gestures

D-018 (Operational Capability Runtime), D-019 (Experience Compiler), D-020
(Verified Operational Control Plane) and D-021 (operational closure for mandatory
compilation) remain authoritative.

Hermes Work adopts the following additional architectural rule:

> **Repeated verified experience should progressively reduce fresh LLM reasoning by
> becoming reusable operational knowledge, and the product of one verified
> compilation level may become the vocabulary of the next.**

The hierarchy is:

~~~text
trusted primitive
  -> Verified Operational Transition / OperationalCapability
  -> Composite OperationalCapability
  -> deterministic workflow
  -> Await/Event
  -> smallest unresolved reasoning boundary
~~~

The atomic learning target is **not** the smallest possible physical action. It is
the smallest semantically closed, parameterizable, executable and verifiable state
transition with positive reuse value. Tool calls and transient UI gestures are
evidence/primitives; they are not automatically durable capability identities.

A recurring composition of capabilities may propose a higher-level composite only
when semantic closure, causal/dependency support, stable parameterization,
effect/authority/verifier closure, positive utility and replay evidence support it.
Frequency alone never promotes. Higher-level composites should normally preserve
child capability dependencies/version pins rather than flatten their primitive
implementations.

Learned capabilities become semantic Router candidates only through conservatively
derived typed formal contracts backed by trusted compiler/runtime evidence.
Missing target/effect/authority/verifier proof means exact reuse or
`NEEDS_REASONING`, not guessed admission.

Long external waits are operational state, not reasoning. Persistent
`AwaitCondition` plus a fenced durable continuation is the canonical semantic
model. The executor should be releasable while waiting. An event wakes; authoritative
state confirms; continuation re-enters Router admission. Polling is a bounded
observer fallback, not a reason to retain an LLM or resident worker indefinitely.

The system should measure **Operational Reasoning Amortization** rather than count
capabilities alone. The preferred leading ratio is verified semantic transitions
executed with zero LLM intervention divided by total verified semantic transitions,
paired with evidence quality, drift, uncertainty and reuse metrics.

This decision does not authorize a second scheduler, registry, control plane, task
database, BrowserTask owner, journal or memory store.

Canonical design:
[HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md](HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md).

## D-023 — Run-local operationalization is distinct from global capability promotion

D-018 through D-022 remain authoritative. Newly verified adaptive behavior may become a
run-scoped compiled segment before TaskRun end only when RunClosureProof establishes
deterministic representation, executable closure, authority/effect containment,
verifier readback, cleared uncertainty, compatible replay/canary and positive utility.

This is not global promotion. The segment is fenced to task/run/operation, may only
narrow current authority, persists through existing WorkPlan/WorkItem/ArtifactStore,
executes through TaskCompiler/DurableBatchRunner/OperationalKernel and never enters the
global PROMOTED Router index.

Do not create a second scheduler for an ExecutionLease. Treat it as bounded WorkPlan
execution metadata. Arbitrary browser_console source remains discovery evidence, not a
trusted learned program.

> **Run outcome does not rewrite transition truth.**

Canonical:
[IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md](IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md).

## D-024 — Verification is a typed evidence contract; learned action and learned oracle are validated separately

D-018 through D-023 remain authoritative.

Hermes Work does not introduce a separate Verifier Compiler subsystem. Verification
extends the existing CapabilityFormalContract / OperationalCapability / Control Plane /
Experience Compiler owners through a typed VerificationContract and a deterministic
VerificationEvaluator.

Canonical rules:

- ACK, observation, persisted readback, semantic equivalence, postcondition proof,
  goal satisfaction and task acceptance are distinct claims;
- unknown verifier metadata never upgrades itself to independent/persisted evidence;
- verifier sufficiency is multidimensional: persistence, source trust/authority,
  failure-domain admissibility, temporal validity/freshness, deterministic relation and
  predicate/goal coverage;
- independence is derived from real provenance/failure domains, never asserted by the
  verifier itself;
- page prose and LLM output may propose observations but may not mint verifier trust,
  consistency guarantees, canonicalizers or authority;
- semantic equivalence must be deterministic, narrow, owner-approved and versioned;
- source disagreement produces CONFLICT/INCONCLUSIVE rather than convenient success;
- a postcondition can prove state satisfaction without proving transition causation;
  idempotent ensure-state operations and causal mutations must not be conflated;
- Experience Compiler may infer verifier candidates from experience, but the same
  discovery traces do not validate the candidate;
- action models and verifier/oracle models are falsified separately and bound only
  after both satisfy their promotion obligations;
- safe negative controls/counterexamples are first-class verifier validation evidence;
  destructive production experiments are not required or authorized;
- H-075 RunClosureProof may hand off only when the required verifier contract/result is
  validated, fresh enough, conflict-free and covers the required predicates.

Do not create a VerifierDB, VerifierRegistry, VerificationScheduler, second evidence
store, second predicate IR, verifier agent or LLM judge as mutation commit authority.

> **OBSERVATION PROPOSES. CONTRACT DEFINES. EVIDENCE PROVES.**

> **THE ACTION AND THE ORACLE ARE LEARNED SEPARATELY; THEY ARE BOUND ONLY AFTER BOTH
> SURVIVE FALSIFICATION.**

Canonical:
[VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md](VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md).

## D-025 — VERIFIED is a scoped contractual claim; external falsification precedes new horizontal primitives

D-017 through D-024 remain authoritative.

A Hermes `VERIFIED` result proves only the predicates that a current contract and
admissible evidence can justify within known authority, temporal/version and
applicability conditions. It must never be treated as a universal claim that the model
contains every fact relevant to real-world correctness or human satisfaction.

Consequences:
- OperationIntent is the current operational specification, not a guaranteed lossless
  encoding of the human need;
- SemanticState is a projection and may be representationally insufficient;
- ORA is an efficiency metric conditioned on external correctness/safety/coverage;
- Experience Compiler must suspend/narrow/quarantine generalization when
  counterexamples show that the abstraction does not discriminate outcomes;
- a validity envelope is derived from existing owners before any dedicated registry;
- new horizontal primitives require a reproduced counterexample, material value,
  absence of a natural existing owner and measured external improvement;
- insufficient proof preserves INCONCLUSIVE/CONFLICT/STALE/WAIT/ASK_HUMAN/WAKE_LLM
  rather than manufacturing certainty.

Do not create ApplicabilityCompiler, AssumptionRegistry, PolicyCompiler, TemporalIntent,
WorldModelService, VerifierDB/OracleManager, UnknownUnknownDetector, a second Control
Plane, evidence store or predicate IR merely to encode H-077 research vocabulary.

> **INTERNAL PROOF != EXTERNAL VALIDITY.**

> **NO OBSERVED CONTRADICTION != COMPLETE MODEL.**

Canonical:
[ARCHITECTURAL_FALSIFICATION_2026-09-19.md](ARCHITECTURAL_FALSIFICATION_2026-09-19.md).

### D-025 implementation compliance note — H-077.1 post-merge audit (2026-09-19)

PR #36 does not supersede D-025 and H-077.1 does not create a new architecture decision.
The audit found implementation paths still inconsistent with D-025:

- TaskCompiler terminal completion must consume canonical verification truth, not kernel ACK;
- VerificationContract judges an observation receipt but may not mint its evidence
  strength/trust/source/failure-domain provenance;
- known task/run/operation lineage must be checked;
- the derived validity envelope must fail closed on missing required applicability
  dimensions and gate reuse through an existing owner;
- external metrics must expose external adjudication coverage and never improve merely
  because ground truth is absent;
- external falsification requires system result and independent oracle result to be
  produced separately;
- non-discriminable outcomes suspend generalization without invented hidden PREs;
- execution ACK, verified success and verified replay are separate accounting concepts.

Canonical corrective program:
[H077_1_QUALIFICATION_CLOSURE_2026-09-19.md](H077_1_QUALIFICATION_CLOSURE_2026-09-19.md).

No Applicability/Assumption/Oracle/WorldModel registry or second control plane is
authorized by this compliance note.

## D-026 — Synchronize upstream while extracting seams; Workstation supervises Hermes unidirectionally

D-017 through D-025 remain authoritative.

Hermes Work will adapt to the current `NousResearch/hermes-agent` upstream, but this
migration is also the beginning of Runtime Independence. We will not first reproduce the
old patch topology on the new upstream and only later attempt a separation.

The canonical direction is:

```text
Hermes generic runtime
  -> generic lifecycle / middleware / provider events
  -> Workstation-owned Hermes adapter
  -> Work Runtime / Control Plane
```

Generic Hermes core must progressively stop importing or special-casing Workstation.
Workstation may depend on stable/generic Hermes extension contracts; the reverse
dependency is migration debt.

Most importantly, removing direct seams must **not** mean that Hermes must "remember" to
use Workstation. Workstation participation cannot depend on prompt compliance, model
choice, or the model selecting `work_execute`. The Workstation must observe normal Hermes
execution and, through generic contracts, be able to intervene, pause, modify, wrap,
reconcile, verify and compile experience where its policy requires.

`work_execute` remains a valid explicit Capability/Intent fast path and external API;
it is not the activation mechanism on which Workstation correctness depends.

For upstream conflicts use exactly one classification:
`ADOPT_UPSTREAM`, `KEEP_WORKSTATION`, `SEMANTIC_PORT`, or `EXTRACT_BOUNDARY`.
Prefer `EXTRACT_BOUNDARY` when existing generic `pre/post_tool_call`,
`tool_request/tool_execution`, `llm_request/llm_execution`, API/session lifecycle or
browser-provider surfaces can own the integration.

No seam is retired before shadow/parity evidence proves that lineage, effect/authority,
uncertainty, verification, BrowserTask ownership, human handoff and Experience Compiler
observations survive. Upstream structure is authoritative for generic Hermes; Workstation
semantics remain authoritative for Workstation-owned invariants.

The migration target is not two diverging products. It is one Work Runtime with Hermes as
the first-party adapter/laboratory, followed later by standalone process/UI packaging.

Canonical:
[UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md](UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md).

## D-027 — First-party seam minimization, not zero-seam purity

D-026 remains authoritative, with this clarification.

Hermes Work does **not** adopt a blanket objective of eliminating every source-level seam
from the downstream Hermes distribution. The target is the **minimum necessary first-party
seam surface** consistent with full Workstation capability, correctness, lifecycle
control and integrated UX.

The Reasoner must not need to remember Workstation, and generic Hermes core should prefer
generic hooks/middleware/providers/plugins over Workstation-specific knowledge. But the
first-party Desktop distribution may deliberately retain narrow source-level integration
when extension surfaces cannot preserve equivalent semantics.

Every source seam is classified as:
- `REMOVE`: generic current surfaces are sufficient;
- `UPSTREAM_ABSTRACT`: capability is legitimate, but a small generic extension boundary
  is missing and should be created/used;
- `PRESERVE_FIRST_PARTY`: privileged lifecycle/native integration is materially required
  and must remain narrow, documented and tested.

The Workstation Browser is the reference constraint: modern upstream pane/plugin APIs may
replace presentation-layer seams, but they are not presumed equivalent to Electron
main-process ownership of persistent `WebContentsView`, BrowserTask lifecycle,
background execution, human takeover, fencing, viewport transfer, native IPC and recovery.

No proven Workstation capability may be downgraded merely to achieve a smaller diff or
"plugin purity".

Every preserved seam must satisfy the first-party seam budget in
[FIRST_PARTY_SEAM_POLICY.md](FIRST_PARTY_SEAM_POLICY.md), be tracked in
`workstation/first_party_seams.json` / `UPSTREAM_DELTA.md`, have behavioral evidence,
and be re-evaluated on each upstream migration.

## D-028 — Migrate semantic causal contracts, not historical patch locations

**Decision:** H-078 implementation is governed by semantic concerns and causal ordering.
A source file is not the unit of preservation.

The migration must:

- adopt modern upstream owners/decomposition;
- identify the Workstation property currently guaranteed by each seam;
- preserve the exact authority/ordering/lineage property;
- place it behind the narrowest generic upstream-compatible contract;
- keep a first-party seam only when generic contracts cannot preserve equivalent
  capability/correctness;
- remove the historical patch location after parity.

Required generic boundaries identified by the deep audit are
`turn_admission`, `tool_batch_admission`, authorized pre-I/O dispatch,
execution-persistence disposition, `completion_admission`, `TurnRoutePolicy`,
`TaskCompletionAdmission`, browser capability registration and trusted `TurnIngress`.

The critical causal invariant is that uncertain mutation state is persisted **after final
arguments and authorization/guardrails, but before external I/O**. A hook at any other
position is not equivalent.

The Browser migration specifically uses dual-control/shadow prediction, never
dual-execution for mutations.

This decision refines D-026/D-027; it does not supersede the minimum-first-party-seam
policy.

## D-029 — First-Party Workstation Adapter via Generic Core Registries

**Decision:** The Hermes generic core is completely decoupled from Workstation internals.
All Workstation capabilities are provided via a first-party adapter (`workstation/integrations/hermes/`)
that wires into generic lifecycle, admission, persistence, and observation registries in `agent/`.

Principles enforced:
- **Zero Core Seams**: Generic agent modules (`run_agent.py`, `conversation_loop.py`, `tool_executor.py`,
  `turn_finalizer.py`, `chat_completion_helpers.py`, `conversation_compression.py`, `turn_constraints.py`,
  `cli.py`, `gateway/run.py`, `kanban_db.py`, `web_server.py`, `file_tools.py`, `tool_search.py`,
  `close_preview_tool.py`) contain **zero** direct imports from `workstation`.
- **Reasoner Independence**: Any Reasoner (AIAgent or an alternate foreign Reasoner) can drive
  the Workstation kernel through the generic lifecycle contracts without importing `run_agent.py`.
- **Causal Invariants**:
  1. Pre-authorized checkpoint fires after argument resolution and authorization, strictly before external I/O.
  2. Raw post-tool observation captures unmutated results and procedure traces before truncation or spilling.
  3. Owner-managed persistence disposition prevents intermediate SessionDB flushes during compiled durable batches.
  4. Completion admission validates verification contracts before DONE commits.
- **Fail-Closed Seam Policy**: `audit_hermes_seams.py --strict` acts as an automated regression
  gate enforcing zero unclassified core seams.

## D-030 — Upstream-first qualified baseline before downstream implementation

**Decision:** upstream synchronization is now a mandatory admission gate for downstream
runtime work, not a periodic maintenance activity.

Before any bug fix, feature, refactor or behavioral adjustment:
1. fetch current upstream;
2. select and pin one exact upstream SHA;
3. establish a true upstream-history baseline on a separate integration lane;
4. reconcile affected seam dispositions;
5. require baseline qualification;
6. only then implement the requested downstream change.

The pin remains immutable during target implementation. Before promotion, fetch upstream
again and classify drift; relevant overlap requires another baseline cycle.

This decision deliberately separates **baseline migration** from **target implementation**
so test failures, ownership changes and rollback remain attributable.

An explicit temporary exception is allowed only when the candidate upstream itself is
known broken/unadoptable and the exception is recorded in CURRENT_STATE and the engineering
journal. Silent exceptions are forbidden.

Canonical:
[UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md](UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md).

D-030 refines D-001/D-002/D-011/D-012 and operationalizes D-027/D-028/D-029.

## Changing a decision

A replacement decision must state which decision it supersedes, why the old invariant no longer holds, how migration/backward compatibility is handled, and which tests prove the new contract. Do not silently drift architecture through implementation-only changes.

## Canonical Work Loop contracts (2026-09-17)

Intention authority comes from a trusted MessageEnvelope, never request prose.
Workstation/Hybrid done requires a verified outcome accepted against the policy
captured at creation. Live handles require bounded liveness; durable proof cannot
prove running. Canonical execution lineage and Task Cockpit are projections over
Kanban, WorkPlans, BrowserTask refs and journal, with no new task store. Routine
execution stop remains distinct from accepted task completion. Implementation
boundaries are documented in [Canonical Work Loop](CANONICAL_WORK_LOOP.md).

## D-031 — Pre-reasoning operational resolution is a generic harness boundary

Before a provider LLM call, Hermes may consult registered operational-resolution providers. The generic `agent/` owner defines only the lifecycle contract; Workstation-specific intent/routing/execution lives behind the first-party Hermes adapter.

Rules:
- only an already-established, typed and trusted `OperationIntent` may enter deterministic routing; raw user prose is not an intent contract;
- inability to prove applicability returns `CONTINUE_REASONING`;
- deterministic execution uses the existing `CapabilityRouter`, certificate/authority checks, `CertifiedDispatcher`, `OperationalKernel` and canonical verifier;
- after an effect may have been dispatched, exceptions never silently fall through into an equivalent LLM-driven mutation; uncertainty/reconciliation semantics apply;
- a canonically verified EXECUTE/COMPOSE result does not call the LLM again for the same step;
- terminal operational outcomes rejoin the canonical turn-finalization lifecycle;
- no fake-success or placeholder dispatcher is permitted;
- Laya or any future System-1 classifier may propose candidates but cannot grant authority, issue certificates, verify effects or promote capabilities.

This decision is informed by the rejection/revert of `471e9b529f745c89a3b18caad865e762f09dfab3` and supersedes that implementation pattern, not the broader H-078B generic-adapter architecture.

# Verified Operational Control Plane — OperationIntent, Capability Router, Await/Trigger Plane


## Hierarchical operational learning integration — P0-P4 QUALIFIED (2026-09-19)

The Control Plane serves as the strict admission/selection owner for the hierarchical
learning layer:

1. **Learned capabilities are routable via proven formal contracts (P1 Closed)**:
   Experience Compiler learned candidates derive a conservative `CapabilityFormalContract`
   from trusted evidence (`derive_formal_contract()`). `CapabilityRouter` dynamically
   rebuilds its index, matching `OperationIntent` against learned capabilities and emitting
   `ExecutableDecision` with a valid `RoutingCertificate`, executing without LLM intervention.
2. **WAIT is non-resident control state (P2 Closed)**:
   `AwaitContinuation` stores durable subgraph, plan metadata, capability pins, and
   verified state. `is_non_resident_wait()` identifies external semantic waits to release
   the worker process. `TriggerCoordinator` fences on `run_id`, `task_id`, and `operation_id`,
   evaluates predicates against authoritative state before wake ("EVENT WAKES. AUTHORITATIVE STATE CONFIRMS."),
   and deletes condition records only after resumption is confirmed.
3. **Truthful dispatch and composition execution (P0 Closed)**:
   `CertifiedDispatcher` fails closed (`DispatchStatus.NEEDS_VERIFICATION`) unless a valid
   verifier confirms postconditions or the contract explicitly permits ACK-only (`allow_ack_only=True` / `E0`).
   Composed decisions execute each step sequentially via `OperationalKernel.execute_capability`
   rather than echoing plan IDs. Authority originates exclusively from trusted sources and cannot
   be synthesized as wildcard defaults.
4. **Hierarchical composition and execution (P3 Closed)**:
   `OperationalKernel` captures `CapabilityInvocation` traces during verified runs.
   `HierarchicalExperienceCompiler` mines recurring sequences and proposes dependency-based
   composites requiring causal JOIN, authority JOIN, and verifier closure. Execution traverses
   dependencies; child drift/quarantine propagates fail-closed.
5. **Operational Reasoning Amortization metrics (P4 Closed)**:
   `ORAMetrics` tracks `ora_ratio`, composite reuse, wait non-residency, and `WakeReason`
   breakdowns, strictly preserving `None` / `null` when denominators are absent.

The Control Plane remains the narrow waist:

~~~text
reasoning proposal OR learned capability/composite
  -> OperationIntent + SemanticState
  -> Router proof
  -> certificate
  -> real deterministic execution
  -> evidence/verifier
  -> commit
~~~

No hierarchical learner may bypass this boundary.

Date established: 2026-09-18
Status: **IMPLEMENTED / CONTRACT VALIDATED (P0-P4 QUALIFIED — 2026-09-19)**

Depends on:
- [CANONICAL_WORK_LOOP.md](CANONICAL_WORK_LOOP.md)
- [PROGRESSIVE_OPERATIONAL_COMPILATION.md](PROGRESSIVE_OPERATIONAL_COMPILATION.md)
- [EXPERIENCE_COMPILER.md](EXPERIENCE_COMPILER.md)
- [HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md](HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md)
- [CANONICAL_EXECUTION_RELIABILITY_GATE.md](CANONICAL_EXECUTION_RELIABILITY_GATE.md)

The Capability Runtime answers **how a known operation can execute deterministically**.
The Experience Compiler answers **how repeated adaptive experience becomes reusable
OperationalCapability knowledge**.

The next boundary is the control plane:

> **how Hermes converts intent + current semantic state + runtime events into a
> justified decision to SATISFY / EXECUTE / COMPOSE / WAIT / ASK_HUMAN / WAKE_LLM.**

The Capability Router is not another agent. It is a deterministic executability
checker/typechecker. Retrieval may be heuristic; mutation admission may not be.

## Executive invariants

1. **The LLM resolves only semantic degrees of freedom not already compiled.**
   It is not the scheduler, waiter, monitor, capability catalog, or mechanical executor.
2. **Intent declares desired state, not an implementation plan.**
3. **Intent coverage and authority are independent gates.**
   An action must be both desired/permitted by the intent and authorized by trusted policy.
4. **Similarity proposes; proof authorizes.**
   Approximate retrieval never grants write authority.
5. **No certificate, no dispatch.**
   `¬CertificateValid => ¬Dispatch`.
6. **Events wake conditions; authoritative state confirms them.**
7. **A response from the LLM returns through Router admission before any mutation.**
8. **The existing owners remain canonical.**
   Do not create a second TaskRun, SessionDB, Kanban, approval, BrowserTask,
   capability registry, journal, memory or scheduler.

## Current implementation baseline on main

Current `main` after PR #27 already contains the substrate this milestone must extend:

- `workstation/contracts.py`
  - `MessageEnvelope`, `MessageOrigin`, `IntentAuthority`;
  - `AcceptanceContract`, `TaskOutcome`, execution/evidence contracts.
- `workstation/work_intent.py`
  - existing **WorkIntent** is a transient execution classifier
    (execution class, durability, browser/worker need, risk, repeatability hint,
    acceptance policy, constraints);
  - it is **not** the declarative OperationIntent defined here and must not be
    renamed/reinterpreted in a way that breaks current callers.
- `workstation/operational_capabilities.py`
  - OperationalCapability Registry/Resolver, versions, dependencies, lifecycle,
    provenance, C-grade/trust metadata and composition foundations.
- `workstation/experience_compiler/`
  - EC0–EC8 are implemented and emit existing OperationalCapability objects.
- `workstation/task_compiler.py` / `work_execute`
  - direct capability replay, automatic exact fingerprint reuse, WorkPlan pins,
    deterministic checkpoints and uncertainty semantics.
- `workstation/reasoning_handoff.py`
  - bounded `NEEDS_REASONING` state_ref handoff already exists.
- `workstation/runtime.py`
  - RuntimeEventBus and an in-memory `WaitContract` exist;
  - EvidenceState and live-handle semantics already exist.
- `workstation/events.py`
  - uncorrelated system events are observations, not authority to create work.
- `workstation/policy.py`
  - ScopedPolicyEngine already owns low-level action policy decisions.
- `workstation/journal.py`
  - canonical durable execution/event evidence remains the journal owner.
- Canonical TaskRun/operation fencing, approval, uncertainty/reconciliation and
  canonical commit ordering already exist and remain authoritative.

### Concrete gaps on current main

1. Existing `WorkIntent` does not encode a stable desired semantic state,
   target identity, invariants, effect budget, authority reference or acceptance
   predicate suitable for deterministic capability routing.
2. OperationalCapability currently stores string preconditions/postconditions and
   a coarse `effect`; there is no shared typed logical IR sufficient to prove
   goal coverage, effect containment or invariant preservation.
3. There is no first-class `RoutingDecision` / `RoutingCertificate`.
4. Exact capability reuse currently begins from explicit capability/fingerprint
   requests; there is no intent-to-capability control-plane Router.
5. Capability composition has dependency/cycle semantics but no whole-plan
   CompositionCertificate proving causal links, effect closure, invariant
   preservation, authority closure and threat absence.
6. `needs_reasoning()` is compact but not yet an `AttentionPacket` /
   `OpenCondition` contract that identifies the smallest unresolved semantic
   proposition while preserving confirmed effects and remaining graph.
7. Runtime wait support is not yet a persistent, restart-safe `AwaitCondition`
   with observer/correlation/continuation/deadline/fence semantics.
8. Runtime/System events do not yet provide a versioned causal event envelope
   with resource version, dedupe lineage and stale-event admission semantics.
9. There is no Router-specific evaluation plane for exact-match precision,
   missed reuse, routing blame, trigger quality, VOLC/RAR or shadow rollout.
10. Skills do not yet have a canonical semantic `requires_family` contract
    decoupled from physical capability IDs.

These are the next architecture gaps. Do not rebuild Capability Runtime or
Experience Compiler.

# 1. Canonical OperationIntent

The new declarative intent is distinct from current `WorkIntent`.

Conceptually:

~~~text
OperationIntent
I = < id, version, mode, target, G, Inv, B, AuthRef, Acc, Lin, context_refs >
~~~

Where:

- `mode`: ACHIEVE | MAINTAIN | OBSERVE | AVOID;
- `target`: resource family + stable target selector/identity;
- `G`: GoalContract / desired final semantic predicates;
- `Inv`: invariants that must remain true;
- `B`: EffectBudget — maximum semantic effects allowed by this intent;
- `AuthRef`: reference to trusted ingress/policy authority;
- `Acc`: AcceptanceContract / required evidence;
- `Lin`: canonical task/run/parent-intent lineage;
- `context_refs`: bounded ArtifactStore references, never raw large context.

OperationIntent does **not** contain:

- tool names;
- transient Browser refs;
- `capability_id`;
- `work_execute`;
- recipes;
- procedural steps;
- implementation route unless the user/policy explicitly constrains it.

Example:

~~~yaml
intent_id: int_42
schema_version: 1
mode: ACHIEVE

target:
  family: github.pull_request
  identity:
    repository: kevyn/hermes
    number: 123

goal:
  - EQ(target.state, merged)

invariants:
  - UNCHANGED(repository.default_branch)
  - FORBID_CHANGE(other_pull_requests)

effect_budget:
  allow:
    - CALL(github.pull_request.merge, target)
  forbid:
    - CALL(github.repository.delete, repository)
    - CALL(github.branch.delete, repository.default_branch)

authority_ref:
  envelope_id: env_779

acceptance:
  minimum_evidence: E2
  predicates:
    - EQ(target.state, merged)

lineage:
  task_id: task_9
  run_id: run_17
~~~

## WorkIntent vs OperationIntent

Preserve the current class:

~~~text
WorkIntent
  = turn/durability/risk/execution-class classifier
~~~

Add:

~~~text
OperationIntent
  = immutable declarative semantic goal + constraints + authority reference
~~~

`WorkIntent` may determine whether a durable TaskRun/BrowserTask/worker is needed.
`OperationIntent` determines what transformation may be routed/executed.

Do not overload one with the other.

## Immutability

Canonical serialization must produce an `intent_hash`.

A TaskRun pins:

- OperationIntent artifact/ref;
- exact hash;
- schema version.

Changing the objective creates an explicit `IntentRevision` with parent intent,
reason, authority reference and new hash. Never silently reinterpret an active
intent after a reasoning wakeup.

# 2. Small Operational Intent IR

Use a deliberately small typed AST. Do not store arbitrary Python/JS predicates.

Initial predicates:

~~~text
TRUE
FALSE
EQ(path, value)
NEQ(path, value)
EXISTS(resource)
ABSENT(resource)
AND(...)
OR(...)
NOT(...)
IN(item, collection)
SUBSET(a, b)
LT / LTE / GT / GTE
UNCHANGED(path)
TRANSITION(path, before, after)
~~~

Initial semantic effects:

~~~text
SET(path, value)
CREATE(resource)
DELETE(resource)
MOVE(source, destination)
CALL(operation_family, target)
SEND(channel, target)
~~~

The IR must be:

- serializable;
- canonicalizable/fingerprintable;
- versioned;
- bounded;
- evaluable without LLM;
- safe to compare by implication/set inclusion rules;
- incapable of executing arbitrary code.

Start with deterministic normalization and a small entailment rule set. Do not add
an SMT solver unless real unsupported proof obligations justify it.

# 3. Capability formal contract

Extend existing OperationalCapability backward-compatibly with optional typed
routing metadata rather than creating another executable object.

Target typed contract:

~~~text
CapabilityContract
C = < target, inputs, P, R, F, Areq, Q, V, lifecycle/version >
~~~

Where:

- `P`: typed preconditions;
- `R`: deterministic implementation/transition;
- `F`: semantic effect footprint;
- `Areq`: required authority;
- `Q`: typed postconditions;
- `V`: verifier/evidence contract.

Recommended additive fields on OperationalCapability or a nested
`formal_contract`:

- `operation_family`;
- `target_family`;
- typed `precondition_predicates`;
- typed `postcondition_predicates`;
- `effect_footprint`;
- `authority_required`;
- `preserves`;
- `event_contract` (later Trigger slice).

Existing string pre/postconditions remain readable for legacy/manual capabilities.
They do not automatically become formal proof authority unless they are converted
through an owner-controlled adapter.

# 4. Intent and authority are independent

Execution requires both:

~~~text
IntentAllows(effect)
AND
AuthorityAllows(effect)
~~~

Never OR.

A user may possess broad credentials while the current intent permits only one
narrow effect. Conversely an intent may request an effect for which the trusted
authority/policy requires approval.

`MessageEnvelope.intent_authority` remains the ingress authority to create/
delegate/update work. Fine-grained execution authority is derived from trusted
MessageEnvelope metadata, existing policy/approval state and target/effect scope;
it is never deserialized from request prose.

Introduce a resource/effect authority partial order (or equivalent structured
comparison). Composition authority is monotonic:

~~~text
RequiredAuthority(plan)
= JOIN(RequiredAuthority(each node))
~~~

A read-only parent cannot hide a write child.

# 5. Capability Router

The Router is a deterministic proof engine/typechecker, not a new model loop.

Inputs:

~~~text
Route(
  OperationIntent I,
  SemanticState S,
  CapabilityLibrary L,
  Policy/Authority P,
  RuntimeState R
) -> RoutingDecision
~~~

Final decision kinds:

- `SATISFIED`;
- `EXECUTE`;
- `COMPOSE`;
- `WAIT`;
- `ASK_HUMAN`;
- `WAKE_LLM`.

Uncertain dispatched mutation is checked before candidate routing and enters the
existing reconciliation boundary. It must not be bypassed by a new plan.

Required decision order:

1. validate canonical TaskRun/run fencing and trusted intent/authority refs;
2. reconcile outstanding uncertain mutation before new mutation planning;
3. observe only semantic state required by the intent/candidate contracts;
4. if goal already holds -> SATISFIED;
5. try exact admitted Capability -> EXECUTE;
6. try bounded deterministic composition -> COMPOSE;
7. if only a future observable predicate is missing -> WAIT;
8. if only human authority/preference is missing -> ASK_HUMAN;
9. otherwise -> WAKE_LLM with minimal OpenCondition/AttentionPacket.

# 6. Candidate match vs execution admission

Internal candidate states:

- `EXACT_EXECUTABLE`;
- `POSSIBLE_MATCH`;
- `INCOMPATIBLE`;
- `NEEDS_REASONING`.

`POSSIBLE_MATCH` may justify deterministic observation/probing. It never grants
mutation authority.

Approximate retrieval/embeddings/semantic search may reduce a large catalog to a
small candidate set. They never participate in proof/admission.

Rule:

> **Approximate retrieval proposes. Symbolic admission authorizes.**

Capabilities must not be exposed as hundreds/thousands of model tool schemas.
Index internally by stable dimensions such as:

- target family;
- desired postcondition/effect keys;
- operation family;
- route/runtime;
- scope;
- lifecycle;
- semantic/compatibility fingerprint;
- typed precondition keys.

# 7. RoutingCertificate

An EXECUTE or COMPOSE decision is dispatchable only with a valid certificate.

Required proof obligations:

- target match;
- all required inputs bound;
- capability lifecycle/version healthy/pinned;
- preconditions observed and true;
- goal coverage;
- effect containment in Intent EffectBudget;
- invariant preservation;
- authority sufficiency;
- policy/approval satisfied;
- verifier/evidence capability sufficient for AcceptanceContract;
- state freshness/version;
- no outstanding relevant uncertainty;
- deterministic closure/no unresolved semantic branch.

Conceptually:

~~~text
Executable(I, C, S) :=
    TargetMatch(I,C)
 ∧  InputsBound(I,C,S)
 ∧  PreconditionsHold(C,S)
 ∧  GoalCovered(I,C)
 ∧  EffectsCovered(I,C)
 ∧  InvariantsPreserved(I,C)
 ∧  AuthoritySatisfied(I,C,S)
 ∧  PolicySatisfied(I,C,S)
 ∧  VerificationAvailable(I,C)
 ∧  StateFresh(S)
 ∧ ¬OutstandingUncertainMutation(I)
 ∧  CapabilityHealthy(C)
 ∧  OpenConditions(C,I,S) = empty
~~~

Public API invariant:

~~~text
¬CertificateValid => ¬Dispatch
~~~

No fallback like “certificate failed but it probably works”.

## Proof semantics

For a capability with precondition `P_C`, postcondition `Q_C` and intent goal
`G_I`:

~~~text
S |= P_C
Q_C => G_I
EffectFootprint(C) subseteq EffectBudget(I)
Transition(C) preserves Inv_I
RequiredAuthority(C) <= GrantedAuthority(I,S)
Verifier(C) >= Acceptance(I)
~~~

Do not claim proof over the unknowable future world. This certificate proves the
decision against a versioned observed SemanticState and declared contracts.
Critical preconditions must be revalidated immediately before side effects.

# 8. RoutingDecision types

Make misuse difficult through types.

Recommended shape:

~~~text
RoutingDecision
  |- SatisfiedDecision
  |- ExecutableDecision       # dispatchable
  |- ComposedDecision         # dispatchable
  |- WaitDecision
  |- HumanDecision
  |- ReasoningDecision
~~~

Only ExecutableDecision and ComposedDecision are dispatchable.

The dispatcher should accept a certified dispatchable decision, not a bare
Capability object.

Before mutable dispatch recheck at minimum:

- certificate hash;
- intent hash;
- state/resource version freshness;
- TaskRun fence;
- capability exact version;
- router policy version;
- approval/policy token/reference;
- critical preconditions.

If stale, invalidate certificate and re-route/reconcile; do not dispatch.

# 9. Router soundness properties

These properties are architectural invariants and test targets.

## Router Soundness

If:

~~~text
Router(I,S) = EXECUTE(C, bindings, cert)
~~~

then deterministic verification must establish:

~~~text
Applicable(C,S)
AND GoalCovered(I,C)
AND Effects(C) subseteq AllowedEffects(I)
AND PreservesInvariants(I,C)
AND RequiredAuthority(C) <= GrantedAuthority(I,S)
AND PolicyAllows(I,C,S)
AND InputsFullyBound(C)
AND Verifiable(C)
AND NoOutstandingUncertainty(I)
AND CertificateValid(cert)
~~~

## Goal Non-Expansion

~~~text
SemanticEffects(plan) subseteq Closure(Intent.effect_budget)
~~~

Uncovered effects block execution or require a new IntentRevision + trusted authority.

## Authority Non-Escalation

~~~text
AuthorityRequired(plan)
= JOIN(authority_required(each node))

AuthorityRequired(plan) <= GrantedAuthority(intent)
~~~

## Deterministic Closure

EXECUTE/COMPOSE requires no open semantic decision. Remaining branches must be
functions of deterministic observable predicates.

## Verification Closure

Required effect evidence must satisfy the intent AcceptanceContract. A capability
with weaker verification cannot execute simply because its action itself succeeded.

## Uncertainty Dominance

An unresolved dispatched mutation in the relevant resource/effect domain blocks
new mutation dispatch until reconciliation.

# 10. Deterministic composition

When no single Capability covers the goal, use bounded backward chaining over typed
postconditions/preconditions/effects.

Budgets:

- max composition depth;
- max nodes expanded;
- max candidates per predicate;
- max wall time;
- max risk/blast radius.

Exceeding budget yields WAKE_LLM, not unbounded planner search.

A `CompositionCertificate` must prove:

- initial state satisfies first unsupplied preconditions;
- every generated precondition has a producer or already holds;
- output/input types are compatible;
- causal links are valid;
- ordering constraints are explicit;
- no node invalidates a later required predicate (threat detection);
- union of effects fits EffectBudget;
- authority JOIN fits granted authority;
- approval closure holds;
- uncertain-effect/idempotency semantics are compatible;
- all intent invariants survive;
- final postconditions imply the intent goal;
- verifier coverage meets acceptance.

If absence of conflict cannot be proven, do not autoexecute.

# 11. Skills and capability families

Skills normally depend on semantic operation families:

~~~yaml
requires_family:
  - scm.pull_request.merge
~~~

not physical capability IDs.

Direct physical pins are reserved for cases where exact implementation identity
is semantically required (reproducibility/compliance/benchmark/pinned workflow).

Capability family/interface and implementation identity are separate:

~~~text
scm.pull_request.merge
  |- github.pull_request.merge
  |- gitlab.merge_request.merge
~~~

The implementation must satisfy the family contract under its own preconditions.

# 12. OpenCondition and AttentionPacket

The smallest reason to wake the LLM is a first-class `OpenCondition`, not the
entire failed workflow.

Example:

~~~yaml
type: SEMANTIC_GAP
proposition: strategy_for_merge_conflict == unknown

known:
  target: PR123
  conflicts: [fileA, fileB]

authority:
  modify_files: allowed

confirmed_effects: []
remaining_subgraph: [resolve_conflict, merge, verify]
state_refs: [artifact://...]
safe_to_resume: true
~~~

`AttentionPacket` contains:

- intent ref/hash;
- capability/plan/version;
- completed_until;
- confirmed effects/evidence;
- expected vs observed;
- exact OpenCondition;
- remaining subgraph;
- authority available;
- state refs;
- safe_to_resume.

The LLM proposes a resolution/intent refinement/plan fragment. That proposal
returns through Router admission. It never bypasses the typechecker.

Extend `reasoning_handoff.needs_reasoning` rather than creating an unrelated
handoff channel.

# 13. AwaitCondition and Trigger Plane

The persistent unit of waiting is **AwaitCondition**, not an event.

Conceptually:

~~~text
AwaitCondition =
< Predicate, Observer, Correlation, Continuation, Deadline, Fence, TemporalSemantics >
~~~

Kinds may include:

- WAITING_FOR_EVENT;
- WAITING_FOR_TIMER;
- WAITING_FOR_EXTERNAL_STATE;
- WAITING_FOR_HUMAN;
- WAITING_FOR_APPROVAL.

All use one underlying contract.

Persist enough to survive restart:

- wait_id;
- typed predicate;
- trusted observer kind/source;
- correlation/resource identity;
- continuation WorkPlan/node;
- task_id/run_id/operation_id fence;
- pinned capability/plan versions;
- created state/resource version;
- deadline/expiry;
- timeout policy;
- poll/backoff budget where required.

Do not create another Task/scheduler database. Store wait/continuation metadata
through existing canonical WorkPlan/TaskRun/Kanban/artifact owners.

## Trigger trust rule

A trusted trigger is:

~~~text
EventPattern
+ Trusted Observer
+ Correlation
+ State Predicate
~~~

Good observer sources include owner/runtime events, process supervisor, filesystem
watcher, authenticated webhook/API, structured Browser runtime, approval/human
lease, and internal clock.

Arbitrary page prose is not a trusted trigger/authority.

Rule:

> **Event wakes; authoritative state confirms.**

Before a mutable continuation, re-read the authoritative state and re-evaluate the
AwaitCondition predicate.

## CausalEventEnvelope

Extend RuntimeEvent/SystemEvent in a backward-compatible way or introduce a
shared normalized envelope carrying:

- event_id/type/schema version;
- source/trust class;
- task/session/run/operation lineage;
- resource identity;
- resource version/sequence;
- correlation id;
- root_event_id / parent_event_id;
- causal depth;
- observed_at;
- evidence ref;
- dedupe key / TTL.

Required protections:

- stale resource versions rejected;
- duplicate/coalesced events do not duplicate effects;
- debounce/rate limit;
- causal-depth bound;
- cycle/fixpoint detection;
- circuit breaker on no-progress trigger loops.

Uncorrelated system events remain observations and cannot create work intent.

# 14. Temporal semantics and polling

Typed temporal conditions:

- AT(timestamp);
- NOT_BEFORE(timestamp);
- DEADLINE(timestamp);
- AFTER(event, duration);
- UNTIL(predicate);
- WITHIN(predicate, duration);
- STABLE_FOR(predicate, duration);
- STABLE_FOR_N_OBSERVATIONS(predicate, n).

Timeout action is explicit: FAIL / ASK_HUMAN / WAKE_LLM / FALLBACK / CANCEL.

Prefer:

~~~text
durable authenticated signal/webhook
  > trusted runtime event
  > filesystem/process observer
  > bounded polling
~~~

Polling is deterministic infrastructure with:

- initial interval;
- exponential/backoff policy;
- max interval;
- deadline;
- max attempts;
- cost budget.

The LLM is not active while waiting.

# 15. Effectively-once mutable continuation

Do not claim universal exactly-once external effects.

Reuse canonical operation identity and uncertainty semantics:

~~~text
PREPARED
-> DISPATCHED
-> ACKNOWLEDGED
-> VERIFIED
-> COMMITTED
~~~

Loss after dispatch becomes UNCERTAIN.

Where supported, `operation_id` is the idempotency key. On restart:

- read durable dispatch/checkpoint state;
- reconcile authoritative external state;
- if already applied -> verify/commit;
- if definitely not applied and retry is safe -> retry under same operation contract;
- if unknown -> human/reconciliation;
- never blind retry.

# 16. Failure attribution

Preserve the RoutingCertificate so outcomes can distinguish:

- INTENT_ERROR;
- OBSERVATION_ERROR;
- ROUTING_ERROR;
- CAPABILITY_DRIFT;
- COMPOSITION_ERROR;
- POLICY_ERROR;
- RUNTIME_FAILURE.

A capability drift should not train the Router as if initial selection was wrong.
A routing mismatch should not automatically poison a valid capability.

# 17. Capability family deduplication / overspecialization

Redundancy detection uses normalized semantic contract, not name:

- target family;
- operation family;
- typed pre/postconditions;
- effect footprint;
- input schema/relations;
- authority/effect class;
- verifier family.

Preserve historical IDs through `family_id`, `alias_of`, `superseded_by`
or equivalent. Never rewrite old run lineage.

Split an over-general capability when branch/precondition complexity, drift,
conditional exceptions or holdout error indicates that specialized contracts
produce lower verified lifetime cost and higher predictability.

# 18. Operational Kernel boundary

Keep mechanism-level behavior in Kernel when changing that mechanism does not
change the capability's semantic contract.

Normally Kernel-level:

- scroll into view;
- focus;
- bounded readiness wait;
- stale-ref reacquisition;
- transport/session plumbing;
- filesystem atomic replace mechanics;
- process pipe mechanics;
- bounded transient retry that cannot duplicate mutable effects.

Normally Capability-level:

- merge pull request;
- rename/move semantic file;
- upload document;
- select account/option;
- change persisted customer property.

A useful test:

> Is there an independently meaningful pre/postcondition outside the mechanism?

If not, prefer Kernel.

# 19. Evaluation / economics

The control plane is successful only if it lowers **lifetime cost per verified
outcome**, not merely LLM call count.

Target metric family:

### Router quality
- Exact Reuse Precision;
- False Exact Match Rate;
- Missed Reuse Rate;
- Unnecessary LLM Rate;
- Wrong Capability Rate;
- Routing-Induced Drift;
- candidates examined p50/p95;
- lookup latency p50/p95;
- composition nodes/depth;
- Router CPU/wall time;
- recovery cost after wrong route;
- Router Regret.

### Trigger quality
- Wakeup Precision/Recall;
- missed wakeups;
- duplicate wakeups;
- stale-event acceptance;
- event-to-resume latency;
- polling/API/CPU cost per wait;
- event-loss recovery rate;
- trigger cycle/circuit-break rate;
- LLM waiting waste (target zero).

### Learning/runtime economics
- Operational Novelty Rate;
- Reasoning Amortization Ratio;
- break-even reuse count;
- Dead Capability Rate;
- deterministic replay rate;
- cross-task/cross-session reuse;
- drift/quarantine rate.

### Global objective

Minimize:

~~~text
Verified Outcome Lifetime Cost (VOLC)
=
  reasoning
+ routing/retrieval
+ compilation/validation
+ monitoring/waiting
+ deterministic execution
+ storage
+ drift recovery
+ maintenance
+ human intervention
------------------------------------------------
verified outcomes
~~~

subject to hard constraints:

- safety invariants;
- authority;
- correctness/evidence thresholds;
- uncertainty semantics;
- latency SLO.

Unknown denominators remain null. Do not fabricate token/cost savings.

# 20. Rollout strategy

Do not immediately authorize production mutations.

Stages:

1. **ADAPTIVE BASELINE** — current behavior.
2. **SHADOW ROUTER** — produce and verify certificates; do not control dispatch.
3. **LOW-RISK ROUTER** — read-only, temp filesystem, sandbox/reversible scopes.
4. **MUTATING ROUTER** — only after exact-match precision/evidence thresholds and
   existing approval/effect policies are proven.

Maintain kill switches for:

- automatic capability routing;
- automatic composition;
- trigger auto-continuation;
- mutating Router;
- automatic learning/promotion.

Fallback remains bounded adaptive reasoning.

# 21. Required implementation sequence

## CP0 — typed intent/effect IR and OperationIntent
1. implement canonical AST + normalization/hash;
2. implement immutable OperationIntent + IntentRevision;
3. preserve WorkIntent semantics;
4. bind authority_ref to trusted MessageEnvelope/policy sources.

## CP1 — formal capability contract
5. add backward-compatible typed formal contract fields;
6. implement target/effect/resource normalization;
7. implement authority lattice/join;
8. adapt learned/manual capabilities conservatively.

## CP2 — direct Router and certificates
9. build internal exact capability index;
10. implement candidate classification;
11. implement proof obligations and RoutingCertificate;
12. implement SATISFIED/EXECUTE/WAIT/HUMAN/REASONING decisions.

## CP3 — certified bounded composition
13. backward-chain over typed effects/preconditions;
14. implement budgets;
15. issue CompositionCertificate;
16. detect causal-link threats/conflicting effects;
17. prove effect/authority/invariant/verifier closure.

## CP4 — dispatch/preflight soundness
18. dispatcher accepts only certified dispatchable decisions;
19. pin intent/state/capability/router-policy versions;
20. revalidate critical state immediately before mutable side effects;
21. stale certificate reroutes/reconciles, never dispatches.

## CP5 — Await/Trigger Plane
22. persist AwaitCondition using existing owners;
23. normalize causal events;
24. implement restart-safe resume/fencing;
25. implement dedupe/stale/cycle/debounce/TTL;
26. implement deterministic polling/temporal conditions;
27. preserve uncorrelated-event observation-only rule.

## CP6 — minimal reasoning handoff
28. add OpenCondition/AttentionPacket to current reasoning_handoff;
29. return only unresolved segment;
30. confirmed effects/checkpoints are preserved;
31. LLM proposal returns through Router admission.

## CP7 — Skills and catalog routing
32. add semantic capability-family requirement metadata for Skills where useful;
33. do not pin physical IDs by default;
34. keep capability catalog internal/lazy;
35. optional approximate retrieval remains proposal-only.

## CP8 — evaluation and shadow rollout
36. extend EvaluationHarness with Router/Trigger/VOLC metrics;
37. add shadow comparison against adaptive baseline;
38. classify failure blame;
39. add holdout cross-instance/cross-session cases;
40. prove unknown denominators remain null.

## CP9 — integration / qualification
41. browser + filesystem + process routing;
42. wait/restart continuation;
43. one external-style mutation fixture with uncertainty reconciliation;
44. cross-backend composition;
45. full Workstation/Work100/Desktop gates;
46. document any native/live qualification not run.

# 22. Required behavior tests

At minimum prove:

1. OperationIntent contains desired state but no procedural implementation dependency.
2. WorkIntent remains backward-compatible.
3. intent hash is stable under canonical serialization and changes on semantic revision.
4. request/page prose cannot mint authority.
5. target mismatch rejects execution.
6. false precondition rejects execution.
7. postcondition that does not imply goal rejects execution.
8. goal-covered capability with one extra forbidden effect rejects execution.
9. intent permission without authority rejects execution.
10. authority without intent permission rejects execution.
11. invariant-breaking capability rejects execution even if goal is reached.
12. insufficient verifier/evidence level rejects execution.
13. outstanding relevant uncertain mutation blocks new mutation route.
14. POSSIBLE_MATCH can never be dispatched.
15. only valid ExecutableDecision/ComposedDecision types are dispatchable.
16. invalid/stale certificate cannot reach side-effect dispatcher.
17. state change between route and preflight invalidates certificate.
18. exact compatible capability yields EXECUTE with no operational-planning LLM call.
19. already-satisfied goal yields SATISFIED and no mutation.
20. deterministic future predicate yields WAIT rather than LLM.
21. authority/preference gap yields ASK_HUMAN.
22. semantic strategy gap yields WAKE_LLM with minimal OpenCondition.
23. LLM response cannot bypass Router re-admission.
24. composition proves Q1=>P2, Q2=>P3, final Q=>Goal.
25. composition effect union stays within EffectBudget.
26. composition authority is JOIN of all children.
27. conflicting intermediate effect/threat blocks or deterministically reorders plan.
28. composition search budget exhaustion wakes LLM rather than searching unboundedly.
29. Skill family requirement resolves implementation without pinning physical ID.
30. thousands of synthetic capabilities can be indexed/routed without adding model tools.
31. approximate retrieval candidate cannot execute without symbolic certificate.
32. AwaitCondition survives restart and resumes exact continuation under TaskRun fence.
33. stale/duplicate event does not duplicate mutable continuation.
34. event wakes but authoritative predicate false prevents continuation.
35. uncorrelated system event never creates work intent.
36. trigger cycle/no-progress trips circuit breaker.
37. polling uses bounded budget/backoff and zero LLM while waiting.
38. uncertain external-style dispatch reconciles before retry.
39. RoutingCertificate permits routing-vs-capability failure attribution.
40. Router/Trigger metrics expose known values and keep unknown denominators null.
41. shadow Router records would_execute/would_wait without controlling mutation.
42. existing Experience Compiler, Capability Runtime, TaskCompiler, Work100,
    approval, BrowserTask, TaskRun, journal and uncertainty contracts remain green.

# 23. Testing requirements

Follow repository root `AGENTS.md`.

Python tests must run through `scripts/run_tests.sh`, never direct pytest.

Add focused suites such as:

- `workstation/tests/test_operation_intent.py`;
- `workstation/tests/test_capability_router.py`;
- `workstation/tests/test_control_plane_composition.py`;
- `workstation/tests/test_await_trigger_plane.py`;
- extend `test_canonical_work_loop.py`, `test_events_pipeline.py`,
  `test_operational_capabilities.py`, `test_task_compiler.py`,
  `test_experience_compiler.py`, policy/approval and uncertainty owners.

Use behavior/property tests. Do not read source text in tests.

Recommended layers:

- deterministic unit contract tests;
- property-based tests for randomly generated intent/capability/state combinations;
- metamorphic tests;
- targeted mutation-test-style guard validation (or equivalent behavior
  counterfixtures if no mutation-test dependency is added);
- shadow/differential fixtures;
- full existing Workstation gate;
- `python workstation/work100.py --run`;
- Desktop/Electron gates only when affected.

# 24. Canonical properties to encode in tests

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

# 25. Prohibited shortcuts

Do not:

- replace current WorkIntent with OperationIntent;
- infer authority from user/page prose;
- let similarity/embedding score authorize execution;
- expose every Capability as a model tool;
- allow arbitrary Python/JS predicates in persisted intent IR;
- dispatch a bare capability without a certificate;
- let the LLM bypass Router after a reasoning wakeup;
- create a second TaskRun/Kanban/approval/event scheduler;
- let Trigger Plane create work from uncorrelated events;
- treat event arrival as proof the predicate is true;
- claim exactly-once for arbitrary external effects;
- blind-retry uncertain mutations;
- compose children then advertise a weaker parent authority;
- hide extra capability effects behind successful goal coverage;
- perform unbounded plan search;
- introduce SMT/embeddings/heavy planning dependencies before simple deterministic
  proof/index structures are insufficient;
- weaken existing Capability/Experience/TaskRun/BrowserTask/evidence contracts.

# Final target architecture

~~~text
Trusted ingress / Skill / Trigger
           |
           v
     OperationIntent
     + AuthorityRef
           |
     Semantic State
           |
           v
   Capability Router / Typechecker
           |
  +--------+---------+---------+----------+
  |                  |         |          |
SATISFIED          EXECUTE   COMPOSE     open gap
                     |          |          |
                     +----+-----+      +---+----------------+
                          |            |         |          |
                   Routing/Composition  WAIT   HUMAN     WAKE_LLM
                      Certificate       |                  |
                          |         AwaitCondition     AttentionPacket
                          |              |                  |
                          |        Event/Observer            |
                          |              |                  |
                          |        state confirms            |
                          +--------------+------------------+
                                         |
                                  Router re-admission
                                         |
                                         v
                                  Operational Kernel
                                         |
                                      verify
                                         |
                                  canonical commit
                                         |
                                  Experience Compiler
                                         |
                                  Capability Library
~~~

The control-plane optimization target is:

> **execute the cheapest proven deterministic path, wait without reasoning when
> time/state is the only missing input, ask humans only for human authority, and
> wake the LLM only for a genuine unresolved semantic decision.**

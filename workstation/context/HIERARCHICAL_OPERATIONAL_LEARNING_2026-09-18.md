# Hierarchical Operational Learning — Verified Action Knowledge and Reasoning Amortization

Date established: 2026-09-18  
Status: **CANONICAL ARCHITECTURE EXTENSION / IMPLEMENTATION OPEN**

Depends on:
- [PROGRESSIVE_OPERATIONAL_COMPILATION.md](PROGRESSIVE_OPERATIONAL_COMPILATION.md)
- [EXPERIENCE_COMPILER.md](EXPERIENCE_COMPILER.md)
- [VERIFIED_OPERATIONAL_CONTROL_PLANE.md](VERIFIED_OPERATIONAL_CONTROL_PLANE.md)
- [BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md](BROWSER_OPERATIONAL_ADMISSION_2026-09-18.md)
- [CANONICAL_EXECUTION_RELIABILITY_GATE.md](CANONICAL_EXECUTION_RELIABILITY_GATE.md)

This document records the architectural synthesis from the 2026-09-18 audit of
current `main`: Hermes Work already contains most of the correct substrate for
progressively reducing repeated LLM reasoning, but the product path does not yet
close the full loop from verified experience to routable learned knowledge,
hierarchical composition, non-resident waiting, and bounded reasoning wakeups.

The goal is **not** to replace the current architecture with a macro recorder.
The goal is to complete the architecture already present.

## Executive invariant

> **Hermes must learn not only facts about the world, but verified ways of acting
> on it. The more an operational transformation proves stable, causal, reusable
> and verifiable, the less reasoning should be required to execute it again.**

Equivalent lifetime loop:

~~~text
reason once
  -> observe
  -> prove
  -> compile
  -> reuse
  -> compose
  -> wait without reasoning
  -> wake only on unresolved semantic uncertainty
  -> learn again
~~~

The optimization target is **Operational Reasoning Amortization**: reduce new
reasoning required per verified outcome over the lifetime of the system without
weakening authority, evidence, drift, uncertainty or canonical completion rules.

## 1. Correct atomicity: smallest semantic closure, not smallest gesture

Hermes must not optimize toward the physically smallest automation.

The canonical atomic learned unit remains the Verified Operational Transition
(VOT):

> **the smallest semantically closed, parameterizable, executable and verifiable
> state transition with positive reuse value.**

Atomicity is therefore defined by meaningful state/effect closure rather than
primitive count.

Seven Browser actions may be one atomic operational capability if only the whole
segment has a meaningful precondition/postcondition/verifier boundary. Conversely,
one filesystem primitive may already be semantically closed.

Bad target:

~~~text
cap_click_1287
cap_focus_3911
cap_scroll_8204
~~~

Good target:

~~~text
prepare_chatgpt_session()
  pre: supported ChatGPT conversation state is reachable
  post: composer is semantically reacquired and ready for input
  verifier: authoritative browser semantic observation
~~~

The example is illustrative, not a site-specific hardcoded contract.

## 2. Canonical hierarchy

The runtime should converge toward the following hierarchy without introducing
new state owners:

~~~text
LEVEL 0 — Trusted Operational Primitives
  browser_navigate / snapshot / semantic click-fill / filesystem / process / ...

        ↓ verified experience

LEVEL 1 — Verified Operational Transitions / OperationalCapabilities
  semantically closed reusable transformations

        ↓ recurrent causal composition

LEVEL 2 — Composite OperationalCapabilities
  capabilities depending on capability families/versions plus bounded local steps

        ↓ recurrent stable composition

LEVEL 3 — Deterministic Workflows
  capability -> capability -> AwaitCondition -> capability -> verifier

        ↓ unresolved semantic degree of freedom only

LEVEL 4 — Reasoning Boundaries
  OpenCondition -> AttentionPacket -> WAKE_LLM -> proposal -> Router admission
~~~

The product of one compilation level becomes candidate vocabulary for the next.
This is **hierarchical operational learning**, not flattening.

## 3. What current main already proves

Current main already contains real pieces of this model:

- adaptive procedure traces and accepted-run projection;
- `TransitionSample`, semantic state/delta and provenance;
- Experience Corpus and automatic mining after accepted canonical completion;
- segmentation, cross-trace alignment and conservative anti-unification;
- dependency/Operational Slicing;
- explicit C0-C5 causal grades;
- controlled replay, safe ablation and counterexample refinement;
- `OperationalCapability`, Registry/Resolver and deterministic Operational Kernel;
- capability dependencies and bounded composition engine;
- `OperationIntent`, Router, certificates and reasoning handoff;
- `AwaitCondition`, causal event envelopes and TriggerCoordinator;
- durable WorkPlans/checkpoints and no-blind-retry uncertainty semantics.

Therefore this milestone must **extend and connect**, not recreate, these systems.

## 4. Confirmed integration gaps on current main

### 4.1 Learned capability -> semantic Router bridge is incomplete

The Experience Compiler emits an `OperationalCapability` containing learned
preconditions/postconditions, verifier contract, semantic/compatibility
fingerprints, provenance and causal metadata.

The Capability Router, however, only grants formal EXECUTE admission to
capabilities with `formal_contract`.

Current compilation does not conservatively derive/populate a
`CapabilityFormalContract` for the learned capability. Exact fingerprint reuse
therefore works while general semantic intent routing cannot automatically use
all promoted learned knowledge.

Required closure:

~~~text
verified experience
  -> learned OperationalCapability
  -> controlled replay / promotion admission
  -> typed formal contract
  -> Router index
  -> OperationIntent can select it
~~~

The formal contract must be derived only from trusted compiler/runtime evidence;
an LLM may not invent or upgrade execution authority.

### 4.2 Composition exists, but production execution and learned macro promotion differ

Current code already supports:
- capability dependencies;
- bounded backward-chaining `CompositionEngine`;
- `CompositionCertificate`.

Two distinct obligations remain:

1. **runtime truth:** a `ComposedDecision` must execute its certified plan for
   real or remain non-terminal; returning plan IDs is not execution;
2. **learning hierarchy:** repeated sequences of capability invocations are not
   yet mined and promoted as larger composite capabilities.

Do not conflate runtime composition with learned macro promotion.

### 4.3 Await exists, but non-resident continuation is not yet the canonical wait path

Current `TaskCompiler` can use `RuntimeEventBus.wait()` or bounded
`time.sleep()` polling. This avoids LLM token waste but retains a resident
worker/thread.

The persistent `AwaitCondition` / `TriggerCoordinator` contract already
contains the right semantics, but the production path still needs:

~~~text
WAIT
  -> persist AwaitCondition
  -> persist continuation reference / exact TaskRun + capability pins
  -> transition owner to WAITING
  -> release worker/executor
  -> event or scheduled observer fires later
  -> authoritative state readback
  -> predicate confirmed
  -> reconstruct continuation
  -> re-enter Router
  -> deterministic execution or WAKE_LLM
~~~

Polling remains a bounded observer fallback, not a resident semantic execution
loop.

Rule retained:

> **EVENT WAKES. AUTHORITATIVE STATE CONFIRMS.**

### 4.4 Control Plane seams must close before higher-level learning is trusted

The active Browser Operational Admission corrective P0 remains a dependency:
- false COMPOSE success must be removed;
- ACK must not become VERIFIED/COMMITTED without accepted verifier evidence;
- request/task/session presence must not mint broad authority;
- mandatory compilation must require operational closure;
- routed decision branches must use their actual dataclass contracts;
- mutation uncertainty remains dominant until reconciled.

Hierarchical learning may only build on truthful execution and verification.

## 5. Hierarchical Experience Compilation

Add a second observation vocabulary in addition to primitive TransitionSamples:
**CapabilityInvocation**.

A CapabilityInvocation should capture, at minimum:

- capability family/id + exact pinned version;
- semantic/compatibility fingerprint;
- typed bound inputs after redaction/sanitization;
- semantic state before/after;
- verified effect/postcondition;
- verifier/evidence refs and evidence strength;
- task/run/operation lineage;
- authority/policy scope actually used;
- duration/provider/runtime metrics;
- outcome, drift/uncertainty and counterexample information.

It must not persist transient browser handles, secrets or model reasoning.

The compiler may then observe traces such as:

~~~text
A -> B -> C
A -> B -> C
A -> B -> C
~~~

but recurrence only proposes a candidate. Promotion requires the same class of
proof as atomic learning:

- semantic closure;
- stable parameterization and parameter relations;
- causal/dependency support;
- stable pre/postconditions;
- effect union closure;
- monotonic authority JOIN closure;
- verifier closure;
- cross-run diversity;
- positive reuse/compression utility;
- controlled replay in an admissible environment;
- counterexample handling and drift policy.

The default composite representation should preserve child dependencies rather
than flattening their primitive implementations. This allows a child capability
to drift/version/quarantine independently.

## 6. Formal-contract derivation for learned capabilities

A learned capability may become Router-visible only when the compiler can derive
a conservative typed contract from existing trusted evidence.

Derive:
- `operation_family` from stable observed operation families;
- `target_family` from stable observed target families;
- typed preconditions from stable semantic predicates;
- typed postconditions from verified effects;
- effect footprint from the canonical effect taxonomy and learned target/effect;
- authority requirement from actual trusted authority used by successful samples,
  never from request prose or capability self-assertion;
- verifier from the existing verifier contract/evidence threshold;
- optional event contract only when the runtime owns a stable event condition.

If any required field cannot be proven, the candidate remains exact-reuse-only or
requires reasoning; missing proof must not be guessed.

## 7. Durable wait/continuation contract

`AwaitCondition.continuation` must become an executable durable continuation
reference rather than inert metadata.

Continuation must be reconstructible without transcript replay and fenced to:
- canonical task_id;
- run_id;
- operation_id;
- intent hash/revision;
- exact capability pins/contracts;
- last verified semantic state/evidence refs;
- remaining subgraph;
- deadline/timeout action.

Trigger satisfaction must not itself mark work completed. It only authorizes
re-entry into control flow after authoritative state confirms the predicate.

A process restart while waiting must preserve the condition and continuation.

## 8. Reasoning boundary

The LLM remains necessary for:
- novel strategy;
- ambiguous intent;
- creation/evaluation;
- unrepresentable primitive gap;
- drift requiring semantic adaptation;
- authority/human choice;
- counterexamples not discriminable by deterministic predicates.

It should not remain active for:
- known navigation/setup;
- known target reacquisition;
- deterministic fill/click/send mechanics;
- stable repeated transformations;
- waiting for external events;
- mechanical verification/readback;
- deterministic composition already certified.

The canonical cycle is:

~~~text
LLM interprets unresolved semantics
  -> Router
  -> deterministic capability/composition
  -> AwaitCondition if needed
  -> executor released
  -> event/state confirmation
  -> Router
  -> deterministic continuation
  -> WAKE_LLM only if an OpenCondition remains
~~~

## 9. Metrics — Operational Reasoning Amortization

Add a first-class metric family complementing VOLC.

Primary ratio:

~~~text
ORA =
  verified semantic state transitions executed with zero LLM intervention
  -----------------------------------------------------------------------
  total verified semantic state transitions
~~~

Track without fabricating unknown denominators:

- LLM calls / verified outcome;
- LLM calls / verified transition;
- exact capability reuse rate;
- Router-mediated capability reuse rate;
- deterministic composition rate;
- composite-capability reuse rate;
- WAITs that fully released the executor;
- worker-seconds / wall-clock waiting;
- WAKE_LLM rate and reason:
  novelty | drift | ambiguity | authority | unrepresentable primitive |
  verifier failure | reconciliation;
- capability drift/quarantine rate;
- experience -> candidate rate;
- candidate -> replay-validated rate;
- candidate -> promoted rate;
- promoted -> reused rate;
- hierarchical candidate/promotion rate.

Success means ORA rises and LLM calls per verified transition fall **without**
degrading verification quality, increasing unresolved uncertain mutations or
hiding drift.

## 10. Implementation sequence

### P0 — Truthful Control Plane closure

Complete the already-open Browser Operational Admission P0 before trusting higher
levels:
- real COMPOSE execution or explicit non-terminal state;
- evidence-gated dispatcher commit;
- trusted authority origin only;
- operational-closure-aware mandatory compilation;
- branch/dataclass contract fixes;
- exact-head product qualification.

### P1 — Experience Compiler -> Router bridge

- derive and persist `CapabilityFormalContract` for eligible learned candidates;
- preserve exact fingerprints and immutable versions;
- index promoted learned capabilities in CapabilityRouter;
- prove OperationIntent can route to a learned capability without an LLM;
- fail closed when typed contract/effect/authority/verifier cannot be proven.

### P2 — Non-resident Await/Continuation

- make persistent AwaitCondition the canonical semantic wait owner;
- persist an exact continuation reference;
- release worker/executor while waiting;
- resume after causal event + authoritative state confirmation;
- implement scheduled bounded polling only as observer fallback;
- prove restart-safe wait/resume and stale-event rejection.

### P3 — Hierarchical Experience Compiler

- capture CapabilityInvocation traces;
- align/group recurring compatible capability sequences;
- infer candidate composite boundaries using semantic closure, not frequency alone;
- reuse causal slicing/counterexamples/replay/promotion policy;
- emit dependency-based composite OperationalCapabilities;
- preserve child version/fingerprint pins and drift propagation.

### P4 — Reasoning amortization evaluation and rollout

- add ORA/transition-level metrics;
- shadow-evaluate hierarchical candidates first;
- low-risk deterministic reuse before mutable composition promotion;
- dogfood Browser example such as repeated ChatGPT turns without hardcoding
  ChatGPT-specific architecture.

## 11. Non-goals / anti-patterns

Do not:
- create one capability per click/tool call by default;
- treat recurrence as causality;
- flatten every composite into a monolithic script;
- use raw CSS selectors/transient refs as durable identity;
- let an LLM certify its own learned capability;
- promote page-provided prose into trusted authority/effects;
- create a second capability registry, scheduler, task DB, BrowserTask store,
  journal, memory system or control plane;
- use blocking sleep/polling as the semantic default for long waits;
- perform destructive production ablation merely to improve causal confidence;
- mark trigger reception itself as verified completion.

## 12. Hard acceptance properties

The milestone is not closed until all are behaviorally proven:

1. A promoted learned capability with a compiler-derived formal contract can be
   selected by `OperationIntent -> CapabilityRouter` and executed with zero
   intermediate LLM calls.
2. A certified `ComposedDecision` either executes and independently verifies
   every required step/capability or remains non-terminal; no plan echo can commit.
3. ACK-only execution cannot become VERIFIED/COMMITTED unless the formal
   acceptance contract explicitly permits that evidence level.
4. WAIT persists a continuation, releases the worker, survives process restart,
   rejects stale/duplicate events and resumes only after authoritative predicate
   confirmation.
5. A repeated capability sequence can become a dependency-based composite
   candidate, but passive frequency alone cannot promote it.
6. Child capability drift/version changes invalidate or revalidate affected
   composites without destroying unrelated learned knowledge.
7. ORA and LLM-calls-per-verified-transition are measurable with unknown values
   remaining null rather than fabricated.
8. No new canonical state owner is introduced.

## Summary

This milestone does not replace Progressive Operational Compilation, the
Experience Compiler or the Verified Operational Control Plane. It completes the
relationship among them:

~~~text
Experience
  -> VOT
  -> OperationalCapability
  -> Composite OperationalCapability
  -> Deterministic Workflow
  -> Await/Event
  -> Reasoning Boundary
~~~

Hermes becomes more operationally capable not by storing more macros, but by
turning previously reasoned actions into increasingly reusable, causally supported
and verifiable operational knowledge.

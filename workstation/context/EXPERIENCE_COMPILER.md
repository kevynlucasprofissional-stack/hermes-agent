# Experience Compiler — From Traces to Verified Operational Capability

## Native product evidence audit — 2026-09-23

Real Hermes Work browser use confirms an important distinction:

```text
capture pipeline works in production
!=
Experience Compiler has produced a real product capability
```

Observed native sessions already produce transition/trace artifacts and adaptive-observation events, but the sampled outcomes remain uncertain/inconclusive with insufficient evidence. Consequently the canonical corpus/compiler gates correctly refuse to treat them as reusable knowledge.

The next implementation goal is **not** to make mining permissive. It is to close a verified product path into the existing compiler:

```text
trusted post-effect observer
-> canonical verified completion
-> ExperienceCorpus accepted segment
-> ExperienceCompiler candidate
-> controlled replay / verifier validation
-> existing promotion policy
```

For Browser, a valid learned effect may describe Workstation-owned browser state rather than an external resource mutation. Example: native BrowserTask reaches `chatgpt.com`, remains owned by the intended task/tab, and the controller reports stable readiness after the effect. This evidence must be typed/trusted honestly and must not be reused to claim login or third-party persistence.

Executable output remains **OperationalCapability**. Do not add a parallel script/skill object. If browser implementation steps later require richer representation, introduce a typed BrowserProcedureIR only inside `OperationalCapability.implementation` and keep execution behind the existing certified Browser path.

The first native-product qualification for this document is now defined by the H-080B vertical E2E in:
[engineering-journal/h080b-real-use-experience-loop-audit-2026-09-23.md](engineering-journal/h080b-real-use-experience-loop-audit-2026-09-23.md).

## H-076 integration — learn transformation and verifier separately (2026-09-19)

H-076 now preserves **how to verify again**: observer/source/extractor, relation and
canonicalizer version, temporal signal, failure-domain provenance, predicate coverage,
validation receipts and verifier fingerprint.

The implemented corrective milestone is
[VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md](VERIFICATION_CONTRACT_SYNTHESIS_2026-09-19.md).

Experience Compiler must therefore split learning into two hypotheses:

~~~text
action hypothesis
verifier hypothesis
~~~

Discovery traces may propose both. They do not validate both. Verifier promotion
requires discriminative evidence/negative controls where safely possible, and action
C0-C5 causal grade remains separate from verifier quality. A controlled replay cannot
upgrade a capability/action pair when its oracle is inadmissible.

Date established: 2026-09-18

Status: **IMPLEMENTED / CONTRACT VALIDATED — native product qualification separate**

## H-075 implementation boundary — 2026-09-19

EC6 distinguishes run-local ephemeral compiled segments from global promotion, but
current-main does not yet operationally hand newly verified adaptive repetition into
the existing DurableBatchRunner/TaskCompiler path before TaskRun completion.

browser_console is intentionally excluded by procedure_trace.candidate_steps; opaque JS
must lower to typed primitives or independently instrumented trusted semantic events.

See [IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md](IN_FLIGHT_OPERATIONALIZATION_2026-09-19.md).
Verified prefixes remain valid evidence but do not bypass global promotion admission.

## Implementation evidence — 2026-09-18

Base: `2479b712f8a3912ff6df9066d1782e8b407b4177`. Implementation is in
`workstation/experience_compiler/`; executable output remains OperationalCapability.
The corpus is a rebuildable ArtifactStore/ExecutionJournal projection. Capture
normalizes semantic anchors before fingerprinting; deterministic replay requires
one exact, uniquely reacquired live control. Ambiguous controls fail closed.

EC0–EC8 now cover bounded semantic browser/filesystem/process projections,
ordered transition samples, closure/segmentation/alignment, conservative typed
anti-unification and parameter relations, positive/negative action models,
reverse dependency slices, separate C0–C5/E0–E3, owner-controlled replay/ablation,
immutable counterexample revisions, independent learned promotion and durable
WorkPlan metadata pins. Candidate consolidation uses exact compatibility and
positive compression/reuse utility. Conditional steps observe state again;
optional observations do not become mandatory actions.
Automatic mining associates success and failure segments by operation/target
family, canonical route/runtime and scope. Missing predicates are unknown evidence,
not a discriminating negative value. Candidate provenance retains source sample
artifact URIs, including counterexamples. Banner presence is a boolean state flag;
actual cookies/credentials remain excluded by the canonical sanitizer.
The capability path in `work_execute` retains durable result checkpoints and uses
the existing reference plane for blobs/large outputs, including confirmed resume.
Unresolved/redacted legacy observation bindings remain corpus evidence; they cannot
become literal executable steps. Owner binding evidence is required before compiling
those samples. Existing declared manual capability variables remain supported.

Canonical completion projects accepted final readback into the corpus and mines
candidates after commit. A failed learning projection cannot undo accepted work.
Ordinary adaptive observations default to environment-origin runtime observations,
not trusted promotion authority. Owner-provided provenance, isolated reset-per-trial
fixtures and verified evidence are required to cross that boundary. Interventions
are explicit owner APIs, never model-provided scripts or production experiments.

Learned browser and real temporary-filesystem replay, a real subprocess readback,
learned filesystem/process composition and atomic reuse in two larger flows are
covered by `test_experience_compiler.py`. Paid-provider cost, global coverage and
novelty are unknown when no trustworthy denominator exists; metrics return null.
No live third-party mutations or destructive ablations were performed. C5 needs
distinct owner-controlled compatible contexts, never passive repetition.

Exact commands/results and native NOT RUN scope are maintained in
[TESTING.md](TESTING.md) and [H-068](engineering-journal/CURRENT.md).

Depends on:
- [ADAPTIVE_EXECUTION_COMPILATION.md](ADAPTIVE_EXECUTION_COMPILATION.md)
- [PROGRESSIVE_OPERATIONAL_COMPILATION.md](PROGRESSIVE_OPERATIONAL_COMPILATION.md)
- [CANONICAL_EXECUTION_RELIABILITY_GATE.md](CANONICAL_EXECUTION_RELIABILITY_GATE.md)

The Progressive Operational Compilation milestone established the deterministic
runtime substrate: semantic operation fingerprints, OperationalCapability,
OperationalCapabilityRegistry/Resolver, Operational Kernel, direct
`work_execute(capability_id, inputs)`, deterministic composition and bounded
`NEEDS_REASONING` drift handoff.

This document defines the next boundary: **how Hermes converts real adaptive
experience into trustworthy OperationalCapabilities without asking an LLM to
re-summarize or re-plan the trace.**

## Hierarchical continuation — learned capabilities become learning vocabulary

The implemented EC0-EC8 pipeline closes the primitive/adaptive-trace to
OperationalCapability path. As of 2026-09-19, the hierarchical continuation extension specified in
[HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md](HIERARCHICAL_OPERATIONAL_LEARNING_2026-09-18.md)
is fully implemented and qualified:

1. **Router bridge (Implemented)**:
   `derive_formal_contract(capability)` in `workstation/experience_compiler/promotion.py`
   conservatively derives a typed `CapabilityFormalContract` from trusted observed families,
   semantic pre/postconditions (as IR `EQ`), canonical effects (as IR `SET`/`CALL`),
   actual proven authority scope from provenance, and verifier requirements. If those facts
   cannot be proven, derivation returns `None` and the capability remains exact-reuse-only.
   The CapabilityRouter index is dynamically rebuilt to index promoted learned capabilities,
   enabling deterministic semantic routing via `OperationIntent`.
2. **Hierarchical mining (Implemented)**:
   `OperationalKernel` captures verified `CapabilityInvocation` observations (`workstation/experience_compiler/models.py`).
   `HierarchicalExperienceCompiler` (`workstation/experience_compiler/hierarchical.py`)
   mines recurring capability sequences (`mine_sequences`) across distinct runs and proposes
   composite capabilities (`propose_composite`). Promotion strictly enforces causal JOIN,
   monotonic authority JOIN, verifier closure, and positive utility.

The composite representation preserves child capability
dependencies/version pins (`CapabilityDependency`) rather than flattening every primitive step. This
allows localized drift/quarantine to propagate fail-closed without corrupting the rest of the catalog.

The canonical hierarchy is:

~~~text
TransitionSample / trusted primitive experience
  -> VOT / OperationalCapability
  -> CapabilityInvocation traces
  -> Composite OperationalCapability
  -> deterministic workflow
~~~

## Executive invariant

> **Hermes must not memorize what it did. It must learn what it knows how to do.**

A trace is evidence, not a procedure. A repeated sequence is a hypothesis, not a
capability. A capability is promoted only when the runtime can establish a
semantic state transition, parameterize it, verify its result, constrain its
authority, and support enough evidence that deterministic reuse is justified.

The core learning rule is:

> **Observation proposes. Repetition generalizes. Counterexample refines.
> Intervention validates. Evidence promotes.**

## Canonical atomic unit: Verified Operational Transition

The smallest reusable operational unit is not a Tool call, script or whole
workflow. It is the smallest **semantically closed, parameterizable, executable
and verifiable state transition with positive reuse value**.

Conceptually:

~~~text
VOT / OperationalCapability
C = < I, Theta, Pi, T, E, V, A, R, F >
~~~

Where:

- `I` — initiation/preconditions: observable state class in which execution is valid;
- `Theta` — typed parameters and relations between them;
- `Pi` — deterministic policy/graph/FSM/DAG composed from trusted primitives/capabilities;
- `T` — termination condition;
- `E` — semantic effect/postcondition;
- `V` — verifier and required evidence strength;
- `A` — effect/authority scope and approval requirements;
- `R` — drift/recovery/reconciliation contract;
- `F` — stable semantic/compatibility fingerprint.

Atomicity is **not** the number of primitive actions. Seven UI operations may form
one atomic capability if only the complete segment has a meaningful independent
postcondition. Conversely one filesystem primitive may already be semantically
closed.

Atomicity test:

> Can the runtime determine when this operation may start, execute it without LLM
> interpretation, and determine by evidence whether it ended correctly?

If not, the unit is not yet a complete OperationalCapability.

## Effect boundary defines the reusable boundary

Capability segmentation should prefer boundaries around meaningful observable
effects rather than around tool names or arbitrary step counts.

Examples:

~~~text
browser.fill_field(field, value)
  post: field.value == value
  evidence: same-session semantic observation

customer.change_email(customer_id, value)
  post: persisted customer.email == value
  evidence: persisted readback
~~~

The first can be an atomic UI-local capability. The second is a larger capability
whose closure is the persisted business effect.

## Historical implementation baseline on main before EC0–EC8

As of main after PR #26, the deterministic capability substrate exists:

- `workstation/execution_policy.py` has `semantic_target_family()` and
  `semantic_operation_fingerprint()`;
- `workstation/operational_capabilities.py` has OperationalCapability,
  lifecycle, registry, resolver, composition dependencies and drift quarantine;
- `workstation/operational_kernel.py` executes deterministic browser/filesystem
  primitives without intermediate LLM calls;
- `work_execute` accepts `capability_id`, version and typed inputs;
- native Electron browser actions expose structured target metadata;
- TaskCompiler can resolve/reuse exact promoted capabilities.

The missing layer is automatic **experience compilation**.

### Concrete gaps reproduced at the baseline and addressed by this milestone

1. `workstation/procedure_trace.py` remains primarily an action log. It stores
   before/after artifact refs but does not normalize them into semantic
   state-before/state-after predicates plus a semantic delta.
2. `record_trace()` can derive a semantic anchor from the previous browser
   inventory, but computes `semantic_operation_fingerprint(name, args)` from the
   original call arguments. Ref-only browser actions can therefore still fall
   back to a structural fingerprint even after a stable anchor was discovered.
3. `record_trace()` may derive anchor `type="name"`, while
   `candidate_steps()` currently admits only `role_name`, `testid` and
   `text`; this can make semantically useful browser observations unreplayable.
4. Current learning remains approximately:
   `trace -> candidate_steps() -> RoutinePromotionService.experience_candidate()`.
   It does not first discover operational slices, cross-trace structure,
   parameter relations or causal support.
5. `OperationalCapabilityRegistry.record_validation(...,
   auto_promote_threshold=2)` can promote from count-based validation. That
   generic mechanism must not by itself authorize auto-promotion of
   experience-learned mutable capabilities.
6. No first-class Experience Corpus / TransitionSample mining pipeline currently
   owns segmentation, alignment, anti-unification, invariant inference,
   dependency slicing, causal grades, safe ablation or counterexample refinement.
7. The current registry resolves capabilities by exact promoted identity, but
   learned-capability promotion does not yet carry a trust/taint-aware causal
   admission contract.

These were the implementation gaps. The milestone extends the existing runtime.

## TransitionSample: trace becomes a semantic transition log

Capture rate should be high; promotion rate should be low.

Every suitable action can produce a normalized observation:

~~~text
TransitionSample
  sample_id

  state_before
    artifact_ref
    semantic_predicates

  operation
    primitive
    canonical_route
    target_instance
    target_family
    operation_family
    parameters
    effect_class

  state_after
    artifact_ref
    semantic_predicates

  delta
    added_predicates
    removed_predicates
    changed_values

  verification
    evidence_strength
    verifier
    verified_predicates
    evidence_refs

  outcome
    verified_success | failed | uncertain | interrupted

  provenance
    task_id
    run_id
    operation_id
    runtime/source
    authority_origin
    trust_class
    taint

  metrics
    duration
    provider_usage
    tool_calls
~~~

Transient refs, WebContents ids, tab ids, secrets, cookies and credentials are
observations only and must not become durable semantic identity.

## Semantic State Abstraction

The compiler must not fingerprint complete DOMs/screenshots/filesystems. It needs
a bounded semantic projection containing only predicates relevant to the
candidate operation.

Example:

~~~text
physical page
  url, DOM, scroll, banners, timestamps, thousands of nodes

semantic state
  site = github
  page_family = pull_request
  pr_id = $PR
  pr_state = open
  mergeable = true
  merge_control_available = true
  authenticated = true
~~~

State abstraction must be owner/runtime-derived when possible. Untrusted page
prose must not become authoritative mutation semantics.

## Experience Compiler pipeline

The target provider-free pipeline is:

~~~text
ObservedTrace
  -> TransitionSample normalization
  -> Semantic State Abstraction
  -> Transition Graph
  -> Candidate Boundary Detection
  -> Cross-Trace Clustering / Alignment
  -> Parameterization / Anti-Unification
  -> Invariant + Action-Model Inference
  -> Dependency Slice / Operational Slice
  -> Safe Replay / Intervention / Ablation
  -> Counterexample Refinement
  -> OperationalCapability Candidate
  -> Validation
  -> Promotion
~~~

LLM reasoning is not required on the successful consolidation path. An LLM may
help diagnose a novel drift outside the compiler, but must not be the authority
that decides a learned capability is safe/promoted.

## 1. Boundary discovery

Use multiple deterministic/statistical signals rather than one threshold:

- semantic state delta;
- effect/commit boundary;
- verification/readback boundary;
- page-family or backend transition;
- reusable input/output boundary;
- recurring bottleneck/subgoal state;
- branch conditioned on an observable predicate;
- handoff/authority boundary;
- statistical changepoint;
- recurrence across compatible traces;
- negative weight for transient-only changes.

No single signal grants promotion.

## 2. Cross-trace clustering and alignment

A single successful trace creates a hypothesis only.

Group compatible traces by stable route/runtime/operation-family/effect/scope
metadata. Align variations so nodes can be classified as:

- `core`;
- `conditional`;
- `optional`;
- `anomalous/recovery-only`.

Do not require byte-identical sequences. Learned models may be linear graphs,
DAGs or finite-state machines.

## 3. Parameterization by structural generalization

Repeated instances must become typed parameters rather than separate memories.

Example:

~~~text
PR 123: navigate -> merge -> confirm -> verify
PR 891: navigate -> merge -> confirm -> verify

generalizes to:
github.merge_pull_request(repo, pr_number)
~~~

The compiler should anti-unify stable structure and replace varying instance data
with parameters. It must also infer relations between parameters where supported,
for example:

~~~text
basename(destination) == basename(source)
requested_email == persisted_email
repo_before == repo_after
~~~

Secrets are never parameters stored in provenance or fingerprints.

## 4. Preconditions, effects and branches

Candidate preconditions begin conservatively from predicates observed before
success. They are weakened only when new positive evidence demonstrates a
predicate is unnecessary.

Candidate effects come from stable semantic deltas, not every observed physical
change.

An action present only when predicate P holds should become a conditional branch,
not an arbitrary optional step, when the evidence supports:

~~~text
P(action | P) high
P(action | not P) low
~~~

Failures and drift are negative examples and are required inputs, not noise.

## 5. Dependency slicing / Operational Slice

For a target postcondition, build data/control/effect dependencies and reverse
slice the trace to the steps that can influence the verified effect.

Definition:

> **Operational Slice = the smallest supported subgraph of the observed
> execution that is needed to obtain a specific postcondition from a class of
> admissible initial states.**

Steps with no dependency path to the postcondition are candidates for removal or
for lowering into an Operational Kernel primitive.

## 6. Observational evidence is not causal proof

Passive traces can establish recurrence and correlation, not general causal
necessity.

The compiler must explicitly separate:

~~~text
OBSERVATIONAL MINING
  pattern exists?
  pattern generalizes?
  positive/negative evidence?
  dependency support?

INTERVENTIONAL VALIDATION
  does replay reproduce the effect?
  can a step be removed without losing the postcondition?
  does the model remain invariant across parameters/states?
~~~

Never report causal proof from recurrence alone.

## Causal evidence grades

Use an explicit causal/evidence ladder for learned capabilities:

- `C0` — one observation;
- `C1` — recurrent across successful traces;
- `C2` — discriminative evidence against failures/counterexamples;
- `C3` — controlled compatible replay reproduces verified effect;
- `C4` — safe ablation/delta reduction supports step necessity/minimality;
- `C5` — invariance confirmed across materially different compatible
  states/parameters/environments.

This grade is separate from existing E0-E3 evidence strength. E0-E3 answers
"how strongly was this effect verified?". C0-C5 answers "how strongly is this
learned operational model supported as reusable/causal?".

Both dimensions matter.

## 7. Safe replay and ablation

When the environment is safe/reversible, apply bounded replay and delta reduction
to candidate slices.

Allowed examples:

- test fixtures;
- temporary filesystem;
- synthetic/test repositories;
- read-only flows;
- reversible local mutations;
- explicitly provisioned staging/sandbox;
- bounded ephemeral browser state.

Do **not** perform destructive causal experiments merely to improve a capability
on real production data, external communications, financial actions, irreversible
deletions, publication or other high-impact effects.

Unsafe-to-ablate candidates may remain conservative and require stronger passive
evidence and/or human policy approval.

## 8. Counterexample-guided refinement

Failure and drift should refine the smallest false assumption:

~~~text
candidate
  -> replay/use
  -> counterexample
  -> refine precondition / branch / parameter relation / effect / verifier
  -> new immutable version candidate
~~~

Never silently rewrite a historical promoted version in place.

## Trust boundary: Experience -> persistent Capability

Experience can contain untrusted external influence. Therefore every
TransitionSample and learned candidate must carry provenance and taint.

At minimum classify:

~~~text
origin/runtime/source
authority_origin = system | user | environment | page-provided
trust_class
taint.untrusted_instructions
taint.external_content_dependency
source/evidence refs
~~~

Frequency does not convert untrusted page instructions into trusted operational
policy.

A learned precondition/effect must come from trusted runtime state/evidence or an
explicit user/system contract, not merely from prose that the page told the agent
to follow.

## Promotion admission: capture nearly everything, promote very little

~~~text
capture rate -> high
candidate rate -> lower
promotion rate -> much lower
~~~

Count-based success is not sufficient for learned mutable capabilities.

The Experience Compiler must own a promotion admission policy that considers:

- semantic closure;
- exact compatibility;
- parameterization/generalization;
- E0-E3 effect evidence;
- C0-C5 causal grade;
- provenance/trust/taint;
- effect/risk/blast radius;
- cross-run diversity;
- replay result;
- drift/failure rate;
- expected reuse/compression utility;
- approval/policy requirements.

`OperationalCapabilityRegistry.record_validation()` may remain a generic registry
primitive, but Experience Compiler candidates must not obtain mutation authority
from its raw success threshold alone.

Default target policy:

- observations/candidates do not autoexecute globally;
- C3 is the minimum target for ordinary learned auto-replay;
- higher-impact external mutations should normally require C4 or stronger plus
  the existing approval/effect policy;
- operations that cannot be safely validated remain conservative/manual-policy
  admitted;
- all existing approval, TaskRun, lease, uncertainty and canonical-commit rules
  remain authoritative.

## Utility / anti-explosion policy

The smallest possible sequence is not always the best reusable unit.

A candidate should have positive expected utility:

~~~text
Utility(C) =
  P(reuse) *
    (reasoning_cost_saved + context_cost_saved + planning_latency_saved)
  - validation_cost
  - retrieval_cost
  - execution_overhead
  - maintenance_cost
  - P(drift) * drift_cost
  - risk * blast_radius
~~~

A simpler Minimum-Description-Length style gain may be used as a deterministic
proxy:

~~~text
Gain(C) =
  cost(raw traces represented)
  - cost(capability definition + invocations + validation + maintenance/risk)
~~~

This prevents a registry full of near-duplicate micro-capabilities and prevents
over-large workflows from hiding reusable atomic units.

## Capability graph and library stability

The capability library is a DAG/grammar, not a flat macro list.

Atomic capabilities remain independently reusable when referenced by larger
composites.

A TaskRun should execute against a stable capability snapshot/version view. New
experience may create candidate revisions during the run, but must not silently
change the meaning of a capability already selected for that run.

A bounded **ephemeral compiled segment** may be reused inside the current
TaskRun after local verification without becoming a globally promoted capability.

## Resolver boundary

Learning and resolving are different problems.

Candidate retrieval may use broad/approximate similarity to find possible
capabilities. **Admission remains strict and deterministic** and must verify:

- promoted/current version;
- route/runtime;
- semantic operation/target family;
- scope;
- preconditions;
- effect/authority;
- approval policy;
- compatibility fingerprint;
- drift state.

Similarity never grants mutation authority.

## Proposed code ownership

Extend existing owners. Do not create a second memory/task/evidence database.

Target package:

~~~text
workstation/experience_compiler/
  transition_samples.py
  state_abstraction.py
  segmenter.py
  corpus.py
  trace_alignment.py
  anti_unification.py
  invariant_learning.py
  action_model.py
  dependency_graph.py
  causal_validation.py
  delta_reducer.py
  counterexample_refinement.py
  utility.py
  promotion.py
~~~

Exact module count may be reduced if simpler ownership is clearer. The package
must compose existing:

- ExecutionJournal / ArtifactStore;
- procedure trace capture;
- `tools.effects`;
- semantic Browser metadata;
- RecipeStore / ProceduralMemory;
- OperationalCapabilityRegistry / CapabilityResolver;
- Operational Kernel;
- TaskCompiler / work_execute;
- TaskRun/BrowserTask/approval/evidence authority.

## Required implementation sequence

### EC0 — fix transition identity at capture

1. turn procedure trace observations into a normalized TransitionSample contract;
2. fix browser semantic fingerprint derivation so a derived stable anchor/target
   participates in the fingerprint instead of falling back to structural shape;
3. make semantic anchor types consistent between capture and replay
   (`name` vs admitted anchor types);
4. preserve transient-ref redaction and bounded trace capture.

### EC1 — semantic state + provenance

5. implement bounded per-backend semantic state abstraction;
6. compute semantic deltas;
7. attach evidence strength, lineage, trust class and taint.

### EC2 — corpus, segmentation and pattern discovery

8. maintain an Experience Corpus projection over existing artifacts/journal;
9. propose effect/verification/changepoint/backend boundaries;
10. cluster and align compatible traces;
11. classify core/conditional/optional/anomalous nodes.

### EC3 — parameterization and action-model inference

12. anti-unify instance values into typed parameters;
13. infer supported parameter relations/invariants;
14. infer conservative preconditions/effects/conditional branches;
15. use failures/drift as negative examples.

### EC4 — dependency and causal support

16. build dependency/effect graph;
17. compute Operational Slice for each candidate postcondition;
18. assign C0-C5 causal grade;
19. distinguish observational support from interventional proof.

### EC5 — safe replay, ablation and counterexample refinement

20. controlled replay in admissible safe environments;
21. bounded delta-debugging/ablation where effect policy permits;
22. refine false assumptions from counterexamples;
23. never experiment destructively on production merely to increase confidence.

### EC6 — promotion hardening and library snapshot

24. add Experience Compiler promotion admission independent from raw validation count;
25. incorporate provenance/taint, causal grade, effect risk and cross-run diversity;
26. snapshot capability version view per TaskRun;
27. distinguish run-local ephemeral compiled segment from global promotion.

### EC7 — integration and efficiency

28. emit OperationalCapability candidates into the existing registry;
29. exact resolver/work_execute reuse remains zero-LLM;
30. add utility/MDL pruning and deduplication;
31. measure reasoning amortization over verified outcomes.

### EC8 — cross-backend proof

32. prove the same compiler lifecycle on browser + filesystem;
33. add one process/local composite case;
34. add at least one cross-backend composed capability;
35. demonstrate that the same atomic learned capability can support two larger flows.

## Required tests / acceptance

The milestone is not complete until behavior tests prove at least:

1. ref-only browser trace with a derived semantic anchor receives semantic rather
   than structural identity;
2. all anchor types emitted by capture can be reacquired by replay, or capture
   normalizes them to supported types;
3. a successful trace containing redundant observation/wait/scroll does not
   blindly become the promoted procedure;
4. two compatible traces with different instance ids anti-unify into one typed
   candidate;
5. optional and state-conditional steps are distinguished;
6. stable parameter relations are preserved;
7. success + failure traces can strengthen/restrict preconditions;
8. passive recurrence alone never claims C3+ causal confidence;
9. safe replay can move a candidate to C3;
10. safe ablation can remove an unnecessary step and raise causal support;
11. high-impact/unsafe operations do not trigger destructive ablation;
12. a counterexample produces a new candidate version/refinement rather than
    silently mutating a promoted historical version;
13. untrusted page-provided instruction content cannot become trusted
    precondition/authority merely through repetition;
14. learned mutable capability cannot auto-promote solely because
    `success_count >= 2`;
15. an exact admitted promoted learned capability replays with zero new
    operational-planning LLM calls;
16. TaskRun capability snapshot prevents mid-run semantic mutation of a selected
    capability;
17. registry growth is bounded/deduplicated by utility/compatibility policy;
18. browser and filesystem use the same TransitionSample/candidate lifecycle;
19. all existing AEPC, OperationalCapability, TaskCompiler, BrowserTask,
    uncertainty, approval, Work100 and canonical reliability tests remain green.

## Metrics

Track at minimum:

- TransitionSamples captured;
- candidate yield rate;
- promotion rate;
- candidate deduplication/merge rate;
- average Operational Slice reduction;
- C0-C5 grade distribution;
- replay validation pass/fail rate;
- counterexample refinement rate;
- learned-capability drift/quarantine rate;
- capability coverage;
- atomic reuse across composites;
- Operational Novelty Rate;
- LLM calls / verified outcome;
- tokens / verified outcome when provider accounting exists;
- Reasoning Amortization Ratio (RAR) where a defensible baseline exists.

Do not invent paid-token savings from provider-free tests.

## Non-goals / prohibited shortcuts

Do not:

- ask an LLM to summarize a trace and call that the Experience Compiler;
- treat a trace as a procedure merely because the task succeeded;
- infer causality from frequency alone;
- auto-promote learned mutations from validation-count threshold alone;
- persist transient DOM refs or secrets;
- let untrusted page prose become capability authority;
- run destructive ablation on production effects;
- create another SessionDB/Kanban/Memory/BrowserTask/evidence store;
- silently mutate a promoted capability in place;
- use fuzzy retrieval as execution authority;
- expose the full learned-capability catalog in every model prompt;
- allow a deterministic capability to silently call an LLM.

## Final architecture

~~~text
novel intention
  -> bounded adaptive reasoning
  -> execution
  -> observation + verification
  -> TransitionSamples
  -> Experience Compiler
       recurrence
       generalization
       operational slicing
       causal validation
       counterexample refinement
  -> OperationalCapability candidate
  -> promotion admission
  -> Capability graph
  -> exact resolver
  -> work_execute / Operational Kernel
  -> deterministic verified outcome
  -> reasoning only on novelty/drift
~~~

The optimization target is no longer merely fewer LLM calls per batch. It is:

> **minimize new reasoning required per verified outcome over the lifetime of the
> system, without weakening authority, safety or evidence.**

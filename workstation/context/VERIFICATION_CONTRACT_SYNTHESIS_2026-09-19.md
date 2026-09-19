# Verification Contract Synthesis — Operational Truth Without Self-Certification

Date established: 2026-09-19
Status: **IMPLEMENTED & WORKSTATION-QUALIFIED (P0-P7, 2026-09-19)**
Current-main audit baseline: e010c8981a4bdeb89ac94479e0d7e891d48eadae (PR #33 merged)

## Executive finding

The hypothesis that Hermes Work needs a separate **Verifier Compiler** subsystem is
mostly falsified. Current main already owns the right execution, evidence, predicate,
routing, acceptance, experience and durability surfaces. The missing layer is a
**typed, provenance-aware Verification Contract** plus deterministic evaluation and a
conservative **Verification Contract Synthesis** phase inside the existing Experience
Compiler.

The target is not a new registry, scheduler, database, certificate system or verifier
agent. It is to make the existing statement "verified" mean something falsifiable.

Canonical distinction:

~~~text
execution acknowledgement
  != observation
  != persisted readback
  != semantic equivalence
  != postcondition proof
  != goal satisfaction
  != task acceptance
~~~

Core rule:

> **The executor may produce evidence, but it may not define by itself what makes that
> evidence sufficient.**

For learned verification:

> **Experience proposes verifier hypotheses. Only verifier hypotheses that
> discriminatively survive positive cases, negative controls, stale/conflicting
> observations and counterexamples may become reusable VerificationContracts.**

This milestone follows H-075. H-075 remains the implementation owner for
adaptive-to-deterministic handoff. H-076 hardens the epistemic contract consumed by
that handoff; it does not create a second execution path.

## Current-main truth after PR #33

Current main already contains:

- CapabilityFormalContract.verifier;
- OperationalCapability.verifier_contract;
- EvidenceStrength E0-E3;
- TransitionSample.Verification;
- typed PRE/POST predicates and Effect IR;
- CertifiedDispatcher with ACKNOWLEDGED -> VERIFIED -> COMMITTED;
- AcceptanceEvaluator;
- Browser transaction readback admission;
- Experience Compiler replay, counterexamples and C0-C5 causal grades;
- AwaitCondition + authoritative state confirmation;
- RunClosureProof and in-flight handoff;
- ArtifactStore / ExecutionJournal lineage.

Therefore extend existing owners.

## Post-merge falsification findings

### F1 — verifier evidence can still be over-promoted from missing metadata

In workstation/task_compiler.py, verifier strength contains a fallback equivalent to:

~~~python
... else (1 if request.get("routine_id") else 3)
~~~

for some verifier steps whose owner metadata does not explicitly carry
evidence_strength.

Absence of evidence metadata must never become INDEPENDENT_PERSISTED_READBACK.
Unknown must fail closed to the owner-declared default/minimum, normally E0 unless a
trusted contract proves more.

### F2 — successful kernel postcondition checking can still be correlated with execution

OperationalKernel.execute_capability() checks postconditions using semantic state and
can return verification.accepted=true with source semantic_observer or
declared_postconditions.

For an external browser mutation, same-surface semantic observation may share the same
renderer/frontend failure domain as the mutation. It can be valid for UI-local truth
but cannot automatically prove persisted external state.

### F3 — Router models freshness as a boolean but does not prove temporal validity

RoutingCertificate.state_fresh exists, but normal route creation sets state_fresh=True
from current semantic state without a first-class revision,
ETag/version/generation/read-after-write/temporal contract.

State-hash equality is useful preflight fencing; it is not a universal proof that a
post-mutation observation is fresh enough for the claimed fact.

### F4 — verifier presence is treated as verifier sufficiency

CapabilityRouter currently treats verifier_available = bool(verifier_dict), and for
evidence policy largely equates a non-empty verifier dict with sufficient verification
capability.

A verifier contract must instead prove that its observer, relation, evidence class,
trust, freshness and coverage are adequate for the required predicates/effects.

### F5 — Dispatcher can still consume executor-produced verification.accepted

The dispatcher correctly separates ACK from verification, but current TaskCompiler
integration supplies a verifier callback that reads the execution result's own
verification.accepted.

That is a useful compatibility seam, not independent verification. The dispatcher must
ultimately consume a canonical VerificationResult produced by a trusted evaluator, not
a bool self-report from the executor.

### F6 — RunClosureProof checks verifier existence, not verifier validity

evaluate_run_local_closure() currently admits a verifier when verifier_contract is
non-empty. Handoff therefore proves "there is a declared verifier", not yet "this exact
validated verifier proves these predicates with the required
freshness/trust/fault separation".

H-075 mechanics remain valid, but H-076 must strengthen this admission.

### F7 — Experience Compiler remembers that verification happened better than how to verify again

The current compiler reduces learned verification largely to effects +
minimum_evidence and derive_formal_contract() emits a similarly shallow verifier dict.

This loses important identity:

- observer/tool/capability;
- source/surface;
- extraction path;
- source-of-record semantics;
- equivalence relation and version;
- freshness/version requirement;
- fault-domain provenance;
- covered predicates;
- validated negative controls.

### F8 — causal replay inherits verifier quality

experience_compiler/causal.py replay admission uses pass state, evidence strength,
evidence refs and predicate equality.

Causal support for the action and epistemic quality of the verifier are different
axes. A replay validated by a weak/correlated oracle must not upgrade the whole pair to
trusted reusable knowledge.

### F9 — exact equality remains too weak as a universal semantic relation

Current batch validation is mostly exact path equality. That correctly avoids
over-permissive fuzzy matching, but creates false negatives for owner-approved
canonical representations.

The correction must remain deterministic and narrow. Never add generic fuzzy text
equivalence or LLM equivalence as a commit oracle.

## Canonical architecture

Use existing CapabilityFormalContract.verifier as the compatibility surface, but make
it parse into a typed contract.

~~~text
CapabilityFormalContract
  PRE
  expected effects / POST
  VerificationContract
        |
Action / deterministic capability
        |
        +--> ACK ----------------------------------+
        |                                          | not proof
        v                                          |
Observation(s)                                     |
        |                                          |
VerificationEvaluator                              |
  - source/trust                                   |
  - extraction                                     |
  - relation                                       |
  - temporal validity                              |
  - fault-domain admissibility                     |
  - predicate coverage                             |
  - disagreement handling                         |
        |                                          |
        v                                          |
VerificationResult <-------------------------------+
  VERIFIED | FAILED | INCONCLUSIVE | CONFLICT | STALE
        |
covered predicates + evidence refs
        |
goal entailment / acceptance
~~~

No new canonical persistence owner is introduced.

## Typed VerificationContract

The minimum useful contract should be serializable and backwards-compatible with
existing verifier dicts.

Conceptual fields:

~~~text
VerificationContract
  schema_version
  contract_id / fingerprint
  subject
    covered_predicates
    effect_classes
  observer
    tool/capability
    source_kind
    resource binding
    extraction paths
  relation
    kind
    parameters
    canonicalizer_id + version when owner-defined
  evidence_requirement
    minimum persistence/evidence class
  trust_requirement
    allowed trust/source classes
  fault_domain_requirement
    mutation/observer provenance constraints
  temporal_requirement
    version/revision/etag/generation/max_age/settling
  settling_policy
    bounded retries/events/deadline
  disagreement_policy
    fail closed by default
  validation
    lifecycle: CANDIDATE | VALIDATED | QUARANTINED
    evidence refs
    sensitivity/negative-control receipts
~~~

Do not encode independence as independent=True. Derive admissibility from actual
mutation and observation provenance/failure domains.

## VerificationEvidence and VerificationResult

Evolve experience_compiler.models.Verification rather than creating another evidence
database.

Evidence must be able to preserve observer identity/version, raw artifact ref, extracted
semantic value, resource identity/version, observed_at, task/run/operation lineage,
trust/source class, mutation provenance/failure domain, verifier fingerprint and
covered predicates.

VerificationResult must not be a bool. Required statuses:

- VERIFIED
- FAILED
- INCONCLUSIVE
- CONFLICT
- STALE

Only VERIFIED with sufficient predicate coverage may advance a mutation to COMMITTED.

## Evidence is multidimensional

Retain E0-E3 as a compatibility dimension for persistence/observation strength, but
verification admission must consider orthogonal requirements:

~~~text
Evidence persistence
x source authority/trust
x fault-domain independence
x temporal validity/freshness
x equivalence specificity
x predicate/goal coverage
~~~

These are logical dimensions, not a synthetic 0-100 confidence score.

## Typed deterministic equivalence

Start with a deliberately small relation set:

- EXACT
- STRUCTURAL_JSON
- ORDERED_SEQUENCE
- SET_EQUAL
- MULTISET_EQUAL
- NUMERIC_TOLERANCE with explicit bound
- DATETIME_INSTANT
- URL_CANONICAL with owner-approved rules
- OWNER_CANONICAL with canonicalizer id and version

Do not initially add fuzzy text equality, embedding similarity, LLM semantic
equivalence or generic Markdown-render equivalence.

An owner canonicalizer must be versioned and property-tested. Normalization may remove
only differences explicitly declared irrelevant by the domain owner.

## Verifier learning: learn action and oracle separately

The Experience Compiler must treat verification discovery as hypothesis generation:

~~~text
experience
  -> infer action hypothesis
  -> infer verifier hypothesis

  -> falsify action where safe
  -> falsify verifier where safe

  -> validate transformation
  -> validate oracle

  -> bind validated pair

  -> OperationalCapability + VerificationContract
~~~

The same trace that proposes a verifier is discovery evidence, not sufficient
validation evidence.

## Verifier sensitivity / counterfactual validation

A verifier is promotable only if it can distinguish success from relevant failure.

Required safe validation patterns where applicable:

1. positive replay: correct effect -> PASS;
2. mutation withheld: no effect -> FAIL, unless PRE already satisfies an idempotent
   state-satisfaction intent;
3. wrong effect/value -> FAIL;
4. stale or optimistic same-surface observation vs source-of-record -> reject or
   inconclusive;
5. owner-approved equivalent representation -> PASS;
6. meaningful representation difference -> FAIL;
7. source disagreement -> CONFLICT;
8. schema/path/version drift -> STALE / NEEDS_REVALIDATION.

Do not perform destructive negative controls on production external state merely to
increase confidence.

## State satisfaction vs transition causation

A postcondition can prove state == desired without proving my action caused the
transition.

- idempotent ensure(X=value): state satisfaction may be enough;
- increment, append, send-once, create-once, transfer, publish: transition causation or
  operation identity may be required.

Extend verification semantics conservatively rather than assuming all POST proofs
establish causation.

## Integration owners

### workstation/control_plane/contract.py
- typed VerificationContract;
- backwards-compatible parse/serialization from existing dicts;
- contract fingerprint.

### workstation/control_plane/verification.py
Small new deterministic module, not a new state owner:
- typed relation enum/parameters;
- Observation / VerificationEvidence view;
- VerificationStatus / VerificationResult;
- deterministic evaluate_verification();
- contract/evidence coverage checks;
- temporal/trust/fault-domain checks.

### workstation/control_plane/router.py
Replace verifier-dict presence checks with verifier-contract admissibility. Do not claim
freshness without an actual temporal/state-version basis when required.

### workstation/control_plane/dispatcher.py
Keep ACK -> VERIFIED -> COMMITTED lifecycle. Prefer canonical VerificationResult over
executor self-report booleans. ACK-only remains explicit trusted owner policy only.

### workstation/task_compiler.py
- remove E3 fallback from absent metadata;
- route step expectations through typed relation where applicable;
- persist canonical VerificationResult/evidence refs;
- do not mark mutation persisted from undeclared verifier strength;
- final composition goal verification uses canonical evaluator where possible.

### workstation/operational_kernel.py
- execute the contract verifier after mutation/postcondition observation;
- same-surface semantic observation is admissible only for compatible effects;
- CapabilityInvocation records verifier fingerprint/evidence refs/result rather than
  unconditional verified=True.

### workstation/run_closure.py
Strengthen RunClosureProof with verifier contract fingerprint, validated lifecycle,
first/replay VerificationResult refs, covered required predicates, temporal/freshness
proof where required, and no unresolved conflict/stale/inconclusive result.

A non-empty verifier dict is no longer enough.

### workstation/control_plane/waiting.py
Reuse the same predicate/evidence evaluator for authoritative state confirmation where
appropriate. Await remains the lifecycle owner.

### workstation/experience_compiler/
Enrich existing Verification and CapabilityInvocation. Synthesize verifier candidates
separately from action models. Keep action causal grade distinct from verifier quality.
Promotion requires a validated verifier contract.

### tools/effects.py and tool owners
Owner-declared metadata is the source for effect class, evidence/source semantics,
consistency/freshness guarantees, trusted canonicalizers and observer failure-domain
classification. Page content and the LLM may never mint these guarantees.

## Implementation plan

### P0 — eliminate false-confidence seams

1. remove undeclared E3 fallback in TaskCompiler;
2. fail closed when evidence strength/source semantics are unknown;
3. replace Router verifier-presence sufficiency with contract validation;
4. make freshness requirement explicit/unknown rather than assumed true where required;
5. prevent external learned Browser mutations from committing from same-surface
   observation alone;
6. preserve final composition goal verification but make evidence source explicit;
7. preserve ACK-only only for trusted owner-declared contracts.

Exit: ACK-liar, stale-DOM and unknown-evidence tests fail closed.

### P1 — typed VerificationContract + deterministic evaluator

Implement workstation/control_plane/verification.py and typed parsing in
CapabilityFormalContract while preserving legacy dict compatibility.

Exit: roundtrip/fingerprint, relation, temporal, trust and coverage tests green.

### P2 — runtime integration

Wire evaluator into OperationalKernel, TaskCompiler, CertifiedDispatcher, composition
final-goal verification and acceptance projection.

Executor compatibility fields may remain as projections of canonical
VerificationResult, but self-report is not terminal truth.

### P3 — RunClosureProof / Await integration

Harden H-075 handoff admission with validated verifier fingerprints/results. Reuse
verifier predicate evaluation in Await authoritative confirmation without creating a
second wait system.

### P4 — Experience Compiler Verification Contract Synthesis

Mine verifier candidates separately from action models: observer identity, extraction,
relation, covered predicates, freshness/version signals and provenance/failure-domain
metadata.

Discovery traces create CANDIDATE contracts only.

### P5 — discriminative verifier validation

Add held-out validation, safe negative controls, mutation-withheld sensitivity where
semantics permit, wrong-effect perturbation, stale/conflicting source cases,
equivalence positive/negative pairs, property/metamorphic tests for canonicalizers and
verifier fingerprint/drift/quarantine.

Only a verifier that distinguishes relevant success/failure may become VALIDATED.

### P6 — action/verifier pair promotion + metrics

Promotion uses the validated pair, with separate action and verifier fingerprints plus a
pair digest/contract version.

Add measurable metrics: verification status distribution, verifier disagreement,
verification latency, verifier drift/quarantine, relation rejection, postcondition and
goal coverage, run-closure verifier rejection reasons and verification-triggered
WAKE_LLM. Do not fabricate denominators.

ORA remains meaningful only when a verified transition means canonical VERIFIED under
the new contract.

### P7 — Trello-shaped truth benchmark + cross-backend fixtures

Extend the existing 12-item qualification fixture. Inject:

- ACK liar;
- optimistic DOM while backend stale;
- owner-approved representation equivalence;
- punctuation/colon meaningful difference;
- composite children pass but final goal false;
- verifier schema drift;
- malicious page "Saved" confirmation;
- valid in-flight handoff;
- verifier disagreement;
- verifier always-passes negative control;
- PRE already equals POST idempotent case vs causal mutation case;
- concurrent overwrite/version mismatch.

Also qualify filesystem/process/read-only examples so verification semantics are not
Browser-specific.

## Mandatory tests

At minimum add behavior equivalent to:

- test_unannotated_read_tool_cannot_become_independent_e3_verifier
- test_ack_success_never_implies_persisted_effect
- test_same_surface_browser_observation_cannot_certify_external_commit
- test_router_verifier_sufficiency_is_proven_not_presence_based
- test_state_fresh_requires_temporal_or_version_basis_when_required
- test_verification_contract_roundtrip_and_fingerprint
- test_exact_relation_rejects_changed_punctuation
- test_owner_canonical_accepts_only_declared_normalizations
- test_owner_canonicalizer_property_roundtrip_and_negative_examples
- test_verification_result_distinguishes_failed_inconclusive_conflict_and_stale
- test_verifier_without_required_predicate_coverage_cannot_commit
- test_all_child_verifiers_pass_but_final_goal_false_blocks_commit
- test_dispatcher_uses_canonical_verification_result_not_executor_self_report
- test_run_closure_rejects_candidate_or_stale_verifier
- test_run_closure_accepts_validated_fresh_covered_verifier
- test_await_and_mutation_verification_share_predicate_evaluator_semantics
- test_verifier_negative_control_detects_always_pass_oracle
- test_mutation_withheld_distinguishes_state_satisfaction_from_causation
- test_verifier_disagreement_preserves_conflict
- test_verifier_fingerprint_drift_quarantines_pair
- test_experience_compiler_proposes_verifier_candidate_without_promoting_it
- test_verifier_promotion_requires_discovery_validation_split
- test_causal_replay_cannot_upgrade_pair_with_inadmissible_verifier
- test_trello_truth_fixture_rejects_stale_dom_and_preserves_valid_handoff

Use property-based tests for canonicalizers where practical.

## Hard acceptance properties

The milestone is not closed until:

1. no undeclared verifier is treated as E3 or independent persisted evidence;
2. external mutation cannot COMMIT from same-surface/self-report verification unless
   a trusted owner explicitly declares that evidence sufficient for that EffectClass;
3. Router verifier/freshness obligations come from real typed contract/evidence
   requirements, not dict presence/default booleans;
4. canonical VerificationResult is the runtime truth projection for verification;
5. RunClosureProof requires a VALIDATED verifier contract/result with required
   predicate coverage and no STALE/CONFLICT/INCONCLUSIVE state;
6. Experience Compiler can learn verifier candidates but discovery evidence alone
   cannot validate/promote them;
7. negative controls/counterexamples can quarantine/refine a verifier without
   rewriting historical receipts;
8. semantic equivalence is deterministic, narrow, owner-approved and versioned;
9. action causal grade and verifier quality remain separate;
10. final OperationIntent goal is verified from adequate evidence, not inferred only
    from child success;
11. no second registry, scheduler, task DB, ArtifactStore, journal, control plane or
    verifier agent is introduced;
12. existing H-075 deterministic handoff remains green after verification hardening.

## Non-goals / anti-patterns

Do not build:

- VerifierDB;
- VerifierRegistry;
- VerificationScheduler;
- verifier LLM / judge as mutation commit oracle;
- second predicate IR;
- second evidence/corpus store;
- universal confidence score;
- fuzzy text comparator;
- generic Markdown equivalence;
- mandatory cross-source corroboration for every operation;
- destructive production falsification experiments.

## Canonical invariants

> **OBSERVATION PROPOSES. CONTRACT DEFINES. EVIDENCE PROVES.**

> **THE ACTION AND THE ORACLE ARE LEARNED SEPARATELY; THEY ARE BOUND ONLY AFTER BOTH
> SURVIVE FALSIFICATION.**

> **VERIFIER RECURRENCE != VERIFIER VALIDITY.**

> **SAME VALUE != SAME TRANSITION.**

> **SOURCE DISAGREEMENT PRESERVES UNCERTAINTY.**

> **UNKNOWN EVIDENCE NEVER UPGRADES ITSELF.**

## Relationship to existing architecture

~~~text
OperationIntent
  -> Router admission
  -> deterministic/adaptive execution
  -> ACK
  -> Observation / VerificationEvidence
  -> typed VerificationContract
  -> VerificationEvaluator
  -> VerificationResult
  -> predicate/goal coverage
  -> commit / acceptance
  -> TransitionSample
  -> Experience Compiler
       action hypothesis
       verifier hypothesis
       separate falsification
  -> validated action + oracle pair
  -> capability promotion
  -> H-075 RunClosureProof / deterministic continuation
~~~

The long-term objective is not merely to teach Hermes more ways to act.

It is to teach Hermes **reusable ways to know whether reality changed as intended,
without allowing the same perceptual mistake that produced an experience to become the
rule that certifies it forever.**

## Implementation receipts

- `control_plane/verification.py` is the pure typed contract/evaluator; it owns no
  database, registry, scheduler, corpus, journal or control plane.
- Router, Dispatcher, OperationalKernel, TaskCompiler, Composition, Await and
  RunClosure consume canonical `VerificationContract` / `VerificationResult` truth.
- Experience Compiler emits CANDIDATE verifier hypotheses and validates them from
  separately identified positive/negative receipts.
- Focused affected suites: **109 passed**.
- Full Workstation regression: **670 passed, 2 skipped in 287.52s**.

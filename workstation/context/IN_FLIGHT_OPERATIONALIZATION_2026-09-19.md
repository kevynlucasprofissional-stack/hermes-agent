# In-Flight Operationalization — Adaptive-to-Deterministic Handoff

Date established: 2026-09-19
Status: **CANONICAL CORRECTIVE ARCHITECTURE / IMPLEMENTATION OPEN**
Audit baseline: main@e36b0f0febed96240fa13bbcb78f1cc13c7c0b24

## Finding after falsification

The broad hypothesis was partially false. Hermes already has a deterministic
continuation substrate: DurableBatchRunner executes repetitive loops outside the
conversational model, TaskCompiler and OperationalKernel have durable checkpoints,
execution_policy already has a fail-closed operational-closure predicate, and the
native Browser already has typed plain-text paste plus semantic anchors.

The confirmed gap is narrower:

> **newly verified adaptive knowledge is not automatically handed to the existing
> deterministic runtime while the same TaskRun is still executing.**

This is the **In-Flight Operationalization Handoff Gap**.

## Falsification matrix

| Claim | Current-main evidence | Verdict |
| --- | --- | --- |
| No deterministic continuation executor | DurableBatchRunner already owns model-free fan-out and anomaly escalation | REFUTED |
| No durable checkpoint mechanism | TaskCompiler and OperationalKernel already persist item/step progress | REFUTED |
| No operational closure predicate | _operational_closure_proven already requires deterministic representation, primitive, route, authority, verifier, certified dispatch and clear uncertainty | REFUTED |
| Rich-editor work requires arbitrary JS | browser_type plain_text_paste and semantic anchors exist | MOSTLY REFUTED |
| browser_console produces transparent semantic traces | Electron executes raw JavaScript and candidate_steps rejects arbitrary action kinds | CONFIRMED GAP |
| Adaptive verified repetition automatically hands off in-run | no automatic run-scoped bridge was found | CONFIRMED GAP |
| Browser accepts ArtifactStore text by reference | browser_type accepts inline text only | CONFIRMED GAP |
| Verified prefix automatically becomes run-local executable knowledge | no automatic path was found | CONFIRMED GAP |

## Trello-shaped evidence

The 2026-09-19 dogfood run synchronized 12 descriptions, discovered a reliable
rich-editor procedure, discovered native due-date mechanics and verified external
state. It still hit the tool-iteration limit with five due dates and final state
publication pending.

About 109 distinct tool calls were observed, about 55 browser_console. At least 35
calls were conservative post-discovery repetition: 23 description calls and 12 due
calls.

The failure is therefore not lack of an executor. It is lack of **control transfer**
from adaptive discovery to deterministic continuation.

## Refined invariant

> **Do not force determinism before semantic closure. Once closure is proven inside a
> TaskRun, do not keep the LLM as scheduler for equivalent remaining transitions.
> Transfer the closed subgraph to the existing deterministic runtime, checkpoint every
> verified mutation and wake reasoning only on explicit exception.**

Run-local operationalization is not global promotion.

~~~text
adaptive discovery
  -> verified transition
  -> RunClosureProof
  -> run-scoped compiled segment
  -> TaskCompiler / DurableBatchRunner / OperationalKernel
  -> durable verified checkpoints
  -> continue without LLM
  -> exception / drift / ambiguity / authority gap
  -> compact WAKE_LLM
  -> repair and re-close
  -> later Experience Corpus evidence
  -> global promotion only through existing causal gates
~~~

## Ownership rule

Reuse existing owners. Do not add another scheduler, task DB, capability registry,
BrowserTask owner, journal or memory store.

- execution_policy.py: closure/admission
- procedure_trace.py: adaptive evidence
- work_execute / TaskCompiler: deterministic entry
- DurableBatchRunner: continuation and exception escalation
- DurableTaskStore / WorkPlan / WorkItem: checkpoints
- OperationalKernel: capability execution
- ArtifactStore: payload/evidence
- CapabilityRouter / CertifiedDispatcher: dispatch admission
- ExperienceCompiler: later cross-run promotion
- ExecutionJournal: provenance

## RunClosureProof

Add a typed run-scoped proof with task/run/operation lineage, semantic fingerprint and
target family, deterministic representation, executable primitive/capability, route,
authority/effect containment, verifier/readback, first verified execution, compatible
replay/canary, uncertainty state, parameter schema/bindings, remaining equivalent work,
expected utility and evidence refs.

Run-local handoff requires parameterizable inputs, observable PRE/POST, executable
determinism, unchanged/narrower authority, sufficient verifier, no relevant UNCERTAIN
mutation, compatible replay/canary for mutable work and positive remaining-work
utility. A fixed repetition count is not causal truth.

## Run-scoped compiled segment

RunScopedCapability is a logical contract, not a second registry. Represent it with
existing OperationalCapability/Recipe/WorkPlan structures and ArtifactStore metadata.

It is fenced to one task/run/operation, immutable after dispatch, excluded from the
global PROMOTED index, unable to widen authority, invalidated by pin/contract drift,
restart-reusable only for the same TaskRun and merely evidence for later global
learning.

## Execution envelope

Do not build another scheduler named ExecutionLease. Store a bounded execution envelope
on the existing WorkPlan: compiled subgraph ref, task/run/operation fence, pins,
authority/effect budget, verifier requirements, limits/deadline, wake conditions and
last verified checkpoint.

Wake reasoning only on unexpected PRE failure, failed/inconclusive verifier, relevant
UNCERTAIN mutation, authority/approval insufficiency, semantic ambiguity, unhandled
drift, contract violation, invariant conflict, explicit user intervention or safe
envelope exhaustion.

The next equivalent item is not a reasoning event.

## Browser rule

browser_console remains exploration. It currently maps to raw executeJavaScript and is
opaque to causal learning. Do not parse JavaScript source and call it a capability.

Stable behavior must lower to typed first-party primitives. Rich editors should use
browser_type plain_text_paste plus semantic anchors and independent persisted-state
readback. Opaque console traces remain non-promotable unless trusted runtime
instrumentation independently emits semantic events; those events, not source JS,
become evidence.

## Artifact-to-Browser data plane

Add text_ref or artifact_ref to browser_type, mutually exclusive with inline text.
Resolve it at the trusted runtime boundary outside the model/page, enforce task/run
ownership and size/MIME limits, preserve hash/ref evidence and never expose filesystem
paths to page JavaScript.

## Verified prefixes

> **Run outcome does not rewrite transition truth.**

Every verified mutable transition must be checkpointed before the next mutation.
Restart reopens the same WorkPlan, skips committed work, classifies
dispatch-without-result as UNCERTAIN, semantically reacquires Browser resources and
resumes only remaining work.

## Existing PR #32 corrections still open

H-075 does not erase the post-merge audit:

- WAIT/HUMAN/REASONING branches must use actual dataclass fields;
- non-resident Await must wire into real TaskRun/WorkPlan suspend/resume;
- CapabilityInvocation must be durable with real run/operation/authority lineage;
- recurrence may propose a composite but never directly make it PROMOTED;
- composite promotion must reuse causal replay/counterexample admission;
- composed commit needs authoritative final-goal verification;
- learned mutation contract derivation must fail closed on ambiguous families or
  missing trusted authority scope;
- ORA must be wired to production execution events.

## Metrics

Keep ORA and add Reasoning Re-entry Rate after closure, Closure Latency,
Deterministic Continuation Span, Avoidable Reasoning Fraction, Verified Transitions per
LLM Call, run-local candidate/admission/reuse, artifact-ref versus inline payload bytes,
exception wake reasons and resumed-without-replay count. Unknown denominators remain
null.

## Reproducible Trello-shaped benchmark

Required qualification must be local and deterministic, not live Trello.

Build an Electron fixture with 12 cards/items, a ProseMirror-like editor, Save with
persisted backing state, native due-date control, authoritative readback, one deliberate
anomaly, large canonical text in ArtifactStore and injected restart mid-batch.

Expected:

1. item 1 may be adaptive;
2. item 2 may be compatible replay/canary;
3. remaining equivalent work transfers to DurableBatchRunner with no LLM re-entry per
   item;
4. large payload uses artifact ref;
5. each verified mutation checkpoints before the next;
6. restart does not replay committed effects;
7. anomaly produces one compact reasoning handoff;
8. repair resumes deterministic continuation;
9. stable path uses typed Browser primitives, not arbitrary console JS;
10. final authoritative readback proves all expected states.

## Implementation sequence

P0 — truth correction and RED tests: route dataclass seams, composition final-goal
verification, conservative authority/family derivation.

P1 — RunClosureProof and expected utility, reusing the existing operational-closure
predicate.

P2 — adaptive-to-compiled handoff: synthesize a run-scoped work_execute/WorkPlan
segment and transfer remaining fan-out to existing deterministic owners.

P3 — Browser lowering and Artifact data plane: text_ref/artifact_ref, robust
plain_text_paste clear semantics and typed post-closure path.

P4 — durable CapabilityInvocation and causal hierarchy: real lineage, candidate
composites first, existing causal promotion gates.

P5 — real non-resident continuation and production telemetry.

P6 — 12-item Trello-shaped Electron qualification with restart and anomaly.

## Mandatory behavior tests

- test_run_local_closure_requires_verified_replay_and_verifier
- test_run_local_closure_cannot_expand_authority_or_effect_budget
- test_adaptive_verified_pair_hands_remaining_batch_to_durable_runner
- test_no_llm_reentry_between_equivalent_items_after_handoff
- test_run_scoped_capability_never_enters_global_promoted_index
- test_verified_prefix_survives_interrupted_run
- test_restart_resumes_remaining_items_without_replaying_committed_mutation
- test_browser_console_trace_is_opaque_and_not_auto_promotable
- test_plain_text_paste_semantic_primitive_replaces_console_for_rich_editor
- test_browser_type_accepts_owned_artifact_text_ref
- test_artifact_text_ref_rejects_cross_task_or_oversized_payload
- test_reasoning_wakes_only_on_declared_exception_after_closure
- test_trello_shaped_12_item_fixture_closes_after_canary_and_finishes
- test_capability_invocation_is_durable_with_real_run_operation_authority_lineage
- test_recurrence_only_proposes_composite_candidate_not_promoted
- test_composite_promotion_requires_causal_replay_policy
- test_composed_execution_verifies_final_intent_goal_authoritatively
- test_ora_and_reentry_metrics_are_wired_to_real_execution_events

Retain the prior route-branch, Await/restart, authority and final-goal tests.

## Non-goals

No second scheduler/executor, task/run DB or global registry.
No global promotion of run-local knowledge.
No causal inference from arbitrary JS source or frequency.
No weakening of authority, verifier, canary, uncertainty or CertifiedDispatcher.
No replay of uncertain mutation after restart.
No compilation before the procedure is known.
No live third-party mutation as the sole qualification gate.

## Success criterion

> **Few reasoning re-entries per verified transition after closure, while every mutable
> effect remains fenced, verified, checkpointed and recoverable.**

# Operational Telemetry Plane — Architecture and Sequencing Record

Date: 2026-09-23

Status: **PHASE 1/2 IMPLEMENTED AND LOCALLY QUALIFIED / EXACT-HEAD CI OPEN**

Local evidence: telemetry 5/5; focused integration 31/31; affected owners
123/123; real product-owned H-080B funnel 1/1; strict seam audit zero
unclassified seams. Dashboard, Phase 3/4 and Laya remain deferred.

Canonical architecture:
[../OPERATIONAL_TELEMETRY.md](../OPERATIONAL_TELEMETRY.md).

## Why this lane exists

Hermes Work has reached the point where release tests and architecture audits can prove important local properties, but they cannot answer longitudinal product questions.

We need durable evidence for questions such as:
- does Experience compilation reduce provider calls over time?
- do promoted capabilities continue to succeed after repeated reuse?
- how often is the Reasoner awakened when an executable deterministic route already exists?
- where does the Experience funnel lose learning capital?
- how many verified runs and how much elapsed time are required before competence is promoted?
- are capabilities drifting or entering quarantine?
- how often does the system continue observing/reasoning after the declared goal is already satisfied?

The objective is not generic "logging". It is an empirical measurement plane for Progressive Operational Compilation.

## Repository observation

`workstation/control_plane/metrics.py` already defines:
- `VOLCMetrics`;
- `ORAMetrics`;
- `ORAMetricsCollector`;
- `FailureAttributor`;
- `ShadowRouter`.

These definitions encode useful semantics, including the rule that unknown cost denominators remain `None`.

The gap is that these objects are not yet backed by one durable correlated product event history. They are metric/model helpers rather than a complete operational telemetry plane.

## Architecture decision

Telemetry is a read-only observational projection of product truth.

```text
canonical product owner
-> event
-> TelemetryEventV1
-> TelemetrySink
-> local event projection
-> metrics projector
```

Telemetry cannot:
- grant authority;
- issue certificates;
- verify an effect;
- promote/quarantine by itself;
- choose retry behavior;
- mutate Browser/task/capability state.

If telemetry fails, product execution continues.

## Sources of truth

Do not duplicate ownership.

Use existing owners:
- ExecutionJournal;
- ArtifactStore;
- OperationalCapabilityRegistry;
- VerificationEvidence/results;
- BrowserSessionState / BrowserOwnerReceipt;
- canonical task/run/operation lineage;
- provider/tool/runtime accounting.

`telemetry.sqlite` is rebuildable analytics state.

## Event-first principle

Do not directly mutate ORA/VOLC counters as the only history.

Persist semantic events first, then project metrics.

This enables:
- recomputation after metric-definition changes;
- audit of denominators;
- comparison across builds/versions;
- new analytics without changing product execution.

## Phase 1 minimum event families

```text
TURN_STARTED
PROVIDER_CALLED
ROUTING_DECIDED
LLM_WOKEN
CAPABILITY_SELECTED
CAPABILITY_EXECUTION_STARTED
CAPABILITY_EXECUTION_FINISHED
MUTATION_DISPATCHED
MUTATION_ACKNOWLEDGED
VERIFICATION_COMPLETED
OUTCOME_ACCEPTED
EXPERIENCE_ACCEPTED
EXPERIENCE_REJECTED
CAPABILITY_CANDIDATE_CREATED
VERIFIER_VALIDATION_COMPLETED
CONTROLLED_REPLAY_COMPLETED
CAPABILITY_PROMOTED
CAPABILITY_QUARANTINED
GOAL_SATISFIED
TURN_FINISHED
```

Do not instrument every function.

## Owner-emission principle

Facts must be emitted where they are known:
- provider usage at provider-call boundary;
- routing at operational-resolution/router integration boundary;
- capability execution at OperationalKernel;
- dispatch/effects at dispatcher/effect-owner boundary;
- verification in verification plane;
- accepted outcome at WorkstationKanbanBridge;
- Experience/candidate at Experience owners;
- validation/replay at lifecycle coordinator;
- promotion/quarantine at capability lifecycle owner.

Do not restore generic-core -> Workstation imports for this.

Use generic hooks/adapters under `workstation/integrations/hermes/`.

## Metrics that matter first

Prioritize metrics that can falsify or support the product thesis:

1. Verified Outcome Rate.
2. ORA Ratio.
3. LLM Calls per Verified Outcome.
4. Provider-Zero Verified Rate.
5. Deterministic Reuse Success Rate.
6. False-Reuse Rate.
7. Uncertain Mutation Rate.
8. Experience Funnel.
9. Runs to Competence.
10. Time to Competence.
11. Capability Drift / Quarantine Rate.
12. Avoidable Reasoning Rate.
13. Post-Goal Work / Oververification.

Do not start from vanity counts such as total tool calls without outcome context.

## Oververification

Real Browser dogfood showed a useful measurement target:
the requested navigation was already proven by native Browser state, yet additional vision/reasoning work followed for an undeclared predicate.

The telemetry plane should eventually record the time/event at which all declared goal predicates became satisfied, then measure work after that boundary.

This yields:
- tool calls after goal satisfaction;
- provider calls after goal satisfaction;
- tokens after goal satisfaction;
- post-goal wall time.

## Shadow evaluation

`ShadowRouter` is useful only after actual event lineage is reliable.

Later:

```text
actual = WAKE_LLM
shadow = EXECUTE promoted capability
terminal actual outcome = VERIFIED
```

can become evidence of a missed deterministic opportunity, with zero shadow mutations.

The same evaluation frame later supports Laya SHADOW benchmarking.

## Privacy

Telemetry is structural by default.

Never duplicate sensitive product content merely for analytics.

Prefer IDs/fingerprints/status/reason/timing/version/evidence refs.

No raw:
- prompts/responses;
- DOM/page text;
- form contents;
- credentials/cookies/tokens;
- email/file contents;
- unsafe URL query/fragment data.

## Sequencing decision

Telemetry does not preempt the open H-080B.2 causal blockers.

Canonical sequence:

```text
H-080B.2 causal correctness
-> Telemetry Phase 1 event backbone
-> Telemetry Phase 2 Experience funnel
-> H-080B.3 real Electron proof emitting telemetry
-> Phase 3 ORA/VOLC projection
-> Phase 4 shadow/oververification/dashboard
-> H-081 Laya SHADOW
```

This gives H-080B.3 an observability substrate without using telemetry as proof or authority.

## Phase 1 acceptance

- versioned `TelemetryEventV1`;
- non-authoritative `TelemetrySink`;
- local append-oriented SQLite projection;
- canonical task/run/operation correlation;
- structural sanitization/privacy;
- owner-boundary event capture;
- normal run reconstructable chronologically;
- telemetry failure does not fail product execution;
- ORA/VOLC derivable from observed facts without invented counts;
- no generic-core dependency regression.

## Final principle

> **Do not merely make Hermes Work more autonomous. Make its autonomy measurable.**

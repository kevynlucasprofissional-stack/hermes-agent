# Operational Telemetry Plane — Hermes Work

Date established: 2026-09-23

Status: **ARCHITECTURE ACCEPTED / IMPLEMENTATION PLANNED AFTER H-080B.2 HARDENING / BEFORE SIGNIFICANT H-080B.3 + H-081 EXPANSION**

## Purpose

Hermes Work has reached the point where architecture and release tests are no longer enough to answer whether Progressive Operational Compilation is producing the intended product outcome.

The telemetry plane exists to answer empirically:

- are verified outcomes increasing?
- are LLM/provider calls per verified outcome decreasing?
- are promoted capabilities actually reused?
- do deterministic reuses remain VERIFIED?
- where does the Experience funnel lose candidates?
- how many independent runs and how much time are required before competence is promoted?
- which capabilities drift or enter quarantine?
- how often does the Reasoner wake when a deterministic route already exists?
- how much work happens after the declared goal is already provably satisfied?

The telemetry plane is an **observational projection**, not an authority plane.

## Primary invariant

> **Telemetry observes Hermes Work. It never authorizes, verifies, promotes, blocks, routes, retries, or mutates an execution.**

If telemetry storage or projection fails:
- the product path continues;
- RoutingCertificate truth is unchanged;
- verifier truth is unchanged;
- capability lifecycle truth is unchanged;
- ExecutionJournal remains canonical evidence;
- ArtifactStore remains canonical artifact evidence;
- Browser owner receipts remain canonical Browser effect evidence.

Telemetry failure may itself be logged, but must never convert an otherwise valid or invalid operation into another outcome.

## Sources of truth vs projection

Canonical product truth remains in existing owners:

```text
ExecutionJournal
ArtifactStore
OperationalCapabilityRegistry
Verification results / evidence
BrowserSessionState / BrowserOwnerReceipt
provider/runtime accounting
canonical task/run/operation lineage
```

The telemetry system consumes observations from those owners and runtime boundaries:

```text
product owners
-> TelemetryEventV1
-> local telemetry sink
-> rebuildable event projection
-> metrics projectors
-> reports / dashboards / shadow evaluation
```

The local telemetry store is **rebuildable materialized analytics state**, not source of truth.

Deleting the telemetry database must not delete:
- tasks;
- capabilities;
- evidence;
- journals;
- Browser state;
- Experience corpus truth.

## Existing metric semantics to preserve

`workstation/control_plane/metrics.py` already defines useful canonical semantics:
- `VOLCMetrics` / Verified Outcome Lifetime Cost;
- `ORAMetrics` / Operational Reasoning Amortization;
- `FailureAttributor`;
- `ShadowRouter`.

Do not replace these with an unrelated metric model.

The telemetry implementation should turn these definitions from mostly in-memory/model helpers into **metrics derived from durable observed events**.

Unknown denominators or unobserved values remain `None`, never fabricated as zero.

## Event capture before metrics

Do not make a mutable counter the only record of an operational fact.

Canonical flow:

```text
runtime fact
-> immutable structured TelemetryEventV1
-> projector
-> ORA / VOLC / funnel / health metrics
```

This permits metric definitions to evolve while historical source events remain inspectable and recomputable.

## TelemetryEventV1

First implementation should define one bounded structural event schema.

Conceptual fields:

```text
schema_version
event_id
event_type
timestamp

session_id
task_id
run_id
turn_id
operation_id

capability_id
capability_version

route
phase
status
reason_code

duration_ms

provider_calls
input_tokens
output_tokens
tool_calls

evidence_refs

build_sha
workstation_version
environment

payload
```

Rules:
- fields not known are null/absent, not zero;
- IDs must preserve canonical task/run/operation lineage when available;
- event payloads are bounded and sanitized;
- event schema is versioned;
- no event field becomes authority input.

## Initial semantic events

Do not capture every line/function call.

Phase 1/2 should cover semantic boundaries:

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

Event names may be implemented as an enum, but semantic meaning must remain stable.

## Owner-emission rule

A telemetry event is emitted by the owner that knows the fact.

Do not build a central observer that guesses facts after the fact.

Owner map:

| Fact | Canonical emitting boundary |
| --- | --- |
| provider call / tokens | provider or conversation-call boundary |
| routing decision | operational-resolution / router integration boundary |
| capability invocation | OperationalKernel |
| dispatch lifecycle | CertifiedDispatcher / effect dispatch boundary |
| physical mutation | effect owner / tool boundary |
| Browser receipt/revision | Electron Browser owner projection |
| verification result | verification plane |
| accepted outcome | WorkstationKanbanBridge acceptance boundary |
| Experience accepted/rejected | ExperienceCorpus / completion integration |
| candidate created | ExperienceCompiler post-mine boundary |
| validation / replay | Experience lifecycle coordinator |
| promotion / quarantine | OperationalCapabilityRegistry / promotion owner |

For generic `agent/` code, do not restore direct Workstation implementation imports. Reuse generic hooks/boundaries and adapt under `workstation/integrations/hermes/`.

## Storage

Initial local projection target:

```text
~/.hermes/workstation/telemetry/
    telemetry.sqlite
```

Recommended first schema:
- one append-oriented `events` table;
- indexed by `timestamp`, `event_type`, `task_id`, `run_id`, `operation_id`, `capability_id`;
- uncommon/versioned fields in bounded JSON payload;
- schema/version metadata.

Do not create twenty specialized tables in V1.

The database is disposable/rebuildable analytics state. If corruption is detected, fail telemetry locally and preserve product execution.

## Privacy and data minimization

Default telemetry is **structural, not content telemetry**.

Do not persist by default:
- prompts;
- model responses;
- page/DOM text;
- form values;
- cookies;
- credentials/tokens;
- clipboard;
- email/file contents;
- raw URLs containing credentials, query strings, or fragments.

Prefer:
- canonical IDs;
- hashes/fingerprints;
- route;
- operation/target family;
- capability ID/version;
- status/reason codes;
- latencies/counts;
- owner revisions;
- build/version;
- sanitized host/page family where already admissible;
- artifact/evidence references instead of copying sensitive payloads.

Use existing sanitizers and safe URL semantics.

## First metrics to derive

Do not start with a large dashboard metric catalogue.

Priority metrics:

1. **Verified Outcome Rate**
   `verified terminal outcomes / terminal outcomes`.

2. **ORA Ratio**
   `verified deterministic transitions / all verified transitions`.

3. **LLM Calls per Verified Outcome**
   Preserve VOLC semantics.

4. **Provider-Zero Verified Rate**
   Use an eligibility denominator, not all turns.

5. **Deterministic Reuse Success Rate**
   `promoted capability invocations ending VERIFIED / promoted capability invocations`.

6. **False-Reuse Rate**
   Deterministic promoted reuse that reaches FAILED/INCONCLUSIVE verification.

7. **Uncertain Mutation Rate**
   `uncertain mutable dispatches / mutable dispatches`.

8. **Experience Funnel**
   ```text
   verified Experience
   -> candidate
   -> verifier validated
   -> replay validated
   -> promotion admitted
   -> PROMOTED
   -> reused
   -> reused + VERIFIED
   ```

9. **Runs to Competence**
   Independent verified runs required from first accepted Experience to promotion.

10. **Time to Competence**
    First verified Experience timestamp -> promotion timestamp.

11. **Capability Drift / Quarantine Rate**
    Include reason attribution.

12. **Avoidable Reasoning Rate**
    WAKE_LLM/Reasoner path for which shadow evaluation later shows an admissible deterministic capability would have covered the goal.

13. **Post-Goal Work / Oververification**
    After authoritative goal satisfaction:
    - extra tool calls;
    - extra provider calls;
    - extra tokens;
    - wall time.

Derived values must carry denominator/sample counts where useful. Never hide small-sample uncertainty.

## Browser telemetry

Browser is the first rich product laboratory.

Structural Browser events may include:
- BrowserTask created/activated;
- navigation requested/committed;
- owner receipt revision observed;
- readiness achieved;
- recovery entered/exited;
- task parked/resumed;
- controller disconnect/reconnect.

Do not duplicate DOM/page/private content into telemetry.

## Shadow evaluation

`ShadowRouter` already provides a zero-mutation evaluation path.

Shadow telemetry is a later phase, after event capture and actual outcome lineage are reliable.

Target comparison:

```text
actual path: WAKE_LLM
shadow path: EXECUTE capability_X
actual terminal outcome: VERIFIED
```

This can derive **Missed Deterministic Opportunity Rate** without granting shadow routing any effect authority.

The same framework can later evaluate Laya in SHADOW mode:

```text
Laya shortlist
vs CapabilityRouter canonical decision
vs actual verified outcome
```

Laya remains non-authoritative.

## Sequencing

Telemetry must not delay the currently open causal H-080B.2 blockers.

Canonical order:

```text
1. close H-080B.2 causal blockers
   - promotion-grade Browser receipt enforcement
   - empirical verifier validation
   - normal-runtime coordinator wiring
   - durable lifecycle ownership

2. Operational Telemetry Phase 1
   - TelemetryEventV1
   - sink interface
   - local rebuildable SQLite event store
   - lineage/privacy/sanitization
   - initial owner-boundary instrumentation

3. Operational Telemetry Phase 2
   - instrument H-080B Experience funnel
   - candidate / validation / replay / promotion / reuse / drift events

4. H-080B.3
   - real Electron/local-server/dogfood proof
   - proof must emit telemetry so the first product run is analytically inspectable

5. Operational Telemetry Phase 3
   - project real event history into ORA/VOLC and the priority metrics

6. Operational Telemetry Phase 4
   - ShadowRouter opportunity metrics
   - post-goal/oververification analytics
   - dashboards/time series

7. H-081 / Laya
   - SHADOW first
   - measured against canonical router/outcome telemetry
```

Phase 1 should be implemented immediately after H-080B.2 hardening and before substantial H-080B.3/Laya expansion.

## Reliability requirements

Telemetry must be:
- non-authoritative;
- fail-open with respect to product execution;
- append-oriented;
- bounded;
- privacy-preserving;
- versioned;
- correlated by canonical lineage;
- independently testable;
- queryable;
- rebuildable where source evidence exists.

Telemetry must never:
- grant effect authority;
- issue RoutingCertificates;
- mark verification success;
- promote capabilities;
- change retry behavior;
- bypass the Experience promotion policy;
- become a required dependency for Browser execution.

## Phase 1 acceptance contract

Phase 1 is complete when:

```text
[ ] TelemetryEventV1 schema exists and is versioned
[ ] event IDs are unique
[ ] canonical task/run/operation lineage is preserved when available
[ ] unknown measurements remain null/absent
[ ] TelemetrySink abstraction is non-authoritative
[ ] local SQLite sink is append-oriented and bounded
[ ] telemetry failure cannot fail an otherwise-valid product execution
[ ] sensitive content is rejected/sanitized by default
[ ] at least routing/provider/capability/verification/outcome/Experience lifecycle boundaries emit events
[ ] events can reconstruct one normal run chronologically
[ ] ORA/VOLC can be projected from captured facts without inventing counts
[ ] deletion/rebuild semantics are documented/tested
[ ] no direct generic-core -> Workstation dependency regression
```

Do not build the dashboard before this contract is true.

## Product question

The telemetry plane exists to let Hermes Work answer with evidence:

> **Are verified operational outcomes becoming cheaper, more deterministic, more reusable and more reliable over time — and where are they not?**

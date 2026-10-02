# Liveness, Progress & Budget Governance — 2026-09-28

**Status:** PLANNED / HIGH-PRIORITY OPERATIONAL HARDENING  
**Roadmap role:** immediate investigation + medium-term hardening after current H-080 release blockers; circuit-breaker pieces may be pulled forward wherever they close a reproduced failure.  
**Canonical owners reused:** EvidenceState, AwaitCondition/AwaitContinuation, RuntimeSupervisor, WorkerRegistry, ORAMetrics, TaskRun, Policy Engine, scheduler and existing model/provider routing.  
**Non-goal:** do not create a second scheduler, task queue, metrics database or agent loop.


## 2026-10-02 policy refinement — budget pressure is not proof of waste

Recent long-run evidence confirms that many tool/model calls can be legitimate when each round reduces pending work or adds verified evidence. The default autonomous policy must not equate raw token count, call count or elapsed work with lack of progress.

```text
cost rising + verified progress/pending reduction -> PROGRESSING (within explicit hard caps)
cost rising + no new evidence/effect + repeated equivalent state/failure -> BUDGET_PRESSURE / LOOP_SUSPECTED
```

User/admin hard budgets and risk limits remain authoritative. This changes the default interpretation of budget pressure, not the ability to enforce an explicit cap.

TaskRun telemetry should expose Cost per Verified Outcome, tokens per verified outcome, pending-item delta, LLM/System-2 wake rate, System-1 hit/abstain/fallback, retries without new evidence and authority-supersession events.

Canonical: [LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md](LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md).


## Problem

A long-running agent can be **alive without making progress**.

Typical failure modes include:

- repeated planning/tool/retry loops with no new externally meaningful state;
- context compaction or recovery repeatedly returning to the same failing condition;
- a required MCP/tool/dependency becoming unhealthy while the agent silently degrades and
  continues;
- “waiting” implemented as an active loop that consumes model calls and context;
- provider/model routing continuing to spend after marginal information gain collapses;
- retries that change wording but not the operational state;
- a technically healthy worker consuming budget indefinitely because no explicit
  progress invariant exists.

Existing Workstation mechanisms bound many individual operations, but a durable agent
needs a cross-cutting answer to:

> **Is continuing this trajectory still justified by new evidence/progress?**

## Context

The Workstation already has most of the components needed:

- `EvidenceState` and explicit runtime states;
- non-resident `AwaitCondition` / `AwaitContinuation`;
- RuntimeSupervisor and Recovery Plane;
- WorkerRegistry and durable worker lifecycle;
- deadlines/cancellation/backpressure;
- budget and model/provider routing contracts;
- ORAMetrics / operational resolution metrics;
- Execution Journal and TaskRun lineage;
- RunClosure/Verification contracts.

Therefore the proposal is a **policy and evaluation layer over canonical evidence**,
not a new executor.

Recent external harness failures are useful falsifiers: very long loops can consume
massive tokens while producing little or no verified change. A production-grade
Workstation should detect that class much earlier.

## Hypothesis / proposal

### 1. Progress Watchdog

Define a progress policy that evaluates a sliding window of canonical evidence.

Potential **positive progress signals**:

- new verified external effect;
- new verifier evidence materially reducing uncertainty;
- canonical state transition toward the desired state;
- dependency/blocker resolved;
- new artifact/deliverable;
- new bounded information that changes the next operational decision;
- successful handoff/resume transition;
- completed subgoal with acceptance evidence.

Potential **anti-progress signals**:

- repeated equivalent SemanticState;
- repeated identical tool/action sequence;
- repeated same failure/refusal with no changed material input;
- rising tokens/cost without new evidence/effect;
- repeated compaction/reconstruction around the same unresolved state;
- long active runtime with only heartbeat/poll traffic;
- oscillation between two states/routes.

The watchdog should not decide task semantics from scratch. It consumes existing
state/evidence and can classify:

```text
PROGRESSING
WAITING
STALLED
LOOP_SUSPECTED
BUDGET_PRESSURE
DEPENDENCY_BLOCKED
NEEDS_REASONING
NEEDS_HUMAN
STOP_REQUIRED
```

### 2. Circuit breakers

Make run/task policy able to declare bounded ceilings:

- max active wall-clock time;
- max active steps/tool rounds;
- max cumulative model/tool cost;
- max repeated equivalent state count;
- max identical failure/refusal count;
- max no-progress interval;
- max recovery/compaction cycles without new evidence;
- optional provider/tool-specific retry budgets.

A circuit breaker should transition to a typed state and preserve evidence; it must not
silently convert into “completed” or blindly restart the same trajectory.

### 3. Waiting is non-resident

Preserve the existing `AwaitCondition` principle:

```text
semantic wait -> persist condition/continuation -> release worker/compute
event/wake hint -> authoritative recheck -> resume if condition is true
```

Polling may exist only where the external system provides no better observer and must be
bounded by cost/deadline/backoff policy.

### 4. Required/optional capability health

Capabilities/dependencies should expose enough typed state to distinguish:

```text
required | optional
healthy | degraded | unavailable
reason
last_verified_at
fallback/degradation policy
```

If a required capability is unavailable:

- fail closed, or
- request an explicit policy/human decision to continue under declared degradation.

Do not silently run a different workflow whose assumptions no longer match the original
OperationIntent.

Optional dependencies may degrade only according to a declared policy.

### 5. Typed operational refusals/failures

Prefer structured reasons over free-text errors when they affect orchestration:

```text
permission_denied
precondition_failed
authority_required
dependency_unhealthy
budget_exhausted
deadline_exceeded
verification_failed
incompatible_version
cancelled
stalled
loop_detected
```

These reason codes should feed policy, UI, metrics and recovery without parsing natural
language. They extend existing status/evidence contracts; they do not replace provider/tool
error detail.

### 6. Cost per Verified Outcome

Add a benchmark/telemetry metric oriented around useful outcomes rather than raw tokens:

```text
Cost per Verified Outcome =
  total attributable model + tool + runtime + retry + verifier cost
  / verified accepted outcomes
```

Rules:

- if a denominator or cost component is unavailable, report `None`/partial truthfully;
- compare task classes only when acceptance criteria are comparable;
- retain raw token/latency/action metrics for diagnosis;
- do not optimize this metric alone at the expense of safety or quality.

### 7. Explicit execution phases

Expose a UI-neutral phase projection distinct from final lifecycle state:

```text
planned
preparing
awaiting_authority
authorized
executing
verifying
waiting
recovering
completed
failed
cancelled
```

This should be a projection from canonical owners, not an alternate state machine. It lets
operators distinguish “thinking”, “about to mutate”, “mutating”, “verifying” and
“non-resident wait” without chain-of-thought exposure.

## Why this matters

Long-lived autonomy becomes useful only when the system can prove both:

1. it is still alive; and
2. continuing is producing enough progress to justify the risk/cost.

This initiative improves:

- runaway-loop containment;
- economic predictability;
- operator trust;
- graceful dependency failure;
- clear model/provider escalation;
- correct non-resident waiting;
- incident diagnosis;
- apples-to-apples harness/model benchmarking.

It also prevents “autonomy duration” from being confused with “autonomy quality”.

## Possible implementation paths

1. **Define progress evidence**
   - map existing Execution Journal / EvidenceState / verifier / effect events to a small
     set of progress categories;
   - keep the definition conservative and task-class aware.

2. **Build watchdog as policy over existing owners**
   - implement evaluation in supervisor/policy code rather than inside the model loop;
   - persist only necessary counters/windows through existing journal/task metadata;
   - make the watchdog unable to perform normal task work.

3. **Introduce circuit-breaker policy fields**
   - extend existing task/run budget contracts where fields are missing;
   - choose safe defaults for long-running agent workloads;
   - require explicit override for materially larger spend/runtime.

4. **Capability health**
   - add health/degradation projection to existing capability/dependency registry;
   - define required-vs-optional semantics;
   - wire external MCP/process health into the projection without turning MCP into canonical
     task state.

5. **Typed reasons**
   - normalize common Workstation-owned orchestration failures;
   - keep raw provider/tool error as nested evidence;
   - ensure refusals remain atomic and do not mutate lifecycle state.

6. **Metrics**
   - derive Cost per Verified Outcome from attributable TaskRun/journal/metrics data;
   - benchmark at least two model-routing/browser/harness strategies on the same task set;
   - preserve `None` for unknown values rather than fabricating precision.

7. **Phase projection**
   - map existing TaskRun/EvidenceState/verification/await transitions into read-only phases;
   - expose to Desktop/Dashboard/TUI through existing resource/event surfaces.

## Dependencies / impacts

- V3.2 EvidenceState, deadlines/backpressure, persistent workers and model routing;
- V3.3 independent watchdog / policy boundary and dependency isolation;
- V3.4 evaluation/efficiency gates and replay;
- H-080A truthful production metrics and real execution evidence;
- H-080B verified experience feedback loop;
- ORAMetrics / VOLC operational truth owners;
- AwaitCondition / AwaitContinuation;
- Execution Journal / TaskRun lineage;
- future browser-backend and model-routing comparative benchmarks.

## Open questions

1. What is the smallest progress vocabulary that works across browser, coding, research,
   shell and API tasks?
2. Which progress signals are deterministic and which require semantic classification?
3. How should a watchdog distinguish useful deliberate exploration from a loop?
4. Should no-progress budgets scale by task complexity/risk, and who is allowed to raise
   them?
5. Which cost components are reliably attributable today?
6. How should local/free compute be represented in Cost per Verified Outcome?
7. What is the correct user experience when a required dependency becomes unavailable
   mid-operation?
8. Can “equivalent state” be detected cheaply enough without making the watchdog itself a
   large inference cost?

## Completion criteria

- a synthetic/reproduced loop is classified and stopped/paused before its configured
  step/time/cost ceiling, with an auditable reason and no false successful completion;
- repeated equivalent-state/no-new-evidence trajectories trigger the expected
  `STALLED/LOOP_SUSPECTED` path;
- semantic waits release worker/model compute and resume only after authoritative
  condition recheck;
- a required unhealthy capability prevents silent degraded execution or requires explicit
  authorized degradation;
- an optional unhealthy capability follows its declared fallback policy without corrupting
  the task lifecycle;
- typed refusal/failure reasons are available to policy/UI/recovery without parsing prose;
- at least one workload is compared under two routing strategies with truthful task success,
  latency, usage/cost, retries, verifier cost and Cost per Verified Outcome;
- execution-phase projection is identical across supported clients because it derives from
  canonical state;
- watchdog/circuit-breaker code cannot execute normal task capabilities;
- focused tests, full Workstation, seam and relevant product qualification gates pass on the
  exact candidate head.

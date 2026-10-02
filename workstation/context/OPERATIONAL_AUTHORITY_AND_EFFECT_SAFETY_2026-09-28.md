# Operational Authority & Effect Safety — 2026-09-28

**Status:** PLANNED / HARDENING INITIATIVE  
**Roadmap role:** high-priority cross-cutting hardening after the current H-080A/H-080B gates; some parts may be pulled forward only when they directly close a current blocker.  
**Canonical owners reused:** `OperationIntent`, `TaskRun`, `OperationalCapability`, Policy Engine, Verification Contracts, Execution Journal, Run Closure and Human Handoff.  
**Non-goal:** do not create a second control plane, approval store, evidence store, task store or effect database.


## 2026-10-02 policy refinement — stale run fence must support safe continuation

`stale_task_run` is a valid mutation fence: an old run must not keep writing after canonical TaskRun ownership moved. It must not turn ordinary supersession into an unrecoverable dead end when the user still authorizes the underlying work.

Distinguish:
```text
SUPERSEDED / AUTHORITY_SUPERSEDED
REVOKED_BY_USER
CANCELLED
POLICY_REVOKED
```

For `SUPERSEDED`, the runtime may atomically checkpoint pending/uncertain work and hand it to the current/new canonical run, then resume only unconfirmed work. Explicit revoke/cancel/policy revocation continues to fence future mutation until the proper authority path is satisfied.

> **STALE RUN MAY NOT MUTATE; VALID WORK SHOULD SURVIVE RUN REPLACEMENT WITHOUT DUPLICATING UNCERTAIN EFFECTS.**

Canonical: [LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md](LAYA_SYSTEM1_DIRECT_INTEGRATION_2026-10-02.md).


## Problem

Hermes Work already has a strong verified-execution architecture, but several recent
agent-system failure modes expose residual gaps at the boundary between **intent and
effect**:

1. user control requests such as stop/pause/cancel/revoke can be semantically weaker
   than an already-running operational objective if they are treated as ordinary
   conversation rather than authority-changing control;
2. an operation can be correctly refused yet still leave locks, ownership records,
   partial lifecycle state or other residue;
3. successful tool dispatch does not prove that the intended external effect occurred;
4. a post-hoc log of tool calls is not the same thing as a canonical account of
   externally meaningful effects;
5. effect risk is not fully captured by a generic “mutation vs read” distinction:
   reversibility, blast radius, externality, monetary cost and required verification
   strength differ materially between effects.

The Workstation should strengthen the existing path rather than add another execution
layer.

## Context

The current architecture already provides most of the necessary primitives:

```text
trusted ingress
-> immutable OperationIntent
-> routing / authority admission
-> OperationalCapability
-> pre-dispatch policy
-> REAL I/O
-> raw post_tool_call
-> verification contract
-> canonical TaskRun commit
-> journal / UI projections
```

H-076, H-077, H-078 and H-080 established that verification, authority, evidence and
completion are distinct concerns. Recent external references and upstream/runtime bugs
suggest four additional invariants worth making explicit:

- **Control authority must outrank task continuation.**
- **A refused operation must be operationally atomic.**
- **Important effects need both preconditions and postconditions.**
- **Effect observability should be a projection of canonical evidence, not inferred from
  prose or tool-call success.**

These are extensions of current owners, not new horizontal subsystems.

## Hypothesis / proposal

### 1. First-class ControlIntent

Introduce a typed control semantic that can be resolved at trusted ingress and has
priority over the current `OperationIntent`:

```text
STOP
PAUSE
RESUME
CANCEL
REVOKE_AUTHORITY
```

A `ControlIntent` changes whether existing work may continue. It does not become a
second task/request model.

Required properties:

- control can be triggered by canonical commands or high-confidence natural-language
  equivalents;
- `STOP/CANCEL/REVOKE_AUTHORITY` fence future mutations before additional tool
  dispatch;
- the control action is journaled with principal, scope, target TaskRun/operation and
  provenance;
- cancellation/revocation propagates deterministically to owned workers, processes,
  BrowserTasks, AwaitConditions and pending tool work according to ownership;
- a stale or ambiguous target fails safe and asks for clarification rather than
  cancelling unrelated work.

### 2. Refusal Atomicity

Formal invariant:

```text
Refused Operation -> ΔOperationalState = 0
```

The only permitted state change from a refused operation is the auditable refusal
record itself.

A denied operation must not leave:

- locks;
- false child/parent ownership;
- pending worker relationships;
- partial process/browser allocation;
- mutated task lifecycle state;
- leaked capability leases;
- residual external effects.

Where allocation is unavoidable before admission, rollback must be deterministic and
proven.

### 3. PreconditionVerifier -> Effect -> PostconditionVerifier

Extend existing verification contracts so mutating capabilities can declare both:

- **preconditions:** what must be true before crossing the effect boundary;
- **postconditions:** what independent evidence must be observed before success can be
  committed.

Examples:

```text
send email:
  pre  -> recipient/authority/content integrity/approval
  effect -> provider send
  post -> provider receipt/message identity

browser mutation:
  pre  -> bound task/run + trusted payload + authority
  effect -> UI/network mutation
  post -> persisted/readback state if risk contract requires it

file mutation:
  pre  -> path/scope/ownership/expected base
  effect -> write
  post -> hash/content/stat readback
```

Not every intermediate UI gesture requires expensive independent verification. The
verification strength is selected at the **externally meaningful effect boundary**.

### 4. Effect Ledger as a derived projection

Add a typed **Effect Ledger projection** over existing Execution Journal / TaskRun /
verification evidence. It is not a new database or authority.

An entry should answer:

```text
what changed?
who/what owned the operation?
which OperationIntent authorized it?
which principal granted authority?
what target/resource was affected?
was the effect reversible?
what did it cost?
what verifier/postcondition observed the result?
was it accepted / committed / rolled back / uncertain?
```

This gives incident/recovery tooling a concise external-effect view while preserving the
journal as the canonical event source.

### 5. Typed effect properties

Where useful, extend capability/effect metadata with conservative fields such as:

- `reversibility`: reversible | compensatable | irreversible | unknown;
- `externality`: local | remote-private | remote-public | physical;
- `cost_ceiling`;
- `blast_radius` / target cardinality;
- required authority level;
- required verifier strength;
- rollback/compensation handle when one exists.

These are policy inputs, not model-generated guarantees.

## Why this matters

This hardening reduces four high-impact failure classes:

1. **agent continues after the human intended to stop it**;
2. **denial succeeds logically but corrupts lifecycle state**;
3. **tool success is mistaken for outcome success**;
4. **incident response cannot reconstruct which real-world changes occurred**.

It also makes the Workstation safer for browser, shell, publishing, money, remote APIs,
future physical-device capabilities and long-running automation without requiring every
model to be perfectly aligned.

## Possible implementation paths

1. **Ingress / control**
   - extend the existing generic ingress/admission surfaces with typed control commands;
   - resolve natural-language stop/pause/revoke before normal operational resolution;
   - reuse TaskRun/ownership fencing and existing cancellation paths.

2. **Refusal atomicity**
   - write falsification tests first for capability refusal, worker/subagent denial,
     Browser admission and MCP/tool rejection;
   - snapshot relevant canonical state before the denied request and assert no delta
     except refusal evidence;
   - repair owners rather than compensating in a new global cleanup service.

3. **Effect pre/post verification**
   - extend existing `VerificationContract` and `CapabilityInvocation` metadata only
     where current fields are insufficient;
   - reuse H-080A’s production-path work as the first real reversible mutation proof;
   - prefer deterministic readback/oracles over same-model self-report.

4. **Effect Ledger**
   - implement a read-only projection/query over journal + invocation + verification
     records;
   - add UI/incident export only after the projection is stable;
   - do not introduce a second effect store.

5. **Policy**
   - derive approval/verification requirements from declared effect properties;
   - unknown/high-risk classifications fail closed or route to human handoff.

## Dependencies / impacts

- H-080A production authority + real dispatch + post-effect evidence qualification;
- H-076 Verification Contract Synthesis;
- D-014 canonical TaskRun identity;
- D-015 commit-before-terminal-projection;
- D-020 declarative `OperationIntent`;
- V3.2 EvidenceState, deadlines and Human Handoff;
- V3.3 watchdog/policy boundary;
- BrowserTask ownership and Browser Operational Admission;
- H-078/H-079 upstream-first/minimum-seam discipline.

This initiative must not bypass current release blockers. When a piece directly repairs
H-080A, it may be implemented inside that lane rather than waiting for a later milestone.

## Open questions

1. Which control intents can be inferred safely from natural language without explicit
   confirmation?
2. What is the minimal ownership target required for STOP versus CANCEL versus
   REVOKE_AUTHORITY?
3. Which effect classes require independent postcondition readback by default?
4. Can all useful Effect Ledger fields be derived from existing journal/invocation
   records, or are small additive fields required?
5. How should compensatable-but-not-reversible effects be represented?
6. Should effect-risk metadata live entirely on `OperationalCapability`, or partly on
   the invocation because risk can depend on arguments/cardinality?
7. How do we prove refusal atomicity across process boundaries and external tool
   allocation without hiding compensating actions?

## Completion criteria

This initiative is considered qualified only when all relevant criteria below have
evidence on the exact candidate head:

- a running operation receives natural-language and explicit STOP/CANCEL/REVOKE and no
  new mutation crosses the effect boundary afterward;
- cancellation/revocation cleanup follows canonical ownership and does not affect an
  unrelated run;
- denied capability/subagent/browser operations pass Refusal Atomicity tests with no
  state delta except the refusal/audit receipt;
- compressed/truncated/untrusted arguments fail closed before an external effect;
- one real reversible external mutation passes:
  `precondition -> real effect -> independent readback -> VERIFIED -> COMMITTED`;
- a failed/inconclusive postcondition cannot become committed success;
- Effect Ledger can reconstruct the externally meaningful effects of a run, including
  authority, owner, target, verification and final disposition, without a second source
  of truth;
- unknown or high-risk effect classification routes conservatively;
- focused, full Workstation, seam and required native/product qualification gates are
  green.

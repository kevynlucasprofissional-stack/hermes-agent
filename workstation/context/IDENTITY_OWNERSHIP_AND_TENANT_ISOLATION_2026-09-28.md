# Identity, Ownership & Tenant Isolation — 2026-09-28

**Status:** PLANNED / HIGH-PRIORITY HARDENING  
**Roadmap role:** medium-term structural hardening with selected P0 investigations when upstream/runtime evidence indicates possible boundary violations.  
**Canonical owners reused:** Hermes profiles/sessions, canonical TaskRun, OperationIntent, WorkerRegistry, BrowserTask, Policy Engine, Execution Journal, runtime supervisor, existing sandbox/container owners.  
**Non-goal:** do not create an independent Agent DB, SessionDB, Kanban, Memory store, browser store or second control plane.

## Problem

As Hermes becomes a persistent multi-profile, multi-session, multi-worker system, several
identities coexist:

```text
Gateway / Runtime
Profile / Agent
Session
Task / TaskRun / OperationIntent
Worker / Subagent
Process
BrowserTask / live page / browser profile
Effect / external resource
```

If these identities are conflated or only implicitly related, failure modes include:

- an orphaned process surviving the task that created it;
- one profile observing or cancelling another profile's worker/subagent;
- state, browser resources or attachments resolving under the wrong session;
- cleanup at a runtime/container boundary destroying work owned by an unrelated task;
- restart/recovery reconstructing transcript text but not operational ownership;
- MCP/plugin subprocesses inheriting secrets or environment that they were never
  authorized to receive;
- UI/client projections appearing to “own” state that actually belongs to another
  canonical subsystem.

The existing Workstation already has strong local ownership contracts. The missing
piece is to make **cross-boundary ownership and non-interference** an explicit,
system-wide invariant.

## Context

Hermes Work has repeatedly converged on the same principle in browser, durable execution
and upstream reliability work:

```text
Execution Location != Semantic Owner
```

A process may run in Docker, SSH, a local subprocess or a browser renderer while its
semantic owner remains one TaskRun/OperationIntent. Likewise, a Gateway may host many
profiles and sessions without becoming the owner of every resource it transports.

The roadmap and current code already contain:

- canonical TaskRun identity;
- BrowserTask identity and task/page ownership;
- session ownership/locking;
- WorkerRegistry lineage;
- resource projections;
- Policy Engine scopes;
- Execution Journal lineage;
- recovery/reconstruction mechanisms.

This initiative should **connect and falsify those owners**, not replace them.

## Hypothesis / proposal

### 1. Explicit identity vocabulary

Treat the following as distinct identities unless a specific adapter proves equivalence:

```text
Runtime/Gateway ID
Profile/Agent ID
Session ID
Task ID
TaskRun ID
Operation ID / OperationIntent
Worker/Subagent ID
Process ID
BrowserTask ID
External Resource / Effect ID
```

Canonical rule:

```text
Agent/Profile ID != Session ID != Operation ID != Process ID
```

A profile/agent may span sessions; a session may contain many operations; an operation
may own many workers/processes; a process location may change across recovery.

### 2. Ownership graph as a derived projection

Expose a read-only ownership graph derived from existing canonical owners:

```text
human/system principal
  -> profile/agent
    -> session
      -> task / TaskRun
        -> OperationIntent
          -> worker/subagent
          -> process
          -> BrowserTask/resource
          -> effect
```

Not every edge is mandatory for every object, but every mutating effect or persistent
resource must be traceable to a canonical owner/principal or be explicitly classified
as system/human-owned outside agent authority.

This projection should power debugging, recovery and the UI; it must not become a new
state authority.

### 3. Cross-Tenant Isolation matrix

Create a repeatable two-tenant/profile falsification suite:

```text
Profile A
Profile B
```

For each relevant resource type, test:

```text
A creates -> B attempts discover
A creates -> B attempts read
A creates -> B attempts mutate
A creates -> B attempts cancel/destroy
A ends/restarts -> verify correct cleanup/persistence
```

Resource classes should include at least:

- session/transcript projection;
- Task / TaskRun / OperationIntent;
- worker/subagent;
- background process;
- container/sandbox/workspace;
- BrowserTask/live page/profile;
- cache/artifact;
- attachment/download/upload;
- secret/credential;
- MCP server/tool;
- memory/procedure references;
- event stream / journal projection.

Expected default: **non-interference unless explicit delegation/policy grants access**.

### 4. Allowlist-first secret/environment propagation

For stdio MCPs, plugins, skills and external subprocesses:

- construct a minimal environment from an explicit allowlist;
- do not pass `os.environ` and attempt to remove known secret names by blacklist;
- keep Workstation/internal secret material outside child environments unless the
  component contract explicitly requests a scoped credential;
- prefer handles/write-only credential mechanisms where practical;
- journal which capability/credential scopes were granted without logging the secrets.

### 5. Agent Registry as a projection, not a database

Provide a compact operator view derived from existing runtime/profile/session/worker
owners:

```text
agent/profile id
runtime/gateway
principal owner
active task/run
active session(s)
declared capabilities
health
current phase
budget/cost estimate
last activity
isolation/sandbox mode
```

The purpose is inventory and operations, not creating another source of identity.

## Why this matters

Long-lived multiagent systems fail at boundaries more often than at the center. Strong
ownership/tenant isolation provides:

- deterministic cancellation and cleanup;
- safe restart/recovery;
- prevention of cross-profile data/secret leakage;
- clearer accountability for external effects;
- simpler incident forensics;
- operator confidence when many agents share one runtime;
- a stable abstraction even when execution moves between local, container, browser,
  remote or future distributed backends.

It also reduces accidental coupling to Hermes implementation details: Workstation
semantics can remain stable while profile/session/runtime internals evolve upstream.

## Possible implementation paths

1. **Audit existing IDs and edges**
   - enumerate canonical identity types and current storage/owner;
   - find implicit conversions/fallbacks (for example “active session” used when an
     operation ID should be required);
   - document only gaps reproducible on current main.

2. **Ownership projection**
   - add a typed read-only projection API over existing owners;
   - make missing lineage explicit instead of guessing it from transcript/context;
   - use the projection in diagnostics and later in the Control Center.

3. **Cross-tenant test harness**
   - build an A/B fixture that can exercise profile/session/process/browser/MCP/resource
     isolation;
   - include restart and recovery boundaries, not only same-process reads;
   - include negative assertions for discoverability and cancellation.

4. **Secret/MCP hardening**
   - audit current environment construction for stdio MCP/plugin child processes;
   - move to allowlist-first construction;
   - add canary secrets to tests and prove they never appear in child environment,
     logs or tool-visible state unless explicitly granted.

5. **Cleanup and recovery**
   - resolve cancellation/cleanup via ownership graph;
   - avoid container-wide/process-wide cleanup when only one operation/profile owns the
     resource;
   - prove resources that should survive restart retain the same semantic owner.

6. **Operator registry**
   - expose the derived Agent Registry through existing resource/event projection;
   - no new database or separate lifecycle.

## Dependencies / impacts

- D-002 and D-007 canonical-owner discipline;
- D-014 TaskRun authority and D-015 commit ordering;
- Browser Ownership & Recovery Reconciliation;
- V3.2 durable session ownership, WorkerRegistry and typed resources;
- V3.3 control-plane boundary, isolation and plugin/MCP hardening;
- H-078/H-079 upstream-first/minimum-seam policy;
- Hermes upstream profile/gateway/session behavior;
- runtime supervisor / Recovery Plane;
- future remote/distributed worker backends.

## Open questions

1. Is “Agent ID” best mapped to the Hermes profile identity, or does Workstation need a
   provider/runtime-neutral alias projection over profile identity?
2. Which resources are legitimately session-scoped versus TaskRun/operation-scoped?
3. Which ownership edges must be durable versus reconstructable from canonical state?
4. How should explicitly shared resources be represented without weakening the default
   non-interference rule?
5. What is the minimal stable identity contract for external runtimes/harnesses?
6. Which child processes genuinely require inherited environment variables, and which can
   run under an almost-empty environment?
7. How do we display ownership in the UI without creating the impression that the view is
   the authority?

## Completion criteria

- a canonical identity/ownership matrix names the authoritative owner for every persistent
  or effectful Workstation resource class;
- every mutating effect/process/BrowserTask/worker can be traced after restart to its
  TaskRun/operation and principal, or is explicitly classified outside agent authority;
- Cross-Tenant Isolation tests prove Profile A cannot discover/read/mutate/cancel Profile
  B resources across the defined matrix unless a tested delegation policy permits it;
- stopping/restarting one profile/session/task does not destroy unrelated resources owned
  by another;
- stdio MCP/plugin child environments contain only allowlisted variables and canary
  internal secrets are absent unless explicitly granted;
- secret values never appear in diagnostic/event projections;
- the Agent Registry view is derived from existing canonical owners and introduces no new
  identity/state database;
- recovery/reconstruction preserves semantic ownership when execution location changes;
- focused isolation, full Workstation, seam and required native/product gates pass on the
  exact candidate head.

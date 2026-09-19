# H-078 — Upstream Migration as Decoupling / Unidirectional Workstation Supervision

Date established: 2026-09-19  
Status: **ACTIVE STRATEGIC MIGRATION PROGRAM**  
Downstream baseline when established: `main@378b5a2df35ac05fe37a606298502d7bb974786d`  
Upstream candidate observed during analysis: `NousResearch/hermes-agent@1f4fbd5145d641c3a815dc97332103679e6139d9`

## Executive decision

Hermes Work will **adapt to the current Hermes upstream while using that migration to
progressively remove direct Workstation seams from Hermes internals**.

This is not a big-bang standalone rewrite and it is not a simple "sync fork" exercise.

The direction is:

```text
adapt upstream
-> preserve Workstation semantics
-> classify every overlap
-> extract coupling boundaries while resolving it
-> move Workstation observation/control onto generic Hermes extension surfaces
-> shrink direct Hermes -> Workstation knowledge
-> keep Hermes as the first-party laboratory / reference reasoner
-> eventually make Work Runtime independently executable
```

The migration is therefore **Upstream Migration as Decoupling**.

## The non-negotiable direction of dependency

The target relation is unidirectional:

```text
Hermes Agent / upstream
        |
        | generic lifecycle + middleware + provider/adapter contracts
        v
Workstation supervisory adapter
        |
        v
Hermes Work Runtime / Control Plane
```

Hermes core must progressively stop importing or special-casing Workstation.

Workstation may consume **generic, versioned Hermes extension contracts** and may observe,
wrap, veto, pause, modify, verify, reconcile or redirect execution through those contracts.
Hermes should not need model-level knowledge that "it must use Hermes Work".

This directly addresses the failure mode where seam removal would make Hermes "forget"
the Workstation. Correctness must not depend on the LLM choosing `work_execute`, following a
prompt convention, or remembering a Workstation-specific workflow.

The Workstation should be able to supervise **normal Hermes behavior**.

## Supervisor, not hidden prompt convention

The desired runtime semantics are:

```text
Hermes proposes / acts normally
        |
        +--> LLM request observed
        +--> tool request observed
        +--> tool execution can be wrapped/intercepted
        +--> result observed
        +--> completion candidate observed
                         |
                         v
                 Workstation Control Plane
                 - admit / reject
                 - pause / ask human
                 - substitute deterministic capability
                 - reconcile uncertainty
                 - verify outcome
                 - compile experience
```

The model can remain unaware of the Workstation-specific machinery.

`work_execute` remains useful as an explicit Capability/Intent execution API and as a
deterministic fast path, but **it must not remain a correctness dependency for Workstation
participation**.

## Why the current upstream makes this feasible

The current fork already contains generic Hermes plugin/lifecycle and middleware surfaces,
and the newer upstream strengthens the same direction.

Observed generic surfaces include:

- lifecycle hooks: `pre_tool_call`, `post_tool_call`, `pre_verify`,
  `pre_api_request`, `post_api_request`, session/task lifecycle hooks;
- behavior-changing middleware:
  - `tool_request` — rewrite effective tool arguments;
  - `tool_execution` — wrap the actual tool execution callback;
  - `llm_request` — rewrite/observe provider request payloads;
  - `llm_execution` — wrap provider execution;
- plugin registration through `PluginContext.register_hook()` and
  `PluginContext.register_middleware()`;
- browser/provider/plugin boundaries in the modern upstream.

These are materially better extraction targets than injecting Workstation imports into
`agent/conversation_loop.py`, `agent/tool_executor.py` or `tools/browser_tool.py`.

The strategic insight is therefore:

> **Do not recreate old Workstation patches inside the upstream's new module layout when a
> generic observer/middleware/provider boundary can own the same behavior.**

## Current seam map on the downstream baseline

### Tier A — inward core seams: retire progressively

These are the highest-priority dependencies because generic Hermes code knows about
Workstation directly.

- `agent/conversation_loop.py`
  - invokes Workstation turn preparation;
  - imports Workstation routing/constraint behavior;
  - projects Workstation continuation state into provider context.
- `agent/tool_executor.py`
  - calls Workstation durable-execution state;
  - performs Workstation mutation preparation/recording;
  - captures raw results for Workstation compilation/learning.
- `agent/turn_finalizer.py`
  - calls Workstation Kanban/finalization and procedure-trace promotion logic.
- `tools/browser_tool.py`
  - directly imports Workstation Browser routing and Workstation artifact/reference/task
    helpers.

Target: replace these with Workstation-owned subscribers/adapters over generic Hermes
surfaces. No replacement seam may require the model to remember to opt in.

### Tier B — product edge adapters: isolate, then keep narrow

Examples:

- `hermes_cli/web_server.py` Workstation API projections;
- `hermes_cli/kanban_db.py` Workstation completion/acceptance integration;
- Desktop `electron/main.ts` / `preload.ts` and Workstation Browser IPC.

These are not equivalent to agent-core coupling. They are legitimate product integration
edges, but the long-term target is a narrow Work Gateway / Desktop adapter rather than
state ownership inside Hermes.

### Tier C — Workstation-owned code: preserve

`workstation/`, Workstation Browser runtime/task/session ownership, Control Plane,
Operational Capability Runtime, Verification, Experience Compiler, Journal, ArtifactStore,
Await/Trigger and canonical task/run semantics remain Workstation-owned.

The migration must move dependencies **toward** these owners, not duplicate them.

## Conflict classification for the upstream migration

Every overlap is classified as exactly one of:

1. **ADOPT_UPSTREAM** — generic Hermes behavior/structure wins.
2. **KEEP_WORKSTATION** — downstream-owned implementation has no upstream owner.
3. **SEMANTIC_PORT** — preserve Workstation invariant but implement it in the new upstream
   structure.
4. **EXTRACT_BOUNDARY** — do not merely port the patch; replace direct coupling with a
   generic hook/middleware/provider/adapter boundary.

`EXTRACT_BOUNDARY` is preferred whenever it can preserve behavior without teaching Hermes
core about Workstation.

Canonical merge rule:

```text
UPSTREAM STRUCTURE
+ WORKSTATION SEMANTICS
+ FEWER DIRECT SEAMS THAN BEFORE
```

## Migration safety rule: shadow before retirement

No existing seam is removed merely because a cleaner API exists.

For each seam:

```text
existing direct path
        |
        +--> remains authoritative temporarily
        |
        +--> new supervisory path runs in shadow/observation mode
                         |
                         v
             compare lineage / decisions / evidence
                         |
                  prove parity or improve
                         |
                    switch authority
                         |
                   remove old seam
```

Required proof before retirement:

- the Workstation still observes the same operational event;
- task/session/run/operation lineage is not lost;
- mutation effect classification is preserved;
- BrowserTask ownership and human-control fencing are preserved where applicable;
- uncertain mutation still reconciles before retry;
- ACK remains distinct from VERIFIED;
- Experience Compiler still receives admissible observations;
- deterministic reuse still works;
- normal Hermes tool use triggers supervision even when the model never calls
  `work_execute`;
- upstream regression tests plus Workstation qualification gates remain green.

## Implementation plan

### P0 — Establish the migration contract and seam audit — ACTIVE

- record D-026 and this canonical document;
- update ROADMAP / UPSTREAM / CURRENT_STATE / Intelligence / AGENTS guidance;
- add a repository seam-audit utility;
- freeze an upstream SHA at execution start;
- generate the initial seam inventory before touching merge conflicts.

Exit: no future coding agent can legitimately treat "reinsert all old Workstation imports"
as the default sync strategy.

### P1 — Controlled upstream baseline migration

- create an immutable pre-migration branch/tag;
- create `integration/upstream-YYYY-MM-DD`;
- merge/rebase only against the pinned upstream SHA;
- classify overlaps by ADOPT_UPSTREAM / KEEP_WORKSTATION / SEMANTIC_PORT /
  EXTRACT_BOUNDARY;
- adopt upstream decompositions instead of resurrecting old monoliths.

Exit: upstream structure is current while Workstation invariants remain testable.

### P2 — Hermes supervisory adapter in shadow mode

Build the first-party Hermes adapter as a Workstation-owned integration using generic
hooks/middleware.

Initial observation/control vocabulary:

```text
LLM_REQUEST
LLM_RESULT
TOOL_PROPOSED
TOOL_DISPATCH
TOOL_RESULT
TURN_VERIFY
TURN_END
SESSION_START/END
```

The adapter translates Hermes-specific payloads into Workstation-owned operational
observations. It must not become a second Control Plane or state store.

Exit: Workstation can reconstruct the relevant Hermes execution timeline without direct
imports from the agent loop.

### P3 — Tool execution seam retirement

Move the semantics currently embedded in `agent/tool_executor.py` toward generic
`tool_request` / `tool_execution` middleware plus `pre_tool_call` /
`post_tool_call` observation.

Target behavior:

- Workstation sees ordinary Hermes tool calls;
- it can preflight/admit/block/pause when required;
- it can wrap execution once, never double-dispatch;
- it captures result/effect/evidence after actual execution;
- deterministic capability substitution is possible only with equivalent authority and
  verification semantics.

Exit: `agent/tool_executor.py` no longer imports Workstation.

### P4 — Turn lifecycle / reasoning boundary retirement

Replace conversation-loop/finalizer Workstation knowledge with generic lifecycle/API
observation plus an adapter-controlled reasoning handoff.

Important constraint:

> Removing direct turn seams must not remove Workstation supervision.

Use generic pre/post request, pre-verify and session/task lifecycle surfaces where they are
semantically sufficient. Widen a **generic** upstream-compatible surface only when a
concrete missing event cannot be represented otherwise.

Exit: `agent/conversation_loop.py` and `agent/turn_finalizer.py` do not import
Workstation.

### P5 — Browser provider boundary

Adopt the upstream Browser architecture and preserve Workstation Chromium / BrowserTask as
a first-class provider/runtime behind a generic browser capability boundary.

Do not make the Workstation Browser a special branch scattered through generic
`browser_tool.py`.

Exit: generic browser facade does not know Workstation identity; Workstation Browser keeps
task ownership, native session, handoff, recovery and verification semantics.

### P6 — Session / Kanban / API edge isolation

Move Workstation-specific completion, projection and API behavior behind narrow adapters
or the Work Gateway while reusing upstream's decomposed session/kanban owners.

Exit: no Workstation state survives merely because an old Hermes internal DB/file shape was
preserved.

### P7 — Work Gateway and standalone runtime boundary

Expose the same Work Runtime through first-party Hermes adapter, MCP, ACP and native
API/SDK.

Hermes stays the default/reference reasoner, not the owner of Workstation truth.

### P8 — Hermes-less qualification

The decisive test:

```text
Hermes Agent = OFF

OperationIntent
-> Route
-> Execute
-> Await
-> Verify
-> Commit
-> Learn

PASS
```

Only after this passes should repository/process separation or a standalone Work Desktop
be treated as a product-packaging decision rather than an architectural rewrite.

## What must not happen

- no blind GitHub "Sync fork" into main;
- no restore of obsolete upstream monoliths merely to preserve old patches;
- no second task DB, BrowserTask store, journal, capability registry or Control Plane;
- no model-prompt convention as the only way to activate Workstation;
- no removal of a seam before shadow parity / E2E evidence;
- no new Workstation import into generic Hermes core unless explicitly temporary,
  documented, and accompanied by a retirement path;
- no conversion of MCP into the Workstation domain model; MCP/ACP remain adapters;
- no standalone rewrite that forks product logic into two copies.

## Target architecture

```text
Hermes Agent     Claude/Codex/etc.     Desktop/CLI
     |                 |                  |
     +----------- adapters/gateway -------+
                       |
                       v
              HERMES WORK RUNTIME
       OperationIntent / SemanticState
                Capability Router
               Certified Dispatch
        Execution / Await / Recovery
        Evidence / Verification / Commit
              Experience Compiler
                       |
          browser / files / APIs / OS
```

For the first-party Hermes path, the strongest desired property is:

> **Hermes does not need to know that it should use Workstation. Workstation knows how to
> observe Hermes, supervise the parts that matter, and intervene through generic contracts
> without depending on model compliance.**

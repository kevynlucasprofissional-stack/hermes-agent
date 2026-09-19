# H-078 — Upstream Migration as Decoupling / Minimum Necessary First-Party Seams

## H-078C — Actual upstream baseline adoption is now the active execution lane

The first real merge against the pinned upstream exposed 69 local UU conflicts and proved
that H-078B's generic-contract work did not itself adopt the upstream commit history or
modern owner decomposition. H-078B remains valid as semantic decoupling preparation;
actual baseline adoption, conflict resolution and ancestry qualification are tracked in
[UPSTREAM_CONFLICT_RESOLUTION_2026-09-19.md](UPSTREAM_CONFLICT_RESOLUTION_2026-09-19.md).

Do not call the upstream migration complete until the pinned SHA is an ancestor of the
qualified integration head/main.


Date established: 2026-09-19  
Status: **ACTIVE STRATEGIC MIGRATION PROGRAM**  
Downstream baseline when established: `main@378b5a2df35ac05fe37a606298502d7bb974786d`  
Upstream candidate observed during analysis: `NousResearch/hermes-agent@1f4fbd5145d641c3a815dc97332103679e6139d9`

## H-078B — Code-to-code migration specification (2026-09-19)

A deeper three-tree audit (common ancestor vs downstream vs upstream) materially refines
H-078. The problem is not "merge ~13k commits". It is **preserve causal Workstation
properties while moving them to the modern upstream owners**.

Audited structural picture:

- downstream changed 467 files since the common ancestor;
- upstream changed 10,165;
- only 129 paths were changed by both sides;
- 338 downstream-changed paths do not collide with upstream at the same path;
- 254 of those non-overlapping files are under `workstation/`;
- the overlap is concentrated in bridges: Desktop, tests, tools, agent, root files and CLI.

Therefore the Workstation runtime itself is comparatively protected. The migration risk is
in the bridges.

### Immediate downstream prerequisite

The H-078 branch was created before H-077/H-077.1 landed. At this refresh the downstream
`main` observed on GitHub is
`9f4ce89e56e204b3c8119d4b937be4462d0dfeaf`, while PR #35 is still based on an older
main and is not mergeable. **Do not start upstream integration from the current PR head.**
First reconcile H-078 with the then-current downstream main so H-077 truthful-core,
external-validity and qualification invariants are part of the migration baseline.

### Upstream pin rule

The deep audit used
`ea94d88e25d7699115a668c1757433361f3420dd` as a research snapshot. The upstream moved
during the investigation and has continued moving; a later GitHub refresh observed
`af2e9a4313f9a8a96618207ae111f9e824241949`.

The research SHA is **not** the automatic integration target. At implementation start:

```text
fetch upstream
-> choose one exact SHA
-> record it in the integration branch/docs
-> PIN IT
-> do not chase upstream/main until the migration cycle closes
```

### Semantic seams, not file dispositions

A path can contain multiple seams with different destinations. In particular,
`agent/tool_executor.py` simultaneously contains:

- uncertain-before-I/O checkpoint -> **UPSTREAM_ABSTRACT**;
- post-effect mutation observation -> **REMOVE** via raw `post_tool_call`;
- raw-result capture -> **REMOVE** via raw `post_tool_call`;
- durable internal persistence suppression -> **UPSTREAM_ABSTRACT**.

Accordingly `workstation/first_party_seams.json` v2 stores semantic concerns with
`symbol_or_concern`, semantic owner, current behavior, required ordering, disposition,
replacement, parity tests and sunset condition.

### Causal extension points that must exist before old seams are removed

The first migration needs a small generic contract set, with generic names and no
`if workstation` branches:

1. **turn_admission** — after session/task/turn identity exists, before compaction,
   auxiliary/provider work or route-sensitive execution;
2. **tool_batch_admission** — sees the complete assistant tool-call batch before any member
   dispatch; supports EXECUTE/FILTER/REWRITE/SYNTHETIC_RESULT/DEFER-HANDOFF;
3. **pre_authorized_dispatch** (name flexible) — FINAL args + authorization/guardrails
   passed + immediately before real external I/O;
4. **execution persistence disposition** — PERSIST/DEFER/OWNER_MANAGED (or equivalent) so
   compiled internal steps do not become accidental conversational turns;
5. **completion_admission** — can reject a terminal candidate before canonical DONE;
6. **TurnRoutePolicy** — one turn-scoped authority policy consulted by primary provider,
   auxiliary provider, browser, terminal, MCP and tool dispatch;
7. **TaskCompletionAdmission provider chain** — generalize the upstream PR acceptance
   prepare/revalidate/record-before-DONE pattern;
8. **browser-control capability registry** — extend the broker generically rather than
   adding Workstation conditionals for extra browser capabilities;
9. **TurnIngress** — trusted origin/authority/session metadata; user text is not authority.

### `run_agent.py` is a migration source, not a future integration owner

Do not preserve the downstream `run_agent.py` monolith. Extract the semantics currently
inside it and land them in the new upstream owners:

```text
turn_tool_round.py
    -> generic batch admission

tool executor / dispatch boundary
    -> authorized pre-effect hook
    -> execution persistence policy

Hermes first-party adapter
    -> progressive compilation
    -> human handoff
    -> route policy production
    -> Workstation observation

workstation/*
    -> domain truth / Control Plane / verification / learning
```

### Tool dispatch causal invariant

The mutation checkpoint must be exactly:

```text
final args
-> authorization + guardrails passed
-> PRE-AUTHORIZED-DISPATCH CHECKPOINT
-> REAL I/O
-> raw terminal result
-> post_tool_call Workstation observer
-> spill/truncate/conversation persistence
```

Checkpointing earlier can persist a mutation that never happened. Checkpointing later can
repeat an external mutation after process death. Ordering is part of correctness.

### Completion invariant

Workstation finalization is not a notification. It is admission:

```text
prepare acceptance outside txn
-> capture owner/run/state snapshot
-> canonical write txn
-> revalidate same owner/run/state
-> record acceptance receipt
-> only then commit DONE
```

The modern upstream PR-acceptance store is the reference implementation pattern.

### Browser convergence rule

Use the modern upstream `BrowserControlBroker` for routing, controller identity,
dispatch and bound-but-unavailable fail-closed behavior. Keep Workstation ownership of
BrowserTask/page lifecycle, native Chromium, human-control lease, persistence, semantic
anchors, recovery and Experience Compiler observations.

Migration is **dual-control, never dual-mutation-execution**:

```text
old route = authoritative execution

new broker/controller route in shadow:
  classify
  resolve task/lane/controller
  predict capability + fail-closed outcome
  DO NOT execute mutation

compare
-> switch authority only after parity
```

Reads may be compared more aggressively; mutation paths must never click/type/submit twice.

### First implementation target

Create a first-party Hermes integration layer such as:

```text
workstation/integrations/hermes/
    adapter.py
    turn_admission.py
    tool_batch_admission.py
    tool_observer.py
    completion_admission.py
    browser_controller.py
    api.py
```

or an equivalent `plugins/workstation/` façade. The façade translates Hermes <->
Workstation; domain truth stays in `workstation/`. Never move the Control Plane into the
plugin.


## Executive decision

Hermes Work will **adapt to the current Hermes upstream while using that migration to
remove accidental coupling and minimize first-party seams without sacrificing proven
Workstation capability or quality**.

This is neither a big-bang standalone rewrite, nor a blind fork sync, nor a "zero source
changes" purity program.

The direction is:

```text
adapt upstream
-> preserve Workstation semantics and product quality
-> classify every overlap
-> remove accidental seams where generic contracts are sufficient
-> introduce small generic abstractions where upstream lacks the right extension point
-> deliberately preserve the few first-party seams that require privileged lifecycle/UI
-> keep Hermes as the first-party laboratory / reference reasoner
-> progressively make Work Runtime independently executable
```

Canonical seam policy:
[FIRST_PARTY_SEAM_POLICY.md](FIRST_PARTY_SEAM_POLICY.md).

## The dependency direction, with one critical nuance

For reasoning/runtime supervision, the target relation remains unidirectional:

```text
Hermes Agent / upstream generic core
        |
        | generic lifecycle + middleware + provider contracts
        v
Workstation supervisory adapter
        |
        v
Hermes Work Runtime / Control Plane
```

The LLM/Reasoner must not need Workstation-specific prompt compliance. Correctness must not
depend on the model choosing `work_execute`, remembering a Workstation workflow, or being
aware that supervision exists.

However, this does **not** imply that the complete first-party Hermes Work distribution
must be unaware of Workstation.

The downstream Desktop may deliberately contain narrow first-party integrations when
generic extension surfaces cannot preserve equivalent capability, lifecycle, authority,
native UI integration or correctness.

```text
Reasoner:             should not need Workstation knowledge
Generic agent core:   should avoid Workstation-specific knowledge where generic seams suffice
First-party Desktop:  may knowingly integrate Workstation at narrow privileged boundaries
```

The objective is **minimum necessary first-party seams**, not zero seams.

## Supervisor, not hidden prompt convention

The desired runtime semantics remain:

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

`work_execute` remains useful as an explicit Capability/Intent execution API and
deterministic fast path, but it is not the activation mechanism on which Workstation
participation depends.

## Why the current upstream makes extraction feasible

The current fork and newer upstream already expose generic Hermes plugin/lifecycle and
middleware surfaces:

- lifecycle hooks: `pre_tool_call`, `post_tool_call`, `pre_verify`,
  `pre_api_request`, `post_api_request`, session/task lifecycle hooks;
- behavior-changing middleware:
  - `tool_request` — rewrite effective tool arguments;
  - `tool_execution` — wrap actual tool execution;
  - `llm_request` — rewrite/observe provider requests;
  - `llm_execution` — wrap provider execution;
- plugin registration through `PluginContext.register_hook()` and
  `PluginContext.register_middleware()`;
- browser/provider/plugin boundaries;
- a substantially stronger Desktop Plugin SDK with contributed panes/workspaces and
  docking surfaces.

These are materially better targets than re-injecting Workstation logic throughout
`agent/conversation_loop.py`, `agent/tool_executor.py` and other refactored owners.

But extension capability is not assumed to be universal. When a generic surface cannot
preserve the required semantics, the choice is not to regress the Workstation merely to
keep upstream pristine.

## The Browser proves why zero-seam purity is wrong

Today the Workstation Browser is not just a renderer plugin.

The integrated path includes:
- successful internal Browser navigation;
- a `workstation.browser.open` desktop event;
- session-aware routing in the Desktop;
- automatic Workstation Browser reveal in the chat Right Rail;
- a persistent Electron Chromium `WebContentsView`;
- BrowserTask/page ownership;
- background execution;
- human take/release control;
- stale-run fencing;
- Hub <-> Chat viewport transfer;
- controller loopback;
- persistent profile and recovery.

Modern upstream can likely absorb some historical presentation seams through its Plugin SDK,
because plugins can now contribute/dock workspaces and panes. Those seams should be tested
for REMOVE or UPSTREAM_ABSTRACT.

But renderer pane extensibility is not equivalent to main-process ownership of a persistent
native `WebContentsView`. Until a generic upstream native-view/provider contract offers
equivalent lifecycle and safety, the native Browser bootstrap/IPC path is a legitimate
PRESERVE_FIRST_PARTY seam.

**No proven Browser capability, UX behavior or correctness invariant may be downgraded just
to reduce the diff against upstream.**

## Current seam map and intended disposition

The old path-level map is superseded by
`workstation/first_party_seams.json` **v2**. File-level dispositions are only the
conservative audit envelope; implementation decisions are made per semantic concern.

Key outcomes from the deep audit:

- `run_agent.py`: **UPSTREAM_ABSTRACT**, then cease using it as a Workstation integration
  owner;
- `conversation_loop.prepare_turn_work`: **UPSTREAM_ABSTRACT** unless the new turn
  lifecycle is proven early enough; `project_for_provider`: **REMOVE** through
  `llm_request` middleware;
- `tool_executor.prepare_mutation`: **UPSTREAM_ABSTRACT** at the exact pre-I/O causal
  boundary; `record_mutation` and `capture_raw_result`: **REMOVE** through raw
  `post_tool_call`; internal durable persistence: **UPSTREAM_ABSTRACT**;
- `turn_finalizer`: **UPSTREAM_ABSTRACT** as completion admission, not observer;
- `kanban_db`: **UPSTREAM_ABSTRACT** into a generic two-phase completion-admission
  provider;
- Browser routing: converge on `BrowserControlBroker`; keep BrowserTask/native-runtime
  semantics Workstation-owned; create a generic broker capability registry for extra
  capabilities;
- `model_tools.py` forced Browser schemas: **REMOVE** after controller-driven capability
  exposure;
- `toolsets.py` hard-coded `work_execute`: **REMOVE** through plugin tool registration;
- `web_server.py` Workstation routes: **REMOVE** into plugin dashboard API, with temporary
  aliases only if compatibility requires them;
- `cli.py` trusted MessageEnvelope: **UPSTREAM_ABSTRACT** into generic `TurnIngress`;
- `agent/turn_constraints.py`: **UPSTREAM_ABSTRACT** into generic `TurnRoutePolicy`;
- Electron `main.ts` native runtime bootstrap and `preload.ts` privileged typed IPC:
  **PRESERVE_FIRST_PARTY**, but concentrate them into the narrowest bootstrap/bridge;
- Browser Right Rail presentation: **UPSTREAM_ABSTRACT/REMOVE** through generic pane/
  workspace contributions once parity is proven.

## Two classification layers

Every upstream overlap is still classified as one of:

1. **ADOPT_UPSTREAM**
2. **KEEP_WORKSTATION**
3. **SEMANTIC_PORT**
4. **EXTRACT_BOUNDARY**

When a source-level first-party seam remains after that analysis, it receives one seam
disposition:

1. **REMOVE** — generic current surface is sufficient.
2. **UPSTREAM_ABSTRACT** — capability is valid; add/use the smallest generic extension
   boundary and place Workstation behind it.
3. **PRESERVE_FIRST_PARTY** — privileged first-party lifecycle is genuinely required.

Canonical merge rule:

```text
UPSTREAM STRUCTURE
+ WORKSTATION SEMANTICS
+ MINIMUM NECESSARY FIRST-PARTY SEAMS
+ NO CAPABILITY REGRESSION FOR PURITY
```

## First-party seam budget

A preserved or newly introduced seam in upstream-owned code must prove:

1. no existing generic extension surface provides equivalent semantics;
2. the feature requires privilege/lifecycle/ordering/native UI access/correctness that a
   higher-level extension cannot provide;
3. it creates material product capability;
4. it is concentrated behind the smallest practical boundary;
5. behavioral contract/E2E coverage proves the capability;
6. it is documented in `UPSTREAM_DELTA.md` and `first_party_seams.json`;
7. every upstream cycle re-evaluates whether a new upstream abstraction makes it removable.

One deliberate seam is preferable to many scattered `if workstation` branches.

## Migration safety rule: shadow before change of authority

No existing seam is removed merely because a cleaner API exists.

```text
existing direct path
        |
        +--> remains authoritative temporarily
        |
        +--> replacement path runs in shadow/observation mode
                         |
                         v
             compare lineage / decisions / evidence / UX
                         |
                 prove behavioral parity
                         |
                    switch authority
                         |
       remove old seam OR retain it deliberately if parity is impossible
```

Required proof includes, where relevant:

- same operational event observed at the right ordering point;
- task/session/run/operation lineage preserved;
- pre-mutation veto/pause ability preserved;
- exactly-once/no-double-dispatch preserved;
- effect classification and authority preserved;
- BrowserTask ownership/human fencing preserved;
- uncertain mutation reconciles before retry;
- ACK remains distinct from VERIFIED;
- Experience Compiler receives admissible observations;
- deterministic reuse still works;
- normal Hermes tool use remains supervised without explicit `work_execute`;
- UI placement/visibility/background continuity remains equivalent;
- upstream regression tests plus Workstation qualification gates stay green.

## Pre-migration hard gate added by H-078B

Before P1 begins:

1. reconcile the H-078 branch with the then-current downstream `main` (including
   H-077/H-077.1);
2. refresh upstream, choose one exact SHA and pin it for the full cycle;
3. run/refresh the semantic seam inventory;
4. make `run_agent.py` and every mixed-concern path explicit in the registry;
5. create the Hermes adapter skeleton and the missing generic contracts before deleting any
   old seam;
6. prove shadow parity concern-by-concern;
7. for Browser/tool mutations, shadow may predict but must not execute a second effect.

Only after these conditions are true may the integration branch begin replacing owners.


## Implementation plan

### P0 — Decision, seam policy and measurable inventory — ACTIVE

- record D-026 plus D-027 and the minimum-seam policy;
- maintain `first_party_seams.json`;
- make the seam audit distinguish unclassified seams from deliberate seams;
- freeze an upstream SHA at integration start;
- generate the initial inventory before conflict resolution.

Exit: no coding agent can treat either "reinsert every old patch" or "remove every seam"
as the default strategy.

### P1 — Controlled upstream baseline migration

- create immutable pre-migration ref;
- create `integration/upstream-YYYY-MM-DD`;
- integrate only the pinned upstream SHA;
- classify overlaps as ADOPT_UPSTREAM / KEEP_WORKSTATION / SEMANTIC_PORT /
  EXTRACT_BOUNDARY;
- classify remaining first-party seams as REMOVE / UPSTREAM_ABSTRACT /
  PRESERVE_FIRST_PARTY;
- adopt upstream decompositions instead of resurrecting old monoliths.

### P2 — Hermes supervisory adapter in shadow mode

Build the first-party Hermes adapter over generic lifecycle/middleware where those
surfaces are semantically sufficient.

Observation/control vocabulary:

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

The adapter translates Hermes payloads into Workstation operational observations. It does
not become a second Control Plane or state store.

### P3 — Minimize tool-execution seams

Attempt to move semantics embedded in `agent/tool_executor.py` to generic
`tool_request/tool_execution` middleware plus `pre/post_tool_call`.

Exit: no **unnecessary** Workstation dependency remains in the tool executor. Any residual
first-party seam must be explicitly classified and justified; functional parity is more
important than a zero-import metric.

### P4 — Minimize turn/finalizer seams

Move turn/finalizer behavior to generic lifecycle/reasoning contracts where possible.
When an exact ordering/correctness capability is missing, prefer a small generic upstream
abstraction over a Workstation-specific conditional.

Exit: conversation/finalization coupling is reduced to the minimum justified surface, with
shadow-parity evidence for every removed seam.

### P5 — Browser boundary without capability loss

Adopt the upstream Browser architecture and push Workstation Browser behavior behind the
strongest generic provider/runtime boundary available.

Use the upstream Desktop Plugin SDK for presentation only when it can reproduce the
current Right Rail/Hub behavior without regression.

Preserve narrow Electron main/preload seams where native `WebContentsView`, BrowserTask
lifecycle, persistent background execution or human-control semantics require privilege
the SDK does not expose.

Exit: no scattered Browser Workstation branches; native first-party seams, if still
necessary, are concentrated, documented and E2E-tested.

### P6 — Session / Kanban / API / Desktop edge minimization

Reuse upstream decomposed owners. Convert edges to narrow adapters where feasible, but do
not remove first-party integrations that are still required for correct canonical
ownership or UX semantics.

### P7 — Work Gateway and standalone runtime boundary

Expose the same Work Runtime through Hermes first-party adapter, MCP, ACP and native
API/SDK. Hermes remains the reference/default reasoner, not the owner of Workstation truth.

### P8 — Hermes-less qualification

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

This proves Runtime Independence. It does **not** require the first-party Hermes Work
distribution to stop using deliberate native integration seams.

## What must not happen

- no blind GitHub "Sync fork" into main;
- no restore of obsolete upstream monoliths to keep patch locations alive;
- no "ours everywhere" / "theirs everywhere";
- no second task DB, BrowserTask store, journal, capability registry or Control Plane;
- no model-prompt convention as the only Workstation activation path;
- no seam removal before parity evidence;
- no **new unclassified** Workstation seam in upstream-owned code;
- no rule that all source-level first-party integrations must eventually disappear;
- no capability/UX/correctness regression merely to achieve plugin purity;
- no MCP-as-domain-model rewrite;
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

FIRST-PARTY HERMES WORK DISTRIBUTION
may retain narrow native seams where required
for product capability and lifecycle.
```

The strongest desired property is now:

> **The Reasoner does not need to remember Workstation. Generic Hermes core should use
> generic contracts wherever possible. The first-party distribution may keep a small,
> deliberate seam budget where deeper integration is the only way to preserve the product
> we are actually building.**

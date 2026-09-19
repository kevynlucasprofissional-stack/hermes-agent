# H-078 — Upstream Migration as Decoupling / Minimum Necessary First-Party Seams

Date established: 2026-09-19  
Status: **ACTIVE STRATEGIC MIGRATION PROGRAM**  
Downstream baseline when established: `main@378b5a2df35ac05fe37a606298502d7bb974786d`  
Upstream candidate observed during analysis: `NousResearch/hermes-agent@1f4fbd5145d641c3a815dc97332103679e6139d9`

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

The initial machine-readable registry is `workstation/first_party_seams.json`.

High-value examples:

- `agent/conversation_loop.py` -> **REMOVE candidate** through generic lifecycle/LLM
  supervision after shadow parity.
- `agent/tool_executor.py` -> **REMOVE candidate** through
  `tool_request/tool_execution` middleware and tool lifecycle hooks.
- `agent/turn_finalizer.py` -> **UPSTREAM_ABSTRACT candidate** if current verification /
  finalization hooks are not strong enough.
- `tools/browser_tool.py` -> **UPSTREAM_ABSTRACT candidate**: generic Browser provider /
  native-browser boundary, Workstation Browser behind it.
- `apps/desktop/electron/main.ts` Workstation Browser runtime bootstrap ->
  **PRESERVE_FIRST_PARTY candidate** while no equivalent native-view provider exists.
- `apps/desktop/electron/preload.ts` Workstation Browser privileged IPC ->
  **PRESERVE_FIRST_PARTY candidate** under the same condition.
- Workstation-specific Right Rail routing -> **UPSTREAM_ABSTRACT candidate** because the
  modern Desktop Plugin SDK may now provide enough UI placement primitives; preserve the
  current path until parity is demonstrated.

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

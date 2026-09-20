# H-078A — Minimum Necessary First-Party Seams

## H-079 operating refinement — classification is not closure

The seam audit answers “is every direct seam understood/classified?” It does **not** answer
“have all seams marked REMOVE actually been removed?”

Every upstream-first baseline cycle must therefore:
- refresh observed direct imports/references;
- verify the real authority path;
- mark REMOVE debt open until the legacy authoritative path is gone;
- re-evaluate UPSTREAM_ABSTRACT/PRESERVE_FIRST_PARTY against the newly pinned upstream;
- require exact-head parity evidence before changing status.

This prevents a green seam inventory from masking an incomplete authority switch such as
the current Browser path.


## H-078B policy refinement — semantic granularity and causal equivalence

A file-level seam disposition is only an audit envelope. The implementation unit is the
**semantic concern**.

The machine-readable v2 registry therefore records, for each concern:

`symbol_or_concern`, `semantic_owner`, `current_behavior`, `required_ordering`,
`disposition`, `replacement`, `parity_tests`, and `sunset_condition`.

"Equivalent" means causal equivalence, not merely similar output. Examples:

- uncertain mutation checkpoint must occur after final args + authorization/guards and
  before external I/O;
- raw-result observation must occur before spill/truncate/provider projection;
- completion admission must be able to reject before canonical DONE;
- route policy must be established before every provider/tool/auxiliary route;
- trusted ingress authority must not be reconstructed from user prose.

Browser shadow migration has an additional hard rule: a mutation can have only one
authoritative executor. Shadow code may classify/resolve/predict, but may not execute the
same external mutation a second time.


Date established: 2026-09-19  
Status: **ACTIVE POLICY**  
Parent program: [UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md](UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md)

## Decision

Hermes Work does **not** pursue zero source-level integration with the Hermes downstream
distribution.

The target is:

> **minimum necessary first-party seams: minimize upstream-owned modifications as far as
> possible without sacrificing Workstation capability, lifecycle control, correctness,
> native UI/UX integration, authority, verification or recovery quality.**

A seam is not automatically debt. Two very different things must be distinguished:

- **accidental coupling** — Workstation logic lives in a Hermes owner only because that was
  the easiest place to inject it;
- **deliberate first-party integration** — the downstream distribution needs privilege,
  lifecycle or product-surface access that no generic extension contract can currently
  provide with equivalent behavior.

The first should disappear. The second is allowed, documented, tested and periodically
re-evaluated.

## Product boundary

The stronger version of "Hermes should not need to know Workstation exists" applies to the
**Reasoner and generic agent core**, not to every layer of the downstream product.

Target:

```text
LLM / Reasoner
    does not need Workstation-specific prompt compliance
                       |
                       v
              Hermes Agent Core
          generic hooks / middleware
             / provider contracts
                       |
              +--------+---------+
              |                  |
              v                  v
     Workstation Supervisor   normal Hermes
              |
              v
        Work Runtime

Hermes Work first-party Desktop distribution
  may deliberately include:
  - Workstation Browser native runtime
  - narrow Electron bootstrap seams
  - preload/IPC bridge
  - Workstation control UI
  - other privileged product integrations that cannot be expressed generically
```

Therefore:

- `work_execute` remains a useful explicit fast path/API, but is not required for
  Workstation supervision;
- generic Hermes core should avoid Workstation-specific knowledge whenever equivalent
  generic surfaces exist;
- the downstream Desktop may remain intentionally aware of Workstation where that awareness
  is what creates the integrated product.

## Seam disposition

Every source-level Workstation seam in an upstream-owned area receives one final
disposition:

### REMOVE

Use when an existing generic surface can preserve behavior without the direct seam.

Typical candidates:
- agent-loop observation that lifecycle hooks already expose;
- tool execution wrapping expressible through `tool_request` /
  `tool_execution` middleware;
- LLM observation/wrapping expressible through `llm_request` /
  `llm_execution`;
- renderer UI that the upstream Plugin SDK can register with full behavioral parity.

### UPSTREAM_ABSTRACT

Use when the capability is legitimate but Hermes lacks a sufficiently generic extension
point.

Instead of adding repeated `if workstation` branches, add the smallest generic boundary,
then put the Workstation implementation behind it.

Example:

```text
Hermes Desktop
    |
    v
NativeViewProvider
    |
    v
WorkstationBrowserProvider
```

The generic abstraction should be useful without knowing Workstation identity and should
be shaped so it can plausibly be proposed upstream.

### PRESERVE_FIRST_PARTY

Use when the first-party distribution genuinely needs privilege/lifecycle access that an
extension cannot provide with equivalent quality.

Examples may include:
- Electron main-process ownership of a persistent `WebContentsView`;
- preload/IPC contracts required to control that native view;
- BrowserTask lifecycle and human-control fencing tied to that native resource;
- other process-level integration that must exist before/under renderer plugin code.

A preserved seam is **not exempt from discipline**. It must stay narrow, named, covered by
contract/E2E tests, listed in `UPSTREAM_DELTA.md`, and re-evaluated every upstream cycle.

## The Browser is the reference case

The current Workstation Browser demonstrates why zero-seam purity is not the goal.

A successful internal navigation can emit:

```text
workstation.browser.open
```

The Desktop routes that event to the visible session and opens the Workstation Browser
preview in the chat Right Rail. Separately, the native Browser runtime owns a persistent
Electron Chromium `WebContentsView`, BrowserTask/page identity, background execution,
human takeover, task fencing, Hub <-> Chat viewport transfer, controller loopback,
persistent profile and recovery.

Modern upstream can already provide more of the presentation layer generically:
its Plugin SDK has contributed panes/workspaces and can dock plugin surfaces beside the
main workspace. That means some historical UI seams may now be REMOVE or
UPSTREAM_ABSTRACT candidates.

But a renderer plugin surface is not equivalent to owning a persistent native
`WebContentsView` and its main-process lifecycle. Until upstream exposes an equivalent
generic native-view/provider contract, the process-level Browser integration is a valid
PRESERVE_FIRST_PARTY candidate.

**No Browser capability may be downgraded merely to make the diff against upstream
smaller.**

## First-party seam budget

Every preserved or newly introduced upstream-owned modification must satisfy all of:

1. no existing generic extension surface provides equivalent semantics;
2. the feature requires privilege, lifecycle, ordering, authority, native UI access or
   correctness unavailable at a higher layer;
3. the seam produces material product capability;
4. the seam is concentrated behind the smallest practical boundary;
5. behavioral contract/E2E coverage proves the capability;
6. the seam is listed in `UPSTREAM_DELTA.md` and the machine-readable seam policy;
7. every upstream synchronization re-evaluates whether a new upstream abstraction now
   makes the seam removable.

Additional rules:

- do not optimize for the raw number of changed files at the expense of architecture;
- do optimize for **blast radius**: one deliberate integration boundary is preferable to
  many scattered Workstation conditionals;
- new first-party seams require an explicit reason why REMOVE and UPSTREAM_ABSTRACT are
  insufficient;
- "plugin purity" is never a valid reason to regress a proven Workstation capability.

## Migration decision procedure

For each existing/touched seam:

```text
Can a current generic hook/middleware/provider/plugin SDK surface preserve
ALL required behavior and ordering?
        |
       yes ----------------------> REMOVE
        |
       no
        v
Would a small generic upstream-compatible abstraction preserve it?
        |
       yes ----------------------> UPSTREAM_ABSTRACT
        |
       no
        v
Is the capability material and dependent on privileged first-party lifecycle?
        |
       yes ----------------------> PRESERVE_FIRST_PARTY
        |
       no -----------------------> REMOVE / redesign
```

"All required behavior" includes, where relevant:

- exact event ordering;
- ability to veto/pause before mutation;
- exactly-once/no-double-dispatch behavior;
- task/session/run/operation lineage;
- authority/effect containment;
- BrowserTask ownership and stale-run fencing;
- human takeover/release;
- uncertainty and reconciliation;
- ACK != VERIFIED;
- evidence and Experience Compiler observations;
- UI placement/visibility semantics;
- background continuity and recovery.

## Relationship to H-078

H-078 still means **synchronize while extracting accidental seams**.

It no longer means "drive direct seams to zero".

The success condition becomes:

```text
UPSTREAM STRUCTURE
+ WORKSTATION SEMANTICS
+ MINIMUM NECESSARY FIRST-PARTY SEAMS
+ NO CAPABILITY REGRESSION FOR PURITY
```

A successful upstream migration may retain a small, deliberate first-party delta if that
is required for the integrated product. The objective is a stable, reviewable seam budget,
not architectural asceticism.

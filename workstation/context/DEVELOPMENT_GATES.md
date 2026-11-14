<!-- Extracted verbatim from AGENTS.md; the hub retains mandatory reading links. -->

## Downstream Workstation context

This downstream fork contains a first-class Hermes Workstation product layer. If a task touches `workstation/`, the Desktop Workstation Browser, `browser_*` Workstation routing, or another Workstation-owned integration point, **read `workstation/context/README.md` and follow its required reading order before editing code**. The root rules in this file remain authoritative; the Workstation context adds current downstream state, settled decisions, constraints, tests, known issues, and the maintained upstream delta. Always verify those documents against current `main` implementation and tests rather than relying on old plans or conversation state.

### Stage A / H-079 — optional upstream synchronization

The H-079 Stage A baseline workflow is **opt-in**. It is useful for planned upstream
merges, seam reconciliation and baseline qualification, but it is **not a prerequisite**
for a downstream implementation, bug fix, refactor, behavioral adjustment or test.

Before ordinary implementation:
- Read the relevant Workstation context and inspect the existing code and changed files.
- Consult the latest *recorded* sync status in [workstation/UPSTREAM.md](../UPSTREAM.md)
  and [workstation/UPSTREAM_DELTA.md](../UPSTREAM_DELTA.md) when upstream context
  could matter. These reports are dated evidence, not live alignment guarantees.
- Continue the target work whether Stage A is incomplete, upstream is behind,
  or historical baseline CI is red. Record uncertainty; do not invent qualification.
- Preserve work in progress, permissions, authority/security boundaries, and
  regression/acceptance verification appropriate to the actual code change.

No upstream fetch, exact SHA pin, true-history merge, upstream drift report, or special
maintainer waiver is required **just to implement**. If an upstream change directly
conflicts with the target implementation, resolve that concrete dependency rather
than imposing a global sync gate.

When the maintainer **elects** to synchronize upstream, use the archived H-079
[procedure](UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md) for its pin/merge/seam
discipline and keep sync work separately reviewable. Never describe an unqualified
candidate as an upstream-qualified baseline. Release/promotion CI requirements
remain governed by the deliverable's own risk and explicit release contract;
they are not universal pre-coding gates.

### Workstation upstream-sync / first-party seam rule

When touching an upstream integration point, conflict, rebase, or migration for Hermes
Workstation, read both:

- `workstation/context/UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md`
- `workstation/context/FIRST_PARTY_SEAM_POLICY.md`

The goal is **minimum necessary first-party seams**, not zero seams and not preservation of
every historical patch.

Core direction:

- the LLM/Reasoner MUST NOT need to remember to use Workstation;
- generic Hermes core SHOULD use generic lifecycle/middleware/provider/plugin contracts
  when those contracts preserve full semantics;
- the first-party Hermes Work distribution MAY deliberately keep narrow source-level
  integration when extension surfaces cannot preserve equivalent capability, lifecycle,
  authority, native UI/UX or correctness;
- never regress a proven Workstation capability merely to reduce the downstream diff.

For every upstream overlap, classify:
`ADOPT_UPSTREAM | KEEP_WORKSTATION | SEMANTIC_PORT | EXTRACT_BOUNDARY`.

For every remaining source seam, classify:
`REMOVE | UPSTREAM_ABSTRACT | PRESERVE_FIRST_PARTY`.

Use this order:
1. REMOVE when a current generic surface preserves all required behavior.
2. UPSTREAM_ABSTRACT when a small generic upstream-compatible boundary can preserve it.
3. PRESERVE_FIRST_PARTY when privileged first-party lifecycle is materially required.

A preserved seam must satisfy the seam budget: no equivalent generic surface, material
product capability, minimum blast radius, behavioral contract/E2E evidence,
`UPSTREAM_DELTA.md` + `workstation/first_party_seams.json` registration, and
re-evaluation on the next upstream cycle.

The Workstation Browser is the reference constraint. Upstream plugin/pane APIs may replace
presentation seams when parity is proven, but they are not presumed equivalent to native
Electron `WebContentsView` lifecycle, BrowserTask ownership, background continuity,
human-control fencing, native IPC or recovery.

Never remove an existing seam until the replacement path has run in shadow/parity and
proves the same relevant lineage, authority, ordering, uncertainty, verification,
BrowserTask/handoff, UX placement/background behavior and learning semantics.

Use `python workstation/scripts/audit_hermes_seams.py` when planning/reviewing the
migration. New **unclassified** Hermes-core -> Workstation seams are forbidden. New
deliberate first-party seams require explicit classification and justification.


# Upstream strategy

## H-078C active integration cycle

Pinned target for the active cycle:
`6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170`.

Local integration branch:
`integration/upstream-6a078969-h078b`.

The first actual merge produced 69 UU conflicts. Resolve them by owner/semantic cluster,
not alphabetically and not with blanket ours/theirs.

Mandatory final ancestry gates:

```bash
git merge-base --is-ancestor 6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170 <qualified-head>
git rev-list --count <qualified-head>..6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170
```

The second command must return `0` before H-078C can close.


## H-078B synchronization rule (2026-09-19)

For the next major sync:

- reconcile the H-078 documentation/policy branch with the then-current downstream main;
- fetch upstream and pin one exact SHA for the whole cycle;
- classify **semantic concerns**, not just conflicted files;
- preserve causal invariants while adopting upstream structure;
- never resurrect old monoliths merely to retain Workstation patch locations;
- never dual-execute a mutation during shadow/parity migration;
- do not switch authority until concern-level parity evidence exists.

Research snapshots are evidence, not moving integration targets.


Primary upstream: `NousResearch/hermes-agent`.

Downstream fork: `kevynlucasprofissional-stack/hermes-agent`.

Initial common base:

`057dcdf236f8a6a26721c10fcc6ccb72726e272a`

Current downstream baseline when H-078 was established:

`378b5a2df35ac05fe37a606298502d7bb974786d`

Upstream candidate observed during the 2026-09-19 audit:

`1f4fbd5145d641c3a815dc97332103679e6139d9`

**Every integration cycle MUST pin one exact upstream SHA before conflict resolution.**

## Canonical strategy: synchronize while minimizing seams

The upstream update is not a plain fork sync. It is the first Runtime Independence
migration, but Runtime Independence does not require zero first-party integration.

```text
UPSTREAM STRUCTURE
+ WORKSTATION SEMANTICS
+ MINIMUM NECESSARY FIRST-PARTY SEAMS
+ NO CAPABILITY REGRESSION FOR PURITY
```

Hermes remains the first-party laboratory/reference reasoner.

The Reasoner and generic agent core should not require Workstation-specific prompt
compliance or imports when equivalent generic lifecycle/middleware/provider/plugin
surfaces exist.

The first-party Hermes Work distribution may retain narrow integration seams when
privileged lifecycle/native UI/correctness cannot be reproduced at the extension layer.

Canonical:
- [context/UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md](context/UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md)
- [context/FIRST_PARTY_SEAM_POLICY.md](context/FIRST_PARTY_SEAM_POLICY.md)
- `first_party_seams.json`

## Recommended remotes

```powershell
git remote add upstream https://github.com/NousResearch/hermes-agent.git
git fetch origin --prune
git fetch upstream --prune
```

## Integration-cycle procedure

1. Read H-078, D-026, D-027 and the seam policy.
2. Fetch both remotes.
3. Record downstream `main` SHA and exact upstream candidate SHA.
4. Freeze that upstream SHA for the cycle.
5. Create immutable pre-migration backup/ref.
6. Create `integration/upstream-YYYY-MM-DD`.
7. Generate the seam inventory and apply `first_party_seams.json`.
8. Compare upstream/downstream from merge base.
9. Classify every overlap:
   - `ADOPT_UPSTREAM`
   - `KEEP_WORKSTATION`
   - `SEMANTIC_PORT`
   - `EXTRACT_BOUNDARY`
10. Classify every remaining source seam:
   - `REMOVE`
   - `UPSTREAM_ABSTRACT`
   - `PRESERVE_FIRST_PARTY`
11. Prefer generic existing surfaces when they have full semantic parity.
12. Prefer a small generic upstream-compatible abstraction over scattered
    Workstation-specific branches when a capability gap exists.
13. Preserve a narrow first-party seam when higher-level surfaces cannot reproduce the
    required capability/lifecycle/correctness.
14. Run replacement paths in shadow before changing authority.
15. Run upstream tests + Workstation contract/E2E gates on the exact candidate head.
16. Update seam registry, `UPSTREAM_DELTA.md`, patch manifest, current state and journal.
17. Merge to main only after semantic qualification.

## Generic integration surfaces preferred

The modern Hermes architecture exposes useful generic boundaries:

- lifecycle: `pre_tool_call`, `post_tool_call`, `pre_verify`,
  `pre_api_request`, `post_api_request`, session/task lifecycle;
- middleware: `tool_request`, `tool_execution`, `llm_request`, `llm_execution`;
- browser/provider interfaces;
- Desktop Plugin SDK with contributed panes/workspaces and docking.

A Workstation behavior that can move to these surfaces **with full parity** should not be
reinserted as a Workstation-specific core import.

But "a plugin can render something" is not proof that the plugin layer can replace native
main-process lifecycle. The Browser's persistent `WebContentsView`, BrowserTask
ownership, background continuity, human control and IPC are the reference example.

## Core rules

- upstream remains authoritative for generic Hermes behavior/module structure;
- Workstation runtime truth remains Workstation-owned;
- do not resurrect old upstream monoliths;
- do not resolve conflicts with blanket ours/theirs;
- accidental direct coupling is debt;
- deliberate first-party integration is permitted when the seam budget is satisfied;
- no new **unclassified** Workstation seam in upstream-owned code;
- a preserved seam must have rationale, behavioral tests, `UPSTREAM_DELTA` entry and
  periodic re-evaluation;
- generic improvements should be structured for possible upstream contribution;
- stable updates promote only after Workstation E2E validation;
- no second task DB, BrowserTask store, journal, capability registry or Control Plane.

## Seam change invariant

Before removing a seam, prove the replacement preserves all relevant behavior.

Before preserving/adding a seam, prove the higher-level extension path cannot preserve all
relevant behavior.

Relevant dimensions include:
- canonical task/run/operation lineage;
- authority/effect containment;
- exact ordering and pre-mutation control;
- uncertain mutation reconciliation;
- ACK != VERIFIED;
- BrowserTask ownership/human fencing;
- Experience Compiler observations;
- deterministic capability reuse;
- UI placement/visibility and background continuity;
- normal Hermes operation without model compliance.

Migration success is not measured by zero seams. It is measured by **upstream compatibility
plus a small, deliberate, capability-preserving first-party seam budget**.

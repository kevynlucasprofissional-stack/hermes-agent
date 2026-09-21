# Upstream strategy

## H-079.2 active baseline refresh requirement

Current `main@964c13361e...` is not upstream-fresh. The latest upstream pin actually ancestral to main is `c1488ac947...`; PR #40's `8d153b26...` merge lives on an integration branch only. Latest observed upstream during this audit is `641f7c8104...`, with downstream 547 ahead / 622 behind and merge-base at `c1488ac947...`.

Therefore the next code-changing cycle MUST execute H-079 Stage A again from current main. Fetch upstream at execution time, freeze one exact new pin, true-merge it into a dedicated integration branch, reconcile seams, and qualify before applying downstream target fixes.

Do not merge `integration/upstream-20260920-8d153b26-h0791` wholesale into main after this amount of upstream movement. Reuse its installer/H-077 work semantically on the new pinned structure.


## Primary sync model — H-079 upstream-first change gate

Canonical:
[context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md](context/UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md).

Upstream synchronization is now the **first phase of every downstream code-change cycle**.

Operational model:
```text
fetch latest upstream
-> pin one exact SHA
-> integrate/qualify baseline
-> reconcile seam registry
-> implement target downstream change
-> exact-head qualification
-> final upstream drift classification
```

Do not continuously move the pin during implementation. Do not postpone upstream
synchronization until after a feature is already built.

H-079 qualified baseline snapshot (2026-09-20; qualification applies only to the recorded SHA):
- adopted pin: `c1488ac947c9bc33fd65ec464548dc9d8edd6122`;
- superseded pin: `b7d7d2929a10e0658a98a7a03f4531093e1480ed` (H-079 candidate pin, adopted by `a13929fb3568ce4c0423c5cf8cbe4f479ea22849`, replaced when the merge below landed);
- downstream `main`: `9e8127e247accf6858f295e554cab7d4bb7adefe`;
- merge commit: `24a8501934374e47a23b51f21183fb9c4edd3a76`;
- ancestry status: verified (`git merge-base 9e8127e247 2c0b2a980c` -> `c1488ac947...`);
- drift at `9e8127e247...` versus upstream snapshot `2c0b2a980c2d0e92f0452500089f5af91208f94c`: 544 downstream-only and 447 upstream-only commits;
- H-079 Stage A & B are merged to `main`.

The drift figures describe the two recorded SHAs, not the moving branch tips. Reproduce them
with `git rev-list --left-right --count 9e8127e247...2c0b2a980c`. The adopted pin is unchanged;
later heads require their own qualification evidence.

**Exact-head CI is green** at the merged head `9e8127e247...` (PR #41, carrying the fix
`1716062f32...` that restores the browser routing ladder; Workstation CI run `35536129052`); the
red run was at `d0ade123c0...`, which that fix supersedes. Aggregate browser convergence is
**UNMEASURED**: no named acceptance check is cited for the former `FULL` claim. The narrower
Browser Authority Convergence evidence in `context/CURRENT_STATE.md` is not aggregate qualification.


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

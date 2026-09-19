# Upstream strategy

Primary upstream: `NousResearch/hermes-agent`.

Downstream fork: `kevynlucasprofissional-stack/hermes-agent`.

Initial common base:

`057dcdf236f8a6a26721c10fcc6ccb72726e272a`

Current downstream baseline when H-078 was established:

`378b5a2df35ac05fe37a606298502d7bb974786d`

Upstream candidate observed during the 2026-09-19 audit:

`1f4fbd5145d641c3a815dc97332103679e6139d9`

**Do not treat that candidate as permanently moving with `upstream/main`. Each
integration cycle MUST pin one exact upstream SHA before conflict resolution begins.**

## Canonical strategy: synchronize while extracting seams

The upstream update is not a plain fork sync. It is the first Runtime Independence
migration.

```text
UPSTREAM STRUCTURE
+ WORKSTATION SEMANTICS
+ FEWER DIRECT SEAMS
```

Hermes remains the first-party laboratory/reference reasoner. Workstation progressively
moves behind a Workstation-owned adapter/runtime boundary.

The target dependency is unidirectional:

```text
Hermes generic lifecycle/middleware/provider contracts
                    |
                    v
         Workstation Hermes adapter
                    |
                    v
             Work Runtime
```

Generic Hermes core should not know Workstation identity. Workstation may observe and
intervene through generic contracts.

This means removing seams must never rely on the model to "remember" to use Workstation.
Normal Hermes tool/model behavior must remain observable and supervisable even when
`work_execute` is never called.

Canonical architecture:
[context/UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md](context/UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md).

## Recommended remotes

```powershell
git remote add upstream https://github.com/NousResearch/hermes-agent.git
git fetch origin --prune
git fetch upstream --prune
```

## Integration-cycle procedure

1. Read the canonical Workstation context and H-078.
2. Fetch both remotes.
3. Record downstream `main` SHA and exact upstream candidate SHA.
4. Freeze the upstream SHA for the whole cycle.
5. Create immutable pre-migration backup/ref.
6. Create `integration/upstream-YYYY-MM-DD`.
7. Generate the direct seam inventory:
   `python workstation/scripts/audit_hermes_seams.py --json`.
8. Compare upstream and downstream from the merge base.
9. Classify every overlap:
   - `ADOPT_UPSTREAM`
   - `KEEP_WORKSTATION`
   - `SEMANTIC_PORT`
   - `EXTRACT_BOUNDARY`
10. Prefer `EXTRACT_BOUNDARY` when generic lifecycle/middleware/provider surfaces can
    preserve Workstation semantics.
11. Run new supervisory paths in shadow before removing old direct seams.
12. Run upstream tests + Workstation contract/E2E gates on the exact candidate head.
13. Update `UPSTREAM_DELTA.md`, `PATCH_MANIFEST.md`, current state and journal.
14. Merge to main only after semantic qualification.

## Generic integration surfaces preferred over patches

The modern Hermes architecture already exposes useful generic boundaries:

- lifecycle hooks:
  `pre_tool_call`, `post_tool_call`, `pre_verify`,
  `pre_api_request`, `post_api_request`, session/task lifecycle;
- middleware:
  `tool_request`, `tool_execution`, `llm_request`, `llm_execution`;
- plugin/provider interfaces, including browser/provider abstractions.

A Workstation behavior that can move onto one of these surfaces should not be reinserted
as a Workstation-specific import into a refactored upstream owner.

## Core rules

- upstream Hermes remains authoritative for generic Hermes behavior and module structure;
- Workstation-owned runtime truth remains under `workstation/`;
- do not resurrect upstream god-files to keep an old patch location alive;
- do not use "ours everywhere" or "theirs everywhere" conflict resolution;
- a direct core modification is temporary debt unless no generic boundary can express the
  required semantics;
- every new direct Hermes -> Workstation dependency requires explicit rationale and a
  retirement path;
- generic improvements should be structured so they can be proposed upstream;
- stable updates are promoted only after Workstation integration/E2E validation;
- edge may follow upstream more aggressively for compatibility testing;
- no second task DB, BrowserTask store, journal, capability registry or Control Plane is
  created to ease the migration.

## Seam-retirement invariant

Before deleting a direct seam, prove the replacement path preserves:

- canonical task/run/operation lineage;
- authority/effect containment;
- uncertain-mutation reconciliation;
- ACK != VERIFIED;
- BrowserTask ownership/human fencing where relevant;
- Experience Compiler observations and promotion gates;
- deterministic capability reuse;
- normal Hermes operation without explicit Workstation model compliance.

The migration succeeds only when upstream compatibility improves **and** the number/scope
of inward Workstation seams monotonically decreases.

# H-078C — Actual Upstream Baseline Adoption / Conflict Resolution

Date established: 2026-09-19  
Status: **ACTIVE — LOCAL THREE-WAY MERGE IN PROGRESS / NOT YET QUALIFIED**  
Parent: H-078 / H-078B  
Downstream GitHub baseline: `main@1192c016cfc59c4fb8edca27c309eb1e983c6aae`  
Pinned upstream target: `6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170`  
Local integration branch reported by audit: `integration/upstream-6a078969-h078b`

## Why H-078C exists

H-078B successfully created generic lifecycle/admission contracts and a first-party
`workstation/integrations/hermes/` adapter, but it did **not** adopt the pinned upstream
history or modern source decomposition.

GitHub still reports the downstream main as diverged from the pinned upstream:

- downstream is 502 commits ahead;
- downstream is 13,313 commits behind the pinned SHA;
- merge-base is still `057dcdf236f8a6a26721c10fcc6ccb72726e272a`.

Compared with current `NousResearch/hermes-agent:main`, the fork is 13,332 commits behind.

Therefore H-078B must be read as **semantic decoupling preparation**, not completion of the
actual upstream baseline migration.

## Local audit evidence

The local conflict audit reports:

- current branch: `integration/upstream-6a078969-h078b`;
- `MERGE_HEAD = 6a078969a2e7e99c6eb9ad5ba8216c3fd9bef170`;
- 69 unresolved files;
- all 69 are `UU / both modified`;
- no conflict was modified during the audit;
- repository is safe to continue only **conditionally** because three pre-existing
  unstaged changes must be safeguarded:
  - `workstation/operational_kernel.py`;
  - `workstation/tests/test_experience_compiler.py`;
  - `workstation/tests/test_operational_capabilities.py`.

The local integration branch is not currently visible as a pushed GitHub branch. GitHub
therefore cannot validate the unresolved index/worktree; local Git remains authoritative
for the active conflict set.

## Critical new finding: H-078B decoupled interfaces but retained old structural owners

The actual GitHub trees make the remaining migration debt concrete.

| Owner | downstream main | pinned upstream |
| --- | ---: | ---: |
| `run_agent.py` | 9,314 lines | 1,593 lines |
| `agent/conversation_loop.py` | 8,634 | 1,746 |
| `agent/tool_executor.py` | 2,972 | 1,850 |
| `hermes_cli/kanban_db.py` | 12,433 | 4,415 |
| `gateway/browser_control_broker.py` | 1,088 | 526 |
| `tools/browser_tool.py` | 6,118 | 1,390 |
| `model_tools.py` | 1,670 | 988 |

This does **not** mean the downstream features are wrong. It means the first H-078B pass
introduced generic contracts into the old downstream structure instead of completing the
required structural transplant into modern upstream owners.

The conflict-resolution rule is therefore stronger:

> **adopt upstream structure first, then semantic-port the proven Workstation properties
> into the narrowest modern owner. Do not preserve the downstream monolith merely because
> H-078B made it dependency-clean.**

## Verified H-078B assets that must survive the transplant

GitHub main contains real generic contracts:

- `agent/turn_ingress.py`;
- `agent/turn_admission.py`;
- `agent/tool_batch_admission.py`;
- `agent/pre_dispatch.py`;
- `agent/post_tool.py`;
- `agent/execution_persistence.py`;
- `agent/turn_route_policy.py`;
- `agent/completion_admission.py`;
- `agent/task_completion_admission.py`;
- `workstation/integrations/hermes/adapter.py`.

The adapter registers Workstation implementations for turn admission, batch admission,
scoped execution, authorized pre-dispatch checkpoint, raw post-tool observation, completion
admission, task completion admission and persistence disposition.

These semantic contracts are preservation targets. Their **current file placement is not
automatically a preservation target**.

## Modern upstream owners confirmed at the pin

The pinned upstream contains:

- `agent/turn_tool_round.py`;
- `agent/turn_context.py`;
- `agent/agent_runtime_helpers.py`;
- decomposed `agent/tool_executor.py`;
- upstream tool hooks/middleware including pre/post tool and tool-execution middleware;
- `gateway/browser_control_broker.py`;
- `tools/browser_extension_router.py`;
- `hermes_cli/kanban_pr_acceptance_store.py` with
  `prepare_acceptance()` / `record_acceptance()`;
- modern Desktop contrib/plugin surfaces.

These are the preferred structural owners.

## Five critical conflict clusters

### C1 — Agent core loop / turn-round decomposition

Includes at minimum `run_agent.py`, `agent/conversation_loop.py`,
`agent/turn_finalizer.py`, `agent/agent_init.py`.

Default strategy: **ADOPT_UPSTREAM + SEMANTIC_PORT / EXTRACT_BOUNDARY**.

Do not keep the downstream monolith. Batch admission belongs at the upstream full-batch
boundary (normally `turn_tool_round.py`); turn admission belongs after trusted identity is
established but before route-sensitive work; completion admission must remain capable of
vetoing terminal completion.

### C2 — Tool dispatch causal ordering / execution persistence

Includes `agent/tool_executor.py`, `agent/tool_guardrails.py`, registry/file/MCP paths.

Default strategy: **ADOPT_UPSTREAM + SEMANTIC_PORT**.

Preserve this exact invariant:

```text
FINAL ARGS
-> authorization / guardrails passed
-> durable uncertain checkpoint
-> REAL I/O
-> raw terminal result
-> Workstation post-tool observation
-> spill / truncate / conversational persistence
```

The upstream pin already has strong pre/post-tool and execution-middleware structure. Add
only the smallest missing generic authorized-pre-effect boundary needed to preserve the
checkpoint.

### C3 — Browser broker / routing / schema

Includes `gateway/browser_control_broker.py`, `tools/browser_tool.py`,
`model_tools.py`, `toolsets.py`.

Default strategy: **ADOPT_UPSTREAM BROKER/ROUTER + SEMANTIC_PORT**.

The downstream broker has a useful generic dynamic capability registry that is absent from
the pinned broker. Port that capability generically rather than keeping the entire larger
downstream broker.

Target:

```text
generic browser tool
-> upstream browser_extension_router
-> upstream BrowserControlBroker (+ minimal generic capability extension)
-> WorkstationBrowserController
-> Workstation native Electron runtime
```

Retire direct Workstation routing/schema seams in `browser_tool.py` / `model_tools.py`
once broker/controller parity is proven.

### C4 — Kanban completion / two-phase admission

Includes `hermes_cli/kanban_db.py`, `tools/kanban_tools.py`.

Default strategy: **ADOPT_UPSTREAM KANBAN + EXTRACT/PORT TaskCompletionAdmission**.

The pinned upstream's PR acceptance pattern is canonical:

```text
prepare outside transaction
-> snapshot run/state/contract
-> begin canonical write transaction
-> revalidate snapshot
-> record acceptance receipt
-> terminal DONE update
```

Workstation completion admission must become another provider in this transaction shape;
do not preserve the 12k-line downstream Kanban owner.

### C5 — Desktop native runtime / bootstrap

Includes `apps/desktop/electron/main.ts` and related bootstrap/window files.

Default strategy: **SEMANTIC_PORT + PRESERVE_FIRST_PARTY only for native privilege**.

Adopt upstream Desktop lifecycle and plugin/contrib structure. Preserve the minimum native
seams required for persistent `WebContentsView`, BrowserTask/page ownership, background
continuity, human takeover/release, stale-run fencing, Hub/Chat transfer, typed IPC and
recovery.

## Safety gate for pre-existing local work

Before resolving any conflict, create an external backup patch/copies of the three
pre-existing unstaged files. Do not use `git add -A`, blanket checkout, reset, restore,
or merge abort.

Stage conflict resolutions path-by-path. The three pre-existing worktree changes must not
be silently absorbed into the merge commit or destroyed.

## Resolution order

1. repository safety / local-change backup;
2. generic lifecycle contracts and upstream agent decomposition;
3. Workstation Hermes adapter re-wiring;
4. tool causal execution boundary and persistence;
5. completion/Kanban transaction;
6. Browser broker/controller/routing;
7. Desktop native + plugin/pane integration;
8. API/tool registration and remaining edges;
9. tests moved to new owners;
10. generated/lock files last;
11. qualification ladder;
12. ancestry proof.

## Qualification gates

The migration is not complete until all are true:

- zero unresolved conflicts / conflict markers;
- no blanket ours/theirs resolution on critical clusters;
- strict seam audit green;
- H-077/H-077.1 truth/verification regressions green;
- H-078B generic causal tests green;
- Browser broker/native E2E green;
- Kanban acceptance/race tests green;
- runtime-independence test green;
- upstream affected tests green;
- `git merge-base --is-ancestor 6a078969... <integration-head>` succeeds;
- `git rev-list --count <integration-head>..6a078969...` is 0;
- after promotion, the pinned upstream SHA is an ancestor of `main`.

## Completion semantics

H-078B status is refined to:

```text
SEMANTIC DECOUPLING: IMPLEMENTED / VERIFIED ON OLD DOWNSTREAM STRUCTURE
ACTUAL UPSTREAM BASELINE ADOPTION: H-078C ACTIVE
```

The migration is complete only after H-078C closes.

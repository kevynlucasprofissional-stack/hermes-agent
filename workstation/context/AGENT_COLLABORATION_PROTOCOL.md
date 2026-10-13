# Single-branch multi-agent protocol — Hermes Work (2026-10-13)

## Purpose and status
One feature branch, **one physical checkout**, several agents safely working in parallel. This document is the **policy**; the **live local truth** is `/.hermes-collab/*.claim/owner.json` (ignored by Git), maintained by `python workstation/scripts/multi_agent_coordination.py`. The durable board is `workstation/context/workstation-hub-mvp/TEAM_BOARD.md`, updated by the integrator at checkpoints. Markdown boards do not provide atomic locking; the local claim tool does.

## Current shared cycle
- Repo: `kevynlucasprofissional-stack/hermes-agent`
- Shared branch: `feat/hermes-workstation-mvp-20261013` from verified `main` `b80d10a4d6d4536b65df52eb4e011ad8d5eef672`
- **ONLY checkout for this cycle:** `C:\Github\hermes-agent`
- No per-agent branches or worktrees for routine adjustments. No new PR for individual fixes; one aggregate PR for this cycle.
- One maintainer-appointed **integrator** owns `git add`, `git commit`, `git push`, `git pull`, `git merge`, `git rebase`, `git switch`, `git reset` and PR edits. All other agents are read/write **only in their claimed source files**. Read-only git commands are allowed. No agent may autonomously merge into main.
- H-079 upstream baseline/CI gate is still authoritative. Treat a recorded upstream pin/qualification as a **one-cycle gate**, not a reason to open a different branch every session. If unmet, record a bounded blocker; do not bypass policy.

## Admission and ownership (mandatory, even for 2 agents)
1. Agent reads root `AGENTS.md`, `workstation/AGENTS.md`, this protocol, `TEAM_BOARD.md` and `STATE.md`. Inspect `python workstation/scripts/multi_agent_coordination.py status`.
2. Identify agent, lane, exact file/directory ownership (repo-relative), task, and immediate next action. A single source file may have ONE writer.
3. Acquire atomic local claim (PowerShell/CMD):
   `python workstation/scripts/multi_agent_coordination.py claim --agent agent-creative --lane creative-agent --paths workstation/integrations/hermes apps/desktop/src/app/creative-workspace --task "Internal Creative capability and tests"`
   Script rejects overlapping directory/file claims. If occupied, do **not** edit or steal; take another unclaimed task or ask integrator to sequence.
4. Publish progress and heartbeat after meaningful change or before context end:
   `python workstation/scripts/multi_agent_coordination.py update --agent agent-creative --lane creative-agent --status IN_PROGRESS --next "Finish RED test then verify GREEN"`
   Use statuses `ACTIVE`, `IN_PROGRESS`, `READY_FOR_INTEGRATION`, `BLOCKED`, `REVIEWING`, `DONE`.
5. Integrator checks `status` before staging exact agreed files; coordinates a short **integration freeze** while it commits/pushes/tests. Agents must not write claimed files during the freeze (communicate through live claims/status). The integrator records HEAD, tests and integration result in `TEAM_BOARD.md`/`STATE.md` and notifies agents to continue.
6. Agent releases its claim **only after** its work has been integrated or intentionally parked with a documented handoff:
   `python workstation/scripts/multi_agent_coordination.py release --agent agent-creative --lane creative-agent`
7. No automatic lock expiry/stealing. If agent crashed, inspect `owner.json`, process state, uncommitted diff and handoff; the integrator/maintainer must explicitly resolve and log recovery before removing a stale claim. An empty/incomplete claim remains blocking.

## Suggested lanes for 4 agents
| Lane | Primary owner | Allowed source ownership | Dependencies / warning |
|---|---|---|---|
| `creative-agent` | Agent A | Creative agent tool registration, capability descriptor and its tests; `workstation/integrations/hermes/` as claimed | No Browser controller semantics reassignment |
| `hub-ui` | Agent B | Sidebar, Browser Hub UI, Creative React mounting and occlusion tests | Shared bridge contract must be agreed with A/C before edits |
| `session-handoff` | Agent C | Electron Browser runtime, BrowserTask, trusted IPC/preload and Gateway session boundaries, specific security tests | No profile/session spoofing, no WebContentsView replacement |
| `integration-qa` | Agent D / integrator | HWH docs, coordination board, integration, cross-component E2E and Git writes | Must coordinate source ownership; may not silently edit files claimed by others |

**A lane is not an automatic permission grant.** Inspect actual file claims. Ownership can move only by explicit release/reclaim. If two workstreams need `preload.ts` or `browser/index.tsx`, designate ONE writer; other agents provide a patch suggestion/test case via their own notes. No cherry-pick/new branch for routine integration.

## Shared working tree & Git hazards
- All agents see all uncommitted edits instantly. `git status` is NOT a per-agent diff. Never `git add .`, `git commit -a`, `git stash`, `git clean`, forced reset or cherry-pick without integrator approval.
- Agents use `git diff -- <owned-path>` to review. Integrator stages explicit paths, inspects `git diff --cached --name-status`, runs relevant tests, commits, pushes; confirms `origin/feat/hermes-workstation-mvp-20261013`.
- No background builds that mutate source/lockfiles, dependency installs, codegen, format-on-save across the repo while other agents work. All generated-output owners must be claimed too.
- Before cross-lane refactors, announce proposed API signature in `TEAM_BOARD.md` via integrator and receive acceptance from consumer. Prefer contracts and small adapters over shared large-file edits.
- Agents do not change root/workstation AGENTS policies or context logs simultaneously; integrator owns them. Work done at a blocked gate is marked DEVELOPMENT_ONLY and never counted as native qualification.
- Live leases are machine-local, suitable for multiple agents all connected to this Windows checkout. For agents on different computers, the system MUST use a centralized claim authority instead; Git markdown alone is not a distributed lock.

## Update protocol (at most 60s of writing per checkpoint)
Agent reports to integrator: ID, lane, exact owned paths, edit/test status, next action, collision risk, blocking gate. Integrator updates `TEAM_BOARD.md` after each meaningful integration. At conversation end, every incomplete agent returns a **self-contained continuation prompt** with same branch, HEAD, owners, exact next test, live claims, acceptance and the obligation to repeat the handoff. A continuation prompt never assumes an absent agent has released its lane.

## Exit rule
The MVP has one integrated branch and **3 planned implementation prompts after this setup**; target completion, not an endless perfect gate. No cross-owner architectural rewrite unless a failing acceptance test proves necessary. On completion, one aggregate PR, native E2E, CI truth; merge into main only with explicit maintainer direction. Retire/reconcile stale claims only after inspecting the working tree.

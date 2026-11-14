# Hermes Work multi-agent collaboration protocol

## 2026-10-25 — P0-A/P0-B/P1/P2 localmente implementados; Git/CI/cliente externo PENDENTES

O coordenador existente em workstation/scripts/multi_agent_coordination.py recebeu correções P0-A para claims exclusivos ate release e strict opt-in; a nova camada P0-B em workstation/scripts/collab_admission.py e collab_git.py oferece credenciais de sessao e guardiao de integracao Git apenas em superficies gerenciadas. A P1 em workstation/scripts/collab_tasks.py publica tarefas/handoffs/alertas no mesmo .hermes-collab. A P2 em workstation/scripts/collab_mcp_server.py fornece ferramentas MCP stdio com um processo e lease por cliente. NENHUMA dessas etapas foi commitada ou qualificada para release nesta sessao.

Prova focada canônica: 76 PASS / 0 FAIL / 1 SKIP (cinco arquivos). Dois clientes MCP stdio de teste operaram em repo Git temporario, mas nem ChatGPT web nem Claude Code receberam registro novo de conector nesta missao. O mcp local 1.28.0 difere do mcp==2.0.0 fixado em pyproject.toml; validar extra versionado antes de release. Instrucoes reais de cliente: [P2_CLIENT_SETUP.md](multi-agent-collaboration-2026-10-25/P2_CLIENT_SETUP.md). Evidencia e limites: [journal P2](engineering-journal/p2-mcp-collaboration-20261025.md). Direitos Git, claims alheias e protecao de acesso irrestrito continuam INALTERADOS; hooks anteriores e raw Controle Windows nao garantem enforcement universal. Nenhum release ou branch nova implicitamente autorizados.

## 2026-10-25 — Snapshot arquitetural inicial, mantido como histórico (anterior à implementação local)

Architectural direction: one observed branch per physical checkout; no agent-created/switched branches or worktrees without explicit maintainer instruction; disjoint file ownership until explicit release irrespective of status (including BLOCKED and READY_FOR_INTEGRATION); Git writes serialized by a designated authorized integrator; local .hermes-collab remains the single machine-local ownership authority. Never infer that current hooks protect arbitrary Windows PowerShell/ChatGPT MCP writes. P0 coordinator correction, P0 guarded writes/Git, P1 task/handoff awareness and P2 MCP adapter are **planned**, not installed. A reference P0 diff and isolated 11/11 passing contract tests exist in [multi-agent-collaboration-2026-10-25](multi-agent-collaboration-2026-10-25/DECISION_AND_EXECUTION_PLAN.md); implementer sequence: [IMPLEMENTER_PROMPTS.md](multi-agent-collaboration-2026-10-25/IMPLEMENTER_PROMPTS.md). Files currently claimed by WhatsApp M3, including roadmap/intelligence/CURRENT journal, were not overwritten: exact doc handoff is [CANONICAL_INSERTS.md](multi-agent-collaboration-2026-10-25/CANONICAL_INSERTS.md).

**Current safety caveat:** the live check_path() currently filters for status ACTIVE only. Until P0 is integrated, treat *every existing claim in any status* as an exclusive reservation even when check-path returns allowed=true, and never edit claimed files without ownership transfer. Hooks currently fail open and do not protect other tool clients: this is a cooperative instruction, not proven system-wide enforcement.

## Current routing policy — updated 2026-10-25

The shared-branch cycle opened on 2026-10-13 is closed. `main` is the canonical branch for current work. `feat/hermes-workstation-mvp-20261013` and its one-branch instructions are historical, not active routing. Never switch branches because a historical document or hook says to. A future branch is valid only when the current task or maintainer explicitly names it. `COLLABORATION_BRANCH` is an optional hook override only for such an explicitly authorized cycle; it does not itself authorize a branch change.

The live local ownership state is `/.hermes-collab/*.claim/owner.json`, maintained by `python workstation/scripts/multi_agent_coordination.py`; claims are cooperative, machine-local and not a security boundary. `TEAM_BOARD.md` is a durable status snapshot, not a lock. Before editing, inspect `HEAD`, branch, full dirty/untracked state and `python workstation/scripts/multi_agent_coordination.py status`, then claim exact disjoint paths. Do not infer current owners or an integrator from the retired cycle.

## Historical cycle — closed 2026-10-13

## Purpose and status
One feature branch, **one physical checkout**, several agents safely working in parallel. This document is the **policy**; the **live local truth** is `/.hermes-collab/*.claim/owner.json` (ignored by Git), maintained by `python workstation/scripts/multi_agent_coordination.py`. The durable board is `workstation/context/workstation-hub-mvp/TEAM_BOARD.md`, updated by the integrator at checkpoints. Markdown boards do not provide atomic locking; the local claim tool does.

## Historical shared-cycle setup
- Repo: `kevynlucasprofissional-stack/hermes-agent`
- Historical branch: `feat/hermes-workstation-mvp-20261013` from the then-verified `main` `b80d10a4d6d4536b65df52eb4e011ad8d5eef672`
- Historical checkout: `C:\Github\hermes-agent`; do not infer a current branch from this record.
- No per-agent branches or worktrees for routine adjustments. No new PR for individual fixes; one aggregate PR for this cycle.
- One maintainer-appointed **integrator** owns `git add`, `git commit`, `git push`, `git pull`, `git merge`, `git rebase`, `git switch`, `git reset` and PR edits. All other agents are read/write **only in their claimed source files**. Read-only git commands are allowed. No agent may autonomously merge into main.
- At that historical checkpoint H-079 upstream baseline/CI gate applied. Current tasks follow the default gate and explicit-exception policy in `workstation/AGENTS.md`.

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
- Agents use `git diff -- <owned-path>` to review. The explicitly designated integrator stages exact paths, inspects `git diff --cached --name-status`, runs relevant tests, commits and pushes to the target branch explicitly defined for the task.
- No background builds that mutate source/lockfiles, dependency installs, codegen, format-on-save across the repo while other agents work. All generated-output owners must be claimed too.
- Before cross-lane refactors, announce proposed API signature in `TEAM_BOARD.md` via integrator and receive acceptance from consumer. Prefer contracts and small adapters over shared large-file edits.
- Root/workstation policies and context logs have one explicitly designated owner and exact claims; a task may authorize that owner to update them. Do not co-edit these files. Work done at a waived or blocked qualification gate is marked DEVELOPMENT_ONLY and never counted as native qualification.
- Live leases are machine-local, suitable for multiple agents all connected to this Windows checkout. For agents on different computers, the system MUST use a centralized claim authority instead; Git markdown alone is not a distributed lock.

## Update protocol (at most 60s of writing per checkpoint)
Agent reports to integrator: ID, lane, exact owned paths, edit/test status, next action, collision risk, blocking gate. Integrator updates `TEAM_BOARD.md` after each meaningful integration. At conversation end, every incomplete agent returns a **self-contained continuation prompt** with same branch, HEAD, owners, exact next test, live claims, acceptance and the obligation to repeat the handoff. A continuation prompt never assumes an absent agent has released its lane.

## Exit rule
The MVP has one integrated branch and **3 planned implementation prompts after this setup**; target completion, not an endless perfect gate. No cross-owner architectural rewrite unless a failing acceptance test proves necessary. On completion, one aggregate PR, native E2E, CI truth; merge into main only with explicit maintainer direction. Retire/reconcile stale claims only after inspecting the working tree.

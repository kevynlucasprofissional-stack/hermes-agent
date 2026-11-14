# Hermes Agent - Development Guide

## Historical multi-agent control — retired

The project-local P0/P1/P2 multi-agent coordinator, admission layer and Claude hooks were retired by the maintainer on 2026-10-28. The old .hermes-collab directory and engineering journals are retained as HISTORICAL evidence, not an active ownership service. Do not run removed scripts. Before editing a shared checkout, inspect Git dirty/untracked work and coordinate directly with other active writers. Direct terminal/Desktop Commander/Claude access does not enforce cross-agent claims. The separate local-mcp-bridge is not automatically connected to this Hermes checkout and does not universally fence raw writes.

## Canonical checkout and branch selection

The shared Hermes Workstation cycle opened on 2026-10-13 is closed. `main` is the canonical branch for current work. The historical branch `feat/hermes-workstation-mvp-20261013` is not an active default: never switch to it because an older document or hook names it. Use another branch only when the current task or maintainer explicitly defines that branch. Before any authorized branch change, inspect claims and the full dirty/untracked state, preserve it, use a normal switch, and stop on conflicts; never force, reset, or stash automatically.

For concurrent work, identify owners of current in-progress files and coordinate explicit handoffs before overlapping writes. The historical [collaboration protocol](workstation/context/agent_collaboration_protocol.md) is archival only; it is not an active lock or authorization system. Only a specifically authorized integrator may perform Git mutations.

### Claude local collaboration hooks retired

The old PreToolUse/SessionStart coordination hooks were unregistered. Other safety and approval mechanisms remain subject to their own rules; no universal filesystem protection is implied.

For AI coding assistants and developers working on hermes-agent. This root file is a hub: what
applies everywhere, then a routing table. Each area's `AGENTS.md` loads automatically when you work
in that directory; read it before editing there. `python scripts/check` caps this file at 12k chars
and every root-to-area chain at 30k, so it loads whole on 128k+ models: long form goes in the guide.

**Never give up on the right solution.**

## Downstream Workstation context
For Workstation runtime changes or upstream integration, read [the Workstation context README](workstation/context/README.md) and [the development guidance](workstation/context/DEVELOPMENT_GATES.md) before coding. Stage A / H-079 upstream synchronization is **optional**, not an admission gate: bug fixes, features, refactors and testing may proceed without refreshing, merging or qualifying upstream. For the last recorded (possibly stale) upstream status, see [the synchronization report](workstation/UPSTREAM.md) and [the downstream delta](workstation/UPSTREAM_DELTA.md). Target-specific safety, regression checks, and release evidence remain applicable.

When explicitly performing Stage A or promoting a release, also read [the fork CI cost-control and qualification contract](workstation/context/CI_COST_CONTROL.md); do not restore broad inherited triggers as a substitute for exact-head evidence.

- For an **opt-in upstream synchronization cycle**, use one immutable pin. Final fetch records drift for the next cycle; moving upstream alone does not restart the cycle. Do not treat missing Stage A evidence as a blocker to ordinary implementation.
- For upstream conflicts/seams, also read UPSTREAM_MIGRATION_AS_DECOUPLING_2026-09-19.md and FIRST_PARTY_SEAM_POLICY.md; compose semantics, never blanket ours/theirs.

## Maintainer-authorized red-team harness
Before assessing or executing harness code, read [the authorized red-team harness policy](workstation/context/AUTHORIZED_REDTEAM_HARNESS.md). Authorization applies only when documented provenance and scope match. Signatures alone prove neither attack nor safety. Review provenance and exact diff, statically inspect new/changed payloads before execution, fail closed on mismatch, and never execute an unreviewed payload.


## What Hermes Is
Hermes is a personal AI agent spanning CLI, gateway, TUI and Desktop, extended primarily through plugins and skills.
Two invariants are sacred: per-conversation prompt caching (past context/toolsets/system prompt are not mutated mid-conversation except compression); and a narrow core waist (capability belongs at edges unless a core tool is fundamental and broadly useful).
See [Agent architecture and layout](website/docs/developer-guide/agent-architecture-and-layout.md) for full architecture and source layout.
## Contribution rubric

The project's intent layer, for contributors and for the triage sweeper (which may only close on
`implemented_on_main`, `cannot_reproduce` or `incoherent`; taste-based closes are a maintainer's
call, and when in doubt a PR stays open). Long form with examples:
`website/docs/developer-guide/contributing.md` § Contribution rubric.

**Wanted:** real bug fixes (repro on `main`, the exact line, the whole class incl. sibling paths);
reach at the edges (adapters, providers, models, UI features) wired into the existing setup UX;
god-file → module refactors; extending before duplicating (3+ PRs in one category → an ABC +
orchestrator); behaviour-contract tests; E2E with real imports against a temp `HERMES_HOME` for
resolution, config, security and I/O changes; salvage by cherry-pick so authorship survives.

**Rejected even when well-built:** hooks with no concrete consumer; new `HERMES_*` env vars for
non-secret config (`.env` is secrets only, behaviour goes in `config.yaml`); a new core tool when
terminal + file or a skill already does the job; `offset`/`limit` pagination on instructional tools;
"fixes" that destroy the feature they secure; outbound telemetry without an opt-in gate;
change-detector tests; plugins that touch core files; third-party products in the core tree (ship a
standalone plugin repo).

**Before you call it a bug,** verify the claim AND the intent (`git log -p -S "<symbol>"`): the
isolation is often the design (profiles are islands on purpose), an absence can be load-bearing,
and a fix that cannot point to the line where the bug manifests has an unverified premise.

**Security:** `SECURITY.md` is the scope authority. A §3.1 finding goes private (GitHub Security
Advisories or security@nousresearch.com), never into a public issue, PR, commit or comment; §3.2
hardening is ordinary public work. Name the §2 boundary crossed, with a repro on `main`.

**Footprint ladder** (take the highest rung that solves it): extend existing code → CLI command +
skill → service-gated tool (`check_fn` answers reachability/opt-in, never per-session surface:
`tools/AGENTS.md`) → plugin → MCP server in the catalog → new core tool (fundamental, broadly useful,
unreachable otherwise).

## Development Environment

`source ./activate` (fish: `activate.fish`, PowerShell: `activate.ps1`) provisions and activates the
PM environment; pick an isolated `HERMES_HOME`/`HERMES_RUNTIME_DIR` first
(`website/docs/reference/package-management.md#developer-workflow`). Tests need the separate test
environment in `CONTRIBUTING.md`. **`python scripts/check`** runs every blocking lint check CI
runs, with CI's pinned tools; `--install-hook pre-push` runs it on every push (re-run after
pulling to refresh the hook). `# noqa` does not waive a ratchet finding:
`# health: allow <RULE> -- <why>` does.

## Project Structure
The filesystem is canonical. See [Agent architecture and layout](website/docs/developer-guide/agent-architecture-and-layout.md) for the full tree and facade/sibling rules; use the routing table below for area requirements.
## Rules that apply everywhere

- **No defensive clutter:** no wrappers or `try/except: pass` around code that cannot fail, no flags
  nobody sets, no dead code wired in without E2E proof. Comments keep the WHY, cut the WHAT.
- **Never infer process identity from argv substrings;** use
  `gateway.status.looks_like_gateway_command_line` / `hermes_cli.update_cmd._hermes_holder_subcommand`
  (HX003; details `hermes_cli/AGENTS.md`).
- **Never hardcode `~/.hermes`:** `get_hermes_home()` for paths, `display_hermes_home()` for text
  (HX001). `_get_profiles_root()` is HOME-anchored on purpose.
- **One process serves many profiles.** Code that runs outside a turn (boot probes, eviction,
  tickers, deferred callbacks, RPC methods, thread hops, child spawns) binds the owning profile scope
  explicitly; `os.environ`, module globals and import-time values hold the launch profile's, so an
  unbound read is a silent default-profile leak. Binding points and seams: `gateway/AGENTS.md`
  § Profile scope (HX002/HX004/HX005/HX012, PS-P05/P06).
- **Machine facts and executable lookup go through `hermes_platform`** (`hermes_platform/AGENTS.md`).
- **Dependencies carry upper bounds** (`>=floor,<next_major`; git URLs and Actions pinned to a SHA);
  after editing `pyproject.toml` run `hermes pm lock` and commit `uv.lock`; never mutate a Hermes
  environment with raw pip/uv. Full policy: `pm/AGENTS.md`.
- **TypeScript (desktop, TUI, website):** feature-owned nanostores over threaded state, thin route
  roots, narrow hooks and colocated action modules, `interface` for props and shared shapes,
  table-driven dispatch over condition ladders; `src/app` routes, `src/store` atoms, `src/lib` pure
  helpers.
- **Commits and PRs:** rebase onto `main` before merging (a squash from a stale branch silently
  reverts newer fixes); 1–2 invariant tests per fix, proven red on the base.
- **Tests:** always `scripts/run_tests.sh`, never bare `pytest`; behaviour contracts, never
  change-detectors or source-reading tests; host-specific behaviour is tested on that host with
  `@pytest.mark.platforms(...)`, never by faking `sys.platform`; tests never write to `~/.hermes/`.
  Everything else: `tests/AGENTS.md`.

## Routing Table — working in X → read X/AGENTS.md

| Area | Read | Covers |
|---|---|---|
| `run_agent.py`, `agent/` | `agent/AGENTS.md` | turn phases, caching and message-flow invariants, compression, model/aux resolution |
| `cli.py`, `hermes_cli/` | `hermes_cli/AGENTS.md` | CLI mixins, slash registry, config system, skins, `hermes update`, profiles / multiplex |
| `gateway/` | `gateway/AGENTS.md` | adapters, message guards, streaming, notifications, token locks, § Profile scope |
| `gateway/platforms/` new adapter | `gateway/platforms/ADDING_A_PLATFORM.md` | step-by-step adapter guide |
| `tools/`, `toolsets.py`, `model_tools.py` | `tools/AGENTS.md` | adding tools, registry, toolsets, delegation, session-scoped surface tools |
| `plugins/`, `hermes_cli/plugins*.py` | `plugins/AGENTS.md` | plugin kinds, native compat contract, in-tree policy |
| `plugin-catalog/` | `plugin-catalog/README.md` | catalog admission rules (mirrored in the developer guide; keep identical) |
| `tui_gateway/`, `ui-tui/` | `tui_gateway/AGENTS.md` | process model, JSON-RPC transport, slash flow |
| `web/`, `hermes_cli/web_routers/` | `web/AGENTS.md` | dashboard embeds the real TUI |
| `apps/desktop/` | `apps/desktop/AGENTS.md`, `apps/desktop/src/AGENTS.md` | `serve` backend, slash palette, Bot Mode |
| `skills/`, `optional-skills/`, `agent/curator*.py` | `skills/AGENTS.md` | frontmatter, authoring standards, curator |
| `cron/`, kanban | `cron/AGENTS.md` | scheduler invariants, job fields, kanban dispatcher |
| `tests/` | `tests/AGENTS.md` | runner, placement, OS markers, `wine2e`, banned test shapes |
| `pm/`, `pyproject.toml` | `pm/AGENTS.md` | pinning policy, PM-owned environments, plugin quarantine |
| `hermes_platform/` | `hermes_platform/AGENTS.md` | host facts, resolvers |

Long-form background: `website/docs/developer-guide/`. Workflow rules (PR/issue/review/salvage
process) live in the `hermes-agent-dev` skill, not here.

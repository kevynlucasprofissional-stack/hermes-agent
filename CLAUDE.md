# CLAUDE.md — Hermes Agent

Project-specific guidance for Claude Code sessions working in this repository.

### Retired multi-agent control

The project-local P0/P1/P2 multi-agent coordinator, admission layer and Claude hooks were retired by the maintainer on 2026-10-28. The old .hermes-collab directory and engineering journals are retained as HISTORICAL evidence, not an active ownership service. Do not run removed scripts. Before editing a shared checkout, inspect Git dirty/untracked work and coordinate directly with other active writers. Direct terminal/Desktop Commander/Claude access does not enforce cross-agent claims. The separate local-mcp-bridge is not automatically connected to this Hermes checkout and does not universally fence raw writes.
Claude Code works through its existing direct machine and Hermes Workstation access; no local-mcp-bridge installation or plugin enrollment is required for this project.

## AI Control & Dogfooding (Desktop)

When developing or testing the Hermes Desktop app (`apps/desktop`) with the
renderer running (`npm run dev`), use the CDP-based AI control workflow
described in [`apps/desktop/docs/AI-CONTROL-GUIDE.md`](apps/desktop/docs/AI-CONTROL-GUIDE.md).

Key points:

- **Read before acting:** always check `window.__hermesAiControlActive` via
  `node apps/desktop/scripts/eval.mjs "window.__hermesAiControlActive"` before
  any destructive UI action (click, fill, navigate). Proceed only when `true`.
- **Toggle:** the user toggles AI control with **Ctrl+Shift+A**; a "🤖 AI Control"
  badge in the top-right corner reflects the current state.
- **Eval CLI:** `node apps/desktop/scripts/eval.mjs "<expression>"` runs JS in
  the renderer via CDP (port 9222, loopback-only, dev-only). See the guide for
  read/write examples and known limitations.
- **Scope:** this mechanism coordinates AI vs human interaction with the
  *desktop UI*. It is unrelated to `workstation/browser_session.py`'s
  `BrowserControlLeaseManager`, which governs the embedded browser's web tabs.

## Skills permanentes (carregar em toda sessão)
As seguintes skills devem ser invocadas automaticamente no início de cada sessão de trabalho técnico neste projeto:
- /ponytail-ponytail (modo lazy senior dev padrão)
- /caveman-compress-caveman (compressão de tokens quando aplicável)
- /investigate-first-caveman (diagnóstico antes de edição)
- /lean-build-caveman (escopo estrito e stop condition)
- /verification-before-completion-superpowers (evidência antes de conclusão)
- /systematic-debugging-superpowers (root cause antes de fix)
- /surgical-patch-caveman (fixes cirúrgicos)
- /verify-and-stop-caveman (provar aceite sem expansão)
- /hermes-work-control (controle CDP da UI do Hermes Desktop em dev; leia apps/desktop/docs/AI-CONTROL-GUIDE.md para detalhes)

Nota: /humanizer-pt-br e /skill-discovery já estão configurados respectivamente como skill condicional e hook automático; não duplicar.

Estas skills complementam mas não substituem as regras do [AGENTS.md](AGENTS.md), que é a fonte primária de regras específicas do hermes-agent.

## Shared checkout coordination

The project-local Claude collaboration hooks were removed. Do not assume direct CLI/filesystem tools provide ownership isolation. Obtain an explicit handoff before touching another active writer's work.

## Repository Conventions

- TypeScript style rules live in `AGENTS.md` at the repo root and in
  `apps/desktop/src/AGENTS.md`; follow them for all desktop changes.
- Tool authoring rules live in `tools/AGENTS.md`; read before adding or
  modifying anything under `tools/`.
- The desktop app spawns its own headless backend via `hermes serve`; never
  re-parent the messaging gateway under it.

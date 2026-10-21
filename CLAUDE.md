# CLAUDE.md — Hermes Agent

Project-specific guidance for Claude Code sessions working in this repository.

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

## Multi-Session Collaboration Enforcement

Hooks automáticos impedem que sessões independentes sobrescrevam trabalho alheio no checkout compartilhado. **Antes de qualquer edição**, o hook `PreToolUse` consulta `python workstation/scripts/multi_agent_coordination.py check-path <path>` e bloqueia escritas em caminhos reclamados por outro agente. O hook `SessionStart` alerta quando a branch atual não é `feat/hermes-workstation-mvp-20261013`.

- Os hooks estão em `.claude/hooks/check-claim-edit.sh`, `check-claim-bash.sh` e `check-branch.sh`, registrados em `.claude/settings.local.json`.
- Se o script de coordenação falhar, os hooks falham abertos (permitem a edição) para não bloquear trabalho solo.
- Sessões novas devem verificar claims (`python workstation/scripts/multi_agent_coordination.py status`) e branch antes de escrever.
- Detalhes completos: [`workstation/context/AGENT_COLLABORATION_PROTOCOL.md`](workstation/context/AGENT_COLLABORATION_PROTOCOL.md).

## Repository Conventions

- TypeScript style rules live in `AGENTS.md` at the repo root and in
  `apps/desktop/src/AGENTS.md`; follow them for all desktop changes.
- Tool authoring rules live in `tools/AGENTS.md`; read before adding or
  modifying anything under `tools/`.
- The desktop app spawns its own headless backend via `hermes serve`; never
  re-parent the messaging gateway under it.
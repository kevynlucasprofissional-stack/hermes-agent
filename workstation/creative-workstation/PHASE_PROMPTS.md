# Prompts enxutos por fase — uso após o briefing

**Todos os prompts pressupõem acesso ao repositório e obedecem `AGENTS.md`, `workstation/context/README.md`, H-079 e [VERIFICATION_MATRIX.md](VERIFICATION_MATRIX.md).** Não use esses prompts para burlar os gates; as leituras mandatórias continuam mandatórias.

## CW-01 — Preflight e auditoria (primeira mensagem recomendada)

> Verifique `workstation/creative-workstation/EXECUTION_BRIEF.md` e a seção CW-01 do `IMPLEMENTATION_PLAN.md`. Leia as instruções mandatórias de AGENTS/context, execute H-079 no HEAD real, identifique main/upstream pins, CI required, blockers H-080/KI e owners existentes para adapter, process lifecycle, Browser, TaskCompiler, artifacts, registry e Experience Compiler. Audite licença e ref de Penpot, Remotion, Three e FFmpeg. **Não altere runtime.** Registre tabela de owner/arquivo/símbolo/gap, baseline e recomendação GO/BLOCKED para CW-02, com receipts/links; atualize journal como investigação e apresente o menor PR/evidência necessário.

## CW-02 — Creative Runtime mínimo

> A partir de um baseline H-079 realmente qualificado, implemente apenas CW-02: contrato tipado de descoberta/health/app opt-in reutilizando lifecycle e authority existentes. Nada de nova DB/Browser/TaskRun ou instalação automática. Localize os símbolos atuais antes de codificar; crie testes positivos e negativos de consentimento, perfil, porta, crash, secret env, rollback e restart conforme Verification Matrix. Feature flag off por padrão. Rode suites reais e abra PR isolado; documente SHAs/recibos/gates, sem merge.

## CW-03A — Vertical estática (sem dependência de Remotion)

> Após CW-02 qualificada, prove `React/SVG → Chromium Electron WebContentsView → PNG` com fonte editável, workspace, hash, dimensões e owner readback. Teste asset ausente, caminho inválido, mutação incerta, reabertura/restart, isolamento A/B e browser bound. Crie apenas a mínima extensão tipada. Execute Electron E2E e testes reais; PR separado, sem merge.

## CW-03B e CW-03C — Renderização e vídeo

> Com CW-03A provada, adicione FFmpeg/ffprobe em operações seguras tipadas, codec/paths/timeout/sha e verificação de vídeo; negative tests e export real. Remotion/Studio/skills só entram em **outro PR**, depois de decisão explícita da licença aplicável ao uso/distribuição. Se licença não admissível, mantenha FFmpeg + React/SVG. Não instalar terceiros automaticamente.

## CW-04 — Penpot

> Com browser/projeto criativo qualificados, audite MCP oficial `penpot/penpot/mcp` no SHA e consentimento, roles, licença Penpot/MPL versus Penpot AI Kit/CC-BY. Implemente adapter tipado mínimo e UI no Chromium existente. Prove projeto criado por agente, editado manualmente por humano, depois nova edição por agente preservando a humana. Negativos: wrong owner/token, stale rev, cross-profile e denied permission; E2E/CI/PR.

## CW-05 — Three.js

> Use Three.js Editor em versão pinada com bridge tipada mínima; comandos inspect/add/transform/material/camera/light/export/snapshot/undo; não fornecer JS livre no renderer privilegiado. Prove GLB/scene que salva, reabre e respeita mudanças humanas, revisão e undo; negativos de stale rev, command injection, wrong owner e export failure. Electron real, testes e PR isolado.

## CW-06 — Engines especializadas

> Só com necessidade e dependência real: Inkscape CLI ou Blender bpy/headless como adapter externo, com versão, limite de filesystem/rede, health, outputs/receipts, negative tests e rollback. Não integrar todos em um PR. Graphite/Godot/áudio/CAD permanecem pesquisa.

## CW-07 — Experience Compiler

> Depois de uma vertical já qualificada, ligue os receipts criativos ao Experience Compiler e OperationalCapabilityRegistry **existentes**. Prove candidate, controles negativos seguros, replay empírico, promoção por policy e segunda execução real verificável. Drift tool/schema/scope/owner deve bloquear reuse; não permitir auto-certificação e não editar estado vivo para experimentos negativos. Métricas somente com dados observados. PR pequeno, testes, journal e relatório causal.

## Relatório para toda fase

`STATUS | HEAD/pin/CI | owners/code diff | tests (comandos + outcomes) | receipts/artifacts | negative tests | blocker/rollback | PR | next smallest safe step`.

A primeira mensagem da série deve ser **CW-01**. Os prompts seguintes são escolhidos somente após gates/CI/avaliação da fase anterior.

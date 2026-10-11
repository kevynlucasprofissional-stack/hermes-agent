# Auditoria Code-to-Code do Ecossistema Browser — Hermes Workstation

**Data:** 10 de Outubro de 2026  
**Status da Auditoria:** CONCLUÍDA / 100% AUDITADO / ZERO ALTERAÇÕES NO RUNTIME  
**HEAD SHA Local:** `56f5758d9b589f3bc04f5a4b4305d80d8fd459a7`  
**Upstream Pinned:** `NousResearch/hermes-agent@6a2662a4aaad68e1b75f6e7ac789409aa653abf7`  

---

## 1. Visão Geral da Entrega

Esta auditoria profunda comparou, linha por linha de código, a implementação do subsistema Browser do **Hermes Work** contra **25 projetos** da categoria Browser presentes na biblioteca local em `referências/02-Browser-Automacao-Web/` e analisou **49 sessões reais de produção** em `workstation/dogfood/dados/Sessões Hermes/`.

Todos os relatórios, matrizes, comparações cruzadas, dados tabulares e planos de implementação foram persistidos neste diretório.

---

## 2. Mapa de Navegação dos Documentos Canônicos

### Documentos Principais de Auditoria
- [00-BASELINE-E-ESCOPO.md](00-BASELINE-E-ESCOPO.md) — Definição do escopo, invariantes não-negociáveis e vocabulário de evidência (`FACT`, `PARTIAL`, `NV`, `INFERENCE`, `RECOMMENDATION`).
- [01-INVENTARIO-REFERENCIAS.md](01-INVENTARIO-REFERENCIAS.md) — Inventário completo dos 25 repositórios com commits, branches, licenças, stacks e testes.
- [02-ARQUITETURA-ATUAL-HERMES.md](02-ARQUITETURA-ATUAL-HERMES.md) — Diagnóstico aprofundado do runtime atual (`workstation-browser-runtime.ts`), identificando os 5 gargalos mecânicos primários.
- [03-MATRIZ-COMPARATIVA.md](03-MATRIZ-COMPARATIVA.md) — Matriz comparativa cobrindo 25 dimensões arquiteturais cruzadas com 8 projetos líderes.
- [04-OPORTUNIDADES-REUTILIZACAO.md](04-OPORTUNIDADES-REUTILIZACAO.md) — Catálogo formal de reuso: `COPY`, `ADAPT`, `REIMPLEMENT PATTERN`, `INTEGRATE EXTERNAL`, `KEEP HERMES` e `REJECT`.
- [05-BROWSEROS-DEEP-DIVE.md](05-BROWSEROS-DEEP-DIVE.md) — Análise arquitetural dedicada sobre o BrowserOS (AGPL-3.0 vs MIT, diff de snapshots, side panel e lições aprendidas).
- [06-DESEMPENHO-E-CUSTO.md](06-DESEMPENHO-E-CUSTO.md) — Decomposição analítica de latência, layout thrashing, consumo de tokens e custos por tarefa.
- [07-SESSOES-REAIS.md](07-SESSOES-REAIS.md) — Análise forense de 49 sessões reais do Hermes Work (Trello, Instagram, Hyperframes), comprovando por que o agente recorre a centenas de hacks em `browser_console`.
- [08-BENCHMARKS-E-EXPERIMENTOS.md](08-BENCHMARKS-E-EXPERIMENTOS.md) — Protocolo de testes reprodutíveis, fixtures locais e medição rigorosa de ganhos.
- [09-RANKING-DE-MELHORIAS.md](09-RANKING-DE-MELHORIAS.md) — Ranking ponderado de 12 oportunidades aplicando a fórmula canônica de benefício (Desempenho 30%, Custo 20%, Confiabilidade 20%, UX 15%, Reuso 15%).
- [10-PLANO-DE-IMPLEMENTACAO.md](10-PLANO-DE-IMPLEMENTACAO.md) — Roteiro de engenharia em 5 fases (P0 a P4) pronto para a próxima missão de implementação.
- [11-SINTESE-EXECUTIVA.md](11-SINTESE-EXECUTIVA.md) — Síntese executiva em português respondendo às três perguntas estratégicas centrais.

---

### Relatórios Individuais de Repositórios (`repositorios/`)
- [browseros.md](repositorios/browseros.md) — BrowserOS (AGPL-3.0, diffs, sidepanel, AXTree).
- [stagehand.md](repositorios/stagehand.md) — Stagehand (Apache-2.0, extração estruturada, cache).
- [browser-use.md](repositorios/browser-use.md) — Família Browser-Use (MIT, watchdogs, desktop overlay, chrome-import).
- [agent-browser.md](repositorios/agent-browser.md) — Agent Browser (Apache-2.0, Rust, CDP AXTree de alta velocidade).
- [browserclaw.md](repositorios/browserclaw.md) — BrowserClaw (MIT, motor de batch, SPA hydration guard).
- [camofox.md](repositorios/camofox.md) — Camofox (MIT, stealth anti-detection engine).
- [hermes-browser-extension.md](repositorios/hermes-browser-extension.md) — Extensão Chrome oficial do Hermes.
- [driftlock.md](repositorios/driftlock.md) — Driftlock (MIT, auto-reparo e classificação de UI drift).
- [browser-memory.md](repositorios/browser-memory.md) — Browser-Memory (MIT, destilação procedural e origin-lock).
- [lattice.md](repositorios/lattice.md) — Lattice (MIT, UI Graph e deltas espaciais).
- [witness.md](repositorios/witness.md) — Witness (MIT, cálculo de custos por modelo e replay).
- [browsertrace.md](repositorios/browsertrace.md) — BrowserTrace (MIT, comparação de execuções).
- [hermes-agent-upstream.md](repositorios/hermes-agent-upstream.md) — Baseline upstream canônica do NousResearch.
- [browser4.md](repositorios/browser4.md), [vibesurf.md](repositorios/vibesurf.md), [hermes-webui.md](repositorios/hermes-webui.md), [openclaw.md](repositorios/openclaw.md), [browserbench.md](repositorios/browserbench.md), [browsewebapp-bench.md](repositorios/browsewebapp-bench.md), [browser-agent.md](repositorios/browser-agent.md).

---

### Comparações Cruzadas (`comparacoes/`)
- [stagehand-vs-browseruse-vs-agentbrowser-vs-hermes.md](comparacoes/stagehand-vs-browseruse-vs-agentbrowser-vs-hermes.md)
- [browseros-vs-browseruse-desktop-vs-hermes.md](comparacoes/browseros-vs-browseruse-desktop-vs-hermes.md)
- [browser-memory-vs-lattice-vs-hermes.md](comparacoes/browser-memory-vs-lattice-vs-hermes.md)
- [browsertrace-vs-witness-vs-journal.md](comparacoes/browsertrace-vs-witness-vs-journal.md)
- [camofox-vs-browserclaw-vs-hermes-native.md](comparacoes/camofox-vs-browserclaw-vs-hermes-native.md)

---

### Dados Tabulares e Evidências
- `dados/inventario.csv` — Inventário tabular dos 25 repositórios.
- `dados/mecanismos.csv` — Comparação tabular de mecanismos.
- `dados/oportunidades.csv` — Pontuação e ranking de oportunidades.
- `dados/benchmarks.csv` — Métricas preliminares medidas e estimadas.
- `evidencias/index.json` — Índice de proveniência de arquivos e receipts.
- `STATUS.json` — Estado consolidado da missão.

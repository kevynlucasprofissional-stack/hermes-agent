# 10 — Plano de Implementação em Fases (Engenharia Acionável)

**Data:** 10 de Outubro de 2026  
**Status:** ACTIONABLE IMPLEMENTATION ROADMAP (Pronto para consumo por agente implementador)  
**Regra Fundamental:** Nenhuma modificação foi ou deve ser realizada no runtime durante esta missão de auditoria. Este plano constitui o roteiro de execução para a próxima missão.

---

## Fase P0 — Otimizações Fundamentais de Desempenho e Ferramental

Objetivo: Eliminar os três gargalos mais graves do runtime (latência de snapshot, ausência de lote e falta de extração estruturada), que hoje forçam o agente a improvisar centenas de hacks em `browser_console`.

### Item P0.1: Implementação do Motor de Lote (`browser_batch_actions`)
- **Arquivos Hermes a Modificar/Criar:**
  - Novo: `apps/desktop/electron/workstation-browser-batch.ts`
  - Editar: `apps/desktop/electron/workstation-browser-runtime.ts` (adicionar `case 'browser_batch_actions'` no switch de ações)
  - Editar: `tools/browser_workstation.py` (adicionar função `browser_batch_actions(actions, task_id=None)`)
  - Editar: `toolsets.py` e `tools/registry.py` (registrar schema da ferramenta para o modelo)
- **Arquivo de Referência:** `referências/02-Browser-Automacao-Web/browserclaw-main/src/actions/batch.ts`
- **Classes/Funções Envolvidas:** `executeBatch()`, `BatchAction`, `executeSingleAction()`.
- **Alterações:** Portar os tipos de ação de `BatchAction` (`click`, `type`, `press`, `fill`, `wait`) para TypeScript no Electron, executando-os sequencialmente sobre o `WebContentsView` sem disparar snapshots intermediários.
- **Licença:** MIT (Cópia e adaptação direta autorizada).
- **Testes:** Novo arquivo `apps/desktop/electron/workstation-browser-batch.test.ts` (testar execução de 5 ações, parada em erro, e timeout de lote).
- **Critério de Aceitação:** Envio de lote com 5 preenchimentos e 1 clique executado com sucesso em menos de 800 ms.
- **Rollback:** Desativar a ferramenta no `tools/registry.py` e no switch do runtime (zero impacto em ferramentas existentes).

---

### Item P0.2: Snapshot Nativo via CDP Accessibility Tree
- **Arquivos Hermes a Modificar/Criar:**
  - Novo: `apps/desktop/electron/workstation-browser-snapshot.ts`
  - Editar: `apps/desktop/electron/workstation-browser-runtime.ts` (substituir o miolo de `snapshotForEntry` pela nova rotina)
- **Arquivos de Referência:**
  - `referências/02-Browser-Automacao-Web/vercel-labs--agent-browser/cli/src/native/snapshot.rs`
  - `referências/02-Browser-Automacao-Web/browseros-ai--BrowserOS/packages/browseros-agent/packages/browser-core/src/core/snapshot/render.ts`
- **Classes/Funções Envolvidas:** `renderSnapshot()`, `Accessibility.getFullAXTree`, `formatLine()`.
- **Alterações:** Anexar uma sessão CDP interna (`wc.debugger.attach('1.3')` ou CDP session) e invocar `Accessibility.getFullAXTree`. Filtrar nós irrelevantes e formatar uma árvore indentada concisa com referências `@1`, `@2`. O `inventoryScript` legado baseado em `querySelectorAll('*')` é completamente aposentado.
- **Licença:** Reimplementação limpa em TypeScript (padrão arquitetural sob MIT).
- **Testes:** `tests/test_browser_snapshot_fast.py` e testes no Jest do Electron.
- **Critério de Aceitação:** Latência de snapshot reduzida de ~800 ms para menos de 60 ms em páginas com mais de 300 elementos. Zero reflow no DOM.
- **Rollback:** Manter flag `browser.workstation.legacy_snapshot: true` em `config.yaml` que volta a chamar o script legado se necessário.

---

### Item P0.3: Extração Estruturada com Cache (`browser_extract`)
- **Arquivos Hermes a Modificar/Criar:**
  - Editar: `apps/desktop/electron/workstation-browser-runtime.ts` (adicionar `case 'browser_extract'`)
  - Editar: `tools/browser_workstation.py` (adicionar `browser_extract(instruction, schema=None, cache=True)`)
- **Arquivo de Referência:** `referências/02-Browser-Automacao-Web/browserbase--stagehand/packages/sdk-python/examples/caching.py` e `packages/sdk-ts/src/clientSchemas.ts`
- **Alterações:** O runtime extrai o conteúdo semântico relevante e aplica o schema JSON. O resultado é armazenado em cache associado a `hash(url + dom_digest + instruction)`. Em chamadas repetidas na mesma página, o retorno é instantâneo com `cache_hit: true`.
- **Licença:** Apache-2.0 (Adaptado com preservação de cabeçalho de copyright).
- **Testes:** Testar extração de lista de 10 itens com verificação de cache na segunda chamada.
- **Critério de Aceitação:** Eliminação comprovada da necessidade de injeção de scripts de scraping em `browser_console`.

---

## Fase P1 — Reutilização de Implementações Maduras e Estabilidade

Objetivo: Economizar tokens de observação intermediária, blindar o navegador contra falhas e eliminar o atrito de autenticação.

### Item P1.1: Diffs de Snapshot Pós-Mutação (`diffSnapshots`)
- **Arquivos:** Novo `apps/desktop/electron/browser-snapshot-diff.ts`.
- **Referência:** `referências/02-Browser-Automacao-Web/browseros-ai--BrowserOS/packages/browseros-agent/packages/browser-core/src/core/snapshot/diff.ts`.
- **Alterações:** Reimplementar em TypeScript (MIT) o algoritmo de LCS com janela deslizante de 3 linhas. O `browser_click` e `browser_type` passam a retornar apenas as linhas que mudaram em vez da página inteira.
- **Impacto:** Economia de até 85% de tokens por passo.

### Item P1.2: Importação de Sessão Local do Google Chrome (`chrome-import`)
- **Arquivos:** Novo `apps/desktop/electron/chrome-import.ts`.
- **Referência:** `referências/02-Browser-Automacao-Web/browser-use--desktop/app/src/main/chrome-import/`.
- **Alterações:** Portar a rotina de leitura do SQLite do Chrome no Windows com descriptografia DPAPI. Expor comando opcional na UI do Desktop e CLI: `hermes browser import-chrome-session`.
- **Impacto:** O usuário não precisa logar manualmente em sites como WhatsApp, Trello e Instagram no Hermes Desktop.

### Item P1.3: Sentinelas Modulares de Crash e Abas (`CrashWatchdog`)
- **Arquivos:** `apps/desktop/electron/workstation-browser-runtime.ts`.
- **Referência:** `referências/02-Browser-Automacao-Web/browser-use--browser-use/browser_use/browser/watchdogs/crash_watchdog.py`.
- **Alterações:** No evento `render-process-gone` do WebContents, interceptar o código de saída, recarregar a URL segura e notificar a tarefa sem derrubar o controller.

---

## Fase P2 — Melhorias na Experiência e Interação Humano-Agente

Objetivo: Proporcionar visualização e cooperação sem fricção entre humano e agente.

### Item P2.1: Overlay Visual de Intervenção Humana
- **Arquivos:** `apps/desktop/src/app/browser/` e `apps/desktop/electron/browser-windows.ts`.
- **Referência:** `browser-use/desktop/app/src/main/takeoverOverlay.ts`.
- **Alterações:** Renderizar borda iluminada suave e badge discreto quando o humano aciona o lease de controle (`Take Control`), fornecendo feedback tátil e visual de posse da navegação.

### Item P2.2: Drawer de Histórico de Execução Compacto
- **Arquivos:** `apps/desktop/src/app/browser/task-journal-drawer.tsx`.
- **Referência:** `browseros-ai/BrowserOS/packages/browseros-agent/apps/app/modules/chat/execution-history-tracker.hooks.ts`.
- **Alterações:** Exibir os passos executados como uma linha do tempo limpa (com miniaturas dos elementos clicados), despoluindo a janela principal do chat.

---

## Fase P3 — Inteligência e Capacidades Operacionais

Objetivo: Integrar as novas capacidades determinísticas ao ciclo de aprendizagem do Hermes.

### Item P3.1: Auto-Reparo e Diagnóstico de Drift com Driftlock
- **Arquivos:** `workstation/operational_kernel.py`.
- **Referência:** `referências/02-Browser-Automacao-Web/VasuBansal7576--driftlock/driftlock/lib/diagnose.mjs`.
- **Alterações:** Ao disparar `CapabilityDriftError`, invocar a classificação de drift. Se for puramente cosmético ou atributo renomeado, tentar reparar o seletor autonomamente antes de congelar a capacidade.

### Item P3.2: Contabilidade Financeira Precisa por TaskRun
- **Arquivos:** `workstation/operational_telemetry.py` e `ExecutionJournal`.
- **Referência:** `referências/02-Browser-Automacao-Web/EricFinland--witness/witness/pricing.py`.
- **Alterações:** Calcular custo real em dólares para cada TaskRun com base em tokens de entrada/saída e visões computacionais, gravando o valor no receipt final da tarefa.

---

## Fase P4 — Pesquisa, Avaliação e Benchmarks

### Item P4.1: Avaliação Contínua com BrowseWebApp-Bench
- **Arquivos:** `workstation/tests/test_browser_acceptance.py`.
- **Referência:** `referências/02-Browser-Automacao-Web/visnia-ai--browsewebapp-bench`.
- **Alterações:** Integrar as fixtures locais de teste offline para garantir que atualizações futuras do Hermes não regridam em formulários complexos ou SPAs.

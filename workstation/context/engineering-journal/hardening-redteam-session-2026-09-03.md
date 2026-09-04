# Engineering Journal: Sessão Exaustiva de Hardening, Red Team e Evolução Quality-First

**Date:** 2026-09-03
**Branch:** `feat/workstation-v1-1-5-integrated-dogfood`
**Status:** IN PROGRESS (Under Quality-First Playbook)

---

## 1. Contexto e Motivação

Após a estruturação inicial dos subsistemas V1, V1.1 e V2, iniciamos uma sessão profunda de engenharia defensiva, testes de penetração/adversariais (red team), levantamento de hipóteses e hardening arquitetural e de UIX conforme estipulado pelo Playbook Quality-First.

O objetivo é transformar implementações funcionais em sistemas resilientes a falhas de produção, tráfego real, páginas complexas da web moderna, concorrência e bordas de usabilidade no Desktop.

---

## 2. Ledger de Hipóteses

### H-101 — Fragilidade de Seletores CSS na Memória Procedural em Aplicações Modernas (SPA / Tailwind)
- **Claim:** Procedimentos web que dependem exclusivamente de um único seletor CSS estático quebram na primeira alteração de compilação de SPAs modernas (Tailwind, Emotion, CSS Modules) ou variações mínimas de ID dinâmico (`:r1:`).
- **Why plausible:** Quase todas as aplicações modernas usam classes utilitárias ou nomes ofuscados que mudam entre deploys, enquanto landmarks semânticos e papéis acessíveis (`role`, `aria-label`, `data-testid`) permanecem estáveis.
- **Expected Confirming Evidence:** Procedimento executado em mock ou página com classes dinâmicas falha com seletor puro, mas recupera com sucesso se possuir estratégia multi-ancorada (fallback anchors).
- **Refutation Attempt:** Provar que seletores CSS puros são suficientes mesmo quando classes são alteradas. (Falsificável: seletores com classes Tailwind sofrem drift imediato).
- **Classification:** CONFIRMED & MITIGATED.
- **Resolution & Evidence:**
  - Em `workstation/memory.py`: Adicionada resolução multi-facetada (`resolve_anchor` em `ProcedureStep`) avaliando em cascata `testid` -> `role_name` -> `text` -> `selector`.
  - Adicionado merge concorrente em disco em `ProceduralMemory._persist()` para evitar perda de dados entre processos.
  - Testes: `test_procedure_multi_facet_anchoring` e `test_concurrent_procedure_persistence` em `workstation/tests/test_memory.py` (4/4 passed).

### H-102 — Alucinação do Agente por Nós Ocultos na Percepção de DOM
- **Claim:** Extrair árvores de acessibilidade sem validação de visibilidade real (`display:none`, `visibility:hidden`, `aria-hidden="true"`, `opacity:0`) polui a percepção e induz o LLM a tentar interagir com modais fechados, dropdowns recolhidos e tags de analytics.
- **Why plausible:** O DOM contém centenas de nós interativos que estão logicamente presentes no código, mas fisicamente invisíveis na tela para o usuário humano.
- **Expected Confirming Evidence:** Uma página com modal oculto gera referências interativas `[#ref]` para botões dentro do modal invisível.
- **Classification:** CONFIRMED & MITIGATED.
- **Resolution & Evidence:**
  - Em `workstation/perception.py`: `_extract_nodes` agora descarta nós e subárvores com `aria-hidden="true"`, `hidden="true"`, `style="display:none"`, `style="visibility:hidden"` ou `type="hidden"`.
  - Teste: `test_perception_filters_hidden_nodes` em `workstation/tests/test_perception.py` confirmou que elementos ocultos não geram badges `[#ref]`.

### H-103 — Truncamento Linear de Tokens Remove Ações Críticas de Rodapé (CTAs / Checkout)
- **Claim:** O truncamento sequencial linear simples quando o `token_budget` é ultrapassado elimina sistematicamente os elementos no final da página, justamente onde se localizam botões de envio, confirmação de pedido e finalização de tarefas.
- **Why plausible:** Em páginas longas, o topo contém headers e navegação volumosa; a ação primária costuma estar no terço inferior.
- **Expected Confirming Evidence:** Orçamentação ingênua descarta o botão de Checkout de uma página de compra de 100 itens. Orçamentação seletiva preserva o formulário e os botões de ação descartando itens estáticos repetitivos de lista.
- **Classification:** CONFIRMED & MITIGATED.
- **Resolution & Evidence:**
  - Em `workstation/perception.py`: Implementado sistema de importância por camadas (*tiered smart budgeting*): Tier 1 (Ações/Botões e Inputs de formulários) é priorizado incondicionalmente sobre Tier 2 (Navegação/Links) e Tier 3 (Conteúdo estático).
  - Teste: `test_smart_budget_preserves_bottom_ctas` provou que um botão de checkout no fim de 50 parágrafos sobrevive ao corte de orçamento.

### H-104 — Bloqueio de Execução por Modais de Consentimento e Overlays Invasivos
- **Claim:** Mutações de página causadas por banners de consentimento de cookies/LGPD, paywalls ou modais de newsletter bloqueiam cliques no elemento alvo, mesmo que o elemento ainda exista no DOM.
- **Why plausible:** Overlays cobrem a viewport com `z-index` elevado e interceptam eventos de ponteiro, causando falhas silenciosas de automação.
- **Expected Confirming Evidence:** Drift Governor detecta presença de termos como "cookie consent" ou backdrop cobrindo a tela e gera recomendação de adaptação para dispensar o modal.
- **Classification:** CONFIRMED & MITIGATED.
- **Resolution & Evidence:**
  - Em `workstation/drift.py`: Adicionada ação `AdaptationAction.DISMISS_OVERLAY` e detecção de padrões de overlays invasivos (`OVERLAY_PATTERNS`) com identificação automática do botão de consentimento/fechamento.
  - Em `workstation/safety.py`: Expandida a fronteira estrita de segurança financeira/irreversível (`checkout`, `placeOrder`, `wire_transfer`, `subscribe`, `delete_account`, etc.), normalizando snake_case e camelCase.
  - Testes: `test_drift_detects_blocking_cookie_overlay` e `test_expanded_financial_safety_boundaries` em `workstation/tests/test_drift.py` (8/8 passed).

### H-105 — Falhas de Decodificação e Falso-Positivos em Conexões Headless no Lightpanda
- **Claim:** Requisições para servidores que enviam Content-Encoding comprimido (`gzip`, `deflate`, `br`) ou que emitem redirects para rotas de autenticação degradam a leitura em lixo binário ou violam o invariante fail-closed.
- **Why plausible:** HTTP streams modernos utilizam compressão por padrão; servidores com auth obrigatória redirecionam para `/login`.
- **Expected Confirming Evidence:** Resposta gzip retorna decodificada em texto legível com descompressor transparente; redirect para tela de login dispara fail-closed imediato.
- **Classification:** CONFIRMED & MITIGATED.
- **Resolution & Evidence:**
  - Em `workstation/lightpanda.py`: Adicionado descompactador transparente para `gzip` e `deflate` (com fallback zlib raw). Adicionada checagem da URL final redirecionada com cancelamento imediato e `PermissionError` fail-closed se apontar para rotas de autenticação (`/login`, `/auth`, `accounts.google`, etc.).
  - Testes: `test_lightpanda_handles_decompression` e `test_lightpanda_aborts_on_auth_redirect` em `workstation/tests/test_lightpanda.py` (4/4 passed).

### H-106 — Deadlocks e Starvation na Fila Multi-Tarefa por Tarefas Órfãs
- **Claim:** Se uma tarefa ativa entrar em espera infinita ou o agente falhar sem chamar `complete_task` ou `park_task`, o agendador multi-tarefa fica permanentemente bloqueado, impedindo que tarefas na fila sejam executadas.
- **Why plausible:** Processos distribuídos sem lease timeout sofrem deadlock quando o detentor da posse falece silenciosamente.
- **Expected Confirming Evidence:** Um agendador com lease timeout e renovação de heartbeat detecta expiração da tarefa órfã e avança para a próxima da fila.
- **Classification:** CONFIRMED & MITIGATED.
- **Resolution & Evidence:**
  - Em `workstation/scheduler.py`: Adicionado campo `lease_expires_at`, método `heartbeat()` e método `reap_expired_leases()` que estaciona tarefas com lease expirado e avança o agendador automaticamente.
  - Testes: `test_scheduler_reaps_expired_lease_and_advances_queue` e `test_scheduler_heartbeat_extends_lease` em `workstation/tests/test_scheduler.py` (5/5 passed).

---

## 3. Descobertas Não-Antecipadas e Hardening Adicional

### Descoberta H-107: Windows Filesystem `EPERM` no `renameSync` Atômico
- **Sintoma:** Durante execução concorrente de testes no Windows (`workstation-browser-session-state`), `this.io.renameSync(temp, this.filePath)` falhava com `EPERM: operation not permitted` quando o arquivo destino estava sendo indexado ou acessado para leitura.
- **Mitigação:** Em `apps/desktop/electron/workstation-browser-session-state.ts`, adicionado tratamento de fallback para `EPERM` e `EBUSY` via `copyFileSync` + `rmSync`.
- **Validação:** Vitest do Electron executou 7 arquivos / 55 testes com 0 warnings e 0 falhas.

### Melhorias de UIX no Desktop
- **Atenção para Intervenção Humana:** `TaskRail` (`task-rail.tsx`) agora renderiza tarefas no estado `waiting-for-human` com contorno de atenção âmbar (`border-amber-500/50 bg-amber-500/10`), badge pulsante `Action Required` e atalho de ação.
- **Painel de Downloads no Hub:** `BrowserView` (`index.tsx`) agora possui botão de Downloads na barra de ferramentas e painel gaveta com exibição de progresso em tempo real e estado dos arquivos baixados.
- **TypeScript:** Typecheck estrito passou com 0 erros (`tsc --noEmit`).


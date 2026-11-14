# Relatório Técnico Integral de Sessão: Auditoria Forense da Falha na Automação do WhatsApp (Hermes Work)

## 0. Identificação e Cobertura da Sessão

- **Tema:** Investigação forense de deadlock no protocolo de admissão de mutações do navegador Electron nativo durante automação do WhatsApp Web.
- **Projeto:** `hermes-agent` (Hermes Workstation).
- **Objetivo Geral:** Diagnosticar a causa-raiz da falha operacional na sessão `20261019_004838_e48747`, onde o agente perdeu o controle do navegador após erro de referência obsoleta, e propor correções arquiteturais.
- **Período da Sessão Auditada:** 19/10/2026 (dados da sessão) a 20/10/2026 (auditoria).
- **Ambiente Técnico:** Electron/Chromium, TypeScript, Node.js, WhatsApp Web (DOM virtualizado).
- **Fontes Examinadas:**
    - Log da sessão: [teste-3-20261019.json](app://localhost/epitaxy/workstation/dogfood/dados/Sess%C3%B5es%20Hermes/teste-3-20261019.json)
    - HTMLs de referência: [WhatsApp.html](app://localhost/epitaxy/workstation/dogfood/dados/P%C3%A1ginas%20de%20sites/WhatsApp.html), [Com chat aberto - WhatsApp.html](app://localhost/epitaxy/workstation/dogfood/dados/P%C3%A1ginas%20de%20sites/Com%20chat%20aberto%20-%20WhatsApp.html)
    - Código-fonte: [workstation-browser-runtime.ts](app://localhost/epitaxy/apps/desktop/electron/workstation-browser-runtime.ts), [workstation-browser-session-state.ts](app://localhost/epitaxy/apps/desktop/electron/workstation-browser-session-state.ts)
- **Limitações:** A auditoria foi realizada em modo read-only sobre artefatos estáticos e logs. Não houve reprodução executiva em runtime Electron.
- **Grau de Confiança:** **ALTO**. A causa-raiz foi rastreada diretamente no código-fonte e correlacionada com evidências temporais e lógicas no log da sessão.

## 1. Sumário Executivo

A falha operacional que interrompeu o inventário de conversas do WhatsApp foi causada por um **deadlock lógico no protocolo de admissão de mutações** do Hermes Workstation Browser. Uma operação `browser_click` falhou na fase pré-dispatch com o erro `stale_or_unknown_ref` (referência DOM obsoleta devido à virtualização da lista de conversas), mas o sistema de persistência já havia registrado a intenção de mutação (`admitBrowserMutation`) antes da validação do elemento. Como o erro ocorreu _antes_ da execução efetiva, nenhum receipt foi gerado para reconhecer (`acknowledge: true`) a admissão pendente. Todas as operações subsequentes foram bloqueadas indefinidamente pelo fence `pendingBrowserMutation`, retornando `reconciliation_required`. O agente tentou recuperar-se com novos snapshots, mas como `browser_snapshot` é uma operação de leitura, ele não gera receipt de mutação e portanto não limpa a admissão órfã. O fallback para `browser_exec` também falhou porque o perfil do Chrome estava travado pela instância Electron nativa ainda ativa. O inventário incompleto (17 de 52 conversas) foi consequência direta do bloqueio prematuro. As correções prioritárias (P0) envolvem a limpeza automática de admissões após erros pré-dispatch seguros e a correção do mapeamento de erros.

## 2. Objetivos, Requisitos e Evolução do Escopo

- **Objetivo Original:** Realizar auditoria forense da sessão `20261019_004838_e48747` para entender por que o agente parou de funcionar após listar 17 conversas, identificar bugs no código e recomendar correções sem implementar.
- **Requisitos Funcionais Investigados:**
    - Mecanismo de referenciamento DOM (`@eN`).
    - Protocolo de admissão e reconciliação de mutações.
    - Comportamento do `inventoryScript` em listas virtualizadas.
    - Classificação e tratamento de erros do controller.
- **Mudanças de Escopo:** A investigação evoluiu de "por que o inventário está incompleto" para "por que o sistema entra em deadlock irreversível". O foco deslocou-se da lógica do agente (LLM) para a infraestrutura de persistência transacional do browser.
- **Restrições Respeitadas:** Nenhuma alteração de código foi feita; análise estritamente read-only; distinção rigorosa entre fato, hipótese e recomendação.

## 3. Linha do Tempo Técnica da Sessão

### Fase 1 — Operação Normal e Inventário Parcial

- **Contexto:** Agente inicia tarefa de levantamento de conversas não lidas no WhatsApp Web.
- **Evento:** Snapshot inicial (`msg 78968`) identifica corretamente 52 conversas não lidas e enumera 85 elementos visíveis.
- **Resultado:** Agente começa a iterar sobre a lista. Click em `@e2` (TRÁFEGO ACIRV) bem-sucedido (`msg 79051`).

### Fase 2 — Falha Pré-Dispatch e Deadlock

- **Contexto:** Agente tenta clicar em `@e22` (Informativo ACIRV) baseado no snapshot anterior.
- **Evento Crítico (1792383033):** `browser_click @e22` falha com `stale_or_unknown_ref` (`msg 78988`). O elemento foi desmontado pela virtualização do WhatsApp entre o snapshot e o click.
- **Falha Sistêmica:** O runtime já havia persistido a admissão desta operação. Como `clickRef` lançou exceção antes de gerar receipt, a admissão permaneceu pendente.
- **Bloqueio (1792383042):** Tentativa subsequente de click retorna `reconciliation_required` / `prior_operation_requires_reconciliation` (`msg 78992`).

### Fase 3 — Loop de Recuperação Ineficaz

- **Contexto:** Agente reconhece o erro e tenta fazer resnapshot.
- **Evento:** Múltiplos ciclos de `browser_snapshot` (sucesso) seguidos de `browser_click` (bloqueado).
- **Análise:** O snapshot renova as refs no DOM, mas não limpa a admissão órfã no disco. O fence de preflight continua bloqueando qualquer nova mutação.
- **Evidência:** Reasoning do agente em `msg 1307`, `1975`, `2142` mostra confusão crescente ("Still reconciliation issues").

### Fase 4 — Fallback Falho e Abandono

- **Contexto:** Após ~18 minutos de tentativas, agente muda de estratégia.
- **Evento (1792384161):** Tenta usar `browser_exec` (Browser Use CLI) como alternativa.
- **Falha:** Erro "chrome is running and has its profile locked" (`msg ~5255`). A instância Electron nativa mantém o lock do perfil, impedindo coexistência.
- **Estado Final:** Inventário parado em 17/52 itens; controle do browser perdido.

## 4. Descobertas Técnicas e Conhecimento Adquirido

### D-01: Deadlock por Admissão Órfã Pré-Dispatch

- **Descoberta:** O fluxo de `browser_click` admite a mutação em disco (`admitDurableControllerEffect`) _antes_ de validar se o elemento existe (`clickRef` → `pointScript`).
- **Evidência:** [workstation-browser-runtime.ts:2799-2808](app://localhost/epitaxy/apps/desktop/electron/workstation-browser-runtime.ts:2799) (admissão) vs. [2966](app://localhost/epitaxy/apps/desktop/electron/workstation-browser-runtime.ts:2966) (execução).
- **Consequência:** Erros de validação DOM (seguros, sem efeito colateral) deixam admissões pendentes perpétuas, pois o caminho de exceção não gera receipt nem limpa o estado.
- **Confiança:** Confirmado no código e no log.

### D-02: Virtualização Absoluta do WhatsApp Invalida Refs

- **Descoberta:** A lista de conversas usa `role="grid"` com `aria-rowcount="518"` mas renderiza apenas ~23 rows (`transform: translateY`).
- **Evidência:** [WhatsApp.html](app://localhost/epitaxy/workstation/dogfood/dados/P%C3%A1ginas%20de%20sites/WhatsApp.html) e `inventoryScript` em [workstation-browser-runtime.ts:764](app://localhost/epitaxy/apps/desktop/electron/workstation-browser-runtime.ts:764) (filtro de visibilidade).
- **Consequência:** Refs `@eN` são efêmeras por design nesta página. Qualquer delay ou scroll entre snapshot e ação causa `stale_or_unknown_ref`.

### D-03: Mapeamento de Erros Incompleto

- **Descoberta:** `normalizeWorkstationControllerError` não inclui `stale_or_unknown_ref` na condição de `STALE_REF`.
- **Evidência:** [workstation-browser-runtime.ts:354](app://localhost/epitaxy/apps/desktop/electron/workstation-browser-runtime.ts:354) lista `ref_required`, `element_unavailable`, `browser_tab_destroyed`, mas omite `stale_or_unknown_ref`.
- **Consequência:** O erro cai no default `CAPABILITY_MISSING` / `ESCALATE`, enganando o modelo sobre a natureza recuperável da falha.

### D-04: Snapshot Não É Mecanismo de Reconciliação

- **Descoberta:** `browser_snapshot` é puramente leitura e não interage com o store de admissões.
- **Evidência:** [workstation-browser-runtime.ts:3718-3838](app://localhost/epitaxy/apps/desktop/electron/workstation-browser-runtime.ts:3718) não chama `recordReceipt` nem `admitBrowserMutation`.
- **Consequência:** A intuição do modelo ("tirar foto nova para destravar") é tecnicamente inválida neste protocolo.

## 5. Decisões Técnicas e Arquiteturais

|ID|Decisão|Justificativa|Estado|
|:--|:--|:--|:--|
|DEC-01|Classificar `stale_or_unknown_ref` como erro pré-dispatch seguro|Nenhum efeito colateral ocorre se o elemento não existe/isConnected=false|Recomendada (P0)|
|DEC-02|Limpar admissão pendente no catch de erros pré-dispatch|Evita deadlock sem comprometer segurança transacional|Recomendada (P0)|
|DEC-03|Manter `browser_exec` como incompatível com Electron nativo|Lock de perfil do Chrome é limitação conhecida do Chromium|Confirmada (Documentar)|
|DEC-04|Não confiar em refs `@eN` para iteração em listas virtualizadas|Instabilidade inerente à arquitetura da página alvo|Recomendada (P1)|

## 6. Inventário de Alterações (Propostas)

Nenhuma alteração foi implementada nesta sessão. As seguintes modificações são propostas como resultado da auditoria:

- **[apps/desktop/electron/workstation-browser-runtime.ts](app://localhost/epitaxy/apps/desktop/electron/workstation-browser-runtime.ts)**
    - Envolver `clickRef`/`typeRef` em try/catch que chame `discardPendingAdmission` em caso de erro pré-dispatch.
    - Adicionar `'stale_or_unknown_ref'` à linha 354 de `normalizeWorkstationControllerError`.
- **[apps/desktop/electron/workstation-browser-session-state.ts](app://localhost/epitaxy/apps/desktop/electron/workstation-browser-session-state.ts)**
    - Implementar método `discardPendingAdmission(operationId)` para remoção segura de admissões órfãs.
    - (Opcional P1) Adicionar TTL/expiry em `findPendingBrowserMutation`.

## 7. Problemas, Bugs e Análise de Causa Raiz

### B-01: Deadlock Irrecuperável após Stale Ref

- **Sintoma:** Todas as operações de mutação retornam `reconciliation_required` indefinidamente.
- **Causa Raiz:** Admissão persistida antes da validação + ausência de cleanup no caminho de erro + ausência de TTL.
- **Evidência:** Sequência `msg 78988` (erro) → `msg 78992` (bloqueio) → `msg 1132` (snapshot ok) → `msg 1230` (bloqueio persiste).
- **Estado:** Aberto. Correção proposta em DEC-01/DEC-02.

### B-02: Inventário Incompleto de Conversas

- **Sintoma:** Agente reportou 17 conversas quando havia 52.
- **Causa Raiz:** Bloqueio B-01 ocorreu durante a iteração. Não é erro de lógica de contagem, mas interrupção prematura.
- **Estado:** Será resolvido indiretamente pela correção de B-01.

### B-03: Classificação Errônea de Erro

- **Sintoma:** Sistema recomenda `ESCALATE` para erro recuperável via resnapshot.
- **Causa Raiz:** Omissão de string literal em condição de normalização.
- **Estado:** Aberto. Correção trivial proposta.

## 8. Testes, Verificações e Evidências

|Cenário|Tipo|Status|Evidência|
|:--|:--|:--|:--|
|Admissão persiste após stale_ref|Code Review|**CONFIRMADO**|Fluxo adm→fail sem cleanup em runtime.ts|
|Snapshot não limpa admissão|Code Review|**CONFIRMADO**|Ausência de chamadas em snapshotForEntry|
|WhatsApp virtualiza lista|DOM Analysis|**CONFIRMADO**|aria-rowcount=518, ~23 rows renderizadas|
|stale_or_unknown_ref mapeado errado|Code Review|**CONFIRMADO**|Linha 354 omissa|
|Recovery loop ineficaz|Log Analysis|**CONFIRMADO**|6+ ciclos snapshot→block em teste-3.json|
|Fix funcional em runtime real|Integração|**PENDENTE**|Requer implementação e teste E2E|

## 9. Estado Final dos Artefatos

- **Repositório:** `hermes-agent`, branch `feat/d049-browser-80-20-impl-20261018` (auditada).
- **Alterações Commitadas:** Nenhuma nesta sessão de auditoria.
- **Artefatos Gerados:** Este relatório técnico.
- **Logs Analisados:** `teste-3-20261019.json` (integridade verificada).

## 10. Pendências, Riscos e Débitos Técnicos

|ID|Pendência|Prioridade|Impacto|Condição de Resolução|
|:--|:--|:--|:--|:--|
|P-01|Implementar cleanup de admissão pré-dispatch|P0|Elimina deadlock|PR mergeado com teste unitário|
|P-02|Corrigir mapeamento de stale_or_unknown_ref|P0|Melhora recovery|PR mergeado|
|P-03|Adicionar TTL em admissões pendentes|P1|Safety net contra leaks|Design aprovado|
|P-04|Criar helper de enumeração virtualizada|P1|Inventários confiáveis|Teste E2E passando|
|P-05|Documentar incompatibilidade browser_exec/Electron|P2|UX/Docs|Docs atualizadas|

## 11. Guia de Continuidade para o Próximo Agente

### 11.1. O que já está estabelecido

- A causa-raiz do deadlock é **confirmada**: admissão órfã pós-erro pré-dispatch.
- O local exato da falha é [workstation-browser-runtime.ts:2966](app://localhost/epitaxy/apps/desktop/electron/workstation-browser-runtime.ts:2966) (ponto de throw sem cleanup) e [2799](app://localhost/epitaxy/apps/desktop/electron/workstation-browser-runtime.ts:2799) (admissão prematura).
- A virtualização do WhatsApp torna refs `@eN` inerentemente instáveis; estratégias baseadas apenas em ref-click falharão eventualmente.

### 11.2. O que não deve ser repetido

- Tentar "resnapshot" como forma de limpar estado de admissão: **não funciona**.
- Tentar `browser_exec` enquanto Electron nativo estiver ativo: **falha garantida**.
- Iterar sobre lista virtualizada sem scroll programático incremental: **perda de cobertura garantida**.

### 11.3. Próximas Ações Recomendadas

1. Implementar `discardPendingAdmission` em `workstation-browser-session-state.ts`.
2. Aplicar try/catch com cleanup em `browser_click`/`browser_type` handlers.
3. Adicionar `'stale_or_unknown_ref'` ao mapeamento STALE_REF.
4. Escrever teste unitário reproduzindo: admit → stale_ref → verificar pending=null.
5. Validar em runtime real com sessão do WhatsApp.

## 12. Matriz Final de Rastreabilidade

|Objetivo|Ação Realizada|Evidência|Estado|
|:--|:--|:--|:--|
|Diagnosticar deadlock|Análise de código + log|Seções 3, 4, 7 deste relatório|✅ Concluído|
|Identificar causa-raiz|Rastreamento adm→fail|[runtime.ts:2799-2966](app://localhost/epitaxy/apps/desktop/electron/workstation-browser-runtime.ts:2799)|✅ Confirmado|
|Explicar inventário parcial|Correlação temporal|Log msg 78988 vs 52 conversas|✅ Explicado|
|Propor correções|Patches P0/P1|Seção 6 e Código Sugerido|📝 Proposto|
|Implementar correções|N/A (read-only)|Escopo da auditoria|⏳ Pendente|
|Validar em runtime|N/A (sem ambiente)|Limitação declarada|⏳ Pendente|

## 13. Avaliação Crítica da Sessão

A sessão de auditoria atingiu seu objetivo principal com alta precisão: transformou um sintoma comportamental ("agente parou") em um diagnóstico estrutural específico (deadlock por admissão órfã pré-dispatch). O maior valor produzido foi a identificação de que o problema **não é do modelo/agente**, mas da infraestrutura de persistência que viola a invariantes de atomicidade (admitir antes de validar). O esforço de investigação do DOM do WhatsApp, embora secundário, forneceu contexto crucial para entender por que o erro pré-dispatch é frequente neste alvo específico. A limitação principal foi a impossibilidade de validação executiva; as correções propostas são logicamente sólidas mas carecem de prova empírica em runtime. Recomenda-se que a próxima fase priorize testes unitários que simulem o ciclo de admissão/falha antes de partir para integração complexa.
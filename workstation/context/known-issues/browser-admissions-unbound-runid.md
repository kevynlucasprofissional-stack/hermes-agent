# Known Issue: 200 Admissões Pendentes com runId=unbound Bloqueiam /v1/action

**Data:** 2026-10-23
**Componente:** Hermes Workstation Browser Runtime (`browser-session.json`)
**Severidade:** Alta — bloqueia todas as ações do browser (inclusive read-only)
**Status:** Aberto — limpeza programática aplicada; causa raiz não corrigida

---

## Sintoma

O endpoint `/v1/action` do gateway HTTP do Workstation Browser expira sem resposta (timeout >10s) mesmo quando `/health` responde em ~20ms. O banner "Uncertain Browser operation for this session. Review the effect; approval never retries the mutation." aparece na UI do Hermes Desktop.

## Causa Raiz

O ledger `operationAdmissions` no arquivo `%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-session.json` acumulou **200 entradas com `outcome: null` e `runId: "unbound"`**. O fence `prior_operation_requires_reconciliation` exige que toda admissão pendente seja reconhecida antes de permitir nova ação mutante — mas como o `runId` é `"unbound"`, nenhuma sessão consegue reivindicar essas admissões, criando um deadlock permanente.

### Por que `runId=unbound`?

As ferramentas de navegador desta sessão foram chamadas fora de um run do dispatcher (`_dispatch`), então o fence `taskId + sessionId + runId` nunca fecha. Sem `runId` válido, toda mutação nasce incerta e fica presa no ledger.

### Distribuição das 200 Admissões Pendentes

| Ação | Contagem | % |
|------|----------|---|
| `browser_navigate` | 110 | 55% |
| `browser_click` | 42 | 21% |
| `browser_type` | 25 | 12.5% |
| `browser_press` | 13 | 6.5% |
| `browser_batch_actions` | 10 | 5% |

Todas têm `runId: "unbound"` e `sessionId: "unbound"`.

### Origens Identificadas

1. **Sessões de automação WhatsApp (task IDs reais):** `20261022_093453_680883`, `20261022_154016_e84982` — operações legítimas despachadas sem `runId` válido.
2. **Fixtures de teste vazando para produção:** `task-batch-1`, `task-batch-bad`, `task-batch-human`, `task-batch-oversize`, `proof-negative`, `proof-no-effect` — IDs de suíte de testes que persistiram no ledger de produção.
3. **Reloads de escape:** Cada `browser_navigate` usado para escapar do `confirm()` nativo do Chromium gerou uma admissão nova (110 navegações no total).

## Impacto

- **Bloqueio total:** Nenhuma ação (mutante ou read-only) pode ser executada via `/v1/action`.
- **UI poluída:** Banner de reconciliação aparece repetidamente.
- **Automação parada:** Campanhas WhatsApp e testes E2E não podem prosseguir.

## Mitigação Aplicada (2026-10-23)

1. **Backup criado:** `%LOCALAPPDATA%\HermesWorkstation\Runtime\backups\browser-session-20261023-001902.json` (103 KB).
2. **Limpeza programática:** Campo `operationAdmissions` zerado via script Python.
3. **Verificação pós-limpeza:** `/v1/action` voltou a responder.

## Correção Definitiva (Pendente)

Para evitar recorrência, as seguintes mudanças são necessárias no runtime do Workstation Browser:

1. **Rejeitar admissões pré-dispatch com `runId` vazio:** Se uma operação não tem `runId` válido, gravar terminal `STALE_OR_UNKNOWN_REF` via `recordPreEffectTerminal` em vez de criar admissão fantasma.
2. **Isolar fixtures de teste:** Admissões de testes unitários/E2E devem usar um namespace separado ou serem limpas automaticamente após execução.
3. **TTL para admissões órfãs:** Admissões com `runId=unbound` devem expirar após N segundos/minutos, já que nenhuma sessão poderá reivindicá-las.
4. **Readback automático para reads:** Operações puramente read-only (`browser_console`, `browser_snapshot`) não deveriam gerar admissões pendentes que bloqueiam mutações subsequentes.

## Referências

- Arquivo afetado: `%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-session.json`
- Backup: `%LOCALAPPDATA%\HermesWorkstation\Runtime\backups\browser-session-20261023-001902.json`
- Código do dispatcher: `tools/browser_workstation.py` (função `_dispatch`, linha ~1040)
- Skill relacionada: `/hermes-work-control`
- Relatório da campanha WhatsApp (contexto): sessão anterior, 2026-10-22

---

## Atualização vinculada — 2026-10-28: admissão órfã de lote em sessão reutilizada

**Status:** incidente com evidência persistida; correção de runtime não aplicada. Os totais abaixo são fotografias históricas, não números em tempo real.

**Caso após reinício.** Sessão/BrowserTask/Run `20261027_102556_e828a7`, `kanbanCardId` vazio, status `parked`. Admissão pai `op_browser_batch_actions_b5c57ae46709`, ação `browser_batch_actions`, sem ACK ou terminal. Último comprovante `op_browser_batch_actions_b5c57ae46709:0`, ação `browser_click`, mesma tarefa, sessão, run e aba, URL sanitizada `https://web.whatsapp.com/`. Snapshot de 28/10 às 01:34:41Z: 258 admissões, 234 `runId=unbound`, 20 sem ACK/terminal; inspeção anterior encontrou 24 — há possibilidade de atualizações por outros processos.

**Código observado.** `apps/desktop/electron/workstation-browser-session-state.ts`: `pendingBrowserMutation`/`findPendingBrowserMutation` bloqueiam mutações da mesma tripla `taskId/sessionId/runId`; `save` (linhas aprox. 997–1007) só marca ACK quando o comprovante tem o mesmo `operationId`, `action`, `taskId`, `tabId` e run compatível. `apps/desktop/electron/workstation-browser-runtime.ts`: `browser_batch_actions` registra comprovantes de subetapa `parent:index`, com ação `browser_<kind>`. Assim, o último comprovante filial não corresponde à admissão pai. A confirmação de uma etapa não certifica a execução global do lote; o fence existe para evitar repetir efeitos externos incertos.

**Escopo do nexo causal.** O cenário da UI e a resposta prefab são compatíveis com falta de confirmação final. A identidade do handoff autenticado e a execução real das últimas tentativas não foram lidas/reproduzidas. `workstation/prefabs/integration.py`/`engine.py` exigem navegação seguida de snapshot independente. `workstation/integrations/hermes/scoped_execution.py` pode consultar Kanban, mas a sessão afetada não tinha `kanbanCardId`. Não atribuir o defeito ao Kanban upstream nem reverter seu código.

**Solução sob validação.** Aproveitar `BrowserSessionStateFilePersistence.reconcilePendingAdmission` e os comandos nativos `browser_admissions_inspect`/`browser_admissions_reconcile`; não criar outra autoridade. Para lote `verified`, avaliar comprovante pai causal persistido após todas as etapas verificadas, mantendo as evidências filhas e separando ACK de pós-condição externa. Para `uncertain/rejected`, manter bloqueio até prova pré-efeito válida ou reconciliação humana fundamentada em readback. Nunca limpar o ledger às cegas, repetir envio WhatsApp, desabilitar ownership ou habilitar CDP automaticamente.

**Baseline de testes durante o planejamento.** Em `apps/desktop`, `vitest run --project electron electron/workstation-browser-batch.test.ts electron/workstation-browser-runtime-batch.test.ts electron/workstation-browser-session-state.test.ts --reporter=dot`: 21 PASS / 12 FAIL (33). As 12 falhas são do `workstation-browser-runtime-batch.test.ts`, por mock Electron incompleto (`TypeError: app.getAppPath is not a function`, runtime linha 1502), antes de provar a função de lote. As outras duas suítes passaram. Testes usam mocks e diretórios temporários; nenhum envio WhatsApp real.

**Governança.** Checkout no preflight `main@f1d5ab2f03`, 196 entradas dirty. Os docs canônicos `CURRENT_STATE.md`, `KNOWN_ISSUES.md`, `DECISIONS.md`, `ROADMAP.md`, `engineering-journal/CURRENT.md` estavam modificados e reivindicados por `whatsapp-m3`; não sobrescrever. A dispensa histórica Stage A de WA-M3 não autoriza automaticamente patch de Browser nesta missão. Plano de implementação e prompts: `workstation/context/BROWSER_BATCH_RECONCILIATION_PLAN_20261028.md`.

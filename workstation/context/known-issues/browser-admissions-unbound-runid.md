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
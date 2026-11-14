# P01 — autorização explícita e execução local (2026-10-28 UTC)

**Autorização do mantenedor nesta sessão:** "Nessa sessão autorizo a pular o stage A, não vamos trabalhar com isso por enquanto. Pode continuar o trabalho com o Stage A pulado." Escopo único: P01 fechamento causal de `browser_batch_actions` no Hermes Work; dispensa de upstream-pin/sync/Stage A para **desenvolvimento local**, NÃO equivale a baseline verde, CI qualificada, E2E ou release. Não reverter Kanban upstream, nem fazer Git branch/worktree/commit/push.

Checkout pré-implementação: `C:\Github\hermes-agent` `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`, 199 entradas dirty. Runtime já alterado por terceiros (113 inserções/11 remoções): preservar diferenças. Claims exclusivos adquiridos para runtime, session-state, runtime-batch fixture, batch-p01 regression, e este documento por `chatgpt-browser-batch-p01-20261028`. Docs canônicos CURRENT_STATE e engineering-journal/CURRENT reivindicados por `whatsapp-m3`; a integração da dispensa nesses documentos aguarda handoff e não será forçada.

Baseline pré-patch da sessão anterior: 21 pass / 12 fail (fixture `app.getAppPath` ausente). Nenhum perfil real/WhatsApp usado em testes.

Status desta nota: preparar e validar implementação local; não promover release sem qualificação distinta.


## Implementação local — evidências efetivas

- Reprodutor RED isolado em `apps/desktop/electron/workstation-browser-runtime-batch.test.ts`: lote de duas etapas retornava `verified`, mas `operationAdmissions['op-p01-batch'].acknowledged` permanecia `undefined`. Falhou na asserção de ACK pai antes da correção, sem disparo remoto.
- Fixture Electron reparado em `workstation-browser-runtime-batch.test.ts`: `app.getAppPath`, `webContents.ipc.on`, distinção do inventário DOM em relação ao script de seleção/geometry. Suíte baseline inicial: 21 PASS/12 FAIL (mock). Após reparo, 12/12 no runtime batch antes da correção pai.
- `apps/desktop/electron/workstation-browser-runtime.ts`: identidade `operationId` e `runId` de batch passa a usar admissão canônica; `checkpoint` exige persistência estrita em vez do helper que silencia falhas; com `batchResult.status==='verified'` e todos os steps verificados, revalida owner/lease/run/session/tab/documento, grava recibo PAI no store existente, preserva child refs e atualiza `BrowserTask` e `lastReceipts`. Qualquer falha retorna `uncertain` e não reexecuta effects.
- `apps/desktop/electron/workstation-browser-session-state.ts`: `saveSessionDurably` e `completeVerifiedBatch` usam o lock canônico. Para lote verified, valida exatamente IDs da admissão, última prova infantil e refs sequenciais `parent:index:tab:revision` (máximo 20). Grava recibo pai e `batchStepReceiptRefs` no próprio admission; `save` reconhece ACK pela correspondência estrita. `fsync` ocorre no arquivo TEMP **antes** da substituição atômica; falha não publica ACK pai. Escritor com snapshot antigo não consegue apagar as child refs. Sem nova store/autoridade.
- Não tocamos em Kanban upstream nem no ledger vivo `%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-session.json`. Toda suíte usa pastas temporárias. Não abrimos WhatsApp real, não enviamos mensagens, não iniciamos Electron real, não habilitamos CDP.

## Validação (27/10, horário local do Windows; 28/10 UTC)

- **RED → GREEN específico:** `vitest run --project electron electron/workstation-browser-runtime-batch.test.ts --testNamePattern='P01 RED'`: primeiro FAIL por ausência de ACK pai; após correção 1/1 PASS; nova instância lê ACK e nova navegação não retorna `prior_operation_requires_reconciliation`.
- **Suítes focadas finais:** de `apps/desktop`, `vitest run --project electron electron/workstation-browser-batch-p01.test.ts electron/workstation-browser-batch.test.ts electron/workstation-browser-runtime-batch.test.ts electron/workstation-browser-session-state.test.ts electron/workstation-browser-runtime-admission.test.ts electron/workstation-browser-runtime-recovery.test.ts --reporter=dot`: **45 PASS / 0 FAIL / 6 arquivos**. Inclui partial/uncertain, takeover humano, documento trocado, owner receipts, checkpoint falho, replay, identidade run/tab divergente, fsync falho, corrupção e lock concorrente, preservação de refs após gravação stale.
- `tsc -p tsconfig.electron.json --noEmit`: **EXIT=0**.
- `eslint electron/workstation-browser-runtime.ts electron/workstation-browser-session-state.ts electron/workstation-browser-runtime-batch.test.ts electron/workstation-browser-batch-p01.test.ts --quiet`: **EXIT=0**. Lint normal inicialmente havia apenas avisos de espaçamento e 2 erros de organização de imports no teste novo; imports corrigidos. A verificação final no modo quiet não apresenta erros; avisos não foram todos eliminados por existirem em trechos pré-existentes.
- `git diff --check` nos três arquivos rastreados modificados: **EXIT=0**.
- Checkout no fechamento: `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`, **203 entradas dirty** no repositório compartilhado. P01 modificou `workstation-browser-runtime.ts` (com diferenças anteriores de terceiros preservadas), `workstation-browser-session-state.ts` e `workstation-browser-runtime-batch.test.ts`, além de novo `workstation-browser-batch-p01.test.ts` e este registro.

## Ressalvas e gates que permanecem abertos

- Dispensa de Stage A foi autorizada **nesta sessão e apenas para desenvolvimento local P01**; não equivale à qualificação upstream nem a CI exata, release, merge ou PR.
- Não houve E2E nativo autenticado do cenário real depois de restart/WhatsApp, nem falha física de energia/disco. Os testes de fsync são sintéticos e demonstram rejeição antes de publicar o ACK, não certificação de garantia física da plataforma/filesystem.
- O ledger de produção ainda pode ter admissions antigas pendentes, inclusive `op_browser_batch_actions_b5c57ae46709`. O patch não e não deve reconciliá-las automaticamente: sem readback causal não há prova de que lote antigo terminou.
- Docs canônicos `workstation/context/CURRENT_STATE.md` e `engineering-journal/CURRENT.md`, bem como `KNOWN_ISSUES.md`, `DECISIONS.md`, `ROADMAP.md`, seguem sob claim `whatsapp-m3`; **handoff documental pendente**. O plano e known issue detalhado estão sob claim `browser-batch-plan-20261028`, portanto não sobrescritos.
- Nenhum commit/push/branch/worktree criado e nenhum PR conhecido/verificado nesta sessão. Requalificação Stage A e CI exata ficam pendentes para eventual release.

## Handoff e próximo gate prioritário

P01 foi implementado e qualificado **localmente**; a próxima missão é P2 de recuperação/restauração de sessão antiga e readback nativo autenticado em perfil temporário, sem WhatsApp real, mantendo efeito incerto bloqueado. Confrontar a atualização do programa com detentores dos claims canônicos e executar a validação de release separadamente. Se uma próxima sessão retomar, verificar HEAD/status/claims e ler **este registro** e `BROWSER_BATCH_RECONCILIATION_PLAN_20261028.md` antes de escrever; não reinvestigar do início.

# Auditoria independente do Browser — ledger, versão ativa e reconciliação (07/11/2026)

## Escopo / coordenação
P1 auditoria de admissões, P0 verificação **passiva** do bundle carregável e P2 investigação de reconciliação com testes isolados. Frente separada do outro chat que opera Database, Cron, Trello, SQLite e AI Control. Nenhuma ação foi disparada no Browser ativo, nenhum clique, reset, retry, reconcile, commit, stash, restart ou limpeza. Arquivo novo e exclusivo deste diagnóstico; `CURRENT.md`, roadmap, dataset edits e Cron intocados.

Checkout observado: `C:\Github\hermes-agent`, branch `main`, HEAD `f1d5ab2f03`, 372 entradas dirty no início, zero staged. Ledger de produção SOMENTE LIDO em `%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-session.json`, schema com 367 admissões. Snapshot observado em 07/11/2026 por volta de 18h; `savedAt` atualizado por outra sessão enquanto transcorria a auditoria (até `2026-11-07T21:14:06.915Z`). Números são fotografia, não garantia de imutabilidade.

## P1 — 24 pendentes: classificação por identidade, vínculo e impacto
Critério usado: ausência de `acknowledged:true` e de `terminal` no registro. Nenhuma das pendências está vinculada a tab `recoveryState=live`; há 2 browser tasks em `parked`, uma vinculada à pendência `browser_navigate` abaixo, e 2 abas (uma `live`, uma `restored`).

- **19 `runId=unbound`**: nenhuma tarefa nem aba atual corresponde aos identificadores. Subclasses: 8 operações com nomes semelhantes a provas/testes (`proof` ou `batch-test`), 11 outras entradas legadas. Origem de teste é indício pelo nome, não prova; todas permanecem preservadas. Não configuram bloqueio confirmado das tarefas vivas.
- **4 runId explícitos sem tarefa/aba atual**: `op_browser_batch_actions_b5c57ae46709` (session 27/10), `op_browser_batch_actions_3d591fa7f8da` (28/10), `op_browser_batch_actions_98aa64141e5b` (28/10; `uncertainty.reason=stale_or_replaced_target`), `op_browser_click_4ce2649915d4` (02/11). Efeitos não estão provados; retenção histórica, sem alvo atual para verificação.
- **1 runId explícito com tarefa e aba restauradas**: `op_browser_navigate_15e24f092715` (session 05/11). Task `parked`, task e tab `restored`, task/run/session e tab owner consistentes. A task guarda `lastReceipt.action=browser_navigate` com o mesmo run, porém **operationId diferente**; admissão pendente sem ACK e sem diagnóstico `uncertainty`. Candidato a bloquear a PRÓXIMA mutação dessa mesma TaskRun se o owner retomá-la, NÃO prova bloqueio das abas vivas atuais. Não criar WebContents para testar: restauração pode navegar.
- Distribuição por operação: 14 `browser_batch_actions`, 6 `browser_navigate`, 4 `browser_click`. Apenas 1 das 24 contém `uncertainty` explícita; ausência de campo não prova que não houve efeito.

## P0 — versão do Electron
Processo principal `electron.exe` PID 37124 iniciado `07/11/2026 17:34:11`, com `electron .` em `apps/desktop`. `package.json` usa `dist/electron-main.mjs`; script `dev:electron` recompila TypeScript e executa `bundle-electron-main.mjs --dev` antes de iniciar Electron. Bundle existente com mtime `2026-11-07T17:34:11.2793262-03:00`, sem gravação posterior ao processo, contendo `semantic_selection_rebound_readback`, `semanticSelection` e `completeVerifiedBatch`. Fonte da correção alterada às 15:44–15:46, anterior ao início. **Forte evidência de que esta versão foi iniciada**, mas sem inspeção da memória/sessão em execução e sem teste funcional na UI ativa. Não reiniciar por suspeita de versão antiga.

## P2 — capacidade, limites de recuperação e provas
- `workstation-browser-runtime.ts::reviewUncertainBatch`: entrada nativa humana, duas verificações independentes de identidade/estado (`before/after`), revisão/lease exigidos, sem repetição de clique nem alegação de entrega. `uncertainBatchReviewCandidate` requer batch com `uncertainty`, etapas executadas sem confirmação, task/session/run/tab concordantes e leitura viva OU tab restaurada com humano, nos casos permitidos.
- `verifiedNavigationCandidate` é deliberadamente restrito a navegação local SINTÉTICA com receipt do próprio `operationId`, tab `live`, URL/owner/WebContents condizentes; não serve para fechar a navegação antiga restaurada sem receipt correspondente. Não ampliar a hosts externos nem eliminar reconciliação manual.
- `workstation-browser-session-state.ts::pendingBrowserMutation` tem recuperação automática **somente** de batch comprovadamente não despachado (`provenNeverDispatchedBatch`). **Não executar essa função sobre o ledger real para auditoria**, pois ela pode gravar um terminal automático.
- Preflight em `executeControlRequest` consulta pendência por task/session/run ANTES de criar/restaurar WebContents e retorna `reconciliation_required` se há operação anterior; logo a navegação pendente restaurada é risco MATERIAL para aquela TaskRun, sem autorizar retry.
- Regressão isolada: `cd apps/desktop && ..\..\node_modules\.bin\vitest.cmd run --project electron electron/workstation-browser-admission-p0a.test.ts electron/workstation-browser-batch-p01.test.ts electron/workstation-browser-batch-proof.test.ts electron/workstation-browser-human-review.test.ts electron/workstation-browser-uncertain-batch-review.test.ts electron/workstation-browser-ipc-human-review.test.ts electron/workstation-browser-runtime-admission.test.ts electron/workstation-browser-runtime-batch.test.ts electron/workstation-browser-session-state.test.ts --reporter=dot`. **9/9 suítes, 91/91 testes, exit 0.** Logs de stderr do mock incluem falha esperada `session.fromPath is not a function` em teste de start controller; nenhuma suíte falhou. Não há RED novo que justifique patch.

## Decisão operacional / próximos passos
1. P1: **não limpar** as 24 admissões, não tratar `unbound` como falha da sessão atual. Preservar a única TaskRun restaurada e sua admissão; se houver demanda real para retomá-la, obter confirmação explícita do owner e evidências seguras para revisão humana, em janela coordenada. Não emitir mutação de teste no Browser real.
2. P0: registrar a correção como **presente no bundle do Electron atual**, com ressalva de que uso pela sessão ativa não foi exercitado. Sem reboot.
3. P2: manter proteção atual. Os limites são intencionais; não automatizar liberação de efeitos incertos, mensagens externas ou clicks. Patch somente com reprodução RED isolada de caso concreto.
4. P3: trabalho delegado: Database, Trello, Cron, proteção SQLite e AI Control pertencem ao outro chat. Não iniciar agendador alternativo nem acessar lease System1.
5. Nenhum novo incidente bloqueante generalizado confirmado. A única pendência potencialmente operacional é a navegação da TaskRun restaurada. Validar apenas em janela e sessão explicitamente coordenadas.

**Limite**: classificação feita sobre snapshot persistente, não sobre memória/lease de cada sessão nem sobre efeitos remotos. O ledger mudou durante o trabalho por atividade externa; este diagnóstico não substitui validação no momento de uma recuperação futura.

## Protocolo de coordenação da tarefa restaurada — HOLD condicionado (07/11/2026)

**Decisão atual:** não retomar, reconciliar, reexecutar nem alterar a operação `op_browser_navigate_15e24f092715`. Esta é uma pendência de navegação associada a uma TaskRun `parked/restored`; não há prova atual de efeito nem bloqueio generalizado. A revisão **não está agendada nem iniciada**.

**Gatilho legítimo:** o usuário ou o agente responsável pelo fluxo Browser/System1 declarar necessidade concreta de **retomar essa mesma TaskRun** e confirmar um bloqueio atual atribuível à admissão. Não antecipar com base apenas na existência da entrada; não monitorar/reabrir tarefas nem acionar a sessão alheia automaticamente.

**Handoff entre frentes:** o chat responsável por Database/Trello/Cron e pela sessão System1 continua dono da operação ativa e de seus leases. Esta frente de confiabilidade fornece somente diagnóstico e evidências; não executa ações concorrentes. Antes de qualquer revisão, obter acordo explícito sobre owner, TaskRun, janela de execução e ausência de operação incerta em andamento. Sem coordenação disponível, **HOLD**.

**Rechecagem somente leitura na janela combinada:**
1. Confirmar `taskId/sessionId/runId/tabId/operationId`, status, lease e revisões a partir de snapshot atual e fonte autoritativa, sem mutar ledger ou recriar WebContents.
2. Verificar se o bloqueio ainda existe para a mesma identidade; comparar o último recibo com `operationId` e efeito esperado. Recibo de outra operação não resolve.
3. Conferir as condições de `verifiedNavigationCandidate`: página `live`, recibo causal correspondente, navegação **sintética/local** e readback independente. Não inferir prova de URL/DOM histórico ou de operação externa.
4. Se esses critérios faltarem, manter `reconciliation_required`; eventual liberação deve ocorrer somente pelo diálogo humano nativo autorizado, com confirmações e revalidação before/after, sem retries cegos.
5. Registrar decisão e evidência na frente proprietária. Nenhum patch ou cleanup automático do legado por conveniência.

**Critério de encerramento:** somente após a retomada autorizada, evidência causal e verificação de que a operação seguinte permitida funciona sem efeito duplicado. Se a tarefa não precisar ser retomada, a pendência permanece preservada como histórico. Não houve teste da sessão ativa, nenhuma reconciliação ou interação com a ponte AI Control nesta etapa.

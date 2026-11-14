# Hermes Native Browser Reliability — Relatório canônico

Data de execução: **29/10/2026**. Missão: persistência, foco independente, ownership e reconciliação autenticada. **Estado: BLOCKED — EXTERNAL DEPENDENCY OR AUTHORIZATION** para novas edições do runtime e E2E nativo; testes e diagnóstico isolados executados. Este documento foi criado sem modificar os arquivos de implementação ou o ledger.

## Preflight verificável (29/10)

- Máquina: `DESKTOP-3NA47UH`; repositório: `C:\Github\hermes-agent`; branch `main`; HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`.
- Git inicial: **230 entradas dirty**, staging 0; muitos arquivos da implementação Browser já estão modificados por WIP anterior. Nenhuma branch/worktree/commit/push/reset/stash/clean desta sessão.
- Referência local `upstream/main`: `571a5911ae6aaa05ef3df53bf0f6720c4556c24a`; `merge-base`: `3b63f7b0a4c7beb9eadbce2f15b9da75d01f5065`; divergência **6574 commits atrás, 1349 à frente**. Não foi realizado `git fetch`: referência upstream não comprovada como atual.
- A dispensa de Stage A registrada no `CURRENT_STATE.md` e diário é **de 28/10**, não 29/10. `UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md` exige pin/baseline qualificado, integração e gates exatos antes de novo patch. A missão proíbe criar branch; portanto o Stage A não foi qualificado nem ignorado. **Nenhum patch de runtime** nesta sessão.
- AI Control: `endpoint unavailable`. Descritor `%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-control.json`: PID **28720**, processo **morto** no preflight. Inventário final de processos `Hermes|electron`: nenhuma correspondência; apenas processos de agentes Codex no preflight. Sem instância de Hermes para E2E real. Não iniciar/reiniciar aplicativo roubando o foco.
- Ledger real `browser-session.json`: somente leitura; timestamp 28/10 17:43:17; operação `op_browser_batch_actions_3d591fa7f8da` ainda presente, sem ACK e sem terminal. Nenhuma reconciliação real ou replay.

## Mapa da cadeia de controle e falhas confirmadas

`Sessão Hermes -> Agent Tool -> tools/browser_workstation.py::_request_json -> _read_control -> browser-control.json -> HTTP loopback autenticado -> workstation-browser-runtime.ts::executeControlRequest -> BrowserTask/WebContents -> CDP interno/DOM -> readback -> receipts -> session-state -> TaskRun/Kanban.`

Fronteira descoberta/cliente: `tools/browser_workstation.py::_request_json` lê descritor antes de cada operação; erro de `URLError/OSError` resulta em `Hermes Browser controller connection failed`, sem redescoberta/retry seguro de leitura no ramo de conexão. `workstation_controller_available` faz health com cache, mas não restaura o runtime ausente.

Fronteira Electron: `workstation-browser-runtime.ts` já inclui watchdog de 1s, republicação do descritor e relisten do mesmo servidor `http.Server`, preservando token e BrowserTask. `workstationBasePath` isola Vitest; foco em attach/activate condicionado à janela hospedeira focada. O executor usa CDP **interno ao WebContents**, não entrada global.

Fronteira admissão: `shouldDeferRestoredNavigation` inspeciona somente `browser_navigate`; batch posterior incerto não necessariamente adia restauração de URL. `browser_admissions_reconcile` recebe e confia em `OPERATOR_REVIEW`/resolved_by declarados pela ferramenta do agente; a autoridade humana real não está provada. Mutação sem task/session/run pode gerar admissão `unbound`.

Fronteira Kanban: `workstation/contracts.py::AcceptanceEvaluator` exige status verificado, pendências resolvidas e evidências; isso é **diferente** de `prior_operation_requires_reconciliation`. Nunca falsear `VERIFIED_COMPLETED` ou apagar fence por conta do aviso de UI.

## Evidência nova: 20 ciclos isolados

Harness revisado em `%TEMP%\hermes-browser-20-cycles-isolated.cjs`, derivado de fixture do repositório, com `HERMES_HOME` e `HERMES_WORKSTATION_HOME` em diretório temporário descartável. Não abre URLs externas nem utiliza perfil produtivo. Foram **20/20 PASS**: 10 descritores obsoletos e 10 listeners encerrados, cada um com readback de PID/URL/token e GET `/health` autenticado. `min=878ms`, `p50=1090ms`, `p95=1099ms`, `max=1099ms`; todas as recuperações abaixo de 10s; 0 navegações externas. Encerramento voluntário verificado sem relisten indevido. **Prova sintética**, não E2E Chromium real ou recuperação de crash do processo Electron.

## Regressões e RED adversariais (29/10)

- Electron: `cd apps/desktop; ..\..\node_modules\.bin\vitest.cmd run --project electron electron/workstation-browser-runtime-task.test.ts electron/workstation-browser-runtime-admission.test.ts electron/workstation-browser-runtime-batch.test.ts electron/workstation-browser-batch.test.ts electron/workstation-browser-batch-proof.test.ts electron/workstation-browser-session-state.test.ts --reporter=dot` => **94/94 PASS**, 6 arquivos, exit 0; hash do descritor de produção inalterado.
- Python: `.venv\Scripts\python.exe -m pytest tests/tools/test_browser_batch_semantic_contract.py tests/tools/test_whatsapp_browser_tools.py -q` => **35/35 PASS**, exit 0.
- Handoff/Python: `.venv\Scripts\python.exe -m pytest workstation/tests/test_p0_native_handoff_review_api.py workstation/tests/prefabs/test_prefabs.py -q` => **29 PASS + 14 subtests**, exit 0.
- UI: `cd apps/desktop; ..\..\node_modules\.bin\vitest.cmd run --project ui src/app/chat/right-rail/workstation-browser-pane.test.tsx --reporter=dot` => **3/3 PASS**, exit 0; avisos não fatais React `act`/localStorage.
- Electron `tsc -p tsconfig.electron.json --noEmit` => **exit 0**.
- Testes adversariais 29/10, **somente perfis temporários**: (1) `hermes-p02-restart-integrated-v2.cjs` confirmou `P02_INTEGRATED_RED=REPRODUCED`, URL histórica implicitamente recarregada apesar de batch pendente; (2) `hermes-p02-reconcile-forgery-red.cjs` confirmou `accepted:true`, terminal sintético `RECONCILED` com `resolvedBy:agent`, exit 2 de asserção RED esperada; (3) `hermes-p02-unbound-runid-red.cjs` confirmou nova admissão `runId:unbound`, exit 2 de asserção RED esperada. O wrapper final de PowerShell gerou erro próprio porque capturou stdout junto aos exit codes: **não contar esse wrapper como teste verde**; os três resultados individuais têm evidência de saída explícita.
- **Nenhuma implementação de P02/autorização/unbound aplicada hoje**, nenhum E2E de Chromium nativo/WhatsApp real, nenhum build de distribuição ou CI exato.

## Critérios de aceite AC-01 a AC-24

Estados são **PASS, FAIL ou BLOCKED**; PASS restrito à evidência indicada, sem extrapolar para o produto.

| AC | Estado | Evidência atual e próximo gate |
|---|---|---|
| AC-01 | FAIL | Descritor aponta PID 28720 morto; sem Controller autenticado ativo no host. Exigir app vivo e /health com owner correto. |
| AC-02 | PASS | Watchdog reparou 10/10 descritores em testes isolados; repetir na instância nativa. |
| AC-03 | BLOCKED | Relisten 10/10 no HTTP mockado com classe runtime real; falta teste Electron/Chromium nativo isolado. |
| AC-04 | PASS | 94 regressões Electron preservaram hash do descritor produtivo. |
| AC-05 | BLOCKED | Testes de identidade/ownership sintéticos prévios; falta cenário nativo attach/detach/sessões. |
| AC-06 | BLOCKED | Click de WebContents sem foco testado com mock; falta readback E2E nativo. |
| AC-07 | BLOCKED | Falta prova de type dirigido ao DOM correto sem foreground. |
| AC-08 | BLOCKED | Falta matriz press/scroll/snapshot foreground/background/minimizado. |
| AC-09 | BLOCKED | Esta sessão não enviou input global; falta instrumentação de não interferência e prova E2E. |
| AC-10 | BLOCKED | Mecanismo de lease existente, ainda sem matriz de concorrência humano/agente nativa. |
| AC-11 | BLOCKED | Regressões de idempotência mockadas; falta prova integrada de crash entre dispatch/ACK. |
| AC-12 | FAIL | Não há via de reconciliação humana comprovadamente autenticada e causal. |
| AC-13 | FAIL | RED atual permite forja `OPERATOR_REVIEW` por ferramenta do agente em perfil sintético. |
| AC-14 | BLOCKED | P01/BROW-N2 presentes, recuperação de batch parcial/crash não homologada. |
| AC-15 | BLOCKED | Isolamento sintético existe; conferir bloqueio real por tab/task/run em E2E. |
| AC-16 | BLOCKED | 3 testes UI e 29 handoff PASS; ainda falta integração conclusiva de evidências/TaskRun/Kanban. |
| AC-17 | BLOCKED | Cliente Python não redescobre/retry leitura após indisponibilidade; implementar após gate. |
| AC-18 | BLOCKED | Fence de operação histórica mantido; falta testes crash/recovery com ledger isolado. |
| AC-19 | PASS | 20/20 ciclos sintéticos; p95 1099 ms, máximo 1099 ms, zero efeitos externos. |
| AC-20 | BLOCKED | Hermes/AI Control não estão em execução; sem dogfooding agente→Chromium. |
| AC-21 | PASS | Suítes-alvo atuais Electron 94, Python 35+29, UI 3 e TypeScript 0 erros. Não qualifica suíte total. |
| AC-22 | BLOCKED | Build de release, native E2E e CI exato não realizados. |
| AC-23 | BLOCKED | Nenhum patch novo de runtime hoje; documentação e consistência de solução final ainda pendentes. |
| AC-24 | PASS | Leitura mostrou operação histórica presente, não ACK, sem terminal. Nenhuma modificação de ledger pela sessão. |

## Prioridade técnica quando gate e Hermes real estiverem disponíveis

1. Qualificar Stage A no workflow aprovado (sem alterar branch compartilhada sem autorização) **ou** obter dispensa explícita datada de 29/10 para escopo desta missão, registrar nos dois documentos canônicos, coordenar escritores antes de alterar arquivos WIP.
2. Restaurar disponibilidade de uma instância **real** do Hermes pelo operador; habilitar AI Control na interface, sem teclado/mouse global; confirmar controller owner, token nunca exposto, /health e cadeia agent tool. Não tomar uma sessão em curso.
3. Corrigir primeiro com RED/GREEN os defeitos de segurança: remover capacidade `browser_admissions_reconcile` de qualquer canal que a LLM controla; manter inspect read-only e projetar revisão humana separada com autorização real, readback causal, escopo e transação; corrigir P02 restore que ignora batch incerto. Testar preservação de fences e sem replay.
4. Corrigir pré-dispatch de novas admissões sem identidade canônica, mantendo sessões legítimas não-Kanban e históricos intactos. Cliente `_request_json`: retry **uma única vez em leitura** após redescoberta autenticada, quando falha ocorre antes de retorno; nunca retry de mutações incertas. Testes RED que distinguem GET de POST.
5. E2E nativo isolado com página sintética para todas as ações/foco/leases, sem manipulação global de input. Testar em Windows foreground/background/minimized com intervenção manual do operador para mudar foco quando exigida.
6. Completar AC restantes, gates CI/build/observabilidade, relatório e novo Resume Prompt até atingir critérios.

**Proteções permanentes:** operação histórica `op_browser_batch_actions_3d591fa7f8da` estritamente somente leitura; não enviar WhatsApp real; não suprimir fences; não usar CDP externo; não modificar automaticamente Git histórico; nunca usar mouse ou teclado global; manter WIP de terceiros.

---

# Continuidade 29/10/2026 — Stage A dispensado, patches P0/P1 locais

**Autoridade registrada:** mantenedor dispensou Stage A para todas as implementações de 29/10/2026, registrada no topo de `workstation/context/CURRENT_STATE.md` e `workstation/context/engineering-journal/CURRENT.md`. Não autoriza release, ações externas, conflitos entre agentes ou alteração do ledger real.

**Preflight atual:** `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`, 231 dirty na entrada, staging 0, agentes Codex ativos. Na última verificação 232 dirty, estágio 0; arquivo de teste Python novo (não rastreado). Não criar branch/commit/push/worktree; preservar WIP anterior.

## Alterações aplicadas nesta continuidade

1. `apps/desktop/electron/workstation-browser-runtime.ts`: o ramo agent-accessible `browser_admissions_reconcile` rejeita `agent_reconciliation_forbidden` antes de chegar a `reconcilePendingAdmission()`. A rota de inspeção `browser_admissions_inspect` continua read-only. **Revisão humana autenticada ainda não foi implementada** e não há liberação automática.
2. Mesmo arquivo: validação pré-dispatch de mutações sem task/run/session em identidade `default` para impedir novas admissões `runId=unbound`; caminhos com `task_id` explícito preservados. Não modifica `unbound` históricos.
3. Mesmo arquivo: `shouldDeferRestoredNavigation` adia carregamento implícito da URL quando há admission pendente **da mesma BrowserTask e mesma aba**, independentemente da antiguidade da navigation ACK. Fail-closed em metadados de run/session legados; preserva fence e exige navegação futura autorizada.
4. `apps/desktop/electron/workstation-browser-runtime-admission.test.ts`: testes TDD integrados RED→GREEN para os dois primeiros e para P02 restart com contador de URLs realmente chamadas pelo `FakeWebContents`. 9/9 em suite focal. Não usar navegação real WhatsApp para esses testes.
5. `tools/browser_workstation.py::_request_json`: redescoberta limitada a **um retry** exclusivamente para `GET /health` e `GET /resources` após erro de conexão, somente quando o descritor autenticado mudou. Não tentar novamente `POST /control` nem operações de estado incerto. `tests/tools/test_browser_controller_readonly_recovery.py` com RED→GREEN (2/2), inclusive teste adversarial sem retry de clique.
6. `apps/desktop/electron/workstation-browser-runtime-recovery.test.ts`: o FakeBrowserWindow passou a implementar `isFocused()` conforme a API real do Electron; regressão inicial falhou por mock incompleto e segunda execução passou sem modificar foco do Windows.

## Testes e provas reais desta continuidade

- Três REDs integrados Electron demonstraram: forja de revisão `Missing expected rejection`, mutação sem identidade `Missing expected rejection`, e recarga implícita de `https://example.com/previous` em snapshot após batch incerto. Todos receberam GREEN após patch.
- Nove suítes Electron: **115/115 PASS**, exit 0, após corrigir mock `isFocused`; uma execução intermediária registrou 114 PASS/1 FAIL, causada exclusivamente pelo mock.
- Python: **66/66 PASS + 14 subtestes**, exit 0 (contratos Browser, WhatsApp sintético, handoff/prefabs, cliente read-only).
- `tsc -p apps/desktop/tsconfig.electron.json --noEmit`: exit 0.
- `git diff --check` nos arquivos alterados: exit 0.
- `node apps/desktop/scripts/bundle-electron-main.mjs --dev`: exit 0; bundle `apps/desktop/dist/electron-main.mjs` gerado.
- Hermes real foi aberto pelo operador com **AI Control true**. Controller descriptor PID **9896**, processo vivo. `tools.browser_workstation._request_json('GET','/health')`: **success True**, runtime `electron-chromium`, uma aba, `paused:false`, nenhum `lastError`. `GET /resources`: success True, três recursos; nenhuma mensagem, clique ou mutação produtiva.
- A instância aberta pode estar executando o bundle anterior à compilação. Não houve hot-reload/restart operacional e **nenhum E2E de BrowserTask real, segundo plano ou WhatsApp**. Não declarar AC-20 concluído.
- Ledger produtivo: operação `op_browser_batch_actions_3d591fa7f8da` ainda presente em snapshot 29/10 12:34:01, **ACK false e terminal ausente**. Nenhuma ação de reconciliação/replay.

## Atualização AC-01 a AC-24 (29/10, pós-patches)

| AC | Estado | Evidência e próxima condição |
|---|---|---|
| AC-01 | PASS | PID 9896 vivo, GET health autenticado, runtime Electron Chromium; verificar após restart com novo bundle |
| AC-02 | PASS | Testes isolados anteriores de recuperação de descritor 10/10 |
| AC-03 | BLOCKED | Relisten HTTP sintético 10/10, ainda não E2E nativo isolado |
| AC-04 | PASS | Isolamento Vitest, descritor produtivo preservado nos ensaios anteriores |
| AC-05 | BLOCKED | Identidade/attach/switch exigem E2E múltiplas sessões |
| AC-06 | BLOCKED | Clique sem OS focus somente mockado |
| AC-07 | BLOCKED | Digitação sem foreground ainda sem E2E |
| AC-08 | BLOCKED | Matriz press/scroll/snapshot foreground/background/minimizado |
| AC-09 | BLOCKED | Sem ação global nesta sessão; falta instrumentação nativa |
| AC-10 | BLOCKED | Leases e arbitragem humana nativa |
| AC-11 | BLOCKED | Replay pós-crash nativo, teste de persistência real isolado |
| AC-12 | FAIL | Hand-off review já autenticado, mas não tem transação causal reconciliadora integrada |
| AC-13 | PASS | Forja agent-only negada em teste integrado; read-only inspect preservado |
| AC-14 | BLOCKED | Batch parcial crash/recovery sem E2E |
| AC-15 | BLOCKED | Isolamento entre BrowserTasks e sessões sem E2E |
| AC-16 | BLOCKED | UI/handoff verdes; integração final Kanban pendente |
| AC-17 | BLOCKED | Retry safe GET passou 2/2, mas falha real de controlador ainda sem E2E |
| AC-18 | BLOCKED | Fences nos testes integrados e ledger real preservado, falta crash/recovery |
| AC-19 | PASS | 20/20 ciclos de recuperação sintética, p95 1,099 s |
| AC-20 | BLOCKED | AI Control e controlador vivos, sem dogfooding agent→Browser Chromium novo |
| AC-21 | PASS | Nove suítes Electron 115, Python 66 + 14 subtestes, TypeScript PASS; alvo selecionado |
| AC-22 | BLOCKED | Bundle dev compilado, sem E2E real nem build de distribuição/CI exato |
| AC-23 | BLOCKED | WIP e escopo verificáveis; canal humano e E2E ainda incompletos |
| AC-24 | PASS | Incidente histórico somente leitura, nenhuma alteração de ACK/terminal |

**Próxima prioridade:** implementar **reconciliação humana realmente autenticada e causal** sem expor capacidade à LLM; testar operação/sessão/run/token/evidência incorretos, idempotência e crash entre decisão e persistência. Depois E2E Chromium de perfil sintético isolado, foco em segundo plano/minimizado sem entrada global, concurrency/leases, Kanban e CI/release. Não manipular o ledger vivo para simular resolução. Regenerar resume prompt caso AC pendentes.
## Fechamento complementar de 29/10 — catálogo, lint e dogfooding read-only

- RED adicional: o catálogo LLM ainda anunciava browser_admissions_reconcile. GREEN após remoção de _WORKSTATION_SCHEMA_TOOLS, mantendo browser_admissions_inspect. O controlador também recusa a execução direta. Testes Python de catálogo e retry: 3/3 PASS.
- Regressões Python após patch: 67 PASS + 14 subtests; TypeScript Electron PASS. ESLint dos três arquivos Electron: 0 erros, 76 avisos após correção de consistent-type-imports.
- Sessão Hermes real ativa via AI Control autenticado: Browser ready=true, paused=false, 1 tab, 1 task parked; controlador PID 9896 vivo, /health autenticado PASS. Nenhuma operação mutante ou WhatsApp enviado.
- O processo aberto antecede o bundle de desenvolvimento recompilado. Não presumir que hot reload aplicou código; precisa de validação nativa após reinício normal pelo operador.
- Ainda faltam via positiva de reconciliação humana autenticada/causal, E2E Chromium com viewport em background/minimized sem foco global, leases/concorrência, batch crash, TaskRun/Kanban, CI/build de release. AC-12 FAIL; AC-20 BLOCKED. Sem liberação do ledger histórico.
- Estado: IN PROGRESS — RESUME REQUIRED. Retomar pelo relatório completo, arquivos/diffs, teste de autorização humana separado do canal agent-only, E2E nativo isolado e proof end-to-end após restart.

---

# CONTINUAÇÃO 2026-10-29 13:14–13:59 BRT — Revisão humana positiva restrita e prova nativa oculta

**Estado final deste ciclo: IN PROGRESS — RESUME REQUIRED.** Não homologado para produção, usuário não foi solicitado a reiniciar, nenhuma janela real/WhatsApp/ledger de produção alterados. Fonte autoritativa de decisões e evidências desta continuação.

## Preflight e preservação

- Windows DESKTOP-3NA47UH, checkout C:\Github\hermes-agent, branch main, HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e.
- Entrada 232 dirty, 174 untracked, staging 0; postflight 238 dirty, 179 untracked, staging 0 (alguns arquivos adicionais novos de teste); não criar branches/worktrees/commits/pushes, não realizar reset/stash/clean.
- Stage A: dispensa expressa do mantenedor para todas as tarefas de 29/10/2026, previamente registrada em CURRENT_STATE.md e engineering-journal/CURRENT.md. Não dispensa E2E, CI/release ou controle de concorrência.
- AI Control confirmado true, painel Sessions, backend v0.21.7+1590 (+1). Controller existente respondeu autenticado GET /health true, runtime electron-chromium. **Essa instância não foi reiniciada e pode não executar o bundle recém-gerado.**
- Incidente histórico op_browser_batch_actions_3d591fa7f8da: no ledger real consultado somente leitura (mtime 2026-10-29 12:34:01), op presente, acknowledged=false e terminal ausente. Não reconciliar, expirar, repetir, limpar ou escrever.

## Causa e solução limitada

O handoff humano atual em workstation-browser-pane.tsx -> web_server.py -> plugin_api.py apenas sinaliza revisão humana com readback_required=true e mutation_authorized=false; não fecha admission nem prova efeito. Em session-state.ts::reconcilePendingAdmission o lock/fsync já existem, mas campos textuais de evidência não constituem autorização de humano. O próprio save() pode ACKar navegação quando receipt de owner está presente: logo, a classe de pendência com receipt e sem ACK é tipicamente **legada ou crash**, não operação normal. Não interpretar teste preparado como prova de desbloqueio WhatsApp.

Criado fluxo limitado e fail-closed **somente para browser_navigate local em origem sintética** (https://example.test, *.example.test, *.localhost ou HTTP loopback sem credenciais/query/fragment). Não cobre cliques, batches, WhatsApp, envios e outros efeitos externos.

- Novo electron/workstation-browser-human-review.ts: valida admission pendente, mesmo BrowserTask/taskId/sessionId/runId/tabId, último receipt durável da navegação, URL sanitizada, WebContents vivo/id e URL atual. Exclui ação/URL sem prova.
- runtime.ts: navigationReviewEvidence(), listVerifiedNavigationReviews(), reviewVerifiedNavigation() com readback antes e depois da decisão; nova verificação de BrowserEntry.ownerTaskId, TaskLifecycle.task.sessionHost/runId, WebContents não destruído/crashed e identidade WebContents. O método review não é acessível pelo controller agent-only.
- session-state.ts: parâmetros opcionais requirePending, expectedAdmission, expectedNavigationReceipt no método transacional existente; faz CAS e rejeita approval reutilizada e alteração de identidade/recibo sob lock, antes de persistir terminal. Mantém legado de chamadas sem essas opções.
- workstation-browser-ipc.ts: canais human-review:list-navigation e :confirm-navigation, somente mainFrame de BrowserWindow dona do runtime. Confirmação exige janela focada e prompt nativo dialog.showMessageBox com Cancel padrão; só resposta nativa afirmativa passa para reviewVerifiedNavigation.
- electron/preload.ts e src/app/browser/types.ts: bridge específica para list/confirm. UI workstation-browser-pane.tsx filtra projeção por activeSessionAliases e oferece botão "Review locally" separado do handoff original. Agente não recebe token de aprovação.
- Testes novos electron/workstation-browser-human-review.test.ts (2/2), workstation-browser-ipc-human-review.test.ts (3/3) para evidência causal, identidade, URL falsa, ação batch/WhatsApp excluída, wrong owner/frame/foco, cancel default, aprovação nativa, CAS single-use e terminal durável. Teste CAS usa snapshot sintético escrito diretamente para representar legado/crash sem ACK, já que save() normalmente reconhece receipt automaticamente.

**Atenção:** o código é estritamente protótipo seguro do caminho positivo local. **Não satisfaz AC-12 para efeitos arbitrários** nem demonstra confirmação real por operador. Não converter para aprovação geral por remoção de restrições; sem causalidade externa, conservar UNCERTAIN.

## Testes e verificações desta continuação

- Vitest Electron 10 arquivos relevantes: 112/112 PASS, exit 0, controller descriptor produtivo SHA inalterado.
- Vitest UI WorkstationBrowserPane: 3/3 PASS, avisos React act/localStorage preexistentes.
- Python Browser+handoff/prefabs: 67/67 PASS, 14 subtests PASS.
- TypeScript Electron: tsc -p tsconfig.electron.json --noEmit = PASS.
- ESLint dos 8 arquivos TS/TSX relevantes: 0 errors, 127 warnings. Seis erros iniciais de ordenação/type-import dos novos arquivos foram corrigidos. Sem auto-fix global em WIP de terceiros.
- node scripts/bundle-electron-main.mjs --dev = PASS, dist/electron-main.mjs 3.3 MB; preload 51.1 KB.
- git diff --check nos arquivos tocados = PASS.
- TypeScript renderer global tsconfig.json ainda acusa 6 erros em runtime.ts e workstation-learning-session.ts (observados separadamente; não inferir que todos sejam causados por este patch). Não chamar release qualificado.
- Script nativo REAL em Windows Electron: apps/desktop/e2e/workstation-native-hidden-browser-audit.cjs e runner.cjs. Chamada reproduzível:
  cd C:\Github\hermes-agent\apps\desktop
  node e2e/workstation-native-hidden-browser-runner.cjs
  => exit 0, NATIVE_HIDDEN_CHROMIUM_PASS {native:true,windowVisible:false,focusable:false,isFocused:false,clicked:1,input:"hermes-native-proof",active:"i",enter:true,scrolled:250.3999,profileTemp:true}.
  Electron externo de teste criou BrowserWindow(show:false,focusable:false,skipTaskbar:true), perfil isolado em %TEMP%, documento data: local; Input.dispatchMouseEvent/insertText/dispatchKeyEvent/mouseWheel com debugger **interno ao WebContents**, readback via executeJavaScript. Sem mouse/teclado global, sem rede, sem CDP externo, sem foco. Um primeiro lançamento por Powershell não capturou saída; segunda execução com capture de child process e runner persistido PASS. **Não é E2E do runtime Hermes/TaskRun/leases nem prova de app minimizado**.

## Matriz de aceite atualizada (evidência estrita)

| AC | Estado | Racional |
|---|---|---|
| AC-01 | PASS | GET health autenticado na instância antiga, owner PID do descritor vivo |
| AC-02 | PASS | 10 reparos de descritor sintéticos anteriores |
| AC-03 | BLOCKED | 10 relistens sintéticos; falta native runtime integrado |
| AC-04 | PASS | Regressões não alteraram SHA do controller descriptor produtivo |
| AC-05 | BLOCKED | falta isolamento Native BrowserTask entre duas sessões/viewports |
| AC-06 | BLOCKED | clique Chromium oculto comprovado, mas sem executor Hermes |
| AC-07 | BLOCKED | digitação Chromium oculta comprovada, mas sem Target BrowserTask |
| AC-08 | BLOCKED | press/scroll/readback Chromium oculto comprovados; matriz Hermes incompleta |
| AC-09 | BLOCKED | teste oculto sem foco comprovado, mas sem instrumentação geral Hermes |
| AC-10 | BLOCKED | lease/concurrency humano/agente ainda não homologadas nativamente |
| AC-11 | BLOCKED | falta crash+replay com TaskRun e ledger integrado |
| AC-12 | BLOCKED | fluxo humano positivo apenas para navegação sintética legada; click/batch/WhatsApp sem evidência ficam incertos |
| AC-13 | PASS | agente sem reconcile em catálogo e controller, regressões anteriores |
| AC-14 | BLOCKED | partial batch e ACK durável após crash não homologados |
| AC-15 | BLOCKED | operação incerta e isolamento entre BrowserTasks reais pendente |
| AC-16 | BLOCKED | Kanban/evidências TaskRun/handoff incompletos |
| AC-17 | BLOCKED | safe GET retry sintético 3/3, falta queda real integrada |
| AC-18 | BLOCKED | testes de fence em mock, falta crash/lease real |
| AC-19 | PASS | 20/20 ciclos isolados anteriores, p95 ~1.099s |
| AC-20 | BLOCKED | instância ativa antigo bundle; não houve cadeia agente→controller→Chromium de mutação |
| AC-21 | PASS | suites-alvo Electron112, Python67+14, UI3, tsc Electron |
| AC-22 | BLOCKED | bundle dev passou; build release/CI/E2E do Hermes não |
| AC-23 | BLOCKED | documentação atualizada, mas produto/integração nativa ainda não completa |
| AC-24 | PASS | ledger produção read-only, admissão histórica sem ACK e sem terminal |

**Próxima prioridade real:** ampliar provas causais seguras para a revisão humana com modelo de autorização verificável que NÃO transforme afirmação humana em evidência de envio externo; integrar handoff revisão e BrowserTask/TaskRun sem liberar efeito incerto. Criar teste IPC de aprovação com mudança de owner e readback durante dialog, integração de concorrência e falha fsync, e E2E Chromium do próprio WorkstationBrowserRuntime isolado. Só após upgrade pelo operador validar o Hermes real pela ponte AI Control. Não repetir a navegação WhatsApp histórica.

---

# CONTINUIDADE P03 — 29/10/2026 14:08–14:51 (America/Sao_Paulo)

**ESTADO: IN PROGRESS — RESUME REQUIRED.** Stage A dispensado pelo mantenedor para 29/10; essa dispensa nao autoriza alterar produção, usar entrada global, contornar fences ou publicar release. Host DESKTOP-3NA47UH, branch main, HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e. Preflight 238 dirty/179 untracked/staging 0, postflight 240 dirty/181 untracked/staging 0; outros processos Codex ativos. Nao usar coordenador historico. Nenhum branch, worktree, commit, push, reset, stash ou clean.

## Correcoes P0 implementadas, RED/GREEN comprovado

- `electron/workstation-browser-human-review.test.ts`: RED de autorizacao humana elegivel mesmo com humanControlLease ativa ou tab `recoveryState:stale`; GREEN em `workstation-browser-human-review.ts::verifiedNavigationCandidate` recusando lease e recovery stale, incorporando `taskRevision` em `VerifiedNavigationReview` e `sameNavigationReview`. Tipo correspondente ajustado em `src/app/browser/types.ts`.
- RED de alteracao concorrente da revisao/lease sob lock; GREEN em `workstation-browser-session-state.ts::reconcilePendingAdmission` com `expectedTaskRevision`, `requireNoHumanLease`, comparados ao estado persistido sob `withExclusiveAdmissionLock()`. `runtime.reviewVerifiedNavigation` passa ambos. Preserva as outras formas de reconciliacao antigas que nao usam esses parametros; caminho agent-only continua negado.
- RED de falha de `fsync`: metodo publicava `RECONCILED` via rename e apenas depois tentava flush, permitindo terminal visivel mesmo quando respondia erro. GREEN: reusar `durableBatchWrite=true` estritamente ao salvar terminal, sincronizando temporario ANTES do rename; flag restaurada com finally. Outro RED mostrou segundo flush redundante depois do rename gerando falso erro depois de terminal persistido; GREEN removendo somente o segundo fsync do ramo reconciliador. Dependencia de rename/copy fallback para power-loss em Windows continua sem prova exaustiva de atomicidade.
- GREEN de dois escritores: lock `browser-session.json.admission.lock` com `wx` impede segundo reconciliador; erro `browser_admission_concurrent_reconciliation_required` sem terminal; apos liberacao escritor legitimo completa. Tudo em perfil temporario, nenhum uso da admissao real.
- `electron/workstation-browser-human-review.test.ts` passou de 2 para 7 testes: lease/stale/revision, CAS em lock, falhas pre/post publication fsync, dois escritores e testes originais. Final: **117/117 testes Electron PASS em 10 arquivos**, `tsc -p tsconfig.electron.json --noEmit` PASS, ESLint 0 errors/140 warnings; Python **67 PASS + 14 subtests**, UI Browser **3/3 PASS**, `git diff --check` PASS. `node scripts/bundle-electron-main.mjs --dev` PASS (dev bundle recompilado, instancia ativa nao reiniciada). Typecheck global renderer completo e release/CI nao homologados nesta continuidade.

## E2E Electron com runtime VERDADEIRO: baseline parcial GREEN, clique RED confirmado

- NOVOS arquivos de teste (nao versionados): `apps/desktop/e2e/workstation-runtime-native-isolated-entry.ts` e `apps/desktop/e2e/workstation-runtime-native-isolated-runner.cjs`. Execute: `cd apps/desktop; node e2e/workstation-runtime-native-isolated-runner.cjs`. Compila o runtime real via esbuild para .cjs temporario, carrega no Electron real em processo filho; `HERMES_HOME`, `HERMES_WORKSTATION_HOME`, perfil, controller, ledger TODOS apontados para diretorio em %TEMP%, limpo no fim; pagina HTTP exclusivamente 127.0.0.1 com button `#b` e input `#i`. Sem CDP externo, sem URL externa, sem janela visivel ao operador, sem mouse/teclado ou foco global.
- GREEN dos subtestes nativos: `WorkstationBrowserRuntime.startControlServer()`, controlador HTTP autenticado, 2 BrowserTasks `task-native-a/b` com `session-native-a/b` e `run-native-a/b`, 2 abas distintas, 2 WebContents vivos, navegações e snapshots com refs `@e1`/`@e2`, recebimento de recibos com lineage correto. Type `browser_type` no input B alterou valor, readback `nativeTypeVerified:true`.
- RED decisivo: `browser_click` em `@e1` do button A retorna sucesso/recibo, mas DOM `window.count===0` => `nativeClickVerified:false`! O runner tem assert de efeito e retorna **EXIT 2** corretamente. Leitura comprova `onclick:function`, `innerWidth=1280`, `innerHeight=754`, button rect [8,8,86.34,21.2], `elementFromPoint(30,10).id==='b'`: nao e referencia antiga nem target fora do viewport na variante com host.
- Variante sem BrowserWindow: clique recusa `target_outside_viewport`; definir somente `WebContentsView.setBounds` nao resolveu e a alteracao experimental foi **revertida**. Variedades de hospedeiro oculto, focavel/não focavel, `showInactive()` fora da tela (-22000,-22000), reapresentacao da task `visible` continuam com clique sem efeito. Um teste manual SOMENTE sintetico de ativacao de botão por key Enter interno tambem falhou; foi retirado do harness final para nao sugerir retry de efeito incerto.
- Controle positivo independente: `node e2e/workstation-native-hidden-browser-runner.cjs` PASS de clique, digitação, Enter e scroll em BrowserWindow raiz oculta e nao focavel. Isso **NAO prova** WebContentsView/BrowserTask. Essa diferenca identifica o compositor/roteamento de evento de ponteiro como frente prioritária e PROIBE contar o recibo de `browser_click` como efeito confirmado sem readback.
- O harness temporario foi endurecido para exigir `nativeClickVerified===true` e retornar nao-zero com `app.exit(2)`. Nao converter RED em GREEN ignorando readback. Proxima solucao deve ser projetada com autoridade do `WebContents`, compatibilidade com viewport humano, sem disputa de foco nem replay. Nao aplicar DOM `element.click()` como fallback geral sem prova de equivalencia e causalidade.

## Preservacao operacional e gates

- AI Control continua ativo no Hermes aberto; `tools.browser_workstation._request_json('GET','/health')` => success true, runtime electron-chromium. Instancia Hermes real NAO reiniciada apos novo bundle, logo AC-20 continua BLOCKED.
- Ledger real `%LOCALAPPDATA%/HermesWorkstation/Runtime/browser-session.json` somente leitura, modificado 29/10 12:34:01; operacao **op_browser_batch_actions_3d591fa7f8da** presente, ACK false, terminal ausente. Nao reconciliar, liberar, limpar, enviar WhatsApp nem replay. Nao alterou cookie, perfil ou BrowserTask produtiva.
- Testes locais P0 nao completam revisao causal para efeitos externos (WhatsApp, batch parcial e clique de resultado desconhecido). AC-12 permanece BLOCKED. Priorizar AC-06 falhando em E2E real, depois AC-07/08/09/10 e demais provas.

## Matriz P03 atualizada (evidencia estrita)

| AC | Status | Evidencia/pendencia |
|---|---|---|
| AC-01 | PASS limitado | Controller real /health na instancia antiga; HTTP nativo isolado autenticado |
| AC-02 | PASS sintetico | Watchdog descritor 10/10 anteriores |
| AC-03 | BLOCKED | Relisten Electron real e BrowserTask sem replay pendente |
| AC-04 | PASS | Perfis/temp de testes isolados, sem alterar controller real |
| AC-05 | BLOCKED | 2 Tasks/tab/run reais comprovadas, falta restart/viewport |
| AC-06 | FAIL | Click reporta ACK mas nao muda onclick em WebContentsView background: RED nativo EXIT 2 |
| AC-07 | BLOCKED | Type com readback GREEN, falta outros estados/minimizado |
| AC-08 | BLOCKED | Snapshot real GREEN; press/scroll apenas Chromium standalone |
| AC-09 | BLOCKED | Sem input global/foco; falta instrumentacao extensa |
| AC-10 | BLOCKED | Lease e CAS negativos GREEN, falta arbitragem runtime nativo |
| AC-11 | BLOCKED | fsync/lock GREEN, crash dispatch/ACK real nao homologado |
| AC-12 | BLOCKED | Human review apenas navegacao sintetica |
| AC-13 | PASS | agente sem reconcile (baseline anterior) |
| AC-14 | BLOCKED | batch parcial nao homologado |
| AC-15 | BLOCKED | 2 Tasks/abas para navigate/type; isolamento mutante completo faltante |
| AC-16 | BLOCKED | TaskRun/Kanban aceite externo pendente |
| AC-17 | BLOCKED | retry GET isolado PASS anterior; crash real nao testado |
| AC-18 | BLOCKED | fences em testes, falta crash nativo |
| AC-19 | PASS | 20 ciclos sinteticos anteriores |
| AC-20 | BLOCKED | Hermes ativo usa build nao homologado, sem dogfood real |
| AC-21 | PASS alvo | Electron117/117, Python67+14, UI3/3, tsc, lint sem erros |
| AC-22 | BLOCKED | bundle dev PASS; E2E click RED, release/CI pendente |
| AC-23 | BLOCKED | runtime ainda sem clique background real |
| AC-24 | PASS | op historica intacta: ACK false, terminal ausente |

## Continuacao critica

P0: resolver **roteamento CDP de ponteiro em WebContentsView destacado/oculto/parked** sem foco Windows. Manter `node apps/desktop/e2e/workstation-runtime-native-isolated-runner.cjs` RED ate `nativeClickVerified=true` com readback causal, nunca por recibo apenas. Comparar Chromium standalone root BrowserWindow que PASS com Chromium no WebContentsView que FAIL; testar coordenadas/compositor/ownership sem ações externas. P1: press/scroll/foco/lease/two-runs/hidden/minimizado, crash/retomada sem replay, relisten, TaskRun/Kanban, read-only WhatsApp apenas apos verde sintetico. P2: typecheck renderer completo, CI/build/release. Nao liberar fences/ledger real, nem efetuar DOM click como bypass geral sem contrato de confiabilidade. Regenerar Resume Prompt se criterios em aberto.

---

# P03 continuação 29/10/2026 14:54–14:58 BRT — investigação adicional do RED nativo de ponteiro

**Status: IN PROGRESS — RESUME REQUIRED.** Preflight host DESKTOP-3NA47UH; main@f1d5ab2f030e940ed4571371b0de45a21a009c9e; 240 dirty/181 untracked/staging vazio. Postflight consultado 242 dirty/183 untracked/staging vazio, mais dois arquivos-probe novos. Stage A dispensado pelo mantenedor somente para 29/10. AI Control autenticado true, painel Sessions, backend desktop; nenhum mouse/teclado/foco global controlado.

A última continuação anterior (14:08–14:51) já fechou RED/GREEN de lease/stale/revision, dupla escrita e falhas fsync na revisão humana: Electron 117/117 PASS, Python 67 + 14 subtests, UI 3 PASS. Não repetir esse trabalho; consultá-lo nas seções imediatamente anteriores.

## AC-06: RED real mantido e nova hipótese descartada

O runner `apps/desktop/e2e/workstation-runtime-native-isolated-runner.cjs` usa WorkstationBrowserRuntime, BrowserTasks e WebContentsViews VERDADEIROS com perfil inteiramente isolado em TEMP. Na execução anterior, `browser_click(ref:'@e1')` da Task A gerou receipt, mas `window.count === 0`, apesar de botão dentro do viewport e `document.elementFromPoint(...)` reconhecer o botão; `browser_type` na Task B teve readback verdadeiro.

**Nova reprodução isolada** criada em dois arquivos novos sem editar a implementação/harness anterior:
- `apps/desktop/e2e/workstation-runtime-native-send-input-probe.ts`
- `apps/desktop/e2e/workstation-runtime-native-send-input-probe-runner.cjs`
Comando: `cd apps/desktop; node e2e/workstation-runtime-native-send-input-probe-runner.cjs`.

Esse probe substitui UMA tentativa de browser_click por `WebContents.sendInputEvent(mouseMove, mouseDown, mouseUp)` na Task A do perfil sintético, sem retry de operação real; continua executando navegação e browser_type nas duas tasks.

**Resultado real**: `NATIVE_SENDINPUT_READBACK={"count":0,"focused":false}`; `nativeClickVerified:false`; `nativeTypeVerified:true`; processo filho exit 2; runner exit 2 (RED esperado). Botão tinha onclick real, rect e hit-test coerentes. Portanto, simplesmente trocar CDP `Input.dispatchMouseEvent` por `webContents.sendInputEvent` não corrige a entrega do ponteiro na WebContentsView estacionada fora da tela. Não implementar esse fallback no produto.

**Causa ainda não comprovada:** hipótese forte é hit-testing/composição de WebContentsView oculto ou janela host offscreen. Necessário ensaio que diferencie compositor, visibilidade e troca de ownership sem tomar foco/mostrar overlay invisível que roube eventos Windows. O teste standalone raiz de BrowserWindow invisível que já passou não representa WebContentsView. Não declarar solução.

## Defeito de confiabilidade adicional

O ramo `workstation-browser-runtime.ts` `case 'browser_click'`, aproximadamente linhas 3469–3530, chama `clickRef` (que usa `cdpClick`) e então registra `taskLifecycle().recordReceipt` e `semantic_effect:'click'` **sem verificar que o evento click atingiu o DOM**. O E2E comprovou receipt falso-positivo quanto à entrega do evento. Recibo de dispatch não deve ser tratado como proof-of-effect. Próximo passo seguro: instrumentar pre/post click delivery com um readback do DOM, vinculado ao elemento resolvido e ao `isTrusted` do evento, antes de declarar semantic_effect/ACK; se não houver prova, manter admissão UNCERTAIN e proibido replay, sem reclassificar como NOT_DISPATCHED. Isso é **proposta pendente**, não patch já aplicado; nem um click DOM confirmado prova envio/entrega externa.

## Validações e preservação

- Não houve alterações novas nos arquivos de runtime/session-state nesta continuação: somente dois arquivos novos de harness de diagnóstico em e2e, preservando WIP de outro agente.
- Nenhum replay de clique no mesmo perfil/operationId, nenhum envio externo, nenhuma entrada global.
- Ledger produtivo lido apenas: `op_browser_batch_actions_3d591fa7f8da` continua presente, sem `acknowledged` e sem `terminal`. Nenhuma reconciliação ou limpeza.
- Próxima prioridade estrita: (1) evitar receipt falso-positivo de click nativo sem readback causal de evento; (2) investigar WebContentsView compositor com Task A isolada e nenhuma ação real; (3) obter native click GREEN; (4) press/scroll/leases/minimizado/crash/TaskRun/Kanban; (5) typecheck global + build release/CI e dogfooding depois de operador carregar bundle novo.
- Matriz: **AC-06 FAIL confirmado**, AC-07 parcial (type nativo PASS), AC-05/08/09/10/11/12/14–18/20/22/23 continuam BLOCKED, AC-24 PASS. Não reclassificar por mock ou receipt.

## P03 continuação ~15:00–15:03 BRT — guard real contra recibo falso-positivo de clique

**P0 corrigido parcialmente no checkout:** em `apps/desktop/electron/workstation-browser-runtime.ts::clickRef`, antes de despachar o clique, armar um listener de capture no elemento `@eN` resolvido e somente registrar `semantic_effect:'click'`/receipt depois que o DOM confirmar evento `click` **isTrusted** no alvo. Nonce por operação, validação de target isConnected e remoção de prova após verificação. Se a entrega não for confirmada, retornar `browser_input_delivery_unverified`, mantendo admission pendente; **sem ACK, sem terminal NOT_DISPATCHED e sem retry de input que pode ter sido entregue**. Captura de clique no DOM prova somente entrega de evento local, NÃO prova efeito downstream, WhatsApp ou rede.

**RED/GREEN observado:** E2E real com `node e2e/workstation-runtime-native-isolated-runner.cjs` e host escondido/offscreen antes emitia recibo `semantic_effect:'click'` apesar de `window.count=0`. Depois do guard, a mesma operação sintética retorna HTTP 400 `CAPABILITY_MISSING` / `browser_input_delivery_unverified` e runner EXIT 2, como esperado enquanto o compositor de WebContentsView não entregar eventos. **O E2E completo não passou**, e continua AC-06 FAIL. O novo guard deixa de afirmar clique verificado, mas não desbloqueia Browser background.

**Mocks atualizados sem mascarar E2E:** `electron/workstation-browser-runtime-task.test.ts` e `electron/workstation-browser-runtime-batch.test.ts` modelam separadamente armamento, mouseReleased e prova posterior; regressões após patch 117/117 Electron PASS (10 arquivos), typecheck Electron PASS, ESLint 0 errors / 102 warnings nos três arquivos tocados, git diff --check PASS e bundle dev compilado PASS. Não foi repetida a suíte Python/UI nesta subcontinuação; baseline anterior continua Python 67+14 e UI 3/3.

**Ponto crítico P0 em aberto:** compreender como despachar clique de ponteiro confiável em WebContentsView de tarefa oculta/offscreen/parked, mantendo viewport humano, sessão e TaskRun vinculados. Input.dispatchMouseEvent e webContents.sendInputEvent ambos falharam nesse estado, enquanto BrowserWindow root oculto passou. Não usar DOM element.click() como bypass genérico; não roubar foco global. Testar modelo distinto de composição/host, ou executor BrowserWindow persistente com viewport humano desacoplado, sem publicar efeitos incertos.

**Release/produção:** nenhuma reinicialização da instância Hermes, AI Control somente leitura, nenhum WhatsApp, nenhuma alteração ledger real. Todos AC mantêm estados anteriores, exceto mitigação de falsa evidência de click agora verificada localmente; AC-06 permanece FAIL, AC-20 BLOCKED, AC-24 PASS.

---

# P04 — 29/10/2026 15:14–15:32 BRT — ROOT CAUSE AND NATIVE CLICK GREEN

**Final status: IN PROGRESS — RESUME REQUIRED.** Stage A waived for 29/10 by maintainer; only local checkout changes. Host `DESKTOP-3NA47UH`; `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`; 242 dirty (preflight), 252 dirty/193 untracked/staging 0 (postflight). Concurrent WIP preserved; no Git branch/worktree/reset/stash/clean/commit/push.

## Root cause — focus within the Chromium target, NOT global Windows focus

- Baseline E2E `apps/desktop/e2e/workstation-runtime-native-isolated-runner.cjs`: **RED** with `browser_input_delivery_unverified` on an unfocused `WebContentsView`. Already mitigated false-positive ACK in P03. `webContents.sendInputEvent()` also previously RED.
- Separate **focus-emulation-only** E2E variant `workstation-runtime-native-focus-emulation-probe.ts` + runner: calls internal Chromium `Emulation.setFocusEmulationEnabled({enabled:true})` on Task A's own `WebContents.debugger` immediately before browser_click. Result **EXIT 0**: owner host `isFocused=false`, target `document.hasFocus=true`, `window.count=1`, Task B input readback GREEN, TaskRuns and receipts preserved. This isolated cause to per-target renderer focus needed for pointer event delivery, without Windows focus.
- Compared **offscreen rendering** variant `workstation-runtime-native-offscreen-probe.ts`: RED remains when focus emulation is not enabled; simply enabling offscreen compositor does not fix dispatch.

## Integrated patch

- `apps/desktop/electron/workstation-browser-runtime.ts::cdpClick()`: use per-WebContents internal CDP `Emulation.setFocusEmulationEnabled(true)` before pointer dispatch, preserve existing pre-dispatch owner and human lease fences and no-blind-retry semantics, and send `enabled:false` in `finally`; if a successful dispatch cannot clear the emulation, fail closed with `browser_input_focus_cleanup_uncertain` (no receipt/ACK/replay). No OS mouse, keyboard or focus operations. Existing `clickRef` validates trusted click event before writing receipt.
- Event-delivery observer in `clickRef` now removes its listener and clears proof on success, unverified readback or exceptional dispatch (if renderer still exists). No lingering listener should later misattribute a human click.
- Test `workstation-browser-runtime-task.test.ts`: asserts focus emulation is enabled before pointer events and disabled after, checks cleanup failure is fail-closed, preserves P0-03 no retry, takeover and uncertain release tests.
- E2E `workstation-runtime-native-isolated-entry.ts`: adds `ownerHostsNotFocused` to output and acceptance assertion.

## E2E evidence (actual Electron + WorkstationBrowserRuntime + authenticated local Controller; all profiles in TEMP)

- `node e2e/workstation-runtime-native-isolated-runner.cjs`: **PASS exit 0**, two sessions and TaskRuns, separate BrowserTasks/WebContents, click actual DOM `count=1`, type `native-proof`, matching receipts, no window focused.
- `node e2e/workstation-runtime-native-parked-probe-runner.cjs`: **PASS exit 0**. Task A stays `parked` while B is visible; click Task A still changes `window.count=1`, without reattaching its viewport or focusing host; B remains distinct; two lineages intact.
- `node e2e/workstation-runtime-native-actions-probe-runner.cjs`: **PASS exit 0**. With A parked and B visible, click A `count=1`, type B `native-proof`, Enter `enterCount=1`, scroll `scrollY=566.4000`, no focused host, valid identity/receipts.
- `node e2e/workstation-runtime-native-minimized-probe-runner.cjs`: **FAIL exit 2**, `target_outside_viewport` (pre-dispatch). Minimized window causes unusable viewport for `WebContentsView`. **No click effect dispatched and no retry.** This is a separate remaining architecture issue; do not mark minimized as green.

All E2E scripts use isolated `HERMES_HOME`, `HERMES_WORKSTATION_HOME`, profile, controller, ledger, loopback HTTP synthetic pages; no external URL, WhatsApp or effects. E2E native API sends Chromium input to task's own WebContents via built-in debugger; no external CDP, OS mouse/keyboard, or foreground window. Focus emulation changes `document.hasFocus()` within renderer, not `BrowserWindow.isFocused()`. The E2E does NOT prove code loaded in the operator's live Hermes.

## Post-patch gates

- Ten Vitest Electron suites: **119/119 PASS**, including two new focus-emulation tests, typecheck Electron `tsc -p tsconfig.electron.json --noEmit` PASS.
- Python regression: **67 PASS and 14 subtests PASS**. UI BrowserPane: **3/3 PASS** (React act warnings pre-existing).
- ESLint directed runtime/task test: **0 errors, 92 warnings**, `git diff --check` PASS, Electron dev bundle rebuilt `node scripts/bundle-electron-main.mjs --dev` PASS.
- Global renderer `tsc -p tsconfig.json --noEmit` **FAIL exit 2** with six errors: runtime.ts:3841/3932 (nullable arguments) and workstation-learning-session.ts:431/437/448/461 (possibly null). Existing prior baseline recorded same six errors; do not count this as release pass.
- Postflight owner: AI Control true, panel Sessions; no restart/hot reload of active Hermes. Production browser-session.json mtime 2026-10-29 12:34:01; protected `op_browser_batch_actions_3d591fa7f8da` present, ACK false, terminal false. No production state written.
- Source SHA256 after patch: runtime.ts `EFF123AF4B35B8CD0881F2D31FF6C5FF33BA5CCF418C4B128F8F5C732D6BF81B`; runtime-task.test.ts `C136F9167E4201F736051E41E47A9628D685D0A40928A1FD0F83E5B1978D2D72`. Recheck hashes before proceeding; other concurrent agents may edit.

## AC-01 to AC-24 updated (strict scope)

| AC | State | Latest evidence/remaining gate |
|---|---|---|
| AC-01 | PASS limited | Existing controller /health authenticated on live instance, no proof new bundle active |
| AC-02 | PASS synthetic | 10 descriptor recovery cycles prior |
| AC-03 | BLOCKED | Native relisten and BrowserTask survival after listener crash untested |
| AC-04 | PASS | Isolated test profile, production controller/ledger untouched |
| AC-05 | BLOCKED | Two native tasks/lineages separate, but full restart/viewport lifecycle untested |
| AC-06 | PASS scoped | Native click while host unfocused and Task A parked, trusted click + DOM count exactly 1; minimized still FAIL |
| AC-07 | PASS scoped | Native type B/readback, not yet all viewport states |
| AC-08 | BLOCKED | Native Enter, scroll and snapshot GREEN in background; minimized FAIL |
| AC-09 | BLOCKED | Native host not focused and no global input; broad audit/minimized pending |
| AC-10 | BLOCKED | Lease change tests/mock, no full native human/agent arbitration |
| AC-11 | BLOCKED | Crash between input dispatch/ACK restart native not yet validated |
| AC-12 | BLOCKED | Authenticated human causal review only safe local synthetic navigation |
| AC-13 | PASS | No agent reconciling capability, tested prior |
| AC-14 | BLOCKED | Partial batch recovery/crash native not complete |
| AC-15 | BLOCKED | Two tasks distinct; complete mutation concurrency/park/crash isolation pending |
| AC-16 | BLOCKED | TaskRun/Kanban acceptance evidence and handoff not end-to-end |
| AC-17 | BLOCKED | Safe GET retry unit passed; real interrupted listener path outstanding |
| AC-18 | BLOCKED | Uncertain fence and historical ledger preserved; crash native E2E missing |
| AC-19 | PASS | Prior 20/20 isolated recoveries |
| AC-20 | BLOCKED | Active Hermes still not confirmed to load patched bundle; no live agent dogfooding |
| AC-21 | PASS targeted | Electron 119, Python 67+14, UI 3, Electron tsc; release renderer tsc fails |
| AC-22 | BLOCKED | Dev bundle green; renderer typecheck and native release/CI not green |
| AC-23 | BLOCKED | Architecture not yet handling minimized host while keeping BrowserTask active |
| AC-24 | PASS | Historical op unchanged, ACK false, terminal absent |

## Next P05 priority

Implement/validate persistent offscreen **nonminimized** compositor host independent of human viewport, to keep WebContentsView input-capable when operator minimizes Hermes; do not fake DOM viewport dimensions or disable `target_outside_viewport`. Design with task ownership, attach/reparent, leases and readback, without OS focus. Use existing minimized RED runner, verify native GREEN only with actual DOM effect and no focus. Then native crash/restart/fence/lease, TaskRun/Kanban, controller relisten, global renderer typecheck, release build/CI. Only after operator reopens current build through normal workflow, dogfood Hermes agent with isolated synthetic task; WhatsApp read-only later. Never replay or reconcile protected historical operation.


---

# P05 — 29/10/2026 15:36–16:16 BRT — MINIMIZE/RESTORE + WATCHDOG NATIVE GREEN

ESTADO: IN PROGRESS — RESUME REQUIRED. Maintainer dispensou Stage A para 29/10/2026; sem extensão a datas posteriores. Host DESKTOP-3NA47UH, main, HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e. Preflight 252 dirty/193 untracked/staged0; último status antes deste apêndice 271 dirty/212 untracked/staged0. Sem Git destructive operations/commits, nenhuma reinicialização do Hermes vivo. Códigos existentes P01–P04 preservados, inclusive isTrusted local click proof e no-blind-retry.

## RED → GREEN e causa

- RED nativo anterior: human BrowserWindow minimizada retorna getContentBounds=0x0, View reduzida 1x1, DOM innerWidth=2 e browser_click devolve target_outside_viewport ANTES do efeito.
- Experimento new e2e/workstation-runtime-native-executor-host-probe.ts (+ runner): reparentamento das mesmas WebContentsViews em hosts auxiliares não minimizados, não focáveis, offscreen x/y -22000, preservando WebContents.id, TaskRun/session/tab; click DOM count=1 e type GREEN, exit0. Nenhuma automação mouse/teclado/foco global.
- Criado apps/desktop/electron/workstation-browser-minimized-compositor.ts: rastreia janelas humanas e suas próprias views, registra minimize/restore/resize/closed. Cria um host de composição auxiliar por BrowserWindow minimizada e o fecha após restore. A janela host é ativada SOMENTE via showInactive() e pode reportar isVisible true offscreen: NÃO afirmar invisibilidade em toda topologia de monitores. Host não tem foco; não realizar efeitos externos.
- Integrado em apps/desktop/electron/workstation-browser-runtime.ts: reservar host antes de validBounds da janela minimizada, manter dimensões reais do renderer e ownership via WeakMaps, usar effectiveWindow para attach/setBounds/detach, usar owningHostFor(view) em parkEntry para não migrar Task A ao host B, ensureChildView/removeChildView pesquisam owner real, restore preserva mesma WebContentsView e mesma identity. Parked view retorna ao limite contentWidth-1/contentHeight-1 com reconciliação resize/setImmediate. Dispose no destroy do runtime.
- RED intermediário: Task A parked movida indevidamente para host B, restaurava B com ambas as views e A vazia. Corrigido mapeando origem por view. Outro RED: Task A x1385 com contentWidth1400 após restore podia sobrepor UI; alinhamento resize agora atinge x1399. RED posterior setBounds via janela minimizada podia rebaixar viewport a 1x1; corrigido para host efetivo.
- Atualizados FakeBrowserWindow.on/off/isMinimized em electron/workstation-browser-runtime-task.test.ts e electron/workstation-browser-runtime-recovery.test.ts; após RED de mock incompleto (104 PASS/15 FAIL), regressão GREEN 119/119.

## E2E nativo isolado (Electron verdadeiro + WorkstationBrowserRuntime verdadeiro)

Todos os runners abaixo em apps/desktop/e2e, executados com node a partir de apps/desktop. Usam perfis, HERMES_HOME, HERMES_WORKSTATION_HOME, ledger/controller em TEMP; páginas HTTP locais somente 127.0.0.1; nenhum WhatsApp, nenhum input global, sem CDP externo.

- workstation-runtime-native-isolated-runner.cjs: PASS exit0, click count1, type valor correto, duas identidades, no-focus.
- workstation-runtime-native-minimized-probe-runner.cjs: PASS exit0, janelas já minimizadas antes de showTask, autohost corretos.
- workstation-runtime-native-minimize-transition-runner.cjs: PASS exit0, minimize durante BrowserTask ativa cria 2 hosts não focados, click count1/type.
- workstation-runtime-native-restore-transition-runner.cjs: PASS exit0, 2 hosts encerrados, 2 views devolvidas às respectivas janelas humanas, IDs inalterados, A parked x1399 e B visible x0, click1/type.
- workstation-runtime-native-minimized-lease-runner.cjs: PASS exit0, human lease A bloqueia click via HTTP409 USER_CONTROL_ACTIVE, count0 e SEM nova admission, B snapshot funciona; release A seguido de click em perfil de teste causa count1, sem foco humano.
- workstation-runtime-native-minimized-bounds-runner.cjs: PASS exit0, setBounds da human minimizada preserva DOM 1280x754 e click1/type.
- workstation-runtime-native-minimized-actions-runner.cjs: PASS exit0, com duas humans minimizadas e A parked: click count1, type B, Enter count1, scrollY600 e readback, host não focado.
- workstation-runtime-native-controller-restart-runner.cjs: PASS exit0, stopControlServer/startControlServer explicitamente mantém IDs/tab/BrowserTask, health autenticado, mesma admission count e click count1 (sem replay).
- workstation-runtime-native-watchdog-relisten-runner.cjs: PASS exit0, força listener HTTP a fechar sem runtime.destroy, watchdog relistens e republica endereço, preserva token, GET health autentica, same WebContents, same admissions, click count1 sem replay. Isto não prova crash completo do processo Electron.
- workstation-runtime-native-executor-host-probe-runner.cjs: PASS exit0, prova inicial de transferência manual entre hosts com IDs inalterados.

## Regressão P05

- Electron Vitest 10 arquivos: 119/119 PASS, exit0; produção control descriptor hash inalterado durante testes.
- Python 67 PASS, 14 subtests; UI WorkstationBrowserPane 3/3 PASS (React act warnings não fatais).
- Electron tsc tsconfig.electron.json --noEmit: PASS; ESLint direcionado nos 4 arquivos TS relevantes: zero errors, 138 warnings; git diff --check: PASS; bundle electron-main.mjs e preload compilados via scripts/bundle-electron-main.mjs --dev: PASS.
- Renderer global tsc tsconfig.json --noEmit: NÃO foi rerodado em P05. Baseline anterior continha 6 erros (2 no browser-runtime.ts nullable arguments; 4 em workstation-learning-session.ts possibly null). Nenhuma homologação de distribuição/release/CI.
- Código implementado/compilado, mas NÃO comprovadamente carregado no Hermes ativo. AI Control foi ativo na última consulta; operador não foi interrompido. Ledger produtivo último read-only: op_browser_batch_actions_3d591fa7f8da presente, ACK=false, terminal ausente. Não modificar/reconciliar/repetir operação histórica.
- Hashes P05 29/10 16:16: minimized-compositor.ts 0C9D0A293CD55EBA6E19C46E1E7A79C30E55F1C3A7A77A6E762BE55616D1709D; runtime.ts CE8E023E26E9926FEB19FF091BDF32F3583A96E4F7E499B10AA87E7B4798A687; runtime-task.test.ts E860763BB618CDB18609C0E74D6F877A0C34B3841A476747A299B1950C0378ED; recovery.test.ts 73CA23B6CD505AD4621FE2E76EF6910A4DD3E7FC8621601FC90A36955DA6E284.

## AC-01..AC-24 em 29/10 P05, estados estritamente limitados à prova

AC-01 PASS limitado, controller /health real anterior; novo bundle live não comprovado.
AC-02 PASS sintético, 10 descriptor recovery cycles anteriores.
AC-03 PASS no E2E nativo isolado, listener relisten watchdog preserva token/BrowserTask; não equivale a crash do processo.
AC-04 PASS, perfis isolados e produção preservada.
AC-05 BLOCKED parcial, 2 sessões/tabs persistem durante minimize/restore; restart completo de processo ainda sem E2E.
AC-06 PASS no E2E isolado, click trusted count1 inclusive parked/minimized; produção não testada.
AC-07 PASS no E2E isolado, type com readback em minimized sem foco.
AC-08 PASS no E2E isolado, snapshot, Enter, scroll/readback em minimized; não afirmar efeito externo.
AC-09 BLOCKED amplo, sem entrada global nos testes, mas auditoria de foco multimonitor/UX falta.
AC-10 BLOCKED amplo, native human lease A 409 sem admission/efeito e B não bloqueada, mas concorrência UI/human in-flight não homologada.
AC-11 BLOCKED, crash entre dispatch/readback/ACK sem E2E multiprocesso.
AC-12 BLOCKED, human review positiva limitada a navegação sintética comprovada, nunca efeito externo.
AC-13 PASS, agent-only reconcile negado.
AC-14 BLOCKED, batch parcial após crash nativo.
AC-15 BLOCKED amplo, cross-task e host mapping GREEN, mas crash/interleavings pendentes.
AC-16 BLOCKED, final TaskRun/Kanban acceptance e handoff E2E.
AC-17 BLOCKED amplo, safe GET retry unit PASS, cliente Python contra relisten real ainda sem E2E.
AC-18 BLOCKED, fences após crash total ainda sem E2E.
AC-19 PASS, 20/20 synthetic recovery cycles anteriores.
AC-20 BLOCKED, Hermes produtivo não comprovadamente carregou P05, sem agent dogfooding.
AC-21 PASS targeted, Electron119/Python67+14/UI3/tsc Electron/lint0.
AC-22 BLOCKED, bundle dev sim, renderer global typecheck e release/CI não.
AC-23 BLOCKED, P05 minimized arquitetura isolada passou, mas host crash/close/monitores e prod faltam.
AC-24 PASS, ledger histórico sem ACK e sem terminal, read-only.

## Próxima prioridade P06 (sem repetir P04/P05)

1. Testar fechamento de human BrowserWindow e perda/crash de host auxiliar; garantir sem janelas órfãs, sem cross-session view hijack e sem inventar recibo. Validar topologias de monitores, resize extremo, multiple minimize/restore cycles, human lease UI real. Provar native in isolated runtime.
2. Testar crash de processo Electron com TEMP HERMES_HOME e admission incerta artificial, reiniciar em outro processo com mesmo perfil de teste; garantir fence prior_operation_requires_reconciliation, nenhum loadURL implícito, nem redespacho de efeito incerto.
3. Testar client Python safe GET após real controller relisten, nunca POST retry.
4. Qualificar seis erros de typecheck global, integridade WIP, build release e CI exact-head. Não escrever arquivos de outros agentes sem coordenação.
5. Só após operador atualizar normalmente o Hermes e reativar AI Control, testar agent→tool→controller→Chromium com BrowserTask sintética/readback, depois WhatsApp read-only. Jamais enviar mensagem ou mexer no incidente protegido.
6. Atualizar este relatório e gerar novo resume prompt autossuficiente se qualquer AC continuar BLOCKED. Sem Windows Agent 01, input global, CDP externo, Git destructive actions ou retired coordinator.


---

# P06 — 29/10/2026 16:35–17:03 BRT — Lifecycle adversarial, crash multiprocesso e gates

**ESTADO: IN PROGRESS — RESUME REQUIRED.** Stage A dispensado pelo mantenedor apenas para implementações locais de 29/10/2026. Host DESKTOP-3NA47UH, main, HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e. Preflight 272 dirty/213 untracked/staged0, relatório SHA C325423F18D3E36DFA5304FDC4B644A7BE627BE99F45E1F2195E34AA67C17752; postflight antes deste apêndice 17:02: 283 dirty/223 untracked/staged0. Sem operações Git destrutivas, commits/branches/worktrees, sem interação de foco/input do Windows ou restart produtivo.

## P06-A — Destruição inesperada do host auxiliar

RED no runner e2e/workstation-runtime-native-p06-host-loss-runner.cjs exit2 com P06_HOST_LOSS_NOT_RECOVERED: host A destruído, WebContents vivo, compositor conservava host destruído e não reanexava. B independente permaneceu.

GREEN exit0 após ajuste real em electron/workstation-browser-minimized-compositor.ts: listener de evento closed distingue host ainda possuído, remove ligação morta, recria host não minimizado/não focável, transfere as mesmas live WebContentsViews e bounds/owner, sem reload ou replay. Evidências: sameTab=true, sameWc=true, originalWcDestroyed=false, host substituto vivo com um child, B vivo, click DOM count1, type correto.

## P06-B — Fechamento humano, reattach, ciclos

RED e2e/workstation-runtime-native-p06-human-close-runner.cjs exit2: janela humana A fechada com B ainda viva destruía host A, mantendo WC vivo mas sem composição. GREEN exit0 após separar fechamento da janela humana de encerramento do runtime: host A fica detached enquanto B humana existe; o novo mecanismo detachedForView associa a view ao host legítimo sem transferi-la para B. O caminho de close do último humano não mantém um host deliberadamente; shutdown destroy remove os detached hosts.

GREEN e2e/workstation-runtime-native-p06-reattach-runner.cjs exit0: nova janela humana recebe a mesma view e WebContents, detachedCountAfter=0, host antigo liberado, sem foco, click DOM count1. Primeiro run falhou intermitentemente ao detectar win.minimize no fixture; segunda execução passou, registrar flakiness e não extrapolar para todos monitores.

GREEN e2e/workstation-runtime-native-p06-cycles-runner.cjs exit0: quatro ciclos adicionais de minimizar/restaurar 2 janelas, cada um 2 hosts durante minimize e 0 após restore; IDs/abas/WC sempre iguais, nenhuma janela focada e click/type preservados.

Limites: não foi injetada exceção durante removeChildView/addChildView, nem testado close do último human em app produtivo, várias telas físicas ou alterações de lease in-flight.

## P06-C — Dois processos Electron com ledger TESTE compartilhado

Novos e2e/workstation-runtime-native-p06-process-crash-entry.ts e -runner.cjs. Electron verdadeiro com esbuild, dados somente em TEMP (HERMES_HOME, HERMES_WORKSTATION_HOME, profile, descriptor, ledger), servidor HTML 127.0.0.1. Processo 1 navega e persiste admission de browser_batch_actions intencionalmente pendente; encerra com process.exit(73) sem runtime.destroy(), antes de qualquer dispatch do batch. Processo 2 (novo PID) reutiliza somente perfil/ledger de teste.

GREEN exit0: seedExit73 PID34388, recoveryExit0 PID34080, differentProcesses=true, pendingBefore/After=true, originalTask=true, snapshot read-only=true, URL about:blank sem carregamento implícito, blockedStatus reconciliation_required com prior_operation_requires_reconciliation, newAdmission=false, priorAcknowledged=false, priorTerminal=false, sameTabId=true. NÃO equivale a crash após o batch realmente executar uma etapa ou após click mouseReleased/readback/ACK. Sem retry, recibo fabricado ou dados produtivos.

## P06-D — TypeScript, regressões e build

RED TypeScript renderer: seis erros anteriores em electron/workstation-browser-runtime.ts (2 step.ref string|undefined) e electron/workstation-learning-session.ts (4 this.state possibly null em recordGesture). GREEN: step.ref ?? null em 2 readbacks; quatro acessos ao this.state alterados para variável recording já validada no começo da função, mantendo guarda após await. Arquivo learning estava Git CLEAN e SHA pré-escrita conferida. Renderer tsc tsconfig.json --noEmit exit0 (57 segundos); Electron tsc tsconfig.electron.json --noEmit exit0.

Electron Vitest 11 files **136/136 PASS**, incluindo 17 testes de workstation-learning-session. Python Browser/WhatsApp/handoff/prefabs **67 PASS + 14 subtests**. UI BrowserPane 3/3 PASS da continuidade P05 (não reexecutado neste P06). ESLint direcionado incluindo learning **0 errors, 159 warnings**, git diff --check PASS. Bundle de desenvolvimento com node scripts/bundle-electron-main.mjs --dev exit0.

**Gates RED atuais:** tsc -p tsconfig.e2e.json --noEmit falha TS6307 (probes Electron nativos importam runtime Electron fora da lista TS E2E) e TS18048 em fixtures. Não excluir provas nem falsificar PASS; qualificar projeto E2E para esbuild/Chromium e TS adequado.

Tentativa real node apps/desktop/scripts/build.mjs exit1 durante stage-native-deps com EPERM no Windows ao renomear apps/desktop/build/native-deps para apps/desktop/build/.native-deps-previous-*/product. DON’T matar processos concorrentes ou apagar diretórios para forçar; identificar owner do lock e negociar janela exclusiva. Sem release build, installer ou CI exact-head. O script de build pode ter criado outputs intermediários ignorados; não limpar sem coordenação.

## Segurança/postflight

Último check 17:02: main HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e, 283 dirty/223 untracked/staged0; AI Control true, activeTab Sessions. Ledger real Runtime/browser-session.json lastWrite 2026-10-29T12:34:01-03:00; op_browser_batch_actions_3d591fa7f8da presente, ack false, terminal false. Não enviar WhatsApp, não reconciliar/reexecutar/expirar incidente, não usar cookies ou dados produtivos.

SHA256 17:02:
- electron/workstation-browser-minimized-compositor.ts: 31D6D3B378C4FD48CEBBECF71D8DBBC87B4180754A4C7D179905EE131AB51E58
- electron/workstation-browser-runtime.ts: 7C187664C28B8C19C38D99E9261EC392E64F378E7A7B890B19EB1EC0392EAA9F
- electron/workstation-learning-session.ts: 9CE4642C5FBDFC14EAD7803CDA0DD64A942C2414E202EF425EC1BACBB4C13F6D
- e2e/workstation-runtime-native-p06-host-loss.ts: A7780D2FB9ADF4A2DD5BBB3585282853566A680DD18E13EBE5B6CA9010F5109C
- e2e/workstation-runtime-native-p06-human-close.ts: 4740DF8986F3C91E8A000E6565AEF98F4C3B396BD10584732C94EA1BF048816F
- e2e/workstation-runtime-native-p06-reattach.ts: EE98C64360077445BE3DCA2697D16E4714EEF631CEA8DD5ABDED5618847AEC00
- e2e/workstation-runtime-native-p06-cycles.ts: 6045740E034DDAAECEB4988100863FB660F092C5FBE8F73C9E61704A6C832F2C
- e2e/workstation-runtime-native-p06-process-crash-entry.ts: 0B6C205324C6B048D4E5732270047C5BFBBF4B9ED3A7D11CE8FC9507B55A495B

## Matriz AC-01..AC-24 depois de P06

AC-01 PASS limitado (controller autenticado no vivo anterior, novo bundle produtivo ainda não carregado comprovadamente).
AC-02 PASS sintético (10 descriptor recoveries anteriores).
AC-03 PASS nativo isolado (watchdog HTTP relisten P05).
AC-04 PASS (teste/perfis TEMP, ledger produtor preservado).
AC-05 BLOCKED parcial (minimize/restore/close/reattach/host-loss e restart 2 processos testados, ciclo app completo pendente).
AC-06 PASS isolado (click trusted no foco/minimizado/parked, DOM count1).
AC-07 PASS isolado (type com readback sem foco).
AC-08 PASS isolado (Enter/scroll/snapshot minimizado).
AC-09 BLOCKED amplo (não usa input global; monitores/overlay/auditoria global pendente).
AC-10 BLOCKED parcial (lease humana 409 sem admission, tarefa B independente; mudança lease durante input ainda sem E2E).
AC-11 BLOCKED parcial (fence após restart de processo com admission pendente, NÃO crash durante efeito e ACK).
AC-12 BLOCKED (reconciliação humana restrita à navegação local sintética; sem prova causal de efeitos externos).
AC-13 PASS (agente não pode reconciliar por declarações).
AC-14 BLOCKED (batch parcial com efeito real e crash intercalado sem E2E).
AC-15 BLOCKED parcial (isolamento multi-task nativo passou em host-loss/reattach; interleavings de concorrência faltam).
AC-16 BLOCKED (TaskRun e Kanban acceptance causal end-to-end).
AC-17 BLOCKED (Python readonly retry unit PASS, real Python/native relisten E2E faltante).
AC-18 BLOCKED parcial (admission fence multiprocesso PASS, efeitos parcialmente despachados não comprovados).
AC-19 PASS (20 ciclos sintéticos anteriores).
AC-20 BLOCKED (Hermes produtivo não reiniciado nem comprovadamente rodando bundle P06; dogfooding Agent->Chromium pendente).
AC-21 PASS direcionado (Electron136, Python67+14, UI3 anterior, Electron/renderer TS green, lint0).
AC-22 BLOCKED (E2E TypeScript TS6307 e source build EPERM; CI/release ausente).
AC-23 BLOCKED (foco/lifecycle corrigidos em isolamento, mas crash parcial, monitores, release e dogfooding faltam).
AC-24 PASS (ledger histórico intacto, no ack/terminal).

## P07 próximo trabalho real, ordem sem duplicações

1. E2E nativo entre mousePressed/mouseReleased, readback e ACK com falha de processo; prova de no-replay, admission fence, no false receipt, 2 TaskRuns e batch parcialmente despachado. Foco segurança; nunca retry cego.
2. Lease humana iniciada durante input e falhas de reparenting remove/add; close último humano, múltiplos monitores e limitação de dimensões, sem ghost hosts/foco.
3. Cliente Python _request_json GET seguro com real relisten Electron; nunca retry de POST mutante.
4. Corrigir/qualificar erro TS6307 da configuração E2E sem ocultar probes; investigar EPERM de native-deps e coordenar janela exclusiva sem matar WIP, depois build/CI/release completos.
5. Atualização manual normal do Hermes pelo operador e AI Control ativo: agente real -> ferramenta -> controller -> BrowserTask -> Chromium -> readback em página sintética. Somente depois WhatsApp Web read-only. Não reiniciar Hermes sem autorização operacional.
6. Atualizar relatório canônico, hashes, AC-01..24; se ainda bloqueado entregar novo Resume Prompt autossuficiente P08.

Proibidos: Windows Agent 01, mouse/teclado/foco global, CDP externo, mensagens WhatsApp, perfil/cookies produtivos, alterações da operação real protegida, scripts do coordenador aposentado, Git destrutivo, commits/push/branches/worktrees ou sobrescrita concorrente. Não considerar E2E mockado ou build dev como release e não chamar complete enquanto algum AC estiver BLOCKED.


---

## MVP OPERACIONAL — 29/10/2026 17h17–17h22 BRT — IMPEDIMENTO DE ATIVAÇÃO

Estado: BLOCKED — EXTERNAL DEPENDENCY OR AUTHORIZATION.

Inspeção real pelo Controle Windows, sem reiniciar ou enviar ações. Host DESKTOP-3NA47UH, HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e, branch main, preflight 283 dirty / 223 untracked / staging vazio.

Processo Electron principal PID 9896 iniciou em 29/10/2026 12:33:16 -03:00. O bundle de entrada apps/desktop/dist/electron-main.mjs foi recompilado em 29/10/2026 17:01:34 -03:00, 4h28 após esse início. apps/desktop/package.json aponta main para dist/electron-main.mjs. dev:electron executa TypeScript + bundle e inicia electron ., sem mecanismo de hot-reload do processo principal. Portanto NÃO foi comprovado o novo bundle P04–P06 no processo vivo; um procedimento de reinício normal precisa carregar a versão compilada.

AI Control autentica e responde: aiControl=true, activeTab=Sessions, backendStatus=desktop. Consulta renderer read-only: document title Hermes, rota /, texto ativo do editor length=0, flag true. Browser Controller autenticado GET /health: success=true, runtime=electron-chromium, controlReady=true. GET /resources: success=true, 3 recursos. Discovery descriptor PID 9896 porta 61701. Nenhum input global ou navegação mutante feita.

Ledger produtivo somente leitura: %LOCALAPPDATA%/HermesWorkstation/Runtime/browser-session.json timestamp 12:34:01.617 -03. Operação protegida op_browser_batch_actions_3d591fa7f8da presente, acknowledged=false e terminal ausente. Não reproduzir/reconciliar/expirar/desbloquear.

Bloqueio operacional atual: pedido proíbe reiniciar/encerrar Hermes vivo sem autorização operacional explícita. Instância segue ativa e não foi reiniciada. Novo ciclo de testes de agent→BrowserTask, ações DOM, minimized e WhatsApp Web NÃO INICIADO porque exige confirmar novo bundle carregado. AC-20 permanece BLOCKED; provas nativas isoladas anteriores não equivalem a dogfooding. Nenhuma mudança de fonte foi feita nesta missão.

Próxima etapa única: operador fechar e reabrir normalmente o Hermes pela rotina já existente de desenvolvimento, após salvar seus trabalhos. A rotina npm run dev engloba renderer Vite e dev:electron (tsc, bundle, electron .). Quando novo PID e bundle ativo forem comprovados, validar pelo próprio agente do Hermes a cadeia Browser Tool→Controller→WebContents→DOM readback, primeiro em página sintética local, depois sem foco/minimizado, e por último WhatsApp Web read-only sem enviar mensagens. Se houver falha corrigir somente o bloqueador observado. Preservar toda segurança P01–P06.



---

## MVP OPERACIONAL — 29/10/2026 17h30–17h41 BRT — HOMOLOGADO COM LIMITES

Estado: MVP OPERACIONAL — HOMOLOGADO para navegação, snapshot, click, type, press, scroll e WhatsApp read-only em uma sessão real do Hermes Agent. Não equivale a release/CI nem fechamento de AC-01..24.

Instância real: Electron main PID 35536 (novo), dist/electron-main.mjs compilado imediatamente antes de iniciar; AI Control bridge autenticada = true, backend desktop; Browser Controller GET /health = success true/runtime electron-chromium/sem lastError. Nenhum reload artificial ou reinício adicional nesta missão.

Atalho real de C:/Users/Kevyn Lucas/Desktop/Hermes Work.lnk inspecionado via COM WScript.Shell: target powershell.exe, args -NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File C:/Github/hermes-agent/workstation/scripts/fast_reopen.ps1; working dir repo, icon existente. Script -Probe retorna HOT (exit0); no hot reabre sinalizando à instância; no cold chama START-HERMES-WORKSTATION.bat -> oneclick_bootstrap.ps1 -> workstation/start.ps1 -> npm run dev, que compila e lança electron. Nenhuma mudança de atalho é necessária.

Sessão nova criada exclusivamente via AI Control nativo, intitulada "Teste operacional Browser NATIVO Hermes". Agent BrowserTask 20261029_173604_b7383a, tabId ab6d2ca2-507a-4516-bf07-69a81bff080e, owner agent, sem human lease. Prompt uma vez por etapa; nenhuma repetição em caso de incerteza. Ferramenta do próprio Hermes Agent (não teste direto Controller) navegou a http://127.0.0.1:18653/ e usou browser_snapshot, browser_click, browser_type, browser_press, browser_scroll, browser_snapshot. Página servidor independente criado no TEMP em Node loopback registrou proof: initial loads=1, clicks=1, typed=mvp-20261029, enters=1, scrolls=1, lastY≈532.8; Browser Agent informou operaçãoId de navegação e de cada input e tab imutável. Isso prova efeito real no DOM independente da afirmação do agente.

Etapa segunda: Hermes UI button Minimize acionado via AI Control renderer, sem mouse/teclado/foco global. Ponte autenticada permaneceu funcional; document.hidden=true/document.hasFocus=false em inspeções durante o fluxo. Prompt interno na mesma task, browser_snapshot, novo clique intencional, type substituição, Enter, scroll up, snapshot. Servidor independente resultou clicks=2, typed=bg-20261029, enters=2, scrolls=2, lastY=0. A URL não recarregou (loads=1). Agent preservou mesma task/tab, sem erro ou admission incerta. Observação: em leitura posterior document.hidden=false/focus=true, sem prova da causa da restauração (operador ou sistema). Portanto NÃO afirmar ausência de qualquer mudança de foco ao longo de todo ciclo, embora nenhuma API de input/foco global tenha sido usada por nós.

Etapa WhatsApp: mesmo Hermes Agent na mesma task navegou https://web.whatsapp.com, snapshot read-only, retorno HTTP200/título WhatsApp, UI de sessão autenticada sincronizando (sem tela QR), nenhum clique em contatos, nenhuma mensagem lida/reproduzida ou enviada. Controller GET /health mostrou 1 tab no domínio web.whatsapp.com, ownerTaskId correto, lastError null. O renderer encontrava-se hidden=true/focus=false na verificação. Não foram utilizados CDP externo ou controles globais.

Toda a prova foi executada na instância real do Hermes e por seu próprio agente, não por runner sintético. Limites: somente este fluxo de uso foi homologado, sem interferência observada de nossas ferramentas, não é certificação geral de não interferência com outras janelas/monitores, concorrência humana ou crash transacional. Os 24 ACs de release ainda têm pendências anteriores. Sem build full, sem alteração de código, branch/commit/reset/stash, nem reinício do Hermes nesta missão. Ledger histórico protegido continua somente leitura.

Critério de encerramento da missão MVP alcançado para operações acima: parar de expandir testes e utilizar o Hermes em tarefas reais dentro dos fences existentes. 
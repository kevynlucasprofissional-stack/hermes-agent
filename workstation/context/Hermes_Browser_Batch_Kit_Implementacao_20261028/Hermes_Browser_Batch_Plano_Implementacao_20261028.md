# Hermes Work — Kit de implementação para fechamento do Browser Batch

**Data-base:** 28/10/2026  
**Escopo:** P02 (recuperação, readback e handoff), riscos residuais do P01 (atomicidade e auditabilidade), validação e documentação. **P03 não é parte destas quatro implementações** e deve continuar como lane independente.  
**Resultado desta etapa:** investigação seletiva, sequência de prompts, patch de referência P02, critérios de teste e inserções documentais preparados; **nenhum código do checkout foi modificado por este planejamento**.

## 1. Diagnóstico técnico e evidências

### Confirmado no checkout inspecionado

- Repositório `C:\Github\hermes-agent`, `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`, **206 entradas dirty no preflight desta etapa**. É um worktree compartilhado: revalidar HEAD/status imediatamente antes de agir.
- Electron/TypeScript: `apps/desktop/electron/workstation-browser-runtime.ts`, `workstation-browser-session-state.ts`, `workstation-browser-task.ts`, `workstation-browser-batch.ts`; UI React/TypeScript em `apps/desktop/src/app/chat/right-rail/workstation-browser-pane.tsx`; prefabs Python em `workstation/prefabs/{engine,integration}.py`; API FastAPI em `hermes_cli/web_server.py` e serviço de handoff em `plugins/workstation/dashboard/plugin_api.py`.
- P01 **está no código**: `completeVerifiedBatch`, `saveSessionDurably`, `batchStepReceiptRefs`, receipt de ação `browser_batch_actions` com identidade do pai, lock canônico e fsync do arquivo temporário. Suítes P01: **45/45 testes Electron PASS** na auditoria imediatamente anterior; typecheck Electron já havia passado. Esses resultados são locais, não release.
- P02 incompleto: `shouldDeferRestoredNavigation(restored)` analisa admissões `browser_navigate`, não considera diretamente um `browser_batch_actions` posterior não resolvido. Reprodução anterior do **método extraído**: RED para nav anterior ACKada + batch incerto; candidato em memória 8/8; **não é E2E nem patch aplicado**.
- `workstation/prefabs/engine.py::navigate` separa `browser_navigate` e `browser_snapshot`; `integration.py::maybe_resolve_navigation` produz HANDOFF se falta comprovação. `web_server.py` exige token no GET/POST de `/api/workstation/handoffs`; `plugin_api.py` exige `session_id/run_id` e devolve `readback_required=true`, `mutation_authorized=false`. Testes prévios positivos: 29 Python prefab/handoff, 3 UI e 26 loop Python, além de 34 Electron selecionados. Não confundí-los com fluxo E2E único.
- P01 risco de confirmação pós-commit: `runtime.ts` chama `completeVerifiedBatch()` (que já persiste o ACK pai) e **depois** `taskLifecycle().recordReceipt()`; o `catch` comum transforma uma falha em `status=uncertain` com `reason=batch_parent_confirmation_not_durable`. A contradição possível **ainda não tem teste RED dedicado**; não declarar bug confirmado antes do teste.
- Persistência de P01 retém **refs ordenadas** filiais. Ainda é preciso demonstrar o nível de evidência durável por etapa que permite auditoria causal após reinício, sem armazenar DOM, mensagens, cookies, telefones, tokens ou imagens.
- Nenhum E2E do cenário P02 com controlador nativo autenticado, perfil temporário e backend loopback foi comprovado. O ledger real antigo não foi reconciliado.

### Governança real e dependências

- `.hermes-collab/browser-batch-p01-patch-20261028.claim/owner.json` reivindica `runtime.ts` e `session-state.ts` (`READY_FOR_INTEGRATION`); `siteops-qualification` reivindica testes `runtime-admission`/`runtime-recovery`; `whatsapp-m3` reivindica documentos canônicos. O relatório de P02 já está sob claim próprio de diagnóstico. Não sobrescrever ou transferir ownership tacitamente.
- O script anterior `workstation/scripts/multi_agent_coordination.py` está **removido do worktree** (`git status D`); não restaurá-lo nem editar arquivos `.claim` diretamente para forçar acesso. Usar fluxo de coordenação/handoff que esteja efetivamente disponível; se indisponível, preparar apenas patches/testes em TEMP e manter HOLD.
- Dispensa de Stage A autorizada pelo usuário neste chat para a missão **P03** não substitui autorização específica de P02/P01 nem a qualificação de CI/release. Registrar permissões reais no momento da execução. Nenhum branch/worktree/reset/stash/clean/commit/push sem pedido expresso.
- Divergência upstream apontada na auditoria anterior: 1.349 ahead / 6.574 behind *na ocasião*. Não usar como valor atual sem reconsulta. Não fazer fetch/merge ou integração destrutiva apenas para este planejamento.

### Decisões a preservar

- Uma etapa verificada não dá ACK ao lote inteiro. Só há parent ACK quando **todas** as etapas e checkpoints estão verificados e duráveis, com identidade/lease/documento atuais.
- `uncertain` não produz retry, clearance automático, TTL, `acknowledged=true` genérico, nem migração de TaskRun entre conversas. `NOT_DISPATCHED` só mediante evidência pré-efeito.
- `parked` e `about:blank` podem representar restauração segura; não são evidência de perda da sessão. `browser_snapshot` é read-only, mas **a materialização lazy** pode carregar URL externa; deve respeitar o fence.
- Preservar store canônica, locks, fsync, owner, human-control lease, `sessionHost/runId`, receipts e Kanban upstream.
- Revisão humana do handoff registra revisão: não abre aba, não autoriza mutação, não emite ACK e exige readback independente.

## 2. Mapa de dependências

| Etapa | Dependências | Gate de avanço | É independente de P03? |
|---|---|---|---|
| **01 — P02 lazy restore** | Handoff dos arquivos de runtime; Stage A da missão ou waiver próprio; RED isolado | 0 `loadURL` externo após batch incerto; mutação nova bloqueada; safe restore sem regressão | Sim |
| **02 — P01 ACK/auditoria** | Handoff P01; saída 01 disponível (mesmo arquivo runtime) | Sem divergência entre resposta e ACK persistido; evidência filial verificável após restart | Sim |
| **03 — P02 E2E autenticado** | 01 e 02 GREEN; backend/IPC/handoff disponível | Cenários completos de restart e readback seguro, identidade correta e revisão sem replay | Sim |
| **04 — docs/CI/integração** | 01–03 GREEN e claims de documentação | Documentos sincronizados, CI exata qualificada ou HOLD fundamentado, sem afirmar release sem prova | Sim |

**Por que quatro prompts:** 01 é uma correção localizada com risco de side effect por leitura; 02 é um problema transacional e de evidência diferente, exigindo raciocínio próprio; 03 é orquestração E2E entre Electron/renderer/Python/API; 04 é integração, documentação e gates, sem diluir a depuração de produto.

## 3. Artefatos preparados

1. `Hermes_P02_Lazy_Restore_Referencia_20261028.patch` — **patch de referência real** para `apps/desktop/electron/workstation-browser-runtime.ts::shouldDeferRestoredNavigation`. Construído a partir da fonte atual; `git apply --check` em `C:\Github\hermes-agent`: **exit 0**, sem aplicação. SHA-256: `755e4887c3dee286d9e44f1e3d465480ad570b3dc7fc91f6ad35de224b2a5560`. A aplicação continua condicionada a RED integrado, ownership e revalidação de fonte.
2. `Hermes_Browser_Batch_Insercoes_Documentais_20261028.md` — texto preparado para documentos canônicos reivindicados; **não aplicado**.
3. Este documento — estratégia, evidências, prompts e limites.

## 4. Sequência completa de prompts, autossuficientes

---

### PROMPT 01 — P02 | Restaurar sessão sem loadURL implícito após operação incerta

**Papel:** Engenheiro Principal de Electron, segurança de operações idempotentes e BrowserTask recovery.

**Missão:** corrigir e validar em `C:\Github\hermes-agent` a materialização lazy de uma aba restaurada quando há um `browser_batch_actions` não resolvido da mesma tarefa/aba/owner. Impedir navegação implícita por `browser_snapshot` (que seria read-only) sem bloquear navegação legítima confirmada. Implementar, testar e documentar, não apenas analisar.

**Contexto comprovado:** `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e` na inspeção de 28/10 (revalidar); P01 parent ACK já implementado no runtime e session-state, com 45/45 Electron PASS. Em `apps/desktop/electron/workstation-browser-runtime.ts::shouldDeferRestoredNavigation` (~4204), o predicado observa apenas últimas admissões `browser_navigate`. A investigação anterior extraiu esse método e confirmou RED: receipt da navegação anterior é válido, mas lote posterior incerto sem receipt não causa defer. Resultado atual: `pendingBatchDeferred=false`, em vez de `true`. A correção candidata, em memória, passou 8/8 testes *do método*, mas não foi aplicada nem testada em E2E. Documentos de origem: `workstation/context/BROWSER_RESTART_P02_GATE_AND_TEST_REPORT_20261028.md`, `BROWSER_BATCH_P01_IMPLEMENTATION_20261028.md` e `BROWSER_BATCH_RECONCILIATION_PLAN_20261028.md`.

**Preflight e limites:** ler `AGENTS.md`, `workstation/AGENTS.md`, `apps/desktop/AGENTS.md`, `workstation/context/README.md`, política Stage A, branch/HEAD/dirty e claims. Não aproveitar dispensa anterior de P03 como waiver de P02. `runtime.ts` e `session-state.ts` estão sob claim P01; teste `workstation-browser-runtime-recovery.test.ts` sob `siteops-qualification`. Obter handoff explícito; se indisponível, criar RED/candidato em TEMP e encerrar HOLD, sem invasão de arquivos. O antigo script de coordenação está deletado no worktree: não restaurar nem editar manifests de claims. Não mudar Kanban, P03, CDP externo, ledger vivo, WhatsApp, mouse/teclado, branches/worktrees, nem realizar operações Git destrutivas/commit/push.

**Arquivos e contrato:** modificar somente `apps/desktop/electron/workstation-browser-runtime.ts` no predicado; criar teste novo `apps/desktop/electron/workstation-browser-runtime-p02-restore.test.ts` sob claim próprio, ou arquivo equivalente se já existir um teste proprietário apropriado. Reutilizar `BrowserSessionStateFilePersistence.pendingBrowserMutation`, `restoreSessionTabs`, `entryForTask/rawEntryForTask`, `BrowserTask`, `FakeWebContents` e `HERMES_HOME/HERMES_WORKSTATION_HOME` temporários. Não criar segunda store de autoridade.

**Passo 1 — RED integrado:** construir fixture `task-a/session-a/run-a`, aba `tab-a`, URL fictícia `https://example.test/phase-1`, nav anterior com receipt correspondente, depois batch parent admitido e sem ACK/terminal. Destruir runtime, criar instância nova, disparar `browser_snapshot` e espionar `FakeWebContents.loadURL`: RED deve provar que o código anterior tenta carregar a safeUrl apesar do batch incerto; nenhum request real. Assert que `browser_navigate` com outro operationId segue barrado por `prior_operation_requires_reconciliation`. Testar também 1 filho persistido/2º incerto; lease humana; tab/run/session divergente; documento modificado; reinício com estado parcial/corrompido; não limpar histórico. Documentar saída RED autêntica.

**Passo 2 — patch candidato:** o arquivo preparado `Hermes_P02_Lazy_Restore_Referencia_20261028.patch` modifica **apenas** `shouldDeferRestoredNavigation()` depois de `if (!persisted) {return true}` e antes do filtro `browser_navigate`. Sua lógica é:

```ts
const owner = persisted.browserTasks.tasks.find(task => task.taskId === restored.browserTaskId)
const hasUnresolvedMutation = Object.values(persisted.operationAdmissions ?? {}).some(operation =>
  operation.taskId === restored.browserTaskId &&
  operation.tabId === restored.id &&
  (!owner?.runId || operation.runId === owner.runId) &&
  (!owner?.sessionHost || operation.sessionId === owner.sessionHost) &&
  operation.acknowledged !== true && !operation.terminal
)
if (hasUnresolvedMutation) {return true}
```

Conferir criticamente se `owner` pode faltar ou divergir em dados legados, se o filtro `tabId` cobre a identidade real, se outros callers `entryForTask` podem carregar URL implicitamente e se snapshot sem nav anterior precisa de regra adicional. **Não aplicar mecanicamente**: se necessário, reforçar fail-closed/owner de forma mínima, justificar alterações e provar com RED/GREEN. Não tratar terminal arbitrário como autorização para nova mutação; conservar o preflight mutante existente.

**Passo 3 — GREEN e regressões:** após correção, na sessão com lote incerto exigir `loadURL` remoto = 0, restauração local segura (`about:blank` quando necessário), pending preservado e nova mutação bloqueada. No cenário seguro, nav ACKada sem pendência, preservar a capacidade de restaurar/observar a URL; após batch pai verified, nova navegação explícita com outro operationId deve funcionar com snapshot independente. Sem cross-chat/cross-run, sem lease humano roubado e sem `NOT_DISPATCHED` fictício.

**Comandos de validação (dentro de `apps/desktop`, após conferir homes temporários):**

```powershell
& C:\Github\hermes-agent\node_modules\.bin\vitest.cmd run --project electron electron/workstation-browser-runtime-p02-restore.test.ts electron/workstation-browser-runtime-batch.test.ts electron/workstation-browser-runtime-recovery.test.ts electron/workstation-browser-runtime-admission.test.ts electron/workstation-browser-session-state.test.ts electron/workstation-browser-batch-p01.test.ts --reporter=dot
& C:\Github\hermes-agent\node_modules\.bin\tsc.cmd -p tsconfig.electron.json --noEmit
& C:\Github\hermes-agent\node_modules\.bin\eslint.cmd electron/workstation-browser-runtime.ts electron/workstation-browser-runtime-p02-restore.test.ts --quiet
git -C C:\Github\hermes-agent diff --check
```

O teste novo é proposto e **não existe ainda**; ajustar o comando ao nome realmente criado. Todo arquivo de teste deve limpar env/fixtures e recusar caminhos de `%LOCALAPPDATA%\HermesWorkstation\Runtime`. Guardar outputs e IDs sanitizados.

**Aceitação:** RED e GREEN integrados reproduzíveis; 0 carregamentos implícitos sob uncertain; verified → nova navegação legítima; nenhuma admissão alterada indevidamente; regressões/typecheck/lint PASS. Relatório: paths/diffs, identity/lease/document epochs, teste, resultados, limitações e RESUME PROMPT. Não declarar P02 completo: seu E2E de backend/handoff é PROMPT 03. Pode substituir a solução proposta por alternativa superior quando justificada por evidência do código.

---

### PROMPT 02 — P01 | Consistência transacional do ACK pai e auditoria das etapas

**Papel:** Engenheiro Principal de persistência durável, transações e idempotência.

**Missão:** fechar dois riscos do P01 sem reconstruir a store nem alterar a semântica de segurança de batches. Aplicar alterações reais, com RED/GREEN específico, se as falhas forem reproduzidas no checkout atual; se uma hipótese não se reproduzir, registrar evidência e não adicionar complexidade especulativa.

**Contexto comprovado:** P01 já implementou `saveSessionDurably()`, `completeVerifiedBatch()`, `batchStepReceiptRefs` e ACK pai no store canônico. 45/45 testes Electron PASS; typecheck previamente PASS. No arquivo `apps/desktop/electron/workstation-browser-runtime.ts`, ramo `case 'browser_batch_actions'` (~3833), `completeVerifiedBatch()` confirma duravelmente parent ACK; depois `taskLifecycle().recordReceipt(taskId,parentReceipt)` ocorre dentro do mesmo `try/catch`. Um erro posterior poderia retornar `status='uncertain'`, `reason='batch_parent_confirmation_not_durable'`, mesmo havendo ACK durável. O mecanismo guarda refs `parent:index:tab:revision`, mas sua capacidade de auditoria pós-restart de cada verificação precisa de prova. Não confundir receipt/ACK do Browser com entrega externa.

**Preflight:** revalidar HEAD, dirty, claims e `AGENTS.md`, etapa Stage A aplicável ou waiver próprio. Obter handoff do claim `browser-batch-p01-patch-20261028` para `workstation-browser-runtime.ts`, `workstation-browser-session-state.ts` e testes pertinentes; criar testes em novo arquivo com claim próprio se os demais estiverem reservados. Preservar as alterações de PROMPT 01, os fixtures e o P03. Não tocar no ledger real, no Kanban upstream, no WhatsApp, nem criar commit/branch/reset/stash/clean.

**Ponto de intervenção:** `apps/desktop/electron/workstation-browser-runtime.ts::executeControlRequest` (`case 'browser_batch_actions'`, `adapter.verifyAfter`/`checkpoint` e pós-`completeVerifiedBatch`); `apps/desktop/electron/workstation-browser-session-state.ts::completeVerifiedBatch/saveSessionDurably/save`; `apps/desktop/electron/workstation-browser-task.ts::recordReceipt` (inspecionar, mas **preferir não editar**). O `BrowserTaskLifecycle.recordReceipt()` persiste snapshot e incrementa revision; a confirmação pai já atualiza `browserTasks` e `receipts` dentro do `completeVerifiedBatch`. Evitar persistência redundante que possa falhar após o commit, sem perder estado em memória.

**Passo 1 — RED pós-commit:** em novo teste isolado, após navegar e preparar batch de duas etapas com readback verificado, injetar falha **somente na atualização `recordReceipt` do pai** (não nos receipts filiais). Persistir parent ACK, ler o arquivo com nova instância e comparar à resposta. Asserção invariante: se o response possui razão `batch_parent_confirmation_not_durable`, o parent ACK não pode já estar duravelmente presente; ou o contrato deve distinguir explicitamente commit confirmado de falha de sincronização local, sem habilitar replay. Confirmar que após restart um novo operationId não duplica o efeito nem herda receipt de outra sessão. Testar fsync falhando **antes** do commit em caso separado (deve permanecer uncertain/fenced).

**Passo 2 — decidir e corrigir:** separar fases de **pré-commit**, **commit canônico** e **sincronização em memória**. Tratar o commit do `completeVerifiedBatch()` como ponto linearizável. Se pós-commit falhar, reidratar ou reconciliar a projeção em memória a partir da própria store **sem segunda autoridade**; classificar a resposta coerentemente com o ACK persistido e a prova anterior de verificação, preservando bloqueio se owner/projeção estiver inconsistente. Não adicionar um estado público novo nem prometer `verified` cegamente sem revisar consumidores. Se revisão de contrato for necessária, compatibilizar `workstation-browser-batch.ts`, IPC e prefabs e testar consumidores. Nunca desfazer ACK durável por mera falha posterior; não usar replay como recuperação. Documentar a decisão e a matriz `(ACK durable?, client status?, new mutation permitted?)`.

**Passo 3 — prova de auditoria:** criar teste que salva batch verified de duas etapas, destrói runtime, reabre store e verifica identidades, ordem, revisões, parent/child refs, quantidade de etapas, checkpoints e correlação com a verificação efetuada. Não pressupor que refs por si só comprovam estado anterior/posterior. Se o contrato original exigir trilha mais rica, estender **a mesma store/registro existente** com metadados mínimos por etapa (step index, receipt ref, tipo de verificação, `verifiedAt`, fingerprint não sensível da revisão/epoch e resultado), com limites, normalização, migração compatível e testes de arquivo antigo; **não armazenar valores DOM, texto de campos, conteúdo WhatsApp, PII, token ou URL completa com query**. Antes de implementar, avaliar se os checkpoints existentes já fornecem prova suficiente, evitando uma segunda extensão redundante. A definição de auditoria aqui é **cadeia causal reconstituível**, não reexecução/reconstrução de conteúdo da página.

**Passo 4 — negativos:** step1 verified/step2 uncertain, falha de checkpoint, falha de fsync, ausência de child, child errado, run/session/tab/epoch trocado, lease humana, replay same op, escritor stale, corrupção, lock concorrente e pós-commit sync quebrado. Confirmar ausência de liberação da cerca para operações cujo efeito é incerto. Compatibilidade de dados legados intacta.

**Validação:** de `apps/desktop`, executar seis suítes P01 existentes (`workstation-browser-batch-p01.test.ts`, `workstation-browser-batch.test.ts`, `workstation-browser-runtime-batch.test.ts`, `workstation-browser-session-state.test.ts`, `workstation-browser-runtime-admission.test.ts`, `workstation-browser-runtime-recovery.test.ts`) + novo teste sob claim. `tsc -p tsconfig.electron.json --noEmit`, ESLint focal `--quiet`, `git diff --check`. Testes em TEMP, sem rede ou Electron autenticado real. Usar `git apply --check` para qualquer patch preparado, nunca `git apply` sem claim.

**Aceitação:** invariantes entre ACK e resposta demonstrados, sem replay após crash; prova filial durable auditável (ou explicação respaldada de por que a store atual já satisfaz o contrato); nenhum enfraquecimento de owner/lease/fence; regressões verdes. Atualizar relatórios P01 somente mediante claim, produzir diff, outputs, decisões e RESUME PROMPT se algum gate ficar aberto. A IA tem autonomia para trocar a abordagem por outra mais correta, com justificativa demonstrável.

---

### PROMPT 03 — P02 | E2E nativo de restart, readback autenticado e handoff

**Papel:** Engenheiro Principal de integração Electron, Python Prefabs, FastAPI e segurança de operações com efeitos externos.

**Missão:** executar o cenário funcional de ponta a ponta **após PROMPTS 01 e 02 GREEN**, com páginas fictícias em servidor loopback e perfil efêmero, comprovando que chat/session antigos podem retomar leitura e navegar novamente sem replay, e que efeitos incertos mantêm cerca até reconciliação humana legítima. Não testar WhatsApp real.

**Contexto real:** runtime Electron `apps/desktop/electron/workstation-browser-runtime.ts` com BrowserTasks `parked` e lazy restore; persistência em `workstation-browser-session-state.ts`; `workstation/prefabs/engine.py::navigate` faz `browser_navigate` + `browser_snapshot` independente; `workstation/prefabs/integration.py::maybe_resolve_navigation` constrói HANDOFF; `hermes_cli/web_server.py` expõe GET `/api/workstation/handoffs` e POST `/api/workstation/handoffs/{handoff_id}/review` com `_require_token`; `plugins/workstation/dashboard/plugin_api.py` verifica session/run/handoff e responde `mutation_authorized=false/readback_required=true`; UI `apps/desktop/src/app/chat/right-rail/workstation-browser-pane.tsx::acknowledgeNativeReview` não deve disparar nova navegação. Testes existentes `workstation/tests/test_p0_native_handoff_review_api.py`, `workstation/tests/prefabs/test_prefabs.py`, `workstation/tests/test_h080b_native_browser_experience_loop.py`, `apps/desktop/src/app/chat/right-rail/workstation-browser-pane.test.tsx`.

**Preflight:** garantir GREEN e evidência dos prompts 01/02, conferir branch/HEAD/dirty, claims de runtime, backend, UI e docs. Handoff para qualquer arquivo com ownership alheio; se uma das interfaces já cumpre o contrato, **não alterá-la**. Stage A/waiver desta missão deve ser registrado separadamente. Não usar CDP externo, Selenium com mouse/teclado, SSH, perfil do usuário, credenciais reais, WhatsApp, sistema de mensagens nem arquivos de produção. Evitar iniciar janela do Hermes visível/interferir com o trabalho do operador.

**Fixture:** servidor HTTP em `127.0.0.1` em porta dinâmica, duas URLs fictícias e payloads sintéticos sem PII; profile/temp-dir e `HERMES_HOME/HERMES_WORKSTATION_HOME` temporários, com limpeza em `finally`. Controlador nativo autenticado de teste (pela via de IPC/AI Control que o projeto oferece, sem habilitar CDP). IDs canônicos `task-a/session-a/run-a` e aba controlada; marcar cada etapa com `operationId`, `handoffId`, `tabId`, `documentEpoch`, `runId` e timestamp monotônico sanitizados. A instrumentação não pode incluir DOM, texto, cookies, tokens, imagens, telefone, conteúdo WhatsApp nem URLs com query sensível.

**Cenário A — positivo:** nova sessão → navegação/receipt → batch 2 passos verified (parent ACK durável) → destroy runtime → nova instância com MESMO perfil temporário e TaskRun → snapshot independente e readback da URL/estado fictício → `browser_navigate` novo `operationId` → novo snapshot independente. Assertions: exatamente um owner, identidade session/run/tab preservada, nenhum replay de ação anterior, parent ACK presente após restart, endpoint real local observado. `parked/about:blank` devem ser interpretados como estado seguro, não perda de identidade.

**Cenário B — negativo:** nav anterior ACKada + batch com 1 child e interrupção antes do ACK pai → destroy/restart → snapshot read-only não carrega safeUrl remota implicitamente → nova mutation retorna `prior_operation_requires_reconciliation` → nenhum `loadURL` externo/novo efeito. Cobrir URL/`documentEpoch` alterados, human-control lease ativa, sessão ou run diferentes, owner spoofed, escrita concorrente e storage corrompido. Não reconciliar para fazer teste passar.

**Cenário C — handoff autenticado:** gerar handoff sintético `uncertain_mutation_requires_review` no `HumanHandoffManager` em HOME temporário; GET com sessão correta vê apenas os próprios IDs; POST exige auth de teste, mesma sessão, run e handoff; token ausente deve falhar, sessão errada 404, run errado 409, repetição 409 (se esse for o contrato observado). Após revisão, comprovar `status=ready`, `readback_required=true`, `mutation_authorized=false`. Espionar executor/IPC para **zero novas mutações** após review; somente nova observação independente e check de TaskRun podem produzir conclusão segura. Não declarar efeito remoto verificado por banner de UI. Não enviar headers/tokens em relatórios.

**Journal:** usar mecanismo existente em `workstation/dogfood/artifacts/journals/` ou journal canônico já empregado pelo fluxo, conforme os schemas reais; eventos mínimos `event_type`, `operation_id`, `parent_id`, `step_index`, `task_id/session_id/run_id`, `tab_id`, `handoff_id`, `status`, `reason_code`, `elapsed_ms`, `timestamp`, `checkpoint_ref`. Se algum campo for sensível, usar identificador sanitizado; jamais gravar conteúdo da página. Não criar uma segunda store de autorização. Reabrir o journal após restart para correlacionar parent/child/handoff.

**Testes e comandos:** fixtures Node/Electron do projeto para E2E de navegador em perfil temporário; somente afirmar "nativo autenticado" quando o teste de fato usa a ponte nativa, não um stub. Em `apps/desktop`, rodar `vitest run --project electron <arquivos-exatos-criados> ...` com as suites P01/P02 relevantes e `vitest run --project ui src/app/chat/right-rail/workstation-browser-pane.test.tsx`; Python via runner canônico `scripts/run_tests.sh workstation/tests/test_p0_native_handoff_review_api.py workstation/tests/prefabs/test_prefabs.py workstation/tests/test_h080b_native_browser_experience_loop.py -q`, com `HERMES_PYTHON` venv. `tsc -p tsconfig.electron.json --noEmit`, lint focal e `git diff --check`.

**Aceitação:** evidência E2E real ou HOLD explícito com motivo (ex.: não há bridge autenticada em perfil temporário), nenhum replay, identidade preservada, nova navegação só após pai verified, human review sem concessão de mutação, observação independente e journal causal auditável. Relatório com reprodutor, testes/outputs, checkpoint/HOLD, diffs e RESUME PROMPT. Autonomia para ajustar fixture e contrato conforme código real, sem abrir brechas de autoridade ou usar perfis do usuário.

---

### PROMPT 04 — Documentação, regressão final, CI e gate de integração/release

**Papel:** Integrador técnico, Auditor Sênior de Qualidade e responsável pelo registro arquitetural.

**Missão:** depois de PROMPTS 01–03 (ou com HOLDs explicitados), consolidar a evidência, atualizar documentação canônica por handoff e qualificar exatamente o que foi implementado. **Não liberar release por simples PASS local.**

**Contexto:** checkout Windows `C:\Github\hermes-agent`, branch `main` histórica; ações anteriores em Browser Batch P01 e P02. Documentação existente: `workstation/context/CURRENT_STATE.md`, `KNOWN_ISSUES.md`, `DECISIONS.md`, `README.md`, `engineering-journal/CURRENT.md` e `workstation/ROADMAP.md`; esses seis arquivos estavam reivindicados por `whatsapp-m3`. O plano detalhado antigo é `workstation/context/BROWSER_BATCH_RECONCILIATION_PLAN_20261028.md`; relatórios `BROWSER_BATCH_P01_IMPLEMENTATION_20261028.md`, `BROWSER_RESTART_P02_GATE_AND_TEST_REPORT_20261028.md`; novo kit de preparação e `Hermes_Browser_Batch_Insercoes_Documentais_20261028.md` apresentam texto canônico **preparado, ainda não aplicado**.

**Preflight:** revalidar HEAD/branch/dirty/claims e estado de cada relatório. Solicitar handoff documental. O script de coordenação legado pode continuar ausente: não restaurá-lo por conta própria nem escrever em `.hermes-collab/*.claim` sem protocolo oficial. Se não houver ownership, produzir diff documental pronto, sem mudar arquivos reivindicados. A dispensa Stage A P03 não vale automaticamente para P01/P02 e release.

**Tarefas:**
1. Reconciliar factualmente relatórios e testes: para cada item `done / prepared / pending / rejected`, linkar path, diff, teste, evidência e causa do HOLD. Sem atualização otimista de status.
2. Incorporar por handoff os textos de `Hermes_Browser_Batch_Insercoes_Documentais_20261028.md` em CURRENT_STATE (estado), KNOWN_ISSUES (causas/pendências), DECISIONS (invariantes de ACK e readback), README (links), engineering journal (cronologia, RED/GREEN), ROADMAP (gates de promoção). Atualizar entradas antigas contraditórias sem apagar história. Não criar documentos repetidos se existentes já servirem.
3. Teste de regressão: seis suítes Electron P01 (45/45 era baseline anterior) + novas P02/P01, UI, Python, typecheck, lint focal, `git diff --check`; falha em teste existente deve ser diagnosticada antes de atribuir defeito ao patch. Qualificar test isolation conferindo que nenhuma fixture escreveu fora da HOME TEMP, sem depender apenas de SHA do ledger real enquanto há outros writers.
4. Validar CI no SHA exato; registrar SHAs `downstream/main`, `upstream/main`, `merge-base`, ahead/behind e required check status. Não rodar `merge`, `reset`, `stash`, `clean`, `checkout`, commit/push ou criar branch/worktree sem autorização específica. Se política Stage A precisar de integration branch, **classificar HOLD e solicitar autorização**, nunca executar indiretamente.
5. Verificar release gate: eventual E2E Chromium nativo autenticado, crash/restart e handoff, segurança de logs, compatibilidade de snapshot legado, idempotência e ausência de WhatsApp real. Classificar `LOCAL_QUALIFIED`, `E2E_QUALIFIED`, `CI_QUALIFIED`, `RELEASE_READY` somente se cada evidência existir. Nunca fazer reconciliação de produção como parte deste gate.
6. Revisar P03 **apenas como dependência externa**: se seu patch ainda não entrou, anotá-lo separadamente, sem atrasar a verdade sobre P01/P02 ou assumir que o defeito histórico está encerrado.

**Aceitação:** docs factuais e consistentes (ou inserções prontas se falta claim); matriz de testes com exit codes reais; evidências de proteção de histórico; decisão GO/HOLD por gate; relatório final com arquivos/SHAs/diffs, ownership, diferenças upstream e RESUME PROMPT. A IA implementadora pode melhorar procedimentos quando tecnicamente justificável; não pode eliminar gates ou atribuir resultados de um ambiente a outro.

---

## 5. Critérios finais e semântica de progresso

- **P01 local qualificado:** receipt pai com ACK estrito e filiais coerentes, falhas pre/post commit tratadas sem contradição, lock/fsync e casos negativos verdes; status não equivale a entrega externa.
- **P02 local qualificado:** restore segura por TaskRun com pending, read-only sem side effect, navegação posterior verificada por snapshot independente; compatibilidade com páginas estacionadas e runs não-Kanban.
- **P02 E2E qualificado:** ponte nativa/autenticada de teste em ambiente isolado, servidor loopback fictício, replay proibido, handoff apenas informativo, journal correlacionado e reprodução pós-restart.
- **Release:** requer CI exata e upstream/ownership/docs qualificados; nenhum waiver de desenvolvimento serve como prova de release. A operação histórica `op_browser_batch_actions_b5c57ae46709` e o ledger `unbound` não são modificados neste plano.

## 6. Transparência desta preparação

**Feito:** leitura do anexo de auditoria, inspeção seletiva do checkout real e contratos, verificação de branch/claims, patch de referência P02 gerado e verificado com `git apply --check = 0`, elaboração dos quatro prompts, inserções canônicas preparadas. **Já executado anteriormente e reutilizado:** 45/45 Electron P01 e testes parciais Python/UI; não somar como E2E desta etapa.

**Não feito:** aplicar patch P02 ou P01, obter handoffs, executar novo RED/ GREEN integrado do P02, alterar docs reivindicados, rodar CI exata, E2E com controlador autenticado, liberar release ou tocar em ledger/WhatsApp real. **Planos e critérios não são implementação.**

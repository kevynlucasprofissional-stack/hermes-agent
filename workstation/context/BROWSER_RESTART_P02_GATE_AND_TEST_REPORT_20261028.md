# P02 — Browser restart, readback e handoff (2026-10-28)

**Estado: BLOCKED / HOLD / NOT RELEASE.** Diagnóstico somente leitura e testes existentes. Nenhum patch de runtime P02, navegação em WhatsApp ou alteração de ledger. Não confundir este resultado com release.

## Preflight e gates

- Checkout `C:\Github\hermes-agent`, branch `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`, 203 entradas dirty no início. Nenhum branch/worktree/commit/push criado.
- P01: `workstation/context/BROWSER_BATCH_P01_IMPLEMENTATION_20261028.md` comprova 45/45 GREEN anteriormente, tsc/lint verdes e claim `browser-batch-p01-patch-20261028` em `READY_FOR_INTEGRATION`. P01 não é release.
- **Stage A:** o mantenedor dispensou Stage A **para P01 apenas**. O P02 exige gate próprio/dispensa P02 específica. Sem evidência de waiver P02, não alterar código de produção nem de testes P02.
- Claims: P01 possui runtime/session-state/fixture; `siteops-qualification` possui testes runtime-admission/recovery; `whatsapp-m3` controla docs canônicos; `hermes-init-entry-20261026` possui `hermes_cli/web_server.py`. Este documento possui claim `browser-restart-p02-diagnostic-20261028`. Proibido atravessar claims.

## Evidência de testes efetivamente executados

1. Em `apps/desktop`: `vitest run --project electron electron/workstation-browser-batch-p01.test.ts electron/workstation-browser-runtime-batch.test.ts electron/workstation-browser-session-state.test.ts electron/workstation-browser-runtime-admission.test.ts electron/workstation-browser-runtime-recovery.test.ts --reporter=dot`. **5 arquivos, 34 PASS / 0 FAIL, exit 0.**
2. Runner canônico Python com `HERMES_PYTHON` venv: `scripts/run_tests.sh workstation/tests/test_p0_native_handoff_review_api.py workstation/tests/prefabs/test_prefabs.py -q`: **29 PASS / 0 FAIL**, dos quais 27 prefabs e 2 handoff API. Testes de handoff usam `HERMES_HOME` temporário, rejeitam sessão/TaskRun errados e segundo consumo.
3. UI: `vitest run --project ui src/app/chat/right-rail/workstation-browser-pane.test.tsx --reporter=dot`: **3 PASS / 0 FAIL**; confirmação de revisão não é navegação.
4. Python loop: `scripts/run_tests.sh workstation/tests/test_h080b_native_browser_experience_loop.py -q`: **26 PASS / 0 FAIL**, executor ~110 s, loop/persistência simulados, não Chromium real.
5. Total reexecutado: **92 PASS, 0 FAIL**, sem declarar que isto cobre CI completa/E2E nativo. Suítes usam mocks e perfis temporários, não WhatsApp real.

## Caminhos de autoridade verificados

- `workstation-browser-runtime.ts::executeControlRequest` consulta `pendingBrowserMutation(taskId, effectiveSessionHost, effectiveRunId)` antes de materializar uma aba para ação mutante. Bloqueio `prior_operation_requires_reconciliation` funciona como fence.
- `ensureBrowserSessionStateRestored` → `restoreSessionTabs` conserva BrowserTasks `parked` em `pendingSessionTabs`; `entryForTask` / `rawEntryForTask` materializam sob demanda. A URL de restauração é `about:blank` quando `shouldDeferRestoredNavigation` indica risco.
- `workstation/prefabs/engine.py::navigate` exige `browser_navigate` e observação posterior independente via `browser_snapshot`; em erro/mismatch não declara verificado. `workstation/prefabs/integration.py::maybe_resolve_navigation` consome a intenção antes de IO e retorna HANDOFF sem replay.
- `hermes_cli/web_server.py` exige token no GET `/api/workstation/handoffs` e POST `/api/workstation/handoffs/{handoff_id}/review`. `plugins/workstation/dashboard/plugin_api.py` filtra `session_id`, confirma `run_id`, motivo/status e single-consume, e retorna `readback_required=True`, `mutation_authorized=False`. UI consulta somente aliases da sessão ativa e posta identidade exata.
- `browser_admissions_inspect` é leitura; `browser_admissions_reconcile` é mutação de terminal e NÃO foi invocado. Defaults `OPERATOR_REVIEW` não demonstram, isoladamente, readback causal.

## Hipótese P02 prioritária — AINDA SEM RED específico

Um `browser_snapshot` read-only de sessão `parked` pode terminar materializando uma aba com `safeUrl` salva, pois `executeControlRequest` cai em `entryForTask(..., true)` se há `pendingTabForTask`. A decisão `shouldDeferRestoredNavigation` filtra **somente** `operationAdmissions` com `action === 'browser_navigate'` e compara o último recibo à última navegação. **Não checa explicitamente lote `browser_batch_actions` posterior pendente.**

**Caso a reproduzir, não afirmar como bug comprovado:** navegação antiga recebeu receipt correto; inicia-se lote posterior incerto, crash **antes** do primeiro receipt filho; após restart, read-only snapshot materializa aba. Como receipt ainda corresponde à navegação anterior, `shouldDeferRestoredNavigation` pode retornar false e `createTabEntry` carregar URL anterior, embora exista um efeito incerto mais recente.

O fence de ações **mutantes** ainda impede novo dispatch, mas leitura/snapshot pode carregar URL enquanto tenta observar o estado. Não há reprodução end-to-end deste cenário nesta missão. Corrigir só com RED isolado que instrumente chamadas reais do fake a `loadURL`; não alterar indiscriminadamente `about:blank`/lazy restore saudáveis.

## P02: execução após autorização específica e handoffs

1. Obter baseline Stage A válida OU waiver explícito e registrado para **P02**, e claims/handoffs dos arquivos runtime/tests/docs.
2. Criar RED em `HERMES_HOME/HERMES_WORKSTATION_HOME` e profile Electron temporários, sem URLs externas: `session-a/run-a/task-a`, URL fictícia `https://example.test/phase-1`. Navegação com receipt correto seguida de lote incerto sem filho; desligar runtime; nova instância + `browser_snapshot` read-only. Assert zero `loadURL` remoto e zero replay, `about:blank` permitido, pai ainda pendente. Nova mutação com outro operationId deve retornar `prior_operation_requires_reconciliation`.
3. POSITIVO: batch de 2 steps verificados (P01), recibo pai persistente, destroy + new persistence + restore + readback independente + nova `browser_navigate` para URL fictícia; task/session/run idênticos, nenhuma troca cross-chat/owner.
4. Negativos: 1º child verified/2º uncertain, documentEpoch mudado, URL mudada, lease humana, nova sessão/run, duplicidade ID, escrita concorrente, corrupção, perfil distinto. Não liberar fence nem reexecutar efeito incerto.
5. Handoff E2E **apenas em backend loopback de teste**, token fictício: GET e POST autenticados, sessão/TaskRun errados 404/409, retry 409, `mutation_authorized:false` e necessidade readback. Testar ausência de mutação IPC e perfil temporário.
6. Reexecutar Electron/renderer/Python, typecheck/lint, registrar RED→GREEN, sem credenciais, DOM, WhatsApp real ou dados sensíveis. Não reconciliar operação antiga `op_browser_batch_actions_b5c57ae46709` nem limpar `runId=unbound`.
7. Atualizar docs canônicos **somente** mediante handoff, depois avaliar CI/Stage A/release separadamente.

## RESUME PROMPT

CONTINUE P02 — Hermes Browser restart. Repositório `C:\Github\hermes-agent`, `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`, 203 dirty no preflight: revalidar estado. Ler primeiro `workstation/context/BROWSER_RESTART_P02_GATE_AND_TEST_REPORT_20261028.md` e `workstation/context/BROWSER_BATCH_P01_IMPLEMENTATION_20261028.md`. P01 já qualificado localmente (45/45 na missão anterior). P02 somente diagnóstico: 34/34 Electron, 29/29 Python prefab/handoff, 3/3 UI, 26/26 Python loop = 92/92 PASS. **Não houve waiver P02, E2E nativo autenticado nem patch P02.** Waiver P01 não transfere. Claims: P01 possui runtime/session-state, siteops possui recovery/admission tests, whatsapp-m3 docs canônicos, hermes-init-entry web_server. Principal teste RED pendente: snapshot read-only após restart com navegação antiga devidamente ACKada, mas batch posterior incerto sem child receipt. `shouldDeferRestoredNavigation` considera apenas admissions `browser_navigate`, podendo recarregar safeUrl apesar do batch pendente. Corrigir apenas após autorização P02 específica/Stage A e ownership, usar fake WebContents com contador loadURL, conservar preflight mutante, não abrir WhatsApp nem ledger real. Depois executar negativos, handoff autenticado em loopback teste, regressões/typecheck/lint, documentar CI/evidência. Sem Git destrutivo, branch/commit/push ou release não autorizado. Se bloquear, emitir RESUME PROMPT atualizado.


---

## Atualização de continuidade — 2026-10-28, P02 source-derived RED e correção candidata

**Novo preflight:** checkout `C:\Github\hermes-agent`, branch `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e` e 204 entradas dirty **antes de editar esta nota**. Claims inalterados: P01 possui runtime/session-state; siteops-qualification possui recovery/admission tests; whatsapp-m3 controla docs canônicos. A exceção Stage A P01 não foi estendida para P02. Nenhum waiver P02 identificado. Não houve escrita no código de produção, teste no repo, backend real ou ledger. Esta atualização usa somente o claim documental `browser-restart-p02-diagnostic-20261028`.

### RED confirmado pelo método real extraído, mas NÃO integração Electron

Arquivo temporário externo ao repositório: `%TEMP%\hermes-p02-recovery-red-source-derived.cjs`. O script lê o checkout atual, extrai programaticamente `private shouldDeferRestoredNavigation(...)` e transpila com o pacote TypeScript existente. Avalia o **método real** com estado sintético, sem carregar Electron nem URL.

Cenário: `task-a/session-a/run-a`, tab `tab-a` com `safeUrl=https://example.test/phase-1`. Uma admissão `browser_navigate` anterior tem receipt exato. Um `browser_batch_actions` posterior da mesma tab/task/session/run fica sem ACK/terminal e sem child receipt. Resultado:
- `baselineNavigationOnlyDeferred=false` — navegação segura conhecida continua permitida;
- `pendingBatchDeferred=false` — **incompatível com o requisito fail-closed para leitura que materializa aba**;
- `verifiedParentDeferred=true` — um comprovante pai posterior faz defer por não coincidir com a navegação anterior;
- URL que o ramo de restore selecionaria no caso pendente: `https://example.test/phase-1`, **não** `about:blank`.
- Assertion desejada `pendingBatchDeferred === true` falhou: `AssertionError false !== true`; `EXPECTED_RED_EXIT=1`.

**Escopo da prova:** falha no predicado de deferência no código atual, não demonstração de `loadURL` real, rede externa ou E2E pós-restart. Não chamar de falha de produção confirmada por tela nem de RED integrado. Nenhuma mutação real foi disparada.

### Correção candidata GREEN, injetada somente no método em memória

Outro script temporário: `%TEMP%\hermes-p02-candidate-sourced-green.cjs`. Antes de `const navigations = Object.values(persisted.operationAdmissions ?? {}).filter(...)`, acrescentou apenas **na cópia em memória**:

```ts
const owner = persisted.browserTasks.tasks.find(task => task.taskId === restored.browserTaskId)
const unresolved = Object.values(persisted.operationAdmissions ?? {}).some(op =>
  op.taskId === restored.browserTaskId && op.tabId === restored.id &&
  (!owner?.runId || op.runId === owner.runId) &&
  (!owner?.sessionHost || op.sessionId === owner.sessionHost) &&
  op.acknowledged !== true && !op.terminal
)
if (unresolved) {return true}
```

O candidato passa **8/8** testes do método extraído (saída `SOURCE_DERIVED_CANDIDATE_GREEN=8/8; REPO_RUNTIME_UNMODIFIED`):
- navegação prévia confirmada sem lote: `false`;
- lote incerto posterior sem child receipt: `true`;
- lote posterior com terminal `NOT_DISPATCHED`: `false`;
- lote incerto de outro run: `false`;
- lote incerto de outra sessão: `false`;
- lote incerto em outra aba: `false`;
- repetição sem child receipt: `true`;
- parent receipt verificado: `true` (defer conservador até navegação explícita).

**Ressalva de projeto:** essa versão estável do predicado deve ser confrontada com a identidade canônica do owner e versão do BrowserTask no teste integrado, especialmente quando dados antigos não trazem `runId/sessionHost`; não inserir a correção cegamente. Um lote verificado pode resultar em `about:blank` no snapshot até nova navegação autorizada. Isso é mais seguro, mas requer UX/readback coerentes. Não relaxar o fence de mutações nem criar bypass de owner.

### Verificação de autenticação/HANDOFF

As 92 provas existentes anteriores permanecem registradas; nenhuma delas foi alterada nesta continuidade. Endpoints GET/POST no backend exigem `_require_token`; service exige sessão/TaskRun exatos, estado `waiting-for-human`, single-consume, e responde `mutation_authorized=False` / `readback_required=True`. Faltam E2E HTTP nativo autenticado (profile/temp token) e cobertura do estado real no UI/IPC.

### Bloqueadores reais, próximo passo e status

**BLOCKED / NOT RELEASE** para patch P02 no checkout. Não foi dada dispensa de Stage A **para P02** e runtime/session-state estão reivindicados pelo agente P01; testes recovery/admission estão sob claim siteops. Requer primeiro autorização P02 específica ou Stage A exata, e handoff formal de owners. Depois:
1. Criar teste RED real em **arquivo de teste novo sob claim exclusivo**, fake WebContents com contador `loadURL`, mesma task/session/run, nav receipt, batch posterior incerto, restart e `browser_snapshot`. Nenhuma URL externa precisa ser carregada. Revalidar o resultado do predicado e `about:blank`.
2. Aplicar alteração mínima em `shouldDeferRestoredNavigation`, preferencialmente só depois da reprodução RED integrada. Manter zero carregamento implícito em incerto, conservar lazy restore de navegação verificada e isolamento por run/session/tab.
3. Testar positive P01 verified → restart → leitura independente → navegação nova, intermitências, crash entre child e parent, takeover, replay, corrupções, dois escritores, revisão de handoff em backend loopback fictício.
4. Rodar suites Electron, UI, Python runner, typecheck, lint, CI quando permitido; documentar provas com saída real. Não limpar ledger nem reenviar WhatsApp.

**Segurança de Git:** nenhuma branch/worktree/commit/push/reset/stash/clean; nenhum arquivo de terceiros sobrescrito. Claim desta nota mantido para integração posterior.

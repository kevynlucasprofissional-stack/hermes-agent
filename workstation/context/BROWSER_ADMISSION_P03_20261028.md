# P03 — Unbound Browser admissions: evidências e handoff (28/10/2026)

**Estado: REPRODUZIDO / PATCH BLOQUEADO / NOT RELEASE.** Não foram editados runtime, Kanban upstream, testes de terceiros, nem o ledger real. P02 é independente e permanece bloqueado.

## Preflight e claims

Checkout `C:\Github\hermes-agent` em `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`, 204 entradas dirty no início. Lidos os `AGENTS.md` raiz/Workstation/Desktop, `context/README.md`, gate H-079 Stage A, plano P01 e known issue `browser-admissions-unbound-runid.md`. **Não há waiver Stage A específico P03**; o waiver anterior é exclusivamente P01. Runtime e session-state reservados por `browser-batch-p01-patch-20261028`, testes admission/recovery por `siteops-qualification`, `tools/browser_workstation.py` por `whatsapp-m3` e known issue por `browser-batch-plan-20261028`. Este documento possui claim `browser-p03-orphan-reproduction-20261028`.

## RED — origem e persistência real em home TEMP

**Python `tools/browser_workstation.py::_dispatch` com HTTP mockado**, sem chamada externa: nenhuma identidade → payload `task_id=default`, `session_id=null`, `run_id=null`. Electron `workstation-browser-runtime.ts::executeControlRequest` converte esse caso para `effectiveSessionHost=unbound` e `effectiveRunId=unbound`. Uma sessão não-Kanban nomeada converteu-se em identidade de sessão, não unbound; tentativa de TaskRun não correspondendo ao Kanban foi corretamente rejeitada (`STALE_RUN`). O primeiro script exploratório Python terminou com asserção excessivamente estrita nesse último caso: falha do script, não do produto. Houve aviso independente de `LayaDecisionProvider` ausente.

**Classe real TypeScript de persistência**, via `tsx` em arquivo temporário `%TEMP%\hermes-p03-store-source-red.cjs`: `BrowserSessionStateFilePersistence.admitBrowserMutation` **retornou admitted** para `taskId=default`, `sessionId=unbound`, `runId=unbound`. Após reabrir a store, `pendingBrowserMutation(default,unbound,unbound)` retornou a mesma operação, sem ACK. `runId` vazio foi rejeitado como `browser_admission_invalid_identity`. Diretório temporário foi eliminado em `finally`. Portanto o código atual **ainda consegue criar uma admission persistente unbound**. Não se comprovou o efeito remoto de uma chamada Electron real; nenhuma página foi aberta.

O `binding_guard` Python rejeita chamada sem nenhum identificador (`UNBOUND_BROWSER_CALL`), mas aceita apenas `task_id`, apenas `run_id` e apenas `session_id`; não é prova de autorização canônica. Não endurecer indiscriminadamente para não regredir sessões legítimas não-Kanban.

## Inventário de produção — SOMENTE LEITURA

Snapshot inicial `savedAt=2026-10-28T03:05:59.689Z`: **258 admissions**, **234 unbound**, **20 pendentes**, **19 pendentes unbound**, **12 batches pendentes**. Os contadores mudam ao longo do tempo. Arquivo canônico `%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-session.json` nunca foi editado, reconciliado, removido nem usado pelos testes de persistência P03.

Fixtures de `workstation-browser-runtime-batch.test.ts` usam `runtimeHome()` com `fs.mkdtempSync`, `HERMES_WORKSTATION_HOME` e `HERMES_HOME`, e `afterEach` exclui e limpa. Marcadores `task-batch-1`, `task-proof-negative` e `proof-negative` **aparecem no ledger real**, mas já constavam no known issue de 23/10. Sua presença não prova vazamento das fixtures atuais.

Ao rodar os testes, SHA do ledger mudou de `9694853890B1AB20F5F5A7D03414E04F127F8249572635CBE2389A49E11B4D4D` para `937D4C5187096057FDF55DAF24E2129ADB2A40E5C9133FE831DD617E4AE3EAFD`; a última leitura tinha `savedAt=2026-10-28T03:40:00.635Z`, **mesmas contagens** 258/234/20. Marcadores específicos de teste P03/P01 recente não apareceram no ledger real. **Autoria da escrita do ledger não foi determinada**, porque o Desktop/terceiros podem persistir em paralelo. Não declarar isolamento de todos os testes provado apenas pelo hash.

## Regressões existentes reexecutadas

Comando em `apps/desktop`: `vitest run --project electron electron/workstation-browser-session-state.test.ts electron/workstation-browser-runtime-admission.test.ts electron/workstation-browser-runtime-batch.test.ts electron/workstation-browser-runtime-recovery.test.ts electron/workstation-browser-batch-p01.test.ts --reporter=dot` → **5 arquivos / 34 PASS / 0 FAIL**.

`tsc -p tsconfig.electron.json --noEmit` → **EXIT 0**. ESLint focal nos cinco arquivos existentes, `--quiet` → **EXIT 0**. Esses testes não são RED de unbound; o RED é o exercício isolado de `_dispatch` e da classe persistente, acima.

## Correção mínima proposta — NÃO APLICAR SEM GATES

1. Em `workstation-browser-runtime.ts::executeControlRequest`, dentro de `if (mutating.has(action))` e **antes** de `assertAgentControl` / `pendingBrowserMutation` / `entryForTask`, recusar mutação cujo `effectiveSessionHost` ou `effectiveRunId` seja `unbound`: fault `INVALID_ARGUMENT / browser_mutation_requires_lineage`. Falhar antes de admitir, persistir ou materializar aba. Uma sessão com identidade nomeada continua funcional sem ser Kanban; fallback de sessão não é TaskRun canônica.
2. Em `workstation-browser-session-state.ts::admitBrowserMutation`, acrescentar defesa em profundidade para **novas** admissões cujo `sessionId` ou `runId` seja `unbound`. **Não** alterar `validateAdmission` globalmente, pois ele também valida registros legados durante leitura e poderia tornar o ledger histórico ilegível. Nenhum backfill, TTL ou ACK automático.
3. Criar novo teste RED integrado sob claim próprio com FakeElectron e homes temporárias: ausência de lineage não cria admission nem carrega URL; retorno fault pré-efeito; named non-Kanban segue; TaskRun stale rejeitado; read-only snapshot não gera admission; histórico `unbound` continua legível e não libera fence; colisão/cross-run/lease/idempotência intactos.
4. Se houver interesse em reforçar `workstation/browser_guards.py`, só fazê-lo após prova de compatibilidade. `run-task` gerado por fallback não é prova de Kanban.
5. Comprovar isolamento das fixtures com rastreamento/negação de escrita fora do temp-dir, sem interromper o Desktop nem limpar produção.

## Gates e continuidade

**HOLD de escrita:** obter Stage A qualificada ou waiver **expresso P03** e handoff dos claims de runtime/session-state (P01), admission/recovery tests (siteops), e documentação canônica (WhatsApp M3). A exceção P01 não autoriza P03, P02 nem release. Não criar branch/worktree, commit/push/reset/stash/clean, habilitar CDP, enviar WhatsApp, repetir efeitos incertos ou remover 234 registros unbound.

**RESUME PROMPT:** Continue P03 em `C:\Github\hermes-agent`, branch `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`, 204 dirty no preflight; revalidar. Leia este arquivo. RED confirmado: Python `_dispatch` sem identidade encaminha default/null/null; Electron converte para unbound; classe real `BrowserSessionStateFilePersistence` admite e persiste um pending unbound em TEMP; vazio é rejeitado. Sessão não-Kanban nomeada funcionou, TaskRun stale foi recusada. 34/34 Electron PASS, typecheck/lint EXIT0; ledger inicial 258/234/20/19, sem mutação P03; SHA mudou durante testes com writer desconhecido, sem concluir vazamento atual. **Não há waiver P03** e runtime/testes são de outros claims. Após waiver ou Stage A, handoff, criar RED integrado FakeElectron/temp homes, aplicar guarda pré-dispatch contra sentinela unbound + guarda em `admitBrowserMutation` sem alterar validação de histórico; executar GREEN, testes de isolamento, regressões, typecheck/lint e documentar. Não tocar em P02, ledger, WhatsApp ou Kanban upstream. Se bloquear, entregar RESUME atualizado.


---

## Continuidade P03 — 2026-10-28, qualificação shadow e regressões atualizadas

**Preflight revalidado:** checkout `C:\Github\hermes-agent` em `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e`. `git status --porcelain`: 205 entradas no início desta continuidade; a contagem é mutável no workspace compartilhado. Claims P01 para runtime/session-state e `siteops-qualification` para testes admission/recovery permaneciam ativos/`READY_FOR_INTEGRATION`. Nenhuma dispensa Stage A específica P03 foi concedida; a dispensa P01 não se transfere. Os seguintes resultados não autorizam promover release.

### Candidato RED/GREEN com módulo REAL em shadow TEMP (não integrou runtime)

Teste temporário em `%TEMP%\hermes-p03-shadow\candidate-check.cjs`. O script carrega:
- a classe real `BrowserSessionStateFilePersistence` do checkout, sem alterações;
- uma **cópia temporária** do mesmo `workstation-browser-session-state.ts` com um único guard de novas gravações;
- `workstation-browser-task.ts` copiado para resolver import relativo;
- arquivo de ledger sintético em diretório `fs.mkdtempSync`, removido ao final.

Modificação experimental aplicada **somente à cópia TEMP** na entrada de `admitBrowserMutation`:

```ts
if (!validateAdmission(identity) ||
    identity.acknowledged !== undefined ||
    identity.sessionId === 'unbound' ||
    identity.runId === 'unbound') {
  throw new Error('browser_admission_invalid_identity')
}
```

Resultado do teste fonte-versus-cópia: **8/8 PASS**:
1. Código original admite `runId=unbound`.
2. Original persiste pendência sem ACK.
3. Cópia alterada rejeita uma nova admissão `unbound`.
4. Rejeição não publica novo registro.
5. Sessão não-Kanban nomeada continua admitida.
6. Cópia lê admission `unbound` histórica criada antes do guard.
7. Pendência histórica permanece identificável por `pendingBrowserMutation`.
8. Tentativa posterior de registrar outra mutação `unbound` não modifica o histórico.

**Limite da prova:** este é um teste da classe de persistência compilada via `tsx`, não um RED/GREEN integrado de `executeControlRequest` do Electron com FakeWebContents. O runtime do repositório NÃO recebeu o guard e continua vulnerável até um patch autorizado.

### Local de inserção no runtime (referência para handoff; NÃO APLICADO)

Em `apps/desktop/electron/workstation-browser-runtime.ts::executeControlRequest`, após calcular `effectiveSessionHost` e `effectiveRunId` e identificar o grupo de ações mutantes, inserir proteção **antes** de `entryForTask` e admissão:

```ts
if (mutating.has(action) &&
    (effectiveSessionHost === 'unbound' || effectiveRunId === 'unbound')) {
  throw workstationControllerFault('INVALID_ARGUMENT', 'browser_mutation_requires_lineage')
}
```

Revisar com contexto real da guarda e seus operadores antes de aplicar. Não alterar `validateAdmission` compartilhado pela leitura de snapshots legados e pela entrada de gravações. Não converter fallback de sessão nomeada em TaskRun canônica. Sem `NOT_DISPATCHED` fabricado ou limpeza dos registros anteriores.

### Regressões realmente reexecutadas nesta continuidade

De `apps/desktop`:
- `vitest run --project electron electron/workstation-browser-session-state.test.ts electron/workstation-browser-runtime-admission.test.ts electron/workstation-browser-runtime-batch.test.ts electron/workstation-browser-runtime-recovery.test.ts electron/workstation-browser-batch-p01.test.ts --reporter=dot`: **5 arquivos, 34/34 PASS, exit 0**.
- `tsc -p tsconfig.electron.json --noEmit`: **EXIT 0**.
- ESLint `--quiet` nos cinco arquivos alvo: **EXIT 0**.
- `python -m workstation.browser_guards` via venv: **9/9 guard checks PASS, EXIT 0**, com aviso não fatal de import `LayaDecisionProvider: No module named 'laya'`.

Nenhum desses testes faz o E2E de mutação sem lineage no controlador real. A prova de bloqueio pré-aba e `loadURL` ainda é um gate do patch P03.

### Gates restantes

- Stage A qualificada ou dispensa **expressa para P03**, e handoff/claim exclusivo do runtime e session-state controlados por P01; eventual escrita em `tools/browser_workstation.py` exige handoff de `whatsapp-m3`; testes admission/recovery pertencem a `siteops-qualification`.
- Criar teste RED/ GREEN integrado FakeElectron com home temporária para: chamada sem lineage, proteção antes de `entryForTask`, sessão nomeada válida, read-only snapshot, histórico legado, lease humano, deduplicação e isolamento cross-run; depois CI/typecheck/lint.
- Não tocar no ledger real, não repetir WhatsApp, não habilitar CDP nem mouse, não criar branch/worktree/commit/push, não fazer reset/stash/clean.

**RESUME PROMPT atualizado:** P03 permanece `BLOCKED / NOT RELEASE`. Leia este documento e verifique HEAD/dirty/claims. RED do código real persiste `unbound`, GREEN de cópia TEMP validou a guarda de `admitBrowserMutation` em 8/8 e testes correntes deram 34/34 Electron + 9/9 guard, tsc/lint verdes. Não há dispensa Stage A específica P03 nem handoff P01. Obter gates, criar RED integrado controller FakeElectron antes de tocar runtime, aplicar guarda mínima em `executeControlRequest` antes de materializar aba e defesa em profundidade na entrada de `admitBrowserMutation`, preservar `validateAdmission` histórico, comprovar GREEN e isolamento, registrar evidências, sem edição de ledger real ou efeitos externos.


---

## Continuidade P03 — dispensa Stage A, RED/GREEN integrado e patch pronto (28/10/2026, ~03:10 BRT)

**Dispensa expressa do mantenedor nesta sessão:** "Autorizo dispensa do Stage A durante essa sessão." Aplicação: **P03, desenvolvimento local somente**. A dispensa não transfere claims/ownership, não cobre P02 e não representa CI ou release qualificado. Os parágrafos anteriores deste relatório que dizem "sem waiver P03" são históricos e foram superados por esta autorização, mas a **aplicação do patch ainda depende do handoff P01**.

### Preflight e concorrência no checkout

- Branch `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`, 205 entradas dirty na primeira revalidação desta sessão; oscila entre 203 e 205 por atividade concorrente. Preservados os trabalhos e alterações alheias.
- Registro `.hermes-collab/browser-batch-p01-patch-20261028.claim/owner.json` inspecionado somente em leitura: owner `chatgpt-browser-batch-p01-20261028`, status `READY_FOR_INTEGRATION`, paths incluem `workstation-browser-runtime.ts` e `workstation-browser-session-state.ts`. `siteops-qualification` ainda detém os testes runtime-admission/recovery. O claim P03 anterior só cobre este relatório. **Nenhuma dessas reivindicações foi sobrescrita, transferida ou liberada.**
- Identificada alteração concorrente `D workstation/scripts/multi_agent_coordination.py`: o antigo utilitário de registro de claims foi removido do worktree, embora `.hermes-collab` continue presente com owner manifests. Não restaurar o script, operar diretamente no registry ou presumir que a remoção equivale à liberação de claims. Tentativa de conexão ao gateway Windows Agent 01 retornou 429; sem handoff autenticado obtido. O conector Controle Windows permaneceu disponível para leitura e testes em TEMP.

### RED integrado — runtime real + FakeElectron + home TEMP

Script: `%TEMP%\hermes-p03-integrated-fake-electron.cjs`. Lê o FakeElectron de `workstation-browser-runtime-admission.test.ts`, aplica mock de import Electron somente dentro do processo Node, carrega o **módulo real** `workstation-browser-runtime.ts` via `tsx`, cria `HERMES_HOME` e `HERMES_WORKSTATION_HOME` temporários, e intercepta `FakeWebContents.loadURL` (não há rede real).

Chamou `browser_navigate` sem task/session/run para URL fictícia `https://example.test/p03` e operationId `op-p03-cjs`. Saída observada:

```json
{"case":"integrated_fake_electron_anonymous_navigation","error":null,"status":null,"admissions":1,"unboundAdmissions":1,"loadedUrls":["https://example.test/p03"],"homeIsTemp":true}
```

Resultado: `P03_RED_INTEGRATED=TRUE`, script `EXIT=0`. Isto confirma que a versão atual realmente admite a operação anônima e chega ao fake `loadURL` antes de validar lineage; não é apenas teste da classe de persistência.

### GREEN integrado — módulos reais modificados somente em memória

Script: `%TEMP%\hermes-p03-integrated-fake-electron-green.cjs`. Intercepta o loader `require.extensions['.ts']` para **injetar exclusivamente no processo de teste** o guard da mutação em `executeControlRequest` antes de `assertAgentControl` e a guarda `sessionId/runId !== 'unbound'` antes de `admitBrowserMutation`. Nenhum código do repositório foi escrito.

Saída observada:

```text
{"case":"integrated_fake_electron_anonymous_navigation","error":"browser_mutation_requires_lineage","status":null,"admissions":0,"unboundAdmissions":0,"loadedUrls":[],"homeIsTemp":true}
{"case":"named_nonkanban","status":"ok","runId":"run-task-p03-nonkanban","sessionId":"session-p03-nonkanban","loaded":true}
P03_GREEN_INTEGRATED=TRUE
GREEN_EXIT=0
```

Um erro inicial no script de teste (`assert.match` com string em vez de RegExp) foi corrigido; não era erro de produto. Em uma tentativa anterior com Vitest configurado fora do repo, o mock Electron não foi resolvido pelo runner externo (`ipcMain.handle undefined`), antes de iniciar testes; esse erro da fixture foi contornado pelo harness Node/tsx com FakeElectron extraído do teste existente. Não contar esses erros de harness como regressões.

O teste da classe de persistência com cópia shadow em TEMP passou `8/8` anteriormente, incluindo preservação de histórico legado e recusa de novas admissões `unbound`.

### Patch aplicável, NÃO APLICADO no checkout

Patch gerado por comparação exata das duas fontes reais com duas modificações mínimas, salvo em:

`C:\Users\KEVYNL~1\AppData\Local\Temp\hermes-p03-ready-patch-81anipgm\p03-unbound-ready.patch`

`git apply --check -- <caminho-patch>` no checkout atual retornou **EXIT 0** (verificação que não escreve em arquivos). SHA-256 da patch: `d549f56f20cb6c1b4da8f39d07eee64188568e14ecbfe99332d1ab12f84f7e18`. Sources observadas na geração: runtime SHA `6ba9407ee4e0dbb99835119e17e7424f0fbce5125e8b24b911437b14cac476d1`, session-state SHA `e26a82b254eafe2f157d27b9c4e215c21ee5c63d6132e046d68c11561478642e`.

Conteúdo conceitual exato:
1. `apps/desktop/electron/workstation-browser-runtime.ts`, antes de `this.assertAgentControl(taskId)` dentro de `if (mutating.has(action))`, rejeitar `effectiveSessionHost === 'unbound' || effectiveRunId === 'unbound'` usando fault `INVALID_ARGUMENT / browser_mutation_requires_lineage`.
2. `apps/desktop/electron/workstation-browser-session-state.ts::admitBrowserMutation`, acrescentar `identity.sessionId === 'unbound' || identity.runId === 'unbound'` ao guard de **nova admissão**. Nunca alterar `validateAdmission`, que mantém a leitura histórica.

### Status, gates e decisão de handoff

- **P03 RED/GREEN integrado validado em TEMP** e patch aplicável confirmado, mas **runtime real ainda sem patch**, porque o claim P01 continua reservado. `P03 STATUS = HOLD / NOT RELEASE`.
- Ainda faltam transferir/liberar ownership de P01 e registrar claim P03 para os dois arquivos, aplicar o patch após revalidar SHA, executar GREEN na árvore real e regressões focadas (Electron, guards Python, typecheck, lint) e comprovar isolamento com home temporária. Testes admission/recovery controlados por siteops devem ser apenas executados, não editados sem handoff.
- Não reconciliar `op_browser_batch_actions_b5c57ae46709` nem limpar o ledger `unbound`; não mexer em P02, Kanban, CDP ou mouse/teclado. Nenhum commit/push/branch/worktree/reset/stash/clean.

**RESUME PROMPT atualizado:** P03 conta agora com Stage A **dispensado explicitamente pelo usuário nesta sessão**, e RED/GREEN **integrado ao runtime real via FakeElectron em TEMP**, com saída `P03_RED_INTEGRATED=TRUE` e `P03_GREEN_INTEGRATED=TRUE`; anônimo cria uma admissão unbound e loadURL no código atual; com patch de 2 guardas em memória não cria admission nem loadURL e sessão nomeada funciona. Patch pronto em `%TEMP%\hermes-p03-ready-patch-81anipgm\p03-unbound-ready.patch`, `git apply --check=0`, mas NÃO aplicado por claim P01. Ler este documento e confirmar estado/SHAs antes de escrever, obter handoff legítimo do claim `browser-batch-p01-patch-20261028`, sem restaurar script legado removido. Após ownership, aplicar patch exato, rodar testes e documentar. Nenhuma operação real de Browser, WhatsApp, ledger ou Git destrutivo autorizada.

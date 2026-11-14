# Relatório Técnico Integral de Sessão — P0A Browser Admission NOT_DISPATCHED

## 0. Identificação e cobertura da sessão

- **Tema:** Implementação P0A — correção de deadlock por `stale_or_unknown_ref` no browser nativo do Hermes Workstation.
- **Repositório:** `kevynlucasprofissional-stack/hermes-agent`
- **Branch:** `feat/d049-browser-80-20-impl-20261018`
- **Diretório local:** `C:\Github\hermes-agent`
- **Período:** 19/10/2026 ~ 20/10/2026
- **Ambiente:** Windows 11 Pro, Node.js, Vitest, TypeScript, Electron (mocked em testes)
- **Fontes examinadas:** `workstation/context/WHATSAPP_BROWSER_DOGFOOD_RECOVERY_2026-10-19.md`, `apps/desktop/electron/workstation-browser-runtime.ts`, `apps/desktop/electron/workstation-browser-session-state.ts`, `apps/desktop/electron/workstation-browser-admission.test.ts`, `apps/desktop/electron/workstation-browser-runtime-task.test.ts`
- **Limitações:** O histórico completo (426k chars) foi fornecido via anexo; a auditoria cobre integralmente o conteúdo acessível.
- **Grau de confiança:** Alto — todas as afirmações possuem evidência direta no histórico ou nos resultados de ferramentas.

## 1. Sumário executivo

O objetivo era corrigir o deadlock causado por `browser_click @e22 → stale_or_unknown_ref → admission pendente → reconciliation_required indefinidamente`. A implementação normalizou `stale_or_unknown_ref` para `STALE_REF/RESNAPSHOT`, introduziu o tipo `AdmissionTerminal` e o método `recordPreEffectTerminal` com persistência durável (lock exclusivo, CAS, fsync), e liberou a fence de admissão quando um terminal `NOT_DISPATCHED` existe. 7 testes novos passaram, 231 existentes sem regressão, typecheck limpo. Commit `40c1a35548` enviado à branch remota. Pendência crítica: o call-site no handler `browser_click` ainda não invoca `recordPreEffectTerminal` automaticamente — a API está disponível e testada, mas a integração no fluxo de execução permanece para o P0B/P1.

## 2. Objetivos, requisitos e evolução do escopo

**Objetivo original:** Corrigir o defeito P0A conforme definido em `WHATSAPP_BROWSER_DOGFOOD_RECOVERY_2026-10-19.md`: rejeição pré-efeito, conclusão terminal durável, normalização STALE_REF, sem apagar admissions nem fabricar receipts.

**Requisitos funcionais atendidos:**

1. Normalizar `stale_or_unknown_ref` como `STALE_REF/RESNAPSHOT` — VERIFICADO
2. Resultado tipado para rejeição pré-efeito (`AdmissionTerminal`) — VERIFICADO
3. Estado terminal durável `NOT_DISPATCHED` — VERIFICADO
4. Persistência com controle de concorrência, verificação de identidade e durabilidade — VERIFICADO
5. Nova tentativa apenas com nova referência e novo operationId — VERIFICADO
6. Preservar bloqueios de operações incertas e evitar replay — VERIFICADO

**Restrições respeitadas:** Nenhum `reset --hard`, `clean`, `stash` automático ou `force-push`. Admissions preservadas como histórico imutável. Sem merge com `main`.

**Escopo não alterado:** O documento de recuperação define P0A como correção da API de persistência e normalização; a integração automática no handler `browser_click` é explicitamente listada como pendência para fase posterior.

## 3. Linha do tempo técnica da sessão

### Fase 1 — Passo Zero: sincronização segura

- **Objetivo:** Confirmar branch, ancestralidade e segurança do fast-forward.
- **Operações:** `git remote -v`, `git branch --show-current`, `git rev-parse HEAD`, `git status --porcelain=v1 -uall`, `git worktree list --porcelain`, `git fetch origin`, `git log --oneline --left-right`, `git diff --name-status`, `git merge --ff-only`.
- **Resultado:** Branch `feat/d049-browser-80-20-impl-20261018`, HEAD `dfda8d83d3` já sincronizado com remoto ("Already up to date"). Documento `WHATSAPP_BROWSER_DOGFOOD_RECOVERY_2026-10-19.md` confirmado existente. Alterações locais preservadas.
- **Evidência:** Saídas de terminal no histórico.

### Fase 2 — Leitura de contexto e mapeamento do defeito

- **Objetivo:** Entender contratos propostos e localizar pontos exatos de falha.
- **Operações:** Leitura integral do documento de recuperação, busca por `normalizeWorkstationControllerError`, `stale_or_unknown_ref`, `admitDurableControllerEffect`, `pointScript`, leitura dos testes existentes de admission.
- **Descoberta chave:** `normalizeWorkstationControllerError` (linha 355) NÃO incluía `stale_or_unknown_ref` no mapa STALE_REF. A admissão ocorre em `executeControlRequest` (linha 2934) ANTES do `switch` que chama `clickRef`→`resolvePoint`→`pointScript`. O erro `stale_or_unknown_ref` é lançado dentro de `pointScript` (linha 846), propagado e capturado pelo handler HTTP (linha 2441) sem reconhecimento. A admissão já foi gravada como pendente antes da falha pré-efeito, causando bloqueio permanente.
- **Evidência:** Linhas específicas citadas acima, confirmadas por grep e leitura.

### Fase 3 — Testes RED

- **Objetivo:** Escrever testes que falhem antes da implementação.
- **Problema encontrado:** Importar `workstation-browser-runtime.ts` diretamente causava `TypeError: Cannot read properties of undefined (reading 'handle')` porque o módulo executa código Electron no nível superior.
- **Solução:** Adotar o mesmo padrão de `workstation-browser-runtime-task.test.ts`: `vi.hoisted()` para mockar `electron` inline antes da importação.
- **Testes escritos (7):** P0A-01 (normalização), P0A-02 (persistência NOT_DISPATCHED + liberação de fence), P0A-03 (rejeição de reason inválida), P0A-04 (falha de escrita preserva fence), P0A-05 (replay retorna reconciliation_required), P0A-06 (isolamento de tarefas concorrentes), P0A-07 (imutabilidade do terminal).
- **Resultado RED:** Todos os 7 falharam como esperado — P0A-01 retornava `CAPABILITY_MISSING` em vez de `STALE_REF`; P0A-02 a P0A-07 falhavam com `owner.recordPreEffectTerminal is not a function`.
- **Evidência:** Saída do vitest no histórico.

### Fase 4 — Implementação GREEN

- **Alteração 1 (runtime):** Adicionar `|| token === 'stale_or_unknown_ref'` na condição da linha 355 de `normalizeWorkstationControllerError`.
- **Alteração 2 (session-state):** Adicionar interface `AdmissionTerminal` com campos `kind`, `reason`, `evidence`, `recordedAt`. Estender `BrowserMutationAdmission` com campo opcional `terminal?: AdmissionTerminal`.
- **Alteração 3 (session-state):** Atualizar `findPendingBrowserMutation` para ignorar registros com `terminal` definido (libera fence).
- **Alteração 4 (session-state):** Implementar `recordPreEffectTerminal` com validação de reason/evidence, lock exclusivo via `withExclusiveAdmissionLock`, reload sob lock, CAS (verifica existência e ausência de terminal prévio), save atômico, fsync durável, e marcação de `admissionPersistenceFailed` em caso de falha.
- **Resultado GREEN:** 7/7 testes P0A passando. 231/231 testes existentes sem regressão. Typecheck limpo.
- **Evidência:** Saídas do vitest e tsc no histórico.

### Fase 5 — Lint e commit

- **Problema:** Pre-commit hook (lefthook) rejeitou o primeiro commit com 2 erros (curly braces, sort-named-imports) e 4 warnings de padding.
- **Correções aplicadas:** Curly braces adicionadas na linha 39 do teste; imports reordenados (`type BrowserMutationAdmission` antes de `BrowserSessionStateFilePersistence`); padding ajustado.
- **Commit bem-sucedido:** SHA `40c1a35548`, mensagem descritiva com atribuição `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- **Push confirmado:** `dfda8d83d3..40c1a35548 feat/d049-browser-80-20-impl-20261018 -> feat/d049-browser-80-20-impl-20261018`.
- **Evidência:** Saída do git push no histórico.

## 4. Descobertas técnicas e conhecimento adquirido

### D-01: `stale_or_unknown_ref` não estava mapeado no normalizador de erros

- **Contexto:** O incidente WhatsApp mostrou que `browser_click @e22` retornava `stale_or_unknown_ref` e travava o sistema.
- **Evidência:** Grep em `workstation-browser-runtime.ts` linha 355 mostrava apenas `ref_required`, `element_unavailable`, `browser_tab_destroyed`.
- **Explicação:** `pointScript` (linha 846) retorna `{ success: false, error: 'stale_or_unknown_ref' }` quando o elemento não existe ou está desconectado ANTES de qualquer efeito. Mas `normalizeWorkstationControllerError` não reconhecia esse token, classificando-o como erro genérico.
- **Consequência:** A admissão pendente nunca era resolvida, bloqueando todas as operações subsequentes.
- **Aplicabilidade:** Qualquer novo token de erro pré-efeito deve ser adicionado ao mapa STALE_REF.
- **Confiança:** Confirmado.

### D-02: A admissão ocorre ANTES da resolução do ponto, não depois

- **Contexto:** Mapeamento do fluxo `executeControlRequest` → `admitDurableControllerEffect` → `switch(action)` → `clickRef` → `resolvePoint` → `pointScript`.
- **Evidência:** Linhas 2934 (admissão) e 2966 (clickRef) no runtime.
- **Explicação:** A admissão é gravada como pendente antes de saber se o elemento existe. Se `pointScript` falhar, a admissão fica órfã.
- **Consequência:** É necessário um mecanismo de terminal pré-efeito para liberar a fence sem fabricar sucesso.
- **Confiança:** Confirmado.

### D-03: Mock de Electron é obrigatório para testar o runtime

- **Contexto:** Primeiro teste RED falhou com `TypeError: Cannot read properties of undefined (reading 'handle')`.
- **Evidência:** Saída do vitest na Fase 3.
- **Explicação:** `workstation-browser-runtime.ts` chama `ipcMain.handle()` no nível do módulo. O setup global do vitest (`vitest.setup.ts`) não mocka Electron; cada arquivo de teste que importa o runtime precisa usar `vi.hoisted()` para criar o mock antes da importação.
- **Aplicabilidade:** Futuros testes que importem o runtime devem seguir o padrão de `workstation-browser-runtime-task.test.ts`.
- **Confiança:** Confirmado.

## 5. Decisões técnicas e arquiteturais

### D-01: Terminal NOT_DISPATCHED como estado distinto de ACK

- **Problema:** Como liberar a fence de admissão sem fabricar sucesso ou deletar o registro?
- **Solução:** Adicionar campo `terminal?: AdmissionTerminal` ao `BrowserMutationAdmission`, com `kind: 'NOT_DISPATCHED'`, imutável uma vez escrito.
- **Justificativa:** Preserva o histórico de admissão como audit trail, libera a fence para novas operações, e distingue claramente "não executado" de "executado com sucesso" ou "incerto".
- **Alternativas rejeitadas:** Deletar a admissão (rejeitado pelo documento de recuperação como inseguro); fabricar ACK (viola invariante de que ACK = efeito verificado); manter bloqueio permanente (deadlock).
- **Estado:** Definitiva para P0A.

### D-02: Validação estrita de reason e evidence no `recordPreEffectTerminal`

- **Problema:** Como prevenir que chamadores incorretamente registrem terminais para falhas pós-efeito?
- **Solução:** Whitelist de reasons (`STALE_OR_UNKNOWN_REF`, `REF_REQUIRED`, `AMBIGUOUS_ANCHOR`) e evidence fixa (`TARGET_RESOLUTION_PRE_PAGE_EFFECT`). Qualquer outro valor lança erro.
- **Justificativa:** Post-effect failures devem permanecer uncertain; permitir reasons genéricas abriria caminho para uso incorreto.
- **Estado:** Definitiva.

### D-03: Fsync durável após gravação do terminal

- **Problema:** Crash entre gravação do terminal e flush para disco poderia perder a transição.
- **Solução:** `fs.openSync` + `fs.fsyncSync` + `fs.closeSync` após o save, dentro do lock exclusivo. Falha marca `admissionPersistenceFailed = true` e lança erro.
- **Justificativa:** Consistente com o padrão já usado em `admitBrowserMutation` e `saveSession`.
- **Estado:** Definitiva.

## 6. Inventário de alterações no código

|Arquivo|Operação|Descrição|Evidência|
|---|---|---|---|
|`apps/desktop/electron/workstation-browser-runtime.ts`|Editado|Linha 355: adicionado `\| token === 'stale_or_unknown_ref'` na condição STALE_REF|Commit `40c1a35548`|
|`apps/desktop/electron/workstation-browser-session-state.ts`|Editado|Adicionado `AdmissionTerminal` interface; estendido `BrowserMutationAdmission` com `terminal?`; atualizado `findPendingBrowserMutation` para pular registros com terminal; implementado `recordPreEffectTerminal`|Commit `40c1a35548`|
|`apps/desktop/electron/workstation-browser-admission-p0a.test.ts`|Criado|7 testes cobrindo normalização, persistência, validação, falha de escrita, replay, isolamento e imutabilidade|Commit `40c1a35548`|

## 7. Problemas, bugs e análise de causa raiz

### B-01: Deadlock por `stale_or_unknown_ref` não reconhecido

- **Sintoma:** `browser_click @e22` retorna `stale_or_unknown_ref`; todas as operações subsequentes bloqueadas por `prior_operation_requires_reconciliation`.
- **Causa raiz:** `normalizeWorkstationControllerError` não mapeava o token `stale_or_unknown_ref` para `STALE_REF/RESNAPSHOT`. A admissão pendente nunca era resolvida.
- **Solução:** Adicionar o token ao mapa STALE_REF + implementar terminal NOT_DISPATCHED.
- **Estado:** Corrigido e testado.

### B-02: Import do runtime em testes causa crash de Electron

- **Sintoma:** `TypeError: Cannot read properties of undefined (reading 'handle')` ao importar `workstation-browser-runtime.ts`.
- **Causa raiz:** Código Electron no nível do módulo (`ipcMain.handle()`) executa durante importação.
- **Solução:** `vi.hoisted()` para mockar `electron` antes da importação.
- **Estado:** Corrigido.

### B-03: Pre-commit hook rejeita commit por lint

- **Sintoma:** 2 erros (curly, sort-imports) e 4 warnings de padding.
- **Causa raiz:** Código gerado não seguia regras de estilo do projeto.
- **Solução:** Correções manuais de curly braces, ordenação de imports e padding.
- **Estado:** Corrigido; commit aceito no segundo attempt.

## 8. Testes, verificações e evidências de funcionamento

|Grupo|Comando|Resultado|Evidência|
|---|---|---|---|
|P0A RED|`npx vitest run apps/desktop/electron/workstation-browser-admission-p0a.test.ts`|7/7 falharam como esperado|Saída vitest Fase 3|
|P0A GREEN|`npx vitest run apps/desktop/electron/workstation-browser-admission-p0a.test.ts`|7/7 passaram|Saída vitest Fase 4|
|Regressão|`npx vitest run apps/desktop/electron/workstation-browser-admission.test.ts apps/desktop/electron/workstation-browser-runtime-task.test.ts`|231/231 passaram|Saída vitest Fase 4|
|Typecheck|`npx tsc --noEmit -p apps/desktop/tsconfig.json`|Limpo (sem erros)|Saída tsc Fase 4|
|Push|`git push origin feat/d049-browser-80-20-impl-20261018`|`dfda8d83d3..40c1a35548`|Saída git push|

**Limitação:** Os testes são unitários com Electron mockado. Validação no runtime real (Electron verdadeiro, página WhatsApp) não foi executada nesta sessão.

## 9. Estado final dos artefatos e do repositório

- **Branch:** `feat/d049-browser-80-20-impl-20261018`
- **SHA inicial:** `dfda8d83d3`
- **SHA final:** `40c1a35548`
- **Commits produzidos:** 1 (`fix(browser): P0A pre-effect NOT_DISPATCHED terminal for stale_or_unknown_ref`)
- **Push:** Confirmado para `origin/feat/d049-browser-80-20-impl-20261018`
- **PR:** Não aberto nesta sessão
- **Arquivos não commitados:** Alterações pré-existentes em `tools/browser_tool.py`, `tools/browser_workstation.py`, `apps/desktop/electron/workstation-browser-extract-cache.test.ts`, `workstation/dogfood/.obsidian/workspace.json` e múltiplos untracked em `optional-skills/` — todos preservados, não tocados pelo P0A.

## 10. Pendências, riscos e débitos técnicos

### P-01: Integração do call-site no handler `browser_click` (P0)

- **Descrição:** `recordPreEffectTerminal` está implementado e testado, mas o handler `browser_click` no runtime (linha ~2966) não o invoca automaticamente quando `pointScript` retorna `stale_or_unknown_ref`. A API está disponível, mas a transição NOT_DISPATCHED não ocorre em produção sem essa conexão.
- **Origem:** Escopo P0A focou na API de persistência e normalização; a integração é listada como tarefa do P0B/P1 no documento de recuperação.
- **Impacto:** Sem essa integração, o deadlock original persiste em produção apesar da API estar correta.
- **Prioridade:** P0 — é a peça que falta para resolver o incidente real.
- **Condição de resolução:** Quando `clickRef`/`resolvePoint` detectar `stale_or_unknown_ref` ANTES de qualquer CDP dispatch, chamar `recordPreEffectTerminal` com reason `STALE_OR_UNKNOWN_REF` e evidence `TARGET_RESOLUTION_PRE_PAGE_EFFECT`, e retornar o erro normalizado ao agente.

### P-02: Warnings de padding pré-existentes (P3)

- **Descrição:** 3 warnings de `padding-line-between-statements` nas linhas 73 (teste), 3058 e 4880 (runtime) não bloqueiam o commit mas aparecem no lint.
- **Origem:** Pré-existentes no código; o lint só falhou porque os arquivos foram tocados.
- **Prioridade:** P3 — cosmético, pode ser limpo com `--fix` futuramente.

## 11. Guia de continuidade para o próximo agente

### 11.1. O que já está estabelecido

- `stale_or_unknown_ref` é normalizado para `STALE_REF/RESNAPSHOT`.
- `AdmissionTerminal` e `recordPreEffectTerminal` existem, são testados e persistentes.
- `findPendingBrowserMutation` libera fence quando terminal existe.
- 7 testes P0A + 231 existentes passam. Commit `40c1a35548` está na branch remota.

### 11.2. O que não deve ser repetido

- Não reimplementar `recordPreEffectTerminal` ou `AdmissionTerminal` — já existem.
- Não tentar importar `workstation-browser-runtime.ts` em testes sem mock de Electron via `vi.hoisted()`.
- Não deletar admissions nem fabricar ACKs para resolver deadlocks.
- Não fazer merge com `main` nesta branch.

### 11.3. O que não deve ser quebrado

- Invariante: admissão é imutável; terminal é imutável uma vez escrito.
- Invariante: post-effect failures NUNCA recebem terminal NOT_DISPATCHED.
- Invariante: replay do mesmo operationId sempre retorna `reconciliation_required`.
- Contrato de lock exclusivo em `withExclusiveAdmissionLock`.
- Fsycn durável após escritas de admissão.

### 11.4. Pontos de atenção no ambiente

- Testes do runtime requerem mock de Electron via `vi.hoisted()` — ver `workstation-browser-admission-p0a.test.ts` e `workstation-browser-runtime-task.test.ts` como referência.
- Pre-commit hook (lefthook) roda lint desktop app; erros bloqueiam commit.
- `scripts/run_tests.sh` é o runner oficial; `npx vitest run` funciona para testes focados.

### 11.5. Próximas ações recomendadas

1. **P-01 (P0):** Integrar `recordPreEffectTerminal` no handler `browser_click` do runtime. Local exato: após `resolvePoint` retornar erro `stale_or_unknown_ref` e ANTES de qualquer CDP dispatch. Critério: teste E2E mostrando que `browser_click` com ref stale retorna erro normalizado E libera fence para próxima operação.
2. **Validação runtime real:** Executar o cenário WhatsApp que originou o incidente com a integração P-01 aplicada.
3. **P-02 (P3):** Limpar warnings de padding com `npx eslint --fix`.

## 12. Matriz final de rastreabilidade

|Requisito|Ação realizada|Evidência|Estado final|Pendência|
|---|---|---|---|---|
|Normalizar `stale_or_unknown_ref`|Editado runtime linha 355|Commit `40c1a35548`, teste P0A-01|✅ Completo|Nenhuma|
|Tipo para rejeição pré-efeito|`AdmissionTerminal` interface|Commit `40c1a35548`|✅ Completo|Nenhuma|
|Estado terminal NOT_DISPATCHED|`recordPreEffectTerminal` + `findPendingBrowserMutation` atualizado|Commit `40c1a35548`, testes P0A-02/05/06/07|✅ Completo|Nenhuma|
|Persistência com concorrência e durabilidade|Lock exclusivo + CAS + fsync|Commit `40c1a35548`, testes P0A-02/04|✅ Completo|Nenhuma|
|Nova tentativa com novo operationId|Fence liberada por terminal|Teste P0A-02|✅ Completo|Nenhuma|
|Preservar bloqueios incertos|Terminal apenas para pré-efeito|Teste P0A-03|✅ Completo|Nenhuma|
|Testes RED→GREEN|7 testes escritos e passando|Saídas vitest|✅ Completo|Nenhuma|
|Typecheck/build viável|`tsc --noEmit` limpo|Saída tsc|✅ Completo|Nenhuma|
|Commit e push na branch|SHA `40c1a35548` pushed|Saída git push|✅ Completo|Nenhuma|
|Integração no handler `browser_click`|NÃO implementada|Ausente no diff|❌ Pendente|P-01 (P0)|

## 13. Avaliação crítica da sessão

**Maior valor produzido:** A API de terminal NOT_DISPATCHED com persistência durável e testes abrangentes resolve a camada de persistência do deadlock de forma correta e segura, respeitando todos os invariantes do documento de recuperação.

**Esforço desproporcional:** A correção de lint no pre-commit consumiu 3 tentativas de commit devido a regras de estilo (curly, sort-imports, padding) que não eram óbvias sem feedback do hook. Futuros agentes devem rodar `npx eslint --fix` antes do primeiro commit.

**Decisões bem fundamentadas:** A escolha de adicionar `terminal` como campo opcional em `BrowserMutationAdmission` (em vez de tabela separada) mantém a atomicidade do registro e simplifica a consulta. A whitelist de reasons previne uso incorreto.

**Insuficiência identificada:** A integração do call-site no handler `browser_click` não foi implementada nesta sessão. Embora o documento de recuperação liste isso como tarefa posterior, a API sozinha não resolve o incidente real em produção. O próximo agente DEVE priorizar P-01.

**Conclusões dependentes de comprovação:** A eficácia da solução em produção depende da integração P-01 e de validação com o cenário WhatsApp real. Os testes unitários provam a correção da API, não a resolução do incidente end-to-end.
# Inserções canônicas preparadas — Browser Batch P01/P02

**Status de todos os trechos abaixo: PREPARADOS, NÃO APLICADOS.**  
**Motivo:** os documentos canônicos do checkout `C:\Github\hermes-agent` permanecem reivindicados por `whatsapp-m3`; nenhum handoff foi confirmado. Inserir **somente após** handoff documentado e confronto com o conteúdo atual. Não apagar informações anteriores nem alterar status de outras frentes. As datas de testes históricos devem ser preservadas.

## 1. `workstation/context/CURRENT_STATE.md`

**Inserir na seção Browser Workstation / Native Browser, ou seção existente equivalente, depois de conferir estrutura:**

> **2026-10-28 — Browser Batch P01/P02 (estado verificado).** P01 tem implementação local no runtime Electron: `completeVerifiedBatch()` confirma o ACK causal do `browser_batch_actions` pai apenas após verificação das etapas, persistindo `batchStepReceiptRefs` na store canônica com lock/fsync. Seis suítes Electron P01 passaram (45/45) na auditoria de 28/10. **Não é release qualificado.** P02 de recuperação de sessão `parked` continua **incompleto**: `shouldDeferRestoredNavigation()` ainda pode selecionar a URL anterior para materialização lazy quando um lote posterior está incerto. Há RED por execução isolada do método e patch P02 de referência aplicável, **não integrado**. Falta GREEN integrado com FakeElectron, E2E com controlador autenticado em profile temporário, handoff/readback e gate de CI. O ledger real não foi reconciliado; P03 é missão distinta.

**Após execução dos quatro prompts:** atualizar apenas os status e resultados comprovados, preservando redação de problemas ainda abertos.

## 2. `workstation/context/KNOWN_ISSUES.md`

> **BROWSER-BATCH-ACK/RESTART — PARTIAL FIX / P02 OPEN / NOT RELEASE (2026-10-28).** Incidente original: `op_browser_batch_actions_b5c57ae46709` ficou pendente após um receipt filial `:0`, que não comprova conclusão do parent. P01 corrigiu localmente fechamento causal para batches novos e persistência durável; não reconciliou operação histórica. Riscos ainda a verificar: divergência entre ACK já persistido e `status=uncertain` se a atualização do `BrowserTaskLifecycle` falhar *após* `completeVerifiedBatch()`, auditabilidade das provas por etapa após restart e lazy restore read-only com `browser_batch_actions` posterior sem ACK. P02 E2E de restart/readback/handoff autenticado ainda pendente. Sem retry, TTL cego, auto-ACK, limpeza de admissions, abertura de WhatsApp real ou alteração do Kanban upstream.

## 3. `workstation/context/DECISIONS.md`

> **ADR operacional — linearização do ACK e leitura segura de sessão restaurada (PROPOSTA, AGUARDA VALIDAÇÃO P01/P02).** O ACK pai é uma decisão durável da autoridade canônica, não prova de entrega externa. Um receipt filial ou simples UI `verified` não reconhece o parent. A separação entre pré-commit, commit durável e sincronização em memória não pode devolver razão `parent_not_durable` se o ACK já está persistido. Falha de sincronização local pós-commit deve ser tratada de modo explicitamente reconciliável sem replay da mutação. Um `browser_snapshot` não pode materializar URL externa quando a mesma identidade task/tab/run/session possui efeito mutante pendente. Revisão humana registra revisão, não concede mutação nem readback. Preservar lineage, lease, idempotência, lazy `parked/about:blank`, journal sanitizado e compatibilidade de snapshots legados. **Esta decisão permanece proposta até testes RED/GREEN e aprovação documental.**

## 4. `workstation/context/README.md`

> - Browser Batch — diagnóstico e plano de referência: `BROWSER_BATCH_RECONCILIATION_PLAN_20261028.md`.
> - P01 — implementação, testes locais e gates: `BROWSER_BATCH_P01_IMPLEMENTATION_20261028.md`.
> - P02 — readback/restart/handoff, hipóteses e HOLD: `BROWSER_RESTART_P02_GATE_AND_TEST_REPORT_20261028.md`.
> - Kit de execução P01/P02 — artefato preparado nesta sessão (`Hermes_Browser_Batch_Plano_Implementacao_20261028.md`); **ainda não importado ao repositório**, incluir link relativo só quando houver arquivo sob claim autorizado.
> - P03 — missão separada de admissões `unbound`: `BROWSER_ADMISSION_P03_20261028.md`.

## 5. `workstation/context/engineering-journal/CURRENT.md`

> **2026-10-28 — Auditoria/planejamento Browser Batch.** Código revisado em `main@f1d5ab2f030e940ed4571371b0de45a21a009c9e` com worktree compartilhado. P01: parent ACK + child refs estão implementados; auditoria anterior reexecutou seis suítes Electron 45/45 PASS, typecheck Electron PASS; riscos pós-commit/filial identificados para RED dedicado (não declarados bug reproduzido). P02: restauração lazy com lote incerto ainda sem patch; RED do método extraído em relatório P02, candidato source-derived 8/8; nesta etapa foi criado **patch de referência** `shouldDeferRestoredNavigation` e validado `git apply --check=0`, sem aplicá-lo. Quatro prompts definidos: P02 lazy restore → P01 commit/auditoria → E2E autenticado P02 → docs/CI/gate de release. Docs canônicos sob claim, aguardam handoff. Nenhum ledger, CDP, WhatsApp ou perfil real utilizado.

**Na execução:** acrescentar apêndices datados com `RED`, `GREEN`, `file SHA`, testes, exit codes, contexto de perfis, decisões e limitações; não substituir resultado histórico por previsão.

## 6. `workstation/ROADMAP.md`

> **2026-10-28 — Fechamento Browser Batch (P01/P02).** **P01: localmente implementado, qualificação final pendente** (consistência pós-ACK e audit trail filial). **P02: não concluído**, faltam patch lazy restore, RED/GREEN integrado e E2E nativo de restart/readback/handoff autenticado em loopback temporário. Etapas de execução: (1) restaurar aba sem loadURL implícito sob pending; (2) fechar inconsistência transacional e evidência das etapas; (3) E2E com revisão sem replay e journal sanitizado; (4) documentação, CI exata, upstream e release gate. **Release HOLD** até evidências. P03 (prevenção `unbound`) segue trilha separada, não autoriza remediação de histórico.

## Regra de aplicação de todas as inserções

1. Obter ownership/handoff para cada arquivo; revalidar branch, HEAD, dirty e conteúdo real.
2. Localizar seção existente e integrar texto com estilo/terminologia do documento, sem criar duplicidade.
3. Quando o estado mudar, atualizar conforme testes reais; não copiar os textos `OPEN` ou `PROPOSTA` se já houver prova de conclusão.
4. `git diff --check` + revisão cruzada das seis fontes; nenhuma exclusão de conteúdos dos outros agentes.
5. Registrar no Engineering Journal os links para relatórios, patch aplicado, arquivos alterados, testes e limitações.

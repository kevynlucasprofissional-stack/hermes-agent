# Plano de implementação — Kanban Hermes × Browser nativo × Trello
Data: 12/11/2026. Projeto: C:\Github\hermes-agent, branch main, HEAD de referência f1d5ab2f03. **Este documento é planejamento; não é homologação da integração genérica.**

> Para agentes implementadores: use o procedimento de planejamento/execução e verificação do Superpowers, quando disponível, sem impor commits, branches ou worktrees ao checkout compartilhado. Leia o prompt da etapa correspondente e implemente/teste. Os cinco prompts abaixo são independentes em instruções; a ordem de execução é vinculada por gates.

## 1. Diagnóstico consolidado — evidência inspecionada

- **Canônico:** `hermes_cli/kanban_db.py` e `hermes_cli/kanban_db_connect.py`. O plugin de UI `apps/desktop/src/plugins/kanban/` é sua apresentação. O bridge `workstation/kanban.py::WorkstationKanbanBridge` chama o `AcceptanceEvaluator`, registra `TaskRun` e só admite `done` se a avaliação aprovar.
- **Não confundir:** `apps/desktop/src/plugins/workstation-board/` tem visualizações Kanban/tabela de bases próprias, independentes da fila canônica de execução. `plugins/workstation_database_agent` também explicita que não substitui o Kanban upstream. O plano NÃO funde bancos nem troca o destino dos cartões.
- **Browser:** `tools/browser_workstation.py::_dispatch` envia ações ao Chromium do Electron, com `task_id`, `session_id`, `kanban_card_id`, `run_id` e `operation_id`. O estado em `browser-session.json` e o recibo de dono suportam navegação vinculada a TaskRun por `read_native_browser_session_state`; a verificação é restrita à navegação.
- **Observação/controle:** `workstation/integrations/hermes/tool_observer.py` registra pre/post dispatch; `workstation/batch_detection.py` protege mutações incertas; `workstation/procedure_trace.py` mantém rastreio de operações; `workstation/integrations/hermes/completion_admission.py` delega finalização canônica.
- **Verificação pré-existente:** `workstation/task_compiler.py`, `workstation/browser_transaction.py` e `workstation/integrations/hermes/run_local_adoption.py` possuem contratos de pré/pós-condição, gradação de evidência e exemplos de leitura de `browser_extract_items`. Não duplicar `AcceptanceEvaluator` nem criar outro dispatcher/browser/DB.
- **Implementado anteriormente e preservado:** `workstation/direct_file_readback.py`, `external_readback.py`, `evidence_recovery.py`, e testes `test_kanban_direct_file_readback.py`, `test_kanban_external_readback.py`, `test_kanban_evidence_recovery.py`. O recibo específico Trello/WhatsApp não deve ser removido; ele oferece evidência mais forte e cobre operações sem browser observável.
- **Lacuna:** `workstation/kanban.py::_verified_native_navigation` certifica apenas uma navegação nativa restrita. Não certifica genericamente `browser_click`, `browser_type` ou `browser_batch_actions` com resultado persistido. O ramo direto `verify_file_write_receipts` rejeita corretamente mutações web sem recibo suportado. O registro genérico de click/ACK não comprova que o servidor alterou um dado.
- **Incerteza estrutural:** o formato real de cada resposta `browser_snapshot`/`browser_extract_items` e as capacidades de reaquisição pós-reload devem ser confirmados por um teste controlado no Chromium antes de fixar extratores universais. Não inferir conteúdo persistido de `success: true`, URL, screenshot, DOM efêmero ou resposta do modelo.

### Decisões arquiteturais (preservar)

1. **Executor universal, prova proporcional:** a execução é site-agnóstica pelo Browser nativo; verificação de interface é genérica, mas prova de persistência externa exige observação independente/autoritativa ou contrato de persistência comprovado. Não prometer “qualquer site automaticamente done” sem fonte verificável.
2. **Separar níveis:** (a) ACK causal do dono — ação despachada; (b) observação semântica fresca do DOM — estado exibido; (c) confirmação pós-reload em nova leitura — durabilidade observável de UI; (d) leitura autoritativa externa (API/GET/revision/DB de fixture) — persistência externa. Apenas o nível exigido no contrato de aceite pode satisfazer o objetivo.
3. **Cobertura por efeito:** cada commit obrigatório deve corresponder a `operation_id`/`call_id` e ao predicado verificado. Uma evidência de outro clique, outro tab, outra sessão, outro run ou outro campo NÃO cobre a operação.
4. **Sem replay incerto:** timeout depois do despacho não autoriza repetir clique de salvar, POST, envio WhatsApp ou alteração Trello. Reconciliar SOMENTE por leitura; o canônico decide `done`. Credenciais, aprovação e leases continuam nas suas camadas.
5. **Trello é integração adjacente:** sincronização de registros Trello ↔ cartões do Kanban Hermes tem identificação, mapeamento e conflitos próprios. O `workstation-board` continua independente. Não reaproveitar automaticamente o mapeamento Database↔Trello como se fosse Kanban Hermes↔Trello.

### Riscos materiais

- Um formulário pode mostrar valor local sem backend ter salvo; nunca equiparar DOM à persistência.
- Navegação pós-save pode ser servida de cache; a fixture usa `Cache-Control: no-store` e permite conferência SQLite/API independente. Fora da fixture, medir qual fonte prova o estado.
- `lastReceipt` em `browser-session.json` é singular e pode ser substituído por ação posterior; preferir rastro por operação no owner ou artefato individual imutável. Não relacionar operação retrospectivamente por “último recibo” sem correspondência exata.
- Interações do Browser às vezes aparecem como `INTERACTIVE` no registry genérico; `workstation/batch_detection.py::is_workstation_mutation` foi adaptado localmente para proteger efeitos com potencial externo. Não regredir para retry implícito.
- Não atribuir ao parent `done` por concluir uma subtarefa consultiva sem reabrir evidência autoritativa da mutação originária. Não alterar histórico dos 79 cartões anteriormente bloqueados sem nova comprovação individual.

## 2. Artefatos já preparados e limites da validação

**Código efetivamente criado na preparação, sem alteração na aplicação de produção:**

- `workstation/tests/fixtures/browser_kanban_qa_fixture.py`: servidor HTTP de loopback em porta efêmera; formulário HTML “Salvar”, `GET /api/item`, SQLite persistido, CAS por revision, operação de formulário idempotente e `Cache-Control: no-store`. Não lê bases do Hermes.
- `workstation/tests/test_browser_kanban_qa_fixture.py`: teste real HTTP→SQLite→nova conexão, repetição idempotente, conflito 409, reabertura. **1/1 PASS em 12/11/2026.** Regressão focal adicional, com testes de Kanban/readbacks existentes: **23/23 PASS** (sem Browser E2E). Ainda não houve interação de `browser_click` nesse site pelo Chromium.
- `python -m py_compile` aprovado para ambos. `.venv\Scripts\python.exe -m ruff` indisponível neste venv (“No module named ruff”); não declarar lint aprovado.

**Estado apenas planejado:** contrato genérico de observação, integração do receipt ao Kanban, recuperação de cliques com resultado incerto, E2E no Chromium, sincronização Trello↔Kanban. **Nada disso foi implementado nesta preparação.** Os 129+47 testes de regressão comunicados em rodada anterior são evidência histórica de outro conjunto de alterações; não foram reexecutados nesta preparação.

**Documentos existentes consultados:** `workstation/ROADMAP.md`, `workstation/context/engineering-journal/CURRENT.md`, `workstation/context/BROWSER_BATCH_RECONCILIATION_PLAN_20261028.md` e `workstation/context/PLANO_UNIFICADO_DATABASE_TRELLO_CRON_20261107.md`. Não reabrir a importação ACIRV, agendamentos, migrações antigas ou campanhas WhatsApp.

## 3. Mapa de dependências e avanço

| Fase | Dependência | Resultado exigido antes de avançar | Natureza |
| --- | --- | --- | --- |
| P1 — Browser: contrato/prova genérica | fixture já preparada | exemplo real de ação + readback separado, rastro causal e rejeição de prova falsa | indispensável |
| P2 — Browser→Kanban: done canônico | P1 aprovado | um formulário persistido gera `EvidenceRef` vinculado e `done` após novo SQLite | indispensável |
| P3 — Recovery e timeout | P2 aprovado | reconcilia por leitura; zero segundo POST/clique; resultado divergente não vira `done` | indispensável |
| P4 — Trello↔Kanban, campo título | P2+P3 | mapeamento estável, pull+push controlados com CAS, sem duplicações, QA | complementar |
| P5 — Trello metadados/histórico | P4 aprovado e campos realmente acessíveis | testes por família de dado, conflitos por campo, arquivo/arquivamento preservados | condicional; não bloqueia MVP genérico |

Cada fase pode corrigir erros comprovados da anterior; não ampliar escopo por refatoração especulativa. Fazer documentação e relatório no mesmo ciclo de código. Operações reais em provedores externos exigem autorização/credenciais já existentes; em caso de ausência, manter HOLD e testar fixture isolada.

---

## 4. Prompts autossuficientes para a IA implementadora

### P1 — Implementar evidência genérica de Browser por operação (sem liberar o Kanban ainda)

**Objetivo:** criar o menor contrato reutilizável para observar uma mutação no Chromium nativo e confirmá-la por leitura independente, sem depender de Trello/WhatsApp e sem marcar um commit externo como persistido apenas por DOM/ACK.

**Contexto e alvos reais:** `C:\Github\hermes-agent`, branch `main`, HEAD-base `f1d5ab2f03`; checkout compartilhado com centenas de alterações dirty (recontar). `tools/browser_workstation.py::_dispatch` e `_record_browser_controller_outcome`, `workstation/integrations/hermes/tool_observer.py`, `workstation/procedure_trace.py`, `workstation/browser_transaction.py`, `workstation/execution_policy.py::EvidenceStrength`, `workstation/integrations/hermes/run_local_adoption.py`, `apps/desktop/electron/workstation-browser-runtime*.ts` e testes de admissão/recibos. O `browser-session.json` só certifica atualmente navegação em `read_native_browser_session_state`; não generalize `lastReceipt` para clicks.

**Executar:**
1. Inspecione somente o caminho de `browser_click`/`browser_type`/`browser_snapshot`/`browser_extract_items` no owner Electron e no dispatcher Python para identificar IDs reais e formas retornadas. Reuse a projeção persistida `operationAdmissions`/recibos já existente, se ela contiver uma identidade suficiente; caso contrário estenda *apenas* o owner com recibo individual limitado, sem criar uma segunda fonte de verdade.
2. Defina/implemente um contrato tipado mínimo, com: `task_id`, `session_id`, `run_id`, `operation_id`, `call_id`, `browser_task_id`, `tab_id`, `action`, alvo/predicado esperado, evidência de ACK, `source_kind`/`evidence_strength`, observação fresca, estado `observed / verified / uncertain` e referência de artefato. Metadados seguros, sem payload de mensagens, credenciais ou DOM inteiro.
3. Separe o ACK do owner, observação pós-ação e readback mais forte; só produza `verified` para predicado com independência suficiente. Reaproveite `ArtifactStore` e `EvidenceRef`; se o alvo não tem leitura independente, emita `uncertain` com motivo, jamais `verified` por `success:true`.
4. Adicione teste de falsificação: outro run/tab/op, receipt ausente, snapshot stale/cache, UI alterada apenas localmente, DOM divergente, owner não Chromium, leitura falha e timeout pós-dispatch. Garanta que o caso de navegação certificado e o adaptador `write_file` permanecem intactos.

**Critérios de aceite:** um receipt por operação com proveniência conferida, predicado pós-ação associado, falhas classificadas sem duplicação e teste negativo para falso `done`. Não introduzir `write_file` em produção apenas para fabricar evidência. Não concluir fase baseado só em mocks; confirmar no owner/Chromium a forma do recibo quando houver acesso. O `Kanban` ainda não muda de `blocked` para `done` nesta fase.

**Validação/registro:** rode `.venv\Scripts\python.exe -m pytest workstation/tests/test_h080b_native_browser_experience_loop.py workstation/tests/test_p0_uncertain_mutation_readback.py -q` e as suites Electron `workstation-browser-runtime-admission.test.ts` / `workstation-browser-batch-proof.test.ts` pelo runner existente; novos testes de receipt. Registre diferenças no `workstation/context/BROWSER_KANBAN_GENERIC_VERIFICATION_PLAN_20261112.md` e no journal. Relatório: arquivos, decisões de formato, IDs reais, testes, prova Chromium versus fixture, lacunas, rollback por função/arquivo. Sem commit/push/restart automático; preservar trabalho paralelo. Se outro desenho for objetivamente melhor, adote-o documentando por quê.


### P2 — Ligar recibos do Browser ao Kanban canônico e provar o fluxo real

**Objetivo:** edição/salvamento no site QA executados por `browser_type` + `browser_click` no Chromium nativo; uma leitura nova confirma o estado persistido; `workstation/kanban.py` gera `EvidenceRef`/`verifier_results`, chama `AcceptanceEvaluator` e registra o `TaskRun` como `done`. O site precisa continuar independente de WhatsApp e Trello.

**Projeto/segurança:** `C:\Github\hermes-agent`; branch `main` com checkout dirty compartilhado. Preflight `git status --short`, `git diff` por arquivo, processos/claims; sem reset, clean, stash, commit, push, troca de branch, CDP externo, Playwright alternativo, teclado/mouse global, restart ou alteração em serviços externos sem autorização. Reuse o dono de Browser do Electron, `tools/browser_workstation.py::_dispatch`, `workstation/integrations/hermes/tool_observer.py`, `workstation/kanban.py::finalize_turn_candidate` e `complete_task_with_report`, `workstation/contracts.py::{EvidenceRef,BrowserTaskReport}`, `workstation/contracts.py::AcceptanceEvaluator` (localização confirmada), `workstation/direct_file_readback.py::verify_file_write_receipts` e a implementação do contrato de P1.

**Artefato QA já pronto:** `workstation/tests/fixtures/browser_kanban_qa_fixture.py::make_server(db_path)` e `workstation/tests/test_browser_kanban_qa_fixture.py`. Site acessível somente em `127.0.0.1`, porta aleatória. Campos HTML `#title`/`#save`/`#persisted-title`. `POST /save` faz CAS+op idempotente; `GET /api/item` lê a persistência SQLite; gravar `Cache-Control: no-store`. Teste HTTP direto já passou; o fluxo Chromium está pendente. Não alterar a fixture para simular receipt do Browser.

**Execução:**
1. Conclua P1 antes desta missão. Valide que o dispatcher fornece a identidade REAL da operação ao pré/pós-observador, não IDs inferidos pelo modelo. Trace/receipt completo por chamada; não use `lastReceipt` global como prova para múltiplas ações se puder ter sido sobrescrito.
2. No `finalize_turn_candidate`, inclua o novo verificador genérico em uma avaliação ÚNICA dos efeitos observados. Reuse `verify_file_write_receipts`/`verify_external_receipt` como caminhos especializados (sem remover seus testes), mas rejeite qualquer mutação obrigatória desconhecida, falha, truncada ou não coberta. Uma prova de navegação não cobre clique de salvar; um recibo de clique não prova persistência. Para uma sequência com várias mutações, mantenha cobertura completa por operação ou trate explicitamente interações não-commit de um mesmo contrato transacional.
3. Persistência externa: para a fixture, faça uma nova consulta de leitura ao `GET /api/item` (canal autorizado) e compare `title` e `revision` com os valores esperados. Reabra o SQLite por outra conexão NO TESTE, não no código genérico do Kanban. Para outros sites, permita um contrato genérico de verificador read-only/GET com campo/predicado explícito e identidade de origem confiável; sem GET/verificador autoritativo, rotule `UI_OBSERVED` e não `EXTERNALLY_PERSISTED`.
4. Execute com Browser nativo REAL do Hermes, não apenas simulação de handlers: iniciar fixture, tarefa QA canônica isolada, BrowserTask atribuída à mesma `session_id / task_id / run_id`, abrir, preencher, salvar, extrair resultado, confirmar leitura autoritativa, concluir. Verificar em uma nova conexão SQLite do **Kanban de teste** o `done` e `TaskRun`/`EvidenceRef`/verifiers vinculados. Não criar registro de teste em banco operacional se não conseguir isolar sessão e DB. Não alegar E2E se usou apenas `HTTPServer`/mocks.
5. Negativos representativos: erro 409, clique só modifica DOM local, mismatch de campo/revision, outra aba/run, resposta do Browser com `success` falso, `raw receipt` sem prova, pacote multiop com um commit sem cobertura. Em cada caso, não autorizar `done` nem repetir mutação.

**Testes:** `.venv\Scripts\python.exe -m pytest workstation/tests/test_browser_kanban_qa_fixture.py workstation/tests/test_kanban_direct_file_readback.py workstation/tests/test_kanban_external_readback.py workstation/tests/test_kanban_evidence_recovery.py workstation/tests/test_h080b_native_browser_experience_loop.py -q --disable-warnings --maxfail=1`, novos testes de finalização genérica, e testes Electron focados onde houver mudança de owner. Use `apps/desktop/package.json` para runner `vitest --project electron` quando disponível. Prove no diário a diferença entre teste HTTP, teste Browser e Kanban SQL.

**Gate:** o Browser REAL edita `title`, a leitura independente mostra a revisão seguinte, o Kanban canônico marca `done` sem caminho especial “site QA”, e um caso de discrepância não marca `done`. Preservar resultados anteriores. Se a prova externa não puder ser fornecida pelo browser em canal permitido, NÃO enfraqueça o contrato: implemente o menor adapter read-only genérico ou deixe `done` explicitamente pendente; reporte o obstáculo.

**Registro e entrega:** atualizar este plano e `workstation/context/engineering-journal/CURRENT.md` (seção curta), relatório de arquivos alterados, testes contados, IDs sanitizados, nível real de evidência, estado SQLite antes/depois, falhas, salvaguardas e eventual desvio técnico. Reverter somente mudanças criadas nesta missão se necessário, nunca alterações preexistentes.

### P3 — Recuperação genérica de Browser incerto e não repetição de efeitos

**Objetivo:** quando `browser_click`/`browser_batch_actions` possivelmente salvou um dado mas perdeu o ACK, o Kanban cria reconciliação **somente leitura** vinculada à operação original; consulta o resultado persistido e conclui o pai apenas se comprovado. Nunca reproduz `POST`/click de salvar, inclusive após reinício.

**Projeto e módulos:** `C:\Github\hermes-agent`, `main`, checkout dirty; preservar. P1/P2 precisam estar testados. Inspecione `workstation/evidence_recovery.py::{schedule_recovery,_descriptor,_owner_reprobe,enforce_recovery_scope,on_recovery_child_completed,try_recover_running_parent}`; já há mecanismo para `workstation_db_trello_api_push` e `whatsapp_send_message`. Inspecione `workstation/batch_detection.py::{prepare_mutation,record_mutation,is_workstation_mutation}`, `workstation/integrations/hermes/completion_admission.py`, `tools/browser_workstation.py::_dispatch` e owner Electron `workstation-browser-admission*.ts`. Use a identidade de operação e os checkpoints persistidos do P1, não crie outro retry executor.

**Execução:**
1. Generalize apenas a entrada de recuperação, aceitando um descriptor **seguro e limitado** para Browser com: `task_id`, `run_id`, `session_id`, `operation_id`, `browser_task_id`, `tab_id`, `action`, `readback_expectation` e `resource_scope`. O descriptor deve vir do owner/contrato antes de despachar, e não de texto arbitrário da IA; não persistir valores secretos.
2. Crie dependência child→parent somente quando houver leitura autorizada capaz de produzir a prova; sem fonte de leitura, registre HOLD com causa concreta. A child pode ler `browser_snapshot`/`browser_extract_items` ou GET autorizado por canal existente; `browser_navigate` não deve ser automaticamente liberado como “somente leitura” (navegações GET também podem causar efeitos). Leia o estado real do owner e respeite leases/recovery_state; sem controller ou sessão legítima, pare.
3. Após `child done`, a rotina canônica reexecuta **apenas o verificador**, relê o predicado, checa run/origem/op original e só então chama `complete_task_with_report` sobre nova execução do pai conforme CAS do Kanban. Se a fonte estiver offline, mantenha pendência reconciliável sem refazer o efeito. Não confundir relatório narrativo da child com evidência autoritativa. Verificação de todas as operações obrigatórias antes do `done`; nenhuma evidência emprestada entre operações.
4. Ao perder ACK na fixture, produzir um único POST no servidor, simular perda de resposta apenas na camada transport (sem forjar confirmação), e recuperar por `GET /api/item`/SQLite; testar nova instância de processo/owner, duplicação de callback, indisponibilidade prolongada, revision drift e tarefa de outro run. Não alterar banco Trello/WhatsApp real.

**Testes:** `workstation/tests/test_kanban_evidence_recovery.py`, `test_p0_uncertain_mutation_readback.py`, `test_browser_batch_actions.py`, `test_browser_kanban_qa_fixture.py`, teste de owner Electron `workstation-browser-runtime-admission.test.ts` e `workstation-browser-batch-proof.test.ts`. Adicionar casos com contador de POST/click=1 e `done` somente após readback; nenhuma aprovação unilateral por timeout ou corpo de chat. Rodar regressão de P2.

**Gate:** 1 efeito externo confirmado, 0 reenvios, child restrita a leitura e pai `done` pelo gate canônico; fonte inverificável → sem `done` e sem duplicação. Se alguma API de leitura não for suficiente, registrar impedimento sem desbloquear envio. Documentar o fluxo e provas em journal/este plano. Sem commit/push/restart destrutivo.


### P4 — Sincronizar Kanban Hermes ↔ Trello em um campo, com prova em ambos os sentidos

**Objetivo:** permitir que um cartão do Trello e a representação **correspondente do Kanban Hermes canônico** compartilhem identidade e mudança controlada de **título**, bidirecionalmente, com baseline por campo e conflito detectado, sem tocar no Kanban de visualização de `workstation-board`.

**Contexto:** `C:\Github\hermes-agent`, branch main compartilhada, inúmeras alterações locais; P1–P3 concluídos e testados. A fonte das tarefas executáveis é `hermes_cli/kanban_db.py` (não `plugins/workstation-board/`). Código existente a reutilizar/inspecionar: `workstation/trello_migration.py::reconcile_trello_legacy`, `workstation/trello_sync_reconcile.py`, `workstation/trello_sync_push.py`, `workstation/trello_sync_api.py`, `workstation/trello_sync_transport.py`, `workstation/dataset_edits.py` somente onde realmente aplicável, `workstation/external_readback.py`, `workstation/kanban.py`, `hermes_cli/hybrid_kanban.py` e contrato do Browser genérico de P1. O documento `workstation/context/PLANO_UNIFICADO_DATABASE_TRELLO_CRON_20261107.md` é referência HISTÓRICA: separa Database/Trello e relata migrações/fixtures, mas não prova esta nova sincronização canônica.

**Execução:**
1. Antes de alterar, decida explicitamente **qual entidade** no Kanban Hermes é mapeada ao cartão Trello: `AgentTask` executável canônico, `hybrid_card` humano, ou ambos com vínculo referencial. Inspecione o schema real e os consumidores. Não misturar `workstation-board` com `hybrid_kanban` ou com `tasks`; preferir vínculo explícito sem reimportar os 119 itens históricos.
2. Use chave estável `(trello_board_id, trello_card_id)` ↔ id do registro canônico decidido; persistência única, UNIQUE e integridade referencial conforme o schema encontrado, checkpoint de última versão/estado observado. Primeira rodada de pareamento apenas dry-run, sem alterar títulos nem criar cartões duplicados.
3. Para o campo `title` implemente comparação 3 vias: baseline da última sincronização, valor local atual e valor Trello atual lido por fonte autorizada. Se um lado mudou, planeje/aplique com CAS e readback; se ambos mudaram para valores divergentes, abra conflito por campo e preserve ambos, sem escolha por “última data” ou opinião do modelo.
4. **Trello→Hermes:** leitura autenticada, identidade verificada, projeção no registro canônico com CAS; confirmar relendo Kanban por outra conexão SQLite. **Hermes→Trello:** intenção durável antes de mutação, preferir readback via Browser nativo da P1 e, se requerido, fonte Trello GET autenticada existente; operação incerta segue P3 sem repetir PUT/click.
5. Use exclusivamente um cartão QA explicitamente autorizado e um registro canônico QA isolado na homologação. Não tocar em quadros produtivos, cartões concluídos/arquivados, mensagens, anexos ou cron. Evitar hardcodes `QA_BOARD_ID` fora dos testes específicos — `trello_sync_api.py` existente tem restrições QA que não devem ser alargadas silenciosamente.

**Testes:** `workstation/tests/test_trello_sync_reconcile.py`, `test_trello_sync_api.py`, `test_trello_sync_push.py`, `test_trello_sync_transport.py`, `test_kanban_evidence_recovery.py`, `test_canonical_work_loop.py`, além de testes de mapeamento/CAS/conflito novos. Casos: pull; push; mesma atualização recebida 2 vezes; ambos lados alterados; sessão não autorizada; arquivado/completo; fonte offline; receipt do Browser de outro run; alteração na mesma entidade após leitura. Qualifique primeiro em fixture ou QA autorizado, depois reabertura/recarga.

**Critério de aceite:** 1 cartão QA vinculado a 1 registro Hermes, título alterado em cada direção com readback, conflito bilateral preservado sem perda, reprocessamento idempotente e 0 duplicações. Documentar como diferiu do pipeline Database↔Trello e como o mapa é mantido. **Não** considerar campos adicionais implementados nesta fase.

**Entrega:** diff mínimo, migração reversível se inevitável, rastreio da identidade sem segredos, testes e E2E de QA, cobertura do contrato/recibo e status do Trello, tudo registrado neste plano e no journal. Sem commit/push/restart automático, sem descartar alterações preexistentes. Se for tecnicamente superior vincular a `hybrid_card` e apenas referenciar uma AgentTask, justificar com evidência de schema e uso.

### P5 — Ampliar integração Trello por famílias de campo (somente se P4 aprovado)

**Objetivo:** estender sincronização canônica já comprovada (P4) a descrição, lista/status, responsáveis, prazo, etiquetas, checklist, comentários, anexos, arquivamento e histórico, **apenas** onde APIs/DOM reais oferecem identidade, leitura e escrita verificáveis. Não é pré-requisito do MVP Browser→Kanban.

**Projeto:** `C:\Github\hermes-agent`, `main` compartilhada; reusar mapas, baseline e CAS de P4, `workstation/trello_sync_reconcile.py`, `trello_action_journal.py`, `trello_sync_transport.py`, `trello_sync_api.py`, `workstation/dataset_edits.py` só se aplicável, contrato do Browser genérico de P1–P3, `hermes_cli/kanban_db.py`/`hybrid_kanban.py`. Consulte `workstation/context/PLANO_UNIFICADO_DATABASE_TRELLO_CRON_20261107.md` e provas mais recentes, distinguindo histórico de funcionalidade atual.

**Execução incremental por família; não implementar todas simultaneamente:**
1. Inspecione uma amostra controlada do cartão QA e liste atributos com `remote_id`/`action_id`, edição permitida, paginação e prova de readback. Não suponha que o DOM exponha todos os comentários/checklists/anexos.
2. Amplie por **família observável**, começando descrições/status/prazo; depois membros/etiquetas; só então checklists/comentários/anexos e histórico, se houver autorização e fonte confiável. Não force todos os campos se um grupo não puder ser comprovado.
3. Conflitos por campo ou por item (checklist/comment) com base comum; eventos e anexos não devem ser duplicados em retry. Para binários, use referência/hash, não transfira conteúdo sensível indevidamente nem regrave fontes históricas. Arquivamento sincronizado; exclusões destrutivas exigem gate humano explícito.
4. Reavalie `upstream kanban status` versus `Trello list/dueComplete` antes de ligar estados automáticos; preserve concluídos e histórico. Nenhum loop diário é ativado nesta fase. O cron existente pode receber agendamento em missão futura específica após homologação de sync, sem criar outro scheduler.

**Testes/gates:** por família, prova remota e local antes/depois, identidade imutável, CAS/conflito, paginação, falha de credenciais, reordenação/duplicação de eventos, anexos e arquivamento. Rodar todas as suites P4 e banco quick_check. Se um campo não for verificável, registrar como não suportado, sem declarar sync total. Relatório por campo com `implemented / verified / hold`, fontes autoritativas, reprocessamento idempotente e pendências.

## 5. Operação, rollback e relato em cada fase

- **Preflight operacional obrigatório:** comparar `git status`, hash dos arquivos-alvo, claims e sessão/TaskRun; confirmar origem do Browser (Electron) e permissão para mutação; registrar estado SQLite. Todo trabalho pré-existente é preservado. Nunca reset/stash/clean/commit/push por padrão.
- **Validação proporcional:** pytest focal por fase, regressões já existentes, testes Electron quando o owner for alterado, `py_compile`/lint quando a ferramenta estiver presente, e um fluxo principal real quando houver autorização. Build não substitui verificação de persistência.
- **Proteção de dados:** fixture HTTP bind 127.0.0.1 com SQLite temporário e fechamento do servidor; no ambiente operacional, backup SQLite consistente antes de migração/restart, avaliação de WAL/leases/interpretador e reinício somente controlado. Nenhuma credencial/corpo WhatsApp em artefato de readback.
- **Rollback:** nova função atrás de verificação e adaptação incremental; se efeito incerto, manter checkpoint e não repetir ação; reverter somente o patch próprio se comprovadamente necessário. Migrações precisam ser aditivas, idempotentes e reversíveis, sem excluir campos/registro preexistentes.
- **Relatório final de cada prompt:** (a) arquivos editados e estado efetivo, (b) diff e decisões, (c) testes com resultado real, (d) evidências do comportamento observado separadas por nível (fixture HTTP / Chromium / remoto / SQLite), (e) regressões e risco residual, (f) pendência exata e gate seguinte. Encerrar quando o slice estiver funcional e validado.

## 6. Estado desta preparação (fonte de verdade deste documento)

| Entrega | Situação 12/11/2026 | Prova |
| --- | --- | --- |
| Inspeção seletiva da arquitetura Python/Electron/Kanban | REALIZADA | Arquivos/símbolos citados nas seções 1 e 4 |
| Decisão browser genérico + especialistas opcionais | DOCUMENTADA | Seções 1, 3 e prompts P1–P5 |
| Fixture de edição SQLite em localhost | IMPLEMENTADA | `workstation/tests/fixtures/browser_kanban_qa_fixture.py` |
| Teste do servidor QA HTTP/SQLite | APROVADO | `workstation/tests/test_browser_kanban_qa_fixture.py`: 1/1 PASS |
| Contrato genérico por operação / navegador→Kanban `done` | PLANEJADO, NÃO IMPLEMENTADO | Prompts P1–P2 |
| Recuperação Browser incerto sem reenviar | PLANEJADO, NÃO IMPLEMENTADO | Prompt P3; reaproveita recuperação especializada existente |
| Sync Kanban Hermes ↔ Trello | PLANEJADO, NÃO IMPLEMENTADO | P4 e P5; Database/Trello parcial não equivale a este objetivo |
| Browser/Electron E2E no formulário | PENDENTE DE EXECUÇÃO | Prompt P2 |
| Suite completa e validação operacional das futuras alterações | PENDENTE | Gates de cada prompt; regressão focal pré-implementação: 23/23 PASS |


---

## P1 — Execução real da etapa em 12/11/2026 (CÓDIGO LOCAL, QA PARCIAL)

**Estado:** contrato e observador implementados no checkout compartilhado, sem commit, push, restart ou alteração nos sites externos. **Não** significa que a versão já foi carregada no backend ativo, nem que o Kanban possa aprovar `done` após browser_click.

### Alterações efetivamente realizadas
- **Novo:** `workstation/native_browser_evidence.py`, dataclass `NativeBrowserOperationReceipt` e `capture_native_browser_operation`. Suporta operações `browser_click` e `browser_type`; consome `operationAdmissions[operationId]` persistido e o recibo causal da resposta do Chromium, verifica TaskRun/session/task/tab/action/ACK/temporalidade e tab `live`. Não usa `lastReceipt` para provar operações anteriores; seu valor atual serve apenas para detectar corrida após a observação.
- **Alterado pontualmente:** `workstation/integrations/hermes/tool_observer.py::workstation_raw_post_tool_observer` registra o recibo no ledger da chamada original e faz uma **nova** leitura nativa `browser_snapshot` diretamente no controller, sem reenviar click/type, com IDs explícitos. O resultado padrão é `observed` (força 1) ou `uncertain` (força 0), não `verified`/persisted.
- **Novo:** `workstation/tests/test_native_browser_operation_evidence.py` com falsificação de IDs de run/tab/op, falha/ausência de receipt, ACK incompleto, origem/runtime divergentes, snapshot de cache, UI observada sem persistência, leitura falha, corrida com outra operação, target privado e cópia imutável de artefatos. Inclui integração real do hook com owner estruturado em fixture e uma consulta HTTP GET posterior a POST real no site QA isolado.
- `authoritative_reader` é parâmetro **exclusivamente de código Python confiável** para ler uma fonte externa e comparar `authoritative_field`/valor esperado em memória; somente isso, acompanhado de `authoritative_resource_id` estável conferido com o campo `id` da leitura externa, permite estado `verified`, força 3, sem registrar valor/DOM/credenciais. Não comprova isoladamente autoria da alteração sem baseline causal. **Nenhuma integração de produção o invoca nesta etapa.** Essa interface não é uma tool/model API e a política de origem da leitura precisa ser verificada pela etapa P2.
- Não houve alteração em `workstation/kanban.py`, `hermes_cli/kanban_db.py`, owner Electron, Database visual, Trello/WhatsApp ou `AcceptanceEvaluator`. O recibo de P1 não é passado ao gate de conclusão canônico. `browser_batch_actions` ainda não é abrangido por este slice.

### Provas e limite
- **Estado real do owner, SOMENTE LEITURA:** `browser-session.json` existente, 255.848 bytes, 500 `operationAdmissions`, 464 acknowledged, 2 `BrowserTask` atuais com último recibo de `browser_click`/admissão correlacionada; uma tab `live` e outra `restored`/parked. O owner Electron já retorna `receipt` por operação e mantém ACK em `operationAdmissions`. **Não ocorreu um novo click/type no Chromium durante este P1**, e as respostas do Chromium usadas nos testes Python foram fixtures estruturais.
- **Testes executados:** `58/58 PASS` nas suites Python de Browser H080B/readback/observação (antes dos últimos ajustes, que tiveram suites focais posteriores); `27/27 PASS` em `workstation-browser-runtime-admission.test.ts` + `workstation-browser-batch-proof.test.ts` (Vitest Electron); `49/49 PASS` nos testes Python de Kanban/readback/recibos antes do último ajuste no teste HTTP; `33/33 PASS` na última suite `test_native_browser_operation_evidence.py` + fixture HTTP/SQLite após os últimos ajustes. Na suite combinada final anterior ao vínculo obrigatório de recurso: `86/86 PASS`.
- `py_compile` dos arquivos Python alterados e `git diff --check` sem erros; `ruff` não está instalado no venv inspecionado, portanto lint não foi dado como aprovado. Não fiz restart, nem nova homologação de runtime carregado.

### Aceite e próximo gate
- **P1 — contrato e cobertura automatizada:** IMPLEMENTADO, com regressões relevantes PASS e observação read-only do schema real.
- **P1 — nova operação real em Chromium + recibo correspondente:** AINDA NÃO HOMOLOGADA. O acesso ao owner existe, mas não foi executada mutação mesmo em fixture por esta missão. Prova end-to-end no Chromium do site QA isolado é gate P2; não afirmar que P1/P2 são homologados operacionalmente.
- **P2 permanece pendente:** vincular predicado de efeito persistido a cada commit, verificar fonte externa, avaliação canônica única de todas as ações e `done` correto. Se a futura leitura for só DOM/ACK, permanecer `observed`/`uncertain`.
- **P3 permanece pendente:** timeout e retomada genéricos de mutações Browser incertas sem click/POST repetido.

**Rollback localizado, se necessário:** remover apenas a função/arquivo `workstation/native_browser_evidence.py` e o bloco identificado pelo comentário `P1: same-owner causal ACK` em `tool_observer.py`, preservando todo restante da árvore dirty. Não usar reset/clean/stash global.


---

## P2 — Browser nativo → verificação persistida → Kanban DONE (12/11/2026)

**Estado: IMPLEMENTADO e HOMOLOGADO NO FLUXO QA ISOLADO; não homologado em sites terceiros.** Branch `main`, HEAD-base `f1d5ab2f03`, checkout com 571 alterações preexistentes na inspeção. Sem reset, clean, stash, checkout, commit, push, restart, CDP externo, Playwright ou automação global de mouse/teclado.

### Mudanças integradas

1. Novo `workstation/browser_operation_readback.py`: `BrowserReadbackContract` imutável, fornecido pelo **host confiável** (não por texto do modelo), exige exatamente um `commit_call_id` browser_click, chamadas `input_call_ids` browser_type anteriores, `resource_id`, `read_path` relativo same-origin sem query, campos esperados e revisão anterior/posterior crescente. Rejeita operação desconhecida/duplicada, falha, prova faltante, cache/owner divergente, status HTTP não-200, recurso/campo/revisão incompatível, GET em outra origem/rota. O browser lê GET com autenticação do próprio Electron (não API paralela), via `browser_read_http` com cabeçalho `Cache-Control: no-store`. EvidenceStrength `SEMANTIC_PERSISTED_READBACK=2`; a prova de SQLite independente em QA é externa ao verificador genérico. Artefato sanitizado (campos/revisão, hash do ID, sem título/credenciais/DOM).
2. `workstation/kanban.py::finalize_turn_candidate`: se a trilha observada contém browser_click/type, exige a verificação genérica em vez de concluir apenas por navegação ou ACK; aceita os verificadores especializados de arquivo/Trello/WhatsApp na via existente, sem misturar aprovação de ferramentas desconhecidas. O mesmo `complete_task_with_report` e `AcceptanceEvaluator` canônico executam CAS e registram `TaskRun`/`EvidenceRef`/`verifier_results`.
3. `workstation/integrations/hermes/completion_admission.py` transmite a referência `agent._work_browser_readback_contract` originada do runtime ao Kanban; não aceita um contrato fabricado em `turn_result`/chat.
4. Novo `workstation/tests/test_browser_kanban_canonical_readback.py`: testes de integração HTTP/SQLite, aceitação no banco QA isolado, divergência 409 e negativas de proveniência, campo, revisão, status, origem, sessão, operação, lote não coberto e falta de GET. Um DOM aparentemente correto não produz DONE sem fonte persistida.
5. `workstation/tests/fixtures/browser_kanban_qa_fixture.py`: a página QA foi adaptada para envio assíncrono **real** por `fetch('/save', POST)`, seguido de `GET /api/item`. A alteração impede a substituição do documento durante a confirmação de entrega do clique do owner. O POST continua gravando SQLite com CAS, revision e idempotência; **nenhum recibo foi simulado**. Os testes HTTP diretos da fixture continuam válidos.
6. Novo executor repetível, específico de QA e sem mocks: `workstation/scripts/browser_kanban_native_e2e_p2.py`. Isola `HERMES_KANBAN_DB` e `HERMES_HOME` em temp, usa o controller Electron autenticado existente e respeita o owner, cria TaskRun QA, navega/form, executa type + click uma vez, solicita GET nativo e lê SQLite do Kanban por outra conexão. Não faz retry de mutações incertas.

### Evidências de execução REAL separadas por fonte

- **Chromium/Electron:** controller preflight `runtime=electron-chromium`, `controlOwner=agent`, `controlReady=true`, sem lease humano, sem restart. No terceiro ensaio, `browser_navigate`, `browser_type` e `browser_click` executaram na BrowserTask nativa; ambos os recibos das interações foram observados (`native_type_observed=true`, `native_click_observed=true`). Não foi usado Playwright/CDP externo.
- **HTTP/SQLite QA:** diretório `C:\Users\KEVYNL~1\AppData\Local\Temp\hermes-p2-native-459e6d4132`. Primeira leitura `id=qa-1`, `revision=0`; após clique, nova resposta do servidor `revision=1`. Nova conexão SQLite encontrou `qa_item.revision=1` e `COUNT(qa_applied_operations)=1`. `PRAGMA quick_check=ok`.
- **Kanban SQL independente:** no mesmo diretório, `kanban-qa.db` tem `tasks.status=done` e `latest_run.status=done`, `workstation.acceptance_approved=true`, `outcome.status=verified_completed`, `EvidenceRef` hash validado, `verifier=native_browser_external_readback`, `evidence_strength=2`, `source_kind=browser_authenticated_same_origin_get` e operation_id compatível. `PRAGMA quick_check=ok`.
- **Ensaio 1:** `hermes-p2-native-e659861baa` navegou pelo Chromium real; parou ANTES de digitar porque o inventário nativo classificava o input como role `input` e não `textbox`; parser corrigido sem nova ação nessa TaskRun.
- **Ensaio 2:** `hermes-p2-native-d337c21509` digitou e um clique causou **um único POST real persistido** (revision=1), mas, devido ao 303 que trocou o documento durante a confirmação, o owner retornou `browser_input_delivery_unverified` e deixou o admission de click sem ACK. **Não foi repetido, não foi marcado DONE** (tarefa QA ficou running). O fluxo de reconciliação geral dessa incerteza pertence a P3; preservar admission original. O ensaio aprovado utilizou outra tarefa e outro banco QA, não repetiu a operação incerta.
- **Regressões Python:** a suite requerida e expandida com P1/P2 teve **104/104 PASS**. Após introdução das negativas adicionais `ui_only` e HTTP 500, os testes focais de P2 + fixture passaram **26/26**. `py_compile` e `git diff --check` sem erros. Ruff indisponível na venv; não alegar lint aprovado.
- **Suite Electron:** `npx vitest run --project electron electron/workstation-browser-runtime-admission.test.ts electron/workstation-browser-batch-proof.test.ts`: **27/27 PASS**. **Sem alterações no owner Electron.**

### Limites e gates remanescentes

- A validação principal é **homologação E2E em QA local**, NÃO uma aprovação para qualquer site, semântica arbitrária ou operação de WhatsApp/Trello. O contrato exige JSON confiável same-origin com `id` e `revision` e é armado pelo host confiável; tarefas normais sem esse contrato permanecem bloqueadas. A preparação automática de contratos a partir de objetivos de usuários não foi implementada.
- O backend Hermes já carregado não foi reiniciado/recarregado; a homologação exercitou código atual por novo processo Python e o proprietário Electron já ativo.
- Outras mutações, `browser_batch_actions` e operações com prova indisponível permanecem sem DONE. A proteção contra replay/reconciliação posterior de `browser_input_delivery_unverified` é escopo de P3, não desta entrega.
- Reversão restrita aos blocos de P2 em `kanban.py`/`completion_admission.py` e arquivos novos de P2, sem tocar em mudanças anteriores no checkout. Não limpar o admission incerto do Electron à força.

### Critério de aceite

**MVP QA APROVADO:** caminho real Browser nativo→POST→GET→Kanban DONE, verificação SQLite independente e caso divergente/falso sucesso rejeitado. Sem ativar sincronização externa; a extensão de disponibilidade operacional para agente já carregado depende de carregamento controlado posterior (não autorizado neste turno).

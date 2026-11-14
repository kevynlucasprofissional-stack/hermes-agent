# Plano unificado — Workstation Database, Trello via Browser e Cron catch-up
Data: 07/11/2026 | Branch canônica: main | Escopo: uso local do Hermes Work

## Baseline confirmado
- O arquivo de contexto consolidado do chat anterior (atualizado 07/11 16h09) reporta: 119/119 tarefas históricas recuperadas a partir de 123 cartões; `tarefas.sqlite` interno com 281 tarefas, 305 eventos, 278 vínculos e 0 violações FK (original ACIRV intocado, 162 tarefas e 246 violações); `trello.sqlite` interno com 395 cartões ativos, dos quais 190 foram recuperados dos exports offline. Essa é evidência do chat anterior, não prova de sync em tempo real.
- Não repetir recuperação nem reimportar snapshots de 205/162 por cima das cópias enriquecidas. Os importadores têm proteções contra sobrescrita parcial.
- O agente tem plugin `workstation_database_agent` habilitado no perfil Windows, com ferramentas `workstation_db_catalog/query/save` previamente testadas; existem outras rotas de edição de cards em `workstation/kanban_local.py`.
- Restante do sistema: Workstation `board.sqlite` e Kanban upstream mantidos separados; não criar segunda base de tarefas/sessões nem segundo scheduler.
- Repositório compartilhado contém alterações não commitadas e arquivos novos. Preservar tudo; sem reset, clean, stash, migração destrutiva ou reinicialização cega.
- A fonte de verdade remota só será Trello para os campos mapeados e confirmados; decisões de conflito prevalecem sobre o timestamp. Histórico de exports offline é preservado como evidência, não como reflexo atual do site.

## Entrega 1 — Gravação local controlada para humanos e agentes (PRIORIDADE IMEDIATA)
Objetivo: todos os atores editam os mesmos registros do Database, sem alterar arquivos originais nem permitir que futuras importações apaguem alterações.
Implementado nesta sessão como vertical slice:
- `workstation/dataset_edits.py`: patches de campos escalares sobre registros já existentes, por dataset/tabela/chave, no `local-edits.sqlite` privado; controle otimista `expected_revision`, eventos persistidos, bloqueio de PK/FK, preservação do valor original por campo e identificação de drift da fonte. Snapshots `tarefas.sqlite/whatsapp.sqlite/trello.sqlite` não são modificados.
- `workstation/acirv_datasets.py`: projeta edições locais em lista e detalhe; detalhe fornece `local_revision`, `pending_external_sync`, `source_conflict_fields`.
- `plugins/workstation-board/dashboard/plugin_api.py`: PATCH no registro para usuário do painel; `apps/desktop/src/plugins/workstation-board/{api.ts,dataset-explorer.tsx}`: editor JSON simples com salvar/cancelar e mensagem de edição local.
- `plugins/workstation_database_agent/__init__.py`: quarto tool `workstation_db_update` para agente, usando exatamente a mesma camada de edição.
- Testes da camada: 19 passaram (inclui regressões ACIRV/Trello); lint dos dois arquivos TS sem erros; despachante real do modelo aplicou e leu edição de uma tarefa temporária, rejeitou versão antiga e preservou original; API REST FastAPI PATCH temporária validada (200, GET correto e conflito 409).
Pendente antes de chamar Entrega 1 de ponta a ponta: teste em painel Desktop real após recarga controlada do backend/ativação do plugin na sessão nova. Ampliar criação de novos registros nas tabelas relacionais e UX de edição de campos se exigir uso real; atualmente `workstation_db_save` já cria registros próprios do agente, e o quadro interno já cria cartões. Não classificar a edição local como sincronização Trello.

Aceite mínimo: pessoa modifica uma tarefa no painel, fecha/reabre Hermes e mantém valor/revisão; agente lê a mesma tarefa e altera com revisão válida; conflito não perde dados; fontes originais intactas. Não reabrir cron ou sync até esse fluxo funcionar.

## Entrega 2 — Cron diário com recuperação de disparo perdido
Inspecionar `cron/scheduler.py`, `cron/jobs.py` e claims existentes: o scheduler atual usa `tick`, `claim_job_for_fire`, `fire_claim` e ledger. Corrigir NESSE scheduler, sem outro timer.
Regra: para job diário habilitado, quando `scheduled_at` já passou no dia local e não houve run daquele dia, colocar em execução assim que o gateway/agente estiver disponível (startup + tick). Identificar ocorrência por (job_id, data local, timezone), claim CAS durável e ledger, com uma ocorrência lógica por data. Distinguir não iniciado, sucesso, execução interrompida, efeito externo incerto; último caso exige reconciliação antes de retry. Não disparar tarefas concluídas em massa após vários dias offline sem uma política explícita de backfill; executar a ocorrência mais recente de maneira segura. Preferência: não rodar quando Browser/credenciais forem indisponíveis; deixar pendente com causa.
Aceite: simular reinício antes/depois do horário, executar 1 vez no dia perdido, não duplicar após dois restarts, não repetir efeito externo incerto.

## Entrega 3 — Sessão Trello autenticada pelo navegador interno
Fazer o agente usar SOMENTE Browser nativo/AI Control autenticado (não CDP adicional nem simulação global de cursor/teclado). Reusar a identidade e controles existentes. Detectar exigência de login/2FA e pausar sem bypass.
Descobrir todos os quadros autorizados do perfil, inclusive se algum dos exports se refere a quadro inacessível na sessão atual. Ler cartão ID, status, dueComplete/complete, lista, datas e metadados visíveis com paginação; validar se comentários/checklists/anexos/histórico carregam e o que fica inacessível. Provar uma leitura real e compará-la ao inventário local antes de qualquer envio.
Aceite: leitura repetível sem falsos 404, mesmo cartão sem duplicata, sem alterar dados no Trello.

## Entrega 4 — Reconciliação bidirecional
- Vincular stable ID de cartão/board/lista entre Trello e Hermes; preservar dados adicionais dos exports e a recuperação histórica; não reativar os 119 concluídos.
- Escopo contínuo: todos os cartões ABERTOS, não arquivados, sem complete/dueComplete, e não em listas finais; cartão concluído permanece no histórico.
- Campos: título, descrição, status/lista, responsável, prazo, etiqueta, checklists, comentários, anexos e histórico realmente disponíveis no Browser; respeitar tipos e limites de edição da UI.
- Rodada 1: pull/merge com checkpoint de versões e dry-run. Rodada 2: push permitido pelo navegador somente após confirmar identidade, cartão alvo, intenção do usuário e proteção contra envio duplicado. Toda mutação externa necessita registro da intenção antes da ação e leitura/verificação posterior; resultado incerto é HOLD, jamais retry cego.
- Detectar conflito por CAMPO usando baseline de última sincronização; salvar duas versões e solicitar decisão humana. Arquivamento sincronizado; exclusão exige confirmação e preservação do histórico.
Aceite: Trello→Hermes, Hermes→Trello, conflitos bilaterais, refresh/restart e nenhum item duplicado ou perdido em casos reais controlados.

## Entrega 5 — Integração Cron → Agente → Browser → Database
Um cron job diário do Hermes lança o agente com contexto e ferramenta Database, executa pull/diff/push com checkpoints, respeita limites/claims da Entrega 2, usa Browser nativo da Entrega 3 e persiste comprovantes e conflitos da Entrega 4. Relatório: cartões lidos, inseridos, atualizados em cada direção, conflitos aguardando decisão, não acessíveis, falhas/efeitos incertos. Execuções com login ausente ou Browser bloqueado não recebem status de sucesso artificial.
Aceite final: job diário perdido dispara após retorno sem duplicar, sincroniza uma edição em cada direção, persiste após reinício, só apresenta conflito para decisão, e mantém todos os bancos originais intactos.

## Ordem e recortes
1. Homologar Entrega 1 no Desktop; se necessário acrescentar criação de linhas sem mexer em PK de fontes externas.
2. Corrigir scheduler com testes de relógio/claim sem Trello envolvido.
3. Homologar leitura Browser Trello em uma conta/board real.
4. Sincronizar campo simples nos dois sentidos com replay seguro; ampliar para metadados e históricos apenas após prova.
5. Ativar cron job único e verificar disparo atrasado real. Não ampliar sistema para Grist/NocoDB inteiro, nem converter tudo em cartões.

## Situação nesta sessão
Entregues alterações de código locais da Entrega 1 e testes acima. NÃO implementados: catch-up, Browser Trello, sincronização e job diário. Nenhuma execução externa/mutação Trello, nenhum commit/push, nenhum reinício do Hermes. A sessão original de outra conversa está encerrada, mas alterações compartilhadas preexistentes devem continuar preservadas.

## Continuação de homologação — 07/11/2026 (sessão posterior)

- HEAD `f1d5ab2f03` na `main`; nenhuma alteração staged, nenhum commit/push/restart. Mantidas as edições concorrentes.
- AI Control: `node apps/desktop/scripts/hermes-nav.mjs status` retornou `AI Control endpoint unavailable` duas vezes. O usuário proibiu ações no mouse/teclado global; não contornar a ponte. Portanto **homologação de clique na UI real segue PENDENTE**, apesar do E2E API/dispatch anterior.
- Cron: código atual já implementa catch-up por padrão em `cron/jobs.py::_fast_forward_missed_recurring`; configuração efetiva do perfil `cron.catch_up_missed=True`, lista de jobs atuais `[]`. Nenhuma alteração no scheduler necessária nesta investigação. Adicionado teste persistente `tests/cron/test_catchup_policy.py::test_daily_outage_catchup_claims_once_and_reanchors_next_day`: ocorrência diária `06/11 09:00-03:00` recuperada em `07/11 17:00-03:00`, claim único, segunda tentativa recusada, próxima em `08/11 09:00-03:00`, mesmo após reabrir store. É validação de elegibilidade e claim, não execução externa.
- Regressões focadas: `python -m pytest -q tests/cron/test_catchup_policy.py tests/cron/test_claim_job_for_fire.py workstation/tests/test_workstation_dataset_edits.py workstation/tests/test_workstation_database_agent.py workstation/tests/test_acirv_datasets.py workstation/tests/test_trello_recovery.py workstation/tests/test_trello_inventory.py` → **44 passed, 1 warning** Starlette preexistente. ESLint dos dois arquivos Desktop: exit 0; `python -m py_compile` nos arquivos editados: exit 0. O runner padrão `scripts/run_tests.sh` no Windows não foi homologado por conflito de CRLF/shebang (ocorrido no ciclo anterior); testes executados pelo Python local.
- Segurança de SQLite: o executável Python 3.13 de teste usa SQLite **3.50.4**, e o próprio Hermes avisa sobre possível bug de WAL reset na família. Foram removidos os comandos que **ativavam WAL em novos bancos** de `workstation/dataset_edits.py` e `plugins/workstation_database_agent/store.py`; novas instâncias usam journal rollback, sem conversão de arquivos WAL abertos. `agent-generated.sqlite` existente permanece em modo WAL e NÃO foi convertido durante o uso. Dois `hermes serve` em execução observados: Python do `.venv` compilado com SQLite **3.53.4**, outro Python uv com SQLite **3.50.4**; este último escutava em `127.0.0.1:51048`. Não inferir qual backend cada sessão usa sem prova, não matar nenhum processo em uso. Antes de writes concorrentes de produção, confirmar interpreter da instância que atende o Desktop e qualificar/atualizar SQLite vulnerável com parada segura.
- Sem navegação Trello, sincronização ou cron job novo, pois não existe sessão Browser autorizada acessível via AI Control; não declarar as Entregas 3–5 prontas.
- Próximo gate exato: quando AI Control for reativado pelo usuário na janela correta, `hermes-nav status` deve retornar `aiControl:true`. Inspecionar leases e ledger da instância de backend, identificar versão do Python/SQLite e só então recarregar controladamente se necessário, sem mexer em sessões ativas. Usar um registro de teste **isolado**, não um cartão Trello produtivo, para provar UI editar → salvar → reler → reiniciar/reabrir, com o mesmo valor recuperado e revisões; preservar dados e conflitos. Depois leitura real de Trello pelo Browser, identidade autenticada e somente depois configurar o único cron diário de sincronização. Não criar job ativo que só produziria falhas em loop.

## Prova nativa após reativação do AI Control — 07/11/2026

A limitação anterior `AI Control endpoint unavailable` foi superada por reativação feita pelo usuário; `hermes-nav status` retornou `aiControl:true`. **Entrega 1 agora possui prova E2E de edição na UI Electron** (não apenas API): linha QA isolada `tarefas/people/-20261107001`, `role=qa-original` → `qa-ui-verified`, revisão 1, alerta 0, persistência após sair/voltar da visualização e consulta concordante por `workstation_db_query` do agente. Em seguida foram excluídos exatamente esse seed, sua revisão e um evento QA; `people=0`, `tasks=281`, FK=0, Trello 395 preservado. **Não houve restart de processo**; o requisito de persistência após reboot continua sem prova nativa devido a sessões ativas. Relatório de evidências: [database-ui-native-proof-20261107](engineering-journal/database-ui-native-proof-20261107.md).

**Entrega 2 (Cron)**: configuração `catch_up_missed=True` e código existente já satisfazem o requisito local de recuperação de ocorrências diárias, com prova de claim único, próximo slot e 44 testes focalizados verdes. Não criar novo scheduler. **Entrega 3 (Trello Browser) HOLD**: painel Navegador mostrou Task Rail WORKING do agente System1 no alvo `http://127.0.0.1:18791`; após restauração da interface, a tarefa estava `Task blocked — needs your input` com `outcome_not_verified`. Não há licença para reutilizar sua sessão/lease ou repetir efeitos incertos. Nenhuma página Trello foi aberta. **Entregas 4/5**: ainda não implementadas/sem cron job criado.

**Risco de SQLite em produção**: `local-edits.sqlite` foi criado em WAL pelo backend já carregado, mesmo com fontes atuais configuradas para não forçar WAL em novas stores. Há intérpretes Hermes concorrentes com SQLite 3.50.4 (alerta WAL reset) e 3.53.4; o banco já existente não foi convertido com conexões abertas. Qualificar o backend realmente em uso e atualizar/converter somente após parada controlada e verificação de leases. Voltar ao Browser Trello apenas quando o owner não estiver pendente/incerto; então leitura autenticada e não destrutiva, base de comparação e só depois escrita bidirecional verificada.

## Correção da autoridade de leitura — 07/11/2026 (ciclo de continuação)

E3: Browser nativo autenticado lê o cartão #944 e o mesmo ID de `trello.sqlite` com URL, título `Hermes Work`, lista Quarta e status aberto. As BrowserTasks System1/Instagram foram mantidas estacionadas sem lease; nenhuma ação externa incerta foi repetida.

E4 (slice pronto): `workstation_db_trello_plan` agora EXIGE `browser_task_id` e obtém o nome/status por leitura independente do Browser, ignorando valores remotos declarados pelo agente. `workstation_db_trello_pull` exige review com `native_observed=True`, verifica novamente título, URL, lista e status da mesma BrowserTask antes de aplicar campo `name` no overlay por CAS. Descrição/placeholder e campos ainda não verificados estão fora do slice. Prova nativa com dispatch do agente em base temporária (sem gravar dados de produção) e regressão focal: **63 testes Python PASS**; seis ferramentas Database publicadas no esquema de processo novo.

Produção conferida em leitura: **281 tasks, 395 Trello cards, quick_check=ok**; `local-edits.sqlite` com 0 edits e WAL; `trello_sync_reviews` não criada em produção. **Sem push Hermes→Trello, sem job diário, sem restart, sem commit/PR.** Próximo gate de produto: push do título por ação Browser com registro prévio da intenção, recibo e readback, qualificado em cartão QA; depois ampliar cobertura e só então cron. Relatório detalhado: [RELATORIO_TRELLO_DATABASE_20261107.md](RELATORIO_TRELLO_DATABASE_20261107.md).


## 2026-11-08 - TR_ROUTE_QA3_20261108

QA3 native Browser outbound title VERIFIED: durable intent before effects, two owner receipts, reload readback and independent Trello connector read. Card https://trello.com/c/nzlI4GhN, new title Hermes Sync QA - two step push validated 20261108; intent 12be978fa45c39829709d3214282a1de verified once. Earlier QA1/QA2 uncertainties preserved without replay.

New decision: board admin can use official Trello API; ordinary member uses agent-controlled native Browser. workstation/trello_sync_transport.py::route_for_board checks authenticated member ID, board ID and membership role; unknown permissions HOLD. Agent tool workstation_db_trello_route is read-only and requires profile secret scope. Verified account admin roles: ACIRV + VCOM SCRUM, Vontade SMART, +Bela, Hermes Sync QA. Local Hermes lacks API key/token, so API end-to-end unqualified; ChatGPT connector credentials are not inherited. Guest LEADS DE ASSOCIADOS native read passed with no write. 103 Python tests PASS; 281 tasks/395 cards intact; no sync Cron, commit/PR/restart. See RELATORIO_TRELLO_HIBRIDO_20261108.md.


## 2026-11-08 - API_REST_QA_P0_20261108

Priorizacao unificada: primeiro credenciais Trello no escopo do perfil Hermes e E2E real API no QUADRO QA (API plan equal -> edit CAS -> API plan push -> intent -> PUT unico -> GET confirmatorio). Codigo QA-only em workstation/trello_sync_api.py e dois tools agent novos, 114 tests PASS, sem API PUT real por credenciais ausentes. Nao usar connector ChatGPT como credencial Hermes, nao repetir QA1/2 uncertain ou QA3 verified. Depois qualificar Browser em board normal, inventario aberto e conflitos, e somente entao cron unico catch_up_missed=True. Ler RELATORIO_TRELLO_API_20261108.md.

## 2026-11-08 - bloqueio de autenticacao persistente

Retomada em main@f1d5ab2f03, staging vazio, AI Control ativo. A .env do perfil Hermes existe mas TRELLO_API_KEY e TRELLO_TOKEN estao ausentes; nenhum PUT real, cartao QA ou mudanca de codigo. 281 tarefas e 395 cartoes inteiros; QA1/QA2 uncertain, QA3 verified preservados. Proximo passo necessario: configurar credenciais no proprio perfil, validar route=api, criar novo QA e fazer push unico com journal e readback. Browser membro, conflito por campo e cron ficam depois. Ver RELATORIO_TRELLO_API_20261108.md.

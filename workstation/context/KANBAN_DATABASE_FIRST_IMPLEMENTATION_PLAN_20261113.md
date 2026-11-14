# Plano de implementação — Hermes Database-first + Kanban Nous auxiliar
**Data:** 13/11/2026 | **Projeto:** C:\Github\hermes-agent | **Referência inspecionada:** main@f1d5ab2f03 | **Estado:** P1 **aprovado em despacho único real e UI**; despacho periódico via gateway ainda **não homologado**. P2–P4 planejados; nenhum patch de produção necessário na P1.

### Evidências P1 — 13/11/2026 (execução real, sem integração externa)

- Preflight: `main@f1d5ab2f03`, **596 entradas dirty** antes da execução; gateway Nous **NOT RUNNING**; Electron PID 29312 e `serve` PIDs 20016/25536 ativos; AI Control autenticado `true`. Banco `kanban.db` padrão com **135 tarefas**, 17 `ready`, todas sem `assignee`; `PRAGMA quick_check=ok`.
- Foi criado só o board QA `qa-kanban-p1-20261113125039`, **sem trocar o board atual operacional**. IDs: atribuído `t_12f55d54`, sem responsável `t_374aa578`. Sem efeitos externos; idempotency_key QA e workspace scratch.
- `kanban --board qa-kanban-p1-20261113125039 dispatch --dry-run --max 1 --json`: previa apenas `t_12f55d54`. `dispatch --max 1 --json` REAL: worker próprio spawnado e TaskRun id **1** efetiva.
- `task_events`: `created → claimed → spawned → heartbeat → completed`; `task_runs.id=1`, `status=done`, `outcome=completed`, `summary` persistido; chamada real `kanban_show` e `kanban_complete` registrada em `kanban/boards/qa-kanban-p1-20261113125039/logs/t_12f55d54.log`. Duração SQL entre start/end ~16 s.
- Negativa: `t_374aa578` continua `ready`, `assignee=NULL`, **0 TaskRuns**. QA `quick_check=ok`; default `kanban.db` manteve 135 tarefas, **0 IDs QA**.
- API REST real do plugin validada **via TestClient ASGI do mesmo router**: `GET /api/plugins/kanban/board?board=qa-kanban-p1-20261113125039` → HTTP 200; `ready` sem assignee e `done` com resumo. **Não confundir TestClient com chamada ao servidor live.**
- UI live da janela Electron: AI Control nativo abriu `Kanban` via botão `Open Kanban`; menu de boards selecionou `QA Kanban Nous P1`; exibiu **2 tarefas**, `READY=1` (sem responsável) e `DONE=1` com o resumo correto. Nenhum uso de mouse/teclado global ou CDP.
- Regressão: os 4 arquivos de teste focal do dispatcher/gateway totalizaram **11 passed** (pytest via `.venv`). Nenhuma mudança de código, migração, reset, restart, commit, push ou edição do Database/WhatsApp/Trello.
- **Limitação material:** `hermes gateway status` continua parado. Não ativado para evitar disparo de cron/plataformas/outros cartões por gateway global; logo **tick periódico real do gateway ainda não homologado**. Não afirmar que o Kanban executará tarefas automaticamente sem gateway ativo. A P1 central (worker + SQLite + API + UI) passou via despacho único real; somente gateway automático permanece pendente de janela/instância QA isolada autorizada.


## 1. Decisão arquitetural vinculante

**Database do Workstation é a fonte de verdade dos registros operacionais locais que ele gerencia. O Kanban Nous não é autoridade central do Hermes.** O Kanban possui autoridade apenas pelo próprio ciclo de vida da tarefa (assignee, TaskRun, ready/running/blocked/review/done e eventos), jamais pelo conteúdo de dados operacionais, cartões locais ou resultados de um serviço externo. O conteúdo externo só é declarado realizado mediante verificação da fonte apropriada. A projeção de um status no Database é informativa: não pode sobrescrever registros de negócio, ações locais ou decisões humanas.

Não colapsar estes contratos em um único SQLite nem introduzir um “gerenciador universal”:
- **Database / quadros locais:** workstation/kanban_local.py, banco get_hermes_home()/workstation/board.sqlite; plugin REST plugins/workstation-board/dashboard/plugin_api.py; UI apps/desktop/src/plugins/workstation-board/board.tsx em /browser?module=database. Tabelas boards/cards/card_delegations; CAS por revision; edições humanas são independentes do Kanban executável.
- **Database / bases relacionais:** workstation/acirv_datasets.py (snapshots importados) + workstation/dataset_edits.py (local-edits.sqlite versionado); **snapshots originais imutáveis**, conflito por revisão; interface da mesma área Database.
- **Database / registros do agente:** plugins/workstation_database_agent/store.py, datasets/agent-generated.sqlite, namespaces/chaves/revision; ferramentas workstation_db_catalog/query/save/update. É armazenamento de registros, não de credenciais nem de estado canônico de sessões.
- **Kanban Nous:** hermes_cli/kanban_db.py + kanban_db_dispatch.py; gateway/kanban_watchers.py; plugin REST plugins/kanban/dashboard/plugin_api.py; UI apps/desktop/src/plugins/kanban. Banco kanban.db isolado por board, ferramenta kanban_* do worker. É uma fila/caderno de tarefas, não substituto do Database.
- **Ligação já existente:** workstation/kanban_local.py::{begin_delegation,link_delegation,reconcile_delegation}, workstation/task_adapter.py::{create_official_task,get_official_task_status}, REST /cards/{card_id}/delegate e /cards/{card_id}/delegation/sync. A delegação é explícita e idempotente; a sincronização apenas projeta status. Não criar tabela de vínculo duplicada.
- **Browser:** owner Electron + operationAdmissions, tools/browser_workstation.py, workstation/browser_operation_readback.py, native_browser_evidence.py, completion_admission.py. Uma mutação incerta nunca pode ser repetida como “recovery”.
- **WhatsApp/Trello:** serviços externos mantêm o estado externo. Seus executores existentes não delegam autoridade de dados ao Kanban. Trello fica FORA DE ESCOPO de implementação nesta sequência.

## 2. Evidências, hipóteses e decisões

**Comprovado por leitura do checkout (13/11):** o Workstation Database e o Kanban Nous têm bancos, APIs e rotas distintos; a delegação local para tarefa oficial já está implementada. A criação por task_adapter.py usa created_by="workstation-database", idempotency_key, board=None e initial_status="running"; hermes_cli/kanban_db_graph.py::initial_task_state converte essa criação sem pais em **ready**, portanto NÃO corrigir esse argumento por inferência. O dispatcher já existe e usa o gateway. CLI aceita kanban boards create, create --assignee, dispatch, diagnostics e gateway status. O perfil CLI possui kanban/browser, mas desktop_ui/whatsapp_send_message não foi comprovado como disponível num worker CLI.

**Snapshot operacional anterior, sujeito a rechecagem:** no banco local kanban.db, 122 tarefas (87 blocked com needs_input, 13 ready, 17 triage, 3 todo, 1 done, 1 archived), todas sem assignee; quick_check=ok. Gateway status retornou NOT RUNNING; dois processos serve não equivalem a um gateway/dispatcher. Não iniciar o gateway global baseado só nesse snapshot: pode haver tarefas novas atribuídas desde então.

**Já validado, NÃO reimplementar:** P1/P2 Chromium → POST único → GET autenticado → TaskRun DONE em QA isolado, inclusive entrada real AIAgent.run_conversation; readback P3 de ACK perdido testado com falha injetada e negativas. Falha espontânea de ACK/HTTP303 no Electron e runtime ativo não homologados em P3. Não transformar P3 em requisito para funcionamento básico do Kanban.

**Hipóteses abertas:** (i) despacho real de worker via gateway e UI no processo atual; (ii) eventual desvio de status na projeção da delegação Database → tarefa oficial; (iii) vínculo do worker com sessão Chromium nativa, pois HERMES_SESSION_SOURCE="kanban" não é a sessão "desktop"; (iv) autorização, toolset e execução de WhatsApp pelo worker. Resolver cada hipótese **apenas na sua etapa**, começando pelo experimento mínimo.

**Critérios de arquitetura:** não criar outro scheduler, fila, state store, replica/sincronizador genérico, servidor Browser ou AcceptanceEvaluator. Não promover nenhum campo do Kanban a fonte de verdade de negócios. Nunca migrar as 122 tarefas históricas por aproximação, atribuir perfis em massa, limpar o checkout (~594 dirty), ativar autosserviço persistente/cron ou tocar Trello/WhatsApp reais sem escopo expresso. Usar QA isolado e preservar serviços abertos.

## 3. Sequência, dependências e critério de avanço

| Ordem | Entrega | Dependência | Critério de avanço |
| --- | --- | --- | --- |
| P1 | Kanban Nous operacional com 1 worker e 1 board QA | nenhuma | worker real captura ready→running→done, resposta persistida, UI reflete estado, sem executar cartões alheios |
| P2 | Database como fonte do cartão e vínculo opcional à tarefa | P1 para prova de execução; código atual independente | edição Database persiste; delegação explícita idempotente e status projetado; edição não sobrescrita |
| P3 | Worker Kanban usa Browser nativo quando autorizado | P1; P2 não obrigatório | em fixture isolada, Electron faz 1 commit, GET comprova, TaskRun DONE, operação incerta sem replay |
| P4 (opcional, sessão futura) | Worker compatível com WhatsApp nativo | P1/P3 + autorização específica | executor correto recebe 1 chamada QA, identidade e resultado corretos; sem envio real não autorizado |

**P4/Trello da nomenclatura antiga** não é o P4 acima: sincronização Trello é backlog independente. O plano Browser/Kanban anterior, em BROWSER_KANBAN_GENERIC_VERIFICATION_PLAN_20261112.md, é referência técnica de P1/P2/P3 do Browser, NÃO roteiro ativo deste plano. Superpowers/community-agent-workflows podem ser consultados como técnica de execução, nunca como razão para introduzir dependências ou mais gates.

### Comandos de diagnóstico já compatíveis com a CLI observada (somente leitura)
~~~powershell
Set-Location 'C:\Github\hermes-agent'
$py = '.\.venv\Scripts\python.exe'
git status --short
git diff -- workstation/task_adapter.py workstation/kanban_local.py hermes_cli/kanban_db.py
& $py -m hermes_cli.main gateway status
& $py -m hermes_cli.main profile list
& $py -m hermes_cli.main kanban stats
& $py -m hermes_cli.main kanban diagnostics
~~~
Se o Gateway estiver ativo na inspeção nova, reutilizá-lo; não iniciar segundo dispatcher. Para autorizações e acesso ao Windows, usar o conector Controle Windows / Remote Desktop Commander. Não usar mouse/teclado globais; para UI nativa usar somente a ponte AI Control já existente.

## 4. Prompt 1 — Kanban upstream realmente executável [EXECUTAR PRIMEIRO]

~~~text
MISSÃO: homologar e corrigir somente o funcionamento básico do Kanban Nous no Hermes Work, SEM torná-lo fonte de verdade do Database e SEM integrar Browser/WhatsApp/Trello.

Projeto: C:\Github\hermes-agent. Leia o plano vigente workstation\context\KANBAN_DATABASE_FIRST_IMPLEMENTATION_PLAN_20261113.md; use o plano BROWSER_KANBAN_GENERIC_VERIFICATION_PLAN_20261112.md apenas para preservar patches anteriores. Checkout compartilhado dirty, branch main; não reset/stash/clean/commit/push, não reiniciar processos alheios.

Arquitetura real: kernel hermes_cli/kanban_db.py, dispatcher hermes_cli/kanban_db_dispatch.py, gateway/kanban_watchers.py, UI apps/desktop/src/plugins/kanban/board.tsx, REST plugins/kanban/dashboard/plugin_api.py, worker toolset kanban_*, config kanban.dispatch_in_gateway. O Kanban coordena somente suas tarefas. Database separado em workstation/kanban_local.py e dataset_edits.py não pode ser alterado por efeito de ciclo de vida.

Fatos anteriores a revalidar: gateway status NOT RUNNING; banco canônico com 122 tarefas e nenhuma com assignee; perfil default configurado; CLI com kanban boards create e kanban dispatch. Esses valores podem ter mudado. Inspecione PIDs, configuração e assignees atuais antes de iniciar dispatcher; se já existir gateway/dispatcher, reutilize-o. NÃO atribua em massa tarefas históricas.

EXECUÇÃO:
1) Verifique em leitura o Gateway, os perfis e as tarefas prontas com assignee. Identifique se iniciar gateway varreria outras tarefas operacionais. Se houver qualquer risco de despacho alheio, faça E2E em HERMES_HOME/board QA isolado com o mecanismo atual de resolução segura de modelo, sem copiar nem imprimir segredos. Não altere o gateway global até essa segurança estar resolvida.
2) Use apenas um board QA com slug novo e uma tarefa mínima, sem ações externas, assignee=default, workspace scratch. Exemplo de sintaxe previamente confirmada:
   $py='.\.venv\Scripts\python.exe'
   & $py -m hermes_cli.main kanban boards create qa-kanban-<slug-novo> --name 'QA Kanban'
   & $py -m hermes_cli.main kanban --board qa-kanban-<slug-novo> create 'QA gravar resumo local' --assignee default --body 'Produzir resposta curta sem efeitos externos' --idempotency-key qa-kanban-<slug-novo>
   (Substitua o slug por um valor novo válido, confira os IDs retornados e NUNCA cole o placeholder literalmente.)
3) Execute uma passada de dispatcher no board QA por 'kanban --board <slug> dispatch' ou gateway controlado existente, depois teste o despacho normal pelo gateway se puder isolá-lo. O teste só vale como real se o worker/processo modelo executar kanban_show + tarefa + kanban_complete, e se SQLite/REST mostrarem o mesmo run DONE. Um spawn falso, mock ou status manual NÃO prova essa etapa.
4) Confirme interface /kanban e atualização de TaskRun real. Em Windows use a bridge AI Control autenticada, sem teclas/cliques globais. Teste um cartão sem assignee apenas em QA; ele não pode ser executado.
5) Só se surgir falha reproduzível, ajuste o menor ponto (gateway/kanban_watchers.py, kanban_db_dispatch.py, REST/plugin UI ou configuração). Não crie daemon nem worker alternativo. Não relacione o Database ao dispatcher.

TESTES FOCAIS: tests/hermes_cli/test_kanban_dispatch_tick_hook.py, test_kanban_dispatch_lock.py, test_kanban_worker_spawn_toolsets.py, tests/gateway/test_kanban_notifier_watcher_dispatch_gate.py e apenas o teste do módulo alterado; usar .venv e runner do repo disponível. Registre run_id, transições e leitura SQL independente; não afirmar homologação de gateway se só executou dispatch one-shot.

ACEITE: 1 tarefa QA atribuída e executada por worker real -> DONE; 1 sem assignee não executada; mesma informação em backend e UI; nenhum cartão operacional modificado. Se o ambiente impedir gateway real, registre exatamente o bloqueio e o alcance efetivo da prova, sem simular PASS.

FINALIZAÇÃO: registre no plano vigente o estado real e no engineering-journal/CURRENT.md apenas evidências, arquivos alterados, PIDs/board QA, testes/resultado, pendências; sem reabrir P2/P3 Browser nem expandir escopo.
~~~

## 5. Prompt 2 — Database-first e delegação opcional [APÓS P1]

~~~text
MISSÃO: validar e, somente se necessário, corrigir a convivência Database do Workstation ↔ tarefas Kanban Nous. Database é fonte de verdade dos registros e do cartão local. Kanban é apenas o ciclo de vida da tarefa delegada. Não centralizar dados no Kanban.

Projeto: C:\Github\hermes-agent. Plano: workstation\context\KANBAN_DATABASE_FIRST_IMPLEMENTATION_PLAN_20261113.md. Só iniciar após P1 ter comprovado pelo menos um worker/TaskRun QA real. Preservar checkout dirty, bancos e processos. Sem Trello/WhatsApp reais.

COMPONENTES JÁ EXISTENTES:
- workstation/kanban_local.py: board_path() e database(), tabelas cards/card_delegations, CAS por revision; begin_delegation, link_delegation, reconcile_delegation.
- plugins/workstation-board/dashboard/plugin_api.py: /cards/{card_id}/delegate (confirmação explícita, intenção durável), /cards/{card_id}/delegation/sync; REST não importa upstream Kanban fora do task_adapter.
- workstation/task_adapter.py: create_official_task e get_official_task_status; deduplicação pelo idempotency_key; cria tarefa na placa oficial com created_by="workstation-database". ATENÇÃO: initial_status="running" é normalizado para ready sem pais em hermes_cli/kanban_db_graph.py::initial_task_state; não “corrigir” esse argumento sem teste de falha.
- workstation/acirv_datasets.py + dataset_edits.py: snapshots imutáveis, local-edits.sqlite revisionado; plugins/workstation_database_agent/store.py: agent-generated.sqlite; workstation_db_query/update/save.
- UI Database: apps/desktop/src/plugins/workstation-board/board.tsx; o Kanban próprio da Nous fica em /kanban.

EXECUÇÃO:
1) Revalide que as três superfícies do Database — cartões locais, registros do agente e bases importadas+overlay — continuam independentes da fila Nous. Não mova tabelas para kanban.db nem transforme status Kanban em valor de negócio.
2) Teste em HERMES_HOME temporário, usando o REST existente ou funções reais: criar um cartão local QA, editar título/descrição com expected_revision, ler novamente; solicitar delegação explícita duas vezes com a MESMA idempotency_key; confirmar uma única tarefa oficial; executar/sincronizar e verificar que apenas card_delegations.task_status/state mudou, sem mudar cards.title/description ou a base relacional. Testar 409 de revision incorreta e falha de link recuperável sem segunda task.
3) Só havendo falha comprovada, corrigir em task_adapter.py, kanban_local.py, plugin_api.py ou no painel consumidor. Reutilizar begin_delegation/link_delegation/reconcile_delegation; não criar novas tabelas, sincronizador bidirecional, migração ou worker para fazer projeção simples. Não ligar automaticamente qualquer cartão a tarefa sem ação explícita.
4) Com teste funcional passado, conferir via UI Database que o cartão original continua editável e que a referência delegada mostra o estado oficial apenas como projeção. Se só API passou, registrar UI pendente em vez de declarar E2E.

TESTES FOCAIS: tests/workstation/test_s04_delegation.py, workstation/tests/test_workstation_database_agent.py, workstation/tests/test_workstation_dataset_edits.py; adicionar apenas teste do defeito encontrado. NÃO usar datasets reais como fixture.

ACEITE: Database mantém conteúdo/revisão; 1 intenção delegada -> no máximo 1 TAREFA oficial (cada tarefa pode ter mais de uma TaskRun legítima); status do Kanban não sobrescreve dados; conflito CAS preservado; resultado lido novamente na API/UI. Se já funcionar, NÃO modificar produção.

REGISTRO: atualizar apenas o plano vigente e CURRENT.md com prova, arquivos alterados, testes e bloqueios. Não duplicar documentação.
~~~


## 6. Prompt 3 — Worker Kanban usa Chromium interno [APÓS P1; P2 INDEPENDENTE]

~~~text
MISSÃO: validar e, somente diante de falha real, corrigir o uso do navegador Chromium NATIVO do Workstation por um worker Kanban da Nous. Kanban não controla dados de negócios: apenas sua TaskRun.

Repo C:\Github\hermes-agent; ler workstation\context\KANBAN_DATABASE_FIRST_IMPLEMENTATION_PLAN_20261113.md e, como referência já implementada, BROWSER_KANBAN_GENERIC_VERIFICATION_PLAN_20261112.md. P1 deste plano deve ter executado um worker real; P2 Database não é pré-requisito. Sem Trello e WhatsApp reais.

INSPECIONAR SOMENTE: hermes_cli/kanban_db_dispatch.py::_default_spawn (HERMES_KANBAN_TASK/RUN_ID, HERMES_SESSION_SOURCE="kanban"); tools/browser_workstation.py::{workstation_desktop_session,workstation_route_is_bound,_dispatch}; tools/browser_extension_router.py::route_browser_tool; workstation/integrations/hermes/browser_controller.py::ensure_workstation_browser_controller e adapter.py; agent/tool_executor.py; workstation/{native_browser_evidence.py,browser_operation_readback.py,kanban.py}; integrations/hermes/completion_admission.py. Owner Electron mantém operationAdmissions. P2 já passou Chromium + 1 POST + GET + TaskRun DONE em AIAgent QA isolado; não refazer P1/P2 por hábito.

EXECUTE:
1. Com UMA TaskRun de worker real e fixture HTTP/SQLite QA, observe se browser_navigate chega ao owner Electron correto. Se já funcionar, não altere roteador.
2. Se a origem kanban impedir acesso, conecte somente uma TaskRun autorizada ao controller Workstation EXISTENTE, no menor ponto de provider/broker, com task_id/run_id/session_id/aba/host válidos. Não force HERMES_SESSION_SOURCE="desktop" globalmente, não exponha browser a workers sem autorização, não habilite fallback Playwright ou CDP externo. Não aceite vínculo vindo do texto livre do modelo.
3. Faça uma edição QA: navigate, type, exatamente UM click/POST, GET read-only com recurso, campo, revision e operation_id. Passe pelo AcceptanceEvaluator já existente. Um resultado divergente ou ACK perdido sem prova fica UNCERTAIN, sem segundo click e sem ACK fabricado. Não repetir a operação histórica t_e31b4463.
4. Verifique a TaskRun correta DONE só com prova persistida; erro de run/origem bloqueia. Medir tempo e chamadas nativas, eliminar apenas redundâncias demonstradas.

TESTES FOCAIS: workstation/tests/test_browser_kanban_host_expectation.py, test_browser_kanban_canonical_readback.py, test_browser_kanban_uncertain_reconciliation.py, test_browser_workstation_route.py; somente regressões dos módulos alterados. Se mudar owner Electron, rodar seus testes focais. Teste mock ou processo Python isolado não substitui a prova pelo worker real.

ACEITE: worker real usa Electron, um commit QA, GET confirma, mesma TaskRun DONE; readback divergente/ACK incerto nunca é replay; sessão normal Desktop intacta. Se for impossível obter autorização host para o worker, documentar bloqueio sem enfraquecer a validação e sem bloquear o Kanban P1.

FINAL: patch mínimo, comandos/testes/resultado, ids de QA, evidências de GET e TaskRun, duração, pendências; atualizar plano e CURRENT.md.
~~~

## 7. Prompt 4 — WhatsApp como ferramenta opcional (ADIAR; não bloqueia Kanban)

~~~text
MISSÃO FUTURA, executar SOMENTE quando o usuário autorizar: conferir se o worker Kanban consegue acionar o executor whatsapp_send_message nativo existente, sem transformar o Kanban em origem de verdade de conversas, destinatários ou mensagens.

Repo C:\Github\hermes-agent; plano workstation\context\KANBAN_DATABASE_FIRST_IMPLEMENTATION_PLAN_20261113.md. P1 e o vínculo Browser de P3 precisam estar homologados para tentar qualquer envio real. NUNCA enviar em teste sem autorização explícita de destinatário/conteúdo. Trello não pertence a esta missão.

INSPECIONAR: toolsets.py (whatsapp_send_message pertence a desktop_ui); tools/browser_tool.py::_handle_whatsapp_send_message; tools/browser_workstation.py::whatsapp_send_message; agent/tool_executor.py (admitted_whatsapp_point_send); workstation/integrations/hermes/{whatsapp_browser_executor.py,whatsapp_native_send_bridge.py,whatsapp_recipient_resolution.py}. O perfil CLI já inspecionado tinha kanban/browser, mas não desktop_ui; não habilitar desktop_ui inteiro globalmente.

EXECUTE: identificar a permissão/capacidade realmente faltante. Se necessário, expor SOMENTE o executor existente a worker com vínculo canônico TaskRun + owner + destinatário autorizado. Não criar sender, scheduler, segundo Kanban, fila ou aprovações redundantes. Primeiro fixture sem efeitos externos: recusa pré-envio FAILED/no_effect; resultado pós-clique sem prova UNCERTAIN, sem replay. Envio real individual somente com autorização específica numa sessão futura e prova de saída independente do WhatsApp. Um TaskRun DONE nunca equivale por si só a mensagem entregue.

TESTES: workstation/tests/test_whatsapp_point_admission.py, test_whatsapp_fast_send.py, test_kanban_evidence_recovery.py e rota modificada. Aceite limitado a compatibilidade/negativas em QA até haver envio real autorizado; registrar exatamente o que foi ou não comprovado. Preservar checkout dirty, bancos e processos; atualizar somente CURRENT.md e plano com resultado e bloqueios.
~~~

## 8. Regras de execução e rollback comuns

- Cada prompt é autossuficiente, verificando o código REAL, o status do checkout e os PIDs antes do patch. Reutilizar Superpowers/community-agent-workflows somente se acrescentarem valor mensurável, sem fases obrigatórias novas.
- A leitura de kanban.db operacional, board.sqlite operacional e datasets é diagnóstica; teste de escrita em board/datasets QA isolados. Não converter WAL, não apagar registros legados nem migrar cartões históricos, não atribuir perfis em massa.
- Config QA exemplificativa, NÃO aplicar cegamente no perfil real: kanban.dispatch_in_gateway=true, dispatch_interval_seconds=60, max_in_progress=1 e max_in_progress_per_profile=1. O gateway global pode varrer TODOS os boards; verificar tarefas operacionais atribuídas antes de iniciá-lo. Preferir HERMES_HOME QA isolado ou dispatch one-shot com board explícito quando necessário; one-shot não prova operação automática do gateway.
- Sem reset/stash/clean/commit/push/restart automático, nem interrupção de processos de outros agentes. AI Control autenticado para interface; não usar mouse/teclado global nem CDP externo.
- Credenciais devem usar a resolução já existente do perfil; não copiá-las para arquivos QA ou relatórios. Ferramentas externas não executadas sem autorização. Um commit potencialmente persistido nunca é repetido como “verificação”.
- Evidência proporcional: SQL read-only + TaskRun real para workflow; revisão e readback do Database para dados; GET independente para persistência Browser; recibo WhatsApp para envio. Não exigir GET HTTP em tarefas locais sem HTTP.
- O implementador pode corrigir ou simplificar uma proposta confrontando-a com o estado real, mas deve justificar desvios e preservar o modelo Database-first. Se teste ou implementação não aproximar do MVP em duas rodadas, reduzir o escopo.
- Rollback de código: reverter somente blocos introduzidos por aquela missão, após revisar diff e trabalho paralelo; nunca reset global. Sem reversão de dados reais por scripts improvisados. Manter QA rastreável.
- P3 Browser e P4 WhatsApp são INDEPENDENTES da aceitação do Kanban Nous P1. Trello continua backlog de outra sessão, SEM prompt ativo neste plano.

## 9. Relatório obrigatório ao encerrar cada prompt

Informar concisamente: objetivo funcional alcançado; arquivos/patches feitos; decisões técnicas e desvios; comandos/testes e PASS/FAIL; evidência operacional real (TaskRun, board, readback, logs necessários); quais processos/dados foram preservados; limitações; bloqueios restantes e próxima etapa apropriada. Nunca reportar build, mock ou documentação como homologação real.

**Estado desta etapa:** plano e prompts preparados; P1–P4 deste plano NÃO foram implementados ou homologados por esta preparação. Nenhum servidor, banco ou tarefa operacional foi modificado por estes prompts.

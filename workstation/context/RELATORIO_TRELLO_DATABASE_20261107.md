# Relatório de engenharia — Hermes Work / Database ↔ Trello

**Data:** 07/11/2026  
**Repositório:** `C:\Github\hermes-agent`  
**Branch/HEAD:** `main` / `f1d5ab2f03`  
**Situação:** sincronização **parcial**; leitura Trello nativa e importação controlada para Database disponíveis como MVP limitado a título de cartão existente; envio Hermes → Trello **não implementado**, cron de sincronização **não cadastrado**.

## Resultado entregue neste ciclo

1. **Browser nativo autenticado.** Reativação AI Control confirmada. A BrowserTask isolada `trello-native-read-20261107` abriu a conta Trello e leu o quadro ACIRV + VCOM: SCRUM; card #944 `https://trello.com/c/gZy747hA/944` foi identificado com título `Hermes Work`, lista `Quarta`, estado aberto e duas pendências de checklist. O cartão #934 também foi acessível. As tarefas prévias de System 1 e Instagram permaneciam `parked`, sem lease assumido por esta missão. Nenhum efeito remoto executado.
2. **Prova remota obrigatória.** `workstation/trello_sync_reconcile.py::verified_browser_card_title` lê título, URL, lista e indicador de conclusão por script fixo de inspeção no BrowserTask nativo; bloqueia páginas não-Trello, títulos ausentes e listas finais. Não usa mouse/teclado global, CDP externo nem JavaScript fornecido por cartões.
3. **Agente não pode inventar estado remoto.** `workstation_db_trello_plan` (plugin `plugins/workstation_database_agent`) agora exige `browser_task_id` e obtém os dados remotamente, de forma independente do texto informado pelo agente. Planeja exclusivamente **título**; não considera placeholder de descrição como conteúdo. Exige ID de 24 hex e shortlink compatível com registro local.
4. **Reconciliador por campo.** `compare_card` classifica `equal/pull/push/conflict/defer` contra uma baseline comum. Sem baseline, diferenças ficam em conflito; os dois valores são preservados. Reviews idempotentes são persistidos em `trello_sync_reviews` na base **existente** `local-edits.sqlite`, nunca no snapshot original. Apenas evidências `native_observed=True` formam baselines confiáveis.
5. **Trello → Hermes com CAS.** `workstation_db_trello_pull` só aplica o `name` de uma revisão nativa qualificada ao overlay versionado de `dataset_edits.py`, com `expected_revision`. Antes de gravar, relê o BrowserTask e rejeita mudança de URL, título, lista ou conclusão. Nunca escreve no Trello, nunca substitui `trello.sqlite`, nunca repete efeito incerto. Testes de revisão obsoleta, segunda alteração inesperada, lista final e título divergente passaram.
6. **Fluxo conectado de verdade, sem fonte simulada:** no Python `.venv`, `model_tools.handle_function_call('workstation_db_trello_plan', ...)` leu a BrowserTask real do cartão #944 e registrou `equal` em uma **base QA temporária**. O texto remoto não foi aceito do argumento do agente. Essa prova não equivale à execução de uma nova conversa do agente LLM no Desktop e não houve escrita em dados reais.

## Verificações finais

- Suíte Python focal: **63 passed**, **1 warning** preexistente de Starlette/HTTPX; `py_compile` das implementações passou.
- Antes desta correção: ESLint dos arquivos Database UI sem erros; não foram alterados nesta rodada.
- `model_tools.get_tool_definitions` retorna seis ferramentas Database: `catalog`, `query`, `save`, `update`, `trello_plan`, `trello_pull`.
- Verificação read-only em produção: `tarefas.sqlite` **281 tarefas**, `trello.sqlite` **395 cartões**, ambos `PRAGMA quick_check = ok`; `local-edits.sqlite` com **0 edits**, `quick_check = ok` e `journal_mode = wal`. **Tabela `trello_sync_reviews` não criada no banco real**; todas as escritas de QA permaneceram em diretórios temporários removidos após os testes.
- `main@f1d5ab2f03`, staging vazio, sem commit, PR, reset, stash ou reinício. Alterações anteriores no checkout compartilhado foram preservadas.

## Não concluído / riscos

- **Hermes → Trello:** não existe executor autorizado de `push` com intenção durável, recibos do Browser, readback confirmatório e tratamento explícito de efeito incerto. A classe `push` é somente uma proposta, não uma operação executável.
- **Cobertura completa:** faltam novos cartões ainda ausentes do inventário, comentários, anexos, checklists, atividade, status/lista, prazos, etiquetas, arquivamento sincronizado e resolução visual de conflitos. Não reimportar os snapshots antigos sobre os **395 cartões** e **281 tarefas**.
- **Cron diário de sincronização:** não cadastrado. O scheduler existente usa `catch_up_missed=True` e seus testes de claim/catch-up passaram, mas isso **não valida** disparo real Browser → Trello → Database e confirmação do ciclo completo.
- **Segurança operacional:** há processos Hermes com SQLite 3.53.4 e 3.50.4; banco de edições ainda está em WAL. Não converter WAL, recarregar módulos ou reiniciar com processos/sessões em uso. A BrowserTask System 1 continua estacionada com histórico de verificação pendente; não liberar sua autoridade ou repetir efeitos incertos.
- **Persistência após restart completo:** não homologada, por preservação de sessões ativas. A revisão em UI Database havia passado em ciclo anterior ao reabrir a visualização.

## Próxima entrega mínima

1. Implementar **um** `push` de título a partir de edição local com baseline nativa e `expected_revision`, intenção durável **antes** da ação, ação Browser nativa com recibo, comparação pós-efeito e estado `UNCERTAIN` sem auto-retry. Homologar em cartão QA isolado, sem modificar cartões institucionais produtivos.
2. Depois de comprovar os dois sentidos em Browser real e a recuperação de conflitos, ampliar ao inventário aberto (inclusive novos cartões) e registrar evidências de campos/coleções efetivamente visíveis, preservando originais.
3. **Só após o E2E real** configurar **um** cron diário no scheduler existente, com catch-up e checkpoint. Reprovar execução com Browser bloqueado, login ausente, SQLite não qualificado ou verificação inconclusiva, em vez de registrar sucesso artificial.

**Conclusão:** leitura nativa, planejar diferenças e aplicar título Trello → Database estão implementados com provas reais do Browser e testes de escrita isolada; sincronização bidirecional completa e cron operacional **ainda não estão prontos**.

## Adendo operacional — QA de push Hermes → Trello, 07/11/2026

Ler o novo relatório detalhado em `workstation/context/RELATORIO_PUSH_TRELLO_QA_20261107.md`. Quadro `Hermes Sync QA` privado criado via conexão Trello somente para preparar os testes; mutações de título executadas pelo Browser nativo. QA1: título realmente persistido, mas BrowserOwner retornou recibo incompleto, intenção permanece `uncertain`, sem retry. QA2: passo único com recibo verificado, porém título NÃO persistiu após recarga, intenção `uncertain`, sem retry. QA3: cartão criado e inspecionado; preparação local expirou antes de executar, nenhum push QA3. Código atualizado em `workstation/trello_sync_push.py` para dois passos nativos separados (type, depois Enter) com estado `typed` durável, recibos e recarga; **a versão nova ainda não foi homologada externamente** porque AI Control ficou indisponível. 86 testes Python PASS, 1 warning conhecido; cópias institucionais preservadas (281 tarefas, 395 cartões). Nenhum Cron criado, nenhum commit/PR/restart.


## 2026-11-08 - TR_ROUTE_QA3_20261108: later verified state

Older QA3 pending statement is superseded: QA3 native push VERIFIED in private board with two receipts, reload and independent Trello read. Routing admin to API, normal member to Browser is implemented READ ONLY; local API credentials not configured, so no local API write qualification. Original 281 tasks/395 cards intact, 103 tests PASS, no Cron. Current report: RELATORIO_TRELLO_HIBRIDO_20261108.md.

# Trello — coleta incremental factual (P02, 2026-10-27)

**Estado:** integrado no código local; validação com transportes sintéticos e SQLite temporário. **Trello API LIVE: NOT TESTED. RELEASE: HOLD.** O waiver H-079 autorizado pelo mantenedor para desenvolvimento local não qualifica publicação. Não há scheduler, Bot, LLM ou mutação externa nesta entrega.

## Autoridade e componentes
- `workstation/prefabs/trello.py::TrelloClient.board_actions(board, before=None, since=None, limit=100)`: faz exclusivamente GET `/1/boards/{boardId}/actions`, campos `id,type,date,data,idMemberCreator`; cliente já possui credenciais vinculadas a `agent.secret_scope`, e testes usam `Credential(fake)` / transport fake.
- `workstation/trello_action_journal.py`: `install_schema(conn)`, `normalize_action`, `append_batch`, `load_checkpoint`, `read_events`, `read_events_for_day`, `poll_board_actions`, `poll_board_actions_into_kanban`. `WorkstationKanbanBridge(board=kanban_board).get_connection()` delega ao `hermes_cli.kanban_db_connect.connect()`, dono SQLite já existente. Não cria banco novo; sem alterações a tabelas tasks/cards.
- Captura determinística: consulta antes/depois dos limites, ordenação newest-first, deduplicação por `(board_id,action_id)`, normalização de timestamp em UTC e allowlist de identificadores. Não salva comentários, descrições, títulos de cartões nem resposta HTTP bruta. `source='trello_rest_board_actions_v1'` identifica procedência.

## Janela e checkpoint
- API documentada do Trello: máximo geral 1000 ações por requisição; esta integração limita cada GET a 100 ações por padrão e no máximo 20 páginas por polling. `before` recebe ID da última ação da página anterior; `since` recebe checkpoint persistido. Página intermediária inválida, HTTP 429 não recuperado ou limite de janelas -> falha SEM gravar eventos/checkpoint daquela coleta.
- `TrelloRateLimitError` representa HTTP 429 sem imprimir URL/token. Retry somente de GET, até 3 tentativas, backoff limitado.
- `append_batch` usa `BEGIN IMMEDIATE`, inserção idempotente e checkpoint na mesma transação; em falha faz `rollback`. `ON CONFLICT ... WHERE excluded.cursor > ...` impede regressão de checkpoint se coletores defasados competirem.
- **Limitação de bootstrap:** quadros com mais ações históricas que a janela de coleta resultam em erro de janela completa; nenhuma perda silenciosa e nenhum checkpoint falso. O operador deve planejar backfill antes de declarar sincronização histórica total, ou implementar um bootstrap desde marco inicial autorizado. Nenhum agendamento automático foi criado.

## Instalação/reversão da migração
`install_schema(conn)` executa `CREATE TABLE/INDEX IF NOT EXISTS` somente na conexão passada pelo owner, sem modificar schema de tasks. Tabelas: `trello_activity_event` e `trello_activity_checkpoint`; índice `ix_trello_activity_time`. O adaptador canônico chama migration ao ser invocado, **não na inicialização global do Hermes**.

Desinstalação manual reversível (somente com permissão e após revisar dependências; apaga exclusivamente o histórico local coletado):
```sql
DROP INDEX IF EXISTS ix_trello_activity_time;
DROP TABLE IF EXISTS trello_activity_event;
DROP TABLE IF EXISTS trello_activity_checkpoint;
```

Nenhum `DROP` foi executado sobre bancos de produção. Testes de reversão foram feitos apenas em SQLite temporário, com tabela `tasks` sentinela preservada.

## Consultas e privacidade
`read_events(conn, board_id, limit=100)` retorna apenas metadados, sempre com `board_id`. `read_events_for_day(conn, board_id, 'YYYY-MM-DD', limit=100)` usa limites de dia UTC [00:00, 00:00 seguinte), inclusive ação exata de meia-noite. Campos: origem Trello, ID de ação, tipo, timestamp UTC, ator, ID de cartão, lista anterior e nova. Sem comentários brutos, tokens, `desc`, nomes ou outros textos de usuário.

## Qualificação
- Testes RED explícitos: função/módulo ausentes, checkpoint concorrente regressivo, board_id ausente da projeção, data inválida, ID aninhado com conteúdo sensível, borda meia-noite.
- GREEN local: `python -m pytest -q workstation/tests/test_trello_action_journal.py workstation/tests/test_trello_board_actions.py` e testes de regressão do Trello/CAS (resultados no handoff da sessão).
- Suite `workstation/tests/opc03_trello_read/test_trello_read_red.py` possui cinco `pytest.fail` intencionais em integração Browser/LLM fora do escopo P02. Não corrigir, marcar como histórico/RED separado.
- Sem acesso à API Trello real nem permissões para sincronização da conta; parâmetros e limites de endpoint verificados na documentação oficial Trello, e mocks foram usados em execução.

## Fonte pública de contrato
- https://developer.atlassian.com/cloud/trello/rest/api-group-boards/
- https://developer.atlassian.com/cloud/trello/guides/rest-api/api-introduction/
- https://developer.atlassian.com/cloud/trello/guides/rest-api/status-codes/

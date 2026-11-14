# Prompt 02 — Handoff documental e qualificação (2026-10-27)

**STATUS:** LOCAL_IMPLEMENTED / SYNTHETIC_GREEN / EXTERNAL_API_NOT_TESTED / RELEASE_HOLD.
**Responsável pelo patch local:** `chatgpt-trello-incremental-p02` (claim `trello-incremental-p02`).
**Owner Git/commit:** não designado; nenhuma operação mutável Git autorizada/executada.
**Owner documental oficial:** claim `chatgpt-whatsapp-m3` ACTIVE mantém `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`, `workstation/context/engineering-journal/CURRENT.md`, `workstation/context/CURRENT_STATE.md`, `workstation/context/KNOWN_ISSUES.md`. Não sobrescrever; owner incorporar inserts abaixo.

## Inserts recomendados para documentação canônica

### Roadmap
`HW-IMP-02 LOCAL_IMPLEMENTED / API_LIVE_NOT_TESTED / RELEASE_HOLD`. Coleta paginada `TrelloClient.board_actions` com GET oficial, retry 429, journal SQLite canônico, idempotência por `(board_id, action_id)`, checkpoint monotônico commitado somente após janela completa, metadata-only por quadro/dia. Sem novo Kanban, DB concorrente, LLM, scheduler ou mutação Trello. P03 Bot de relatório depende de autorização explícita sobre consumo, não faz parte desta entrega.

### Intelligence
Trechos de fatos normalizados da API oficial (source `trello_rest_board_actions_v1`) alimentam histórico determinístico: ação, tipo, timestamp UTC, ator, IDs de cartão/listas. Não são prova independente de intenção humana nem autorização de ação; reportar somente metadados conforme política, comentários e descrições não persistem no journal. Source `workstation/context/TRELLO_INCREMENTAL_ACTIONS_20261027.md`.

### Engineering Journal / Current State
Git inicial: main / f1d5ab2f030e940ed4571371b0de45a21a009c9e; preflight Trello.py e kanban.py sem dirty registrado, docs oficiais sujos e claimed. Claim P02 apenas trello.py / journal / 2 suites novas; doc novo próprio e handoff. H-079 waiver histórico do mantenedor aplicado somente ao trabalho local, sem qualificar release. RED inicial import/módulo ausente; RED adicionais: regressão de checkpoint por stale writer, board_id ausente, hora inválida, PII aninhada em IDs, consulta meia-noite UTC. GREEN: `python -m pytest -q workstation/tests/test_trello_action_journal.py workstation/tests/test_trello_board_actions.py workstation/tests/test_trello_concurrent_edit_protection.py workstation/tests/opc03_trello_read/test_trello_read_red.py -k 'not TestTrelloReadIntegrationRED'` => 42 passed, 7 skipped (credenciais live ausentes), 5 deselected, exit 0. `python -m compileall -q ...` exit 0; `git diff --check -- P02 files` exit 0. Com suíte `opc03_trello_read` integral: 5 falhas explícitas `pytest.fail` históricas não ligadas à coleta; não mudar as suites. Ruff via Python 3.13: indisponível (No module named ruff), não alegar lint GREEN. Trello real: NOT TESTED; nenhum contato ou cartão alterado.

### Known Issues / risco residual
`HW-TRELLO-ACTIONS-01`: bootstrap histórico maior que 20 páginas x 100 ações não avança checkpoint, falha fechada; requer estratégia de backfill autorizada ou período inicial definido antes de reivindicar histórico total. Paginação entre mudanças concorrentes no Trello pode produzir janelas divergentes, mas nunca força checkpoint após consulta intermediária falha; confirmar comportamento live. `TrelloClient.from_secret_scope()` mantém fallback legado para env em contexto sem scope, contrato não alterado neste P02; revisar multiplex em missão de credenciais, não reivindicar correção. O endpoint real GET /1/boards/{boardId}/actions foi verificado nos docs oficiais mas não testado com conta. Sem atualização em WA-M3-01, HLM M3 ou H-079 release.

## Contrato de banco e migração
Conexão canônica: `WorkstationKanbanBridge(board=...).get_connection()` delega `hermes_cli.kanban_db_connect.connect(board=...)`. `poll_board_actions_into_kanban` aceita essa conexão, instala `trello_activity_event` e `trello_activity_checkpoint` por CREATE IF NOT EXISTS e índice `ix_trello_activity_time`. Não existe arquivo DB adicional em produção. Testes usam SQLite in-memory e fixture temp. Migração reversível manual (somente por owner autorizado após revisar dependências): `DROP INDEX IF EXISTS ix_trello_activity_time; DROP TABLE IF EXISTS trello_activity_event; DROP TABLE IF EXISTS trello_activity_checkpoint;`. Não foi executada em dados reais.

## Trechos exatos alterados
- `workstation/prefabs/trello.py`: `TrelloRateLimitError`, mapeamento de HTTPError 429 em `_request`, `TrelloClient.board_actions` (único método novo do cliente).
- `workstation/trello_action_journal.py`: módulo integrado derivado de referência, schema, normalizer allowlisted, atomic journal e cursores, polling e consulta diária.
- `workstation/tests/test_trello_board_actions.py`, `workstation/tests/test_trello_action_journal.py`: novos RED/GREEN e migração/restart/recovery/privacy.
- `workstation/context/TRELLO_INCREMENTAL_ACTIONS_20261027.md`: documentação operacional fora dos caminhos claimed.

## Próximo passo não destrutivo
1. Owner documental incorporar somente os inserts descritos, mantendo conteúdo WIP alheio.
2. Integrador Git autorizado rever diff e claims; sem branch/switch/reset/stash automático.
3. Aprovar uma leitura Trello live específica (somente GET) e credenciais do profile correto; provar page 1/2 + 429 sem dados brutos expostos; observar rate-limits e cursor de borda.
4. Definir bootstrap de histórico em quadros com mais que a janela de polling antes de chamar sincronização produtiva, e executar CI de release separadamente.

**Proibição permanente:** não chamar DONE/RELEASE por 42 testes de transporte fake; não publicar títulos, `desc`, comentários nem token. Não enviar mensagens de WhatsApp.

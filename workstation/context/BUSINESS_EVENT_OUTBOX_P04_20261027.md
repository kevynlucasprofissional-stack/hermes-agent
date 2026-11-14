# P04 — Evento de negócio confiável → outbox → Cron do Hermes (2026-10-27)

**Estado:** `LOCAL_IMPLEMENTED / 105_REGRESSION_PASS / SYNTHETIC_E2E_PASS / LIVE_DISPATCH_NOT_TESTED / RELEASE_HOLD`.

## Autoridade e integração

Os módulos `workstation/business_event_outbox.py` e `workstation/business_event_dispatch.py` usam **a conexão SQLite canônica que o chamador autorizado fornece**. `with_kanban_connection(callback, kanban_board=...)` resolve por `WorkstationKanbanBridge(...).get_connection()`, sem criar novo arquivo de produção, task table, Kanban ou scheduler. Não altera `workstation/events.py::SystemEventPipeline`, `tools/cronjob_tools.py`, `cron/scheduler.py`, `cron/executions.py`, P02 ou P03. `recover_interrupted_executions()` no Cron marca a tentativa upstream como desconhecida, mas não é fonte de prova de entrega da outbox.

**P02 ownership:** `chatgpt-trello-incremental-p02` detém journal/Trello. O adaptador **somente lê** `trello_activity_event`; nunca altera os arquivos/claims P02, não invoca API Trello e não torna evento do `SystemEventPipeline` em intenção de tarefa. O owner de esquema da base continua sendo o Kanban bridge; instalar tabelas requer uma conexão que o owner autorizou explicitamente. Tabelas P04 foram instaladas somente em SQLite de teste, nunca no banco do usuário.

## Envelope, filtro e fonte

`BusinessEventEnvelope(source,event_id,event_type,object_id,observed_at,payload_ref)`. Identidade estável Trello: `source='trello'`, `event_id=f'{board_id}:{action_id}'`, `object_id` = ID do cartão **confirmado** no journal, `payload_ref=f'trello_activity_event:{board_id}:{action_id}'`. A ação do P02 fornece tipo e hora UTC; o adapter verifica que `evidence_json` concorda com a row. Se há ID de cartão ausente, divergência, ação/board/route desautorizada, falha fechada. Não persiste títulos, `desc`, comentários, URLs com token, segredos ou origem arbitrária.

`AuthorizedBusinessRoute` obriga a escolher `route_id`, `board_id`, tipos autorizados e `job_id` existente; v1 admite apenas fonte `trello` e `delivery='local'`. `load_authorized_routes(profile_home)` lê **somente** `config.yaml` confiável do perfil escolhido (`business_events.routes`); eventos não podem criar regras nem jobs. Rotas desabilitadas não são carregadas. Exemplo **NÃO instalado**:
```yaml
business_events:
  routes:
    - id: trello-daily-v1
      enabled: false
      source: trello
      board_id: "BOARD_OFICIAL"
      event_types: [updateCard]
      job_id: "JOB_CRON_EXISTENTE"
      delivery: local
```
Ativar/autorizar regra e assegurar perfil correto é ato explícito do owner. Não carregar `job_id` de um campo Trello. Na execução, o Cron deve estar habilitado e confinado a `deliver=local`, caso contrário o evento termina `FAILED_SAFE` **sem chamar** o executor. O job P03 `af77883863f8` continua PAUSADO; teste in-memory com o **job real** devolveu `FAILED_SAFE` e zero execução.

## Tabelas e máquina de estados

`install_outbox_schema(conn)` instala aditivamente `business_event_outbox` e `business_event_decision` (log auditável), índices `ix_business_event_outbox_pending`, `ix_business_event_outbox_route`, `ix_business_event_decision`; aceita schema reduzido do reference P04 via `ALTER TABLE` com defaults e não altera tarefas. Chave `PRIMARY KEY(source,event_id,route_id)`, payload e `job_id` imutáveis em duplicata; substituição conflitante rejeitada.

Estados: `PENDING` (evento confirmado no journal, ainda não reservado), `CLAIMED` (exclusive `BEGIN IMMEDIATE`, token e lease, *não é efeito entregue*), `FAILED_SAFE` (pré-dispatch não autorizado/job ausente/pausado — executor **não foi chamado**), `UNCERTAIN` (Cron pode ter começado; **não há replay automático**) e `DELIVERED` (somente mediante comprovante independente correlacionado ao evento + verificador explícito). `attempt_count`, `claimed_at`, `lease_until`, timestamps e decisões são gravados em transação. A aquisição `claim_next` jamais gera novo ID de evento; UUID serve apenas ao token efêmero de claim.

`dispatch_pending` é uma **chamada explícita única**, sem daemon, fila separada nem timer; resolve rota confiável, valida job existente/habilitado, executa o `execute_job_for_event(job_id,extra_prompt=...)` do Cron legado apenas com metadados allowlisted. Depois da chamada, **até quando o Cron retorna `claimed=True,success=True`, o estado é `UNCERTAIN`**, pois o retorno não possui prova de entrega vinculada ao `event_id`. Erro/timeout depois da chamada também é `UNCERTAIN`. Expiração de lease faz `CLAIMED -> UNCERTAIN`, nunca `CLAIMED -> PENDING`. `reconcile_uncertain` admite transição terminal mediante verificação independente fornecida pelo owner; **não reenvia**. O verificador é ponto de autoridade externo ainda não conectado a receipts Cron específicos: não declarar `DELIVERED` em produção.

O adapter não faz recuperação/autorretry após evento incerto. Alterar `route_id` para rearmar um evento equivale a nova autorização/rota e deve exigir revisão humana, já que a chave de deduplicação inclui rota.

## Reversão e riscos

Reversão manual por owner (destrutiva **somente para tabelas da outbox**, após revisão de dependências; **nunca executada na DB real**):
```sql
DROP INDEX IF EXISTS ix_business_event_outbox_pending;
DROP INDEX IF EXISTS ix_business_event_outbox_route;
DROP INDEX IF EXISTS ix_business_event_decision;
DROP TABLE IF EXISTS business_event_decision;
DROP TABLE IF EXISTS business_event_outbox;
```

Riscos residuais: `execute_job_for_event` não tem idempotency key por evento; o fence é **apenas deste adaptador**, chamadas diretas ao Cron contornam a outbox. Dois route IDs podem disparar o mesmo job intencionalmente, cada rota com sua deduplicação própria. Evidência de Cron output em `local` não significa efeito entregue no Bot Chat. `UNCERTAIN` requer reconciliação independente e nunca pode ser convertida em PENDING automaticamente. Alteração não autorizada do `config.yaml` por outro processo não é impedida pela outbox. Perfil usado por Cron e perfil da DB devem ser qualificados como a mesma autoridade: não assumir que Bot `trello-relator` já tem acesso à DB P02.

## Evidência TDD e testes

- RED: `python -m pytest -q workstation/tests/test_business_event_dispatch.py` → `ModuleNotFoundError: workstation.business_event_outbox`, **exit 2**, antes do patch.
- GREEN inicial: 14 testes, um erro de expectativa do teste (tentativa de `DELIVERED` sem receipt foi corretamente rejeitada, política mais forte; teste corrigido). `python -m pytest -q workstation/tests/test_business_event_outbox.py workstation/tests/test_business_event_dispatch.py` → **29 PASS, exit 0** (inclui 2 workers e disparo simulado único).
- Matriz focada integrada `python -m pytest -q workstation/tests/test_business_event_outbox.py workstation/tests/test_business_event_dispatch.py workstation/tests/test_trello_action_journal.py workstation/tests/test_trello_board_actions.py workstation/tests/test_trello_daily_brief.py workstation/tests/test_trello_daily_brief_cron.py workstation/tests/test_trello_concurrent_edit_protection.py workstation/tests/test_events_pipeline.py tests/cron/test_atomic_paused_creation.py tests/cron/test_cron_context_from.py` → **105 PASS, exit 0**.
- `python -m compileall -q` dos quatro arquivos P04: **exit 0**. `git diff --check --` no código tracked: **exit 0**, mas arquivos P04 são UNTRACKED e esse comando não os valida; conferir por inspeção própria. `python -m ruff`: indisponível (`No module named ruff`, exit 1), portanto **lint NOT TESTED**.
- Perfil Bot P03 real `trello-relator` com Cron `af77883863f8` PAUSADO usado somente para consultar o registro de job, com outbox `:memory:`; `FAILED_SAFE`, **0 chamadas ao Cron**, exit 0. Outros testes usando `cron.jobs.create_job` usam perfil temporário e executor FAKE, não ação externa.
- Nenhum Trello API LIVE/LLM/Bot Chat/executor Cron real foi disparado. Nenhuma mutação externa, WhatsApp, criação de cartões ou alteração de configuração de perfil.

## Próximos gates

1. Owner Kanban/P02 autoriza instalação aditiva das tabelas no DB canônico real e confirma política de leitura do journal/perfil.
2. Owner define/ativa `business_events.routes` em `config.yaml` de perfil específico. Sem isso, **nenhuma fonte real** tem autorização de disparo.
3. Validar Cron real com idempotency/correlation receipt independente antes de alegar `DELIVERED`; enquanto não houver, manter `UNCERTAIN` como estado terminal operacional.
4. Testar E2E aplicativo completo, provider/CI e upstream gates próprios; não qualificar release por transporte sintético.
5. Registrar documentos oficiais pelo **owner documental WhatsApp M3**; handoff isolado `HANDOFF_PROMPT_04_20261027.md`.

## Refor?o P04 final: isolamento de rotas (RED ? GREEN)
Um dispatcher com `routes={}` n?o reivindica nem reconcilia eventos; com rotas autorizadas somente consome eventos de `route_id` expl?citos, n?o altera CLAIMED de outra rota e n?o transforma regra ausente em FAILSAFE para evento de outro propriet?rio. Reproduzido por teste RED (1 FAIL), corrigido e revalidado; matriz final P04 29/29 e integrada 105/105 PASS, exit 0.

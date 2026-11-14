# P04 — Handoff de documentação canônica e integração (2026-10-27)

**Resultado factual:** `LOCAL_IMPLEMENTED / P04=29_PASS / P02+P03+P04+EVENTS+CRON=103_PASS / REAL_CRON_DISPATCH_NOT_TESTED / RELEASE_HOLD`. Documentação detalhada em `workstation/context/BUSINESS_EVENT_OUTBOX_P04_20261027.md`.

## Propriedade e Git
- Checkout inicial: `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`; arquivos de produto P04 ausentes inicialmente, docs oficiais já modificados/claimed.
- Agente/claim: `chatgpt-business-outbox-p04`, lane `p04-business-outbox`; paths reservados: `workstation/business_event_outbox.py`, `workstation/business_event_dispatch.py`, `workstation/tests/test_business_event_outbox.py`, `workstation/tests/test_business_event_dispatch.py`, `workstation/context/BUSINESS_EVENT_OUTBOX_P04_20261027.md`, este handoff.
- P02 journal continua propriedade de `chatgpt-trello-incremental-p02`; arquivos do Cron/event pipeline não foram editados. Owner canônico documental `chatgpt-whatsapp-m3` reivindica `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`, `workstation/context/engineering-journal/CURRENT.md`, `KNOWN_ISSUES.md`; **integrar apenas pelo owner documental**. Integrador de commit NÃO designado. Não executar reset/stash/checkout, nem abrir branch/worktree, nem commit/push.

## Inserts para ROADMAP.md
`HW-IMP-04 LOCAL_IMPLEMENTED / 105 REGRESSION PASS / OUTBOX_SQLITE_SYNTHETIC_GREEN / LIVE_EXECUTION_HOLD.` Criados adaptadores P04 para converter somente ações existentes no journal do Trello em `BusinessEventEnvelope` imutável, passar por filtro de rota confiável e consultar um job Cron já existente. Registro/outbox no DB canônico delegado pelo Kanban (sem DB concorrente), chave `(source,event_id,route_id)`, aquisição `BEGIN IMMEDIATE`, token/lease, journal de transições e nenhuma repetição após `UNCERTAIN`. Bot P03 real `af77883863f8` permanece PAUSADO; teste de gate real resultou `FAILED_SAFE` (0 execuções). Não há novo scheduler, envio WA, criação automática de cartões/tarefas nem autorização de sistema decorrente de evento não correlacionado.

## Inserts para HERMES_WORKSTATION_INTELLIGENCE.md
`SystemEventPipeline` permanece observacional, não promove eventos externos à autoridade TaskRun. P04 só aceita eventos Trello já normalizados e existentes em `trello_activity_event` do P02, com `source=trello`, event_id `board_id:action_id`, tipo/horário e `card_id` atestados pelo journal. Regra de disparo é confiável e prévia via config.yaml do perfil (`business_events.routes`, `enabled=true`, board/tipo/job/delivery locais); nunca deriva de texto de ação. `CLAIMED` indica reserva; `UNCERTAIN` é desfecho após chamada Cron e não pode ser tratado como `DELIVERED` só por `claimed=true`/`success=true`. Corrigir para `DELIVERED` demanda evidência externa independently verified e por evento.

## Inserts para engineering-journal/CURRENT.md
Prompt 04 (2026-10-27) em branch `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`: RED inicial `python -m pytest -q workstation/tests/test_business_event_dispatch.py` => `ModuleNotFoundError` exit 2. GREEN P04 `python -m pytest -q workstation/tests/test_business_event_outbox.py workstation/tests/test_business_event_dispatch.py` => **29 PASS, exit 0**. Matriz P02/P03/P04/events/Cron focada => **105 PASS, exit 0**. `compileall` código/testes P04 exit 0, `git diff --check` tracked exit 0 (não verifica arquivos novos), `ruff` ausente exit 1 NOT QUALIFIED. Testes reais Cron com job pausado `af77883863f8` e outbox :memory: => `FAILED_SAFE`/zero chamada, exit 0. Mock do executor Cron e registro real de jobs em perfil isolado: 1 invocação para 2 workers concorrentes; sem chamada LLM/WhatsApp/Trello API. Nenhuma migration executada em DB real. Aprovação do H-079 anterior não configura release gate.

## Inserts para KNOWN_ISSUES.md
`HW-P04-OUTBOX-01`: idempotência end-to-end só existe dentro do adaptador/outbox para uma rota específica. `execute_job_for_event` não recebe idempotency key por evento; qualquer Cron fora deste adaptador pode correr em paralelo. O estado `UNCERTAIN` é HOLD deliberado sem retry, e não prova falha nem sucesso. Interface de reconciliação exige `independent_verifier` injetado; não foi conectado a receipt independente do Cron. Não ativar jobs reais nem entregar em Bot Chat/WhatsApp até receber prova de autoridade e E2E. Owner DB deve confirmar instalação da migration em perfil correto. Persistem pendências anteriores P02 (Trello API live/backfill), P03 (modelo/provider Bot, entrega Bot Chat) e WA-M3 hold.

## Diferenças por arquivo
- `business_event_outbox.py` (novo): envelope, schema + migração aditiva de schema de referência, audit ledger, enqueue dedupe/collision, claim exclusivo, lease expire-to-UNCERTAIN, settlement com fence, reconciliação explícita e query metadata.
- `business_event_dispatch.py` (novo): configuração de rotas do profile confiável, adaptação P02 journal, validação de job existente, invocação `tools.cronjob_tools.execute_job_for_event` somente após claim; preflight termina FAILED_SAFE, postdispatch UNKNOWN termina UNCERTAIN; entrypoint canônico.
- `test_business_event_outbox.py` (novo): persistência após reinício, migrations idempotentes, configuração de rota, proof gate, audit, profile/DB.
- `test_business_event_dispatch.py` (novo): TDD/2 workers e concorrência, duplicate/replay, crash após claim, job missing/paused, rate of call, fake Cron registry existente, Trello journal, privacidade, rollback.
- `BUSINESS_EVENT_OUTBOX_P04_20261027.md` (novo): contrato/migration/limites, evidências e rollback.
- `HANDOFF_PROMPT_04_20261027.md` (novo): inserts para owner documental.
- Arquivos upstream P02/P03, Cron, events, docs oficiais permaneceram **inalterados por P04**.

## Rollback controlado
Somente por autorização do owner DB: `DROP INDEX IF EXISTS ix_business_event_outbox_pending; DROP INDEX IF EXISTS ix_business_event_outbox_route; DROP INDEX IF EXISTS ix_business_event_decision; DROP TABLE IF EXISTS business_event_decision; DROP TABLE IF EXISTS business_event_outbox;`. Destrói histórico P04 local, não altera tasks/kanban, e **não foi executado** em DB real. Para revogar rota em produção: `enabled: false` na config confiável e garantir dispatcher não ativo; não remapear evento antigo para nova rota sem decisão formal.

**Sem chamada real ao Cron executor, sem promoção release.** Owner documental pode incorporar inserts após reconciliar seu próprio WIP. A validação live de Trello/LLM/CI continua separada dos gates P04 sintéticos.

## Refor?o P04 final: isolamento de rotas (RED ? GREEN)
Um dispatcher com `routes={}` n?o reivindica nem reconcilia eventos; com rotas autorizadas somente consome eventos de `route_id` expl?citos, n?o altera CLAIMED de outra rota e n?o transforma regra ausente em FAILSAFE para evento de outro propriet?rio. Reproduzido por teste RED (1 FAIL), corrigido e revalidado; matriz final P04 29/29 e integrada 105/105 PASS, exit 0.

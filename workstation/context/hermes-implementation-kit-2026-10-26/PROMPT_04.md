# PROMPT 04 — Acionar jobs existentes por evento de negócio com outbox idempotente

**Missão.** Conectar eventos confiáveis (inicialmente Trello) aos Bots/Cron do Hermes. **Não** criar um segundo scheduler ou concluir automaticamente tarefas a partir de um evento não correlacionado.

**Preflight.** Ler `workstation/events.py::SystemEventPipeline`, `tools/cronjob_tools.py::execute_job_for_event`, `cron/executions.py::recover_interrupted_executions`, `tests/gateway/test_webhook_cron_trigger.py` e testes de eventos. Obter claims para novo adaptador e banco autorizado; coordenar com owner Trello do prompt 02 para contrato de evento, sem editar as mesmas fontes simultaneamente.

**Onde e como.** Usar `reference-code/business_event_outbox.py` + `reference-tests/test_business_event_outbox.py` como base isolada (4/4 testes em sandbox), após revisar migration/claims. Criar `workstation/business_event_dispatch.py` como adaptador fino, não alterar `SystemEventPipeline` para atribuir autoridade a eventos sem TaskRun. Definir `BusinessEventEnvelope(source,event_id,event_type,object_id,observed_at,payload_ref)` — ID estável vem da origem, não de UUID aleatório. Persistir `event_delivery`/outbox numa tabela de controle do mesmo banco autorizado: `UNIQUE(source,event_id,route_id)` com estados `PENDING`, `CLAIMED`, `DELIVERED`, `UNCERTAIN`, `FAILED_SAFE`, timestamp e número de tentativa. Roteador resolve regra **previamente autorizada** para job existente, depois chama `execute_job_for_event(job_ref, extra_prompt=...)`. Não transformar `claimed=true` em prova de que um efeito externo foi entregue; estado depende de confirmação independente.

**Plano mínimo:** (1) RED: dois eventos idênticos, 2 workers concorrentes, crash após claim, job inexistente, fonte não autorizada e ação parcialmente concluída; (2) migration + reserva transacional do outbox; (3) publisher com lease/claim e reconciliação antes de retry; (4) GREEN com fake job/Cron, provando que duplicate não dispara uma segunda execução; (5) um percurso Trello → journal → dispatch → Bot, read-only e verificável. Se o executor Cron não suportar idempotency key por evento, implemente fence/outbox neste adaptador e seja conservador após estado incerto.

**DONE.** Sem duplicação sob replay/restart, sem escalação de eventos não correlacionados, dados restritos a origem/regra, auditoria de todas as decisões e testes locais de concorrência. Não enviar WhatsApp nem modificar cartões externos. Documentar migrations, retry policy e significado preciso de `UNCERTAIN`.

---

## Formato de entrega obrigatório para CADA prompt

Entregar ao final: (a) HEAD/branch/dirty inicial e final; (b) caminhos sob claim do agente e integrador dono de commit; (c) contrato/decisões e desvios justificados; (d) diffs por arquivo; (e) evidência RED + GREEN com comandos e exits; (f) validação nativa onde exigida; (g) segurança e riscos residuais; (h) Known Issues que continuam abertos; (i) atualização incremental do `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` e `workstation/context/engineering-journal/CURRENT.md` somente pelo owner documental, ou handoff de inserts caso esses arquivos estejam claimed. Não chamar `DONE/RELEASE` para teste sintético ou código não integrado.

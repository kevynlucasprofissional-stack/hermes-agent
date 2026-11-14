# PROMPT 03 — Bot narrativo diário do Trello com evidências, sem envio externo automático

**Missão.** Produzir o primeiro resultado operacional: resumo diário legível das alterações Trello capturadas pelo prompt 02, com fontes e interpretação prudente; configurar Bot + Cron já existentes, sem novo framework de agentes ou provider.

**Preflight.** Confirmar que o journal do prompt 02 está GREEN e que o acesso à base foi delegado; ler `tools/cronjob_tools.py`, `cron/scheduler_delivery.py`, `cron/scheduler.py`, contratos Bots e `workstation/trello_action_journal.py`. Reservar somente novo módulo de resumo/testes/config e docs; não editar arquivos do Cron se simples configuração e job bastarem.

**Implementação.** (1) Criar `workstation/trello_daily_brief.py` (ou módulo de Bot estabelecido na arquitetura) com função pura `collect_brief_facts(conn,board_id,period_start,period_end)` retornando fatos ordenados, contagens e `action_id` fonte, limitados por janela e quantidade; (2) separar `render_brief_prompt(facts,instructions)` de execução LLM, encapsulando eventos como dados não confiáveis, não como instruções; (3) registrar um Bot de relato (prompt configurável) e um Cron que utiliza a configuração existente `cron.model`/`cron.model_provider` quando não há override por job; (4) entregar inicialmente no chat/inbox interno do Hermes, com dry-run. WhatsApp pessoal é entrega futura dependente de canal WA qualificado e autorização explícita; **não enviar agora**.

**Roteiro de testes.** Teste RED de janela UTC/locale, mais de um quadro, nenhum evento, duplicatas no journal, cartões renomeados/movidos, comentários sem acesso ao conteúdo e injeção de prompt nos dados; GREEN: texto não inventa nomes, motivos, conclusões nem prazos ausentes, inclui referência ao ID do evento e declara lacunas. Usar fake LLM para inspecionar prompt; teste de Cron/delivery em ambiente isolado, conforme `tests/gateway/test_webhook_cron_trigger.py` e suites locais, sem calls externas.

**DONE.** Um `cron_job` existente gera relatório baseado apenas em eventos de fixture e mantém a saída persistida e rastreável. Comandos, entradas de fixture, hashes/IDs, falhas, custos estimados e instrução do Bot registrados. A configuração é reversível; nenhum token de API entra em versionamento. Não inventar sucesso de envio para WhatsApp.

---

## Formato de entrega obrigatório para CADA prompt

Entregar ao final: (a) HEAD/branch/dirty inicial e final; (b) caminhos sob claim do agente e integrador dono de commit; (c) contrato/decisões e desvios justificados; (d) diffs por arquivo; (e) evidência RED + GREEN com comandos e exits; (f) validação nativa onde exigida; (g) segurança e riscos residuais; (h) Known Issues que continuam abertos; (i) atualização incremental do `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` e `workstation/context/engineering-journal/CURRENT.md` somente pelo owner documental, ou handoff de inserts caso esses arquivos estejam claimed. Não chamar `DONE/RELEASE` para teste sintético ou código não integrado.

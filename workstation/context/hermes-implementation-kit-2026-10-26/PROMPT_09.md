# PROMPT 09 — Extração de demandas WhatsApp → triagem Kanban, sem tarefa automática definitiva

**Missão.** Relacionar demandas explicitamente identificadas em mensagens autorizadas com a triagem canônica do Kanban, sem criar tarefas duplicadas ou inventar prazos/responsáveis.

**Preflight.** Depende do Prompt 08 e da existência de mensagens verificáveis; ler `workstation/kanban.py::WorkstationKanbanBridge`, `workstation/work_intent.py`, `workstation/task_compiler.py`, `workstation/events.py` e schemas WA. Confirmar fonte de verdade e claim das alterações; não utilizar o P0 MCP experimental como autorização do Hermes.

**Alterações.** (1) Definir contrato puro `DemandCandidate(source_message_id,contact_id,description,due?,assignee?,confidence,evidence_refs)`; (2) usar LLM apenas para `candidate` com evidência, proibir assumir que pedido a terceiro é necessariamente tarefa do usuário; (3) registrar `UNIQUE(source,message_id,candidate_kind)` e `review_required` para ambiguidade; (4) quando claramente autorizado, chamar API de triagem existente da Kanban sem forjar TaskRun/execução; (5) registrar mudanças de status e permitir revisão/descartar. Sem envio de resposta WhatsApp.

**Testes/aceite.** Corpus com exemplos positivos/negativos/ambíguos, reprocessamento, mensagens editadas, grupos, datas relativas incertas, múltiplos contatos homônimos. Nenhuma TaskRun aparece sem claim real, nenhum prazo é inventado, duplicatas permanecem uma só demanda. Reportar precisão/amostras e falhas.

---

## Formato de entrega obrigatório para CADA prompt

Entregar ao final: (a) HEAD/branch/dirty inicial e final; (b) caminhos sob claim do agente e integrador dono de commit; (c) contrato/decisões e desvios justificados; (d) diffs por arquivo; (e) evidência RED + GREEN com comandos e exits; (f) validação nativa onde exigida; (g) segurança e riscos residuais; (h) Known Issues que continuam abertos; (i) atualização incremental do `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` e `workstation/context/engineering-journal/CURRENT.md` somente pelo owner documental, ou handoff de inserts caso esses arquivos estejam claimed. Não chamar `DONE/RELEASE` para teste sintético ou código não integrado.

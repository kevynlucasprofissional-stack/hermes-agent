## 2026-10-26 — Proposta: Work como operador orientado a eventos, sem inteligência contínua de vigilância (DESIGN)

A capacidade-alvo é **observar → normalizar eventos → persistir evidência → aplicar regra determinística → chamar Bot somente quando indispensável → verificar efeito**. Não deve haver um LLM observando cada mutação DOM.

**Reutilização demonstrada em leitura:** `SystemEventPipeline` (`workstation/events.py`) fornece callbacks e ligação a `ExecutionJournal`, mas seus eventos recentes estão em memória de processo; `execute_job_for_event` (`tools/cronjob_tools.py`) já aciona um job Cron existente; TrelloClient oferece leitura de cartões/listas; Browser usa CDP e possui `MutationObserver` para cache/aprendizagem; WhatsApp tem tabelas factuais em SQLite e gates de envio. Nenhum desses achados prova a existência de um monitor persistente por aba, journal durável de ações Trello ou memória semântica por contato completa.

**Separar autoridades:** Trello/WhatsApp são fontes de eventos e seus estados externos; o Kanban canônico permanece autoridade local de tarefas Work; journal de eventos não é segundo Kanban; Bot não pode inventar tarefa/atividade; *CandidateLesson* de demonstração não é capacidade verificada. Novas tabelas precisam de migration na conexão canônica explicitamente escolhida; não impor uma escolha PostgreSQL/SQLite em desacordo com o owner.

**Eventos:** usar IDs estáveis de origem, timestamps e referências a objeto, dedup, checkpoint transacional e outbox idempotente para efeitos assíncronos. O payload de terceiros deve ser tratado como dados não confiáveis, limitado em tamanho e higienizado; nenhum segredo/telefone/corpo bruto desnecessário em logs ou prompts. O dispatcher não interpreta evento não correlacionado como ordem de criação de tarefa.

**Browser file upload:** classificar como mutação potencial, porque `setFileInputFiles` pode gerar evento `change` e efeito de rede no site; exigir admission/owner/escopo de arquivos e confirmação independente. Nunca declarar mensagem entregue apenas porque o arquivo foi selecionado.

**Execução incremental:** primeiro upload e Trello; em seguida evento→Bot, áudio local, monitor simples; só depois WhatsApp semântico/replay autonomizado, respeitando HOLD. A ordem muda apenas por claims ou prova de ROI, nunca por conveniência de contornar gates.

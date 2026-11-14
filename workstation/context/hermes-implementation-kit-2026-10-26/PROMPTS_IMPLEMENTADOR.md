# Prompts operacionais autossuficientes — Hermes Work

**Uso:** envie **um prompt por vez** à IA implementadora com acesso autorizado ao projeto Hermes. Não enviar a sequência inteira como única tarefa. O pacote de referência está em `PLANO_IMPLEMENTACAO.md`, `reference-code/trello_action_journal.py` e `updates/`.

**Nota de acesso:** o Windows - Agent 01 consultado nesta preparação só estava autorizado ao projeto P0 de isolamento MCP, não ao Hermes. Antes de qualquer escrita, o operador deve adicionar explicitamente o repositório correto à lista de projetos permitidos e o agente deve obter claim exclusivo pelos caminhos exatos. Não usar outro conector para contornar a limitação.

---

## PROMPT 01 — Concluir upload nativo do Browser, protegendo admissão e arquivos

**Missão e por quê.** Faça a correção funcional e de segurança da ferramenta `browser_file_upload` no Hermes Work, reaproveitando a implementação existente por CDP. A entrega é selecionar arquivos autorizados em formulários web sem Computer Use. Não desenvolva controlador de janela nativa nem Playwright externo. Não enviar mensagens nem postar conteúdos reais para testar.

**Preflight obrigatório.** No checkout autorizado `C:\Github\hermes-agent`, leia `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/AGENT_COLLABORATION_PROTOCOL.md`, `KNOWN_ISSUES.md` e os gates Browser. Execute apenas Git READ (`rev-parse`, `status`, `diff`) e status de claims; confirme branch e responsável por integração. **Não edite** paths sujos ou reservados por outro agente; obtenha claim para `apps/desktop/electron/workstation-browser-runtime.ts`, teste Electron dedicado e, se necessário, `tools/browser_workstation.py`. Sem permissão, escreva handoff exato em destino autorizado, não execute patch às escondidas.

**Código observado.** Em `apps/desktop/electron/workstation-browser-runtime.ts::executeControlRequest`, `mutating = new Set([...])` (~linha 2891) omite `browser_file_upload`. O switch `case 'browser_file_upload'` (~3406) usa `path.resolve`, `existsSync`, `document.querySelector` e `DOM.setFileInputFiles`, retorna `files_uploaded` com caminhos completos. Em `tools/browser_workstation.py`, `_WORKSTATION_SCHEMA_TOOLS` inclui a ferramenta e `_upload` encaminha para `_dispatch`. `whatsapp_send_attachment` usa esse callback; preservar API e contratos de sessão/TaskRun/owner.

**Mudanças exatas e proposta de código:**

1. **TDD RED** em `apps/desktop/electron/workstation-browser-runtime-upload.test.ts` (ou suite Electron nativa análoga): prove que `browser_file_upload` sem `assertAgentControl` válido/sem lease deve ser recusado ANTES de qualquer `DOM.setFileInputFiles`; quando houver mutação incerta, replay por mesma operation ID não deve fazer segunda seleção; retornos não devem expor caminho local absoluto. Use fixture offline `<input type=file>` e verifique `change` e arquivo entregue no elemento. NEGATIVOS: arquivo inexistente, diretório, symlink escapando raiz, caminho fora da allowlist, tamanho excedido, selector não aponta input, sessão incorreta, takeover humano e `input` dentro de iframe (erro explícito ou suporte restrito testado).
2. Acrescente `'browser_file_upload'` ao conjunto `mutating` somente após compreender todos os ramos de admission, registro de receipts e sua semântica de `operation_id`. A ferramenta deve receber os mesmos guards/fences das outras mutações, incluindo operação ambígua `UNCERTAIN` sem retry implícito. Atenção: setar arquivos pode disparar `change` e upload automático; seleção é efeito externo potencial, não uma leitura.
3. Extraia/adicione uma validação de lista de arquivos (somente arquivos regulares, `realpath`, limite configurável de tamanho, checagem dentro das raízes autorizadas com boundary de segmento; não `startsWith` ingênuo) antes de executar o CDP. Recusar diretórios e travessia por symlink, sem ler conteúdo desnecessário. **Não inventar pasta permitida**: localizar configuração de file access no Hermes e, se inexistente, exigir aprovação/escopo explícitos por TaskRun em vez de permitir todo disco.
4. Manter CDP `DOM.setFileInputFiles` como caminho padrão; `Runtime.evaluate(querySelector)` deve falhar fechado quando não for `HTMLInputElement[type=file]`, ambíguo ou indisponível. Iframe/shadow só com resolução de alvo segura, testes nativos e contexto CDP correto; não implementar fallback inseguro via `evaluate` arbitrário. Retorno mínimo com contagem, nome base (se política permitir), estado e receipt; sem caminho completo.
5. Manter `whatsapp_send_attachment` somente como **consumidor** do upload; não editar fluxo de envio WA-M3 em HOLD nem disparar mensagem real.

**Verificação e DONE.** Observar RED → GREEN. Executar Vitest Electron focado, suites de admission/recovery, typecheck em `apps/desktop` (`npm run typecheck` naquele diretório) e fixture real Electron/Chromium em origem de teste offline, coletando evidência de seleção/alteração, não de envio. Documentar `UNKNOWN` quando sem prova nativa; não marcar release se suites maiores estiverem vermelhas. Registrar caminhos/diff, comandos/exit codes, falhas, riscos e handoff no Jornal; atualizar roadmap/Intelligence/KNOWN_ISSUES somente sob claim documental do integrador. Se versão do código divergir, preservar os invariantes e justificar alternativa superior em relatório curto.

---

## PROMPT 02 — Implementar coleta incremental e histórico factual do Trello (read-only)

**Missão.** Converter o cliente Trello existente em fonte de mudanças **sem criar novo Kanban ou novo orquestrador**. Implementar leitura paginada das ações, persistência determinística de eventos e checkpoint, com zero mutações de cartões e nenhuma IA na captura.

**Preflight e ownership.** Ler `AGENTS.md`, `workstation/AGENTS.md`, colaboração e estado do checkout; reivindicar exclusivamente `workstation/prefabs/trello.py`, `workstation/trello_action_journal.py`, seus testes e migration do banco canônico escolhido. Não mudar branch/worktree nem mexer em WIP alheio. O runtime existente usa SQLite no `WorkstationKanbanBridge` (`workstation/kanban.py`), mas confirmar o DB com o owner canônico antes de instalar tabelas.

**Código observado e onde agir.** `workstation/prefabs/trello.py::TrelloClient._request(method,path,query,form)` já permite GET oficial; `board_lists`, `board_cards`, `card` validam IDs e retornos. Acrescentar **somente** `TrelloClient.board_actions(board, *, before=None, since=None, limit=100)` (parâmetros finais devem respeitar endpoint oficial efetivo) com validação, paginação e tratamento de rate limits, lendo `/1/boards/{id}/actions` ou endpoint compatível confirmado. Não registrar credenciais nem persistir `desc`/comentários brutos no journal base.

**Código preparado.** Use `reference-code/trello_action_journal.py` e `reference-tests/test_trello_action_journal.py` deste pacote como base avaliada. Fornece `install_schema(conn)`, `normalize_action`, `append_batch(conn,board_id,actions,completed_checkpoint=...)`, `load_checkpoint`, `read_events`, tabela `trello_activity_event` com PRIMARY KEY `(board_id,action_id)` e `trello_activity_checkpoint`. Está testado **isoladamente** (5/5). Integre-o ao módulo do projeto apenas após conferir migrations, transações e contrato do DB real. **Não criar novo arquivo .db com tarefas concorrentes.**

**Etapas.** (1) Testes RED via transporte `TrelloClient(credential=fake,transport=fake)` para paginação, 429, falha intermediária, ação repetida/fora de ordem, vazio, IDs inválidos, cursor, limite; (2) implementar GET e adaptador que lê até completar lote/intervalo, não avança cursor no fracasso; (3) adicionar journal sob migration compatível com versões antigas; (4) teste GREEN de reinicialização, duas consultas repetidas e recuperação sem duplicação; (5) fornecer interface de consulta por quadro/dia sem publicar dados brutos não autorizados.

**DONE.** `pytest` focado e regressão das suites Trello existentes executados, dados de fixture provam sem perdas/duplicados e rollbacks atômicos. O callback de leitura não modifica Trello. Todos os eventos incluem `board_id`, `action_id`, `type`, horário e IDs de objeto/proveniência; conteúdos textuais sensíveis ficam sujeitos a políticas separadas. Documentar endpoint/limites reais observados, comandos/testes/exits, migração reversível e contrato de origem. Se acesso API live não foi autorizado, marcar integração externa **NOT TESTED**, sem alegar sincronização produtiva.

---

## PROMPT 03 — Bot narrativo diário do Trello com evidências, sem envio externo automático

**Missão.** Produzir o primeiro resultado operacional: resumo diário legível das alterações Trello capturadas pelo prompt 02, com fontes e interpretação prudente; configurar Bot + Cron já existentes, sem novo framework de agentes ou provider.

**Preflight.** Confirmar que o journal do prompt 02 está GREEN e que o acesso à base foi delegado; ler `tools/cronjob_tools.py`, `cron/scheduler_delivery.py`, `cron/scheduler.py`, contratos Bots e `workstation/trello_action_journal.py`. Reservar somente novo módulo de resumo/testes/config e docs; não editar arquivos do Cron se simples configuração e job bastarem.

**Implementação.** (1) Criar `workstation/trello_daily_brief.py` (ou módulo de Bot estabelecido na arquitetura) com função pura `collect_brief_facts(conn,board_id,period_start,period_end)` retornando fatos ordenados, contagens e `action_id` fonte, limitados por janela e quantidade; (2) separar `render_brief_prompt(facts,instructions)` de execução LLM, encapsulando eventos como dados não confiáveis, não como instruções; (3) registrar um Bot de relato (prompt configurável) e um Cron que utiliza a configuração existente `cron.model`/`cron.model_provider` quando não há override por job; (4) entregar inicialmente no chat/inbox interno do Hermes, com dry-run. WhatsApp pessoal é entrega futura dependente de canal WA qualificado e autorização explícita; **não enviar agora**.

**Roteiro de testes.** Teste RED de janela UTC/locale, mais de um quadro, nenhum evento, duplicatas no journal, cartões renomeados/movidos, comentários sem acesso ao conteúdo e injeção de prompt nos dados; GREEN: texto não inventa nomes, motivos, conclusões nem prazos ausentes, inclui referência ao ID do evento e declara lacunas. Usar fake LLM para inspecionar prompt; teste de Cron/delivery em ambiente isolado, conforme `tests/gateway/test_webhook_cron_trigger.py` e suites locais, sem calls externas.

**DONE.** Um `cron_job` existente gera relatório baseado apenas em eventos de fixture e mantém a saída persistida e rastreável. Comandos, entradas de fixture, hashes/IDs, falhas, custos estimados e instrução do Bot registrados. A configuração é reversível; nenhum token de API entra em versionamento. Não inventar sucesso de envio para WhatsApp.

---

## PROMPT 04 — Acionar jobs existentes por evento de negócio com outbox idempotente

**Missão.** Conectar eventos confiáveis (inicialmente Trello) aos Bots/Cron do Hermes. **Não** criar um segundo scheduler ou concluir automaticamente tarefas a partir de um evento não correlacionado.

**Preflight.** Ler `workstation/events.py::SystemEventPipeline`, `tools/cronjob_tools.py::execute_job_for_event`, `cron/executions.py::recover_interrupted_executions`, `tests/gateway/test_webhook_cron_trigger.py` e testes de eventos. Obter claims para novo adaptador e banco autorizado; coordenar com owner Trello do prompt 02 para contrato de evento, sem editar as mesmas fontes simultaneamente.

**Onde e como.** Usar `reference-code/business_event_outbox.py` + `reference-tests/test_business_event_outbox.py` como base isolada (4/4 testes em sandbox), após revisar migration/claims. Criar `workstation/business_event_dispatch.py` como adaptador fino, não alterar `SystemEventPipeline` para atribuir autoridade a eventos sem TaskRun. Definir `BusinessEventEnvelope(source,event_id,event_type,object_id,observed_at,payload_ref)` — ID estável vem da origem, não de UUID aleatório. Persistir `event_delivery`/outbox numa tabela de controle do mesmo banco autorizado: `UNIQUE(source,event_id,route_id)` com estados `PENDING`, `CLAIMED`, `DELIVERED`, `UNCERTAIN`, `FAILED_SAFE`, timestamp e número de tentativa. Roteador resolve regra **previamente autorizada** para job existente, depois chama `execute_job_for_event(job_ref, extra_prompt=...)`. Não transformar `claimed=true` em prova de que um efeito externo foi entregue; estado depende de confirmação independente.

**Plano mínimo:** (1) RED: dois eventos idênticos, 2 workers concorrentes, crash após claim, job inexistente, fonte não autorizada e ação parcialmente concluída; (2) migration + reserva transacional do outbox; (3) publisher com lease/claim e reconciliação antes de retry; (4) GREEN com fake job/Cron, provando que duplicate não dispara uma segunda execução; (5) um percurso Trello → journal → dispatch → Bot, read-only e verificável. Se o executor Cron não suportar idempotency key por evento, implemente fence/outbox neste adaptador e seja conservador após estado incerto.

**DONE.** Sem duplicação sob replay/restart, sem escalação de eventos não correlacionados, dados restritos a origem/regra, auditoria de todas as decisões e testes locais de concorrência. Não enviar WhatsApp nem modificar cartões externos. Documentar migrations, retry policy e significado preciso de `UNCERTAIN`.

---

## PROMPT 05 — Homologação ASR/TTS local e configuração de modelo por automação

**Missão.** Transformar mecanismos de áudio e seleção de modelos já existentes em capacidade qualificada do Hermes, sem instalar VoiceStudio, duplicar TTS ou automatizar Google AI Studio.

**Preflight.** Reservar somente configuração de runtime de áudio e testes; conferir `tools/transcription_tools.py::transcribe_audio`, `tools/transcription_local.py`, `agent/transcription_provider.py`, `tools/tts_tool.py::text_to_speech_tool`, `tools/tts_tool_local.py`, `agent/tts_provider.py`, `tools/cronjob_job_args.py` e configuração `cron.model`/`cron.model_provider`. Não instalar modelos pesados automaticamente em máquina compartilhada; verificar licenças, dependências e memória antes.

**Execução.** (1) Criar fixtures de áudio sintético/consentido e texto português em diretório temporário; (2) diagnosticar dependências instaladas por provedor sem imprimir segredos, testar `faster-whisper` local com presets pequenos (por ex. `base`/`small` + `int8` em CPU se suportado) e TTS já configurado, medindo latência, RSS, qualidade e formato; (3) adicionar ou reparar adaptador determinístico `path -> transcribe_audio -> {text,language,provenance}` no runtime existente, sem chamar LLM durante transcrição; (4) teste de síntese `text -> áudio real` com ffprobe quando disponível; (5) validar precedência modelo do job > default Cron > modelo do agente, sem criar configuração global duplicada.

**Testes e aceite.** RED para falhas de dependência, input ausente, arquivo grande, língua pt-BR, áudio inválido, provedor desabilitado, outbound network acidental; GREEN com fixture de áudio verdadeiro e comando real. Registrar comandos, provider, versionamentos, CPU/RAM e variabilidade. Não afirmar voz nativa WhatsApp; isso fica em gate separado. Evitar distribuir gravações ou dados de voz de pessoas.

---

## PROMPT 06 — MVP de monitoramento configurável de uma página sem IA em loop

**Missão.** Adicionar à Workstation o menor monitor de página reutilizável: configurar uma aba/elemento, observar alterações com limites e registrar evento, acionando o adaptador do prompt 04 quando regra autorizada corresponder. Não criar monitor universal de todas as origens no primeiro incremento.

**Preflight.** Exigir prompts 02/04 qualificados e claims Browser/UI. Ler `apps/desktop/electron/workstation-browser-dom-revision.ts`, `workstation-learning-dom.ts`, `workstation-browser-runtime.ts`, gerenciamento de BrowserTask/owner/lease, e UI de abas `apps/desktop/src/app/browser/`. Os `MutationObserver` atuais são para cache e efeitos locais, não monitor durável; não reutilizar listeners com ciclos de vida incompatíveis.

**Alterações.** (1) Contrato `PageWatchConfig{id,session_id,tab_id,origin,selector?,rule,route_id,enabled}` validado e persistido na store canônica de configuração, separadamente de estado de tarefas; (2) um observador por aba/origem, debounce, diff sem dados sensíveis, fingerprint estável, eventos tipados `page_changed` e periodic reconciler restrito; (3) UI `Ativar monitoramento` e painel pequeno com status, último evento, pausa, erro de autenticação; (4) módulo de ligação com outbox do prompt 04, sem invocar LLM para cada mutação; (5) desativação imediata em login/logout/navegação fora da origem, takeover humano e fechamento da aba. Persistir configuração, **não fingir persistência do observador quando aba está fechada**. Background capture é escopo futuro próprio.

**Testes.** RED para repaints, relógio/digitação (ruído), 2 observers concorrentes, DOM virtualizado, reload SPA, logout, mudança de origem, seleção de input sensível, logout+restart, aba fechada, travamento renderer, event duplicate; GREEN unitário + Electron Chromium real. Não capturar conversa/credencial de páginas arbitrárias nem inventar acessos ao WhatsApp.

**DONE.** Usuário ativa/desativa um monitor em página fixture, um evento é emitido com prova de origem e sem conteúdo privado, pausa/reconciliação funcionam, duplicatas suprimidas, sem alteração na autoridade de TaskRun e sem execução pós-logout. Documentar limites e exatamente o que deixa de funcionar com aba fechada.

---

## PROMPT 07 — Fechar o bloqueio WA-M3 de evidência nativa (não habilitar envios)

**Missão.** Concluir a qualificação da prova de identidade da conversa/destinatário e ACK no WhatsApp Browser nativo, SEM envio de mensagens reais nem relaxamento dos controles.

**Preflight.** Confirmar expressamente ownership de caminhos WA-M3 e liberar claims anteriores por owner — não roubar claim. Ler `workstation/context/WHATSAPP_RELIABILITY_2026-10-24.md`, `WHATSAPP_IMPLEMENTER_PROMPTS_2026-10-24.md`, `KNOWN_ISSUES.md` `WA-M3-01`, `workstation/integrations/hermes/whatsapp_browser_executor.py`, `site-ops/scripts/site-ops/whatsapp-web.mjs`, `apps/desktop/electron/workstation-browser-runtime.ts` e `tests/tools/test_whatsapp_browser_tools.py`. M1/M2 locais devem ser preservados.

**Correção proposta.** (1) TDD RED: snapshot nativo não apresenta `data-chat-id`, `data-recipient-id`, `data-direction`, `data-ack` comprováveis; casos homônimo, bolha antiga, `msg-meta` avulso, composer vazio, click sem receipt e recibo com `run_id` incompatível devem bloquear prova; (2) projetar metadados mínimos DOM autorizados, tipados e somente leitura no runtime nativo ou adaptar verificadores a evidência genuinamente disponível — não inventar atributos no JavaScript; (3) garantir base de saída antes do click, nova mensagem após click, identidade exata, digest de conteúdo e ACK da mesma mensagem; (4) estado pós-dispatch ambíguo → `UNCERTAIN`, sem segundo clique/retry automático; (5) verificar snapshot real **sem enviar** e testes negativos comparando identidades/sessões.

**DONE.** E2E readback real do Browser demonstra origem e atributos válidos (ou registra HOLD sem inventar sucesso); testes nativos admission/recovery + Python WA focados verdes, preservação PII e políticas auditadas. M4–M6 permanecem HOLD até gate completo, mesmo que sintéticos passem. O integrador, não o agente, decide enviar teste real a número explicitamente autorizado.

---

## PROMPT 08 — Memória semântica do WhatsApp com evidência e sem duplicar mensagens

**Missão.** Construir projeção semântica por contato a partir do histórico WhatsApp Control autorizado, sem criar outro banco de contatos e sem transformar hipóteses em fatos.

**Preflight.** Depende de WA-M3 qualificado para efeitos externos; para leitura/rascunho pode avançar isoladamente se o owner aprovar, sem alterar o executor M3. Ler schema `contacts/conversations/messages` e `persist_read_messages` em `workstation/integrations/hermes/whatsapp_browser_executor.py`, política de privacidade e de identidade de contatos. Claim exclusivo sobre migrations de memória e novos módulos.

**Alterações.** (1) Criar projeção/versionamento de `contact_memory_fact` na mesma base autorizada, com `contact_id`, `fact_key`, `value` minimizado, `source_message_id`, `confidence`, `status={hypothesis,confirmed,retracted}`, `updated_at` e `expires_at`; `source_message_id` deve referenciar mensagem efetivamente persistida; (2) janela recente das últimas 30 mensagens deve ser **consulta**, nunca duplicação de material bruto; (3) extrator LLM somente para novidades semanticamente relevantes, produzindo candidatos inertes para revisão quando ambíguos; (4) reconciliação por versões/contradições (retract/supersede), retenção privada, classificação por origem autorizada; (5) logs sem conteúdo bruto e sem PII.

**Testes/aceite.** Duas capturas da mesma mensagem não duplicam fatos; conflito entre mensagens preserva evidências e gera revisão; identidade inexistente não une contatos por homônimo; mensagem apagada/retenção expirada invalida projeções conforme política; restore reconstruível. Não enviar nada a terceiros. Registrar testes, migração, política de retenção e posição das novas tabelas no modelo canônico.

---

## PROMPT 09 — Extração de demandas WhatsApp → triagem Kanban, sem tarefa automática definitiva

**Missão.** Relacionar demandas explicitamente identificadas em mensagens autorizadas com a triagem canônica do Kanban, sem criar tarefas duplicadas ou inventar prazos/responsáveis.

**Preflight.** Depende do Prompt 08 e da existência de mensagens verificáveis; ler `workstation/kanban.py::WorkstationKanbanBridge`, `workstation/work_intent.py`, `workstation/task_compiler.py`, `workstation/events.py` e schemas WA. Confirmar fonte de verdade e claim das alterações; não utilizar o P0 MCP experimental como autorização do Hermes.

**Alterações.** (1) Definir contrato puro `DemandCandidate(source_message_id,contact_id,description,due?,assignee?,confidence,evidence_refs)`; (2) usar LLM apenas para `candidate` com evidência, proibir assumir que pedido a terceiro é necessariamente tarefa do usuário; (3) registrar `UNIQUE(source,message_id,candidate_kind)` e `review_required` para ambiguidade; (4) quando claramente autorizado, chamar API de triagem existente da Kanban sem forjar TaskRun/execução; (5) registrar mudanças de status e permitir revisão/descartar. Sem envio de resposta WhatsApp.

**Testes/aceite.** Corpus com exemplos positivos/negativos/ambíguos, reprocessamento, mensagens editadas, grupos, datas relativas incertas, múltiplos contatos homônimos. Nenhuma TaskRun aparece sem claim real, nenhum prazo é inventado, duplicatas permanecem uma só demanda. Reportar precisão/amostras e falhas.

---

## PROMPT 10 — Homologar replay supervisionado do Modo Aprender sem autopromoção

**Missão.** Fechar somente o gate de execução supervisionada de candidatas do Modo Aprender. Reaproveitar observadores DOM, gravador, question engine e Experience Compiler existentes.

**Preflight.** Ler `workstation/context/CURRENT_STATE.md` P02/P03/P04/P05, `KNOWN_ISSUES.md` HLM-KI-06, `apps/desktop/electron/workstation-learning-session.ts`, `workstation-learning-segmenter.ts`, `workstation/skill_learning.py`, lifecycle TaskRun e testes já existentes. Claims separados dos owners do runtime Browser/WhatsApp; se chocarem, estacionar o trabalho.

**Implementação.** TDD RED da promoção indevida: CandidateLesson de demonstração sem `VERIFIED_SUCCESS` nunca passa a capacidade ativa. Implementar percurso supervisionado explícito: seleciona candidato → autorização humana contextual → TaskRun com session/tab/owner → execução em fixture → readback independente e receipt → qualificar somente se critérios verificáveis forem atingidos. Falha, mudança de origem ou tomada humana resultam em HOLD e trilha de evidências, sem forjar etapas do chat.

**DONE.** Replay em Electron Chromium com artefato real e verificação independente; testes de fracasso/restart/duplicidade; nenhuma aprendizagem promovida por mera observação. Documentar captura e gate do recorder FFmpeg separadamente da validação de replay.

---

## PROMPT 11 (OPCIONAL, NÃO PRIORITÁRIO) — Benchmark isolado do Moli

**Missão.** Responder experimentalmente se o navegador Moli merece ser backend **auxiliar**, sem substituir Chromium ou alterar Browser Workstation principal. Ler `tools/browser_lightpanda.py`, `tools/browser_tool_lightpanda_fallback.py`, `agent/browser_provider.py` e contratos de Browser nativo. Inspecionar licença/versionamento e instalar somente em sandbox reversível, com autorização, não globalmente.

**Etapas.** Criar benchmark idêntico em Chromium e Moli: páginas públicas/fixture e fluxo de DOM, HTML dinâmico, autenticação falsa local, upload falso, compatibilidade CDP, consumo CPU/RSS, latência, erros, falsas confirmações e cleanup. Proibir credenciais reais. Medir ganho total considerando falhas/retries. Emitir decisão `GO_EXPERIMENTAL` ou `NO_GO` documentada; integração de produção é tarefa posterior independente.

---

## PROMPT 12 (OPCIONAL, NÃO PRIORITÁRIO) — Pesquisa EmbeddingGemma 2

**Missão.** Validar exclusivamente a utilidade de EmbeddingGemma 2 na **recuperação** multimodal, não transcrição ASR ou raciocínio. Inspecionar `agent/memory_provider.py`, indexadores existentes, licença/model card e configuração local. Não adicionar ao caminho crítico nem armazenar WhatsApp bruto.

**Etapas.** Propor corpus sintético consentido com texto/imagem/áudio/documentos e consultas cruzadas; comparar com busca determinística/BM25/embedding existente, medindo recall@k, latência, RSS, custo de indexação e falsos positivos. Executar benchmark isolado e produzir API pequena de backend candidato apenas se superar baseline de forma significativa. Proibir migração de dados reais sem consentimento e plano de rollback. Emitir GO/NO-GO; não apresentar como alternativa ao faster-whisper.

---

## Formato de entrega obrigatório para CADA prompt

Entregar ao final: (a) HEAD/branch/dirty inicial e final; (b) caminhos sob claim do agente e integrador dono de commit; (c) contrato/decisões e desvios justificados; (d) diffs por arquivo; (e) evidência RED + GREEN com comandos e exits; (f) validação nativa onde exigida; (g) segurança e riscos residuais; (h) Known Issues que continuam abertos; (i) atualização incremental do `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` e `workstation/context/engineering-journal/CURRENT.md` somente pelo owner documental, ou handoff de inserts caso esses arquivos estejam claimed. Não chamar `DONE/RELEASE` para teste sintético ou código não integrado.

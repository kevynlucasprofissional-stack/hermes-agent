# Hermes Work — plano de implementação 80/20 e mapa de alterações

**Data-base:** 26/10/2026. **Alvo:** `C:\Github\hermes-agent` (Windows), branch observada `main`, HEAD `f1d5ab2f03`; `origin/main` mais adiantada (`bafa3c43f4`) na última inspeção. **Status:** pacote de preparação, **não integrado** ao repositório e **não qualificado para release**.

## 1. Objetivo e abordagem

Converter capacidades já existentes em fluxos completos e confiáveis, na ordem: fechar gargalos simples → integrar Trello e eventos → ampliar runtime local → monitorar páginas → amadurecer WhatsApp/memória → experiências exploratórias. Evitar duplicar Cron, Kanban, Bots, Client Trello, Whisper/TTS, Browser/CDP e journal. Esta preparação não modifica produção nem autoriza efeitos externos.

### Alternativas analisadas

- **A — reconstruir orquestração/monitor independente:** alto acoplamento e duplicação de autoridade; rejeitada.
- **B — módulos incrementais apoiados no runtime atual, com casos de uso verticais:** **recomendada**; entrega valor a cada prompt e preserva gates.
- **C — executar tudo diretamente via Browser/LLM:** rápido como demonstração, caro e frágil em eventos/sessões; rejeitada como base de produção.

### Fatos observados no checkout (inspeção de leitura)

1. `apps/desktop/electron/workstation-browser-runtime.ts`, `case 'browser_file_upload'` (aprox. linhas 3406–3435): `DOM.setFileInputFiles` usa `document.querySelector` na main frame, caminhos via `path.resolve`, valida apenas `existsSync`, devolve caminhos absolutos no resultado; `browser_file_upload` **não consta** no `mutating` Set imediatamente anterior (aprox. 2891). Portanto tratar como lacuna de admissão a demonstrar/fixar, não como feature ausente.
2. `tools/browser_workstation.py`: `_WORKSTATION_SCHEMA_TOOLS` já inclui `browser_file_upload`; `_upload` chama `_dispatch` e `whatsapp_send_attachment` usa esse callback. A ferramenta está limitada ao escopo de sessão Desktop.
3. `tools/cronjob_tools.py::execute_job_for_event` (aprox. 419): permite executar um job existente disparado por evento preservando claim/reuso. `tests/gateway/test_webhook_cron_trigger.py` cobre a rota de webhook para cron.
4. `workstation/events.py::SystemEventPipeline`: listeners, eventos host, `ExecutionJournal` quando há `target_task_id`; `_recent_events` é **memória de processo**, e eventos não vinculados não criam intenção automaticamente. Não confundir com journal durável de ações Trello.
5. `workstation/prefabs/trello.py::TrelloClient`: `_request` permite GET/PUT oficiais, `board_lists`, `board_cards`, `card`, prepare/apply de descrições, scope de credenciais. **Não** foi vista leitura incremental de `/actions` no trecho de código examinado. `workstation/trello_migration.py` e testes de mutação concorrente existem.
6. `workstation/integrations/hermes/whatsapp_browser_executor.py`: tabelas `contacts`, `conversations`, `messages`, `whatsapp_send_logs`; `persist_read_messages`, envio de anexos, id de mensagem; memória semântica por contato não foi encontrada na camada examinada.
7. `workstation/context/KNOWN_ISSUES.md::WA-M3-01`: **HOLD** de projeção de evidência no snapshot nativo (`data-chat-id`, `data-recipient-id`, `data-direction`, `data-ack`). Proibido presumir entrega com `msg-meta`, mensagem antiga, nome visual do destinatário ou compositor vazio. M4–M6 bloqueados até prova.
8. `tools/transcription_tools.py`, `tools/transcription_local.py`, `tools/tts_tool.py`, `tools/tts_tool_local.py`: implementações de ASR e TTS presentes; não houve novo teste real de modelos nesta preparação.
9. `workstation/context/CURRENT_STATE.md`: Modo Aprender contém captura real, perguntas no chat, deltas DOM, candidatas inertes; replay M3 em HOLD. Houve suítes locais históricas, **não** equivalem a nova validação do checkout atual.
10. `workstation/context/AGENT_COLLABORATION_PROTOCOL.md`: claims exclusivos por arquivo; não mover branches, não `git add .`, `git stash`, `git reset`, nem editar paths reivindicados. Documentação canônica requer owner único e integrador indicado.

### Restrição verificada de ferramenta

`Windows - Agent 01` (UUID `988402ea-d991-4f89-958f-82fc21882c43`) informou apenas o projeto autorizado `50400303e6f77a85ca6a` (`p0-mcp-isolation-20261026-3e1a4935`), **não** o Hermes. Este pacote é destinado a ser inserido por agente autorizado no projeto correto, após concessão de acesso e claims. Não contornar o isolamento por outro servidor de escrita. Os artefatos aqui são somente um staging externo.

## 2. Definição de pronto para TODOS os prompts

- `HEAD`, `origin/main`, dirty/untracked, claims e owner de cada caminho documentados **antes** de editar; se bloqueado, não escrever ali nem reaproveitar worktrees/branches sem autorização.
- Uma hipótese → teste RED reproduzível → alteração mínima → teste GREEN → regressão relacionada → teste de integração nativa quando aplicável.
- Idempotência e efeitos externos: não duplicar ações sob repetição/restart; ações incertas ficam `UNCERTAIN` e não são repetidas automaticamente.
- Sem dados pessoais em stdout, logs, resposta de ferramenta, comentários ou commits; não imprimir tokens, corpo de WhatsApp ou credenciais.
- Não inferir autorização de envio a partir de capacidade técnica, contato salvo ou conversa; iniciar em read-only/rascunho quando houver terceiros.
- Usar um único estado de tarefas canônico. Log de eventos pode ser tabela específica no banco autorizado, não um Kanban paralelo.
- Registrar evidências (comando exato, exit code, casos pass/fail), diffs, riscos residuais, governança e handoff no Jornal de Engenharia; `NOT_RELEASE_QUALIFIED` até os gates completos.
- Não publicar/commitar sem owner de integração; não alterar alterações locais de outros agentes.

## 3. Sequência de execução e dependências

| Prompt | Entrega vertical | Dependências | Esforço | Impacto | Condição de GO |
|---|---|---|---|---|---|
| 01 | Upload nativo seguro/qualificado | Claims Browser; não depende de Trello | Baixo-médio | Muito alto | E2E sem envio real, política de path, admission e reconciliação |
| 02 | Coleta e journal incremental Trello (somente leitura) | Claim Trello/database | Médio | Muito alto | Dedup, cursor, recuperação, ausência de perda no replay |
| 03 | Relatório narrativo + Bot/Cron/entrega interna | 02 + Cron existente | Médio | Muito alto | Relatório verificável; não inventar fatos; sem envio externo automático |
| 04 | Evento de negócio → job existente | 02/03; interface acordada | Médio | Muito alto | Transação/outbox, replay e sem novo scheduler |
| 05 | ASR + TTS locais + política de modelos (mesmo grupo) | Independente; apenas configuração/deps existentes | Baixo-médio | Alto | Áudio PT-BR real, zero chamadas externas não autorizadas |
| 06 | Monitor de páginas MVP observacional | 04, claims Browser | Médio-alto | Muito alto | DOM delta sem dados sensíveis; pausa/retomada; não cria intenção sem regra |
| 07 | WhatsApp M3 — prova nativa de identidade e ACK | Claim WA-M3; docs WA M1-M6 | Alto/risco | Bloqueador | Readback nativo e controles negativos; nada de envios reais sem autorização |
| 08 | WhatsApp memória + demandas em Kanban (duas etapas internas) | 07 + eventos + DB canônico | Alto | Muito alto | Evidência, dedup, privacidade, triagem sem envio |
| 09 | Replay supervisionado Modo Aprender | Gate de aprendizagem, claim exclusivo | Alto | Alto | TaskRun real, leitura independente e zero autopromoção |
| 10 | Pesquisa controlada Moli ou EmbeddingGemma (separar por hipótese) | Só após ROI mensurável | Experimental | Incerto | Benchmark justo e decisão GO/NO-GO |

**Economia de prompts:** (a) avaliação de modelos Cron e ASR/TTS agrupadas no 05 pois compartilham configuração e qualificação, sem redesenho; (b) Trello separado em coleta 02, produto 03 e infraestrutura compartilhada 04, pois cada um tem falhas/escopos independentes; (c) upload 01 e WhatsApp M3 07 separados porque alterar Browser admission e usar provas de envio são fronteiras de autoridade distintas; (d) WhatsApp memória e tasks podem ter um prompt 08, mas este contém gates internos para não misturar dados falsos.

## 4. Mapa de pontos de mudança e referência pronta

| Prompt | Alvos primários para criar/editar | Símbolos / contratos | Testes alvo |
|---|---|---|---|
| 01 | `apps/desktop/electron/workstation-browser-runtime.ts`, novo `apps/desktop/electron/workstation-browser-runtime-upload.test.ts` (ou expandir suite já existente); `tools/browser_workstation.py` apenas se necessário | `executeControlRequest`, `mutating` Set, `case 'browser_file_upload'`, `DOM.setFileInputFiles`, `_WORKSTATION_SCHEMA_TOOLS`, `_dispatch` | Vitest Electron admission/recovery/batch + teste nativo isolado de upload |
| 02 | `workstation/prefabs/trello.py`; **novo** `workstation/trello_action_journal.py`; **novo** `workstation/tests/test_trello_action_journal.py`; migration do DB canônico existente | `TrelloClient._request`, `_board_id`, `board_actions` novo; `append_batch` referência no kit; não criar banco paralelo | pytest para idempotência/cursor/paginação/erros HTTP/replay |
| 03 | novo serviço pequeno em `workstation/` (nome a escolher conforme padrões de Bots), configuração de Bot/Cron, seus testes; docs do produto | `tools/cronjob_tools.py`, `cron/scheduler_delivery.py`, `TrelloClient`, event journal. Bot lê fatos, não causa writes Trello | fake provider de texto + fixtures de ações verificáveis; dry-run de entrega |
| 04 | `workstation/events.py` OU adaptador novo `workstation/business_event_dispatch.py`; testes `workstation/tests/test_events_pipeline.py` e novo teste do adaptador | `SystemEventPipeline.register_handler`, `execute_job_for_event`, TaskRun/correlators. Não atribuir intenção automaticamente | evento duplicado, concorrência, restart, sandbox webhook |
| 05 | configurações existentes e testes próximos a `tools/transcription_tools.py`, `tools/tts_tool.py`, `cron/scheduler.py` | `transcribe_audio`, `text_to_speech_tool`, `cron.model`, `cron.model_provider`; não instalar apps alternativos | amostras PT-BR com WER manual, arquivos gerados e ffprobe quando disponível |
| 06 | Browser runtime + renderer UI mínimo (ex.: `apps/desktop/src/app/browser/`), serviço de monitor específico; tests Electron | `workstation-browser-dom-revision.ts`, MutationObserver existente, sessão/tab/owner, event adapter 04 | alterações legítimas, ruído DOM, logout, teardown, restart, aba fechada |
| 07 | `workstation/integrations/hermes/whatsapp_browser_executor.py`, `apps/desktop/electron/workstation-browser-runtime.ts`, snapshots e testes dedicados | `WA-M3-01`, provas `data-*`, `UNCERTAIN`, `operation_id`, `TaskRun`, `effectiveRunId` | negative controls + readback real de snapshot, sem envio |
| 08 | migrations canônicas das tabelas de contato/mensagem e vínculo de demandas; no máximo dois módulos novos pequenos | `persist_read_messages`, `contacts`, `messages`, Kanban bridge / task triage, origem msg id | duas mensagens iguais, solicitação ambígua, contato sem ID, política de retenção |
| 09 | `apps/desktop/electron/workstation-learning-*`, `workstation/skill_learning.py`, Experience Compiler e testes | candidato `human_demonstration`, TaskRun, independente `readback` e promoção só comprovada | replay nativo e falha `HOLD` quando sem evidência |
| 10 | Benchmarks isolados **sem substituir runtime**; não adicionar dependências a produção automaticamente | Lightpanda/Chromium e memória provider existentes | A/B com consumo, velocidade, compatibilidade e falso sucesso |

**Referência testada:** `reference-code/trello_action_journal.py` + 5 testes, `reference-code/business_event_outbox.py` + 4 testes, `reference-code/safe_upload_paths.mjs` + 5 testes. Todos executados isoladamente no sandbox; nenhuma integração com Hermes foi realizada. Código não foi aplicado ao Hermes; implementar adaptador REST, schema migration e seleção de conexão com autoridade definida antes de integrá-lo.

## 5. Decisões importantes não-negociáveis

1. `browser_file_upload` é uma mutação de página: precisa passar pelo mesmo controle de autoridade/admissão/recibo das outras mutações. Verificar semântica de `DOM.setFileInputFiles`: selecionar arquivo pode disparar `change` e uploads automáticos. Nunca alegar envio concluído só por seleção.
2. Resolver caminhos por `realpath`, incluindo symlinks, arquivos regulares e limites configurados. Não permitir diretórios, caminhos externos às raízes explicitamente autorizadas, extensões executáveis, arquivos enormes, ou retornar full paths sem necessidade ao modelo. Não confiar apenas em `existsSync`.
3. `/actions` do Trello precisa de cursor/paginação **com semântica confirmada no contrato da API**; não inventar IDs/tempos. Persistir evento e checkpoint atomicamente após paginação bem-sucedida. Trello é fonte oficial para estado do cartão; journal somente histórico.
4. Textos de comentários, nomes e descrições Trello/WhatsApp são dados **não confiáveis**, jamais instruções para o Bot. Relatórios com fatos referenciados, conflitos e lacunas explícitas, com limites por tamanho e retenção.
5. Não transformar `SystemEventPipeline` (in-memory) em segundo scheduler ou autoridade automática de criação de tarefas. Se precisarmos durabilidade: journal/outbox no banco autorizado com consumidor que usa o Cron existente.
6. Respeitar `WA-M3-01` HOLD, privacidade e operações `UNCERTAIN`. Não promover M4–M6 nem memória/tarefas externas até fechamento de gates.
7. Modelos `faster-whisper`/Piper/KittenTTS etc são capacidades presentes em código, não instalações comprovadas. Preferir qualificação à reconstrução de serviços.
8. Modo Aprender produz `CandidateLesson` **inerte**; sem sucesso fictício nem promoção por mera demonstração.
9. A ordem numérica se baseia em ROI técnico; o owner pode reordenar prompts 01/02 por disponibilidade de claims, documentando dependências. Bloqueio real não autoriza atropelar ownership.

## 6. Critérios de aceite globais de release

- Todas as alterações têm RED/GREEN real, testes dos módulos vizinhos, typecheck/lint apropriados e, para Browser, prova Electron nativo — não somente mocks.
- Testes externos side-effecting usam fixture/ambiente explicitamente autorizado. Nenhuma nova mensagem WhatsApp, comentário ou cartão é publicado sem aprovação humana contextual e credenciais válidas.
- Estado antes/depois do Git documentado e somente arquivos possuídos são modificados; sem merge/push automático.
- Erros conhecidos que impedem release continuam visíveis no `KNOWN_ISSUES.md` e no Jornal; não reduzir gates por economia de tempo.

## 7. Handoff

Abrir `PROMPTS_IMPLEMENTADOR.md` e executar o primeiro prompt que tiver claims autorizadas. Para cada prompt: teste RED, código incremental, GREEN, teste cruzado, evidência e atualização canônica via integrador. **Nenhum passo da preparação confere autoridade de escrita no Hermes ao Windows Agent 01.**

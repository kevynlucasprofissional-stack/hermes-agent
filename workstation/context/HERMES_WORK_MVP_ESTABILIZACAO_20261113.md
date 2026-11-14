# Hermes Work — Estabilização do MVP antes do PROMPT 5

**Criado:** 13/11/2026 · **Repositório:** `C:\Github\hermes-agent` · **Branch/HEAD observados na preparação:** `main@f1d5ab2f03` (revalidar em toda execução).
**Estado:** E1 verificado parcialmente em 13/11/2026 (Unicode RPC PASS, 50 testes focais PASS, versão ativa iniciada após patches; comportamento `no_effect` não exercitado diretamente no processo servidor). E2–E4 permanecem pendentes. Nenhuma mensagem, TaskRun operacional ou reinício foi realizado por este ensaio.

**Evidência E1:** checkout `main@f1d5ab2f03`, ~592 entradas dirty/untracked na abertura. Electron iniciou às 01h25; bundle `electron-main.mjs` de 01h25; os módulos P1 e `no_effect` foram modificados em 12/11 às 16h42–17h25. O backend `hermes_cli.main serve` foi observado após reinícios externos às 02h17 e 02h31, com instalação do Workstation Adapter às 02h31; `hermes-nav.mjs status` confirmou `aiControl:true`. Um `gateway.ping` via PowerShell → Python `-X utf8` → WebSocket respondeu com o mesmo ID Unicode `Você — texto QA: mensagem unica` (codepoints exatos; 1 RPC read-only; 0 sends e 0 TaskRuns solicitadas). A correção do transporte requer `OutputEncoding` e `PYTHONIOENCODING` UTF-8; a alteração é no harness, **não** no verificador de destinatário. Runner oficial: `test_kanban_evidence_recovery.py`, `test_denied_mutation_handoff_recovery.py`, `test_whatsapp_point_admission.py`, `test_whatsapp_fast_send.py` — **50 PASS / 0 FAIL**. Parametrizado `test_whatsapp_pre_send_failure_does_not_open_recovery_child` para `PRE_SEND` e `RESOLVE_RECIPIENT`; os testes existentes preservam incerteza pós-clique. **Limite:** processo iniciado depois do patch e adapter ativo não equivalem à execução demonstrada do ramo `no_effect` pelo gateway; nenhuma TaskRun foi criada para testar isso em produção. Sem código-fonte alterado nesta etapa; somente teste e registros. Não reiniciar novamente apenas para validar timestamp.
**E2 verificado em 13/11/2026 — HOMOLOGAÇÃO PARCIAL:** o backend ativo usa `hermes_cli/kanban_db.py::kanban_home` compartilhado **entre perfis** por design; `session.create` não aceita board/DB per-session e `work_intent.py` usa a seleção compartilhada. Portanto **não existe isolamento QA por sessão comprovado** para executar mutação+DONE no mesmo servidor sem gravar no banco operacional. Nenhuma tentativa de reconfigurar `HERMES_KANBAN_DB`/board global ou forjar DONE foi feita. Em QA loopback temporária: revision inicial/final 0, `qa_applied_operations=0`, `quick_check=ok`. Gateway operacional real: sessão `20261113_030034_ed1536` criada por `session.create` + uma `prompt.submit`, `browser_navigate` iniciou e concluiu, BrowserTask Electron vista, mas o observador expirou após 26,37 s sem evento `message.complete`. **Surpresa negativa:** uma tarefa foi criada no Kanban operacional pela própria classificação de ingresso, `t_ac005742` / run 106 `done`, sem POST: **NÃO é prova E2**, não foi editada/apagada. Causa reproduzida: a frase de restrição `do not create tasks` e a palavra `test` foram contadas como duas ações, gerando `durable_task`. Correção mínima em `workstation/kanban.py::is_multistep_request` ignora verbos de ação negados na detecção multi-ação; novo teste `test_p0_kanban_intent_semantics.py` RED 1 FAIL → GREEN com `test_current_command_native_intent_contract.py`: **14 PASS**. Readback e evidência: **73 PASS** em três arquivos focais. Correção no checkout, **não carregada automaticamente no runtime**. A UI Kanban foi aberta com `hermes-nav.mjs goto kanban` (`headings: Kanban`); a visibilidade/estado da tarefa QA na interface não foi comprovada. O processo de fixture QA (PID 26752) foi encerrado, relatórios em `%TEMP%\hermes-e2-readonly-86689e307c\negative-report.json`; nenhum clique de salvar, nenhum POST, nenhum dado externo editado. A navegação da UI não foi revertida por `goto sessions` (módulo inexistente), mas `activeTab` permaneceu `Sessions`. **E2 continua PENDENTE**; para homologação estrita é preciso um ingresso QA com board escopado ao mesmo processo, reaproveitando o mecanismo de boards existente, ou declarar essa limitação sem distorcer testes isolados.

**Relação:** complementa `HERMES_WORK_MVP_EXECUTION_PROMPTS_20261112.md` (P1–P4); **P5 fica suspenso** até que os fluxos essenciais sejam comprovados. O plano `BROWSER_KANBAN_GENERIC_VERIFICATION_PLAN_20261112.md` é específico do Kanban e exclui Trello; respeitar esse escopo quando executá-lo.

## 1. Diagnóstico de partida — fatos, não hipóteses

| Frente | Prova existente | Lacuna que ainda importa |
| --- | --- | --- |
| P1 — WhatsApp/TaskRun | O modelo chamou `whatsapp_send_message` através do gateway real; `whatsapp_point_admission.py` criou TaskRun automaticamente; testes P1 37 PASS | Verificar qual versão das últimas correções de resultado está realmente carregada; não recriar ingresso/TaskRun |
| P2 — ACK perdido / HTTP 303 | Readback com identidade causal testado; POST único; negativas impedem DONE | O owner Electron não fecha duravelmente a admissão original; falha espontânea nativa não foi homologada. Não repetir clique histórico |
| P3 — Browser → Kanban | Processo QA isolado com `AIAgent.run_conversation`: 1 POST, GET novo, revisão 0→1, TaskRun `done`, 1 EvidenceRef; gateway ativo abriu `trello.com` via `prompt.submit` | Mesmo processo do backend ativo ainda não demonstrou **edição QA + persistência + done**; fluxo funcional do Kanban Hermes precisa ser verificado sem confundir com Trello |
| P4 — WhatsApp único | Auto-chat `hermes_local/1` resolveu; gateway real executou exatamente 1 tool call; `FAILED/RECIPIENT_NAME_MISMATCH/PRE_SEND`, 0 cliques, 0 envios, 0 intents; 10,95 s, 2 LLM calls | O **harness PowerShell → Python**, não o Browser, trocou `Você` por `Voc?` e corrompeu o corpo Unicode. Não houve envio real pela rota atual |
| Recuperação indevida | Falha `PRE_SEND` gerou subtarefa de evidência sem existir efeito; patch `no_effect` em `tool_observer.py`/`evidence_recovery.py`, RED→GREEN 48 PASS | Patch ainda não comprovadamente carregado no backend; preservar histórico e tarefas já criadas |
| Medição | P3: 17,84 s / 4 chamadas LLM; navegação gateway: 19,55 s; P4: 10,95 s / 69.125 tokens processados | Não há base para promover P5 nem afirmar redução de custo |

**Evidências principais:** `workstation/context/engineering-journal/CURRENT.md`; `%TEMP%\hermes-native-agent-qa-bf608088b7\report.json`; `%TEMP%\hermes-p3-gateway-92a0c23753\report.json`; `%TEMP%\hermes-p4-whatsapp-7acf3a31d4\report.json`. Se arquivos temporários sumirem, não inventar métricas; usar journal e verificar novamente apenas o necessário.

**Preservação:** checkout compartilhado com ~591 entradas dirty/untracked na última inspeção; outro agente pode estar escrevendo. Não fazer reset, stash, clean, troca de branch, commit, push ou restart automático. Não alterar dados do Trello, banco de contatos, campanhas ou tarefas históricas. Não executar envios do WhatsApp como teste de regressão. Usar `scripts/run_tests.sh` somente nos testes diretamente afetados. Stage A não é gate de desenvolvimento local.

## 2. Ordem e critérios de saída

| Ordem | Missão | Evidência de saída |
| --- | --- | --- |
| **E1 — P0** | Verificar versões carregadas, corrigir Unicode no harness e aplicar classificação `no_effect` | Texto Unicode chega intacto por `prompt.submit` **sem enviar**; `FAILED/PRE_SEND` não cria recuperação indevida em QA; runtime carregado identificado |
| **E2 — P0** | Fazer o Kanban Hermes concluir uma tarefa QA pelo ingresso operacional | 1 `browser_type`, 1 `browser_click`, POST=1, GET independente, revisão 0→1, `tasks=done` e `latest_run=done` com EvidenceRef; uma negativa sem DONE |
| **E3 — P1 condicional** | Fechar admissão do owner após ACK perdido | Mesma operation admission reconciliada com readback causal, sem ACK inventado e sem novo POST; identidade run/session/tab preservada. Só executar se bloquear/contaminar operações reais |
| **E4 — P0** | Homologar **nova** mensagem individual auto-chat | Uma solicitação explícita nova de usuário, uma tool call, destino exato, 0–1 clique, novo recibo ou falha correta; ledger e latência auditados; nunca duplicar |

**Critério para iniciar P5:** E1, E2 e E4 utilizáveis, sem duplicidade e com estados de evidência honestos. E3 só bloqueia quando houver impedimento concreto na rota normal; um caso histórico isolado pode permanecer HOLD. Não converter P5 em novo gate universal.

---

## PROMPT E1 — Runtime real, Unicode e recusa sem efeito

**MISSÃO:** inspecionar os processos/versões do Hermes Desktop, backend Python, owner Electron e o diff dos alvos; comprovar que o patch P1 e a correção `no_effect` estão carregados. Não duplicar código.

**Procedimento:**
1. Observar Git, processos, timestamps/entrypoints e import dos módulos atuais; não presumir que `git status` prova código carregado. Se houver versão antiga, identificar modo de recarga já existente e impacto sobre sessões, leases e BrowserTasks. Não reiniciar sem necessidade e autorização compatível.
2. Testar o transporte de texto **sem efeitos externos**: `PowerShell` → `Python` → RPC com `Você`, travessão e corpo de QA. Comparar bytes/codepoints de entrada com os observados pela ferramenta/ingresso. Se o ensaio usar `python.exe -`, empregar `$OutputEncoding = New-Object System.Text.UTF8Encoding($false)`, `$env:PYTHONIOENCODING='utf-8'` e `-X utf8`, ou alternativa equivalente confirmada. **Não alterar a comparação rigorosa de destinatário para mascarar erro do transporte.**
3. Verificar em teste isolado `workstation/integrations/hermes/tool_observer.py` e `workstation/evidence_recovery.py`: `FAILED` nas fases `PRE_SEND`/`RESOLVE_RECIPIENT` vira `no_effect` e não agenda filho; `UNCERTAIN` pós-clique mantém fence e investigação somente leitura. Não editar `t_80898c0c` / `t_c6777211` nem outros registros históricos.
4. Roda curta de testes: `test_kanban_evidence_recovery.py`, `test_denied_mutation_handoff_recovery.py`, `test_whatsapp_point_admission.py` e testes de Unicode/ingresso realmente tocados.

**Aceite:** versão ativa comprovada, Unicode íntegro, no-effect correto no fluxo de teste, nenhuma mensagem e nenhuma TaskRun operacional nova. Se recarga não for viável, `CÓDIGO PRONTO / RUNTIME PENDENTE`, não alegar homologação.

## PROMPT E2 — Kanban real, não Trello

**MISSÃO:** provar o caminho `ingress de chat → TaskRun → Browser nativo → servidor QA → GET → Kanban DONE` **pelo backend operacional** do Hermes. Reutilizar `workstation/browser_operation_readback.py`, `completion_admission.py`, `kanban.py` e harness de agente existente; não criar outro evaluator.

**Procedimento:**
1. Conferir que E1 habilitou os módulos carregados. Preparar fixture loopback/SQLite temporário de edição com revisão inicial 0 e identidade única. **Não redirecionar globalmente** o SQLite/Kanban do usuário nem alterar tarefas existentes. Se o backend ativo não suportar isolamento por sessão/fixture, usar apenas o mecanismo oficial já disponível ou classificar a limitação precisamente; não produzir um DONE falso no DB operacional.
2. Por `session.create` + `prompt.submit` do gateway real, criar uma TaskRun QA legítima (sem forjar ContextVar/task_id); fazer 1 type e 1 click no Chromium Electron, contar POSTs. GET read-only *novo* precisa confirmar recurso, título/revisão e operação. Verificar `tasks.status`, `latest_run.status`, `EvidenceRef` e `verifier_results` na base QA.
3. Uma negativa mínima: GET ausente/divergente ou revisão errada → **não DONE**; não segundo clique. Validar que navegação simples não cria TaskRun desnecessária. Conferir que a interface do Kanban Hermes mostra estado coerente, sem consultar Trello.
4. Não repetir E2E histórico como substituto. Testes focais: `test_browser_kanban_canonical_readback.py`, `test_native_browser_operation_evidence.py`, admission/kanban pertinentes.

**Aceite:** 1 POST, GET causal, DONE canônico e interface coerente **na via real**. Sem esta prova, resultado `HOMOLOGAÇÃO PARCIAL` com bloqueio exato; sem nova arquitetura apenas para maquiar o teste.

## PROMPT E3 — Owner Electron após ACK perdido (somente se necessário)

**MISSÃO:** se uma operation admission pendente realmente afetar uma nova operação ou impedir E2, resolver seu estado terminal usando o contrato existente; caso contrário manter no backlog sem atrasar E4/P5.

**Procedimento:** inspecionar `apps/desktop/electron/workstation-browser-session-state.ts::reconcilePendingAdmission`, `workstation-browser-runtime.ts`, `browser_operation_readback.py` e receipt original. Reproduzir uma vez em fixture nova de HTTP 303 com ACK intencionalmente ausente; GET read-only deve trazer ID causal/revisão. Conciliar **a mesma** admission/task/run, sem forjar ACK, sem reemitir click/POST; divergências → UNCERTAIN. Testar isolamento entre abas/runs e recarga do documento. Usar testes Electron correlatos apenas se IPC/owner mudar. Nunca executar cliques sobre operações históricas pendentes.

**Aceite:** no máximo um POST; admissão não herda resultado alheio; efeito provado concilia por via canônica; evidência insuficiente continua UNCERTAIN; fluxo normal não sofre regressão.

## PROMPT E4 — WhatsApp self-chat: uma homologação nova

**MISSÃO:** somente mediante **nova instrução explícita de envio** do usuário, realizar um único `whatsapp_send_message` pela entrada operacional Hermes já preparada em E1. O plano não reutiliza a autorização ou o texto da operação FAILED anterior.

**Procedimento:**
1. Revalidar `hermes_local/1` pelo banco privado, o nome literal cadastrado e o ledger do **novo texto**. Não expor telefone, corpo, tokens de sessão ou IDs privados em logs. Se operação anterior com mesmo corpo/escopo estiver OBSERVED/UNCERTAIN, **HOLD**. Sem busca fuzzy.
2. Antes de submeter, conferir UTF-8 na fronteira do RPC (nome e corpo exatos), sem modificar o texto enviado. Uma entrada `prompt.submit`, uma tool call, TaskRun automática; sem cartão manual, segundo approval, CDP externo ou clipboard. Preflight de destinatário fica no executor nativo.
3. Se a validação de identidade falhar antes do clique: `FAILED/PRE_SEND`, zero clique, nenhum recovery child. Se clicar: ler novo message ID/baseline, recibo DOM e registro de intent. `OBSERVED` indica apenas UI; `CONFIRMED` exige fonte independente; evidência insuficiente → `UNCERTAIN` e nenhuma repetição. Não reenviar sob outro operation_id.
4. Medir `user_to_result_ms`, calls nativos/snapshots, LLM turns/tokens conforme logs reais; sem inventar custos. Testes focais: `test_whatsapp_fast_send.py`, `test_whatsapp_point_admission.py`, `test_whatsapp_browser_executor.py`, `test_whatsapp_causal_receipt.py`, `test_whatsapp_recipient_resolution.py` apenas se código correspondente mudar.

**Aceite:** destinatário exato, no máximo 1 clique, estado verdadeiro e ledger persistente, zero duplicações. Se continuar FAILED, registrar o defeito preciso e encerrar a operação sem segunda tentativa.

## 3. Entrega e disciplina de execução

Ao concluir **cada** prompt, atualizar somente este plano e uma nota factual em `engineering-journal/CURRENT.md`, com arquivos/linhas alterados, testes RED/GREEN, IDs QA sanitizados, contagens, tempo/calls e **código em disco versus runtime efetivamente carregado**. Não retomar o PROMPT 5 original antes dos critérios de saída. Evitar reexecutar as 104 regressões históricas e não confundir build/mocks/relato com fluxo real. Se bloqueado, retornar RESUME PROMPT de um único próximo defeito verificável; não relançar a investigação inteira.

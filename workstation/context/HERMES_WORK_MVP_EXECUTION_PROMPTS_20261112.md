# Hermes Work — MVP executável: plano consolidado e prompts de implementação

**Preparação:** 12/11/2026 · **Checkout:** C:\Github\hermes-agent · **Branch observada:** main · **HEAD observado:** f1d5ab2f03.
**Estado atualizado (12/11): P1 implementado/testado; P2 readback em QA; P3 chat operacional de navegação aprovado, escrita no backend ativo pendente; P4 executado uma vez e FAILED PRE_SEND por corrupção Unicode no transporte QA (zero cliques/envios); P5 pendente.** Não tratar ensaios ou correções ainda não carregadas como homologação integral.
**Objetivo:** três fluxos pela entrada real do Hermes: (1) abrir Trello; (2) enviar uma mensagem individual autorizada; (3) editar um item QA pelo Browser, confirmar persistência e concluir TaskRun. Menos chamadas, sem falsos sucessos e sem duplicação.

## 1. Evidências e decisões: não refazer o que já existe

| Área | Estado inspecionado em 12/11 | Consequência para o implementador |
| --- | --- | --- |
| Base | Python + Electron/TypeScript, Chromium WebContentsView, SQLite canônico, Workstation + Prefabs + System 1; Electron/Vite/Python ativos em desenvolvimento | Inspecionar o código **carregado**, pois processos podem anteceder as últimas edições em disco |
| Checkout | main@f1d5ab2f03; centenas de arquivos dirty/untracked (581 na inspeção anterior). Estado volátil, com escritores simultâneos | Não resetar, limpar, trocar branch, fazer stash/commit/push/restart automático ou sobrescrever alterações |
| Ingresso | workstation/work_intent.py distingue conversa, point_action e durable_task; workstation/kanban.py fornece WorkstationKanbanBridge | Preservar essa separação; não produzir cartão para leitura/conversa |
| WhatsApp ingress | workstation/integrations/hermes/whatsapp_point_admission.py::admitted_whatsapp_point_send e agent/tool_executor.py::_dispatch_authorized_once já implementam claim automático de TaskRun | **Não implementar novamente**; validar e integrar |
| Contradição WhatsApp | **Corrigida no model-facing** em tools/browser_tool.py::_handle_whatsapp_send_message: exige current_work_execution_identity com mesma sessão; TaskRun é criada automaticamente por agent/tool_executor.py. O wrapper interno conserva session-only para callers internos existentes | **Implementado e 37 testes PASS; sem recarga do Hermes ativo nem envio real** |
| Recusa sem efeito | workstation/batch_detection.py::_whatsapp_pre_dispatch_refusal e record_mutation já registram refused_no_effect | Não reimplementar; apenas provar que a via operacional usa esse estado |
| Execução WhatsApp | whatsapp_native_send_bridge.py já concentra um clique e prova DOM, e existem melhorias de snapshot documentadas no jornal | Evitar rollback do fast path; OBSERVED não é confirmação independente do servidor |
| Browser → Kanban | browser_operation_readback.py, native_browser_evidence.py, completion_admission.py e Kanban; browser_kanban_native_e2e_p2.py aprovou Chromium/GET/SQLite em QA isolado | Falta homologação **pela entrada real do agente** com código atualizado |
| ACK perdido | POST real com HTTP 303 persistiu, mas browser_click retornou browser_input_delivery_unverified; TaskRun ficou running; sem segundo POST | P3 real: reconciliação read-only sem novo commit |
| Operação conhecida | integrations/hermes/operational_resolution.py, work_intent.py::recognize_current_command, prefabs/integration.py, system1 e browser_readiness.py já têm fast paths | Medir e corrigir só falhas reproduzidas de despacho/retorno; não criar novo router |
| Trello | Database visual, Kanban executável e Trello externo são entidades distintas; sincronização integral não integra este MVP | Usar fixture QA para edição genérica; Trello real só com cartão QA explicitamente autorizado |

**Evidências existentes:** context/BROWSER_KANBAN_GENERIC_VERIFICATION_PLAN_20261112.md; context/WA_MVP_02B_AUTONOMOUS_E2E_20261112.md; context/WHATSAPP_EXECUTION_PLAN_20261112.md; context/OPERATIONAL_SPEED_COST_REDUCTION_2026-10-10.md; context/engineering-journal/CURRENT.md. No jornal consta um envio anterior ao auto-chat com recibo de interface, não uma homologação de envio autônomo pelo fluxo atual.

**Regras de autoridade e evidência:** destino/escopo corretos; um efeito por operação; não repetir efeito potencialmente ocorrido; leitura independente quando o objetivo é persistência externa; diferenciar OWNER_ACK, UI_OBSERVED, EXTERNALLY_PERSISTED e UNCERTAIN. Para WhatsApp, usar OBSERVED quando houver apenas recibo DOM; não simular ACK do servidor. Não modificar base de contatos ou campanhas. Preservar isolamento de sessões, controle humano sobre BrowserTask, IDs canônicos e contratos de ToolEffect.

**Diretriz contra sobrearquitetura:** resolver a falha mais próxima do efeito; não criar outro Browser, Kanban, gateway, banco de admissão, verificador ou scheduler. Stage A/H-079 não bloqueia correção local (AGENTS.md e workstation/AGENTS.md). Documentos históricos não substituem testes atuais. Superpowers e community-agent-workflows: consultar se presentes, empregar apenas práticas úteis, sem novos gates.

## 2. Solução preparada — ponto de decisão e patch candidato

O conflito concreto deve ser decidido no PROMPT 1:
- Caminho A (preferido se a política canônica atual for exigência do owner): a ferramenta model-facing só é despachada dentro de admitted_whatsapp_point_send; a TaskRun criada pelo host fica invisível ao usuário. Nesse caso **remover fallback somente do handler model-facing**, mantendo compatibilidade de callers trusted onde comprovada. O patch condicional abaixo aplica-se em tools/browser_tool.py::_handle_whatsapp_send_message, depois de validar o contexto e antes de chamar whatsapp_send_message.
- Caminho B (somente se demonstrar equivalência de autoridade): operação individual de fato é session-scoped com BrowserTask, operação durável única e reserva idempotente; então o wrapper de TaskRun extra deve ser simplificado, sem deixar dois modelos de identidade simultâneos. Precisa provar que chamada externa não pode contornar autorização e que replay não duplica envio.
- **Não aplicar A ou B por aparência**. Decidir com código da via real, testes e um ensaio sem envio. A atual mistura é a hipótese de maior risco de integração.

Patch A, **APLICADO NESTA MISSÃO** ao handler model-facing (sem alteração do wrapper interno). Registro RED: 2 testes falharam antes da mudança; GREEN: 37/37 testes PASS pelo scripts/run_tests.sh:

~~~diff
--- a/tools/browser_tool.py
+++ b/tools/browser_tool.py
@@
-    if identity is not None and identity["session_id"] != session_id:
+    if identity is None or identity["session_id"] != session_id:
         return json.dumps({"sent": False, "state": "REVIEW_REQUIRED",
                            "error_code": "TASKRUN_AUTHORITY_REQUIRED",
                            "failure_phase": "VERIFY_TASKRUN"})
-    canonical_task = identity["kanban_card_id"] if identity is not None else None
-    canonical_run = identity["run_id"] if identity is not None else str(call_id)
+    canonical_task = identity["kanban_card_id"]
+    canonical_run = identity["run_id"]
~~~

**Decisão executada:** descrição da ferramenta alterada para declarar claim automático da TaskRun; test_whatsapp_fast_send.py agora exige recusa antes de despachar na ausência de identidade canônica; test_whatsapp_point_admission.py conserva a prova positiva via dispatcher/registry e ajusta schema. A verificação de recusa sem efeito permanece no batch_detection, com regressão de handoff verde. **Não foi introduzido segundo guard no wrapper nem novo sistema de autorização.** Para PROMPT 4 falta confirmar carregamento pelo Hermes real e observar um ensaio autorizado; não repetir este patch.

## 3. Sequência e dependências

PROMPT 1 (consolidar contrato do envio, recusa e TaskRun) → PROMPT 2 (Browser ACK perdido e reconciliação) → PROMPT 3 (entrada real Browser → Kanban e edição QA). PROMPT 4 (WhatsApp individual real) depende de PROMPT 1 e de Browser sem bloqueio impeditivo do PROMPT 2; não depende de conclusão de P3 se o Browser estiver funcional. PROMPT 5 (fast path, medição, homologação final) depende dos fluxos utilizáveis de P3 e P4.

Condição de avanço: um defeito reproduzido resolvido com teste focado e resultado na via real sempre que possível. Caso o fluxo normal já passe, marcar como comprovado e **não implementar** patch redundante. Não criar novo gate para prosseguir a uma fase independente. Trello externo, campanhas e sync integral permanecem fora do MVP.

---

## PROMPT 1 — Convergir ingresso de mutação individual e classificações sem efeito

**MISSÃO:** C:\Github\hermes-agent, main. Resolver a contradição entre TaskRun automática do envio individual e o fallback session-only; deixar uma política model-facing inequívoca. Ações individuais não podem exigir cartão criado pelo usuário e perguntas/navegações não devem criar Tasks. Corrigir somente defeitos atuais.

**Contexto comprovado:** workstation/work_intent.py::prepare_turn_work classifica point_action; workstation/kanban.py::WorkstationKanbanBridge possui claim canônico. workstation/integrations/hermes/whatsapp_point_admission.py::admitted_whatsapp_point_send, chamado em agent/tool_executor.py::_dispatch_authorized_once após policy/guardrails, já abre TaskRun real e ContextVar. tools/browser_tool.py::_handle_whatsapp_send_message e tools/browser_workstation.py::whatsapp_send_message ainda suportam session-only. test_whatsapp_point_admission.py verifica TaskRun; test_whatsapp_fast_send.py ainda testa o fallback sem ela. workstation/batch_detection.py::_whatsapp_pre_dispatch_refusal já classifica no-effect.

**Procedimento:**
1. Inspecione estado do checkout e diff destes arquivos, incluindo escritores ativos. Leia AGENTS.md, workstation/AGENTS.md, tools/AGENTS.md, context/README.md e DEVELOPMENT_GATES.md; nada de reset, stash, troca de branch, commit, push ou restart. Ignore Stage A como gate de desenvolvimento. Não reabrir pesquisa geral.
2. Confirme se o dispatcher do modelo é a única via externa para whatsapp_send_message. Reproduza o resultado da via real **sem envio** usando mocks e testes existentes; compare session-only e TaskRun por identidade, autorização, isolamento e replay.
3. Escolha um único contrato para **chamadas model-facing**: preferir ingresso canônico automático já escrito se o Browser/ledger o exigirem. Se escolher TaskRun, considere este patch **diretamente no handler existente**, após conferir o diff atual:

~~~diff
-    if identity is not None and identity["session_id"] != session_id:
+    if identity is None or identity["session_id"] != session_id:
         return json.dumps({"sent": False, "state": "REVIEW_REQUIRED",
                            "error_code": "TASKRUN_AUTHORITY_REQUIRED",
                            "failure_phase": "VERIFY_TASKRUN"})
-    canonical_task = identity["kanban_card_id"] if identity is not None else None
-    canonical_run = identity["run_id"] if identity is not None else str(call_id)
+    canonical_task = identity["kanban_card_id"]
+    canonical_run = identity["run_id"]
~~~

Atualize também tools/browser_tool.py (descrição da ferramenta) para indicar que a TaskRun é vinculada automaticamente pelo host; adapte a expectativa session-only em test_whatsapp_fast_send.py. Se escolher session-only, **não aplique** o patch: justifique com evidência a equivalência do BrowserTask/ledger e simplifique a camada redundante sem enfraquecer idempotência. Preserve chamadas internas com uso comprovado.
4. Testar: uma requisição legítima cria no máximo uma execução; dois tool calls no mesmo turno não enviam duas vezes; outra sessão/turno ou tarefa bloqueada não adota run antiga; origem não confiável não passa; recusa pré-dispatch não vira UNCERTAIN/handoff; trabalho durável e leitura continuam intactos.
5. Aplicar correção mínima, sem alterar WhatsApp real nem DB operacional. Reutilizar testes existentes; criar apenas teste faltante que reproduza desvio. Conferir que o executável operacional pode exigir recarga para adotar o módulo novo, sem reiniciar silenciosamente.

**Testes pertinentes:** workstation/tests/test_whatsapp_point_admission.py; test_whatsapp_fast_send.py; test_p0_kanban_intent_semantics.py; testes de workstation/batch_detection e de tool_executor diretamente afetados. Preferir scripts/run_tests.sh (Git Bash; runner oficial); no Windows usar runner do projeto já configurado. Não executar suíte completa histórica por padrão.

**Aceite:** a mesma invocação autorizada recebe um vínculo válido (ou política session-only comprovadamente equivalente), sem intervenção extra, com zero envio no ensaio; negativas não produzem efeitos ou handoffs falsos. Não basta mocks para declarar envio homologado.

**Relatório:** arquivos e linhas alterados; contrato escolhido e motivo; RED/GREEN/negativas; versão carregada; evidência; pendência única. Atualizar contexto no plano vigente e uma nota factual no engineering-journal/CURRENT.md. Se bloqueado, fornecer RESUME PROMPT específico, não reiniciar investigação.

---

## PROMPT 2 — Recuperação mínima do Browser nativo após ACK perdido

**MISSÃO:** reproduzir e corrigir o erro comprovado no fluxo Chromium: POST persistido + navegação HTTP 303 + browser_input_delivery_unverified, sem segundo POST e sem falsa conclusão. Não reconstruir Browser nem criar serviço de recuperação.

**Estado verificado em documentação:** fixture QA: um clique realizou POST, revisão 0→1, mas o ACK não chegou e a operação permaneceu INCERTA. E2E P2 normal separado funcionou. Há operationAdmissions no owner Electron e workstation/evidence_recovery.py, workstation/browser_operation_readback.py, workstation/native_browser_evidence.py, workstation/integrations/hermes/tool_observer.py. Estado corrente de P3 deve ser revalidado no código antes de alterar.

**Procedimento:**
1. Inspecionar diff dos alvos: apps/desktop/electron/workstation-browser-runtime.ts (admission, input, receipt), tools/browser_workstation.py::_dispatch, workstation/evidence_recovery.py e browser_operation_readback.py; focar chamada/ACK/303, não realizar auditoria do Browser inteiro.
2. Reproduzir uma vez em fixture isolada com identificador novo, sem clicar em pendência operacional histórica. Identificar se a falha decorre de navegação, owner receipt, IPC ou tratamento Python. Antes de qualquer retry, consultar o endpoint read-only do recurso original com operation_id e estado/revisão.
3. Se GET vinculado comprova o efeito, conciliar **a mesma** operation admission/TaskRun pela via canônica; sem fabricar ACK retroativo. Se não comprova, devolver UNCERTAIN e parar; não reemitir clique. Se o despacho comprovadamente não ocorreu, liberar nova tentativa legítima sem herdar bloqueio alheio.
4. Garantir escopo de task/session/run/tab/op e bloqueio de replay, inclusive ao perder foco/lease ou recarregar documento. Não criar segundo gate e não recarregar Electron sem necessidade. Ajustar a camada responsável apenas onde o defeito for reproduzido.
5. Manter o caminho P2 normal utilizável mesmo se um caso inconclusivo de P3 permanecer HOLD.

**Testes:** workstation/tests/test_browser_kanban_canonical_readback.py, workstation/tests/test_native_browser_operation_evidence.py, testes Electron owner/admission correlatos; fixture native real existente workstation/scripts/browser_kanban_native_e2e_p2.py para caminho positivo, apenas se necessário. Negativos: contador POST=1, GET divergente sem done, outro run/tab não herda resultado, operação anterior não sofre segundo clique. Usar temp SQLite/loopback; sem Trello/WhatsApp externo.

**Aceite:** ACK perdido não gera mutação duplicada; readback correto permite conciliar o mesmo efeito; o que não pode ser comprovado permanece UNCERTAIN; não contamina operações independentes. Evidenciar contador de POST e identidades, não somente pytest.

**Relatório:** causa exata, patch mínimo, testes, artefatos QA, estado funcional e pendências. Registrar uma nota no plano Browser já existente + journal, sem nova coleção de documentos.

---

## PROMPT 3 — Homologar entrada operacional Browser → persistência → Kanban

**MISSÃO:** provar pelo chat e runtime **real** do Hermes o fluxo já aprovado isoladamente: ação Browser nativa, gravação em servidor QA e finalização da TaskRun no Kanban. Corrigir apenas a desconexão necessária; não duplicar o verificador.

**Contexto comprovado:** workstation/scripts/browser_kanban_native_e2e_p2.py executou uma fixture HTTP loopback + SQLite QA, type/click no Chromium, POST único, leitura GET com revision 0→1 e conclusão done. Esse script executa seu próprio processo Python e utiliza owner Electron; não demonstra que o ingress, executor e completion_admission estejam carregados e conectados no servidor Hermes ativo. Componentes: workstation/browser_operation_readback.py::{BrowserReadbackContract,verify_native_browser_receipts}, workstation/native_browser_evidence.py, workstation/integrations/hermes/tool_observer.py, completion_admission.py, workstation/kanban.py::{finalize_turn_candidate,complete_task_with_report}, workstation/contracts.py::{EvidenceRef,BrowserTaskReport,AcceptanceEvaluator}, tools/browser_workstation.py::_dispatch.

**Procedimento:**
1. Revalidar checkout/diff e processos ativos. Confirme, com evidência, qual código o servidor Python e owner Electron carregaram. Se o backend ainda for anterior ao patch, preparar recarga controlada preservando sessões e BrowserTask; não reiniciar cegamente nem declarar homologação de código apenas salvo no disco.
2. Rodar **uma** TaskRun QA com entrada real do agente, o Chromium existente e a fixture isolada. Não repetir o script P2 histórico como substituto. Se precisar criar harness de entrada do agente, reutilizar ferramentas e ingress reais, não simular assinatura/TaskRun ou forjar ContextVars.
3. Executar browser_type + browser_click com operation_id e scope legítimos, manter único commit; obter uma leitura GET nova e confiável do recurso com id/campo/revisão. Alimentar o contrato P2 para o AcceptanceEvaluator existente. O fixture deve começar com revisão conhecida e persistir exclusivamente em tmp.
4. Confirmar tasks.status=done, latest_run.status=done, EvidenceRef/verifier correctos na base QA; divergência de id, campo ou revision impede done. Medir user_to_verified_ms, chamadas do Browser e LLM observáveis. Se o Browser normal funcionar mas reconciliação HTTP303 do PROMPT 2 continuar indeterminada, não recriar efeito nem ampliar escopo.
5. Como teste de valor ao usuário, abrir Trello pelo chat real e verificar host/BrowserTask/readiness. Para escrita, **não editar cartão Trello de produção**: a fixture QA é o alvo do MVP. Editar cartão remoto só se houver cartão QA explicitamente separado e autorizado, sem sobrescrever conteúdo humano.

**Testes:** workstation/tests/test_browser_kanban_canonical_readback.py e test_native_browser_operation_evidence.py, contratos do executor/admission/completion diretamente tocados, testes Electron apenas se owner IPC mudar. Script histórico pode ser usado como baseline, mas a prova obrigatória é passagem pela entrada real. Testes negativos: no done sem GET; revision incorreta; run/aba divergentes; efeito incerto não reenviado; perguntas não geram Tasks.

**Aceite:** um único POST confirmado por GET e revisão; um done canônico na TaskRun correta; uma negativa sem done; Trello abre pela entrada real; nenhum dado operacional externo tocado no ensaio. Guardar IDs redigidos, relatório QA e contagens de chamadas.

**Relatório:** arquivos, causa de falha de integração, evidência do processo carregado, roteiro executado, counters de commit/GET, estados SQLite, latência/calls, pendência concreta. Atualizar context/BROWSER_KANBAN_GENERIC_VERIFICATION_PLAN_20261112.md e journal sem recontar 104 testes históricos. Se runtime não puder ser recarregado, classificar **código pronto / homologação pendente**, sem concluir falsamente.

---

## PROMPT 4 — WhatsApp individual nativo, uma execução real, sem burocracia

**Execução registrada (12/11; NÃO REENVIAR):** WS real `session.create` + `prompt.submit`, sessão `20261112_172012_5ee671`, auto-chat `hermes_local/1` pré-validado, 1 chamada `whatsapp_send_message`, estado `FAILED`, `RECIPIENT_NAME_MISMATCH`, `PRE_SEND`, **0 cliques/0 envios/0 novas intenções**. A causa foi o pipe PowerShell → Python sem UTF-8: `Você` virou `Voc?` e o corpo Unicode também foi alterado antes do modelo. Correção do transporte **verificada sem enviar**: `$OutputEncoding = New-Object System.Text.UTF8Encoding($false)`, `$env:PYTHONIOENCODING='utf-8'`, Python `-X utf8`. Houve RED→GREEN para impedir que uma falha definitiva antes do envio crie nova tarefa de recuperação: 48 PASS em cinco arquivos focais; os testes não homologam envio. O antigo filho QA de recuperação foi preservado; não fazer limpeza. Medição: 10,95 s; 2 chamadas LLM, 68.632 entrada (14.080 cache), 493 saída; 69.125 tokens processados. Evidência sanitizada em `%TEMP%\hermes-p4-whatsapp-7acf3a31d4\report.json`. Para uma operação nova, revalidar ledger e destinatário e usar UTF-8; **não repetir esta operação**. O código de recuperação alterado nesta missão só estará no backend após recarga posterior controlada.

**MISSÃO:** pela interface operacional do Hermes, enviar **no máximo uma** mensagem técnica ao auto-chat autorizado usando o Browser nativo e registrar o estado verdadeiro. Não criar campanha, duplicar envio ou exigir cartões e confirmações extra do usuário. Depende de PROMPT 1; PROMPT 2 deve ter eliminado bloqueios de Browser relevantes ou deixado a operação anterior com escopo que não contamine a nova.

**Contexto técnico:** ferramentas já existentes whatsapp_find_contacts e whatsapp_send_message em tools/browser_tool.py; wrapper em tools/browser_workstation.py; executor workstation/integrations/hermes/whatsapp_browser_executor.py::whatsapp_send_message; nativo whatsapp_native_send_bridge.py::native_send_once; controle de destino por whatsapp_recipient_resolution.py e sqlite de intent; entrada canônica em agent/tool_executor.py e, conforme contrato escolhido, whatsapp_point_admission.py. Há canário histórico de self-chat com um clique e recibo DOM, sem qualificação da rota atual. Estados de retorno incluem FAILED, OBSERVED e UNCERTAIN. OBSERVED é evidência de UI e não ACK independente do servidor.

**Parâmetros da missão:** alvo exclusivamente self-chat previamente registrado no perfil, ref privado de contato (source=hermes_local, contact_id=1) se ainda resolver de modo unívoco para a própria conta; nome esperado literal do cadastro privado validado, sem confiar em seleção fuzzy. Texto novo e literal a usar apenas se o próprio prompt for enviado pelo usuário como autorização de uma operação: "QA Hermes MVP 20261112 — mensagem individual única do fluxo operacional." Se a referência tiver mudado ou existir outra operação incerta com o mesmo corpo/escopo, NÃO enviar. Não colocar número/corpo em logs abertos.

**Procedimento:**
1. Confirmar que o runtime carregou a correção do PROMPT 1 e que não há intenção **desta operação** já enviada ou incerta no ledger. Diferenciar operações históricas por run/op sem limpar ou reabrir admissão anterior. Confirmar sessão/browser owner e ref da própria conta. Não pesquisar manualmente o WhatsApp repetidamente: o executor faz o preflight necessário.
2. Na entrada real do agente, invocar whatsapp_send_message uma vez com recipient_ref, expected_recipient_name e message. A criação de TaskRun, quando exigida, é responsabilidade automática do host, sem pedido extra. Não usar terminal, CDP externo, clipboard ou canal alternativo.
3. Verificar no Browser nativo o destino correto, composer exato, no máximo um clique de enviar e um identificador novo de mensagem/baseline. Ler o estado da nova bolha e o registro durável da intenção. Se o clique tiver resultado incerto, **somente leitura**, sem nova chamada de envio nem novo operation_id.
4. Classificar corretamente: FAILED sem efeito, OBSERVED com recibo causal de UI, CONFIRMED somente se existir fonte independente de confirmação, UNCERTAIN se não puder resolver. Não marcar done ou sent em massa porque DOM histórico estava presente.
5. Medir duração total, chamadas Browser nativas, snapshots extras, LLM turns e tokens reais disponíveis. Reutilizar a melhoria do fast path do executor; não reimplementar otimização já feita.

**Testes:** workstation/tests/test_whatsapp_point_admission.py, test_whatsapp_fast_send.py, test_whatsapp_browser_executor.py, test_whatsapp_causal_receipt.py, test_whatsapp_recipient_resolution.py, test_whatsapp_batch_runner_runtime.py (somente regressões afetadas). Adicionar caso de destinatário divergente sem clique; duplicação por operation_id; falha de ACK; scope de outra sessão; pre-send refusal não vira uncertain. Testes isolados não substituem o ensaio vivo de uma mensagem.

**Aceite:** uma entrada de usuário, um destinatário self-chat correto, zero ou um envio efetivo (nunca dois), estado registrado condizente com a prova, sem etapa manual redundante. Para afirmar resultado "mensagem enviada" é suficiente declarar OBSERVED se só houver recibo DOM; **não** afirmar entrega do servidor. Campanhas continuam fora do escopo.

**Relatório:** evidência sanitizada da mensagem nova, quantidade de cliques, operações DB, estado/failure_phase, tempo e chamadas, arquivos alterados. Se não for seguro enviar, reportar HOLD específico sem tentar mais uma vez ou pedir aprovação que não acrescenta informação.

---

## PROMPT 5 — Fast paths, custo por resultado e homologação final do MVP

**MISSÃO:** após P3 e P4, tornar previsíveis e econômicas as capacidades conhecidas, provar o fluxo operacional completo e encerrar o MVP sem adicionar arquitetura. Não repetir envios como benchmark.

**Código existente:** workstation/integrations/hermes/operational_resolution.py::workstation_operational_resolution já tenta browser_find, QA System 1, maybe_resolve_navigation e intents duráveis antes do System 2; workstation/work_intent.py::recognize_current_command cobre Trello/HyperFrames; workstation/prefabs/integration.py, workstation/system1/laya_provider.py, workstation/browser_readiness.py, workstation/telemetry.py, workstation/task_compiler.py, workstation/operational_kernel.py. WhatsApp possui executor composto, e o jornal registra redução de snapshots sintéticos, não tempo real validado.

**Procedimento:**
1. Medir, com os mesmos cenários e estado equivalente, uma execução real de abrir Trello e outra de editar fixture QA. No caso WhatsApp, usar dados do ensaio P4, **sem reenvio**. Instrumentar usando telemetria existente: tempo ingresso→conclusão, tempo LLM, Browser, espera e readback; chamadas únicas por call_id, bytes, tokens cobrados quando disponíveis. Não usar tokens_estimated=350 como custo real; marcar indisponível em vez de inventar.
2. Identificar a maior repetição concreta de chamadas (por exemplo snapshots redundantes, resolver semântico repetido ou provider LLM desnecessário). Se os fast paths já funcionarem, apenas medir e registrar; não refatorar. Se falharem, corrigir no resolver/prefab/dispatcher atual, sem novo router ou uso da Laya como autoridade.
3. Para comando conhecido, usar reconhecimento exato sem LLM quando viável; ambiguidade/falha não conhecida cai em System 2, sem reexecutar efeito incerto. Reusar resultado fresco de chamada Electron quando suficiente; persistência externa ainda exige leitura confiável. Nenhum checkpoint/Experience Compiler bloqueia ação simples.
4. Reexecutar o mínimo necessário de negativos e fluxo real: abrir Trello correto; editar fixture QA uma vez e fechar TaskRun com GET; evidência do único WhatsApp P4 com estado correto. Não tocar Trello real nem reexecutar WhatsApp por curiosidade.
5. Consolidar os números before/after (mediana e p95 quando houver amostra real suficiente), com erros/UNKNOWN explícitos. Se um dos três cenários não tiver prova funcional, manter MVP **PARCIAL** e entregar próximo RESUME PROMPT focado, sem abrir um novo programa de arquitetura.

**Testes:** workstation/tests/test_operational_resolution_provider.py, test_current_command_native_intent_contract.py, test_p0_kanban_intent_semantics.py, testes Prefab/browser readiness efetivamente afetados, e smoke real P3/P4. TypeScript Electron se houve mudança no host; suites completas apenas quando evidência de regressão transversal exigir. Não tratar build ou mocks como E2E.

**Aceite:** três operações utilizáveis e honestamente classificadas; nenhuma duplicação; dados preservados; comandos reconhecidos sem micro-orquestração supérflua; números reais de latência/chamadas/custo disponíveis ou marcados UNKNOWN. Nenhuma meta percentual arbitrária; economias só declaradas se comparadas.

**Relatório:** resultado por cenário (PASS/HOLD/UNKNOWN), correções, testes, evidências, tempos/chamadas/tokens, impacto, limitações reais. Atualizar journal, context/CURRENT_STATE.md se a homologação mudou e o plano consolidado. Encerrar quando o MVP realmente funcionar.

---

## 4. Mapa de aprovação e encerramento

| Marco | Depende de | Prova suficiente | Não é necessário |
| --- | --- | --- | --- |
| M1 identidade única de envio | Nenhum | Dispatcher autenticado com um contrato coerente e negativas | Criar outro Task DB ou approval modal |
| M2 recuperação Browser | M1 não é requisito | Uma fixture HTTP303, POST único, readback ou UNCERTAIN honesto | Corrigir casos hipotéticos |
| M3 edição persistida e Kanban | Browser operacional | Entrada agente real + Chromium + GET novo + done em QA | Sincronização Trello |
| M4 mensagem individual | M1; Browser sem conflito relevante | Uma única operação ao self-chat, recibo causal ou HOLD correto | Campanhas ou múltiplos canários |
| M5 economia demonstrada | M3 e M4 | Comparação de chamadas/latência e estado dos três fluxos | Novo compilador, router, verificador ou grande suíte |

**Estado atualizado:** M1 implementado em código e exercitado pelo despacho real; M2 recuperação parcial em QA; M3 navegação real aprovada e escrita real comprovada apenas no processo QA isolado; M4 primeira operação real **FAILED PRE_SEND**, sem envio, com causa de codificação identificada e correção de falso handoff testada (não carregada); M5 não iniciado. O backend anterior a M4 não deve ser dado como corrigido por testes locais. Não repetir mutações/patches existentes sem verificar o checkout.

**Modelo obrigatório de handoff de cada implementador:** estado do checkout; problema e causa; arquivos/funções alterados; RED/GREEN, runtime e evidência; versão carregada; ações e efeitos externos reais; próxima falha material; RESUME PROMPT independente caso haja HOLD. Evitar relatório extenso sem resultado.

**Limites:** não limpar WAL, não importar cartões históricos, não mandar em lote, não executar efeitos externos fora do alvo autorizado, não descartar edições humanas. Se duas rodadas não melhorarem o fluxo real, reduzir ao menor caso reproduzível em vez de ampliar gates.

## 5. Transparência da preparação

- **Inspecionados diretamente:** AGENTS.md, workstation/AGENTS.md, tools/AGENTS.md; WorkIntent, Kanban, ponto de admissão, tool dispatcher/handler/wrapper, batch_detection, executor WhatsApp nativo, testes de ingresso e fast send, script Browser QA, index e jornal; processos Electron/Python e status Git na investigação anterior.
- **Executado nesta preparação:** runner oficial scripts/run_tests.sh para test_whatsapp_point_admission.py, test_whatsapp_fast_send.py e test_p0_kanban_intent_semantics.py: **25 PASS, 0 FAIL**. Os dois caminhos de teste passam isoladamente; isso **não** prova que o contrato único esteja integrado em runtime.
- **Atualização após execução do PROMPT 1:** patch A **aplicado** somente ao handler model-facing e descrição da ferramenta; dois testes ajustados. Verificado por 37 PASS / 0 FAIL no runner oficial. Configurações, bancos, WhatsApp real e Browser do usuário não foram alterados. A validação de runtime carregado permanece pendente.
- **Ainda não comprovado:** nova TaskRun e call model-facing no processo operacional carregado, recuperação do HTTP303, envio autônomo da nova mensagem, abertura Trello + edição via entrada real, redução efetiva de custo/latência. O jornal contém evidências históricas que não substituem essas provas.

# WA-MVP-02B — Envio individual autonomo sem segunda autorizacao

Estado observado em 12/11/2026 apos HOLD real de WA-MVP-02:
- Git main, HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e. Worktree compartilhada dirty; preservar alteracoes existentes.
- Codigo atual tools/browser_workstation.py:1977-1979 ja contem "No modal approval is requested". O prompt que exigia ONCE estava desatualizado para esta politica de UX. Nenhum cartao deve ser inventado.
- Skill instalada whatsapp-native-operator v0.2.0 descreve autonomia individual, sem approval interativo.
- Teste local focado workstation/tests/test_whatsapp_autonomous_send.py + test_whatsapp_taskrun_binding.py: 16 passed em 6.70 s. Estes testes nao sao E2E.
- Fonte privada: ref {"source":"hermes_local","contact_id":1}, display_name "+55 64 9247-0988 (Você)", phone_source=user_requested_unverified. Ledger whatsapp_send_logs: 0 linhas.
- Evidencia factual do Hermes em %LOCALAPPDATA%/hermes/qa/whatsapp/hold_wa-opc-011_20261112.json: nenhum whatsapp_send_message chamado; 0 envios; 0 cliques efetivados; TaskRun nao canonica (kanbanCardId null); browser_click recusado com browser_input_delivery_unverified e posteriormente reconciliation_required para op_browser_click_58652ca02566.
- Um canario anterior existe no auto-chat, mas NAO prova que o texto novo foi enviado e NAO autoriza repeticao de operacao incerta.
- A criacao automatica de TaskRun passa pela infraestrutura WorkstationKanbanBridge / ingress e o contexto de execucao de workstation/task_compiler.py. Nunca falsificar ids ou contextvars de autorizacao. Browser admission e um limite real e independente de TaskRun.

## Prompt corrigido para uma NOVA execucao no Hermes Work

MISSÃO WA-MVP-02B — Corrigir bloqueios reais e executar UMA mensagem autonoma para si mesmo.

O usuario ja definiu QUEM e O QUE. Nao mostre opcoes A/B/C, nao pergunte novamente quem/qual texto e nao crie cartao interativo ONCE. Nao utilize approval simulado nem tokens manuais. Esta delegacao vale SOMENTE para o seguinte envio individual, sem lote:

DESTINO: proprio auto-chat do WhatsApp Web, identificado como "+55 64 9247-0988 (Você)".
RECIPIENT_REF: {"source":"hermes_local","contact_id":1}.
EXPECTED_RECIPIENT_NAME: "+55 64 9247-0988 (Você)" (literal exato do cadastro confiavel).
CORPO LITERAL: WA-OPC-011 QA 20261112 — teste individual do Hermes Work — autorização única.
ENVIOS AUTORIZADOS: NO MAXIMO UM. Nao criar segunda tentativa.

1. Inspecione a skill instalada v0.2.0, registry e o estado atual do Hermes. Reconheca que a ferramenta whatsapp_send_message ja opera sem modal. Nao reimplemente approval desnecessario. Atualize instrucao obsoleta que sugira somente acirv_contacts: hermes_local tambem e fonte permitida de contatos individuais.
2. Corrija primeiro a falha de ingress/ciclo de vida: uma requisicao de envio singular e explicita deve entrar automaticamente em uma tarefa canonica Work do mesmo session_id (Kanban card + TaskRun/run_id) por WorkstationKanbanBridge. Reutilize o ingresso/provedor de Tasks real; sem fabricar contextvars, HERMES_KANBAN_TASK, ids, claims, sessions ou runs. Nao trate chat generico sem TaskRun como autorizado. Se o ingress falhar, reporte o erro reproduzivel e HOLD sem enviar.
3. Antes de qualquer clique, inspecione o journal de Browser admissions da operacao op_browser_click_58652ca02566. Reconcile lendo evidencia do controller nativo e do estado real da pagina sem reemitir o efeito. Utilize recuperacao automatica APENAS para casos provados pre-dispatch/zero efeito e suportados pelo controller. Se permanecer reconciliation_required ou browser_input_delivery_unverified sem confirmacao de nao-efeito, HOLD com codigo e causa tecnica. Nao contorne o bloqueio nem tente outro navegador.
4. Dentro da TaskRun REAL, use whatsapp_find_contacts(source="hermes_local",query="Você"). Exija exatamente ref hermes_local/1 e o label esperado. Confirme que o numero inteiro no perfil autenticado e no auto-chat nativo e +55 64 9247-0988; nome/URL sozinhos nao bastam. Se nao houver prova, HOLD.
5. Use whatsapp_send_message com recipient_ref, expected_recipient_name literal, message literal e verify_delivery=true. Nao solicite modal ONCE nem outra decisao ao usuario. A operacao deve reservar a intencao persistente antes do efeito e executar exclusivamente com a BrowserTask do run autentico.
6. No maximo UM clique de Enviar. Exija bolha NOVA, ID novo, corpo, autor e ACK correlatos. Verifique registro persistente de task/run/operation e estado. OBSERVED no DOM NAO E CONFIRMED pelo servidor.
7. Em qualquer resultado UNCERTAIN, nao repita send, nao renove operation_id e nao use deeplink/script externo como alternativa. Se a mensagem ja estiver presente, reporte evidencia; nao reenvie.
8. Campanhas continuam HOLD. Nao tocar no worktree de terceiros, nao realizar reset, stash, checkout, commit, push ou restart automatico.

ACEITE: task/run criados automaticamente de forma legitima, browser controller sem pendencia nao reconciliada, destino self-chat identificado, um unico envio, recibo causal e persistencia verificada sem segunda decisao humana.

Se um gate real impedir a execucao, reporte HOLD tecnico (sem escolher A/B/C) e o codigo especifico do defeito ainda a corrigir. Nao declarar homologacao com mocks, builds ou testes locais.

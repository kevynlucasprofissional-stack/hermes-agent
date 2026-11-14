# WA-OPC-011: ensaio autonomo real no Hermes

Data: 2026-11-12. Roteiro atual: substitui o procedimento antigo que
presumia fonte ACIRV para um teste de auto-chat.

## Destinatario de teste ja indicado pelo usuario

- Destino: o proprio WhatsApp Web autenticado, identificado na UI como Você.
- Referencia canonica: source=hermes_local, contact_id=1.
- Conta propria confiavel: telefone final 0988. Nao use acirv_contacts/88
  nem nenhum candidato obtido por busca semelhante.
- Mensagem unica especificada anteriormente:
  WA-OPC-011 QA 20261112 — teste individual do Hermes Work — autorização única.

## Estado comprovado ate aqui

- No teste anterior do Chromium, verified_sender_from_open_self_chat passou com
  cinco amostras e tres leituras nativas em 197 ms, sem envio.
- O modelo desktop expunha whatsapp_send_message e whatsapp_find_contacts;
  o schema exige recipient_ref, expected_recipient_name e message.
- Corrigido alias self-chat Você para hermes_local/1 somente se o numero do
  rotulo do contato coincide com o numero confiavel e com o numero proprio
  lido no auto-chat. A correspondencia nao se estende a outros contatos.
- O AI Control esta indisponivel agora: arquivo de descoberta da ponte
  aponta para PID terminado. Nao reativar por CDP, teclado ou bypass.
- Nenhum envio novo executado na rodada. Um teste unitario nao equivale
  a homologacao real do agente.

## Prompt para a TaskRun real (usar somente com AI Control autenticado)

Execute uma tarefa operacional individual no Hermes Work: envie exatamente
uma mensagem para o MEU PROPRIO WhatsApp conectado ("Você"), nao para
um contato homonimo nem para um contato da ACIRV.

Use a skill whatsapp-native-operator v0.2.0, o BrowserTask nativo da mesma
TaskRun e exclusivamente a tool registrada whatsapp_send_message.
Nao abra cartao de aprovacao humana: a TaskRun delega a operacao.

O destinatario e a referencia autorizados para este teste sao:
recipient_ref = {"source":"hermes_local","contact_id":1}
expected_recipient_name = "Você"
message = "WA-OPC-011 QA 20261112 — teste individual do Hermes Work — autorização única."

1. Confirme a TaskRun canonica e que a propria conversa Você esta aberta
   no WhatsApp Web autenticado. Se nao estiver na mesma BrowserTask, use
   apenas as tools nativas para localiza-la. Sem ownership, retorne HOLD.
2. Confirme autoria historica: linha de auto-chat, compositor, >=2 autores,
   e numero proprio identico a referencia hermes_local/1.
3. Use whatsapp_send_message UMA VEZ com os tres parametros acima.
4. Antes do clique o executor deve checar o destino no painel, texto no
   compositor e ausencia de replay da operacao; depois confirme ID novo,
   autoria, texto exato e status causal associado ao mesmo ID.
5. Retorne estado e evidencia de forma saneada (OBSERVED nao e servidor).
   Nao repita mensagens UNCERTAIN e nao use scripts privados, terminal,
   CDP externo, alteracao do banco ou um contato substituto.

Se a tool nao aparecer no schema atual do modelo, se AI Control estiver
indisponivel ou se a identidade divergir, nao envie. Relate o bloqueio
concreto (failure_phase/error_code) e encerre.

## Validacao pendente

A prova de envio iniciada pelo PROPRIO agente Hermes com essa referencia
ainda nao ocorreu nesta rodada. Campanhas continuam em HOLD.

# WA-MVP-02D - Envio real unico para auto-chat

Execute um unico envio real no WhatsApp Web nativo do Hermes. Ja defini destinatario e mensagem; esta solicitacao autoriza apenas essa operacao. Nao solicite ONCE, menu de escolhas ou criacao manual de TaskRun.

Destinatario: minha propria conta, +55 64 9247-0988 (Você).
recipient_ref = {"source":"hermes_local","contact_id":1}
expected_recipient_name = "+55 64 9247-0988 (Você)"
Mensagem literal: WA-MVP-02D QA 20261112 - verificacao real do auto-chat do Hermes.

Carregue a skill whatsapp-native-operator atual e chame diretamente whatsapp_send_message com esses tres parametros. O dispatcher assume a TaskRun automaticamente. O executor valida o chat, digita a mensagem, clica em Enviar no maximo uma vez e confere a nova mensagem com texto/ID/ACK e o registro persistente.

Nao repita uma operacao com efeito incerto. Em erro anterior ao clique, informe state, error_code, failure_phase, numero de cliques e log. OBSERVED no DOM nao e confirmacao independente do servidor. Nao envie por shell/CDP externo, nao mexa no Kanban ou nos logs e nao dispare campanhas.

Pre-condicao tecnica: o Hermes Desktop deve reiniciar manualmente depois da atualizacao de whatsapp_native_send_bridge.py, para que o backend Python carregue o codigo corrigido.

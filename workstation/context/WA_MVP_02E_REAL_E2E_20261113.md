# WA-MVP-02E — Teste real após correção do carregamento do auto-chat

**Pré-condição:** executar em um Hermes Desktop reiniciado após a edição de `workstation/integrations/hermes/whatsapp_native_send_bridge.py` de 13/11/2026. Não reutilizar a sessão de envio que retornou `CHAT_IDENTITY_UNVERIFIED`.

**MISSÃO:** execute UM envio individual real para o meu próprio WhatsApp Web. Esta mensagem autoriza somente o destino e o corpo abaixo. Não peça ONCE, não crie cartão manual, não ofereça escolhas A/B/C.

**recipient_ref:** `{"source":"hermes_local","contact_id":1}`
**expected_recipient_name:** `+55 64 9247-0988 (Você)`
**message (literal):** `WA-MVP-02E QA 20261113 - envio unico do Hermes para o proprio WhatsApp.`

Use a skill `whatsapp-native-operator` e chame `whatsapp_send_message` diretamente com esses três argumentos. O dispatcher gera a TaskRun automaticamente. O executor atual verifica o chat ativo, aguarda até 1 segundo apenas se a identidade ainda não estiver renderizada, digita o texto e clica em Enviar **no máximo uma vez**.

Registre o estado real (`OBSERVED`, `FAILED` ou `UNCERTAIN`), `error_code`, clique 0/1, novo identificador da mensagem, ACK e persistência. DOM `OBSERVED` não equivale a confirmação independente de servidor. Não repita operações `UNCERTAIN`, não reutilize textos/operações antigos e não faça envio alternativo por shell/CDP. Se houver falha pré-clique, reporte o defeito específico sem pedir nova autorização.

Critério de aceite: uma única mensagem nova no auto-chat correto e um registro durável coerente; nenhum segundo clique, campanha ou lote.
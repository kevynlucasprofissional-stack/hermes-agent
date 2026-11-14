# WA-OPC-011 — Reteste após correção de CHAT_HEADER_NOT_UNIQUE

**Destinatário autorizado:** meu próprio WhatsApp, conversa "Você". Referência interna já conhecida: `{"source":"hermes_local","contact_id":1}`.

Execute **um único envio individual real** usando diretamente a ferramenta registrada `whatsapp_send_message`, sem criar Kanban manual e sem chamar `work_execute`. A TaskRun deve ser criada automaticamente pelo host.

Parâmetros exatos:

```json
{
  "recipient_ref": {"source": "hermes_local", "contact_id": 1},
  "expected_recipient_name": "Você",
  "message": "WA-OPC-011 | reteste header | 12/11/2026 | caso-A72E"
}
```

Não procure outro contato nem use números brutos. Não solicite cartão de aprovação adicional. O executor deve confirmar o chat de destino no Chromium nativo; se o cabeçalho não trouxer identidade inequívoca, poderá validar o **próprio** auto-chat mediante a linha "Você" com número e o número do destinatário no compositor. Um chat ID explícito e divergente bloqueia o envio.

Execute a tool **uma única vez**. Não repita a chamada após erro, principalmente em estado `UNCERTAIN`, nem use shell/CDP/navegador alternativo para enviar.

Relate em poucas linhas: `state`, `error_code`/`failure_phase`, se houve clique, se existe mensagem nova/recibo e os identificadores da TaskRun criados pelo host. Distinga `OBSERVED` de confirmação independente do servidor. Não divulgue números privados.

# WA-OPC-011 — Teste real do Hermes

Envie agora **uma única mensagem de teste para o MEU PRÓPRIO WhatsApp** conectado, identificado como **Você**, utilizando o executor nativo do Hermes Work.

Chame diretamente a ferramenta registrada `whatsapp_send_message` com estes parâmetros exatos:

```json
{
  "recipient_ref": {"source": "hermes_local", "contact_id": 1},
  "expected_recipient_name": "Você",
  "message": "WA-OPC-011 | QA real | admissão automática TaskRun | 12/11/2026 | teste-7C41"
}
```

O host deve criar/reivindicar a TaskRun automaticamente. **Não crie cartões no Kanban, não chame `work_execute`, não peça aprovação adicional e não use terminal, scripts privados, CDP externo ou navegador alternativo.** Não faça uma investigação preliminar: a referência já foi resolvida pelo cadastro confiável. Não substitua o destino por contatos da ACIRV ou por correspondências semelhantes.

A própria ferramenta deve conferir o destinatário e realizar, no máximo, um clique de envio. Se o navegador ou a identidade não forem verificáveis, pare sem enviar. Se o resultado for `UNCERTAIN`, **não tente novamente**. `OBSERVED` é recibo no DOM, não ACK independente do servidor.

Responda objetivamente com: estado retornado, `error_code`/`failure_phase` se houver, se ocorreu clique, se houve novo ID de mensagem e se a TaskRun foi criada automaticamente. Não afirme entrega sem evidência e não revele número de telefone, caminho do banco ou conteúdo privado de terceiros.

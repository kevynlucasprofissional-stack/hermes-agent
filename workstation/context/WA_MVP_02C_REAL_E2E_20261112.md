# WA-MVP-02C — Teste E2E real de envio individual

Execute agora **um único envio real** pelo WhatsApp Web nativo do Hermes Work. Esta é a autorização explícita para **este destinatário e este texto**, sem segunda aprovação, cartão ONCE, escolha A/B/C ou criação manual de tarefa.

**Destinatário:** minha própria conta WhatsApp, exibida como `+55 64 9247-0988 (Você)`.

**Referência confiável:** `{"source":"hermes_local","contact_id":1}`.

**Nome esperado (exato):** `+55 64 9247-0988 (Você)`.

**Mensagem literal (não altere):**

WA-MVP-02 REAL 20261112 — teste de envio autônomo para meu próprio WhatsApp.

## Execute diretamente

1. Utilize a skill instalada `whatsapp-native-operator` e chame **`whatsapp_send_message` diretamente**, com `recipient_ref`, `expected_recipient_name` e `message` acima. A referência já é conhecida: não repita a busca nem faça preflight de Kanban, logs ou painel.
2. O dispatcher do Hermes deve assumir a TaskRun canônica automaticamente nesta chamada; não exija que eu a crie ou aprove outra vez. Não tente forjar identificadores de sessão ou TaskRun.
3. Deixe o executor nativo conferir o destino, compor o texto e clicar **no máximo uma vez**. A confirmação mínima é a observação de uma mensagem **nova** com destinatário, texto e recibo causal correlatos, mais o registro persistente da operação.
4. Relate em poucas linhas: `OBSERVED`, `FAILED` ou `UNCERTAIN`, código de erro, clique realizado (0/1), nova mensagem observada (sim/não) e registro persistente (sim/não). `OBSERVED` no DOM não significa confirmação independente de entrega no servidor.

**Regras materiais:** nunca reutilize o envio antigo WA-OPC-011 nem a operação de Browser pendente `op_browser_click_58652ca02566`; este teste utiliza texto novo. Não repita uma operação `UNCERTAIN`, não dispare por shell/CDP externo, não faça envio em lote, não limpe logs nem altere dados para simular sucesso. Em falha comprovadamente anterior ao clique, encerre com o defeito objetivo sem pedir decisão ou apresentar opções.

Não responda só com diagnóstico ou plano: execute o envio único pelo fluxo nativo, se tecnicamente viável, e reporte o resultado factual.
# WA-OPC-011 — Pesquisa e solução mínima para recibo causal no WhatsApp Web (12/11/2026)

## Resultado observado

**Um único canário foi enviado ao auto-chat autorizado**, sob `aiControl=true`, BrowserTask/sessionHost existente `20261112_013246_3572a5` e runtime `electron-chromium`. O artefato privado `workstation/dogfood/artifacts/wa-opc011-canary-20261111/causal-self-canary-intent-20261112.json` confirma `click_count=1`, baseline de 6 IDs e `CAUSAL_DOM_RECEIPT_OBSERVED`; a mensagem nova apresentou ID exclusivo, marcador correspondente, autoria própria e estado `read`. A mensagem técnica e os IDs completos não foram exibidos nem gravados em logs de saída. Somente um hash SHA-256 do ID consta no diagnóstico.

**Limite:** isto é um recibo causal da interface, não prova criptográfica nem evento independente do servidor WhatsApp. `can_send=false` e `independently_verified=false` permanecem. O executor de campanhas não foi liberado.

## Defeito de contrato verificado

`workstation/integrations/hermes/whatsapp_browser_executor.py` espera `data-chat-id` no cabeçalho e `data-id`, `data-direction`, `data-recipient-id`, `data-ack` diretamente no `msg-container`. Essa premissa não corresponde ao DOM observado no Chromium desta sessão: ID fica em ancestral `[data-id]:has([data-testid="msg-container"])`; a autoria de textos pode ser extraída de descendente `[data-pre-plain-text]`; o estado de recibo está associado ao ancestral via `[data-testid="msg-meta"] [aria-label]`. As classes antigas `message-in`/`message-out` também não estavam presentes. Concluir `sent=true` usando apenas clique ou mensagem antiga seria falso positivo.

## Solução aplicada e comprovada

1. **Pure gate**: `workstation/integrations/hermes/whatsapp_causal_receipt.py`, função `assess_causal_dom_receipt()`. Exige autor próprio, auto-chat autorizado, clique único confirmado, inventário não ambíguo, marcador novo ausente do baseline, ID hexadecimal inédito e um status `sent/delivered/read` associado à mensagem. Retorna somente dados agregados e **nunca concede permissão para enviar**.
2. **Prova real**: o canário utiliza exclusivamente `browser_snapshot`, `browser_extract_items(mode=inspect)`, `browser_type` e um `browser_click` de envio pelo BrowserTask autenticado. Identidade do próprio contato conferida em três superfícies (linha `você`, compositor e painel), com telefone apenas em memória. Intenção persistida antes do clique, sem retry se resultado for desconhecido. Inspeção pré/pós preservou identidade de `task_id`/`tab_id`/origem.
3. **TDD**: `workstation/tests/test_whatsapp_causal_receipt.py` com cinco casos (positivo, ID antigo/nonce repetido, autor ou ACK inválido, duplicata, ausência de autorização). RED por importação inexistente antes da implementação; GREEN **5/5**. Regressão ampliada de 15 arquivos do Workstation/WhatsApp/BrowserTask: **193 PASS / 0 FAIL**.
4. **Artefatos privados**: script one-shot e intenção em `workstation/dogfood/artifacts/wa-opc011-canary-20261111/` ignorados pelo Git. Não substituir nem repetir a intenção. Sem envio para terceiros, sem mídia e sem escrita no banco ACIRV.

## Pesquisa externa: o que reutilizar e o que evitar

- **Upstream Hermes oficial:** `scripts/whatsapp-bridge/bridge_helpers.js` correlaciona eventos de status com `key.id`, `key.fromMe` e `isOwnSend(key.id)`; `bridge.js` observa `messages.update` e `message-receipt.update`; `outbound_ids.js` contém rastreador limitado dos envios recentes. Este é o padrão correto de **correlação de identidade da operação**, porém usa Baileys/uma sessão separada. Não conectar automaticamente à BrowserTask existente. Fontes: https://github.com/NousResearch/hermes-agent/blob/main/scripts/whatsapp-bridge/bridge_helpers.js ; https://github.com/NousResearch/hermes-agent/blob/main/scripts/whatsapp-bridge/bridge.js ; https://github.com/NousResearch/hermes-agent/blob/main/scripts/whatsapp-bridge/outbound_ids.js
- **whatsapp-web.js:** `message_ack` e `Message.ack` mostram como eventos são ligados a objetos de mensagem. Porém a implementação manipula o estado interno do WhatsApp Web, fora do transporte DOM permitido nesta missão. Fonte: https://github.com/wwebjs/whatsapp-web.js/blob/main/src/Client.js
- **WPPConnect/WA-JS:** fornece outro canal de automação, mas é dependente de APIs internas/instalação que não atendem à restrição de preservar a sessão BrowserTask. Fonte: https://github.com/wppconnect-team/wa-js
- **Exemplos de DOM:** projetos públicos recomendam alternativas de botão `aria-label`, `data-testid` e `data-icon`, porém são sensíveis às mudanças do frontend; por isso o script validou a referência real antes do clique. Fonte: https://github.com/AngBan2x/whatsapp-playwright-bot
- **Referências locais** `referências/02-Browser-Automacao-Web`: `aaronlab--browsertrace` (traces/replay), `EricFinland--witness` (diferenças de DOM e diagnóstico por passo), `VasuBansal7576--driftlock` (evidência antes de adaptação e HOLD por insuficiência). Nenhuma delas é um adaptador pronto de ACK do WhatsApp; reutilizou-se o princípio de evidência por etapa, sem incorporar outro browser/driver.

## Próximo gate do produto (não resolvido pelo canário)

Para liberar mensagens a destinatários arbitrários no executor, **separadamente**: (a) vincular telefone resolvido pelo Hermes/TaskRun a contato e compositor nativos e à aprovação do usuário, (b) trocar a lógica obsoleta `_outbound_messages()` e `_verified_chat_identity()` por inspeção nativa orientada a IDs ancestrais, autoria e status associado, (c) capturar baseline no mesmo task/tab antes do clique, registrar uma intenção durável, observar mensagem/ACK novos sem reenvio em dúvida, (d) testar destinatário errado, mudanças de chat, colisões, assincronia e falhas de persistência, (e) provar um envio real aprovado a destinatário de teste antes de campanhas. **Não relaxar o verificador atual enquanto esse gate não for concluído.**

---
name: whatsapp-web-ops
description: Native WhatsApp Web operations through the Hermes Browser; minimal path for individual sends.
version: 1.1.1
native: true
auto_update: true
site_map: site-ops/maps/whatsapp-web.json
operations_script: site-ops/scripts/site-ops/whatsapp-web.mjs
deep_map_script: site-ops/scripts/site-deep-map.mjs
---

# WhatsApp Web — operações nativas

## Envio individual

Use diretamente a ferramenta registrada whatsapp_send_message com a referência exata do destinatário, o nome literal solicitado e o texto literal.

- Não leia o mapa do site antes de um envio normal.
- Não execute varredura de autoria, painel de contato, health check manual, inspeção de abas ou preflight duplicado.
- A ferramenta usa o TaskRun existente, quando já houver; caso contrário, usa a sessão Hermes e o ID da chamada. Confirma o ID da conversa, clica em Enviar uma vez e lê a nova mensagem.
- Não exige criar cartão Kanban nem obter aprovação adicional.
- FAILED antes do envio significa que nenhum clique foi executado; corrija o defeito técnico.
- UNCERTAIN após o clique nunca deve ser repetido automaticamente.

## Leitura e diagnóstico

- A operação legada get-unread-count continua somente leitura.
- Use o mapa e o deep-map apenas quando a ferramenta nativa falhar por seletor ausente ou incompatível, não como etapa de rotina.
- Não use scripts de disparo, clipboard, CDP externo ou sessão concorrente para enviar mensagens.
- Não altere campanhas ou lotes ao executar um envio individual.

## Arquitetura

O Hermes Browser nativo é a única via de interação. O resultado do clique inclui um snapshot atualizado; a ferramenta de WhatsApp verifica o estado específico da mensagem. A admissão do Browser continua protegendo contra repetição de operações cujo efeito permaneça incerto.

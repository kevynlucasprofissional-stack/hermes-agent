## HW-20261026-PLAN — Gaps levantados por inspeção de leitura (NOT RELEASE)

- **HW-UPLOAD-01 / REVIEW REQUIRED:** `browser_file_upload` executa `DOM.setFileInputFiles` enquanto não apareceu no Set de ações `mutating` observado em `executeControlRequest`. Necessário confirmar todos os guards e ajustar admission/receipt com testes Electron; também validar origem/arquivo real e não expor caminho absoluto.
- **HW-TRELLO-ACTIVITY-01 / NOT IMPLEMENTED:** cliente REST `TrelloClient` possui leitura de cartões/listas, mas journal paginado de `/actions` e checkpoint transacional não foram identificados; não alegar histórico completo.
- **HW-PAGE-MONITOR-01 / NOT IMPLEMENTED:** `MutationObserver` atual atende cache/learning; não equivale a monitor persistente por aba com regras/teardown/restart.
- **HW-EVENT-OUTBOX-01 / NOT IMPLEMENTED:** `SystemEventPipeline` mantém janela recente in-memory; despacho Cron por eventos existe, mas outbox com identidade persistente de eventos de negócio não foi verificada.
- **HW-WA-SEMANTIC-01 / NOT IMPLEMENTED:** tabelas factuais de mensagens não equivalem a memória semântica e extração de demanda por contato.
- **PRÉ-EXISTENTES INALTERADOS:** `WA-M3-01` e HLM-M3 replay continuam HOLD. Helpers isolados testados em sandbox não alteram status de release.

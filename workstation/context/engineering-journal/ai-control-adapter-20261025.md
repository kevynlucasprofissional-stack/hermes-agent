# Engineering Journal — AC-ADAPTER / 2026-10-25

Author: ChatGPT, planejamento e código de referência; não integra runtime. Branch main, HEAD no início f1d5ab2f030e940ed4571371b0de45a21a009c9e. Verificado em C:\Github\hermes-agent usando Controle Windows. WIP no checkout preexistia, incluindo arquivos de WhatsApp e docs centrais. Nenhum arquivo de produção, lockfile, branch ou instância Electron foi modificado nesta missão.

## Observado no código
- ai-control-bridge.ts: HTTP status/evaluate, token efêmero, host loopback e operação de toggle/revogação. main.ts vincula a webContents principal; preload/AiControlBadge apenas refletem estado; cliente ai-control-client.mjs e hermes-nav.mjs funcionaram anteriormente no Desktop vivo (status, DOM read, clique reversível).
- /evaluate aceita strings arbitrárias mesmo quando os demais endpoints são tipados. Timeout Promise.race não cancela side-effects já disparados. Falha de compatibilidade com Playwright.connectOverCDP em /json/version é legítima.
- Browser nativo já tem mecanismo próprio de BrowserTask, snapshots, ações/leases/admissão e capturePage. Não duplicar; não transferir grant do Desktop ao Browser guest automaticamente.
- MCP SDK Node não aparecia resolvível; Playwright-core já instalado. Preferir SDK oficial existente ou justificar pequeno pin se necessário, sem instalação nesta fase.

## Decisões
- AC-1 contrato/autoridade e controles P0, deixando /evaluate legado explicitamente identificado até migração completa.
- AC-2 interações/percepção tipadas nativas para a UI de Hermes.
- AC-3 SDK e CLI Playwright-like sem afirmar implementação do protocolo CDP; desligar eval irrestrito por padrão.
- AC-4 MCP stdio + E2E real, documentação e controle da integração.
- Não adotar CDP aberto ou proxy CDP como caminho principal; não alterar inicializador saudável.

## Artefatos efetivamente criados
- ../AI_CONTROL_ADAPTER_ARCHITECTURE_2026-10-25.md — decisão, ameaças, boundaries, gates e mapa de arquivos.
- ../AI_CONTROL_ADAPTER_IMPLEMENTER_PROMPTS_2026-10-25.md — 4 prompts completos em ordem de dependência, com paths, métodos e testes.
- ../AI_CONTROL_ADAPTER_CANONICAL_INSERTS_2026-10-25.md — blocos prontos para inserir em ROADMAP.md, CURRENT.md, HERMES_WORKSTATION_INTELLIGENCE.md, DECISIONS.md, KNOWN_ISSUES.md, README.md, quando claims forem liberados.
- ../ai-control-adapter-reference/ai-control-operations.mjs e .test.mjs — validador de shape puro (sem autoridade e sem integrações em produção).

## Evidência de teste local nesta missão
Executado no Windows: node --test workstation/context/ai-control-adapter-reference/ai-control-operations.test.mjs => 3 testes PASS, exit 0. Isso valida apenas referência de contrato. Não foi rodado Electron nativo ou E2E nesta missão e nada disso pode ser anunciado como qualificação.

## Bloqueio de escrita canônica
O agente chatgpt-whatsapp-m3 tinha claim ACTIVE abrangendo workstation/roadmap.md, workstation/context/current_state.md, decisions.md, engineering-journal/current.md, hermes_workstation_intelligence.md, known_issues.md e readme.md. No Windows o case-insensitive equivale aos paths maiúsculos. Por isso não os editei; preparadas inserções prontas com status PENDING-INTEGRATION. Não forçar claim nem remover reserva por heartbeat.

## Próxima operação
Pedir ao implementador AC-1 que leia arquitetura + prompts, revalide main/claims/Stage A, adquira claims exatos do runtime, escreva primeiro testes RED, aplique validador TS e rotas tipadas com binding real e reporte GREEN. Integrador insere blocos canônicos após liberação das reservas e revisa a base corrente. Nenhum commit/push/merge foi autorizado ou realizado.

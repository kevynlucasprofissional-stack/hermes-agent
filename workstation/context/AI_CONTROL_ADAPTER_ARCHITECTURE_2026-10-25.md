# AC-ADAPTER — Arquitetura e evidência local (25/10/2026)

ESTADO: decisão técnica e código de referência; não é runtime implementado, merge aprovado ou release. Branch canônica main; HEAD observado f1d5ab2f030e940ed4571371b0de45a21a009c9e. Revalidar antes de escrever código.

## Evidências já comprovadas

- Hermes Electron real PID 25108 com AI Control ativo: node apps/desktop/scripts/hermes-nav.mjs status passou, bem como eval.mjs lendo título e URL e clique reversível num botão temporário invisível.
- Ponte em 127.0.0.1 porta efêmera 55365 naquele teste. Descoberta via APPDATA/Hermes/ai-control-bridge.json; nunca fixar porta/PID/token.
- HTTP sem bearer: 401; origin forjado com token: 401; bearer correto: 200; Chromium CDP 9222 e 9333 fechados.
- Chromium.connectOverCDP direto na ponte falhou com HTTP 401 em /json/version, como esperado; endpoint atual NÃO é servidor CDP.
- Fonte atual: apps/desktop/electron/ai-control-bridge.ts exporta createAiControlBridge, opera /status e /evaluate (JavaScript livre); main.ts autoriza Ctrl+Shift+A, preload.ts e AiControlBadge.tsx mostram estado; scripts/ai-control-client.mjs descobre a ponte; dev-cdp.ts mantém Chromium CDP off sem opt-in.
- Infra existente independente: workstation-browser-runtime.ts possui BrowserTask, snapshots, capturePage, ações estruturadas, lease humano e receipts. Não duplicar nem contornar este executor e não tornar o guest parte do grant do renderer Desktop sem contrato específico.
- playwright-core já instalado; @modelcontextprotocol/sdk NÃO resolvia no Node root na verificação anterior, requer revalidação. Não instalar sem gate.

## Decisão arquitetural

AI Control nativo é a autoridade para controlar a INTERFACE DESKTOP de Hermes. Adicionar ações tipadas e percepção usando a MESMA ponte autenticada. Um cliente local fornece interface estilo Playwright (locator, click, fill, press, waitFor, snapshot, screenshot), SEM fingir ser um Browser/Playwright CDP real. O adaptador MCP stdio é uma camada fina posterior. Manter modo manual de Chromium CDP somente com opt-in explícito em desenvolvimento; não fixar 9222 nem converter /json/version em bypass.

Fluxo canônico:
Agente CLI/MCP -> ai-control-client.mjs (descoberta/token) -> AI Control loopback (autenticação/cotas/grant) -> operações tipadas -> webContents do renderer principal -> observação ou resultado verificado.

Escopo inicial exclusivamente surface=desktop, sem controle implícito dos WebContentsViews de sites externos. Browser guest continua sob seu próprio contrato de admissão e controle. O token armazenado em arquivo legível ao mesmo usuário OS NÃO autentica individualmente cada agente; documentar esta ameaça residual. A sessão não deve imprimir token.

## Contrato AC-V1 sugerido

Operações de leitura: status, snapshot, locate, waitFor, screenshot.
Operações com efeitos: click, fill, press.
Alvos: kind=css, role, label, text, testId; value string estrita. Snapshot retorna metadados opacos documentId + grantId emitidos pelo PROCESSO PRINCIPAL, não pelo agente. Efeitos incluem expected:{documentId,grantId}, com rechecagem server-side imediatamente antes do efeito. A presença desses IDs fornecidos pelo cliente não concede autoridade; compare com estado/lease gerados internamente.

Código de referência real criado em workstation/context/ai-control-adapter-reference/ai-control-operations.mjs e teste .test.mjs. Valida formato, op, tamanho, alvo e campos proibidos. NÃO valida autorização e NÃO é código integrado em Electron. Implementador deve criar versão TS no runtime com testes RED primeiro e preservar flexibilidade para alternativa superior.

Interações: localizar no DOM somente do renderer principal; não usar apenas element.click e KeyboardEvent sintéticos como prova de input real. Usar webContents.sendInputEvent para clique/tecla quando apropriado, verificando geometria, foco, unicidade, origem, época do documento e ausência de password/sensíveis. Screenshot: webContents.capturePage do desktop, payload limitado e redigido; não persistir imagem por padrão. WaitFor: polling bounded/cancelável, sem busy loop e sem prolongar revogação.

## P0 inegociável e riscos concretos

1. A rota /evaluate atual executa JS arbitrário: SOMENTE adicionar /operation não resolve segurança. Desabilitar/restringir a rota legado antes de declarar operação tipada como segura; manter manual --unsafe-dev-eval somente com opt-in explícito e teste de rejeição em modo padrão. Não silenciar scripts antigos sem atualizar seus consumidores.
2. Promise.race com timeout não interrompe executeJavaScript já iniciado. Reavaliar fencing e concorrência; evitar payload JS de origem não confiável; revogação impede admissão e publicação tardia, mas não reverte efeito já emitido.
3. Fencing por token, AI Control ligado, PID/owner, webContents/document epoch, grant, frame e origem. Reload/logout/toggle/fechamento invalidam binding. Concurrency/queue bounded, requests/capture/result size bounded, sem tokens, cookies, senhas, corpos privados nos logs.
4. Mutação com locator ambíguo falha fechado; document epoch mudou => rejeitar; clique com efeito potencialmente irreversível NÃO é liberado só por AI Control. Reusar approval/BrowserTask/TaskRun/receipt e sinal UNCERTAIN para efeitos reais, sem envios de WhatsApp ou publicação em testes.
5. CLI nunca cair silenciosamente de bridge inválida para CDP 9222 ou app errado.

## Sequência 80/20

AC-1 P0: endurecer autorização e contrato tipado, fechar caminho JS irrestrito por padrão, baseline RED e resultado GREEN.
AC-2 P1: resolver locator/esperas/input real/snapshot/screenshot limitado na janela principal.
AC-3 P1: SDK/CLI Playwright-like sobre operações tipadas, migrar ferramentas atuais e skill do Antigravity, preservar debug manual explícito.
AC-4 P2: MCP stdio, qualificação nativa de ponta a ponta e documentação/integrador; sem proxy CDP.

## Gates

Ler AGENTS.md, workstation/AGENTS.md, workstation/context/README.md, DEVELOPMENT_GATES.md e AGENT_COLLABORATION_PROTOCOL.md atuais. main é canônica, branch MVP antiga é histórica. Nenhuma dispensa de H-079/Stage A foi concedida automaticamente para esta frente. Preservar claims ativos, WIP, approvals, sandbox, cache, launcher e integrações WhatsApp. Não executar commit, stage ou push sem integrador.

Critérios nativos finais: AI Control off sem endpoint; on com bearer; sem token 401; token antigo 401; Origin não confiável 401; operações tipadas + readback; screenshot em memória; ligação com documento; revogação durante operação; reload invalida; Browser guest não se torna alvo; CDP 9222 ausente; Vite/launcher/doctor saudáveis; integridade de testes e CI claramente qualificada.

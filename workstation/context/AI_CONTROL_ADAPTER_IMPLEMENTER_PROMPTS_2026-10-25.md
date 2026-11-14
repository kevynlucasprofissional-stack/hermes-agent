# AC-V1 — Prompts operacionais 80/20 (25/10/2026)

Repositório C:\Github\hermes-agent, Windows/PowerShell, branch main; HEAD observado f1d5ab2f030e940ed4571371b0de45a21a009c9e. Estes prompts são AUTOSSUFICIENTES; revalidar o HEAD, claims, status e contratos, sem presumir que o snapshot continua vigente. A ordem é obrigatória AC1 -> AC2 -> AC3 -> AC4. Não criar branch/worktree por padrão, não fazer commit/push/stage sem integrador; preservar WIP e owners.

Arquivos de preparação:
- workstation/context/AI_CONTROL_ADAPTER_ARCHITECTURE_2026-10-25.md
- workstation/context/ai-control-adapter-reference/ai-control-operations.mjs (código de referência já executável, não integrado)
- workstation/context/ai-control-adapter-reference/ai-control-operations.test.mjs (3/3 PASS no snapshot)
- workstation/context/AI_CONTROL_ADAPTER_CANONICAL_INSERTS_2026-10-25.md (seams de documentação protegidos)
- workstation/context/engineering-journal/ai-control-adapter-20261025.md

## PROMPT AC-1 — P0: autoridade, isolamento, contrato e RED/GREEN

MISSÃO. Converta a ponte AI Control existente para admitir operações tipadas sem ampliar o poder do agente. Primeiro preserve a autenticação/descoberta já validada; implemente binding de documento e grant de mutação no MAIN do Electron; adicione contrato v1. Não implemente novo browser nem MCP.

PRE-FLIGHT. No Windows acesse C:\Github\hermes-agent; leia AGENTS.md, workstation/AGENTS.md, workstation/context/README.md, DEVELOPMENT_GATES.md, AGENT_COLLABORATION_PROTOCOL.md e AI_CONTROL_ADAPTER_ARCHITECTURE_2026-10-25.md. Confirme git branch --show-current, HEAD, status --short, claims atuais e preflight upstream-first/Stage A aplicável. Se gate não estiver qualificado, siga a autorização de desenvolvimento local que realmente existir; não invente waiver. Solicite claim exato em apps/desktop/electron/ai-control-bridge.ts, ai-control-bridge.test.ts, main.ts e novos arquivos ai-control-operations.ts/test.ts. Não tocar nos arquivos de WhatsApp ou Browser runtime de outro agente.

PONTOS EXATOS.
1) Em apps/desktop/electron/ai-control-bridge.ts, manter createAiControlBridge, enable/disable/toggle, 127.0.0.1 dinâmico, timingSafeEqual, descoberta com token efêmero e GET /status. Adicionar handler POST /operation apenas depois de autenticação e limites; nunca criar outra ponte ou DB. Conectar operação a callback tipado na opção createAiControlBridge; validar shape logo após parse do body. Migrar/adaptar a referência ai-control-adapter-reference/ai-control-operations.mjs para TS em apps/desktop/electron/ai-control-operations.ts (interface/protocolo como contrato, NÃO autoridade).
2) No main.ts onde const aiControlBridge é criado (~1964 no snapshot), ligar os callbacks ao webContents principal obtido de mainWindow; exigir mesma instância, URL/isolamento válido, grant criado no Electron enquanto Ctrl+Shift+A está ativo, documentId vinculado ao reload/navegação/frame; revogar ao desligar/fechar/recarregar. Retornar documento e grant apenas por resposta autenticada de observação, nunca por argumento não validado da página.
3) Em ai-control-bridge.ts, tornar o /evaluate legado transitoriamente identificado como UNSAFE/DEV-ONLY (compatibilidade com scripts antigos até AC-3). Não afirmar segurança de operações tipadas enquanto /evaluate arbitrário estiver habilitado. Documentar a dependência e o gate obrigatório de fechamento em AC-3.
4) Evitar Promise.race entendido como cancelamento de JavaScript: timeout apenas deixa de aguardar. Não aceitar JS livre através de /operation, nem serializar objects extensos/credentials.

TESTES RED antes da implementação, GREEN depois: auth 401; host/Origin forjado 401; body inválido; payload oversized; operação/escopo inesperado; sem grant, grant stale, documentId antigo, mainWindow trocada, reload/toggle off/fechamento, operação in-flight revogada (sem publicação tardia nem novo efeito após fence), HTTP status coerentes. Testes devem usar servidor real local e Electron test fixture onde adequado. node --test no contrato de referência e vitest electron no real. Typecheck Electron e git diff --check. Não finalizar só com mocks.

SAÍDA. Implementação nos arquivos reais, evidência exata (pass/fail), status de /evaluate legado marcado PENDENTE até AC-3, handoff com paths e revisão de autorização. Quando qualquer gate bloquear código, NÃO contorne; prepare patch concreto e prompt de continuação.

## PROMPT AC-2 — P1: localizadores e interações nativas + percepção

MISSÃO. Sobre o contrato tipado AC-1, implementar o conjunto mínimo de automação de UI do renderer Desktop: snapshot, locate, waitFor, screenshot, click, fill, press. Reusar webContents/BrowserWindow e a autorização já existente. Não tocar WebContentsView de terceiros nem substituir Workstation Browser.

PRE-FLIGHT. Revalidar Git/main/claims/gates e ler os mesmos documentos obrigatórios + relatório AC-1. Só iniciar se AC-1 passou contratos auth/document/grant (ou fazer correção localizada desses contratos). Claim exato: ai-control-operations.ts, ai-control-bridge.ts, main.ts (se necessário) e testes novos; não editar workspaces de outros agentes.

CÓDIGO/SEAMS.
- Criar apps/desktop/electron/ai-control-desktop-actions.ts e .test.ts; interface dependência injetável: getCurrentDesktopContents(): Electron.WebContents, checkBinding, now, capture.
- Resolver target.kind em DOM do renderer PRINCIPAL com script CONSTRUÍDO PELO CÓDIGO TRUSTED e parâmetros escapados por JSON.stringify; não concatenar JS fornecido pelo agente. Suportar CSS, role, label, text, testId com exact e find unique; para mutações exigir exatamente um elemento visível/estável/habilitado, senão erro AMBIGUOUS_TARGET/NOT_FOUND/NOT_INTERACTABLE.
- Para click: resolver retângulo em coordenadas CSS no renderer, conferir navegação/binding e chamar wc.sendInputEvent mouseMove/mouseDown/mouseUp pelo main. Não tratar Element.click() como input físico. Para press usar keyDown/char/keyUp com allowlist; para fill usar focus + input confiável compatível e verificar valor, recusando type=password, campos com autocomplete sensível, iframes não autorizados e elementos disabled. Se desenho nativo alternativo for superior, justificar prova real.
- Para snapshot: árvore limitada de role, accessible name, texto sanitizado e geometria visível; nada de cookies/headers/valores de formulário; cap número de nós e bytes de resposta. Retornar documentId/grantId onde autorizados. Para screenshot: wc.capturePage() -> PNG em memória, tamanho máximo fixo, sem gravar em disco nem vazar base64 para logs. Para waitFor: polling limitado com timeout e invalidação ao desativar/reload.
- Padrão de resultado: {ok,op,data?,documentId?,error_code?,retryable?}; sem prometer idempotência para clique. Toda action revalida grant/token/current document no ponto da emissão.

GATES. RED/GREEN para ambiguidades, docs obsoletos, campos sensíveis, frame externo, screenshot excessiva, texto longo, timeout, click result readback, revogação, substituição de webContents. Fixture Electron sandbox com DOM controlado; e apenas ação não mutante/reversível sobre app real depois de grant humano. Vitest, tsc, npm script checks. Handoff AC-3 com API e exemplos precisos. Nenhum envio/publicação/WhatsApp real.

## PROMPT AC-3 — P1: SDK, ferramentas CLI, migração e fechamento do legado

MISSÃO. Criar um SDK local simples estilo Playwright sobre as operações do AC-2, migrar consumidores para o contrato tipado e DESLIGAR a rota /evaluate arbitrária no fluxo padrão. Não fingir compatibilidade com chromium.connectOverCDP.

PRE-FLIGHT. Leia docs e relatórios AC-1/2, revalide HEAD/claims/gates. Claim: apps/desktop/scripts/ai-control-client.mjs, ai-control-client.test.mjs, hermes-nav.mjs, eval.mjs, eval-batch.mjs, hermes-deep-map.mjs, interactive-tour.mjs, check-browser-status.mjs e scripts adicionais que realmente importam connectAiControl; skill do Antigravity no caminho local ~/.gemini/config/skills/hermes-work-control/SKILL.md, observando que fica fora do Git. Claim ai-control-bridge.ts/test.ts para fechamento do endpoint. Nenhum arquivo de site-ops ou outro agente.

CONTRATO SDK a implementar no ai-control-client.mjs ou módulo adjacente:
connectAiControl() -> client.status(), snapshot(), locator({kind,value,exact}).count()/click()/fill()/press(), waitFor({target,timeoutMs}), screenshot(), close(); usar request /operation com grant/document obtidos do main, não fabricar. A API é PLAYWRIGHT-LIKE, não um Browser/Playwright real.
Clientes CLI: status/read/tour/goto/click usarem operação tipada; scripts de avaliação livre deverão receber erro explícito orientando API tipada por padrão. Se debug livre for imprescindível, modo --unsafe-dev-eval deve exigir opt-in explícito de desenvolvedor no processo principal, nunca concedido só por query ou atributo do cliente; sem fallback oculto para 9222 ou perfil errado.
Revisar consumidores exatos com rg -n 'connectAiControl|/evaluate|HERMES_DESKTOP_CDP_PORT' apps/desktop/scripts e atualizar cada um com migração segura ou descontinuação documentada. Skill deve indicar bridge dinâmica, limites de permissão, exemplos claros, e especificar que connectOverCDP só funciona com debug manual explícito e diferente.

TESTES. JS node --test para SDK, RPC revocation, token stale, erro estruturado, consumidores com stub; Electron real para snapshot/read/screenshot e click reversível; npm typecheck, vitest suites e smoke do launcher sem reinstalar deps; CDP off. Critério P0: grep/inspeção prova que rota /evaluate livre não fica habilitada por padrão; testes provam não aceitar script remoto. Preserve fake/test runners existentes que explicitamente precisem de modo dev. Documentar que não houve paridade total CDP e que alterações privilegiadas precisam de aprovação própria.

## PROMPT AC-4 — P2: MCP stdio fino, qualificação integrada e integração

MISSÃO. Disponibilizar a capacidade já comprovada em AC-1..3 para Antigravity e demais agentes via MCP stdio, sem executor nem HTTP público extra. Encerrar o MVP somente com evidência end-to-end real e integração coordenada.

PRE-FLIGHT. HEAD, claim, stages, owner e testes. Revalidar disponibilidade de @modelcontextprotocol/sdk e Python mcp local. Preferir SDK oficial REUTILIZADO; se faltar, justificar dependência pinned e lockfile com integrador; não instalar pacote às cegas nem implementar proxy CDP inteiro.
Código proposto: apps/desktop/scripts/hermes-ai-control-mcp.mjs e teste .test.mjs. Inicializar MCP Server stdio (SDK escolhido), declarar ferramentas hermes_status, hermes_snapshot, hermes_locator, hermes_click, hermes_fill, hermes_press, hermes_wait, hermes_screenshot (esta com resposta image adequada ao cliente). Cada ferramenta chama cliente tipado AC-3, revalida auth/epoch/grant; não transforma argumentos em JS. stdout SOMENTE protocolo JSON-RPC, logs redigidos em stderr. Configurar conexão local em skill Antigravity, com comando Node e caminho absoluto sem token no JSON. Nenhuma disponibilidade se AI Control off.
Qualificação: teste de protocolo MCP com cliente real, cenário off/on/off, invalid token, relay cross-process, screenshot redigida, UI com carregamento/reload, documento obsoleto, input reversível, mutex/backpressure, ausência de CDN e CDP 9222; test Electron Windows com aplicação real e usuário/consentimento quando apropriado; manter browser guest protegido. Testes específicos Node/Vitest/tsc mais regressões adjacentes. Segurança: registrar risco de outros processos do mesmo usuário obterem token do arquivo, e não afirmar sandbox/capability perfeita.
Integração: atualizar docs canônicos ROADMAP.md, engineering-journal/CURRENT.md, HERMES_WORKSTATION_INTELLIGENCE.md, DECISIONS.md e KNOWN_ISSUES.md usando arquivo AI_CONTROL_ADAPTER_CANONICAL_INSERTS_2026-10-25.md, mas somente após claims liberados e com integrador; não sobrescrever trabalho WhatsApp. Não commitar/stage/push sem autorização. Relatório final: paths, comando e contagem de testes, screenshot de fixture sem dados reais, logs saneados, gates, limitações. Se nenhum cliente MCP nativo for verificável, marcar NOT QUALIFIED e fornecer prompt de retomada.

## Política comum obrigatória

A IA implementadora é analista crítica e engenheira: confronta recomendações com código vivo, corrige escolhas ruins justificadamente, mas NÃO reinvestiga genericamente, não reconstrói browser/DB/TaskRun, não enfraquece sandbox/leasing, não cria branch por reflexo e não encerra em mera análise quando as operações estão permitidas. Nenhuma alteração na main por um agente deve atropelar worktree/claims de outro. Ordem AC1..AC4. Se tarefa interrompida, entregar PROMPT DE RETOMADA autossuficiente com HEAD, claim, RED/GREEN, arquivos e próxima operação exata.

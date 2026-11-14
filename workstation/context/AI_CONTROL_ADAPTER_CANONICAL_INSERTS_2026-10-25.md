# AC-ADAPTER — Inserções prontas para documentação canônica (25/10/2026)

STATUS: patches de documentação preparados, ainda NÃO integrados nas fontes canônicas. No momento da preparação os arquivos ROADMAP.md, engineering-journal/CURRENT.md, HERMES_WORKSTATION_INTELLIGENCE.md, DECISIONS.md, KNOWN_ISSUES.md e README.md têm alterações não commitadas de WhatsApp M3 e estão reservados pelo agente chatgpt-whatsapp-m3. Não editar nem substituir esses arquivos enquanto a reserva estiver ativa. Integrador deve adquirir claim/handoff, fazer inserção cirúrgica no topo preservando o restante, sem tocar em entradas WA.

Revalidar branch/HEAD/status/claims antes de cada inserção. Local canônico C:\Github\hermes-agent.

## 1) workstation/ROADMAP.md — inserir após o título e antes dos tópicos atuais

### AC-V1 — Automação tipada sobre AI Control nativo (2026-10-25; PLAN_ONLY)
AI Control Electron está implementado para controle do renderer Desktop: modo Ctrl+Shift+A, ponte HTTP loopback autenticada, porta/token efêmeros, status e avaliação JS livre; captura de DOM/click reversível e segurança HTTP foram validadas no Hermes real. Não é CDP: Playwright.connectOverCDP falha legitimamente (401 no /json/version). Roadmap AC-1 P0: binding de autorização/documento, operação tipada e fechamento seguro do evaluate genérico; AC-2 P1: locator/click/fill/press/waitFor/snapshot/screenshot nativos para a UI principal; AC-3 P1: SDK/CLI e Antigravity migrados e legado JS livre off por padrão; AC-4 P2: MCP stdio e E2E nativo. Sem duplicar BrowserTask, engine Chrome/CDP nem executor de efeitos. Nenhuma missão AC-1..AC-4 está implementada/released. [Arquitetura](context/AI_CONTROL_ADAPTER_ARCHITECTURE_2026-10-25.md) e [prompts](context/AI_CONTROL_ADAPTER_IMPLEMENTER_PROMPTS_2026-10-25.md).

## 2) workstation/context/engineering-journal/CURRENT.md — inserir após o título

### 2026-10-25 — AI Control / adaptador Playwright-like, preparação sem runtime
Inspecionados HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e, main e claims. AI Control real já confirmado: PID 25108 (histórico), status/avaliação funcional, autenticação 401/200, /json/version CDP incompatível por protocolo e sem CDP 9222 padrão. Arquivo ai-control-bridge.ts executa /evaluate livre no renderer principal — risco remanescente; Promise.race(timeout) não interrompe código em andamento. Planejadas AC1 autorização e fence, AC2 ações e percepção nativas, AC3 SDK/CLI e retirada do JS genérico, AC4 MCP e E2E. Referência pura em context/ai-control-adapter-reference/ai-control-operations.mjs, node --test 3/3 PASS; não runtime. Contexto e prompts em AI_CONTROL_ADAPTER_*. Fonte canônica não editada por claim de WhatsApp; integração pendente. Não declarar tests de release.

## 3) workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md — inserir após o título

### 2026-10-25 — AI Control como ponte de automação do Desktop, não CDP
Electron main é proprietário da autorização concedida via atalho e controla descoberta por token efêmero, não a variável JS do renderer. Ponte atual disponibiliza eval arbitrário com bearer e deve ser restringida antes de ser chamada de segurança de operações tipadas. CLI/Antigravity já consegue ler e clicar em DOM com AI Control ativo, mas Playwright.connectOverCDP exige protocolo CDP e não aceita a ponte HTTP existente. Não implantar proxy CDP completo, servidor aberto em 9222, outro browser ou memória paralela. Adaptador estilo Playwright executará operações tipadas no renderer principal com document epoch/lease; BrowserWorkstation WebContentsViews permanecem isolados em executor atual e sob seus controles. MCP é apenas invólucro de transporte do cliente já autorizado. Referência e sequência: AI_CONTROL_ADAPTER_ARCHITECTURE_2026-10-25.md.

## 4) workstation/context/DECISIONS.md — inserir após o título

### AC-D1 — Controle nativo tipado e MCP, sem CDP público (DECISÃO; NOT IMPLEMENTED; 2026-10-25)
Aceita a arquitetura AC-1..AC-4: ponte AI Control local existente é a autoridade para UI do Desktop; validar operações tipadas e binding no main; promover read/click/fill/press/wait/snapshot/capture limitados; SDK compatível com conceitos Playwright mas não com protocolo CDP; MCP stdio fino em último estágio. Manter manual CDP opt-in dev, nunca startup padrão, preservar sandbox/launcher, não herdar autorização para Browser guest nem ignorar TaskRun/lease/admission. Prioridade P0 eliminar eval irrestrito por padrão após migração CLI, pois uma rota tipada paralela não remove esse risco. Escopo/aceite em AI_CONTROL_ADAPTER_ARCHITECTURE_2026-10-25.md.

## 5) workstation/context/KNOWN_ISSUES.md — inserir após o título

### AC-KI-001 — Scripts Playwright CDP incompatíveis com ponte AI Control (OPEN / KNOWN)
Evidência: o endpoint HTTP autenticado em porta dinâmica retorna 401 no /json/version do connectOverCDP; essa resposta é esperada, não falha do bootstrap ou CDP interno Workstation. Mitigação atual: usar ai-control-client.mjs/hermes-nav.mjs (status e DOM reversível funcionando no Hermes real). Correção desejada: adaptador estilo Playwright + MCP AC1..AC4. Residual: /evaluate aceita JavaScript arbitrário durante AI Control ativo; não equivale a autorização fina, e o timeout não cancela execução já iniciada. Sem suite end-to-end AC-V1 nem release qualificado.

## 6) workstation/context/README.md — inserir no início do índice operacional

Para qualquer intervenção em AI Control externo/Playwright-like/MCP, leia AI_CONTROL_ADAPTER_ARCHITECTURE_2026-10-25.md, AI_CONTROL_ADAPTER_IMPLEMENTER_PROMPTS_2026-10-25.md e engenharia journal ai-control-adapter-20261025.md DEPOIS dos gates obrigatórios; usar main canônica e respeitar claims atuais. Esta entrada é preparação, não liberação de Stage A.

## Integração segura

Não substituir seções WA existentes, nem atualizar contagens de testes incorretamente, nem alterar o roadmap funcional de WhatsApp. Abrir os documentos, confirmar que heading original permanece, inserir seções depois do primeiro heading (não repetir se já houver versão mais recente), git diff --check com paths exatos; release/integração somente por mantenedor/integrador. A concatenação aqui é proposta de integração, não prova de escrita nos arquivos canônicos.

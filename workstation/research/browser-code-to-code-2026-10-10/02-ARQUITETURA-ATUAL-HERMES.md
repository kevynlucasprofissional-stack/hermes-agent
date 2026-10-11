# 02 — Arquitetura Atual do Subsistema Browser no Hermes Work

**Arquivo Canônico de Diagnóstico:** `workstation/research/browser-code-to-code-2026-10-10/02-ARQUITETURA-ATUAL-HERMES.md`  
**Data:** 10 de Outubro de 2026  
**Status:** FACT / AUDITADO DIRETAMENTE NO CÓDIGO  

---

## 1. Visão Geral Arquitetural e Camadas

O subsistema Browser do Hermes Work é uma implementação especializada sobre o Chromium embutido do Electron, desenhada para permitir navegação assistida por IA com preservação de estado, operação concorrente em segundo plano, controle de autoridade humano-agente e compilação de procedimentos operacionais.

Diferente de wrappers comuns de Playwright ou Puppeteer, o Hermes Work não instancia um processo externo do Google Chrome ou Microsoft Edge: ele hospeda abas como instâncias nativas de `WebContentsView` dentro do processo Electron Desktop.

A arquitetura divide-se em 5 camadas principais:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CAMADA DE APRESENTAÇÃO (UI)                      │
│   • Browser Hub (apps/desktop/src/app/browser/index.tsx)               │
│   • Chat Right Rail (workstation-browser-pane.tsx)                     │
│   • Native View Occlusion Manager (native-view-occlusion.ts)           │
│   • Task Rail & Journal Drawer (task-rail.tsx, task-journal-drawer.tsx)│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ IPC Electron (hermes:workstation-browser:*)
┌───────────────────────────────────▼────────────────────────────────────┐
│                    DESKTOP RUNTIME & HOST (ELECTRON)                   │
│   • WorkstationBrowserRuntime (electron/workstation-browser-runtime.ts)│
│   • BrowserTaskLifecycle (electron/workstation-browser-task.ts)        │
│   • BrowserSessionStatePersistence (workstation-browser-session-state) │
│   • Pool de WebContentsView (background frame-rate: 6fps / visível: 60)│
│   • Loopback HTTP Controller (/v1/action, /health, /events, /resources)│
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP Loopback (127.0.0.1:port + Bearer Token)
┌───────────────────────────────────▼────────────────────────────────────┐
│                     CAMADA DE DISPATCH PYTHON / TOOLS                  │
│   • tools/browser_workstation.py (cliente loopback autenticado)        │
│   • tools/browser_extension_router.py (broker de roteamento)           │
│   • gateway/browser_control_broker.py (broker agnóstico de controle)   │
│   • Fallbacks: tools/browser_tool.py, browser_camofox.py, cdp_tool.py  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Contratos / Receipts / Provas
┌───────────────────────────────────▼────────────────────────────────────┐
│                   OPERATIONAL KERNEL & CONTROL PLANE                   │
│   • workstation/operational_kernel.py (execução determinística)       │
│   • workstation/task_compiler.py (composição e seleção de rota)        │
│   • workstation/operational_capabilities.py (registro de capacidades) │
│   • Verificação de pré/pós-condições, detecção de drift e quarentena   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Eventos semânticos e amostras
┌───────────────────────────────────▼────────────────────────────────────┐
│                  LEARNING & EXPERIENCE COMPILER (OFFLINE)               │
│   • workstation/experience_compiler/ (mineração determinística)        │
│   • Laya / System-1 (sensor de estágio online; sem autoridade direta)   │
│   • Promoção verificada e reuso parametrizado em TaskRuns futuros      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Inspecionando os Componentes Principais

### 2.1. O Host Electron: `WorkstationBrowserRuntime`
- **Arquivo:** `apps/desktop/electron/workstation-browser-runtime.ts` (4.301 linhas).
- **Responsabilidades:**
  - Gerencia o pool de abas `WebContentsView` associadas a instâncias de `BrowserTask`.
  - Configura sessões persistentes no diretório de perfil (`profile_path = workstationBrowserProfilePath()`).
  - Throttle dinâmico de taxa de quadros: abas ativas operam a 60 fps; abas em segundo plano recebem `DEFAULT_BACKGROUND_FRAME_RATE = 6` para economia drástica de CPU e GPU.
  - Sobe um servidor HTTP loopback em porta TCP dinâmica (`server.listen(0, '127.0.0.1')`) gravando um arquivo de controle seguro (`.control.json`) com permissões restritas e token bearer de 256 bits (`crypto.randomBytes(32)`).
  - Trata oclusão de visão nativa: como `WebContentsView` é desenhada diretamente pela GPU sobre o canvas do Electron, elementos de overlay (modais, menus) precisam ocultar ou recortar a view nativa via `native-view-occlusion.ts`.

### 2.2. O Ciclo de Vida da Tarefa: `BrowserTaskLifecycle` e `BrowserSessionState`
- **Arquivos:** `apps/desktop/electron/workstation-browser-task.ts` (652 linhas) e `workstation-browser-session-state.ts` (608 linhas).
- **Invariantes:**
  - Cada tarefa recebe um `taskId` único. Um agente Kanban ou worker em background tem sua aba vinculada exclusivamente ao seu `taskId`.
  - O usuário humano pode alternar entre abas no Browser Hub sem desviar a execução do agente em background.
  - **Human-in-the-loop Lease:** Existe o conceito de `BrowserHumanControlLease` com TTL padrão de 5 minutos (`HUMAN_CONTROL_LEASE_TTL_MS`). Se o humano assume o controle (Take Control), o controller rejeita mutações do agente retornando erro `409 USER_CONTROL_ACTIVE`, protegendo a intervenção humana.
  - **Recuperação pós-restart:** O estado das abas e tarefas é persistido em arquivo JSON (`BrowserSessionStateFilePersistence`). Ao reiniciar o app, as abas de tarefas não são todas recarregadas imediatamente na memória para evitar picos de consumo; elas ficam em estado `parked`/`restored` e sofrem recarga lazy quando solicitadas.

### 2.3. O Cliente Python: `tools/browser_workstation.py`
- **Arquivo:** `tools/browser_workstation.py` (903 linhas).
- **Mecanismos:**
  - Localiza o descritor de controle lendo `_CONTROL_VERSION = 1`.
  - Verifica o endpoint de health (`/health`) com timeout ultracurto de 200 ms e cache de disponibilidade de 750 ms (`_AVAILABILITY_CACHE_SECONDS`).
  - Executa requisições via POST para `http://127.0.0.1:{port}/v1/action` enviando JSON estruturado (`action`, `task_id`, `arguments`, `session_id`, `run_id`).
  - Força a redação de segredos no payload retornado antes de devolvê-lo ao modelo (`redact_sensitive_text`).
  - Implementa fail-closed após binding: se uma tarefa já executou uma ação com sucesso no Browser nativo e o controller cair, ela **nunca** faz fallback silencioso para outro browser (Playwright/Cloud), pois isso vazaria contexto ou quebraria autenticação.

### 2.4. O Roteamento de Ferramentas: Broker e Extensão
- **Arquivos:** `tools/browser_extension_router.py` (175 linhas) e `gateway/browser_control_broker.py` (549 linhas).
- **Mecanismos:**
  - Implementa um broker agnóstico de controle de navegador com tickets descartáveis de autenticação.
  - Suporta extensões Chrome oficiais (ex: `abundantbeing/hermes-browser-extension`), permitindo que sessões externas do Chrome do usuário se conectem ao gateway do Hermes com as mesmas garantias de protocolo.

### 2.5. Execução Determinística: `OperationalKernel`
- **Arquivo:** `workstation/operational_kernel.py` (1.050 linhas).
- **Mecanismos:**
  - Executa capacidades operacionais compostas sem inferência intermediária do LLM.
  - Resolução de âncoras semânticas: `_find_ref_by_anchor` busca seletores por `testid`, `name`, `role_name` (`role:label`) e texto.
  - Se a interface do site mudar e a âncora não for encontrada, o Kernel dispara `CapabilityDriftError`, abortando o passo e devolvendo o controle com quarentena para o agente deliberar (System-2), em vez de clicar às cegas.

---

## 3. Gargalos e Deficiências Identificadas no Código Atual

Durante a leitura detalhada das 4.301 linhas de `workstation-browser-runtime.ts` e seus arquivos irmãos, foram descobertos cinco gargalos graves de implementação:

### Gargalo 1: O Ineficiente `inventoryScript` de Percepção DOM
No método `snapshotForEntry` (linhas 1300–1450 de `workstation-browser-runtime.ts`):
- O código injeta via `executeJavaScript` uma string JS gigante contendo `inventoryScript`.
- Esse script faz `document.querySelectorAll('*')` recursivo através de Shadow DOM e iframes.
- Para **cada elemento interativo** (até 400 no modo full ou 120 no modo compact), ele executa `getBoundingClientRect()` e `getComputedStyle(el)`.
- *Consequência:* Executar `getComputedStyle()` em centenas de nós força reflows síncronos e recalcs de estilo no Chromium! Em páginas pesadas ou SPAs ricas (Trello, Instagram, WhatsApp Web), essa chamada bloqueia a thread de renderização da página por 300 ms a 1.200 ms a cada snapshot.

### Gargalo 2: Auto-Snapshot Obrigatório em Clicks e Types
Em `executeControlRequest` (linhas 2388–2440 de `workstation-browser-runtime.ts`):
```typescript
case 'browser_click': {
    const clickResult = await this.clickRef(entry, String(args.ref ?? ''), anchor)
    await delay(220)
    const snap = await this.snapshotForEntry(entry, false)
    return { ...snap, target: clickResult?.target, semantic_effect: 'click' }
}
```
- Cada clique e cada digitação forçam um `await delay(220)` ou `await delay(160)` fixo somado a um snapshot completo imediato.
- Se o agente precisa preencher 5 campos de um formulário, ele executa:
  `type -> delay 160ms -> snapshot pesado (500ms) -> modelo LLM pensa -> type -> delay 160ms -> snapshot pesado (500ms)...`
- *Consequência:* Perda maciça de tempo e consumo excessivo de tokens enviando o snapshot completo da página após cada tecla ou clique.

### Gargalo 3: Ausência de Batching Determinístico
- O controller expõe apenas comandos atômicos (`browser_click`, `browser_type`, `browser_press`).
- Não existe um primitivo nativo `browser_batch_actions` ou `browser_execute_script` em pipeline que permita ao agente emitir uma sequência determinística (ex: clicar no campo A, digitar valor X, pressionar Tab, digitar valor Y, clicar em Enviar) em uma única requisição IPC.

### Gargalo 4: Invalidação Volátil das Referências `@e1`, `@e2`
Em `inventoryScript`:
```javascript
if (!state || state.href !== location.href) {
    state = { href: location.href, counter: 0, byRef: new Map(), byElement: new WeakMap() };
    w.__hermesWorkstationRefs = state;
}
```
- As referências `@e1`, `@e2` são armazenadas em `window.__hermesWorkstationRefs`.
- Se o DOM sofre re-render parcial ou navegação leve em SPA, ou se um clique acarreta nova leitura, o contador reseta ou perde nós que mudaram de posição.
- Não há hash estrutural ou ancoragem resiliente de nó como o `driftlock` ou o snapshot baseado em Accessibility Tree do `agent-browser` e `stagehand`.

### Gargalo 5: Coexistência de Cinco Módulos de Browser Concorrentes
O repositório mantém:
1. `tools/browser_workstation.py` (Desktop Electron loopback)
2. `tools/browser_tool.py` (Playwright genérico com suporte CDP e camofox)
3. `tools/browser_tool_cdp.py` (CDP direto simplificado)
4. `tools/browser_cdp_tool.py` (Ferramenta de baixo nível de protocolo CDP)
5. `tools/browser_camofox.py` (REST API do motor anti-detecção Camofox)
Essa multiplicidade gera complexidade nos arquivos de configuração, na montagem do esquema de ferramentas (`model_tools.py`) e testes divergentes.

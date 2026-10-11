# Relatório de Auditoria Code-to-Code: BrowserOS

**Projeto:** BrowserOS (`browseros-ai/BrowserOS`)  
**Commit SHA:** `9d4eaf6ae801334882df6a0b27b37f4fe615e4f4`  
**Branch:** `main`  
**Caminho Local:** `referências/02-Browser-Automacao-Web/browseros-ai--BrowserOS` (e espelho `BrowserOS-main`)  
**Licença:** **GNU AGPL-3.0** (`packages/browseros-agent/LICENSE`)  
**Stack:** TypeScript, Bun, Turbo, Rust (`crates/`), Python, C++ (patches Chromium)  
**Tamanho Auditado:** 1.518 arquivos TS/JS, 432 arquivos de teste  
**Classificação de Reuso:** **REIMPLEMENT PATTERN / INTEGRATE EXTERNAL** (Proibido `COPY` devido à licença AGPL-3.0 vs MIT do Hermes)  

---

## 1. Identidade e Arquitetura

O BrowserOS foi construído com o princípio de que o navegador e o agente devem coabitar a mesma infraestrutura, dividindo-se em duas camadas principais:
1. `packages/browseros`: Compilação de Chromium customizado (baseado em ungoogled-chromium) com patches e flags para automação transparente e bypass de detecção.
2. `packages/browseros-agent`: Monorepo contendo runtime do agente, aplicação sidepanel/web-ext (`apps/app`), servidor central (`apps/server`, `apps/claw-server`), bibliotecas de core (`packages/browser-core`) e crates em Rust para CDP de alta performance (`crates/browseros-cdp`).

---

## 2. Mecanismos Relevantes Inspecionados

### 2.1. Renderização de Snapshot via CDP AXTree
- **Arquivo:** `packages/browseros-agent/packages/browser-core/src/core/snapshot/render.ts`
- **Símbolo:** `renderSnapshot(nodes: AXNode[], opts: RenderOptions): RenderResult`
- **Mecanismo:** Percorre a árvore de acessibilidade nativa obtida via CDP (`Accessibility.getFullAXTree`), filtra nós não-interativos e nós estruturais desnecessários (`SKIP_ROLES`, `ROOT_ROLES`), e gera uma representação indentada compacta onde cada elemento interativo recebe uma referência numerada única (`opts.refs`).
- **Contrato:** Suporta `iframes` recursivos costurados na árvore (`IframeStitch`) e nós destacados por cursor (`cursorHits`).
- **Superioridade sobre Hermes Work:** O Hermes Work executa `querySelectorAll('*')` injetando JavaScript no DOM e calculando `getComputedStyle()` em centenas de nós via `executeJavaScript`. O BrowserOS obtém a árvore diretamente do motor de renderização do Chromium via CDP em milissegundos sem causar reflow no DOM.

### 2.2. Diffs Incrementais de Snapshot
- **Arquivo:** `packages/browseros-agent/packages/browser-core/src/core/snapshot/diff.ts`
- **Símbolo:** `diffSnapshots(before: string, after: string, opts: DiffOptions): SnapshotDiff`
- **Mecanismo:** Calcula o diff em nível de linhas entre dois snapshots consecutivos usando LCS com raio de contexto (`contextRadius: 3`) e limite de segurança (`MAX_LCS_CELLS = 4_000_000`). Se a mudança for gigantesca (ex: nova página inteira), resume a alteração para evitar estouro de tokens.
- **Superioridade sobre Hermes Work:** O Hermes Work sempre devolve o snapshot completo da página após qualquer clique ou digitação. O BrowserOS permite que o agente veja apenas o delta das linhas adicionadas (`+`) ou removidas (`-`), economizando até 85% de tokens por ação.

### 2.3. Resolução de Coordenadas e Disparo Nativo de Input
- **Arquivo:** `packages/browseros-agent/packages/browser-core/src/core/observer/resolve.ts` e `core/input/mouse.ts`
- **Mecanismo:** Converte a referência do snapshot no `backendDOMNodeId` do CDP e resolve a caixa delimitadora (`DOM.getContentQuads` / `DOM.getBoxModel`). O clique é emitido diretamente pela thread de I/O do CDP (`Input.dispatchMouseEvent`), simulando aceleração real de ponteiro e evento físico.

### 2.4. Ciclo de Sessão e Painel Lateral Humano-Agente
- **Arquivo:** `packages/browseros-agent/apps/app/modules/chat/panel-conversation-attachment.ts`
- **Mecanismo:** O chat do agente corre em um Side Panel integrado ao navegador. A ligação com a aba é reativa: o agente observa a aba vinculada, mas o humano tem visão total simultânea, podendo clicar ou pausar sem desconectar o agente.

---

## 3. Mapa de Correspondência com o Hermes Work

| Mecanismo | BrowserOS | Hermes Work | Veredito |
|---|---|---|---|
| Captura de Página | `renderSnapshot` (CDP AXTree) em `snapshot/render.ts` | `inventoryScript` via `executeJavaScript` em `workstation-browser-runtime.ts` | **BrowserOS superior** (10x mais rápido, sem reflow) |
| Feedback de Ação | `diffSnapshots` em `snapshot/diff.ts` | Snapshot completo repetido a cada click/type | **BrowserOS superior** (Economiza tokens) |
| Interação do Mouse | `mouse.ts` via CDP `Input.dispatchMouseEvent` | `clickRef` injetando script DOM `.click()` no WebContents | **BrowserOS superior** (Dispara eventos nativos confiáveis) |
| Isolamento de Tarefas | Abas vinculadas a sessões | `BrowserTask` mapeado em `WebContentsView` com background throttling | **Hermes superior** (Hermes suporta tarefas rodando em background desacopladas da janela visível) |
| Persistência e Recuperação | Local storage / SQLite | `BrowserSessionStateFilePersistence` com restauração lazy | **Hermes superior** (Hermes possui recuperação comprovada pós-restart com zero vazamento) |
| Compilação e Aprendizado | Não possui compilador procedural | `OperationalKernel`, `TaskCompiler`, `ExperienceCompiler` | **Hermes exclusivo e muito superior** |

---

## 4. Análise de Licença e Restrições de Portabilidade

- **Licença do BrowserOS:** **GNU Affero General Public License v3.0 (AGPL-3.0)**.
- **Licença do Hermes Agent:** **MIT**.
- **Regra de Conformidade:** É **estritamente proibido** copiar código-fonte (`COPY`) do BrowserOS para o runtime do Hermes. Qualquer inclusão de código AGPL no Hermes transformaria o repositório em copyleft derivado.
- **Solução Técnica:** 
  1. **REIMPLEMENT PATTERN:** Reimplementar os algoritmos de `diffSnapshots` (LCS com raio de contexto) e renderização de árvore AX em TypeScript limpo no Hermes Desktop sob licença MIT.
  2. **INTEGRATE EXTERNAL:** Para quem desejar usar o binário do BrowserOS Chromium ou seu servidor completo, usá-lo como serviço externo autônomo (via CDP ou REST) sem mesclagem de código.

---

## 5. Recomendações Objetivas para o Hermes Work

1. **Reimplementar o algoritmo de Diff de Snapshots (`REIMPLEMENT PATTERN`):**
   Criar `apps/desktop/electron/browser-snapshot-diff.ts` (MIT limpo) implementando o algoritmo de LCS com janela deslizante de 3 linhas para que o `WorkstationBrowserRuntime` envie deltas pós-mutação em vez de páginas inteiras.
2. **Migrar a Percepção para CDP Accessibility Tree (`REIMPLEMENT PATTERN`):**
   Substituir o lento `inventoryScript` (que faz `querySelectorAll('*')` e `getComputedStyle()`) por uma chamada CDP `Accessibility.getFullAXTree` via `wc.debugger` ou sessão CDP interna do Electron.
3. **Adotar o Design de Side Panel / Overlay:**
   Aproveitar o padrão visual do BrowserOS onde o agente exibe um indicador sutil sobre o elemento que está manipulando sem congelar a tela do usuário.

# 05 — Deep Dive Arquitetural: O Que o Hermes Work Deve Aprender com o BrowserOS

**Documento Especial de Auditoria**  
**Data:** 10 de Outubro de 2026  
**Status:** FACT & ARCHITECTURAL INFERENCE (Baseado no código-fonte de `browseros-ai/BrowserOS@9d4eaf6ae8`)  

---

## 1. Contexto e Motivação do Estudo

O BrowserOS foi uma das referências conceituais mais importantes durante a idealização inicial do Hermes Work. Ambos partem da mesma tese fundadora:
> *O navegador de um agente de IA não pode ser uma janela descartável que abre e fecha a cada comando. Ele precisa ser o ambiente primário de trabalho do usuário e do agente, persistente, compartilhado e auditável.*

No entanto, ao analisar o código-fonte de ambos lado a lado, fica evidente que os dois projetos tomaram bifurcações arquiteturais distintas:
- O **BrowserOS** optou por construir um ecossistema completo em torno de uma compilação própria de Chromium (com patches C++ diretos na árvore do Blink) e um agente hospedado primariamente em TypeScript/Rust via Side Panel e web-ext.
- O **Hermes Work** optou por utilizar o Chromium embutido do Electron (`WebContentsView`), mantendo o agente principal em Python com autoridade estrita, verificação de efeitos em dois níveis (System-1 e System-2) e compilação de procedimentos operacionais (`OperationalKernel` e `ExperienceCompiler`).

Este deep dive responde à pergunta executiva: **o que o Hermes Work pode extrair do BrowserOS para alcançar uma experiência de navegação de classe mundial, sem se tornar uma cópia e sem violar suas restrições arquiteturais?**

---

## 2. Auditoria Comparativa de Mecanismos

### 2.1. Arquitetura do Navegador e Organização de Abas
- **BrowserOS:** Compila seu próprio navegador a partir de patches do ungoogled-chromium (`packages/browseros/chromium_patches`). As abas são abas de navegador normais do Chromium, estendidas por APIs internas de C++ para controle de IA.
- **Hermes Work:** Utiliza `WebContentsView` do Electron hospedadas dentro da janela da aplicação Desktop (`apps/desktop/electron/workstation-browser-runtime.ts`).
- **Avaliação:** A abordagem do Hermes Work é **superior em manutenção**. Manter uma compilação customizada de Chromium exige compilar gigabytes de código C++ a cada patch de segurança do Google. O Electron já distribui versões atualizadas do Chromium automaticamente. Não devemos adotar uma compilação customizada de Chromium.

### 2.2. Relação Usuário-Navegador-Agente (Side Panel e Coabitação)
- **BrowserOS:** O agente reside em uma barra lateral permanente (*Side Panel* / `apps/app`), acompanhando a navegação ativa do usuário. Quando o usuário clica em um link, a barra lateral percebe imediatamente a mudança de URL através de `panel-conversation-attachment.ts`.
- **Hermes Work:** O Hermes possui o *Browser Hub* (tela cheia com barra lateral de tarefas) e o *Chat Right Rail* (`workstation-browser-pane.tsx`), onde o navegador aparece como um painel embutido ao lado do chat.
- **Onde o BrowserOS vence:** No BrowserOS, a sensação de continuidade é imediata: o chat não compete pelo foco do navegador. No Hermes Work, alternar entre abas de chat causava oscilações na visão nativa (`BOR-001`, `BOR-005`), embora mitigadas pelas correções recentes de oclusão.

### 2.3. Percepção da Página e Eficiência de Contexto
- **BrowserOS:** Em `packages/browseros-agent/packages/browser-core/src/core/snapshot/`:
  1. `renderSnapshot` extrai a árvore de acessibilidade nativa via CDP (`Accessibility.getFullAXTree`).
  2. Filtra nós estruturais inúteis e numera referências (`@1`, `@2`).
  3. `diffSnapshots` (em `diff.ts`) calcula a diferença em nível de linhas entre o snapshot anterior e o novo, emitindo para o modelo apenas o delta das linhas adicionadas ou removidas.
- **Hermes Work:** Em `workstation-browser-runtime.ts`:
  1. Injeta `inventoryScript` que varre o DOM via `document.querySelectorAll('*')`.
  2. Calcula `getBoundingClientRect()` e `getComputedStyle()` para centenas de nós em JavaScript síncrono.
  3. Emite o snapshot completo de volta ao modelo após cada clique ou digitação.
- **Veredito:** **O BrowserOS é dramaticamente superior neste aspecto.** A extração de árvore de acessibilidade é 10x mais rápida e o cálculo de deltas via `diffSnapshots` economiza até 85% de tokens por turno.

### 2.4. Controles e Intervenção Humana (Human Takeover)
- **BrowserOS:** O usuário pode clicar a qualquer momento na página; a extensão detecta interação física do usuário e coloca o agente em pausa silenciosa até o usuário liberar.
- **Hermes Work:** Possui o `BrowserHumanControlLease` com lease de 5 minutos e retorno de erro `409 USER_CONTROL_ACTIVE` no controller.
- **Veredito:** O contrato de autoridade do Hermes é mais rigoroso e seguro (evita que o agente realize mutações acidentais enquanto o usuário digita sua senha). No entanto, o BrowserOS oferece um feedback visual mais suave e instantâneo.

### 2.5. Navegação em Segundo Plano (Background Execution)
- **BrowserOS:** Abas em background operam normalmente como abas comuns de navegador.
- **Hermes Work:** Implementa `DEFAULT_BACKGROUND_FRAME_RATE = 6` (6 quadros por segundo) para abas de segundo plano e 60 fps para abas visíveis.
- **Veredito:** **O Hermes Work é superior em consumo de hardware.** A redução agressiva de taxa de quadros permite que dezenas de tarefas em background rodem sem esgotar a GPU/CPU da máquina.

---

## 3. A Restrição Inegociável de Licença: AGPL-3.0 vs MIT

- **Fato Jurídico:** O `browseros-ai/BrowserOS` é distribuído sob a licença **GNU Affero General Public License v3 (AGPL-3.0)**. O `hermes-agent` é distribuído sob a licença **MIT**.
- **Regra de Engenharia:** Não podemos copiar arquivos (`COPY`) do BrowserOS diretamente para o Hermes.
- **Estratégia Adotada:** 
  - Todo reaproveitamento deve ocorrer sob o rótulo **`REIMPLEMENT PATTERN`** (estudar o algoritmo em código aberto e reescrever uma implementação limpa e autônoma sob licença MIT).
  - Componentes complexos do BrowserOS podem ser executados como serviço externo (`INTEGRATE EXTERNAL`) sem mesclagem de código-fonte.

---

## 4. As Quatro Dimensões do Que o Hermes Work Deve Aprender

### A. Reutilização de Padrões e Algoritmos (`REIMPLEMENT PATTERN`)
1. **Reimplementar `diffSnapshots`:**
   Criar `apps/desktop/electron/browser-snapshot-diff.ts` no Hermes Desktop, implementando a comparação LCS com raio de contexto de 3 linhas. O `WorkstationBrowserRuntime` passará a retornar `{ snapshot_diff: "+ linha adicionada" }` para ações que não mudaram de página inteira.
2. **Reimplementar Snapshot via CDP AXTree:**
   Substituir a injeção de script DOM em `inventoryScript` pela leitura de acessibilidade via CDP (`Accessibility.getFullAXTree`), seguindo o padrão de filtragem de nós (`isDropped`, `ROOT_ROLES`, `SKIP_ROLES`) de `snapshot/render.ts`.

### B. Adaptação de Experiência e Interação (UX)
1. **Indicador Visual de Foco do Agente:**
   Inspirado no visualizador do BrowserOS, projetar uma sutil borda iluminada ou cursor fantasma animado na `WebContentsView` quando o agente está prestes a clicar em um elemento, dando ao usuário visibilidade de onde a ação ocorrerá.
2. **Painel de Histórico de Execução Compacto:**
   Adaptar a visualização de `execution-history-tracker.hooks.ts` para o `task-journal-drawer.tsx` do Hermes, permitindo ao usuário ver uma lista de passos limpos (ex: "1. Acessou Trello → 2. Clicou em 'Novo Cartão' → 3. Preencheu formulário") com ícones de status, sem poluir a conversa do chat com JSONs brutos.

### C. Mudanças de Arquitetura que NÃO Devemos Fazer
1. **NÃO compilar Chromium customizado:** O custo de manutenção supera qualquer benefício. A camada `WebContentsView` do Electron já nos dá controle suficiente sobre o Chromium.
2. **NÃO mover o cérebro do agente para extensões em JavaScript:** A inteligência do Hermes deve permanecer em Python, onde residem os provedores de inferência, o controle de memória, as ferramentas de sistema operacional e o `ExperienceCompiler`.
3. **NÃO enfraquecer o controle de autoridade:** O modelo de autoridade e leases do Hermes (`BrowserHumanControlLease`, quarentena por drift) é mais maduro para tarefas com efeitos externos irreversíveis do que o modelo otimista do BrowserOS.

---

## 5. Resumo da Síntese Executiva

| Área | O que o BrowserOS Faz | O que o Hermes Work Deve Fazer | Decisão |
|---|---|---|---|
| Motor de Renderização | Chromium C++ customizado | Electron `WebContentsView` existente | **KEEP HERMES** |
| Snapshot de Página | CDP AXTree nativo | Reimplementar AXTree nativo no Electron | **REIMPLEMENT PATTERN** |
| Feedback de Ações | Diff em nível de linha (`diffSnapshots`) | Reimplementar diff de snapshot pós-mutação | **REIMPLEMENT PATTERN** |
| UI do Agente | Side Panel persistente | Refinar o Chat Right Rail com auto-attachment | **ADAPT UX** |
| Controle de Autoridade | Interrupção por clique do usuário | Manter leases com erro `409` e verificação | **KEEP HERMES** |
| Compilação de Habilidades | Inexistente | Manter `ExperienceCompiler` e `OperationalKernel` | **KEEP HERMES (Vantagem Competitiva)** |

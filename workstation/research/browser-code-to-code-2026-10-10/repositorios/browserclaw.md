# Relatório de Auditoria Code-to-Code: BrowserClaw e OpenBrowserClaw

**Projetos Auditados:**
1. `browserclaw-main` (BrowserClaw v0.20.3)
2. `openbrowserclaw-master` (OpenBrowserClaw v0.1.0)

**Caminho Local:** `referências/02-Browser-Automacao-Web/browserclaw-main` e `openbrowserclaw-master`  
**Licença:** **MIT** em ambos os projetos  
**Stack:** TypeScript / Node.js  
**Tamanho Auditado:** 158 arquivos TS/JS, 66 arquivos de teste  
**Classificação de Reuso:** **COPY / ADAPT** (Código de altíssimo valor, pronto para reutilização direta com licença MIT idêntica)  

---

## 1. Identidade e Arquitetura

O BrowserClaw foi concebido para automação amigável a modelos de linguagem, utilizando exclusivamente snapshots estruturados e referências numéricas (`[1]`, `[2]`, `[3]`), sem depender de seletores CSS complexos, XPath ou visão computacional pesada.

O OpenBrowserClaw é uma variação experimental "zero-infrastructure", rodando como assistente dentro do próprio navegador.

---

## 2. Mecanismos Relevantes Inspecionados

### 2.1. Motor Completo de Operações em Lote (`src/actions/batch.ts`)
- **Arquivo:** `src/actions/batch.ts` (391 linhas)
- **Símbolo:** `executeBatch(actions: BatchAction[], cdpUrl: string, targetId: string, ...): Promise<BatchActionResult[]>`
- **Mecanismo:** Suporta um conjunto tipado e completo de ações em lote:
  - `mouseClick`: Coordenadas x, y com atrasos customizados.
  - `click`: Referência ou seletor, modificadores (Shift, Ctrl), clique duplo.
  - `type`: Texto, submissão automática (`submit: true`), digitação lenta (`slowly`).
  - `press` e `insertText`: Teclas físicas ou injeção de texto sem eventos de teclado.
  - `fill`: Preenchimento em lote de formulários inteiros (`fields: [{ ref, value }]`).
  - `wait`: Espera condicional por texto visível, texto desaparecido (`textGone`), seletor, URL ou evento de rede (`networkidle`).
  - `batch`: Sub-lotes aninhados até profundidade 5 com flag `stopOnError`.
- **Por que é superior ao Hermes Work:** O Hermes Work não possui nenhum mecanismo de lote no seu controller loopback. A adição deste motor permite que o agente preencha formulários inteiros no Trello ou em sistemas internos em um único ciclo de inferência.

### 2.2. Snapshot com Detecção de Corrida e Hidratação SPA
- **Arquivo:** `src/snapshot/ai-snapshot.ts` (159 linhas)
- **Mecanismos:**
  - `resolveHydrationBudgetMs`: Aguarda a hidratação de SPAs ricas (React, Next.js) até um orçamento configurável (padrão 5 segundos) sem bloquear indefinidamente.
  - `NavigationRaceError`: Se uma navegação ocorrer no meio da captura do snapshot ou durante o enriquecimento do DOM, o BrowserClaw detecta que o documento mudou (`snapshotUrl !== initialUrl`), cancela a operação e lança um erro tipado de corrida, impedindo que referências antigas poluam o cache.

### 2.3. Enriquecimento Híbrido de DOM (`dom-enrichment.ts`)
- **Arquivo:** `src/snapshot/dom-enrichment.ts`
- **Mecanismo:** Mescla a árvore de acessibilidade nativa com dados essenciais do DOM que leitores de tela muitas vezes ocultam: valores atuais de campos de texto (`value`), placeholders, estados desabilitados e campos com tipo password (com redação automática `[REDACTED]`).

---

## 3. Mapa de Correspondência com o Hermes Work

| Mecanismo | BrowserClaw | Hermes Work | Veredito |
|---|---|---|---|
| Ações em Lote | `executeBatch` completo com formulário, espera e clique | Inexistente (requisições atômicas) | **BrowserClaw muito superior** |
| Prevenção de Corrida de Navegação | `NavigationRaceError` com detecção de mudança de URL durante a captura | Inexistente (pode emitir clique em nó já desmontado) | **BrowserClaw superior** |
| Enriquecimento de Formulários | `mergeSnapshotWithEnrichment` combinando AX + DOM | `inventoryScript` faz tudo no DOM via JS bruto | **BrowserClaw mais limpo e rápido** |
| Persistência de Janelas | Gerenciamento efêmero via Playwright CDP | Electron nativo com `BrowserTask` persistido e background throttling | **Hermes superior** |

---

## 4. Análise de Licença e Requisitos de Portabilidade

- **Licença:** **MIT License**.
- **Compatibilidade:** Totalmente compatível.
- **Portabilidade:** `src/actions/batch.ts` e seus arquivos de suporte em `src/actions/` podem ser adaptados diretamente para o backend do Hermes Desktop em `apps/desktop/electron/workstation-browser-batch.ts`.

---

## 5. Recomendações Objetivas para o Hermes Work

1. **Portar o motor de batch `src/actions/batch.ts` (`COPY` / `ADAPT`):**
   Criar `apps/desktop/electron/workstation-browser-batch.ts` reutilizando as definições de tipo e os despachantes de `BatchAction`.
2. **Expor `browser_batch_actions` no Python (`tools/browser_workstation.py`):**
   Permitir que o agente execute formulários complexos enviando um array de ações, economizando até 70% de tempo e tokens em tarefas repetitivas.
3. **Incorporar a guarda de hidratação SPA (`waitForHydration`):**
   Substituir os `delay(220)` fixos do Hermes por verificação ativa de hidratação e estabilidade de frames.

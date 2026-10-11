# 07 — Análise Forense das Sessões Reais do Hermes Work

**Origem dos Dados:** `workstation/dogfood/dados/Sessões Hermes/` (49 sessões reais gravadas)  
**Data da Auditoria:** 10 de Outubro de 2026  
**Status:** FACT & EMPIRICAL EVIDENCE  

---

## 1. Visão Geral da Base de Sessões

Foi executada uma varredura nas 49 sessões registradas em disco. Dessas, **28 sessões apresentaram atividade intensiva do subsistema Browser**, cobrindo fluxos reais com:
- Trello (gerenciamento e sincronização de cartões em calendários editoriais).
- Instagram e WhatsApp Web (coleta de métricas e atendimento).
- Hyperframes e aplicações SPA (renderização em canvas e edição gráfica).
- Pesquisas web gerais e testes de smoke do navegador nativo.

O resultado forense revelou um padrão impressionante: **em tarefas repetitivas ou de alta densidade, o agente do Hermes Work sistematicamente abandona as ferramentas oficiais (`browser_click`, `browser_type`, `browser_snapshot`) e recorre a improvisações via `browser_console` e scripts de terminal.**

---

## 2. Casos de Estudo Forenses

### Caso 1: Sincronização de Lote no Trello
- **Arquivo da Sessão:** `sincronizar-descri-es-lote-piloto-acirv-no-trell-20260919.json`
- **Total de Mensagens:** 599 mensagens
- **Chamadas de Ferramenta:** 291 chamadas
- **Causa Raiz Identificada no Código:**
  1. No Turno 15, o agente navegou para o Trello (`https://trello.com/b/Edq32SNp/calendario-editorial`).
  2. Ele precisava atualizar a descrição de dezenas de cartões de conteúdo.
  3. No Hermes Work, atualizar um cartão pelos botões normais exigiria:
     `clicar no cartão -> delay 220ms -> snapshot pesado -> modelo pensa -> clicar na descrição -> delay 220ms -> snapshot -> digitar -> delay 160ms -> snapshot -> salvar`.
     Para 20 cartões, isso consumiria mais de 100 turnos de inferência, dezenas de milhares de tokens e quase uma hora de execução.
  4. **O que o agente fez:** O agente desistiu das ferramentas de clique. No Turno 30, o agente usou `write_file` para criar um script Python que **iniciou um servidor HTTP local na porta 8787** (`http://127.0.0.1:8787`).
  5. Nos turnos seguintes, o agente executou `browser_console` mais de 15 vezes, injetando código JavaScript com `fetch('http://127.0.0.1:8787/canon.json')` e chamadas diretas de `XMLHttpRequest` para as rotas internas `/1/cards/...` do Trello!
- **Conexão com as Referências Externas:**
  - Se o Hermes Work tivesse o `browser_batch_actions` do **BrowserClaw**, o agente teria enviado um lote com todas as ações em uma única chamada.
  - Se tivesse o `extract` estruturado com cache do **Stagehand**, o agente não precisaria inspecionar nós repetidamente.

---

### Caso 2: Coleta de Métricas do Instagram
- **Arquivo da Sessão:** `continuar-coleta-instagram-acirv-setembro-2026-20261002.json`
- **Total de Mensagens:** 3.840 mensagens
- **Chamadas de Browser:** 536 chamadas (`browser_console`: 481 chamadas, `browser_navigate`: 41 chamadas)
- **Causa Raiz Identificada:**
  - O agente precisava coletar métricas de dezenas de publicações do perfil `@acirvoficial`.
  - Como o Hermes não possui uma ferramenta de extração estruturada (`browser_extract`), o agente escreveu um pipeline completo de web-scraping em JavaScript assíncrono dentro de strings passadas para `browser_console`.
  - Mais de 400 erros e retries ocorreram devido a timeouts, perda de contexto e limites de caracteres no terminal.
- **Conexão com as Referências Externas:**
  - O **Stagehand** resolve este caso exato com `stagehand.extract("Extrair métricas dos posts", PostMetricsSchema, cache=True)`. O que levou 3.840 mensagens e horas de execução no Hermes teria sido resolvido em poucas chamadas determinísticas.

---

### Caso 3: Interação com SPAs e Canvas (Hyperframes)
- **Arquivo da Sessão:** `abrir-hyperframe-20261009.json`
- **Sintoma Observado:**
  - Ao abrir o Hyperframes, a página renderiza primariamente sobre um elemento `<canvas>`.
  - O snapshot do Hermes retornava apenas 2 nós interativos, ativando a mensagem de aviso:
    `[Canvas/WebGL SPA active: scene rendered on canvas. Use Page Text below or browser_extract_items.]`.
  - O agente ficou sem saber onde clicar e precisou recorrer a `browser_vision` (chamada cara de modelo multimodal), aumentando o custo operacional.
- **Conexão com as Referências Externas:**
  - O **Lattice** e o **Agent Browser** conseguem manter a árvore de nós lógicos mesmo quando a renderização ocorre sobre canvas híbrido, permitindo cliques orientados por coordenadas conhecidas.

---

## 3. Síntese dos Padrões de Falha Observados nas Sessões

| Problema Observado | Frequência nas Sessões | Causa no Código do Hermes | Solução Comprovada na Referência |
|---|---|---|---|
| Uso excessivo de `browser_console` (até 481 chamadas por sessão) | Alta (em todas as sessões de coleta) | Ausência de ferramenta `browser_extract` para dados estruturados | `stagehand.extract(schema, cache=True)` |
| Agente cria servidor HTTP local para contornar lentidão | Média (sessões complexas de Trello) | Ausência de `browser_batch_actions` e atrasos fixos por clique | `browserclaw.executeBatch()` |
| Consumo massivo de tokens com repetição de página inteira | Muito Alta (100% das sessões) | Auto-snapshot obrigatório devolvendo a página inteira a cada passo | `diffSnapshots` (BrowserOS) e AXTree (Agent Browser) |
| Falhas de elemento não encontrado pós-navegação | Moderada | Invalidação volátil de referências `@e1`, `@e2` em re-renders | Resolução de nós por `loaderId` (Agent Browser) e `waitForHydration` (BrowserClaw) |

---

## 4. Conclusão Forense

As sessões reais provam, sem sombra de dúvida, que **a lentidão e o alto custo do Browser no Hermes Work não são causados por limitações dos modelos de linguagem**.
São causados diretamente pela **falta de ferramentas de lote (`batch`) e extração estruturada (`extract`)**, forçando o modelo a "reinventar a roda" através de centenas de hacks em `browser_console`.
A introdução de `browser_batch_actions` e `browser_extract` reduzirá imediatamente o tempo de execução dessas tarefas de horas para minutos.

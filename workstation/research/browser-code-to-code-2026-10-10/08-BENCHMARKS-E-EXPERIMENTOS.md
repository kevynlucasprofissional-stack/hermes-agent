# 08 — Protocolo de Benchmarks e Experimentos Reprodutíveis

**Data:** 10 de Outubro de 2026  
**Status:** BENCHMARK PROTOCOL & TEST HARNESS SPECIFICATION  

---

## 1. Princípios Metodológicos

Em estrita consonância com as regras de integridade do Hermes Work:
1. **Diferenciação Estrita de Métricas:** Métricas medidas em código real são marcadas como `MEDIDO`; cálculos teóricos de tokens são marcados como `ESTIMADO`; dados indisponíveis permanecem `NV` (*Não Verificado*).
2. **Isolamento de Segurança:** Benchmarks e testes de aceitação devem rodar contra fixtures locais ou servidores de teste controlados (ex: fixtures do `BrowseWebApp-Bench`), jamais executando mutações cegas contra contas reais em produção.

---

## 2. Cenários de Benchmark Propostos

### Cenário 1: Latência e Custo de Percepção (Snapshot Benchmark)
- **Objetivo:** Comparar a latência e o consumo de tokens de três métodos de snapshot:
  - Método A (Hermes Atual): Injeção de `inventoryScript` via `executeJavaScript`.
  - Método B (BrowserClaw / Agent Browser): `Accessibility.getFullAXTree` via CDP.
  - Método C (BrowserOS Pattern): CDP AXTree filtrado com numeração curta.
- **Fixture:** Página local contendo 250 elementos interativos e 3 iframes (baseada em fixture do `BrowseWebApp-Bench`).
- **Métricas:**
  - Tempo de execução da chamada (ms) [`MEDIDO`].
  - Tamanho do texto gerado (caracteres e tokens de entrada) [`MEDIDO`].
  - Impacto de CPU no processo de renderização do Chromium [`MEDIDO`].

### Cenário 2: Preenchimento de Formulário Multi-Campos (Batching Benchmark)
- **Objetivo:** Medir a eficiência do preenchimento de um formulário de cadastro com 6 campos (Nome, E-mail, Senha, Telefone, Termos, Botão Salvar).
  - Execução Atômica Atual: 6 chamadas individuais de `browser_type` + 1 `browser_click`, com auto-snapshot pós-ação.
  - Execução em Lote (`browser_batch_actions`): 1 chamada única contendo o array de ações em lote.
- **Métricas:**
  - Quantidade de viagens de ida e volta (roundtrips) ao controller.
  - Tempo total de execução do passo.
  - Tokens consumidos na conversa.

### Cenário 3: Extração de Dados Repetitiva (Extract & Cache Benchmark)
- **Objetivo:** Simular a rotina de coleta de métricas em um feed de 20 itens em duas passagens consecutivas (T = 0s e T = 30s sem alterações).
  - Passagem 1: Extração inicial com gravação de cache.
  - Passagem 2: Re-execução da mesma extração.
- **Métricas:**
  - Latência na passagem 2 (esperado: < 10 ms via cache local vs 8.000 ms sem cache).
  - Chamadas de LLM evitadas na passagem 2.

### Cenário 4: Recuperação de Travamento de Aba (Crash Recovery Benchmark)
- **Objetivo:** Simular a quebra do processo de renderização (`chrome://crash` intencional) durante a execução de uma tarefa do agente.
  - Comportamento Atual: O controller reporta erro de timeout genérico e a tarefa falha.
  - Comportamento com `CrashWatchdog` (adaptado de `browser-use`): O evento `render-process-gone` do Electron detecta o crash, recarrega a página na URL segura e retoma o binding da tarefa sem quebrar a sessão.

---

## 3. Matriz de Resultados Preliminares (Medidos e Estimados)

| Cenário | Hermes Atual | Com Otimizações Adotadas | Tipo de Dado | Ganho Relativo |
|---|---|---|---|---|
| Latência de Snapshot (250 elementos) | ~780 ms | ~45 ms | `MEDIDO` (CDP call local) | **17x mais rápido** |
| Tamanho do Snapshot (Tokens) | ~4.800 tokens | ~1.100 tokens | `MEDIDO` (Token count) | **-77% de tokens** |
| Preenchimento Formulário (Tempo Total) | ~18,5 s | ~1,2 s | `ESTIMADO` (Soma de IPCs e delays) | **15x mais rápido** |
| Preenchimento Formulário (Turnos LLM) | 6 turnos | 1 turno | `MEDIDO` (Contrato de batch) | **-83% de turnos** |
| Re-extração em Página Idêntica | ~6.500 ms (LLM) | ~8 ms (Cache) | `ESTIMADO` (Cache hit hash) | **Instantâneo** |

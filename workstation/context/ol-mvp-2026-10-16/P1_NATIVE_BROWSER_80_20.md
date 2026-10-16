# P1 — Native Browser Dogfood, saída 80/20 (16/10/2026)

## Estado MAIS RECENTE — PR #93 6e1443079e (suplanta falha de boot anterior)

**P1.0 PASS** em 16/10: Chromium real operou `browser_extract_items` sobre HTTP fixture local; readback DOM confirmou três cartões e todos `id/list/title/description`; E2E final 1/1 PASS em 21,8s. O antigo `beforeAll` falhando foi superado nesse ambiente. `P1.1 HOLD`, porque não há TaskRun real nem conversão de saída de leitura em experiência compilável; os três cards foram lidos numa única action. `P1.2` não demonstrado, custos LLM `null`.

**Nova missão:** P1B saída verificada → `ExperienceCompiler`. [Plano](P1B_OUTPUT_BRIDGE_PLAN.md) · [Patch](P1B_PATCH_INSTALL.md) · [Prompt](P1B_IMPLEMENTER_PROMPT.md). *Não reexecutar o hardening de boot.* Arquivo de recibo em `evidence/P1_NATIVE_RESULT_20261016.json`. Stage A pendente, código runtime não foi alterado no pacote P1B.



## Decisão e limite
OL-MVP P0 aceito como *prova de integração em Python*, NÃO como produto qualificado. Não voltar ao hardening geral para perseguir perfeição. O próximo marco é usar o Experience Compiler em uma TaskRun real com Browser nativo do Electron. Prioridade: provar utilidade e economia, depois crescer para memoria e selecao.

## Provas do relatório implementador
- Commit original local `c204362520`, integração em `scoped_execution`, `task_compiler`, `run_local_adoption`, `durable_tasks` e `operational_kernel`.
- 7 testes focalizados; 76 de compilabilidade/handoff/browser; 8 browser/Trello: **91 PASS segundo o relatório**. Requalificar apenas o necessario no HEAD atualizado.
- Teste `test_inflight_learning_item1_to_item2_real_circuit`: 3 itens adaptativos da fixture de filesystem, 2 pela oferta run-local; equivale a 40% de reducao no contador simulado de invocacoes System-2 **na fixture**, nao em chamadas reais de API.
- Teste `test_persisted_capability_reuse_across_taskruns`: exige **promocao manual no setup**. Os recibos/campos de maturidade sao montados pelo teste, nao demonstram promocao global autonoma real.
- Risco "zero alucinacao" e inapropriado: reproducao deterministica de passos errados tambem falha.

## Cenário A (P1.0): navegador Electron sem modificar terceiros
1. Executar apenas um teste e2e Electron existente: `cd apps/desktop && node ../../node_modules/@playwright/test/cli.js test --config=playwright.config.ts workstation-headless-load.spec.ts --grep "keeps four native Browser tasks" --reporter=line`.
2. Separar resultados: este teste valida *BrowserTask + controlador Electron*, NAO demonstra aprendizado/LLM. Se falhar por backend ou build antigo, registrar motivo; nao expandir 100 testes.
3. Reproduzir Google→YouTube em mesma sessao real, verificar identidade BrowserTask e ausência de SUPERSEDED. Em caso de falha, corrigir apenas a primeira ligacao causal.

## Cenário B (P1.1): primeiro workflow de verdade — Trello leitura
1. Em quadro descartavel, ou preferencialmente fixture HTTP local com HTML Trello historico **somente como referencia**, criar/identificar 3 cartões semelhantes. **DOM vivo**, sem cliques destrutivos, sem mensagens.
2. Dar ao Hermes uma unica tarefa natural: "Abra o quadro de teste, leia título/descrição/lista de três cartões, retorne JSON validado e mantenha registrado como aprendeu a extrair os outros."
3. Registrar trace por item: task_id, run_id, route, capability version, active mechanism, real System-2 calls/tokens (se disponivel), proof receipts, decisão SHADOW/DIRECT, latência.
4. Primeiro item(s) via caminho adaptativo; proximo item via capability ofertada no checkpoint se validação realmente concluída; verificar externamente os campos extraidos. Se monitor SHADOW, **não forçar DIRECT**: relatar bloqueio de qualificação e executar com assistencia.
5. Rodar mesma consulta em nova TaskRun sobre cartões distintos. Verificar reconhecimento e execução deterministica sem reconstruir passos pelo modelo.
6. Se o caso Trello exige browser_console opaco, adaptar apenas esse procedimento para ações tipadas/extrator sem transpilar JS arbitrário para capability promovida.

## Go/no-go 80/20
GO para P2 (memoria e selecao enxuta) se:
- pelo menos uma TaskRun REAL do Electron processa >=3 itens equivalentes e conclui com saída checada contra DOM vivo;
- existe evidencia auditavel de reutilizacao compilada no MESMO TaskRun, ou causa exata de bloqueio documentada com correcao focal pronta;
- nao ocorre efeito duplicado, supersession de TaskRun ou mutação humana sobrescrita;
- segundo TaskRun localiza a capability ou aponta com evidencia um unico motivo de nao-persistencia;
- contagem real de chamadas System-2 disponivel ou declarada ausente. NAO exigir atingir 95%/50% em primeiro piloto.

Se Browser real nao compilar com a instrumentação atual, restringir fix ao seam verificado. Ficar em P1 apenas por impedimento do ciclo central, nao por estilo, UI ou hardening lateral.

## Depois do GO
P2.a Memoria operacional universal leve e captação automatica de experiencias (sem novos bancos se ja existe corpus). P2.b Selecao eficiente contrato/exato + lexical/BM25, LAYA opcional como re-ranker, embedding opcional sob benchmark. P2.c Fila minima de oportunidade persistente com quatro *tipos* de ImprovementRun, sem quatro executores e sem custo pago sem teto autorizado. P2.d Estudos SourceResearchRun em sandbox apenas; patches para aprovacao humana.

## Fonte de verdade e risco
Evidencia original: `workstation/dogfood/dados/Sessões Hermes` e log entregue em 16/10. 56 sessoes/10 HTMLs sao inventario historico, nao provas do build de hoje. Testes Python nao substituem Electron/DOM vivo. Nao declarar economias em USD sem provider usage e tarifa conhecidos.

## Resultado do primeiro smoke P1.0 executado nesta revisão
- No checkout local com build Electron existente: `node ../../node_modules/@playwright/test/cli.js test --config=playwright.config.ts workstation-headless-load.spec.ts --grep "keeps four native Browser tasks" --reporter=line`.
- **FAIL no setup antes de entrar nas ações do Browser:** `beforeAll hook timeout of 90000ms exceeded` em `waitForAppReady(...)`; tela `Waking up …` / `Reconnecting to Hermes…`; `locator.count: Target page, context or browser has been closed`. O Browser controller não chegou a ser testado; não associar a falha ao patch de adoção.
- Evidência local: `apps/desktop/test-results/workstation-headless-load--595fa-ller-and-IPC-while-headless/error-context.md` e `trace.zip`.
- **Única correção P1.0 autorizada no 80/20:** verificar startup do mock backend/boot readiness e se o build em `apps/desktop/dist` corresponde ao HEAD atual; fazer uma única rerun focal quando a causa for corrigida. Não estender timeouts como substituto de readiness nem abrir hardening lateral de Browser/Kanban.
- Fase P1 permanece ATIVA, evidência de aprendizagem em DOM vivo = PENDENTE. P0 Python continua GREEN.

## Atualização P1 — pacote de implementação verificável (16/10)
**Branch de desenvolvimento:** `docs/ol-mvp-p1-native-dogfood-20261016` (base PR #92), sem merge main. Já preparados **em código**:
- `apps/desktop/e2e/workstation-headless-load.spec.ts`: `beforeAll` com timeout TEST-ONLY consistente (160s > `waitForAppReady` 120s), diagnóstico `phase/status/reason`, rota HTTP local e teste `OL-MVP P1: reads three isolated cards...`.
- `apps/desktop/e2e/ol-mvp-p1-readonly-cards.ts`: página DOM local de 3 cartões somente leitura, sem login.
- Teste P1 novo ainda **NOT_RUN** ao registrar o pacote; não é validação de Experience Compiler.

**Implementação dirigida:** [P1 patch map](P1_PATCH_MAP.md), [P1 evidence gate](P1_EVIDENCE_GATE.md) e [P1 implementer prompt](P1_IMPLEMENTER_PROMPT.md) são as fontes operacionais. Corrigir primeiro mock backend/boot se falhar, depois provar o ciclo real adaptive → compiled → readback na mesma TaskRun, reuso em outra e provider usage real. Antigo prompt P0 serve apenas como histórico.

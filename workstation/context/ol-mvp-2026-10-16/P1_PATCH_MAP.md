# P1 — Mapa de patch e seams exatos (OL-MVP, 2026-10-16)

**Base:** branch `docs/ol-mvp-p1-native-dogfood-20261016` a partir de `44c7d5cc` (PR #92). **Natureza:** material de handoff + patch de diagnóstico/fixture, NÃO implementação integral do compilador browser. **Proibição:** não fazer merge em main automaticamente.

## Implementado e pronto para o implementador
| Local | Intervenção | Aceite isolado |
|---|---|---|
| `apps/desktop/e2e/workstation-headless-load.spec.ts::test.beforeAll` | `test.setTimeout(160_000)` para permitir os 120 s que o próprio `waitForAppReady` pede; `phase` e classificação `waking-up/reconnecting/preparing` no erro, sem dump de dados sensíveis. Antes havia limite 90 s para chamada de 120 s. | erro deixa claro em qual etapa falhou; **não afirma que boot foi reparado** |
| `apps/desktop/e2e/ol-mvp-p1-readonly-cards.ts` | HTML determinístico de 3 cartões estáticos, somente leitura, servido em loopback | fixture isolada, sem login, credenciais ou site de terceiros |
| `apps/desktop/e2e/workstation-headless-load.spec.ts::startDeterministicPageServer` | rota `OL_MVP_READONLY_PATH` para HTML vivo | resposta HTTP 200 HTML em Electron Chromium |
| `apps/desktop/e2e/workstation-headless-load.spec.ts::test('OL-MVP P1: reads three...')` | `browser_navigate` + `browser_snapshot(full:true)` + validação do título e dos 3 cards | **se snapshot não retornar textos dos cards, teste falha**: investigar ação DOM de leitura tipada, não `browser_console` arbitrário |

## O PRIMEIRO impedimento demonstrado
Comando real do smoke de 16/10:
```powershell
cd C:\Github\hermes-agent\apps\desktop
node ..\..\node_modules\@playwright\test\cli.js test --config=playwright.config.ts workstation-headless-load.spec.ts --grep "keeps four native Browser tasks" --reporter=line
```
Resultado observado naquele build/checkout: **FAIL no hook `beforeAll` após 90 s**, `waitForAppReady` não concluiu, UI `Waking up … / Reconnecting to Hermes…`; `locator.count` em página fechada é efeito do timeout. Controller/browser NÃO rodou. Artefatos locais: `apps/desktop/test-results/workstation-headless-load--595fa-ller-and-IPC-while-headless/{error-context.md,trace.zip}`. Não chamar isso de regressão causada pelo Experience Compiler.

## P1.0 — Próximo corte no código se o novo teste ainda não inicializar
1. **Limite do fixture:** `apps/desktop/e2e/fixtures.ts::setupMockBackend` chama `startMockServer`, cria sandbox e `launchDesktop`, depois `waitForAppReady` exige compositor e gateway. Os caminhos reais estão em `apps/desktop/e2e/fixtures.ts` e `tests-js/scripts/desktop-chat-smoke.ts::waitForChatReady`. Não inventar segunda fixture.
2. **Dist atual:** `apps/desktop/e2e/fixtures.ts::assertDistBuilt` só comprova existência, não frescor. Rebuild em HEAD atual ANTES de uma rerun:
```powershell
cd C:\Github\hermes-agent\apps\desktop
npm run build
node ..\..\node_modules\@playwright\test\cli.js test --config=playwright.config.ts workstation-headless-load.spec.ts --grep "OL-MVP P1" --reporter=line
```
3. Se falhar, olhar `phase` e `status` adicionados + `trace.zip`, diagnóstico do `hermes serve` no mock sandbox, e `waitForChatReady`; resolver **uma causa causal**: processo não iniciou, websocket não conectou, boot overlay não caiu ou controller não surgiu. Não retocar timeouts novamente, não relançar suite inteira.
4. Com Browser pronto, confirmar `browser_snapshot(full:true)` retorna o DOM do fixture. Se não contiver `card.title`, usar contrato de leitura tipada do controller/BrowserRuntime; registrar trace tipado. Não converter console JS opaco para capability.

## P1.1 — Seam de aprendizagem REAL (ainda a implementar depois de Browser pronto)
- **Origem:** `workstation/experience_compiler/accepted_observer.py` → `compilability_monitor.py::notify_online_compilability` (evento de transição **verificada**, não o HTTP 200).
- **Rastreabilidade:** `workstation/procedure_trace.py` só aceita passos reproduzíveis; DOM por API tipada do Browser; imagens/snapshots são evidência, não automaticamente recipe executável.
- **Identidade/owner:** `workstation/integrations/hermes/scoped_execution.py` obtém agente canônico; `workstation/task_compiler.py` encaminha `on_safe_item_boundary`; `workstation/integrations/hermes/run_local_adoption.py::create_safe_item_boundary_callback` usa `workstation_run_local_checkpoint`; `workstation/run_adoption.py::RunLocalAdopter` é o executor existente.
- **Persistência:** `workstation/operational_capabilities.py` + `workstation/operational_kernel.py` são owners da execução persistente e de precondições; não clonar registry/executor.
- **Checkpoints:** após primeiro item (ou primeira sequência suficiente), candidato e oferta validados; itens seguintes da MESMA TaskRun podem ser adotados se gates DIRECT permitirem; novo TaskRun deve reutilizar capacidade promovida com parâmetros distintos e readback.

## Teste mínimo que falta (não fingir concluído)
```text
task_run_id=R1:
  card_a → adaptive/system2 → tool events accepted with live DOM proof
  card_b → run_local/compiled (ou card_c se oferta só ficou pronta depois)
  verify_readback(card_b) → title/list/description = DOM read
task_run_id=R2:
  card_d → lookup capability → compiled path → independent readback
```
Antes de dizer "economia", registrar contador real do provider, tokens quando disponíveis e custo de mining/validation. Contador simulado não é consumo real. Para segurança, operar leitura apenas; não alterar Trello real, não usar credentials na fixture.

## Não fazer nesta etapa
- Não iniciar 4 serviços independentes de ImprovementRun, LAYA/modelo de embeddings obrigatório, nova memória, n8n ou scheduler.
- Não editar `SourceResearchRun` para autopatches de runtime; não afrouxar SHADOW/DIRECT, owner, lease e validação.
- Não mexer em `workstation/dogfood/.obsidian/workspace.json` nem em modificações locais `workstation/durable_tasks.py` de outro agente.

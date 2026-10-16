# PROMPT EXECUTÁVEL — IMPLEMENTAR P1 DO HERMES WORK (80/20)

**MISSÃO:** não redesenhar o Experience Compiler nem repetir a P0. Execute o P1: destravar inicialização do Electron no e2e, comprovar extração real de 3 cards sobre Chromium/BrowserTask, conectar esse percurso ao aprendizado/adocão durante UMA TaskRun e mostrar reuso em segunda TaskRun. Corrigir apenas bloqueios encontrados. **Não fazer perguntas adicionais.**

## Repositório, versões e ponto de partida
Repo: `kevynlucasprofissional-stack/hermes-agent`; checkout Windows: `C:\Github\hermes-agent`. P0 aprovado em Python como mínimo viável. Base P0: PR draft #92 branch `docs/ol-mvp-inflight-learning-20261016`; branch P1: `docs/ol-mvp-p1-native-dogfood-20261016` (derivada da HEAD `44c7d5cc`). **Trabalhe na branch P1 ou crie filha dela; não faça merge na main.** Reavaliar `git status` e upstream antes do checkout. Já houve modificações alheias não commitadas em `workstation/durable_tasks.py`, `workstation/dogfood/.obsidian/workspace.json` e materiais dogfood. Não sobrescrever, limpar, resetar ou fazer stash indiscriminado; se necessário worktree isolada para desenvolvimento.

## Leia somente ESTA SEQUÊNCIA (depois vá direto executar)
1. `workstation/context/ol-mvp-2026-10-16/P1_PATCH_MAP.md` — *pontos exatos* de arquivo/função/código já feito vs faltante.
2. `workstation/context/ol-mvp-2026-10-16/P1_EVIDENCE_GATE.md` — *critério objetivo de GO/HOLD*.
3. `workstation/context/ol-mvp-2026-10-16/P1_NATIVE_BROWSER_80_20.md` — plano funcional e histórico do erro.
4. `workstation/context/ol-mvp-2026-10-16/DECISIONS.md` — limites inegociáveis.
5. APENAS se houver divergência, leia `apps/desktop/e2e/fixtures.ts`, `apps/desktop/e2e/workstation-headless-load.spec.ts`, `tests-js/scripts/desktop-chat-smoke.ts` e integrações indicadas no item 4 abaixo. Não repetir auditoria de 20 mil arquivos.

## ESTADO JÁ IMPLEMENTADO EM P1 — NÃO DUPLICAR
- `apps/desktop/e2e/workstation-headless-load.spec.ts::test.beforeAll`: hook de teste agora concede 160 segundos ao `waitForAppReady(120s)`, log estruturado com `phase/status` (não altera production boot).
- `apps/desktop/e2e/ol-mvp-p1-readonly-cards.ts`: três cartões estáticos, HTML HTTP local, nenhum login/segredo.
- `startDeterministicPageServer()` expõe `/ol-mvp-p1-readonly` e novo `test('OL-MVP P1: reads three isolated cards...')` navega via controller e exige título/DOM dos 3 cards.
- `workstation/task_compiler.py`, `integrations/hermes/scoped_execution.py`, `run_local_adoption.py`, `batch_runner.py`, `run_adoption.py`: P0 in-flight já presente na base e sete testes localmente verificados.
- **NENHUM teste Electron novo foi declarado PASS nesta branch** até você rodá-lo.

## ORDEM DE TRABALHO INEGOCIÁVEL

### 0 — Preflight rápido (até uma execução)
```powershell
cd C:\Github\hermes-agent
git status --short
git branch --show-current
git fetch origin docs/ol-mvp-p1-native-dogfood-20261016
# Trabalhe em worktree isolada se houver conflitos no checkout ativo.
```
Não acessar site de terceiros antes do smoke local.

### 1 — Corrigir somente o boot de TESTE que impede BrowserTask
Nos arquivos `apps/desktop/e2e/fixtures.ts::{setupMockBackend,launchDesktop,waitForAppReady}` e `apps/desktop/e2e/workstation-headless-load.spec.ts::test.beforeAll`, a falha anterior foi `beforeAll timeout 90000ms`, tela `Waking up …/Reconnecting to Hermes…` em `waitForChatReady`, antes de qualquer action Browser. A causa verdadeira do backend ainda é desconhecida. O hook de 90s vs wait 120s foi corrigido no P1 (somente teste).

Rode exatamente:
```powershell
cd C:\Github\hermes-agent\apps\desktop
npm run build
node ..\..\node_modules\@playwright\test\cli.js test --config=playwright.config.ts workstation-headless-load.spec.ts --grep "OL-MVP P1" --reporter=line
```
Se FAIL, usar `[P1/OL-MVP] Electron native smoke blocked {phase,status,reason}`, trace/screenshot e startup do `hermes serve` no sandbox. Identificar **uma** causa comprovada: dist defasado, Python/env/backend mock, gateway/ws, overlay ou Browser controller. Aplicar patch apenas nessa seam e repetir teste focal, **não** aumentar timeout em loop, desativar testes, falsificar handshake ou abrir hardening genérico. Se não for possível provar, informar `BLOCKED_AT_BOOT` com log/trace e seguir para documentação do impedimento, sem escrever PASS.

### 2 — DOM vivo de 3 cartões, SEM depender de Trello
A página local de fixture vem pronta em `apps/desktop/e2e/ol-mvp-p1-readonly-cards.ts`, ligada ao controller pelo teste novo. Verificar navegação real pelo `browser_navigate`, `browser_snapshot(full:true)`, extração de **título/lista/descrição** de cada card e concordância com HTML vivo. O teste inicial exige ao menos os TÍTULOS no snapshot para detectar falta da rota DOM; se snapshots só retornarem URL/title, o teste deve permanecer RED até usar uma leitura DOM tipada autorizada.

Pontos: `apps/desktop/e2e/workstation-headless-load.spec.ts::{startDeterministicPageServer,browserAction,controllerRequest}`, implementação Browser controller no Electron e `workstation/procedure_trace.py`. **Não** transformar `browser_console` arbitrário em receita persistente. A fixture local prova Browser real, mas NÃO prova Trello autenticado nem aprendizado.

### 3 — Ligar o navegador REAL ao Experience Compiler, sem novos motores
Encontre a menor rota para emitir `accepted evidence` do BrowserTask para a compilação existente:
```text
native Chromium BrowserTask read (typed)
  → accepted tool outcome + independent readback
  → procedure_trace.py / accepted_observer.py
  → compilability_monitor.py (real candidate + qualification)
  → run_local_adoption.py / RunLocalAdopter (same canonical TaskRun)
  → batch_runner.py (state refetch, no duplicate)
  → next card read / verified JSON
```
Inspect **only**: `workstation/procedure_trace.py`, `workstation/experience_compiler/{accepted_observer,compilability_monitor,compiler}.py`, `workstation/integrations/hermes/{scoped_execution,run_local_adoption}.py`, `workstation/task_compiler.py`, `workstation/run_adoption.py`. If a missing event adapter is proven, implement one thin adapter within these owners. Never create a second dispatcher/registry/LLM agent.

Real test with natural user instruction: **"Abra o quadro de teste, leia título, lista e descrição de três cartões e devolva JSON. Aproveite automaticamente um procedimento validado para os cartões restantes."**

Minimum verification: one canonical task_run_id, ≥3 cards, results matching live DOM, at least one following card read via **compiled route** if DIRECT legitimately qualified. If SHADOW/insufficient qualification, do NOT flip flag: record exact decline reason and what blocks valid DIRECT admission. Progress can still be marked partial and next phase scheduled, but not FULL_PASS.

### 4 — Segunda TaskRun + contadores reais
Repeat with changed card parameters in a NEW canonical TaskRun. Recover via `OperationalCapabilityRegistry` and `TaskCompiler`; no manual fabricated receipts/promotions. Annotate if cross-run promotion still requires setup of test. Capture available provider usage: `real_llm_calls`, tokens, provider price, learning time, validation time, compiled count, verified result count. Unknown = null. Never claim "40% USD saved" from fixture `fx.system2_calls`.

### 5 — Critério 80/20 e encerramento
PASS se native Chromium real funciona, ≥3 cards verified com as mesmas identidades canônicas, reutilização in-flight confirmada e nenhum efeito duplicado. PARTIAL se qualificação/propagação exige intervenção, mas o erro está isolado e não bloqueia a entrega normal da tarefa. FAIL apenas quando Browser/TaskRun não funciona, existe falsa verificação, autoridade foi burlada ou há reexecução perigosa.

Não rodar suite completa; rodar teste P1 focado, Python focal (7 casos) e no máximo regressões adjacentes às mudanças reais. Não implementar quatro ImprovementRuns, index vetorial, GUI, n8n, SourceResearch autopatch ou nova camada de hardening neste PR.

## Entrega final e commit
Atualizar `workstation/context/ol-mvp-2026-10-16/P1_EVIDENCE_GATE.md`, `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` e `workstation/context/engineering-journal/CURRENT.md` com resultados VERDADEIROS. Criar journal de P1 para evidências linkadas.

Entregar commit/branch/PR draft, tabela com `P1.0 boot`, `P1.1 native DOM`, `P1.2 in-flight`, `P1.3 cross-TaskRun`, `P1.4 cost` (PASS/FAIL/PARTIAL/NOT_RUN) e logs/evidence refs. Se uma etapa falhar, relatar causa causal e próxima mudança pequena. **Não anunciar release nem fazer merge main.**

**Meta 80/20: provar UM fluxo operacional verdadeiro, não construir um sistema de testes perfeito.**

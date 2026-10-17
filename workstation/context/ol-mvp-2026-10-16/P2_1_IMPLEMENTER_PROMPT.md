# PROMPT DE IMPLEMENTAÇÃO — HERMES WORK P2.1 (80/20): ADOTAR E RECUPERAR CAPACIDADE REAL

**Missão:** continuar o trabalho que JÁ completou duas TaskRuns de leitura no Electron, transformar esse resultado em primeira prova de `adaptive → compiled → verified` e tentar a recuperação em uma TaskRun posterior, sem construir novos engines. Sem perguntas arquiteturais: as decisões D01–D19 são suficientes. Faça melhorias pontuais enquanto testa.

## REFERÊNCIAS E GIT — PRIMEIROS 5 MINUTOS
Repositório `kevynlucasprofissional-stack/hermes-agent`.
Checkout habitual `C:\Github\hermes-agent`. PR #96 `docs/ol-mvp-p2-reconciliation-20261017` base remota `6c5963b4f4cafa9b4d12c66690571d3b3d9021a0`. Branch documental deste handoff `docs/ol-mvp-p2-1-native-adoption-20261017`. **Não assumir que remote contém patch local P2.0.** Desktop Commander estava offline na preparação. O usuário relatou E2E `--grep "OL-MVP P2"` 1/1 PASS, 52,8 s, dois planos/TaskRuns distintas, 6 WorkItems COMPLETED, browser card readbacks e regressões 8/8,40/40,7/7, health 0. Tudo isso é evidência do RELATÓRIO, não resultado que você deve copiar cegamente para o GitHub como prova sua.

```powershell
cd C:\Github\hermes-agent
git status --short --branch
git log -5 --oneline
git worktree list --porcelain
git stash list
git diff --stat
git ls-files --others --exclude-standard
```
Ler `AGENTS.md` e claims ativos antes de editar. Encontrar a cópia de `apps/desktop/e2e/workstation-headless-load.spec.ts` com teste `OL-MVP P2`, último `ol-mvp-p2-native-chat-work-execute-evidence-*.json` em `apps/desktop/test-results`, alterações em `scoped_execution.py`, `task_compiler.py`, `run_local_adoption.py`, `corpus.py`, `progressive.py`, `tool_observer.py` e docs. **Preservar e commitar somente seu escopo em branch/worktree isolada.** Não reset, clean, stash pop, força de checkout/push, reverter CW-047 ou copiar código P1C sintético.

**Script read-only já pronto:** `workstation/context/ol-mvp-2026-10-16/patches/P2_1_SAFE_PREFLIGHT.ps1` executa somente `git status/log/worktree/diff/ls-files`, descobre o último JSON E2E e exibe só nomes de chaves (não DOM). Execução:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Github\hermes-agent\workstation\context\ol-mvp-2026-10-16\patches\P2_1_SAFE_PREFLIGHT.ps1" -RepoRoot "C:\Github\hermes-agent"
```
O script foi criado nesta branch documental, **não executado no Windows remoto**. Não confundir com qualificação de resultado.

Ler SOMENTE:
- `workstation/context/ol-mvp-2026-10-16/P2_1_NATIVE_ADOPTION_PLAN.md`
- `workstation/context/ol-mvp-2026-10-16/P2_1_PATCH_MAP.md`
- `workstation/context/ol-mvp-2026-10-16/DECISIONS.md`
e depois APENAS os arquivos de código mencionados no mapa. Não repetir auditoria de 20 mil arquivos.

## ESTADO APROVADO PARA AVANÇAR (NÃO REFAZER)
- O Browser Electron, chat/Gateway, navegação, `work_execute` com 3 extrações READ-ONLY e readback independente já FUNCIONAM no E2E reportado.
- `capture_raw_result` import, `canonical_run_id`, BrowserTask ID e WorkItem `COMPLETED` foram corrigidos localmente segundo relatório. **Verificar se patches já existem antes de tocar.**
- A segunda TaskRun do E2E teve novos parâmetros e terminou 3/3, **mas isso NÃO prova que selecionou ou reutilizou uma capacidade compilada**. O scripted mock provider implica tokens/custo reais `null`.
- Stage A foi autorizado explicitamente como `PASS_WITH_AUTORIZATION` durante desenvolvimento, mas Stage A não é autorização automática de DIRECT nem promoção global. `SourceResearchRun` jamais altera fonte operacional sem aprovação humana.

## 1. AUDITAR PRIMEIRO O RESULTADO DA PRÓPRIA EXECUÇÃO (SEM NOVO TESTE)
Inspecionar um único JSON `ol-mvp-p2-native-chat-work-execute-evidence-*.json` do último E2E e cruzar cada `task_id/run_id/plan_id/item_id/operation_id/raw_result_ref/transition_ref/readback_ref` com SQLite/ArtifactStore reais, usando os métodos owners existentes. São duas TaskRuns, seis WorkItems COMPLETED; distingua os itens `adaptive` vs `compiled` **pelo dispatcher/receipt efetivo**, não pelo status de conclusão ou por `reused=True` em flag de teste. Se não houver prova de compiled, classificar esse E2E como P2.0 PASS / P2.1 NOT_PROVED.

## 2. APENAS SE FALTAR CANDIDATO: CORRIGIR A PRIMEIRA LIGAÇÃO CAUSAL
Reutilize `workstation/integrations/hermes/tool_observer.py`, `experience_compiler/{progressive,corpus,compilability_monitor}.py`, `integrations/hermes/run_local_adoption.py`, e `workstation/task_compiler.py`.
O primeiro cartão deve gerar resultado bruto persistido → readback independente owner → amostra canônica `VERIFIED_SUCCESS` da MESMA operação → candidata. Não aceite tool ACK nem `last sample` de outra operação; `completed=3` não substitui `accepted sample`.
Se falha, capture a reason code e ajuste SÓ esse seam. Caso a candidata exista, não reabrir compiler.

## 3. PRIMEIRA ADOÇÃO NO MESMO RUN (PRIORIDADE DO PROJETO)
No checkpoint entre itens que JÁ existe, conferir `create_safe_item_boundary_callback` → `workstation_run_local_checkpoint` → `RunLocalAdopter.run_checkpoint`. Verificar se candidato é QUALIFICADO para DIRECT por regras reais; se `SHADOW`, sem evidência suficiente ou Stage A limitado, **não forçar**. Repetir 1 teste somente após corrigir a razão causal.
**PASS de in-flight** exige: `item_id` posterior foi despachado pelo owner compilado, recusa/allowlist/lease preservados, `run_local_reuse_*.json` do runtime com refs reais e readback verificado; worker adaptativo NÃO executou o mesmo item duas vezes. Se impossível por autorização, registrar PARTIAL e manter trabalho do usuário completo via adaptive.

## 4. SELEÇÃO ENTRE TASKRUNS SEM DUPLICAR O ROUTER
**IMPORTANTE:** no HEAD do PR #96 que inspecionamos, `workstation/control_plane/router.py::CapabilityRouter.route` já executa `_rebuild_index()`, `_index.candidates(target_family,operation_family,family_id)`, fallback promovidas e System-1 opcional, sob checagem de contrato, goal, efeitos, policy, autoridade e verificador. `workstation/task_compiler.py::_execute_route` JÁ chama esse Router e `CertifiedDispatcher`; `execute()` tem `OperationalCapabilityRegistry.find_matching` para `operation_fingerprint`, **mas `operation_intent` é tratado antes**. Não adicionar novo `registry.find_matching` dentro de `operation_intent` automaticamente; primeiro comprove por que o Router existente não selecionou.
- Uma terceira solicitação/TaskRun (ou duas novas isoladas se o teste atual não prova) usa novos `card_id`/seletores mas MESMA família e contrato estável `browser_extract_items`.
- A intent vem do ingresso canônico, não de `operation_fingerprint` fabricado. Comparar metadados de `operation_family, target_family, family_id`, contrato formal, `PROMOTED`, `healthy`, escopo host/path, versões, pre/postconditions, autoridade e `readback`.
- Quando Router retorna `ExecutableDecision` com certificado válido, o `CertifiedDispatcher` existente executa a capacidade e valida o resultado. `SATISFIED` não é reuso; `ReasoningDecision` não deve acionar replay. Em ausência de qualificação ou candidato, abstém e encaminha reasoning/SHADOW.
- Corrija apenas a **primeira incompatibilidade real comprovada** (ex.: metadados da capacidade, contrato, ligação do owner). Não criar outro Router, executor, registry ou novo banco.

## 5. MÍNIMO DE TESTES E MÉTRICAS
Use o MESMO teste E2E `apps/desktop/e2e/workstation-headless-load.spec.ts` `--grep "OL-MVP P2"` e acrescente asserção focada em `adaptive vs compiled` com receipt do owner. Não recriar harness nem revalidar o boot de Electron. Se tocar no Router, estenda SÓ testes adjacentes `workstation/tests/test_e2e_operational_resolution.py` e `test_operational_resolution_provider.py`; testar `known promoted`, `no certificate`, `uncertain mutation`, `quarantined` e `verifier failed`. Se tocar na adoção, rodar `test_ol_mvp_inflight_boundary.py`.
Smoke:
```powershell
python scripts/run_tests_parallel.py workstation/tests/test_ol_mvp_inflight_boundary.py
python scripts/run_tests_parallel.py workstation/tests/test_e2e_operational_resolution.py
python scripts/check --only health
cd apps/desktop
node ..\..\node_modules\@playwright\test\cli.js test --config=playwright.config.ts workstation-headless-load.spec.ts --grep "OL-MVP P2" --reporter=line
```
Rode apenas arquivos impactados, não suíte geral. Capture tasks/refs das DUAS Runs, candidate version/qualificação/adoption e motivo de fallbacks. `real_llm_calls/tokens/cost=null` para scripted mock provider, sem supor economia paga. Não habilitar chamadas pagas autônomas sem teto definido pelo usuário.

## 6. FINALIZAR 80/20
Se o E2E comprovar in-flight compilada e reutilização na Run seguinte por Router/Kernel: **GO P2.2**, mesmo que 1 fluxo não esteja perfeito. Se completar tarefas com SHADOW e candidate mas DIRECT bloqueado por autorização: **PARTIAL**; avançar SOMENTE documentação/telemetria/seleção SHADOW, sem dizer que a automação aprendeu execução autônoma. Se faltou binding de amostra/owner/identidade: **HOLD técnico focal**, corrigir um ponto.

Commit/push na branch certa, sem merge main, com cuidado com claims. Atualizar `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`, `workstation/context/engineering-journal/CURRENT.md`, journal P2 e evidência JSON com refs auditados. Reportar checklist: P2.0 native WorkItems PASS, P2.1 accepted sample/candidate/qualificação/adopted/retrieved cross-run (PASS/PARTIAL/HOLD), provider usage null ou real, commit/PR e próximo GO.

**A meta é obter o primeiro recibo de capacidade APRENDIDA E REUTILIZADA em uma TaskRun real, não apenas processar seis cartões com o mesmo executor adaptativo.**

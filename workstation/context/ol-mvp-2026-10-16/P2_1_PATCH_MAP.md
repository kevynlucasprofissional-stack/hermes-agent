# OL-MVP P2.1 — Mapa técnico de owners e patches condicionais (17/10/2026)

Este mapa é baseado no código remoto PR #96 HEAD `6c5963b4`, mais o relato P2.0 local enviado pelo usuário. Os patches P2.0 não estão disponíveis remotamente nem pelo Desktop Commander nesta sessão. **Inspecione diffs locais antes de substituir qualquer método.**

## Ownership já confirmado no GitHub

| Ordem | Código e função | Ação exata do implementador |
|---|---|---|
| 0 | `AGENTS.md` + `git status/log/worktree/branch` | Verificar claim/local dirty tree, localizar P2.0 e publicar só o que é do seu escopo. Não restaurar stash P1C indiscriminadamente, nem mexer em CW-047 ou outros trabalhos. |
| 1 | `workstation/integrations/hermes/scoped_execution.py::workstation_durable_dispatch` | O remoto PR #96 **ainda não importa** `capture_raw_result`; o log P2.0 diz que patch local já corrigiu. Conferir presença e não duplicar; BrowserTask vs canonical TaskRun, no lease bypass. |
| 2 | `workstation/task_compiler.py::TaskCompiler.execute` | Verificar `canonical_run_id` local, WorkItem COMPLETED, `request["operation_intent"]` conduz primeiro a `_execute_route`; já existe lookup `operation_fingerprint` somente na rota `sem operation_intent`. Não copiar lookup para branch de intent sem evidência causal. |
| 3 | `workstation/integrations/hermes/tool_observer.py` + `experience_compiler/{progressive,corpus}.py` | Conferir trace e outcome de cada `browser_extract_items`; `raw_result_ref/transition_ref` da mesma operação e `accept_work_item` com owner receipt, sem `candidates[-1]`/synthetic sample. |
| 4 | `workstation/integrations/hermes/run_local_adoption.py::{create_safe_item_boundary_callback,workstation_run_local_checkpoint,build_run_adoption_owner}` + `workstation/run_adoption.py::RunLocalAdopter.run_checkpoint` | Primeiro local de código se candidato existe mas nenhum item é adotado. Diagnosticar SHADOW, falta de offer, critérios e lease antes de editar; nunca falsificar DIRECT. |
| 5 | `workstation/control_plane/router.py::CapabilityRouter.route` (candidatos por famílias a partir da linha ~379 no SHA remoto) | **JÁ** possui index e seleção de `PROMOTED`; `_index.candidates(target_family,operation_family,family_id)` e fallback `registry.list_capabilities`. Com múltiplos, System-1 opcional. Não criar novo Router ou novo `registry.find_matching` na intent sem necessidade comprovada. |
| 6 | `workstation/task_compiler.py::_execute_route` (~1051) | Resolve `OperationIntent` → `CapabilityRouter.route` → `CertifiedDispatcher` → `_execute_capability`. Entra aqui um candidate legítimo de nova Run, não executa por match sem certificado. |
| 7 | `workstation/integrations/hermes/operational_resolution.py::_established_intent`, `workstation_operational_resolution` | Pré-LLM já chama `_dispatch_intent`; resolve somente owner task+goal de forma canônica, nunca texto cru inventado. Se o novo objetivo não chega, corrigir contrato/metadata de intent, não adicionar outra engine. |
| 8 | `workstation/operational_capabilities.py::OperationalCapabilityRegistry.find_matching` | Match por `route, semantic_fingerprint, scope, promoted_only`. Aplicável a requests com `operation_fingerprint`; esse não é o mecanismo único de Router de intent. Recusar candidate DISCOVERED/SHADOW quando `promoted_only=True`. |
| 9 | `workstation/tests/test_e2e_operational_resolution.py` e `test_operational_resolution_provider.py` | Testes pré-LLM já existem para `KNOWN PROMOTED`, `OUTSTANDING UNCERTAIN`, `NO CERTIFICATE`, `VERIFY FAIL`. Estender SÓ um teste usando candidate read-only do Browser se integração exigir; usar fixture já existente. |
| 10 | `apps/desktop/e2e/workstation-headless-load.spec.ts` + `ol-mvp-p1-readonly-cards.ts` | Reaproveitar `--grep "OL-MVP P2"`; a sonda local reportada já cria 2 TaskRuns e 6 WorkItems e valida owner readback. **Adicionar no mesmo teste** uma assertion de resultado de seleção/adocão, sem copiar o controller/harness. |

## Instrumentação focal (pseudocódigo, não colar antes de verificar API)
```python
# Junto ao callback legítimo da adoção por WorkItem:
candidate = qualified_offer_from_runtime_owner(...)  # usa API REAL existente
if candidate is None:
    record_decline("NO_QUALIFIED_OFFER")  # registrar, continuar adaptativo
else:
    adoption_report = existing_run_local_checkpoint(...)  # invocação EXISTENTE
    # Provar dispatch compilado pelo owner e readback. Não criar recibo em teste.

# Na NOVA TaskRun, request contém OperationIntent canônica:
decision = existing_capability_router.route(intent, state, trusted_authority, ...)
# O Router JÁ faz candidate search e admission.
# Se não executar, persistir reason/certificate e depurar lacuna exata.
```
As funções `qualified_offer_from_runtime_owner` e `record_decline` acima são **placeholders de localização**, não APIs reais. Consultar `compilability_monitor.py` e callback de `run_local_adoption.py` antes de escolher a menor chamada já implementada. Não adicionar método com esse nome por hábito.

## Teste obrigatório para distinguir resultado de reuso
O E2E P2.0 pode passar com **6 WorkItems adaptive**. P2.1 exige um evento independente de `compiled_adoption` do próprio owner e, para cross-run, resultado de `CapabilityRouter` com certificado válido + readback.
**Uma decisão `SATISFIED` não é adoção**; `routing_decision=EXECUTE` sozinho não basta; `candidate DISCOVERED` não é `PROMOTED`. O mesmo resultado `completed=3` não diz qual rota trabalhou.

## Comandos de smoke (a confirmar no worktree)
```powershell
python scripts/run_tests_parallel.py workstation/tests/test_ol_mvp_inflight_boundary.py
python scripts/run_tests_parallel.py workstation/tests/test_experience_compiler.py
python scripts/run_tests_parallel.py workstation/tests/test_durable_agent_integration.py workstation/tests/test_durable_learning_checkpoint.py
python scripts/run_tests_parallel.py workstation/tests/test_e2e_operational_resolution.py
cd apps/desktop
node ..\..\node_modules\@playwright\test\cli.js test --config=playwright.config.ts workstation-headless-load.spec.ts --grep "OL-MVP P2" --reporter=line
```
Não disparar todos de saída: primeiro o novo smoke P2.1 com 1 ciclo, depois Python adjacente se código for alterado. Registrar Git SHA, run IDs e refs no resultado; scripted mock provider → custo real `null`.

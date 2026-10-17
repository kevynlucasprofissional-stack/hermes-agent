# P1C — Mapa de código exato e prioridade de alterações

### Código RED já preparado (não instalado)
`patches/test_P1C_strict_read_acceptance.py` contém três casos negativos para `ExperienceCorpus.accept_work_item` (amostra inexistente, `operation_id` divergente e `raw_result_ref` divergente). Copiar para `workstation/tests/test_p1c_strict_read_acceptance.py`, executar RED e corrigir EXCLUSIVAMENTE a correspondência de amostra/ref com fail-closed. Este código está em docs/patches e não foi executado contra o runtime — não alegar PASS. O helper `P1C_evidence_gate.py` e seus seis testes são estruturais e separados.



Base `docs/ol-mvp-p1c-native-taskrun-20261016` sobre `docs/ol-mvp-p1b-read-output-20261016@27b6376535dc` PR #94. **Não modificar main nem sobrescrever worktree da IA anterior.**

| Ordem | Owner/arquivo | Ação mínima e critério |
|---|---|---|
| 0 | `apps/desktop/e2e/workstation-headless-load.spec.ts` + `apps/desktop/e2e/fixtures.ts` | Reutilizar boot/navegador P1.0. Novo caso focal precisa passar pelo **chat/Gateway → work_execute** real; a chamada direta a `controllerRequest` é somente baseline |
| 1 | `workstation/task_compiler.py::execute_batch`, `workstation/integrations/hermes/scoped_execution.py::workstation_scoped_execution` | Garantir 3 WorkItems da mesma TaskRun e `on_safe_item_boundary` canônico, sem worker sintético |
| 2 | `workstation/integrations/hermes/tool_observer.py::workstation_raw_post_tool_observer` | Operação `op_id`, `raw_result_ref` e `transition_ref` do I/O real; não usar `_last_*` de outra operação |
| 3 | `workstation/integrations/hermes/run_local_adoption.py::{dispatch,canonical_source_for_readback,_readback_browser_extract_items}` | A leitura já funciona. Recusar se IDs/referências não coincidirem com dispatch *atual* + persisted raw receipt; manter 4 inspeções e fail closed. **Não fabricar op_id/raw/trans** quando faltarem |
| 4 | `workstation/experience_compiler/corpus.py::accept_work_item` | Exigir sample/transition_ref canônico exato à operação e conteúdo/raw receipt; **remover fallback `candidates[-1]` / fabricação de `TransitionSample` para produção**, teste negativo para ausência/mismatch. Não converter tool ACK em VERIFIED |
| 5 | `workstation/experience_compiler/compilability_monitor.py` + `workstation/integrations/hermes/run_local_adoption.py::create_safe_item_boundary_callback` | Offer SHADOW/DIRECT real e provenance rastreável. Sem criar atestação/credencial DIRECT a partir de testes |
| 6 | `workstation/run_adoption.py::RunLocalAdopter`, `workstation/operational_capabilities.py` | Provar pelo `run_local_reuse_*.json` do próprio runtime que o WorkItem seguinte foi executado por compiled route, não `worker()` |
| 7 | `workstation/integrations/hermes/operational_resolution.py` / `workstation/task_compiler.py` | Nova TaskRun, consulta capability em registry durável com outros inputs e verificação final; sem semear candidatos no teste |
| 8 | `workstation/telemetry.py` | Usage real por provider quando disponível; não inferir tokens/USD de contadores de fixture |

### Snippets orientativos (NÃO patches aplicáveis cegamente)
**Vinculação causal no owner:** a origem do readback só pode ser resolvida do dispatch canônico da mesma operação. Padrão:
```python
# Só depois que o owner persistiu o raw e a TransitionSample para ESTA operação:
record = verified_runtime_operation_index.get(current_operation_id)
if record is None or record.task_id != task_id or str(record.run_id) != str(run_id):
    return {"ok": False, "evidence_ref": None}
if not record.raw_result_ref or not record.transition_ref:
    return {"ok": False, "evidence_ref": None}
# Resolver ambos no ArtifactStore e comparar schema, operation_id, conteúdo e owner.
# NUNCA escolher last sample, criar op_id com uuid ou sintetizar receipt.
```
`verified_runtime_operation_index` é pseudocódigo; **não existe com esse nome** no repositório. O implementador deve reutilizar a captura/instrumentação já existente ou, se indispensável, criar um índice *run-local mínimo* no owner. Não introduzir banco novo.

**Aceite seguro:** no `ExperienceCorpus.accept_work_item`, após recuperar o `evidence_ref`:
```python
# Remover caminhos de fallback ao sample de outra operação.
trans_ref = body.get("transition_ref")
if not isinstance(trans_ref, str) or not trans_ref.startswith(f"artifact://tasks/{task_id}/"):
    return None
# Resolva o sample, conferindo o schema hermes.transition_sample.v1 e
# matching exato de task_id/run_id/operation_id/raw_result_ref + readback/ref.
# Só depois use deepcopy(sample) e projete os predicados read.*.
```
Não tratar esse snippet como verificador de integridade completo. Os valores do artifact e a identidade devem ser confirmados pelo owner.

**Teste do ciclo real:** `test_ol_mvp_p1b_cards_workitems.py` é sintético. Fazer um novo teste focal que NÃO chama manualmente `capture_progressive`, `readback_fn`, `notify_online_compilability`, `mine_candidate_in_run` ou `RunLocalAdopter`. O pedido deve entrar pelo Desktop/Gateway normal. Inspecionar `apps/desktop/e2e/workstation-headless-load.spec.ts` e fixtures de chat atuais; trabalhar por similaridade, sem inventar endpoint.

### Comandos de sanidade e prova (PowerShell no worktree)
```powershell
git status --short --branch
python -m pytest -q workstation/tests/test_run_local_owner_factory.py workstation/tests/test_run_local_card_readback.py workstation/tests/test_read_output_contract.py workstation/tests/test_run_local_browser_effect_authority.py workstation/tests/test_browser_extract_compilation.py workstation/tests/test_ol_mvp_p1b_cards_workitems.py
python -m pytest -q workstation/tests/test_ol_mvp_inflight_boundary.py workstation/tests/test_in_flight_handoff.py workstation/tests/test_online_compilability_safety.py
# Smoke Electron já passou no P1.0; somente rodar UM caso novo de gateway + TaskRun.
cd apps/desktop
node ..\..\node_modules\@playwright\test\cli.js test --config=playwright.config.ts workstation-headless-load.spec.ts --grep "OL-MVP P1C" --reporter=line
```
O último comando é objetivo de integração: **o teste com esse grep ainda não foi criado neste pacote**. Caso Gate Stage A bloqueie um uso real de DIRECT, documentar recusa e prosseguir na rota adaptativa. Não forçar política.

### Local do recibo
`workstation/context/ol-mvp-2026-10-16/evidence/P1C_NATIVE_TASKRUN_RESULT.json` deve conter conteúdo produzido e conferido pelo implementador, NÃO ser gerado preenchendo manualmente sucesso.

Validador independente: `python workstation/context/ol-mvp-2026-10-16/patches/P1C_evidence_gate.py <recibo.json>`; **não comprova autenticidade nem libera execução**.

**Escopo proibido nesta etapa:** reconstruir P0/P1.0, reescrever BrowserRuntime, novo compiler, n8n, sistema de vetores, LAYA obrigatório, 4 ImprovementRuns, novo banco, merges/autoautorizações.

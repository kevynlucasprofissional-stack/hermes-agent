# P1B — Instruções de patch quase plug-and-play

## Código preparado / verificado
- `patches/P1B_read_output_contract.py` → futuro destino `workstation/experience_compiler/read_output_contract.py` (não instalado, Stage A pendente).
- `patches/P1B_test_read_output_contract.py` → futuro destino `workstation/tests/test_read_output_contract.py`. Adaptar linha de import para `from workstation.experience_compiler.read_output_contract import ...`. Já executados 5 testes unittest em sandbox Windows: **5 PASS**.
- Sem qualquer alteração dos módulos runtime acima; são **propostas** prontas para copy/replace quando autorizado.

## Instruções exatas de integração após autorização
1. **Canonical owner/verifier:** em `workstation/integrations/hermes/run_local_adoption.py`, criar `_readback_browser_extract_items(dispatch,artifacts,task_id)` que dispara uma segunda leitura nativa tipada da mesma identidade BrowserTask, com `selector`, `limit`, `attributes` limitados e operação marcada read-only. Obter campos completos de cards por um DOM-read de owner; vincular canonical task/run/operation, `raw_result_ref` e id de BrowserTask. Sem credencial/reutilização de macro opaca. Persistir `hermes.browser_live_readback.v1` no ArtifactStore, com `observer`, `source_kind`, `trust_class`, freshness e status determinado por comparação real. O code `P1B_read_output_contract.py` normaliza e compara os textos.
2. **Aceitação:** em `workstation/experience_compiler/corpus.py::accept_run`, encaixar um ramo `elif last.operation.primitive == 'browser_extract_items' ...` ANTES do `return None` do fallback atual; exigir `outcome.status == verified_completed`, `not outcome.uncertain_mutation`, `outcome.evidence_refs` conter artifact do owner, `verifier_results.passed=True`, `evidence_ref` ligado à mesma TaskRun/operation/raw result, schema certo e readback tipado independente. `resolve_structured` ANTES de `guarded_projection`. Só então atualizar no clone `revised.state_after.semantic_predicates` com invariantes e `revised.verification.verified_predicates`, preservando provenance, evidence_strength e verificação independente. Não conceder `VERIFIED_SUCCESS` apenas por helper.
3. **Fechamento entre WorkItems:** `accept_run` atualmente fecha a TaskRun toda; ligar uma aceitação **por item** ao callback de `DurableBatchRunner` já presente, com o mesmo owner e contrato, persistindo novo `TransitionSample` e chamando `notify_canonical_acceptance` antes de tentar `RunLocalAdopter`. Não falsificar `verified_completed` para item; exigir estado durável de item + validator + readback de owner.
4. **Compiler:** `state_abstraction.py` já suporta `SemanticState`; usar `StateDelta.between` no clone com invariantes de resultado aceito. Em `segmentation.py::segments` manter gate `VERIFIED_SUCCESS` e predicados verificados; se necessário aceitar fechamento de leitura **apenas** sob `browser_extract_items`/read-only com `read.output_shape` verificado. `generalization.infer_action_model` receberá `read.output_shape` e `read.fields_complete` como efeitos de *resultado*, sem mutar DOM. `compiler.compile` já tem browser_extract_items em _PRIMITIVES; não ampliar efeitos de outras ferramentas.
5. **RunLocalAdopter:** alterar as duas allowlists `_SUPPORTED` e `_READBACK` apenas depois de a função de readback indep. e testes negativos funcionarem. A função `_build_readback_fns` deve devolver `browser_extract_items` → handler testado. Não incorporar `_readback_browser_snapshot` atual: ele usa resposta RAW e nem está em `_READBACK`. Trocar só primitives read-only, nunca mutable.
6. **Teste de produto:** uma TaskRun real com 3 WorkItems (um extrator tipado por card), depois uma TaskRun com novos IDs; receipt comprova cada item e route adaptive/compiled. Se Stage A/DIRECT não liberado, marcar parcial; não burlar.

## Snippet para append somente após verificação REAL de recibo
```python
# Dentro do branch de aceitação da leitura no ExperienceCorpus (NÃO antes).
# Assumir canonical owner já conferiu run_id/task_id/operation_id/ref, assinaturas,
# artifact schema/freshness e independently observed DOM values.
from workstation.experience_compiler.read_output_contract import guarded_projection

projection = guarded_projection(
    extraction_payload, independent_dom_rows,
    task_id=outcome.task_id, run_id=str(outcome.run_id),
    operation_id=last.provenance.operation_id,
    raw_result_ref=last.raw_result_ref or last.state_after.artifact_ref,
    owner_readback_receipt=verified_owner_receipt,
)
revised.state_after.semantic_predicates.update(projection["semantic_predicates"])
revised.verification.verified_predicates.update(projection["proposed_verified_predicates"])
revised.delta = StateDelta.between(revised.state_before, revised.state_after)
# revised.outcome = VERIFIED_SUCCESS SOMENTE mediante canonical owner acceptance.
# persistir novo ref via self.capture(revised), atualizar journal e notificar monitor.
```

**Atenção:** `verified_owner_receipt` e `independent_dom_rows` **não são variáveis já existentes** no corpus atual. Devem ser obtidas e verificadas pelo executor owner, não injetadas por um teste ou pelo modelo. O snippet é uma localização de montagem, não um código diretamente aplicável sem a etapa 1. Sua aplicação isolada fabricaria evidência.

## Comandos de aceite
```powershell
# Proposta isolada, já passou:
cd C:\Github\ol-mvp-p1b-scratch
python -m unittest -v P1B_test_read_output_contract

# Depois da instalação AUTORIZADA:
python -m pytest -q workstation/tests/test_online_compilability_safety.py workstation/tests/test_ol_mvp_inflight_boundary.py workstation/tests/test_in_flight_handoff.py
cd apps/desktop
node ..\..\node_modules\@playwright\test\cli.js test --config=playwright.config.ts workstation-headless-load.spec.ts --grep "OL-MVP P1" --reporter=line
```
Somente registrar valores reais. Stage A pendente = não rodar integração em runtime sem autorização.

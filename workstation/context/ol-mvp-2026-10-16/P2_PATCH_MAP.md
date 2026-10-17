# P2 — Mapa de integração 80/20 (17/10/2026)

**Base Git remota:** PR #95 `2b9f7162507cf5db0fe32a7c77fb28f121d1e8f3`. Mudanças P1C do relatório **não aparecem no GitHub**; cada localização abaixo indica onde verificar/aplicar **depois de recuperar o código local**. Nunca cole patches imaginários em interfaces não inspecionadas.

| Ordem | Local existente | Ponto exato / ação permitida |
| --- | --- | --- |
| 0 | `C:\Github\hermes-agent`, `.worktrees`, PR #95 | Obter status/diff/log e localizar mudanças locais, testes, recibo. Commit + push **somente do P1C** após preservar alterações alheias. Evitar reset/clean/force-push. |
| 1 | `workstation/task_compiler.py::TaskCompiler.execute` e `::compile_and_execute` caso exista localmente | Confirmar ingress de gateway/work_execute real, owner canônico, `DurableBatchRunner` 3 WorkItems; verificar se `compiled_reused` é fruto da execução do owner ou apenas uma flag de wrapper. |
| 2 | `workstation/integrations/hermes/run_local_adoption.py::{canonical_source_for_readback,_readback_browser_extract_items,build_run_adoption_owner}` | Garantir que identidade do dispatch, raw, transition e receipt são exatamente a mesma operação. Rejeitar `_last_*` de outra operação e não sintetizar op_id. Readback DOM genuinamente independente. |
| 3 | `workstation/experience_compiler/corpus.py::accept_work_item` | Confirmar que recibos de leitura precisam resolver sample e raw REF de mesma `task_id/run_id/operation_id`. Rejeitar fallback `candidates[-1]` ou sample construído; não converter ACK em VERIFIED. |
| 4 | `workstation/experience_compiler/promotion.py::ExperiencePromotionPolicy` e `::PromotionGate` SE implementado localmente; `workstation/operational_capabilities.py::record_validation/promote` | Candidata ≠ promovida/qualificada. Qualquer nova facade `PromotionGate` não pode ignorar política de promoção ou emitir autorização de DIRECT. |
| 5 | `workstation/experience_compiler/compilability_monitor.py`, `workstation/run_adoption.py::RunLocalAdopter.run_checkpoint` | A adoção só é comprovada por owner, oferta qualificada e receipt real correlacionado ao WorkItem seguinte; `run_local_reuse_*.json` criado manualmente no wrapper não basta. |
| 6 | `workstation/integrations/hermes/operational_resolution.py`, `workstation/operational_capabilities.py::find_matching`, `workstation/task_compiler.py::_execute_route` | Próxima funcionalidade P2: recuperar intenção via fingerprint/contrato/inputs e escolher candidato **antes de System-2**, após router/permission/verifier; ausência de confiança ⇒ abstém. Não criar outro Router. |
| 7 | `workstation/telemetry/` (inspecionar organização real), `workstation/control_plane/metrics.py` | Exportar contagens reais/usage dos owners/provider, não criar DB. Campos desconhecidos `null`; custo líquido só com base verificável. |
| 8 | `apps/desktop/e2e/workstation-headless-load.spec.ts` e `ol-mvp-p1-readonly-cards.ts` | 1 E2E novo usando chat/Gateway e WorkItems verdadeiros. O P1.0 controller-only já provou browser; não basta repeti-lo. |

## Código já entregue nesta branch

`patches/p2_receipt_gate.py` valida estruturalmente o JSON histórico `hermes.ol_mvp.p1c_result.v1` e `workstation.ol_mvp.p1c.evidence.v1`; detecta IDs genéricos (`"real"`), refs para arquivos de teste, ausência de recibo de adoção e de E2E nativo. **Não autentica artefatos, status do Gateway, assinatura de autorização, nem execução.** `patches/test_p2_receipt_gate.py`: 5 testes PASS em Python local, verificar novamente no ambiente Hermes.

### Snippet para classificação de seleção sem novo Router (ILUSTRATIVO, não colar cegamente)

```python
# Dentro do owner de resolução PRÉ-LLM existente, depois de carregar
# objetivo CANÔNICO e verificar ausência de efeito incerto pendente:
# capabilities = registry.find_matching(route=known_route, semantic_fingerprint=trusted_fp)
# candidate = ...  # no máximo candidato compatível com contrato e versão
# if not candidate or not contract_applicable(candidate, runtime_inputs):
#     return CONTINUE_REASONING  # usa enum do módulo real, NÃO criar outro
# result = task_compiler._execute_route(... )  # autoridade/policy no owner existente
# # Sem verification_result.status == VERIFIED e accepted == True:
# # nunca retornar OperationalOutcome.EXECUTED.
```

`find_matching` já existe. `contract_applicable` é **pseudocódigo**, NÃO existe com esse nome no repositório; reutilizar validações de contrato do Router/Kernel em vez de implementá-lo como rota alternativa.

## Definição de feito
- **P2.0**: código P1C recuperado/publicado + relatório objetivo distinguindo teste Python, teste Electron, uso de provider, e estado Stage A.
- **P2.1**: uma capacidade previamente aprendida resolvida e executada sob política em segunda TaskRun; fallback autorizado sem falso sucesso.
- **P2.2**: taxa verificada e custos reais quando disponíveis, sem estimar consumo pago a partir de counters sintéticos.
- STOP após uma vertical read-only em funcionamento satisfatório. Quatro ImprovementRuns/BM25/embeddings/LAYA/vetores permanecem arquiteturalmente documentados, não entregas deste PR.

**Prompt único:** [P2_IMPLEMENTER_PROMPT.md](P2_IMPLEMENTER_PROMPT.md)

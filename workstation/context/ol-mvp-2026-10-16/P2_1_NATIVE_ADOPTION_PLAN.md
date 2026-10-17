# OL-MVP P2.1 — Adocão REAL + seleção por contrato no Runtime existente (17/10/2026)

**Decisão 80/20:** P2.0 (duas TaskRuns reais, 6 WorkItems e readback tipado) é **GO de desenvolvimento**, **não é ainda PASS de aprendizagem/adocão compilada**. Próximo passo: ligar candidato aceito → oferta qualificada → RunLocalAdopter → recuperação numa nova TaskRun, com evidência. Não redesenhar Compiler/Router nem fazer hardening geral.

## Evidências e sua força
- **Do relatório fornecido pelo usuário, não revalidado nesta revisão:** um E2E Playwright `--grep "OL-MVP P2"` reporta 1/1 PASS em 52,8s; Electron/chat/Gateway, 2 TaskRuns distintas, 2 planos, 6 WorkItems `COMPLETED`, 3 cartões por Run; `hermes.browser_card_readback.v1` e `raw_result_ref/transition_ref/browser_task_id` em ArtifactStore. Python focal: 8/8 in-flight, 40/40 Experience Compiler, 7/7 durable; health 0 blocking/advisory.
- **Ainda NÃO demonstrado pelo relatório:** um `run_local_reuse_*.json` do próprio owner provando item posterior executado via capacidade compilada; candidate versionado e qualified offer resolvidos por operação; Router seleccionando mesma capacidade em TaskRun posterior; custos reais de provider (mock). Duas TaskRuns só com execução adaptativa são um avanço de infraestrutura, não prova de menor dependência do modelo.
- **Estado remoto verificado:** PR #96, branch `docs/ol-mvp-p2-reconciliation-20261017`, HEAD `6c5963b4f4cafa9b4d12c66690571d3b3d9021a0`; mudanças de código e evidência E2E **podem existir apenas no checkout local**. Desktop Commander OFFLINE nesta revisão. Não sobrescrever nada nem afirmar que o resultado foi publicado.
- **Stage A:** usuário autorizou `PASS_WITH_AUTORIZATION` segundo anexo de log anterior; isso libera apenas exceção de desenvolvimento explicitamente concedida, NÃO aprova automações `DIRECT` ou promoção global sem política, nem merge main.

## Descoberta crítica da leitura da base remota
`workstation/control_plane/router.py::CapabilityRouter.route` **JÁ** faz `_rebuild_index()` e `_index.candidates(target_family,operation_family,family_id)`, fallback promovidas e, se múltiplas, ranking System-1 opcional; todas passam precondition/goal/effect/authority/certificate e verificador. `workstation/task_compiler.py::_execute_route` já passa a intent via `router.route` e faz `CertifiedDispatcher` e `_execute_capability`. `task_compiler.py::execute` também já possui `OperationalCapabilityRegistry.find_matching` com `operation_fingerprint`, **mas o branch `operation_intent` tem precedência sobre ele**. **NÃO adicionar um novo lookup para `operation_intent` sem prova de falha; verificar primeiro o Router existente.**

`workstation/integrations/hermes/operational_resolution.py` está no boundary pré-LLM; `_established_intent` e `_canonical_task` exigem proveniência/goal; prefab fast path opera antes do registry. `RunLocalAdopter` é a outra frente, para adoção entre WorkItems da mesma Run; não confundir com `CapabilityRouter` de nova Run.

## Uma só vertical, sequência
### A. Recuperação segura / baseline
Inspecionar worktree e branches/claims sem forçar switch; localizar os commits reais do P2.0, a edição em `scoped_execution.py`, `task_compiler.py`, `run_local_adoption.py`, `corpus.py`, `progressive.py`, `tool_observer.py`, teste E2E com `OL-MVP P2` e evidence `ol-mvp-p2-native-chat-work-execute-evidence-*.json`. Publicar somente o conjunto da implementação autorizada em branch apropriada, sem merge na main, com resultados de testes focais. Se concorrência tiver claim, isolar worktree em vez de assumir o checkout.
### B. Auditar uma Run em vez de criar mecanismo novo
Para cada um dos 3 WorkItems da primeira Run, cruzar `task_run_id/item_id/operation_id/raw_result_ref/transition_ref/readback_ref` com ArtifactStore. Confirmar que `accepted` existe **por operação**, não apenas conclusão do plano. Capturar ref de candidata/capability e `qualification_mode`. Se não houver candidata, encontrar primeiro elo causal faltante entre resultado aceito e `notify_online_compilability`, corrigir só este elo. Não confiar apenas em `completed=3`.
### C. Uma adoção run-local de verdade
Usar `create_safe_item_boundary_callback` / `workstation_run_local_checkpoint` / `RunLocalAdopter.run_checkpoint` **existentes**. Candidata não implica DIRECT; se qualificação é SHADOW, só registrar proposta + motivo de recusa e manter execução adaptativa. Caso autorizado legítimo, um dos itens seguintes tem que possuir recibo efetivo de adoção com readback e não pode ter outro dispatch adaptativo do mesmo item. Não criar recibos a partir do teste.
### D. Nova TaskRun / catálogo persistente sem atalhos
Gerar segunda TaskRun com novos card_ids e seletores. Se capacidade já está validada/promovida pelo processo canônico, conferir `OperationalCapabilityRegistry.get/find_matching`, formal_contract, `semantic_fingerprint` e `operation_family/target_family/family_id`, escopo, lifecycle, drift. Testar `CapabilityRouter.route` na mesma intent legítima e `_execute_route`; se a rota não aciona, registrar se foi `no_promoted_candidate`, `missing_formal_contract`, `intent_metadata_mismatch`, `precondition_false`, `goal_not_covered`, `unauthorized` ou `insufficient_readback`. Não fabricar fingerprint, autorização, promotion receipt ou offer. Se tudo está qualificado, a ferramenta executa via Kernel/dispatcher com verificação independente.
### E. Métrica econômica curta
Comparar 2–3 TaskRuns read-only da mesma família, taxas verified, adaptive, compiled `com recibo`, fallback e latência. Mock provider ≠ chamadas/tokens/custo reais; registrar `null` para real_llm_calls/tokens/USD. Nenhuma afirmação de 40%/50% de economia paga.

## Critérios para avançar além da P2.1
- **GO P2.2:** 3 WorkItems reais verificados, ≥1 adoção por `RunLocalAdopter` sob oferta qualificada na MESMA Run e uma segunda Run com capacidade recuperada e verificada; refs reais auditadas. Sem necessidade de 30 casos ou metas de 95% agora.
- **PARTIAL (GO P2.2 somente telemetria/observabilidade):** todas as conexões e candidate provadas, porém DIRECT/promoção humana ainda bloqueada. Não forçar execução. Registar razão única e próximo experimento curto.
- **HOLD técnico focal:** não há amostra aceita por item; browser readback/owner inválido; falsa identidade; dupla execução; provas sintéticas ou perda de TaskRun.
- **NÃO FAZER:** reabrir Electron boot, criar outro Router, usar `explicit_seed.py/explicit_replay.py`, embeddings/LAYA/BM25 obrigatório, quatro ImprovementRuns, scheduler, novo DB, autorrevisão do código-fonte. Essas decisões D01–D19 ficam para etapas futuras.

**Próximo handoff:** `P2_1_IMPLEMENTER_PROMPT.md`, `P2_1_PATCH_MAP.md`; resultados registrados com honestidade no journal.

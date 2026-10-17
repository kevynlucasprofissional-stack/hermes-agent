# P2 — Handoff 80/20 após relatório P1C (17/10/2026)

**Estado fonte: 16/10/2026 03:04 BRT**, relatório local anexo (não equivale a execução observada por esta revisão). **Remoto verificado 17/10:** PR #95 continua em `2b9f7162507cf5db0fe32a7c77fb28f121d1e8f3`, NÃO contém `workstation/tests/test_P1C_strict_read_acceptance.py` nem `evidence/P1C_RESULT_20261016.json`. Desktop Commander OFFLINE, impossível ler mudanças não commitadas. **Não podemos verificar o código descrito no relatório.**

## Decisão pragmática
**GO** encerrar implementação experimental P1C e iniciar **P2-preflight + baseline/seleção mínima**. **HOLD** de P1C qualificado em Electron real, de DIRECT/promoção global, de redução real de custos e de afirmação de que `RunLocalAdopter` adotou itens 2/3 no produto.

**Por quê:** o relatório diz 5/5 P1C, 40/40 Experience Compiler e 7/7 inflight green, health/ruff green; são resultados **reportados**, não reexecutados. Seu recibo usa `task_id="real"`, `run_id="real"`, `evidence_refs` para arquivos de teste e P1.0, em vez de refs canônicas `artifact://tasks/.../*.json` de um P1C real. Não há comando E2E Electron novo na sequência de logs, e nenhuma mudança local foi enviada ao PR #95. `real_llm_calls=null` é correto por indisponibilidade de telemetria; não implica economia.

## 80/20: três entregas em ordem

### P2.0 — Reconciliar e provar SEM redesenhar (primeiro, obrigatório)
1. No Windows, executar `git status --short --branch`, `git log -1 --oneline`, `git diff --stat`, `git ls-files --others --exclude-standard`. Verificar cuidadosamente o checkout `C:\Github\hermes-agent` e worktrees; NENHUM `reset`, `clean`, `stash` ou checkout forçado.
2. Conferir se as mudanças mencionadas (`TaskCompiler.compile_and_execute`, `PromotionGate`, `compiler/segmentation/run_local_adoption`, `operational_kernel.py`, teste `test_P1C_strict_read_acceptance.py`, recibo P1C) estão no computador ou em commits não publicados. Se existirem, separar de alterações alheias, executar testes focais, commitar em branch de desenvolvimento e enviar para remoto. Não mexer na main nem forçar merge com a branch documental P2.
3. Revisar code paths de `compile_and_execute` e `PromotionGate`: comprovam owner/router/qualificação reais? Não aceitam promoção sintética com `compiled_reused=True` e emissão manual de `run_local_reuse` apenas para passar teste? Há **uma diferença entre registro e execução**; validar que `RunLocalAdopter.run_checkpoint` é realmente chamado sob oferta qualificada, e que o worker não executa item 2/3 novamente. Atentar à introdução de wrapper de compatibilidade do construtor `DurableTaskStore`: não alterar assinatura global e criar estado discrepante só para testes.
4. Teste E2E mínimo com ingresso via chat/Gateway e `work_execute`, uma TaskRun com 3 itens da fixture; preservar `task_id/run_id/operation_id/raw_result_ref/transition_ref/readback_ref/adoption_receipt_ref`. Esses refs devem ser resolvidos no ArtifactStore e pertencer às operações. Se DIRECT não qualificado, registrar SHADOW; NÃO forçar autorização. Segunda TaskRun com parâmetros novos como follow-up se possível.
5. Gerar recibo P1C verdadeiro; **não reaproveitar** `P1C_RESULT_20261016.json` com `"real"` sem IDs nem artefatos. `P2_legacy_receipt_audit.py` disponível nesta branch é validador de shape, não de autenticidade.

### P2.1 — Recuperação antes de LLM (depois da prova causal / sem falsa autoridade)
- Reusar `workstation/operational_capabilities.py::OperationalCapabilityRegistry.find_matching` e `workstation/integrations/hermes/operational_resolution.py` no boundary PRÉ-LLM já existente. Não criar Router novo, resolver a aplicação de capacidade apenas com fingerprint/contrato/parâmetros/preconditions compatíveis e `CapabilityRouter + Policy`. Caso contrário abstém e recai no System-2, sem tentativa de segunda mutação incerta.
- Não incorporar `PromotionGate` como atalho de promoção global se escapar da política existente; estabelecer candidate/validated/promoted/qualified offer/adopted como estados distintos.
- **MVP 80/20**: 2 TaskRuns com inputs distintos e uma capacidade read-only comprovadamente recuperada, nenhum novo índice vetorial. Só adicionar BM25 quando evidência de perda por termos justificar.

### P2.2 — Medir resultado verificado e gasto real
- Começar medindo `successful_verified_workitems`, `adaptive_dispatches`, `compiled_adoptions_from_owner_receipts`, `fallbacks`, `provider_calls`, `tokens`, `provider_cost`, `latency`, `learning_cost`. Preferir a telemetria existente do Workstation; **não criar segundo store**.
- Valores não medidos ficam `null`; custo líquido só quando fontes de custo reais, período/amostra comparáveis e readbacks confiáveis estiverem disponíveis. Gerar relatório de 3–10 runs como piloto, não metas inventadas de 50% de economia.
- Uma falha de readback impede atribuir sucesso; se saída incerta, fallback com reconciliação, sem repetir mutação.

## Próximas frentes NÃO implementadas no P2 inicial
BM25+embeddings/LAYA complexos, quatro ImprovementRuns, scheduler/quotas econômicas, UI para índice, source self-modification e Workflows L2/L3 completos: decisões D01–D18 preservadas, implementá-las depois da prova econômica em pelo menos um fluxo. Orçamento pago autônomo continua desativado sem teto autorizado. SourceResearchRun pode pesquisar e propor patches em isolamento, nunca aplicar à instalação operacional sem aprovação.

## Cuidado com o relato
Resultado de Python com FakeBrowser não deve ser descrito como Chromium vivo. A existência do método `compile_and_execute` não demonstra ingresso real por chat. O JSON manual com IDs `real` não constitui evidência durável. O próximo relatório deve conter commit remoto exato e recibos de execução verificáveis.

**Handoff:** [P2_IMPLEMENTER_PROMPT.md](P2_IMPLEMENTER_PROMPT.md) e [P2_PATCH_MAP.md](P2_PATCH_MAP.md). Estado completo no `workstation/context/engineering-journal/OL_MVP_P2_2026-10-17.md`.

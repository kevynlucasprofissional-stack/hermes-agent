# HANDOFF IMEDIATO — HERMES WORK P2 80/20: RECONCILIAR P1C, PROVAR REUSO, MEDIR E RECUPERAR

Você é a IA implementadora. **Não reinicie P0/P1.0/P1B/P1C nem redesenhe a arquitetura.** Execute as operações abaixo em ordem. Prioridade: resultado do usuário, zero falso sucesso, nenhum hardening geral.

## STATUS CONFIRMADO / IMPORTANTE
Repo `kevynlucasprofissional-stack/hermes-agent`.
PR #95 (P1C) está **remotamente** em `2b9f7162507cf5db0fe32a7c77fb28f121d1e8f3`; o relatório do implementador de 17/10 cita alterações em `task_compiler.py`, `compiler.py`, `segmentation.py`, `promotion.py`, `run_local_adoption.py`, `operational_kernel.py`, testes e recibo `P1C_RESULT_20261016.json`, mas **ESSES ARQUIVOS/ALTERAÇÕES NOVAS NÃO CONSTAM DO HEAD REMOTO**. Em particular, `workstation/tests/test_P1C_strict_read_acceptance.py` e `workstation/context/ol-mvp-2026-10-16/evidence/P1C_RESULT_20261016.json` resultaram 404 no PR #95 consultado. Desktop Commander está offline. **Reconciliar ANTES de editar.**

Branch desta documentação: `docs/ol-mvp-p2-reconciliation-20261017`, em PR separado empilhado no #95. NÃO faça checkout/reset por cima do trabalho local. **Preserve** `workstation/durable_tasks.py`, `workstation/dogfood/.obsidian/workspace.json` e quaisquer alterações de usuário.

Relatório IA anterior (ainda não reexecutado): 5 testes P1C PASS, 40 ExperienceCompiler PASS, 7 boundary PASS, code health e Ruff PASS. Recibo dizia `task_id="real"`, `run_id="real"` e `evidence_refs=[caminhos de testes]`: **não é prova canônica** de E2E ou adoção DIRECT real. Nenhum novo E2E Electron pós-P1C identificado no log. P1.0 Browser Electron continua aprovado em E2E histórico.

## 0. Recuperar o código local antes de TUDO (não modificar código ainda)
No Windows:
```powershell
cd C:\Github\hermes-agent
git status --short --branch
git log -1 --format="%H %s"
git worktree list --porcelain
git diff --name-status
git ls-files --others --exclude-standard
git branch --show-current
```
Localizar onde estão `compile_and_execute`, `PromotionGate`, `test_P1C_strict_read_acceptance.py`, `P1C_RESULT_20261016.json`, `run_local_reuse_*.json`. Verificar código e diffs contra `origin/docs/ol-mvp-p1c-native-taskrun-20261016`; se houver mudanças locais, **NÃO** `reset --hard`, `clean`, `stash`, force push, nem recriar sem analisar. Se estiverem em mudanças de usuário, separar em commit de desenvolvimento P1C selecionando SÓ os arquivos de escopo, após testes; push na branch P1C com autorização e sem merge main. Se for branch diferente, preservar e publicar na branch correta para revisão. Registrar commit SHA publicado. Não misturar branches sem checar ancestrais.

Verificar instalação atual de `PromotionGate` e `compile_and_execute` contra implementações existentes de `ExperiencePromotionPolicy`, `RunLocalAdopter` e `TaskCompiler.execute`. Se `PromotionGate` habilitar promoção sem admissibilidade ou `compile_and_execute` registrar `compiled_reused=True` sem owner real, classificar como prova simulada e retirar da conclusão (não reescrever o motor, apenas corrigir a chamada/fonte de verdade). Suspeitar de wrapper de compatibilidade `DurableTaskStore` em `task_compiler.py`; não alterar assinatura global para teste passar.

## 1. Mínimo de validação causal (somente UM fluxo)
**Fazer nova TaskRun na aplicação/Gateway real**, 3 WorkItems separados de cartão somente leitura, usando a fixture já existente `apps/desktop/e2e/ol-mvp-p1-readonly-cards.ts`. Não chamar manualmente compiler/monitor/owner no teste. Fonte de verdade: cada `operation_id` do dispatch, `raw_result_ref`, `transition_ref`, `readback_ref`, `candidate_ref`, `qualified_offer_ref`, e, SE LEGITIMAMENTE AUTORIZADO, `adoption_receipt_ref` do próprio `RunLocalAdopter.run_checkpoint`. Garantir que worker adaptativo não execute novamente item adotado.

A **segunda TaskRun** deve ter outro `run_id` e parâmetros diferentes; nenhum `PromotionGate` chamado no teste para fabricar a promoção. Se modo SHADOW/Stage A sem autorização DIRECT, anotar recusa, executar adaptativamente e declarar PARTIAL. Não usar `"real"` em IDs. E2E nativo e modelo/provider real são provas diferentes; `real_llm_calls=null` é aceitável, economia em USD não comprovada.

Arquivo de teste alvo: `apps/desktop/e2e/workstation-headless-load.spec.ts` ou spec adjacente usando fixture de chat/Gateway existente. Evite reabrir boot já comprovado.

## 2. Ferramenta de triagem de recibos PRONTA
`workstation/context/ol-mvp-2026-10-16/patches/p2_receipt_gate.py` (script pronto, zero dependências externas; NÃO autentica artefatos). `test_p2_receipt_gate.py` tem 5 testes:
```powershell
cd workstation/context/ol-mvp-2026-10-16/patches
python -m unittest -v test_p2_receipt_gate
python p2_receipt_gate.py ..\evidence\P1C_RESULT_20261016.json
```
Quando o JSON local existir, ele deve apontar placeholders, caminhos de testes e ausência de recibos de adoção. **Não altere os critérios para fazê-lo passar.** O script nunca garante AUTHENTICITY/PASS, mesmo com shape preenchido. Validar cada artifact ref no ArtifactStore de verdade.

## 3. P2.1 Seleção conhecida antes da LLM — SEM embeddings agora
`workstation/integrations/hermes/operational_resolution.py` já é boundary pré-LLM, e `workstation/operational_capabilities.py::OperationalCapabilityRegistry` já possui `find_matching` e `get`. Reutilize `workstation/control_plane/router.py`, `TaskCompiler._execute_route` e o dispatch atual. Nenhum segundo Router.

Com TaskRun real verificada, aplique a menor conexão: intenções com fingerprint/contrato/inputs completos → candidatos do registro com versão/lifecycle/escopo compatíveis → autoridade e precondições Router/Policy → exec + independent readback. Incerto/mismatch/sem qualificação ⇒ abstenção + fluxo LLM normal, sem repetir mutação incerta. **Não promover** candidatos apenas por dois testes/ `PromotionGate` novo; seguir a política existente `ExperiencePromotionPolicy`. Primeiro correspondência determinística, depois recuperação lexical simples SE houver evidência real de falsos negativos. BM25, embeddings, LAYA não são dependência da P2 inicial.

## 4. P2.2 Baseline técnico/econômico sem inventar economia
Reusar telemetria existente. Por TaskRun, registrar: `task_id/run_id`, `capability_id/version`, sucesso verificado, count adaptive/compiled *com recibos*, falhas/fallback, chamadas reais ao provider, input/output/cache tokens, tempo, aprendizado/validação, custo por resultado. Dado ausente = null. Comparar mesmo contrato em ao menos duas TaskRuns; não inferir custo a partir de redução de chamadas em fixture. Não criar DB/serviço novo.

## 5. Qualificação e fechamento (não prolongar)
Testes focais P1C (quando código recuperado), `test_experience_compiler.py`, `test_ol_mvp_inflight_boundary.py`, e UM E2E desktop de TaskRun. `python scripts/check --only health` e Ruff apenas nos arquivos tocados. Evitar suíte total, CI amplo ou hardening geral enquanto o caso principal não funcionar.

Atualizar `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`, `workstation/context/engineering-journal/CURRENT.md`, jornal P2 e `DECISIONS.md`. Registrar `P1C_LOCAL_RECOVERED/REMOTE_SHA/NATIVE_E2E/INFLIGHT_REUSE/CROSS_RUN/PROVIDER_USAGE/NET_SAVINGS`: PASS, PARTIAL, HOLD ou NOT_RUN, com REF concreto. PR (pode ser draft) sem merge main; não misturar resultados P1C locais com alterações de docs P2 antes de reconciliar.

## Gates de GO
- GO P2 execução: P1C código reconciliado + uma TaskRun nativa e artefatos reais.
- GO seleção: reusable capability de verdade recuperada em nova TaskRun, sem bypass; caso contrário SHADOW/observabilidade até prova.
- GO economia: usage real de provider atribuível a mesmas famílias e resultados verificados; caso contrário reportar null.
- Stage A, DIRECT, promoção automática, gastos de aprendizagem pagos e source-code self-modification continuam exigindo políticas/autorização correspondentes.

**Não pergunte por novas decisões arquiteturais. O trabalho é reconciliar, provar e reutilizar o que já existe; parar quando estiver decente e verificável.**

# PROMPT PRONTO — HERMES WORK OL-MVP P1C | PROVAR ADOCÃO NO PRODUTO REAL (80/20)

### Testes RED de operação exata já preparados
Antes da fase 2 de vinculação, copie `workstation/context/ol-mvp-2026-10-16/patches/test_P1C_strict_read_acceptance.py` para `workstation/tests/test_p1c_strict_read_acceptance.py` e rode somente esse arquivo em RED. A correção deve fazer 3 testes passarem rejeitando sample inexistente, outra operação e raw_ref trocado. Os testes foram **preparados, NÃO executados** nesta preparação; adaptar somente se APIs concretas divergirem. Não baixar a segurança para fazê-los passar.



Você é a IA executora do Hermes Work. **Execute mudanças e testes; não recomece a arquitetura, não reimplemente P1B, não se concentre em hardening geral.** O objetivo é provar que o código existente trabalha automaticamente no Hermes real.

### Repositório e estado
- Repositório: `kevynlucasprofissional-stack/hermes-agent`.
- Checkout Windows habitual: `C:\Github\hermes-agent`; worktree P1B anterior: `C:\Github\hermes-agent\.worktrees\ol-mvp-p1b`. **Não presuma que estejam limpos nem resete nenhum.**
- PR #94: `docs/ol-mvp-p1b-read-output-20261016`, commit base `27b6376535dcfb92025fd4d468411feb0d7d3a34`, aberto como draft, Stage A pendente.
- Nova branch de preparação e documentação: `docs/ol-mvp-p1c-native-taskrun-20261016` (empilhada sobre #94), contendo este prompt, mapa exato e scripts de auditoria. Use checkout/worktree ISOLADO sem sobrescrever mudanças preexistentes. Não merge main, não conceder DIRECT.
- Data dos relatórios: 16/10/2026. Fonte recente: logs do implementador após commit `27b63765`, PR #94, testes em `workstation/tests`.

### Fatos JÁ COMPROVADOS — não repetir
1. P1.0 Electron Chromium via controller nativo leu três cartões de fixture HTTP loopback e verificou os campos independentemente: E2E 1/1 PASS 21,8s.
2. P1B implementou `_readback_browser_extract_items`, `read_output_contract.py`, suporte read-only no dispatcher, `capture_progressive`, `accept_work_item`, `read.*` e candidato em `ExperienceCompiler`. O relatório informa 30 testes focais (8+8+5+5+3+1, pelos totais de sua tabela) e 53 regressões de segurança aprovados; **não recontar subtests como testes independentes**.
3. `test_ol_mvp_p1b_cards_workitems.py` processa 3 WorkItems, MAS o `worker()` chama `self.dispatch()` sintético para **TODOS OS TRÊS** e minera candidate com chamadas diretas no teste. Esse teste **não** demonstra 2/3 execuções compiladas, `RunLocalAdopter.run_checkpoint()` real, chat/Gateway ou nova TaskRun. Seu docstring foi corrigido no P1C.
4. O Stage A continua pendente. `P1B_STAGE_A_EXCEPTION_20261016.md` permitiu alterações em branch/worktree isolado, NÃO promoveu runtime, nem autorizou testes DIRECT em produto, merge ou release.

### LEITURA OBRIGATÓRIA MÍNIMA
Abra apenas:
- `workstation/context/ol-mvp-2026-10-16/P1C_NATIVE_DOGFOOD_PLAN.md`
- `workstation/context/ol-mvp-2026-10-16/P1C_EXACT_PATCH_MAP.md`
- `workstation/context/ol-mvp-2026-10-16/DECISIONS.md`
Depois inspecione somente os arquivos-alvo citados abaixo, no HEAD. Não audite 200 arquivos; não faça perguntas para redefinir conceitos aprovados.

## ORDEM EXATA DE IMPLEMENTAÇÃO

### 0. Preflight e baseline (rápidos)
```powershell
cd C:\Github\hermes-agent
git status --short --branch
git worktree list --porcelain
git fetch origin docs/ol-mvp-p1c-native-taskrun-20261016
# Se o worktree anterior estiver ocupado ou com modificações, crie OUTRO isolado
# fora de C:\Github\hermes-agent\.worktrees\ol-mvp-p1b e preserve tudo.
```
Rodar teste Python focal do P1B **uma vez** e registrar SHA + resultado. Não rodar a suíte inteira.

### 1. Caso E2E nativo, sem worker fictício — PRIORIDADE ABSOLUTA
Arquivos: `apps/desktop/e2e/workstation-headless-load.spec.ts` + `apps/desktop/e2e/fixtures.ts`, fixture `ol-mvp-p1-readonly-cards.ts`, fluxo de chat/gateway/`work_execute` que já existe; `workstation/task_compiler.py` e `integrations/hermes/scoped_execution.py`.

**Novo teste alvo:** `test('OL-MVP P1C: real TaskRun learns and reuses a native card read', ...)` (adicionar no spec existente ou spec adjacente que compartilhe setup; não copiar BrowserRuntime).

Use uma ÚNICA instrução em linguagem natural entrando pelo gateway real:
> "Abra o quadro de demonstração local, leia individualmente título, lista e descrição dos três cartões, devolva um JSON validado. Aprenda e reutilize a extração nos próximos cartões se estiver validada."

O Hermes precisa criar **três WorkItems** sob UMA TaskRun canônica; **não** uma chamada `browser_extract_items(limit=3)`. Cada card usa selector parametrizado, tipado e leitura via mesma BrowserTask. Não chamar manualmente `capture_progressive`, `readback_fn`, `notify_online_compilability` ou `monitor.mine_candidate_in_run` a partir do teste para fingir que o runtime os chamou.

Teste primeiro apenas: ingresso real → 3 WorkItems → readback/JSON por item, com TaskRun e BrowserTask ligados corretamente. Corrigir só o primeiro seam que falhar.

### 2. Prova causal do primeiro item — NÃO fabricar identidades
Validar para card A, contra `ArtifactStore` REAL:
- canonical `task_id/run_id/operation_id` (diferenciar BrowserTask ID e TaskRun ID)
- raw_result_ref do I/O realmente despachado
- transition_ref capturado naquela operação
- evidence_ref do readback DOM obtido pelo owner
- sample accepted `VERIFIED_SUCCESS` e `read.output_shape`/fields_complete correspondentes.

**Inspect:** `workstation/integrations/hermes/{tool_observer,run_local_adoption}.py`, `workstation/experience_compiler/{progressive,corpus}.py`.

Encontrados dois riscos no código do PR #94: `canonical_source_for_readback` tem fallback criando UUID/raw/trans quando faltam, e `ExperienceCorpus.accept_work_item` cai em `candidates[-1]` ou fabrica TransitionSample. Para PRODUCT EVIDENCE, isso é inadmissível: usar only receipt e sample EXATOS, ou **fail closed e continuar TaskRun pelo caminho normal**. Adicionar testes negativos por operação divergente/stale sample/RAW ausente; patch mínimo, sem nova camada de memória.

O fato de `readback` retornar ok não implica que `accept_work_item` tenha retornado sample aceito. Auditar ambos separadamente; exceções devem aparecer no diagnóstico sem bloquear a tarefa.

### 3. Minerar/qualificar/adotar na MESMA TaskRun
`OnlineCompilabilityMonitor` deve receber evento do owner durante a execução, compilar candidato e avaliar oferta para o WorkItem seguinte. `RunLocalAdopter.run_checkpoint()` executa item compilado quando a política legítima permitir.

**Para declarar adoção real:** exigir recibo `run_local_reuse_*.json` escrito pelo runtime com os refs da mesma Run, a versão/candidate/offer, o item_id do cartão posterior e readback independentemente verificado. Confirmar que worker adaptativo NÃO despachou novamente o mesmo item. **Não basta `mined_during_run` e `candidate.lifecycle=DISCOVERED`.**

Se não houver qualificação DIRECT genuína (Stage A/atestado HMAC), **não fabricar, configurar bypass nem usar `mode=DIRECT` na produção**. Registrar `SHADOW / DECLINED` e motivo concreto, finalizar cartões com rota adaptativa e preservar candidato. O resultado será PARTIAL, não FAIL do navegador.

### 4. Nova TaskRun + custo real
Pedir o mesmo procedimento com **IDs/parâmetros diferentes** em outra TaskRun e verificar uso do Registry/OperationalKernel ou motivo exato de ausência (sem registrar/promover candidate manualmente).
Registrar `provider_usage.real_llm_calls`, tokens e tarifas somente se medidos pelo provedor; em ambiente de modelo mock = null. Não alegar 40% de economia como valor pago. `SourceResearchRun` não pode modificar runtime para resolver este piloto.

### 5. Evidência de produto mínima e entrega
Produzir `workstation/context/ol-mvp-2026-10-16/evidence/P1C_NATIVE_TASKRUN_RESULT.json` **somente a partir de observações verdadeiras**, respeitando o schema no `P1C_NATIVE_RECEIPT_TEMPLATE.json`. Use referências reais do ArtifactStore.
A ferramenta de auditoria **estrutural, não autoritativa** já preparada:
```powershell
python -m unittest discover -s workstation/context/ol-mvp-2026-10-16/patches -p "test_P1C_evidence_gate.py" -v
python workstation/context/ol-mvp-2026-10-16/patches/P1C_evidence_gate.py workstation/context/ol-mvp-2026-10-16/evidence/P1C_NATIVE_TASKRUN_RESULT.json
```
`READY_FOR_HUMAN_EVIDENCE_REVIEW` não significa aprovação; ler os artefatos citados, comprovar integridade/owner/qualificação. Não preencher template só para deixá-lo verde.

Atualizar ROADMAP, HERMES_WORKSTATION_INTELLIGENCE, engineering-journal/CURRENT e journal P1C com status reais:
`native_chat/3_workitems/accepted_sample/candidate/qualified_offer/inflight_adoption/cross_run/provider_usage`.
Cada item: PASS, PARTIAL, HOLD ou NOT_RUN, com ref/resultado. Se a integração estiver só parcialmente completa, descreva UMA causa causal seguinte e interrompa hardening.

### GATES 80/20 / SEGURANÇA
- **GO P2**: existe ao menos uma TaskRun nativa de 3 WorkItems realmente verificados e ao menos uma reutilização compilada por owner com verificação real, mais nova Run com recuperação; nada de duplicação ou permissão artificial.
- **GO P2 LIMITADO**: TaskRun nativa e candidate aceitos; única dependência para adoção é qualificação Stage A/humana não concedida. Registrar P1C como PARTIAL e manter DIRECT/promocão bloqueados. Na P2, só trabalhar em observabilidade/seleção SHADOW, sem afirmar autonomia em produção.
- **HOLD técnico**: ausência de TaskRun nativa, readback fabricado, falsa aceitação causal, candidato isolado sem caminho de execução. Corrigir isso focalmente antes de novas frentes.
- Não reconstruir P0/P1.0/P1B; não implementar embeddings, LAYA obrigatório, BM25 avançado, 4 serviços, scheduler, n8n ou autorrevisão de código nesta entrega.
- Trabalho autorizado apenas em branch/worktree de desenvolvimento. Sem merge main, sem promoção global, sem override DIRECT, sem gastos pagos autônomos sem teto autorizado.

**Meta final:** provar UM caminho real `adaptive → accepted result → compiled → verified reuse` no Hermes Work, com evidências auditáveis, e avançar à P2 apenas dentro da confiança efetivamente demonstrada.

# OL-MVP P1B — Fechar a ponte de resultados de leitura (80/20)

**16/10/2026. Estado:** P1.0 **PASS** em Electron real com HTTP loopback/DOM vivo. P1.1 (TaskRun + compilação/adocão) **HOLD**. P1.2 (outra TaskRun) **NOT_DEMONSTRATED**. Nenhuma economia de modelo aferida. Documento derivado do recibo canônico `evidence/P1_NATIVE_RESULT_20261016.json` no commit `6e1443079e`; usar como evidência e não reexecutar boot/hardening.

## Decisão GO/HOLD
**GO:** parar de mexer no BrowserRuntime; já funciona para extração tipada read-only. **HOLD focal:** não avançar a memória avançada, LAYA, vetor, quatro ImprovementRuns, scheduler ou novas integrações antes de conectar resultado verificado → capacidade executável. O próximo objetivo é P1B e contém apenas UMA família, `browser_extract_items`.

## O que o recibo comprova
1. Electron + Chromium native; 3 cards, `id/list/title/description` confirmados por `browser_extract_items` tipado e leitura DOM independente.
2. E2E 1/1 PASS (21,8s teste final). Build, typecheck e hooks reportados PASS. Há advertência `dirty tree` no recibo, logo não é certificação de build limpo/release.
3. Os três cards foram extraídos por **uma operação em lote**, com IDs de BrowserTask artificiais do teste; **não são três WorkItems canônicos** nem provam reuso entre itens.
4. Não houve `TaskRun` real; identidade canônica, custo de LLM, oferta DIRECT, persistência, recompilação e ganho líquido = ausentes.

## Lacuna concreta no código atual (GitHub commit 6e1443079e)
- `workstation/procedure_trace.py::record_trace`: `browser_extract_items` gera observação `executed_unverified`, mas o resultado não se converte automaticamente num predicado semântico de RESULTADO aceito. `candidate_steps` ignora `extract_items`, o que é correto para macro de navegação mas não pode impedir o `ExperienceCompiler` de tratar uma primitiva tipada de leitura.
- `workstation/experience_compiler/state_abstraction.py::abstract_state`: estado de Browser preserva URL/host/control flags, não a saída estruturada verificada.
- `workstation/experience_compiler/corpus.py::accept_run`: só fecha aceitação em `verified_completed` no final da Run; exceção de readback explícita atual cobre apenas navegação `browser_navigate`. Não há projeção de leitura por WorkItem canonico.
- `workstation/experience_compiler/segmentation.py::segments`: exige mudança semântica; leitura pode não alterar a página.
- `workstation/experience_compiler/generalization.py::infer_action_model` + `compiler.py::compile`: efeitos são delta de estado e o compilador recusa `no stable verified semantic effect`.
- `workstation/integrations/hermes/run_local_adoption.py`: `_SUPPORTED` e `_READBACK` não admitem `browser_extract_items`; lista `_build_readback_fns` não tem verificador independente para extração. Estender allowlist ANTES de verificação real seria regressão de autoridade.

## Plano de implementação em ordem, sem novos engines

### B0 — Garantir um evento por WorkItem real
- Reusar `TaskCompiler` + `DurableBatchRunner` para três itens com seletores diferentes na MESMA Run canônica. A fixture HTML já serve; agora cada WorkItem deve extrair **um cartão**, não um `browser_extract_items` único com `limit:3`.
- Preservar `task_id/run_id/operation_id` reais no `record_trace`; a URL loopback não é autorização.
- Se TaskRun não aciona `record_trace`, colocar a ponte mais estreita no owner/dispatcher já existente em `workstation/integrations/hermes/scoped_execution.py`.

### B1 — Contrato de saída semântica, não efeito colateral falso
- A saída é `read_only` e **não cria estado mutado**. Definir postcondição `read.output_shape=native_browser.card_fields.v1`, `read.fields_complete=True`, com ID/list/title/description validos. Não persistir IDs/títulos como postcondição geral; mantê-los no artefato verificado do item.
- Criar recibo de leitura DOM **separado** no owner nativo, obtido por segunda leitura DOM independente; vincular `task_id,run_id,operation_id,raw_result_ref`, observer/source/trust/freshness e evidência no ArtifactStore; sem dados pessoais. Não considerar tool ACK ou read result auto-verificação.
- Para o código preparado **copiar apenas após liberação Stage A** o arquivo [`patches/P1B_read_output_contract.py`](patches/P1B_read_output_contract.py) para `workstation/experience_compiler/read_output_contract.py`. A função `guarded_projection()` apenas checa igualdade de extração/DOM e metadados, NÃO valida autoridade/receipts criptograficamente. Os recibos têm de ser resolvidos pelo `ArtifactStore` e autenticados pelo owner antes de chamar o helper.
- **Inserção exata após Stage A:** `ExperienceCorpus.accept_run` e callback de aceitação **por item** podem adicionar, ao `TransitionSample` já autenticado, `state_after.semantic_predicates.update(projection["semantic_predicates"])` e `verification.verified_predicates.update(projection["proposed_verified_predicates"])`, `delta=StateDelta.between(state_before,state_after)` SOMENTE após owner-verifier produzir `VERIFIED_SUCCESS`. Não atualizar amostras in-place nem reclassificar `executed_unverified` sem receipt aceito. Capture novo ref e notifique `notify_canonical_acceptance()` com o ref resultante.

### B2 — Admissão mínima no compilador
- Ao incluir novo predicado estável **somente de saída verificada**, `infer_action_model` passa a inferir o modelo de efeito abstrato sem confundir leitura com mutação. `segments` pode fechar com delta sintético de **observação aceita**, não delta de DOM; limitar esta permissão a `effect_class in {read_only,PURE_READ,DISCOVERY}` e `primitive==browser_extract_items`, `VERIFIED_SUCCESS`, contrato/receipt independentes. Nenhuma alteração da exigência para mutações.
- `ExperienceCompiler.compile` já inclui `browser_extract_items` em `_PRIMITIVES`; provar candidate output `effect='read_only'` com preconditions/shape/canonical refs. Não zerar globalmente `if not model.effects`, não permitir tool ACK como verified. Verificar `dependency_graph()/operational_slice()` preserva extração como nó terminal.
- Resultado de uma primeira amostra pode ser candidato, mas não implica DIRECT; as regras do `validate_run_local_candidate` continuam exigindo evidência, parametrização, replay seguro e oferta qualificada.

### B3 — Verificação independente de reuso (somente depois de B1/B2)
- Em `run_local_adoption.py`, permitir `browser_extract_items` em `_SUPPORTED` apenas quando dispatch nativo tipado já executa e a nova função `_readback_browser_extract_items` consegue obter DOM fresco, comparar extração, criar receipt próprio, vincular operação e resolver evidência. Adicionar a `_READBACK` somente após teste RED→GREEN de divergência/timeout/operador. Não reaproveitar response RAW como readback.
- Reusar `RunLocalAdopter`, `create_safe_item_boundary_callback` e `OperationalCapabilityRegistry`; NÃO criar `explicit_replay.py`, outro executor ou autoativar DIRECT. Se monitor SHADOW/Stage A impede, produzir `PARTIAL_DECLINED` com motivo exato.

### B4 — Validar MVP e avançar
1. Teste isolado: projeção não eleva confiança e rejeita mismatch, 5 casos preparados PASS. Teste integrado: `owner_readback` realmente independente, `accept_run` e aceitação por-item autenticadas.
2. Native Electron real: UMA TaskRun de três WorkItems (não apenas 3 DOM rows) com pelo menos um candidato criado. Depois ao menos um item compilado no mesmo run **SE** DIRECT validamente autorizado; alternativa é motivo causal documentado.
3. Segunda TaskRun sem promoção/recibos artificiais; campos e seletores parametrizados. Nunca inventar economia com contador sintético.
4. P1B adequado para GO P2 apenas após circuito ser verificado ou restar **uma** dependência de autorização Stage A externa claramente identificada, com restante provado. A ausência geral da ponte de compilação continua HOLD, não "produto aprovado".

## Não negociar
- Stage A PENDENTE: **NÃO editar runtime operacional nesta atividade de preparação.** Os códigos em `patches/` são propostas testáveis para o implementador aplicar quando houver autorização de alteração. Não confundir pedido para CRIAR PATCH com permissão de integração à fonte em produção.
- Sem bypass `SHADOW/DIRECT`, sem promoção global sem política, sem novas autoridades; SourceResearchRun só faz patch experimental e recomenda.
- Evitar privacidade: nunca armazenar DOM integral/credenciais por telemetria, só contratos, artefatos necessários e dados de fixture. Gastos autônomos pagos desligados até teto do usuário.

# PROMPT P1B — FECHAR APRENDIZAGEM DE LEITURA NATIVA SEM REFAZER P1.0 (80/20)

Você é a IA implementadora do Hermes Work. Repo: `kevynlucasprofissional-stack/hermes-agent`. Checkout Windows: `C:\Github\hermes-agent`. Branch pronta: `docs/ol-mvp-p1b-read-output-20261016`, derivada do commit `6e1443079e` do PR draft #93; o #93 depende do #92. Não fazer merge na main, nem alterar artefatos dogfood e `workstation/durable_tasks.py` com mudanças não commitadas.

## STATUS REAL — NÃO REPITA VERIFICAÇÕES CONCLUÍDAS
- `P1.0 PASS`: Electron real (Chromium/BrowserTask), 3 cartões read-only na fixture HTTP local. `browser_extract_items` tipado + leitura independente DOM validaram `id/list/title/description`; build e tsc PASS; E2E 1/1 PASS em 21,8 s. Evidência: `workstation/context/ol-mvp-2026-10-16/evidence/P1_NATIVE_RESULT_20261016.json` no commit de origem. P1.0 tinha dirty tree e não prova release.
- `P1.1 HOLD`: sem TaskRun real, aprendizado/compilação/adocão in-flight. `P1.2 NOT_RUN`: sem reuso automático em outra TaskRun. Chamadas reais de LLM e custo = null. Uma leitura de 3 cards em uma chamada NÃO são 3 WorkItems nem economias demonstradas.
- Stage A permanece pendente: **não modifique código-fonte operacional antes de autorização explícita**. A branch contém patch experimental em `workstation/context/ol-mvp-2026-10-16/patches/`, NÃO importado pelo runtime.

## OBJETIVO EXATO
Com o Browser NATIVO JÁ APROVADO, completar a menor ponte:
```text
TaskRun canônica com 3 WorkItems independentes
→ browser_extract_items por cartão (read_only)
→ readback DOM independente, mesmo BrowserTask e parâmetros
→ aceite canônico por WorkItem, receipt e TransitionSample VALIDADO
→ read.output_shape + read.fields_complete (resultado observado, NÃO mutação de DOM)
→ ExperienceCompiler (candidato)
→ CompilabilityMonitor (SHADOW/DIRECT conforme política)
→ RunLocalAdopter (próximo WorkItem na MESMA TaskRun quando permitido)
→ persistência + novo TaskRun com cartões/parametros distintos
```
Não criar outro compilador, registry, controlador, executor, scheduler, rotas vetoriais ou quatro ImprovementRuns nesta PR.

## QUANDO STAGE A LIBERAR — ORDEM DE IMPLEMENTAÇÃO

### B0. Baseline dirigido
1. Inspecionar `git status --short` e os HEADs dos PRs #92/#93 e branch P1B. Usar worktree isolada.
2. Ler somente `P1B_OUTPUT_BRIDGE_PLAN.md` e `P1B_PATCH_INSTALL.md` além deste prompt.
3. Conferir `workstation/experience_compiler/{corpus,state_abstraction,segmentation,generalization,compiler}.py`, `workstation/integrations/hermes/{run_local_adoption,scoped_execution}.py`, `workstation/task_compiler.py`, `workstation/procedure_trace.py` e `workstation/run_adoption.py`. Ler testes adjacentes conforme necessidade.
4. Não executar suíte inteira. Antes: reproduzir caso RED de `browser_extract_items` validado que não vira candidato, sem fabricar recibo.

### B1. Reusar o fixture P1.0 em uma TaskRun REAL
- `apps/desktop/e2e/ol-mvp-p1-readonly-cards.ts` é a única fixture. Criar uma TaskRun canônica com três WorkItems por IDs `ol-card-a/b/c`, cada um invocando `browser_extract_items` com seleção parametrizada por item (não repetir `limit=3` como um único item).
- Cada resultado vinculado a `task_id/run_id/operation_id` reais e readback de DOM obtido fora do retorno da ferramenta, com `id/list/title/description`. Nenhuma permissão concedida pelo HTML.
- **Não injetar os mesmos identificadores sintéticos que o spec E2E usa nos owners de produção.**

### B2. Criar o readback e a projeção
- Implementar readback independente tipado para `browser_extract_items` no owner já existente. Comparar IDs/listas/títulos/descrições com uma segunda leitura nativa, mesmo escopo de BrowserTask e predicados e cardinalidade.
- Copiar o código já escrito em `patches/P1B_read_output_contract.py` para `workstation/experience_compiler/read_output_contract.py` e seu teste para `workstation/tests/test_read_output_contract.py` (ajustar import). A função `guarded_projection` é APENAS validação de consistência; não é uma verificação independente e não pode autenticar um receipt fornecido por um modelo.
- Resolver o receipt do `ArtifactStore`, conferir identidade canônica, freshness, trust, schema e aceitação do owner antes de chamá-la. Sem receipt verificável, retornar `NOT_VERIFIED` e manter fallback.

### B3. Completar a fonte de resultados do Compiler sem enfraquecer segurança
- Em `workstation/experience_compiler/corpus.py::accept_run`, o fallback hoje só trata readback excepcional de `browser_navigate`. Adicionar ramo **específico de `browser_extract_items`** apoiado em owner receipt independente; e criar aceitação por WorkItem durante a Run no owner existente, sem forjar `verified_completed` global.
- Só depois de aceite: clonar sample, atualizar `state_after.semantic_predicates` e `verification.verified_predicates` com `read.output_shape=native_browser.card_fields.v1` e `read.fields_complete=True`; `StateDelta.between` agora representa *novo resultado observado* e não mutação DOM. Persistir novo `TransitionSample`, `outcome=VERIFIED_SUCCESS` autorizado e `notify_canonical_acceptance` com ref real.
- `segments()` exige delta e VERIFICATION: não remover gates para mutações. `infer_action_model()` passa a encontrar efeitos estáveis do contrato; `compiler.py` já contém `browser_extract_items` em `_PRIMITIVES`. Diagnosticar o próximo bloqueio exato com um teste. Não editar mais do que a primeira seam quebrada.

### B4. Adocão run-local e verificação
- Só adicionar `browser_extract_items` às allowlists `_SUPPORTED` e `_READBACK` em `workstation/integrations/hermes/run_local_adoption.py` DEPOIS de existir verificador de replay readback real. `_readback_browser_snapshot` atual utiliza o RAW e não satisfaz independência.
- Manter `create_safe_item_boundary_callback` → `workstation_run_local_checkpoint` → `RunLocalAdopter`, owner/lease/SHADOW/DIRECT, CAS e idempotência. O monitor jamais concede autoridade por si.
- Esperado: item 1 (ou primeiros itens até adquirir evidência) adaptativo; próximo item elegível compilado sob DIRECT validado; estado durável correto; nenhum item repetido. Se SHADOW/Stage A impedir DIRECT, reportar abstenção com motivo concreto e não declarar PASS da adoção.

### B5. Nova TaskRun / métricas
- Com inputs diferentes, comprovar recuperação de capacidade persistida sem criar promoção artificial no teste. Mudar IDs e textos mantendo mesmo contrato de saída. Verificar readback real.
- Medir chamadas reais ao provedor, tokens e custo da aprendizagem se disponíveis; `null` em caso contrário. Nunca converter 3→2 contagem de fixture em economia financeira.
- Fallback para LLM somente nos subpassos falhos, sem repetir efeito externo incerto.

## TESTES MÍNIMOS E ENTREGA
- Proposta isolada `P1B_read_output_contract.py` passou cinco testes unittest na preparação. Reexecutar depois de copiar.
- Criar testes negativos: output vazio, mismatch DOM, recibo de outro Run, ACK sem verificação, alteração do mesmo ID, readback indisponível, replay errado, SHADOW abstém, resultado read-only não concede permissões de mutação.
- Rodar regressões adjacentes Python e um Electron E2E real pela mesma fixture. Não aumentar duração de smoke além do necessário.
- Apresentar matriz `B0 canonical WorkItems/B1 owner readback/B2 accepted sample/B3 candidate/B4 in-flight/B5 cross-run/cost`: PASS/PARTIAL/HOLD/NOT_RUN com prova; branch/commit, arquivos alterados, causa focal e próxima decisão.
- Atualizar `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`, `workstation/context/engineering-journal/CURRENT.md` e journal com evidências observadas, sem tratar resultado simulado como produto.

**RESTRIÇÕES INEGOCIÁVEIS:** não editar fonte operacional antes de Stage A autorizado; nenhuma assinatura, receipt, owner, controle de versão ou autoridade fabricados; não force DIRECT; não altere main; não faça hardening genérico; não tente replicar n8n. Se Stage A continuar pendente, mantenha o patch proposto e testes em isolamento e classifique produção como HOLD, sem simular autorização. Não solicite decisões arquiteturais antigas novamente.

**80/20:** faça o Browser, já aprovado, ensinar e reutilizar UMA extração nativa. Só depois avance para P2 memória/seleção multimétodo.

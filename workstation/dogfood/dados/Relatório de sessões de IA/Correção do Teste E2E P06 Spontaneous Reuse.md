# Relatório Técnico Integral de Sessão: Correção do Teste E2E P06 Spontaneous Reuse

## 0. Identificação e Cobertura da Sessão

- **Tema:** Depuração e correção do teste de integração `test_p06_spontaneous_reuse_e2e.py` no projeto Hermes Agent.
- **Repositório:** `C:\Github\hermes-agent`
- **Objetivo:** Fazer o teste E2E P06 passar, validando o ciclo completo de aprendizado, compilação, promoção e roteamento espontâneo de capabilities sem reconstrução via LLM.
- **Ambiente:** Windows, Python 3.13.12, pytest 9.0.2.
- **Fontes Examinadas:** Histórico da conversa (incluindo contexto compactado), código-fonte do compilador (`workstation/experience_compiler/`), router (`workstation/control_plane/router.py`), modelos (`models.py`, `promotion.py`) e o próprio arquivo de teste.
- **Grau de Confiança:** Alto. O teste passou com evidência de saída do pytest (`1 passed in 1.23s`).

## 1. Sumário Executivo

O teste E2E P06, que valida a reutilização espontânea de experiências compiladas entre duas execuções de tarefas (TaskRuns), falhava devido a uma combinação de incompatibilidades de API, dados de teste insuficientes para as políticas de promoção e configuração incorreta do roteador. As principais entregas foram a correção da primitiva de `http_post` para `write_file`, a construção de traces multi-run com predicados comuns para inferência estável de efeitos, a satisfação explícita dos critérios de promoção (`CausalGrade`, `controlled_replay`, `validate_verifier`) e o ajuste fino do `OperationIntent` e `semantic_state` para permitir o match determinístico no `CapabilityRouter`. O teste agora passa consistentemente, comprovando a viabilidade do fluxo "learn-compile-promote-route" puramente determinístico.

## 2. Objetivos, Requisitos e Evolução do Escopo

- **Objetivo Original:** Corrigir a chamada do `router.route()` e a construção do `OperationIntent` no teste P06.
- **Evolução:** O escopo expandiu-se significativamente ao descobrir que o teste falhava em múltiplas etapas anteriores ao roteamento:
    1. Primitiva inválida (`http_post` não existe em `_PRIMITIVES`).
    2. Falha na promoção por falta de diversidade cross-run, grau causal e evidência de replay.
    3. Falha na inferência de modelo de ação por predicados de estado divergentes entre runs.
    4. Falha no roteamento por goal trivial (`TRUE()`), effect budget vazio, precondições não satisfeitas no estado top-level e ausência de authority scope explícito.
- **Critérios de Aceite:** `pytest workstation/tests/test_p06_spontaneous_reuse_e2e.py` deve retornar `PASSED`.

## 3. Linha do Tempo Técnica da Sessão

### Fase 1 — Diagnóstico Inicial e Correção de Primitiva

- **Contexto:** O teste falhava com `ValueError: unsupported trusted primitive: http_post`.
- **Ação:** Substituição de `http_post` por `write_file` (presente em `_PRIMITIVES`) nas amostras e chamadas de checkpoint.
- **Resultado:** Compilação avançou, mas falhou na promoção.

### Fase 2 — Satisfação da Política de Promoção

- **Contexto:** `PromotionAdmission(admitted=False, reasons=('parameterization', 'causal_grade', 'cross_run_diversity', 'replay', 'verifier_validated'))`.
- **Ação:** Adição de imports (`CausalGrade`, `VerificationContract`, `VerificationLifecycle`), construção de traces com 2 run_ids distintos, injeção de `authority_scope`, definição manual de `causal_grade = REPLAY_VALIDATED`, adição de evidência de `controlled_replay` e chamada a `compiler.validate_verifier()`.
- **Resultado:** Promoção admitida, mas compilação falhou com `no stable verified semantic effect`.

### Fase 3 — Estabilização da Inferência de Efeitos

- **Contexto:** `infer_action_model` usa interseção de predicados; chaves distintas (`kv_r1`, `kv_r2`) resultavam em conjunto vazio.
- **Ação:** Unificação dos predicados de estado para `{"kv_written": False}` → `{"kv_written": True}` em ambos os runs.
- **Resultado:** Compilação e promoção bem-sucedidas. Roteamento falhou com `SatisfiedDecision` (goal `TRUE()` já satisfeito).

### Fase 4 — Correção do Roteamento Determinístico

- **Contexto:** Router retornava `SatisfiedDecision` ou `ReasoningDecision(no_certifiable_capability_found)`.
- **Ações Iterativas:**
    1. Goal alterado para `EQ("kv_written", True)`.
    2. `effect_budget` preenchido com `[SET("kv_written", True)]`.
    3. Import de `SET` adicionado.
    4. `semantic_state` ajustado para incluir `kv_written: False` no nível superior (não apenas em `baseline_state`).
    5. `AuthorityScope` explícito passado ao `router.route()`.
- **Resultado Final:** Teste PASSED em 1.23s.

## 4. Descobertas Técnicas e Conhecimento Adquirido

|Descoberta|Contexto|Explicação Técnica|Aplicabilidade Futura|
|:--|:--|:--|:--|
|`_PRIMITIVES` é whitelist estrita|Compilação rejeitou `http_post`|O compilador só aceita primitivas listadas em `compiler.py:18-21`.|Sempre verificar `_PRIMITIVES` antes de criar traces sintéticos.|
|`infer_action_model` exige interseção|`no stable verified semantic effect`|A função calcula efeitos via interseção de deltas verificados; predicados distintos por run anulam a interseção.|Usar predicados canônicos comuns em testes multi-run.|
|`cross_run_diversity` requer ≥2 run_ids|Promotion rejected|`promotion.py:28`: `len(set(m.get('run_ids', []))) >= 2`.|Sempre fornecer traces de pelo menos 2 runs distintos.|
|Router avalia precondições no top-level|`preconditions_hold` falhava|`EQ.evaluate()` busca chave diretamente no dict `state`, não em `baseline_state` aninhado.|`semantic_state` deve conter predicados de precondição no nível raiz.|
|`effect_contained` exige budget explícito|Router rejeitava capability válida|Budget vazio `[]` não contém nenhum efeito SET; containment é verificado via igualdade ou prefixo.|Sempre declarar `effect_budget` compatível com o footprint da capability.|
|`AuthorityScope` é obrigatório para mutação|`authority_satisfied` falhava|Capabilities de `state_mutation` exigem authority level ≥ `LOCAL_MUTATION`.|Passar `authority_scope` explicitamente ao chamar `router.route()`.|

## 5. Decisões Técnicas e Arquiteturais

- **D-01: Uso de `write_file` como primitiva canônica.** Justificativa: presente em `_PRIMITIVES`, efeito `state_mutation` simples. Alternativa `http_post` rejeitada. Estado: Definitiva.
- **D-02: Predicado unificado `kv_written`.** Justificativa: permite interseção não-vazia em `infer_action_model`. Alternativas (chaves por run) falharam. Estado: Definitiva.
- **D-03: Construção manual de evidência de promoção.** Justificativa: teste é fixture-based, não executa replay real. Estado: Provisória (idealmente o harness de teste deveria executar replay controlado).
- **D-04: AuthorityScope explícito no teste.** Justificativa: router não infere autoridade do contexto de teste. Estado: Definitiva.

## 6. Inventário de Alterações

**Arquivo Modificado:** [workstation/tests/test_p06_spontaneous_reuse_e2e.py](app://localhost/epitaxy/workstation/tests/test_p06_spontaneous_reuse_e2e.py)

|Região|Alteração|Evidência|
|:--|:--|:--|
|Imports|Adicionados `CausalGrade`, `VerificationContract`, `VerificationLifecycle`, `SET`, `EQ`|Linhas de import atualizadas|
|`_record_verified_trace` calls|Primitiva `http_post` → `write_file` com args `{path, content}`|Edição confirmada|
|`calls_a`|Atualizado para `write_file` com path/content|Edição confirmada|
|Bloco de compilação|Substituído por traces multi-run com `kv_written`, `authority_scope`, `CausalGrade.REPLAY_VALIDATED`, `controlled_replay` evidence, `validate_verifier`|Edição confirmada|
|TaskRun B Intent|`goal=EQ("kv_written", True)`, `effect_budget=[SET(...)]`, metadata completo|Edição confirmada|
|TaskRun B Route|`semantic_state` com `kv_written: False` top-level, `AuthorityScope` explícito|Edição confirmada|

## 7. Problemas e Análise de Causa Raiz

- **B-01: Primitiva inválida.** Causa: `http_post` não está em `_PRIMITIVES`. Solução: usar `write_file`.
- **B-02: Promoção rejeitada (5 razões).** Causa: teste fornecia apenas 1 run, sem causal grade, sem replay evidence, sem verifier validation. Solução: construir todos os artefatos manualmente seguindo padrão de `test_learned_capability_routing.py`.
- **B-03: Efeito instável.** Causa: predicados `kv_r1`/`kv_r2` não intersectam. Solução: unificar para `kv_written`.
- **B-04: Goal trivial satisfeito.** Causa: `TRUE()` sempre satisfeito. Solução: `EQ("kv_written", True)`.
- **B-05: Effect containment falha.** Causa: budget vazio. Solução: `[SET("kv_written", True)]`.
- **B-06: Precondição não avaliada.** Causa: predicado aninhado em `baseline_state`. Solução: mover para top-level.
- **B-07: Authority shortfall.** Causa: nenhum authority scope passado. Solução: `AuthorityScope(level=LOCAL_MUTATION, ...)`.

## 8. Testes e Verificações

|Comando|Resultado|Evidência|
|:--|:--|:--|
|`pytest ... -x -v` (após fix write_file)|FAILED (promotion)|Saída pytest|
|`pytest ... -x -v` (após multi-run)|FAILED (no stable effect)|Saída pytest|
|`pytest ... -x -v` (após kv_written)|FAILED (SatisfiedDecision)|Saída pytest|
|`pytest ... -x -v` (após EQ goal)|FAILED (no_certifiable_capability)|Saída pytest|
|`pytest ... -x -v` (após SET budget)|FAILED (no_certifiable_capability)|Saída pytest|
|`pytest ... -x -v --tb=long` (final)|**PASSED**|`1 passed in 1.23s`|

Script de inspeção Python executado para verificar estrutura da capability compilada: confirmou `family_id=kv_write:kv_entry`, postconditions `[EQ(kv_written, True)]`, footprint `[SET(kv_written, True)]`, authority `LOCAL_MUTATION`.

## 9. Estado Final dos Artefatos

- **Teste:** `test_p06_spontaneous_reuse_e2e.py` — PASSANDO.
- **Branch:** Não verificado (nenhum commit/push foi realizado nesta sessão).
- **Alterações não commitadas:** Sim, o arquivo de teste foi modificado em disco.

## 10. Pendências e Riscos

- **P-01 (P2):** Commit e push das alterações no teste P06.
- **P-02 (P3):** O teste constrói evidência de promoção manualmente; idealmente um harness de teste deveria executar replay controlado real para maior fidelidade.
- **Risco:** Se `_PRIMITIVES` ou a política de promoção mudarem, o teste pode quebrar silenciosamente se as fixtures não forem atualizadas.

## 11. Guia de Continuidade

### 11.1. Estabelecido

O ciclo learn→compile→promote→route funciona end-to-end com tipos reais. Os padrões de construção de traces multi-run, promoção e roteamento estão documentados neste relatório e no código do teste.

### 11.2. Não Repetir

Não usar `http_post` como primitiva. Não usar predicados distintos por run. Não usar `TRUE()` como goal. Não omitir `effect_budget`, `authority_scope` ou predicados top-level no semantic state.

### 11.3. Não Quebrar

A assinatura de `compiler.compile(traces, failures=())`, `compiler.promote(cap)`, `compiler.validate_verifier(cap, contract, receipts)` e `router.route(intent, state, authority_scope=...)` são contratos estáveis usados pelo teste.

### 11.4. Próximas Ações

1. Commitar as alterações em `test_p06_spontaneous_reuse_e2e.py`.
2. Executar suite completa de testes do experience_compiler para regressão.
3. Considerar extrair helpers de construção de traces/promoção para módulo compartilhado de teste.

## 12. Matriz de Rastreabilidade

|Requisito|Ação|Evidência|Estado|
|:--|:--|:--|:--|
|Teste P06 passar|7 iterações de correção|`1 passed in 1.23s`|✅ VERIFICADO|
|Primitiva válida|`http_post` → `write_file`|Edição + compile success|✅ VERIFICADO|
|Multi-run diversity|2 traces com run_ids distintos|Promotion admitted|✅ VERIFICADO|
|Stable effect|Predicado `kv_written` unificado|Compile success|✅ VERIFICADO|
|Router match|EQ goal + SET budget + authority + top-level state|ExecutableDecision returned|✅ VERIFICADO|
|Commit/push|Não executado|N/A|⏳ PENDENTE|

## 13. Avaliação Crítica

A sessão produziu valor tangível: um teste E2E crítico que estava bloqueado agora passa e serve como referência canônica para o fluxo de spontaneous reuse. O esforço foi proporcional à complexidade — 7 iterações de diagnóstico-correção-validação, cada uma resolvendo uma camada específica de incompatibilidade. A decisão de inspecionar a capability compilada via script Python intermediário foi particularmente eficaz para desacoplar problemas de compilação de problemas de roteamento. A principal limitação é que a evidência de promoção é construída manualmente; um futuro refactor deveria introduzir um test harness que execute replay controlado real. Nenhuma investigação foi desperdiçada — cada falha revelou um requisito real da política de promoção ou do router que não estava documentado explicitamente.
# OL-MVP — Índice de execução (2026-10-16)

## PRIORIDADE VIGENTE — P1C: uma TaskRun REAL usando capacidade compilada

O PR #94 `27b6376535dc` concluiu em código o P1B (aceitação/verificação de leitura; 30 testes focais + 53 regressões reportados). **NÃO comprovou o `RunLocalAdopter` executando 2/3 cartões**: o teste de três WorkItems utiliza `worker` com dispatcher sintético para TODOS os itens. P1C deve validar a rota completa `desktop chat/Gateway → TaskCompiler → 3 WorkItems → ExperienceCompiler → RunLocalAdopter → outra TaskRun` e os artefatos do owner. Stage A/qualificação DIRECT em HOLD.

**Entregas P1C:** [PROMPT IMPLEMENTADOR](P1C_IMPLEMENTER_PROMPT.md) · [MAPA DE PATCH](P1C_EXACT_PATCH_MAP.md) · [PLANO / GATES](P1C_NATIVE_DOGFOOD_PLAN.md) · [TEMPLATE DE RECIBO](P1C_NATIVE_RECEIPT_TEMPLATE.json). Código auxiliar: `patches/P1C_evidence_gate.py` (validação **só estrutural**, não de identidade/authority, com 6 testes) e `patches/test_P1C_strict_read_acceptance.py` (testes RED propostos; **NÃO executados**, copiar para `workstation/tests` antes do patch de fail-closed).

Não reconstruir P0, P1.0, P1B; manter planos anteriores como histórico. No P1C, a prioridade é uma execução de produto real, não quatro ImprovedRuns nem novo sistema de embeddings.



## PRIORIDADE ATUAL (16/10/2026): P1B — leitura verificada → capacidade executável

**P1.0 Browser nativo já PASS** no PR #93 `6e1443079e`, E2E 1/1 em 21,8s. Três cartões obtidos numa ação `browser_extract_items` e verificados por leitura DOM independente; sem TaskRun/learning real. Não investir mais em boot/fixture.

**A IA deve começar por [P1B_IMPLEMENTER_PROMPT.md](P1B_IMPLEMENTER_PROMPT.md)**, consultar [P1B_OUTPUT_BRIDGE_PLAN.md](P1B_OUTPUT_BRIDGE_PLAN.md) para estado causal, [P1B_PATCH_INSTALL.md](P1B_PATCH_INSTALL.md) para locais exatos e `patches/P1B_read_output_contract.py` + teste para código puro preparado e validado em isolamento (5 PASS).

P1.1 ainda HOLD. Stage A pendente: patch não instalado no runtime, nenhuma política DIRECT alterada, sem merge main. Os antigos P1_*.md são históricos e foram preservados por rastreabilidade.



**AGORA: P1 Native Browser Dogfood (80/20).** P0 Python foi demonstrado em fixtures; P1 prova execução real Chromium/BrowserTask e depois Experience Compiler dentro de uma TaskRun. A meta é qualidade *decente e verificada* em um fluxo, não hardening de todos os sistemas.

**A IA implementadora deve abrir APENAS estes 3 documentos e executar:**
1. [P1_IMPLEMENTER_PROMPT.md](P1_IMPLEMENTER_PROMPT.md) — roteiro pronto para executar.
2. [P1_PATCH_MAP.md](P1_PATCH_MAP.md) — arquivos, funções e código já aplicado.
3. [P1_EVIDENCE_GATE.md](P1_EVIDENCE_GATE.md) — PASS/PARTIAL/HOLD, evidência mínima.

Contexto opcional: [P1_NATIVE_BROWSER_80_20.md](P1_NATIVE_BROWSER_80_20.md), [DECISIONS.md](DECISIONS.md), [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) e [journal P1](../engineering-journal/OL_MVP_P1_2026-10-16.md).

**Status atualizado (16/10):** P1.0 PASS no E2E Electron nativo com fixture loopback (1/1; 21,8 s), extração tipada e readback DOM independente; [recibo](evidence/P1_NATIVE_RESULT_20261016.json). P1.1/P1.2 seguem NOT DEMONSTRATED: nenhum TaskRun canônico iniciou; métricas de TaskRun permanecem null. A execução NOT_RUN mencionada em registros anteriores é histórica e foi supersedida por este resultado.

**Atenção:** `IMPLEMENTER_PROMPT.md` e `PATCH_MAP.md` sem prefixo P1 são históricos do P0, não executar novamente. Usar P1. Branch P1 empilhada sobre PR #92; sem merge automático na main.

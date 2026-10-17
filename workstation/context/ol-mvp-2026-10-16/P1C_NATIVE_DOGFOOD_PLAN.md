# OL-MVP P1C — Prova de produto: aprender, adotar e recuperar sem fixture de dispatch

**Decisão em 16/10/2026 | Estratégia 80/20:** o P1B está **IMPLEMENTADO EM CÓDIGO** no PR #94, HEAD `27b6376535dcfb92025fd4d468411feb0d7d3a34`, mas **NÃO ESTÁ QUALIFICADO NO PRODUTO NATIVO**. Não reabrir Browser P1.0, não criar motor/registry/novos ImprovementRuns. P1C deve ser um dogfood pequeno e auditável na interface real do Hermes Work; depois P2 leve.

## Evidência conhecida (separar testes de produção)
- P1.0 Electron Chromium + HTML loopback + browser_extract_items: 1/1 E2E PASS em 21,8s, recibo `evidence/P1_NATIVE_RESULT_20261016.json`.
- P1B: novo owner `_readback_browser_extract_items` com leituras frescas não atômicas, dispatcher, `read_output_contract`, `accept_work_item`, saída `read.*`, mineração candidata e regressões. Relatório do implementador no anexo de 16/10: **30 testes focais, somando a tabela com 6 suítes, e 53 regressões de segurança** reportados aprovados; lint/commit/push também reportados. Não reexecutados nesta revisão porque Desktop Commander está offline.
- `test_ol_mvp_p1b_cards_workitems.py` usa `self.dispatch()` sintético, chama `capture_progressive`, `readback_fn`, `notify_online_compilability` e `monitor.mine_candidate_in_run()` explicitamente. **`worker()` processa todos os 3 cards. Não chama `RunLocalAdopter.run_checkpoint()`, não executa uma oferta DIRECT real nem mede API LLM.** Não declarar 2/3 cards compilados. Corrigimos o docstring do teste para distinguir isso.
- Stage A continua PENDENTE. `P1B_STAGE_A_EXCEPTION_20261016.md` autorizou desenvolvimento isolado, não promoção, DIRECT forçado, release ou merge main.

## Objetivo mínimo P1C
1. Uma conversa / `work_execute` verdadeira pelo gateway desktop invoca UMA TaskRun canônica, com três **WorkItems** independentes (um por cartão) sobre a fixture loopback já existente. `browser_extract_items` tipado via proprietário real do BrowserTask. Sem scripts chamando manualmente o compilador a partir do teste.
2. Observar no runtime o primeiro(s) WorkItem(s): `raw_result_ref` real + `transition_ref` correspondente + `readback_ref` independente + `candidate_ref`; comprovar IDs da própria operação. Não aceitar fallback para `candidates[-1]`, `_last_*_ref` ou IDs aleatórios como associação causal.
3. Submeter o candidato ao fluxo legítimo de qualificação; se houver atestação DIRECT ativa e autorização real, o runtime `RunLocalAdopter` conclui ao menos um WorkItem seguinte, com `run_local_reuse_*.json` e readback independente. Caso contrário, seguir execução adaptativa sem falhar a tarefa e registrar motivo `SHADOW`/Stage A/insuficiência de evidência.
4. Uma **nova** TaskRun, com outros parâmetros e sem semear promoção/recibos no setup do teste, tenta resolver e executar a capacidade persistida; readback dos resultados.
5. Registrar contagem de chamadas reais de modelo, tokens/custo quando presentes; se provedor é mock/teste, `real_llm_calls=null`, e não declarar economia USD.

## Primeiras lacunas pontuais a verificar antes do teste real
- `workstation/integrations/hermes/run_local_adoption.py::canonical_source_for_readback` usa `agent._current_operation_id` / `agent._last_raw_result_ref` / `agent._last_progressive_ref` e possui fallbacks que **criam IDs/artefatos/transition** quando faltam. Exigir vínculo EXATO à operação atual e ao resultado persistido; não fabricar last-read causal.
- `workstation/experience_compiler/corpus.py::accept_work_item` escolhe `matching[-1]`, senão `candidates[-1]`, e pode **fabricar um TransitionSample** se não localizar amostra; para aprendizado em produção, falhar fechado em amostra inexistente, vínculo de operação divergente ou ausência de receipt íntegro. Não aceitar apenas campos autodeclarados do recibo.
- `workstation/integrations/hermes/run_local_adoption.py` chama `ExperienceCorpus(...).accept_work_item(...)` dentro de `try/except: pass` após readback e pode responder `ok=True` sem a aceitação. **Readback correto ≠ aprendizado aceito**; são estados distintos e devem ser auditáveis.
- `RunLocalAdopter` exige offer qualificada, lease, inputs/admission, versionamento e verificação. Sem atestação legítima DIRECT, não habilitar replay por override de teste no runtime de produto.

## Sequência de engenharia 80/20
**A.** Primeiro teste nativo só com TaskRun verdadeira + três leituras verificadas. Se falhar, corrigir exclusivamente ingresso `desktop_chat → work_execute → TaskCompiler → BrowserTask`.

**B.** Depois verificar amostra/receipt/operation_id real do primeiro cartão; se gate falhar, um patch focal de vinculação (sem reescrever compiler).

**C.** Depois provar candidate miner, offer SHADOW ou DIRECT legítima e checkpoint de adoção, com auditoria da rota real de execução.

**D.** Segunda TaskRun com cards novos e consulta ao mesmo registry; sem promoção artificial.

**E.** Um relatório curto com evidências + GO/HOLD; parar aqui. P2 só começa com no mínimo um caminho reutilizável demonstrado ou impedimento isolado que dependa exclusivamente de autorização não técnica.

## Esquema e código de suporte já preparado
- `patches/P1C_evidence_gate.py`: classificação estática **não autoritativa** de recibo P1C; exige referências por item, duas Runs separadas, candidato, offer qualificada e recibo de adoção. Não verifica bytes/proveniência do ArtifactStore, não concede Stage A/DIRECT, não deve ser usado como engine de autorização.
- `patches/test_P1C_evidence_gate.py`: 6 testes de casos negativos/positivos; uma versão equivalente foi executada com sucesso em Python 3.13 local no contêiner (6 PASS), mas o commit do GitHub ainda requer execução no ambiente Hermes para qualificação exata.
- `P1C_NATIVE_RECEIPT_TEMPLATE.json`: template com valores nulos; **NÃO é prova**, deve ser preenchido exclusivamente com evidência de runtime real.

## Critério GO/HOLD honesto
- **P1C PASS:** 3 WorkItems nativos verificados, `adaptive → compiled` comprovado por **recibo do RunLocalAdopter** após qualificação legítima, novo run distinto recupera a capacidade e readback, sem violar lease/authority nem duplicar efeito.
- **P1C PARTIAL:** TaskRun real + output/candidato completo e bloqueio SHADOW/Stage A específico, documentado e não mascarado. Produto continua em HOLD de DIRECT.
- **P1C HOLD:** fixture sintética, TaskRun ausente, só candidato criado, sem raw/evidence refs válidos, ou falso sucesso. Não tentar compensar ausência de E2E com 300 testes isolados.
- Stage A/PRs: branch de desenvolvimento isolada, sem merge main; aprovação humana continua obrigatória para alteração do runtime operacional fora da exceção existente.

### Depois do P1C (não implementar simultaneamente)
P2.1 persistência e recuperação por contrato exato/lexical simples; P2.2 seleção BM25/semântica/LAYA **sob benchmark**, nunca como dependência universal; P2.3 fila persistente mínima com quatro especialidades usando runtime/scheduler compartilhados, orçamento financeiro pago desabilitado até teto explícito; pesquisa de source apenas em sandbox com autorização para integração humana. Preservar evolução global otimista de versões, rollback contextual e telemetria independente. Não criar novos bancos ou quatro motores.

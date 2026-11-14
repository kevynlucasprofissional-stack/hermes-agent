# Hermes Work — System 1 Browser: E2E humano isolado (07/11/2026)

## Resultado: PASS para seleção determinística de alvo único

A mesma frase humana exata `Localize o botão Relatórios na página atual` foi enviada duas vezes pela interface de uma **instância Electron separada** do Hermes na sessão `20261107_181843_c29320`, com BrowserTask e backend Python próprios. O alvo estava visível na fixture local `http://127.0.0.1:18791/unique`, referência `@e1`. Nenhum botão foi clicado.

A/B observável (um turno completo por variante):

| Métrica | Baseline antes da correção | Fast path corrigido |
| --- | ---: | ---: |
| Chamadas `PROVIDER_CALLED` ao DeepSeek Flash | 2 | **0** |
| Tokens de entrada enviados em requisições ao modelo | 52.382 | **0** |
| Tokens de saída enviados em respostas do modelo | 590 | **0** |
| Duração registrada do turno | 9,6 s | **1,2 s** |
| `browser_snapshot` nativos observados | 2 | **2** |
| Latência dos dois snapshots nativos | 56,17 / 58,45 ms | **42,13 / 16,09 ms** |
| Resolução operacional | `CONTINUE_REASONING` (2x) | **`SATISFIED`** |
| Referência final | `@e1` | **`@e1`** |
| Cliques | nenhum | **nenhum** |

Redução de **87,5% no tempo do turno observado**, eliminação de **2 chamadas System 2** e de **52.382 tokens de entrada / 590 de saída** que constam nos eventos das requisições. Tokens incluem cache potencial e não são custo faturado. Uma medição por variante **não** prova p50/p95 geral, robustez em sites externos ou economia de custos em produção.

Arquivo auditável: `RESULTADO_A_B_ISOLADO_20261107.json`; script read-only de reprodução: `compare_isolated_turns.py`. Fonte: SQLite isolado `%LOCALAPPDATA%\HermesWorkstation\qualification\system1-desktop-e2e\e2e-20261107211148-057da9\hermes-home\workstation\telemetry\telemetry.sqlite` e `logs\agent.log` do mesmo sandbox.

## Defeitos confirmados e corrigidos

1. **TaskRun indevida para leitura pontual:** `workstation/work_intent.py:prepare_turn_work` não cria TaskRun para um comando pontual, corretamente. `maybe_resolve_browser_find` exigia `_canonical_work_task_id`; passou a usar **BrowserTask da sessão autenticada** para *somente* `browser_snapshot`, com validação cruzada de `session_id` no envelope/contexto/agente, sem criar ou tomar emprestada uma TaskRun.
2. **Snapshot compactado:** o executor encaminhava o resultado projetado para o LLM por `tools.browser_workstation.project_model_browser_payload`, que remove `elements` quando já presentes na representação textual. O seletor necessita de `elements` estruturados para verificar identidade, ambiguidade e readback. `workstation/integrations/hermes/scoped_execution.py:workstation_durable_dispatch` recebeu a opção explícita **`raw_browser_snapshot=True`**, restrita ao nome `browser_snapshot`. Reutiliza o despacho nativo já existente, pre-dispatch hook, controle de lease, política, observador e ledger, sem mudar o caminho padrão das ferramentas comuns. `workstation/system1/browser_read_fastpath.py` passou a requisitar essa opção.
3. **Ambiguidade e abstenção:** conservados `test_duplicate_exact_labels_fail_closed_before_model`, `test_two_partial_matches_fail_closed_before_model`, `test_untrusted_model_output_does_not_invent_targets_or_commands`, `test_invalid_snapshot_never_calls_model_or_readback`, `test_operational_fastpath_is_disabled_by_default` e testes de cross-session.

## Evidências de execução e segurança

- RED do binding pontual: `test_human_point_lookup_uses_own_session_browser_task_without_kanban_task` falhou antes do patch (`NoneType`), GREEN depois.
- RED do snapshot nativo: `test_native_read_dispatch_preserves_structured_snapshot_for_enabled_tool` falhou antes do patch (`unexpected keyword argument 'raw_browser_snapshot'`), GREEN depois.
- Runner canônico: `scripts/run_tests.sh workstation/tests/test_system1_browser_read_fastpath.py workstation/tests/test_operational_resolution_provider.py workstation/tests/prefabs/test_prefabs.py workstation/tests/test_system1_capability_routing.py workstation/tests/test_system1_safety.py -j 3 -q` => **62/62 PASS**. Não foi a suíte completa do repositório.
- `ruff check` em arquivos Python alterados => PASS; `git diff --check` nas alterações rastreadas => PASS.
- Turno real concluído em `2026-11-07T21:39:58Z`: log `Operational resolution: SATISFIED by workstation_operational_resolution (system1_browser_read_verified)`, `api_calls=0/500`, `duration=1.2s`. Dois `BROWSER_OPERATION_OBSERVED status=OBSERVED` com `operation_id=system1_browser_read_*` precederam a decisão.
- Identidade: a mesma sessão de chat `20261107_181843_c29320`, mesma fixture e botão `@e1`. No Workstation, um comando de leitura pontual **não tem TaskRun Kanban**; o BrowserTask válido é controlado por identidade de sessão e regras do Browser. Não foi forjada TaskRun para satisfazer o roteiro inicial.
- O primeiro backend isolado foi reiniciado **somente dentro do sandbox** para recarregar as correções; a ponte AI Control autenticada da instância isolada forneceu leitura da UI e submissão dos turnos. O backend/profiling produtivo não foi reiniciado ou modificado, sem CDP nem mouse/teclado globais.
- Houve um turno inicial de setup rejeitado pela configuração errada de modelo `z-ai/glm-5.3` no provedor DeepSeek (HTTP 400); a instância passou a usar `deepseek-flash` aceito. Esse erro não está incluído no A/B, que compara exclusivamente turnos completos da mesma frase e mesmo modelo.
- O teste Laya multilíngue para alvos parciais foi qualificado isoladamente anteriormente; **não foi executado nesta rodada como novo E2E completo**. A rota exata validada usa o seletor determinístico, sem Laya, como proposto.

## Estado de entrega

**MVP da rota exata: aprovado em E2E humano com backend/Browser isolados.** Permanecer com `HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED` desativada por padrão; **não ativar globalmente**, não integrar a `.venv` produtiva e não alegar prova de ganho geral em produção. O experimento ativo usou a flag apenas no processo de teste.

Checkout `C:\Github\hermes-agent`, branch `main`, HEAD inicial `f1d5ab2f03`, compartilhado e muito alterado. Nenhuma alteração de outros agentes foi revertida; sem commit/push/PR. Novos scripts e relatórios ficam em `workstation/benchmarks/system1_live_session/`.

**Melhorias adiadas, não bloqueantes:** estatística de múltiplos turnos, demonstração de fluxo humano em /partial com Laya real, teste negativo E2E em /duplicate e /missing. Testes focados de recusa e ausência seguem verdes. Não ampliar escopo nesta entrega.

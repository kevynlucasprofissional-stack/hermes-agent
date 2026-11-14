# Homologação final do System 1 Browser — Hermes principal

**Data:** 07/11/2026, 22h01 (America/Sao_Paulo)  
**Veredito:** **PASS** — rota determinística, alvo exato e único, mensagem originada pela interface autenticada do Hermes.

## Identidade e escopo
- Repositório: `C:\Github\hermes-agent`, branch `main`, HEAD observado `f1d5ab2f03`.
- Sessão criada exclusivamente para esta homologação: `20261107_220115_133cc6`.
- AI Control: `aiControl:true`; env de usuário `HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED=1` observado.
- Browser nativo da sessão aberto em `http://127.0.0.1:18791/unique`; fixture respondendo `/health` e página mostrada no renderer.
- Primeiro turno preparatório abriu a URL via `browser_navigate` e descreveu elementos `@e1` Relatórios, `@e2` Configurações, `@e3` Painel e `@e4` Ajuda. **Duas chamadas ao DeepSeek Flash ocorreram na preparação**; não estão incluídas na comparação do turno exato.
- Segundo turno enviado separadamente por `apps/desktop/scripts/hermes-nav.mjs inject` quando `location.href` era `http://127.0.0.1:5174/#/20261107_220115_133cc6`:
  `Localize o botão Relatórios na página atual`

## Resultado do turno exato (PASS)
- Resposta visível: `Localizei botão "Relatórios" na página atual (@e1). Nenhum clique foi realizado.`
- Log do agente: `Operational resolution: SATISFIED by workstation_operational_resolution (system1_browser_read_verified)`.
- Log de conclusão: `reason=operational_resolution(SATISFIED)`; `api_calls=0/100`; `duration=1.3s`; sessão `20261107_220115_133cc6`.
- SQLite de produção: `%LOCALAPPDATA%\hermes\workstation\telemetry\telemetry.sqlite`, consultado **somente leitura** entre 2026-11-08T01:01:37Z e 01:01:41Z, sessão exata.
- `TURN_STARTED` presente; `ROUTING_DECIDED status=SATISFIED provider=system1_browser_read`.
- Exatamente **2 snapshots Browser nativos confirmados** (`BROWSER_OPERATION_OBSERVED status=OBSERVED action=browser_snapshot`): 96,5614 ms e 17,9422 ms; operation IDs `system1_browser_read_4097019ff00040b9` e `system1_browser_read_5dde691e459942e4`.
- **0 eventos `PROVIDER_CALLED`** e **0 operações de Browser mutantes** nessa janela.
- Script de verificação reexecutável: `workstation/benchmarks/system1_live_session/verify_main_20261107.py`, retorno exit code **0**, campo `summary.pass=true`.

## Comparação com o sandbox aprovado anteriormente
- A/B na instância isolada, mesma frase: baseline 2 chamadas System 2, 9,6s; fast path 0 chamadas, 1,2s, ambos com dois snapshots, `@e1`. Relatório: `RELATORIO_ENDTOEND_ISOLADO_20261107.md`, JSON `RESULTADO_A_B_ISOLADO_20261107.json`.
- A validação atual é **mais forte que o sandbox**, pois usa o Hermes principal pós-implantação, mas apenas uma ocorrência para esta frase/fixture. Não é uma curva p50/p95 nem prova de todos os sites.
- Suíte focada executada na etapa anterior: **62/62 PASS**; não repetida nessa etapa, pois nenhum código de produção foi alterado aqui.

## Segurança, alterações e encerramento
- Não houve cliques, digitação na página, mudanças em dados ou chamadas de navegação fora do primeiro turno preparatório da sessão exclusiva. Não foram reiniciados processos nem alteradas permissões/leases durante esta homologação.
- Esta rodada só criou um arquivo de verificação de telemetria e este relatório sob `workstation/benchmarks/system1_live_session/`, e criou a sessão experimental no Hermes; preservou o checkout compartilhado. Sem commit, push, PR ou branch switch.
- Flag de produção `HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED=1` mantida para a rota determinística. Laya não habilitado globalmente.
- **Conclusão:** três etapas acordadas (limpeza de isolados, reinício controlado/ativação, homologação real principal) finalizadas. Melhorias de Laya, mais sites e amostragem estatística são opcionais e não bloqueantes.

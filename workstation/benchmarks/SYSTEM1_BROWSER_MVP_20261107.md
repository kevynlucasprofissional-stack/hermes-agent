# Hermes Work — System 1 Browser MVP: execução e evidências (07/11/2026)

## Situação
**Implementação local parcial e segura, sem ativação no processo Electron já em execução.** Rota de localização read-only conectada ao pré-raciocínio do Hermes. Um modelo System 1 pode propor seleção entre referências nativas, mas Laya não está disponível no ambiente Python testado; operações de alvo exato funcionam deterministicamente sem inferência. Não houve navegação no perfil produtivo nem clique/tecla global.

## Baseline Entrega 0 — observado
- Checkout original: `C:\Github\hermes-agent`, `main@f1d5ab2f03`, 343 entradas dirty/untracked no preflight. Não houve switch/reset/stash/clean ou mudanças nos arquivos Browser anteriormente modificados.
- Hermes Desktop ativo; `hermes-nav.mjs status` reportou `aiControl:true`; `check-browser-status.mjs` reportou controle nativo pronto, aba produtiva estacionada em `about:blank`. Esta aba não foi operada.
- `node apps/desktop/e2e/workstation-runtime-native-isolated-runner.cjs`: PASS (exit 0), navegador Electron isolado com duas BrowserTasks; navegação, clique e digitação confirmados por readback, recibos e isolamento.
- Ambiente Python `.venv`: Python 3.14.0, `laya` ausente; suíte inicial `test_laya_real_contract.py`: **2 FAIL ModuleNotFoundError: laya; 1 skipped**; testes de roteamento/segurança independentes do modelo passaram (5). Cache HuggingFace de modelo Laya presente, mas não substitui instalação/inferência.
- Ainda não há baseline instrumental comparável de **tempo total até resultado do System 2, custo ou chamadas evitadas**; não inferir esses ganhos.

## Entrega 1 — arquivos tocados
- Novo `workstation/system1/browser_read_fastpath.py`: interpreta apenas comandos explícitos de localização (botão/aba/link), consume snapshot **nativo**, consulta somente elementos habilitados com referência observada, seleciona único rótulo exato sem LLM, ou usa proposta de `decide_system1` com limite de candidatos. Recusa schema inválido, modelo indisponível/abstido, ref inventada, rótulo sem fundamento e mudanças de task/tab/URL/revision/elemento. Não dispara efeitos.
- Em `workstation/integrations/hermes/operational_resolution.py`: **somente seis linhas adicionadas** para invocar o novo caminho antes da rota Prefab existente; arquivo estava limpo antes desta alteração.
- Novo `workstation/tests/test_system1_browser_read_fastpath.py`: testes de contrato, autoridade da origem, integração à resolução operacional, fallback e segurança.
- Novos `apps/desktop/e2e/workstation-system1-native-snapshot.ts` e `-runner.cjs`, e `workstation/benchmarks/system1_browser_native_probe.py`: fixture localhost em perfil temporário; nove snapshots reais, alvo `@e1`, referência confirmada por segundo snapshot.

## Provas (última execução)
- `scripts/run_tests.sh workstation/tests/test_system1_browser_read_fastpath.py workstation/tests/test_operational_resolution_provider.py workstation/tests/prefabs/test_prefabs.py workstation/tests/test_system1_capability_routing.py workstation/tests/test_system1_safety.py -j 3 -q`: **56 PASS, 0 FAIL**, runner canônico (17s aproximadamente). Não é a suíte completa do repositório.
- TDD de segurança: `test_high_confidence_model_cannot_verify_unrelated_label` reproduziu **RED: modelo com 100% de confiança devolvia rótulo alheio**, seguido de GREEN com exigência de rótulo observável.
- `node apps/desktop/e2e/workstation-system1-native-snapshot-runner.cjs`: **PASS exit 0**; amostra n=9: snapshot nativo p50 8,129ms, p95/maior amostra 11,048ms; seletor local p50 0,015ms, p95 0,075ms; uma BrowserTask, foco humano não tomado; referência `@e1` validada.
- Repetição final n=9: snapshot p50 7,639ms e p95/maior amostra **69,370ms** (variação relevante); seletor p50 0,024ms e p95 0,099ms. Ambas as execuções terminam com exit 0, mas amostra é pequena e não demonstra aceleração do fluxo inteiro.
- `node apps/desktop/e2e/workstation-runtime-native-isolated-runner.cjs`: **PASS exit 0** após integração.
- `python -m py_compile` dos três arquivos novos: PASS; `ruff check` em arquivos Python novos: PASS (verificar novamente após alterações futuras); `git diff --check` no único arquivo versionado modificado: PASS.

## Limites que não podem virar alegação de sucesso
- A integração do caminho de entrada foi provada em regressão com dispatcher falso; a seleção de referência foi provada com **snapshots reais** de Electron isolado. O trajeto completo "mensagem humana no Desktop -> TaskRun real -> Laya real -> economia de chamada LLM" **não foi homologado**.
- Laya 0.3.23 declarado como extra, **não instalado** no `.venv` testado. Não instalar usando pip/uv cru; seguir `pm/AGENTS.md` e preservar o processo Hermes ativo.
- Nenhuma economia de tokens/custo nem aceleração ponta a ponta foi medida. O próprio teste marca `system2_calls:not_measured` e `laya_checkpoint_inference:not_measured`.
- Nenhum efeito de Browser foi executado via novo caminho. Nenhuma reconciliação foi alterada, nenhum estado histórico foi liberado; o app ativo não foi reiniciado. Nada foi commitado, staged, enviado ou mesclado.

## Única próxima qualificação material, se esta missão for retomada
1. Verificar branch/HEAD, estado Git e escritores concorrentes; preservar WIP, sem reset/stash/clean.
2. Disponibilizar Laya **em ambiente isolado gerenciado pelo PM**, sem alterar a `.venv` do Hermes em uso; confirmar proveniência e comparar acurácia/abstenção em português nos exemplos read-only.
3. Executar uma solicitação read-only de localização pelo fluxo **humano real** do Hermes, sem automatizar teclado/mouse nem tocar no ledger produtivo; verificar readback e número real de chamadas System 2 vs baseline equivalente.
4. Se houver ganho mensurado sem regressão de segurança, qualificar ativação; caso contrário, manter o modo restrito a rótulo exato e não promover integração de modelo.

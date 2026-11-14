# Hermes Work — Qualificação System 1 Browser + Laya (07/11/2026)

**Decisão:** rota de produção não promovida; permanece **desabilitada por padrão** (`HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED` diferente de `1`). Critérios pendentes: mensagem humana real no Desktop → TaskRun autenticado → recibo verificado → comparação real de chamadas/custo do System 2. Provas isoladas não substituem esse gate.

## Ambiente e preservação
- Checkout compartilhado: `C:\Github\hermes-agent`, `main@f1d5ab2f03`. Havia **358 entradas modificadas/não rastreadas** no preflight, de diversas missões. Não houve reset, stash, clean, switch, commit, push, merge ou reinício do Hermes.
- Processo Hermes ativo usa `C:\Github\hermes-agent\.venv`; Laya continua ausente desse ambiente.
- PM criou somente **dois ambientes laterais** em `%LOCALAPPDATA%\HermesWorkstation\qualification\system1-laya` (requisitos mínimos para benchmark) e `...\system1-laya-project` (dependências fechadas do Hermes + extra `system1-laya`). Nenhum foi selecionado como ambiente do aplicativo ativo.
- Proveniência estrita no ambiente PM: **PASS**, Laya `0.3.23`, Torch `2.14.1+cpu`, Transformers `5.18.0`; bytes da fonte vendorizada e origem do pacote confirmados. Modelo multilíngue em cache local; inferências realizadas com `HF_HUB_OFFLINE=1` e `TRANSFORMERS_OFFLINE=1`.

## Prova de inferência em português (CPU, 9 casos)
Evidência: `workstation/benchmarks/system1_laya_pt_results_20261107.json`, produzido por `workstation/benchmarks/system1_laya_pt_qualification.py`.
- Primeira passagem **antes do hard guard**: 7/9 corretos, 1 falso aceite. Duplicidade: o Laya escolheu um de dois botões idênticos “Relatórios”, confiança 0,9012. Risco inaceitável.
- TDD: dois testes RED reais (`test_duplicate_exact_labels_fail_closed_before_model`, `test_two_partial_matches_fail_closed_before_model`), depois GREEN. O guard passou a rejeitar ambiguidades **antes da inferência**, preservando fallback e sem afetar os executores.
- Reexecução guardada: **8/9 corretos, 0 falsos aceites, 4 fallbacks**, p50 de inferência aquecida **272,38ms** e máxima aquecida **310,45ms**. A primeira inferência levou **10,15s** com carregamento. O caso “Calendário editorial” foi respondido corretamente pelo modelo, mas abstido pelo limiar de confiança (0,4119); não mascarar esse caso.
- Esses casos são sintéticos. N=9 não demonstra robustez geral e a latência do modelo não prova economia frente ao System 2.

## Provas integradas
- `workstation/benchmarks/system1_laya_hermes_smoke.py` executado no ambiente de projeto PM: provedor real `LayaDecisionProvider`, pergunta parcial em português, modelo correto, ref `@e1` verificada e **DecisionReceipt** persistido em diretório sandbox.
- `node apps/desktop/e2e/workstation-system1-native-snapshot-runner.cjs`, passando `HERMES_LAYA_QUAL_PYTHON` apontando para o Python isolado: **PASS / exit 0**. Criou Chromium Electron isolado com fixture local 127.0.0.1, capturou 9 snapshots reais e passou dois deles ao provedor Laya real; modelo selecionou `@e1` para “Relatório” com confiança **0,9811**, readback independente validou a mesma referência e confirmou receipt.
- Repetição final do E2E: snapshot p50 **4,967ms**, p95 de 9 amostras **7,260ms**; seletor determinístico p50 **0,024ms**, p95 **0,104ms**. Provedor Laya com cold load e emissão de recibo **20,13s**. Não comparar diretamente esses números com chamada System 2; não há baseline equivalente.
- `scripts/run_tests.sh workstation/tests/test_system1_browser_read_fastpath.py workstation/tests/test_operational_resolution_provider.py workstation/tests/prefabs/test_prefabs.py workstation/tests/test_system1_capability_routing.py workstation/tests/test_system1_safety.py -j 3 -q`: **59 PASS, 0 FAIL** (suites focadas, não a suíte total).
- `ruff check` nos arquivos Python modificados/adicionados: **PASS**; `git diff --check` no arquivo versionado alterado: **PASS**.
- Teste RED→GREEN da configuração: sem flag, `maybe_resolve_browser_find` tentava construir dispatcher; agora retorna `None` antes de qualquer IO e o caminho anterior permanece inalterado. Teste de habilitação explícita usa flag **somente dentro do processo de teste**.

## O que permanece sem prova
1. **Fluxo realmente originado na UI humana do Desktop** com TaskRun/BrowserTask de teste e identidade coerente: não foi executado. É proibido enviar um prompt/abrir uma nova tarefa na sessão produtiva ou alterar o ledger dela para suprir essa lacuna. Um teste com envelope humano mockado ou snapshot real isolado **não equivale** a essa prova.
2. **Chamadas e custos reais do System 2**: não há medição comparável nem baseline real; resultados de teste registram `not_measured`. Logo, não afirmar redução de latência ou tokens end-to-end.
3. Laya **não está integrado ao Python do Hermes em execução**; PM isolado não altera a ativação do produto. A flag de fast path permanece desligada por padrão.

## Única próxima ação condicionada
Se houver necessidade de promoção, montar uma **sessão de teste verdadeiramente isolada** (UI + backend + BrowserTask + armazenamento + provedor de modelo), enviar uma mensagem humana de localização read-only via ponte autorizada, registrar chamadas System 2, latência p50/p95 e readback, comparar com a mesma tarefa pelo caminho antigo e só então decidir ativar a rota. **Não tocar nas sessões, filas, leases ou ledgers produtivos.**


## Verificação final do Hermes em execução (07/11/2026, após os testes)
- `node apps/desktop/scripts/hermes-nav.mjs status`: **exit 1 — AI Control endpoint unavailable**. `node apps/desktop/scripts/check-browser-status.mjs`: mesma falha. Na verificação passiva de processos havia processos de desenvolvimento Node/Vite/TypeScript, mas **nenhum `electron.exe` correspondente ao Hermes**. O aplicativo em execução não pode ser considerado homologado neste instante.
- Os testes Electron anteriormente descritos rodaram **em processos e perfis temporários isolados**, com sucesso; não são prova de que o Desktop produtivo esteja disponível agora.
- **Não foi solicitada nem realizada reinicialização, mudança do toggle AI Control, emissão de prompt na sessão produtiva ou intervenção em mouse/teclado.** Desconhece-se se o usuário fechou o Desktop ou se uma outra sessão o reiniciou.
- Git em `main@f1d5ab2f03`; contagem de status no fechamento **367**, com alterações concorrentes presentes. Arquivos desta missão continuam não staged, salvo a inserção versionada já identificada em `workstation/integrations/hermes/operational_resolution.py`.
- Criterio de conclusão operacional **não atingido**: Desktop humano indisponível e comparação real de chamadas System 2 não realizada. **Não promover a flag**.

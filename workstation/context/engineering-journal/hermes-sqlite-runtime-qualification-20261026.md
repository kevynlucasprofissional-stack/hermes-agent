# Hermes Work — SQLite 3.53.4 e qualificacao operacional (26/10/2026)

## Contexto, autorizacao, claims
- Retomada direta de workstation/context/engineering-journal/hermes-model-init-remediation-20261026.md. A dispensa especifica do Stage A concedida pelo mantenedor permanece restrita a esta missao, nao qualifica release.
- Checkout: C:\Github\hermes-agent, branch main, HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e; 157 arquivos dirty/untracked no preflight.
- Nao houve commit, push, merge, branch switch, reset, clean ou stash. Claims existentes de chatgpt-hermes-init-fix-20261026 continuam READY_FOR_INTEGRATION e seus arquivos nao foram modificados. Novo claim exclusivo somente para este documento.

## Preflight operacional
- Electron e backend Hermes antigos nao estavam mais em execucao; porta antiga 60272 estava sem listener. Python/Node restantes pertenciam a local-mcp-bridge, Codex, Desktop Commander e Remotion; nada foi interrompido.
- Havia sessao Desktop sem ended_at e oito task_runs Kanban com status running. Os leases estavam expirados ha dias e worker_pid=NULL; nao foram apagados, cancelados ou modificados.

## Backup e rollback de dados
- Snapshot em C:\Users\Kevyn Lucas\AppData\Local\hermes\backups\sqlite-maintenance-20261026-150012.
- 8 bancos, 14 arquivos com WAL/SHM, 571.950.280 bytes. O estado dos arquivos originais ficou estavel durante a copia. SHA-256 das copias e originais coincidiram e os valores estao no manifest.json.
- Recuperacao testada copiando todos os arquivos para restore-validation, preservando raw intacto; todos os oito bancos passaram PRAGMA integrity_check(3) usando SQLite 3.53.4, incluindo state.db com WAL de 12.158.152 bytes.
- Nao se alterou journal_mode dos bancos de producao, nao houve checkpoint forcado e nao foi feita substituicao dos DBs originais.

## SQLite privado
- SQLite 3.53.4 oficial Windows x64 preparado previamente; ZIP oficial SHA3-256 deddee963c810d1eeac3ce5e15c7c41da21a1c54d7a39cf54fbf577d2f50de3a.
- DLL e _sqlite3.pyd CPython 3.14 instaladas primeiramente em %LOCALAPPDATA%\hermes\runtime\sqlite-3.53.4-win-x64, pois a distribuicao uv global nao pode ser modificada.
- Hook local em C:\Github\hermes-agent\.venv\Lib\site-packages\00_hermes_private_sqlite.pth.
- Um teste da suite oficial recusou acesso ao HOME real feito por biblioteca no local inicial da DLL. O runtime privado foi realocado para %LOCALAPPDATA%\HermesPrivateRuntime\sqlite-3.53.4-win-x64, diretorio irmao ao HOME real; o hook .pth foi atualizado. Nenhum codigo versionado foi editado.
- Processos novos da venv carregam SQLite 3.53.4 do diretorio irmao. O Desktop que havia iniciado antes da realocacao continua com sqlite3.dll 3.53.4 do diretorio interno anterior carregada em memoria.
- Rollback do hook repetido e validado: com .pth temporariamente renomeado, subprocesso retornou SQLite 3.50.4; reativado o hook, retornou 3.53.4. Rebuild da venv pode exigir reaplicacao do hook.

## Validacao real do Desktop
- Inicializacao por npm run dev --workspace apps/desktop, Electron PID 28720, backend Python PID 19716, porta 49345. Renderer concluiu carregamento e janela revelou.
- Módulos carregados pelo backend foram observados em Get-Process -Module, com _sqlite3.pyd e sqlite3.dll da pasta privada interna, FileVersionInfo de sqlite3.dll = 3.53.4. A distribuicao uv compartilhada permaneceu intacta.
- GET /api/status retornou HTTP 200. GET /api/plugins/vault/status retornou HTTP 401 sem token: protecao preservada, sem bypass. O plugin Vault foi montado em /api/plugins/vault/ e passou 4 respostas HTTP 200 em TestClient isolado na fase anterior.
- O foco do Windows estava em uma janela chamada Adicionar um dispositivo, nao em Hermes. Por nao interromper a atividade humana, nenhum clique ou mensagem foi enviada na GUI. Portanto a resposta autenticada na interface Electron permanece PENDENTE.
- O gateway isolado em etapa anterior criou sessao DeepSeek e obteve message.complete com resposta real iniciada por OK.
- Nova CLI com HOME temporario e SQLite corrigido retornou OK; usage confirmou provider deepseek, model deepseek-flash, api_calls 1, exit 0.

## Testes oficiais e logs
- Runner oficial scripts/run_tests.sh, oito arquivos (OpenAI, Vault, SQLite WAL), Python 3.14 e SQLite 3.53.4: 62 PASS, 4 SKIP, 0 FAIL apos ajuste de isolamento. Testes em Windows, skips incluidos testes exclusivos Linux.
- Desde boot de 15h04 nao ha novos registros de deadlock, failed-to-initialize-OpenAI-client, No module named yaml ou WAL-reset nos logs inspecionados.
- MCP my-server, trello e browserclaw continuam disabled. Warning de discovery com zero servidores conectados e esperado com todos desabilitados, mas ainda aparece.
- Outros avisos nao bloqueantes: LayaDecisionProvider ausente, comando /plan de skill duplicado, duas worktrees antigas com trabalho nao integrado.

## Estado de aceite / handoff
- FUNCIONAL LOCALMENTE: DeepSeek, prewarm SDK, Vault HTTP isolado, SQLite privado com WAL e recuperacao dos backups.
- VALIDADO NO DESKTOP: boot Electron/backend real, SQLite 3.53.4 carregado, /api/status 200 e rota Vault montada.
- PENDENTE: resposta enviada pela GUI Electron autenticada; Vault HTTP autenticado no Desktop; restart futuro para que backend passe a carregar SQLite do caminho privado irmao. A versao carregada hoje ja e 3.53.4.
- NAO MODIFICAR: worktrees, agentes externos, claims de outros agentes, tarefas Kanban expired/running e bancos de dados sem novo backup/janela.
- ROLLBACK: com Hermes fechado, renomear .venv\Lib\site-packages\00_hermes_private_sqlite.pth para .disabled e reiniciar. Se restaurar dados, usar todos os arquivos da mesma geracao raw e conferir SHA-256 do manifest.json; nunca restaurar sobre escritores ativos.
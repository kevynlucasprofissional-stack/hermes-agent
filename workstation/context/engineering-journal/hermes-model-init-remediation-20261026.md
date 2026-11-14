# Hermes Work — Remediacao do modelo e boot (2026-10-26)

## Estado e limites
- Checkout C:\Github\hermes-agent, main, HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e.
- 149 alteracoes locais e 15 claims antes do inicio; sem alteracoes Git, branch, reset ou stash.
- Claim proprio exclusivo: chatgpt-hermes-model-p0-20261026, somente para este novo arquivo.
- Stage A / H-079 PENDING / NOT QUALIFIED conforme workstation/context/CURRENT_STATE.md, sem dispensa nesta missao.
- Consequencia: nenhuma alteracao em codigo runtime e nem nos arquivos sob claims de outros agentes.

## DeepSeek padrao — CONFIGURACAO APLICADA
- Configuracao global: C:\Users\Kevyn Lucas\AppData\Local\hermes\config.yaml.
- Perfil: C:\Users\Kevyn Lucas\AppData\Local\hermes\profiles\default\config.yaml.
- Ambos usam model.default=deepseek-flash; model.provider=deepseek; model.base_url=https://api.deepseek.com/v1; model.api_mode=chat_completions.
- Configuracoes validadas com _validated_main_model_selection; gravadas por persist_model_selection; demais secoes YAML preservadas.
- DEEPSEEK_API_KEY presente; valor nao lido nem impresso nesta evidencia.
- Backups em cada diretorio: config.yaml.bak-hermes-p0-20261026-130211.
- Smoke CLI global, sem override: resposta OK, exit 0; usage model=deepseek-flash, provider=deepseek, 1 API call, 22249 input tokens, 2 output tokens, custo estimado USD 0.003339702.
- Smoke CLI com HERMES_HOME=profiles/default, sem override: resposta OK, exit 0; usage model=deepseek-flash, provider=deepseek, 1 API call, 11313 input tokens, 2 output tokens, custo estimado USD 0.00169815.
- Evidencias: TEMP\hermes-deepseek-smoke-20261026.json e TEMP\hermes-deepseek-default-profile-smoke-20261026.json.
- Ainda nao validada uma nova sessao pela interface Electron. Backend existente nao foi reiniciado.

## MCP my-server — CONFIGURACAO MITIGADA
- Desabilitado somente mcp_servers.my-server.enabled=false, preservando seu comando npx e argumento /path/to/dir para revisao futura.
- As outras duas entradas MCP nao sofreram alteracoes.
- Backup anterior a alteracao: config.yaml.bak-mcp-p1-20261026-130326 no Hermes home global.
- Discovery em processo novo permanece pendente, pois nao houve restart dos processos em uso.

## Deadlock — CODIGO AINDA NAO CORRIGIDO
- Ambiente: Python 3.14.0, openai 2.24.0.
- Evidencia anterior: 10 importacoes concorrentes do SDK, 3 _DeadlockError em openai.types; com preimport de OpenAI e ChatCompletion, 0/10 em um teste.
- Caminhos: agent/process_bootstrap.py::_load_openai_cls; agent/agent_runtime_helpers.py::create_openai_client; agent/agent_init.py::_init_openai_client.
- Corrigir depois de Stage A qualificado ou dispensa explicita deste trabalho: prewarm seguro antes do fan-out, mantendo patchability e sem lock global longo; testes RED/GREEN em subprocessos limpos e agentes auxiliares.

## Vault — CODIGO AINDA NAO CORRIGIDO
- workstation/vault.py importa yaml e usa yaml.safe_load e yaml.safe_dump, mas PyYAML esta ausente.
- ruamel.yaml ja esta instalado. Avaliar migracao com semantica de frontmatter, Unicode e roundtrip preservada; ou dependencias extras corretamente pinadas.
- Executar workstation/tests/test_vault.py e regressao de rota API apos gate.

## SQLite — RISCO SEM MITIGACAO INTRUSIVA
- Python 3.14.0 na venv e demais runtimes 3.13.12 / 3.14.3 observados utilizam SQLite 3.50.4.
- PRAGMA quick_check(1), somente leitura, retornou ok para state.db (558272512 bytes), projects.db (45056 bytes), kanban.db (749568 bytes).
- quick_check nao descarta WAL-reset bug. Nao foi trocada DLL, nem journal mode, nem foram feitos checkpoints forcados.
- Upgrade para SQLite 3.51.3+ ou backport oficial exige janela sem writers, backup consistente, testes em copia e rollback.

## Pendente para encerramento
- Qualificar Stage A/H-079 ou registrar dispensa de escopo especifico, mantendo seguranca/claims.
- Implementar e testar correcoes de OpenAI SDK e Vault.
- Testar discovery MCP e nova sessao Electron apos restart seguro, sem interromper outros agentes.
- Rever agent.log, gui.log, errors.log e desktop.log apos novo marco de startup.
- Nao alterar historico de sessoes pinadas em modelos anteriores, inclusive Nous 404 (26/10 08:11).
## Evidencia complementar executada
- Stress independente em 6 processos Python, 10 threads por processo: 3 rodadas cold tiveram respectivamente 4, 6 e 1 _DeadlockError (11 no total); 3 rodadas com preimport de OpenAI e ChatCompletion tiveram 0 erros, 0 threads penduradas. O teste nao altera runtime e e prova RED + mitigacao experimental, nao patch de producao.
- Teste do Vault: python -m pytest workstation/tests/test_vault.py -q --disable-warnings --maxfail=1: exit code 2, falha na coleta por ModuleNotFoundError: No module named 'yaml', import no proprio arquivo de testes (linha 8). Corrigir testes e modulo em conjunto apos gate.
## Continuacao autorizada em 2026-10-26 — 14h America/Sao_Paulo

Autorizacao: o mantenedor dispensou expressamente Stage A/H-079 NESTA MISSAO para corrigir deadlock, Vault e validar MCP/SQLite. Excecao de processo, nao prova de Stage A e nao qualificacao de release. Os arquivos canonicos CURRENT_STATE.md e engineering-journal/CURRENT.md tem outros claims e foram preservados. Esta entrada exclusiva registra a excecao e os resultados.

Preflight: main, HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e, 150 arquivos dirty/untracked no inicio. Claims disjuntos para agent/process_bootstrap.py, hermes_cli/main.py, hermes_cli/web_server.py, tui_gateway/entry.py, workstation/vault.py, workstation/tests/test_vault.py, workstation/tests/test_vault_tools.py, tests/agent/test_openai_import_deadlock.py, agent/agent_runtime_helpers.py, agent/auxiliary_client.py e este diario. Nenhum arquivo reclamado por outro agente foi editado.

Mudancas:
- agent/process_bootstrap.py: funcao prewarm_openai_sdk() conclui import de OpenAI, ChatCompletion e Completions antes dos workers, preservando proxy lazy existente.
- hermes_cli/main.py: cmd_chat preaquece SDK antes de iniciar setup e threads. hermes_cli/web_server.py: lifespan preaquece SDK antes de workers. tui_gateway/entry.py: main preaquece SDK em sua primeira fase.
- workstation/vault.py: safe_load/safe_dump do PyYAML migrados para ruamel.yaml.YAML(typ=safe, pure=True), com StringIO, Unicode e tratamento correto de YAMLError.
- workstation/tests/test_vault.py: teste YAML migrado para ruamel.
- tests/agent/test_openai_import_deadlock.py: 3 subprocessos limpos, cada um com 10 threads e criacao de clientes offline, incluindo cliente auxiliar.
- agent/agent_runtime_helpers.py e agent/auxiliary_client.py inspecionados, nao modificados.

Testes: scripts/run_tests.sh no Git Bash, -j 2, cinco arquivos, 31 passed, 2 skipped, 0 failed. git diff --check para os seis arquivos existentes modificados PASS; sintaxe Python PASS; importacao de plugins.vault.dashboard.plugin_api PASS; parse Unicode com acao/cafe PASS. Ruff pleno de vault.py acusa debitos de tipagem existentes anteriores; sem autofix indiscriminado.

MCP: Hermes mcp list mostra my-server disabled; browserclaw e trello permanecem disabled conforme a configuracao anterior. Discovery apos restart ainda pendente.

Desktop: backend Python e Electron continuam executando processos anteriores das 11h26. Sem restart, patch nao foi carregado no processo antigo. Tentativa de WebSocket local para criar sessao independente em /api/ws recebeu HTTP 403: nao contornar autenticacao. Dois testes anteriores CLI com chamada real confirmaram DeepSeek Flash nos perfis global e default. Nao ha E2E de nova sessao Electron apos patch.

SQLite: Python 3.14.0 continua com SQLite 3.50.4 (WAL-reset afetado); quick_check(1) anterior em state.db, projects.db e kanban.db retornou ok. O backend tem writers ativos e bancos em WAL; sem janela comprovadamente segura, backups consistentes e rollback, nenhuma atualizacao do runtime/DLL foi aplicada; nao alterar journal mode nem forcar checkpoints. Atualizar para 3.51.3+ ou backport oficial em janela coordenada.

Pendencias: nova inicializacao controlada do Desktop quando outros agentes estiverem ociosos, sessao autenticada pela UI, Vault API e MCP discovery verificados contra logs novos; migracao SQLite sob backup consistente e sem escritores; Stage A tecnicamente pendente.
## Qualificacao complementar (2026-10-26, tarde) — CONTINUACAO SEM RESTART DA INSTANCIA PRINCIPAL

### Integridade/ownership
- Mantidos main e HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e, 157 entradas dirty/untracked observadas no preflight, sem merge/commit/push/reset/clean/stash.
- Claims chatgpt-hermes-init-fix-20261026 continuam READY_FOR_INTEGRATION e reservam exclusivamente arquivos da correção e este diario. Nenhum codigo foi modificado nesta continuacao.
- Stage A foi dispensado para esta missao pelo mantenedor, mas ainda nao esta tecnicamente qualificado.

### Desktop principal — por que nao reiniciado
- PID Electron 24184 e backend Python PIDs 24332/21816 iniciados as 11h26, com conexoes locais estabelecidas.
- state.db possui sessao Desktop ainda sem ended_at, iniciada UTC 11:11, com last_activity_at UTC 11:13; nao ha novas mensagens no periodo de 45 minutos verificado.
- kanban.db tem oito tarefas e oito task_runs com status running, porem claim_expires antigos e worker_pid NULL; nao se concluiu que e seguro apagar/reparar esses estados.
- Desktop registrou as 14h37:19 a ocultacao na bandeja, evidenciando interacao recente; nao interromper a instancia de forma remota sem janela de manutencao.
- Logs do processo antigo relatam event-loop stalled 123s e 2475.9s, e Resume failed: gateway is not connected, todos anteriores a qualificacao isolada e sem relacao causal demonstrada com o novo patch.
- Tentativa anterior de WS da instancia principal resultou HTTP 403; nao houve bypass de autenticacao.

### Gateway real isolado, codigo corrigido (PASS)
- HOME temporario criado em TEMP/hermes-gateway-qual2-n_iaulwc, configurado com deepseek-flash e DEEPSEEK_API_KEY herdada de modo seguro, sem acesso a state.db do perfil principal.
- Gateway ready; session.create modelo deepseek-flash; prompt.submit aceito com status streaming e user_row_id 1; message.complete texto iniciado com OK. Conclusao em aproximadamente 13.1s.
- state.db da instancia de qualificacao contem source desktop, model deepseek-flash, billing_provider deepseek, api_call_count 1, message_count 2.
- Isto demonstra RPC real e inferencia atraves do gateway apos patch; NAO e sessao verificada pela interface Electron principal. Primeiro teste de harness falhou apenas por campo source extra em prompt.submit; corrigido na segunda tentativa.

### Vault API HTTP isolada (PASS)
- FastAPI TestClient com router plugins.vault.dashboard.plugin_api e VaultManager com root TEMP isolado.
- GET /status 200, POST /notes 200, GET /notes/Validacao 200, GET /notes 200 com count=1. Campos Unicode testados; nenhuma nota da conta principal modificada.
- LayaDecisionProvider ausente registrado como aviso separado, nao bloqueante para este teste.

### MCP (PASS apenas para configuracao/desabilitados)
- HOME isolado com my-server, browserclaw e trello todos enabled=false: mcp_servers_awaiting_connect() = []; get_mcp_status() relata disabled, connected=False em todos.
- hermes mcp list executado na configuracao real confirma os tres desabilitados.
- Nenhum endpoint MCP externo testado ou ligado; verificacao na inicializacao do Desktop principal continua pendente.

### SQLite (STAGING VERIFICADO, PRODUCAO NAO ALTERADA)
- Runtime principal CPython 3.14.0 continua linkado a SQLite 3.50.4; modulo nativo usa DLL compartilhada em AppData/Roaming/uv/python/cpython-3.14-windows-x86_64-none/DLLs/sqlite3.dll, portanto substituir ali afetaria outros ambientes.
- Obtida DLL x64 oficial SQLite 3.53.4 do sqlite.org, arquivo sqlite-dll-win-x64-3530400.zip, em TEMP/hermes-sqlite-3530400-stage-20261026. SHA3-256 validado: deddee963c810d1eeac3ce5e15c7c41da21a1c54d7a39cf54fbf577d2f50de3a.
- Copia isolada de _sqlite3.pyd junto a DLL oficial, ativada SOMENTE no subprocesso pelo PYTHONPATH de staging, reportou sqlite3.sqlite_version=3.53.4 e importou a extensao do diretorio temporario.
- Teste isolado SQLite 3.53.4: modo WAL, insert/select com Unicode, PRAGMA quick_check -> ok.
- Gateway Hermes isolado com esta DLL 3.53.4 iniciou, publicou gateway.ready e criou nova sessao deepseek-flash em 3.58s, sem warning WAL-reset nos logs capturados.
- Nenhum banco principal, runtime compartilhado, .venv ou SQLite DLL de producao modificado. Nao foi feito backup completo de state.db (mais de 550MB), checkpoint, conversao WAL ou manutencao online: migracao permanece BLOQUEADA sem janela sem writers.
- Plano de migracao: encerrar responsavelmente execucoes agendadas e instancias Hermes com consentimento/janela, comprovar que nenhum writer resta, obter backups consistentes de todos DBs (incluindo WAL), testar restauracao offline e integridade, preparar runtime privado de Hermes com SQLite >=3.51.3 sem tocar na distribuicao uv global, executar suite e smoke, trocar launcher apenas apos qualificacao, manter rollback testado.

### Suite final repetida
- scripts/run_tests.sh com HERMES_PYTHON=.venv/Scripts/python.exe, -j 2 em tests/agent/test_openai_import_deadlock.py, tests/agent/test_create_openai_client_reuse.py, tests/agent/test_create_openai_client_kwargs_isolation.py, workstation/tests/test_vault.py e workstation/tests/test_vault_tools.py.
- Resultado atual: 31 PASSED, 2 SKIPPED, 0 FAILED, runner exit 0.
- Nao foi realizada implantacao/restart do Desktop real nesta continuacao.

### Handoff minimo
- Preservar claims e checkout; nao tocar em arquivos de outras lanes.
- Janela operacional consensual: parar workers, cron, backend e Electron somente apos confirmar tarefas ociosas; backup e rollback; trocar apenas runtime privado; reiniciar, validar sessao autenticada pela interface, API Vault e logs novos; release apenas apos os gates de produto.
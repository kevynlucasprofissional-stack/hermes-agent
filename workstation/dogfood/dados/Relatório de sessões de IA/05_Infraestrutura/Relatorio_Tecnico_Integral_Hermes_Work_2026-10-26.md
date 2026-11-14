# Relatório Técnico Integral de Sessão
## Hermes Work — diagnóstico, correção de inicialização, DeepSeek e SQLite

> **Natureza:** auditoria retrospectiva e documento de continuidade, não ata de homologação ou prova de release.  
> **Data do trabalho auditado:** 26/10/2026. **Inspeção complementar:** 26/10/2026, aproximadamente 17h31 (America/Sao_Paulo).  
> **Convenção:** **VERIFICADO** = evidência concreta; **REPORTADO** = afirmação sem evidência acessível suficiente; **PARCIAL** = critério parcialmente atendido; **FALHOU** = execução com erro; **PENDENTE** = não executado; **INDETERMINADO** = prova insuficiente. A validade temporal importa: `VERIFICADO` em uma fase não assegura estado idêntico depois.

## 0. Identificação e cobertura da sessão

| Campo | Informação |
|---|---|
| Projeto | Hermes Agent / Hermes Work, especialmente Desktop Electron, gateway TUI, SDK OpenAI, Vault, MCP e persistência SQLite |
| Repositório | `C:\Github\hermes-agent` |
| Branch/HEAD observados | `main` / `f1d5ab2f030e940ed4571371b0de45a21a009c9e` |
| Objetivo | Restaurar a inicialização do Hermes, tornar DeepSeek padrão, preservar ambiente multiagente e corrigir risco SQLite sem perda de dados |
| Ambiente | Windows 11; `.venv` com Python 3.14.0; `openai==2.24.0`; Electron/Vite; SQLite 3.50.4 inicialmente, SQLite 3.53.4 privado posteriormente |
| Fonte operacional | Ferramenta conectada **Controle Windows**, invocada para comandos PowerShell e subprocessos Python; evidências de scripts, logs, SQLite e Git |
| Artefatos de engenharia | `workstation/context/engineering-journal/hermes-model-init-remediation-20261026.md`; `.../hermes-sqlite-runtime-qualification-20261026.md` |
| Completude | **Média**: boa cobertura de solicitações, saídas de ferramentas e arquivos finais; investigação inaugural parcialmente recuperada de contexto compactado |

### 0.1. Material efetivamente disponível

Histórico desta conversa; registro compactado da investigação inicial (incluindo reprodução em 10 threads); comandos e respostas de ferramenta preservados nas continuações; inspeção **somente de leitura** dos patches atuais via `git diff`, do teste `test_openai_import_deadlock.py`, configurações YAML, `.pth`, manifestos, claims, processos Windows, módulos carregados, `state.db` e logs do Hermes. Nenhuma modificação do dispositivo foi feita **durante a auditoria**.

### 0.2. Limites e proveniência

1. A primeira captura do erro e parte das saídas de ferramentas da investigação inaugural encontram-se resumidas/compactadas. Sua existência é suportada pelo histórico disponível, mas não há reprodução textual integral de todas as interações originais.
2. `state.db` e logs podem conter mudanças posteriores às últimas respostas do assistente. A inspeção de 17h31 é uma **fotografia atual**, não uma extensão retroativa da evidência de conclusão às 15h15.
3. Não foi feito teste pela interface Electron autenticada durante a auditoria, nem reexecutada a suíte; resultados dos testes provêm de saídas anteriores de ferramentas e do registro histórico.
4. Os resultados de chamadas externas DeepSeek foram observados por respostas CLI/gateway e arquivos `usage.json`; não foram auditados registros financeiros externos ou faturamento da conta.

## 1. Sumário executivo

O primeiro problema foi a mensagem `Failed to initialize OpenAI client: deadlock detected by _ModuleLock('openai.types.chat')`. A investigação encontrou uma corrida plausível entre imports frios do SDK OpenAI executados por threads concorrentes; testes reproduziram `_DeadlockError` e indicaram eficácia do pré-carregamento.

O escopo foi ampliado para definir `deepseek-flash` como padrão global e do perfil `default`, desabilitar a entrada MCP de exemplo `my-server`, eliminar a dependência ausente de PyYAML no Vault e corrigir o SQLite 3.50.4 afetado por WAL-reset. As configurações DeepSeek foram aplicadas e comprovadas por inferência real na CLI e pelo gateway isolado.

Com dispensa explícita e limitada do Stage A pelo usuário, foram escritos patches de pré-carregamento e migração para `ruamel.yaml`, ainda **sem commit**. A suíte oficial final teve **62 PASS, 4 SKIP, 0 FAIL**, abrangendo SDK, Vault e SQLite WAL.

Foram preservados 8 bancos em 14 arquivos (571.950.280 bytes), com SHA-256 e restauração em cópia separada aprovada por `PRAGMA integrity_check(3)`. SQLite 3.53.4 foi ativado na `.venv` por runtime privado e seu rollback foi testado. O Electron e backend reais reiniciaram; o processo carregou DLL 3.53.4, e `/api/status` respondeu HTTP 200.

**Não ficou demonstrada uma resposta originada na interface Electron autenticada após o reinício.** Na inspeção complementar, apareceu uma troca posterior de uma sessão para NVIDIA (15h18), embora os dois padrões persistidos continuem DeepSeek. Restam integração/commit do trabalho, qualificação da UI, análise de avisos e manutenção das invariantes multiagente.

## 2. Objetivos, requisitos e evolução do escopo

### 2.1. Sequência de pedidos e decisões do usuário

| Momento lógico | Pedido efetivo | Evolução / resultado |
|---|---|---|
| Investigação inicial | Investigar no Windows por que o Hermes não iniciava o cliente OpenAI e apresentava `_ModuleLock('openai.types.chat')` | Causa provável investigada, testes de reprodução e pré-importação |
| Solicitação de refinamento | Configurar DeepSeek como modelo padrão e corrigir os erros; antes, aprofundar a investigação e entregar prompt de implementação | Investigação adicional; prompt preparado, **sem executar modificações nessa etapa** |
| Missão P0/P1 enviada | Implementar DeepSeek global/default; corrigir deadlock, Vault, MCP, 404 Nous e risco SQLite; testar e documentar | Inicialmente bloqueio de governança Stage A |
| Dispensa explícita | Usuário autorizou **pular Stage A nessa missão** | Autorização aplicada apenas ao escopo da missão, sem declarar Stage A tecnicamente qualificado |
| Continuação 1 | Aplicar patches SDK/Vault, regressões e validação MCP/SQLite | 31 testes PASS, 2 SKIP; patches não commitados |
| Continuação 2 | Qualificar reinício seguro, nova sessão Desktop e preparar SQLite corrigido | Gateway independente com DeepSeek respondeu; SQLite 3.53.4 testado, mas Desktop principal mantido inicialmente |
| Continuação 3 | Reiniciar com segurança, backup/rollback, runtime privado e qualificação final | Backup/restauração, instalação SQLite 3.53.4 privada, boot real, 62 PASS/4 SKIP; UI autenticada ainda pendente |
| Pedido atual | Auditar integralmente a própria sessão, sem novos desenvolvimentos | Relatório presente, com inspeção de leitura do estado final |

### 2.2. Requisitos transversais

- **Funcionamento:** novas sessões devem iniciar em `deepseek-flash` sem override; antigas escolhas explícitas/histórico preservados; SDK inicializa sob concorrência; Vault lê/grava Markdown com frontmatter/Unicode; MCP inválido não inicia; bancos íntegros e runtime corrigido.
- **Arquitetura:** usar APIs canônicas de configuração, interfaces e `seams` existentes; evitar mudanças arbitrárias em bancos/instalador; não usar retries cegos como substituto de causa raiz.
- **Governança:** checkout `main` compartilhado, registrar/respeitar claims por arquivo, nenhuma sobrescrita de trabalho alheio; nenhuma branch, reset, clean, stash, commit, merge ou push.
- **Segurança operacional:** não reiniciar agentes externos; não contornar autenticação; não substituir `sqlite3.dll` da distribuição uv global; backup consistente, integridade e rollback antes de migração.
- **Aceite:** testes de código e de execução real, logs por janela temporal, nova sessão Electron autenticada, prova de modelo default, inventário e relatório de continuidade.

### 2.3. Decisões e sugestões não equivalentes a pedidos

O usuário exigiu DeepSeek e segurança da migração; a decisão de usar pré-carregamento específico, `ruamel.yaml`, `.pth` na `.venv`, `npm run dev --workspace apps/desktop`, pastas temporárias e teste isolado foi tomada durante a investigação/implementação. A recomendação de não tomar o foco de outra janela foi decisão operacional do assistente. Stage A não foi abandonado globalmente: houve **dispensa específica**, concedida pelo usuário após recusa inicial.

### 2.4. Aceites não completados

Não há prova de mensagem redigida/enviada e resposta recebida **na UI Electron real pós-reinício**; `/api/plugins/vault/status` respondeu HTTP 401 sem credencial, não houve teste autenticado dessa rota no backend principal; código permaneceu não integrado por commit/merge; não há prova de comportamento após reconstrução/reinstalação completa da `.venv`.

## 3. Linha do tempo técnica da sessão

### Fase 1 — Diagnóstico do erro inaugural (VERIFICADO/PARCIAL)

**Sintoma:** captura do Hermes: `Hermes couldn't finish the reply`, com `Failed to initialize OpenAI client: deadlock detected by _ModuleLock('openai.types.chat')`. O frontend iniciou; a falha ocorreu na construção do cliente do agente.

**Inspeção:** `agent/process_bootstrap.py::_load_openai_cls` importa `OpenAI` tardiamente; `agent/agent_runtime_helpers.py::create_openai_client` solicita o proxy; `agent/agent_init.py::_init_openai_client` captura o erro e o encapsula em `RuntimeError`. Ambiente Python 3.14.0 e OpenAI SDK 2.24.0.

**Experimento:** subprocessos Python com `threading.Barrier(10)` e importação concorrente de `openai.OpenAI`, `openai.types.chat` e `openai.resources.chat.completions`: **3/10** `_DeadlockError` em amostra inicial (`openai.types`, não necessariamente o mesmo objeto-lock de produção). Com `from openai import OpenAI` e `from openai.types.chat import ChatCompletion` antes de iniciar threads: **0/10**. A localização precisa da inversão de locks interna do SDK não foi provada por stack de todas as threads da falha original.

**Achados correlatos:** `yaml` ausente no Vault; `my-server` apontando para `/path/to/dir`; Nous `stealth/space-bunny-alpha` devolveu 404; SQLite 3.50.4 produziu aviso WAL-reset. Nenhuma alteração inicial do código.

### Fase 2 — Refinamento de requisitos e precedência do modelo (VERIFICADO)

Foram encontradas configurações divergentes:

- `%LOCALAPPDATA%\hermes\config.yaml`: provedor `nous`, modelo `stealth/space-bunny-alpha`.
- `%LOCALAPPDATA%\hermes\profiles\default\config.yaml`: provedor `nvidia`, modelo `nvidia/nemotron-3-ultra-550b-a55b`.

A investigação de `hermes_cli/web_server_config.py`, `hermes_cli/model_switch.py`, `tui_gateway` e métodos de perfil indicou que alterar apenas o YAML global seria insuficiente. O usuário recebeu prompt de implementação detalhado; nesta fase não houve mutação.

### Fase 3 — Aplicação DeepSeek, MCP e primeiro impasse Stage A (VERIFICADO/PARCIAL)

Preflight: `main`, HEAD acima, aproximadamente 149 alterações locais no início e claims de outros agentes. Stage A em `workstation/context/CURRENT_STATE.md` identificado como `PENDING / NOT QUALIFIED`.

A seleção foi validada por `_validated_main_model_selection` e persistida com `persist_model_selection`, nos dois arquivos de configuração. Estado persistido: `provider=deepseek`, `default=deepseek-flash`, `base_url=https://api.deepseek.com/v1`, `api_mode=chat_completions`. Backup individual `config.yaml.bak-hermes-p0-20261026-130211` em cada diretório.

Somente `mcp_servers.my-server.enabled` foi definido para `false` por `atomic_roundtrip_yaml_update`; preservou-se o servidor para eventual reativação e as outras entradas MCP. Backup global `config.yaml.bak-mcp-p1-20261026-130326`.

Dois smokes reais pela CLI, sem override, retornaram `OK` e código 0: um com configuração global e outro com `HERMES_HOME=profiles/default`; `usage.json` registrou `model=deepseek-flash`, `provider=deepseek`, `api_calls=1` em cada caso. Não havia ainda teste Electron. Por Stage A não qualificado, patches de código foram adiados. Um diário específico da missão foi criado.

### Fase 4 — Dispensa Stage A e patches do SDK/Vault (VERIFICADO)

O usuário autorizou expressamente a dispensa do Stage A **para a missão**, sem autorizar mudança irrestrita no checkout. Claims foram feitos para os caminhos de runtime/testes. Implementou-se `prewarm_openai_sdk()` e sua chamada antes dos workers da CLI, FastAPI e gateway. No Vault, foi substituído PyYAML por `ruamel.yaml`, com helpers para leitura e gravação.

Criou-se `tests/agent/test_openai_import_deadlock.py` com três subprocessos limpos e dez threads cada; importação e criação de clientes locais com endereço `example.invalid`, sem chamadas de rede. `workstation/tests/test_vault.py` passou a importar `YAML` da biblioteca existente. `agent/agent_runtime_helpers.py` e `agent/auxiliary_client.py` foram examinados mas **não editados**.

Uma execução inicial de testes falhou por diretório de trabalho incorreto; refeita a partir do root, passou. O teste Vault anterior ao patch falhara na **coleta**, por `ModuleNotFoundError: No module named 'yaml'`. Resultado progressivo após correção: 21 PASS/2 SKIP no Vault e 31 PASS/2 SKIP na suíte focada de cinco arquivos.

### Fase 5 — Qualificação gateway isolado, sem invadir a UI (VERIFICADO/PARCIAL)

Tentou-se WebSocket da instância principal e houve HTTP 403. Não se contornou autenticação. Criou-se um processo `tui_gateway.entry` isolado, com `HERMES_HOME` temporário. Primeiro harness recebeu erro `4000` em `prompt.submit` por fornecer parâmetro `source` extra; corrigido o payload, `session.create` selecionou `deepseek-flash`, `prompt.submit` aceitou `streaming` e `message.complete` iniciou com `OK`. O banco isolado registrou `source=desktop`, `model=deepseek-flash`, `billing_provider=deepseek`, `api_call_count=1`, `message_count=2`.

A saída completa incluiu texto de boas-vindas além de `OK` (a instrução de responder **apenas** OK não foi seguida literalmente); não afetou a prova de inferência. Uma simulação REST da API do Vault por `TestClient` retornou quatro HTTP 200 (status/criar/ler/listar). Rotas reais continuaram exigindo credencial.

### Fase 6 — SQLite: validação de distribuição oficial, ainda sem instalação (VERIFICADO)

Os Python 3.13/3.14 alternativos examinados também utilizavam SQLite 3.50.4; trocar somente de interpretador não resolvia. Identificou-se DLL compartilhada `...\uv\python\cpython-3.14-windows-x86_64-none\DLLs\sqlite3.dll`, que não deveria ser substituída.

Baixou-se a distribuição oficial `https://www.sqlite.org/2026/sqlite-dll-win-x64-3530400.zip` para `%TEMP%\hermes-sqlite-3530400-stage-20261026`, conferindo **SHA3-256** `deddee963c810d1eeac3ce5e15c7c41da21a1c54d7a39cf54fbf577d2f50de3a`. `_sqlite3.pyd` compatível foi copiado ao estágio; com `PYTHONPATH` apontando para lá, novo processo reportou SQLite **3.53.4**. Teste WAL/Unicode/`quick_check` passou; gateway isolado com a DLL publicou `gateway.ready`, criou sessão DeepSeek e não apresentou alerta WAL-reset na saída capturada. A instalação principal foi mantida intacta nessa fase.

Tentativa inicial de calcular hash por `python -c` sofreu erros de quoting no PowerShell e foi corrigida usando here-string e stdin; **não** houve instalação sem verificação de hash.

### Fase 7 — Reavaliação dos escritores, backup e recuperação (VERIFICADO)

Na retomada posterior, o processo Electron antigo e o backend **já não estavam executando**, porta anterior 60272 sem listener. Permaneciam processos externos do `local-mcp-bridge`, Codex, Desktop Commander e Remotion, que não foram interrompidos. `kanban.db` mantinha oito `tasks` e oito `task_runs` com status `running`, `worker_pid=NULL` e leases expirados; não houve limpeza ou cancelamento dessas linhas.

Antes de instalar, foram copiados 8 bancos e seus sidecars WAL/SHM, totalizando 14 arquivos e **571.950.280 bytes**, para `%LOCALAPPDATA%\hermes\backups\sqlite-maintenance-20261026-150012\raw`. Os arquivos de origem e cópia tiveram fingerprint temporal/tamanho e SHA-256 conferidos; `manifest.json` documentou resultados. A seguir, cópias do snapshot foram restauradas em `restore-validation`; todos os 8 DBs passaram em `PRAGMA integrity_check(3)` sob SQLite 3.53.4, incluindo WAL de `state.db` com 12.158.152 bytes. Não foi feito checkpoint forçado nem conversão dos bancos de produção.

**Limite:** esse mecanismo foi cópia de arquivos com verificação de estabilidade, não um snapshot sob lock exclusivo/backup API SQLite; não se deve inferir garantia absoluta contra uma escrita concorrente fora da janela observada. A restauração testada fornece evidência forte de utilizabilidade do snapshot.

### Fase 8 — Ativação privada e reinício do Desktop (VERIFICADO/PARCIAL)

Foram copiados `sqlite3.dll` e `_sqlite3.pyd` para `%LOCALAPPDATA%\hermes\runtime\sqlite-3.53.4-win-x64`, e criado um arquivo `.pth` na `.venv` para elevar esse diretório no `sys.path`. Um processo novo da `.venv` carregou 3.53.4; desabilitar temporariamente o `.pth` retornou 3.50.4, reativá-lo restaurou 3.53.4: rollback funcional em subprocessos.

Com inexistência de backend Hermes anterior, iniciou-se `npm run dev --workspace apps/desktop`. Electron PID 28720, backend Python PID 19716; log `HERMES_BACKEND_READY port=49345`, renderer carregado e janela visível. `Get-Process -Module` no **backend real** confirmou `_sqlite3.pyd` e `sqlite3.dll` da pasta privada com versão de arquivo DLL 3.53.4. `GET /api/status` retornou HTTP 200; `GET /api/plugins/vault/status` retornou HTTP 401 sem token (proteção mantida). Log informou `Mounted plugin API routes: /api/plugins/vault/`.

Uma tentativa de capturar/manipular UI foi deliberadamente suspensa: a janela ativa do Windows era `Adicionar um dispositivo`, não o Hermes. Não houve digitação, clique ou nova mensagem pela UI Electron autenticada.

### Fase 9 — Isolamento de testes, realocação do SQLite e qualificação final (VERIFICADO)

Uma ampliação da suíte de 8 arquivos encontrou **61 PASS/1 FAIL/4 SKIP**. A falha foi `test_create_openai_client_reuse.py::test_second_create_does_not_wrap_closed_transport_from_first`: o harness detectou I/O contra o `HERMES_HOME` real por causa da DLL privada colocada dentro desse diretório. Não era erro de lógica de SQLite nem evidência de corrupção; era violação de isolamento de teste.

Sem alterar os patches versionados, o runtime privado foi **copiado** para `%LOCALAPPDATA%\HermesPrivateRuntime\sqlite-3.53.4-win-x64` (irmão do `HERMES_HOME`), e o `.pth` alterado para esse destino. O runtime anterior foi conservado porque o backend Electron aberto já havia carregado DLLs a partir dele. O teste isolado voltou a passar **6/6**; a suíte total foi repetida com **62 PASS/0 FAIL/4 SKIP**. O rollback com `.pth` foi repetido após a realocação.

Nova CLI com `HERMES_HOME` temporário + SQLite corrigido respondeu `OK`, `exit 0`, `usage.json` `provider=deepseek`, `model=deepseek-flash`, `api_calls=1`. Logs após o boot de 15h04 não mostraram ocorrências novas das strings deadlock/erro YAML/WAL-reset, mas mantiveram avisos não tratados de Laya ausente, colisão `/plan`, descoberta MCP com 0 servidores e worktrees antigas.

Criou-se o relatório `hermes-sqlite-runtime-qualification-20261026.md` com claim específico; estado `READY_FOR_INTEGRATION`. Último Git dessa fase: **158 entradas dirty/untracked**; HEAD e branch preservados.

### Fase 10 — Auditoria atual, exclusivamente de leitura (VERIFICADO)

Reexaminou-se `git diff` dos seis arquivos rastreados alterados, teste novo, `.pth`, configs, manifestos, claims, processos e logs. O ambiente persistido mantém DeepSeek nos dois YAMLs e os três MCPs desabilitados. O processo backend PID 19716 continuava com SQLite 3.53.4 carregado da **pasta privada interna antiga**, enquanto processos novos da `.venv` usam o diretório irmão. Ambos possuem mesma versão SQLite, mas a convergência de caminhos só ocorrerá em reinício futuro controlado.

**Nova observação crítica:** `agent.log` registra às 15h18:06 `OpenAI client created (switch_model, ... provider=nvidia)` e `Model switched in-place: deepseek-flash (deepseek) -> nvidia/nemotron-3-ultra-550b-a55b (nvidia)`. O banco de estado agora reflete modelo NVIDIA na sessão Desktop antiga, apesar de `config.yaml` e `profiles/default/config.yaml` seguirem com `deepseek-flash`. Na mesma hora: `OPENAI_BASE_URL is set (https://api.openai.com/v1) but model.provider is 'nvidia'`, risco para clientes auxiliares; e `AGENTS.md ... TRUNCATED: 21887 chars exceeds limit of 20000`. Não há prova do autor/motivo do switch, nem de que uma sessão nova tenha perdido o padrão. Esses avisos não haviam sido destacados no fechamento anterior.

## 4. Descobertas técnicas e conhecimento adquirido

| ID | Descoberta e mecanismo | Evidência | Consequência / aplicabilidade | Confiança |
|---|---|---|---|---|
| C-01 | Importação fria do SDK OpenAI em múltiplas threads pode produzir deadlock de `_ModuleLock` em Python 3.14 e SDK 2.24.0. | 3/10 em amostra inicial; depois 11 deadlocks em três rodadas sem prewarm versus zero com prewarm. | Esquentar SDK antes do fan-out e testar sempre em processo limpo, não apenas em processo já importado. | **Confirmado para o cenário artificial; provável como causa exata da ocorrência original.** |
| C-02 | O proxy `process_bootstrap.OpenAI` conserva cache de classe, mas a primeira importação pode acontecer em worker; `agent_init` encapsula falhas. | Código de `_load_openai_cls`, `create_openai_client`, `_init_openai_client` e mensagem original. | Hook deve viver em pontos de inicialização, evitando mexer na API dos consumidores e no contrato de construção de clientes. | Confirmado |
| C-03 | Há escopos distintos de configuração global, de perfil e de sessão. | Dois YAML divergentes antes; inspeção `model_switch`/`tui_gateway`; sessão NVIDIA depois com defaults DeepSeek. | Não inferir modelo efetivo de sessão apenas pelo default; preservar escolhas explícitas ao mudar o default. | Confirmado |
| C-04 | Modelos Nous sem suporte podem responder 404 mesmo com GUI operacional. | `Model 'stealth/space-bunny-alpha' not found` às 08h11. | Verificar modelo/endpoint e fazer smoke real; 404 Nous não demonstra problema no importador. | Confirmado |
| C-05 | Vault exigia `yaml` (PyYAML) não presente, enquanto `ruamel.yaml` já estava disponível. | Falha em import da API do Vault e coleta pytest; diff de `vault.py` e testes; suite verde. | Reaproveitar a biblioteca existente e validar round-trip Unicode/frontmatter. | Confirmado |
| C-06 | Servidor MCP de exemplo era configurado com `/path/to/dir`; mesmo desativado, outros servidores podem estar desabilitados. | YAML e `hermes mcp list`: `my-server`, `browserclaw`, `trello` disabled. | Separar erro de servidor inválido de discovery sem servidores habilitados; não religar conectores sem autorização. | Confirmado |
| C-07 | Python 3.13/3.14 instalado não oferecia automaticamente SQLite corrigido; `_sqlite3.pyd` do Python uv usa DLL da distribuição global. | `sqlite3.sqlite_version` 3.50.4; `...uv\python\...\DLLs\sqlite3.dll`. | Atualização exige isolamento de DLL; não sobrescrever o uv compartilhado. | Confirmado |
| C-08 | Uma DLL SQLite 3.53.4 com `_sqlite3.pyd` compatível funciona via diretório prioritário em `sys.path`. | Staging, SHA3, processo Python 3.14, WAL Unicode e gateway isolado. | Permite runtime privado por `.pth`, sujeito a regressão no bootstrap e rebuild da venv. | Confirmado |
| C-09 | Caminho sob `HERMES_HOME` real pode violar isolamento de testes mesmo para dependências DLL. | Falha explícita `TEST BUG: file I/O against the REAL hermes home`, sanada mudando a DLL para pasta irmã. | Não guardar artefatos de boot compartilhados dentro da árvore de dados que testes protegem. | Confirmado |
| C-10 | Instância Desktop pode ter DLL antiga **em localização** embora correta **em versão** após atualizar `.pth`. | PID 19716 carregou SQLite 3.53.4 da pasta interna anterior; processo novo da venv carrega 3.53.4 do diretório irmão. | Não apagar diretório antigo nem presumir mudança em processo vivo; aguardar reinício seguro. | Confirmado |
| C-11 | A interface autêntica é um seam distinto do gateway isolado e CLI. | Gateway produz `message.complete`; UI WS diretamente recusou 403; HTTP Vault vivo recusou 401; janela humana tinha foco. | Smoke headless não homologa o ciclo completo Electron-renderer-IPC-gateway. | Confirmado |
| C-12 | `OPENAI_BASE_URL` pode interferir em clientes auxiliares após troca para NVIDIA; `AGENTS.md` sofre truncamento por limite 20.000 caracteres. | Novos avisos `agent.log` às 15h18, não investigados na execução original. | Próxima investigação dirigida: roteamento auxiliar e limite contextual, sem atribuir causa a outros bugs. | **Risco confirmado pelo aviso; impacto funcional indeterminado.** |
| C-13 | Leases Kanban vencidos e `worker_pid=NULL` não comprovam que é seguro apagar registros `running`. | Consultas readonly a `kanban.db` com oito tasks e oito runs `running`. | Fazer reconciliação de estado via autoridade Kanban, sem DML ad hoc. | Confirmado |
| C-14 | Mudança de configuração persistida pode ser percebida em novas inicializações, sem alterar modelo pinned de sessões antigas. | Dois YAMLs DeepSeek, CLI smokes e sessão NVIDIA preservada depois. | Criar sessão realmente nova para homologar default; não forçar sessão antiga. | Confirmado para o comportamento observado; política geral requer testes adicionais |

## 5. Decisões técnicas e arquiteturais

IDs `D-xx` pertencem **somente a este relatório**; não correspondem a ADRs ou issues existentes.

| ID | Decisão e justificativa | Alternativas efetivamente consideradas / trade-offs | Estado |
|---|---|---|---|
| D-01 | Escrever DeepSeek em ambos os escopos persistidos por `persist_model_selection` após validação canônica. | Editar só um YAML foi rejeitado por precedências divergentes. | **Definitiva para default**, sem vincular sessões antigas. |
| D-02 | Manter `DEEPSEEK_API_KEY` pelo ambiente, sem registrar chave em relatório. | Não houve plano de embutir segredo em arquivo. | Definitiva |
| D-03 | Desabilitar apenas `mcp_servers.my-server`, preservando comando e argumentos. | Apagar entrada ou alterar outros conectores foi rejeitado. | Definitiva para configuração atual; reversível |
| D-04 | Respeitar Stage A até autorização de exceção; após consentimento, executar apenas escopo da missão. | Implementação antes do gate havia sido bloqueada; dispensa geral não foi presumida. | **Revisada por decisão do usuário**, waiver específico em vigor |
| D-05 | Pré-importar SDK antes de workers em CLI/FastAPI/gateway, mantendo proxy lazy para outros consumidores. | Retry cego não corrige lock; lock global prolongado/reescrita ampla não selecionados. | Código implementado, local, não integrado por commit |
| D-06 | Migrar Vault de PyYAML para `ruamel.yaml` existente, com `YAML(typ='safe', pure=True)`. | Adicionar/pinar PyYAML considerado, rejeitado por dependência adicional evitável. | Implementado, local |
| D-07 | Testar gateway isolado com `HERMES_HOME` temporário antes de reiniciar instância compartilhada. | Autenticação 403 não deveria ser contornada; não forçar uso da UI. | Adotada; valida gateway, não renderer |
| D-08 | Não substituir SQLite do uv global; usar DLL oficial e `_sqlite3.pyd` privado. | Troca de Python não resolvia; sobrescrever DLL compartilhada foi rejeitado. | Definitiva quanto ao isolamento |
| D-09 | Fazer cópia SHA-256 dos DBs/WALs com verificação de estabilidade e restauração offline antes da implantação. | Atualização sem snapshot foi rejeitada; API SQLite backup não foi usada nesse fluxo. | Implementado; ver limites de atomicidade |
| D-10 | Ativar SQLite por `.pth` na venv, com rollback por desabilitação do hook. | Substituição global uv explicitamente rejeitada. | Implementado; depende da venv |
| D-11 | **Revisar D-10:** mover runtime privado de `%LOCALAPPDATA%\hermes\runtime` para `%LOCALAPPDATA%\HermesPrivateRuntime`. | Local inicial causou falha em teste de isolamento. | Destino novo prevalece para processos futuros; o processo atual conserva DLL antiga em memória |
| D-12 | Não tomar foco de `Adicionar um dispositivo`; não forçar sessão Electron ou contornar HTTP 401/403. | Automação agressiva da UI rejeitada para preservar atividade humana. | Decisão operacional, validação UI pendente |
| D-13 | Não executar Git commit/merge/push e preservar claims `READY_FOR_INTEGRATION`. | Integração imediata não autorizada. | Definitiva no escopo da sessão |

## 6. Inventário de alterações no código, configuração e infraestrutura

### 6.1. Patch do SDK OpenAI — **VERIFICADO no diff atual**

| Arquivo | Operação / impacto |
|---|---|
| `agent/process_bootstrap.py` | **Editado:** adicionada `prewarm_openai_sdk()` antes de `_load_openai_cls`, aquecendo `OpenAI`, `ChatCompletion` e `Completions`; proxy `_load_openai_cls` mantido. Diff: +12 linhas. |
| `hermes_cli/main.py` | **Editado:** `cmd_chat(args)` chama prewarm antes do setup/prefetch; +4 linhas. |
| `hermes_cli/web_server.py` | **Editado:** `_lifespan(app: FastAPI)` preaquece SDK antes de workers de boot; +4 linhas. |
| `tui_gateway/entry.py` | **Editado:** `main()` preaquece antes de callbacks e threads; +4 linhas. |
| `tests/agent/test_openai_import_deadlock.py` | **Novo, untracked:** três parametrizações; subprocessos limpos, barrier de 10 threads, imports concorrentes e criação de clientes OpenAI/auxiliares sem rede. |

`agent/agent_runtime_helpers.py`, `agent/agent_init.py` e `agent/auxiliary_client.py` foram analisados, mas **não há patch rastreado desta missão** nos dois primeiros e no auxiliar. Não se atribuiram alterações não demonstradas.

**Seam afetado:** processo inicializador → registro do gateway/FastAPI/CLI → worker pool → `AIAgent._init_openai_client` → proxy SDK. O patch minimiza imports frios dentro dos workers nas entradas cobertas. Ainda não prova que toda entrada alternativa/terceirizada tenha prewarm; scope global requer cobertura adicional.

### 6.2. Patch Vault — **VERIFICADO no diff atual**

| Arquivo | Operação / impacto |
|---|---|
| `workstation/vault.py` | **Editado:** `import yaml` substituído por `StringIO`, `YAML` de `ruamel.yaml` e `YAMLError`; novos `_safe_yaml_load(value)` e `_safe_yaml_dump(value)`; chamadas na análise de frontmatter, emissão Markdown e leitura de configuração substituídas. Diff +21/-5. |
| `workstation/tests/test_vault.py` | **Editado:** import de PyYAML e teste de `safe_load` substituídos por `ruamel.yaml.YAML(typ='safe').load`. Diff +2/-2. |
| `workstation/tests/test_vault_tools.py` | **Não modificado**, porém incluído nas regressões. |

**Seam afetado:** API do plugin `plugins/vault/dashboard/plugin_api.py` → `workstation.vault.VaultManager` → Markdown/frontmatter/índice local e YAML de configuração. Manteve-se contrato de endpoints; a migração muda a biblioteca de serialização, razão para testar dados reais adicionais se houver formas YAML não cobertas (tags/aliases/escalares especiais).

### 6.3. Configuração — **VERIFICADO em leitura atual**

| Caminho | Mutação e resultado |
|---|---|
| `%LOCALAPPDATA%\hermes\config.yaml` | `model.default=deepseek-flash`; `provider=deepseek`; `base_url=https://api.deepseek.com/v1`; `api_mode=chat_completions`; `mcp_servers.my-server.enabled=false`. `browserclaw`/`trello` atualmente `false`, não foram alterados pela missão. |
| `%LOCALAPPDATA%\hermes\profiles\default\config.yaml` | Mesmo conjunto de chaves de modelo DeepSeek; outras seções originalmente preservadas. |
| Backups de YAML | `config.yaml.bak-hermes-p0-20261026-130211` em ambos os diretórios; `config.yaml.bak-mcp-p1-20261026-130326` no global. |

**Nuance:** um modelo NVIDIA foi aplicado **a uma sessão existente** às 15h18; os padrões persistidos permaneceram DeepSeek às 17h31.

### 6.4. SQLite, runtime e infraestrutura — **VERIFICADO**

| Artefato | Estado / papel |
|---|---|
| `%TEMP%\hermes-sqlite-3530400-stage-20261026` | ZIP oficial, DLL 3.53.4, `.def`, `_sqlite3.pyd` e DB smoke. Material de staging, não fonte de verdade de release. |
| `%LOCALAPPDATA%\hermes\runtime\sqlite-3.53.4-win-x64` | Primeira cópia privada; **ainda utilizada pelo backend Electron aberto**, DLL carregada em memória. Não apagar a quente. |
| `%LOCALAPPDATA%\HermesPrivateRuntime\sqlite-3.53.4-win-x64` | **Destino atual da venv para novos processos**, fora de `HERMES_HOME` para preservar isolamento. |
| `C:\Github\hermes-agent\.venv\Lib\site-packages\00_hermes_private_sqlite.pth` | **Criado:** linha `import os,sys;sys.path.insert(0,os.path.join(os.environ['LOCALAPPDATA'],'HermesPrivateRuntime','sqlite-3.53.4-win-x64'))`. É mudança local não versionada da venv. |
| `%LOCALAPPDATA%\hermes\backups\sqlite-maintenance-20261026-150012` | Backup `raw`, manifesto SHA-256, `restore-validation`, metadados de implantação e versão anterior de metadados. 8 DBs/14 arquivos. |
| Distribuição `...\uv\python\cpython-3.14-windows-x86_64-none` | **Não foi alvo de troca de DLL ou reinstalação**. Não há auditoria hash bit a bit da distribuição inteira. |
| `state.db`, `kanban.db`, `projects.db` e outros bancos de produção | Não há evidência de DML, checkpoint forçado, alteração WAL ou restauração por esta missão; consultas e boot normal podem atualizar metadados automaticamente. |

### 6.5. Documentação e Git

- `workstation/context/engineering-journal/hermes-model-init-remediation-20261026.md`: **novo, untracked**, histórico P0/P1, testes, impedimentos e waivers.
- `workstation/context/engineering-journal/hermes-sqlite-runtime-qualification-20261026.md`: **novo, untracked**, backup/rollback/boot e pendências finais.
- Claim `chatgpt-hermes-init-fix-20261026` em lanes `hermes-init-entry-20261026` e `hermes-init-vault-20261026`: `READY_FOR_INTEGRATION`.
- Claim `chatgpt-hermes-sqlite-qualification-20261026`: `READY_FOR_INTEGRATION` sobre o segundo relatório.
- Nenhum commit, push, PR ou merge da missão demonstrado. `git diff` atual exibe 6 arquivos rastreados modificados; teste e 2 relatórios novos continuam sem rastreamento (`??`).

### 6.6. Apenas considerados, **não executados**

Integração de correções por commit/PR; reconstrução do runtime em instalador universal; validação de UI com automação autenticada e sessão nova; liberação/limpeza das oito tasks Kanban `running`; alterar ativação de MCP alheios; reparo de Laya, `/plan`, contexto AGENTS; substituição da distribuição Python uv global (explicitamente rejeitada).

## 7. Problemas, bugs e análise de causa raiz

| ID | Sintoma, causa/hipótese e evidência | Ação / observação após mudança | Estado e risco residual |
|---|---|---|---|
| B-01 | `_DeadlockError` no import de `openai.types.chat`; reproduzido paralelamente em testes frios; importação paralela é **causa provável**, não traço completo do lock original. | Prewarm nos pontos de entrada; stress e regressões aprovados; cliente OpenAI criado no backend real após boot, logs sem novo deadlock na janela observada. | **VERIFICADO como mitigação funcional nos caminhos testados; PARCIAL para ausência absoluta em todos os caminhos.** |
| B-02 | `Model 'stealth/space-bunny-alpha' not found` (HTTP 404 Nous, 08h11). | DeepSeek default persistido e chamadas reais respondidas. | **VERIFICADO** para novas rotas testadas; sessões antigas Nous não reescritas. |
| B-03 | Global Nous versus perfil NVIDIA: precedência divergente. | Ambos persistidos como DeepSeek. | **VERIFICADO**; distinção default/sessão importante. |
| B-04 | `ModuleNotFoundError: No module named 'yaml'` no `workstation.vault` e na coleta pytest. | Migrado para `ruamel.yaml`; Vault HTTP isolado 4x200, testes verdes; rota montada no Desktop. | **VERIFICADO localmente; PARCIAL** para chamada autenticada ao backend vivo. |
| B-05 | MCP `my-server` com `/path/to/dir` inexistente, falhas de conexão/zero ferramentas. | Apenas `enabled=false`; status `disabled`, sem pendência de conexão. | **VERIFICADO na configuração**. Aviso de discovery zero servidores persiste e é compatível com três MCPs disabled. |
| B-06 | SQLite 3.50.4 potencialmente vulnerável a WAL-reset; alerta de runtime. | DLL oficial 3.53.4 privada, SHA3, rollback, backup/restauração e carga no Desktop. | **VERIFICADO** uso da versão corrigida no backend, mas necessário qualificar reinstalação e rebootstrap. |
| B-07 | Teste Vault quebrava na fase de coleta por dependência de teste PyYAML. | Teste migrado para ruamel. | **VERIFICADO** solucionado na suíte. |
| B-08 | Falha de um teste após instalar DLL sob `HERMES_HOME` real: `TEST BUG: file I/O against the REAL hermes home`. | Realocação para diretório irmão, teste 6/6 e suíte 62/0. | **VERIFICADO** resolvido para isolamento testado. |
| B-09 | `prompt.submit` retornou erro 4000 por parâmetro `source` extra no harness isolado. | Payload corrigido, resposta `message.complete` obtida. | **FALHOU na primeira tentativa; VERIFICADO** na repetição. Não foi bug de produto. |
| B-10 | WS principal recusou HTTP 403, Vault vivo 401. | Sem bypass; teste via gateway isolado e TestClient. | **PARCIAL**: autenticação deliberada; E2E UI principal não verificado. |
| B-11 | Backend antigo relatou event-loop stalls 123 s/2475,9 s e falha de reconexão. | Novo boot ocorreu; logs após boot não provaram recorrência desses stalls. | **PENDENTE/INDETERMINADO** causa do stall e reprodução sob carga. |
| B-12 | `OPENAI_BASE_URL` setado com OpenAI ao selecionar NVIDIA às 15h18; log avisa desvio potencial de auxiliares. | Nenhuma intervenção nesta missão; não se verificou requisição auxiliar. | **PENDENTE P1**, impacto real indeterminado. |
| B-13 | `AGENTS.md` truncado por 21.887 > 20.000 chars durante sessão após mudança de modelo. | Sem intervenção. | **PENDENTE P2** (risco de perder instruções contextuais). |
| B-14 | `LayaDecisionProvider` ausente, colisão `/plan`, worktrees antigas e discovery MCP zero. | Registro e preservação, não corrigidos. | **PENDENTE/INDETERMINADO** quanto ao impacto; fora do escopo principal. |

## 8. Testes, verificações e evidências de funcionamento

### 8.1. Matriz de validação histórica

| Grupo / procedimento | Ambiente e resultado observável | Evidência e limitação | Classificação |
|---|---|---|---|
| Imports concorrentes **sem** prewarm | Python 3.14, 10 threads, primeira amostra 3 `_DeadlockError`; em 3 execuções posteriores 4+6+1 = 11 ocorrências. | Reproduz classe de falha, não a inversão exata da screenshot. | **FALHOU** (reprodução de bug) |
| Imports concorrentes **com** prewarm experimental | 3 execuções independentes × 10 threads, 0 erros e 0 penduradas. | Prova mitigação no harness; SDK/ordem de import da produção pode divergir. | **VERIFICADO** |
| Smokes de configuração global e perfil | CLI `-z 'Responda somente OK.'` sem override; ambos `exit 0`, 1 chamada, `deepseek-flash`. | Resposta de inferência real; não é Electron. | **VERIFICADO** |
| Vault antes da correção | `pytest workstation/tests/test_vault.py`: erro na coleta por `yaml` ausente. | Comando/traceback preservado. | **FALHOU** |
| Vault depois da correção | `workstation/tests/test_vault.py` + `_tools.py`: 21 PASS/2 SKIP. | Local unitário. | **VERIFICADO** |
| API Vault por FastAPI `TestClient` | `GET /status`, `POST /notes`, `GET /notes/{title}`, `GET /notes`: 4 HTTP 200. | Root temporário, não backend principal. | **VERIFICADO** |
| SDK + Vault (5 arquivos) | Runner oficial `scripts/run_tests.sh -j 2`: 31 PASS, 2 SKIP, 0 FAIL. | Windows, subprocessos por arquivo. | **VERIFICADO** |
| Gateway isolado após correções | `tui_gateway.entry`, sessão `deepseek-flash`, prompt `streaming`, `message.complete` iniciada com OK; DB isolado `api_call_count=1`. | Prova fluxo real; não é mensagem originada da UI. | **VERIFICADO** |
| Gateway com SQLite 3.53.4 em staging | `gateway.ready`, `session.create`, 3.58 s; sem WAL-reset na saída capturada. | Ambiente isolado. | **VERIFICADO** |
| SQLite WAL/Unicode em staging | `PRAGMA journal_mode=WAL`, INSERT/SELECT Unicode, `quick_check=ok`. | Banco sintético. | **VERIFICADO** |
| Backup e recuperação | 8 DBs/14 arquivos, hashes SHA-256 conferidos, cópia restaurada passou `integrity_check(3)`. | Garantia condicionada à janela de estabilidade dos originais. | **VERIFICADO** |
| Ativação e rollback da DLL | `.pth` on = 3.53.4; `.pth` desativado = 3.50.4; reativado = 3.53.4. | Processos Python novos; não mexeu no uv global. | **VERIFICADO** |
| Desktop real pós-restart | `HERMES_BACKEND_READY port=49345`; Electron/processos em execução; DLL SQLite 3.53.4 carregada; `/api/status` 200. | Não confirma `prompt.submit` pela UI. | **VERIFICADO/PARCIAL** |
| Vault no Desktop autenticado | `/api/plugins/vault/status`: 401 sem credencial; rota aparece montada nos logs. | Autenticação não contornada. | **PENDENTE** teste autenticado |
| Primeira regressão ampliada | 8 arquivos: 61 PASS, 1 FAIL, 4 SKIP por guard de I/O do runtime sob HOME. | Falha operacional relevante e diagnosticada. | **FALHOU**, depois corrigida |
| Regressão ampliada após realocação | 8 arquivos: **62 PASS, 0 FAIL, 4 SKIP**. | Conjunto direcionado, não suíte integral do projeto ou CI cross-platform. | **VERIFICADO** |
| Smoke final CLI com novo SQLite | `deepseek-flash`, `deepseek`, 1 API call, resposta OK e código 0. | `HERMES_HOME` temporário. | **VERIFICADO** |
| Logs após boot | Não encontrados novos deadlock/YAML/WAL-reset no intervalo analisado. | Ausência no log não prova impossibilidade de regressão. | **PARCIAL** |
| `git diff --check` dos arquivos alterados | exit code 0; avisos de conversão CRLF/LF. | Não prova design/funcionalidade; sem integração Git. | **VERIFICADO** |
| UI Electron envia mensagem e recebe resposta real | Não executado por conflito de foco com janela humana. | Critério explícito ainda aberto. | **PENDENTE** |

### 8.2. Comandos e protocolos reprodutíveis

**Runner dirigido:**

```powershell
cd C:\Github\hermes-agent
$env:HERMES_PYTHON='C:\Github\hermes-agent\.venv\Scripts\python.exe'
$env:HERMES_TEST_FILE_RETRIES='0'
& 'C:\Program Files\Git\bin\bash.exe' scripts/run_tests.sh -j 3 `
  tests/agent/test_openai_import_deadlock.py `
  tests/agent/test_create_openai_client_reuse.py `
  tests/agent/test_create_openai_client_kwargs_isolation.py `
  workstation/tests/test_vault.py `
  workstation/tests/test_vault_tools.py `
  tests/hermes_state/test_hermes_state_wal_fallback.py `
  tests/hermes_state/test_deleted_wal_checkpoint_guard.py `
  tests/hermes_state/test_journal_mode_upgrade_warning.py -q
```

**Estado read-only:** `git status --porcelain=v1`; `git diff --unified=5 -- <arquivos>`; `python -c "import sqlite3;print(sqlite3.sqlite_version)"`; `hermes mcp list`; `GET http://127.0.0.1:49345/api/status` enquanto porta existir; `PRAGMA integrity_check(3)` somente em cópias de backup (preferível).

**Reprodução do deadlock:** o arquivo `tests/agent/test_openai_import_deadlock.py` guarda a variante GREEN com `prewarm_openai_sdk()`. O harness RED pré-patch distribuiu imports frios entre dez threads com `threading.Barrier`; não apagar esse contexto ao interpretar teste GREEN. Um teste de regressão não precisa introduzir a corrida real no processo de produção.

**Atenção:** não executar rotinas de restauração, mudanças no `.pth`, trocas de DLL, `PRAGMA journal_mode`, `VACUUM`, checkpoints ou mudanças em Git durante uma auditoria ou enquanto houver escritores.

## 9. Estado final dos artefatos e do repositório

### 9.1. Estado da última inspeção (17h31, 26/10/2026)

- **Git:** `main`; HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`; `git status --porcelain=v1` = **158 entradas** dirty/untracked, inclusive trabalho alheio. Não se deve atribuir todas essas 158 mudanças a esta missão. Dos arquivos diretamente identificados, seis rastreados modificados e três novos/untracked (teste e dois relatórios).
- **Commits criados nesta sessão:** **nenhum verificado; o HEAD não avançou**. **Push:** nenhum verificado. **PR:** nenhum aberto nesta missão. **Merge:** nenhum.
- **Claims:** três lanes da missão em `READY_FOR_INTEGRATION`, não equivalentes a merge ou aprovação de release. Os claims dos outros agentes continuam e não foram removidos.
- **Configuração persistida:** ambos YAMLs DeepSeek default; `my-server`, `browserclaw` e `trello` desabilitados. Não há valores de chaves secretas neste relatório.
- **Ambiente:** `.venv` Python 3.14.0; `openai==2.24.0` observado na fase inicial; `.pth` particular aponta para `%LOCALAPPDATA%\HermesPrivateRuntime\sqlite-3.53.4-win-x64`; Python recém-iniciado reporta SQLite 3.53.4.
- **Processos observados:** Electron PID 28720 e backend Python PID 19716 iniciados às 15h04, ativos/responsivos na inspeção. **Não se garante que esses PIDs ainda existam após a auditoria.** O backend em memória carrega DLL SQLite 3.53.4 da pasta privada interna anterior; novos processos carregam 3.53.4 da pasta irmã.
- **Sessão existente:** um registro Desktop que antes tinha `deepseek-flash` agora aparece com `nvidia/nemotron-3-ultra-550b-a55b`; log às 15h18 registra switch em execução. Isso não invalida a configuração global/default.
- **Logs relevantes:** boot `HERMES_BACKEND_READY port=49345`; rota Vault montada; warnings de Laya, MCP zero, `/plan`, worktrees; warning novo de endpoint auxiliar quando provedor NVIDIA; AGENTS truncado.
- **Backups/documentação:** pastas, manifestos e relatórios existem no Windows. Os dois `.md` em engenharia estão **untracked**.

### 9.2. Variáveis de ambiente (nomes/finalidades)

| Variável | Utilização conhecida |
|---|---|
| `DEEPSEEK_API_KEY` | Autenticação de inferência DeepSeek; **valor não incluído**. |
| `HERMES_HOME` | Escopo de configuração, perfis e bancos; utilizado em testes isolados. |
| `PYTHONPATH` | Em staging temporário, carregamento privado de `_sqlite3.pyd`; instalação definitiva usa `.pth` da venv. |
| `HERMES_SAFE_MODE` | Isolou execução de CLI/gateway e evitou descoberta de plugins em testes. |
| `HERMES_PYTHON` | Seleciona interpretador para runner de testes. |
| `HERMES_TEST_FILE_RETRIES` | Zero nas regressões, para mostrar falhas sem reruns automáticos. |
| `OPENAI_BASE_URL` | Aviso de possível conflito com sessão NVIDIA; deve-se verificar origem/uso sem supor que seja defeito. |
| `HERMES_IGNORE_RULES` | Usado em harness isolado; não deve ser copiado como configuração do Desktop. |

### 9.3. Mudanças temporárias, pendências de limpeza

Os diretórios de `TEMP` contêm staging SQLite, testes isolados de gateway, DBs smoke e `usage.json`; nenhum é garantia de persistência duradoura. O diretório interno antigo `%LOCALAPPDATA%\hermes\runtime\sqlite-3.53.4-win-x64` não deve ser apagado enquanto qualquer processo tiver a DLL carregada. O snapshot de backup e `restore-validation` devem ser retidos até homologação de release/rollback. `test_durations.json` pode ser recalculado pelo runner, mas o Git foi comparado apenas pelo estado final, sem atribuição segura de seu histórico.

## 10. Pendências, riscos e débitos técnicos

### 10.1. Pendências identificadas durante a sessão

| ID / prioridade | Item e impacto | Evidência / pré-requisitos | Conclusão objetiva |
|---|---|---|---|
| P-01 **P0** | Homologar sessão **criada e respondida pela UI Electron autenticada** pós-boot. Sem isso não há aceite ponta a ponta da interface principal. | Janela do Hermes não era foreground; 401/403 sem credencial; gateway isolado passou. | Criar sessão nova pelo renderer sem override, enviar prompt, verificar `message.complete`, persistência e modelo no log/DB. |
| P-02 **P1** | Integrar patches e documentação ao processo Git autorizado, preservando claims e worktree. Sem integração, correções locais podem ser perdidas. | 6 arquivos rastreados modificados, 3 novos untracked, status `READY_FOR_INTEGRATION`, HEAD imóvel. | Review, gates pertinentes, commit/PR/merge autorizados e testes de CI; usuário proibiu integrar nesta sessão. |
| P-03 **P1** | Verificar `OPENAI_BASE_URL` após troca para NVIDIA e clientes auxiliares. Risco de endpoint incorreto. | Aviso `agent.auxiliary_client` às 15h18. | Traçar resolução de endpoint por cliente auxiliar e teste de roteamento em ambiente isolado, sem expor chaves. |
| P-04 **P1** | Confirmar carregamento do runtime **definitivo** após próximo reinício seguro, sem apagar a pasta antiga antecipadamente. | Backend PID 19716 carrega 3.53.4 do caminho antigo; `.pth` novo aponta para pasta irmã. | Reinício controlado; `Get-Process -Module` confirma caminho irmão e versão 3.53.4; rollback preservado. |
| P-05 **P1** | Qualificar Vault autenticado no backend vivo. | Rota real montada, mas GET sem credencial retornou 401; `TestClient` local passou. | Requisição pela própria sessão/UI autenticada, operações temporárias controladas, HTTP esperado, sem bypass. |
| P-06 **P2** | Avaliar avisos de event-loop stalls (123s/2475,9s) e desconexão. | Logs anteriores ao novo boot; causa não demonstrada. | Stress/telemetria de GIL/loop em execução controlada; sem stalls indevidos e reconexão verificável. |
| P-07 **P2** | Reconciliação de 8 tasks/runs `running` com leases expirados. | Kanban DB, `worker_pid=NULL`, sem heartbeats. | Reconciliar via autoridade Kanban/claims, registrar estado terminal ou retomar conscientemente; nunca SQL destrutivo direto. |
| P-08 **P2** | Tornar mecanismo `.pth` resistente à reconstrução da venv e atualizações. | Arquivo é local/não versionado; recompilação da venv pode apagá-lo. | Procedimento de bootstrap/installer aprovado com detecção de SQLite >= versão corrigida e rollback, sem afetar uv global. |
| P-09 **P2** | Tratar truncamento AGENTS.md 21.887/20.000 e colisão `/plan`, caso impactem tarefas. | Avisos após sessão 15h18/boot. | Redução/seleção de contexto e política explícita de nomes; testes direcionados. |
| P-10 **P2** | Verificar opcionalmente MCP discovery com servidores **habilitados legitimamente**. | Todos os três atuais disabled; warning zero conectados não prova defeito. | Habilitar somente se houver necessidade e autorização; conexão/descoberta demonstradas por servidor legítimo. |
| P-11 **P3** | Avaliar LayaDecisionProvider não encontrado e worktrees antigas preservadas. | Warnings no boot; não ligados diretamente ao objetivo. | Confirmar impacto e dono; correção ou aceitação registrada, sem excluir worktrees não integradas. |
| P-12 **P2** | Ampliar regressão de prewarm para outros entrypoints e instalar em CI/plataformas. | Teste de três subprocessos e caminhos principais; não prova universalidade do import. | Matriz de entradas, concorrência e diferentes Python/SDK, CI incluindo Linux, sem `_DeadlockError`. |

### 10.2. Recomendações novas da auditoria (não confundir com decisão executada)

- **R-01/P1:** escrever ADR curto de seleção e precedência de modelo (global, perfil, sessão pinned), incluindo efeitos da troca `switch_model` e separação de cliente principal/auxiliar.
- **R-02/P1:** converter o procedimento privado do SQLite em bootstrap idempotente, versionado, com validação da origem/assinatura e rollback; evitar depender permanentemente de `.pth` manual.
- **R-03/P2:** executar restore periódico de backup real em ambiente segregado, com tempo de recuperação conhecido, além de `integrity_check` limitado.
- **R-04/P2:** incluir telemetria explícita de DLL SQLite efetiva, modelo/provedor por sessão e boot timestamp nos relatórios do Desktop; isso evitaria confundir configurações persistidas, clientes existentes e runtime carregado.

## 11. Guia de continuidade para o próximo agente

### 11.1. O que já está estabelecido

1. `deepseek-flash` é default persistido nos dois escopos YAML. `DEEPSEEK_API_KEY` existe; jamais copiar segredo para log. Sessões antigas podem ter modelo diferente.
2. `prewarm_openai_sdk()` existe em `agent/process_bootstrap.py` e é chamado nas entradas CLI, `_lifespan` FastAPI e `tui_gateway.entry.main`. Patches estão no **working tree**, não num commit.
3. Vault foi migrado para `ruamel.yaml`; import, testes e API isolada funcionaram.
4. SQLite privado 3.53.4 funciona com Python 3.14; `.venv` seleciona diretório irmão por `.pth`. Distribuição uv global não foi intencionalmente modificada.
5. Backup `%LOCALAPPDATA%\hermes\backups\sqlite-maintenance-20261026-150012` conserva `raw`, hashes e `restore-validation` aprovados.
6. Desktop reiniciado; backend principal carrega SQLite 3.53.4 e responde `/api/status` com HTTP 200; UI chat não foi homologada.
7. Claims reservam os arquivos modificados e os relatos; situação `READY_FOR_INTEGRATION` **não** é aprovação de merge.

### 11.2. O que não deve ser repetido

- Pesquisa genérica por causa do deadlock; já há reprodução RED/GREEN e patch com regressão aprovada. Reabrir somente diante de novo stack ou falha reproduzível.
- Troca de versão do Python como solução isolada de SQLite: versões inspecionadas também vinham com 3.50.4.
- Instalação global de PyYAML para corrigir Vault: o código já usa `ruamel.yaml`.
- Reactivar `my-server` com `/path/to/dir`: a entrada de exemplo é inválida, desativada intencionalmente.
- Repetir acesso direto não autenticado à UI WebSocket como se fosse homologação: HTTP 403 é controle de acesso, não licença para bypass.
- Recolocar runtime SQLite no `HERMES_HOME` real: o harness anti-I/O reprova essa solução.
- Refazer backup/restauração por insegurança genérica sem verificar primeiro a validade temporal/estado do snapshot e a necessidade concreta de nova cópia.

### 11.3. O que não deve ser quebrado

Preservar perfil/global/sessão e modelos pinned; preservar autoridade backend na sessão, Electron na máquina e renderer na apresentação; não escrever bancos ativos manualmente; não reconfigurar provedores não envolvidos; não adulterar claims nem worktrees de outros agentes; não reinstalar Python global, nem apagar DLL carregada; não suprimir warnings sem causa comprovada; manter rollback e backup; não abrir PR/merge/push sem autorização específica.

### 11.4. Pontos de atenção

```text
Repositório: C:\Github\hermes-agent
Branch histórica: main
HEAD histórico: f1d5ab2f030e940ed4571371b0de45a21a009c9e
Configs: %LOCALAPPDATA%\hermes\config.yaml
         %LOCALAPPDATA%\hermes\profiles\default\config.yaml
Runtime privado definitivo: %LOCALAPPDATA%\HermesPrivateRuntime\sqlite-3.53.4-win-x64
Hook venv: C:\Github\hermes-agent\.venv\Lib\site-packages\00_hermes_private_sqlite.pth
Pasta de DLL anterior ainda carregada: %LOCALAPPDATA%\hermes\runtime\sqlite-3.53.4-win-x64
Backup: %LOCALAPPDATA%\hermes\backups\sqlite-maintenance-20261026-150012
Relatórios: workstation\context\engineering-journal\hermes-model-init-remediation-20261026.md
            workstation\context\engineering-journal\hermes-sqlite-runtime-qualification-20261026.md
```

Arquivos de código: `agent/process_bootstrap.py`, `hermes_cli/main.py`, `hermes_cli/web_server.py`, `tui_gateway/entry.py`, `workstation/vault.py`, `workstation/tests/test_vault.py`, `tests/agent/test_openai_import_deadlock.py`. Logs: `%LOCALAPPDATA%\hermes\logs\agent.log`, `errors.log`, `gui.log`, `desktop.log`. Use a ferramenta Controle Windows em modo read-only para preflight, e revalide PID/porta: **28720/19716/49345 eram estados observados, não endereços permanentes**.

### 11.5. Ordem recomendada de retomada

1. **Obrigatório:** novo preflight Git, claims, locks, processos, configuração e mudanças posteriores à inspeção. Critério: owner dos paths e janela de trabalho conhecida.
2. **P0:** teste manual/autenticado da UI Electron criando sessão **nova** sem override e recebendo resposta DeepSeek. Conferir `session.create`, modelo registrado, `prompt.submit`, `message.complete` e logs. Critério: prova ponta a ponta real, distinta do gateway isolado.
3. **P1:** verificar o destino de SQLite carregado em eventual novo backend, confirmar 3.53.4 e integridade normal. Critério: DLL do diretório irmão, nenhum WAL-reset.
4. **P1:** qualificar Vault pelo mecanismo de autenticação normal da UI/endpoint protegido, sem bypass. Critério: operações autorizadas sem erro YAML.
5. **P1:** revisar os novos avisos de `OPENAI_BASE_URL` com NVIDIA; confirmar se houve intenção de trocar modelo da sessão, sem tocar no default. Critério: provas de roteamento correto dos clientes auxiliares.
6. **P1:** review/integrar patches e documentos conforme política multiagente e autorização do usuário. Critério: commit/PR identificado, suíte + CI verdes; não fazer integração por presunção.
7. **P2:** formalizar bootstrap/rollback SQLite, reconciliação Kanban e investigação dos avisos residuais conforme impacto medido.

## 12. Matriz final de rastreabilidade

| Requisito/objetivo | Ação realizada | Evidência | Estado final | Pendência |
|---|---|---|---|---|
| Diagnosticar deadlock OpenAI | Investigação do proxy, reproduções concorrentes | `_DeadlockError`, testes RED, imports no código | **VERIFICADO/PARCIAL** | Stack causal exato do incidente original não capturado |
| Corrigir deadlock | Prewarm em CLI/FastAPI/gateway | Diff e testes com subprocessos | **VERIFICADO** local | Cobertura universal/CI/release |
| DeepSeek como default global | Config canônica persistida | YAML e smoke CLI | **VERIFICADO** | N/A |
| DeepSeek como default do perfil | Config perfil default persistida | YAML e smoke CLI | **VERIFICADO** | N/A |
| Preservar sessões antigas | Sem reescrita em massa, sesssão NVIDIA observada | Inspeção DB e `switch_model` | **VERIFICADO** em amostra | Auditar políticas de pinning se necessário |
| Eliminar 404 Nous para novas sessões default | Seleção DeepSeek e inferência | CLI/gateway com provider DeepSeek | **VERIFICADO** nos caminhos testados | Sessões antigas Nous não alteradas |
| Resolver dependência Vault | PyYAML → ruamel | Diff, pytest, API isolada | **VERIFICADO** local | API autenticada real |
| Desabilitar MCP placeholder | `my-server.enabled=false` | YAML, `mcp list`, status discovery | **VERIFICADO** | Servidores efetivamente habilitados não testados |
| Preservar outros MCP | Browserclaw/Trello não alterados | Comparação config e estado | **VERIFICADO** | N/A |
| Corrigir risco SQLite | DLL 3.53.4 privada e hook `.venv` | SHA3, módulos de backend, versão atual | **VERIFICADO** | Bootstrap durável/reboot de caminho irmão |
| Backup consistente e rollback | 14 arquivos, SHA-256, restauração e integridade, teste `.pth` rollback | Manifestos, 8 checks ok, reversão de versão | **VERIFICADO**, com limite de atomicidade | Política de backup recorrente |
| Reiniciar Hermes com segurança | Electron/backend iniciados após ausência anterior | Log READY, processos e status HTTP | **VERIFICADO** | N/A para boot básico |
| Confirmar resposta gateway | Sessão isolada DeepSeek e `message.complete` | Eventos RPC e banco temporário | **VERIFICADO** | Não confundir com UI |
| Confirmar UI Electron autenticada | Não realizada por foco da janela alheia | Inspeção foreground, ausência de prova de `prompt.submit` via renderer | **PENDENTE** | Aceite E2E |
| Validar Vault no Desktop autenticado | Endpoint montado, HTTP 401 sem token | Logs + chamada HTTP | **PARCIAL** | Credencial normal/fluxo UI |
| Revisar logs de inicialização | Busca de erros pós-boot | Sem novos erros nomeados na janela; outros avisos encontrados | **PARCIAL** | Stress longo e investigação Laya/MCP/stalls |
| Respeitar claims/sem Git destrutivo | Claims, nenhum commit/merge/push | Status e HEAD, claims | **VERIFICADO** | Integração posterior autorizada |
| Documentar continuidade | Dois diários locais; relatório atual | Arquivos confirmados | **VERIFICADO** | Versionar documentação quando autorizado |

## 13. Avaliação crítica da sessão

### 13.1. Fatos observados

- O maior ganho comprovado foi sair de uma falha de inicialização reproduzível e um ambiente SQLite vulnerável para patches locais com regressões verdes, inferência DeepSeek real, runtime corrigido no backend e recuperação de backup demonstrada.
- A separação de causas evitou tratar 404 Nous, ausência PyYAML, erro MCP e deadlock como se fossem um único defeito.
- A restrição de claims/checkout evitou integração destrutiva em repositório altamente sujo. A dispensa do Stage A foi explicitamente limitada, não interpretada como liberação irrestrita.
- Falhas de harness e de compatibilidade de ambiente foram preservadas e corrigidas: quoting PowerShell, parâmetro RPC extra, diretório de execução pytest e posição indevida da DLL sob `HERMES_HOME`.
- Os processos finais carregaram SQLite 3.53.4; **não houve validação final da mensagem pela GUI Electron**. A seleção posterior de NVIDIA na sessão aberta é observação factual, não prova de regressão no default.

### 13.2. Avaliações e recomendações do auditor

**Pontos bem fundamentados:** testes em processos limpos para imports concorrentes; método de configuração canônico; tentativa de preservação do estado multiagente; isolamento de SQLite fora da distribuição uv; testes reais de recuperação do backup e verificação do módulo carregado **no PID do backend**.

**Esforço com retorno limitado:** múltiplas reiterações de mensagens de continuidade e prompts; tentativas de RPC que sabidamente não estavam autenticadas ou tinham contrato incompleto; algumas falhas de quoting/PowerShell que exigiram novas chamadas; uso de `.pth` manual como solução operacional que precisará de durabilidade no bootstrap.

**Insuficiências:** nenhum teste automatizado da interface Electron real; ausência de prova de todas as entradas do SDK; sem processo de integração Git; backup por cópia estável e restore, mas não com lock/backup SQLite transacional formal; não há garantia de que outros subsistemas não usem diferentes caminhos de Python/SQLite; mudança de modelo para NVIDIA e aviso auxiliar só identificados pela auditoria final.

**Próxima abordagem recomendada:** não iniciar nova rodada genérica de correções. Fazer uma sessão curta de aceite E2E autenticado, verificar modelo em sessão **nova**, confirmar a DLL em processo reiniciado usando caminho privado definitivo, inspecionar roteamento auxiliar quando sessão NVIDIA for escolhida, depois submeter patches para review/CI com owners/claims preservados. Somente após esses gates declarar o Hermes Work completamente homologado.

---

**Conclusão probatória:** os fatos sustentam **correções locais funcionais, SQLite privado 3.53.4 efetivamente carregado no backend, backup restaurável e testes direcionados verdes**. Não sustentam ainda **homologação integral da interface Electron, integração dos patches em Git ou garantia universal contra qualquer deadlock futuro**. O padrão persistido DeepSeek está confirmado, mas o modelo efetivo de sessões existentes pode diferir, como demonstrado pela seleção NVIDIA registrada às 15h18.

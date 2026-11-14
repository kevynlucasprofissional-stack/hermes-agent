# Hermes multiagente — qualificação MCP 2.0 e integração ChatGPT (2026-10-25)

**Estado:** SDK mcp==2.0.0 QUALIFICADO LOCALMENTE; UI ChatGPT web / Controle Windows NÃO INTEGRADA; sem release, commit, branch change ou serviço remoto.

## Evidência reproduzível

Checkout C:\Github\hermes-agent, main, HEAD inicial f1d5ab2f030e940ed4571371b0de45a21a009c9e. Dirty/untracked e claims de terceiros preservados.

Baseline anterior: Python 3.13 global, mcp 1.28.0, P2 76 PASS + 1 SKIP. Teste inicial em uv isolado com mcp 2.0.0 falhou ao importar mcp.server.fastmcp.FastMCP (módulo removido na 2.0). Inspeção em ambiente isolado revelou MCPServer em mcp.server.mcpserver / mcp.server. Adaptação cirúrgica no arquivo OWNED workstation/scripts/collab_mcp_server.py: importar FastMCP em 1.x, MCPServer como FastMCP na versão 2.0.0. A API de ferramentas e transporte stdio usada permanece compatível no escopo testado.

Outra quebra em testes: MCP 2 renomeou atributos CallToolResult.isError/structuredContent para is_error/structured_content. Teste workstation/tests/test_collab_mcp_server.py adaptado para suportar ambos. Nenhum patch em P0-A, P0-B ou P1.

Comando isolado Windows, SEM alterar pyproject.toml, uv.lock ou instalar a versão 2.0.0 globalmente:

    uv run --no-project --python 3.13 --with 'mcp==2.0.0' --with 'pytest==9.0.2' -- python -m pytest workstation/tests/test_collab_mcp_server.py workstation/tests/test_collab_tasks.py workstation/tests/test_collab_admission.py workstation/tests/test_collab_git.py workstation/tests/test_multi_agent_coordination.py -q --tb=short

**Resultado mcp==2.0.0:** 76 passed, 1 skipped, 37 subtests passed; exit 0. Ruff dos arquivos P2: PASS.

Também foi repetido o runner canônico do Hermes com seu script scripts/run_tests.sh (em Git Bash), 5 arquivos, 76 PASS / 0 FAIL / 1 SKIP, exit 0, após fallback de bootstrap do ambiente devido a escape PowerShell inválido na variável HERMES_PYTHON; fonte Git, HEAD e branch não foram alterados. O skip foi o teste antigo de criação de symlink no Windows; sem nova regressão.

## O que significa para várias sessões ChatGPT

**Objetivo pretendido:** N chats consultam a mesma autoridade .hermes-collab. Cada chat é obrigado a obter claim disjunta e uma sessão autenticada com segredo retido SERVER-SIDE; write em path sem claim ou de outro owner retorna DENY; handoff não transfere; RELEASE só com decisão explícita; Git com integrador único. O teste de duas sessões comprova isso APENAS via clientes MCP Python independentes e checkout temporário.

**Estado real hoje:** controle-windows/Desktop Commander mantém tools start_process, write_file, edit_block e outros comandos de escrita DIRETOS; não encaminha os efeitos via workstation/scripts/collab_mcp_server.py e não executa os hooks Claude. Portanto N chats ChatGPT usando Controle Windows NÃO são isolados. O comportamento atual é cooperação voluntária com inspect/claim. A documentação instrui clientes a se coordenar, mas documentação NÃO é enforcement. SDK MCP 2.0 verde não altera essa conclusão.

## ChatGPT web: conexão remota necessária

Documentação pública OpenAI:
- https://help.openai.com/en/articles/12584461-connecting-custom-mcp-servers-in-chatgpt
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://developers.openai.com/plugins/build/app-quickstart

O ChatGPT web não lança diretamente servidor MCP stdio no PC. Requer endpoint MCP HTTPS autenticado OU Secure MCP Tunnel associado por ação do usuário na UI Plugins; planos/permissões de escrita podem variar conforme workspace e produto.

**Não conectar a fachada atual como HTTP multiusuário sem refatoração de identidade.** O objeto CollaborationFacade mantém uma única identidade de lease por processo, adequada a stdio com um processo por cliente, e NÃO distingue vários chats recebidos numa única instância web. Um simples FastMCP.run(streamable-http), reverse proxy ou túnel PUBLICADO exporia um servidor com identidade compartilhada e permitiria confusão de ownership. Necessário servidor multi-cliente com credenciais de chamador verificadas, isolamento por sessão/chat, autorização de operação no lado do servidor, rotação/revogação, gates de release/Git, testes RED de sessão cruzada e proteção de rede. Alternativa compatível, se disponível na conta/cliente, é ChatGPT Work com executor local que inicie STDIO separados; verificar suporte real antes de configurar.

Não foram abertos serviços HTTP, expostas portas, criados túneis, instalados plugins ou cadastrados conectores de ChatGPT/Claude. Requer ação explícita de instalação/conexão e acesso do produto. Não declarar integração ChatGPT concluída.

## Documentação atualizada e ownership

Atualizados sob claim específica p2-readiness-context-20261025:
- AGENTS.md: entrypoint raiz e regra de segurança de chats paralelos
- CLAUDE.md: hooks legados e superfície MCP gerenciada
- workstation/AGENTS.md: ponto de entrada de tarefas/ownership
- README.md e workstation/README.md: links e status de colaboração
- CHATGPT.md: novo guia específico (não é auto-lido por padrão)
- este documento.

Arquivos de P2 alterados sob claim p2-mcp-20261025, originalmente criada pela mesma sessão responsável pelo P2: workstation/scripts/collab_mcp_server.py e workstation/tests/test_collab_mcp_server.py. Arquivos M3/WhatsApp (workstation/context/README.md, ROADMAP.md, HERMES_WORKSTATION_INTELLIGENCE.md, CURRENT_STATE.md, DECISIONS.md, engineering-journal/CURRENT.md) não foram editados, porque possuem claims alheios.

## Próximos gates (não executados)

1. Garantir versão MCP 2.0 no runtime de produção (idealmente via extra mcp do Hermes, sem misturar environments) e CI.
2. Escolher formalmente UMA superfície de ChatGPT com capability de custom MCP (Work local executor ou ChatGPT web via Secure MCP Tunnel), configurar consentimento/credenciais e uma identidade por chat.
3. Bloquear/proibir writers irrestritos para tarefas compartilhadas ou não prometer isolamento. Fazer E2E de dois chats ChatGPT reais acessando o mesmo checkout com operação em path estrangeiro NEGADA no host, não somente sugerida por prompt.
4. Integrador autorizado reconcilia arquivos dirty/claims e realiza Git stage/commit/push, após gates do projeto. Nunca usar heartbeat como release automático.

**Aceite para produção concorrente ChatGPT:** N chats isolados, owner A autorizado em paths A, estranho B negado por ferramenta/servidor, sem bypass por terminal exposto a agentes gerenciados; testes em cliente externo, branch/HEAD e Git integration exclusivos. Não atingido ainda.

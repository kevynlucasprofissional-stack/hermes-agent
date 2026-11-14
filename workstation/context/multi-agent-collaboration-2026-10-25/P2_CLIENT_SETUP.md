# Hermes Work P2 — Instruções de conexão MCP (2026-10-25)

**Implementação local:** workstation/scripts/collab_mcp_server.py. Utiliza o SDK MCP Python FastMCP e transporte stdio. Reutiliza multi_agent_coordination.py, collab_admission.py, collab_tasks.py e collab_git.py. A autoridade única de arquivos permanece .hermes-collab/*.claim/owner.json.

**Estado atualizado (2026-10-25):** dois processos MCP stdio independentes passaram testes com SDK real em checkout Git TEMPORÁRIO. Compatibilidade MCP 2.0.0 agora qualificada em ambiente uv ISOLADO: 76 testes PASS / 1 SKIP em cinco arquivos; runner canônico do Hermes também 76 PASS / 1 SKIP. O código suporta FastMCP de 1.x e MCPServer de 2.0.0. Nenhum cadastro externo ChatGPT/Claude foi efetuado. Para ChatGPT web, servidor remoto autenticado ou Secure MCP Tunnel e isolamento por sessão cliente ainda precisam ser implementados e aprovados; ver QUALIFICATION_AND_CHATGPT_CONNECTOR_20261025.md.

## Modelo de sessão

Cada cliente MCP precisa ter um processo stdio distinto. collab_claim registra uma claim nova e vincula o processo a uma sessão P0-B; o token fica no processo e nunca é retornado pela ferramenta. Não usar o mesmo credential-file para dois clientes em paralelo.

Para suportar reconexão, o operador pode escolher --credential-file, apontando para um JSON sob o estado IGNORADO .hermes-collab. O arquivo contém uma credencial bearer, protegida apenas pelas permissões disponíveis na conta Windows atual. Não é isolamento entre processos da mesma conta.

## Claude Code (CLI verificada, instalação NÃO executada)

O comando claude mcp add --help desta máquina confirma -s local, transporte stdio e delimitador --. Para registrar manualmente o adaptador, usar PowerShell:

    claude mcp add -s local hermes-collab -- "C:\Users\Kevyn Lucas\AppData\Local\Programs\Python\Python313\python.exe" "C:\Github\hermes-agent\workstation\scripts\collab_mcp_server.py" --root "C:\Github\hermes-agent" --credential-file "C:\Github\hermes-agent\.hermes-collab\.client-credentials\claude-main.json" --enable-managed-writes

A opção --enable-managed-writes é consentimento explícito para editar por essa interface. OMITA para não permitir escritas. A opção --enable-release fica DESABILITADA por padrão e requer decisão separada do operador. Cada sessão Claude independente deve ter nome de servidor e credential-file diferentes. Não inserir token em prompt, arquivo versionado ou mensagens.

## ChatGPT e Controle Windows

O conector Controle Windows/Desktop Commander que ChatGPT já usa NÃO passa automaticamente pelo MCP recém-criado. Um servidor local stdio não surge sozinho como ferramenta nativa no ChatGPT web.

Para habilitar ChatGPT diretamente, é necessária uma superfície cliente compatível que inicialize o MCP no Windows, ou um gateway remoto autenticado, caso o cliente só suporte servidores de rede. Essa configuração externa não foi efetuada nesta missão, e nenhum endpoint HTTP/OAuth foi criado. Não expor portas, credenciais ou arquivos no ChatGPT sem arquitetura/autorização.

Consultas read-only permanecem disponíveis com o conector Windows atual:
    python workstation/scripts/collab_tasks.py tasks
    python workstation/scripts/collab_tasks.py conflicts

Isso não protege comandos PowerShell ou operações de arquivo irrestritas.

## Ferramentas do servidor

- collab_status: status global, branch, HEAD, tarefas, claims e conflitos; não imprime tokens.
- collab_claim: reclama paths livres e vincula a sessão ao processo.
- collab_check_write: valida identidade/branch/ownership em modo estrito sem editar.
- collab_write_file: com opt-in do operador, cria arquivo texto somente se inexistente ou substitui por SHA-256 esperado; conteúdo até 256 KiB; valida antes de gravar.
- collab_update: publica status e progresso sob owner verificado.
- collab_handoff: grava evento de handoff idempotente, sem transferir propriedade.
- collab_resume: leitura somente; nunca autoriza retomada com escrita.
- collab_release: exige --enable-release e confirmação literal release:<lane>.
- collab_git_request: produz pedido sem stage, commit, push, switch ou merge.

## Limitações explícitas

Servidor local e claims fornecem controle cooperativo sobre operações executadas por essa interface, não uma sandbox de sistema operacional. Um agente com ferramentas diretas de terminal/arquivo pode contorná-los. Arquivos de credencial não isolam processos sob o mesmo usuário Windows. O compare-and-replace ainda possui janela TOCTOU. A implementação é local, não commitada, não é release; testes de código com mcp==2.0.0 aprovados; conexão dos aplicativos e release ainda pendentes. Não tocar ROADMAP, Intelligence e CURRENT, reclamados por M3.

Registro técnico e resultados: workstation/context/engineering-journal/p2-mcp-collaboration-20261025.md

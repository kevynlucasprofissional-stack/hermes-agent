# Hermes P2 — MCP multiagente, handoff de engenharia — 2026-10-25

**Estado:** IMPLEMENTADO/TESTADO LOCALMENTE; NÃO COMMITADO, NÃO INTEGRADO AOS CLIENTES CHATGPT/CLAUDE, NÃO RELEASE.

## Checkout e claims
- C:\Github\hermes-agent, branch main, HEAD na entrada f1d5ab2f030e940ed4571371b0de45a21a009c9e.
- 12 claims observadas antes da missão. P0-A, P0-B e P1 READY_FOR_INTEGRATION intocadas; WhatsApp M3 e Site Ops preservados.
- Claim chatgpt-p2-mcp-20261025 / p2-mcp-20261025: workstation/scripts/collab_mcp_server.py, workstation/tests/test_collab_mcp_server.py, este journal e workstation/context/multi-agent-collaboration-2026-10-25/P2_CLIENT_SETUP.md.
- Claim separada p2-docs-20261025, mesmo agente, para adendos dos docs AGENT_COLLABORATION_PROTOCOL.md e DECISION_AND_EXECUTION_PLAN.md; ambos previamente livres.
- Nenhum git add/commit/push/merge/switch/reset/clean/stash no checkout. Branch/HEAD não alterados.

## Implementação concreta
- Novo FastMCP stdio em workstation/scripts/collab_mcp_server.py: collab_status, collab_claim, collab_check_write, collab_write_file, collab_update, collab_handoff, collab_resume, collab_release e collab_git_request.
- Cada processo MCP tem apenas UMA sessão; usa collab_admission.issue_session/verified_session, multi_agent_coordination para claims, collab_tasks para tarefa/handoff e collab_git somente para consulta Git. Token não é exibido nas respostas MCP.
- Credential-file para reconexão é OPT-IN do operador e restrito ao diretório .hermes-collab ignorado pelo Git. O token é um bearer local, sem isolamento OS entre processos da mesma conta Windows.
- Operações de escrita do servidor são DESABILITADAS por padrão. Opt-in --enable-managed-writes; cria somente arquivo inexistente ou substitui arquivo apenas após comparar SHA-256, até 256 KiB; caminho, branch, lease e ownership checados. Não é transação/sandbox contra escritores externos.
- Liberação é DESABILITADA por padrão; --enable-release mais confirmação release:<lane>. Handoff não transfere, e Git request não stage/commita.
- Proteção contra reuso de antiga lease da mesma lane/agent foi reforçada localmente no facade comparando leases posteriores: teste dedicado confirmado; P0-B original não foi alterado.
- Um detalhe Windows/stdio: processos Git herdavam a entrada stdin reservada ao protocolo e ficavam bloqueados em git rev-parse HEAD. Adapter privado de subprocess em P2 fornece stdin=DEVNULL às funções herdadas de P0-B/P1 SÓ dentro desse servidor. Debug temporário removido antes da qualificação final.
- As nove funções MCP são registradas pelo SDK disponível, sem daemon, rede, DB ou novo Kanban.

## Evidências de testes
- P2 isolado: 15 testes PASS / 4 subtests; inclusive dois processos MCP reais via stdio do SDK e cliente ClientSession, claim A/B, escrita de a.py e b.py em repo Git TEMPORÁRIO, negação B→A, negação sem claim, READY_FOR_INTEGRATION sem release, update/handoff/resume, pedido Git somente leitura, reinício A por credencial salva, release de A autorizado, nova claim C depois do release, HEAD/branch intactos.
- Após corrigir caso de tests_summary apagado por handoff sem novo resumo, e depois fixar credenciais sob .hermes-collab, suíte final canônica (5 arquivos):
  & 'C:\Program Files\Git\bin\bash.exe' scripts/run_tests.sh workstation/tests/test_collab_mcp_server.py workstation/tests/test_collab_tasks.py workstation/tests/test_collab_admission.py workstation/tests/test_collab_git.py workstation/tests/test_multi_agent_coordination.py -q --tb=short
  Resultado **76 passed, 0 failed, 1 skipped**, execução sem retry flaky, 5 arquivos em ~21,1 s. O SKIP é anterior, symlink limitado no Windows.
- Ruff nos dois novos arquivos P2: All checks passed. git diff --check: PASS. Testes em diretórios temporários, sem arquivos dos demais owners.
- Smoke no checkout real somente leitura: 13 tarefas visíveis, 10 alertas de conflitos/heartbeat no momento da consulta; managed_write false por padrão, branch main. Os números variam conforme os demais agentes trabalham.

## Pendente e advertências de qualificação
- Qualificação adicional P2 em 25/10: MCP 2.0.0 testado em ambiente uv isolado, sem substituir o Python global. Adaptado o import FastMCP 1.x / MCPServer 2.0 e o teste de nomes de campos do resultado (`isError` / `is_error`, `structuredContent` / `structured_content`). A suíte de 5 arquivos passou com 76 testes, 1 skip e 37 subtests; Ruff PASS. A suíte canônica também passou 76/1 após bootstrap por erro de escape da variável HERMES_PYTHON. Integração real ChatGPT/Claude, CI e release continuam pendentes; ver QUALIFICATION_AND_CHATGPT_CONNECTOR_20261025.md.
- Claude Code local tem comando cli claude mcp add confirmado, mas NÃO foi registrado para não modificar a configuração do usuário. Procedimento em P2_CLIENT_SETUP.md.
- ChatGPT web NÃO adquire novos tools só por ter Desktop Commander. Necessita ponte MCP cliente ou serviço HTTP com autenticação/OAuth, sem ação implementada/registrada nesta missão; nenhum conector real ChatGPT/Claude foi afirmado testado.
- O test E2E de dois processos MCP comprova o contrato no protocolo, NÃO interop dos aplicativos de terceiros. Nenhum HTTP server, porta, webhook ou integração externa criada.
- Segurança cooperativa: terminal/PowerShell/Desktop Commander/Git irrestrito pode contornar guardas. Múltiplos processos sob um mesmo login Windows podem ler arquivos de credencial. Não prometer sandbox.
- Roadmap, Hermes Intelligence, CURRENT e Decisions canônicos continuam reclamados por M3; nenhum foi editado. Handoff para owner/integrador permitido apenas após verificação de claims.

## Próximo gate
Marcar P2 e p2-docs como READY_FOR_INTEGRATION, preservar claims, não liberar nem integrar Git sem designação/autorização. Conferir versão fixada SDK mcp 2.0.0, registrar cliente Claude real com consentimento e planejar ChatGPT bridge sob aprovação separada. Após E2E entre aplicativos reais, qualificação de release/integração deve ser feita por integrador autorizado.

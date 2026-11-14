# START HERE — Hermes multi-agent rollout (2026-10-25)

Este pacote foi criado NO checkout local C:\Github\hermes-agent, sem criar branch/worktree, fazer commit ou instalar componentes. Continua em PROPOSTA e nao substitui o coordenador em execucao.

1. Leia DECISION_AND_EXECUTION_PLAN.md para decisoes, limites, owners e prioridades.
2. Copie o PROMPT 1 de IMPLEMENTER_PROMPTS.md para um agente implementador com acesso ao Controle Windows. Os prompts 2, 3 e 4 devem seguir apenas apos gate da etapa anterior.
3. O codigo realmente pronto para revisar e aplicar na primeira etapa esta em reference/multi_agent_coordination_p0.patch e multi_agent_coordination_p0.py. Nao promover se o arquivo vivo tiver mudado; build_p0_patch.py exige source exata.
4. reference/test_p0_candidate.py passou 11/11 isolado; reference/pretool_write_guard.py e um prototipo de admission de escrita, NAO hook instalado; coordination_task_schema.json e mcp_tool_contract.json sao contratos de design, nao runtime implementado.
5. CANONICAL_INSERTS.md prepara as insercoes destinadas a workstation/ROADMAP.md, Hermes Workstation Intelligence, CURRENT journal e Decisions, atualmente reclamados por M3. AGENT_COLLABORATION_PROTOCOL.md recebeu adendo com link para este dossie; journal factual isolado: ../engineering-journal/multi-agent-collaboration-20261025.md.
6. Em caso de conflito, preserve todos os owners existentes, evite alteracoes globais de Git e entregue handoff. Nenhum prompt autoriza operacoes Git mutantes ou release automaticamente.

Verificacoes locais:
- python workstation/context/multi-agent-collaboration-2026-10-25/reference/build_p0_patch.py
- python workstation/context/multi-agent-collaboration-2026-10-25/reference/test_p0_candidate.py -v
- python -m py_compile workstation/context/multi-agent-collaboration-2026-10-25/reference/pretool_write_guard.py
- python workstation/scripts/multi_agent_coordination.py status

Importante: nao executar build_p0_patch.py enquanto outro agente estiver modificando workstation/scripts/multi_agent_coordination.py. O builder verifica a fonte e grava somente dentro da pasta reference, mas a suite de integracao deve pertencer ao implementador P0-A.

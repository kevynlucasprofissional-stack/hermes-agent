# Hermes Work — Multi-Agent Shared Checkout | Decisão técnica e plano de implementação
Data: 2026-10-25. STATUS ATUAL: P0-A, P0-B, P1 E P2 IMPLEMENTADOS E TESTADOS NO CHECKOUT LOCAL, SEM GIT INTEGRATION/RELEASE; CLIENTES EXTERNOS NÃO CADASTRADOS. O diagnóstico abaixo é o snapshot inicial da análise (antes das correções). Ver workstation/context/engineering-journal/p0a-coordinator-20261025.md, p0b-guarded-admission-20261025.md, p1-collaboration-20261025.md e p2-mcp-collaboration-20261025.md. P2: 76 PASS, 0 FAIL, 1 SKIP no runner canônico. Claude Code suporta configuração stdio, mas não foi cadastrado. ChatGPT web requer bridge compatível: nenhum novo conector foi conectado. O ambiente local usa mcp 1.28.0 e pyproject.toml fixa mcp 2.0.0, ainda não qualificado no extra. Configuração em P2_CLIENT_SETUP.md.

## Origem e checkout inspecionado
- Repositório: C:\Github\hermes-agent; branch observada main; HEAD f1d5ab2f030e940ed4571371b0de45a21a009c9e.
- Checkout compartilhado com numerosas alterações locais, inclusive mudanças não integradas de WhatsApp/Browser/Site Ops.
- 12 claims no snapshot de 2026-10-25, incluindo chatgpt-whatsapp-m3 com ownership de workstation/ROADMAP.md, workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md e workstation/context/engineering-journal/CURRENT.md (casefold intencional).
- Arquivo de coordenação em produção: workstation/scripts/multi_agent_coordination.py; autoridade local: .hermes-collab/*.claim/owner.json.
- Contratos em AGENTS.md, CLAUDE.md, workstation/AGENTS.md, workstation/context/AGENT_COLLABORATION_PROTOCOL.md e .claude/hooks. Não redefinir os gates Workstation / H-079 nem inferir release.

## Diagnóstico reproduzido
1. check_path() ignora toda reserva que não esteja em status ACTIVE, embora os status READY_FOR_INTEGRATION/BLOCKED/IN_PROGRESS não liberem propriedade. Exemplo reproduzido: apps/desktop/electron/ipc/site-ops.ts pertence a claim READY_FOR_INTEGRATION mas check-path respondeu allowed=true.
2. check_path() permite edição não reclamada, inclusive quando a política exige claim; ambos os hooks têm fallback fail-open.
3. check-claim-edit.sh e check-claim-bash.sh chamam check-path sem identidade do agente. O proprietário de tools/browser_workstation.py foi bloqueado em teste sem --agent, mas liberado com --agent chatgpt-whatsapp-m3.
4. check-branch.sh somente avisa diferença de branch, sem bloquear Git mutante. Sessões Claude são protegidas parcialmente; operações PowerShell/Windows MCP/ChatGPT não estão integralmente cercadas.
5. Um diretório *.claim sem owner.json é visível no status, mas não bloqueia automaticamente outras claims ou writes. owner.json de registro corrompido deve falhar fechado.
6. TEAM_BOARD.md é snapshot histórico, não plano vivo da equipe. O controle de transcrições Claude em workstation/dogfood/dados/CONTROLE_SESSOES_IA.json cataloga históricos, mas NÃO é autoridade de arquivos nem substitui claims.
7. read_claims()+registry_guard usa mkdir atomicamente no Windows; NÃO substituir sem prova, nem implantar PostgreSQL/Redis/Kanban paralelo agora.

## Decisões arquiteturais
D-MA-01 — Uma branch por checkout físico: ler git branch --show-current no início; NUNCA criar/trocar/apagar branch/worktree sem autorização expressa da tarefa e preflight. A existência de main neste momento não autoriza override permanente quando o mantenedor tiver mudado a branch.
D-MA-02 — Claims são exclusividade cooperativa de escrita, separados do status operacional: qualquer claim existe e bloqueia todos os outros até release/transferência explícitos; status DONE/READY/BLOCKED não libera por si só.
D-MA-03 — Sem reserva, sem escrita após ativar strict mode. O rollout será gradual, por ferramenta/canal, para não interromper agentes que já executam tarefas. Invalid path, registry corrupt/partial e identidade ausente devem negar mutações gerenciadas; leitura continua possível.
D-MA-04 — Identidade real é por sessão/run (id não reutilizável) com prova de posse da lease para APIs gerenciadas. Um --agent livre é apenas cooperação legada, NÃO autenticação contra ferramentas arbitrárias rodando sob a mesma conta Windows.
D-MA-05 — Integração Git exclusiva e serializada, com autorização expressa de operação e seleção precisa de paths (nada de git add ., clean, reset, stash, switch automático). Bloquear mutation no ponto de entrada controlado; wrapper não torna binários Git externos magicamente seguros.
D-MA-06 — Persistir eventos/handoff na mesma raiz .hermes-collab, sob mesma registry_guard ou protocolo de gravação serializado, sem novo DB/segundo Kanban. Uma visão Kanban futura deve ser projeção, não autoridade.
D-MA-07 — Heartbeat/timeout são sinais de recuperação; nunca expirar, roubar ou apagar claim silenciosamente. Recuperação demanda reconciliação de diffs, PID/sessão quando verificável e decisão humana/integrador.
D-MA-08 — Hooks Claude e MCP ChatGPT convergem em operação local única de admission; ferramentas irrestritas de shell/file ainda conseguem contornar regras: não vender isolamento de segurança como garantido antes de limitar essas ferramentas.
D-MA-09 — Uma implementação por missão com provas RED→GREEN, testes de regressão e E2E real; nenhum envio WhatsApp ou efeito externo nesta iniciativa.
D-MA-10 — Artefatos técnicos e documentação de proposta não concedem Stage A green, promoção, integração nem consentimento para modificar arquivos de outros agentes.

## Arquivos de referência prontos
- reference/build_p0_patch.py — gera diff somente se encontrar exatamente a fonte esperada; falha em drift, sem editar runtime.
- reference/multi_agent_coordination_p0.py — candidato gerado do runtime com proteção de claims independentes de status, registro incompleto fail-closed e modo estrito opt-in.
- reference/multi_agent_coordination_p0.patch — patch unificado aplicável/revisável pelo implementador; nunca aplicar cegamente.
- reference/test_p0_candidate.py — 11 testes isolados PASS em Windows; fonte viva NÃO foi alterada.
- CANONICAL_INSERTS.md — pontos de inserção exatos destinados aos documentos reclamados por chatgpt-whatsapp-m3.
- IMPLEMENTER_PROMPTS.md — prompts de execução 1–4, com critérios mensuráveis.
- engineering-journal/multi-agent-collaboration-20261025.md — evidência da preparação.

## Sequência e critérios
P0-A (1 prompt): patch coordinator+testes existentes, backward compatibility e strict opt-in. Sem tocar nos claims atuais ou nos demais owners; migrar quando seguro.
P0-B (1 prompt): guard hooks/CLI, identidade vinculada à sessão, path canonicalization, Git integration freeze e mecanismos de adopção gradual. Segurança real depende de todos os caminhos de escrita aderirem ao admission; não pressupor isso.
P1 (1 prompt): task registry/handoff/eventos/heartbeats com owner/lease, conflicts/status/tasks, sem novo banco de dados e sem timeout stealing.
P2 (1 prompt): MCP adapter leve reutilizando o serviço local de coordenação; credenciais/autorizações locais e teste de dois chats usando Controle Windows + Claude sem efeitos externos. Tool configuration externa pode exigir ação do usuário.

## Convergência da documentação
Os docs canônicos ROADMAP.md, CURRENT_STATE.md, HERMES_WORKSTATION_INTELLIGENCE.md, engineering-journal/CURRENT.md, DECISIONS.md estão atualmente reclamados por M3. NÃO editar sem release ou handoff. CANONICAL_INSERTS.md preserva proposta pronta para owner aplicar. Este arquivo + journal próprio + adendo ao AGENT_COLLABORATION_PROTOCOL.md são a documentação vigente desta análise, sem falsificar integração canônica.

## Stop conditions
- Outro claim em path a editar: parar, preparar handoff isolado, nunca substituir.
- Registro inconsistente, falha de Python/PowerShell ou função de guarda: negar mutação, permitir inspeção; solucionar a causa antes de continuar.
- Patch-source drift: reapreciar somente a função alterada, não reler indiscriminadamente o projeto.
- Necessidade de mudança Git mutante/branch/release: só integrador designado e autorização específica.
- Mudança para Windows+Linux multi-host real: abrir decisão própria para autoridade distribuída; não prometer locks locais cross-host.

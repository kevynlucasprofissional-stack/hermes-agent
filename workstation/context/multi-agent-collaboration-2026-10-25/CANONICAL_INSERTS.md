# CANONICAL_INSERTS — insercoes aguardando release/handoff do owner M3 (2026-10-25)
NAO editar os docs reclamados com base apenas neste arquivo. Depois de autorizacao ou release, o owner le o estado real e integra sem apagar texto local. Cada bloco abaixo e uma INSERCAO, nao substituicao integral.

## workstation/ROADMAP.md — inserir na secao de iniciativas operacionais/P0, antes das milestones pendentes
### MA-2026-10-25 — multi-agent shared-checkout coordination (P0-A → P0-B → P1 → P2)
Design preparado (NAO implementado no runtime): corrigir ownership claim em todos os status; strict admission opt-in; autenticar identidade da sessao e serializar Git; visibilidade de tarefas, dependencias e handoff; integrar adapter MCP ao ChatGPT/Claude. Reutilizar workstation/scripts/multi_agent_coordination.py e .hermes-collab. Nao criar outro DB, Kanban, branch/worktree ou estado central. Patch de referencia e 11 testes PASS isolados em workstation/context/multi-agent-collaboration-2026-10-25/reference/. Prompts autossuficientes em IMPLEMENTER_PROMPTS.md. Guardas existentes Claude nao cobrem todos os caminhos Windows/PowerShell/ChatGPT; nao declarar enforcement universal nem release.

## workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md — inserir em Diretrizes Estrategicas e Operacionais, nao no historico de funcionalidades comprovadas
Decisao MA-2026-10-25: o Windows compartilhado usa uma branch lida do checkout (mudancas so se mantainer pedir), claims exclusivos por path independentes do status, registry local unico em .hermes-collab e um integrador explicitamente autorizado para Git mutante. Chats usam plano de tarefas/handoff, nao memoria de conversa como autoridade. Adoção MCP planejada para que cada cliente consulte o mesmo coordenador. Arquitetura cooperativa: comandos arbitrarios fora da interface gerenciada ainda podem contornar a politica; exigir superficie de escrita controlada para garantias. Codigo preparado nao equivale a codigo runtime promovido; nenhuma qualificacao Stage A ou release inferida.

## workstation/context/DECISIONS.md — adicionar ID novo SOMENTE depois de conferir context/ID_DISAMBIGUATION.md
Adotar: uma branch por checkout; claims de escrita retidos ate release; ownership por sessao, lock de Git exclusivo, status operacional nao libera; sem PostgreSQL/Redis/Kanban duplicado no host unico; heartbeat so evidencia, sem expiracao/roubo; MCP adapter fino, nao novo runtime. Decisoes e limitacoes em multi-agent-collaboration-2026-10-25/DECISION_AND_EXECUTION_PLAN.md. Consultar index para alocar D-ID exclusivo, NUNCA reaproveitar um identificador existente.

## workstation/context/engineering-journal/CURRENT.md — insercao de observacao com link ao journal isolado
2026-10-25: diagnostico multiagente: check_path() ignora claims READY/BLOCKED e hooks Claude falham abertos/nao fornecem ID; branch hook apenas avisa. Checkout main f1d5ab2f..., 12 claims no snapshot, inclusive owner M3 dos docs centrais. Preparado patch para coordinator sem aplicacao, 11 testes de referencia PASS em tmpdir; escopo em workstation/context/multi-agent-collaboration-2026-10-25/. O patch e DESIGN/READY_FOR_IMPLEMENTATION, nao fix da producao. Handoff e evidencias em engineering-journal/multi-agent-collaboration-20261025.md.

## workstation/context/CURRENT_STATE.md — registrar somente apos owner conferir HEAD/claims atualizados
Iniciativa MA-2026-10-25 planejada; nenhum gate/runtime promovido. Claims existentes preservados. Padrao Git: branch atual somente, sem nova branch/worktree por iniciativa dos agentes. P0-A core bugs, P0-B guards/git, P1 handoff, P2 MCP. Escalonar etapas sob claims livres e sem competir com WhatsApp M3/ SiteOps ativos.

## workstation/context/README.md / AGENTS.md / CLAUDE.md — modificar apenas depois de P0-B qualificado
Acrescentar ponte curta aos artefatos do protocolo: no comeco da sessao ler .hermes-collab via status e respeitar claims independentemente do status; exigir claim antes de write, novo mecanismo de identidade e hooks estritos somente quando ja instalados. NAO documentar comandos nao implementados como se operacionais. Nunca instruir default switch para branch historica.

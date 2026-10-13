# HWH-001 — Estado operacional vigente em 2026-10-13

> Este documento substitui o checkpoint histórico de 2026-10-12, que descrevia PRs e worktrees já consolidados na main. Não usar identidades antigas para orientar novas alterações.

## Identidade
- Repositório: `kevynlucasprofissional-stack/hermes-agent`.
- Base verificada em `main`/`origin/main` ao abrir o ciclo: `b80d10a4d6d4536b65df52eb4e011ad8d5eef672`.
- Branch compartilhada: `feat/hermes-workstation-mvp-20261013`.
- Único checkout de desenvolvimento: `C:\Github\hermes-agent`.
- Projeto e documentação: `workstation/context/workstation-hub-mvp/`.
- SHA atual, status de sincronização e claims: executar `git rev-parse HEAD`, `git status -sb`, `python workstation/scripts/multi_agent_coordination.py status`. Não confundir este baseline inicial com HEAD futuro.
- Antigo PR #87: merged em `main`, **documentação apenas**; o antigo `NEXT_PROMPT.md` e bloqueios específicos daquela sessão foram superados como identidades de trabalho, NÃO como provas funcionais.

## Prova de observação 2026-10-13
- `apps/desktop/src/app/creative-workspace/CreativeWorkspacePage.tsx` inclui `CreativeWorkspaceProvider`; evitar recodificação redundante.
- `apps/desktop/src/app/chat/sidebar/index.tsx` ainda mostra `label: 'Browser'`.
- Não foi demonstrada no produto a capability de abrir o Creative interno pelo comando do agente, a aba Creative dentro do Hub, nem o botão seguro `Levar para sessão`. Os três fluxos permanecem como entrega a fazer.
- Original `main` estava limpa e sincronizada no instante do checkout; ferramentas de coordenação foram adicionadas na nova branch.
- O gate H-079 upstream-first e CI exata continuam válidos; estado H-079 atual não foi requalificado nesta fase documental. Não assumir PASS automaticamente.
- Há worktrees externos antigos do Codex registrados por Git; não apagá-los sem confirmar owner. Nenhum worktree adicional foi criado neste ciclo.

## Fases — orçamento de prompts
| Fase | Produto | Estado neste checkpoint |
|---|---|---|
| 0 | Branch única, protocolo compartilhado, ferramenta de claims, testes e handoff | Em execução; passa a DONE após verificação, commit e push |
| 1 | Agent abre Creative + sidebar Workstation + aba Creative | NOT_STARTED |
| 2 | Levar tab manual para sessão real, sem recriar Chromium, com lease humano | NOT_STARTED |
| 3 | Três E2E nativos, segurança, CI, PR final | NOT_STARTED |

**Meta: 3 próximos prompts** depois da fase 0; pode haver mais apenas diante de bloqueio material comprovado. Se um prompt terminar com uma fase completa e houver capacidade, continuar na próxima.

## Critérios
Sem E2E Electron real = `NOT_VERIFIED_NATIVE`. Sem autoridade autenticada/lease de usuário = `RELEASE_BLOCKED`. Agentes não alteram `main` e não abrem branches/worktrees extras. O integrador é o único escritor Git, e conflitos de arquivo têm owner definido no protocolo.

## Continuidade
Ler `TEAM_BOARD.md`, `IMPLEMENTATION_STAGES.md`, `NEXT_PROMPT.md` e `../AGENT_COLLABORATION_PROTOCOL.md`; confirmar HEAD/claims reais. Ao final de qualquer sessão incompleta, publicar próximo prompt autossuficiente, com estado factual e obrigação recursiva.

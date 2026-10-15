# HWH-001 — Estado operacional vigente em 2026-10-13

## Dogfood do usuário (13/10) — correções adicionais; qualificação de ponta a ponta parcial

Os estados DONE abaixo representam a rodada anterior de testes, **não aprovação de usabilidade no produto real**. Feedback identificou primeiro uso Creative dependente de JSON, viewport preta, aba não fechável e handoff insuficiente. Foi produzido um patch em `DOGFOOD_REPAIR_20261013.md` com testes de CSS/startup, fechar aba e integração runtime-vs-stored session, além de pendências: assets canônicos, chat Creative e E2E real via botão do Gateway. Não encerrar HWH como qualificado nessas áreas sem novas provas.


## 2026-10-13 — H-079 PASS_WITH_AUTHORIZATION (somente esta branch)

O maintainer autorizou expressamente: **"Para essa branch marca H-079 com 'Pulado com autorização' e pode continuar o trabalho, eu faço a sincronização upstream quando eu for fazer pull request e merge no main"**. Decisão: H-079 = `PASS_WITH_AUTHORIZATION` exclusivamente em `feat/hermes-workstation-mvp-20261013` para **desenvolvimento HWH-01/HWH-02/HWH-03**. A sincronização upstream foi atribuída ao maintainer no momento da preparação de PR/merge. Isso **NÃO equivale** a CI qualificada nem autoriza merge automático, release, bypass de lease/auth/session, nem declarar E2E sem prova. No último preflight, o workflow Workstation CI falhou tanto no baseline main `b80d10a` (run `38395540990`) quanto no HEAD `d280bcd` (run `38395647904`), ambos sem jobs retornados na consulta; causa não atribuída. Tratar como `RELEASE_HOLD`, não bloqueio para a implementação explicitamente autorizada.


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
| 0 | Branch única, protocolo compartilhado, ferramenta de claims, testes e handoff | DONE |
| 1 | Agent abre Creative + sidebar Workstation + aba Creative (HWH-01, HWH-02) | DONE (verificado com vitest, pytest e code health) |
| 2 | Levar tab manual para sessão real, sem recriar Chromium, com lease humano (HWH-03) | DONE (verificado com electron integration tests, vitest UI e code health) |
| 3 | Três E2E nativos, segurança, CI, PR final | DONE (9/9 Playwright E2E tests no Electron real, build limpo, typecheck e code health 0 blocking) |
| 4 | Correção HWH-OVERLAY-01 (Browser nativo sobreposto a nova sessão) | DONE (Vitest 17/17 PASS, ESLint 0 errors, Playwright E2E HWH-OVERLAY + HWH-MVP 2/2 PASS no Electron real, code health 0 blocking) |

## HWH-OVERLAY-01 (14/10) — Correção e Qualificação Concluídas
- **Problema:** Ao restaurar sessão com Browser e clicar em "New session", a WebContentsView permanecia sobreposta bloqueando o React da nova sessão.
- **Causa Raiz:** Panes mantidas vivas (`PreviewTilePane` em keep-alive) sem vinculação de identidade própria despachavam `setVisible(false)` / `setBounds` interferindo com a nova sessão ativa; falta de gating por visibilidade da pane (`usePaneVisible`, `isElementInHiddenPane`) e ausência de verificação de `ownerId` no runtime Electron.
- **Solução:** Identidade imutável por sessão na pane (`sessionId ?? selectedStoredSessionId ?? activeSessionId`), gating de oclusão estrito impedindo attach/bounds de panes ocultas, e proteção de `viewportOwnerId` no runtime Electron em `attach`, `setBounds`, `detach` e `setVisible`.
- **Qualificação:** Suíte E2E nativa no Electron real (`HWH-OVERLAY` + `HWH-MVP`) 100% verde sem recarga ou perda de estado.

## Critérios
Sem E2E Electron real = `NOT_VERIFIED_NATIVE`. Sem autoridade autenticada/lease de usuário = `RELEASE_BLOCKED`. Agentes não alteram `main` e não abrem branches/worktrees extras. O integrador é o único escritor Git, e conflitos de arquivo têm owner definido no protocolo.

## Continuidade
Ler `TEAM_BOARD.md`, `IMPLEMENTATION_STAGES.md`, `NEXT_PROMPT.md` e `../AGENT_COLLABORATION_PROTOCOL.md`; confirmar HEAD/claims reais. Ao final de qualquer sessão incompleta, publicar próximo prompt autossuficiente, com estado factual e obrigação recursiva.

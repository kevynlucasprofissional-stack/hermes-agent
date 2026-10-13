# EXECUTAR FASE 3/3 — HWH-001: PROVAS NATIVAS E2E, QUALIFICAÇÃO CI E PR AGREGADO
**IMPLEMENTAÇÃO DIRETA. UM ÚNICO BRANCH/CHECKOUT. SEM NOVAS BRANCHES/WORKTREES. SEM MERGE NA MAIN.**

Você opera no Windows diretamente em `C:\Github\hermes-agent`, na branch `feat/hermes-workstation-mvp-20261013`. Não crie branches extras, clones ou worktrees. O usuário aprovou a continuidade direta sem reinício de auditoria.

## 1. Identidade e estado verificado
- Repo: `kevynlucasprofissional-stack/hermes-agent`
- Branch única: `feat/hermes-workstation-mvp-20261013`
- Checkout único: `C:\Github\hermes-agent`
- Último HEAD publicado confirmado: `74560902ac`
- Commits concluídos neste ciclo:
  - `c527e60032`: feat(workstation): integrate HWH-01 and HWH-02 Agent-Creative and Workstation Hub UI
  - `74560902ac`: feat(workstation): implement HWH-03 manual tab adoption into session with WebContentsView and human lease preservation
- Working tree: LIMPO (`git status --short` vazio), sincronizado com `origin/feat/hermes-workstation-mvp-20261013`.
- Gate H-079: `H-079 = PASS_WITH_AUTHORIZATION` exclusivamente nesta branch (sincronização upstream pelo maintainer antes do PR/merge). Não interromper a qualificação por esse gate.
- Documentação sincronizada em: `workstation/context/workstation-hub-mvp/{STATE,TEAM_BOARD,NEXT_PROMPT}.md` e `workstation/context/engineering-journal/CURRENT.md`.

## 2. Entregas consolidadas até o momento
- **HWH-01 (Agent → Creative):** Ferramenta `open_creative_workstation` em `tools/creative_workstation_tool.py`, registrada no toolset `desktop_ui` (`toolsets.py`), evento `creative.open` roteado pelo bridge do desktop (`desktop-bridge.ts`) navegando para `/browser?creative=1`. 4/4 pytests PASS.
- **HWH-02 (Browser → Workstation):** Sidebar renomeada para 'Workstation' mantendo rota `/browser` (`apps/desktop/src/app/chat/sidebar/index.tsx`), aba interna React Creative com alternância fluida e preservação da WebContentsView Chromium (`apps/desktop/src/app/browser/index.tsx`), modularização em subcomponentes satisfazendo o ratchet de complexidade ciclomática. 25/25 vitests de UI e routes PASS.
- **HWH-03 (Levar para sessão):** Método `adoptTab` no runtime Electron (`apps/desktop/electron/workstation-browser-runtime.ts`), canal IPC tipado em `workstation-browser-ipc.ts`, exposto via preload (`preload.ts`), botão 'Levar para sessão' com hook `useAdoptTabToSession` prevenindo double-clicks e adotando a `WebContentsView` sem disparar `loadURL`, vinculando `BrowserTask` à sessão Gateway e retendo o lease de controle humano (erro 409 `USER_CONTROL_ACTIVE` até liberação explícita). 36/36 testes do runtime Electron PASS, 3/3 testes unitários de adoção PASS, code health 0 blocking.

## 3. Coordenação multiagente
Antes de editar qualquer arquivo:
`python workstation/scripts/multi_agent_coordination.py status`
- Reivindique os arquivos com `claim` apenas se a lane estiver livre:
  `python workstation/scripts/multi_agent_coordination.py claim --agent agent-integrator --lane integration-qa --paths apps/desktop/e2e workstation/context/workstation-hub-mvp --task "HWH-04 Stage 3 Native E2E and CI qualification"`
- Somente o `agent-integrator` realiza commits e push no Git. Nunca utilize `git reset --hard`, `git clean -fd` ou `git checkout main`.

## 4. Objetivo desta sessão — Fase 3: E2E Nativo, Segurança e PR Final
1. **Executar / Adaptar testes E2E do Electron:**
   - Executar os testes E2E direcionados do Desktop:
     `npm run typecheck` (em `apps/desktop`)
     `npm run check:lint` (em `apps/desktop`)
     `python scripts/check --only health` (na raiz do repositório)
   - Executar suíte Playwright ou headless E2E para comprovar as três jornadas:
     `npx playwright test e2e/workstation-headless-load.spec.ts` (ou via suite configurada)
   - Comprovar que a adoção de sessão e a troca de abas preservam o estado sob o Electron real sem crashes ou vazamento de viewport.
2. **Qualificação CI e Preparação de PR:**
   - Validar que todos os testes Python e TypeScript passam com zero findings bloqueantes.
   - Criar PR agregado a partir de `feat/hermes-workstation-mvp-20261013` direcionado ao repositório ou preparar evidências para o maintainer.
   - Atualizar `EVIDENCE.md`, `TEAM_BOARD.md` e `STATE.md` com os logs das execuções E2E nativas.

## 5. Handoff recursivo obrigatório
Se a sessão terminar antes da abertura do PR ou da finalização das provas nativas:
1. Registre o progresso exato em `workstation/context/engineering-journal/CURRENT.md` e `workstation/context/workstation-hub-mvp/STATE.md`.
2. Atualize o heartbeat com `python workstation/scripts/multi_agent_coordination.py update`.
3. Entregue um novo prompt de continuidade integral pronto para executar no Antigravity, preservando todos os contratos, comandos e esta mesma obrigação recursiva.

# EXECUTAR FASE 1/3 — HWH-001: CREATIVE LAUNCH + WORKSTATION HUB
**IMPLEMENTAÇÃO DIRETA. UM ÚNICO BRANCH/WORKTREE (CHECKOUT). SEM NOVAS BRANCHES/WORKTREES. SEM MERGE NA MAIN.**

Você opera no Windows via GitHub, Remote Desktop Commander, Superpowers e Community Agent Workflows. O usuário concluiu a consolidação anterior e já aprovou a estratégia de coordenação e o MVP 20/80. Não transforme esta solicitação em nova auditoria geral.

## 1. Identidade e estado verificado
Repo: `kevynlucasprofissional-stack/hermes-agent`
Branch compartilhada: `feat/hermes-workstation-mvp-20261013`
Checkout único: `C:\Github\hermes-agent`
Origem: `main`/`origin/main` limpa em `b80d10a4d6d4536b65df52eb4e011ad8d5eef672` no preflight de 2026-10-13.
O HEAD na sua sessão pode ser posterior; confirme `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, `git rev-parse origin/feat/hermes-workstation-mvp-20261013` (se publicado). Não volte a fazer checkout em `main` para trabalhar.
Estado factual e orçamento: `workstation/context/workstation-hub-mvp/{STATE,TEAM_BOARD,IMPLEMENTATION_STAGES,PLAN,EVIDENCE,DECISIONS,NEXT_PROMPT}.md`; protocolo obrigatório: `workstation/context/AGENT_COLLABORATION_PROTOCOL.md`; regras: `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/README.md`.
O antigo PR #87 foi merged, mas somente documentou pendências. Atualmente `CreativeWorkspacePage.tsx` JÁ tem Provider. Sidebar ainda dizia `Browser`. As três jornadas completas ainda não foram comprovadas.

## 2. Cooperação obrigatória com outros agentes
Antes de editar, execute:
`python workstation/scripts/multi_agent_coordination.py status`
Se `integration-qa` estiver disponível e você tiver função de integrador, faça claim do board/docs e conduza apenas você operações de Git write. Se outra IA já é integradora, NÃO escreva índice Git/commits/push, e escolha uma lane livre com fonte disjunta.
Claims exemplares (modifique a lista --paths para as fontes realmente editadas):
`python workstation/scripts/multi_agent_coordination.py claim --agent agent-creative --lane creative-agent --paths workstation/integrations/hermes apps/desktop/src/app/creative-workspace --task "HWH01 opening Creative internally"`
`python workstation/scripts/multi_agent_coordination.py claim --agent agent-hub --lane hub-ui --paths apps/desktop/src/app/browser apps/desktop/src/app/chat/sidebar --task "HWH02 Workstation and Creative tab"`
Outros agentes nunca escrevem arquivos que estejam no claim de outro. Arquivos integradores (`apps/desktop/electron/preload.ts`, `browser/index.tsx`, `contrib/surfaces.tsx` etc.) têm um único owner; consumidor entrega sugestão de patch ao owner. Atualize `update --agent ... --lane ... --status IN_PROGRESS --next "..."` após mudanças materiais. Sem lock steal nem edição simultânea de código/índice. O integrador controla freeze/commit/push, apenas arquivos explicitamente listados.
O sistema é cooperativo, não substitui autenticação/authority nem resolve colaboração em máquinas diferentes. Não use `git add .`, `git clean`, `git reset --hard`, stashes ou troca de branch enquanto há outros agentes.

## 3. Objetivo desta sessão — entregar DOIS recursos em um incremento vertical
**HWH-01:** pedido natural “Abra o Creative Workstation” (e aliases) aciona uma ferramenta/capacidade real e conhecida do Hermes Agent para abrir ou focar o **Creative React interno** via canal Desktop autenticado; sem pesquisas no filesystem, sem URL de HyperFrames e sem falso sucesso. Seguir registro de ferramentas já existente, não criar outro tool framework. Operação existente `browser_creative_studio_open` é para estúdios loopback e NÃO equivale à interface interna. Repetição é idempotente; indisponibilidade Desktop retorna erro tipado.
**HWH-02:** menu lateral **Browser → Workstation** (continuar `/browser`), botão **Abrir Creative Workstation** no Hub, aba React Creative lado a lado com abas Chromium nativas. Alternância preserva `WebContentsView`, JS/form/scroll web; preserva estado do Creative, oculta/mostra native viewport sem interceptar cliques. Reutilizar Provider correto JÁ PRESENTE. O botão deve usar a mesma operação interna que o agente, sem dois caminhos paralelos.

## 4. Touchpoints verificados
`apps/desktop/src/app/browser/index.tsx` — Browser Hub, abas, `useNativeViewOcclusion`; `apps/desktop/src/app/browser/native-view-occlusion.ts` e testes; `apps/desktop/src/app/chat/sidebar/index.tsx` — label Browser; `apps/desktop/src/app/contrib/surfaces.tsx` — rota Creative; `apps/desktop/src/app/creative-workspace/CreativeWorkspacePage.tsx` — Provider já montado; `apps/desktop/electron/preload.ts`; `apps/desktop/electron/workstation-browser-runtime.ts`; Hermes integration `workstation/integrations/hermes/browser_controller.py`, e registro de tools Agent. Use mínima investigação causal dos contratos reais e conte com os PRs antigos apenas como histórico já merged.
A parte Creative híbrida TaskRun do PR #81 pode estar ainda release-held; abrir a UI não autoriza mutação canônica. Respeite o gate H-079/CI do repositório: verificar a admissibilidade atual em um preflight limitado, registrar blocker apenas uma vez/ciclo; sem bypass ou downstream runtime change proibido pela política.

## 5. TDD / aceites concretos
Escreva teste RED antes de patches comportamentais. Faça GREEN e regressão focada. Comprove:
A. comando do agente abre UI interna, sem ferramentas de busca de código, segundo comando só foca; Desktop indisponível falha fechada.
B. sidebar diz Workstation com `/browser` intacta, botão abre Creative funcional, alternância web↔Creative não recria/recarrega native tab nem bloqueia clique; provider não falha.
Não declarar conclusão com testes unitários apenas: demonstre no Electron real quando ambiente permitir, senão marque `NOT_VERIFIED_NATIVE`.
Sem expandir para editor profissional, EffectCraft completo, refatoração Browser, Experience Compiler, Kanban ou automação aprendida. Não abrir nova branch/PR por microajuste.

## 6. Orçamento de prompts/etapas
Fase 0 — colaboração/branch/contexto já preparados.
**Fase 1 (esta):** HWH01 + HWH02 integrados.
**Fase 2 (próximo prompt):** botão **Levar para sessão**, `session.create` canônico, adotar MESMA `WebContentsView`, BrowserTask↔Session, human 409/release, duplicações/rollback.
**Fase 3:** três native E2E A/B/C, security/CI e PR agregado final.
A meta são **3 prompts de implementação após setup**, não uma lei física. Se concluir a fase 1 e ainda puder trabalhar, CONTINUE imediatamente fase 2, sem solicitar outro prompt ou confirmação.
Cada investigação deve resolver um problema objetivo de acceptance. Corrigir gaps de segurança realmente necessários, mas não buscar perfeição de arquitetura sem falha reproduzível.

## 7. Handoff recursivo obrigatório
Se parar incompleto, atualize os documentos canônicos `STATE.md`, `TEAM_BOARD.md`, `EVIDENCE.md`, `NEXT_PROMPT.md` **via integrador**, e entregue um prompt completo pronto para copiar/colar que cite:
- branch e checkout únicos, HEAD real, estado local e remoto, PR agregado (somente se de fato existente);
- claims vivos e owner, alterações staged/unstaged, arquivos, símbolos e contrato entre lanes;
- fases `NOT_STARTED / IN_PROGRESS / VERIFIED_UNIT / VERIFIED_NATIVE / BLOCKED / QUALIFIED`;
- comandos de teste efetivamente executados, PASS/FAIL/SKIP/exit, logs e bloqueios reais;
- uma próxima ação direta: arquivo/símbolo, teste RED e resultado esperado, implementação mais curta e regressão;
- as três metas finais e critérios, preservação humana/TaskRun, git index por integrador, economia 20/80;
- **esta mesma obrigação de gerar o próximo prompt integral em cada sessão incompleta**, sem reiniciar auditoria.
Não confundir escrita em arquivo com commit/push. Não inventar testes, E2E, CI, sessões ou sucesso.

**EXECUTE AGORA a fase 1; se terminar, avance.**

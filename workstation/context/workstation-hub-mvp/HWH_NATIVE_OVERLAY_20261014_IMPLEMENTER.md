# HWH-OVERLAY-01 — kit de correção da WebContentsView sobre a nova sessão

**Data do diagnóstico:** 2026-10-14. **Evidência:** dogfood do usuário: após retomar uma sessão com Browser nativo aberto no WhatsApp, clicar em **New session** deixa a página Chromium por cima da tela inicial da nova conversa. Reiniciar momentaneamente limpa o sintoma; nova tentativa reproduz. **A captura original não foi copiada para o repositório** porque expõe conversas/contatos privados.

**Base inspecionada via GitHub:** repo `kevynlucasprofissional-stack/hermes-agent`, branch única `feat/hermes-workstation-mvp-20261013`, código de produto no HEAD `ed7bf2eea585382cfc465b82df34f2c85b76dd93`. Ao preparar este kit, os docs novos avançaram a branch: **sempre verifique `git rev-parse HEAD` e rode `git fetch` + `git merge --ff-only` por integrador, nunca pressuponha esse HEAD como atual.** `main` não deve sofrer merge nessa tarefa.

## 1. Diagnóstico reproduzível e arquivos exatos

1. `apps/desktop/src/components/pane-shell/pane-visibility.ts` declara `PaneVisibleContext`, `usePaneVisible()`, `isElementInHiddenPane()`. O projeto já tem o contrato certo.
2. `apps/desktop/src/components/pane-shell/tree/renderer/keep-alive-panes.tsx` propaga `PaneVisibleContext value={placement.visible}` em host persistente, inclusive quando CSS marca `data-pane-hidden` e mantém **mesmo retângulo** da aba ativa; em `tree-group.tsx` idem.
3. `apps/desktop/src/app/chat/preview-tile.tsx`, `pane-mirror.ts`: a origem de preview `workstation-browser` pode ficar montada, mesmo quando sua sessão sai da árvore visível (`retainHiddenPreview`, `lifecycleKeepAlive`). Esse comportamento é intencional, para preservar estado.
4. **Causa principal confirmada no código:** `apps/desktop/src/app/chat/right-rail/workstation-browser-pane.tsx` não consome `usePaneVisible`. `publishBounds`/efeito de attach ligam `bridge.attach(bounds,'chat',preferredTaskId)` mesmo para pane mantida invisível. E `useNativeViewOcclusion(bridge,'chat')` assume `enabled=true`.
5. **Causa secundária confirmada no código:** `apps/desktop/src/app/browser/native-view-occlusion.ts` chama `setVisible(true,'chat')` no cleanup do hook quando não há modal. Isso pode reexibir o filho nativo durante transição ou desmontagem.
6. O processo Electron `apps/desktop/electron/workstation-browser-runtime.ts` adiciona o `WebContentsView` com `window.contentView.addChildView(view)` em `attach()`; esse filho **fica acima do React**, independente de `z-index`/CSS. `setVisible(false, expectedHost)` usa `removeChildView`, sem destruir `webContents`/perfil. **Não mover o Browser para outro renderer, não chamar `loadURL`, não fechar a view.**
7. Limite estrutural a verificar por E2E: `expectedHost='chat'` é compartilhado por várias panes do Chat. Se duas panes Browser forem alternadas, um callback atrasado da pane A pode tentar ocultar a pane B. O patch abaixo cobre o bug principal; se o teste A→B→A demonstrar esse conflito, implementar fencing por identidade de instância/host no contrato nativo antes de aprovar.

## 2. Material pronto — não recriar patch

| Arquivo | Uso |
| --- | --- |
| `workstation/context/workstation-hub-mvp/HWH_NATIVE_OVERLAY_01_RED_TESTS.patch` | Introduz **2 novos testes RED**: pane invisível não faz attach, volta ao mesmo viewport quando visível; unmount do hook não ressuscita child nativo. |
| `workstation/context/workstation-hub-mvp/HWH_NATIVE_OVERLAY_01_FIX.patch` | **Código já preparado** nos dois arquivos de produção: `usePaneVisible`, `isElementInHiddenPane`, `publishBounds` gated, reattach em reativação, `useNativeViewOcclusion({enabled:paneVisible})`, cleanup sem `setVisible(true)`. |
| `workstation/context/workstation-hub-mvp/HWH_NATIVE_OVERLAY_01.patch` | Patch integral alternativo (tests+fix). **Não aplicar depois dos dois acima**. |

São diffs baseados nos conteúdos **exatos** da branch em 2026-10-14, não trechos hipotéticos. `git apply --check` é a prova de compatibilidade com o checkout atualizado. Se divergir, localizar apenas hunk divergente, adaptar sem substituir implementações de outros agentes.

## 3. Operação única para o Antigravity

**Regra zero:** `AGENTS.md`, `workstation/AGENTS.md`, `workstation/context/AGENT_COLLABORATION_PROTOCOL.md`. Um checkout `C:\Github\hermes-agent`, uma branch, claims exclusivos; somente agente integrador manipula Git index/commits/push. H-079 mantém `PASS_WITH_AUTHORIZATION` limitado ao ciclo, sem dispensa de verificação/CI. Se outro agente reivindicou algum arquivo, **pare o patch desse arquivo**.

Execute na ordem, na raiz, pelo integrador designado:

```powershell
Set-Location 'C:\Github\hermes-agent'
git branch --show-current
git status -sb
python workstation/scripts/multi_agent_coordination.py status
# Confirme ausência de claims concorrentes e que NÃO há alterações suas nos 4 arquivos alvo.
git fetch origin feat/hermes-workstation-mvp-20261013
git merge --ff-only origin/feat/hermes-workstation-mvp-20261013

python workstation/scripts/multi_agent_coordination.py claim --agent agent-antigravity-overlay --lane hub-ui --paths apps/desktop/src/app/chat/right-rail/workstation-browser-pane.tsx apps/desktop/src/app/chat/right-rail/workstation-browser-pane.test.tsx apps/desktop/src/app/browser/native-view-occlusion.ts apps/desktop/src/app/browser/native-view-occlusion.test.ts --task 'HWH native Chromium overlay bug fix RED GREEN'

# RED (não avançar sem reproduzir ou documentar resultado exato)
git apply --check workstation/context/workstation-hub-mvp/HWH_NATIVE_OVERLAY_01_RED_TESTS.patch
git apply workstation/context/workstation-hub-mvp/HWH_NATIVE_OVERLAY_01_RED_TESTS.patch
Set-Location apps/desktop
npx vitest run --project ui src/app/browser/native-view-occlusion.test.ts src/app/chat/right-rail/workstation-browser-pane.test.tsx --reporter=dot
Set-Location ../..

# GREEN — somente depois de observar falha nos novos testes
git apply --check workstation/context/workstation-hub-mvp/HWH_NATIVE_OVERLAY_01_FIX.patch
git apply workstation/context/workstation-hub-mvp/HWH_NATIVE_OVERLAY_01_FIX.patch
Set-Location apps/desktop
npx vitest run --project ui src/app/browser/native-view-occlusion.test.ts src/app/chat/right-rail/workstation-browser-pane.test.tsx --reporter=dot
npx eslint src/app/browser/native-view-occlusion.ts src/app/browser/native-view-occlusion.test.ts src/app/chat/right-rail/workstation-browser-pane.tsx src/app/chat/right-rail/workstation-browser-pane.test.tsx --max-warnings=0
npx tsc -p . --noEmit --pretty false
Set-Location ../..
git diff --check -- apps/desktop/src/app/browser apps/desktop/src/app/chat/right-rail
```

**ATENÇÃO:** caso `git apply --check` falhe porque outro agente já alterou um trecho, não forçar `git reset`, `git checkout --`, `git clean` ou `stash`; inspecione os 4 arquivos-alvo e integre o mesmo contrato manualmente. Não tocar `workstation/dogfood/` (há notas/imagens locais não relacionadas).

## 4. Prova nativa obrigatória — reproduzir exatamente o bug do PDF

Reusar `apps/desktop/e2e/workstation-headless-load.spec.ts`, principalmente `nativeViewportSnapshot(fixture.app)`, `nativePageUrls(fixture.app)`, `createRealChat` e `openStoredSessionByTitle`; a suíte já sabe recuperar IDs/bounds reais via `fixture.app.evaluate(({BrowserWindow})=>...contentView.children)`. **Criar teste novo para o clique `New session`; os testes HWH-MVP anteriores não exercitam esta transição.**

Sequência mínima (testar no Electron real no mesmo processo, com página determinística do fixture local e um DOM modificável):

1. Criar/abrir sessão A com preview `workstation-browser` visível; navegar Browser Chromium a uma página de fixture com formulário e alterar o valor de um campo por interação humana; registrar `webContents.id`, URL e estado do campo.
2. Clicar no botão real `New session` do sidebar (padrão pronto em `createRealChat`). A tela inicial da nova sessão B deve ficar totalmente interativa.
3. Usando `nativeViewportSnapshot`, demonstrar que o `WebContentsView` de A **não está em `BrowserWindow.contentView.children`** enquanto B não apresenta Browser. Verificar de novo depois de um pequeno tempo (callback atrasado); repetir criar nova sessão C. Apenas capturar screenshot não prova isso.
4. Reabrir A sem reiniciar Electron; a página deve voltar com **o mesmo `webContents.id` e conteúdo de formulário**, sem recarregar `loadURL`; relatar também a captura visual. A identidade de WebContents **não deve** ser exigida através de um restart real do Electron.
5. Alternar A→B→A→B e em ambos os sentidos com duas sessões que tenham seus próprios previews Browser. As tentativas de `setVisible(false,'chat')` de uma pane oculta **não** podem esconder a pane agora ativa. Se falhar, é necessário fencing do owner da WebContentsView em runtime/preload, sem criar WebContentsView duplicada.
6. Confirmar modal/dropdown real oculta o Browser e fecha restaurando somente quando o host ativo o permite; Chat↔Hub e Creative↔Browser continuam funcionando.
7. Não alterar `409 USER_CONTROL_ACTIVE`, controle humano/agente, `BrowserTask`, sessão Gateway, `browser_navigate` (abertura rápida) ou perfil Chromium.

Comando inicial:

```powershell
Set-Location 'C:\Github\hermes-agent\apps\desktop'
npm run build
npx playwright test e2e/workstation-headless-load.spec.ts -g 'HWH-OVERLAY' --reporter=line
```

O Antigravity deve adicionar `test('HWH-OVERLAY: ...')` antes de executar o `-g`; não aceitar `No tests found` como aprovação. Executar também a regressão `-g 'HWH-MVP|HWH-OVERLAY'`. Se a página nativa ainda aparecer sobre B, investigar dois donos de `chat` e a ordem attach/setVisible; **não** mascarar com `z-index`, recarregamento ou `close()`.

## 5. Critério de encerramento e publicação

- RED comprovado antes do código GREEN; testes de unidade e tipos aprovados.
- Electron real: repetição A→New session→A e A→B→A, sem view órfã, sem mudança de identidade intra-processo, sem campos perdidos.
- Invariantes de isolamento: uma aba de sessão A não aparece em sessão B sem pin explícito; hosts inativos não roubam foco nem exibem view.
- `npm run build`, ESLint, typecheck e regressões relevantes verdes. Execução CI no **HEAD exato** publicada/qualificada onde exigido; relatar o que não foi executado.
- Integrador faz `git add` **somente nos arquivos alvo e no registro específico de testes**, revisa `git diff --cached --check`, `git commit`, `git push origin feat/hermes-workstation-mvp-20261013`; nunca merge na main.
- Atualizar jornal/STATE com causas, testes e HEAD, liberar claims e devolver relatório com evidências nativas; se interromper, um **RESUME PROMPT autossuficiente** com HEAD, arquivos editados, RED/GREEN, próximo teste, owner e proibição de repetir diagnóstico geral.

**Observação de confiança:** esta é uma análise causal sustentada pelo código publicado e pelo sintoma visual do PDF, não um teste de execução desse patch. O comportamento nativo só estará confirmado após o Antigravity executar a validação acima.

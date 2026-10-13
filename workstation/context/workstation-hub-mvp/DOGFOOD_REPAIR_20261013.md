# HWH-001 — correções de dogfood (13/10/2026)

Branch única: `feat/hermes-workstation-mvp-20261013`. Baseline antes dos ajustes: `7071f2d6ff`.
H-079: `PASS_WITH_AUTHORIZATION` **somente para esta branch**; upstream pelo maintainer antes do PR/merge, não é liberação de CI.

## Feedback de uso real e causas identificadas

1. Creative inicialmente pedia JSON e mostrava fundo preto: `CreativeWorkspacePage` não inicializava projeto, e `creative-workspace.css` não era importado pelo módulo. Corrigido: abre projeto vazio, aplica CSS e oferece importação local de imagem/vídeo/áudio para preview.
2. Browser + Creative pretos: `useNativeViewOcclusion` controla WebContentsView, e o retorno do Creative precisava reafirmar `attach(bounds,'hub')` **na WebContentsView existente**, após layout. A regressão React confirma `setVisible(true)`; a jornada Playwright Electron HWH-MVP confirma abertura/fechamento/alternância, mas **não mede pixels de uma página real**.
3. Aba Creative não fechava: agora existe botão acessível de fechar, que oculta a aba mantendo o componente React vivo (estado em memória enquanto Hub montado).
4. `browser_navigate` para WhatsApp em uma chamada: nenhuma alteração no caminho de navegação; preservar desempenho.
5. `Levar para sessão`: corrigidos **três** erros de integração:
   - removido fallback que fabricava sessão local se `session.create` falhasse (agora falha fechado);
   - preview do Browser pertence explicitamente ao **novo stored_session_id** em vez da conversa anterior;
   - BrowserTask é vinculado ao **runtime session_id**, com `taskId` também igual ao runtime session ID, porque a ferramenta `browser_*` do agente roteia pelo runtime session ID. Antes o código gerava um taskId aleatório, o que permitia o agente abrir uma outra aba.
   - nenhum `loadURL` ou novo `WebContentsView` foi introduzido por essas mudanças.

## Provas observadas

- TDD RED: 5 falhas iniciais nos testes de first-run, botão de fechar e falha/ownership de sessão.
- Vitest após correções: **84/84 PASS** em 5 arquivos, incluindo store de preview, Browser tab e occlusion.
- `npx eslint` em arquivos alterados: **0 warnings/errors**, após autofix dos arquivos próprios.
- Desktop renderer `tsc -p . --noEmit`: sem erros na primeira rodada; reexecutar após ajuste de runtime-vs-stored ID antes de publicar.
- `npm run build`: PASS. `npx playwright test e2e/workstation-headless-load.spec.ts -g HWH-MVP --reporter=line`: **1/1 PASS** em Electron real, inclusive teste com `preferredTaskId` vinculado ao session ID.
- CI remota em HEAD final: NOT_RUN.
- Teste nativo **usando o botão e o Gateway real**, em vez de chamar `bridge.adoptTab` diretamente: **NOT_VERIFIED**.

## Pendências de produto (não alegar concluídas)

- Asset shelf usa Blob URLs efêmeras; arquivos não são persistidos no documento canônico nem editáveis pelo Hermes. Interface declara esta limitação. Próximo passo: `asset.import` do backend com hash/proveniência e comando de Creative autorizado para humano/agente no mesmo documento.
- Criar UX real `Levar Creative para chat` com documento canônico e bridge de edição, não simples redirecionamento para chat vazio.
- E2E completo real `aba preenchida → botão → session.create real → mesma WebContentsView/mesmo DOM/inputs → release lease → primeira ação do agente na mesma tab`; verificar sessão estrangeira e efeitos incertos. A suíte Electron existente apenas testa a adoção via bridge, não via botão/Gateway real.
- Captura visual real da WebContentsView em páginas de navegação; teste atual prova presença de controles/identidade, não ausência de frame preto em todos os sistemas.

## Invariantes

Uma branch e um checkout. Não tocar nas notas modificadas em `workstation/dogfood/`. Sem merge na main. H-079 somente autorizado no desenvolvimento; CI, segurança e autoridade humanos não dispensadas.

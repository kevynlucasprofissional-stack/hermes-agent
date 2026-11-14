# Hermes Work — P06 | Homologação com AI Control e Chromium (28/10/2026)

**VEREDITO: NÃO DONE / RELEASE_HOLD.** Testes do núcleo isolado passaram; integração operacional ao Hermes Desktop aberto não existe. Não ativar P07 como se P06 tivesse sido concluído.

## Escopo, canal e segurança
- Sessão real do Hermes aberta no Windows `DESKTOP-3NA47UH`; `node apps/desktop/scripts/hermes-nav.mjs status` retornou `aiControl: true`, `activeTab: Sessions`, `backendStatus: desktop`, exit 0. Canal autenticado AI Control, sem automação de mouse/teclado.
- Leitura passiva pelo renderer: documento `Hermes`, aba Browser presente, **nenhum controle `Ativar monitoramento` detectado**. A UI atual não contém binding P06. Não navegar/alterar sessão existente.
- Plugin Windows Agent 02: identidade confirmada, healthy, mas seu único projeto aprovado é `p0-mcp-isolation-20261026-3e1a4935`; não concede autorização para editar o Hermes. O `Controle Windows` foi usado para consultas e suítes de testes autorizadas, nunca para input global.
- `CHATGPT.md` atual informa que o coordenador multiagente local foi **retirado em 28/10**; não rodar `multi_agent_coordination.py` inexistente. Não escrever arquivos com WIP de outros agentes.
- Git: `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`, dirty preexistente em `workstation-browser-runtime.ts`, docs e outros arquivos. Nenhum reset/stash/checkout/branch/commit/push.

## Provas executadas nesta sessão (não resultados históricos)

| Matriz | Comando | Resultado |
|---|---|---|
| P02+P04+P06 Python | `python -m pytest -q workstation/tests/test_page_watch_event_bridge.py workstation/tests/test_business_event_dispatch.py workstation/tests/test_business_event_outbox.py workstation/tests/test_trello_action_journal.py workstation/tests/test_trello_board_actions.py` | **70 PASS, exit 0** |
| Browser | `npm run test:desktop:platforms -- electron/workstation-browser-page-watch.test.ts electron/workstation-browser-dom-revision.test.ts electron/workstation-browser-task.test.ts electron/workstation-browser-session-state.test.ts` | **46 PASS, exit 0** |
| UI isolada | `npm run test:ui -- src/app/browser/page-watch-panel.test.tsx` | **3 PASS, exit 0** |
| Real Chromium, fixture `127.0.0.1` | `node .\\node_modules\\electron\\cli.js electron/fixtures/native-page-watch.cjs` | **PASS, exit 0**, Chromium `144.0.7559.236`, um evento, fingerprint sem texto, pausa após fechamento; logs GPU no encerramento, sem falha |
| ESLint | `npx eslint --quiet electron/workstation-browser-page-watch.ts electron/workstation-browser-page-watch.test.ts src/app/browser/page-watch-panel.tsx src/app/browser/page-watch-panel.test.tsx` | **exit 0** |
| TypeScript | `npm run typecheck` | **exit 0**, 67,23 segundos |
| AI Control | `node apps/desktop/scripts/hermes-nav.mjs status` e `eval.mjs` de metadados renderer | **exit 0**. `aiControl: true`; monitor P06 ausente na UI |

## Novo RED de qualidade: colisão de identidade após restart

Prova somente leitura de `PageWatchCoordinator` por esbuild+VM sob Node, sem editar repositório. Em **duas instâncias independentes** do monitor com mesma config e uma transição legítima `child_count 1 -> 2` cada, o `event_id` gerado foi **idêntico**:

`9c80127349a655db...` em ambas; `eventIdsEqual=true`, processo exit 0.

Causa: composição do ID por `config.id`, `tab_id`, `entry.epoch`, `sequence`, contagens e fingerprint; `epoch` e `sequence` reinicializam in-memory. Duas ocorrências reais diferentes após restart podem receber a mesma identidade; a unicidade downstream `(source,event_id,route_id)` suprime indevidamente a segunda. Não corrigir gerando UUID aleatório por observação: a identidade deve nascer de uma fonte/ledger durável idempotente ou estado de sequência monotônica autoritativa, com fence do perfil e reinicialização segura.

## Gate de integração: resultado negativo, com evidências

Busca `rg 'PageWatchPanel|PageWatchCoordinator|page_watch_outbox_gate|buildPageWatchProbe' apps/desktop/src/app/browser/index.tsx apps/desktop/electron/workstation-browser-runtime.ts apps/desktop/electron/workstation-browser-ipc.ts workstation/business_event_dispatch.py` -> **nenhuma referência (rg exit 1)**. Os módulos P06 só aparecem em seus próprios arquivos, fixtures e testes. Assim:

1. **UI não montada e IPC não criado**. Usuário não pode clicar `Ativar monitoramento` no Hermes real.
2. **BrowserTask/lease não integrados**. Testes de logout, human takeover, navegação, aba fechada, renderer crash são de coordinator/fixture, não hooks efetivos em `workstation-browser-runtime.ts`; não há prova de cancelamento após logout real.
3. **Store não instalada no perfil canônico**, só fixture temporária. Config pode persistir na abstração, mas não está habilitada no produto. Nenhum observer continua ao fechar aba.
4. **P04 não autoriza `source=page_watch`**; `page_watch_outbox_gate` retorna `P04_PAGE_WATCH_SOURCE_NOT_QUALIFIED` e não escreve na outbox. Nenhuma entrega real ao Cron/Bot foi testada nem deveria ser permitida.
5. **P02/P04 release gates ainda abertos** (docs P02: Trello API LIVE NOT TESTED; P04: LIVE_DISPATCH_NOT_TESTED). Sem qualified outbox/receipts, não há DONE E2E.
6. **Stage A e revisão de WIP** em runtime Browser/IPC/UI continuam necessários. Não editar essas superfícies a partir deste teste sem reconciliar o trabalho concorrente.

## Critérios que precisam passar antes de DONE
- Consertar identidade durável com testes RED/GREEN de restart, replay e duas alterações legítimas idênticas em momentos distintos, preservando `source+event_id+route_id` idempotente.
- Qualificar source/rule `page_watch` no P04 com rota por perfil, projeção segura, persistência e reconciliação de efeitos incertos; nenhum bypass por `source=trello`.
- Integrar storage de config por perfil; montar painel via Browser IPC tipado com owner/lease e gate de autorização do backend; um observer por aba/origem.
- Testar na Workstation real, usando página fixture em aba explicitamente autorizada: ativar, mudar contagem, ver um evento no journal/outbox, confirmar pausa/reativação, testar login/logout, takeover humano, navegação cross-origin, SPA, fechamento e restart. Provar ausência de efeitos após revogação.
- Sem envio WhatsApp, sem leitura de conteúdo privado, sem LLM por mutação, sem alterar TaskRun.

## Decisão
P06 está **LOCAL_TESTS_GREEN / NATIVE_FIXTURE_GREEN / REAL_UI_NOT_MOUNTED / OUTBOX_HOLD / RESTART_ID_BUG / NOT_DONE**.

Pode-se estudar/planejar P07 de forma independente, mas é incorreto dar P06 como DONE ou habilitar monitoramento real antes da integração e nova homologação. Este arquivo é novo; os canônicos reservados/dirty não foram sobrescritos.

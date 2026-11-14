# Prompt 06 — Handoff para owner documental e integrador (2026-10-27)

**RESULTADO COMPROVADO:** `P06 ISOLATED_PROTOTYPE_GREEN / NATIVE_CHROMIUM_FIXTURE_PASS / GUI_AND_P04_LIVE_HOLD / RELEASE_HOLD`. Registro integral e evidências: `workstation/context/PAGE_WATCH_P06_20261027.md`.

**Preflight essencial:** P02 (`chatgpt-trello-incremental-p02`) e P04 (`chatgpt-business-outbox-p04`) estão `READY_FOR_INTEGRATION`, não qualificados produtivamente. `AuthorizedBusinessRoute` P04 aceita somente `source=trello`; eventos `page_watch` devem permanecer em `HOLD`, nunca disfarçados como ações Trello. Docs canônicos `ROADMAP`, `HERMES_WORKSTATION_INTELLIGENCE`, `engineering-journal/CURRENT` e `KNOWN_ISSUES` sob claim ACTIVE de `chatgpt-whatsapp-m3`; inserir pelo owner, sem sobrescrever WIP. Integrador de commit não designado.

## Inserção sugerida para workstation/ROADMAP.md

`HW-IMP-06 PROTOTYPE_LOCAL_IMPLEMENTED / 46 BROWSER_REGRESSION_PASS / 3 UI_PASS / 12 OUTBOX_GUARD_PASS / NATIVE_CHROMIUM_FIXTURE_PASS / LIVE_BROWSER_INTEGRATION_HOLD / RELEASE_HOLD`. Motor `PageWatchConfig` por sessão/aba/origem/selector/regra/rota e estado `enabled`; somente presença e contagem estrutural; fingerprint e `page_changed` sem texto; debounce e limite de polling; pausas e teardown; store de arquivo atômico num caminho de perfil fornecido (não instalada na config canônica real). Painel UI protótipo não montado em `BrowserView`. Ligação com P04 é guard `HOLD`, não dispatch, por falta de source autorizada. Nenhum site real monitorado, nenhuma chamada LLM, WhatsApp ou Cron externo.

## Inserção sugerida para workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md

Monitoramento de página não é captura de conteúdo: somente `presence`/`child_count` em seletor autorizado, com teto 1000 e proteções contra inputs/iframe/senhas/chat. `page_changed` tem `source=page_watch`, IDs estáveis SHA-256 por transição ativa, fingerprint SHA256 de metadados, origin e contagens, não texto ou valores. Um único observador por tab/origin, independente de `workstation-browser-dom-revision` e `workstation-learning-dom`. Config pode persistir mas observador/TaskRun não persiste após fechamento ou restart. Evento externo não concede TaskRun authority. O P04 precisa permitir explicitamente source/route page_watch em contrato futuro; hoje apenas Trello. Nenhum evento de P06 pode invocar job sem gate.

## Inserção sugerida para workstation/context/engineering-journal/CURRENT.md

- Git `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`; dirty preexistente em Browser runtime, Docs e work do M3 preservado. Claim `chatgpt-page-watch-p06` lane `p06-page-watch-isolated` sobre nove caminhos novos. Sem branch/worktree/commit/push.
- TDD RED: `npm run test:desktop:platforms -- electron/workstation-browser-page-watch.test.ts` -> module missing, exit 1. GREEN: 16 P06 tests PASS. Browser regression 46 PASS exit 0 (`page-watch`, `dom-revision`, `browser-task`, `browser-session-state`). UI `npm run test:ui -- src/app/browser/page-watch-panel.test.tsx` -> 3 PASS exit 0. Python bridge `python -m pytest -q workstation/tests/test_page_watch_event_bridge.py` -> 12 PASS exit 0; compileall exit 0.
- Native Chromium `node .\\node_modules\\electron\\cli.js electron/fixtures/native-page-watch.cjs` em `apps/desktop`: real Electron/Chromium 144.0.7559.236 em `127.0.0.1`, uma transição estrutural, event ID SHA256, clock repaint ignorado, auth_required pausa, observer disconnect, tab_closed pausa, exit 0. Erro inicial de harness (URL ausente no VM) corrigido sem mudança de runtime produtivo.
- `npm run typecheck` Desktop exit 0. ESLint --quiet arquivos novos exit 0; --fix limitado aos quatro arquivos P06. Sem CI release, sem Stage A qualificado, sem IPC/GUI montados ou P04 live.
- `page_watch_event_bridge.py` rejeita a entrega para outbox com `P04_PAGE_WATCH_SOURCE_NOT_QUALIFIED`. Nem banco canônico nem config real foram alterados.

## Inserção sugerida para Known Issues

`HW-P06-01`: P02/P04 prod gates não concluídos, fonte P04 page_watch ausente, portanto dispatch/HERMES job sempre HOLD.
`HW-P06-02`: painel não conectado a BrowserView/IPC; Browser runtime WIP alheio e Stage A impedem integração.
`HW-P06-03`: lifecycle real BrowserTask/human-control/logout/renderer crash ainda não instalado; simulação/nativo fixture não qualificam páginas arbitrárias.
`HW-P06-04`: persistência de config só em file adapter isolado; política/perfil store canônico precisa integração/autorização; nada monitora com aba fechada. Nunca fazer silent rearm após restart.
`HW-P06-05`: mudanças em DOM virtualizado/texto com contagem igual ficam invisíveis; segurança deliberada, sem conteúdo sensível.
`HW-P06-06`: somente mundo de teste; integrar em Electron isolated world, verificar origem/owner/lease em cada amostra, storage e outbox metadata via política já aprovada.
`HW-P06-07`: sem monitor de background nem WhatsApp ou Google logado arbitrário. Não é requisito do primeiro incremento.

## Diffs por arquivo (todos NOVOS e untracked)

- `apps/desktop/electron/workstation-browser-page-watch.ts`: configuração, store, script de observação, script de disconnect, coordinator e prova de proveniência.
- `apps/desktop/electron/workstation-browser-page-watch.test.ts`: 16 testes de admissões/lifecycle/proveniência/restarts.
- `apps/desktop/electron/fixtures/native-page-watch.cjs`: prova native Chromium.
- `apps/desktop/src/app/browser/page-watch-panel.tsx`: botões/status/alerta, desabilitado por gate; não montado.
- `apps/desktop/src/app/browser/page-watch-panel.test.tsx`: 3 testes.
- `workstation/page_watch_event_bridge.py`: guard source/rule (sem outbox write).
- `workstation/tests/test_page_watch_event_bridge.py`: 12 testes.
- `workstation/context/PAGE_WATCH_P06_20261027.md`: documentação operacional.
- Este handoff.

## Próximos gates e reversão

Gate explícito antes de novos edits: qualificar P02/P04 + política para `source=page_watch`; upstream pin/Stage A da superfície Browser e claims exclusivos de runtime/IPC/BrowserView; escolher armazenamento canônico do perfil, integrar callbacks de cancelamento/owner, renderizar painel com bridge tipada; qualificar emissão no Hermes Desktop real com outbox idempotente e recibos independentes. Não fazer neste patch, dado o contrato do prompt.

Sem migration executada; para reverter, integrador autorizado pode retirar os nove novos arquivos após revisar claims. WIP alheio permanece intacto. Não há ativação automática/monitoramento em produção.

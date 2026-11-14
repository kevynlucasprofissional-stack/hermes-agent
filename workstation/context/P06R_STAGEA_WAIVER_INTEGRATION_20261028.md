# Hermes Work — P06-R com waiver Stage A: integração local e homologação (28/10/2026)

**STATUS: IMPLEMENTAÇÃO LOCAL INTEGRADA / FIXTURE CHROMIUM E P04 GREEN / LIVE HERMES DESKTOP NOT QUALIFIED / RELEASE HOLD.**

## A. Autorizações e estado Git

- Usuário dispensou explicitamente **Stage A somente nesta sessão** para correções P06-R. Não transfere ownership de arquivos e não equivale a release/CI. `AGENTS.md` e `CHATGPT.md` lidos; script de claims foi descontinuado e não foi executado.
- Branch inicial/final `main`, HEAD `f1d5ab2f030e940ed4571371b0de45a21a009c9e`. Checkout já tinha muitas alterações WIP, incluindo `apps/desktop/electron/workstation-browser-runtime.ts` (preservado sem edição), `workstation/ROADMAP.md`, Intelligence/Journal e Python P02/P04 untracked. Nenhum branch, worktree, reset, stash, clean, commit ou push; integrador de commit não definido.
- Agent 02 MCP: healthy, mas projeto registrado nele corresponde a isolamento MCP, não ao Hermes; nenhum claim novo presumido. Controle Windows usado para execução de testes e edições autorizadas. A UI do Hermes foi navegada unicamente por AI Control autenticado, sem usar input global; aba Sessions restaurada ao final.

## B. Diffs e contrato implementado

- `apps/desktop/electron/workstation-browser-page-watch.ts` (P06 original, atualizado): reserva assíncrona `reserveEventId` integrada ao `PageWatchCoordinator`, nonce por ativação (NÃO UUID por evento), pós-reserva com fence contra epoch/sequence alterados, evita dupla emissão por probes concorrentes, debounce e observador isolado preservados. A identidade produtiva vem do ledger.
- `apps/desktop/electron/workstation-browser-page-watch-ledger.ts` NOVO: `node:sqlite` sobre caminho **canônico Kanban** (pin `HERMES_KANBAN_DB` quando presente, ou root Hermes default), duas tabelas aditivas `page_watch_sequence` e `page_watch_occurrence`; `BEGIN IMMEDIATE`, chave `(watch_id,activation_key,observation_key)` e sequência monotônica. Replay devolve o mesmo event_id; transições legítimas repetidas em nova ativação recebem ID distinto. `PENDING` persiste após crash, sem autorizar retry de efeitos Cron.
- `apps/desktop/electron/workstation-browser-page-watch-service.ts` NOVO: serviço do Electron sobre APIs públicas `getWorkstationBrowserRuntime().state/getWebContents`, sem editar runtime WIP; configuração por perfil salva ao lado do perfil Chromium; valida aba ativa/sessão/origem/lease, exige **HTTP loopback** (127.0.0.1/localhost) neste MVP, seleciona regra `child_count` e seletor restrito, inicia reconciliação limitada, cancela após navegação principal, render-process-gone, fechamento, pausa/takeover e perda de autoridade. Nenhum watcher é restaurado automaticamente.
- `apps/desktop/electron/workstation-browser-ipc.ts` ALTERADO: handlers `page-watch:status/enable/pause`, validados contra remetente principal, owning host window e aba ativa, mais fences diretos em `close-tab` e `take-control`.
- `apps/desktop/electron/preload.ts` ALTERADO: bridge tipada de Page Watch.
- `apps/desktop/src/app/browser/types.ts` ALTERADO: tipos da bridge; `apps/desktop/src/app/browser/index.tsx` ALTERADO: seletor e `PageWatchPanel` montado na Browser Hub, status consultado do backend, botões habilitados apenas por retorno de autorização no main process, erro local de UI. O componente P06 anterior é reaproveitado.
- `workstation/business_event_dispatch.py` (P04 untracked, atualizado): `AuthorizedBusinessRoute` aceita agora fonte `page_watch` somente para origin **exata e loopback** e evento `page_changed`, `board_id=page_watch`, delivery local; aceita apenas ocorrência já confirmada na tabela canônica e preserva gates do P04. Trello não foi disfarçado.
- `workstation/page_watch_event_bridge.py` (P06 untracked, atualizado): comando one-shot de evento autorizado que carrega rotas `business_events.routes` do `config.yaml` do perfil, reserva na outbox P04 e invoca somente o executor Cron P04 existente se configuração local confiável permitir. Nunca cria novo scheduler; eventos sem rota retornam HOLD. Estado `UNCERTAIN` continua conservador após chamada ao Cron.
- `apps/desktop/electron/workstation-browser-page-watch-restart.test.ts` P06-R RED convertido a GREEN; novo teste de concorrência simultânea.
- `apps/desktop/electron/workstation-browser-page-watch-ledger.test.ts`, `apps/desktop/electron/fixtures/native-page-watch-service.cjs`, `workstation/tests/test_page_watch_authorized_dispatch.py` NOVOS: testes de sequenciador, prova nativa Chromium com SQLite/P04 e política de rota.
- Referência Python transacional anterior em `workstation/context/p06r-reference/` continua somente como referência, não é executada em produção.
- **Não** alteramos `workstation-browser-runtime.ts` nem dados de tarefas, mensagens, credenciais ou áudio.

## C. Evidência de RED/GREEN e comandos

**RED anterior:** `npm run test:desktop:platforms -- electron/workstation-browser-page-watch-restart.test.ts` (1 FAIL / 1 PASS, exit 1) reproduziu colisão entre transições 1→2 após duas ativações diferentes. Corrigido o motor e o sequenciador. Um segundo RED adversarial: dois probes simultâneos em mesma reserva emitiam dois eventos; fence pós-reserva corrigiu, teste passou.

**GREEN local final:**
- `npm run test:desktop:platforms -- electron/workstation-browser-page-watch-restart.test.ts electron/workstation-browser-page-watch-ledger.test.ts electron/workstation-browser-page-watch.test.ts` → **22 PASS, exit 0**, incluindo concorrência/replay/identidade.
- `npm run test:desktop:platforms -- electron/workstation-browser-page-watch-restart.test.ts electron/workstation-browser-page-watch-ledger.test.ts electron/workstation-browser-page-watch.test.ts electron/workstation-browser-dom-revision.test.ts electron/workstation-browser-task.test.ts electron/workstation-browser-session-state.test.ts` → **53 PASS, exit 0** antes do teste de concorrência extra; foco revisado 22 PASS depois.
- `python -m pytest -q workstation/tests/test_page_watch_authorized_dispatch.py workstation/tests/test_page_watch_event_bridge.py workstation/tests/test_business_event_dispatch.py workstation/tests/test_business_event_outbox.py workstation/tests/test_trello_action_journal.py workstation/tests/test_trello_board_actions.py` → **76 PASS, exit 0**.
- `npm run test:ui -- src/app/browser/page-watch-panel.test.tsx` → **3 PASS, exit 0**.
- `npx eslint --quiet` em novos/alterados P06 TS/TSX → **exit 0**.
- `npx tsc -p tsconfig.electron.json --noEmit` → **exit 0**.
- `npx tsc -p tsconfig.json --noEmit` → **exit 2**, seis erros em `workstation-browser-runtime.ts` (linhas 3669, 3760) e `workstation-learning-session.ts` (431,437,448,461), de WIP externo ao P06; não foram alterados nesta missão. Full typecheck **não GREEN**.
- Referência Python isolada `python -m pytest -q workstation/context/p06r-reference/test_sequence_ledger.py` → 9 PASS, exit 0.

## D. Prova Chromium REAL e outbox P04

**Cenário local sem rota autorizada:**
`node .\\node_modules\\electron\\cli.js electron/fixtures/native-page-watch-service.cjs` em `apps/desktop` → **exit 0**, `Chromium 144.0.7559.236`, um evento estrutural, horário/clock apenas texto ignorado, config salva em perfil temporário, registro SQLite `PENDING`, pausa e teardown, `p04State=UNCONFIGURED`, zero ações externas.

**Cenário com rota habilitada, fixture loopback e job inexistente:**
`$env:P06_FIXTURE_AUTHORIZED='1'; node .\\node_modules\\electron\\cli.js electron/fixtures/native-page-watch-service.cjs` → **exit 0**, 1 evento, `p04State=FAILED_SAFE` gravado na outbox canônica, nenhum Cron real executado, nenhuma LLM. Foi necessário corrigir a fixture que criava tabela `tasks(id)` falsa incompatível com o Kanban canônico. Depois, Python P04 inicializa o schema real e a prova passou.

**Atenção:** comprova Chromium real + serviço do Electron + CLI P04 + SQLite temporário, **não** prova interface do Hermes já aberto nem envio/entrega produtiva. P04 com execução local mock retorna `UNCERTAIN` corretamente em testes. Não houve WhatsApp, Google AI Studio, leitura de conversa, CDP externo ou capture de conteúdo privado.

## E. Verificação UI por AI Control

`node apps/desktop/scripts/hermes-nav.mjs status`: `aiControl: true`, backend `desktop`. Foi aberta a aba Browser por click interno à ponte AI Control, sem mouse global; via `goto workstation` o renderer mostrou hash `#/browser`. **A instância já aberta continua com o preload anterior:** `typeof window.hermesDesktop?.workstationBrowser?.pageWatchEnable === 'undefined'`, controle Ativar monitoramento ausente. Não houve reinicialização para não romper sessão e BrowserTask com estado possivelmente incerto. A aba Sessions original foi restaurada.

**Isso impede DONE de produto nesta sessão**. Requer inicializar versão recompilada em ambiente limpo ou reiniciar o Hermes de forma controlada após reconciliação de BrowserTask, verificar que bridge + painel estão carregados e repetir E2E via AI Control. Não forçar hot-injection, CDP externo ou restart sem segurança.

## F. Limites/risco residual

- Somente loopback de fixture no MVP, por política explícita: não monitora arbitrariamente Trello/WhatsApp reais; isso pertence a gate de autorização posterior. Nenhuma leitura de texto/valores/cookies.
- Perda de navegador/lease cancela polling; listeners diretos para navegação, crash, close, takeover IPC e verificação periódica de estado. Hooks ausentes fora desses eventos ainda precisam de E2E contra Hermes integrado.
- Identidade garantida no nível de aceitação SQLite, não exactly-once de efeito externo; `PENDING` após crash exige reconciliação, `UNCERTAIN` sem receipt nunca vira `DELIVERED` por presunção.
- P02 Trello live continua não qualificado; waiver Stage A não o qualifica.
- Depuração encontrou SQLite Python 3.50.4 com warning de vulnerabilidade WAL-reset; conector Kanban do Hermes faz fallback para journal DELETE. Antes de release, atualizar versão conforme orientação do próprio runtime e qualificar compatibilidade com `node:sqlite`, sem mudar DB produtivo nesta sessão.
- Source P04 no checkout é untracked: integração ao repositório precisa owner designado antes de release; sem commit/push.
- A configuração de perfil de Page Watch persiste; observador ativo não é restaurado após restart. O fechamento da aba elimina observação, sem background capture.
- O app atual ainda não carregou o novo preload e o typecheck global tem seis erros em WIP externo; não declarar DONE/RELEASE.

## G. Handoff documental

Inserções sugeridas ao owner dos canônicos:
- `ROADMAP.md`: P06-R source/IPC/UI+SQLite local implementado e NATIVE_CHROMIUM/P04 fixture green; LIVE_UI_HOLD, renderer typecheck baseline RED, P02 live HOLD.
- `HERMES_WORKSTATION_INTELLIGENCE.md`: watch por aba/fixture, sem conteúdo privado, fingerprint/event id por ocorrência SQLite e P04 route trusted config, nenhum LLM por mutação.
- `engineering-journal/CURRENT.md`: registrar waiver de Stage A específico de 28/10, comandos/exits acima, cinco frentes de integração sem takeover de mouse, antiduplo concorrente, P04 FAILED_SAFE.
- `KNOWN_ISSUES.md`: P06-R-UI-01 preload da sessão existente stale; P06-R-CI-02 typecheck 6 erros de outras frentes; P06-R-PROD-03 P02/P04 live qualificação não comprovada; P06-R-SQLITE-04 python sqlite warning cross-process; P06-R-BROWSER-05 testes de lifecycle dentro do Hermes UI pendentes.

**Veredito: PARTIAL — código e prova nativa integrados, mas UI ativa e release não homologados.** O trabalho do P07 só pode começar independentemente ou quando esse gate operacional for fechado; não declarar DONE por simulação.

## H. Verificações finais adicionais — gates após correção de concorrência/lifecycle

- Concluído o fence pós-reserva: teste adversarial de dois probes simultâneos inicialmente RED (dupla emissão), agora GREEN. Comando `npm run test:desktop:platforms -- electron/workstation-browser-page-watch-restart.test.ts electron/workstation-browser-page-watch-ledger.test.ts electron/workstation-browser-page-watch.test.ts electron/workstation-browser-dom-revision.test.ts electron/workstation-browser-task.test.ts electron/workstation-browser-session-state.test.ts` → **54 PASS, exit 0**.
- `npm run test:ui -- src/app/browser/page-watch-panel.test.tsx` → **3 PASS, exit 0**.
- `python -m pytest -q workstation/tests/test_page_watch_authorized_dispatch.py workstation/tests/test_page_watch_event_bridge.py workstation/tests/test_business_event_dispatch.py workstation/tests/test_business_event_outbox.py workstation/tests/test_trello_action_journal.py workstation/tests/test_trello_board_actions.py` → **76 PASS, exit 0**.
- `npx eslint --quiet` dos arquivos TS/TSX P06 novos e alterados → **exit 0**. `npx tsc -p tsconfig.electron.json --noEmit` → **exit 0**.
- `npx tsc -p tsconfig.json --noEmit` → **exit 2**, 6 falhas em WIP externo `workstation-browser-runtime.ts` e `workstation-learning-session.ts`. Esses arquivos não foram editados.
- Removido efeito colateral de leitura: `pageWatchUiState` deixou de abrir SQLite e criar/migrar tabelas somente para renderizar status; migração ocorre ao ativar monitor.
- `emitAuthorizedP04` agora exige reconciliação de tab, sessão, origem, lease/human control e watch ativo **na fronteira de dispatch**; não depende apenas de poll a cada 500 ms.
- Teste nativo ampliado com `P06_FIXTURE_AUTHORIZED=1`: Chromium 144.0.7559.236, `events=1`, `configPersisted=true`, `humanTakeoverRevokes=true`, `navigationRevokes=true`, `p04State=FAILED_SAFE`, `externalCalls=0`, **exit 0**.
- Mesmo teste sem `P06_FIXTURE_AUTHORIZED`: `events=1`, takeover e navegação revogados, `p04State=UNCONFIGURED`, **exit 0**. O E2E usa estado BrowserTask de fixture com WebContents Chromium real; não substitui validação na instância Hermes já aberta.
- AI Control no Hermes aberto retornou `ready=true`, **1 aba de Browser, 2 BrowserTasks**, `paused=false`, sem lease humano; a aplicação carregada continua sem método `pageWatchEnable` no preload. Reiniciar em presença de tarefas potencialmente ativas seria interruptivo e não foi feito. Aba Sessions foi restaurada pelo AI Control sem movimento de mouse.
- A prova do P04 autorizou exclusivamente um job local propositalmente inexistente e obteve `FAILED_SAFE`, não houve execução real de Cron. Config/DB da prova nativa em diretórios TEMP; nenhum acesso aos conteúdos de WhatsApp/Trello.

**Conclusão final de aceite:** `PARTIAL / LOCAL_CODE_INTEGRATED / TRANSACTIONAL_ID_FIXED / CHROMIUM_REAL_FIXTURE_GREEN / LIVE_UI_GATE_OPEN / GLOBAL_TSC_RED / NOT_DONE`. P07 pode começar só se independente da conclusão operacional do P06; não declarar P06 DONE nem RELEASE por teste de fixture.

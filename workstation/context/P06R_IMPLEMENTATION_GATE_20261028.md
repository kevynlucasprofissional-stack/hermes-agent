# P06-R — Auditoria, reprodução RED e referência transacional GREEN (28/10/2026)

**VEREDITO: PARTIAL / INTEGRATION_BLOCKED / NOT_DONE / RELEASE_HOLD.** Implementação de referência transacional aprovada; motor produtivo e interface reais não foram alterados.

## 1. Preflight e autoridade

- Repositório: `C:\Github\hermes-agent`, branch `main`, HEAD inicial/final `f1d5ab2f030e940ed4571371b0de45a21a009c9e`. Checkout compartilhado com dezenas de modificações existentes, incluindo `apps/desktop/electron/workstation-browser-runtime.ts`, BrowserTask tests, P02/P04, docs canônicos.
- `AGENTS.md`, `CHATGPT.md`, `workstation/context/README.md`, `workstation/context/DEVELOPMENT_GATES.md` e `UPSTREAM_FIRST_CHANGE_GATE_2026-09-20.md` consultados. Coordenador P0/P1/P2 de claims foi retirado em 28/10; não invocá-lo. `AGENTS.md` exige Stage A upstream-aligned qualificado **antes de editar downstream runtime**; `workstation/context/BROWSER_BATCH_P01_HOLD_HANDOFF_20261028.md` reporta Stage A não comprovado no mesmo HEAD. Não existe waiver P06 documentado no material inspecionado; waiver anterior WA-M3 é específico e não transfere autoridade.
- `Windows - Agent 02` conectado com `agent_id=d1b485d3-c8b3-4093-ae16-4ecdad34c155`, health `mcp_ready=true` e `managed_writes=true`, mas só tem projeto autorizado `p0-mcp-isolation-20261026-3e1a4935`, **não o Hermes**. Não usar esse projeto para fingir claim do checkout Hermes. Nenhum integrador de commit nomeado.
- AI Control: `node apps/desktop/scripts/hermes-nav.mjs status` → `aiControl=true`, backend `desktop`, exit 0; `eval.mjs` de leitura indica **0 controles** de `Ativar monitoramento` na UI. Nenhum mouse/teclado global, CDP externo, restart, mensagem WhatsApp, form submission ou ação externa.

## 2. Trace e falha comprovada

`workstation-browser-page-watch.ts::PageWatchCoordinator.probeOnce` gera `event_id = SHA256([watch_id,tab_id,epoch,sequence,previous,current,fingerprint])`. `epoch` e `sequence` são voláteis por instância e reiniciam quando `PageWatchCoordinator` é reconstruído. Duas ocorrências `1→2`, em ativações diferentes, podem ter o mesmo ID. Essa identidade colide na política `UNIQUE(source,event_id,route_id)` do P04.

Novo teste permanente RED em `apps/desktop/electron/workstation-browser-page-watch-restart.test.ts`:
```powershell
cd C:\Github\hermes-agent\apps\desktop
npm run test:desktop:platforms -- electron/workstation-browser-page-watch-restart.test.ts
# 1 PASS, 1 FAIL (esperado): two legitimate transitions after restart need distinct event_ids
# P06R_RED_EXIT=1
```
A falha não é uma simulação de sucesso. O outro teste confirma que probe duplicado de uma mesma transição não emite outro evento.

## 3. GREEN de referência, **não promoção ao runtime**

Arquivos NOVOS (sem editar módulo produtivo, Browser runtime, IPC, preload, UI ou P04):
- `workstation/context/p06r-reference/sequence_ledger.py` — referência Python/SQLite usando **conexão fornecida por autoridade**, schema aditivo, `BEGIN IMMEDIATE`, contador monotônico `watch_id`, chave de ocorrência `(watch_id, activation_key, observation_key)`, id SHA256 de identidade/seq, `PENDING` após commit e API de readback. Nenhum banco real criado. Esse schema de referência **não foi migrado no Hermes**.
- `workstation/context/p06r-reference/test_sequence_ledger.py` — 9 testes: replay estável, duas transições iguais após restart com IDs distintos, sequência crescente, concorrência do mesmo evento, concorrência de eventos diferentes, crash após commit, colisão de payload, validação de identidade e preservação da tabela canônica `tasks`.
- `apps/desktop/electron/workstation-browser-page-watch-restart.test.ts` — RED contra implementação atual.
- Este relatório, sem sobrescrever docs existentes.

```powershell
cd C:\Github\hermes-agent
python -m pytest -q workstation/context/p06r-reference/test_sequence_ledger.py
# 9 passed, P06R_REFERENCE_GREEN_EXIT=0
python -m pytest -q workstation/tests/test_page_watch_event_bridge.py workstation/tests/test_business_event_dispatch.py workstation/tests/test_business_event_outbox.py
# 41 passed, P06R_P04_REFERENCE_REGRESSION_EXIT=0
```

**Limite essencial:** a referência exige `activation_key` e `observation_key` derivadas de identidade causal confiável do host/BrowserTask, não aceitas de DOM arbitrário. Não confundir hash de contagem, timestamp, UUID aleatório ou `MutationObserver` volátil com identificador de ocorrência. Um registro `PENDING` após crash permite reconciliação de aceitação, **não autoriza replay cego do efeito Cron**. O método `ack_outbox` na referência contém apenas uma flag de recibo injetada pelo teste; a integração deve substituí-la por **readback P04 verificado independentemente** antes de reconhecer admissão. Não usar o booleano como prova produtiva.

## 4. Regressão nativa e interface

```powershell
cd C:\Github\hermes-agent\apps\desktop
npm run test:desktop:platforms -- electron/workstation-browser-page-watch.test.ts electron/workstation-browser-dom-revision.test.ts electron/workstation-browser-task.test.ts electron/workstation-browser-session-state.test.ts
# 46 PASS, exit 0
npm run test:ui -- src/app/browser/page-watch-panel.test.tsx
# 3 PASS, exit 0
node .\\node_modules\\electron\\cli.js electron/fixtures/native-page-watch.cjs
# Chromium 144.0.7559.236, um evento, sem texto privado, pausa após tab_closed, exit 0
npm run typecheck
# exit 0
npx eslint --quiet electron/workstation-browser-page-watch-restart.test.ts
# exit 0 após --fix limitado ao arquivo novo
```

O teste nativo foi em **fixture localhost** separada, não na aba real do Hermes. Via AI Control só houve inspeção; nenhuma UI de monitoramento aparece no renderer atual. BrowserTask lifecycle e UI/IPC não estão integrados (busca de refs de `PageWatchCoordinator`/`PageWatchPanel` no runtime/IPC/UI retornou sem resultados na homologação anterior). Não há E2E de acionamento, pausa, reinício, logout/takeover real nem entrega P04/contatos.

## 5. Integração posterior — mudanças que exigem Stage A e ownership

1. Qualificar Stage A exato ou obter waiver **específico e documentado** do P06-R, com trilha dos owners documentais. Não herdar waiver WA-M3.
2. Reconciliar diretamente o WIP atual do owner Browser runtime antes de qualquer edição. Alterar só depois os módulos `workstation-browser-runtime.ts`, `workstation-browser-ipc.ts`, `preload.ts`, `src/app/browser/types.ts` e `src/app/browser/index.tsx` com contrato tipado e check backend `BrowserTask owner/lease/session/tab/origin`; sem input global.
3. Inserir sequenciador de ocorrência **no mesmo SQLite autorizado de controle do P04**, ou no storage canônico explicitamente aprovado. Gerar `activation_key` somente da identidade do host (BrowserTask/session/document lifecycle) e `observation_key` apenas de revisão causal reconciliável; confirmar consistência após reload/restart e não presumir que DOM virtualizado expõe causalidade suficiente. Reserva/dedup transacional antes do publish; falha após persistência -> registro pendente, não duplicata.
4. Criar autorização explícita de `source=page_watch` com rota P04 existente em config de perfil confiável. Ajustar `AuthorizedBusinessRoute` e `dispatch_pending` preservando `source=trello` e gates de P04; **não** converter page_watch em Trello nem contornar allowlist. Para P04 os estados `CLAIMED`/`UNCERTAIN` não provam efeito entregue. Se receipt indep. faltar, nunca atribuir `DELIVERED`.
5. Configurar `PageWatchConfigStore` por perfil, persistindo somente config, sem arm automático no restart. Montar painel e IPC; usar `executeJavaScriptInIsolatedWorld` com tab validada, origin e dono. Hooks reais de navegação, login/logout, takeover humano, tab close, crash e lease perda **antes** de qualquer nova observação/dispatch.
6. Homologar no Desktop aberto por AI Control, com página fixture autorizada sem causar side-effects externos. Testar todas as linhas da matriz do Prompt 06-R; somente então qualificar `DONE`.

## 6. Riscos e Known Issues ainda abertos

- `P06-R-KI-01`: bug produtivo de ID duplicado após restart ainda PRESENTE; RED permanente agora registra a falha.
- `P06-R-KI-02`: implementação transacional GREEN só em módulo de referência sem integração; não foram alterados base canônica/config reais.
- `P06-R-KI-03`: UI/IPC/BrowserTask sem integração de lifecycle, sem prova de desativação na aplicação real.
- `P06-R-KI-04`: P04 apenas Trello, source page_watch não autorizada, receipt externo ausente, NO DISPATCH.
- `P06-R-KI-05`: Stage A H-079 não qualificado neste ciclo; upstream drift/exact-head CI e WIP Browser runtime alheio bloqueiam mutação produtiva.
- `P06-R-KI-06`: Node/renderer e Python/P04 precisam contrato de chamada explícito sem expor ponte irrestrita; nenhuma prova de exatamente-uma-entrega externa.
- `P06-R-KI-07`: mudanças textuais não estruturais e DOM virtualizado continuam fora de escopo da detecção mínima; não ampliar para conteúdo privado.

## 7. Git, alteração e entrega

Apenas 4 caminhos novos listados nesta sessão; `main` e HEAD inalterados. Nenhum `git add`, `commit`, `push`, `reset`, `stash`, `checkout`, restart do Hermes, modificação de fontes claimed/dirty ou operação de WhatsApp. Coordenador de claims aposentado: **nenhum claim novo inferido**. Integrador de commit não atribuído. Owner documental atual deve aplicar os inserts apropriados a `ROADMAP`, `HERMES_WORKSTATION_INTELLIGENCE`, `engineering-journal/CURRENT` e Known Issues após handoff; originais mantidos.

**DECISÃO:** PARTIAL. Não marcar P06 DONE e não usar P07 como dependência concluída. A correção está testada como projeto de referência, com RED produtivo preservado e bloqueio de integração identificado.

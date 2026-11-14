# Hermes Browser — recuperação operacional prioritária (28/10/2026)

**Mandato:** usuário autorizou dispensa de Stage A para TODAS as tarefas de 28/10/2026, somente desenvolvimento local, não release. Registrar também em `CURRENT_STATE.md`.

## Sintoma real observado por AI Control

Sessão visual "Abre o whatsapp": ferramenta mostrou "Failed to open web.whatsapp.com" e o agente interno investigava conexão Browser. A interface principal do Hermes estava operacional, com status backend desktop. Isso não demonstra indisponibilidade do domínio WhatsApp; a falha ocorreu no percurso de ferramenta/controlador.

## Causa operacional identificada (evidência)

- Antes da reinicialização, o descritor `%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-control.json` apontava para PID **33040**, loopback **58292**, `created_at=2026-10-28T18:37:09.049Z`.
- O PID 33040 não existia; a conexão à porta anunciada expirou. Electron principal anterior PID 23180 continuava ativo, e a UI Browser pela ponte AI Control indicava `ready:true`, 1 aba, `paused:false`, `lastError:null`.
- Portanto, o descritor público do controlador não correspondia a um processo disponível; uma interface aparentemente saudável podia estar inacessível ao agente. A origem da escrita no descritor ainda é hipótese, não causa raiz comprovada. Investigar colisão entre instâncias Electron/testes e recuperação do descritor.
- Durante a investigação o Electron reiniciou (não foi comandado por esta sessão). Novo PID **3392** foi registrado no descritor em **15:54:25**; processo vivo.
- Cliente oficial Python `tools.browser_workstation._request_json('GET','/health',timeout=4)`: **success True**, runtime `electron-chromium`, uma aba, não pausado, nenhum erro. `GET /resources` retornou success True, três recursos.
- Chamadas da ferramenta `_dispatch`: `browser_tabs` retornou erro **unsupported_action** (não é comando suportado; rede e autenticação atingiram o controlador). `browser_admissions_inspect` terminou exit 0, devolveu projeção como string; não alterou admissões.
- `AI Control` autenticado estava ativo antes do reinício; após o reinício, `hermes-nav.mjs status` e uma tentativa de `eval.mjs` passaram a responder **AI Control endpoint unavailable**. É necessário ativação manual pelo usuário após o reinício; não usar teclado/mouse global para isso.

## Prioridade de correção

1. **P0 recuperabilidade da descoberta do controlador:** criar teste RED de app Electron vivo + descritor sobrescrito por PID/porta obsoletos + ferramenta Python falhando; demonstrar recuperação autenticada e segura **sem reiniciar**. Implementar republicação atômica do descritor somente pelo proprietário real do servidor, com detecção de descritor stale, sem roubar ownership de outra instância viva. Evitar controller process ghost e artefatos de testes de outras instâncias sobrescreverem o perfil vivo. Verificar PID, token e porta em privado; nunca expor credenciais.
2. **P0 pipeline real agente→controlador:** executar ação somente leitura a partir do ambiente exato do agente Hermes (não apenas via Python Windows), verificar como o backend descobre `browser-control.json`, se usa outro SO/ambiente, qual usuário, `HERMES_WORKSTATION_HOME`, configuração Workstation browser e erros categorizados. Consertar o encaminhamento no caminho canônico, sem criar CDP/servidor paralelo, SSH ou bypass. Executar navegação `https://web.whatsapp.com` **uma vez com identidade legítima** após a prova de conexão, nunca enviar mensagens.
3. **P0 recuperação de UI/AI Control:** reativar o toggle apenas por ação humana; após autenticação, observar WebContents e snapshot independente de host/ready.
4. **P1 correções anteriores:** P02 `shouldDeferRestoredNavigation`, remoção do bypass `browser_admissions_reconcile` acessível ao agente e prevenção de novas admissões `runId=unbound`, conforme `BROWSER_P02_RESTART_AUTH_DIAGNOSTIC_20261028_CHATGPT.md` e fixtures em `%TEMP%`. Não confundir estas correções com o incidente do descritor.
5. **Verificação:** RED/GREEN, Vitest, pytest, typecheck, integração Controller Python, E2E do Browser Chromium real, reinício/recuperação, test isolation, login WhatsApp quando aplicável sem exportar dados. CI/release ainda HOLD.

## Garantias preservadas

Nenhum envio WhatsApp; nenhuma mutação de admissão histórica `op_browser_batch_actions_3d591fa7f8da`, nenhum ACK/replay/terminal falsificado; nenhuma automação de mouse/teclado; nenhum CDP externo; nenhuma alteração no runtime nesta investigação. Reinício Electron foi observado, não solicitado; não atribuir autoria. O cliente e o renderer podem ficar fora de sincronia. Não considerar GET /health como E2E da automação.

## P0 de reparo implementado localmente — 28/10/2026

**Fonte:** `apps/desktop/electron/workstation-browser-runtime.ts` (alteração cirúrgica no WIP existente; nenhuma branch/commit/push).

1. `refreshOwnedControlDescriptor()` compara token/URL/PID do descritor com o servidor HTTP realmente mantido pelo Electron. Se publicado corretamente, não escreve. Se outro PID estiver vivo, preserva o ownership alheio; se não existir, republica atomicamente o descritor com o **mesmo** token e URL. O servidor não é reiniciado nem o ledger manipulado.
2. Watchdog `controlDescriptorTimer` a cada 1.000ms, `unref` e limpeza em `stopControlServer`; `startControlServer` repetido também executa readback do descriptor.
3. `workstationBasePath()` prioriza `HERMES_WORKSTATION_HOME` e, no ambiente `VITEST`/worker, usa `os.tmpdir()/HermesWorkstation-vitest/<pid>`, impedindo que testes que limpam sua HOME substituam o controlador produtivo.
4. RED sintético em `%TEMP%\hermes-browser-control-descriptor-red.cjs` reproduziu `recovered:false` após sobreposição por PID 999999; GREEN após patch: `recovered:true`, exit 0. O teste usa apenas HOME/profile temporários.
5. Electron regressão 3 suites: 18/18 PASS, exit 0; hash do `browser-control.json` **inalterado** durante essa execução, confirmando isolamento do runner. TypeScript `tsc -p tsconfig.electron.json --noEmit` passou. `node scripts/bundle-electron-main.mjs --dev`: exit 0, bundle `apps/desktop/dist/electron-main.mjs` regenerado.
6. **Ainda não ativado no processo principal**: a instância ativa continua anunciando PID órfão 35068 (descritor modificado por suíte anterior às 16:08); AI Control indica endpoint indisponível. O operador precisa fechar/reabrir Hermes normalmente, sem automatizar mouse/teclado ou alterar o foco. Depois ativar AI Control manualmente e validar GET /health + navegação real `https://web.whatsapp.com` com sua identidade de sessão. Não executar ações de envio.
7. P02, autenticação real de reconciliação e identidade `unbound` continuam fora desta correção operacional, conforme outro relatório. Não atribuir a falha da navegação a esses patches sem E2E.

**Incidente confirmado por correlação:** às 16:08, após Vitest, um descritor produtivo apontava para PID 35068 morto e o GET /health autenticado retornou ConnectionRefusedError. Depois da correção de isolamento, repetir testes deixou o descriptor preservado. Esta é evidência direta do conflito com testes, não prova da identidade exata de cada processo que escreveu.

## Continuidade de robustez — recuperação do listener HTTP sem reiniciar o Desktop (28/10/2026)

O diagnóstico do Hermes (controlador morto, descritor com PID/porta inválidos) confirma o **sintoma**, mas não prova por si a morte do servidor real. Na investigação anterior, foi observado que workers Vitest podiam publicar o próprio descritor no diretório do operador. O aplicativo principal já possui `requestSingleInstanceLock` em `apps/desktop/electron/main.ts`; isto limita segundas instâncias normais, mas não substitui isolamento de testes e health check do controlador.

**RED adicional obtido:** `%TEMP%\hermes-browser-control-server-close-red.cjs` iniciou `WorkstationBrowserRuntime` isolado, fechou somente seu servidor HTTP e aguardou watchdog. Antes do patch: `autoRestarted:false`, `descriptorRebound:false`, exit 2 intencional. Sem perfil real, sem navegação, sem replay.

**Patch aplicado em `apps/desktop/electron/workstation-browser-runtime.ts`:**
- `relistenClosedControlServer()` faz relisten do mesmo `http.Server` na interface loopback, sem reconstruir runtime/BrowserTask e sem renovar o token. Atualiza a porta no `ControlHandle`, republica o descritor pelo watchdog e emite estado.
- Guarda `controlRelistening` previne tentativas simultâneas. Encerramento intencional limpa intervalo e estado de relisten; erros de servidor são registrados.
- Preservadas as proteções anteriores: `refreshOwnedControlDescriptor()` verifica owner/token/URL, não se apropria de descritor de PID concorrente vivo, watchdog de 1s; testes Vitest isolados em diretório temporário.
- GREEN temporário após patch: `autoRestarted:true`, `descriptorRebound:true`, exit 0 (novo loopback port). Nenhuma ação Browser foi repetida.

**Testes oficiais acrescentados** ao arquivo `apps/desktop/electron/workstation-browser-runtime-admission.test.ts`:
1. Descritor sobrescrito por PID morto é restaurado sem reiniciar BrowserTask.
2. Servidor HTTP fechado é relistado no mesmo runtime, com o descritor correto.

**Verificações frescas:** Vitest Electron 8 arquivos = **73/73 PASS**; Python contratos Browser/WhatsApp = **35/35 PASS**; TypeScript Electron = PASS; `git diff --check` = PASS. Durante Vitest, SHA-256 de `%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-control.json` não mudou. Bundle `apps/desktop/dist/electron-main.mjs` regenerado com `node scripts/bundle-electron-main.mjs --dev` (exit 0). Branch `main@f1d5ab2f03`, 229 entradas dirty, staging 0, sem commit ou push. Não utilizar regressões como prova de E2E nativo de Chromium/WhatsApp.

**Limites da promessa de disponibilidade:** o watchdog funciona enquanto o processo principal Electron e o event loop continuam vivos; não recupera crash completo, hang do event loop, falha de Windows ou controle sem autenticação. Continuidade total exige supervisor externo com reinício controlado, health check autenticado, gestão de owner única e relatórios de indisponibilidade. Cliente Browser pode adicionar uma única nova tentativa **somente para leitura** após recapturar descritor válido; operações mutantes incertas jamais devem sofrer retry automático. Endurecer testes de instância concorrente e recuperação durante shutdown. Um único `/health` positivo não comprova a cadeia agente→WhatsApp Web.

**Validação operacional ainda pendente:** o Electron em execução deve carregar o bundle novo por reinício normal, sem entrada global pelo ChatGPT; reativar manualmente AI Control caso necessário. Conferir controlador `/health` autenticado, descoberta entre agentes e navegador nativo, `browser_navigate` e `browser_snapshot` com sessão legítima e sem envio WhatsApp. Manter ledger histórico e fences.

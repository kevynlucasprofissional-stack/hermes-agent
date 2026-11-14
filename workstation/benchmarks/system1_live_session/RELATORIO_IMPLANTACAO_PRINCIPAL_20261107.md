# Hermes Work — implantação do fast path determinístico no Desktop principal (07/11/2026)

## Resultado da missão
**Parcial: instâncias de qualificação encerradas, flag persistida e Desktop principal recuperado; validação humana principal bloqueada por AI Control desativado após reinicialização.** Não inventar PASS da UI.

### 1. Limpeza dos testes (PASS)
- Instâncias isoladas Electron PID **11272** (`e2e-20261107211148-057da9`) e **47924** (`e2e-20261107212515-f7695a`): encerradas **graciosamente** via `CloseMainWindow()` e desaparecimento confirmado.
- Pré-encerramento: bases Kanban isoladas sem Tasks/TaskRuns em andamento; `browser-session.json` com **0 operações não confirmadas**. Perfis e relatórios preservados no disco.
- Nenhum processo Electron/Python dos sandboxes permaneceu ativo.

### 2. Configuração e reinicialização principal (PASS após recuperação)
- Repositório `C:\Github\hermes-agent`, `main@f1d5ab2f03`, checkout compartilhado com **379 entradas dirty antes desta documentação**. Sem git reset/stash/clean, commit ou push. Não foram modificados arquivos de código nesta intervenção.
- Baseline principal: Electron PID **37124** e backend PID **40584**, sem Tasks/TaskRuns em `running`/`in_progress`. Status do banco antes/depois: `tasks: archived 1, blocked 67, ready 9, triage 14`; `task_runs: blocked 69, reclaimed 8`. Histórico e dados mantidos.
- A preferência original `minimize-to-tray.json` continha `enabled:true`. Uma primeira tentativa de `CloseMainWindow()` apenas escondeu a janela na bandeja (comportamento intencional); não foi forçado o encerramento e a flag foi revertida nesse ponto.
- Por meio da ponte AI Control autenticada e da API pública `window.hermesDesktop.minimizeToTray.set(false)`, a preferência foi temporariamente desativada. O processo original saiu normalmente em seguida, antes de lançar o novo. Preferência original **restaurada `enabled:true`** antes da reinicialização.
- `HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED=1` foi definida em ambiente **User** do Windows, e também fornecida explicitamente ao novo Electron ao iniciá-lo.
- Primeira inicialização pós-restart (PID **48404**, backend **40064**) encontrou o servidor de desenvolvimento Vite `127.0.0.1:5174` desligado: renderer esgotou o orçamento de recarregamentos e exibiu erro `did-fail-load`. Isso decorreu do encerramento do launcher dev anterior com `concurrently -k`.
- Restaurado Vite no processo independente Node **41608**, escutando somente `127.0.0.1:5174` e respondendo **HTTP 200**. Como o Electron de inicialização falha não se recuperou automaticamente, esse processo e seu backend foram encerrados **uma única vez, de forma direcionada após preflight sem trabalho ativo**, e o Desktop foi aberto novamente com Vite já disponível.
- Estado final: Electron **41280**, backend filho **46432** e Vite **41608**, todos presentes; `renderer.did-finish-load`, `HERMES_BACKEND_READY` e `gateway-route active` em logs. Janela principal responsiva e visível. Préferência de bandeja original `enabled:true` e flag de usuário `1` confirmadas.
- O backend `hermes serve` usa API headless; resposta de `/health` indicando dashboard desativado não é, isoladamente, defeito de inicialização. A comprovação de readiness é o log `HERMES_BACKEND_READY` e o processo filho.

### 3. Gate de mensagem humana no Desktop principal (BLOQUEADO)
- `node apps/desktop/scripts/hermes-nav.mjs status` informa: **AI Control disabled or Hermes not restarted with native bridge**. Após o restart, o toggle **não permaneceu habilitado**.
- Por instruções obrigatórias da skill `controle-windows-hermes-ai-control`, não ativar o toggle por conta própria, não simular `Ctrl+Shift+A`, não usar global mouse/keyboard e não substituir a ponte por CDP ou HTTP direto. **Nenhum prompt foi enviado na sessão produtiva**.
- Logo, **a execução real com a frase exata no Hermes principal, contagem 0 de chamadas System 2, duas leituras e readback final não foram verificadas nesta implantação**. A evidência prévia do MVP em instância isolada permanece válida: `RELATORIO_ENDTOEND_ISOLADO_20261107.md` e `RESULTADO_A_B_ISOLADO_20261107.json`, onde 62/62 regressões e E2E PASS deram 2→0 chamadas, 9,6 s→1,2 s, `@e1`.
- A fixture `http://127.0.0.1:18791/unique` permanece disponível (HTTP 200) para a última qualificação.

### Única ação pendente
1. **Usuário** ativa manualmente AI Control no Hermes principal (`Ctrl+Shift+A`, janela Hermes em primeiro plano) e avisa no chat.
2. Com a ponte `aiControl:true`, validar a instância principal, abrir uma **sessão de teste nova e identificada** (sem tocar nas outras) e navegar pela BrowserTask nativa para `http://127.0.0.1:18791/unique`. Enviar em turno isolado, exatamente `Localize o botão Relatórios na página atual`.
3. Ler logs/SQLite da sessão real e provar `Operational resolution: SATISFIED`, `system1_browser_read_verified`, `api_calls=0`, snapshots inicial/fresco da mesma BrowserTask e nenhuma mutação; comparar com baseline isolada. Se falhar, devolver flag ao valor anterior e registrar.
4. Não reiniciar/alterar outras sessões, nenhuma mutação incerta; **não promover Laya**, o caminho exato é determinístico.

### Reversão de preferência
- Backup da flag anterior (ausente) em `%LOCALAPPDATA%\HermesWorkstation\qualification\system1-deployment-20261107\preflight.json`.
- Para desativar apenas a rota em novos processos: `[Environment]::SetEnvironmentVariable('HERMES_SYSTEM1_BROWSER_FASTPATH_ENABLED',$null,'User')`; reinicialização controlada somente quando a sessão estiver ociosa. Não aplicar reinicialização automática a uma sessão ativa.

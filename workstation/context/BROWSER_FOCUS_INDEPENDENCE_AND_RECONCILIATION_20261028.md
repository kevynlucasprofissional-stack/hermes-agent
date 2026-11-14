# Hermes Work — Browser nativo independente de foco e reconciliação segura (28/10/2026)

**Status:** correção pontual de foco implementada e compilada, regressões PASS. Incidente de lote pendente e aceite do Kanban NÃO reconciliados; homologação nativa em segundo plano e após reinício continua pendente.

## Solicitação operacional e evidência

O usuário apresentou aviso da UI "Task blocked — needs your input": `outcome_not_verified; blocking_pending_items; verification_evidence_missing`. Descreveu bloqueio `prior_operation_requires_reconciliation` em lote e perda de controle do Browser nativo quando outra aplicação recebe o foco.

`workstation/contracts.py::AcceptanceEvaluator.evaluate()` origina os três motivos do Kanban. São checks de conclusão de tarefa/evidência. Separadamente, `workstation-browser-runtime.ts::executeControlRequest()` recusa **novas mutações** do mesmo escopo quando `pendingBrowserMutation(...)` encontra admissão pendente. NÃO equiparar aviso de Kanban ao erro de input nem desbloquear uma operação incerta sem confirmação causal.

## Arquitetura verificada e causa de foco

- Execução de `browser_click` usa `this.cdp(wc, 'Input.dispatchMouseEvent', ...)` no **WebContents específico da BrowserTask**, sem input de mouse global; `browser_press` usa `Input.dispatchKeyEvent` no mesmo wc; `browser_snapshot` usa `executeJavaScript` e não exige foreground. A arquitetura já pode funcionar em background.
- O runtime ainda chamava `entry.view.webContents.focus()` incondicionalmente ao ativar uma aba e anexar seu viewport, mesmo quando a janela host não estava em primeiro plano. Isso mistura controle visual humano com execução de IA e pode interferir na experiência de foco.
- TDD: acrescentei teste `Browser viewport does not steal foreground focus when Hermes host is backgrounded` em `workstation-browser-runtime-task.test.ts`. RED reproduzido: `background attachment must not focus the WebContents`, `true !== false`, exit 1.
- Mudança cirúrgica em `workstation-browser-runtime.ts`: ambas as chamadas automáticas a `focus()` ficam condicionadas a `BrowserWindow.isFocused()`. Não existe nova chamada de ativação global, nem uso de teclado/mouse externo. Quando janela está em foreground, a interação humana continua recebendo foco natural.
- GREEN do teste acima exit 0. Teste sintético adicional `agent Browser click stays bound to WebContents while the host window has no foreground focus` PASS: navigate + click via controlador com janela host não focada e sem chamar `focus()`.
- O estado visual (`activeTabId`, attach, host) não deve substituir identidade (`taskId`, `runId`, `sessionId`, `tabId`) ou lease humana. O runtime já tem teste de isolamento entre sessões, mas ainda não há E2E Chromium real com app minimizado/segundo plano.

## Validação deste trabalho

- `vitest run --project electron` em 6 arquivos relevantes: **94 PASS**, exit 0.
- Python: `pytest tests/tools/test_browser_batch_semantic_contract.py tests/tools/test_whatsapp_browser_tools.py -q`: **35 PASS**, exit 0.
- `tsc -p tsconfig.electron.json --noEmit`: PASS.
- `git diff --check` dos dois arquivos editados: exit 0.
- `node scripts/bundle-electron-main.mjs --dev`: PASS, bundle de desenvolvimento regenerado.
- Durante teste Electron, SHA de `%LOCALAPPDATA%\HermesWorkstation\Runtime\browser-control.json` preservado. Nenhum teste executou WhatsApp real, retomou operação pendente ou alterou ledger produtivo.
- Branch `main@f1d5ab2f03`, 229 dirty, staging vazio. Arquivos alterados: `apps/desktop/electron/workstation-browser-runtime.ts` (WIP preservado), `apps/desktop/electron/workstation-browser-runtime-task.test.ts` (dois testes novos e mock `isFocused`). Sem branch, commit, push, reset, clean, stash.
- AI Control respondeu `endpoint unavailable` durante investigação; não usar input global para reativá-lo.

## Arquitetura-alvo — Browser como ator persistente, não como janela focada

1. **Controle:** servidor Browser nativo no Electron (já existente), comando sempre dirigido ao WebContents de um `tabId` ligado a uma `BrowserTask` canônica. UI/aba é só projeção e host visual. Ocultar, minimizar ou alternar entre aplicativos não deve transferir owner nem foco obrigatório para o agente.
2. **Arbitragem:** lease humana real, com bloqueio de mutações concorrentes quando operador controla o mesmo WebContents. O usuário pode usar o Browser visivelmente; o agente pode ler sob observação permitida e só volta a mutar após release e readback; nunca burlar lock por perda de foco. Foco do SO ≠ autoridade humana; foco DOM de alvo ≠ foreground da janela.
3. **Operações:** recibos duráveis admission/dispatch/readback/ACK pai; sem replay automático de mensagem, clique incerto, navegação ou lote com efeito ambíguo. Persistência sobrevive a recriação de viewport ou control-server; não confundir watchdog de porta com restauração de ação.
4. **Recuperação UI:** em `prior_operation_requires_reconciliation`, mostrar operação causadora e evidência permitida; oferecer `Inspect` read-only e handoff humano real. Separar estados `not_dispatched`, `effect_verified`, `uncertain` e `reconciled` com aprovação autenticada. Nunca converter `OPERATOR_REVIEW` autodeclarada em terminal; ver relatório P02 anterior.
5. **Kanban:** mostrar pendências/verificadores/evidências ausentes; quando necessário, permitir trabalho independente e consultas somente leitura, sem falsificar `VERIFIED_COMPLETED`. `kanbanCardId` pode ser ausente no incidente histórico; não inventar vínculo.
6. **Supervisor:** watchdog HTTP/descritor, isolamento Vitest e relisten já foram implementados na missão anterior; processo Electron inteiro morto exige recuperação externa, jamais promessa de controle ininterrupto em qualquer circunstância.

## Gates restantes (prioridade)

- Reabrir Hermes com novo bundle e reativar AI Control pelo operador; teste **nativo** com perfil/URL sintética, alternando foco Windows e minimizando janela, para `snapshot`, `click`, `type`, `press`, `scroll`, com readback causal. Evitar mensagens ou logins reais.
- Investigar especificamente se `Input.dispatchKeyEvent` em WebContents oculto mantém o foco **DOM do alvo** quando a janela perde o foreground; não reintroduzir `window.focus()` ou `webContents.focus()` para forçar foco global. Seleção deve ser explícita/dirigida ao elemento.
- Implementar fluxo humano de reconciliação comprovável, separado da ferramenta agent-only `browser_admissions_reconcile`, e recuperação de lote de etapas parcial sem replay.
- Testar Screen/Human Control lease, WebContents destruído/recriado, browser parked, run mismatch, crash/restart, perda de controlador e concorrência entre tarefas.
- Validação completa de Electron nativo, Kanban e release. As alterações locais não comprovam a experiência real em segundo plano até E2E.

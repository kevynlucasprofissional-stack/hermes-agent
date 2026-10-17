# HLM-MVP — Patch map (2026-10-17, main fd57e40)

**Status:** mapeamento inspecionado; apenas `workstation-learning-question-policy.ts` e respectivo teste são código preparado e não conectado. Não substituir arquivos completos grandes. Adicionar métodos pequenos sob owner atual, mantendo contratos.

| Caminho exato | Pontos existentes | Patch obrigatório |
| --- | --- | --- |
| `apps/desktop/electron/workstation-browser-runtime.ts` | `BrowserEntry`, `wireEntry`, `takeControl`, `screenshotForEntry`, `cdp` | add LearningSessionRecorder owner: start/stop/epoch/events/window/leases. Não criar segundo WebContentsView. |
| `apps/desktop/electron/workstation-browser-ipc.ts` | `registerWorkstationBrowserIpc`, `senderWindow` | IPC `learning:start/status/set-intensity/stop/discard/answer`, autenticar sender vs owner. |
| `apps/desktop/src/app/browser/index.tsx` | `BrowserControlBar` linha ~244, `useAdoptTabToSession` linha ~339 | Botão Aprender com reuse da adoção real antes da captura; não confundir IDs runtime/stored. |
| `apps/desktop/src/app/chat/right-rail/workstation-browser-pane.tsx` | `WorkstationBrowserPane`, `activeSessionKey`, botões de lease | Botão Aprender + seletor de intensidade live + log e estados/erros. |
| `apps/desktop/src/app/browser/types.ts` | `WorkstationBrowserBridge` | Acrescentar `LearningSessionState`, `LearningIntensity`, APIs tipadas. |
| `apps/desktop/electron/workstation-learning-question-policy.ts` | **Novo/inert já criado nesta branch** | Reutilizar `parseLearningIntensity` e `decideLearningQuestion`, não reescrever policy. |
| `apps/desktop/electron/workstation-learning-question-policy.test.ts` | **Novo/inert** | Executar testes reais e adicionar casos de corrida/budgets/pausa; não declarar PASS ainda. |
| `apps/desktop/electron/*preload*` | Encontrar binding existente `workstationBrowser` | Expor métodos e manter sender validation; não expor CDP/filesystem a renderer. |
| `workstation/experience_compiler/compilability_monitor.py` | `process_event`, `LearningPolicy` | Learning Mode é origem humana separada; nunca forçar `VERIFIED_SUCCESS`, `DIRECT` ou `AdoptionOffer`. |
| `workstation/experience_compiler/capability_studio.py` | `project_capability`, `draft_revision` | Exibir rascunhos e evidências humanas sem autorizar dispatch/promotion. |
| `workstation/skill_learning.py` | `ExperienceLessonCompiler.record_candidate_lesson` | Registrar skill candidata descritiva se caminho mais curto que OperationalCapability, com fonte `human_demonstration`. |
| `workstation/operational_capabilities.py` | `OperationalCapabilityRegistry` | Só `DISCOVERED` + prova/cross-run antes de mudar lifecycle; sem bypass. |

**Arquivos NOVOS sugeridos**: `apps/desktop/electron/workstation-learning-session.ts` (owner de captura/video/storages), `apps/desktop/electron/workstation-learning-events.ts` (sanitização), `apps/desktop/src/app/browser/learning-controls.tsx` (UI compartilhada), `workstation/learning_mode/questions.py` ou integração adjacente ao Gateway atual (interpreter provider), `workstation/tests/test_human_demonstration_boundary.py`.

**Segurança e E2E**: usar fixtures locais de DOM/canvas com campos sensíveis, teste native Electron com 1 sessão + handoff; teste de aba errada, navegação para login, background tab, crash/restart, zero old-lease replay, vídeo+JSONL time-sync, mudança intensidade durante gravação, no duplicate LLM, provider error, disabled sharing, zero auto promotion.

**Sinal de falsificação**: se compilador Python esperar somente `VERIFIED_SUCCESS`, NÃO reclassifique origem humana; registre candidato inerte e prove integração independente antes de avançar. Se vídeo não puder ser gravado com privacidade garantida no build Electron Windows, mantenha `video_status=blocked`, não substitua silenciosamente por screenshots e não declare M0 PASS.

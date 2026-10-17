# HLM-MVP — Auditoria técnica corretiva 80/20 — 2026-10-17

**Status:** REVISÃO DE CÓDIGO, SEM TESTES EXECUTADOS NESTA AUDITORIA. **Baseline consultada:** `main` `2e5b042e4c905acda8b6b9545a2cd5f5377060dc`; origem HLM `066b24142102a1abe25d9a01e096aafafbeba1b0`. PR #99 consta merged. PR #100 consta closed/unmerged, porém `main...066b241` apresenta status `behind` (commit #100 é ancestral da main), e os problemas abaixo ainda aparecem em arquivos da main. Não inferir mecanismo de incorporação a partir do estado de PR.

## Decisão

**ACEITAR COM RESERVAS** a estrutura do protótipo (React UI, intensidade live, contratos de gestos, JSONL, método Python de CandidateLesson). **REPROVAR as alegações de M0–M2 concluídos e A–I PASS** como qualificação de produto. O handoff novo é uma rodada corretiva estreita, não um reboot de arquitetura. M3 replay permanece HOLD.

### P0-1 — Vídeo declarado não corresponde ao Browser

`apps/desktop/electron/workstation-learning-session.ts::startVideoRecording` executa `ffmpeg -f lavfi -i color=c=black:s=1280x720:r=15 -t 1 -c:v libvpx recording.webm`: fonte sintética preta de um segundo, **não** captura pixels de `WebContentsView`; `stop()` faz kill do processo e marca status stopped sem comprovar arquivo e duração. O teste vertical utiliza `videoEnabled:false` e não demonstra vídeo real. Correção obrigatória: capturar superfície do Browser de modo limitado e autorizado; produzir vídeo real e reproduzível; timestamps relativos ao mesmo relógio do evento; verificar duração, frames variáveis e arquivo não preto, status VERIFIED|BLOCKED|ERROR baseado no resultado. Nenhuma tela fora do escopo ou autenticação deve ser capturada.

### P0-2 — Origem dos gestos, limites e proteção de dados

`workstation-browser-runtime.ts::injectLearningObserver` utiliza JS de página e `console.debug('__HERMES_GESTURE__' + JSON.stringify(...))`; `wireEntry` interpreta `wc.on('console-message')` de todas as tabs como gestos possíveis se existir qualquer recorder ativo. O handler reescreve `tabId` como `entry.id` e chama `recordLearningGesture` sem checar `state.tabId`, `webContentsId`, `documentEpoch` e scoped origin. Página pode imprimir marcador idêntico. `senderWindow(event)` nos novos handlers IPC valida apenas ser BrowserWindow, não proprietário da sessão/aba. **Não considerar a entrada confiável**. Trocar por canal de observação isolado/autenticado com owner e binding de tab/wc/epoch; aplicar allowlist e consent antes da captura em cada evento/snapshot; descartar evento de outra aba, script forjado, lease vencido e post-pause. Nunca permitir que a instrumentação sobreviva indevidamente a stop/discard. Navegações devem parar **também o vídeo**, não só alterar flag de evento. Não enviar vídeo bruto a provedores sem consentimento separado.

### P0-3 — Identidade temporal, consistência e falhas

`wireEntry` atribui `relativeTimeMs=Date.now()` e `LearningSessionRecorder` persiste `time_ms` diretamente: isto é wall clock absoluto, não offset monotônico sincronizado ao vídeo. `captureScreenshot(...)` descarta retorno e não registra snapshot_ref/event_ref; `persistManifest` e `appendFileSync` engolem erros mas incrementam contadores. Corrigir relógio monotônico comum, `event.origin/actor` comprovados, `documentEpoch`, backpressure, evidência snapshot antes/depois com refs, persistência atômica, error states e discriminação de arquivo parcial. Add tests de crash/restart/dedup/lease.

### P1-1 — Question Engine **não é contextual/IA**

`LearningSessionRecorder::generateCandidate(gesture)` implementa 3 templates: Ctrl+tecla, click role/name, pointerup coords. Valores novelty/uncertainty/reuse são constantes hardcoded e a pergunta é gerada de um evento isolado. A política `decideLearningQuestion()` é útil, mas não substitui segmentação, estado anterior/posterior ou LLM multimodal. O teste "vertical integration" envia gestos criados manualmente, mocks de screenshot e `videoEnabled:false`: não comprova inferência real. MVP corretivo: construir **um** segmentador pequeno (ações contíguas+pausa natural+mudança de estado); produzir 2 snapshots seguros; invocar provider já configurado para hipótese estruturada com evidência, intenção, razão e pergunta; marcar `awaiting_interpretation` se provider offline, sem template falso; não interromper drag, respeitar cooldown e live intensity; feedback humano deve realmente revisar hipótese e candidato downstream, não só marcar flag.

### P1-2 — Geração de candidatas ainda não conectada

`workstation/skill_learning.py::record_human_demonstration_candidate` persiste candidatas inertes corretamente quando chamado, mas a integração product `LearningSessionRecorder → Gateway/Python` não está demonstrada. Testes Pytest chamam função manualmente com dados de ficção; nenhum caminho do `stop()` ou do `answerQuestion()` invoca o compiler. Ligar à etapa de segmento confirmado via owner autorizado, evidência real, `CandidateLesson` inert (ou `DISCOVERED`), revisão, persistência e referência a question/event/video. **NÃO** fabricar TaskRun, owner receipt nem `VERIFIED_SUCCESS`.

## Matriz auditada de verdade

| Critério original | Evidência efetiva | Status revisado |
|---|---|---|
| A OFF sem gravação | teste inerte recorder, não Electron real | PARCIAL |
| B handoff mesma aba | UI adota, teste simulado sem E2E real de aprendizagem | PARCIAL |
| C intensidade live | método `setIntensity()` atualiza status/policy na mesma sessão | IMPLEMENTADO PARCIALMENTE (vídeo não contínuo) |
| D DOM/Canvas/shortcut | eventos e sanitizador parcial; origem não confiável | PARCIAL/SECURITY HOLD |
| E auth/off-origin pausa | flags de evento, vídeo não interrompido | FAIL |
| F pergunta contextual | templates por evento, correção somente flag | FAIL |
| G vídeo sincronizado + JSONL | fonte `lavfi color=black` 1s; wall clock | FAIL |
| H candidata humana integrada | API isolada + teste mock, pipeline não conectado | PARCIAL |
| I cross-owner/crash | IPC e `console-message` insuficientemente vinculados | FAIL/SECURITY HOLD |
| J replay supervisionado | não demonstrado | HOLD CORRETO |

**Nota:** status são derivados de inspeção estática de `main` e PR #100, não de execução local nesta auditoria. Testes 19 Vitest/2 Pytest/typecheck foram informados no relatório, não repetidos aqui. Não publicar `PASS M0–M2` por eles.

## O que PRESERVAR

- `learning-controls.tsx` e integrações Hub/pane como ponto de partida (corrigir binding por sessão/aba).
- `LearningSessionRecorder` lifecycle, schemas, JSONL e método `setIntensity`, ampliados em vez de reescritos.
- `workstation-learning-question-policy.ts` (score/cooldowns/limites) como filtro heurístico pós-inferência, *não* como gerador semântico.
- `workstation-learning-events.ts` como sanitizador auxiliar, **não como garantia suficiente de origem/consentimento**.
- `ExperienceLessonCompiler.record_human_demonstration_candidate` e fronteira `candidate` sem promoção.

## Prova 80/20 indispensável

1. Iniciar `Aprender` numa tab real do Browser Hub, ver redirecionamento à **mesma** WebContentsView da sessão chat e sessão ligada.
2. Gerar vídeo **real** de 10–20 segundos com mudança visual de DOM+Canvas, reproduzi-lo e localizar eventos por diferença temporal máxima definida (alvo 250ms), sem exposição de outra origem.
3. Alterar intensidade durante gravação, sem reinício ou perda de eventos.
4. Segmento composto de várias ações, interpretação REAL via provider habilitado, pergunta causal específica ao segmento; confirmar e depois corrigir outro segmento; replay das perguntas e referência de snapshots/gestos.
5. Exibir candidata humana inerte persistida por fluxo real, sem bypass de ExperienceCompiler.
6. Teste explícito `forged_console_marker`, outra aba, origem externa, login, crash, falha de escrita e provider offline. Nenhum evento capturado, vídeo aberto ou candidata promovida em contextos não autorizados.
7. Documentar trilha de evidência com commit/testes/arquivo WebM real e `ffprobe` ou equivalente e logs, separando unit tests vs Electron Windows E2E.

**Handoff:** [HLM_MVP_CORRECTIVE_IMPLEMENTER_PROMPT.md](../learning-mode/HLM_MVP_CORRECTIVE_IMPLEMENTER_PROMPT.md).

**Regra de promoção:** não realizar merge/afirmar estado VERIFICADO até haver evidências E2E desses pontos. Preserve D-046, D-047, browser native lease, runtime owner, TaskRun boundaries.

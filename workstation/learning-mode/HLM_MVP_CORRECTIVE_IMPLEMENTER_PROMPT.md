# HLM-MVP — PROMPT CORRETIVO PRONTO PARA EXECUÇÃO (80/20)

**IA implementadora — EXECUTE, não discuta arquitetura.** Corrija a implementação existente do `Hermes Learning Mode` aproveitando código útil; não recrie a feature. Não faça merge automático nem force push.

Repo `kevynlucasprofissional-stack/hermes-agent`.

**PRECONDIÇÃO DE VERDADE:** PR #99 foi merged; PR #100 mostra closed/unmerged no GitHub, mas seu commit `066b24142102a1abe25d9a01e096aafafbeba1b0` é ancestral de `main` HEAD `2e5b042e4c905acda8b6b9545a2cd5f5377060dc` (comparação status `behind`). A MAIN JÁ CONTÉM o HLM básico e também os defeitos abaixo. Não retornar ingenuamente à PR #100, não reimplementar de zero. Main pode evoluir: recalcule HEAD, diff e `git status` no início. Não tocar em arquivos dirty, worktrees de outros agentes ou stashes (o relatório indica stash WIP prévio; preservá-lo).

**DOCUMENTAÇÃO DE ENTRADA OBRIGATÓRIA:** `workstation/context/LEARNING_MODE_AUDIT_2026-10-17.md` (leia inteiro); D-047 `workstation/context/LEARNING_MODE_HUMAN_DEMONSTRATIONS_2026-10-17.md`; mapa `workstation/learning-mode/LEARNING_MODE_PATCH_MAP.md`. Leia só os arquivos-alvo a seguir e qualquer AGENTS.md vigente. Não gerar outro longo planejamento.

## Prioridade P0 (executar nesta ordem)

**P0a — identidade, privacidade e fonte confiável:** `apps/desktop/electron/workstation-browser-runtime.ts` (métodos HLM após takeControl, `injectLearningObserver` e `wireEntry`); `apps/desktop/electron/workstation-browser-ipc.ts`; `apps/desktop/electron/workstation-learning-session.ts`. **REMOVA** transporte de eventos confiável por `console.debug('__HERMES_GESTURE__')`. Console de página não autentica um evento humano; qualquer script de página pode imitá-lo. Use world isolado/CDP event bridge limitado ao Browser owner (reutilizar CDP se já anexado, não criar outro debugger concorrente). Associe `tabId/webContentsId/documentEpoch/origin/runtimeSessionId/storedSessionId` canônicos, com nonce/session token não exposto à página, verificados a cada ingestão. Uma aba diferente jamais pode alimentar a LearningSession. Garantir caller legítimo via IPC além de `senderWindow`; impedir Stop/Discard/intensity de outra janela/sessão. Revalidar human lease (5min TTL) por owner e não capturar quando inválido. Consentimento opt-in e allowlist estrito da aba/origem/site, bloquear auth/checkout e campos sensíveis antes de gravar; não capturar valores de input, texto digitado, clipboard, senhas ou outros tabs. Em `stop/pause/discard/crash`, desarmar hooks/câmera/frames efetivamente, não apenas status no manifest. Testes maliciosos de outra aba, console spoof, page JS injection, navegação e entrada sensível.

**P0b — VÍDEO DO BROWSER REAL:** `apps/desktop/electron/workstation-learning-session.ts::startVideoRecording/stopVideoRecording`. Substituir completamente fonte fake `-f lavfi -i color=c=black:s=1280x720:r=15 -t 1`: proibido vídeos pretos ou placeholder. Preferir stream frames da mesma WebContentsView com captura real e encoder qualificado, sem capturar desktop/chat/janela externa; reaproveitar `webContents.capturePage` ou CDP de forma segura, com benchmark 5/10/15fps, limite de CPU/disco/backpressure. Conteúdo visual pode conter segredos mesmo que evento DOM não contenha; proteger frames/opt-in e bloquear cenas sensíveis. Não iniciar vídeo até autorização de aba/origem; em pause/navigate parar fonte antes de novo frame; flush/close encoder com ack e verificar `recording.webm` legível. Em FFmpeg ausente, status `blocked`, UI mostra bloqueio e não declara G PASS. Video 10–20s com transições DOM/Canvas e duração validada por ffprobe.

**P0c — TIMEBASE + SNAPSHOTS + persistência:** Atribuir offset monotônico `performance.now/process.hrtime.bigint` a partir de start da LearningSession, converter para `time_ms` comum ao vídeo; NÃO `Date.now()` como time relative. Garantir `events.jsonl` com `event_id, tabId, epoch, time_ms`, coordenadas normalizadas e `snapshot_before_ref/snapshot_after_ref` quando capturados (hoje retorno de `captureScreenshot` é descartado). Append/manifest atomic/error reporting: falha de fs não incrementa contadores e não silencia erro; restart/crash marca arquivo parcial, sem fabricar sucesso. Evitar snapshot no diretório errado/fotos órfãs.

## Prioridade P1 (só depois P0 validado)

**P1a — QUESTION ENGINE DE VERDADE, minimamente contextual:** em `LearningSessionRecorder::generateCandidate` remover template-candidates tratados como inferência. Manter policy `decideLearningQuestion` para intensidade live, cooldown, dedupe. Implementar segmento com 2+ ações, janela temporal/pause natural e snapshots pre/post e contexto da aplicação; extrair hipótese por chamada real ao modelo multimodal CONFIGURADO no Hermes (usar provider/Gateway existentes, sem credencial nova hardcoded e sem gerar novo TaskRun de efeitos). Schema estrito de saída {segment_event_refs,hypothesis,uncertainty,question,kind,reasoning_summary}, com origem/proveniência, budget, feedback humano e incerteza não inventada. Perguntar sobre causalidade, decisão, validação com base na sequência; se provider indisponível/sem consentimento enviar frames, `awaiting_interpretation`/erro visível, sem templates artificiais. Reduzir chamadas LLM via segmentação e regras baratas. No drag/máscara/keyframe, enfileirar; após pausa, mostrar UMA pergunta. Intensidade Discreto/Equilibrado/Intensivo muda imediatamente na mesma sessão. Correction: preservar texto original e gerar revisão/invalidar candidata afetada, não só marcar `needsReinterpretation`.

**P1b — LIGAR CANDIDATA REAL AO COMPILADOR:** `workstation/skill_learning.py` já tem `record_human_demonstration_candidate` que está testado isoladamente. Criar caminho legítimo Electron LearningSession → Gateway/Python (API local autenticada) → CandidateLesson a partir de pelo menos 1 segmento humano explicado/confirmado. Persistir id, refs eventos/frames/vídeo, intenção, heurística, resultado, correção, status inert, e torná-lo recuperável em UI ou endpoint de revisão. `human_demonstration` nunca `VERIFIED_SUCCESS` e nunca auto-promove. Se no caminho atual faltar owner/API, reportar HOLD preciso; NÃO fabricar integração por teste que chama método diretamente.

## Sequência curta de execução

0. Inspecionar `git status/HEAD`, criar branch própria `fix/hlm-real-capture-question-engine-20261017` a partir de MAIN **atual**; preservar alterações locais. Rodar testes de baseline.
1. Escrever testes de origem confiável/tab/lease/consent e vídeo real que falhem na implementação atual; corrigir P0a e P0b.
2. Corrigir P0c, provar `event↔timecode↔frame` e crash safe.
3. Substituir perguntas templates por um vertical cognitivo REAL em aplicativo DOM simples + Canvas; integrar provider e registrar 1 pergunta causal relevante, persistir resposta/correção.
4. Integrar 1 candidata inerte via caminho produtivo Gateway/Python; inspecionar após reiniciar.
5. Rodar Vitest/pytest/tsc/eslint + Electron Windows REAL; capturar evidências por teste com hash/filename, duração vídeo, snapshots e logs. Separar mocks de prova de produto.
6. Atualizar `workstation/ROADMAP.md`, `context/CURRENT_STATE.md`, `DECISIONS.md`, `HERMES_WORKSTATION_INTELLIGENCE.md`, `KNOWN_ISSUES.md`, `engineering-journal/CURRENT.md` substituindo alegações prévias M0–M2 VERIFICADOS por estados comprovados. Não apagar histórico, adicione errata datada. Abrir PR DRAFT de correção sem merge.

## GATES DE ACEITAÇÃO IMUTÁVEIS

- [ ] Origem única da aba autorizada, fake console descartado, outra aba e outra sessão isoladas, IPC com owner; payloads de page controlados.
- [ ] Off-origin/login/secret UI param frame/eventos ANTES de captura; vídeo local, sem upload sem consentimento independente.
- [ ] WebM real com >10s de mudanças visíveis da aba, validado por decoder e frame sampling; nunca `lavfi black`.
- [ ] `time_ms` relativo monotônico e refs verificáveis do evento no vídeo e snapshots; teste de sincronização.
- [ ] Mesma LearningSession mantém ID e gravação com troca Intensivo→Discreto→Equilibrado; sem restart.
- [ ] Pergunta inteligente com referência a sequência real de 2+ ações + evidência visual e provider real; sem modelo => `awaiting_interpretation` transparente.
- [ ] Correção humana modifica interpretação e dependentes, não apenas um boolean.
- [ ] CandidateLesson inert criado por fluxo produtivo, não por chamada direta do teste.
- [ ] Testes de crash/restart/fs fail/provider fail, sem leaked secrets, E2E Windows Electron.
- [ ] Nenhuma promoção, TaskRun fictícia, ou replay autônomo alegado sem verdade canônica.

## Saída exigida

PR link + HEAD; diffs; tabela PASS/FAIL/HOLD item por item com localizador para artefatos de E2E verdadeiros; testes por tipo, custo/overhead quando medido; known issues; último registro em journal; **recomendação 80/20** de próxima ação. Não transformar resultado parcial em `M0–M2 VERIFIED`. Corrigir sobretudo A/E/F/G/H/I antes de reportar. Execute agora.

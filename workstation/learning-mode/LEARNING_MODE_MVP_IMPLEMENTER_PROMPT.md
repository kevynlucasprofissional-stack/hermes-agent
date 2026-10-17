# PROMPT EXECUTÁVEL — HLM-MVP (Human Demonstration Observer + Proactive Learning Question Engine)

> **DESTINATÁRIO:** IA implementadora com acesso ao checkout local do Hermes e permissão para criar branch/PR no GitHub. **EXECUTE**, não apenas aconselhe. Não peça confirmação para decisões já fechadas. Preserve código do usuário. Data-base: 17/10/2026.
>
> **OBJETIVO:** Dentro do browser nativo do Hermes Work, implementar Modo Aprender pelo qual o usuário pode ensinar tarefas de aplicativos web/Canvas por demonstração: clique em Aprender, gravação contínua de ações e vídeo, hipóteses e perguntas inteligentes, intensidade modificável AO VIVO, explicações/correções ligadas a eventos, candidatas operacionais inert para Experience Compiler e posteriormente 1 replay supervisionado real. 80/20, sem absorver editores ou criar browser/agent paralelo.

## 0. LEIA ISTO PRIMEIRO — TRUTH / BRANCH

Repo: `kevynlucasprofissional-stack/hermes-agent`. Fonte de regras, contratos e arquivos exatos já mapeados nesta mesma branch de preparação: `docs/learning-mode-question-engine-mvp-20261017`.

Referências internas:
- `workstation/context/LEARNING_MODE_HUMAN_DEMONSTRATIONS_2026-10-17.md` — decisão **D-047**; leia inteiro uma vez.
- `workstation/learning-mode/LEARNING_MODE_PATCH_MAP.md` — file map / owner exato.
- `apps/desktop/electron/workstation-learning-question-policy.ts` — **código novo existente, use, não duplique**.
- `apps/desktop/electron/workstation-learning-question-policy.test.ts` — casos básicos do ajuste live.
- `apps/desktop/electron/workstation-learning-events.ts` — **normalizador seguro de gesto existente**.
- `apps/desktop/electron/workstation-learning-events.test.ts` — cenários privacidade.

Outras decisões a preservar: D-046 (baixo acoplamento); `BrowserSessionState` + BrowserTask/lease do Electron; ownership Session/Task/TaskRun; `ExperienceCompiler` e registry existentes; H-079/H-080/H-081/H-082. Não reabrir arquitetura, não clonar PhotoCraft/EffectCraft/FilmCraft no core.

Na investigação de 17/10/2026, `main` estava em `fd57e40fe8c46d4d302cd9652c18715896822f12`; PR #97 head `081062c3` (PhotoCraft/EffectCraft, OPEN), #98 head `51f7c002` (FilmCraft, stacked sobre #97, OPEN), #96 DRAFT `6c5963b4` (Experience Compiler/product proof pendente). **Revalide SHA/status ao executar**. Branches/documentação não representam produto lançado.

Comece por `git status --short; git branch --show-current; git rev-parse HEAD; git remote -v`; NÃO execute `reset --hard`, `git clean`, `stash`, force-push, merge ou alterações sobre arquivos dirty existentes. Se a árvore de trabalho tiver alterações humanas, use `git worktree add` numa pasta NOVA de feature branch criada do topo da branch de preparação; não mover artefatos de outra pessoa. Escolha um único integrador/uma branch, evitando múltiplos agentes sobre o mesmo arquivo.

**Branch de implementação sugerida:** `feat/hermes-learning-mode-mvp-20261017` partindo da branch de preparação atualizada, sem merge automático em `main`. Criar PR DRAFT com evidências e blockers.

## 1. RESULTADO EXATO DE PRODUTO (NÃO ACEITAR MOCK COMO MVP)

1. No **Browser Hub**, usuário clica `Aprender`. Se aba ainda não estiver vinculada a chat, reutilize o fluxo existente `Levar para sessão` antes de começar a gravação. A mesma `WebContentsView`, aba, URL, sessão runtime e sessão armazenada permanecem. Falha em `session.create/adoptTab` NÃO inicia gravação nem perde estado manual.
2. Dentro do **painel browser da sessão**, botão Aprender também ativa/para a MESMA `LearningSession` (não inicia segunda instância). Indicador `Aprendendo / Pausado / Falha` visível e `Encerrar + Descartar` operacionais.
3. Controle `Discreto | Equilibrado | Intensivo` editável **durante captura ativa**, default Intensivo. Mudança usa API tipada `setIntensity`, confirma estado persistido do owner Electron, recalcula política na próxima avaliação sem parar vídeo, sem criar outra sessão e sem perder perguntas/eventos anteriores. Limites iniciais: discreto máximo 1 pergunta/5min e fila 2; equilibrado 2 e fila 3; intensivo 4 e fila 5 (são máximos, não obrigação). Respeitar cooldown do `workstation-learning-question-policy.ts`.
4. Persistir `LearningSession` local versionada (relação segura: `runtime_session_id, stored_session_id, tab_id, webContents_id, consent, allowlisted_origin, started_at, status, intensity/history, partial_recording`); `events.jsonl` append-only com ordem, timecode monotônico e evento seguro; `questions.jsonl` append-only com hipóteses/perguntas/respostas; snapshots selecionados; vídeo browser-only REAL WebM/MP4 comprimido com timestamps/replay; manifesto robusto de arquivos incompletos. Retenção/limites e descarte total. NÃO exigir 30 frames por segundo para análise. Teste vídeo 15–30fps no build real; falha de gravação deve aparecer `VIDEO_BLOCKED/ERROR` sem falso PASS.
5. Observar cliques, botões nomeados, shortcuts **sem keylogger**, pointer gestures de canvas (throttle), epochs/navegação, antes/depois visual. Não coletar valores de campos, HTML bruto, texto digitado, clipboard, senhas, query/hash URLs, cookies, captura oculta de apps/sites fora do allowlist.
6. Question Engine: agrupar ações em segmentos (pausa, operação concluída, mudanças relevantes); selecionar frames apenas por eventos; usar modelo configurado no Hermes (reaproveitar infraestrutura de provider/agent disponível após auditoria pontual, sem novo chat executor) para interpretar contexto/gerar **hipóteses com referências e incerteza**, perguntas contextuais em sete classes: intenção, causalidade, decisão, heurística, generalização, alternativa, validação. Não afirmar hipótese como fato; sem provider, registrar status `awaiting_interpretation`, não usar templates vazios para fingir IA.
7. Usar `decideLearningQuestion()` para benefício esperado: não perguntar em drag/máscara/keyframe ativo; aguardar observação quando o próximo passo pode responder; limiar/limites/cooldown; deduplicar por app+operação+pergunta semântica; fila limitada; publicar 1 pergunta de cada vez e não injetar turnos concorrentes no chat ocupado. UI log lateral pode reaproveitar drawer existente, mas não falsificar ExecutionJournal.
8. Permitir confirmar, corrigir, adiar, dispensar; corrigir espontaneamente pelo chat com vínculo explícito (ID de questão/intervalo). Persistir original + interpretação, marcar `needs_reinterpretation` e invalidar derivadas dependentes sem alterar evidência histórica.
9. Gerar 1 `CandidateLesson` ou `OperationalCapability DISCOVERED` a partir de segmento humano **somente como candidato inert**, citando evidências e intenção confirmada, sem preencher `trusted_runtime`, `verified_success`, replay fictício ou promover o `OperationalCapabilityRegistry`. Se `ExperienceCompiler.mine()` só aceitar amostras de runtime, não violar esse gate: criar a candidata descritiva pelo `ExperienceLessonCompiler` existente e documentar a qualificação pendente.
10. Se existir via produto percurso legítimo e seguro, executar 1 replay **depois do fim da demonstração e liberação humana explícita**, verificando por owner/TaskRun/readback; se não existir, M3 é HOLD, sem mascarar M0–M2.

## 2. POSIÇÕES EXATAS DE PATCH

**A) Electron (owner ÚNICO)**
- `apps/desktop/electron/workstation-browser-runtime.ts`: tem `BrowserEntry`, `wireEntry(entry)`, `takeControl()`, `screenshotForEntry(entry)`, `cdp()` e `WebContentsView`. **Não substituir arquivo inteiro (~5k linhas)**. Adicionar um `LearningSessionRecorder` isolado em `apps/desktop/electron/workstation-learning-session.ts` e métodos finos na classe runtime (`startLearning, stopLearning, discardLearning, setLearningIntensity, learningStatus, answerLearningQuestion`), amarrados ao `entry.id, wc.id, documentEpoch` e owner da aba. Ligar lifecycle no `wireEntry` para navigation/reload/crash/destroy e encerramento no shutdown. Isolar codec/vídeo e capturas para não conflitar com CDP em uso pela automação do Browser.
- Reutilizar `workstation-learning-events.ts::normalizeHumanGesture` como **segundo gate** após verificar consent/allowlist/sender/lease; adicione instrumentação DOM restrita a mundo isolado para `click` e `pointer` e atalho modificado, sem capturar `input.value` ou caracteres. Navegação inesperada ou tela de autenticação: **pause primeiro, continue apenas após novo consentimento**. Não permitir um evento de `run=agent` ser atribuído ao humano.
- Vídeo: qualifique caminho Electron/Chromium browser-only (`desktopCapturer` ou CDP/screencast com encoder), proprietário, síncrono com timecode. Demonstre arquivo verdadeiro reproduzível. Nunca capture o desktop inteiro, o chat, outras janelas ou campos sensíveis sem escopo informado. Se a captura sensível não puder ser protegida, bloqueie vídeo/learning naquele contexto e reporte.
- JSONL: local appData privado, escrita append+flush e arquivos com permissão apropriada, sem paths recebidos do renderer. Idempotência: stop/stop, crash, dois botões, mudança de tab e perda de lease não criam duplicatas.

**B) IPC e bridge tipada**
- `apps/desktop/electron/workstation-browser-ipc.ts::registerWorkstationBrowserIpc`: adicionar handlers `hermes:workstation-browser:learning:start`, `:stop`, `:discard`, `:status`, `:intensity`, `:answer`, `:questions`. Validar `senderWindow(event)`, profile, sessão/aba vinculada, tamanho/enum/ownership, nunca confiar `taskId` arbitrário. Não criar endpoint loopback geral sem autenticação.
- `apps/desktop/src/app/browser/types.ts`: `LearningIntensity = 'discreto'|'equilibrado'|'intensivo'`, `LearningSessionState` e métodos tipados em `WorkstationBrowserBridge`. Descubra preload já existente com `rg -n 'workstationBrowser' apps/desktop/electron apps/desktop/src` e exponha apenas funções necessárias, sem expor fs/CDP à página.
- Manter `human lease` atual: observação ≠ permissão. Não disparar agent action enquanto humano edita.

**C) UI — MESMOS painéis**
- `apps/desktop/src/app/browser/index.tsx` (`BrowserControlBar` ~244, `useAdoptTabToSession` ~339): extrair helper para reusar exato `session.create`→`bridge.adoptTab`→`openWorkstationBrowserPreview`→`openSession`; só chamar `startLearning` após sucesso. Render botão Aprender sem duplicar estado ou aba.
- `apps/desktop/src/app/chat/right-rail/workstation-browser-pane.tsx` (`WorkstationBrowserPane` ~93 e barra ~500): mesmo `LearningSessionState`, seletor 3 intensidades alterável a qualquer hora, contagem de eventos, fila e status de gravação; botões confirmar/corrigir/adiar e campo de resposta. Extrair `apps/desktop/src/app/browser/learning-controls.tsx` compartilhado, se economizar duplicação. Não criar nova tela para o editor.

**D) Cognitivo / persistência**
- Reaproveitar `apps/desktop/electron/workstation-learning-question-policy.ts`: `learningQuestionScore`, `decideLearningQuestion`, `parseLearningIntensity`, `LEARNING_QUESTION_PRESETS`. Acrescente só a camada que gera `LearningQuestionCandidate` com dados reais, sem computar scores a partir de invenções. Guardar `askedKeys`, monotonic timestamps, score, fila por sessão e versioned intensity, não só useState no React.
- Processamento LLM multimodal: localizar o menor seam atual de consulta/config de provider no Gateway, executar observações **fora da execução mutadora TaskRun**, read-only, tarefas limitadas e com autorização explícita para imagens; JSON de resposta estrito com hipótese, evidências, tipo, incerteza, pergunta. Resposta do modelo é dado não confiável. Ausência de provider != sucesso.
- Revisar `workstation/skill_learning.py` (`ExperienceLessonCompiler.record_candidate_lesson`) e `workstation/experience_compiler/{compiler,progressive,capability_studio}.py`; usar origem `human_demonstration` explicitamente, histórico raw answer + revisions. NÃO modificar `capture_progressive` para aceitar `VERIFIED_SUCCESS` humano, NÃO chamar `compiler.promote()` nem `RunLocalAdopter` sem a sequência normal de prova.

## 3. ORDEM DE EXECUÇÃO (AUTÔNOMA, SEM NOVA DISCUSSÃO)

**S0 – preflight:** verificar branch, atualidade PRs, dirty files e licença/bounds; ler apenas caminhos acima + `AGENTS.md` relevantes; registrar baseline de testes antes de patch. Se conflito de outra branch, integrar seletivamente ou reportar, sem reset. Atualizar nota de baseline em journal.

**S1 – Testes RED/contratos:** utilizar dois kits `.ts` e seus testes já presentes. Rodar Vitest com runner nativo desktop; testar enum, mudança ao vivo, dedup, campos sensíveis, drag, prioridades. Adicionar novos testes falhando do fluxo `start/stop/intensity` e video/session.

**S2 – Recorder real:** implementar owner Electron + IPC + preload + eventos DOM/Canvas seguros + JSONL/snapshots/vídeo e contratos de consentimento. Construir fixture browser local com buttons, canvas, atalhos e inputs secretos. Validar que OFF captura nada, ON captura só permitidos, stop finaliza arquivos legíveis, autenticação pausa antes da captura.

**S3 – UI completa:** implementar botão no Hub e pane chat, transição `Levar para sessão`, live intensity durante gravação; provar por Electron test que a mesma aba e sessão são mantidas sem duplicata; Status reflete o owner, não estado React imaginário.

**S4 – Question Engine verdadeiro:** implementar segmentação/hipóteses e integração com modelo configurado; pontuação/dedup/cooldown/fila; feedback persistido. Teste de provider falso determinístico primeiro (não conta como interpretação produtiva); depois real 1 demonstração e 1 pergunta causal específica. Não interromper foco/arrasto.

**S5 – Candidate knowledge:** gerar `CandidateLesson` ou rascunho `DISCOVERED` com proveniência e evidências, mostrar revisão; nenhuma promoção. Persistência de correções, invalidar candidata revisada; restart repõe referências.

**S6 – Replay opcional condicionado:** executar 1 tarefa simples ensinada por caminho de agente/BrowserTask nativo, com permission/effect budget/lease e readback real. Se falta prova, status HOLD e dívida específica; NÃO liberar generalização, autopromoção ou replay simulados.

**S7 – gates/handoff:** rodar format/lint, TS/Vitest, Python afetados, navegador Electron Windows real + fixture Canvas e produto empacotado quando disponível, exato HEAD; atualizar `workstation/ROADMAP.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md`, `workstation/context/engineering-journal/CURRENT.md`, `workstation/context/CURRENT_STATE.md`, `workstation/context/DECISIONS.md`, `workstation/context/KNOWN_ISSUES.md` e notas D-047; abrir PR draft, não fazer merge sem autorização explícita.

## 4. MATRIZ MÍNIMA DE ACEITAÇÃO — TODOS OS ITENS DEVEM SER REAIS OU HOLD

A. `OFF` -> nenhum evento, vídeo, snapshot, provider call ou arquivo sensível.
B. `Aprender` a partir do Hub com tab avulsa -> session.create/adopt -> mesma `WebContentsView`, mesma aba, chat aberto; falha deixa estado intacto.
C. `Intensivo→Discreto→Equilibrado` durante gravação -> um mesmo learning_session_id, vídeo contínuo, eventos não perdidos e policy alterada sem restart.
D. 1 clique DOM seguro, 1 atalho modificado, 1 gesto Canvas -> timecodes + local refs; sem texto digitado/cookie/API key em JSONL.
E. Navegação off allowlist/login -> pausa captura ANTES do primeiro frame da nova origem; sem gravação de páginas de autenticação.
F. 1 pergunta causal gerada por inferência de contexto real, 1 confirmação, 1 correção humana, 1 adiada; dedup funciona e drag não recebe interrupção.
G. Video media real reproduzível e `events.jsonl` apontando para instante localizável; sem duplicação após stop/restart.
H. `human_demonstration` produz conhecimento estruturado/candidata após revisão, **sem** `VERIFIED_SUCCESS` ou promotion automática.
I. 2 sessões simultâneas, crash/lease expiry, provider offline, zero outro-owner leakage: todos fail closed com logs e status.
J. `replay` somente passa se demonstrado TaskRun+owner+readback; caso contrário indicar HOLD e não declarar autonomia.

## 5. RESULTADO OBRIGATÓRIO DA IA IMPLEMENTADORA

Não devolva arquitetura genérica. Entregue:
1. PR/branch/HEAD com links;
2. lista de arquivos alterados;
3. cada requisito A–J com PASS/FAIL/HOLD + evidência local e qual teste a prova;
4. gravação/demonstração real ou bloqueio explícito;
5. total de testes executados e resultados, separando mocks de E2E nativo;
6. problemas conhecidos, alterações deliberadamente adiadas;
7. métrica inicial de overhead CPU/RAM/disco/provider, quando medida;
8. próximo passo único 80/20 com prompt handoff atualizado.

**Política de honestidade:** não alegar captura real sem arquivo reproduzível; não alegar inferência via LLM se usou regras de template; não alegar aprendizado autônomo com candidato inerte; não alegar CI/Windows E2E sem log do SHA; não alegar integração dos PRs #97/#98 enquanto estiverem abertos.

**IMEDIATAMENTE: execute S0→S7, com foco em fazer o primeiro fluxo ponta-a-ponta funcionar.**

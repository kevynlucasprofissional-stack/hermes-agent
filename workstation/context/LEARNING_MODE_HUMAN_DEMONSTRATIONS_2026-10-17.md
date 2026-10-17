# D-047 — Hermes Learning Mode: ensino operacional por demonstração humana (2026-10-17)

**Status:** DECISÃO DE PRODUTO ACEITA; preparação de documentação + política de perguntas INERTE em branch. **Não** há captura, vídeo, LLM, UI, Skill ou compilação de demonstrações conectados no produto por esta entrega. A referência canônica é a `main` `fd57e40fe8c46d4d302cd9652c18715896822f12`, conferida em 17/10/2026. PR #97 (PhotoCraft/EffectCraft) e PR #98 (FilmCraft, stacked sobre #97) estão abertos e fora de main.

## 1. Objetivo, não objetivos e medida de valor

Human Demonstration Observer observa o operador dentro do **mesmo Browser Electron Chromium**, enquanto Proactive Learning Question Engine formula hipóteses e pergunta em momentos valiosos para extrair intenção, causalidade, heurísticas, alternativas e critérios de sucesso. Segmentos observados + diálogo tornam-se material para `ExperienceCompiler` e `OperationalCapabilityRegistry` existentes. Não criar outro navegador, outro agente executor, outra DB de capacidades, clone interno de editor, motor workflow ou novo sistema de autoridade.

Fluxo: operador demonstra -> evento humano com origem e tempo -> evidência local (JSONL+video+snapshots seletivos) -> segmentação -> hipótese -> questionamento -> resposta/correção -> candidata **inert/discovered** -> futuro replay por runtime proprietário, validação e promoção pela política existente.

**Métrica primária:** tarefa humana ensinada reproduzida mais tarde pelo agente com *readback independente* e resultado verificado, sem intervenções; métricas intermediárias são taxa de segmentos interpretados/corrigidos, perguntas úteis, duração/atraso, custo de provider e gravador, volume de dados, fallbacks e taxa de candidatos considerados. Nunca equivaler perguntas, gravações ou testes sintéticos a autonomia adquirida.

## 2. Invariantes de segurança / hierarquia de autoridade

- `LearningSession` é **observacional**, vinculada a `runtime_session_id`, `stored_session_id` e `browser_tab_id/webContents.id`; pode existir sem Task/TaskRun. Não criar Kanban automaticamente no ato de aprender.
- Posse humana segue `BrowserTaskLifecycle` / `BrowserSessionState` / lease; o Learning Mode não concede permissão ao executor, nunca dispara `browser_*` mutador durante gravação. Renovar lease apenas pelo mecanismo proprietário autorizado, não criar token alternativo.
- `human_demonstration` nunca vira `VERIFIED_SUCCESS` em `capture_progressive` por rótulo do usuário/modelo. `ExperienceCompiler` existente e `ExperiencePromotionPolicy` continuam donos da transformação para capacidades promovidas.
- D-046 prevalece: apps independentes abertos no Browser; adapters somente-leitura limitados por gargalo comprovado.
- Gravação **OFF** inicialmente; opt-in consciente + indicador persistente + Stop/Discard + seleção explícita de escopo/aba/origem. Não registrar campos de texto, passwords, inputs, clipboard, cookies, dados de credenciais, HTML bruto, tokens, query/hash de URL, nem conteúdo de apps fora da lista permitida.
- Captura de vídeo/screenshot pode conter segredos que sanitização DOM não alcança. Bloquear navegações para domínios/path de autenticação e escopos não autorizados; **pausar antes de capturar** quando origem mudar; não enviar vídeo/frames para provider remoto por default; oferta visual remota separada requer consentimento informado. Não presumir que redaction heurística torna captura indiscriminada segura.
- Mesma aba e mesmo `WebContentsView` antes/depois do handoff `Levar para sessão`. Falha de Gateway/adopt deve deixar tab intocada e aprender OFF; jamais fabricar id.
- Falha do recorder, do encoder, do LLM ou do compilador deve resultar em status explícito, sem mutação, sem dados “verificados” fabricados e com recuperação segura.
- Uma pessoa só pode ativar uma demonstração da aba num dado momento; bloquear captura de outras janelas, abas de terceiros e múltiplos owners.

## 3. Intensidade ao vivo — DECISÃO ACEITA

Três níveis: `discreto` (0–1 perguntas/5min, fila 2), `equilibrado` (até 2/5min, fila 3), `intensivo` (até 4/5min, fila 5). Default para nova LearningSession **intensivo**. Esses números são limites experimentais, não quotas compulsórias. Score heurístico, novas evidências e cooldown determinam efetiva frequência. A intensidade pode ser alterada **enquanto o vídeo/recorder está ativo**; alterações versionadas na mesma LearningSession mudam imediatamente limiar, ritmo e fila futura, sem reabrir abas, resetar eventos, reter permissões extras ou reenviar inferências canceladas.

Política reutilizável preparada no repositório: `apps/desktop/electron/workstation-learning-question-policy.ts` e testes `.test.ts`. É **inert/unwired**, ainda sem validação de suite real. Um motor proprietário do LearningSession deve consumir `decideLearningQuestion()` e se responsabilizar pelo controle das perguntas, estado atômico, persistência, debounce/dedupe e scheduling. Intensity NÃO influencia autorização a efeitos nem FPS de gravação; são dois controles distintos.

## 4. Question Engine — objetivos cognitivos

Tipos: intention, causality, decision, heuristic, generalization, alternative, validation. Prioridade para causalidade, decisão e validação. Perguntar em resposta a **sequência e mudança de estado**, não a clique isolado. Gerar hipótese acompanhada de incerteza e fonte; não afirmar objetivos pessoais sem evidência.

`learning_question.v1` deve incluir: id, learning_session_id, browser_tab_id, ordered event_ids, from_ms/to_ms, safe snapshot refs, categoria, hipótese + score calculado como heurística, pergunta proposta, `pending|confirmed|corrected|deferred|dismissed`, resposta bruta explícita, versão de interpretação, candidate_refs e `needs_reinterpretation`. Correções humanas invalidam derivações associadas, mas não silenciosamente reescrevem a evidência original.

Quando arrasto/desenho/keyframe edit ativo, **enfileirar e não interromper**. Em pausas naturais, perguntar o que só um especialista pode esclarecer. Uma mudança observada em seguida pode resolver a ambiguidade sem questionar. Deduplicar por fingerprint semântico incluindo família da operação/contexto, não por texto literal de pergunta. Nunca gerar uma avalanche de turnos no chat, sobretudo quando o chat está ocupado; apresentar cartões num log lateral e encaminhar respostas ao contexto persistente.

## 5. Captura / armazenamento mínimo

`learning_session.json`: schema/version/consent/versioned intensity/owner/bound ids/allowlisted origin/status/started_at/ended_at/video status; `events.jsonl`: eventos seguros com `event_id, tab_id, document_epoch, monotonic_time_ms, category, safe selector/role/name, x,y normalized, button/key combination, evidence refs, actor=human`; `questions.jsonl`: append-only state transitions (não sobrescrever histórico); `media/recording.webm`: vídeo local comprimido com timestamp sincronizado; `snapshots/`: keyframes seletivos; `summary.md`: gerado opcionalmente e sempre revisão humana antes de publicar.

Captura DOM: usar scripts de observação no mundo isolado, capturar interação em `capture` phase de eventos que efetivamente atinjam o DOM, sem registrar `input.value` ou texto digitado. Registrar atalhos por combo controlado, sem keylogging caractere a caractere. Canvas/WebGL: registrar coordenadas normalizadas e ações pointer (down/move throttled/up) com before/after screenshots; declarar target semântico `unknown` quando DOM não permitir inferir; sem inventar objeto editado. Iframes e páginas com CSP/isolamento: suportar quando autorizado e mensurável; caso contrário evidenciar a limitação.

Vídeo: preferir captura somente da superfície do browser e compressão contínua (teste real de possibilidade CDP screencast/captura equivalente). 15–30fps é referência para vídeo, **não** 30fps para inferência. Seleção de imagens por mudanças; nunca exportar 108k quadros/hora por default. Forçar encerramento, flush e manifest em stop, crash/restart, navigation off-allowlist, profile logout ou revogação de consentimento. Gravação parcial deve ser identificada como tal. Limitar quota/retention local.

## 6. Fases do MVP

**M0 captura real**: Browser Hub + Chat Browser pane botão Aprender; start/stop/discard com real tab identity e handoff idempotente; intensidade ajustável em tempo real; mínimo DOM+pointer+shortcuts+JSONL+timestamps; vídeo real browser-only ou bloquear conclusão com blocker explícito; sem capturar dados privados. Gate: 1 demo end-to-end, evento buscado no vídeo, stop/restart seguro.

**M1 interpretação**: segmentar por janela e mudança de estado; usar snapshots seletivos; modelo configurado pelo Hermes existente (não SDK/provider paralelo), perguntas baseadas em hipóteses e ganho de informação, log vivo, 7 tipos; responder/confirmar/corrigir/adiar; evidenciar qual modelo foi efetivamente chamado. Gate: 1 pergunta causal pertinente e 1 correção altera interpretação e suprime duplicata, sem interromper drag.

**M2 candidatas**: gerar `human_demonstration` scoped candidate lesson ou `OperationalCapability` discovered/review-only usando seams existentes; colocar em projeção de revisão; sem `VERIFIED_SUCCESS` sintético. Gate: candidata recuperável após reiniciar, com refs de evidência e sem capacidade mutadora promovida.

**M3 prova supervisionada**: 1 replay do Browser por executor canônico (lease liberado conscientemente), verificação real e comparação com a demonstração; registrar se passou/falhou/inconclusivo. Gate: sucesso somente com readback/owner/TaskRun exatos, evitar duplicar efeitos; se não existir caminho autêntico, HOLD transparente e terminar M0–M2 sem falsificar PASS.

Não bloquear M0–M2 em LAYA, EmbeddingGemma 2, modelo vetorial, FilmCraft, adaptação profunda de Canvas, loop geral de melhoria ou nova UI. Essas opções são posteriores ao vertical funcional.

## 7. Referências de implementação

- `apps/desktop/electron/workstation-browser-runtime.ts`: BrowserEntry, `wireEntry()`, `takeControl()`, screenshotForEntry/cdp helpers, tab document epoch; observar *sem substituir* execução.
- `apps/desktop/electron/workstation-browser-ipc.ts`: validar caller, criar `learning:start|stop|status|set-intensity|answer|discard` com owner/auth e argumentos tipados; não aceitar caminhos de arquivos do renderer.
- `apps/desktop/src/app/browser/index.tsx`: BrowserControlBar + `useAdoptTabToSession` já mantém runtime_session_id e stored_session_id sem criar aba duplicada.
- `apps/desktop/src/app/chat/right-rail/workstation-browser-pane.tsx`: Learning toggle + live-intensity selector + log/discussão.
- `apps/desktop/src/app/browser/types.ts` + bridge preload (localizar por `workstationBrowser`): contratos tipados.
- `workstation/experience_compiler/{compiler,progressive,accepted_observer,capability_studio}.py` e `workstation/operational_capabilities.py`: a validação/promos existentes não podem ser suplantadas.

Prioridades anteriores preservadas: D-046, H-079, H-080, H-081/082, PRs #96/#97/#98 independentes; não alegar merge, release, qualificação E2E nem economia sem recibos.

## 8. Fonte primária deste registro

Briefing humano de 2026-10-17 e conversa de detalhamento do Hermes Question Engine até 11:25 BRT; repositório main `fd57e40` e heads PR #97 `081062c3`, #98 `51f7c002`, #96 `6c5963b4` revisados. Implementador tem handoff executável em [LEARNING_MODE_MVP_IMPLEMENTER_PROMPT.md](../learning-mode/LEARNING_MODE_MVP_IMPLEMENTER_PROMPT.md).

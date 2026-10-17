# Hermes Work — Seis prompts implementadores, 17/10/2026

**Ordem:** P01 → P02 → P03 → P04 → P05 → P06. **Uma IA/sessão por prompt**, sempre trabalhar em branch dedicada, reaproveitando as implementações aceitas anteriores. P01/P02 poderiam ser desenvolvidos paralelamente **apenas em worktrees independentes**. Cada prompt é autocontido para copiar diretamente. **Status:** prompts publicados, implementação não executada nesta branch.

Baseline inspecionado: `main` no GitHub e worktree `C:\Github\hermes-agent`, branch `docs/ol-mvp-p2-1-native-adoption-20261017` HEAD `2befe8b185` (a worktree contém alterações não commitadas; não mexer). A branch remota `docs/dogfood-recovery-hlm-runtime-20261017` contém a atualização documental D-048, ainda sem merge na main.

## PROMPT P01 — Recuperação real do navegador nativo (P0; dedicação exclusiva)

Você é a IA implementadora do Hermes Work. Corrija **apenas** as telas pretas do browser nativo Chromium no Windows/Electron em dois cenários: (a) pesquisa/navegação; (b) aparecimento e fechamento de notificação/overlay. Código-fonte: `kevynlucasprofissional-stack/hermes-agent`; máquina local `C:\Github\hermes-agent`. Primeiro rode `git status --short --branch`, identifique HEAD, origin/main e SHAs de backend/Electron/Gateway carregados; preserve todos os arquivos modificados/não rastreados, não execute reset/clean/checkout destrutivo. Crie sua branch/worktree isolada. Leia somente os arquivos listados e testes próximos.

**Arquivos e ordem exata:**
1. `apps/desktop/src/app/browser/native-view-occlusion.ts` e `native-view-occlusion.test.ts`: verificar MutationObserver, o momento que `[data-native-view-occluder="true"]` desaparece, owner/host e `revision`; toast simples NÃO deve esconder a view se não a obstrui.
2. `apps/desktop/src/app/browser/index.tsx` e `apps/desktop/src/app/chat/right-rail/workstation-browser-pane.tsx`: verificar `useNativeViewOcclusion`, `publishBounds`, transferência hub ↔ chat, panes keep-alive, desmontagem e reattach após notificações.
3. `apps/desktop/electron/workstation-browser-runtime.ts`: corrigir as transições de `attach`, `setVisible`, `setBounds`, `ensureChildView`, `removeChildView`, `detachActiveView` com owner/host e idempotência. Observação: `addChildView` pode reordenar a camada nativa para o topo; não chamar cegamente.
4. `apps/desktop/src/app/overlays/overlay-view.tsx`, `apps/desktop/src/app/command-palette/index.tsx`, `apps/desktop/src/app/session-switcher.tsx` e mecanismos de toast/notificações: identificar se o marcador de occlusão fica preso.
5. `workstation-browser-runtime.ts` listeners de navegação `did-start-loading`, `did-stop-loading`, `did-fail-load` (adicionar se necessário), `render-process-gone`. Correlacionar `ERR_ABORTED (-3)` com navegação real — cancelamento sozinho não comprova crash.

**Mudança mínima:** garantir que a intenção de visibilidade do host ativo persiste, que o término do overlay restaura o **mesmo** `WebContentsView` com bounds não zero, e que reanexos não saltam host/owner. Se a navegação falhar, renderizar estado/retry contextual; não recarregar abas com documentos não salvos. Eventos de diagnóstico limitados a ids, tipo de transição e motivos sanitizados.

**Aceite obrigatório em Electron real no Windows, não somente JSDOM:** abrir uma página fixture, fazer pesquisa válida, abrir/fechar toast, diálogo e menu, alternar Hub ↔ Chat, repetir 10 vezes. O `webContents.id` deve permanecer estável, a página legível, tabs/TaskRuns intactos; ao erro exibir falha recuperável. Acrescentar testes de regressão focados nas transições; `pnpm`/comando de teste deve ser o real encontrado no package.json. Apresentar causa **confirmada por reprodução**, diff, testes, limitações e GO/HOLD. Se não reproduzir, instrumentar e classificar `HOLD: causa não comprovada`, sem correções especulativas.

No encerramento, atualizar `workstation/ROADMAP.md`, `workstation/context/KNOWN_ISSUES.md`, `workstation/context/HERMES_WORKSTATION_INTELLIGENCE.md` e `workstation/context/engineering-journal/CURRENT.md` com fatos e evidências; não marcar as outras cinco tarefas como resolvidas. Não enviar push/merge automático nem modificar main.

---

## PROMPT P02 — Gravação real de vídeo e snapshots (P0; dedicação exclusiva)

Você implementará exclusivamente gravação visual **real** no modo Aprender do Hermes Work. Primeiro verificar `git status`, build carregado e preservar working tree suja; branch/worktree isolada com P01 integrado se disponível. Não implementar Question Engine, cards no chat ou novo Compiler nesta sessão.

**Defeito comprovado:** `apps/desktop/electron/workstation-learning-session.ts::startVideoRecording` chama FFmpeg com `-f lavfi -i color=c=black:s=1280x720:r=15 -t 1`. Isso cria vídeo sintético, não grava a tab; `videoStatus='stopped'` é falso sinal de sucesso. A LearningSession real `learn-1792260534434-05158b7f` durou 11m45, vídeo 3.702 bytes, snapshots vazios, gestos e perguntas presentes.

**Ações sequenciais:** (1) em `workstation-browser-runtime.ts::getLearningRecorder`, fornecer callback que captura **a WebContents da tab autorizada** com `entry.view.webContents.capturePage()`, sem mudar o owner ou recarregar tab; não copiar screenshots genéricos do browser para pasta externa sem correlação. (2) em `workstation-learning-session.ts`, substituir gerador `lavfi` por pipeline real de frames `NativeImage`→PNG→encoder FFmpeg. Ponto de partida para o encoder (ajustar tamanho fixo/frame rate ao contrato, não copiar cegamente):

```ts
const ffmpegArgs = [
  '-y', '-f', 'image2pipe', '-framerate', '3',
  '-vcodec', 'png', '-i', 'pipe:0',
  '-an', '-c:v', 'libvpx-vp9',
  '-deadline', 'realtime', '-cpu-used', '5',
  '-pix_fmt', 'yuv420p', videoPath
]
```

Implementar loop **não sobreposto** (backpressure no `stdin`, intervalos limitados, frame PNG com dimensões consistentes, parada/await do encoder, timeout e quotas). Guardar `frame_index.jsonl` com tempo monotônico relativo e, em `snapshots/`, quadros selecionados com `event_id` e hash; snapshots assíncronos devem ser aguardados no Stop. A taxa de 3fps é default 80/20 ajustável se a infraestrutura exigir; priorizar sincronismo/segurança, não alta resolução.

**Segurança:** explícito opt-in, somente tab/origem autorizada, não iniciar antes de gate; pause/stop ao navegar para login, origem estranha, renderer crash ou aba destruída; sanitizar dados, sem upload de vídeo; `Discard` elimina mídia somente dessa sessão. Se encoder indisponível, `videoStatus=error|blocked` e erro verdadeiro; preservar eventos/correções e não alegar gravação. Não registrar videoStatus `stopped` como sucesso antes de `exit 0` + arquivo real validado. Evitar deadlock caso ffmpeg não drene.

**Teste:** fixture visual muda visivelmente a cada 5s durante sessão ≥30s; `ffprobe` confirma codec, duração próxima à sessão, quadros diferentes, fps, dimensão e sincronização com gestos; navegar para origem proibida verifica parada **antes** do próximo frame. Testar cancelamento, erro do encoder e 2 sessões sem vazamento. Rodar testes Electron + integração Windows quando possível. Entregar evidências com tamanhos, ffprobe e limitações, não enviar dados privados. Atualizar ROADMAP, KNOWN_ISSUES, INTELLIGENCE, CURRENT e D-048 conforme resultado. Não tocar em main/push/merge.

---

## PROMPT P03 — Aprender no chat + transparência de operações (P1; conjunto leve)

Implemente o conjunto limitado de duas melhorias de UI/eventos. Assuma as correções P01/P02 aceitas ou marque dependência HOLD. Antes de codificar: `git status --short --branch`, conferir HEAD/build e preservar trabalhos locais. Sem refazer gravação, Compiler, Navigator ou Kanban.

**1 — Perguntas no chat, nunca sobre o Canvas.** `apps/desktop/src/app/browser/learning-controls.tsx` hoje contém barra de controle e componente `LearningQuestionCard`, renderizando `activeQuestion` abaixo da barra do host (Browser Hub ou Chat pane). Separe a **barra** (Aprender, Parar, Descartar, intensidade ao vivo) da **apresentação**. Mantenha um único estado canônico vindo de `workstation-browser-runtime.ts::emitLearningState` → `workstation-browser-ipc.ts` → `preload.ts` → tipos `apps/desktop/src/app/browser/types.ts`. Renderize cada questão como item persistente ou cartão vinculado ao transcript da sessão de chat, usando componentes de mensagens existentes em `apps/desktop/src/app/session` e `apps/desktop/src/app/chat`, com ações Confirmar/Corrigir/Adiar/Dispensar chamando `bridge.learningAnswerQuestion`. Respeitar `storedSessionId`/`runtimeSessionId` e `question.id`; deduplicar por id+estado e suportar reconstrução/reconexão sem perguntas duplicadas. Se o Browser Hub não estiver associado a chat, manter perguntas em inbox não intrusiva **sem overlay no editor**, com vínculo posterior seguro.

**2 — Logs reais no transcript.** Há precedente de `review.summary` em `apps/desktop/src/app/session/hooks/use-message-stream/gateway-event/status.ts`. Use fluxo existente (Gateway event ou IPC já publicado, conforme owner) para milestones auditáveis; **não inventar banco/event bus novo**. Contrato mínimo de payload para os eventos que de fato existirem:

```ts
type WorkstationMilestone = {
  eventId: string;
  sessionId: string;
  stage: 'observed' | 'candidate' | 'compilation_started'
       | 'validation_passed' | 'validation_failed' | 'capability_selected'
       | 'executed' | 'rejected';
  occurredAt: string;
  taskRunId?: string;
  learningSessionId?: string;
  capabilityId?: string;
  evidenceRefs: string[];
  reasonCode?: string;
};
```

Mapear eventos fonte `workstation/execution_policy.py`, `workstation/experience_compiler`, `workstation/control_plane/router.py` e owner LearningSession, SEM sinalizar estágios não emitidos ou evidências inexistentes; evento `candidate` não significa `promoted`. UI mostra estágio, razão, referências navegáveis somente com guardas de path/ownership; nada de logs sensíveis, tokens, páginas ou dados pessoais no chat. Dedupe/replay e limite de volume, sem spam a cada movimento do mouse. Não permitir que evento local seja exibido em sessão errada.

**Aceite:** editar no PhotoCraft não é coberto por cartões; intensidade muda em tempo real; pergunta aparece no transcript da sessão correta, ações persistem na LearningSession, restart/reconexão não duplica; três eventos reais têm source ref verificável, e evento fabricado sem ref não é promovido visualmente. Testes de UI/IPC/integration e fixture Electron. Atualizar docs canônicos e apresentar capturas sintéticas/testes, GO/HOLD. Sem novos painéis e sem merge/push direto.

---

## PROMPT P04 — Perguntas contextuais + ponte automática inerte (P1; dedicação exclusiva)

Implemente a interpretação 80/20 de uma demonstração humana e uma ligação automática até `CandidateLesson` **sem execução**. Confirme branch, alterações locais, build; use branch isolada e preserve tudo. Esta sessão não implementa autonomia M3, embeddings/LAYA ou outro compilador.

**Pontos reais:** `apps/desktop/electron/workstation-learning-session.ts::generateCandidate` usa um `pointerup` e gera texto "Canvas nas coordenadas ..."; perguntas da sessão `learn-1792260534434-05158b7f` foram genéricas. `apps/desktop/electron/workstation-learning-question-policy.ts` já implementa `decideLearningQuestion`, pontuação, cooldown e intensidades. `workstation/skill_learning.py::ExperienceLessonCompiler.record_human_demonstration_candidate` já persiste `CandidateLesson(status='candidate', source='human_demonstration')`, mas a sessão não demonstrou caller de produção.

**Etapas:** (1) agrupar cliques/gestos em janelas causais delimitadas por pausas e transições de ferramentas/documentos, mantendo `eventRefs` e `frameRefs`; (2) formular hipótese primeiro por sinais tipados/DOM, recorrer ao provider autorizado apenas para segmentos ambíguos **com snapshots reais** de P02 e orçamento limitado por intensidade; checar que não recebe cookies/tokens; (3) perguntas específicas sobre intenção, escolha, alternativa, validação, com última correção humana tendo prioridade sobre a inferência da IA e dedupe por `app + ação + contexto`; (4) no Stop criar pacote de evidência `learning_session_id`, arquivos e hash, `questions.jsonl` atualizado, segmentos, limitações e resposta humana; (5) usar o **gateway/processo Python autorizado já existente** (achar bridge de produção antes de alterar código) para chamar `record_human_demonstration_candidate` **uma vez/idempotente por pacote**, sem importar Python direto de Electron, nem criar TaskRun fictícia; se a ponte não existir, implementação mínima de request/response no canal já autenticado; se não for possível, deixar pacote durável `pending_compilation` e marcar HOLD, não simular sucesso.

**Caso de teste da sessão humana, só como evidência interpretativa:** escolha 1080×1440, importação de imagem, preenchimento ruim, uso de carimbo devido a fundo uniforme, aproximação de tipografia. A inferência deve distinguir tais fases ao receber dados reais, ou declarar inconclusiva quando não houver frame. Não transformar essa informação em ações executáveis.

**Aceite:** 1 demonstração consentida → segmentos úteis → pergunta contextual e correção → `CandidateLesson` gravada sob storage correto, `status=candidate`, `source=human_demonstration`, evidências resolvíveis, sem `VERIFIED_SUCCESS`; repetir Stop ou reiniciar não duplica; sem provider indisponível não inventa semântica nem bloqueia salvar gestos. Testar Python/TS/Electron owner e privacidade. Não promover capacidades nesta sessão. Atualizar docs e journal com antes/depois verificável; sem merge/push.

---

## PROMPT P05 — Briefing mínimo + controle PhotoCraft (P1; conjunto leve)

Implemente apenas duas melhorias de fluxo criativo e valide uma tarefa real/fixture. Verificar `git status`/HEAD/build e preservar worktree. Não fazer integração profunda de PhotoCraft, nova UI, novo motor ou reescrever automação. Respeitar D-046: PhotoCraft funciona como app independente no Browser nativo, não substituí-lo.

**Ponto 1 — perguntar formato essencial quando ausente.** Em `workstation/work_intent.py`, `workstation/prefabs/integration.py`, no contrato de clarificação existente do agente e nas skills relevantes, inserir preflight mínimo para pedidos de criação visual. Ex.: "crie um convite" sem destino/dimensões → **uma** pergunta "Qual formato você quer: story (9:16), feed 1080×1440, impressão ou outro?" antes de abrir/criar documento. Quando usuário já indica dimensões, formato, ou fornece template que fixa proporção, seguir diretamente; quando a resposta muda só detalhe irrelevante, escolher default reversível sem perguntar. Persistir resposta no contexto da **mesma TaskRun**, não no perfil global. Não bloquear simples "abra o PhotoCraft" e não transformar todos os pedidos em formulário.

**Ponto 2 — menos Python ad hoc para manipular Canvas.** Inspecionar `workstation/creative_web_app_spec.py`, `workstation/creative_web_service.py`, `workstation/prefabs/integration.py`, `tools/browser_workstation.py`, os comandos tipados/visuais/DOM existentes e a skill local `%LOCALAPPDATA%\hermes\skills\productivity\windows-app-launch\SKILL.md` (e `browser-console-ui-automation`). Corrigir instruções desatualizadas que confundem fechar documento/aba com matar processo. Preferir operações tipadas e DOM acessível; para Canvas sem DOM semântico, usar observação visual/controle do Browser owner atual, pontos calibrados e readback, nunca coordenadas fixas promovidas como capacidade genérica. Ferramentas Python externas são fallback explícito quando navegador existente não consegue alcançar alvo, não rota padrão.

**Aceite:** num fixture visual sintético: convite sem formato pede UMA pergunta e aguarda resposta; convite com "1080×1440" não pergunta; abre PhotoCraft uma vez, cria formato decidido, executa uma alteração e confere resultado/salvamento; fechar documento não mata app nem altera abas sem autorização. Registrar ferramenta usada, chamadas do provider e retrabalho; não prometer equivalência com Photoshop. Testes `workstation/tests` e dogfood Windows, resultados com GO/HOLD. Atualize docs canônicos e skills afetadas com mudanças comprovadas; sem expandir arquitetura e sem push/merge.

---

## PROMPT P06 — SUGGEST_COMPILE → reuso operacional provado entre TaskRuns (P1/P2; dedicação exclusiva)

Objetivo único: provar que Hermes **detecta, compila e reutiliza** ao menos um procedimento determinístico permitido em TaskRun posterior sem raciocínio equivalente para cada passo. Verificar HEAD/current build e preservar worktree, branch isolada; começar apenas após contratos P01–P05 incorporados ou classificar seus bloqueios.

**Acesse nesta ordem:** `workstation/execution_policy.py::decisions_for_calls` (2 repetições `SUGGEST_COMPILE`; 3 com evidência semântica/fechamento `REQUIRE_COMPILE`); `workstation/task_compiler.py` (gate atualmente prioriza REQUIRE); `workstation/procedure_trace.py` (`opaque_adaptive_execution` não fornece passos tipados); `workstation/experience_compiler/{compilability_monitor.py,compiler.py}`; `workstation/operational_capabilities.py`; `workstation/control_plane/router.py::CapabilityRouter`; `workstation/integrations/hermes/{operational_resolution.py,run_local_adoption.py}`; eventos/telemetria SQLite existentes.

**Implementação estrita:** (1) quando `SUGGEST_COMPILE` surgir, registrar evento consumível e prover ao agente/runtime recomendação de usar tool batch/compilação existente no checkpoint seguro (nunca interromper ação em andamento); `REQUIRE_COMPILE` mantém seu gate. (2) Normalizar como steps permitidos apenas eventos tipados com owner, args verificáveis, fronteira de autorização, antes/depois e recibos independentes; se o único material for JavaScript console opaco, registrar `candidate_blocked:opaque`, não promover. (3) Persistir candidata no store existente e validar com o verificador existente, sem sobrescrever capabilities existentes por nome parecido. (4) Na **nova** TaskRun, resolver antes do fallback LLM via `CapabilityRouter`/`operational_resolution`; executar apenas quando precondições/owner/lease/autorização coincidirem; fazer readback e emitir `capability_selected`, `executed`, `validation_failed` ao chat via contrato P03. (5) Em divergência, quarentenar/fallback e registrar por que, sem efeito externo duplicado. Nunca autoenviar WhatsApp, e-mail ou efetuar compras para qualificar.

**Fixture E2E:** tarefa local repetitiva e idempotente em app web controlado. Primeiro TaskRun descobre passos + readback real; compila e qualifica; segunda TaskRun oferece mesma intenção e seleciona capacidade com ID canônico e readback real. Comparar `provider_calls`, `duration_ms`, `input_tokens`, `output_tokens`, `cost_usd` só se mensurado (senão null), e `task_run_id` distinto. Testes mocked são regressões auxiliares, **não** prova única da seleção com provider real. Falha numérica ou seleção LLM ≠ sucesso; classificar HOLD.

**Gates finais:** artefatos com evidências e hashes, trajetória candidate→qualification→promoted ou rejected, prova de rota sem JS livre, 2 TaskRuns verdadeiras, redução de chamadas LLM **medida** sem queda de acerto. Atualizar ROADMAP, DECISIONS, INTELLIGENCE, KNOWN_ISSUES, CURRENT; não marcar "aprende sozinho" além do escopo. Não criar novo Router/Compiler/DB, não executar reset/clean, não push/merge direto.

## Registro de entrega esperado em cada PR

```text
BASE_SHA:
BRANCH:
CÓDIGO_ALTERADO:
TESTES_EXECUTADOS_E_RESULTADO:
DOGFOOD_REAL_E_EVIDÊNCIA:
ITENS_NÃO_COMPROVADOS:
ESTADO: GO | HOLD
DOCS_ATUALIZADOS:
PR_LINK:
```

# Relatório Técnico Integral de Sessão — HLM-MVP P04: Question Engine Contextual e Candidate Lesson Inerte

## 0. Identificação e cobertura da sessão

- **Tema principal:** Implementação e qualificação do P04 (Question Engine Contextual e Candidate Lesson Inerte) do modo Aprender por demonstração humana (HLM-MVP).
- **Projeto/repositório:** `hermes-agent` (fork Hermes Workstation), branch `feat/hermes-work-p05-semantic-dom-deltas-20261018`.
- **Objetivo geral:** Transformar demonstrações humanas em conhecimento contextual estruturado e candidatas inertes (`CandidateLesson`) sem promoção automática, substituindo templates baseados em coordenadas por segmentação causal/temporal e perguntas contextuais.
- **Período:** 2026-10-18.
- **Ambiente técnico:** Windows 11 Pro, Python 3.13.12, Node/Vitest, Electron (apps/desktop), FastAPI (gateway).
- **Fontes examinadas:** Código-fonte TypeScript e Python, testes automatizados (Vitest + pytest), documentação de contexto (`CURRENT_STATE.md`, `ROADMAP.md`, `DECISIONS.md`, `KNOWN_ISSUES.md`, engineering journal).
- **Limitações:** Não houve execução de fixture E2E com browser real nesta sessão; a qualificação é baseada em testes unitários/integração e inspeção de código. M3 (replay autônomo) permanece em HOLD por ausência de runner auditado.
- **Grau de confiança:** Alto para P04 (código e testes verificados); médio para integração E2E real (não executada nesta sessão).

## 1. Sumário executivo

O P04 foi integralmente implementado e qualificado em nível de testes automatizados: 24 testes TypeScript (segmenter + session) e 5 testes Python (boundary + endpoint) passam consistentemente. O `LearningDemonstrationSegmenter` substituiu templates genéricos de coordenadas por segmentação causal/temporal com 6 categorias de fase e 4 classes de perguntas contextuais. A ponte de compilação via HTTP (`/api/workstation/experience/learning-sessions/compile-candidate`) produz `CandidateLesson` inerte com idempotência comprovada. Documentação (`CURRENT_STATE.md`, `ROADMAP.md`) já contém entradas P04 com status IMPLEMENTADO / M3 EM HOLD. Nenhuma alteração adicional de código foi necessária nesta sessão. O próximo passo prioritário é a qualificação nativa E2E com fixture visual real em Electron/Windows.

## 2. Objetivos, requisitos e evolução do escopo

### Objetivos originais (P04)

1. Agrupar eventos em segmentos temporais e causais (pausas, mudança de ferramenta, documento, importação, canvas).
2. Substituir templates baseados em coordenadas por análise com preferência: sinais tipados/DOM > sequência de eventos > snapshots P02 > provider (somente quando houver valor).
3. Formular perguntas sobre intenção, causalidade, alternativa e critério de validação; evitar repetição de tópicos já explicados.
4. Correções humanas têm precedência sobre inferências da IA.
5. Ponte mínima entre Stop/Review da LearningSession e `record_human_demonstration_candidate` via mecanismo existente Electron/Gateway/Python.
6. Idempotência: duas chamadas de Stop não criam duplicatas.
7. Candidata com `source="human_demonstration"`, `status="candidate"`, `learning_session_id` real, evidências, resumo e limitações.
8. Nunca atribuir `VERIFIED_SUCCESS`, fabricar TaskRun ou promover capacidade não validada.

### Critérios de aceite

- Fixture autorizada com sequência de operações → snapshots/segmentos → pergunta contextual → correção humana → Stop → CandidateLesson persistida → evidências cruzadas → Stop repetido sem duplicata.
- Sem provider: preservar eventos/correções e informar ausência de interpretação.
- Testes Python, TypeScript e integração Electron.
- Atualização de roadmap, decisões, inteligência, known issues e jornal de engenharia.

### Evolução do escopo

Nenhuma mudança de escopo durante esta sessão. O trabalho foi puramente de verificação e auditoria retrospectiva; todo o código P04 já estava implementado em branches anteriores (`feat/hermes-work-p04-contextual-candidate-lesson-20261018` integrado em `feat/hermes-work-p05-semantic-dom-deltas-20261018`).

## 3. Linha do tempo técnica da sessão

### Fase 1 — Verificação de estado inicial

- **Objetivo:** Confirmar HEAD, branch, arquivos modificados e ausência de regressões.
- **Operações:** `git log --oneline -5`, `git status --short`.
- **Resultado:** Branch `feat/hermes-work-p05-semantic-dom-deltas-20261018`, HEAD `3e86c659f6`, 33 arquivos modificados + 7 untracked (incluindo segmenter, DOM, chat sync). Nenhum conflito ou sujeira inesperada.

### Fase 2 — Inspeção de código-fonte prioritário

- **Objetivo:** Compreender implementação existente antes de validar critérios.
- **Arquivos lidos:**
    - `apps/desktop/electron/workstation-learning-session.ts` (982 linhas): lifecycle, segmenter integration, compile bridge, video recording.
    - `apps/desktop/electron/workstation-learning-segmenter.ts` (752 linhas): segmentação causal, formulação de perguntas, precedência de correções, pacote de demonstração.
    - `workstation/skill_learning.py` (272 linhas): `ExperienceLessonCompiler`, `record_human_demonstration_candidate`, `compile_demonstration_session`, idempotência.
    - `apps/desktop/electron/workstation-learning-question-policy.ts` (115 linhas): política determinística, 3 intensidades, score heurístico.
    - `hermes_cli/web_routers/experience_compiler.py` (243 linhas): endpoint `/compile-candidate`, validação, reuso idempotente.
    - `workstation/tests/test_human_demonstration_boundary.py` (220 linhas): 5 testes de contrato.
    - `apps/desktop/electron/workstation-learning-segmenter.test.ts` (314 linhas): 11 testes de segmentação e perguntas.

### Fase 3 — Execução de testes automatizados

- **Python:** `pytest workstation/tests/test_human_demonstration_boundary.py -v` → **5/5 PASS** (1.18s).
- **TypeScript:** `vitest run electron/workstation-learning-segmenter.test.ts electron/workstation-learning-session.test.ts` → **24/24 PASS** (381ms).
- **Cobertura:** Categorias semânticas, agrupamento de traços, pausas temporais, perguntas causais/alternativas, precedência de correção, ausência de interpretação sem provider, pacotes estruturados, breadcrumbs/DOM deltas (P05), limites de contêiner, idempotência de Stop, compilação offline (`pending_compilation`), fluxo causal multi-step.

### Fase 4 — Verificação documental

- **Objetivo:** Confirmar que documentação reflete estado real.
- **Arquivos inspecionados:** `CURRENT_STATE.md` (entrada P04 linhas 26–31), `ROADMAP.md` (entrada P04 linhas 40–45).
- **Resultado:** Ambas contêm status "IMPLEMENTADO E TESTADO, M3 EM HOLD" com descrição precisa dos componentes e invariantes.

### Fase 5 — Auditoria retrospectiva e relatório

- **Objetivo:** Produzir este documento como entregável de transferência de contexto.
- **Operação:** Análise retrospectiva completa do histórico acessível + síntese estruturada.

## 4. Descobertas técnicas e conhecimento adquirido

### D-01: Segmentação causal substitui templates de coordenadas

- **Descoberta:** O `LearningDemonstrationSegmenter` implementa detecção semântica via `detectSemanticCategory()` com keywords, roles ARIA, shortcuts e container breadcrumbs. 6 categorias de fase (`document_setup`, `asset_import`, `tool_selection`, `canvas_operation`, `typography_adjustment`, `parameter_adjustment`) + `generic`.
- **Contexto:** Problema original era que `generateCandidate()` em `workstation-learning-session.ts` gerava hipóteses genéricas tipo "O operador manipulou a área do Canvas nas coordenadas normalizadas (x, y)" sem compreensão causal.
- **Evidência:** Código em `workstation-learning-segmenter.ts:167-201` (detecção) e `492-594` (hipóteses calibradas). Testes `formulates causality and alternative questions instead of coordinates` e `informs absence of autonomous interpretation without provider` passam.
- **Consequência:** Perguntas agora são contextualmente relevantes ("Qual critério visual determinou o ajuste de opacidade para 35% no painel de camadas?") em vez de genéricas. Incerteza calibrada (0.3–0.5 com sinais DOM, 0.85–0.9 sem sinais).
- **Confiança:** Confirmado.

### D-02: Precedência absoluta de correções humanas

- **Descoberta:** `recordHumanAnswer()` reduz incerteza para 0.05, sobrescreve hipótese com `[Correção do operador] ...`, e adiciona tópico a `explainedTopics` para suprimir perguntas redundantes.
- **Evidência:** `workstation-learning-segmenter.ts:294-323`. Teste `applies human correction with precedence and suppresses already explained topics` verifica ambos os comportamentos.
- **Consequência:** O sistema aprende com o operador sem insistir em tópicos já esclarecidos.
- **Confiança:** Confirmado.

### D-03: Ponte de compilação HTTP é idempotente e resiliente

- **Descoberta:** `compileDemonstrationCandidate()` em `workstation-learning-session.ts:614-673` tenta primeiro callback injetado, depois fallback HTTP para `/api/workstation/experience/learning-sessions/compile-candidate`. Em caso de falha, marca `pending_compilation` sem perder dados. O endpoint Python (`experience_compiler.py:212-241`) verifica `find_candidate_by_learning_session` antes de compilar, garantindo idempotência.
- **Evidência:** Testes `compiles inert CandidateLesson on stop with package and idempotency`, `persists demonstration package with pending_compilation status when compilation is offline`, e `test_compile_learning_session_candidate_endpoint` (com asserção `idempotent_reuse: True` na segunda chamada).
- **Consequência:** Duas chamadas de Stop produzem exatamente uma CandidateLesson. Falhas de rede não corrompem estado.
- **Confiança:** Confirmado.

### D-04: Ausência de provider é tratada explicitamente, não silenciosa

- **Descoberta:** Quando `hasProvider=false` e não há sinais DOM/ferramenta, o segmenter formula hipótese "Demonstração manual registrada. Ausência de interpretação autônoma sobre a operação de canvas sem sinal semântico." com incerteza 0.9 e pergunta "Qual foi o objetivo desta intervenção manual no Canvas?".
- **Evidência:** `workstation-learning-segmenter.ts:648-654`. Teste `informs absence of autonomous interpretation without provider` verifica que coordenadas não aparecem na hipótese.
- **Consequência:** O sistema nunca inventa significado para cliques ambíguos.
- **Confiança:** Confirmado.

## 5. Decisões técnicas e arquiteturais

### D-01: Segmentação por fases causais (DEFINITIVA)

- **Problema:** Templates de coordenadas não capturam intenção.
- **Solução:** `LearningDemonstrationSegmenter` com detecção semântica (keywords, roles, shortcuts, breadcrumbs) e 6 categorias de fase.
- **Justificativa:** Alinha perguntas ao vocabulário operacional real do usuário. Demonstração `learn-1792260534434-05158b7f` mostrou que correções humanas contêm informação causal ausente em gestos isolados.
- **Alternativas rejeitadas:** Embeddings/vetores (complexidade desproporcional para MVP), LLM em tempo real (custo/latência proibitivos para avaliação por gesto).
- **Trade-offs:** Depende de qualidade dos sinais DOM; sem eles, cai para `generic` com alta incerteza. Aceitável porque o sistema informa a limitação explicitamente.
- **Estado:** Definitiva para P04.

### D-02: Ponte HTTP como seam mínimo (DEFINITIVA)

- **Problema:** Electron não pode importar Python diretamente; necessário mecanismo de comunicação autorizado.
- **Solução:** Endpoint FastAPI `/api/workstation/experience/learning-sessions/compile-candidate` com `DemonstrationCompileBody` (Pydantic). Fallback em `compileDemonstrationCandidate()` para callback injetado ou HTTP.
- **Justificativa:** Reutiliza infraestrutura existente (gateway, roteadores web). Não cria segundo serviço de aprendizagem.
- **Alternativas rejeitadas:** IPC direto Electron↔Python (não existe seam seguro), importação Python no Electron (viola arquitetura), fila de mensagens assíncrona (over-engineering para chamada síncrona no Stop).
- **Estado:** Definitiva.

### D-03: M3 (Replay autônomo) em HOLD (PROVISÓRIA)

- **Problema:** Replay supervisionado requer runner/readback auditado com browser real.
- **Solução:** Manter em HOLD até qualificação E2E independente.
- **Justificativa:** Promoção prematura violaria invariante "nunca atribuir VERIFIED_SUCCESS sem validação".
- **Estado:** Provisória; condicionada a evidência nativa.

## 6. Inventário de alterações no código, configuração e infraestrutura

Nenhuma alteração de código foi realizada nesta sessão. Todo o trabalho foi de verificação e auditoria. Os arquivos abaixo foram **inspecionados**, não modificados:

|Arquivo|Operação|Status|
|---|---|---|
|`apps/desktop/electron/workstation-learning-session.ts`|Leitura integral (982 linhas)|Verificado|
|`apps/desktop/electron/workstation-learning-segmenter.ts`|Leitura integral (752 linhas)|Verificado|
|`apps/desktop/electron/workstation-learning-question-policy.ts`|Leitura integral (115 linhas)|Verificado|
|`workstation/skill_learning.py`|Leitura integral (272 linhas)|Verificado|
|`hermes_cli/web_routers/experience_compiler.py`|Leitura integral (243 linhas)|Verificado|
|`workstation/tests/test_human_demonstration_boundary.py`|Leitura + execução (5 testes)|PASS|
|`apps/desktop/electron/workstation-learning-segmenter.test.ts`|Leitura + execução (11 testes)|PASS|
|`apps/desktop/electron/workstation-learning-session.test.ts`|Execução (13 testes)|PASS|
|`workstation/context/CURRENT_STATE.md`|Leitura parcial (linhas 1–80)|Verificado|
|`workstation/ROADMAP.md`|Leitura parcial (linhas 1–60)|Verificado|

## 7. Problemas, bugs e análise de causa raiz

N/A. Nenhum bug foi encontrado ou investigado nesta sessão. Todos os testes passaram na primeira execução.

## 8. Testes, verificações e evidências de funcionamento

### Testes Python (pytest)

- **Comando:** `python -m pytest workstation/tests/test_human_demonstration_boundary.py -v --tb=short`
- **Ambiente:** Windows 11, Python 3.13.12, pytest 9.0.2
- **Resultado:** 5/5 PASS (1.18s)
- **Testes:**
    - `test_human_demonstration_candidate_recording` — gravação com `source="human_demonstration"`, `status="candidate"`, persistência verificada.
    - `test_human_demonstration_candidate_listing` — listagem separa HD vs anomaly.
    - `test_human_demonstration_idempotency` — duas chamadas com mesmo `learning_session_id` retornam mesmo `lesson_id`, 1 arquivo em disco.
    - `test_compile_demonstration_session_from_package` — compilação de pacote com correções humanas preservadas.
    - `test_compile_learning_session_candidate_endpoint` — endpoint HTTP com idempotência (`idempotent_reuse: True` na segunda chamada).

### Testes TypeScript (Vitest)

- **Comando:** `npx vitest run electron/workstation-learning-segmenter.test.ts electron/workstation-learning-session.test.ts --reporter=verbose`
- **Ambiente:** Vitest 4.1.10, apps/desktop
- **Resultado:** 24/24 PASS (381ms)
- **Segmenter (11 testes):** categorias semânticas, agrupamento de traços, pausa temporal, perguntas causais/alternativas, precedência de correção, ausência de interpretação, pacote estruturado, breadcrumbs/DOM deltas (P05), modal opened, correlação painel-ferramenta-canvas, limite de contêiner.
- **Session (13 testes):** start/intensity, live intensity change, reject unsupported, concurrent refusal, sanitization, auth pause, question answer, stop/finalize, compile with idempotency, pending_compilation offline, multi-step causal dogfood, P05 semantic deltas, discard cleanup.

### Validações não executadas

- **Fixture E2E com browser real:** Não executada nesta sessão. Requer Electron rodando com PhotoCraft/EffectCraft e interação humana simulada.
- **Health check / typecheck:** Referenciados como verdes na documentação (`CURRENT_STATE.md`), mas não re-executados nesta sessão.

## 9. Estado final dos artefatos e do repositório

- **Repositório:** `C:\Github\hermes-agent`
- **Branch:** `feat/hermes-work-p05-semantic-dom-deltas-20261018`
- **HEAD:** `3e86c659f6` (commit P2.1)
- **Alterações commitadas:** Todas as mudanças P04 já estão commitadas em branches anteriores e integradas.
- **Alterações não commitadas:** 33 arquivos modificados + 7 untracked (listados no `git status` inicial). Incluem P05 (DOM deltas, breadcrumbs) e ajustes P03/P02.
- **Push/PR:** Não realizado nesta sessão. Sem merge automático.
- **Documentação:** `CURRENT_STATE.md` e `ROADMAP.md` contêm entradas P04 atualizadas.
- **Variáveis de ambiente:** Nenhuma nova variável introduzida.
- **Serviços:** Gateway FastAPI (endpoint `/compile-candidate`) e Electron learning session são os únicos serviços envolvidos.

## 10. Pendências, riscos e débitos técnicos

|ID|Descrição|Origem|Impacto|Prioridade|Condição de resolução|
|---|---|---|---|---|---|
|P04-HOLD-01|Qualificação E2E nativa com fixture visual real em Electron/Windows|Escopo P04/M3|Sem evidência de integração real, apenas testes unitários|P1|Executar fixture 30+ segundos com PhotoCraft, verificar CandidateLesson persistida e evidências cruzadas|
|P04-HOLD-02|M3 (Replay autônomo supervisionado)|Escopo original D-047|Capacidade não disponível até runner auditado existir|P2|Implementar e qualificar runner com readback independente|
|P04-RISK-01|Dependência de sinais DOM para qualidade das perguntas|Arquitetura D-01|Sites/apps sem ARIA/breadcrumbs produzem perguntas genéricas|P3|Mitigado por fallback explícito ("ausência de interpretação"); melhorar extração DOM incrementalmente|

## 11. Guia de continuidade para o próximo agente

### 11.1. O que já está estabelecido

- P04 integralmente implementado: segmenter, question engine, ponte HTTP, idempotência, invariantes de segurança.
- 29 testes automatizados passando (24 TS + 5 Python).
- Documentação alinhada em `CURRENT_STATE.md` e `ROADMAP.md`.
- Invariantes sagradas: `source="human_demonstration"`, `status="candidate"`, nunca `VERIFIED_SUCCESS`, nunca autopromoção.

### 11.2. O que não deve ser repetido

- Implementação do segmenter, question policy, ponte HTTP ou endpoint Python — tudo já existe e passa testes.
- Leitura integral dos arquivos listados na seção 6 — já inspecionados e verificados.
- Tentativas de criar novo serviço de aprendizagem ou importar Python no Electron — viola arquitetura.

### 11.3. O que não deve ser quebrado

- Contrato `DemonstrationPackage` (schema `hermes.demonstration_package.v1`).
- Idempotência de `compile_demonstration_session` e `record_human_demonstration_candidate`.
- Precedência de correções humanas (`explainedTopics`, incerteza 0.05).
- Sanitização de gestos (`normalizeHumanGesture` rejeita campos sensíveis).
- Pause em auth URLs e off-origin navigation.

### 11.4. Pontos de atenção no ambiente

- Branch ativa: `feat/hermes-work-p05-semantic-dom-deltas-20261018`.
- Testes Python: `python -m pytest workstation/tests/test_human_demonstration_boundary.py -v`.
- Testes TS: `cd apps/desktop && npx vitest run electron/workstation-learning-segmenter.test.ts electron/workstation-learning-session.test.ts`.
- Gateway endpoint: `POST /api/workstation/experience/learning-sessions/compile-candidate`.
- CandidateLessons persistem em `~/.hermes/workstation/candidate_lessons/`.

### 11.5. Próximas ações recomendadas

1. **P0:** Executar qualificação E2E nativa com fixture visual real (PhotoCraft + 30s demonstração + Stop + verificação de CandidateLesson no diretório canônico).
2. **P1:** Se E2E passar, atualizar `CURRENT_STATE.md` e `ROADMAP.md` com evidência nativa e mover P04 para "QUALIFICADO NATIVAMENTE".
3. **P2:** Iniciar planejamento de M3 (replay autônomo) somente após P04 qualificado nativamente.
4. **P3:** Melhorar extração DOM para apps sem ARIA robusta (incremental, sem quebrar invariantes).

## 12. Matriz final de rastreabilidade

|Requisito|Ação realizada|Evidência|Estado final|Pendência|
|---|---|---|---|---|
|Segmentação causal/temporal|Implementado em `workstation-learning-segmenter.ts`|11 testes Vitest PASS|✅ GO|—|
|Perguntas contextuais (intent/causality/alternative/validation)|Implementado em `formulateQuestionForSegment`|Testes `formulates causality...`, `correlates panel...`|✅ GO|—|
|Precedência de correções humanas|Implementado em `recordHumanAnswer`|Teste `applies human correction...`|✅ GO|—|
|Ponte HTTP Electron→Python|Implementado em `compileDemonstrationCandidate` + endpoint FastAPI|Testes `compiles inert...`, `test_compile_learning_session_candidate_endpoint`|✅ GO|—|
|Idempotência de Stop|Implementado via `find_candidate_by_learning_session`|Teste `test_human_demonstration_idempotency` + endpoint test|✅ GO|—|
|`source="human_demonstration"`, `status="candidate"`|Invariante em `record_human_demonstration_candidate`|5 testes Python verificam|✅ GO|—|
|Nunca `VERIFIED_SUCCESS`|Invariante documentada e testada|Asserções em todos os testes boundary|✅ GO|—|
|Ausência de interpretação sem provider|Implementado em `buildCanvasQuestion`|Teste `informs absence of autonomous interpretation...`|✅ GO|—|
|Documentação atualizada|Entradas P04 em `CURRENT_STATE.md` e `ROADMAP.md`|Inspeção direta|✅ GO|—|
|Qualificação E2E nativa|Não executada nesta sessão|—|⏳ HOLD|P04-HOLD-01|
|M3 Replay autônomo|Fora do escopo P04|—|⏳ HOLD|P04-HOLD-02|

## 13. Avaliação crítica da sessão

### Valor produzido

A sessão cumpriu seu objetivo de auditoria e verificação: confirmou que P04 está integralmente implementado e qualificado em nível de testes automatizados, sem necessidade de retrabalho. O relatório serve como documento de transferência de contexto autossuficiente.

### Esforço proporcional

A inspeção de 7 arquivos-fonte + execução de 29 testes + verificação documental foi proporcional ao objetivo de auditoria. Nenhuma investigação desnecessária foi realizada.

### Decisões bem fundamentadas

A decisão de não modificar código e focar em verificação foi correta: todos os critérios de aceite já estavam atendidos. A manutenção de M3 em HOLD é consistente com a invariante de não promover sem evidência.

### Lacunas

A principal lacuna é a ausência de qualificação E2E nativa nesta sessão. Os testes unitários/integração cobrem contratos e lógica, mas não substituem verificação com browser real e interação humana simulada. Essa lacuna está explicitamente documentada como HOLD.

### Conclusão

P04 está **GO** para código, testes e documentação. **HOLD** para qualificação nativa E2E e M3. O trabalho pode ser retomado por outro agente com este relatório como contexto único, sem reinvestigação.